#!/usr/bin/env python3
"""Catalogue refresh 25.11.2026 after the owner's category migration (bresser.de removed, categories re-assigned).

Read-only inputs (no network):
  inputs/shopping_product_2026-11-25.csv   Claude Code read-only GAQL export 25.11 (all Merchants of the Ads account)
  inputs/campaigns_2026-11-25.json         campaign status/end date/priority + listing scopes 25.11
  ../04_chatgpt_attachments/catalog_coverage_2026-11-15.csv  previous snapshot (ChatGPT, 15.11)
Outputs (all PROPOSALS, nothing applied):
  category_reconciliation.csv     one row per composite ID present on 15.11 or 25.11: old/new label, availability, status, change type
  label_transitions.csv           old label -> new label counts for IDs present on both dates
  coverage_by_label_2026-11-25.csv
  label_contract.csv              every label0 seen on 25.11 -> project route; unknown label = CONTRACT_FAIL
  full_catalog_coverage_plan_2026-11-25.csv + full_coverage_summary_2026-11-25.csv
Admission model (ChatGPT 04c decision on R4-CLAUDECODE-07): risky roles only by VERIFIED item_id; other labels by category
+ explicit ads_review_ok. No review register exists yet -> ads_review_ok = NOT_REVIEWED for every gap row, so the
generated allowlist (allowlist_generated.csv) is EMPTY by design until reviews are recorded. Any *_policy_violation code is a
hard project hold regardless of availability, role or wave (R4-CLAUDE-11).
"""
import csv, json, os, re, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
R4 = os.path.normpath(os.path.join(HERE, '..'))
NEW_CSV = os.path.join(HERE, 'inputs/shopping_product_2026-11-25.csv')
CAMP_JSON = os.path.join(HERE, 'inputs/campaigns_2026-11-25.json')
OLD_CSV = os.path.join(R4, '04_chatgpt_attachments/catalog_coverage_2026-11-15.csv')
PILOT_CSV = os.path.join(R4, '02_claude_code_attachments/coverage_map.csv')
SONATA_MERCHANT = '5831333799'

# label0 -> project route. Existing scoped campaigns come from the 25.11 listing scopes (see campaigns JSON).
NEW = {
    'NEW_SK_SHOP_Pozorovacia_optika': ['monokuláre', 'spektívy', 'lupy', 'domáce planetáriá', 'kompasy a buzoly', 'diaľkomery'],
    'NEW_SK_SHOP_Prislusenstvo_optika': ['príslušenstvo k ďalekohľadom', 'príslušenstvo k spektívom', 'statívy', 'montáže a statívy',
                                         'nástroje na čistenie optiky'],
    'NEW_SK_SHOP_Astro_prislusenstvo': ['astronomické príslušenstvo', 'astronomické filtre', 'okuláre na teleskopy', 'astrofotografia'],
    'NEW_SK_SHOP_Mikroskopy_prislusenstvo': ['príslušenstvo pre mikroskopy'],
    'NEW_SK_SHOP_Meranie_veda': ['meteostanice', 'meracie nástroje', 'refraktometre', 'spektroskopy', 'polarimetre', 'príslušenstvo pre polarimetre'],
    'NEW_SK_SHOP_Outdoor_tech': ['fotopasce', 'príslušenstvo pre fotopasce', 'akčné kamery', 'drony'],
    'NEW_SK_SHOP_Nocne_videnie_VERIFIED_ONLY': ['nočné videnie', 'príslušenstvo pre nočné videnie', 'príslušenstvo k termovíziám'],
}
WAVE = {'NEW_SK_SHOP_Pozorovacia_optika': 1, 'NEW_SK_SHOP_Prislusenstvo_optika': 1, 'NEW_SK_SHOP_Astro_prislusenstvo': 1,
        'NEW_SK_SHOP_Mikroskopy_prislusenstvo': 1, 'NEW_SK_SHOP_Meranie_veda': 2, 'NEW_SK_SHOP_Outdoor_tech': 2,
        'NEW_SK_SHOP_Nocne_videnie_VERIFIED_ONLY': 3}
