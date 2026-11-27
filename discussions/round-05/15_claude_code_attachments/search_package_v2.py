#!/usr/bin/env python3
"""Round 5 move 15: SO27 Search package v2 (fixes R5-CHATGPT-22/23). Reuses copy rules, RSA texts, landing check and canonical
URL map from search_package.py (move 13) and replaces the routing parts:
- one ad group per magnification with its own category page (10x56 has no page -> keyword dropped);
- model groups only for full designations (EXACT + PHRASE), ad-group negatives for conflicting sizes/generations/mounts;
- ambiguous family queries ("celestron c8", "bresser junior teleskop", "levenhuk karma 10x42" ...) go to the brand/family page;
- brand groups carry negatives of the model designators, so a full model query reaches only its model group;
- semantic router simulates Google keyword matching (EXACT = whole query, PHRASE = contiguous tokens; negatives BROAD/PHRASE
  literal, account + campaign + ad group) and requires EXACTLY ONE eligible ad group with the expected URL per test query.
Outputs (overwrite move-13 names in this folder): search_keywords.csv, search_rsa.csv, search_negatives.csv,
search_semantic_tests.csv, search_checks.txt, search_landing_check.csv (--check-landing). Nothing is applied."""
import csv, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); R5 = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.dont_write_bytecode = True
import search_package as P  # noqa  (move-13 module, same folder)
SITE, CANON = P.SITE, P.CANON
U = lambda path: CANON.get(SITE + path, SITE + path)
KAT, ZNM, PRED = 'SO27 | SEARCH | Kategórie', 'SO27 | SEARCH | Značky a modely', 'NEW26 | SEARCH | Bratislava | Predajňa'

# ---------------- Kategórie ----------------
CAT = dict(P.CAT)
CAT.pop('Ďalekohľady 10x50 a 10x42')
SIZES = {'10x50': ['dalekohlad 10x50', 'ďalekohľad 10x50', 'dalekohled 10x50', 'dalekohlady 10x50'], '10x42': ['dalekohlad 10x42', 'ďalekohľad 10x42', 'dalekohlady 10x42'],
         '8x42': ['dalekohlad 8x42', 'ďalekohľad 8x42'], '12x50': ['dalekohlad 12x50', 'ďalekohľad 12x50'], '8x56': ['dalekohlad 8x56', 'ďalekohľad 8x56'],
         '20x50': ['dalekohlad 20x50', 'ďalekohľad 20x50'], '8x32': ['dalekohlad 8x32', 'ďalekohľad 8x32']}
for s, ks in SIZES.items():
    CAT[f'Ďalekohľady {s}'] = (f'/dalekohlady/dalekohlady-{s}/', [(k, 'P') for k in ks])
CAT['Astronomické binokuláre'] = ('/dalekohlady/astronomicke-binokulare-na-nocnu-oblohu/', [('astronomicky binokular', 'P'), ('astronomický binokulár', 'P'), ('binokular na hviezdy', 'P')])
d = CAT['Ďalekohľady']
CAT['Ďalekohľady'] = (d[0], [k for k in d[1] if k[0] not in ('turisticky dalekohlad', 'dalekohlad na pozorovanie vtakov')])
CAT['Turistické ďalekohľady'] = ('/dalekohlady/turisticke-dalekohlady/', [('turisticky dalekohlad', 'P'), ('turistický ďalekohľad', 'P')])
CAT['Ornitologické ďalekohľady'] = ('/dalekohlady/ornitologicke-dalekohlady/', [('dalekohlad na pozorovanie vtakov', 'P'), ('ďalekohľad na pozorovanie vtákov', 'P'), ('ornitologicky dalekohlad', 'P')])
CAT['Vreckové ďalekohľady'] = ('/dalekohlady/vreckove-a-kompaktne-dalekohlady/', [('vreckovy dalekohlad', 'P'), ('vreckový ďalekohľad', 'P'), ('mini dalekohlad', 'P'), ('maly dalekohlad', 'P')])
SIZE_TOKENS = [s for s in SIZES] + ['10x56', '8x25', '10x25', '7x50', '15x70', '20x80', '15x56', '10x40', '25x100']
# generic groups must not catch an explicit size (it has its own group / or no page): group negatives
CAT_GROUP_NEG = {g: SIZE_TOKENS for g in ('Ďalekohľady', 'Turistické ďalekohľady', 'Ornitologické ďalekohľady', 'Vreckové ďalekohľady', 'Detské ďalekohľady', 'Astronomické binokuláre')}
for s in SIZES:
    CAT_GROUP_NEG[f'Ďalekohľady {s}'] = [t for t in SIZE_TOKENS if t != s]
