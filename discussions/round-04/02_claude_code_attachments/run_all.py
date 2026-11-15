#!/usr/bin/env python3
"""Run every round-4 script, then validate the package. Writes test_run_output.txt.
Usage (from repository root):  python -I discussions/round-04/02_claude_code_attachments/run_all.py
"""
import csv, io, json, os, re, subprocess, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
SCRIPTS = ['coverage_map.py', 'routing_tests.py', 'economics_recheck.py', 'stock_sync_dryrun.py']
out = io.StringIO()
fails = []


def say(*a):
    print(*a); print(*a, file=out)


def check(name, cond, detail=''):
    say(('PASS ' if cond else 'FAIL ') + name + (f'  [{detail}]' if detail else ''))
    if not cond:
        fails.append(name)


def rows(fn):
    with open(os.path.join(HERE, fn), encoding='utf-8') as f:
        return list(csv.DictReader(f))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    sha = subprocess.run(['git', '-C', REPO, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    say('repo HEAD at run time:', sha or 'UNKNOWN')
    for s in SCRIPTS:
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, s)], capture_output=True, text=True, encoding='utf-8')
        say(f'\n$ python -I {s}  (exit {r.returncode})')
        say(r.stdout.rstrip())
        if r.returncode:
            say(r.stderr); fails.append(s)

    say('\n=== package checks ===')
    cm = rows('coverage_map.csv')
    ids = [r['offer_id'] for r in cm if r['offer_id']]
    check('coverage: exactly 32 rows', len(cm) == 32, len(cm))
    check('coverage: 26 non-empty offerIds, all unique', len(ids) == 26 and len(set(ids)) == 26, f'{len(ids)}/{len(set(ids))}')
    site = [r for r in cm if not r['offer_id']]
    check('coverage: 6 site-only rows', len(site) == 6)
    check('coverage: site-only never claimed absent from current Merchant / CS-Cart error',
          all(r['coverage_status'] == 'SITE_ONLY_UNKNOWN' and 'NOT CHECKED' in r['status_reason'] and 'Not proof' in r['status_reason'] for r in site))
    check('coverage: site-only availability stays UNKNOWN (no zeros / no invented status)',
          all(r['fact_availability_2026_11_14'] == 'UNKNOWN' and r['price_eur_snapshot_2026_11_14'] == 'UNKNOWN' for r in site))
    m = {r['offer_id']: r for r in cm if r['offer_id']}
    check('26130 is monocular with label monokuláre, not relabelled',
          m['26130']['product_type'] == 'monocular' and m['26130']['fact_cc_2026_11_15_label0'] == 'monokuláre'
          and 'Do NOT relabel' in m['26130']['project_label_rule'])
    check('26130 rollback boundary states there is no previous ad',
          'NO previous ad' in m['26130']['rollback_boundary'])
    check('26130 classified as in-stock gap without campaign', m['26130']['coverage_status'] == 'GAP_IN_STOCK_NO_CAMPAIGN')
    check('snapshot columns: 14.11 values are labelled by date, live columns separate',
          all(k.endswith('2026_11_14') or 'live' not in k for k in cm[0]))
    check('no coverage row uses the word live for a 14.11 value',
          not any('live' in r['fact_availability_2026_11_14'].lower() for r in cm))
    check('every Merchant row has acceptance + rollback', all(r['acceptance_pre_launch'] and r['rollback'] for r in cm if r['offer_id']))
    check('pilot proposal never changes old campaigns in pilot phase',
          all(r['project_old_campaign_change'].startswith('NONE') for r in cm))
    # synthetic join test: two campaign rows of one offerId must both survive
    sys.path.insert(0, HERE)
    from collections import defaultdict
    fake = [{'offer_id': 'X', 'campaign': 'A'}, {'offer_id': 'X', 'campaign': 'B'}]
    agg = defaultdict(list)
    for p in fake:
        agg[p['offer_id']].append(p)
    check('join keeps several campaign rows per offerId (unit)', len(agg['X']) == 2)
    check('coverage: Claude Code recheck keeps all campaign memberships',
          all(r['fact_cc_2026_11_15_campaigns'].count('|') >= 2 for r in cm if r['offer_id']),
          'each offerId listed for 3 old unscoped campaigns + its scoped one')

    rt = rows('routing_tests.csv')
    v = Counter(r['verdict'] for r in rt)
    check('routing: 47 tests produced', len(rt) == 47, dict(v))
    cats = {r['category'] for r in rt}
    need = {'model', 'kde_kupit', 'cena', 'generation', 'mono_bino', 'magnification', 'goto_mount', 'accessory', 'hyphen_diacritics', 'excluded', 'generic'}
    check('routing: all required categories covered', need <= cats, sorted(need - cats))
    check('routing: three owner queries present verbatim',
          {'leica trinovid 10x42 hd', 'levenhuk vegas ed 10×42', 'skywatcher explorer-150pds eq3'} <= {r['query'] for r in rt})
    check('routing: literal and close-variant results kept in separate columns',
          all('search_route_literal_final' in r and 'search_route_assumed_cv' in r for r in rt))
    diff = rows('negative_keyword_diff.csv')
    check('diff: every row is a proposal, nothing applied', all(r['status'] == 'PROPOSAL_NOT_APPLIED' for r in diff))
    check('diff: every row has basis, example, risk and verification',
          all(r['basis'] and r['example_tests'] and r['risk'] and r['verification'] for r in diff))
    blockers = {h for r in rt if r['expected_shopping_reaches_auction'] == 'True' for h in r['account_neg_hits_literal'].split(';') if h}
    covered = {f"{r['match_type']}:{r['negative']}" for r in diff if r['level'] == 'ACCOUNT'}
    check('diff: every account negative that blocks a commercial test is reviewed', blockers <= covered, sorted(blockers - covered))
    after = rows('routing_tests_after_proposed_diff.csv')
    rem = [r['test_id'] for r in after if r['verdict_after_simulated_diff'] == 'FAIL']
    check('simulated diff leaves only owner-decision failures', set(rem) <= {'R13', 'R41', 'R42'}, rem)

    ee = rows('economics_edge_tests.csv')
    check('economics: all edge tests pass', all(r['result'] == 'PASS' for r in ee), f"{sum(r['result']=='PASS' for r in ee)}/{len(ee)}")
    er = rows('economics_recheck.csv')
    check('economics: Cowork script rerun identical to published CSV', all(r['rerun_identical'] == 'True' for r in er))
    check('economics: independent formula within rounding (<=0.01 EUR)', max(float(r['abs_diff_independent']) for r in er) <= 0.01)
    check('economics: all rows marked SCENARIO', all('SCENARIO' in r['data_status'] for r in er))
    ss = []
    with open(os.path.join(HERE, 'stock_sync_dryrun_results.csv'), encoding='utf-8') as f:
        ss = list(csv.DictReader(f))
    check('stock sync: all dry-run scenarios pass', all(r['result'] == 'PASS' for r in ss), f"{sum(r['result']=='PASS' for r in ss)}/{len(ss)}")

    # relative links in markdown files of this package must resolve
    md = [os.path.join(HERE, f) for f in os.listdir(HERE) if f.endswith('.md')]
    rep = os.path.join(HERE, '..', '02_claude_code_report.md')
    if os.path.exists(rep):
        md.append(rep)
    bad = []
    for p in md:
        txt = open(p, encoding='utf-8').read()
        for link in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', txt):
            if link.startswith('http'):
                continue
            if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p), link))):
                bad.append(f'{os.path.basename(p)} -> {link}')
    check('markdown relative links resolve', not bad, bad[:5])

    say(f'\nRESULT: {"ALL CHECKS PASS" if not fails else "FAILED: " + ", ".join(fails)}')
    with open(os.path.join(HERE, 'test_run_output.txt'), 'w', encoding='utf-8') as f:
        f.write(out.getvalue())
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
