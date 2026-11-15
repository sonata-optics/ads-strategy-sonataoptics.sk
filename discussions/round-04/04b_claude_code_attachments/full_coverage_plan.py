#!/usr/bin/env python3
"""Full Merchant coverage plan (R4-CHATGPT-01 / R4-CLAUDE-02). No network, no live changes.

Input  : 04_chatgpt_attachments/catalog_coverage_2026-11-15.csv (ChatGPT read-only, Merchant 5831333799, 6078 rows;
         166 rows of another Merchant were already excluded by ChatGPT and stay outside the denominator),
         round-03 catalog_buckets.csv (heuristic weapon-optic flags + MC-1, 14.11), Merchant snapshot 14.11 (brand),
         02 package coverage_map.csv (26 pilot IDs).
Outputs: full_catalog_coverage_plan.csv (one row per composite ID), full_coverage_summary.csv (label x action).
Nothing here enables anything: every row is a PROPOSAL; policy and data flags block automatic inclusion.
"""
import csv, glob, json, os, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
SRC = os.path.join(REPO, 'discussions/round-04/04_chatgpt_attachments/catalog_coverage_2026-11-15.csv')
RO = os.path.join(REPO, 'discussions/round-04/04_chatgpt_attachments/read_only_checks.json')
BUCKETS = os.path.join(REPO, 'discussions/round-03/04_claude_attachments/catalog_buckets.csv')
PILOT = os.path.join(REPO, 'discussions/round-04/02_claude_code_attachments/coverage_map.csv')

EXISTING = {'ďalekohľady a binokuláre': '24440851881', 'termovízie': '24440851839', 'sonata junior lab': '24446149352',
            'teleskopy a hvezdárske ďalekohľady': '24451885423', 'mikroskopy': '24451886281'}
# proposed NEW Standard Shopping campaigns (created PAUSED, priority 0 like the rest unless decided otherwise)
NEW = {
    'NEW_SK_SHOP_Pozorovacia_optika': ['monokuláre', 'pozorovacie ďalekohľady - spektívy', 'diaľkomery', 'lupy', 'domáce planetáriá', 'kompasy a buzoly'],
    'NEW_SK_SHOP_Prislusenstvo_optika': ['príslušenstvo k ďalekohľadom', 'príslušenstvo pre binokulárne ďalekohľady', 'príslušenstvo k spektívom',
                                         'príslušenstvo k diaľkomerom', 'statívy', 'montáže a statívy'],
    'NEW_SK_SHOP_Astro_prislusenstvo': ['astronomické príslušenstvo', 'astronomické filtre', 'okuláre na teleskopy', 'astrofotografia'],
    'NEW_SK_SHOP_Mikroskopy_prislusenstvo': ['príslušenstvo pre mikroskopy'],
    'NEW_SK_SHOP_Meranie_meteo': ['meteostanice', 'meracie nástroje', 'refraktometre'],
    'NEW_SK_SHOP_Outdoor_tech': ['fotopasce', 'príslušenstvo pre fotopasce', 'príslušenstvo k fotopasciam', 'akčné kamery', 'drony', 'svietidlá'],
    'NEW_SK_SHOP_Nocne_videnie_POLICY_HOLD': ['nočné videnie', 'príslušenstvo pre nočné videnie', 'príslušenstvo k termovíziám'],
}
LABEL_TO_NEW = {l: c for c, ls in NEW.items() for l in ls}
# label-level policy review: products that can be weapon-mounted or weapon-adjacent (Google weapons/parts policy).
POLICY_LABELS = {'nočné videnie': 'night vision: some devices are weapon-mountable',
                 'príslušenstvo pre nočné videnie': '107671 here has guns_parts_policy_violation',
                 'príslušenstvo k termovíziám': 'thermal accessories may include weapon mounts/adapters',
                 'svietidlá': 'flashlights may include weapon lights/mounts',
                 'diaľkomery': 'hunting rangefinders: usually allowed, check weapon-mount variants'}
