#!/usr/bin/env python3
"""Round 5 move 3: line-by-line impact diff of proposed negative changes (R5-CHATGPT-06). No network, nothing applied.
Evidence base: (a) Marketing Miner SK core 26.11 (317 relevant keywords >= 30/month, volumes are MM estimates),
(b) ChatGPT/owner test queries (store, model+description/choice, device+kit, accessory sale).
Engine: routing_tests.neg_hit (literal; Google close variants are NOT simulated for negatives).
Outputs: negatives_impact_diff.csv, negatives_impact_tests.csv
"""
import csv, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'discussions/round-04/02_claude_code_attachments')); sys.dont_write_bytecode = True
import routing_tests as rt  # noqa

ACC = [(n['matchType'], n['text']) for n in json.load(open(os.path.join(REPO, 'discussions/round-03/05_chatgpt_attachments/live_checks_2026-11-15.json'), encoding='utf-8'))['account_negative_keywords']]
CORE = list(csv.DictReader(open(os.path.join(REPO, 'discussions/round-05/keyword_core/mm_core_relevant_ge30_2026-11-26.csv'), encoding='utf-8')))
ENABLED = 'Shopping 24440851839, 24440851881, 24451885423, 24451886281 (enabled); Search 24341095320, 24425793295 (enabled); all future campaigns'

# (level, action, match, text, scope_note, rationale)
P = [
 ('ACCOUNT', 'REMOVE', 'BROAD', 'kde', ENABLED, 'owner: do not block "kde kúpiť <model>"; NO global PHRASE replacement (would block "kde je predajňa")'),
 ('ACCOUNT', 'REMOVE', 'BROAD', 'poradiť', ENABLED, 'owner direction (pick/advice intent)'),
 ('ACCOUNT', 'REMOVE', 'BROAD', 'lacno', ENABLED, 'owner direction (cheap intent)'),
 ('ACCOUNT', 'REMOVE', 'BROAD', 'nie drahé', ENABLED, 'owner direction'),
 ('ACCOUNT', 'REMOVE', 'BROAD', 'cheap', ENABLED, 'owner direction'),
 ('ACCOUNT', 'REMOVE', 'BROAD', 'popis', ENABLED, 'owner direction; MM: "mikroskop popis" 100, "popis mikroskopu" 40 blocked today'),
 ('ACCOUNT', 'REMOVE', 'BROAD', 'keyword_text', ENABLED, 'CSV header artefact'),
 ('ACCOUNT', 'REMOVE', 'BROAD', 'slabozrakých', ENABLED, 'MM: "lupa na čítanie pre slabozrakých" 70 blocked; magnifiers are sold (catalogue decision)'),
 ('ACCOUNT', 'REMOVE', 'BROAD', 'nevidiacich', ENABLED, 'same family as slabozrakých (magnifiers for low vision); keep only if owner objects'),
 ('ACCOUNT', 'REMOVE', 'BROAD', 'drony', ENABLED, 'drones are sold (label drony); MM "dron s termokamerou" 320 is relevant'),
 ('ACCOUNT', 'REMOVE', 'PHRASE', 'dalekohlad s fotoaparatom', ENABLED, 'digital binoculars are sold; diacritic form not blocked anyway'),
 ('ACCOUNT', 'ADD', 'BROAD', 'bazár', ENABLED, 'used; account has bazar only'),
 ('ACCOUNT', 'ADD', 'BROAD', 'bazoš', ENABLED, 'used; MM "bazos" variants 3 760/month across seeds'),
 ('ACCOUNT', 'ADD', 'BROAD', 'predám', ENABLED, 'used; account has predam only'),
 ('ACCOUNT', 'ADD', 'PHRASE', 'na pušku', ENABLED, 'weapon wording (Google weapons policy + owner rule no hunting/weapon ads)'),
 ('ACCOUNT', 'ADD', 'PHRASE', 'na pusku', ENABLED, 'weapon wording, unaccented (MM: Slovaks mostly type without diacritics)'),
 ('ACCOUNT', 'ADD', 'PHRASE', 'na puškohľad', ENABLED, 'weapon wording'),
 ('ACCOUNT', 'ADD', 'PHRASE', 'na puskohlad', ENABLED, 'weapon wording, unaccented'),
 ('ACCOUNT', 'ADD', 'PHRASE', 'na gulovnicu', ENABLED, 'weapon wording'),
 ('ACCOUNT', 'ADD', 'PHRASE', 'na guľovnicu', ENABLED, 'weapon wording'),
 ('ACCOUNT', 'ADD', 'PHRASE', 'na vzduchovku', ENABLED, 'weapon wording'),
 ('ACCOUNT', 'ADD', 'BROAD', 'puskohlad', ENABLED, 'weapon optic category not advertised in Google'),
 ('ACCOUNT', 'ADD', 'BROAD', 'puškohľad', ENABLED, 'weapon optic category not advertised in Google'),
 ('ACCOUNT', 'ADD', 'BROAD', 'alza', ENABLED, 'competitor navigation'),
 ('ACCOUNT', 'ADD', 'BROAD', 'kaufland', ENABLED, 'competitor navigation'),
 ('ACCOUNT', 'ADD', 'BROAD', 'decathlon', ENABLED, 'competitor navigation'),
 ('ACCOUNT', 'ADD', 'BROAD', 'dráčik', ENABLED, 'competitor navigation'),
 ('ACCOUNT', 'ADD', 'BROAD', 'emos', ENABLED, 'brand not sold (weather stations)'),
 ('NEW_SEARCH_CAMPAIGN', 'ADD', 'PHRASE', 'kde pozorovať', 'new model/category Search only', 'informational kde form, local to new Search; Shopping keeps kde open'),
 ('NEW_SEARCH_CAMPAIGN', 'ADD', 'PHRASE', 'kde vidieť', 'new model/category Search only', 'informational'),
 ('NEW_SEARCH_CAMPAIGN', 'ADD', 'PHRASE', 'ako funguje', 'new model/category Search only', 'research; Shopping keeps it open (account funguje stays)'),
 ('STATIV_GROUP', 'ADD', 'BROAD', 'statiny / statíny / státia / statia / statik / static / zákaz', 'only an ad group or campaign that bids on "stativ"', 'MM: 19 910 irrelevant searches around "stativ" (statins, parking sign)'),
 ('PULSAR_GROUP', 'ADD', 'BROAD', 'nissan / hodinky / salomon / salamon / wallbox', 'only Pulsar Search groups', 'MM: 4 670 irrelevant searches around "pulsar"'),
 ('ACCOUNT', 'KEEP', 'BROAD', 'aký / ake / Ktoré / Správny / Nájsť / typy / druhy / stary', ENABLED, 'not covered by owner direction; kept with explicit coverage limit (blocked queries cannot appear in search terms)'),
 ('ACCOUNT', 'KEEP', 'BROAD', 'heureka', ENABLED, 'OWNER_DECISION_HEUREKA, test deferred'),
]

