#!/usr/bin/env python3
"""Independent economics check (Cowork r4). Derives CM_exp from explicit order states instead of the
closed formula of 05_budget_and_roas.md, then compares. Inputs = SCENARIO assumptions of Cowork r3
(not Sonata data); prices = Merchant snapshot 14.11.2026.
State model per initial order:
  kept     (prob 1-r): +P_n - C + D_n - F - S_out - H
  returned (prob r)  : +D_n - D_ret - F - S_out - H - S_back - H_ret - L   (goods back, revenue refunded)
Outputs both value bases, break-even margin, Max CPC at CR = purchases/ad clicks, and a VAT-base error demo.
"""
import csv, sys
VAT = 0.23; FEE = 0.015
SKU = {'103933': (1275.00, dict(S_out=8, H=3, r=0.04, S_back=0, H_ret=8, l=0.10)),
       '26113': (329.95, dict(S_out=5, H=3, r=0.05, S_back=0, H_ret=5, l=0.10)),
       '103640': (209.95, dict(S_out=5, H=3, r=0.05, S_back=0, H_ret=5, l=0.10)),
       '47420': (697.22, dict(S_out=25, H=8, r=0.05, S_back=0, H_ret=15, l=0.15))}
def states(Pg, m, S_out, H, r, S_back, H_ret, l, D_n=0.0, D_ret=0.0):
    Pn = Pg / (1 + VAT); C = Pn * (1 - m); F = FEE * Pg; L = l * C
    kept = Pn - C + D_n - F - S_out - H
    ret = D_n - D_ret - F - S_out - H - S_back - H_ret - L
    return Pn, (1 - r) * kept + r * ret
def closed(Pg, m, S_out, H, r, S_back, H_ret, l):   # formula of 05_ with D_n=D_ret=0
    Pn = Pg / (1 + VAT); C = Pn * (1 - m); F = FEE * Pg; L = l * C
    return (1 - r) * (Pn - C) - F - S_out - H - r * (S_back + H_ret + L)
def be_margin(Pg, p, lo=-1.0, hi=1.0):
    for _ in range(200):
        mid = (lo + hi) / 2
        if states(Pg, mid, **p)[1] > 0: hi = mid
        else: lo = mid
    return hi
rows = []
for oid, (Pg, p0) in SKU.items():
    for m in (0.15, 0.25, 0.35):
        for sc in ('base', 'stress'):
            p = dict(p0)
            if sc == 'stress': p.update(r=2 * p0['r'], S_back=p0['S_out'])
            Pn, cm = states(Pg, m, **p); cmc = closed(Pg, m, **p)
            V_adj = (1 - p['r']) * Pn
            rows.append(dict(offer_id=oid, scenario=sc, margin=m, P_gross=Pg, P_net=round(Pn, 2), r=p['r'],
                CM_states=round(cm, 2), CM_closed_05=round(cmc, 2), diff=round(abs(cm - cmc), 6),
                BE_ROAS_adjusted_value=round(V_adj / cm, 3) if cm > 0 else 'NO_POSITIVE_THRESHOLD',
                BE_ROAS_value_before_returns=round(Pn / cm, 3) if cm > 0 else 'NO_POSITIVE_THRESHOLD',
                WRONG_threshold_if_value_incl_VAT=round(Pg / cm, 3) if cm > 0 else '',
                breakeven_margin_pct=round(100 * be_margin(Pg, p), 2),
                maxCPC_CR1=round(max(cm, 0) * 0.01, 2), maxCPC_CR2=round(max(cm, 0) * 0.02, 2), maxCPC_CR3=round(max(cm, 0) * 0.03, 2),
                data_status='SCENARIO'))
assert all(r['diff'] < 1e-9 for r in rows), 'state model and closed formula disagree'
out = sys.argv[1] if len(sys.argv) > 1 else 'economics_independent.csv'
with open(out, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
for r in rows:
    if r['margin'] == 0.25 or r['scenario'] == 'stress' and r['margin'] == 0.15:
        print(r['offer_id'], r['scenario'], r['margin'], r['CM_states'], r['BE_ROAS_adjusted_value'], r['BE_ROAS_value_before_returns'], r['WRONG_threshold_if_value_incl_VAT'], r['breakeven_margin_pct'])
# negative contribution example: small margin, stress
Pn, cm = states(209.95, 0.05, **dict(SKU['103640'][1], r=0.10, S_back=5))
print('negative example 103640 m=5% stress:', round(cm, 2))
