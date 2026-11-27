#!/usr/bin/env python3
"""Round 5 move 13: executable SO27 Search package (R5-CODE-14). Generates keywords, RSAs, cross-routing negatives and checks.
Inputs: MM core (keyword_core/mm_core_relevant_ge30_2026-11-26.csv), brand variant ids (site filter links), in-stock counts per
brand x category (SK Merchant scan 26.11, ads_ok + in_stock). Outputs: search_keywords.csv, search_rsa.csv, search_negatives.csv,
search_checks.txt. --check-landing fetches every final URL (honest UA) and records HTTP code + product count. Nothing is applied.
Copy rules (CLAUDE.md + owner): Slovak with diacritics; never "Exkluzívne"; status claims only where true: "Oficiálny distribútor"
Meopta/Levenhuk/Unistellar, "Autorizovaný predajca" Leica, Pulsar not in this package; no other brand gets a status claim;
no hunting/weapon words; no emoji; headline <= 30, description <= 90 chars; no "skladom" promise for a whole brand."""
import csv, json, os, re, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); R5 = os.path.dirname(HERE)
SITE = 'https://sonataoptics.sk'
# ---------------- 1. Kategórie (generic commercial demand) ----------------
CAT = {  # ad group: (final url, [(keyword, match)])  keywords come from MM core; E = exact, P = phrase; unaccented variants included
 'Teleskopy': ('/teleskopy/', [('teleskop', 'E'), ('teleskopy', 'E'), ('teleskop cena', 'P'), ('teleskop na hviezdy', 'P'), ('hvezdarsky teleskop', 'P'),
               ('hvezdársky teleskop', 'P'), ('astronomicky teleskop', 'P'), ('teleskop hvezdarsky', 'P'), ('teleskop pre zaciatocnikov', 'P'), ('teleskop pre začiatočníkov', 'P')]),
 'Hvezdárske ďalekohľady': ('/teleskopy/', [('dalekohlad na hviezdy', 'P'), ('ďalekohľad na hviezdy', 'P'), ('hvezdarsky dalekohlad', 'P'), ('hvezdársky ďalekohľad', 'P'),
               ('astronomicky dalekohlad', 'P'), ('astronomický ďalekohľad', 'P'), ('hviezdny dalekohlad', 'P'), ('dalekohlad na pozorovanie hviezd', 'P')]),
 'Teleskopy pre deti': ('/teleskopy/?features_hash=509-66472', [('teleskop pre deti', 'P'), ('detsky teleskop', 'P'), ('detský teleskop', 'P'), ('teleskop detsky', 'P'),
               ('detsky dalekohlad na hviezdy', 'P'), ('dalekohlad na hviezdy pre deti', 'P'), ('detsky hvezdarsky dalekohlad', 'P'), ('hvezdarsky dalekohlad pre deti', 'P')]),
 'Ďalekohľady': ('/dalekohlady/', [('dalekohlad', 'E'), ('ďalekohľad', 'E'), ('dalekohlady', 'E'), ('ďalekohľady', 'E'), ('binokularny dalekohlad', 'P'), ('binokulárny ďalekohľad', 'P'),
               ('turisticky dalekohlad', 'P'), ('kvalitny dalekohlad', 'P'), ('dalekohlad cena', 'P'), ('dalekohlad na pozorovanie vtakov', 'P'), ('pozorovaci dalekohlad', 'P')]),
 'Ďalekohľady 10x50 a 10x42': ('/dalekohlady/dalekohlady-10x50/', [('dalekohlad 10x50', 'P'), ('ďalekohľad 10x50', 'P'), ('dalekohled 10x50', 'P'), ('dalekohlad 10x42', 'P'),
               ('dalekohlad 8x42', 'P'), ('dalekohlad 12x50', 'P'), ('dalekohlad 8x56', 'P'), ('ďalekohľad 8x56', 'P'), ('dalekohlad 10x56', 'P')]),
 'Astronomické binokuláre': ('/dalekohlady/astronomicke-binokulare-na-nocnu-oblohu/', [('dalekohlad 20x50', 'P'), ('astronomicky binokular', 'P'), ('astronomický binokulár', 'P'), ('binokular na hviezdy', 'P')]),
 'Detské ďalekohľady': ('/dalekohlady/?features_hash=509-66472', [('detsky dalekohlad', 'P'), ('detský ďalekohľad', 'P'), ('dalekohlad pre deti', 'P'), ('ďalekohľad pre deti', 'P'), ('dalekohlad detsky', 'P')]),
 'Mikroskopy': ('/mikroskopy/', [('mikroskop', 'E'), ('mikroskopy', 'E'), ('mikroskop cena', 'P'), ('mikroskop predaj', 'P'), ('opticky mikroskop', 'P'), ('optický mikroskop', 'P'), ('mikroskop popis', 'P')]),
 'Mikroskopy pre deti a školské': ('/mikroskopy/skolske-a-studentske-mikroskopy/', [('mikroskop pre deti', 'P'), ('detsky mikroskop', 'P'), ('detský mikroskop', 'P'), ('detske mikroskopy', 'P'),
               ('skolsky mikroskop', 'P'), ('školský mikroskop', 'P')]),
 'Digitálne mikroskopy': ('/mikroskopy/digitalne-mikroskopy/', [('digitalny mikroskop', 'P'), ('digitálny mikroskop', 'P'), ('usb mikroskop', 'P'), ('digitálne mikroskopy', 'P'), ('digitálny mikroskop pre deti', 'P')]),
 'Stereomikroskopy': ('/mikroskopy/stereoskopicke-mikroskopy/', [('stereomikroskop', 'P'), ('stereo mikroskop', 'P'), ('stereoskopický mikroskop', 'P'), ('stereoskopické mikroskopy', 'P')]),
}
CAT_RSA = {
 'tel': (['Teleskopy | Sonata Optics', 'Teleskopy pre začiatočníkov', 'Hvezdárske ďalekohľady', 'Teleskopy aj pre deti', 'Poradíme s výberom teleskopu',
          'Predajňa v Bratislave', 'Vyskúšajte v predajni', 'Doprava po celom Slovensku', 'Refraktory, Newtony aj SCT', 'Teleskop ako darček',
          'Montáže a okuláre', 'Celestron a Sky-Watcher', 'Odborné poradenstvo', 'Špecialisti na astronómiu', 'Nákup s istotou'],
         ['Teleskopy pre začiatočníkov aj pokročilých. Pomôžeme vybrať ten správny model.', 'Predajňa v Bratislave, doprava po celom Slovensku. Poradíme pred nákupom.',
          'Refraktory, Newtonove teleskopy aj Schmidt-Cassegrain. Montáže a príslušenstvo.', 'Hľadáte darček? Teleskopy pre deti aj dospelých s odbornou radou.']),
 'bin': (['Ďalekohľady | Sonata Optics', 'Ďalekohľady 8x42, 10x42, 10x50', 'Ďalekohľady na prírodu', 'Ďalekohľady pre deti', 'Poradíme s výberom',
          'Predajňa v Bratislave', 'Vyskúšajte v predajni', 'Doprava po celom Slovensku', 'Leica, Zeiss, Meopta, Minox', 'Ďalekohľad ako darček',
          'Kompaktné aj astronomické', 'Odborné poradenstvo', 'Špecialisti na optiku', 'Nákup s istotou', 'Turistické ďalekohľady'],
         ['Ďalekohľady na turistiku, prírodu aj hviezdy. Pomôžeme vybrať zväčšenie a objektív.', 'Predajňa v Bratislave, doprava po celom Slovensku. Poradíme pred nákupom.',
          'Od vreckových modelov po prémiovú optiku Leica, Zeiss a Meopta.', 'Hľadáte darček? Ďalekohľady pre deti aj dospelých s odbornou radou.']),
 'mic': (['Mikroskopy | Sonata Optics', 'Mikroskopy pre deti a školy', 'Biologické a stereo mikroskopy', 'Digitálne mikroskopy', 'Poradíme s výberom',
          'Predajňa v Bratislave', 'Doprava po celom Slovensku', 'Mikroskop ako darček', 'Euromex, Kern, Bresser', 'Ponuky pre školy a firmy',
          'Odborné poradenstvo', 'Špecialisti na mikroskopiu', 'Nákup s istotou', 'Kamery a príslušenstvo', 'Mikroskopy na každú prácu'],
         ['Mikroskopy pre deti, školy, laboratóriá aj priemysel. Pomôžeme s výberom.', 'Predajňa v Bratislave, doprava po celom Slovensku. Poradíme pred nákupom.',
          'Biologické, stereo aj digitálne mikroskopy. Kamery, objektívy a príslušenstvo.', 'Hľadáte darček? Mikroskopy pre deti so sadou preparátov a radou.']),
}
CAT_RSA_OF = lambda g: 'tel' if 'eleskop' in g or 'Hvezd' in g else ('mic' if 'ikroskop' in g else 'bin')
# ---------------- 2. Značky a modely (brand x category; brands with >= 8 in-stock ads_ok items, 26.11; Meopta kept: official distributor) ----------------
V = {'Levenhuk': '37169', 'Bresser': '37168', 'Celestron': '65727', 'Sky-Watcher': '52381', 'Omegon': '44874', 'William Optics': '65457', 'Vixen': '67350',
     'National Geographic': '82684', 'Explore Scientific': '45963', 'Leica': '52912', 'Zeiss': '52902', 'Minox': '52916', 'Vortex': '53544', 'Delta': '125968',
     'Discovery': '37167', 'Meopta': '53392', 'Euromex': '95557', 'Kern': '95560', 'MAGUS': '55533', 'Kelvin': '97877'}
