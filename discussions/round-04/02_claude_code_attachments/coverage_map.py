#!/usr/bin/env python3
"""Round-4 coverage map: 32 source rows = 26 Merchant offerIds + 6 site-only URLs.

Inputs (repository files only, no network):
  ../../round-03/04_claude_attachments/control_sku_variants.csv   (32 rows, Cowork r3, snapshot 14.11)
  ../../round-03/05_chatgpt_attachments/live_checks_2026-11-15.json (ChatGPT read-only snapshot)
  inputs/live_recheck_2026-11-15_claude_code.json                  (Claude Code read-only recheck)
  ../../../data/catalog/2026-11-14/merchant-*.json, assortment-*.json
Output: coverage_map.csv

Rules enforced in code:
  * FACT columns come only from snapshots; PROJECT columns are proposals.
  * Several campaign rows of one offerId are kept (joined, never overwritten).
  * Unknown stays UNKNOWN; a 14.11 snapshot value is never labelled live.
  * 26130 / 26131 stay monocular (label monokuláre); no binocular relabel.
  * site-only = absent from our 14.11 Merchant snapshot, nothing more.
"""
import csv, glob, json, os, sys
from collections import defaultdict, OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
VARIANTS = os.path.join(REPO, 'discussions/round-03/04_claude_attachments/control_sku_variants.csv')
LIVE_CG = os.path.join(REPO, 'discussions/round-03/05_chatgpt_attachments/live_checks_2026-11-15.json')
LIVE_CC = os.path.join(HERE, 'inputs/live_recheck_2026-11-15_claude_code.json')
CAT = os.path.join(REPO, 'data/catalog/2026-11-14')

PILOT_CAMPAIGN = 'SK_SHOP_Models_Pilot (PROPOSAL, not created)'
FAMILY_SHORT = {'leica trinovid 10x42 hd': 'TRINOVID', 'levenhuk vegas ed 10x42': 'VEGAS',
                'skywatcher explorer-150pds eq3': 'EXPLORER150'}


def load_json_pages(pattern):
    out = []
    for p in sorted(glob.glob(os.path.join(CAT, pattern))):
        with open(p, encoding='utf-8') as f:
            d = json.load(f)
        out.extend(d if isinstance(d, list) else d.get('items', []))
    return out


def product_type(title, note):
    t = (title + ' ' + note).lower()
    if 'monokul' in t or 'monocular' in t:
        return 'monocular'
    if 'teleskop' in t or 'reflektor' in t or 'newton' in t or 'minidobson' in t:
        return 'telescope'
    return 'binocular'


