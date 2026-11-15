#!/usr/bin/env python3
"""Cowork re-check (04c) of Claude Code stock_sync_dryrun v2: plan() -> (actions, proposed), commit().
Reuses the module unchanged; builds its own fixtures. No network.
Usage: python3 -I -B stock_sync_counterexamples_v2.py <path to 02_claude_code_attachments>
"""
import os, sys, copy
sys.dont_write_bytecode = True
from datetime import datetime, timedelta
cc = os.path.abspath(sys.argv[1]); sys.path.insert(0, cc)
import stock_sync_dryrun as s

NOW = datetime(2026, 11, 15, 12, 0)
CFG = copy.deepcopy(s.DEFAULT_CFG)
K = lambda oid, fl='SK': f'5831333799~ONLINE~sk~{fl}~{oid}'
OTHERS = ['26113', '103640', '47420', '107817', '26130']        # padding so a single flip stays below the 30% guard

def ob(oid, status='ENABLED', owner=None, labels=None, conf=None, raw=None):
    return dict(object_id='AG_' + oid, identity=raw or K(oid), status=status, pause_owner=owner,
                labels=list(labels) if labels is not None else ([s.SYNC_LABEL] if owner == 'SYNC' else []),
                allowlisted=True, confirmations=list(conf or []))

def world(target):
    return [target] + [ob(x) for x in OTHERS]

def rd(read_id, fetched, av, upstream=None, extra=None):
    items = {K(x): dict(availability='IN_STOCK') for x in OTHERS}
    items[K('103933')] = dict(availability=av, **({'upstream_updated_at': upstream} if upstream else {}))
    r = dict(ok=True, read_id=read_id, fetched_at=fetched, items=items)
    r.update(extra or {})
    return r

def run(state, read, now, cfg=CFG, apply_ok=True):
    j = []
    acts, prop = s.plan(state, read, cfg, now, j, read.get('read_id') or 'run')
    new = s.commit(state, acts, prop, apply_ok)
    dec = [f"{x['decision']}:{x['reason']}" for x in j if x['object_id'] in ('AG_103933', '*')]
    return acts, prop, new, dec

def tgt(state):
    return next(o for o in state if o['object_id'] == 'AG_103933')

R = []
def check(cid, desc, ok, detail):
    R.append((cid, 'OK' if ok else 'PROBLEM', desc, detail))

# ---------- C1: replay / confirmation semantics ----------
st = world(ob('103933', 'PAUSED', 'SYNC'))
t1 = NOW - timedelta(hours=1)
a, p, st1, d1 = run(st, rd('R1', t1, 'IN_STOCK'), NOW)
a, p, st2, d2 = run(st1, rd('R1', t1, 'IN_STOCK'), NOW + timedelta(minutes=5))
check('C1a', 'same read_id replayed after commit adds no confirmation', not a and len(tgt(st2)['confirmations']) == 1, d2)
a, p, st3, d3 = run(st1, rd('R2', t1, 'IN_STOCK'), NOW + timedelta(minutes=5))
check('C1b', 'new read_id but same fetched_at (re-labelled replay) -> WAIT', not a and len(tgt(st3)['confirmations']) == 1, d3)
a, p, st4, d4 = run(st1, rd('R3', t1 + timedelta(minutes=10), 'IN_STOCK'), NOW + timedelta(minutes=10))
check('C1c', 'distinct read only 10 min newer -> WAIT (min interval 30)', not a, d4)
a, p, st5, d5 = run(st1, rd('R4', t1 + timedelta(minutes=40), 'IN_STOCK'), NOW + timedelta(minutes=40))
check('C1d', 'distinct read 40 min newer -> ENABLE', [x[1] for x in a] == ['ENABLE'] and tgt(st5)['status'] == 'ENABLED', d5)
a, p, st6, d6 = run(st1, rd('R4', t1 + timedelta(minutes=40), 'IN_STOCK'), NOW + timedelta(minutes=40), apply_ok=False)
check('C1e', 'ENABLE planned but apply failed -> stored state unchanged (still 1 confirmation, PAUSED)',
      tgt(st6) == tgt(st1), tgt(st6))
a, p, st7, d7 = run(st1, rd('R0', t1 - timedelta(minutes=50), 'IN_STOCK'), NOW + timedelta(minutes=40))
check('C1f', 'older read arriving late -> WAIT', not a, d7)
# OOS between confirmations resets the counter
a, p, st8, _ = run(st1, rd('R5', t1 + timedelta(minutes=35), 'OUT_OF_STOCK'), NOW + timedelta(minutes=35))
a, p, st9, d9 = run(st8, rd('R6', t1 + timedelta(minutes=70), 'IN_STOCK'), NOW + timedelta(minutes=70))
check('C1g', 'OOS between two IN_STOCK reads resets confirmations -> WAIT', not a and len(tgt(st9)['confirmations']) == 1, d9)