KIDS = ['deti', 'detsky', 'detský', 'detske', 'detské']
STARS = ['hviezdy', 'hvezdarsky', 'hvezdársky', 'astronomicky', 'astronomický']
CAT_GROUP_NEG['Hvezdárske ďalekohľady'] = KIDS
CAT_GROUP_NEG['Detské ďalekohľady'] = CAT_GROUP_NEG['Detské ďalekohľady'] + STARS
CAT_GROUP_NEG['Digitálne mikroskopy'] = KIDS
CAT['Digitálne mikroskopy'] = (CAT['Digitálne mikroskopy'][0], [k for k in CAT['Digitálne mikroskopy'][1] if 'deti' not in k[0]])

# ---------------- Značky a modely ----------------
BRANDS = {k: list(v) for k, v in P.BRANDS.items()}
BRANDS['teleskopy'].append('Bresser Junior'); P.V['Bresser Junior'] = '66472'
BRANDS['dalekohlady'].remove('Vortex')   # live Vortex RSA DISAPPROVED (GUNS) 26.11 -> no Vortex in Search; Shopping only
MODELS = [  # group, PDP, EXACT/PHRASE keywords with full designation, ad-group negatives (conflicting variants), brand group, designators
 ('Celestron AstroMaster 114EQ', '/teleskop-celestron-astromaster-114eq-teleskop.html', ['celestron astromaster 114eq', 'astromaster 114eq', 'astromaster 114 eq'],
  ['114az', 'az', 'lt', '70', '90', '102', '130'], 'Teleskopy | Celestron', ['114eq', '114 eq']),
 ('Celestron StarSense LT 70AZ', '/teleskop-celestron-starsense-explorer-lt-70az.html', ['starsense explorer lt 70az', 'celestron starsense lt 70az', 'starsense lt 70az'],
  ['80az', '114az', '127az', '130az', 'dx', '102az'], 'Teleskopy | Celestron', ['70az']),
 ('Celestron C8 XLT OTA', '/teleskop-celestron-8-sc-xlt-tubus-ota-mit-3-schiene-76mm.html', ['celestron c8 ota', 'celestron c8 xlt ota', 'c8 xlt ota', 'celestron c8 tubus'],
  ['nexstar', 'se', 'cpc', 'evolution', 'avx', 'cgem', 'cgx', 'edgehd', 'edge', 'sgt', 'starsense', 'origin'], 'Teleskopy | Celestron', ['ota', 'tubus']),
 ('Sky-Watcher Explorer 130/900 EQ2', '/product-47488.html', ['sky-watcher explorer 130 eq2', 'skywatcher explorer 130 eq2', 'sky watcher explorer 130 eq2', 'explorer 130/900 eq2', 'explorer 130 eq2'],
  ['pds', '130p', '130m', 'eq3', 'eq-3', 'motor', 'az', '150', 'virtuoso', 'heritage'], 'Teleskopy | Sky-Watcher', ['explorer 130 eq2', '130 eq2', '130/900 eq2']),
 ('Bresser Messier AR-127S EXOS-2', '/bresser-teleskop-ac-127s-635-messier-exos-2.html', ['bresser messier ar-127s exos-2', 'messier ar-127s exos-2', 'ar-127s exos-2', 'ar 127s exos 2', 'bresser ar-127s/635'],
  ['127l', 'ar-127l', 'ota', 'tubus', 'exos-1', 'nano'], 'Teleskopy | Bresser', ['ar-127s', '127s']),
 ('National Geographic 114/900', '/bresser-national-geographic-114-900-az-telescope.html', ['national geographic 114/900', 'national geographic 114 900', 'national geographic teleskop 114/900'],
  ['eq', '76/700', '70/700', '50/360', '60/700', '90/900'], 'Teleskopy | National Geographic', ['114/900', '114 900']),
 ('Bresser Junior 70/900 EL', '/bresser-junior-teleskop-ac-70-900-el.html', ['bresser junior 70/900', 'bresser junior 70 900', 'bresser junior 70/900 el'],
  ['50/360', '70/400', '50 360', '70 400', '40', '60/700'], 'Teleskopy | Bresser Junior', ['70/900', '70 900']),
 ('Bresser Condor UR 10x42', '/bresser-condor-ur-10x42-binoculars.html', ['bresser condor 10x42', 'bresser condor ur 10x42', 'condor ur 10x42'],
  ['8x42', '10x50', '8x32', '12x50', '10x25', '8x25'], 'Ďalekohľady | Bresser', ['condor 10x42', 'condor ur 10x42']),
 ('Levenhuk New Karma PLUS 10x42', '/levenhuk-new-karma-plus-10x42.html', ['levenhuk karma plus 10x42', 'karma plus 10x42', 'levenhuk new karma plus 10x42', 'new karma plus 10x42'],
  ['pro', 'ed', '8x42', '10x50', '8x32', '12x50', '16x50', '8x25'], 'Ďalekohľady | Levenhuk', ['karma plus']),
 ('Bresser Erudit Basic Bino', '/bresser-erudit-basic-bino-40x-400x-mikroskop.html', ['bresser erudit basic bino', 'erudit basic bino', 'bresser erudit bino'],
  ['mono', 'trino', 'dlx', 'researcher'], 'Mikroskopy | Bresser', ['erudit basic bino', 'erudit bino']),
 ('Omegon Binofield 40-800x LED', '/omegon-mikroskop-binofield-40800-led.html', ['omegon binofield 40-800x', 'binofield 40-800x', 'omegon binofield 40-800x led', 'binofield 40 800x'],
  ['stereo', '20x', '2x', '4x'], 'Mikroskopy | Omegon', ['binofield 40-800x', 'binofield 40 800x']),
]
FAMILY = {  # ambiguous family queries -> brand/family page (brand group), PHRASE
 'Teleskopy | Celestron': ['celestron c8', 'celestron astromaster', 'celestron starsense'], 'Teleskopy | Sky-Watcher': ['sky-watcher explorer', 'skywatcher explorer'],
 'Teleskopy | Bresser': ['bresser messier'], 'Teleskopy | Bresser Junior': ['bresser junior teleskop', 'teleskop bresser junior'],
 'Ďalekohľady | Bresser': ['bresser condor'], 'Ďalekohľady | Levenhuk': ['levenhuk karma'],
 'Mikroskopy | Bresser': ['bresser erudit'], 'Mikroskopy | Omegon': ['omegon binofield'], 'Teleskopy | National Geographic': ['national geographic teleskop'],
}
STORE = {
 'Predajňa – značka a adresa': ('/kontakt/', P.STORE['Predajňa – značka a adresa'][1]),   # live ad on /kontakt/ DISAPPROVED (GUNS): do not enable before the cause is fixed
 'Predajňa – teleskopy': ('/teleskopy/', [('teleskopy bratislava', 'E'), ('teleskop bratislava', 'E'), ('teleskop predajna bratislava', 'E')]),
 'Predajňa – mikroskopy': ('/mikroskopy/', [('mikroskopy bratislava', 'E'), ('mikroskop bratislava', 'E'), ('mikroskop predajna bratislava', 'E')]),
 'Predajňa – ďalekohľady': ('/dalekohlady/', P.STORE['Predajňa – ďalekohľady'][1]),
}
STORE['Predajňa – poradenstvo a osobný odber'] = ('/teleskopy/', [('astronomicka predajna', 'P'), ('predajna teleskopov', 'P'), ('predajna dalekohladov', 'P'), ('predajňa teleskopov', 'P'), ('osobny odber teleskop', 'P')])
PRED_CAMPAIGN_NEG = ['okuliare', 'okuliarov', 'šošovky', 'sosovky', 'kontaktné', 'kontaktne', 'dioptrické', 'dioptricke', 'očný', 'ocny', 'meranie zraku', 'vyšetrenie zraku',
                     'vysetrenie zraku', 'optika okuliare', 'slnečné okuliare', 'pracovné ponuky', 'brigáda']

