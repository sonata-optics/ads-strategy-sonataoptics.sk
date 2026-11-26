#!/usr/bin/env python3
"""Round 5 move 7: effective negative sets per SO27 route = account-level list (after diff) + attached shared lists + campaign.
Source of the account list: account_level_negatives_2026-11-26.json (direct read, 258 rows). Decisions: 04 negative_decisions.csv
+ two seasonal additions by Code (REMOVE 'Čo', 'dať': block gift questions "čo dať / čo kúpiť na Vianoce").
Engine: literal matching (routing_tests.neg_hit); Google does not expand negatives to close variants, so every fixture is tested
with and without diacritics. Nothing is applied. Outputs: negatives_account_diff.csv, negatives_fixtures_results.csv"""
import csv, json, os, sys, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'discussions/round-04/02_claude_code_attachments')); sys.dont_write_bytecode = True
import routing_tests as rt  # noqa

ACC = [(k['match_type'], k['text']) for k in json.load(open(os.path.join(HERE, 'account_level_negatives_2026-11-26.json'), encoding='utf-8'))['keywords']]

# --- account-level diff (applies to every campaign incl. SO27, legacy fallback and Predajňa) ---
REMOVE = [('BROAD', w) for w in ['kde', 'poradiť', 'lacno', 'nie drahé', 'cheap', 'popis', 'keyword_text', 'slabozrakých', 'aký', 'ake',
                                 'funguje', 'drony', 'Čo', 'dať', 'dracik']] + [('PHRASE', 'dalekohlad s fotoaparatom')]
WHY = {'Čo': 'Code, season: blocks "čo dať/kúpiť na Vianoce"', 'dať': 'Code, season: blocks "čo dať ... pod stromček"',
       'drony': '04: remove when route ready - drones are ads_ok in SO27 catch-all', 'dracik': '04: BROAD -> EXACT',
       'funguje': '04: remove global, local only', 'aký': '04: early controlled review', 'ake': '04: early controlled review'}
ADD = [('BROAD', 'bazár'), ('BROAD', 'bazoš'), ('BROAD', 'predám'),
       ('PHRASE', 'na pušku'), ('PHRASE', 'na pusku'), ('PHRASE', 'na puškohľad'), ('PHRASE', 'na puskohlad'),
       ('PHRASE', 'na gulovnicu'), ('PHRASE', 'na guľovnicu'), ('PHRASE', 'na vzduchovku'), ('BROAD', 'puskohlad'), ('BROAD', 'puškohľad'),
       ('EXACT', 'alza'), ('EXACT', 'alza sk'), ('EXACT', 'kaufland'), ('EXACT', 'decathlon'), ('EXACT', 'dráčik'), ('EXACT', 'dracik'),
       ('EXACT', 'allegro'), ('EXACT', 'allegro sk')]
KEEP_NOTE = {'nevidiacich': '04: hold pending product check', 'heureka': 'owner: deferred', 'Ktoré': '04 temporary keep', 'Správny': '04 temporary keep',
             'Nájsť': '04 temporary keep', 'typy': '04 temporary keep', 'druhy': '04 temporary keep', 'stary': '04 temporary keep'}

# --- SO27 shared lists (new, attached per route) ---
SO27_SHOP = [('PHRASE', 'pracovné ponuky'), ('PHRASE', 'brigáda'), ('PHRASE', 'dioptrické okuliare'), ('PHRASE', 'dioptricke okuliare'),
             ('PHRASE', 'kontaktné šošovky'), ('PHRASE', 'kontaktne sosovky'), ('PHRASE', 'očný lekár'), ('PHRASE', 'ocny lekar'), ('PHRASE', 'meranie zraku')]
SO27_SEARCH = SO27_SHOP + [('PHRASE', 'návod'), ('PHRASE', 'navod'), ('PHRASE', 'manuál'), ('PHRASE', 'manual'), ('PHRASE', 'pdf'),
                           ('PHRASE', 'oprava'), ('PHRASE', 'servis'), ('PHRASE', 'náhradné diely')]
NO_HUNTING = [('PHRASE', 'poľovníctvo'), ('PHRASE', 'polovnictvo'), ('PHRASE', 'lovu zdar'), ('PHRASE', 'na lov'), ('PHRASE', 'poľovnícky'),
              ('PHRASE', 'polovnicky'), ('PHRASE', 'na diviaky'), ('PHRASE', 'na diviaka')]     # thermal only (owner rule, no hunting words)
PREDAJNA = [('PHRASE', 'pracovné ponuky'), ('PHRASE', 'brigáda'), ('PHRASE', 'dioptrické okuliare'), ('PHRASE', 'dioptricke okuliare'),
            ('PHRASE', 'kontaktné šošovky'), ('PHRASE', 'kontaktne sosovky'), ('PHRASE', 'očný lekár'), ('PHRASE', 'ocny lekar'), ('PHRASE', 'meranie zraku')]
ROUTES = {'shopping_core': SO27_SHOP, 'shopping_thermal': SO27_SHOP + NO_HUNTING, 'search_category': SO27_SEARCH,
          'search_brand_model': SO27_SEARCH, 'predajna': PREDAJNA}

