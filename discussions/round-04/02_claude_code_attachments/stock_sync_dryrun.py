#!/usr/bin/env python3
"""Local dry-run model of the stock sync (R3-CLAUDE-06 / R3-CHATGPT-10). No network, no API calls.

The planner is a pure function: (managed objects, Merchant availability read, config, now) -> actions + journal.
It never calls Google Ads. Tests below exercise the rules of stock_sync_spec.md and write
stock_sync_dryrun_log.csv (journal of every scenario) and print PASS/FAIL per scenario.
Managed objects = model Search ad groups only. Shopping product groups are never paused by sync:
Merchant availability already makes an OOS offer NOT_ELIGIBLE and the feed must stay truthful.
"""
import csv, hashlib, json, os, sys, copy
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
SYNC_LABEL = 'paused-by-sync'
DEFAULT_CFG = dict(kill_switch=False, max_age_hours=6, max_flip_share=0.30, min_flips_for_guard=2, enable_confirmations=2,
                   allowed_identity=dict(merchant_id='5831333799', channel='ONLINE', language='sk', feed_label='SK'))


def identity(resource):
    """'5831333799~ONLINE~sk~SK~103645' -> dict. Composite key; offer_id alone is NOT an identity."""
    m, ch, lang, fl, oid = resource.split('~')
    return dict(merchant_id=m, channel=ch, language=lang, feed_label=fl, offer_id=oid)


def key(idt):
    return '~'.join(idt[k] for k in ('merchant_id', 'channel', 'language', 'feed_label', 'offer_id'))


def plan(objects, read, cfg, now, journal, run_id):
    """objects: list of dict(object_id, identity, status, pause_owner, allowlisted, in_stock_streak)
    read: dict(ok, fetched_at, items: {identity_key: availability}) ; returns list of actions (dry-run)."""
    def log(obj, decision, reason, action=None):
        journal.append(dict(run_id=run_id, ts=now.isoformat(), object_id=obj and obj['object_id'] or '*',
                            identity=obj and obj['identity'] or '*', decision=decision, reason=reason, action=action or ''))
    if cfg['kill_switch']:
        log(None, 'NO_OP', 'kill switch ON'); return []
    if not read.get('ok'):
        log(None, 'NO_OP', 'API error: ' + read.get('error', 'unknown')); return []
    if not read.get('items'):
        log(None, 'NO_OP', 'empty response is not evidence of OOS'); return []
    age = now - read['fetched_at']
    if age > timedelta(hours=cfg['max_age_hours']):
        log(None, 'NO_OP', f'stale read {age}'); return []
    actions = []
    allow = cfg['allowed_identity']
    for o in objects:
        idt = identity(o['identity'])
        if not o['allowlisted']:
            log(o, 'SKIP', 'not in allowlist'); continue
        if any(idt[k] != v for k, v in allow.items()):
            log(o, 'SKIP', 'identity outside SK destination/merchant'); continue
        av = read['items'].get(key(idt))
        if av is None:
            log(o, 'ALERT', 'item missing from read: not treated as OOS'); continue
        if av not in ('IN_STOCK', 'OUT_OF_STOCK', 'PREORDER', 'BACKORDER'):
            log(o, 'ALERT', f'unknown availability {av}'); continue
        if av == 'OUT_OF_STOCK':
            o['in_stock_streak'] = 0
            if o['status'] == 'ENABLED':
                actions.append((o['object_id'], 'PAUSE', SYNC_LABEL)); log(o, 'PAUSE', 'OOS and enabled', f'PAUSE+label {SYNC_LABEL}')
            else:
                log(o, 'NO_OP', f'OOS, already paused (owner={o["pause_owner"]})')
            continue
        # IN_STOCK / PREORDER / BACKORDER treated as sellable only for IN_STOCK; others need owner rule
        if av != 'IN_STOCK':
            log(o, 'NO_OP', f'{av}: no automatic enable (owner rule required)'); continue
        if o['status'] == 'ENABLED':
            if o['pause_owner'] == 'SYNC':
                log(o, 'CLEANUP', 'enabled manually while labelled; remove stale label', 'remove label only')
                actions.append((o['object_id'], 'REMOVE_LABEL', SYNC_LABEL))
            else:
                log(o, 'NO_OP', 'in stock and enabled')
            continue
        if o['pause_owner'] != 'SYNC':
            log(o, 'NO_OP', f'paused by {o["pause_owner"]}: sync never enables it'); continue
        o['in_stock_streak'] = o.get('in_stock_streak', 0) + 1
        if o['in_stock_streak'] < cfg['enable_confirmations']:
            log(o, 'WAIT', f'in-stock confirmation {o["in_stock_streak"]}/{cfg["enable_confirmations"]}'); continue
        actions.append((o['object_id'], 'ENABLE', SYNC_LABEL)); log(o, 'ENABLE', 'in stock, paused by sync, confirmed', 'ENABLE+remove label')
    flips = [a for a in actions if a[1] in ('PAUSE', 'ENABLE')]
    n_allow = sum(1 for o in objects if o['allowlisted']) or 1
    if len(flips) >= cfg['min_flips_for_guard'] and len(flips) / n_allow > cfg['max_flip_share']:
        log(None, 'HALT', f'{len(flips)}/{n_allow} objects would flip > {cfg["max_flip_share"]:.0%}: manual confirmation required')
        return []
    return actions