RISKY_LABELS = {'nočné videnie': 'night vision: some devices are weapon-mountable',
                'príslušenstvo pre nočné videnie': 'accessories incl. weapon-mount parts (107671 guns_parts)',
                'príslušenstvo k termovíziám': 'thermal accessories may include weapon mounts/adapters',
                'diaľkomery': 'hunting rangefinders: check weapon-mount variants',
                'termovízie': 'thermal: existing scoped campaign; 107817 on MC-1 list'}
ROLE_UNDECIDED = {'knihy, mapy, postery': 'role not decided'}
# title heuristics (word-start anchored). HARD = clearly weapon-related wording; SOFT = ambiguous, needs a human look.
HARD_RX = re.compile(r'(?<![\w])(zbra[nň]\w*|pušk\w*|pusk\w*|puškohľad\w*|picatinny|weaver|tlmi[čc]\w*|clip[- ]?on|predsádk\w*|úchyt\w* na zbra\w*|na pušku|rifle|weapon)', re.I)
SOFT_RX = re.compile(r'(?<![\w])(zameriava\w*|red ?dot|kolimátor\w*|lovec\w*|poľovn\w*|balistick\w*|kalib(?!r)\w*)', re.I)


def policy_codes(codes):
    return [c for c in codes if c.endswith('_policy_violation')]