def main(out_path):
    with open(VARIANTS, encoding='utf-8') as f:
        src = list(csv.DictReader(f))
    with open(LIVE_CG, encoding='utf-8') as f:
        cg = json.load(f)
    with open(LIVE_CC, encoding='utf-8') as f:
        cc = json.load(f)

    merchant = {m['offerId']: m for m in load_json_pages('merchant-*.json')}
    assortment_urls = {a.get('url') or a.get('loc') or a.get('link') for a in load_json_pages('assortment-*.json')}
    merchant_links = {m.get('link') for m in merchant.values()}

    # ChatGPT snapshot: keep ALL campaign rows per offerId (do not overwrite on join)
    cg_rows = defaultdict(list)
    for p in cg['products']:
        cg_rows[p['offer_id']].append(p)
    cg_label = {l['offer_id']: l['label0'] for l in cg['labels']}
    scope = {s['campaign']: s['dimensions'][0]['productCustomAttribute']['value'] for s in cg['scopes']}

    # Claude Code recheck: campaign memberships per offerId (may be several)
    cc_label = {}
    for key, ids in cc['account_level']['custom_attribute0'].items():
        for i in ids:
            cc_label[i] = cc['account_level']['label_values_verbatim'][key]
    cc_oos = set(cc['account_level']['out_of_stock'])
    cc_campaigns = defaultdict(list)
    for camp, info in cc['per_campaign'].items():
        for i in info.get('eligible', []):
            cc_campaigns[i].append(f'{camp}:ELIGIBLE')
        for i, why in info.get('not_eligible', {}).items():
            cc_campaigns[i].append(f'{camp}:NOT_ELIGIBLE({why})')
        if info.get('all_status') == 'NOT_ELIGIBLE':
            why = 'excluded_listing_group+campaign_ended' if info.get('issues_sample') else 'reason NOT_FETCHED'
            for i in cc['account_level']['custom_attribute0'].values():
                for x in i:
                    cc_campaigns[x].append(f'{camp}:NOT_ELIGIBLE({why})')

    rows = []
    for n, r in enumerate(src, 1):
        oid = (r['offer_id'] or '').strip()
        fam = FAMILY_SHORT[r['query_family']]
        ptype = product_type(r['title'], r['variant_note'])
        row = OrderedDict()
        row['row_no'] = n
        row['row_kind'] = 'merchant_offer' if oid else 'site_only_url'
        row['query_family'] = r['query_family']
        row['offer_id'] = oid or ''
        row['role_r3'] = r['role']
        row['product_type'] = ptype
        row['title_snapshot'] = r['title']
        row['url'] = r['url']
        row['price_eur_snapshot_2026_11_14'] = r['price_eur_with_vat'] or 'UNKNOWN'
        row['src_variants'] = 'round-03/04_claude_attachments/control_sku_variants.csv (Merchant snapshot 2026-11-14)'
        # --- FACT: 14.11 snapshot
        if oid:
            m = merchant.get(oid)
            row['fact_merchant_snapshot_2026_11_14'] = 'PRESENT' if m else 'ABSENT'
            row['fact_availability_2026_11_14'] = m['availability'] if m else 'UNKNOWN'
            row['fact_feed_label_2026_11_14'] = m.get('feedLabel', 'UNKNOWN') if m else 'UNKNOWN'
        else:
            row['fact_merchant_snapshot_2026_11_14'] = 'ABSENT_URL' if r['url'] not in merchant_links else 'PRESENT_URL'
            row['fact_availability_2026_11_14'] = 'UNKNOWN'
            row['fact_feed_label_2026_11_14'] = 'UNKNOWN'
        row['fact_in_site_sitemap_2026_11_14'] = 'YES' if r['url'] in assortment_urls else 'NOT_FOUND_IN_SNAPSHOT'
        # --- FACT: ChatGPT live 15.11
        if oid and cg_rows.get(oid):
            ps = cg_rows[oid]
            row['fact_cg_2026_11_15_campaign_rows'] = ' | '.join(
                f"{p['campaign']}:{p['availability']}:{p['status']}" + (f"({','.join(p['issues'])})" if p['issues'] else '') for p in ps)
            row['fact_cg_2026_11_15_n_rows'] = len(ps)
        else:
            row['fact_cg_2026_11_15_campaign_rows'] = 'NOT_IN_SNAPSHOT' if oid else 'NOT_APPLICABLE_NO_OFFER_ID'
            row['fact_cg_2026_11_15_n_rows'] = 0
        row['fact_label0_cg_2026_11_15'] = cg_label.get(oid, 'UNKNOWN') if oid else 'NOT_APPLICABLE'
        # --- FACT: Claude Code recheck 15.11
        if oid:
            row['fact_cc_2026_11_15_label0'] = cc_label.get(oid, 'UNKNOWN')
            row['fact_cc_2026_11_15_availability'] = ('OUT_OF_STOCK' if oid in cc_oos else 'IN_STOCK') if oid in cc_label else 'UNKNOWN'
            row['fact_cc_2026_11_15_campaigns'] = ' | '.join(cc_campaigns.get(oid, [])) or 'NONE_RETURNED'
        else:
            row['fact_cc_2026_11_15_label0'] = 'NOT_APPLICABLE'
            row['fact_cc_2026_11_15_availability'] = 'UNKNOWN'
            row['fact_cc_2026_11_15_campaigns'] = 'NOT_APPLICABLE_NO_OFFER_ID'
        # --- current campaign / filter (fact)
        if oid:
            elig = [c.split(':')[0] for c in cc_campaigns.get(oid, []) if c.endswith(':ELIGIBLE')]
            served_by = [c.split(':')[0] for c in cc_campaigns.get(oid, []) if not c.split(':', 1)[1].startswith('NOT_ELIGIBLE(excluded') and not c.split(':', 1)[1].startswith('NOT_ELIGIBLE(reason')]
            if served_by:
                c = served_by[0]
                row['current_campaign_filter'] = f"{c} priority=0 MANUAL_CPC; campaign scope custom_label_0='{scope.get(c, 'NONE')}'"
            else:
                row['current_campaign_filter'] = 'NONE: no ENABLED Shopping campaign includes this item (not_eligible_in_any_campaign)'
            row['current_eligible_campaigns'] = ';'.join(elig) or 'NONE'
        else:
            row['current_campaign_filter'] = 'NOT_APPLICABLE: no offerId in snapshot'
            row['current_eligible_campaigns'] = 'NOT_APPLICABLE'
        # --- status + reason (fact-based classification)
        live_av = row['fact_cc_2026_11_15_availability']
        if not oid:
            st, why = 'SITE_ONLY_UNKNOWN', 'URL not in Merchant snapshot 14.11; current Merchant/CS-Cart export state NOT CHECKED. Not proof of a CS-Cart error.'
        elif 'not_eligible_in_any_campaign' in row['fact_cg_2026_11_15_campaign_rows'] and live_av == 'IN_STOCK':
            st, why = 'GAP_IN_STOCK_NO_CAMPAIGN', "label0='monokuláre' matches no campaign scope; old unscoped campaigns exclude it. Coverage gap, not a policy violation."
        elif 'not_eligible_in_any_campaign' in row['fact_cg_2026_11_15_campaign_rows']:
            st, why = 'GAP_OOS_AND_NO_CAMPAIGN', 'OUT_OF_STOCK and no campaign; would stay not eligible even after stock returns'
        elif live_av == 'OUT_OF_STOCK':
            st, why = 'NOT_ELIGIBLE_OOS', 'In campaign scope, OUT_OF_STOCK in Merchant (truthful); returns when IN_STOCK'
        elif row['current_eligible_campaigns'] not in ('', 'NONE'):
            st, why = 'COVERED_ELIGIBLE', 'ELIGIBLE in one campaign; eligibility != impressions/auction wins'
        else:
            st, why = 'UNKNOWN', 'no data'
        row['coverage_status'] = st
        row['status_reason'] = why
        # --- PROJECT (proposal only)
        if oid:
            row['project_route'] = 'PROPOSAL: pilot item_id allowlist'
            row['project_campaign'] = PILOT_CAMPAIGN
            row['project_ad_group'] = f'SHOP_{fam}_{oid}'
            row['project_listing_tree'] = f'item_id={oid} INCLUDED; everything else EXCLUDED'
            if ptype == 'monocular':
                row['project_label_rule'] = "keep label0='monokuláre' (truthful). Do NOT relabel as binocular. Route by item_id, label-independent."
            else:
                row['project_label_rule'] = 'no label change needed for pilot (item_id based)'
            row['project_old_campaign_change'] = 'NONE in pilot phase (old scopes untouched; separate decision with evidence)'
            if st == 'GAP_IN_STOCK_NO_CAMPAIGN':
                row['acceptance_pre_launch'] = 'Static: pilot shopping_product(campaign=pilot) returns 26130 with status ELIGIBLE or reason other than in_any_campaign; tree has exactly one INCLUDED leaf'
                row['acceptance_post_launch'] = 'After owner-approved launch: shopping_performance_view impressions for 26130 in pilot; 0 impressions = investigate (demand/rank/budget), not fail'
                row['rollback'] = 'Pause pilot ad group / campaign'
                row['rollback_boundary'] = 'NO previous ad: rollback returns 26130 to not_eligible_in_any_campaign (zero coverage). There is nothing to restore; pausing removes the only route.'
            elif st in ('NOT_ELIGIBLE_OOS', 'GAP_OOS_AND_NO_CAMPAIGN'):
                row['acceptance_pre_launch'] = 'Static: item in pilot tree; expected NOT_ELIGIBLE(out_of_stock) while OOS — this is a PASS, not a defect'
                row['acceptance_post_launch'] = 'When Merchant shows IN_STOCK: becomes ELIGIBLE in pilot without any enable by sync (tree already includes it)'
                row['rollback'] = 'Pause pilot ad group'
                row['rollback_boundary'] = ('No previous ad either (26131 not in any campaign)' if st == 'GAP_OOS_AND_NO_CAMPAIGN'
                                            else 'Old campaign 24451885423 still includes it; restores old route only')
            else:
                row['acceptance_pre_launch'] = 'Static: pilot shopping_product(campaign=pilot) ELIGIBLE; old campaign still ELIGIBLE (overlap expected)'
                row['acceptance_post_launch'] = 'After owner-approved launch: impressions attributed to pilot campaign for this item_id; old campaign share falls only by priority, not by exclusion'
                row['rollback'] = 'Pause pilot ad group/campaign; old campaign unchanged so its route resumes'
                row['rollback_boundary'] = 'Restores settings, not guaranteed immediate impressions (auction, budget, learning)'
        else:
            row['project_route'] = 'NO SHOPPING ROUTE POSSIBLE until an offerId exists'
            row['project_campaign'] = 'NONE'
            row['project_ad_group'] = 'NONE'
            row['project_listing_tree'] = 'NONE'
            row['project_label_rule'] = 'NOT_APPLICABLE'
            row['project_old_campaign_change'] = 'NONE'
            row['acceptance_pre_launch'] = 'Data task: export CS-Cart product status/feed flag + current Merchant lookup by URL; classify as sellable/disabled/duplicate/excluded'
            row['acceptance_post_launch'] = 'NOT_APPLICABLE'
            row['rollback'] = 'NOT_APPLICABLE (no change)'
            row['rollback_boundary'] = 'NOT_APPLICABLE'
        row['open_issue_ids'] = ';'.join(x for x in [
            'R3-CHATGPT-06' if ptype == 'monocular' else '',
            'R3-CHATGPT-09' if oid else '',
            'R3-CHATGPT-10' if oid else '',
            'R3-CLAUDE-09' if fam == 'VEGAS' else ''] if x)
        rows.append(row)

    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    by = defaultdict(int)
    for r in rows:
        by[r['coverage_status']] += 1
    print('rows', len(rows), dict(by))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'coverage_map.csv'))