BRANDS = {'teleskopy': ['Sky-Watcher', 'Celestron', 'Omegon', 'Levenhuk', 'Bresser', 'William Optics', 'Vixen', 'National Geographic', 'Explore Scientific', 'Discovery'],
          'dalekohlady': ['Levenhuk', 'Omegon', 'Bresser', 'Leica', 'Zeiss', 'Minox', 'Celestron', 'Vortex', 'Delta', 'National Geographic', 'Discovery', 'Meopta'],
          'mikroskopy': ['Euromex', 'Kern', 'Bresser', 'MAGUS', 'Levenhuk', 'Omegon', 'Kelvin', 'Discovery']}
STATUS = {'Meopta': 'Oficiálny distribútor Meopta', 'Levenhuk': 'Oficiálny distribútor Levenhuk', 'Leica': 'Autorizovaný predajca Leica'}
NOUN = {'teleskopy': [('teleskop', 'teleskop'), ('teleskopy', 'teleskopy'), ('hvezdársky ďalekohľad', 'hvezdarsky dalekohlad')],
        'dalekohlady': [('ďalekohľad', 'dalekohlad'), ('ďalekohľady', 'dalekohlady'), ('binokulár', 'binokular')],
        'mikroskopy': [('mikroskop', 'mikroskop'), ('mikroskopy', 'mikroskopy'), ('stereomikroskop', 'stereomikroskop')]}
