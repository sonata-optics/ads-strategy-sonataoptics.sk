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
 ('R48', 'accessory', 'leica trinovid 10x42 hd s puzdrom', AG['T'], True, '103933', 'bundle wording: accessory negatives must not block "model s puzdrom"'),
 ('R49', 'accessory', 'puzdro na leica trinovid 10x42', 'NONE', True, 'ACCESSORY', 'accessory itself'),
 # Cowork round-4 counterexamples C01-C14 (03_claude_attachments/routing_counterexamples.py), expectations as Cowork wrote them
 ('C01', 'cowork_counterexample', 'poradiť leica trinovid 10x42 hd', AG['T'], True, '103933', 'advice intent = pre-purchase'),
 ('C02', 'cowork_counterexample', 'ake leica trinovid 10x42 hd', AG['T'], True, '103933', 'ake = aký without diacritics'),
 ('C03', 'cowork_counterexample', 'leica trinovid 10x42 hd nie drahé', AG['T'], True, '103933', 'price-sensitive commercial'),
 ('C04', 'cowork_counterexample', 'správny ďalekohľad leica trinovid 10x42', AG['T'], True, '103933', 'selection intent'),
 ('C05', 'cowork_counterexample', 'levenhuk vegas ed 10x42 popis', AG['V'], True, '26113', 'spec lookup'),
 ('C06', 'cowork_counterexample', 'typy ďalekohľadov leica trinovid', 'NONE', True, 'ANY', 'research; owner decision (Cowork)'),
 ('C07', 'cowork_counterexample', 'termovízne drony autel', 'NONE', True, 'drones in stock', 'account BROAD drony vs catalogue'),
 ('C08', 'cowork_counterexample', 'dalekohlad s fotoaparatom', 'NONE', True, 'Atom DNB300', 'account PHRASE vs catalogue'),
 ('C09', 'cowork_counterexample', 'ďalekohľad s fotoaparátom', 'NONE', True, 'Atom DNB300', 'diacritic form not blocked (inconsistency)'),
 ('C10', 'cowork_counterexample', 'čo je leica trinovid 10x42 hd', 'NONE', False, '-', 'informational; block acceptable'),
 ('C11', 'cowork_counterexample', 'leica trinovid 10x42 hd recenzia', AG['T'], True, '103933', 'review intent'),
 ('C12', 'cowork_counterexample', 'leica trinovid 10x42 hd vs 8x42', 'NONE', True, '103933|55858', 'comparison'),
 ('C13', 'cowork_counterexample', 'nájsť leica trinovid 10x42 hd', AG['T'], True, '103933', 'find intent'),
 ('C14', 'cowork_counterexample', 'trinowid 10x42', 'NONE', True, '103933', 'typo; literal none'),
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

    # ---- negative diff: PROPOSALS ONLY (v2, 04b). Commercial modifiers are OWNER_DECISION with options;
    # nothing here is a final instruction. Full 258-word review: ../04b_claude_code_attachments/account_negatives_review.csv
    OPT = ('Options (owner, after 90-day search terms of ALL campaigns): A keep in account list; '
           'B remove from account list (opens the word for every Search/Shopping campaign); '
           'C narrow to specific PHRASE forms; D move the word from the account list to campaign lists of chosen campaigns '
           '(leaves it blocked there for the rest of the catalogue; it is a way to limit the experiment, not a fix). No option is pre-selected.')

    def CM(word, tests, risk):
        return ('OWNER_DECISION', OPT, f'{word} blocks commercial/pre-purchase model queries ({tests}) in Search AND Shopping', risk,
                f'search_term_view 90 d with {word}; rerun routing_tests')
    RATIONALE = {
        'BROAD:kde': CM('kde', 'R07-R09', 'informational "kde ..." traffic returns if removed/narrowed'),
        'BROAD:aký': CM('aký', 'R40', 'research traffic; note "ake" is a separate entry'),
        'BROAD:ake': CM('ake', 'C02', 'same as aký; diacritic forms are separate negatives'),
        'BROAD:lacno': CM('lacno', 'R13', 'bargain hunters'),
        'BROAD:nie drahé': CM('nie drahé', 'C03', 'bargain hunters'),
        'BROAD:poradiť': CM('poradiť', 'C01', 'advice seekers; some convert'),
        'BROAD:Správny': CM('Správny', 'C04', 'selection intent'),
        'BROAD:Nájsť': CM('Nájsť', 'C13', 'navigational/find intent'),
        'BROAD:popis': CM('popis', 'C05', 'spec lookup, mixed intent'),
        'BROAD:heureka': CM('heureka', 'R42', 'buyers may purchase on Heureka anyway; separate channel decision'),
        'BROAD:Ktoré': CM('Ktoré', 'R41', 'comparison intent; only the exact form "ktoré" is covered'),
        'BROAD:typy': CM('typy', 'C06', 'research intent; Cowork marks it a possible correct block'),
        'BROAD:stary': ('OWNER_DECISION', OPT + ' Consistency: if kept, add "starý"; if removed, both forms open.',
                        'blocks explicit old-generation model queries (R17) while "starý" passes (R18)', 'antique/used traffic (bazar/použitý already blocked)',
                        'R17 and R18 must route identically'),
        'BROAD:drony': ('OWNER_DECISION_CATALOG', 'Catalogue sells drones (label drony, 5 IN_STOCK 15.11): remove from account list or narrow to unrelated forms after search terms',
                        'BROAD drony blocks queries for products in stock (C07)', 'toy/hobby drone traffic', 'C07 reaches Shopping after change; check drone search terms'),
        'PHRASE:dalekohlad s fotoaparatom': ('OWNER_DECISION_CATALOG', 'Catalogue sells a digital binocular (Levenhuk Atom DNB300): remove; the diacritic form is not blocked anyway (C09)',
                                             'blocks a product-type query (C08) and is inconsistent with C09', 'camera-binocular queries for products not sold', 'C08 = C09 after change'),
    }
    extra = [
        ('ACCOUNT', 'BROAD', 'keyword_text', 'REMOVE', 'remove', 'Looks like a CSV header imported as a keyword', 'None expected (no real query contains keyword_text)', 'Confirm the entry exists in UI list before removal', '-'),
        ('ACCOUNT', 'BROAD', 'bazár', 'ADD', 'add BROAD bazár next to existing bazar', 'Account list has bazar but not bazár; negatives do not match variants (R43 relies on campaign negative only)', 'Very low', 'R43 blocked by account list after change', 'R43'),
        ('SEARCH_AG_26113', 'EXACT', 'levenhuk vegas ed 10×42', 'ADD_KEYWORD_PROPOSAL', 'positive keyword in the form the owner typed, if Google Ads accepts the × character; otherwise rely on close variants and verify in search terms', 'R03 routes only under the close-variant assumption', 'None if rejected by editor', 'Editor validation; search_term_view after approved launch', 'R03'),
        ('SEARCH_AG_47420', 'EXACT', 'skywatcher explorer-150pds eq3; sky-watcher explorer-150pds eq3', 'ADD_KEYWORD_PROPOSAL', 'positive keywords with hyphen as typed by owner', 'R04/R35 route only under the close-variant assumption', 'Low', 'R04/R35 literal PASS', 'R04;R35'),
        ('SEARCH_AG_103933', 'EXACT', 'leica trinovid 10 x 42 hd', 'ADD_KEYWORD_PROPOSAL', 'spaced magnification form', 'R38 routes only under the close-variant assumption', 'Low', 'R38 literal PASS', 'R38'),
        ('PILOT_SHOPPING+NEW_SEARCH', 'PHRASE', 'návod, navod, manuál, manual, pdf, servis, oprava, náhradné diely', 'COPY_TO_NEW_CAMPAIGNS', 'copy the existing Search campaign phrase negatives into the pilot Shopping and the new model Search campaign',
         'R44: these negatives exist only in old Search campaigns 24341095320/24425793295 and are NOT inherited by new campaigns; account list has none of them', 'Blocks rare "<model> manual" buyers; low', 'R44 blocked in both surfaces', 'R44'),
        ('PILOT_SHOPPING', 'BROAD', 'bazár/bazar/použitý/pouzity', 'ADD_IN_NEW_CAMPAIGN', 'as Cowork r3', 'used goods', 'Low', 'R43', 'R43'),
        ('SEARCH_AG_103640', 'EXACT', 'levenhuk nový vegas ed 10x42', 'ADD_KEYWORD_PROPOSAL', 'positive keyword, not a negative', 'R16: Slovak "nový" is negated in AG_26113 and absent in AG_103640 -> no Search route', 'Duplicate-intent with New keywords; low', 'R16 routes to AG_103640', 'R16'),
        ('SEARCH_AG_ALL', 'BROAD', 'puzdro, popruh, okulár, protizávažie, filter, adaptér', 'ADD_AD_GROUP_NEGATIVES', 'accessory nouns (base form) in each model Search group; NOT in Shopping',
         'R31-R34: phrase keywords capture accessory queries (false positive)', 'Bundle wording "s puzdrom" stays open only because negatives do not match inflected forms (R48); verify in search terms', 'R31-R34 Search=NONE, R48 still routes, R49 blocked', 'R31;R32;R33;R34;R48;R49'),
    ]
    diff = []
    for h, tids in sorted(acc_blockers.items()):
        mt, term = h.split(':', 1)
        act, prop, basis, risk, check = RATIONALE.get(h, ('UNREVIEWED', '-', 'blocks a commercial test', '-', 'review needed'))
        diff.append(dict(level='ACCOUNT', match_type=mt, negative=term, action=act, proposal=prop,
                         basis=basis, example_tests=';'.join(tids), risk=risk, verification=check, status='PROPOSAL_NOT_APPLIED'))
    for lvl, mt, term, act, prop, basis, risk, check, ex in extra:
        diff.append(dict(level=lvl, match_type=mt, negative=term, action=act, proposal=prop, basis=basis,
                         example_tests=ex, risk=risk, verification=check, status='PROPOSAL_NOT_APPLIED'))
    assert 'keyword_text' in [t for _, t in acc], 'keyword_text no longer in account list'
    with open(os.path.join(outdir, 'negative_keyword_diff.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(diff[0].keys()))
        w.writeheader()
        w.writerows(diff)

    # ---- two SIMULATED scenarios (nothing applied live; neither pre-decides owner words)
    import copy
    g2 = copy.deepcopy(groups)
    g2[AG['V']]['exact'].append('levenhuk vegas ed 10×42')
    g2[AG['S']]['exact'] += ['skywatcher explorer-150pds eq3', 'sky-watcher explorer-150pds eq3']
    g2[AG['T']]['exact'].append('leica trinovid 10 x 42 hd')
    g2[AG['N']]['exact'].append('levenhuk nový vegas ed 10x42')
    manual = [('PHRASE', t) for t in ('návod', 'navod', 'manuál', 'manual', 'pdf', 'servis', 'oprava', 'náhradné diely')]
    for g in g2.values():
        g['neg'] += [('BROAD', t) for t in ('puzdro', 'popruh', 'okulár', 'protizávažie', 'filter', 'adaptér')]
    acc_a = [(m, t) for m, t in acc if t != 'keyword_text'] + [('BROAD', 'bazár')]
    rows_a, _ = evaluate(acc_a, camp, g2, search_camp_neg + manual, PILOT_SHOP_CAMPAIGN_NEG + manual)
    owner_words = {h for h, v in RATIONALE.items() if v[0].startswith('OWNER_DECISION')}
    acc_b = [(m, t) for m, t in acc_a if f'{m}:{t}' not in owner_words]
    rows_b, _ = evaluate(acc_b, camp, g2, search_camp_neg + manual, PILOT_SHOP_CAMPAIGN_NEG + manual)
    with open(os.path.join(outdir, 'routing_tests_after_proposed_diff.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['test_id', 'query', 'verdict_now', 'verdict_A_technical_fixes_only', 'verdict_B_upper_bound_owner_words_removed',
                    'resolution', 'remaining_problem_A', 'note'])
        for a, b, c in zip(rows, rows_a, rows_b):
            blk = [h for h in b['account_neg_hits_literal'].split(';') if h]
            if a['verdict'] in ('PASS', 'PASS_LITERAL_RISK_CV'):
                res = 'NO_CHANGE_NEEDED'
            elif a['verdict'] == 'OWNER_DECISION':
                res = 'OWNER_DECISION:R3-CLAUDE-09'
            elif b['verdict'] in ('PASS', 'PASS_LITERAL_RISK_CV'):
                res = 'FIXED_BY_TECHNICAL_PROPOSAL (not applied)'
            elif blk and all(h in owner_words for h in blk):
                res = 'OWNER_DECISION:' + ','.join(blk)
            else:
                res = 'OPEN'
            w.writerow([a['test_id'], a['query'], a['verdict'], b['verdict'], c['verdict'], res, b['problems'],
                        'SIMULATION ONLY. A = keywords, ad-group/campaign negatives, keyword_text, bazár. B = A + every OWNER_DECISION word removed from account list: upper bound of effect, not a recommendation'])
    from collections import Counter
    print('scenario A', Counter(r['verdict'] for r in rows_a), [r['test_id'] for r in rows_a if r['verdict'] == 'FAIL'])
    print('scenario B', Counter(r['verdict'] for r in rows_b), [r['test_id'] for r in rows_b if r['verdict'] == 'FAIL'])
    print('tests', len(rows), Counter(r['verdict'] for r in rows))
    for r in rows:
        print(r['test_id'], r['verdict'], '| acc:', r['account_neg_hits_literal'] or '-', '| S:', r['search_route_literal_final'], '| shop:', r['shopping_pilot'], '|', r['problems'])
    print('diff rows', len(diff), [d['negative'] + ':' + d['action'] for d in diff])
    unreviewed = [d for d in diff if d['action'] == 'UNREVIEWED']
    print('UNREVIEWED account blockers:', len(unreviewed))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else HERE)
