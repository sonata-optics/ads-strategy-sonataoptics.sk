#!/usr/bin/env python3
"""Round 5 move 22: SO27 Search package v3 = v2 (moves 15-19) + Gemini/ChatGPT fixes GEM-FINAL-01..08 (ход 21/21b).
- RSA copy: no silent [:30]/[:90] truncation anywhere (a text that does not fit FAILS the build); explicit short texts for the five
  truncated fields; every narrow Kategórie group gets its OWN template matching its landing (no foreign brands/sizes/types);
- keywords: positive 'mikroskop popis' removed; exact duplicates removed; uniqueness of (campaign, group, keyword, match) is a test;
- Vortex: 'montaz' added to the weapon/mount negatives of BOTH Vortex groups;
- Predajňa: targeted store phrases (mikroskopov, osobný odber, brand/size + bratislava) with positive and negative tests;
- landing check reports product_count (from the page counter) separately from buyable_detected; unknown count is never "1".
Outputs: search_keywords.csv, search_rsa.csv, search_rsa_before_after.csv, search_negatives.csv, search_semantic_tests.csv,
search_checks.txt, search_landing_check.csv (--check-landing). Nothing is applied."""
import csv, os, re, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); R5 = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(R5, '07_claude_code_attachments')); sys.dont_write_bytecode = True
import search_package as P      # noqa  move-13 rules/texts
import search_package_v2 as V2  # noqa  move-15..19 routing
import negatives_effective as NE  # noqa
SITE, U, KAT, ZNM, PRED = V2.SITE, V2.U, V2.KAT, V2.ZNM, V2.PRED

# ---------- keyword / negative fixes (before build) ----------
V2.CAT['Mikroskopy'] = (V2.CAT['Mikroskopy'][0], [k for k in V2.CAT['Mikroskopy'][1] if k[0] != 'mikroskop popis'])      # GEM-04
for t in ('montaz',):                                                                                                         # GEM-05
    if t not in V2.VORTEX_WEAPON_NEG:
        V2.VORTEX_WEAPON_NEG.append(t)
st = V2.STORE                                                                                                                 # GEM-08
st['Predajňa – mikroskopy'] = (st['Predajňa – mikroskopy'][0], st['Predajňa – mikroskopy'][1] + [('predajna mikroskopov', 'P'), ('predajňa mikroskopov', 'P')])
st['Predajňa – ďalekohľady'] = (st['Predajňa – ďalekohľady'][0], st['Predajňa – ďalekohľady'][1] + [('osobny odber dalekohlad', 'P'), ('osobný odber ďalekohľad', 'P')]
                                + [(f'dalekohlad {s} bratislava', 'P') for s in V2.SIZES] + [(f'ďalekohľad {s} bratislava', 'P') for s in V2.SIZES])
TEL_STORE_BRANDS = ['celestron', 'sky-watcher', 'bresser', 'levenhuk', 'omegon']
BIN_STORE_BRANDS = ['leica', 'zeiss', 'meopta', 'bresser', 'levenhuk', 'vortex', 'minox']
st['Predajňa – teleskopy'] = (st['Predajňa – teleskopy'][0], st['Predajňa – teleskopy'][1] + [(f'teleskop {b} bratislava', 'P') for b in TEL_STORE_BRANDS] + [(f'{b} teleskop bratislava', 'P') for b in TEL_STORE_BRANDS])
st['Predajňa – ďalekohľady'] = (st['Predajňa – ďalekohľady'][0], st['Predajňa – ďalekohľady'][1] + [(f'dalekohlad {b} bratislava', 'P') for b in BIN_STORE_BRANDS] + [(f'{b} dalekohlad bratislava', 'P') for b in BIN_STORE_BRANDS])
STORE_WEAPON_NEG = ['na pusku', 'na pušku', 'puskohlad', 'puškohľad', 'kolimator', 'kolimátor', 'zbran', 'zbraň', 'polovnicky', 'poľovnícky']   # Predajňa campaign level

# ---------- RSA copy ----------
D_STORE = 'Predajňa v Bratislave a doprava po celom Slovensku. Odborné poradenstvo pred nákupom.'
SIZE_T = lambda s: ([f'Ďalekohľady {s}', f'Binokuláre {s} | Sonata', f'Výber modelov {s}', 'Poradíme s výberom optiky', 'Predajňa v Bratislave'],
                    [f'Ďalekohľady {s}. Pomôžeme vybrať model podľa spôsobu pozorovania.', f'Aktuálna ponuka ďalekohľadov {s}. Predajňa v Bratislave a doprava po Slovensku.'])