TITLE = {'teleskopy': 'Teleskopy', 'dalekohlady': 'Ďalekohľady', 'mikroskopy': 'Mikroskopy'}
MODELS = [  # (ad group, final url = PDP, keywords): heroes with purchases, in stock 26.11
 ('Celestron AstroMaster 114EQ', '/teleskop-celestron-astromaster-114eq-teleskop.html', ['celestron astromaster 114eq', 'astromaster 114eq', 'celestron astromaster 114']),
 ('Celestron StarSense LT 70AZ', '/teleskop-celestron-starsense-explorer-lt-70az.html', ['starsense explorer lt 70az', 'celestron starsense lt 70az', 'celestron starsense 70az']),
 ('Celestron C8 XLT OTA', '/teleskop-celestron-8-sc-xlt-tubus-ota-mit-3-schiene-76mm.html', ['celestron c8', 'celestron c8 xlt', 'celestron c8 ota']),
 ('Sky-Watcher Explorer 130 EQ2', '/product-47488.html', ['sky-watcher explorer 130', 'skywatcher explorer 130', 'explorer 130 eq2']),
 ('Bresser Messier AR-127S', '/bresser-teleskop-ac-127s-635-messier-exos-2.html', ['bresser messier ar-127s', 'messier ar 127s', 'bresser ar-127s']),
 ('National Geographic 114/900', '/bresser-national-geographic-114-900-az-telescope.html', ['national geographic 114/900', 'national geographic teleskop 114', 'national geographic 114 900']),
 ('Bresser Junior 70/900', '/bresser-junior-teleskop-ac-70-900-el.html', ['bresser junior 70/900', 'bresser junior teleskop', 'bresser junior 70 900']),
 ('Vortex Crossfire HD 12x50', '/alekohlad-vortex-crossfire-hd-12x50-ru-sk.html', ['vortex crossfire hd 12x50', 'vortex crossfire 12x50', 'crossfire hd 12x50']),
 ('Bresser Condor 10x42', '/bresser-condor-ur-10x42-binoculars.html', ['bresser condor 10x42', 'bresser condor ur 10x42', 'condor 10x42']),
 ('Levenhuk Karma PLUS 10x42', '/levenhuk-new-karma-plus-10x42.html', ['levenhuk karma plus 10x42', 'levenhuk karma 10x42', 'karma plus 10x42']),
 ('Bresser Erudit Basic Bino', '/bresser-erudit-basic-bino-40x-400x-mikroskop.html', ['bresser erudit basic', 'bresser erudit bino', 'erudit basic bino']),
 ('Omegon Binofield', '/omegon-mikroskop-binofield-40800-led.html', ['omegon binofield', 'binofield 40-800x', 'omegon binofield mikroskop']),
]
MODEL_RSA_D = ['Overený model s odbornou radou. Predajňa v Bratislave, doprava po Slovensku.', 'Pred nákupom poradíme s príslušenstvom a použitím. Bezpečný nákup.',
               'Aktuálna cena a dostupnosť na stránke produktu. Sonata Optics.', 'Špecialisti na optiku – teleskopy, ďalekohľady a mikroskopy.']
