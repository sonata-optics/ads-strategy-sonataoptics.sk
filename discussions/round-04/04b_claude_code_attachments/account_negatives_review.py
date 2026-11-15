#!/usr/bin/env python3
"""Review of all 258 account-level negatives (R4-CLAUDE-01/08, R4-CHATGPT-05). No network.

Inputs: live_checks_2026-11-15.json (258 negatives, verbatim), 02 package routing_tests.csv (which tests each
word blocks), Merchant titles 14.11 (data/catalog) joined to availability 15.11 (04_chatgpt_attachments).
Output: account_negatives_review.csv - one row per negative, text/case/diacritics/match type kept verbatim.

A class is a description, never an automatic action: informational words are not auto-kept,
product-type words are not auto-removed. Every non-KEEP action is an owner decision or a proposal.
"""
import csv, glob, json, os, re, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
CC = os.path.join(REPO, 'discussions/round-04/02_claude_code_attachments')
sys.path.insert(0, CC)
sys.dont_write_bytecode = True
import routing_tests as rt  # noqa: E402  (same matching engine as the routing tests)

APPLIES_TO = ('all Search and Shopping campaigns of the account incl. future pilot/new campaigns '
              '(enabled now: Shopping 24440851839, 24440851881, 24446149352, 24451885423, 24451886281; '
              'Search 24341095320, 24425793295; ended 03.11: 24341660055, 24346760069, 24346760072)')

# class, action, useful query it blocks (example), unwanted query it blocks (example), rationale, uncertainty
C = {}
def put(words, cls, action, useful, unwanted, why, unc):
    for w in words:
        C[w] = (cls, action, useful, unwanted, why, unc)

put(['kde', 'aký', 'ake', 'Ktoré', 'Správny', 'poradiť', 'Nájsť', 'popis', 'typy', 'druhy'], 'commercial_or_research_modifier', 'OWNER_DECISION',
    'kde kúpiť leica trinovid 10x42 hd / aký ďalekohľad na poľovačku', 'kde pozorovať kométu / druhy hviezd',
    'Pre-purchase modifiers block model queries in Search and Shopping (routing_tests).', 'Share of buyers vs researchers unknown without search terms (E5).')
put(['lacno', 'nie drahé', 'cheap'], 'price_modifier', 'OWNER_DECISION', 'ďalekohľad lacno 10x42', 'lacno zadarmo hry',
    'Price-intent buyers; margin impact unknown.', 'Conversion of price queries unknown.')
put(['heureka'], 'comparison_site', 'OWNER_DECISION', 'leica trinovid heureka', 'heureka recenzie obchodu', 'Heureka is a separate channel decision.', 'Unknown share of buyers.')
put(['stary'], 'condition_or_generation', 'OWNER_DECISION', 'vegas ed stary model', 'stary ruský ďalekohľad', 'Blocks old-generation model intent; "starý" not blocked (inconsistent).', 'Antique traffic volume unknown.')
put(['drony'], 'product_type_in_catalogue', 'OWNER_DECISION_CATALOG', 'termovízne drony autel', 'drony pre deti hračka', 'Label drony: 5 IN_STOCK on 15.11.', 'Which drone queries are relevant is unknown.')
put(['dalekohlad s fotoaparatom'], 'product_type_in_catalogue', 'OWNER_DECISION_CATALOG', 'dalekohlad s fotoaparatom', '-', 'Digital binocular sold; diacritic form not blocked.', 'Low volume.')
put(['nevidiacich', 'slabozrakých'], 'product_type_in_catalogue', 'OWNER_DECISION_CATALOG', 'lupa pre slabozrakých', 'písmo pre nevidiacich',
    'Magnifiers are sold (label lupy, 25 IN_STOCK): low-vision buyers are a real lupa audience.', 'Healthcare-like wording may need policy care.')
put(['premietací prístroj'], 'product_type_in_catalogue', 'OWNER_DECISION_CATALOG', 'premietací prístroj hviezdnej oblohy', 'premietací prístroj na filmy',
    'Home planetaria (projectors) are sold (label domáce planetáriá).', 'Mostly film projector traffic probably.')