FIX = [  # route, query, expected (True = must reach), note
 ('shopping_core', 'kde kúpiť ďalekohľad', True, 'where to buy'), ('shopping_core', 'kde je predajňa sonata optics', True, 'store'),
 ('predajna', 'kde je predajňa sonata optics bratislava', True, 'store question'), ('predajna', 'sonata optics otváracie hodiny', True, 'store hours'),
 ('shopping_core', 'teleskop lacno', True, 'cheap intent'), ('shopping_core', 'ďalekohľad nie drahé', True, 'cheap intent'),
 ('shopping_core', 'aký teleskop kúpiť', True, 'choice'), ('shopping_core', 'ake dalekohlady su najlepsie', True, 'choice'),
 ('shopping_core', 'čo dať dieťaťu na vianoce teleskop', True, 'gift (season)'), ('shopping_core', 'co kupit na vianoce mikroskop', True, 'gift (season)'),
 ('shopping_core', 'mikroskop popis', True, 'description'), ('shopping_core', 'lupa na čítanie pre slabozrakých', True, 'low vision'),
 ('shopping_core', 'dron s termokamerou', True, 'drone sold'), ('shopping_core', 'ďalekohľad s fotoaparátom', True, 'digital binocular'),
 ('shopping_core', 'dalekohlad s fotoaparatom', True, 'digital binocular, unaccented'), ('shopping_core', 'ako funguje teleskop', True, 'research, Shopping open'),
 ('shopping_core', 'leica trinovid 10x42 alza', True, 'model + competitor is commercial'), ('shopping_core', 'puzdro na ďalekohľad', True, 'accessory'),
 ('shopping_core', 'ďalekohľad poľovnícky', True, 'binocular for hunting is not a weapon (ChatGPT)'), ('shopping_core', 'dalekohlad polovnicky', True, 'unaccented'),
 ('shopping_thermal', 'termovízia na pozorovanie zveri', True, 'observation'), ('shopping_thermal', 'termovizia hikmicro', True, 'brand'),
 ('search_category', 'teleskop pre deti', True, 'kids'), ('search_category', 'hvezdarsky dalekohlad cena', True, 'unaccented'),
 ('search_brand_model', 'celestron nexstar 8se', True, 'model'),
 ('shopping_core', 'alza', False, 'pure navigation'), ('shopping_core', 'allegro sk', False, 'pure navigation'), ('shopping_core', 'dracik', False, 'pure navigation'),
 ('shopping_core', 'ďalekohľad bazár', False, 'used'), ('shopping_core', 'predám ďalekohľad', False, 'used'), ('shopping_core', 'teleskop bazos', False, 'used'),
 ('shopping_core', 'nočné videnie na pušku', False, 'weapon'), ('shopping_core', 'nocne videnie na pusku', False, 'weapon unaccented'),
 ('shopping_core', 'dalekohlad na vzduchovku', False, 'weapon'), ('shopping_core', 'puskohlad', False, 'weapon optic'),
 ('shopping_thermal', 'poľovníctvo', False, 'hunting (thermal)'), ('shopping_thermal', 'lovu zdar', False, 'hunting (thermal)'),
 ('shopping_thermal', 'termovizia na diviaky', False, 'hunting (thermal)'),
 ('search_category', 'teleskop návod pdf', False, 'manual'), ('predajna', 'očný lekár bratislava', False, 'optician confusion'),
 ('shopping_core', 'mikroskop porno', False, 'adult'),
]


def strip(s):
    return ''.join(ch for ch in unicodedata.normalize('NFD', s) if unicodedata.category(ch) != 'Mn')


def apply():
    acc = [x for x in ACC if x not in REMOVE]
    for a in ADD:
        if a not in acc:
            acc.append(a)
    return acc


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    missing = [r for r in REMOVE if r not in ACC]
    after = apply()
    with open(os.path.join(HERE, 'negatives_account_diff.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['level', 'action', 'match_type', 'text', 'reason', 'status'])
        for mt, t in REMOVE:
            w.writerow(['ACCOUNT_LEVEL_LIST', 'REMOVE', mt, t, WHY.get(t, '04 negative_decisions ACCEPT REMOVE'), 'PROPOSAL_NOT_APPLIED'])
        for mt, t in ADD:
            w.writerow(['ACCOUNT_LEVEL_LIST', 'ADD', mt, t, 'used/weapon wording/pure navigation (04)', 'PROPOSAL_NOT_APPLIED'])
        for t, why in KEEP_NOTE.items():
            w.writerow(['ACCOUNT_LEVEL_LIST', 'KEEP', 'BROAD', t, why, 'unchanged'])
        for route, lst in ROUTES.items():
            for mt, t in lst:
                w.writerow([f'SO27 list attached to route {route}', 'ADD', mt, t, 'route-local', 'PROPOSAL_NOT_APPLIED'])
    res, bad = [], 0
    for route, q, reach, note in FIX:
        for variant in sorted({q, strip(q)}):
            now = rt.hits(variant, ACC)
            eff = rt.hits(variant, after + ROUTES[route])
            ok = (not eff) == reach
            bad += not ok
            res.append(dict(route=route, query=variant, expected='reach' if reach else 'blocked', blocked_now_by_account=';'.join(now) or '-',
                            blocked_after_effective=';'.join(eff) or '-', result='PASS' if ok else 'FAIL', note=note))
    with open(os.path.join(HERE, 'negatives_fixtures_results.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(res[0].keys())); w.writeheader(); w.writerows(res)
    print('account list', len(ACC), '-> after diff', len(after), '| REMOVE entries not found in live list:', missing)
    for r in res:
        if r['result'] == 'FAIL' or r['blocked_now_by_account'] != '-':
            print(r['result'], r['route'], r['query'], '| now:', r['blocked_now_by_account'], '| after:', r['blocked_after_effective'])
    print('fixtures', len(res) - bad, '/', len(res), 'PASS')
    return bad


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