# ---------------- 3. Predajňa (new groups inside the existing campaign) ----------------
STORE = {
 'Predajňa – značka a adresa': ('/kontakt/', [('sonata optics', 'E'), ('sonata optics bratislava', 'E'), ('sonata optics predajna', 'E'), ('sonata optics predajňa', 'E'), ('sonataoptics', 'E')]),
 'Predajňa – teleskopy a mikroskopy': ('/kontakt/', [('teleskopy bratislava', 'E'), ('teleskop bratislava', 'E'), ('mikroskopy bratislava', 'E'), ('mikroskop bratislava', 'E'),
                                                      ('teleskop predajna bratislava', 'E'), ('mikroskop predajna bratislava', 'E')]),
 'Predajňa – ďalekohľady': ('/kontakt/', [('dalekohlady bratislava', 'E'), ('ďalekohľady bratislava', 'E'), ('dalekohlad bratislava', 'E'), ('dalekohlad predajna bratislava', 'E')]),
 'Predajňa – poradenstvo a osobný odber': ('/kontakt/', [('optika predajna bratislava', 'P'), ('astronomicka predajna', 'P'), ('predajna teleskopov', 'P'), ('predajna dalekohladov', 'P')]),
}
STORE_RSA = (['Predajňa Sonata Optics', 'Showroom v Bratislave', 'Pri Suchom mlyne 29', 'Vyskúšajte optiku osobne', 'Poradíme s výberom',
              'Osobný odber v Bratislave', 'Teleskopy a mikroskopy', 'Ďalekohľady na vyskúšanie', 'Odborné poradenstvo', 'Navštívte našu predajňu'],
             ['Pozrite si optiku osobne v Bratislave, Pri Suchom mlyne 29. Poradíme s výberom.', 'Pred návštevou si overte dostupnosť vybraného modelu. Osobný odber možný.',
              'Teleskopy, ďalekohľady a mikroskopy – predvedenie a odborná rada v predajni.'])
BANNED = re.compile(r'exkluzív|výhradn|poľov|polov|(?<![a-záäčďéíĺľňóôŕšťúýž])lov(?![a-záäčďéíĺľňóôŕšťúýž])|zbra|pušk|pusk|oficiálny predajca|skladom', re.I)

CANON = json.load(open(os.path.join(HERE, 'landing_canonical_urls.json'), encoding='utf-8')) if os.path.exists(os.path.join(HERE, 'landing_canonical_urls.json')) else {}

