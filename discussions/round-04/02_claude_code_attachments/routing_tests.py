#!/usr/bin/env python3
"""Round-4 routing tests with the real inherited negatives.

Inputs (repository only, no network):
  ../../round-03/05_chatgpt_attachments/live_checks_2026-11-15.json  -> 258 account-level negatives
  inputs/campaign_negatives_2026-11-15.csv                           -> 95 campaign negatives (read-only export)
  ../../round-03/04_claude_attachments/search_keywords.csv / search_negatives.csv -> Cowork r3 Search design
Outputs: routing_tests.csv, negative_keyword_diff.csv

Two matching modes are reported side by side and never merged:
  LITERAL     lower-case only (Google keywords are case-insensitive), whitespace tokens,
              diacritics, hyphens and '×' kept as typed. Negatives: BROAD = all tokens present in any
              order, PHRASE = contiguous token sequence, EXACT = identical query.
              Google documents that negatives do not match close variants -> LITERAL is the primary
              model for negatives.
  ASSUMED_CV  HYPOTHESIS about Google close variants for POSITIVE keywords only: hyphen->space,
              '×'->x, 'N x M'->'NxM', diacritics stripped. It is not a documented algorithm; a
              difference between the two modes is reported as RISK, never as PASS.
Shopping has no keywords: a query can reach a Shopping auction unless a negative blocks it; which
product Google picks is NOT simulated.
"""
import csv, json, os, re, sys, unicodedata
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
LIVE_CG = os.path.join(REPO, 'discussions/round-03/05_chatgpt_attachments/live_checks_2026-11-15.json')
CAMP_NEG = os.path.join(HERE, 'inputs/campaign_negatives_2026-11-15.csv')
R3 = os.path.join(REPO, 'discussions/round-03/04_claude_attachments')

PILOT_SHOP_CAMPAIGN_NEG = [('BROAD', 'bazár'), ('BROAD', 'bazar'), ('BROAD', 'použitý'), ('BROAD', 'pouzity')]  # Cowork r3 proposal
SERVING_SHOPPING = ['24440851881', '24451885423']   # campaigns where the control SKUs are ELIGIBLE today
EXISTING_SEARCH = ['24341095320', '24425793295']


def lit(s):
    return ' '.join(s.lower().split())


def cv(s):
    s = s.lower().replace('×', 'x').replace('–', ' ').replace('-', ' ')
    s = re.sub(r'(\d)\s*x\s*(\d)', r'\1x\2', s)
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if unicodedata.category(c) != 'Mn')  # strip Latin diacritics only
    return ' '.join(s.split())


def neg_hit(q, mt, term, f=lit):
    a, b = f(q), f(term)
    qt, tt = a.split(), b.split()
    if not tt:
        return False
    if mt == 'EXACT':
        return a == b
    if mt == 'PHRASE':
        return any(qt[i:i + len(tt)] == tt for i in range(len(qt) - len(tt) + 1))
    return all(t in qt for t in tt)      # BROAD negative


def hits(q, negs, f=lit):
    return [f'{mt}:{t}' for mt, t in negs if neg_hit(q, mt, t, f)]


