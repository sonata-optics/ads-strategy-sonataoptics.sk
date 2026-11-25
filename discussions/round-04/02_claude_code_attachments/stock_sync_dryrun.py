#!/usr/bin/env python3
"""Local dry-run model of the stock sync (R3-CLAUDE-06 / R3-CHATGPT-10 / R4-CLAUDE-05/09/10). No network, no API calls.

v3 (04d, 25.11.2026):
  * Confirmations expire: only confirmations observed within confirmation_window_hours (default 6 h, a project
    default equal to the freshness limit, not a business SLA) and not in the future are counted (R4-CLAUDE-09).
  * Observed set/unset of 'sync-hold' resets the confirmation history; the previous hold state is stored
    (hold_seen). A hold set and removed BETWEEN two polls cannot be seen without change_event provenance.
  * Account context (R4-CLAUDE-10): the read must carry customer_id == allowed_customer_id; every managed object
    carries ads_customer_id from the trusted Ads object; a full resource_name with another customer -> ALERT.
    A short composite key never gets a customer appended silently: it is accepted only with a trusted object context.
  * Feed label may contain '-' or '_' (Merchant Center allows it) but must be in the configured allowed set.
  * Partial failure: commit() accepts per-object apply results; reconcile() rereads the real Ads state before the
    next cycle and trusts observed status/labels over stored assumptions.
v2 rules kept: plan() is pure and returns (actions, proposed_state); distinct read_id + minimum interval; upstream
freshness when available; sync-hold freezes both directions; unknown pause owner never enables; mass-flip HALT.
Managed objects = model Search ad groups only. Shopping product groups are never paused by sync.
"""
import copy, csv, json, os, re, sys
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
SYNC_LABEL, HOLD_LABEL = 'paused-by-sync', 'sync-hold'
DEFAULT_CFG = dict(kill_switch=False, max_age_hours=6, max_future_skew_minutes=5, min_confirm_interval_minutes=30,
                   confirmation_window_hours=6, max_flip_share=0.30, min_flips_for_guard=2, enable_confirmations=2,
                   allowed_customer_id='9492722541',
                   allowed_identity=dict(merchant_id='5831333799', channel='ONLINE', language='sk', feed_labels=('SK',)))
ID_RE = re.compile(r'^(?:customers/(\d+)/shoppingProducts/)?(\d+)~(ONLINE|LOCAL)~([a-z]{2})~([A-Za-z0-9][A-Za-z0-9_-]{0,49})~([^~/\s]+)$')


def parse_identity(raw):
    """Returns dict (customer_id may be None for a short key) or None for an unknown format."""
    m = ID_RE.match(raw or '')
    if not m:
        return None
    cid, mid, ch, lang, fl, oid = m.groups()
    return dict(customer_id=cid, merchant_id=mid, channel=ch, language=lang, feed_label=fl, offer_id=oid)


def key(idt):
    return '~'.join(idt[k] for k in ('merchant_id', 'channel', 'language', 'feed_label', 'offer_id'))