# ---------- C2: identity formats ----------
a, p, _, d = run(world(ob('103933', raw='customers/1234567890/shoppingProducts/' + K('103933'))), rd('R1', t1, 'OUT_OF_STOCK'), NOW)
check('C2a', 'full resource_name parsed -> PAUSE', [x[1] for x in a] == ['PAUSE'], d)
a, p, _, d = run(world(ob('103933', raw='103933')), rd('R1', t1, 'OUT_OF_STOCK'), NOW)
check('C2b', 'bare offer_id -> ALERT, no action', not a and any(x.startswith('ALERT') for x in d), d)
a, p, _, d = run(world(ob('103933', raw='customers/1/shoppingProducts/5831333799~ONLINE~sk~SK-2~103933')), rd('R1', t1, 'OUT_OF_STOCK'), NOW)
check('C2c', 'feed label with hyphen (allowed by Merchant Center) -> ALERT (fail-safe, but would block a real label)', not a and any(x.startswith('ALERT') for x in d), d)
a, p, _, d = run(world(ob('103933', raw='customers/999/shoppingProducts/' + K('103933'))), rd('R1', t1, 'OUT_OF_STOCK'), NOW)
check('C2d', 'resource_name of ANOTHER Google Ads customer id is accepted (customer id not validated)', not a, d)

# ---------- C3 / C4: sync-hold ----------
a, p, _, d = run(world(ob('103933', 'PAUSED', 'SYNC', labels=[s.SYNC_LABEL, s.HOLD_LABEL], conf=[dict(read_id='R0', observed_at=NOW - timedelta(hours=3))])), rd('R1', t1, 'IN_STOCK'), NOW)
check('C3', 'sync-hold on sync-paused group blocks ENABLE', not a, d)
a, p, _, d = run(world(ob('103933', 'ENABLED', 'MANUAL', labels=[s.HOLD_LABEL])), rd('R1', t1, 'OUT_OF_STOCK'), NOW)
check('C4a', 'sync-hold on enabled OOS group blocks PAUSE', not a, d)
a, p, _, d = run(world(ob('103933', 'ENABLED', 'MANUAL')), rd('R1', t1, 'OUT_OF_STOCK'), NOW)
check('C4b', 'manual enable without hold -> PAUSE (documented rule)', [x[1] for x in a] == ['PAUSE'], d)
# stale confirmation survives a hold period
old = [dict(read_id='R0', observed_at=NOW - timedelta(days=5))]
a, p, _, d = run(world(ob('103933', 'PAUSED', 'SYNC', conf=old)), rd('R9', t1, 'IN_STOCK'), NOW)
check('C3x', '5-day-old confirmation (e.g. kept through a sync-hold) + ONE fresh read -> ENABLE', not a, d)

# ---------- U: unknown owner ----------
a, p, _, d = run(world(ob('103933', 'PAUSED', None, labels=[])), rd('R1', t1, 'IN_STOCK'), NOW)
check('U1', 'PAUSED with unknown owner never enabled', not a, d)
a, p, _, d = run(world(ob('103933', 'PAUSED', 'SYNC', labels=[], conf=old)), rd('R1', t1, 'IN_STOCK'), NOW)
check('U2', 'owner SYNC without label -> no enable', not a, d)

# ---------- F: freshness ----------
a, p, _, d = run(world(ob('103933')), rd('R1', NOW + timedelta(hours=1), 'OUT_OF_STOCK'), NOW)
check('F1', 'fetch time in the future -> ALERT', not a and any(x.startswith('ALERT') for x in d), d)
a, p, _, d = run(world(ob('103933')), rd('', t1, 'OUT_OF_STOCK'), NOW)
check('F2', 'no read_id -> ALERT', not a and any(x.startswith('ALERT') for x in d), d)
a, p, _, d = run(world(ob('103933')), rd('R1', t1, 'OUT_OF_STOCK', upstream=NOW - timedelta(hours=10)), NOW)
check('F3', 'stale upstream with fresh fetch -> no action', not a, d)
a, p, _, d = run(world(ob('103933')), rd('R1', t1, 'OUT_OF_STOCK', upstream=NOW + timedelta(hours=2)), NOW)
check('F4', 'upstream time in the future -> ALERT', not a and any(x.startswith('ALERT') for x in d), d)
j = []; s.plan(world(ob('103933')), rd('R1', t1, 'OUT_OF_STOCK'), CFG, NOW, j, 'r')
check('F5', 'journal records freshness_basis', any(x.get('freshness_basis') == 'fetch_time' for x in j), [x['freshness_basis'] for x in j if x['object_id'] == 'AG_103933'])

# ---------- M: HALT / apply error ----------
mass = [ob('103933'), ob('26113'), ob('103640'), ob('47420')]
r = dict(ok=True, read_id='R1', fetched_at=t1, items={K(x): dict(availability='OUT_OF_STOCK') for x in ('103933', '26113')} | {K(x): dict(availability='IN_STOCK') for x in ('103640', '47420')})
j = []; a, p = s.plan(mass, r, CFG, NOW, j, 'r')
check('M1', 'mass flip -> HALT, nothing proposed', a == [] and p == {} and any(x['decision'] == 'HALT' for x in j), [x['decision'] for x in j if x['object_id'] == '*'])
before = copy.deepcopy(mass)
a, p = s.plan(mass, rd('R1', t1, 'OUT_OF_STOCK'), CFG, NOW, [], 'r')
check('M3', 'plan() does not mutate its input', mass == before, '')

bad = [x for x in R if x[1] == 'PROBLEM']
for cid, st_, desc, det in R:
    print(f'{st_:8}{cid:5} {desc} | {det}')
print(f'\n{len(R)} checks, {len(bad)} PROBLEM')
