#!/usr/bin/env python3
"""Run every round-4 script (02 package + 04b fixes), then validate the package.
Writes test_run_output.txt here and ../04b_claude_code_attachments/test_run_output_04b.txt.
Usage (from repository root):  python -I discussions/round-04/02_claude_code_attachments/run_all.py
"""
import csv, io, os, re, subprocess, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.normpath(os.path.join(HERE, '..', '04b_claude_code_attachments'))
D04D = os.path.normpath(os.path.join(HERE, '..', '04d_claude_code_attachments'))
REPO = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
SCRIPTS = [os.path.join(HERE, s) for s in ('coverage_map.py', 'routing_tests.py', 'economics_recheck.py', 'stock_sync_dryrun.py')] + \
          [os.path.join(FIX, s) for s in ('account_negatives_review.py', 'full_coverage_plan.py')] + \
          [os.path.join(D04D, s) for s in ('account_negatives_review_v2.py', 'test_catalog_refresh.py')]
out = io.StringIO()
fails = []


def say(*a):
    print(*a); print(*a, file=out)


def check(name, cond, detail=''):
    say(('PASS ' if cond else 'FAIL ') + name + (f'  [{detail}]' if detail != '' else ''))
    if not cond:
        fails.append(name)


def rows(fn, d=HERE):
    with open(os.path.join(d, fn), encoding='utf-8') as f:
        return list(csv.DictReader(f))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    sys.path.insert(0, HERE); sys.dont_write_bytecode = True
    sha = subprocess.run(['git', '-C', REPO, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    say('repo HEAD at run time:', sha or 'UNKNOWN')
    for s in SCRIPTS:
        r = subprocess.run([sys.executable, '-I', s], capture_output=True, text=True, encoding='utf-8')
        say(f'\n$ python -I {os.path.relpath(s, REPO)}  (exit {r.returncode})')
        say(r.stdout.rstrip())
        if r.returncode:
            say(r.stderr); fails.append(os.path.basename(s))

    say('\n=== package checks: coverage map (pilot 32) ===')
    cm = rows('coverage_map.csv')
    ids = [r['offer_id'] for r in cm if r['offer_id']]
    check('coverage: exactly 32 rows', len(cm) == 32, len(cm))
    check('coverage: 26 non-empty offerIds, all unique', len(ids) == 26 and len(set(ids)) == 26, f'{len(ids)}/{len(set(ids))}')
    site = [r for r in cm if not r['offer_id']]
    check('coverage: 6 site-only rows, UNKNOWN, not claimed as CS-Cart error',
          len(site) == 6 and all(r['coverage_status'] == 'SITE_ONLY_UNKNOWN' and 'Not proof' in r['status_reason']
                                 and r['fact_availability_2026_11_14'] == 'UNKNOWN' for r in site))
    m = {r['offer_id']: r for r in cm if r['offer_id']}
    check('26130 monocular, label monokuláre kept, rollback = no previous ad',
          m['26130']['product_type'] == 'monocular' and m['26130']['fact_cc_2026_11_15_label0'] == 'monokuláre'
          and 'NO previous ad' in m['26130']['rollback_boundary'])
    check('coverage: all campaign memberships kept per offerId', all(r['fact_cc_2026_11_15_campaigns'].count('|') >= 2 for r in cm if r['offer_id']))

    say('\n=== routing + negatives ===')
    rt = rows('routing_tests.csv')
    tids = {r['test_id'] for r in rt}
    check('routing: 63 tests (47 + R48/R49 + Cowork C01-C14)', len(rt) == 63, dict(Counter(r['verdict'] for r in rt)))
    check('routing: Cowork C01-C14 all present', {f'C{i:02d}' for i in range(1, 15)} <= tids)
    need = {'model', 'kde_kupit', 'cena', 'generation', 'mono_bino', 'magnification', 'goto_mount', 'accessory', 'hyphen_diacritics', 'excluded', 'generic', 'cowork_counterexample'}
    check('routing: all required categories covered', need <= {r['category'] for r in rt})
    check('routing: three owner queries verbatim', {'leica trinovid 10x42 hd', 'levenhuk vegas ed 10×42', 'skywatcher explorer-150pds eq3'} <= {r['query'] for r in rt})
    by = {r['test_id']: r for r in rt}
    check('routing: "s puzdrom" bundle wording not blocked by accessory proposal (R48)', by['R48']['verdict'].startswith('PASS'))
    after = rows('routing_tests_after_proposed_diff.csv')
    res = Counter(r['current_resolution'].split(':')[0] for r in after)
    check('routing: every test has a current resolution, none OPEN', res.get('OPEN', 0) == 0 and all(r['current_resolution'] for r in after), dict(res))
    remA = {r['test_id'] for r in after if r['verdict_A_technical_fixes_only'] == 'FAIL'}
    check('routing: scenario A leaves only owner-decision failures',
          all(x['proposed_resolution_after_A'].startswith('OWNER_DECISION') for x in after if x['test_id'] in remA), sorted(remA))
    ab = {r['test_id']: r for r in after}
    check('routing 04d p.5: R18/C09/R43 current = MONITOR_CV', all(ab[t]['current_resolution'] == 'MONITOR_CV' for t in ('R18', 'C09', 'R43')))
    check('routing 04d p.5: R43 proposed FIXED_LITERAL; R18/C09 stay MONITOR_CV',
          ab['R43']['proposed_resolution_after_A'] == 'FIXED_LITERAL' and all(ab[t]['proposed_resolution_after_A'] == 'MONITOR_CV' for t in ('R18', 'C09')))
    closed = lambda v: v in ('NO_CHANGE_NEEDED', 'FIXED_LITERAL', 'FIXED_BY_TECHNICAL_PROPOSAL')
    check('routing 04d p.5: MONITOR_CV is never counted as closed; current/proposed consistent',
          all(not closed(r['current_resolution']) for r in after if r['verdict_now'] != 'PASS')
          and all(r['proposed_resolution_after_A'] == 'NO_CHANGE_NEEDED' for r in after if r['current_resolution'] == 'NO_CHANGE_NEEDED')
          and all(r['proposed_resolution_after_A'] == 'MONITOR_CV' for r in after if r['verdict_A_technical_fixes_only'] == 'PASS_LITERAL_RISK_CV'))
    diff = rows('negative_keyword_diff.csv')
    check('diff: all rows PROPOSAL_NOT_APPLIED with basis/example/risk/verification',
          all(r['status'] == 'PROPOSAL_NOT_APPLIED' and r['basis'] and r['example_tests'] and r['risk'] and r['verification'] for r in diff))
    kde = [r for r in diff if r['negative'] == 'kde']
    check('diff: kde is an owner decision with options, not a final move to all campaigns',
          kde and kde[0]['action'] == 'OWNER_DECISION' and 'No option is pre-selected' in kde[0]['proposal'])
    blockers = {h for r in rt if r['expected_shopping_reaches_auction'] == 'True' for h in r['account_neg_hits_literal'].split(';') if h}
    covered = {f"{r['match_type']}:{r['negative']}" for r in diff if r['level'] == 'ACCOUNT'}
    check('diff: every account negative blocking a commercial test is in the diff', blockers <= covered, sorted(blockers - covered))
    nr = rows('account_negatives_review.csv', FIX)
    import json
    src = json.load(open(os.path.join(REPO, 'discussions/round-03/05_chatgpt_attachments/live_checks_2026-11-15.json'), encoding='utf-8'))['account_negative_keywords']
    check('negatives review: all 258 verbatim (text, case, diacritics, match type)',
          len(nr) == 258 and [(r['text'], r['match_type']) for r in nr] == [(n['text'], n['matchType']) for n in src])
    check('negatives review: no UNCLASSIFIED word', not [r for r in nr if r['word_class'] == 'UNCLASSIFIED'])
    check('negatives review: every word with a commercial test hit is not plain KEEP',
          all(r['recommended_action'] != 'KEEP' for r in nr if [t for t in r['tests_blocked'].split(';') if t and t not in ('R45', 'C10', 'R43', 'R44')]))
    check('negatives review: words matching in-stock titles are not plain KEEP', all(r['recommended_action'] != 'KEEP' for r in nr if int(r['catalogue_in_stock_15_11']) > 0))

    say('\n=== economics ===')
    ee = rows('economics_edge_tests.csv')
    check('economics: all edge tests pass', all(r['result'] == 'PASS' for r in ee), f"{sum(r['result']=='PASS' for r in ee)}/{len(ee)}")
    er = rows('economics_recheck.csv')
    check('economics: Cowork rerun identical; independent within 0.01 EUR',
          all(r['rerun_identical'] == 'True' for r in er) and max(float(r['abs_diff_independent']) for r in er) <= 0.01)
    check('economics: no "gross" ROAS column; bases named without_VAT', not [k for k in er[0] if 'BE_ROAS' in k and ('gross' in k or 'without_VAT' not in k)], list(er[0]))
    check('economics: rows labelled scenario, not actual costs', all('not actual Sonata costs' in r['data_status'] for r in er))

    say('\n=== stock sync ===')
    ss = rows('stock_sync_dryrun_results.csv')
    sids = {r['scenario'] for r in ss}
    check('stock sync: all scenarios pass', all(r['result'] == 'PASS' for r in ss), f"{sum(r['result']=='PASS' for r in ss)}/{len(ss)}")
    check('stock sync: Cowork C1-C4 + purity/provenance regressions present',
          {'C1', 'C2a', 'C2b', 'C3', 'C4a', 'C4b', 'U1', 'U2', 'F1', 'F2', 'F3', 'I1', 'M1', 'M2'} <= sids)
    check('stock sync 04d: window/hold/customer/feed-label/partial-failure regressions present',
          {'C3x', 'W1', 'W2', 'W3', 'H1', 'H2', 'C2c', 'C2d', 'C2e', 'C2f', 'C2g', 'C2h', 'C2i', 'P1', 'P2'} <= sids)
    ad = subprocess.run([sys.executable, '-I', os.path.join(D04D, 'stock_sync_counterexamples_v2_adapted.py'), HERE], capture_output=True, text=True, encoding='utf-8')
    open(os.path.join(D04D, 'stock_sync_counterexamples_v2_adapted_output.txt'), 'w', encoding='utf-8').write(ad.stdout)
    check('stock sync 04d: adapted Cowork counterexamples 0 PROBLEM', '0 PROBLEM' in ad.stdout, ad.stdout.strip().splitlines()[-1] if ad.stdout else ad.stderr[-200:])

    say('\n=== negatives review v2 (04d p.4) ===')
    nv = rows('account_negatives_review_v2.csv', D04D)
    raw = {r['offer_id']: r for r in rows('inputs/shopping_product_2026-11-25.csv', D04D) if r['merchant_id'] == '5831333799'}
    import routing_tests as rtm
    check('v2: 258 rows, every illustrative query literally blocked by its own word and match type',
          len(nv) == 258 and all(rtm.neg_hit(r['illustrative_query_stored_form'], r['match_type'], r['text']) for r in nv))
    check('v2: catalogue examples are real 25.11 offers whose title literally matches, else NO_VERIFIED_CATALOG_EXAMPLE',
          all((r['catalogue_example_offer_id'] == 'NO_VERIFIED_CATALOG_EXAMPLE' and r['catalogue_literal_matches'] == '0')
              or (r['catalogue_example_offer_id'] in raw and raw[r['catalogue_example_offer_id']]['title'] == r['catalogue_example_title']
                  and rtm.neg_hit(r['catalogue_example_title'], r['match_type'], r['text'])) for r in nv))
    check('v2: every example is marked illustrative, none claimed as historical search term',
          all(r['example_kind'].startswith('illustrative') for r in nv))
    sol = next(r for r in nv if r['text'] == 'solarna')
    check('v2: solarna vs solárna literal tests differ (blocked / not blocked)', sol['blocked_literal_stored_form'] == 'True' and sol['blocked_literal_other_form'] == 'False')
    check('v2: heureka is OWNER_DECISION_HEUREKA; owner-direction words limited to kde/poradiť/lacno/nie drahé/cheap/popis',
          next(r for r in nv if r['text'] == 'heureka')['action_v2'] == 'OWNER_DECISION_HEUREKA'
          and {r['text'] for r in nv if r['action_v2'] == 'PROPOSED_BY_OWNER_DIRECTION'} == {'kde', 'poradiť', 'lacno', 'nie drahé', 'cheap', 'popis'})
    check('v2: every row is a proposal', all(r['status'] == 'PROPOSAL_NOT_APPLIED' for r in nv))
    cat_out = open(os.path.join(D04D, 'test_catalog_refresh_output.txt'), encoding='utf-8').read()
    check('catalogue refresh 25.11: all its checks pass', 'RESULT: ALL CHECKS PASS' in cat_out)

    say('\n=== full catalogue coverage plan ===')
    fp = rows('full_catalog_coverage_plan.csv', FIX)
    ins = [r for r in fp if r['availability'] == 'IN_STOCK']
    cs = Counter(r['current_state'] for r in ins)
    check('full: 6078 rows, unique composite IDs, only Merchant 5831333799',
          len(fp) == 6078 and len({r['composite_id'] for r in fp}) == 6078 and {r['merchant_id'] for r in fp} == {'5831333799'})
    check('full: 4269 in stock = 1886 eligible + 2376 no campaign + 7 other block',
          len(ins) == 4269 and cs['COVERED_ELIGIBLE'] == 1886 and cs['IN_STOCK_NO_CAMPAIGN'] == 2376 and cs['IN_STOCK_OTHER_BLOCK'] == 7, dict(cs))
    gap = [r for r in ins if r['current_state'] == 'IN_STOCK_NO_CAMPAIGN']
    check('full: no policy-flagged gap row is proposed for plain wave inclusion',
          not [r for r in gap if r['policy_review_required'] == 'YES' and r['proposed_action'] == 'ADD_IN_WAVE'])
    check('full: rows with policy issue codes are excluded pending review',
          all(r['proposed_action'] in ('EXCLUDE_PENDING_POLICY_REVIEW', 'KEEP_CURRENT_POLICY_REVIEW', 'HOLD_ROLE_UNRESOLVED')
              for r in fp if re.search('guns_parts|hacking|healthcare', r['issue_codes'])))
    check('full: bresser.de gets no invented role/campaign', all(r['proposed_campaign'] == 'NONE_UNTIL_ROLE_DECIDED' for r in fp if r['label0'] == 'bresser.de'))
    check('full: existing scoped coverage untouched', all(r['proposed_action'].startswith('KEEP') or r['proposed_action'] == 'FIX_DATA_KEEP_IN_TREE'
                                                          for r in fp if r['current_state'] == 'COVERED_ELIGIBLE'))
    check('full: 26 pilot IDs present and marked', sum(r['pilot_26_member'] == 'YES' for r in fp) == 26)
    check('full: every row is a proposal', all(r['status'] == 'PROPOSAL_NOT_APPLIED' for r in fp))

    md = [os.path.join(HERE, f) for f in os.listdir(HERE) if f.endswith('.md')]
    for rep in ('02_claude_code_report.md', '04b_claude_code_fix_report.md', '04d_claude_code_report.md', '04d_claude_code_catalog_refresh.md'):
        p = os.path.join(HERE, '..', rep)
        if os.path.exists(p):
            md.append(p)
    bad = []
    for p in md:
        txt = open(p, encoding='utf-8').read()
        for link in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', txt):
            if not link.startswith('http') and not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p), link))):
                bad.append(f'{os.path.basename(p)} -> {link}')
    check('markdown relative links resolve', not bad, bad[:5])

    say(f'\nRESULT: {"ALL CHECKS PASS" if not fails else "FAILED: " + ", ".join(fails)}')
    for p in (os.path.join(HERE, 'test_run_output.txt'), os.path.join(D04D, 'test_run_output_04d.txt')):
        with open(p, 'w', encoding='utf-8') as f:
            f.write(out.getvalue())
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