CAT_COPY = {
 'Teleskopy': (['Teleskopy | Sonata Optics', 'Teleskopy pre začiatočníkov', 'Hvezdárske ďalekohľady', 'Poradíme s výberom teleskopu', 'Predajňa v Bratislave',
                'Doprava po celom Slovensku', 'Refraktory, Newtony aj SCT', 'Montáže a okuláre', 'Odborné poradenstvo', 'Teleskop ako darček'],
               ['Teleskopy pre začiatočníkov aj pokročilých. Pomôžeme vybrať ten správny model.', 'Refraktory, Newtonove teleskopy aj Schmidt-Cassegrain. Montáže a príslušenstvo.', D_STORE]),
 'Hvezdárske ďalekohľady': (['Hvezdárske ďalekohľady', 'Teleskopy na hviezdy', 'Ďalekohľad na pozorovanie', 'Poradíme s výberom teleskopu', 'Predajňa v Bratislave', 'Odborné poradenstvo'],
               ['Hvezdárske ďalekohľady na Mesiac, planéty aj hviezdy. Pomôžeme vybrať model.', D_STORE]),
 'Teleskopy pre deti': (['Teleskopy pre deti', 'Detské hvezdárske ďalekohľady', 'Prvý teleskop na hviezdy', 'Teleskop pre deti ako darček', 'Poradíme s výberom | Sonata'],
               ['Teleskopy pre deti a začiatočníkov na prvé pozorovanie Mesiaca a hviezd. Poradíme.', 'Predajňa v Bratislave, doprava po Slovensku. Pomôžeme s výberom teleskopu.']),
 'Ďalekohľady': (['Ďalekohľady | Sonata Optics', 'Ďalekohľady na prírodu', 'Kompaktné aj výkonné modely', 'Poradíme s výberom', 'Predajňa v Bratislave',
                  'Doprava po celom Slovensku', 'Odborné poradenstvo', 'Ďalekohľad ako darček'],
                 ['Ďalekohľady na turistiku, prírodu aj šport. Pomôžeme vybrať zväčšenie a objektív.', D_STORE]),
 'Astronomické binokuláre': (['Astronomické binokuláre', 'Binokuláre na nočnú oblohu', 'Binokuláre na hviezdy', 'Poradíme s výberom', 'Predajňa v Bratislave'],
               ['Astronomické binokuláre na pozorovanie nočnej oblohy. Pomôžeme vybrať model.', D_STORE]),
 'Detské ďalekohľady': (['Detské ďalekohľady', 'Ďalekohľady pre deti', 'Ďalekohľad ako darček', 'Poradíme s výberom | Sonata'],
               ['Detské ďalekohľady na prírodu a výlety. Pomôžeme vybrať model podľa veku dieťaťa.', D_STORE]),
 'Turistické ďalekohľady': (['Turistické ďalekohľady', 'Ďalekohľady na turistiku', 'Ďalekohľady na výlety', 'Poradíme s výberom', 'Predajňa v Bratislave'],
               ['Turistické ďalekohľady na výlety a prírodu. Pomôžeme vybrať zväčšenie a objektív.', D_STORE]),
 'Ornitologické ďalekohľady': (['Ornitologické ďalekohľady', 'Ďalekohľady na vtáky', 'Pozorovanie vtákov', 'Poradíme s výberom', 'Predajňa v Bratislave'],
               ['Ďalekohľady na pozorovanie vtákov a prírody. Pomôžeme vybrať vhodný model.', D_STORE]),
 'Vreckové ďalekohľady': (['Vreckové ďalekohľady', 'Kompaktné ďalekohľady', 'Malé ďalekohľady na cesty', 'Poradíme s výberom', 'Predajňa v Bratislave'],
               ['Vreckové a kompaktné ďalekohľady na cesty a výlety. Pomôžeme vybrať model.', D_STORE]),
 'Mikroskopy': (['Mikroskopy | Sonata Optics', 'Biologické a stereo mikroskopy', 'Mikroskopy pre školy a firmy', 'Poradíme s výberom', 'Predajňa v Bratislave',
                 'Doprava po celom Slovensku', 'Odborné poradenstvo'],
                ['Mikroskopy pre školy, laboratóriá aj hobby. Pomôžeme vybrať správny model.', D_STORE]),
 'Mikroskopy pre deti a školské': (['Mikroskopy pre deti', 'Školské mikroskopy', 'Mikroskop ako darček', 'Poradíme s výberom | Sonata', 'Predajňa v Bratislave'],
               ['Mikroskopy pre deti a školákov. Pomôžeme vybrať model podľa veku a použitia.', D_STORE]),
 'Digitálne mikroskopy': (['Digitálne mikroskopy', 'Mikroskopy s kamerou', 'Odborné poradenstvo | Sonata', 'Predajňa v Bratislave', 'Poradíme s výberom'],
               ['Digitálne mikroskopy. Pomôžeme vybrať model podľa vašich požiadaviek.', D_STORE]),
 'Stereomikroskopy': (['Stereomikroskopy', 'Stereoskopické mikroskopy', 'Odborné poradenstvo | Sonata', 'Predajňa v Bratislave', 'Poradíme s výberom'],
               ['Stereoskopické mikroskopy pre servis, elektroniku, laboratóriá aj hobby. Poradíme.', 'Pomôžeme vybrať stereomikroskop na vašu prácu. Predajňa v Bratislave.']),
}
for s in V2.SIZES:
    CAT_COPY[f'Ďalekohľady {s}'] = SIZE_T(s)
