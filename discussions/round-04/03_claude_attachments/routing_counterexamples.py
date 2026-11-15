#!/usr/bin/env python3
"""Cowork counterexamples for Claude Code routing engine (round 4).
Reuses routing_tests.py (load/hits/search_route/lit/cv) unchanged. Read-only, no network.
Usage: python3 -I routing_counterexamples.py <path to 02_claude_code_attachments> <out.csv>
"""
import csv, os, sys
sys.dont_write_bytecode = True
cc = os.path.abspath(sys.argv[1]); sys.path.insert(0, cc); os.chdir(cc)
import routing_tests as rt
acc, camp, groups, search_camp_neg = rt.load()
# (id, query, why it matters, should Shopping reach auction?, expected Search route or NONE)
C = [
 ('C01', 'poradiť leica trinovid 10x42 hd', 'advice intent = pre-purchase', True, 'AG_103933_Leica_Trinovid_10x42_HD'),
 ('C02', 'ake leica trinovid 10x42 hd', '"ake" (aký without diacritics) also in account list; diff covers only aký', True, 'AG_103933_Leica_Trinovid_10x42_HD'),
 ('C03', 'leica trinovid 10x42 hd nie drahé', 'price-sensitive commercial', True, 'AG_103933_Leica_Trinovid_10x42_HD'),
 ('C04', 'správny ďalekohľad leica trinovid 10x42', 'selection intent ("Správny")', True, 'AG_103933_Leica_Trinovid_10x42_HD'),
 ('C05', 'levenhuk vegas ed 10x42 popis', 'spec/description lookup on product', True, 'AG_26113_Levenhuk_Vegas_ED_10x42'),
 ('C06', 'typy ďalekohľadov leica trinovid', 'research', True, 'NONE'),
 ('C07', 'termovízne drony autel', 'catalog has 5 IN_STOCK Autel drones; account BROAD "drony"', True, 'NONE'),
 ('C08', 'dalekohlad s fotoaparatom', 'catalog has Levenhuk Atom DNB300 digital binocular; account PHRASE', True, 'NONE'),
 ('C09', 'ďalekohľad s fotoaparátom', 'same query with diacritics: literal not blocked (inconsistency)', True, 'NONE'),
 ('C10', 'čo je leica trinovid 10x42 hd', '"Čo" — informational; block acceptable', False, 'NONE'),
 ('C11', 'leica trinovid 10x42 hd recenzia', 'review intent is not in account list', True, 'AG_103933_Leica_Trinovid_10x42_HD'),
 ('C12', 'leica trinovid 10x42 hd vs 8x42', 'comparison: 8x42 phrase negative blocks Search; Shopping ok', True, 'NONE'),
 ('C13', 'nájsť leica trinovid 10x42 hd', '"Nájsť" (find)', True, 'AG_103933_Leica_Trinovid_10x42_HD'),
 ('C14', 'trinowid 10x42', 'typo: literal none, CV maybe', True, 'NONE'),
]
rows = []
for cid, q, why, shop_exp, s_exp in C:
    a_lit, a_cv = rt.hits(q, acc), rt.hits(q, acc, rt.cv)
    s_lit, blk = rt.search_route(q, groups, rt.lit)
    s_final = 'NONE' if (a_lit or rt.hits(q, search_camp_neg)) else s_lit
    shop = 'BLOCKED' if (a_lit or rt.hits(q, rt.PILOT_SHOP_CAMPAIGN_NEG)) else 'REACHES_AUCTION'
    ok = (shop == 'REACHES_AUCTION') == shop_exp and s_final == s_exp
    rows.append(dict(id=cid, query=q, why=why, account_neg_literal=';'.join(a_lit), account_neg_if_cv=';'.join(a_cv),
                     search_literal=s_final, shopping=shop, expected_shopping_reach=shop_exp, expected_search=s_exp,
                     verdict='PASS' if ok else 'FAIL'))
with open(sys.argv[2], 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
for r in rows: print(r['id'], r['verdict'], r['account_neg_literal'] or '-', '|', r['account_neg_if_cv'] or '-', '|', r['search_literal'], r['shopping'])