def apply_simulated(objects, actions):
    """Simulated state change used to test idempotency (never an API call)."""
    by = {o['object_id']: o for o in objects}
    for oid, act, _ in actions:
        if act == 'PAUSE':
            by[oid]['status'], by[oid]['pause_owner'] = 'PAUSED', 'SYNC'
        elif act == 'ENABLE':
            by[oid]['status'], by[oid]['pause_owner'], by[oid]['in_stock_streak'] = 'ENABLED', None, 0
        elif act == 'REMOVE_LABEL':
            by[oid]['pause_owner'] = None


def obj(oid, offer, status='ENABLED', owner=None, allow=True, fl='SK'):
    return dict(object_id=oid, identity=f'5831333799~ONLINE~sk~{fl}~{offer}', status=status, pause_owner=owner,
                allowlisted=allow, in_stock_streak=0)


def rd(now, items, ok=True, age_h=1, err=''):
    return dict(ok=ok, fetched_at=now - timedelta(hours=age_h), error=err,
                items={f'5831333799~ONLINE~sk~SK~{k}': v for k, v in items.items()})


def scenarios():
    now = datetime(2026, 11, 15, 12, 0)
    cfg = copy.deepcopy(DEFAULT_CFG)
    S = []
    base = lambda: [obj('AG_103933', '103933'), obj('AG_26113', '26113'), obj('AG_103640', '103640'), obj('AG_47420', '47420')]
    S.append(('S01', 'OOS enabled group is paused and labelled', base(), rd(now, {'103933': 'OUT_OF_STOCK', '26113': 'IN_STOCK', '103640': 'IN_STOCK', '47420': 'IN_STOCK'}), cfg,
              [('AG_103933', 'PAUSE')]))
    S.append(('S02', 'API error -> no action', base(), rd(now, {}, ok=False, err='500'), cfg, []))
    S.append(('S03', 'empty response is not OOS', base(), rd(now, {}), cfg, []))
    S.append(('S04', 'stale read (8 h) -> no action', base(), rd(now, {'103933': 'OUT_OF_STOCK'}, age_h=8), cfg, []))
    k = copy.deepcopy(cfg); k['kill_switch'] = True
    S.append(('S05', 'kill switch -> no action', base(), rd(now, {'103933': 'OUT_OF_STOCK'}), k, []))
    S.append(('S06', 'manual pause is never auto-enabled', [obj('AG_103933', '103933', 'PAUSED', 'MANUAL')], rd(now, {'103933': 'IN_STOCK'}), cfg, []))
    S.append(('S07', 'new group created PAUSED for review is never labelled or enabled', [obj('AG_26130', '26130', 'PAUSED', 'REVIEW')], rd(now, {'26130': 'IN_STOCK'}), cfg, []))
    S.append(('S08', 'sync-paused group needs 2 consecutive IN_STOCK reads (first run waits)', [obj('AG_47420', '47420', 'PAUSED', 'SYNC')], rd(now, {'47420': 'IN_STOCK'}), cfg, []))
    S.append(('S09', 'item missing from read -> alert, not OOS', base(), rd(now, {'26113': 'IN_STOCK', '103640': 'IN_STOCK', '47420': 'IN_STOCK'}), cfg, []))
    S.append(('S10', 'identity outside SK (feed_label AT) ignored even if offer_id equal', [obj('AG_X', '103933', fl='AT')], rd(now, {'103933': 'OUT_OF_STOCK'}), cfg, []))
    S.append(('S11', 'non-allowlisted object untouched', [obj('AG_OLD', '103933', allow=False)], rd(now, {'103933': 'OUT_OF_STOCK'}), cfg, []))
    S.append(('S12', 'mass flip >30% halts the run', base(), rd(now, {'103933': 'OUT_OF_STOCK', '26113': 'OUT_OF_STOCK', '103640': 'IN_STOCK', '47420': 'IN_STOCK'}), cfg, []))
    S.append(('S13', 'manually enabled while labelled -> only remove stale label', [obj('AG_103640', '103640', 'ENABLED', 'SYNC')], rd(now, {'103640': 'IN_STOCK'}), cfg, [('AG_103640', 'REMOVE_LABEL')]))
    S.append(('S14', 'PREORDER/BACKORDER never auto-enable', [obj('AG_47420', '47420', 'PAUSED', 'SYNC')], rd(now, {'47420': 'BACKORDER'}), cfg, []))
    return now, S


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    now, S = scenarios()
    journal, results = [], []
    for sid, desc, objs, read, cfg, expected in S:
        acts = plan(objs, read, cfg, now, journal, sid)
        got = [(a[0], a[1]) for a in acts]
        results.append((sid, desc, got == expected, got, expected))
    # S15 idempotency: apply S01 actions in simulation, rerun same read -> 0 actions
    objs = [obj('AG_103933', '103933'), obj('AG_26113', '26113'), obj('AG_103640', '103640'), obj('AG_47420', '47420')]
    r = rd(now, {'103933': 'OUT_OF_STOCK', '26113': 'IN_STOCK', '103640': 'IN_STOCK', '47420': 'IN_STOCK'})
    a1 = plan(objs, r, DEFAULT_CFG, now, journal, 'S15a'); apply_simulated(objs, a1)
    a2 = plan(objs, r, DEFAULT_CFG, now, journal, 'S15b')
    results.append(('S15', 'idempotent: same input twice -> second run 0 actions', len(a1) == 1 and a2 == [], a2, []))
    # S16 two consecutive in-stock reads re-enable a sync-paused group
    objs = [obj('AG_47420', '47420', 'PAUSED', 'SYNC')]
    r = rd(now, {'47420': 'IN_STOCK'})
    b1 = plan(objs, r, DEFAULT_CFG, now, journal, 'S16a')
    b2 = plan(objs, rd(now + timedelta(hours=1), {'47420': 'IN_STOCK'}), DEFAULT_CFG, now + timedelta(hours=1), journal, 'S16b')
    results.append(('S16', 'second confirmed IN_STOCK read enables sync-paused group', b1 == [] and [(x[0], x[1]) for x in b2] == [('AG_47420', 'ENABLE')], b2, [('AG_47420', 'ENABLE')]))
    with open(os.path.join(HERE, 'stock_sync_dryrun_log.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(journal[0].keys())); w.writeheader(); w.writerows(journal)
    with open(os.path.join(HERE, 'stock_sync_dryrun_results.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['scenario', 'description', 'result', 'actions', 'expected'])
        for sid, desc, ok, got, exp in results:
            w.writerow([sid, desc, 'PASS' if ok else 'FAIL', json.dumps(got), json.dumps(exp)])
    for sid, desc, ok, got, exp in results:
        print(sid, 'PASS' if ok else 'FAIL', desc)
    print('scenarios', sum(1 for x in results if x[2]), '/', len(results))


if __name__ == '__main__':
    main()