def plan(objects, read, cfg, now, journal, run_id):
    """PURE planner. Returns (actions, proposed_state). Inputs are never modified."""
    objects = copy.deepcopy(objects)
    proposed = {}

    def log(o, decision, reason, action='', basis=''):
        journal.append(dict(run_id=run_id, ts=now.isoformat(), read_id=read.get('read_id', ''),
                            object_id=o['object_id'] if o else '*', identity=o['identity'] if o else '*',
                            decision=decision, reason=reason, action=action, freshness_basis=basis))

    if cfg['kill_switch']:
        log(None, 'NO_OP', 'kill switch ON'); return [], {}
    if not read.get('ok'):
        log(None, 'NO_OP', 'API error: ' + read.get('error', 'unknown')); return [], {}
    if not read.get('items'):
        log(None, 'NO_OP', 'empty response is not evidence of OOS'); return [], {}
    if not read.get('read_id'):
        log(None, 'ALERT', 'read without read_id: provenance unknown, no action'); return [], {}
    if read.get('customer_id') != cfg['allowed_customer_id']:
        log(None, 'ALERT', f'read customer context {read.get("customer_id")!r} is not the allowed account: no action'); return [], {}
    fetched = read['fetched_at']
    skew = timedelta(minutes=cfg['max_future_skew_minutes'])
    if fetched > now + skew:
        log(None, 'ALERT', f'read timestamp in the future ({fetched})'); return [], {}
    if now - fetched > timedelta(hours=cfg['max_age_hours']):
        log(None, 'NO_OP', f'stale fetch {now - fetched}'); return [], {}

    actions, allow = [], cfg['allowed_identity']
    window = timedelta(hours=cfg['confirmation_window_hours'])
    for o in objects:
        if not o['allowlisted']:
            log(o, 'SKIP', 'not in allowlist'); continue
        if o.get('ads_customer_id') != cfg['allowed_customer_id']:
            log(o, 'ALERT', f'managed object customer context {o.get("ads_customer_id")!r} missing or foreign: no action'); continue
        idt = parse_identity(o['identity'])
        if idt is None:
            log(o, 'ALERT', 'identity format not recognised'); continue
        if idt['customer_id'] is not None and idt['customer_id'] != cfg['allowed_customer_id']:
            log(o, 'ALERT', f'resource_name belongs to another customer ({idt["customer_id"]}): no action'); continue
        if (idt['merchant_id'], idt['channel'], idt['language']) != (allow['merchant_id'], allow['channel'], allow['language']) \
                or idt['feed_label'] not in allow['feed_labels']:
            log(o, 'SKIP', 'identity outside allowed merchant/destination/feed label'); continue
        st = {}
        hold_now = HOLD_LABEL in o.get('labels', [])
        conf = list(o.get('confirmations', []))
        if hold_now != bool(o.get('hold_seen', False)):
            conf = []
            st.update(hold_seen=hold_now, confirmations=[])
            log(o, 'RESET', f'sync-hold {"set" if hold_now else "removed"} since last observation: confirmation history reset')
        if hold_now:
            if st:
                proposed[o['object_id']] = st
            log(o, 'NO_OP', 'sync-hold: object frozen in both directions'); continue
        # drop expired and future-dated confirmations (R4-CLAUDE-09)
        kept = [c for c in conf if now - window <= c['observed_at'] <= now + skew]
        if len(kept) != len(conf):
            log(o, 'PRUNE', f'{len(conf) - len(kept)} confirmation(s) outside the {cfg["confirmation_window_hours"]} h window or in the future dropped')
            st['confirmations'] = kept
        conf = kept

        item = read['items'].get(key(idt))
        if item is None:
            if st:
                proposed[o['object_id']] = st
            log(o, 'ALERT', 'item missing from read: not treated as OOS'); continue
        av, up = item.get('availability'), item.get('upstream_updated_at')
        basis = 'upstream_updated_at' if up else 'fetch_time'
        obs = up or fetched
        if up and up > now + skew:
            log(o, 'ALERT', 'upstream time in the future', basis=basis); continue
        if now - obs > timedelta(hours=cfg['max_age_hours']):
            log(o, 'NO_OP', f'stale {basis}', basis=basis); continue
        if av not in ('IN_STOCK', 'OUT_OF_STOCK', 'PREORDER', 'BACKORDER'):
            log(o, 'ALERT', f'unknown availability {av}', basis=basis); continue

        def done():
            if st:
                proposed[o['object_id']] = st
        if av == 'OUT_OF_STOCK':
            st['confirmations'] = []
            done()
            if o['status'] == 'ENABLED':
                actions.append((o['object_id'], 'PAUSE', SYNC_LABEL))
                log(o, 'PAUSE', 'OOS and enabled (manual enable alone does not authorise advertising OOS; use sync-hold)', f'PAUSE+label {SYNC_LABEL}', basis)
            else:
                log(o, 'NO_OP', f'OOS, already paused (owner={o.get("pause_owner")})', basis=basis)
            continue
        if av != 'IN_STOCK':
            done(); log(o, 'NO_OP', f'{av}: no automatic enable (owner rule required)', basis=basis); continue
        if o['status'] == 'ENABLED':
            done()
            if SYNC_LABEL in o.get('labels', []):
                actions.append((o['object_id'], 'REMOVE_LABEL', SYNC_LABEL))
                log(o, 'CLEANUP', 'enabled by a human while labelled; remove stale label only', 'remove label', basis)
            else:
                log(o, 'NO_OP', 'in stock and enabled', basis=basis)
            continue
        if o.get('pause_owner') != 'SYNC' or SYNC_LABEL not in o.get('labels', []):
            done(); log(o, 'NO_OP', f'paused by {o.get("pause_owner") or "UNKNOWN"}: sync never enables it', basis=basis); continue
        if any(c['read_id'] == read['read_id'] for c in conf):
            done(); log(o, 'WAIT', 'same read already counted: replay adds no confirmation', basis=basis); continue
        if conf and obs <= conf[-1]['observed_at']:
            done(); log(o, 'WAIT', 'observation not newer than previous confirmation', basis=basis); continue
        if conf and obs - conf[-1]['observed_at'] < timedelta(minutes=cfg['min_confirm_interval_minutes']):
            done(); log(o, 'WAIT', 'below minimum interval between confirmations', basis=basis); continue
        conf.append(dict(read_id=read['read_id'], observed_at=obs))
        st['confirmations'] = conf
        done()
        if len(conf) < cfg['enable_confirmations']:
            log(o, 'WAIT', f'in-stock confirmation {len(conf)}/{cfg["enable_confirmations"]}', basis=basis); continue
        actions.append((o['object_id'], 'ENABLE', SYNC_LABEL))
        log(o, 'ENABLE', 'in stock, paused by sync, confirmed by distinct fresh reads', 'ENABLE+remove label', basis)

    flips = [a for a in actions if a[1] in ('PAUSE', 'ENABLE')]
    n_allow = sum(1 for o in objects if o['allowlisted']) or 1
    if len(flips) >= cfg['min_flips_for_guard'] and len(flips) / n_allow > cfg['max_flip_share']:
        log(None, 'HALT', f'{len(flips)}/{n_allow} objects would flip > {cfg["max_flip_share"]:.0%}: manual confirmation required')
        return [], {}
    return actions, proposed


