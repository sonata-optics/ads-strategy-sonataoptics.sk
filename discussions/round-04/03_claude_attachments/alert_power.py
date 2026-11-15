#!/usr/bin/env python3
"""Replaces Cowork r3 '~74 impressions' with an explicit model (round 4).
Model: daily impressions N ~ overdispersed count, Var = phi * mean (quasi-Poisson; phi unknown, estimate from E4).
Test: log-ratio of pilot cohort to concurrent control cohort, compared with the same ratio in a baseline window.
  Var(log R_test) ~ phi*(1/Ep + 1/Ec),  Var(log R_base) ~ phi*(1/Bp + 1/Bc)
Detect relative drop delta with one-sided alpha and power (1-beta):
  |log(1-delta)| >= (z_a + z_b) * sqrt(phi*(1/Ep+1/Ec) + phi*(1/Bp+1/Bc))
Assume Ec = c*Ep (control size ratio) and baseline window w times longer (Bp = w*Ep, Bc = w*Ec).
Solve for Ep. Also: family-wise false alarm of repeated daily checks.
"""
import csv, math, sys
from statistics import NormalDist
Z = NormalDist().inv_cdf
def ep_required(delta, alpha, power, phi, c=1.0, w=4.0):
    k = (Z(1 - alpha) + Z(power)) ** 2 / math.log(1 - delta) ** 2
    # k <= 1/[phi*(1/Ep)(1+1/c)(1+1/w)]  -> Ep >= k*phi*(1+1/c)*(1+1/w)
    return k * phi * (1 + 1 / c) * (1 + 1 / w)
old = (2.58 / 0.3) ** 2
rows = []
for delta in (0.3, 0.5):
    for phi in (1, 3, 10):
        for c in (1.0, 3.0):
            ep = ep_required(delta, 0.01, 0.8, phi, c)
            rows.append(dict(drop=delta, alpha_one_sided=0.01, power=0.8, phi=phi, control_size_ratio=c, baseline_window_x=4,
                             pilot_expected_impressions_needed=round(ep), days_at_40_per_day=round(ep / 40, 1),
                             days_at_200_per_day=round(ep / 200, 1)))
out = sys.argv[1] if len(sys.argv) > 1 else 'alert_power.csv'
with open(out, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print('r3 rule (z=2.58, delta=.3, known baseline, Poisson, 50% power):', round(old))
print('same, Poisson, known baseline, 80% power, one-sided 1%:', round((Z(.99) + Z(.8) * math.sqrt(.7)) ** 2 / .3 ** 2))
for r in rows: print(r)
for n in (14, 28):
    for a in (0.01, 0.05):
        print(f'daily checks n={n} alpha={a}: P(>=1 false alarm) = {1 - (1 - a) ** n:.2f} (independent approx)')
