#!/usr/bin/env python3
"""Round-4 economics: rerun Cowork r3 calculation + independent implementation + edge tests.

No real Sonata COGS, returns, fees or budget are used: every number is the Cowork r3 SCENARIO or
an explicit synthetic edge value. Outputs:
  economics_recheck.csv      Cowork CSV vs fresh rerun vs independent formula (24 rows)
  economics_edge_tests.csv   boundary tests with expected behaviour and PASS/FAIL
Formula source: markets/sk/05_budget_and_roas.md (CM_exp, V_exp_adjusted, thresholds, Max CPC).
"""
import csv, math, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
R3 = os.path.join(REPO, 'discussions/round-03/04_claude_attachments')
VAT = 0.23


def cm_doc(P_n, C, r, F, S_out, H, S_back, H_ret, L, D_n=0.0, D_ret=0.0):
    """Literal transcription of 05_budget_and_roas.md (independent of Cowork's code)."""
    return (1 - r) * (P_n - C) + D_n - r * D_ret - F - S_out - H - r * (S_back + H_ret + L)


def thresholds(P_n, r, cm, desired_profit=0.0):
    """Returns (BE_ROAS_adjusted, BE_ROAS_value_before_returns, target_CPA). None = not attainable."""
    if cm <= 0:
        return None, None, None
    v_adj = (1 - r) * P_n
    tgt = cm - desired_profit
    return v_adj / cm, P_n / cm, (tgt if tgt > 0 else None)


def max_cpc(cm, purchases, ad_clicks):
    """Max CPC = CM_exp * purchases / ad clicks. Unknown or non-positive -> 0 (never negative)."""
    if ad_clicks is None or ad_clicks <= 0 or purchases is None:
        return None
    return max(0.0, cm) * purchases / ad_clicks


def recheck():
    tmp = tempfile.mkdtemp()
    fresh = os.path.join(tmp, 'ue.csv')
    subprocess.run([sys.executable, '-I', os.path.join(R3, 'unit_economics_4sku.py'), fresh], check=True,
                   stdout=subprocess.DEVNULL)
    with open(os.path.join(R3, 'unit_economics_4sku.csv'), encoding='utf-8') as f:
        pub = list(csv.DictReader(f))
    with open(fresh, encoding='utf-8') as f:
        new = list(csv.DictReader(f))
    assert len(pub) == len(new) == 24
    FEE = 0.015
    rows = []
    for a, b in zip(pub, new):
        Pg = float(a['price_with_vat']); m = float(a['gross_margin']); r = float(a['r'])
        P_n = Pg / (1 + VAT); C = P_n * (1 - m)
        # Cowork scenario params for L (share of COGS) and H_ret are not in the CSV: take from script defaults
        p = {'103933': (8, 3, 0.10), '26113': (5, 3, 0.10), '103640': (5, 3, 0.10), '47420': (25, 8, 0.15)}[a['offer_id']]
        H_ret_base, H, lshare = {'103933': 8, '26113': 5, '103640': 5, '47420': 15}[a['offer_id']], p[1], p[2]
        cm_i = cm_doc(P_n, C, r, FEE * Pg, float(a['S_out']), H, float(a['S_back']), H_ret_base, lshare * C)
        be_adj, be_gross, _ = thresholds(P_n, r, cm_i)
        same_rerun = all(a[k] == b[k] for k in a)
        rows.append(dict(offer_id=a['offer_id'], margin=m, scenario=a['scenario'], CM_published=a['CM_exp'], CM_rerun=b['CM_exp'],
                         CM_independent=round(cm_i, 2), rerun_identical=same_rerun,
                         abs_diff_independent=round(abs(cm_i - float(a['CM_exp'])), 4),
                         BE_ROAS_adj_published=a['BE_ROAS_adjusted'], BE_ROAS_adj_independent=round(be_adj, 2) if be_adj else 'n/a',
                         BE_ROAS_gross_published=a['BE_ROAS_value_before_returns'], BE_ROAS_gross_independent=round(be_gross, 2) if be_gross else 'n/a',
                         breakeven_margin_pct=round(100 * breakeven_margin(Pg, r, FEE * Pg, float(a['S_out']), H, float(a['S_back']), H_ret_base, lshare), 2),
                         data_status='SCENARIO (Cowork r3), not Sonata data'))
    return rows


