#!/usr/bin/env python3
"""04d p.4 + owner clarification: review v2 of all 258 account negatives.
Changes vs 04b account_negatives_review.csv (kept as history):
  * Catalogue examples are REAL products from the read-only shopping_product export 25.11 (offer_id + title + date),
    found by the same literal matching engine (routing_tests.neg_hit) for the word's own match type; if none ->
    NO_VERIFIED_CATALOG_EXAMPLE. Diacritic-folded matches are reported separately and never called literal.
  * Example queries are generated from the word itself and checked with neg_hit; they are marked
    'illustrative (not a historical search term)'. No search-term data (E5) is used or claimed.
  * Every word gets two literal tests: as stored and the other diacritic form (e.g. solarna / solárna).
  * Row-level proposed diff (not applied): per owner 25.11 clarification, relevant model queries with
    'kde (kúpiť) / poradiť / lacno / nie drahé / cheap / popis' should not be blocked; other commercial words stay
    OWNER_DECISION; heureka -> OWNER_DECISION_HEUREKA (navigational vs model + Heureka).
"""
import csv, json, os, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
CC = os.path.join(REPO, 'discussions/round-04/02_claude_code_attachments')
sys.path.insert(0, CC); sys.dont_write_bytecode = True
import routing_tests as rt  # noqa: E402

SRC_DATE = 'shopping_product 2026-11-25 (read-only)'
OLD_REVIEW = os.path.join(REPO, 'discussions/round-04/04b_claude_code_attachments/account_negatives_review.csv')
MODEL = 'leica trinovid 10x42 hd'          # sold model; used only for commercial-intent words

# Row-level proposals (owner direction 25.11). Each is a PROPOSAL; nothing is applied.
OWNER_ALLOWED = {   # owner: do not block relevant model queries with these intents
    'kde': ('REMOVE_BROAD_ADD_INFO_PHRASES', 'remove account BROAD kde; add account PHRASE "kde je", "kde sa nachádza", "kde pozorovať", "kde vidieť"'),
    'poradiť': ('REMOVE_BROAD', 'remove account BROAD poradiť (pick/choose intent)'),
    'lacno': ('REMOVE_BROAD', 'remove account BROAD lacno (cheap intent)'),
    'nie drahé': ('REMOVE_BROAD', 'remove account BROAD nie drahé'),
    'cheap': ('REMOVE_BROAD', 'remove account BROAD cheap'),
    'popis': ('REMOVE_BROAD', 'remove account BROAD popis (description intent)'),
}
STILL_OWNER = {'aký', 'ake', 'Ktoré', 'Správny', 'Nájsť', 'typy', 'druhy', 'stary'}
CATALOG = {'drony', 'dalekohlad s fotoaparatom', 'nevidiacich', 'slabozrakých', 'premietací prístroj', 'vzorka', 'casti'}


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if unicodedata.category(c) != 'Mn')