MODEL_H1 = {'Sky-Watcher Explorer 130/900 EQ2': 'Sky-Watcher 130/900 EQ2', 'Levenhuk New Karma PLUS 10x42': 'Levenhuk Karma PLUS 10x42',
            'Bresser Messier AR-127S EXOS-2': 'Bresser Messier AR-127S', 'Omegon Binofield 40-800x LED': 'Omegon Binofield 40-800x'}
BRAND_H_OVERRIDE = {('Teleskopy', 'National Geographic'): ['Teleskopy National Geographic', 'National Geographic | Sonata'],
                    ('Teleskopy', 'Explore Scientific'): ['Teleskopy Explore Scientific', 'Explore Scientific | Sonata'],
                    ('Ďalekohľady', 'National Geographic'): ['National Geographic binokuláre', 'Optika National Geographic']}

def fit(t, n, where, problems):
    if len(t) > n:
        problems.append(f'{where}: "{t}" ({len(t)} > {n})')
    return t

def copy_for(c, g, old_h, old_d, problems):
    if c == KAT:
        h, d = CAT_COPY[g]
    elif g.startswith('Model | '):
        name = g[len('Model | '):]
        h = [MODEL_H1.get(name, name), 'Sonata Optics', 'Predajňa v Bratislave', 'Poradíme s výberom', 'Doprava po celom Slovensku', 'Odborné poradenstvo', 'Nákup s istotou', 'Aktuálna cena online']
        d = P.MODEL_RSA_D
    elif c == ZNM:
        title, b = g.split(' | ', 1)
        h1, h2 = BRAND_H_OVERRIDE.get((title, b), [f'{title} {b}', f'{b} | Sonata Optics' if len(f'{b} | Sonata Optics') <= 30 else f'{b} | Sonata'])
        h = [h1, h2, f'Celý výber {b}' if len(f'Celý výber {b}') <= 30 else f'Výber {b}', 'Predajňa v Bratislave', 'Poradíme s výberom', 'Doprava po celom Slovensku',
             'Odborné poradenstvo', 'Vyskúšajte v predajni', 'Nákup s istotou', 'Aktuálne ceny online']
        if b in P.STATUS: h.insert(2, P.STATUS[b])
        d = [f'{title} {b} – aktuálna ponuka a ceny. Pomôžeme vybrať správny model.', 'Predajňa v Bratislave, doprava po celom Slovensku. Poradíme pred nákupom.',
             'Odborná rada k výberu aj príslušenstvu. Sonata Optics – špecialisti na optiku.']
        if len(d[0]) > 90: d[0] = f'{title} {b}. Pomôžeme vybrať správny model.'
        if b in P.STATUS: d.insert(0, f'{P.STATUS[b]}. Predajňa v Bratislave, doprava po Slovensku.')
    else:
        h, d = list(old_h), list(old_d)
    h = [fit(x, 30, f'{g} H', problems) for x in h]; d = [fit(x, 90, f'{g} D', problems) for x in d]
    return h, d

