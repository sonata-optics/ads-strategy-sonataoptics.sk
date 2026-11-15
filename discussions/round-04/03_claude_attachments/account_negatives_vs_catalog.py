#!/usr/bin/env python3
"""Which account-level negatives share a token (literal, lower-case) with Merchant titles (snapshot 14.11)?
A hit is NOT proof of harm: it lists negatives that can block queries naming real catalog products.
Usage: python3 -I account_negatives_vs_catalog.py <repo_root> <out.csv>
"""
import csv, glob, json, os, re, sys, collections
root = sys.argv[1]
live = json.load(open(os.path.join(root, 'discussions/round-03/05_chatgpt_attachments/live_checks_2026-11-15.json'), encoding='utf-8'))
neg = [(n['matchType'], n['text']) for n in live['account_negative_keywords']]
merchant = [m for f in sorted(glob.glob(os.path.join(root, 'data/catalog/2026-11-14/merchant-*.json'))) for m in json.load(open(f, encoding='utf-8'))]
tok = lambda s: re.findall(r'[\w×]+', s.lower())
title_tokens = [(m['offerId'], m['availability'], set(tok(m['title'])), m['title']) for m in merchant]
rows = []
for mt, t in neg:
    tt = tok(t)
    if not tt: continue
    hit = [(o, a, ti) for o, a, ts, ti in title_tokens if all(x in ts for x in tt)]
    if hit:
        rows.append(dict(match_type=mt, negative=t, merchant_titles_with_all_tokens=len(hit),
                         in_stock=sum(a == 'IN_STOCK' for _, a, _ in hit), examples=' || '.join(ti[:70] for _, _, ti in hit[:3])))
rows.sort(key=lambda r: -r['in_stock'])
with open(sys.argv[2], 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['match_type', 'negative', 'merchant_titles_with_all_tokens', 'in_stock', 'examples']); w.writeheader(); w.writerows(rows)
for r in rows: print(r['match_type'], r['negative'], r['merchant_titles_with_all_tokens'], r['in_stock'], '|', r['examples'][:120])