def load():
    with open(LIVE_CG, encoding='utf-8') as fh:
        acc = [(n['matchType'], n['text']) for n in json.load(fh)['account_negative_keywords']]
    camp = defaultdict(list)
    with open(CAMP_NEG, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            camp[r['campaign_id']].append((r['match_type'], r['text']))
    groups = defaultdict(lambda: {'exact': [], 'phrase': [], 'neg': [], 'offer': ''})
    with open(os.path.join(R3, 'search_keywords.csv'), encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            g = groups[r['ad_group']]
            g['offer'] = r['offer_id']
            g['exact' if r['match_type'] == 'EXACT' else 'phrase'].append(r['keyword'])
    search_camp_neg = []
    with open(os.path.join(R3, 'search_negatives.csv'), encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['level'] == 'campaign':
                search_camp_neg.append((r['match_type'], r['negative']))
            else:
                groups[r['ad_group']]['neg'].append((r['match_type'], r['negative']))
    return acc, camp, dict(groups), search_camp_neg


def search_route(q, groups, f):
    cands, blocked = [], []
    for ag, g in groups.items():
        b = hits(q, g['neg'], f)
        if b:
            blocked.append(ag)
            continue
        if f(q) in [f(x) for x in g['exact']]:
            cands.append((0, ag))
        elif any(f(q) == f(p) or (' ' + f(p) + ' ') in (' ' + f(q) + ' ') for p in g['phrase']):
            cands.append((1, ag))
    if not cands:
        return 'NONE', blocked
    cands.sort()
    best = [c[1] for c in cands if c[0] == cands[0][0]]
    return ('AMBIGUOUS:' + '|'.join(best)) if len(best) > 1 else best[0], blocked


AG = {'T': 'AG_103933_Leica_Trinovid_10x42_HD', 'V': 'AG_26113_Levenhuk_Vegas_ED_10x42',
      'N': 'AG_103640_Levenhuk_New_Vegas_ED_10x42', 'S': 'AG_47420_SkyWatcher_Explorer_150PDS_EQ3'}
# id, category, query, expected Search route (literal design intent), Shopping should reach auction?, intended product, note
TESTS = [
 ('R01', 'model', 'leica trinovid 10x42 hd', AG['T'], True, '103933', 'owner example 1'),
 ('R02', 'model', 'levenhuk vegas ed 10x42', AG['V'], True, '26113|103640', 'owner example 2 typed with x; generation ambiguous (R3-CLAUDE-09)'),
 ('R03', 'model', 'levenhuk vegas ed 10×42', AG['V'], True, '26113|103640', 'owner example 2 exactly as written (×)'),
 ('R04', 'model', 'skywatcher explorer-150pds eq3', AG['S'], True, '47420', 'owner example 3 exactly as written (hyphen)'),
 ('R05', 'model', 'levenhuk new vegas ed 10x42', AG['N'], True, '103640', 'fourth control model'),
 ('R06', 'model', 'sky watcher explorer 150pds eq3', AG['S'], True, '47420', ''),
 ('R07', 'kde_kupit', 'kde kúpiť leica trinovid 10x42 hd', AG['T'], True, '103933', 'purchase intent with kde'),
 ('R08', 'kde_kupit', 'kde kupit levenhuk vegas ed 10x42', AG['V'], True, '26113|103640', 'without diacritics'),
 ('R09', 'kde_kupit', 'kde kúpiť skywatcher 150pds eq3', AG['S'], True, '47420', ''),
 ('R10', 'cena', 'leica trinovid 10x42 hd cena', AG['T'], True, '103933', ''),
 ('R11', 'cena', 'cena sky watcher 150pds eq3', AG['S'], True, '47420', ''),
 ('R12', 'cena', 'levenhuk new vegas ed 10x42 najlepšia cena', AG['N'], True, '103640', ''),
 ('R13', 'cena', 'leica trinovid 10x42 hd lacno', AG['T'], True, '103933', 'price-sensitive buyer; blocked by account lacno'),
 ('R14', 'generation', 'levenhuk vegas 10x42', 'UNROUTED_BY_DESIGN', True, '26113|103640', 'no ED: owner decision R3-CLAUDE-09'),
 ('R15', 'generation', 'new vegas ed 10x42', AG['N'], True, '103640', ''),
 ('R16', 'generation', 'levenhuk nový vegas ed 10x42', AG['N'], True, '103640', 'Slovak "new": AG_26113 blocks it, AG_103640 has no Slovak keyword -> Search gap'),
 ('R17', 'generation', 'levenhuk vegas ed 10x42 stary model', AG['V'], True, '26113', 'old generation explicitly; account negative stary'),
 ('R18', 'generation', 'levenhuk vegas ed 10x42 starý model', AG['V'], True, '26113', 'same with diacritics: negative stary does not match literally'),
 ('R19', 'mono_bino', 'levenhuk vegas ed 10x50 monokulár', 'NONE', True, '26130', 'monocular: no Search group; Shopping only via pilot (26130 has no campaign today)'),
 ('R20', 'mono_bino', 'levenhuk monokular vegas ed', 'NONE', True, '26130|26131', ''),
 ('R21', 'mono_bino', 'vegas ed 10x50', 'NONE', True, '26130|103641', 'ambiguous monocular vs New Vegas binocular 10x50'),
 ('R22', 'mono_bino', 'new vegas ed 10x50 ďalekohľad', 'NONE', True, '103641', 'binocular sibling; no Search group in pilot'),
 ('R23', 'magnification', 'leica trinovid 8x42 hd', 'NONE', True, '55858', 'sibling must not enter AG_103933'),
 ('R24', 'magnification', 'leica trinovid 10x32 hd', 'NONE', True, '55369', ''),
 ('R25', 'magnification', 'levenhuk vegas ed 8x42', 'NONE', True, '103639', ''),
 ('R26', 'magnification', 'leica trinovid 10x25 bca', 'NONE', True, '103932', ''),
 ('R27', 'goto_mount', 'sky-watcher 150pds eq3 goto', 'NONE', True, '47500', 'GoTo sibling must not enter AG_47420'),
 ('R28', 'goto_mount', 'skywatcher explorer 150pds eq5 goto', 'NONE', True, '47452', ''),
 ('R29', 'goto_mount', 'sky watcher 150p eq3', 'NONE', True, '47489', 'P vs PDS'),
 ('R30', 'goto_mount', 'skywatcher 150pds ota', 'NONE', True, '47472', ''),
 ('R31', 'accessory', 'leica trinovid 10x42 puzdro', 'NONE', True, 'ACCESSORY', 'case for the binocular, not the binocular'),
 ('R32', 'accessory', 'popruh leica trinovid 10x42 hd', 'NONE', True, 'ACCESSORY', 'strap'),
 ('R33', 'accessory', 'okulár pre skywatcher 150pds eq3', 'NONE', True, 'ACCESSORY', 'eyepiece'),
 ('R34', 'accessory', 'protizávažie eq3 150pds', 'NONE', True, 'ACCESSORY', 'counterweight'),
 ('R35', 'hyphen_diacritics', 'sky-watcher explorer-150pds eq3', AG['S'], True, '47420', ''),
 ('R36', 'hyphen_diacritics', 'sky watcher explorer 150 pds eq3', AG['S'], True, '47420', ''),
 ('R37', 'hyphen_diacritics', 'dalekohlad leica trinovid 10x42', AG['T'], True, '103933', ''),
 ('R38', 'hyphen_diacritics', 'leica trinovid 10 x 42 hd', AG['T'], True, '103933', ''),
 ('R39', 'hyphen_diacritics', 'LEICA Trinovid 10X42 HD', AG['T'], True, '103933', 'case only'),
 ('R40', 'research', 'aký ďalekohľad leica trinovid 10x42 hd', AG['T'], True, '103933', 'comparison intent; account aký'),
 ('R41', 'research', 'ktoré leica trinovid 10x42 alebo 8x42', 'NONE', True, '103933|55858', 'account Ktoré'),
 ('R42', 'research', 'leica trinovid 10x42 hd heureka', AG['T'], True, '103933', 'price comparison intent; account heureka'),
 ('R43', 'excluded', 'leica trinovid 10x42 hd bazár', 'NONE', False, '-', 'used: should be blocked'),
 ('R44', 'excluded', 'levenhuk vegas ed 10x42 návod pdf', 'NONE', False, '-', 'manual: informational'),
 ('R45', 'excluded', 'leica trinovid 10x42 hd zadarmo', 'NONE', False, '-', ''),
 ('R46', 'generic', 'ďalekohľad 10x42', 'NONE', True, 'ANY', 'generic, Shopping only'),
 ('R47', 'generic', 'teleskop pre začiatočníkov', 'NONE', True, 'ANY', ''),
]


def evaluate(acc, camp, groups, search_camp_neg, pilot_neg):
    rows, acc_blockers = [], defaultdict(list)
    for tid, cat, q, exp_s, exp_shop, prod, note in TESTS:
        a_lit, a_cv = hits(q, acc), hits(q, acc, cv)
        pshop = hits(q, pilot_neg)
        serving = {c: hits(q, camp.get(c, [])) for c in SERVING_SHOPPING}
        exist_search = {c: hits(q, camp.get(c, [])) for c in EXISTING_SEARCH}
        scn = hits(q, search_camp_neg)
        s_lit, blk_lit = search_route(q, groups, lit)
        s_cv, _ = search_route(q, groups, cv)
        acc_block = bool(a_lit)
        search_final = 'NONE' if (acc_block or scn) else s_lit
        shop_now = 'BLOCKED' if (acc_block or any(serving.values())) else 'REACHES_AUCTION'
        shop_pilot = 'BLOCKED' if (acc_block or pshop) else 'REACHES_AUCTION'
        exp_s_eff = 'NONE' if exp_s == 'UNROUTED_BY_DESIGN' else exp_s
        problems = []
        if search_final != exp_s_eff:
            problems.append(f'Search literal={search_final} expected={exp_s}')
        if (shop_pilot == 'REACHES_AUCTION') != exp_shop:
            problems.append(f'Shopping pilot={shop_pilot} expected_reach={exp_shop}')
        search_cv_final = 'NONE' if (acc_block or scn) else s_cv
        neg_cv_extra = bool(a_cv) and not a_lit
        if problems and search_cv_final == exp_s_eff and not [p for p in problems if p.startswith('Shopping')]:
            verdict = 'CV_DEPENDENT'      # works only if Google applies close variants
        elif problems:
            verdict = 'FAIL'
        elif search_cv_final != exp_s_eff or neg_cv_extra:
            verdict = 'PASS_LITERAL_RISK_CV'
        else:
            verdict = 'PASS'
        if exp_s == 'UNROUTED_BY_DESIGN' and verdict.startswith('PASS'):
            verdict = 'OWNER_DECISION'
        if a_lit and exp_shop:
            for h in a_lit:
                acc_blockers[h].append(tid)
        # 26130 note: current Shopping coverage is zero whatever the query
        cur_cov = ''
        if '26130' in prod:
            cur_cov = '26130 not_eligible_in_any_campaign today: no current Shopping route; pilot allowlist adds it'
        rows.append(dict(
            test_id=tid, category=cat, query=q, intended_product=prod,
            expected_search=exp_s, expected_shopping_reaches_auction=exp_shop,
            account_neg_hits_literal=';'.join(a_lit), account_neg_hits_assumed_cv=';'.join(a_cv),
            serving_shopping_campaign_neg_hits=json.dumps({k: v for k, v in serving.items() if v}, ensure_ascii=False) if any(serving.values()) else 'NONE (0 negatives in 24440851881/24451885423)',
            existing_search_campaign_neg_hits=json.dumps({k: v for k, v in exist_search.items() if v}, ensure_ascii=False) if any(exist_search.values()) else '',
            proposed_search_campaign_neg_hits=';'.join(scn), proposed_pilot_shopping_neg_hits=';'.join(pshop),
            adgroup_neg_blocked_groups_literal=';'.join(blk_lit),
            search_route_literal_before_account=s_lit, search_route_literal_final=search_final,
            search_route_assumed_cv=s_cv,
            shopping_current=shop_now, shopping_pilot=shop_pilot,
            current_shopping_coverage_note=cur_cov,
            verdict=verdict, problems=' / '.join(problems), note=note,
            campaign_group_negatives_data='complete: account 258 + campaign 95 + ad_group 0 (read-only 2026-11-15); proposed pilot/search negatives from Cowork r3'))
    return rows, acc_blockers


def main(outdir):
    sys.stdout.reconfigure(encoding='utf-8')
    acc, camp, groups, search_camp_neg = load()
    assert len(acc) == 258, len(acc)
    assert sum(len(v) for v in camp.values()) == 95
    assert all(len(camp.get(c, [])) == 0 for c in SERVING_SHOPPING), 'serving Shopping campaigns gained negatives: rerun'
    rows, acc_blockers = evaluate(acc, camp, groups, search_camp_neg, PILOT_SHOP_CAMPAIGN_NEG)
    with open(os.path.join(outdir, 'routing_tests.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # ---- negative diff: PROPOSALS ONLY. Every account negative that blocks a commercial test must appear.
    RATIONALE = {
        'BROAD:kde': ('REPLACE', 'kde (BROAD) -> remove; add PHRASE: "kde sa nachádza", "kde pozorovať", "kde je" after search-term review',
                      'kde blocks every "kde kúpiť <model>" query in Search AND Shopping (account list applies to both)',
                      'Informational "kde ..." traffic returns; mitigate with phrase negatives from real search terms',
                      'Before: search_term_view 90 d for terms containing kde (count, clicks, conv). After approval: weekly search terms; test R07-R09 must PASS'),
        'BROAD:lacno': ('OWNER_DECISION', 'lacno (BROAD) -> keep or remove; if removed keep "zadarmo","free" etc.',
                        'blocks "<model> lacno" price-intent queries (R13)', 'Low-margin bargain hunters; price-comparison traffic',
                        'Check historical conversion of lacno terms in old reports (private data) before deciding'),
        'BROAD:stary': ('REPLACE', 'stary (BROAD) -> PHRASE "stary dalekohlad", "stary teleskop" or remove; Search old-generation intent goes to AG_26113',
                        'blocks explicit old-generation queries ("vegas ed stary model", R17) while "starý" with diacritics is NOT blocked (R18): inconsistent',
                        'Antique/used optics traffic; bazar/použitý negatives already cover used',
                        'R17 and R18 must give the same route after change; review search terms with star*'),
        'BROAD:heureka': ('OWNER_DECISION', 'heureka (BROAD) -> keep (likely intended) or remove for model queries',
                          'blocks "<model> heureka" comparison queries (R42); Heureka is a separate channel',
                          'Removing may buy clicks from users who will buy on Heureka anyway', 'Owner/Heureka channel decision; no change by default'),
        'BROAD:aký': ('REPLACE', 'aký (BROAD) -> PHRASE "aký je", "aký zvoliť" only after review; keep for non-model generic terms',
                      'blocks "aký ďalekohľad <model>" comparison queries (R40)', 'More research traffic',
                      'search_term_view for aký/ake/ktoré; R40 PASS after change'),
        'BROAD:Ktoré': ('REVIEW', 'Ktoré (BROAD): case-insensitive, matches only the exact form "ktoré"; keep but note "ktorý/ktorá" not covered',
                        'blocks "ktoré leica trinovid 10x42 alebo 8x42" (R41); expected Search=NONE anyway, Shopping blocked',
                        'Low', 'Decide together with aký'),
    }
    extra = [
        ('ACCOUNT', 'BROAD', 'keyword_text', 'REMOVE', 'remove', 'Looks like a CSV header imported as a keyword', 'None expected (no real query contains keyword_text)', 'Confirm the entry exists in UI list before removal'),
        ('ACCOUNT', 'BROAD', 'bazár', 'ADD', 'add BROAD bazár next to existing bazar', 'Account list has bazar but not bazár; negatives do not match variants (R43 relies on campaign negative only)', 'Very low', 'R43 blocked by account list after change'),
        ('ACCOUNT', 'BROAD', 'starý', 'NO_CHANGE_UNLESS_stary_KEPT', 'if owner keeps stary, add starý for consistency', 'R17/R18 inconsistency', 'Same as stary', 'R17 = R18'),
        ('SEARCH_AG_26113', 'EXACT', 'levenhuk vegas ed 10×42', 'ADD_KEYWORD_PROPOSAL', 'positive keyword in the form the owner typed, if Google Ads accepts the × character; otherwise rely on close variants and verify in search terms', 'R03 routes only under the close-variant assumption', 'None if rejected by editor', 'Editor validation; search_term_view after approved launch'),
        ('SEARCH_AG_47420', 'EXACT', 'skywatcher explorer-150pds eq3; sky-watcher explorer-150pds eq3', 'ADD_KEYWORD_PROPOSAL', 'positive keywords with hyphen as typed by owner', 'R04/R35 route only under the close-variant assumption', 'Low', 'R04/R35 literal PASS'),
        ('SEARCH_AG_103933', 'EXACT', 'leica trinovid 10 x 42 hd', 'ADD_KEYWORD_PROPOSAL', 'spaced magnification form', 'R38 routes only under the close-variant assumption', 'Low', 'R38 literal PASS'),
        ('PILOT_SHOPPING+NEW_SEARCH', 'PHRASE', 'návod, navod, manuál, manual, pdf, servis, oprava, náhradné diely', 'COPY_TO_NEW_CAMPAIGNS', 'copy the existing Search campaign phrase negatives into the pilot Shopping and the new model Search campaign',
         'R44: these negatives exist only in old Search campaigns 24341095320/24425793295 and are NOT inherited by new campaigns; account list has none of them', 'Blocks rare "<model> manual" buyers; low', 'R44 blocked in both surfaces'),
        ('PILOT_SHOPPING', 'BROAD', 'bazár/bazar/použitý/pouzity', 'ADD_IN_NEW_CAMPAIGN', 'as Cowork r3', 'used goods', 'Low', 'R43'),
        ('SEARCH_AG_103640', 'EXACT', 'levenhuk nový vegas ed 10x42', 'ADD_KEYWORD_PROPOSAL', 'positive keyword, not a negative', 'R16: Slovak "nový" is negated in AG_26113 and absent in AG_103640 -> no Search route', 'Duplicate-intent with New keywords; low', 'R16 routes to AG_103640'),
        ('SEARCH_AG_ALL', 'BROAD', 'puzdro, popruh, okulár, protizávažie, filter, adaptér', 'ADD_AD_GROUP_NEGATIVES', 'accessory words in each model group',
         'R31-R34: phrase keywords "trinovid 10x42"/"150pds eq3" capture accessory queries (false positive)', 'Loses rare "binocular with case" bundle queries', 'R31-R34 Search=NONE after change; Shopping still reaches auction (accessory SKUs)'),
    ]
    diff = []
    for h, tids in sorted(acc_blockers.items()):
        mt, term = h.split(':', 1)
        if h in RATIONALE:
            act, prop, basis, risk, check = RATIONALE[h]
        else:
            act, prop, basis, risk, check = ('UNREVIEWED', '-', 'blocks a commercial test', '-', 'review needed')
        diff.append(dict(level='ACCOUNT', match_type=mt, negative=term, action=act, proposal=prop,
                         basis=basis, example_tests=';'.join(tids), risk=risk, verification=check, status='PROPOSAL_NOT_APPLIED'))
    for lvl, mt, term, act, prop, basis, risk, check in extra:
        diff.append(dict(level=lvl, match_type=mt, negative=term, action=act, proposal=prop, basis=basis,
                         example_tests={'keyword_text': '-', 'bazár': 'R43', 'starý': 'R17;R18', 'levenhuk vegas ed 10×42': 'R03', 'leica trinovid 10 x 42 hd': 'R38'}.get(term, 'R16' if 'nový' in term else ('R31;R32;R33;R34' if 'puzdro' in term else ('R04;R35' if 'explorer-150pds' in term else ('R44' if 'návod' in term else 'R43')))),
                         risk=risk, verification=check, status='PROPOSAL_NOT_APPLIED'))
    assert 'keyword_text' in [t for _, t in acc], 'keyword_text no longer in account list'
    with open(os.path.join(outdir, 'negative_keyword_diff.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(diff[0].keys()))
        w.writeheader()
        w.writerows(diff)

    # ---- counterfactual: apply only the NON-owner-decision proposals in simulation (nothing is applied live)
    import copy
    acc2 = [(m, t) for m, t in acc if (m, t) not in {('BROAD', 'kde'), ('BROAD', 'stary'), ('BROAD', 'aký'), ('BROAD', 'keyword_text')}]
    acc2 += [('PHRASE', 'kde sa nachádza'), ('PHRASE', 'kde pozorovať'), ('PHRASE', 'kde je'), ('BROAD', 'bazár'),
             ('PHRASE', 'stary dalekohlad'), ('PHRASE', 'stary teleskop'), ('PHRASE', 'aký je'), ('PHRASE', 'aký zvoliť')]
    g2 = copy.deepcopy(groups)
    g2[AG['V']]['exact'].append('levenhuk vegas ed 10×42')
    g2[AG['S']]['exact'] += ['skywatcher explorer-150pds eq3', 'sky-watcher explorer-150pds eq3']
    g2[AG['T']]['exact'].append('leica trinovid 10 x 42 hd')
    g2[AG['N']]['exact'].append('levenhuk nový vegas ed 10x42')
    manual = [('PHRASE', t) for t in ('návod', 'navod', 'manuál', 'manual', 'pdf', 'servis', 'oprava', 'náhradné diely')]
    for g in g2.values():
        g['neg'] += [('BROAD', t) for t in ('puzdro', 'popruh', 'okulár', 'protizávažie', 'filter', 'adaptér')]
    rows2, _ = evaluate(acc2, camp, g2, search_camp_neg + manual, PILOT_SHOP_CAMPAIGN_NEG + manual)
    with open(os.path.join(outdir, 'routing_tests_after_proposed_diff.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['test_id', 'query', 'verdict_now', 'verdict_after_simulated_diff', 'search_after', 'shopping_pilot_after', 'remaining_problem', 'note'])
        for a, b in zip(rows, rows2):
            w.writerow([a['test_id'], a['query'], a['verdict'], b['verdict'], b['search_route_literal_final'], b['shopping_pilot'], b['problems'],
                        'SIMULATION ONLY; lacno/heureka/Ktoré left unchanged as owner decisions'])
    from collections import Counter
    print('after simulated diff', Counter(r['verdict'] for r in rows2), [r['test_id'] for r in rows2 if r['verdict'] == 'FAIL'])
    print('tests', len(rows), Counter(r['verdict'] for r in rows))
    for r in rows:
        print(r['test_id'], r['verdict'], '| acc:', r['account_neg_hits_literal'] or '-', '| S:', r['search_route_literal_final'], '| cv:', r['search_route_assumed_cv'], '| shop:', r['shopping_pilot'], '|', r['problems'])
    print('diff rows', len(diff), [d['negative'] + ':' + d['action'] for d in diff])
    unreviewed = [d for d in diff if d['action'] == 'UNREVIEWED']
    print('UNREVIEWED account blockers:', len(unreviewed))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else HERE)