def landing(urls):
    res = []
    for u in sorted(urls):
        try:
            req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (compatible; SonataAdsLandingCheck/1.0)'})
            with urllib.request.urlopen(req, timeout=30) as r:
                code, html, final = r.status, r.read().decode('utf-8', 'ignore'), r.geturl()
        except Exception as e:
            res.append(dict(url=u, http=getattr(e, 'code', 'ERR'), redirected_to='', product_count='', buyable_detected='', result='FAIL')); continue
        pdp = u.endswith('.html')
        counts = [int(x.replace(' ', '').replace('\xa0', '')) for x in re.findall(r'(\d[\d\s\xa0]*)\s*produkt', html)]
        cnt = min(counts) if counts and not pdp else ''          # listing counter; '' = unknown (never coerced to 1)
        buy = ('do košíka' in html.lower() or 'add_to_cart' in html.lower())
        oos = pdp and ('Na objednávku' in html or 'Vypredané' in html) and 'Skladom' not in html
        info = u.rstrip('/').endswith('/kontakt')    # info page (showroom): HTTP 200 + no redirect; no product counter expected
        if info: cnt = 'n/a (info page)'
        ok = code == 200 and final.rstrip('/') == u.rstrip('/') and (info or (pdp and buy and not oos) or (not pdp and isinstance(cnt, int) and cnt > 0))
        res.append(dict(url=u, http=code, redirected_to='' if final == u else final, product_count=cnt, buyable_detected=buy, result='PASS' if ok else 'FAIL'))
        time.sleep(0.4)
    return res