def other_form(w):
    """The other diacritic form of the word: folded if it has diacritics; else a known accented form if any."""
    f = fold(w)
    if f != w:
        return f
    known = {'solarna': 'solárna', 'stary': 'starý', 'lacno': 'lacno', 'zadarmo': 'zadarmo', 'casti': 'časti', 'casovac': 'časovač',
             'ake': 'aké', 'bazar': 'bazár', 'nivelak': 'nivelák', 'papier': 'papier', 'ruske': 'ruské', 'rusky': 'ruský',
             'naramky': 'náramky', 'dalekohlad s fotoaparatom': 'ďalekohľad s fotoaparátom', 'predam': 'predám', 'kniha': 'kniha'}
    return known.get(w, w)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    acc = [(n['matchType'], n['text']) for n in json.load(open(os.path.join(REPO, 'discussions/round-03/05_chatgpt_attachments/live_checks_2026-11-15.json'), encoding='utf-8'))['account_negative_keywords']]
    cat = [r for r in csv.DictReader(open(os.path.join(HERE, 'inputs/shopping_product_2026-11-25.csv'), encoding='utf-8')) if r['merchant_id'] == '5831333799']
    old = {(r['text'], r['match_type']): r for r in csv.DictReader(open(OLD_REVIEW, encoding='utf-8'))}
    out = []
    for mt, t in acc:
        o = old[(t, mt)]
        lit = [r for r in cat if rt.neg_hit(r['title'], mt, t)]
        litin = [r for r in lit if r['availability'] == 'IN_STOCK']
        fld = [r for r in cat if not rt.neg_hit(r['title'], mt, t) and rt.neg_hit(fold(r['title']), mt, fold(t))]
        ex = (litin or lit)[:1]
        model_intent = t in OWNER_ALLOWED or t in STILL_OWNER or t == 'heureka'
        alt = other_form(t)
        if model_intent and mt != 'EXACT':      # the question is whether a sold-model query with this word is blocked
            q_stored, q_alt = f'{t} {MODEL}'.lower(), f'{alt} {MODEL}'.lower()
        elif ex and mt != 'EXACT':              # a real product title that literally contains the word
            q_stored, q_alt = ex[0]['title'].lower(), fold(ex[0]['title']).lower() if fold(t) != t else ex[0]['title'].lower()
        else:                                   # minimal query: the word itself
            q_stored, q_alt = t.lower(), alt.lower()
        b_stored, b_alt = rt.neg_hit(q_stored, mt, t), rt.neg_hit(q_alt, mt, t)
        assert b_stored, (t, q_stored)                      # the illustrative query really contains the negative
        cls = o['word_class']
        if t == 'heureka':
            act, prop = 'OWNER_DECISION_HEUREKA', ('options: (1) keep BROAD heureka (blocks navigation AND "<model> heureka"); '
                                                  '(2) replace by EXACT [heureka], [heureka sk], [heureka.sk] + PHRASE "heureka recenzie" so "<model> heureka" can reach ads; '
                                                  'a test of (2) needs owner spend limit; not now')
        elif t in OWNER_ALLOWED:
            act, prop = 'PROPOSED_BY_OWNER_DIRECTION', OWNER_ALLOWED[t][1]
        elif t in STILL_OWNER:
            act, prop = 'OWNER_DECISION', 'not covered by the owner direction of 25.11; decide per word after search terms (E5)'
        elif t in CATALOG:
            act = 'OWNER_DECISION_CATALOG'
            prop = ('remove or narrow: literal catalogue match ' + (f'{ex[0]["offer_id"]} {ex[0]["title"][:60]}' if ex else 'none')
                    + ('; folded-only matches exist' if fld else ''))
        else:
            act, prop = o['recommended_action'], ('-' if o['recommended_action'] == 'KEEP' else o['rationale'])
        out.append(dict(
            text=t, match_type=mt, word_class=cls, action_v2=act, proposed_change=prop, level='ACCOUNT', status='PROPOSAL_NOT_APPLIED',
            catalogue_literal_matches=len(lit), catalogue_literal_in_stock=len(litin), catalogue_folded_only_matches=len(fld),
            catalogue_example_offer_id=ex[0]['offer_id'] if ex else 'NO_VERIFIED_CATALOG_EXAMPLE',
            catalogue_example_title=ex[0]['title'] if ex else '', catalogue_example_availability=ex[0]['availability'] if ex else '',
            catalogue_example_source=SRC_DATE if ex else '',
            folded_only_example=(f'{fld[0]["offer_id"]} {fld[0]["title"][:70]}' if fld else ''),
            illustrative_query_stored_form=q_stored, blocked_literal_stored_form=b_stored,
            illustrative_query_other_diacritic_form=q_alt if q_alt != q_stored else '', blocked_literal_other_form=(b_alt if q_alt != q_stored else ''),
            example_kind='illustrative (generated from the word; not a historical search term)',
            tests_blocked=o['tests_blocked'], uncertainty=o['uncertainty']))
    with open(os.path.join(HERE, 'account_negatives_review_v2.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
    from collections import Counter
    print('rows', len(out), Counter(r['action_v2'] for r in out))
    for r in out:
        if r['text'] in ('solarna', 'kniha', 'ovládanie', 'free', 'zadarmo', 'drony', 'dalekohlad s fotoaparatom', 'kde', 'heureka', 'stary'):
            print(f"{r['match_type']}:{r['text']} | lit {r['catalogue_literal_matches']} (in stock {r['catalogue_literal_in_stock']}) folded-only {r['catalogue_folded_only_matches']} | "
                  f"ex {r['catalogue_example_offer_id']} {r['catalogue_example_title'][:50]} | q '{r['illustrative_query_stored_form']}'={r['blocked_literal_stored_form']} "
                  f"'{r['illustrative_query_other_diacritic_form']}'={r['blocked_literal_other_form']} | {r['action_v2']}")


if __name__ == '__main__':
    main()
