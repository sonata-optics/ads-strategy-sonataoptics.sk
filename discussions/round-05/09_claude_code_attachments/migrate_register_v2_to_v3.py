#!/usr/bin/env python3
"""One-time migration of ~/merchant-private/ads-review.json (register v2 -> v3) for AdsGate v3.2. Dry run by default.
Usage: python3 migrate_register_v2_to_v3.py /path/ads-review.json --account 5831333799 --lang sk --feed SK [--write]
- keeps hold / review / ok lists byte-for-byte (only entries of this Merchant identity are counted; others are reported);
- adds version 3, context {account_id, content_language, feed_label, channel ONLINE}, migrated_from, generated_at (now);
- refuses: not v2, already has context, missing/ non-list hold|review|ok, or ok entries lacking author/reason/evidence/date/fingerprint
  (v3.2 would treat them as invalid anyway; the script prints them so the owner can re-confirm instead of silently keeping them);
- --write: backup <file>.v2.<UTC>.bak, tmp + rename, mode 0600. Prints a summary; never prints credentials (the file has none)."""
import argparse, datetime, json, os, shutil, sys

ap = argparse.ArgumentParser(); ap.add_argument('file'); ap.add_argument('--account', required=True); ap.add_argument('--lang', required=True)
ap.add_argument('--feed', required=True); ap.add_argument('--write', action='store_true'); a = ap.parse_args()
d = json.load(open(a.file, encoding='utf-8'))
if d.get('version') != 2 or 'context' in d:
    sys.exit('refuse: expected an unbound version-2 register')
for k in ('hold', 'review', 'ok'):
    if not isinstance(d.get(k), list):
        sys.exit(f'refuse: {k} missing or not a list')
prefix = f'{a.account}~ONLINE~{a.lang}~{a.feed}~'
ident = lambda e: e.get('id', '') if isinstance(e, dict) else str(e)
foreign = {k: [ident(e) for e in d[k] if not ident(e).startswith(prefix)] for k in ('hold', 'review', 'ok')}
bad_ok = [ident(e) for e in d['ok'] if not isinstance(e, dict) or any(not str(e.get(f, '')).strip() for f in ('id', 'fingerprint', 'author', 'reason', 'evidence', 'date'))]
if bad_ok:
    sys.exit(f'refuse: incomplete manual ok entries (re-confirm them first): {bad_ok}')
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
out = dict(d); out.update({'version': 3, 'rules': 'ads-gate-v3.2', 'generated_at': now.isoformat().replace('+00:00', 'Z'), 'migrated_from': {'version': 2, 'generated_at': d.get('generated_at')},
                           'context': {'account_id': a.account, 'content_language': a.lang, 'feed_label': a.feed, 'channel': 'ONLINE'}})
print(json.dumps({'hold': len(d['hold']), 'review': len(d['review']), 'ok': len(d['ok']), 'foreign_ids_ignored_by_gate': {k: len(v) for k, v in foreign.items()}, 'write': a.write}))
if a.write:
    bak = f"{a.file}.v2.{now.strftime('%Y%m%dT%H%M%SZ')}.bak"; shutil.copy2(a.file, bak); os.chmod(bak, 0o600)
    tmp = a.file + '.tmp'; old = os.umask(0o077)
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        os.replace(tmp, a.file)
    finally:
        os.umask(old)
    print('written; backup', os.path.basename(bak))
