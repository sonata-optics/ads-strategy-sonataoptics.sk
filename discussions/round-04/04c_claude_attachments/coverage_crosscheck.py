#!/usr/bin/env python3
"""Cowork 04c: cross-check Claude Code full_catalog_coverage_plan.csv against ChatGPT catalog_coverage_2026-11-15.csv.
Usage: python3 -I -B coverage_crosscheck.py <round-04 dir>"""
import csv, sys, os, collections as C
d = sys.argv[1]
P = list(csv.DictReader(open(os.path.join(d, '04b_claude_code_attachments/full_catalog_coverage_plan.csv'), encoding='utf-8')))
G = list(csv.DictReader(open(os.path.join(d, '04_chatgpt_attachments/catalog_coverage_2026-11-15.csv'), encoding='utf-8')))
gk = {'~'.join([g['merchant_id'], g['channel'], g['language'], g['feed_label'], g['offer_id']]): g for g in G}
pk = {p['composite_id']: p for p in P}
print('rows plan/source', len(P), len(G), '| unique', len(pk), len(gk), '| same key set', set(pk) == set(gk))
mism = C.Counter()
pairs = [('availability', 'availability'), ('label0', 'label0'), ('account_status', 'account_status'),
         ('issue_codes', 'account_issue_codes'), ('current_scoped_statuses', 'scoped_campaign_statuses'),
         ('current_eligible_campaigns', 'eligible_campaign_ids')]
ex = {}
for k, p in pk.items():
    g = gk.get(k)
    if not g: mism['missing_in_source'] += 1; continue
    for a, b in pairs:
        norm = lambda v: '' if (v or '').strip() == 'NONE' else (v or '').strip()
        if norm(p[a]) != norm(g[b]):
            mism[a] += 1; ex.setdefault(a, (k, p[a], g[b]))
print('field mismatches', dict(mism) or 'none', ex)
# derived counts
inst = [p for p in P if p['availability'] == 'IN_STOCK']
print('IN_STOCK', len(inst), C.Counter(p['current_state'] for p in inst).most_common())
print('proposed_action x availability'); [print('  ', k, v) for k, v in sorted(C.Counter((p['proposed_action'], p['availability']) for p in P).items())]
print('wave (IN_STOCK)', sorted(C.Counter(p['wave'] for p in inst).items()))
# consistency rules
bad = C.Counter()
for p in P:
    elig = p['current_eligible_campaigns'] not in ('', 'NONE')
    if elig and p['current_state'] != 'COVERED_ELIGIBLE': bad['eligible_but_not_COVERED_ELIGIBLE'] += 1
    if not elig and p['current_state'] == 'COVERED_ELIGIBLE': bad['COVERED_ELIGIBLE_without_campaign'] += 1
    if p['proposed_action'] in ('ADD_IN_WAVE',) and (p['policy_review_required'] == 'YES' or p['data_review_required'] == 'YES'): bad['plain_wave_with_flag'] += 1
    if p['proposed_action'].startswith('ADD') and elig: bad['ADD_while_already_eligible'] += 1
    if p['proposed_action'] == 'ADD_IN_WAVE' and p['issue_codes']: bad['ADD_IN_WAVE_with_merchant_issue_code'] += 1
    if p['proposed_action'].startswith('KEEP_CURRENT') and p['availability'] == 'IN_STOCK' and not elig: bad['KEEP_CURRENT_in_stock_not_eligible'] += 1
    if p['proposed_action'] == 'ADD_IN_WAVE' and p['proposed_campaign'] in ('', 'NONE'): bad['ADD_without_campaign'] += 1
    if p['proposed_action'] == 'HOLD_ROLE_UNRESOLVED' and p['proposed_campaign'] not in ('', 'NONE'): bad['HOLD_with_campaign'] += 1
print('rule violations', dict(bad) or 'none')
# policy / data flags overview
print('policy reasons', C.Counter(p['policy_reason'] for p in P if p['policy_review_required'] == 'YES').most_common(12))
print('data reasons', C.Counter(p['data_reason'] for p in P if p['data_review_required'] == 'YES').most_common(12))

ins = [p for p in P if p['availability'] == 'IN_STOCK']
cnt = C.Counter(p['proposed_action'] for p in ins)
upper = cnt['KEEP_CURRENT'] + cnt['KEEP_CURRENT_POLICY_REVIEW'] + cnt['ADD_IN_WAVE'] + cnt['ADD_IN_WAVE_DATA_REVIEW']
print('upper bound (eligible now + plain/data waves)', upper, '| +policy-review', upper + cnt['ADD_AFTER_LABEL_POLICY_REVIEW'], '| +fix-first', upper + cnt['ADD_AFTER_LABEL_POLICY_REVIEW'] + cnt['ADD_TO_TREE_FIX_DATA_FIRST'])
print('wave1 by label0', C.Counter(p['label0'] for p in ins if p['proposed_action'] == 'ADD_IN_WAVE' and p['wave'] == '1').most_common(8))
print('HOLD_ROLE_UNRESOLVED label0', C.Counter(p['label0'] for p in P if p['proposed_action'] == 'HOLD_ROLE_UNRESOLVED').most_common(4))
print('107817', [(p['proposed_action'], p['policy_reason'], p['issue_codes']) for p in P if p['offer_id'] == '107817'])