def load():
    with open(NEW_CSV, encoding='utf-8') as f:
        allrows = list(csv.DictReader(f))
    with open(OLD_CSV, encoding='utf-8') as f:
        old = {r['offer_id']: r for r in csv.DictReader(f)}
    camps = json.load(open(CAMP_JSON, encoding='utf-8'))
    pilot = {r['offer_id'] for r in csv.DictReader(open(PILOT_CSV, encoding='utf-8')) if r['offer_id']}
    return allrows, old, camps, pilot


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    allrows, old, camps, pilot = load()
    other = [r for r in allrows if r['merchant_id'] != SONATA_MERCHANT]
    rows = [r for r in allrows if r['merchant_id'] == SONATA_MERCHANT]
    new = {r['offer_id']: r for r in rows}
    scope = {s['campaign_id']: s['label0'] for s in camps['listing_scopes']}
    cstat = {c['id']: c for c in camps['campaigns']}
    serving_scoped = {lab: cid for cid, lab in scope.items() if cstat[cid]['status'] == 'ENABLED' and cstat[cid]['serving_status'] == 'SERVING'}
    paused_scoped = {lab: cid for cid, lab in scope.items() if lab not in serving_scoped}

    # ---------- 1. reconciliation 15.11 -> 25.11 by stable offer ID (all on merchant 5831333799 / ONLINE / sk / SK)
    rec = []
    for oid in sorted(set(old) | set(new), key=lambda x: (len(x), x)):
        o, n = old.get(oid), new.get(oid)
        if o and n:
            ct = 'LABEL_CHANGED' if o['label0'] != n['label0'] else 'UNCHANGED_LABEL'
        elif n:
            ct = 'NEW_ID'
        else:
            ct = 'REMOVED_ID'
        rec.append(dict(offer_id=oid, change_type=ct, label0_2026_11_15=o['label0'] if o else '', label0_2026_11_25=n['label0'] if n else '',
                        availability_2026_11_15=o['availability'] if o else '', availability_2026_11_25=n['availability'] if n else '',
                        status_2026_11_15=o['account_status'] if o else '', status_2026_11_25=n['account_status'] if n else '',
                        title_2026_11_25=n['title'] if n else '',
                        from_temporary_bresser_de='YES' if o and o['label0'] == 'bresser.de' else 'NO'))
    with open(os.path.join(HERE, 'category_reconciliation.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rec[0].keys())); w.writeheader(); w.writerows(rec)
    tr = Counter((r['label0_2026_11_15'], r['label0_2026_11_25']) for r in rec if r['change_type'] == 'LABEL_CHANGED')
    with open(os.path.join(HERE, 'label_transitions.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['label0_2026_11_15', 'label0_2026_11_25', 'ids'])
        for (a, b), v in tr.most_common():
            w.writerow([a, b, v])

    # ---------- 2. label contract
    labels = Counter(r['label0'] for r in rows)
    lab2new = {l: c for c, ls in NEW.items() for l in ls}
    contract = []
    for lab, n in labels.most_common():
        if lab in serving_scoped:
            route, st = f'EXISTING {serving_scoped[lab]} (ENABLED, SERVING)', 'OK'
        elif lab in paused_scoped:
            cid = paused_scoped[lab]
            route, st = f'EXISTING {cid} ({cstat[cid]["status"]}) - owner decision to resume', 'OK_PAUSED_CAMPAIGN'
        elif lab in lab2new:
            route, st = lab2new[lab], 'OK'
        elif lab in ROLE_UNDECIDED:
            route, st = 'NONE_UNTIL_ROLE_DECIDED', 'OK_UNDECIDED'
        else:
            route, st = 'UNMAPPED', 'CONTRACT_FAIL'
        contract.append(dict(label0=lab, products=n, in_stock=sum(1 for r in rows if r['label0'] == lab and r['availability'] == 'IN_STOCK'),
                             route=route, risky_label='YES' if lab in RISKY_LABELS else 'NO', contract_status=st))
    with open(os.path.join(HERE, 'label_contract.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(contract[0].keys())); w.writeheader(); w.writerows(contract)

    # ---------- 3. coverage by label + plan
    plan = []
    for r in rows:
        codes = [c for c in r['issue_codes'].split(';') if c]
        lab, av, st = r['label0'], r['availability'], r['account_status']
        in_stock = av == 'IN_STOCK'
        pol = policy_codes(codes)
        if st.startswith('ELIGIBLE'):
            cur = 'COVERED_ELIGIBLE'
        elif 'not_eligible_in_any_campaign' in codes:
            cur = 'IN_STOCK_NO_CAMPAIGN' if in_stock else 'OOS_NO_CAMPAIGN'
        else:
            cur = 'IN_STOCK_OTHER_BLOCK' if in_stock else 'OOS_OTHER'
        hard = HARD_RX.search(r['title']); soft = SOFT_RX.search(r['title'])
        o = old.get(r['offer_id'])
        changed = 'NEW_ID' if not o else ('LABEL_CHANGED' if o['label0'] != lab else 'UNCHANGED')
        risky = lab in RISKY_LABELS or bool(pol) or bool(hard) or bool(soft)
        admission = 'VERIFIED_ID' if risky else 'CATEGORY_PLUS_ADS_REVIEW_OK'
        if lab in serving_scoped:
            camp = serving_scoped[lab]
        elif lab in paused_scoped:
            camp = paused_scoped[lab] + '_PAUSED'
        elif lab in lab2new:
            camp = lab2new[lab]
        else:
            camp = 'NONE_UNTIL_ROLE_DECIDED'
        # ---- proposed action (project only)
        if pol:
            action = 'POLICY_HOLD'                       # hard hold, also for OOS and already-eligible rows
        elif cur == 'COVERED_ELIGIBLE':
            action = 'KEEP_CURRENT_VERIFY_ID' if risky else 'KEEP_CURRENT'
        elif camp == 'NONE_UNTIL_ROLE_DECIDED':
            action = 'HOLD_ROLE_UNDECIDED'
        elif camp.endswith('_PAUSED'):
            action = 'OWNER_DECISION_RESUME_CAMPAIGN'
        elif lab in serving_scoped:
            action = 'KEEP_IN_SCOPE_FIX_DATA' if cur == 'IN_STOCK_OTHER_BLOCK' else 'KEEP_IN_SCOPE'
        else:
            action = 'CANDIDATE_PENDING_REVIEW'          # enters allowlist only after ads_review_ok / verified ID
        wave = WAVE.get(camp, '') if action == 'CANDIDATE_PENDING_REVIEW' else ''
        plan.append(dict(composite_id='~'.join([r['merchant_id'], r['channel'], r['language'], r['feed_label'], r['offer_id']]),
                         offer_id=r['offer_id'], title=r['title'], brand=r['brand'], label0=lab, availability=av,
                         account_status=st, issue_codes=';'.join(codes), current_state=cur, change_since_2026_11_15=changed,
                         label0_2026_11_15=o['label0'] if o else '',
                         proposed_campaign=camp, proposed_action=action, wave=wave, admission_mode=admission,
                         ads_review_ok='NOT_REVIEWED', policy_codes=';'.join(pol),
                         risk_reason=' | '.join(x for x in [RISKY_LABELS.get(lab, ''), ('policy: ' + ','.join(pol)) if pol else '',
                                                             ('title hard: ' + hard.group(0)) if hard else '', ('title soft: ' + soft.group(0)) if soft else ''] if x),
                         pilot_26_member='YES' if r['offer_id'] in pilot else 'NO',
                         source='read-only shopping_product 2026-11-25 (Claude Code)', status='PROPOSAL_NOT_APPLIED'))
    with open(os.path.join(HERE, 'full_catalog_coverage_plan_2026-11-25.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(plan[0].keys())); w.writeheader(); w.writerows(plan)
    # generated allowlist = candidates with review recorded. No review register yet -> header only.
    allow = [p for p in plan if p['proposed_action'] == 'CANDIDATE_PENDING_REVIEW' and p['ads_review_ok'] == 'YES']
    with open(os.path.join(HERE, 'allowlist_generated.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['composite_id', 'proposed_campaign', 'review_ref'])
        for p in allow:
            w.writerow([p['composite_id'], p['proposed_campaign'], ''])
    byl = defaultdict(Counter)
    for p in plan:
        c = byl[p['label0']]
        c['total'] += 1
        if p['availability'] == 'IN_STOCK':
            c['in_stock'] += 1
            c[p['current_state']] += 1
    with open(os.path.join(HERE, 'coverage_by_label_2026-11-25.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['label0', 'total', 'in_stock', 'eligible_in_stock', 'no_campaign_in_stock', 'other_blocked_in_stock'])
        for lab, c in sorted(byl.items(), key=lambda x: -x[1]['in_stock']):
            w.writerow([lab, c['total'], c['in_stock'], c['COVERED_ELIGIBLE'], c['IN_STOCK_NO_CAMPAIGN'], c['IN_STOCK_OTHER_BLOCK']])
    summ = defaultdict(Counter)
    for p in plan:
        summ[(p['label0'], p['proposed_campaign'])][p['proposed_action'] + ('|IN' if p['availability'] == 'IN_STOCK' else '|OOS')] += 1
    acts = sorted({k for c in summ.values() for k in c})
    with open(os.path.join(HERE, 'full_coverage_summary_2026-11-25.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['label0', 'proposed_campaign'] + acts)
        for (l, c), cnt in sorted(summ.items(), key=lambda x: -sum(x[1].values())):
            w.writerow([l, c] + [cnt.get(a, 0) for a in acts])

    # ---------- printed log
    ins = [p for p in plan if p['availability'] == 'IN_STOCK']
    cs = Counter(p['current_state'] for p in ins)
    print('export rows', len(allrows), '| other Merchant excluded', len(other), Counter((r['merchant_id'], r['feed_label']) for r in other))
    print('Sonata rows', len(rows), 'unique composite', len({p['composite_id'] for p in plan}), 'in stock', len(ins), dict(cs))
    print('reconciliation', Counter(r['change_type'] for r in rec))
    b = [r for r in rec if r['from_temporary_bresser_de'] == 'YES']
    print('bresser.de 15.11:', len(b), Counter(r['change_type'] for r in b), '| still labelled bresser.de on 25.11:', labels.get('bresser.de', 0))
    print('label contract', Counter(c['contract_status'] for c in contract), [c['label0'] for c in contract if c['contract_status'] != 'OK'])
    print('scoped serving', serving_scoped, '| scoped not serving', paused_scoped)
    gap = [p for p in ins if p['current_state'] == 'IN_STOCK_NO_CAMPAIGN']
    print('in-stock gap', len(gap), Counter(p['proposed_action'] for p in gap))
    print('gap by campaign/admission', Counter((p['proposed_campaign'], p['admission_mode']) for p in gap if p['proposed_action'] == 'CANDIDATE_PENDING_REVIEW').most_common())
    print('policy hold all rows', Counter((p['availability'], p['current_state']) for p in plan if p['proposed_action'] == 'POLICY_HOLD'))
    print('eligible needing ID verification', sum(p['proposed_action'] == 'KEEP_CURRENT_VERIFY_ID' for p in plan))
    print('allowlist_generated rows', len(allow), '(no review register yet)')
    for oid in ('26130', '26916', '107817', '107671', '103933'):
        p = next((x for x in plan if x['offer_id'] == oid), None)
        print(' ', oid, p and (p['label0'], p['availability'], p['current_state'], p['proposed_action'], p['admission_mode']))


if __name__ == '__main__':
    main()
