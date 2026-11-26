#!/usr/bin/env python3
"""Rollback helper (round 5 move 11). Before ANY code rollback from AdsGate v3.2 to the old v2 code, fold every known hold
into the register's manual `hold` list, because v2 never reads ads-policy-holds.json (sticky) and drops policy holds once the
snapshot is older than 3 days. Manual holds are honoured by both v2 and v3.2 as long as the register is fresh (v2: <= 30 days).
Union = register.hold + snapshot.hold + sticky.hold (any version, any age) for the given Merchant identity. Nothing is removed.
Usage: python3 rollback_merge_holds.py --dir ~/merchant-private --account 5831333799 --lang sk --feed SK [--write]
Exit 2 (and no write) if any of the three files exists but cannot be parsed: then routes stay PAUSED and v3.2 is fixed instead.
--write: backup ads-review.json.<UTC>.pre-rollback.bak, tmp + rename, mode 0600; generated_at = now (fresh for v2's 30-day rule)."""
import argparse, datetime, json, os, shutil, sys

ap = argparse.ArgumentParser(); ap.add_argument('--dir', required=True); ap.add_argument('--account', required=True); ap.add_argument('--lang', required=True)
ap.add_argument('--feed', required=True); ap.add_argument('--write', action='store_true'); a = ap.parse_args()
prefix = f'{a.account}~ONLINE~{a.lang}~{a.feed}~'
paths = {k: os.path.join(a.dir, f) for k, f in (('reg', 'ads-review.json'), ('pol', 'ads-policy.json'), ('sticky', 'ads-policy-holds.json'))}
data = {}
for k, p in paths.items():
    if not os.path.exists(p):
        data[k] = None; continue
    try:
        data[k] = json.load(open(p, encoding='utf-8'))
    except Exception as e:  # unreadable state = unknown holds -> refuse
        print(json.dumps({'error': f'{k} unreadable: {e.__class__.__name__}', 'action': 'keep paid routes PAUSED, fix v3.2, do not roll back code'})); sys.exit(2)
reg = data['reg']
if not isinstance(reg, dict) or not isinstance(reg.get('hold'), list):
    print(json.dumps({'error': 'register missing or without hold list', 'action': 'keep paid routes PAUSED'})); sys.exit(2)
have = {(e.get('id') if isinstance(e, dict) else str(e)) for e in reg['hold']}
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
added = []
for src in ('pol', 'sticky'):
    d = data[src]
    if d is None:
        continue
    h = d.get('hold') if isinstance(d, dict) else None
    if not isinstance(h, dict):
        if h in ([], None) and isinstance(d, dict):
            continue
        print(json.dumps({'error': f'{src} hold is not a map', 'action': 'keep paid routes PAUSED'})); sys.exit(2)
    for pid, codes in h.items():
        if pid.startswith(prefix) and pid not in have:
            have.add(pid)
            added.append({'id': pid, 'reason': 'rollback merge of policy hold: ' + ','.join(map(str, codes if isinstance(codes, list) else [codes])),
                          'source': src + ' file at rollback', 'date': now.date().isoformat()})
out = dict(reg); out['hold'] = list(reg['hold']) + added; out['generated_at'] = now.isoformat().replace('+00:00', 'Z')
out['rollback_merge'] = {'at': out['generated_at'], 'added': len(added)}
print(json.dumps({'register_holds_before': len(reg['hold']), 'added_from_snapshot_or_sticky': len(added), 'register_holds_after': len(out['hold']), 'write': a.write}))
if a.write:
    bak = paths['reg'] + '.' + now.strftime('%Y%m%dT%H%M%SZ') + '.pre-rollback.bak'; shutil.copy2(paths['reg'], bak); os.chmod(bak, 0o600)
    tmp = paths['reg'] + '.tmp'; old = os.umask(0o077)
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        os.replace(tmp, paths['reg'])
    finally:
        os.umask(old)
