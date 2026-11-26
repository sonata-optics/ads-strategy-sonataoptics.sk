# python3 test_merge_schema_extra.py rollback_merge_holds.py - more damaged/valid state shapes (move 13), all with --write.
import json, subprocess, sys, tempfile
from pathlib import Path
script = sys.argv[1]; CTX = {'account_id': '999000111', 'content_language': 'sk', 'feed_label': 'SK', 'channel': 'ONLINE'}
REG = {'version': 3, 'context': CTX, 'generated_at': '2026-11-26T12:00:00Z', 'hold': [], 'review': [], 'ok': []}
POL = {'version': 3, 'context': CTX, 'generated_at': '2026-11-26T12:00:00Z', 'complete': True, 'products_read': 1200, 'hold': {}}
X = '999000111~ONLINE~sk~SK~X'
cases = [  # name, register, policy, sticky ('ABSENT' = no file), expected exit, expected holds added
 ('register JSON null', None, POL, 'ABSENT', 2, None), ('policy hold null', REG, dict(POL, hold=None), 'ABSENT', 2, None),
 ('policy hold missing', REG, {k: v for k, v in POL.items() if k != 'hold'}, 'ABSENT', 2, None),
 ('sticky v3 foreign context', REG, POL, dict(POL, context=dict(CTX, feed_label='CZ')), 2, None), ('sticky v3 hold as list', REG, POL, dict(POL, hold=[X]), 2, None),
 ('sticky unknown version 9', REG, POL, dict(POL, version=9), 2, None), ('sticky hold entry without codes', REG, POL, dict(POL, hold={X: []}), 2, None),
 ('register v3 without context', {k: v for k, v in REG.items() if k != 'context'}, POL, 'ABSENT', 2, None),
 ('valid: sticky absent, empty v3 policy', REG, POL, 'ABSENT', 0, 0), ('valid: v2 snapshot with documented empty []', REG, {'version': 2, 'generated_at': '2026-11-20T00:00:00Z', 'hold': []}, 'ABSENT', 0, 0),
 ('valid: sticky with one hold', REG, POL, dict(POL, hold={X: ['x_policy_violation']}), 0, 1)]
fail = 0
for name, reg, pol, sticky, exp_rc, exp_added in cases:
    with tempfile.TemporaryDirectory() as t:
        p = Path(t); (p / 'ads-review.json').write_text(json.dumps(reg)); (p / 'ads-policy.json').write_text(json.dumps(pol))
        if sticky != 'ABSENT': (p / 'ads-policy-holds.json').write_text(json.dumps(sticky))
        before = (p / 'ads-review.json').read_bytes()
        r = subprocess.run([sys.executable, script, '--dir', t, '--account', '999000111', '--lang', 'sk', '--feed', 'SK', '--write'], capture_output=True, text=True)
        changed = before != (p / 'ads-review.json').read_bytes()
        added = json.loads(r.stdout.strip().splitlines()[0]).get('added_from_snapshot_or_sticky') if r.returncode == 0 else None
        ok = r.returncode == exp_rc and (changed == (exp_rc == 0)) and added == exp_added
        fail += not ok
        print('PASS' if ok else 'FAIL', name, 'exit', r.returncode, 'written', changed, 'added', added)
print(f'{len(cases) - fail}/{len(cases)} PASS'); sys.exit(1 if fail else 0)