def rows():
    kw, rsa, neg = [], [], []
    for g, (url, ks) in CAT.items():
        for k, m in ks:
            kw.append(['SO27 | SEARCH | Kategórie', g, k, {'E': 'EXACT', 'P': 'PHRASE'}[m], CANON.get(SITE + url, SITE + url)])
        h, d = CAT_RSA[CAT_RSA_OF(g)]
        rsa.append(['SO27 | SEARCH | Kategórie', g, CANON.get(SITE + url, SITE + url), h, d])
    for cat, brands in BRANDS.items():
        for b in brands:
            g = f'{TITLE[cat]} | {b}'; url = f'{SITE}/{cat}/?features_hash=509-{V[b]}'; url = CANON.get(url, url)  # site redirects brand filters to SEO subcategories
            for acc, plain in NOUN[cat]:
                for k in {f'{b.lower()} {acc}', f'{acc} {b.lower()}', f'{b.lower().replace("-", " ")} {plain}', f'{plain} {b.lower().replace("-", " ")}'}:
                    kw.append(['SO27 | SEARCH | Značky a modely', g, k, 'PHRASE', url])
            h = [f'{TITLE[cat]} {b}'[:30], f'{b} | Sonata Optics'[:30], f'Celý výber {b}'[:30], 'Predajňa v Bratislave', 'Poradíme s výberom', 'Doprava po celom Slovensku',
                 'Odborné poradenstvo', 'Vyskúšajte v predajni', 'Nákup s istotou', 'Aktuálne ceny online']
            if b in STATUS: h.insert(2, STATUS[b][:30])
            d = [f'{TITLE[cat]} {b} – aktuálna ponuka a ceny. Pomôžeme vybrať správny model.'[:90], 'Predajňa v Bratislave, doprava po celom Slovensku. Poradíme pred nákupom.',
                 'Odborná rada k výberu aj príslušenstvu. Sonata Optics – špecialisti na optiku.']
            if b in STATUS: d.insert(0, f'{STATUS[b]}. Predajňa v Bratislave, doprava po Slovensku.'[:90])
            rsa.append(['SO27 | SEARCH | Značky a modely', g, url, h, d])
    for g, url, ks in MODELS:
        for k in ks:
            kw.append(['SO27 | SEARCH | Značky a modely', 'Model | ' + g, k, 'PHRASE', SITE + url])
        h = [g[:30], f'{g} | cena'[:30], 'Sonata Optics', 'Predajňa v Bratislave', 'Poradíme s výberom', 'Doprava po celom Slovensku', 'Odborné poradenstvo', 'Nákup s istotou']
        rsa.append(['SO27 | SEARCH | Značky a modely', 'Model | ' + g, SITE + url, h, MODEL_RSA_D])
    for g, (url, ks) in STORE.items():
        for k, m in ks:
            kw.append(['NEW26 | SEARCH | Bratislava | Predajňa', g, k, {'E': 'EXACT', 'P': 'PHRASE'}[m], SITE + url])
        rsa.append(['NEW26 | SEARCH | Bratislava | Predajňa', g, SITE + url, STORE_RSA[0], STORE_RSA[1]])
    # cross-routing negatives (campaign level): category campaign must not catch brand/model/store queries
    for b in sorted({b for v in BRANDS.values() for b in v} | {'Pulsar', 'Hikmicro', 'Swarovski', 'Nikon', 'Bushnell'}):
        for t in {b.lower(), b.lower().replace('-', ' '), b.lower().replace('-', '')}:
            neg.append(['SO27 | SEARCH | Kategórie', 'PHRASE', t, 'brand queries go to Značky a modely or nowhere'])
    for t in ['bratislava', 'predajna', 'predajňa', 'sonata optics']:
        neg.append(['SO27 | SEARCH | Kategórie', 'PHRASE', t, 'store queries go to Predajňa'])
        neg.append(['SO27 | SEARCH | Značky a modely', 'PHRASE', t, 'store queries go to Predajňa'])
    for t in ['nocnym videnim', 'nočným videním', 'nocne videnie', 'nočné videnie', 'termo', 'termovizia', 'termovízia', 'dialkomer', 'diaľkomer', 'infra']:
        neg.append(['SO27 | SEARCH | Kategórie', 'PHRASE', t, 'night vision / thermal / rangefinder are not in this campaign (gate review)'])
    for t in ['seestar', 'dwarf', 'dwarflab', 'unistellar', 'vaonis', 'vespera', 'evscope', 'celestron origin']:
        neg.append(['SO27 | SEARCH | Značky a modely', 'PHRASE', t, 'smart telescopes: Stellarscope after cutover; not bought in SO27 Search'])
    return kw, rsa, neg

