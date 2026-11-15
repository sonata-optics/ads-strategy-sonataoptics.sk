#!/usr/bin/env python3
"""Parametric unit economics for 4 control SKUs, formula of markets/sk/05_budget_and_roas.md v1.
ALL cost parameters below are SCENARIO ASSUMPTIONS, not Sonata data. Prices = Merchant snapshot 14.11.2026.
CR_ad = purchases / ad clicks (not site sessions).
"""
import csv, math, sys
VAT = 0.23  # base rate; per-SKU rate must be confirmed in CS-Cart
SKU = {  # offerId: (name, price_with_vat, scenario params)
 '103933': ('Leica Trinovid 10x42 HD', 1275.00, dict(S_out=8, H=3, r=0.04, S_back=0, H_ret=8, l=0.10)),
 '26113':  ('Levenhuk Vegas ED 10x42', 329.95, dict(S_out=5, H=3, r=0.05, S_back=0, H_ret=5, l=0.10)),
 '103640': ('Levenhuk New Vegas ED 10x42', 209.95, dict(S_out=5, H=3, r=0.05, S_back=0, H_ret=5, l=0.10)),
 '47420':  ('Sky-Watcher Explorer-150PDS EQ3', 697.22, dict(S_out=25, H=8, r=0.05, S_back=0, H_ret=15, l=0.15)),
}
FEE = 0.015       # payment fee share of gross order value, not refunded on return (assumption)
D_n = D_ret = 0.0 # free delivery assumed
def cm(Pg, m, S_out, H, r, S_back, H_ret, l):
    Pn = Pg / (1 + VAT); C = Pn * (1 - m); F = FEE * Pg; L = l * C
    CM = (1 - r) * (Pn - C) + D_n - r * D_ret - F - S_out - H - r * (S_back + H_ret + L)
    return Pn, C, F, CM
rows = []
for oid, (name, Pg, p) in SKU.items():
    for m in (0.15, 0.25, 0.35):
        for stress in (False, True):
            q = dict(p)
            if stress: q.update(r=2 * p['r'], S_back=p['S_out'])  # double returns, shop pays return shipping
            Pn, C, F, CM = cm(Pg, m, **q)
            row = dict(offer_id=oid, model=name, price_with_vat=Pg, net_price=round(Pn, 2), gross_margin=m,
                       scenario='stress' if stress else 'base', r=q['r'], cogs=round(C, 2), fees=round(F, 2),
                       S_out=q['S_out'], H=q['H'], S_back=q['S_back'], CM_exp=round(CM, 2),
                       BE_ROAS_adjusted=round((1 - q['r']) * Pn / CM, 2) if CM > 0 else 'n/a',
                       BE_ROAS_value_before_returns=round(Pn / CM, 2) if CM > 0 else 'n/a')
            for cr in (0.005, 0.01, 0.02, 0.03):
                row[f'maxCPC_BE_at_CRad_{cr*100:g}pct'] = round(CM * cr, 2) if CM > 0 else 0
            rows.append(row)
out = sys.argv[1] if len(sys.argv) > 1 else 'unit_economics_4sku.csv'
with open(out, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
for r in rows:
    if r['scenario'] == 'base': print(r['offer_id'], r['gross_margin'], r['CM_exp'], r['BE_ROAS_adjusted'], r['BE_ROAS_value_before_returns'], [r[k] for k in r if k.startswith('maxCPC')])
print('--- stress')
for r in rows:
    if r['scenario'] == 'stress': print(r['offer_id'], r['gross_margin'], r['CM_exp'], r['BE_ROAS_adjusted'])
# Vegas: CR ratio 103640/26113 needed for equal contribution per click
print('--- Vegas indifference CR_103640 / CR_26113 (equal margin %)')
for m in (0.15, 0.25, 0.35):
    a = cm(329.95, m, **SKU['26113'][2])[3]; b = cm(209.95, m, **SKU['103640'][2])[3]
    print(m, round(a, 2), round(b, 2), round(a / b, 2))
print('--- P(0 purchases) when spend = k*CM_exp at break-even CPC, CR p')
for k in (1.5, 2, 3):
    print(k, [(p, round((1 - p) ** (k / p), 3)) for p in (0.01, 0.02, 0.03)], 'limit e^-k', round(math.exp(-k), 3))