def commit(objects, actions, proposed, apply_ok=True):
    """Return NEW state. apply_ok: True (all applied), False (nothing committed) or {object_id: bool} per object.
    An object whose action failed keeps its stored state; its real state must be re-read (reconcile) before the next cycle."""
    if apply_ok is False:
        return copy.deepcopy(objects)
    res = {a[0]: True for a in actions} if apply_ok is True else dict(apply_ok)
    new = copy.deepcopy(objects)
    by = {o['object_id']: o for o in new}
    acted = {a[0] for a in actions}
    for oid, st in proposed.items():
        if oid in acted and not res.get(oid, False):
            continue                                  # unknown outcome: do not commit bookkeeping either
        by[oid].update(copy.deepcopy(st))
    for oid, act, _ in actions:
        if not res.get(oid, False):
            by[oid]['needs_reconcile'] = True
            continue
        o = by[oid]
        labels = set(o.get('labels', []))
        if act == 'PAUSE':
            o['status'], o['pause_owner'] = 'PAUSED', 'SYNC'; labels.add(SYNC_LABEL); o['confirmations'] = []
        elif act == 'ENABLE':
            o['status'], o['pause_owner'] = 'ENABLED', None; labels.discard(SYNC_LABEL); o['confirmations'] = []
        elif act == 'REMOVE_LABEL':
            labels.discard(SYNC_LABEL); o['pause_owner'] = None
        o['labels'] = sorted(labels)
    return new


