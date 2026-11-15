#!/usr/bin/env python3
"""Cowork counterexamples for Claude Code stock_sync_dryrun.plan (round 4). Reuses plan() unchanged.
Usage: python3 -I stock_sync_counterexamples.py <path to 02_claude_code_attachments>
"""
import os, sys, copy
sys.dont_write_bytecode = True
from datetime import datetime, timedelta, timezone
cc = os.path.abspath(sys.argv[1]); sys.path.insert(0, cc); os.chdir(cc)
import stock_sync_dryrun as s
now = datetime(2026, 11, 15, 12, 0)
cfg = dict(kill_switch=False, max_age_hours=6, enable_confirmations=2, max_flip_share=0.30, min_flips_for_guard=2,
           allowed_identity=dict(merchant_id='5831333799', channel='ONLINE', language='sk', feed_label='SK'))
idt = lambda oid: f'5831333799~ONLINE~sk~SK~{oid}'
def obj(oid, status, owner, streak=0):
    return dict(object_id='AG_' + oid, identity=idt(oid), status=status,
                pause_owner=owner, allowlisted=True, in_stock_streak=streak)
def read(items, fetched):
    return dict(ok=True, fetched_at=fetched, items={idt(k): v for k, v in items.items()})
res = []
# C1: the SAME read (same fetched_at) processed twice must not count as two confirmations
objs = [obj('103933', 'PAUSED', 'SYNC'), obj('26113', 'ENABLED', None), obj('103640', 'ENABLED', None), obj('47420', 'ENABLED', None)]
r = read({'103933': 'IN_STOCK', '26113': 'IN_STOCK', '103640': 'IN_STOCK', '47420': 'IN_STOCK'}, now - timedelta(hours=1))
j = []
a1 = s.plan(objs, r, cfg, now, j, 'run1'); a2 = s.plan(objs, r, cfg, now + timedelta(minutes=5), j, 'run2')
print([x['decision']+':'+x['reason'] for x in j if x['object_id']=='AG_103933'])
res.append(('C1 same read twice -> 2nd run enables (should WAIT for a NEW read)', a1, a2, bool(a2)))
# C2: integration input in raw shopping_product.resource_name format -> every object silently skipped
o2 = [dict(obj('103933', 'ENABLED', None), identity='customers/1/shoppingProducts/' + idt('103933'))]
j2 = []
a = s.plan(o2, read({'103933': 'OUT_OF_STOCK'}, now - timedelta(hours=1)), cfg, now, j2, 'r')
skipped = any(x['decision'] == 'SKIP' for x in j2)
res.append(('C2 raw resource_name (customers/.../shoppingProducts/...) is SKIPPED, OOS group stays enabled; fail-safe but silent — needs explicit parse + alert', a, [x['reason'] for x in j2], skipped))
# C3: human deliberately keeps a SYNC-paused group paused (no status change => owner stays SYNC)
objs = [obj('103933', 'PAUSED', 'SYNC', streak=1), obj('26113', 'ENABLED', None), obj('103640', 'ENABLED', None), obj('47420', 'ENABLED', None)]
a = s.plan(objs, read({'103933': 'IN_STOCK', '26113': 'IN_STOCK', '103640': 'IN_STOCK', '47420': 'IN_STOCK'}, now - timedelta(hours=1)), cfg, now, [], 'r')
res.append(('C3 manual HOLD on a sync-paused group is not representable; sync enables it', a, '', bool(a)))
# C4: human enables an OOS group on purpose (e.g. preorder text) -> sync pauses it every run
objs = [obj('103933', 'ENABLED', 'MANUAL'), obj('26113', 'ENABLED', None), obj('103640', 'ENABLED', None), obj('47420', 'ENABLED', None)]
a = s.plan(objs, read({'103933': 'OUT_OF_STOCK', '26113': 'IN_STOCK', '103640': 'IN_STOCK', '47420': 'IN_STOCK'}, now - timedelta(hours=1)), cfg, now, [], 'r')
res.append(('C4 manual override to keep OOS group enabled is not representable; sync pauses it', a, '', bool(a)))
for name, x, y, problem in res:
    print(('PROBLEM ' if problem else 'OK      ') + name, '|', x, '|', y)