TESTS = [  # query, should a SALES query reach ads? (True) or be blocked (False), note
 ('kde je predajňa sonata optics', True, 'store question (ChatGPT): must not be blocked'),
 ('kde kúpiť leica trinovid 10x42 hd', True, 'model + where to buy'),
 ('kde kupit dalekohlad bratislava', True, 'category + where to buy, unaccented'),
 ('leica trinovid 10x42 popis', True, 'model + description'),
 ('ako vybrať ďalekohľad leica', True, 'model choice (research), allowed by owner direction? stays blocked only by own campaign negatives'),
 ('ďalekohľad leica s puzdrom', True, 'device + kit'),
 ('puzdro na ďalekohľad', True, 'accessory sale: must reach accessory Shopping'),
 ('dalekohlad lacno', True, 'cheap intent (owner direction)'),
 ('lupa na čítanie pre slabozrakých', True, 'magnifier for low vision'),
 ('dron s termokamerou', True, 'sold drones'),
 ('nocne videnie na pusku', False, 'weapon wording must be blocked'),
 ('nočné videnie na puškohľad', False, 'weapon wording must be blocked'),
 ('dalekohlad na vzduchovku', False, 'weapon wording must be blocked'),
 ('meteostanica alza', False, 'competitor navigation'),
 ('ďalekohľad bazár', False, 'used'),
 ('predám ďalekohľad', False, 'used'),
 ('teleskop pre deti dracik', False, 'competitor navigation'),
]


def apply(base):
    acc = list(base)
    for lvl, act, mt, text, _, _ in P:
        if lvl != 'ACCOUNT' or act == 'KEEP':
            continue
        if act == 'REMOVE':
            acc = [(m, t) for m, t in acc if not (m == mt and t == text)]
        else:
            acc.append((mt, text))
    return acc


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    after = apply(ACC)
    rows = []
    for lvl, act, mt, text, scope, why in P:
        terms = [x.strip() for x in text.split('/')] if '/' in text else [text]
        hit = [r for r in CORE if any(rt.neg_hit(r['keyword'], mt, t) for t in terms)]
        vol = sum(int(r['search_volume_sk']) for r in hit)
        rows.append(dict(level=lvl, action=act, match_type=mt, negative=text, applies_to=scope,
                         mm_core_keywords_matched=len(hit), mm_core_volume_matched=vol,
                         examples='; '.join(f"{r['keyword']} ({r['search_volume_sk']})" for r in hit[:4]),
                         effect=('UNBLOCKS these relevant queries' if act == 'REMOVE' else ('BLOCKS these relevant queries - check!' if act == 'ADD' and hit else ('blocks nothing in relevant core' if act == 'ADD' else 'unchanged'))),
                         rationale=why, status='PROPOSAL_NOT_APPLIED'))
    with open(os.path.join(HERE, 'negatives_impact_diff.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    tr, bad = [], 0
    for q, sale, note in TESTS:
        now = [f'{m}:{t}' for m, t in ACC if rt.neg_hit(q, m, t)]
        aft = [f'{m}:{t}' for m, t in after if rt.neg_hit(q, m, t)]
        ok = (not aft) == sale
        bad += not ok
        tr.append(dict(query=q, expected='reach ads' if sale else 'blocked', account_now=';'.join(now) or '-', account_after=';'.join(aft) or '-',
                       result='PASS' if ok else 'FAIL', note=note))
    with open(os.path.join(HERE, 'negatives_impact_tests.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(tr[0].keys())); w.writeheader(); w.writerows(tr)
    blocked_now = sum(int(r['search_volume_sk']) for r in CORE if any(rt.neg_hit(r['keyword'], m, t) for m, t in ACC))
    blocked_after = [r for r in CORE if any(rt.neg_hit(r['keyword'], m, t) for m, t in after)]
    print('core volume blocked by account list now', blocked_now, '| after', sum(int(r['search_volume_sk']) for r in blocked_after), [r['keyword'] for r in blocked_after])
    for r in rows:
        if r['action'] == 'ADD' and r['mm_core_keywords_matched']:
            print('ADD hits relevant core:', r['negative'], r['examples'])
    for t in tr:
        print(t['result'], t['query'], '| now:', t['account_now'], '| after:', t['account_after'])
    print('tests', len(tr) - bad, '/', len(tr))


if __name__ == '__main__':
    main()