SEM_EXTRA = [
 ('vortex crossfire montaz', None, 'GEM-05'), ('vortex crossfire hd 12x50 montaz', None, 'GEM-05'),
 ('vortex crossfire hd 12x50', SITE + '/alekohlad-vortex-crossfire-hd-12x50-ru-sk.html', 'model PDP (policy HOLD still applies)'),
 ('mikroskop popis', None, 'GEM-04: no positive route (not a guarantee against Google close variants)'), ('mikroskop cena', U('/mikroskopy/'), 'GEM-04 kept'),
 ('predajna mikroskopov', SITE + '/mikroskopy/', 'GEM-08'), ('predajňa mikroskopov', SITE + '/mikroskopy/', 'GEM-08'),
 ('osobny odber dalekohlad', SITE + '/dalekohlady/', 'GEM-08'), ('osobný odber ďalekohľad', SITE + '/dalekohlady/', 'GEM-08'),
 ('teleskop celestron bratislava', SITE + '/teleskopy/', 'GEM-08 brand+category+city -> store telescopes'),
 ('dalekohlad 10x42 bratislava', SITE + '/dalekohlady/', 'GEM-08 size+city -> store binoculars (documented: category page, not the 10x42 page)'),
 ('dalekohlad leica bratislava', SITE + '/dalekohlady/', 'brand+category+city'),
 ('predajna mikroskopov okuliare', None, 'eyewear blocked'), ('predajna dalekohladov na pusku', None, 'weapon wording blocked'),
 ('dalekohlad bratislava puskohlad', None, 'weapon wording blocked in store'),
 ('celestron bratislava', None, 'documented gap: brand + city without category -> no ad (not a random PDP)'),
]

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    kw0, rsa0, neg = V2.build()
    for t in STORE_WEAPON_NEG:
        neg.append([PRED, '', 'PHRASE', t, 'weapon wording not for the showroom campaign'])
    seen, kw, dups = set(), [], []
    for r in kw0:                                                   # GEM-06 dedupe
        key = (r[0], r[1], r[2].lower(), r[3])
        if key in seen: dups.append(r); continue
        seen.add(key); kw.append(r)
    problems, rsa, ba = [], [], []
    for c, g, url, h, d in rsa0:
        nh, nd = copy_for(c, g, h, d, problems)
        rsa.append([c, g, url, nh, nd])
        for kind, old, new in (('H', h, nh), ('D', d, nd)):
            for i in range(max(len(old), len(new))):
                o = old[i] if i < len(old) else ''; n = new[i] if i < len(new) else ''
                if o != n: ba.append([c, g, f'{kind}{i + 1}', o, n, len(n)])
    route = V2.router(kw, neg, NE.apply())
    out, bad = [], 0
    def chk(ok, msg):
        nonlocal bad; bad += not ok; out.append(('PASS ' if ok else 'FAIL ') + msg)
    chk(not problems, f'no text exceeds limits (no truncation applied): {problems[:5]}')
    keys = [(r[0], r[1], r[2].lower(), r[3]) for r in kw]
    chk(len(keys) == len(set(keys)), f'unique (campaign, group, keyword, match): {len(keys)} rows, removed duplicates {[(d[1], d[2], d[3]) for d in dups]}')
    chk(not any(r[2] == 'mikroskop popis' for r in kw), 'positive "mikroskop popis" removed')
    for g in ('Ďalekohľady | Vortex', 'Model | Vortex Crossfire HD 12x50'):
        have = {t for c2, g2, m2, t, _ in neg if g2 == g}
        chk(all(t in have for t in V2.VORTEX_WEAPON_NEG), f'full Vortex negative set incl. montaz in [{g}]')
    for c, g, url, h, d in rsa:
        chk(3 <= len(h) <= 15 and len(set(h)) == len(h), f'headlines count/unique: {g}')
        chk(2 <= len(d) <= 4, f'descriptions count: {g}')
        chk(not [x for x in h + d if P.BANNED.search(x)], f'no banned words/claims: {g}')
        if c == KAT:   # copy matches its own landing: no foreign brand names, no foreign size
            allb = sorted({b for v in V2.BRANDS.values() for b in v} | {'Pulsar', 'Hikmicro', 'Swarovski', 'Nikon', 'Bushnell'})
            foreign = [x for x in h + d if any(re.search(r'(?i)(?<!\w)' + re.escape(bb) + r'(?!\w)', x) for bb in allb)] if g not in ('Teleskopy',) else []
            if g.startswith('Ďalekohľady ') and re.match(r'Ďalekohľady \d', g):
                s = g.split(' ', 1)[1]
                foreign += [x for x in h + d if set(re.findall(r'\d+x\d+', x)) - {s}]   # R5-CHATGPT-26: any foreign size, also mixed
            chk(not foreign, f'copy matches landing (no foreign brand/size): {g} {foreign[:2]}')
    for c, g, k, m, url in kw:
        r = route(k)
        chk(len(r) == 1 and r[0][1] == g, f'keyword reaches only its group: [{g}] {k} {m} -> {[x[1] for x in r]}')
    sem = []
    for q, exp, note in V2.SEM + SEM_EXTRA:
        if q == 'mikroskop popis': pass
        r = route(q)
        got = r[0][2] if len(r) == 1 else (None if not r else 'AMBIGUOUS:' + ' | '.join(x[1] for x in r))
        ok = got == exp
        chk(ok, f'semantic: "{q}" -> {got} (expected {exp})')
        sem.append(dict(query=q, expected=exp or '(no ad)', got=got or '(no ad)', groups=' | '.join(x[1] for x in r) or '-', result='PASS' if ok else 'FAIL', note=note))
    W = lambda name, head, rows: csv.writer(open(os.path.join(HERE, name), 'w', newline='', encoding='utf-8')).writerows([head] + rows)
    W('search_keywords.csv', ['campaign', 'ad_group', 'keyword', 'match_type', 'final_url'], kw)
    W('search_rsa.csv', ['campaign', 'ad_group', 'final_url'] + [f'H{i}' for i in range(1, 16)] + [f'D{i}' for i in range(1, 5)],
      [[c, g, u] + (h + [''] * 15)[:15] + (d + [''] * 4)[:4] for c, g, u, h, d in rsa])
    W('search_rsa_before_after.csv', ['campaign', 'ad_group', 'field', 'before (move 19)', 'after (move 22)', 'len_after'], ba)
    W('search_negatives.csv', ['campaign', 'ad_group (empty = campaign level)', 'match_type', 'negative', 'reason'], neg)
    W('search_semantic_tests.csv', list(sem[0].keys()), [list(x.values()) for x in sem])
    if '--check-landing' in sys.argv:
        lr = landing({r[4] for r in kw} | {r[2] for r in rsa})
        W('search_landing_check.csv', list(lr[0].keys()), [list(x.values()) for x in lr])
        lb = sum(1 for x in lr if x['result'] == 'FAIL'); chk(not lb, f'landing pages {len(lr) - lb}/{len(lr)} (listing: counter > 0; PDP: buyable and not on-order)')
    groups = sorted({(r[0], r[1]) for r in rsa})
    changed = sorted({(x[0], x[1]) for x in ba})
    summary = f'keywords {len(kw)}, ad groups {len(groups)}, negatives {len(neg)}, semantic tests {len(sem)}, RSA groups with changed copy {len(changed)}; checks {len(out) - bad}/{len(out)} PASS'
    open(os.path.join(HERE, 'search_checks.txt'), 'w', encoding='utf-8').write('\n'.join(out + [summary]) + '\n')
    W('changed_groups.csv', ['campaign', 'ad_group'], [list(x) for x in changed])
    for line in out:
        if line.startswith('FAIL'): print(line)
    print(summary)
    return bad

if __name__ == '__main__':
    sys.exit(1 if main() else 0)
