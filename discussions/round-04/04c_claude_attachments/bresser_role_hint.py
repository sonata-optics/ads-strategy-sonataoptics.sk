#!/usr/bin/env python3
"""Cowork 04c: rough, title-keyword role HINTS for bresser.de rows (HOLD_ROLE_UNRESOLVED). Hints only, not a decision.
Usage: python3 -I -B bresser_role_hint.py <repo root>"""
import csv, json, glob, os, re, sys, collections as C
root = sys.argv[1]
D = os.path.join(root, 'data/catalog/2026-11-14')
T = {x['offerId']: x['title'] for f in sorted(glob.glob(D + '/merchant-*.json')) for x in json.load(open(f, encoding='utf-8'))}
P = list(csv.DictReader(open(os.path.join(root, 'discussions/round-04/04b_claude_code_attachments/full_catalog_coverage_plan.csv'), encoding='utf-8')))
RULES = [('astronomické príslušenstvo (hint)', r'okulár|slnečn|filter|adaptér|t-adapt|hľadáč|polárn|protizáv|reduktor|redukčn|barlow|diagonál|zenit|focus|ostren|kolim|montá[žz]n[ae] (dosk|lišt)|rosn|deflek|kamera|autoguid'),
         ('montáže a statívy (hint)', r'^montáž|statív|stĺp|vidlic|eq-?\d|azimut|držiak|blokovac|pár '),
         ('pozorovacie ďalekohľady - spektívy (hint)', r'spektív'),
         ('ďalekohľady / monokuláre (hint)', r'monokul|ďalekohľad|binokul'),
         ('mikroskopy / lupy (hint)', r'mikrosk|lup[ay]'),
         ('teleskopy (hint)', r'teleskop|refraktor|reflektor|newton|dobson|maksutov')]
c = C.Counter(); out = []
for p in P:
    if p['label0'] != 'bresser.de' or p['availability'] != 'IN_STOCK': continue
    t = T.get(p['offer_id'], '')
    role = next((r for r, rx in RULES if re.search(rx, t, re.I)), 'unclear -> owner')
    c[role] += 1; out.append((p['offer_id'], role, t))
for k, v in c.most_common(): print(f'{v:4}  {k}')
print('total', sum(c.values()))
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bresser_role_hint.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['offer_id', 'role_hint', 'title_14_11']); w.writerows(out)
