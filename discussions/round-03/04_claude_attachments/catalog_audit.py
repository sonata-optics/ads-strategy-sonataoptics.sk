#!/usr/bin/env python3
"""Reproducible catalog audit, round 2 (Claude Cowork).
Inputs (repo paths, read-only):
  data/catalog/2026-11-14/assortment-*.json, merchant-*.json, scope-candidates.json
  discussions/round-01/04_claude_attachments/merchant_risk_skus.csv
  discussions/round-01/04_claude_attachments/site_weapon_optic_role_candidates.csv
Usage: python3 catalog_audit.py <repo_root> <out_dir>
Every URL gets exactly one primary_bucket. Heuristic weapon-optic candidates are
flags for manual review, NOT confirmed policy violations.
"""
import csv, glob, json, os, sys, collections
root, out = sys.argv[1], sys.argv[2]
D = os.path.join(root, 'data/catalog/2026-11-14')
A1 = os.path.join(root, 'discussions/round-01/04_claude_attachments')
assort = [x for f in sorted(glob.glob(D + '/assortment-*.json')) for x in json.load(open(f))]
merchant = [x for f in sorted(glob.glob(D + '/merchant-*.json')) for x in json.load(open(f))]
scope = {p['url'] for p in json.load(open(D + '/scope-candidates.json'))['products']}
risk = {r['offer_id']: r for r in csv.DictReader(open(A1 + '/merchant_risk_skus.csv'))}
policy_ids = {k for k, r in risk.items() if r['risk_level'] in ('high', 'medium')}
false_ids = {k for k, r in risk.items() if r['risk_level'].startswith('false_trigger')}
cand = {r['url']: r for r in csv.DictReader(open(A1 + '/site_weapon_optic_role_candidates.csv'))}
mby = {m['link']: m for m in merchant}
assert len(assort) == len({a['url'] for a in assort}) == 14716
assert len(merchant) == len(mby) == len({m['offerId'] for m in merchant}) == 6077
assert all(l in {a['url'] for a in assort} for l in mby)

BUCKETS = [
 ('MC-1', 'Merchant: policy review (7 SKU from round-1 risk list)'),
 ('MC-2', 'Merchant: IN_STOCK, brand filled, not in policy review'),
 ('MC-3', 'Merchant: IN_STOCK, brand empty, not in policy review'),
 ('MC-4', 'Merchant: OUT_OF_STOCK, brand filled, not in policy review'),
 ('MC-5', 'Merchant: OUT_OF_STOCK, brand empty, not in policy review'),
 ('ST-1', 'Site only: heuristic weapon-optic candidate (needs manual role)'),
 ('ST-2', 'Site only: title known (image sitemap), not a candidate'),
 ('ST-3', 'Site only: no title/price/availability in snapshot, not a candidate'),
]
rows = []
for a in assort:
    m = mby.get(a['url'])
    r = dict(url=a['url'], offer_id='', in_merchant=bool(m), availability='', brand='',
             brand_filled=False, title=(m or a)['title'] or '', title_source=a['title_source'] or '',
             price_eur_with_vat='', weapon_candidate_heuristic=a['url'] in cand,
             candidate_role=cand.get(a['url'], {}).get('proposed_role', ''),
             in_scope_candidates=a['url'] in scope, policy_review=False, false_trigger_title=False)
    if m:
        r.update(offer_id=m['offerId'], availability=m['availability'], brand=m.get('brand') or '',
                 brand_filled=bool((m.get('brand') or '').strip()), price_eur_with_vat=m['price']['value'],
                 policy_review=m['offerId'] in policy_ids, false_trigger_title=m['offerId'] in false_ids)
        if r['policy_review']: b = 'MC-1'
        elif m['availability'] == 'IN_STOCK': b = 'MC-2' if r['brand_filled'] else 'MC-3'
        else: b = 'MC-4' if r['brand_filled'] else 'MC-5'
    else:
        if r['weapon_candidate_heuristic']: b = 'ST-1'
        elif a['title']: b = 'ST-2'
        else: b = 'ST-3'
    r['primary_bucket'] = b
    rows.append(r)
os.makedirs(out, exist_ok=True)
with open(os.path.join(out, 'catalog_buckets.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
c = collections.Counter(r['primary_bucket'] for r in rows)
with open(os.path.join(out, 'catalog_bucket_summary.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['bucket', 'description', 'count',
        'in_stock', 'out_of_stock', 'weapon_candidate_flag', 'false_trigger_title_flag', 'untitled'])
    for k, d in BUCKETS:
        rs = [r for r in rows if r['primary_bucket'] == k]
        w.writerow([k, d, len(rs), sum(r['availability'] == 'IN_STOCK' for r in rs),
                    sum(r['availability'] == 'OUT_OF_STOCK' for r in rs),
                    sum(r['weapon_candidate_heuristic'] for r in rs), sum(r['false_trigger_title'] for r in rs),
                    sum(not r['title'] for r in rs)])
    w.writerow(['TOTAL', '', sum(c.values()), '', '', '', '', ''])
assert sum(c.values()) == 14716 and sum(c[k] for k in ('MC-1','MC-2','MC-3','MC-4','MC-5')) == 6077
print(dict(sorted(c.items())))