def tok(s):
    return s.lower().split()

def build():
    kw, rsa, neg = [], [], []      # kw: campaign, group, keyword, match, url; neg: campaign, group('' = campaign level), match, text, reason
    for g, (url, ks) in CAT.items():
        for k, m in ks:
            kw.append([KAT, g, k, {'E': 'EXACT', 'P': 'PHRASE'}[m], U(url)])
        h, dd = P.CAT_RSA[P.CAT_RSA_OF(g)]
        rsa.append([KAT, g, U(url), h, dd])
        for t in CAT_GROUP_NEG.get(g, []):
            neg.append([KAT, g, 'PHRASE', t, 'explicit size belongs to its own size group / page'])
    model_designators = {}
    for g, url, ks, gneg, bgroup, desig in MODELS:
        for k in ks:
            kw.append([ZNM, 'Model | ' + g, k, 'EXACT', SITE + url]); kw.append([ZNM, 'Model | ' + g, k, 'PHRASE', SITE + url])
        for t in gneg:
            neg.append([ZNM, 'Model | ' + g, 'PHRASE', t, 'conflicting size/generation/mount -> not this PDP'])
        model_designators.setdefault(bgroup, set()).update(desig)
        h = [g[:30], 'Sonata Optics', 'Predajňa v Bratislave', 'Poradíme s výberom', 'Doprava po celom Slovensku', 'Odborné poradenstvo', 'Nákup s istotou', 'Aktuálna cena online']
        rsa.append([ZNM, 'Model | ' + g, SITE + url, h, P.MODEL_RSA_D])
    for cat, brands in BRANDS.items():
        for b in brands:
            g = f'{P.TITLE[cat]} | {b}'; url = CANON.get(f'{SITE}/{cat}/?features_hash=509-{P.V[b]}', f'{SITE}/{cat}/?features_hash=509-{P.V[b]}')
            for acc, plain in P.NOUN[cat]:
                for k in {f'{b.lower()} {acc}', f'{acc} {b.lower()}', f'{b.lower().replace("-", " ")} {plain}', f'{plain} {b.lower().replace("-", " ")}'}:
                    kw.append([ZNM, g, k, 'PHRASE', url])
            for k in FAMILY.get(g, []):
                kw.append([ZNM, g, k, 'PHRASE', url])
            for t in sorted(model_designators.get(g, [])):
                neg.append([ZNM, g, 'PHRASE', t, 'full model designation belongs to the model group'])
            if cat == 'dalekohlady':
                for t in ('hvezdarsky', 'hvezdársky'):
                    neg.append([ZNM, g, 'PHRASE', t, 'hvezdársky ďalekohľad = telescope -> Teleskopy brand group'])
            if b == 'Bresser':
                neg.append([ZNM, g, 'PHRASE', 'junior', 'Bresser Junior has its own family group'])
            h = [f'{P.TITLE[cat]} {b}'[:30], f'{b} | Sonata Optics'[:30], f'Celý výber {b}'[:30], 'Predajňa v Bratislave', 'Poradíme s výberom', 'Doprava po celom Slovensku',
                 'Odborné poradenstvo', 'Vyskúšajte v predajni', 'Nákup s istotou', 'Aktuálne ceny online']
            if b in P.STATUS: h.insert(2, P.STATUS[b][:30])
            dd = [f'{P.TITLE[cat]} {b} – aktuálna ponuka a ceny. Pomôžeme vybrať správny model.'[:90], 'Predajňa v Bratislave, doprava po celom Slovensku. Poradíme pred nákupom.',
                  'Odborná rada k výberu aj príslušenstvu. Sonata Optics – špecialisti na optiku.']
            if b in P.STATUS: dd.insert(0, f'{P.STATUS[b]}. Predajňa v Bratislave, doprava po Slovensku.'[:90])
            rsa.append([ZNM, g, url, h, dd])
    for g, (url, ks) in STORE.items():
        for k, m in ks:
            kw.append([PRED, g, k, {'E': 'EXACT', 'P': 'PHRASE'}[m], SITE + url])
        rsa.append([PRED, g, SITE + url, P.STORE_RSA[0], P.STORE_RSA[1]])
    allbrands = sorted({b for v in BRANDS.values() for b in v} | {'Pulsar', 'Hikmicro', 'Swarovski', 'Nikon', 'Bushnell', 'Meade', 'National'})
    for b in allbrands:
        for t in {b.lower(), b.lower().replace('-', ' '), b.lower().replace('-', '')}:
            neg.append([KAT, '', 'PHRASE', t, 'brand queries go to Značky a modely'])
    for t in ['bratislava', 'predajna', 'predajňa', 'sonata optics']:
        neg.append([KAT, '', 'PHRASE', t, 'store queries go to Predajňa']); neg.append([ZNM, '', 'PHRASE', t, 'store queries go to Predajňa'])
    for t in ['nocnym videnim', 'nočným videním', 'nocne videnie', 'nočné videnie', 'termo', 'termovizia', 'termovízia', 'dialkomer', 'diaľkomer', 'infra']:
        neg.append([KAT, '', 'PHRASE', t, 'night vision / thermal / rangefinder not in this campaign (gate review)'])
    for t in ['seestar', 'dwarf', 'dwarflab', 'unistellar', 'vaonis', 'vespera', 'evscope', 'celestron origin']:
        neg.append([ZNM, '', 'PHRASE', t, 'smart telescopes not bought in SO27 Search'])
    for t in PRED_CAMPAIGN_NEG:
        neg.append([PRED, '', 'PHRASE', t, 'optician / eyewear confusion'])
    return kw, rsa, neg