def breakeven_margin(Pg, r, F, S_out, H, S_back, H_ret, lshare):
    """Gross margin m at which CM_exp = 0 (CM is linear in m; L = lshare*C)."""
    P_n = Pg / (1 + VAT)
    f = lambda m: cm_doc(P_n, P_n * (1 - m), r, F, S_out, H, S_back, H_ret, lshare * P_n * (1 - m))
    a, b = f(0.0), f(1.0)
    return -a / (b - a)


def edge_tests():
    T = []
    def add(tid, desc, inputs, expected, actual, ok):
        T.append(dict(test_id=tid, description=desc, inputs=inputs, expected=expected, actual=actual, result='PASS' if ok else 'FAIL'))
    # doc example
    cm = cm_doc(100, 60, 0.10, 2, 5, 3, 4, 2, 6)
    be_adj, be_gross, _ = thresholds(100, 0.10, cm)
    add('E01', 'Method example 05_budget_and_roas', 'P_n=100 C=60 r=.1 F=2 S_out=5 H=3 S_back=4 H_ret=2 L=6', 'CM=24.8; BE adj 3.629; BE gross 4.032',
        f'CM={cm:.2f}; {be_adj:.3f}; {be_gross:.3f}', abs(cm - 24.8) < 1e-9 and round(be_adj, 3) == 3.629 and round(be_gross, 3) == 4.032)
    profit = 100 * cm - 2480
    add('E02', '100 initial orders, spend 2480 -> zero contribution after ads in both bases', 'as E01', '0', f'{profit:.6f}', abs(profit) < 1e-6)
    # zero / negative margin
    for tid, C in (('E03', 100.0), ('E04', 120.0)):
        cm = cm_doc(100, C, 0.05, 2, 5, 3, 0, 2, 0)
        be = thresholds(100, 0.05, cm)
        mc = max_cpc(cm, 1, 50)
        add(tid, f'Margin {"zero" if C == 100 else "negative"}: no positive BE ROAS, Max CPC clipped to 0', f'P_n=100 C={C}', 'CM<0; thresholds None; MaxCPC 0',
            f'CM={cm:.2f}; {be}; MaxCPC={mc}', cm < 0 and be == (None, None, None) and mc == 0.0)
    # all returned
    cm = cm_doc(100, 60, 1.0, 2, 5, 3, 4, 2, 6)
    add('E05', 'r=1 (every order returned): V_adj=0, CM negative', 'r=1', 'CM<0', f'CM={cm:.2f}', cm < 0)
    # monotone in r
    cms = [cm_doc(100, 60, r / 100, 2, 5, 3, 4, 2, 6) for r in range(0, 101, 5)]
    add('E06', 'CM_exp strictly decreasing in return rate r', 'r=0..1 step .05', 'monotone decreasing', f'{cms[0]:.2f} .. {cms[-1]:.2f}',
        all(x > y for x, y in zip(cms, cms[1:])))
    # base mixing
    cm = cm_doc(100, 60, 0.10, 2, 5, 3, 4, 2, 6); _, _, _ = thresholds(100, 0.1, cm)
    observed_gross_roas = 3.8   # between 3.629 (adjusted) and 4.032 (gross)
    wrong = observed_gross_roas >= 90 / cm      # comparing gross value with adjusted threshold
    right = observed_gross_roas >= 100 / cm
    add('E07', 'Mixing bases flips the verdict: gross ROAS 3.8 vs adjusted threshold says profitable, vs own threshold says loss',
        'gross ROAS=3.8', 'wrong=profitable, right=loss', f'wrong={wrong}; right={right}', wrong and not right)
    # remaining-purchase threshold
    cm = 24.8; r = 0.10
    add('E08', 'Ads removes returned conversions: CPA threshold per remaining purchase = CM/(1-r)', 'CM=24.8 r=.1', '27.56',
        f'{cm / (1 - r):.2f}', round(cm / (1 - r), 2) == 27.56)
    # desired profit >= CM
    be = thresholds(100, 0.1, 24.8, desired_profit=30)
    add('E09', 'desired_profit >= CM: no positive target CPA', 'CM=24.8 profit=30', 'target None', f'{be[2]}', be[2] is None)
    # CR denominators
    purchases, clicks, sessions = 6, 400, 520
    cpc_click = max_cpc(24.8, purchases, clicks)
    cpc_wrong = 24.8 * purchases / sessions
    add('E10', 'CR must be purchases/ad clicks; using purchases/sessions understates Max CPC when sessions>clicks',
        f'purchases={purchases} clicks={clicks} sessions={sessions} (synthetic)', 'click-based 0.372 > session-based 0.286',
        f'{cpc_click:.3f} vs {cpc_wrong:.3f}', round(cpc_click, 3) == 0.372 and cpc_click > cpc_wrong)
    add('E11', 'Unknown clicks: Max CPC is UNKNOWN, not 0 and not computed', 'clicks=None', 'None', f'{max_cpc(24.8, 1, None)}', max_cpc(24.8, 1, None) is None)
    add('E12', 'Zero purchases observed: CR estimate 0 gives Max CPC 0 -> must be read as no evidence, not a bid', 'purchases=0 clicks=14',
        '0.0 (flag INSUFFICIENT_DATA)', f'{max_cpc(24.8, 0, 14)}', max_cpc(24.8, 0, 14) == 0.0)
    # partial return by states vs averaged r
    # order: two lines A (P=80,C=50) and B (P=20,C=10); state 1 (p=.9) keep both; state 2 (p=.1) return B only
    keep = (80 - 50) + (20 - 10)
    partial = (80 - 50) - 2   # B returned, L=2 on B, no S_back
    ev_states = 0.9 * keep + 0.1 * partial
    r_avg = 0.1 * 20 / 100   # value-weighted average return share 2%
    ev_avg = (1 - r_avg) * (100 - 60) - r_avg * 2
    add('E13', 'Partial returns: expectation by states differs from single averaged r', 'lines A 80/50, B 20/10; P(return B)=.1, L_B=2',
        'state model != averaged-r model', f'states={ev_states:.2f}; avg_r={ev_avg:.2f}', abs(ev_states - ev_avg) > 0.01)
    # P(0 purchases) check of Cowork approximation
    k, p = 2, 0.02
    exact = (1 - p) ** (k / p)
    add('E14', 'Cowork: P(0 purchases) when spend = k*CM at break-even CPC ~ e^-k', 'k=2 p=.02', 'close to e^-2=0.135',
        f'{exact:.4f}', abs(exact - math.exp(-k)) < 0.005)
    return T


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rows = recheck()
    with open(os.path.join(HERE, 'economics_recheck.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    T = edge_tests()
    with open(os.path.join(HERE, 'economics_edge_tests.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(T[0].keys())); w.writeheader(); w.writerows(T)
    print('recheck rows', len(rows), 'rerun identical:', all(r['rerun_identical'] for r in rows),
          'max |indep - published| CM:', max(r['abs_diff_independent'] for r in rows))
    for r in rows:
        if r['scenario'] == 'base' and r['margin'] == 0.25:
            print(' ', r['offer_id'], r['CM_published'], r['CM_independent'], 'BE margin %', r['breakeven_margin_pct'])
    print('edge tests', sum(t['result'] == 'PASS' for t in T), '/', len(T), [t['test_id'] for t in T if t['result'] != 'PASS'])


if __name__ == '__main__':
    main()
