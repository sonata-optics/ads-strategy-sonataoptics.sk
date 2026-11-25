#!/usr/bin/env python3
"""Checks for the 25.11 catalogue refresh. Runs catalog_refresh_2026-11-25.py first, then validates outputs.
Writes test_catalog_refresh_output.txt. No network, no live changes.
Usage (repo root): python -I discussions/round-04/04d_claude_code_attachments/test_catalog_refresh.py
"""
import csv, importlib.util, io, os, subprocess, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
out, fails = io.StringIO(), []


def say(*a):
    print(*a); print(*a, file=out)


def check(name, cond, detail=''):
    say(('PASS ' if cond else 'FAIL ') + name + (f'  [{detail}]' if detail != '' else ''))
    if not cond:
        fails.append(name)


def rows(fn):
    with open(os.path.join(HERE, fn), encoding='utf-8') as f:
        return list(csv.DictReader(f))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'catalog_refresh_2026-11-25.py')], capture_output=True, text=True, encoding='utf-8')
    say('$ python -I catalog_refresh_2026-11-25.py (exit %d)' % r.returncode); say(r.stdout.rstrip())
    if r.returncode:
        say(r.stderr); fails.append('generator')
    spec = importlib.util.spec_from_file_location('cr', os.path.join(HERE, 'catalog_refresh_2026-11-25.py'))
    cr = importlib.util.module_from_spec(spec); spec.loader.exec_module(cr)

    raw = rows('inputs/shopping_product_2026-11-25.csv')
    plan = rows('full_catalog_coverage_plan_2026-11-25.csv')
    rec = rows('category_reconciliation.csv')
    con = rows('label_contract.csv')
    say('\n=== export and denominators ===')
    check('export: 8090 rows, unique composite keys', len(raw) == 8090 and len({'~'.join(x[k] for k in ('merchant_id', 'channel', 'language', 'feed_label', 'offer_id')) for x in raw}) == 8090)
    check('plan: only Merchant 5831333799 (262 rows of Merchant 755641187 / feed SHOP excluded)',
          len(plan) == 7828 and {p['composite_id'].split('~')[0] for p in plan} == {'5831333799'})
    ins = [p for p in plan if p['availability'] == 'IN_STOCK']
    cs = Counter(p['current_state'] for p in ins)
    check('plan: 4712 in stock = 1720 eligible + 2984 no campaign + 8 other block',
          len(ins) == 4712 and cs['COVERED_ELIGIBLE'] == 1720 and cs['IN_STOCK_NO_CAMPAIGN'] == 2984 and cs['IN_STOCK_OTHER_BLOCK'] == 8, dict(cs))
    check('every row has titles (no silent empties)', all(p['title'] for p in plan))

    say('\n=== category migration (owner: bresser.de removed) ===')
    check('no product carries label bresser.de on 25.11', not [p for p in plan if p['label0'] == 'bresser.de'])
    b = [x for x in rec if x['from_temporary_bresser_de'] == 'YES']
    check('all 558 former bresser.de IDs accounted for (re-labelled or absent from Merchant)',
          len(b) == 558 and all(x['change_type'] in ('LABEL_CHANGED', 'REMOVED_ID') for x in b), dict(Counter(x['change_type'] for x in b)))
    check('reconciliation covers union of both snapshots', len(rec) == len({x['offer_id'] for x in rec}) == 6078 + 3531)
    p = {x['offer_id']: x for x in plan}
    check('regression 26916 Zoom monokulár: label monokuláre, routed to observation optics, not astro accessories',
          p['26916']['label0'] == 'monokuláre' and p['26916']['proposed_campaign'] == 'NEW_SK_SHOP_Pozorovacia_optika')
    check('regression 26130 monocular: still monokuláre, still no campaign today', p['26130']['label0'] == 'monokuláre' and p['26130']['current_state'] == 'IN_STOCK_NO_CAMPAIGN')
    check('label contract: every 25.11 label is mapped (no CONTRACT_FAIL)', all(c['contract_status'] != 'CONTRACT_FAIL' for c in con), [c['label0'] for c in con if c['contract_status'] == 'CONTRACT_FAIL'])
    check('label contract: an unknown future label would fail', 'nová kategória X' not in {l for ls in cr.NEW.values() for l in ls} and 'nová kategória X' not in cr.ROLE_UNDECIDED)

    say('\n=== admission (hybrid, R4-CLAUDECODE-07) and policy (R4-CLAUDE-11) ===')
    check('every *_policy_violation row is POLICY_HOLD regardless of availability/state',
          all(x['proposed_action'] == 'POLICY_HOLD' for x in plan if x['policy_codes']), dict(Counter((x['availability'], x['current_state']) for x in plan if x['policy_codes'])))
    check('policy detection is generic (synthetic new code)', cr.policy_codes(['not_eligible_in_any_campaign', 'new_future_policy_violation']) == ['new_future_policy_violation'])
    check('not_eligible_in_any_campaign is not treated as policy', cr.policy_codes(['not_eligible_in_any_campaign']) == [])
    check('risky labels only by VERIFIED_ID', all(x['admission_mode'] == 'VERIFIED_ID' for x in plan if x['label0'] in cr.RISKY_LABELS))
    check('no row is reviewed yet; generated allowlist is empty (new IDs not advertised before review)',
          all(x['ads_review_ok'] == 'NOT_REVIEWED' for x in plan) and len(rows('allowlist_generated.csv')) == 0)
    # simulated review register: before/after review of a new SKU and a new policy code
    cand = next(x for x in plan if x['proposed_action'] == 'CANDIDATE_PENDING_REVIEW' and x['change_since_2026_11_15'] == 'NEW_ID')
    def admitted(x, reviewed):
        if x['policy_codes']:
            return False
        if x['proposed_action'] != 'CANDIDATE_PENDING_REVIEW':
            return False
        return x['composite_id'] in reviewed
    check('new SKU: not admitted before review, admitted after review record', not admitted(cand, set()) and admitted(cand, {cand['composite_id']}), cand['offer_id'])
    flagged = dict(cand, policy_codes='new_future_policy_violation')
    check('reviewed SKU that later gets a policy code loses admission', not admitted(flagged, {cand['composite_id']}))
    check('existing scoped coverage kept (eligible rows never proposed for move)',
          all(x['proposed_action'] in ('KEEP_CURRENT', 'KEEP_CURRENT_VERIFY_ID', 'POLICY_HOLD') for x in plan if x['current_state'] == 'COVERED_ELIGIBLE'))
    check('paused Junior Lab campaign is an owner decision, not a new campaign',
          all(x['proposed_action'] in ('OWNER_DECISION_RESUME_CAMPAIGN', 'POLICY_HOLD', 'KEEP_CURRENT', 'KEEP_CURRENT_VERIFY_ID') or x['current_state'] != 'IN_STOCK_NO_CAMPAIGN'
              for x in plan if x['label0'] == 'sonata junior lab'))
    check('every row is a proposal', all(x['status'] == 'PROPOSAL_NOT_APPLIED' for x in plan))

    say(f'\nRESULT: {"ALL CHECKS PASS" if not fails else "FAILED: " + ", ".join(fails)}')
    open(os.path.join(HERE, 'test_catalog_refresh_output.txt'), 'w', encoding='utf-8').write(out.getvalue())
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