def match_kw(q, k, m):
    qt, kt = tok(q), tok(k)
    if m == 'EXACT':
        return qt == kt
    return any(qt[i:i + len(kt)] == kt for i in range(len(qt) - len(kt) + 1))

def neg_hit(q, m, t):
    qt, tt = tok(q), tok(t)
    if m == 'EXACT':
        return qt == tt
    if m == 'PHRASE':
        return any(qt[i:i + len(tt)] == tt for i in range(len(qt) - len(tt) + 1))
    return all(x in qt for x in tt)

def router(kw, neg, account):
    camp_neg, grp_neg = {}, {}
    for c, g, m, t, _ in neg:
        (grp_neg.setdefault((c, g), []) if g else camp_neg.setdefault(c, [])).append((m, t))
    def route(q):
        if any(neg_hit(q, m, t) for m, t in account):
            return []
        hits = {}
        for c, g, k, m, url in kw:
            if match_kw(q, k, m) and not any(neg_hit(q, mm, t) for mm, t in camp_neg.get(c, [])) and not any(neg_hit(q, mm, t) for mm, t in grp_neg.get((c, g), [])):
                hits[(c, g)] = url
        return sorted((c, g, u) for (c, g), u in hits.items())
    return route

SEM = [  # query, expected url (None = no Search ad expected), note
 ('dalekohlad 10x50', U('/dalekohlady/dalekohlady-10x50/'), 'size'), ('dalekohlad 10x42', U('/dalekohlady/dalekohlady-10x42/'), 'size (R5-22)'),
 ('dalekohlad 8x42', U('/dalekohlady/dalekohlady-8x42/'), 'size (R5-22)'), ('dalekohlad 12x50', U('/dalekohlady/dalekohlady-12x50/'), 'size (R5-22)'),
 ('dalekohlad 8x56', U('/dalekohlady/dalekohlady-8x56/'), 'size (R5-22)'), ('ďalekohľad 8x56', U('/dalekohlady/dalekohlady-8x56/'), 'size (R5-22)'),
 ('dalekohlad 10x56', None, 'no 10x56 page -> no ad rather than a wrong size'), ('dalekohlad 20x50', U('/dalekohlady/dalekohlady-20x50/'), 'size'),
 ('turisticky dalekohlad 10x42', U('/dalekohlady/dalekohlady-10x42/'), 'size wins over purpose'), ('turisticky dalekohlad', U('/dalekohlady/turisticke-dalekohlady/'), 'purpose'),
 ('dalekohlad', U('/dalekohlady/'), 'generic'), ('teleskop', U('/teleskopy/'), 'generic'), ('mikroskop pre deti', U('/mikroskopy/skolske-a-studentske-mikroskopy/'), 'kids'),
 ('teleskop celestron', U('/teleskopy/?features_hash=509-65727'), 'brand'), ('celestron c8', U('/teleskopy/?features_hash=509-65727'), 'ambiguous family -> brand page (R5-23)'),
 ('celestron c8 ota', SITE + '/teleskop-celestron-8-sc-xlt-tubus-ota-mit-3-schiene-76mm.html', 'model'), ('celestron nexstar 8se', None, 'no group for this model; brand phrase does not match'),
 ('celestron c8 nexstar ota', None, 'conflicting variant blocked in model group, designator blocks brand group'),
 ('celestron astromaster 114eq', SITE + '/teleskop-celestron-astromaster-114eq-teleskop.html', 'model'), ('celestron astromaster 114az', U('/teleskopy/?features_hash=509-65727'), 'other variant -> family page, not the EQ PDP'),
 ('bresser junior teleskop', U('/teleskopy/?features_hash=509-66472'), 'ambiguous family -> Junior page (R5-23)'), ('bresser junior 70/900', SITE + '/bresser-junior-teleskop-ac-70-900-el.html', 'model'),
 ('bresser junior 70/400', None, 'other variant: model group blocks, family phrase does not match'), ('teleskop bresser', U('/teleskopy/?features_hash=509-37168'), 'brand'),
 ('teleskop bresser junior', U('/teleskopy/?features_hash=509-66472'), 'Junior family, not Bresser brand'),
 ('levenhuk karma 10x42', U('/dalekohlady/?features_hash=509-37169'), 'ambiguous (PLUS/PRO) -> brand page (R5-23)'), ('levenhuk karma plus 10x42', SITE + '/levenhuk-new-karma-plus-10x42.html', 'model'),
 ('levenhuk karma pro 10x42', U('/dalekohlady/?features_hash=509-37169'), 'other generation -> brand page, not PLUS PDP'),
 ('vortex crossfire hd 12x50', None, 'Vortex not in Search (GUNS disapproval); Shopping only'), ('vortex dalekohlad', None, 'Vortex not in Search'),
 ('sky-watcher explorer 130 eq2', SITE + '/product-47488.html', 'model'), ('sky-watcher explorer 130p eq2', U('/teleskopy/?features_hash=509-52381'), 'other variant -> brand page'),
 ('bresser erudit basic mono', U('/mikroskopy/?features_hash=509-37168'), 'other variant -> brand page'),
 ('sonata optics', SITE + '/kontakt/', 'store'), ('teleskopy bratislava', SITE + '/teleskopy/', 'store -> approved category landing'), ('mikroskop bratislava', SITE + '/mikroskopy/', 'store'), ('optika predajna bratislava okuliare', None, 'eyewear blocked'),
 ('dalekohlad s nocnym videnim', None, 'night vision not bought in Search'), ('seestar s50', None, 'smart telescope not bought'),
]

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    kw, rsa, neg = build()
    sys.path.insert(0, os.path.join(R5, '07_claude_code_attachments'))
    import negatives_effective as ne  # noqa
    account = ne.apply()
    route = router(kw, neg, account)
    out, bad = [], 0
    def chk(ok, msg):
        nonlocal bad; bad += not ok; out.append(('PASS ' if ok else 'FAIL ') + msg)
    for c, g, url, h, d in rsa:
        chk(3 <= len(h) <= 15 and all(len(x) <= 30 for x in h) and len(set(h)) == len(h), f'headlines: {g}')
        chk(2 <= len(d) <= 4 and all(len(x) <= 90 for x in d), f'descriptions: {g}')
        chk(not [x for x in h + d if P.BANNED.search(x)], f'no banned words/claims: {g}')
    for c, g, k, m, url in kw:   # every keyword reaches exactly its own group (own query)
        r = route(k)
        chk(len(r) == 1 and r[0][1] == g, f'keyword reaches only its group: [{g}] {k} {m} -> {[(x[1]) for x in r]}')
    sem = []
    for q, exp, note in SEM:
        r = route(q)
        got = r[0][2] if len(r) == 1 else (None if not r else 'AMBIGUOUS:' + ' | '.join(x[1] for x in r))
        ok = got == exp
        chk(ok, f'semantic: "{q}" -> {got} (expected {exp})')
        sem.append(dict(query=q, expected=exp or '(no ad)', got=got or '(no ad)', groups=' | '.join(x[1] for x in r) or '-', result='PASS' if ok else 'FAIL', note=note))
    with open(os.path.join(HERE, 'search_keywords.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['campaign', 'ad_group', 'keyword', 'match_type', 'final_url']); w.writerows(kw)
    with open(os.path.join(HERE, 'search_rsa.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['campaign', 'ad_group', 'final_url'] + [f'H{i}' for i in range(1, 16)] + [f'D{i}' for i in range(1, 5)])
        for c, g, u, h, d in rsa:
            w.writerow([c, g, u] + (h + [''] * 15)[:15] + (d + [''] * 4)[:4])
    with open(os.path.join(HERE, 'search_negatives.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['campaign', 'ad_group (empty = campaign level)', 'match_type', 'negative', 'reason']); w.writerows(neg)
    with open(os.path.join(HERE, 'search_semantic_tests.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(sem[0].keys())); w.writeheader(); w.writerows(sem)
    if '--check-landing' in sys.argv:
        lr = P.landing({r[4] for r in kw} | {r[2] for r in rsa})
        with open(os.path.join(HERE, 'search_landing_check.csv'), 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f); w.writerow(['url', 'http', 'redirected_to', 'products_or_buyable', 'result']); w.writerows(lr)
        lb = sum(1 for x in lr if x[4] == 'FAIL'); chk(not lb, f'landing pages {len(lr) - lb}/{len(lr)}')
    summary = f'keywords {len(kw)}, ad groups {len(rsa)}, negatives {len(neg)}, semantic tests {len(SEM)}; checks {len(out) - bad}/{len(out)} PASS'
    open(os.path.join(HERE, 'search_checks.txt'), 'w', encoding='utf-8').write('\n'.join(out + [summary]) + '\n')
    for line in out:
        if line.startswith('FAIL'):
            print(line)
    print(summary)
    return bad

if __name__ == '__main__':
    sys.exit(1 if main() else 0)
