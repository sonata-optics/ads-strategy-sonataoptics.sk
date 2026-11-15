#!/usr/bin/env python3
"""Cowork 04c: scan titles (Merchant snapshot 14.11) of rows proposed for plain waves for weapon-adjacent terms
that the label/heuristic flags may miss. Usage: python3 -I -B wave_title_scan.py <repo root>"""
import csv, json, glob, os, re, sys, collections as C
root = sys.argv[1]
D = os.path.join(root, 'data/catalog/2026-11-14')
T = {x['offerId']: x['title'] for f in sorted(glob.glob(D + '/merchant-*.json')) for x in json.load(open(f, encoding='utf-8'))}
P = list(csv.DictReader(open(os.path.join(root, 'discussions/round-04/04b_claude_code_attachments/full_catalog_coverage_plan.csv'), encoding='utf-8')))
RX = re.compile(r'(zbra[nň]|puš|pusk|weapon|rifle|picatinny|weaver|\bmont[aá]ž na zbra|zameriava|kolimátor|red ?dot|clip[- ]?on|lovec|lov |kolim|tlmi|úchyt na zbra|na zbra|kalib|nábo)', re.I)
hits = C.Counter(); rows = []
for p in P:
    if p['proposed_action'] not in ('ADD_IN_WAVE', 'ADD_IN_WAVE_DATA_REVIEW'): continue
    t = T.get(p['offer_id'], '')
    m = RX.search(t)
    if m:
        hits[(p['label0'], p['availability'])] += 1
        rows.append((p['offer_id'], p['availability'], p['label0'], p['wave'], m.group(0), t[:110]))
print('plain/data-wave rows with weapon-adjacent title terms:', len(rows))
for k, v in hits.most_common(): print('  ', k, v)
for r in rows: print(' | '.join(r))
print('titles missing for plan rows:', sum(1 for p in P if p['offer_id'] not in T))