UNRESOLVED_LABELS = {'bresser.de': 'label is a supplier/source tag, not a product role',
                     'iné': 'generic "other" label', 'knihy, mapy, postery': 'role not decided (0 in stock)'}
POLICY_CODES = {'guns_parts_policy_violation', 'hacking_policy_violation', 'healthcare_pdt_policy_violation'}
DATA_CODES = {'image_unwanted_overlays', 'image_decoding_error', 'image_link_broken', 'image_link_pending_crawl', 'landing_page_error'}
WAVE = {'NEW_SK_SHOP_Pozorovacia_optika': 1, 'NEW_SK_SHOP_Prislusenstvo_optika': 1, 'NEW_SK_SHOP_Astro_prislusenstvo': 1,
        'NEW_SK_SHOP_Mikroskopy_prislusenstvo': 1, 'NEW_SK_SHOP_Meranie_meteo': 2, 'NEW_SK_SHOP_Outdoor_tech': 2,
        'NEW_SK_SHOP_Nocne_videnie_POLICY_HOLD': 3}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    with open(SRC, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    ro = json.load(open(RO, encoding='utf-8'))
    heur, mc1 = {}, set()
    with open(BUCKETS, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['offer_id']:
                if r['weapon_candidate_heuristic'] == 'True':
                    heur[r['offer_id']] = r['candidate_role'] or 'heuristic weapon-optic candidate'
                if r['policy_review'] == 'True':
                    mc1.add(r['offer_id'])
    brand = {}
    for p in sorted(glob.glob(os.path.join(REPO, 'data/catalog/2026-11-14/merchant-*.json'))):
        for m in json.load(open(p, encoding='utf-8')):
            brand[m['offerId']] = (m.get('brand') or '').strip()
    pilot = {r['offer_id'] for r in csv.DictReader(open(PILOT, encoding='utf-8')) if r['offer_id']}

    out = []
    for r in rows:
        cid = '~'.join(r[k] for k in ('merchant_id', 'channel', 'language', 'feed_label', 'offer_id'))
        codes = [c for c in r['account_issue_codes'].split(';') if c]
        lab, av, st = r['label0'], r['availability'], r['account_status']
        in_stock = av == 'IN_STOCK'
        scoped = r['scoped_campaign_statuses']
        eligible = r['eligible_campaign_ids']
        # ---- current state (fact)
        if st.startswith('ELIGIBLE'):
            cur = 'COVERED_ELIGIBLE'
        elif 'not_eligible_in_any_campaign' in codes:
            cur = 'IN_STOCK_NO_CAMPAIGN' if in_stock else 'OOS_NO_CAMPAIGN'
        elif in_stock:
            cur = 'IN_STOCK_OTHER_BLOCK'
        else:
            cur = 'OOS_IN_SCOPE' if scoped else 'OOS_OTHER'
        # ---- flags
        pol = []
        pol += [c for c in codes if c in POLICY_CODES]
        if lab in POLICY_LABELS:
            pol.append('label: ' + POLICY_LABELS[lab])
        if r['offer_id'] in heur:
            pol.append('heuristic 14.11: ' + heur[r['offer_id']])
        if r['offer_id'] in mc1:
            pol.append('MC-1 policy review list')
        dat = []
        dat += [c for c in codes if c in DATA_CODES]
        if lab in UNRESOLVED_LABELS:
            dat.append('label: ' + UNRESOLVED_LABELS[lab])
        if r['offer_id'] not in brand:
            dat.append('not in 14.11 snapshot (new offer): brand/title unchecked')
        elif not brand[r['offer_id']]:
            dat.append('brand empty in 14.11 snapshot')
        if not lab:
            dat.append('label0 empty')
        # ---- proposal
        if lab in EXISTING:
            camp = EXISTING[lab]
        elif lab in LABEL_TO_NEW:
            camp = LABEL_TO_NEW[lab]
        else:
            camp = 'NONE_UNTIL_ROLE_DECIDED'
        hard_policy = any(c in POLICY_CODES for c in codes) or r['offer_id'] in heur or r['offer_id'] in mc1
        if cur == 'COVERED_ELIGIBLE':
            action = 'KEEP_CURRENT_POLICY_REVIEW' if hard_policy else 'KEEP_CURRENT'
            wave = 0
        elif camp == 'NONE_UNTIL_ROLE_DECIDED':
            action, wave = 'HOLD_ROLE_UNRESOLVED', None
        elif hard_policy:
            action, wave = 'EXCLUDE_PENDING_POLICY_REVIEW', None
        elif lab in POLICY_LABELS or camp.endswith('POLICY_HOLD'):
            action, wave = 'ADD_AFTER_LABEL_POLICY_REVIEW', 3 if camp.endswith('POLICY_HOLD') else WAVE.get(camp)
        elif cur in ('IN_STOCK_OTHER_BLOCK',) or any(c in DATA_CODES for c in codes):
            action = 'FIX_DATA_KEEP_IN_TREE' if lab in EXISTING else 'ADD_TO_TREE_FIX_DATA_FIRST'
            wave = 0 if lab in EXISTING else WAVE.get(camp)
        elif lab in EXISTING:
            action, wave = 'KEEP_CURRENT_SCOPE', 0          # OOS rows already inside an existing scope
        else:
            action, wave = 'ADD_IN_WAVE', WAVE.get(camp)
        if action.startswith('ADD') and dat and not any(c in DATA_CODES for c in codes) and action == 'ADD_IN_WAVE':
            action = 'ADD_IN_WAVE_DATA_REVIEW'
        if action in ('ADD_IN_WAVE', 'ADD_IN_WAVE_DATA_REVIEW', 'ADD_TO_TREE_FIX_DATA_FIRST', 'ADD_AFTER_LABEL_POLICY_REVIEW'):
            acc_pre = (f'Static (campaign PAUSED): shopping_product(campaign={camp}) returns this ID; status ELIGIBLE if IN_STOCK and no other issue, '
                       'else the remaining reason is not in_any_campaign; excluded IDs absent')
            acc_post = 'After owner-approved enable: impressions per item_id in shopping_performance_view; 0 = diagnose (demand/rank/budget), unknown = UNKNOWN not 0'
            rb = 'Pause the new campaign/ad group; item returns to not_eligible_in_any_campaign (no previous ad: rollback = zero coverage)'
        elif action.startswith('KEEP') or action == 'FIX_DATA_KEEP_IN_TREE':
            acc_pre = 'Unchanged: same status as 15.11 in its campaign before and after other waves'
            acc_post = 'Not affected by new campaigns (different label0 scope)'
            rb = 'Nothing to roll back'
        else:
            acc_pre, acc_post, rb = 'Not added', 'Not applicable', 'Not applicable'
        unresolved = []
        if action == 'EXCLUDE_PENDING_POLICY_REVIEW':
            unresolved.append('policy decision (owner + Google policy check)')
        if action == 'HOLD_ROLE_UNRESOLVED':
            unresolved.append('product role/category for this label')
        if action == 'ADD_AFTER_LABEL_POLICY_REVIEW':
            unresolved.append('label-level policy review')
        if 'DATA' in action or action == 'FIX_DATA_KEEP_IN_TREE':
            unresolved.append('data fix: ' + ','.join(c for c in codes if c in DATA_CODES) if any(c in DATA_CODES for c in codes) else 'brand/label data review')
        if action == 'KEEP_CURRENT_POLICY_REVIEW':
            unresolved.append('currently ELIGIBLE but on policy review list: owner decision (no change proposed here)')
        out.append(dict(composite_id=cid, merchant_id=r['merchant_id'], offer_id=r['offer_id'], label0=lab, availability=av,
                        account_status=st, issue_codes=';'.join(codes), current_state=cur,
                        current_eligible_campaigns=eligible or 'NONE', current_scoped_statuses=scoped or 'NONE',
                        proposed_campaign=camp, proposed_ad_group=f'LABEL::{lab}' if camp.startswith('NEW') else ('existing tree' if lab in EXISTING else 'NONE'),
                        proposed_action=action, wave='' if wave is None else wave,
                        policy_review_required='YES' if pol else 'NO', policy_reason=' | '.join(pol),
                        data_review_required='YES' if dat else 'NO', data_reason=' | '.join(dat),
                        pilot_26_member='YES' if r['offer_id'] in pilot else 'NO',
                        basis='ChatGPT read-only shopping_product 2026-11-15; flags: issue codes 15.11, heuristics/brand 14.11',
                        acceptance_pre_launch=acc_pre, acceptance_post_launch=acc_post, rollback=rb,
                        unresolved=' | '.join(unresolved), status='PROPOSAL_NOT_APPLIED'))

    with open(os.path.join(HERE, 'full_catalog_coverage_plan.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
    summ = defaultdict(Counter)
    for o in out:
        summ[(o['label0'], o['proposed_campaign'])][o['proposed_action'] + ('|IN' if o['availability'] == 'IN_STOCK' else '|OOS')] += 1
    acts = sorted({k for c in summ.values() for k in c})
    with open(os.path.join(HERE, 'full_coverage_summary.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['label0', 'proposed_campaign'] + acts)
        for (l, c), cnt in sorted(summ.items(), key=lambda x: -sum(x[1].values())):
            w.writerow([l, c] + [cnt.get(a, 0) for a in acts])

    # ---- checks printed for the log
    T = ro['totals']
    ins = [o for o in out if o['availability'] == 'IN_STOCK']
    cs = Counter(o['current_state'] for o in ins)
    print('rows', len(out), 'unique composite', len({o['composite_id'] for o in out}), 'merchants', Counter(o['merchant_id'] for o in out))
    print('in stock', len(ins), dict(cs))
    assert len(out) == T['total'] == 6078 and len(ins) == T['inStock'] == 4269
    assert cs['COVERED_ELIGIBLE'] == T['eligibleInStock'] == 1886
    assert cs['IN_STOCK_NO_CAMPAIGN'] == T['inStockNoCampaign'] == 2376
    assert cs['IN_STOCK_OTHER_BLOCK'] == T['inStockOtherBlock'] == 7
    assert 1886 + 2376 + 7 == 4269
    print('other Merchant rows excluded (per ChatGPT JSON):', ro['otherMerchantRowsExcluded'])
    gap = [o for o in ins if o['current_state'] == 'IN_STOCK_NO_CAMPAIGN']
    print('2376 gap by action', Counter(o['proposed_action'] for o in gap))
    print('2376 gap by wave', Counter(o['wave'] for o in gap))
    print('2376 gap policy flag', Counter(o['policy_review_required'] for o in gap), 'data flag', Counter(o['data_review_required'] for o in gap))
    auto = [o for o in gap if o['proposed_action'] == 'ADD_IN_WAVE']
    print('gap rows with no policy and no data flag (ADD_IN_WAVE):', len(auto))
    print('in-stock potentially routed after waves 1-2 (eligibility upper bound, not impressions):',
          1886 + sum(1 for o in gap if o['proposed_action'] in ('ADD_IN_WAVE', 'ADD_IN_WAVE_DATA_REVIEW') and o['wave'] in (1, 2)))
    print('pilot members', sum(o['pilot_26_member'] == 'YES' for o in out), Counter(o['proposed_action'] for o in out if o['pilot_26_member'] == 'YES'))
    print('eligible in-stock with policy flag', [(o['offer_id'], o['label0']) for o in ins if o['proposed_action'] == 'KEEP_CURRENT_POLICY_REVIEW'][:15],
          sum(o['proposed_action'] == 'KEEP_CURRENT_POLICY_REVIEW' for o in ins))


if __name__ == '__main__':
    main()