put(['vzorka'], 'product_type_in_catalogue', 'OWNER_DECISION_CATALOG', 'mikroskop vzorka preparát', 'vzorka zmluvy',
    'Microscope sample/slide queries; 887 microscope accessories in stock.', 'Ambiguous word.')
put(['casti'], 'product_type_in_catalogue', 'OWNER_DECISION_CATALOG', 'casti teleskopu náhradné', 'casti tela', 'Spare parts/accessories are sold.', 'Mostly informational probably.')
put(['nivelak', 'úniku plynu', 'casovac'], 'possible_product_type', 'REVIEW_WITH_CATALOGUE', 'nivelak laserový', 'detektor úniku plynu návod',
    'Measuring instruments are sold (label meracie nástroje 139 IN_STOCK); check whether these types are in the assortment.', 'Catalogue title check below; may be unrelated.')
put(['ovládanie', 'kniha', 'kúzelnícka sada', 'solarna', 'papier', 'samolepiaci'], 'word_in_some_titles', 'REVIEW_WITH_CATALOGUE', 'RA motor + ovládanie', 'ovládanie tv',
    'Word appears in catalogue titles or adjacent kids/astro products.', 'Mostly unrelated traffic probably.')
put(['zadarmo', 'free', 'bez nákladov', 'pre nič', 'download', 'torrent', 'torrents', 'torent', 'torents', 'firmvéru'], 'free_or_download', 'KEEP',
    '"<fotopasca> + SD karta zadarmo" (title wording, rare as query)', 'teleskop zadarmo / download návod', 'Free/download intent.', 'zadarmo/free also appear in 4 titles (Cowork).')
put(['bazar', 'bazos', 'predam', 'kúpil', 'objednal', 'volal'], 'used_or_post_purchase', 'KEEP', '-', 'ďalekohľad bazar / objednal som kedy príde',
    'Used market or post-purchase service queries.', 'bazár (diacritics) not in list: proposal ADD.')
put(['amazon', 'aliexpress', 'temu', 'lidl', 'datart', 'wildberries', 'xiaomi', 'sencor', 'auriol', 'planeo', 'tenolix', 'reekon', 'dracik'], 'other_retailer_or_brand_not_sold', 'KEEP',
    '-', 'ďalekohľad lidl / xiaomi monokulár', 'Retailers or brands Sonata does not sell (verify against catalogue).', 'If a brand enters assortment, remove.')
put(['porn', 'porno', 'sex', 'erotika', 'erotické'], 'adult', 'KEEP', '-', 'self-explanatory', 'Brand safety.', 'none')
put(['wiki', 'wikipedia', 'blog', 'faq', 'fórum', 'článok', 'čítať', 'definícia', 'funguje', 'Prečo', 'Čo', 'Toto', 'metódy', 'technológie', 'správa', 'správy',
     'poučenie', 'triky', 'robiť', 'vytvoriť', 'písať', 'naladiť', 'dať', 'spôsobom', 'zvládanie', 'vyzerá', 'sníval', 'kniha snov', 'Obrázky', 'ikonu', 'tapeta',
     'vektor', 'abstraktné', 'grafické umenie', 'schémy', 'krajiny', 'Domy', 'ruky', 'sám za seba', 'ich'],
    'informational', 'KEEP', 'rare: "ako funguje <model>" before purchase', 'ako funguje ďalekohľad / obrázky mesiaca', 'Informational/content intent.', 'Some pre-purchase research is lost; acceptable unless search terms show buyers.')
put(['diplom', 'diplomovej práce', 'dizertačnej práce', 'ročníková práca', 'učebnica', 'spolužiakov', 'registrácia', 'suhlas so spracovanim', 'gdpr zákon',
     'zákon o ochrane osobných údajov', 'zmluvy', 'reklama', 'Job', 'voľné pracovné miesto', 'vodič', 'habr', 'habra', 'habrhabr'],
    'education_legal_jobs', 'KEEP', '-', 'diplomová práca optika', 'Not shopping intent.', 'none')
put(['hudba', 'piesne', 'klip', 'humor', 'vtip', 'vtipný', 'recept', 'variť', 'naramky', 'postieľka', 'ostrohy', 'zavlahu', 'zlúčenina', 'ceruzka', 'studio light',
     'studiyne svitlo', 'štúdiové svetlo', 'prehliadač', 'ussr', 'ruske', 'rusky', 'ruský'],
    'unrelated_topic', 'KEEP', '-', 'hudba klip', 'Unrelated topic.', 'ussr/ruský also catch "ruský ďalekohľad" (antique) - intended.')