def reconcile(stored, observed, journal, run_id='reconcile'):
    """Before each cycle: trust the re-read Ads state {object_id: {status, labels}} over stored assumptions.
    Mismatch -> observed values win; a PAUSED object without the sync label gets owner UNKNOWN; history reset."""
    new = copy.deepcopy(stored)
    for o in new:
        ob = observed.get(o['object_id'])
        if ob is None:
            journal.append(dict(run_id=run_id, ts='', read_id='', object_id=o['object_id'], identity=o['identity'],
                                decision='ALERT', reason='object not found on re-read', action='', freshness_basis=''))
            continue
        if ob['status'] != o['status'] or sorted(ob['labels']) != sorted(o.get('labels', [])) or o.get('needs_reconcile'):
            journal.append(dict(run_id=run_id, ts='', read_id='', object_id=o['object_id'], identity=o['identity'],
                                decision='RECONCILE', reason=f'stored {o["status"]}/{o.get("labels")} -> observed {ob["status"]}/{ob["labels"]}',
                                action='', freshness_basis=''))
            o['status'], o['labels'] = ob['status'], sorted(ob['labels'])
            if ob['status'] == 'PAUSED':
                o['pause_owner'] = 'SYNC' if SYNC_LABEL in ob['labels'] else 'UNKNOWN'
            else:
                o['pause_owner'] = None
            o['confirmations'] = []
            o.pop('needs_reconcile', None)
    return new


# ---------------- test fixtures ----------------
CID = '9492722541'


def obj(oid, offer, status='ENABLED', owner=None, allow=True, fl='SK', labels=None, conf=None, raw=None, cust=CID, hold_seen=None):
    labels = labels if labels is not None else ([SYNC_LABEL] if owner == 'SYNC' else [])
    return dict(object_id=oid, ads_customer_id=cust, identity=raw or f'5831333799~ONLINE~sk~{fl}~{offer}', status=status,
                pause_owner=owner, labels=labels, allowlisted=allow, confirmations=conf or [],
                hold_seen=(HOLD_LABEL in labels) if hold_seen is None else hold_seen)


def rd(now, items, ok=True, age_h=1, err='', read_id='R1', upstream=None, cust=CID, fl='SK'):
    return dict(ok=ok, read_id=read_id, customer_id=cust, fetched_at=now - timedelta(hours=age_h), error=err,
                items={f'5831333799~ONLINE~sk~{fl}~{k}': dict(availability=v, **({'upstream_updated_at': upstream} if upstream else {}))
                       for k, v in items.items()})


