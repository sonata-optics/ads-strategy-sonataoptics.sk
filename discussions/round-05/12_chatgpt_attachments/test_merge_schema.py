import json, subprocess, sys, tempfile
from pathlib import Path

script = sys.argv[1]
failed = 0
for damaged in ({}, {'version': 3, 'hold': None}, None):
    with tempfile.TemporaryDirectory() as temp:
        p = Path(temp)
        reg = {'version': 3, 'generated_at': '2026-11-26T12:00:00Z', 'hold': [], 'review': [], 'ok': []}
        (p / 'ads-review.json').write_text(json.dumps(reg))
        (p / 'ads-policy.json').write_text(json.dumps({'version': 3, 'hold': {}}))
        (p / 'ads-policy-holds.json').write_text(json.dumps(damaged))
        before = (p / 'ads-review.json').read_bytes()
        r = subprocess.run([sys.executable, script, '--dir', temp, '--account', '999000111', '--lang', 'sk', '--feed', 'SK', '--write'], capture_output=True, text=True)
        unchanged = before == (p / 'ads-review.json').read_bytes()
        ok = r.returncode == 2 and unchanged
        failed += not ok
        print(('PASS' if ok else 'FAIL'), 'sticky=', damaged, 'exit=', r.returncode, 'unchanged=', unchanged, 'expected exit=2 unchanged=True')
print(f'{3-failed}/3 PASS')
sys.exit(bool(failed))