def checks(kw, rsa, neg):
    out, bad = [], 0
    def chk(ok, msg):
        nonlocal bad; bad += not ok; out.append(('PASS ' if ok else 'FAIL ') + msg)
    for c, g, url, h, d in rsa:
        chk(3 <= len(h) <= 15 and all(len(x) <= 30 for x in h), f'headlines 3..15, <=30: {g} ({len(h)}, max {max(map(len, h))})')
        chk(2 <= len(d) <= 4 and all(len(x) <= 90 for x in d), f'descriptions 2..4, <=90: {g} ({len(d)}, max {max(map(len, d))})')
        chk(len(set(h)) == len(h), f'unique headlines: {g}')
        bad_words = [x for x in h + d if BANNED.search(x)]
        chk(not bad_words, f'no banned claims/words: {g} {bad_words}')
    groups = {}
    for c, g, k, m, url in kw:
        groups.setdefault((c, k.lower(), m), []).append(g)
    dup = {k: v for k, v in groups.items() if len(set(v)) > 1}
    chk(not dup, f'no keyword in two ad groups of one campaign: {list(dup)[:5]}')
    negs = {}
    for c, m, t, _ in neg:
        negs.setdefault(c, []).append(t)
    blocked = [(c, g, k) for c, g, k, m, u in kw if any(re.search(r'(^| )' + re.escape(t) + r'( |$)', k.lower()) for t in negs.get(c, []))]
    chk(not blocked, f'own campaign negatives do not block own keywords: {blocked[:5]}')
    # account-level list after the move-7 diff must not block package keywords
    sys.path.insert(0, os.path.join(R5, '07_claude_code_attachments')); sys.dont_write_bytecode = True
    import negatives_effective as ne  # noqa
    acc = ne.apply()
    import routing_tests as rt  # noqa
    hit = [(g, k, rt.hits(k, acc)) for c, g, k, m, u in kw if rt.hits(k, acc)]
    chk(not hit, f'account-level list (after diff) does not block package keywords: {hit[:5]}')
    return out, bad

def landing(urls):
    res = []
    for u in sorted(urls):
        try:
            req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (compatible; SonataAdsLandingCheck/1.0)'})
            with urllib.request.urlopen(req, timeout=30) as r:
                code, html, final = r.status, r.read().decode('utf-8', 'ignore'), r.geturl()
        except Exception as e:
            res.append((u, getattr(e, 'code', 'ERR'), '', 0, 'FAIL')); continue
        n = re.findall(r'(\d[\d\s]*) produkt', html)
        cnt = min(int(x.replace(' ', '').replace('\xa0', '')) for x in n) if n else (1 if u.endswith('.html') and 'add_to_cart' in html.lower() or 'do košíka' in html.lower() else 0)
        oos = u.endswith('.html') and ('Na objednávku' in html or 'Vypredané' in html) and 'Skladom' not in html
        ok = code == 200 and final.rstrip('/') == u.rstrip('/') and cnt > 0 and not oos
        res.append((u, code, '' if final == u else final, cnt, 'PASS' if ok else 'FAIL'))
        time.sleep(0.5)
    return res

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    kw, rsa, neg = rows()
    with open(os.path.join(HERE, 'search_keywords.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['campaign', 'ad_group', 'keyword', 'match_type', 'final_url']); w.writerows(kw)
    with open(os.path.join(HERE, 'search_rsa.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['campaign', 'ad_group', 'final_url'] + [f'H{i}' for i in range(1, 16)] + [f'D{i}' for i in range(1, 5)])
        for c, g, u, h, d in rsa:
            w.writerow([c, g, u] + (h + [''] * 15)[:15] + (d + [''] * 4)[:4])
    with open(os.path.join(HERE, 'search_negatives.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['campaign', 'match_type', 'negative', 'reason']); w.writerows(neg)
    out, bad = checks(kw, rsa, neg)
    if '--check-landing' in sys.argv:
        lr = landing({r[4] for r in kw} | {r[2] for r in rsa})
        with open(os.path.join(HERE, 'search_landing_check.csv'), 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f); w.writerow(['url', 'http', 'redirected_to', 'products_or_buyable', 'result']); w.writerows(lr)
        lb = sum(1 for x in lr if x[4] == 'FAIL'); bad += lb
        out.append(f'{"PASS" if not lb else "FAIL"} landing pages: {len(lr) - lb}/{len(lr)} (HTTP 200, no redirect, >=1 product / buyable PDP)')
    summary = f'keywords {len(kw)}, ad groups {len(rsa)}, negatives {len(neg)}; checks {len(out) - bad}/{len(out)} PASS'
    open(os.path.join(HERE, 'search_checks.txt'), 'w', encoding='utf-8').write('\n'.join(out + [summary]) + '\n')
    for line in out:
        if line.startswith('FAIL'):
            print(line)
    print(summary)
    return bad

if __name__ == '__main__':
    sys.exit(1 if main() else 0)