def scenarios():
    now = datetime(2026, 11, 15, 12, 0)
    cfg = copy.deepcopy(DEFAULT_CFG)
    base = lambda: [obj('AG_103933', '103933'), obj('AG_26113', '26113'), obj('AG_103640', '103640'), obj('AG_47420', '47420')]
    allin = {'103933': 'IN_STOCK', '26113': 'IN_STOCK', '103640': 'IN_STOCK', '47420': 'IN_STOCK'}
    c1 = lambda h: [dict(read_id='R0', observed_at=now - timedelta(hours=h))]
    sk2 = dict(cfg, allowed_identity=dict(cfg['allowed_identity'], feed_labels=('SK', 'SK-2')))
    S = [
        ('S01', 'OOS enabled group is paused and labelled', base(), rd(now, dict(allin, **{'103933': 'OUT_OF_STOCK'})), cfg, [('AG_103933', 'PAUSE')]),
        ('S02', 'API error -> no action', base(), rd(now, {}, ok=False, err='500'), cfg, []),
        ('S03', 'empty response is not OOS', base(), rd(now, {}), cfg, []),
        ('S04', 'stale read (8 h) -> no action', base(), rd(now, {'103933': 'OUT_OF_STOCK'}, age_h=8), cfg, []),
        ('S05', 'kill switch -> no action', base(), rd(now, {'103933': 'OUT_OF_STOCK'}), dict(cfg, kill_switch=True), []),
        ('S06', 'manual pause is never auto-enabled', [obj('AG_103933', '103933', 'PAUSED', 'MANUAL')], rd(now, {'103933': 'IN_STOCK'}), cfg, []),
        ('S07', 'new group created PAUSED for review is never labelled or enabled', [obj('AG_26130', '26130', 'PAUSED', 'REVIEW')], rd(now, {'26130': 'IN_STOCK'}), cfg, []),
        ('S08', 'first IN_STOCK read only waits', [obj('AG_47420', '47420', 'PAUSED', 'SYNC')], rd(now, {'47420': 'IN_STOCK'}), cfg, []),
        ('S09', 'item missing from read -> alert, not OOS', base(), rd(now, {'26113': 'IN_STOCK'}), cfg, []),
        ('S10', 'identity with another feed label ignored even if offer_id equal', [obj('AG_X', '103933', fl='AT')], rd(now, {'103933': 'OUT_OF_STOCK'}), cfg, []),
        ('S11', 'non-allowlisted object untouched', [obj('AG_OLD', '103933', allow=False)], rd(now, {'103933': 'OUT_OF_STOCK'}), cfg, []),
        ('S12', 'mass flip >30% halts the run', base(), rd(now, dict(allin, **{'103933': 'OUT_OF_STOCK', '26113': 'OUT_OF_STOCK'})), cfg, []),
        ('S13', 'manually enabled while labelled -> only remove stale label', [obj('AG_103640', '103640', 'ENABLED', None, labels=[SYNC_LABEL])], rd(now, {'103640': 'IN_STOCK'}), cfg, [('AG_103640', 'REMOVE_LABEL')]),
        ('S14', 'PREORDER/BACKORDER never auto-enable', [obj('AG_47420', '47420', 'PAUSED', 'SYNC')], rd(now, {'47420': 'BACKORDER'}), cfg, []),
        ('C2a', 'full resource_name of the allowed customer is parsed and acted on (OOS -> PAUSE)',
         [obj('AG_103933', '103933', raw=f'customers/{CID}/shoppingProducts/5831333799~ONLINE~sk~SK~103933')], rd(now, {'103933': 'OUT_OF_STOCK'}), cfg, [('AG_103933', 'PAUSE')]),
        ('C2b', 'unknown identity format -> ALERT, no action', [obj('AG_103933', '103933', raw='103933')], rd(now, {'103933': 'OUT_OF_STOCK'}), cfg, []),
        ('C2c', 'resource_name of a foreign customer (1234567890) -> ALERT, no action',
         [obj('AG_103933', '103933', raw='customers/1234567890/shoppingProducts/5831333799~ONLINE~sk~SK~103933')], rd(now, {'103933': 'OUT_OF_STOCK'}), cfg, []),
        ('C2d', 'feed label with hyphen SK-2 parsed and accepted when it is in the allowed set', [obj('AG_103933', '103933', fl='SK-2')],
         rd(now, {'103933': 'OUT_OF_STOCK'}, fl='SK-2'), sk2, [('AG_103933', 'PAUSE')]),
        ('C2e', 'feed label SK-2 not in the allowed set -> SKIP', [obj('AG_103933', '103933', fl='SK-2')], rd(now, {'103933': 'OUT_OF_STOCK'}, fl='SK-2'), cfg, []),
        ('C2f', 'short key without trusted object customer context -> ALERT (no silent customer append)', [obj('AG_103933', '103933', cust=None)],
         rd(now, {'103933': 'OUT_OF_STOCK'}), cfg, []),
        ('C2g', 'managed object belongs to another customer -> ALERT', [obj('AG_103933', '103933', cust='1234567890')], rd(now, {'103933': 'OUT_OF_STOCK'}), cfg, []),
        ('C2h', 'read from another customer -> ALERT for the whole run', base(), rd(now, {'103933': 'OUT_OF_STOCK'}, cust='1234567890'), cfg, []),
        ('C2i', 'read without customer context -> ALERT', base(), rd(now, {'103933': 'OUT_OF_STOCK'}, cust=None), cfg, []),
        ('C3', 'sync-hold on a sync-paused group blocks enable', [obj('AG_103933', '103933', 'PAUSED', 'SYNC', labels=[SYNC_LABEL, HOLD_LABEL], conf=c1(3))],
         rd(now, {'103933': 'IN_STOCK'}), cfg, []),
        ('C4a', 'sync-hold on an enabled OOS group blocks pause', [obj('AG_103933', '103933', 'ENABLED', 'MANUAL', labels=[HOLD_LABEL])], rd(now, {'103933': 'OUT_OF_STOCK'}), cfg, []),
        ('C4b', 'manual enable WITHOUT hold does not authorise OOS advertising -> PAUSE', [obj('AG_103933', '103933', 'ENABLED', 'MANUAL')], rd(now, {'103933': 'OUT_OF_STOCK'}), cfg, [('AG_103933', 'PAUSE')]),
        ('C3x', 'Cowork: 5-day-old confirmation + one fresh read -> WAIT (expired confirmation dropped)', [obj('AG_103933', '103933', 'PAUSED', 'SYNC', conf=[dict(read_id='R0', observed_at=now - timedelta(days=5))])],
         rd(now, {'103933': 'IN_STOCK'}), cfg, []),
        ('W1', 'confirmation exactly at the 6 h window edge is kept -> ENABLE', [obj('AG_103933', '103933', 'PAUSED', 'SYNC', conf=c1(6))], rd(now, {'103933': 'IN_STOCK'}, age_h=0), cfg, [('AG_103933', 'ENABLE')]),
        ('W2', 'confirmation 6 h 1 min old is dropped -> WAIT', [obj('AG_103933', '103933', 'PAUSED', 'SYNC', conf=[dict(read_id='R0', observed_at=now - timedelta(hours=6, minutes=1))])],
         rd(now, {'103933': 'IN_STOCK'}, age_h=0), cfg, []),
        ('W3', 'stored confirmation dated in the future is dropped -> WAIT', [obj('AG_103933', '103933', 'PAUSED', 'SYNC', conf=[dict(read_id='R0', observed_at=now + timedelta(hours=2))])],
         rd(now, {'103933': 'IN_STOCK'}, age_h=0), cfg, []),
        ('U1', 'paused with UNKNOWN owner is never enabled', [obj('AG_103933', '103933', 'PAUSED', None, labels=[])], rd(now, {'103933': 'IN_STOCK'}), cfg, []),
        ('U2', 'owner SYNC but label missing -> treated as unknown, no enable', [obj('AG_103933', '103933', 'PAUSED', 'SYNC', labels=[], conf=c1(3))], rd(now, {'103933': 'IN_STOCK'}), cfg, []),
        ('F1', 'read timestamp in the future -> ALERT', base(), dict(rd(now, {'103933': 'OUT_OF_STOCK'}), fetched_at=now + timedelta(hours=1)), cfg, []),
        ('F2', 'read without read_id -> ALERT', base(), dict(rd(now, {'103933': 'OUT_OF_STOCK'}), read_id=''), cfg, []),
        ('F3', 'stale upstream time even with fresh fetch -> no action', [obj('AG_103933', '103933')], rd(now, {'103933': 'OUT_OF_STOCK'}, upstream=now - timedelta(hours=10)), cfg, []),
    ]
    return now, S


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    now, S = scenarios()
    journal, results = [], []
    for sid, desc, objs, read, cfg, expected in S:
        before = copy.deepcopy(objs)
        acts, _ = plan(objs, read, cfg, now, journal, sid)
        got = [(a[0], a[1]) for a in acts]
        results.append((sid, desc, got == expected and objs == before, got, expected))
    cfg = DEFAULT_CFG
    allin = {'103933': 'IN_STOCK', '26113': 'IN_STOCK', '103640': 'IN_STOCK', '47420': 'IN_STOCK'}
    four = lambda: [obj('AG_103933', '103933'), obj('AG_26113', '26113'), obj('AG_103640', '103640'), obj('AG_47420', '47420')]
    # S15 idempotency through commit
    objs = four(); r = rd(now, dict(allin, **{'103933': 'OUT_OF_STOCK'}))
    a1, p1 = plan(objs, r, cfg, now, journal, 'S15a'); st = commit(objs, a1, p1)
    a2, _ = plan(st, r, cfg, now, journal, 'S15b')
    results.append(('S15', 'idempotent: same input after commit -> 0 actions', len(a1) == 1 and a2 == [], a2, []))
    # C1 replay
    objs = [obj('AG_103933', '103933', 'PAUSED', 'SYNC')]
    r = rd(now, {'103933': 'IN_STOCK'}, read_id='R7')
    a1, p1 = plan(objs, r, cfg, now, journal, 'C1a'); st1 = commit(objs, a1, p1)
    a2, _ = plan(st1, r, cfg, now + timedelta(minutes=5), journal, 'C1b')
    results.append(('C1', 'replaying the same read adds no confirmation', a1 == [] and a2 == [], a2, []))
    r2 = rd(now + timedelta(hours=1), {'103933': 'IN_STOCK'}, read_id='R8')
    a3, _ = plan(st1, r2, cfg, now + timedelta(hours=1), journal, 'S16')
    results.append(('S16', 'second distinct fresh read (unchanged IN_STOCK) enables', [(x[0], x[1]) for x in a3] == [('AG_103933', 'ENABLE')], a3, [('AG_103933', 'ENABLE')]))
    r3 = rd(now - timedelta(minutes=50), {'103933': 'IN_STOCK'}, read_id='R9', age_h=0)
    a4, _ = plan(st1, r3, cfg, now, journal, 'I1')
    results.append(('I1', 'distinct read below minimum interval does not confirm', a4 == [], a4, []))
    # H1: hold set on a sync-paused group with one confirmation -> reset; after unhold two new reads needed
    o = [obj('AG_103933', '103933', 'PAUSED', 'SYNC', conf=[dict(read_id='R0', observed_at=now - timedelta(hours=1))], hold_seen=False)]
    o[0]['labels'] = [SYNC_LABEL, HOLD_LABEL]
    a, p = plan(o, rd(now, {'103933': 'IN_STOCK'}, read_id='H1a', age_h=0), cfg, now, journal, 'H1a'); s1 = commit(o, a, p)
    s1[0]['labels'] = [SYNC_LABEL]                                   # human removes the hold
    t = now + timedelta(hours=1)
    a, p = plan(s1, rd(t, {'103933': 'IN_STOCK'}, read_id='H1b', age_h=0), cfg, t, journal, 'H1b'); s2 = commit(s1, a, p)
    first_after_unhold_waits = a == [] and len(s2[0]['confirmations']) == 1 and s2[0]['hold_seen'] is False
    t2 = t + timedelta(hours=1)
    a, p = plan(s2, rd(t2, {'103933': 'IN_STOCK'}, read_id='H1c', age_h=0), cfg, t2, journal, 'H1c')
    results.append(('H1', 'hold set resets history; after unhold one fresh read waits, the second enables',
                    s1[0]['confirmations'] == [] and s1[0]['hold_seen'] is True and first_after_unhold_waits and [(x[0], x[1]) for x in a] == [('AG_103933', 'ENABLE')], a, [('AG_103933', 'ENABLE')]))
    # H2: hold -> OOS -> unhold: hold freezes an enabled group through OOS; after unhold the OOS pause happens
    o = [obj('AG_103933', '103933', 'ENABLED', 'MANUAL', labels=[HOLD_LABEL])]
    a, p = plan(o, rd(now, {'103933': 'OUT_OF_STOCK'}, read_id='H2a', age_h=0), cfg, now, journal, 'H2a'); s1 = commit(o, a, p)
    s1[0]['labels'] = []
    a2, p2 = plan(s1, rd(t, {'103933': 'OUT_OF_STOCK'}, read_id='H2b', age_h=0), cfg, t, journal, 'H2b')
    results.append(('H2', 'hold -> OOS (no action) -> unhold -> PAUSE', a == [] and [(x[0], x[1]) for x in a2] == [('AG_103933', 'PAUSE')], a2, [('AG_103933', 'PAUSE')]))
    # M1 purity on HALT; M2 failed apply
    objs = four(); snap = copy.deepcopy(objs)
    a5, p5 = plan(objs, rd(now, dict(allin, **{'103933': 'OUT_OF_STOCK', '26113': 'OUT_OF_STOCK'})), cfg, now, journal, 'M1')
    results.append(('M1', 'HALT: no actions, no proposed state, input unchanged', a5 == [] and p5 == {} and objs == snap, a5, []))
    objs = [obj('AG_103933', '103933', 'PAUSED', 'SYNC')]
    a6, p6 = plan(objs, rd(now, {'103933': 'IN_STOCK'}, read_id='R10'), cfg, now, journal, 'M2')
    st = commit(objs, a6, p6, apply_ok=False)
    results.append(('M2', 'failed apply -> stored confirmations not advanced', st == objs and st[0]['confirmations'] == [], st[0]['confirmations'], []))
    # P1/P2: partial failure + reconcile from re-read Ads state
    objs = [obj(f'AG_{i}', i) for i in ('103933', '26113', '103640', '47420', '55858', '55369', '55859')]
    r = rd(now, {i: ('OUT_OF_STOCK' if i in ('103933', '26113') else 'IN_STOCK') for i in ('103933', '26113', '103640', '47420', '55858', '55369', '55859')})
    a, p = plan(objs, r, cfg, now, journal, 'P1')
    st = commit(objs, a, p, apply_ok={'AG_103933': True, 'AG_26113': False})
    by = {x['object_id']: x for x in st}
    p1 = sorted((x[0], x[1]) for x in a) == [('AG_103933', 'PAUSE'), ('AG_26113', 'PAUSE')] and by['AG_103933']['status'] == 'PAUSED' \
        and by['AG_26113']['status'] == 'ENABLED' and by['AG_26113'].get('needs_reconcile') is True
    results.append(('P1', 'partial success: only the applied object changes; the failed one is marked for re-read', p1, sorted(x[0] for x in a), ['AG_103933', 'AG_26113']))
    observed = {x['object_id']: dict(status=x['status'], labels=x['labels']) for x in st}
    observed['AG_26113'] = dict(status='PAUSED', labels=[SYNC_LABEL])          # API timed out but the change did land
    observed['AG_103640'] = dict(status='PAUSED', labels=[])                    # a human paused it meanwhile
    rec = reconcile(st, observed, journal, 'P2')
    rb = {x['object_id']: x for x in rec}
    p2 = rb['AG_26113']['status'] == 'PAUSED' and rb['AG_26113']['pause_owner'] == 'SYNC' and 'needs_reconcile' not in rb['AG_26113'] \
        and rb['AG_103640']['pause_owner'] == 'UNKNOWN'
    a, _ = plan(rec, rd(now + timedelta(hours=1), {i: 'IN_STOCK' for i in ('103933', '26113', '103640', '47420', '55858', '55369', '55859')}, read_id='P2b', age_h=0),
                cfg, now + timedelta(hours=1), journal, 'P2b')
    results.append(('P2', 'reconcile trusts re-read state; human pause becomes UNKNOWN owner and is never enabled',
                    p2 and not [x for x in a if x[0] == 'AG_103640'], [(x[0], x[1]) for x in a], []))
    with open(os.path.join(HERE, 'stock_sync_dryrun_log.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(journal[0].keys())); w.writeheader(); w.writerows(journal)
    with open(os.path.join(HERE, 'stock_sync_dryrun_results.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['scenario', 'description', 'result', 'actions', 'expected'])
        for sid, desc, ok, got, exp in results:
            w.writerow([sid, desc, 'PASS' if ok else 'FAIL', json.dumps(got, default=str), json.dumps(exp)])
    for sid, desc, ok, got, exp in results:
        print(sid, 'PASS' if ok else 'FAIL', desc)
    print('scenarios', sum(1 for x in results if x[2]), '/', len(results))


if __name__ == '__main__':
    main()