put(['keyword_text'], 'junk_import_artifact', 'REMOVE', '-', '-', 'CSV header imported as a keyword.', 'none')


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s.lower()) if unicodedata.category(c) != 'Mn')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    with open(os.path.join(REPO, 'discussions/round-03/05_chatgpt_attachments/live_checks_2026-11-15.json'), encoding='utf-8') as f:
        acc = [(n['matchType'], n['text']) for n in json.load(f)['account_negative_keywords']]
    titles = {}
    for p in sorted(glob.glob(os.path.join(REPO, 'data/catalog/2026-11-14/merchant-*.json'))):
        for m in json.load(open(p, encoding='utf-8')):
            titles[m['offerId']] = m.get('title') or ''
    avail = {}
    with open(os.path.join(REPO, 'discussions/round-04/04_chatgpt_attachments/catalog_coverage_2026-11-15.csv'), encoding='utf-8') as f:
        for r in csv.DictReader(f):
            avail[r['offer_id']] = r['availability']
    tests = {}
    with open(os.path.join(CC, 'routing_tests.csv'), encoding='utf-8') as f:
        for r in csv.DictReader(f):
            for h in r['account_neg_hits_literal'].split(';'):
                if h:
                    tests.setdefault(h, []).append(r['test_id'])
    rows = []
    for mt, t in acc:
        cyr = bool(re.search('[Ѐ-ӿ]', t))
        if cyr:
            cls, act, useful, unwanted, why, unc = ('off_market_language_ru_uk', 'KEEP', '-', 'скачать бесплатно',
                                                    'Cyrillic query on the SK market; informational/free/marketplace words.', 'none for SK shopping')
        elif t in C:
            cls, act, useful, unwanted, why, unc = C[t]
        else:
            cls, act, useful, unwanted, why, unc = ('UNCLASSIFIED', 'REVIEW', '-', '-', 'not classified', 'needs review')
        hits_lit = [o for o, ti in titles.items() if ti and rt.neg_hit(ti, mt, t)]
        hits_fold = [o for o, ti in titles.items() if ti and rt.neg_hit(fold(ti), mt, fold(t))]
        in_stock = [o for o in hits_fold if avail.get(o) == 'IN_STOCK']
        th = tests.get(f'{mt}:{t}', [])
        if act == 'KEEP' and (in_stock or [x for x in th if x not in ('R45', 'C10', 'R43', 'R44')]):
            act = 'REVIEW_WITH_CATALOGUE'   # never keep silently when it touches stocked titles or commercial tests
        rows.append(dict(text=t, match_type=mt, script='cyrillic' if cyr else 'latin', has_diacritics=fold(t) != t.lower(),
                         word_class=cls, recommended_action=act,
                         level='ACCOUNT (current); any change only after owner decision',
                         applies_to=APPLIES_TO,
                         catalogue_titles_literal=len(hits_lit), catalogue_titles_diacritic_folded=len(hits_fold),
                         catalogue_in_stock_15_11=len(in_stock), catalogue_examples=' || '.join(titles[o][:70] for o in in_stock[:2]),
                         tests_blocked=';'.join(th), useful_query_blocked_example=useful, unwanted_query_blocked_example=unwanted,
                         rationale=why, uncertainty=unc, status='PROPOSAL_NOT_APPLIED'))
    out = os.path.join(HERE, 'account_negatives_review.csv')
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    from collections import Counter
    print('negatives', len(rows), 'unique', len({(r['text'], r['match_type']) for r in rows}))
    print('classes', Counter(r['word_class'] for r in rows))
    print('actions', Counter(r['recommended_action'] for r in rows))
    for r in rows:
        if r['recommended_action'] != 'KEEP':
            print(f"  {r['match_type']}:{r['text']} -> {r['recommended_action']} | titles {r['catalogue_titles_diacritic_folded']} in_stock {r['catalogue_in_stock_15_11']} | tests {r['tests_blocked']}")


if __name__ == '__main__':
    main()
