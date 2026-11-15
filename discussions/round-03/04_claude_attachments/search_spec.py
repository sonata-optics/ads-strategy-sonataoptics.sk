#!/usr/bin/env python3
"""Round-3 model Search spec for 4 control SKUs + deterministic routing simulation.
Outputs: search_keywords.csv, search_negatives.csv, search_rsa.csv, search_routing_results.csv
Simulation covers ONLY literal keyword/negative logic (identical exact, phrase containment, negative
broad/phrase/exact). Google close variants, spell correction and Ad Rank are NOT simulated:
results are a pre-flight check, not a prediction of live serving.
"""
import csv, re, sys, unicodedata
out = sys.argv[1] if len(sys.argv) > 1 else '.'
def norm(s, strip_diacritics=False):
    s = s.lower().replace('×', 'x').replace('–', ' ').replace('-', ' ')
    s = re.sub(r'(\d)\s*x\s*(\d)', r'\1x\2', s)          # "10 x 42" -> "10x42" (assumption, verify)
    if strip_diacritics:
        s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return ' '.join(s.split())

G = {
 'AG_103933_Leica_Trinovid_10x42_HD': dict(
   offer='103933', url='https://sonataoptics.sk/leica-trinovid-10x42-hd-alekohlad.html',
   exact=['leica trinovid 10x42 hd','leica trinovid hd 10x42','trinovid 10x42 hd','leica trinovid 10x42','ďalekohľad leica trinovid 10x42'],
   phrase=['trinovid 10x42','trinovid hd 10x42'],
   neg=[('phrase','8x42'),('phrase','10x32'),('phrase','8x32'),('phrase','10x25'),('phrase','8x20'),
        ('broad','bca'),('broad','ultravid'),('broad','noctivid'),('broad','geovid'),('broad','retrovid'),('broad','monokulár'),('broad','monokular')],
   rsa_h=[('Leica Trinovid 10×42 HD','H1'),('Binokulárny ďalekohľad Leica',''),('Zväčšenie 10×, objektív 42 mm',''),
          ('Prémiová optika Leica',''),('Na pozorovanie prírody',''),('Kúpte v Sonata Optics',''),('Obchod s optikou',''),
          ('Trinovid HD 10×42 online','')],
   rsa_d=['Leica Trinovid 10×42 HD – binokulárny ďalekohľad. Parametre a cenu nájdete na webe.',
          'Objednajte online v Sonata Optics, obchode s optikou.'],
   cond=[('Cena {CUSTOMIZER.cena}','price customizer — only from the same source as landing price'),
         ('Skladom – odosielame ihneď','only with live stock sync + owner-confirmed dispatch time')]),
 'AG_26113_Levenhuk_Vegas_ED_10x42': dict(
   offer='26113', url='https://sonataoptics.sk/levenhuk-vegas-ed-10x42-binoculars.html',
   exact=['levenhuk vegas ed 10x42','vegas ed 10x42','ďalekohľad levenhuk vegas ed 10x42'],
   phrase=['levenhuk vegas ed 10x42'],
   neg=[('broad','new'),('broad','nový'),('broad','novy'),('phrase','8x42'),('phrase','10x50'),('phrase','12x50'),('phrase','10x56'),('phrase','12x56'),
        ('broad','monokulár'),('broad','monokular'),('broad','monocular')],
   rsa_h=[('Levenhuk Vegas ED 10×42','H1'),('Binokulárny ďalekohľad 10×42',''),('Optika s ED sklom',''),
          ('Zväčšenie 10×, objektív 42 mm',''),('Kúpte v Sonata Optics',''),('Obchod s optikou','')],
   rsa_d=['Levenhuk Vegas ED 10×42 – binokulárny ďalekohľad s ED sklom. Parametre a cena na webe.',
          'Objednajte online v Sonata Optics, obchode s optikou.'],
   cond=[('Cena {CUSTOMIZER.cena}','price customizer'),('Skladom','only with live stock sync')]),
 'AG_103640_Levenhuk_New_Vegas_ED_10x42': dict(
   offer='103640', url='https://sonataoptics.sk/levenhuk-new-vegas-ed-10x42-binokular.html',
   exact=['levenhuk new vegas ed 10x42','new vegas ed 10x42','ďalekohľad levenhuk new vegas ed 10x42'],
   phrase=['new vegas ed 10x42'],
   neg=[('phrase','8x42'),('phrase','10x50'),('phrase','12x50'),('phrase','10x56'),('phrase','12x56'),
        ('broad','monokulár'),('broad','monokular'),('broad','monocular')],
   rsa_h=[('Levenhuk New Vegas ED 10×42','H1'),('Nová rada Vegas ED',''),('Binokulárny ďalekohľad 10×42',''),
          ('Optika s ED sklom',''),('Zväčšenie 10×, objektív 42 mm',''),('Kúpte v Sonata Optics','')],
   rsa_d=['Levenhuk New Vegas ED 10×42 – binokulárny ďalekohľad s ED sklom. Parametre na webe.',
          'Objednajte online v Sonata Optics, obchode s optikou.'],
   cond=[('Cena {CUSTOMIZER.cena}','price customizer'),('Skladom','only with live stock sync')]),
 'AG_47420_SkyWatcher_Explorer_150PDS_EQ3': dict(
   offer='47420', url='https://sonataoptics.sk/skywatcher-teleskop-n-150-750-pds-explorer-bd-eq3.html',
   exact=['sky watcher explorer 150pds eq3','skywatcher explorer 150pds eq3','explorer 150pds eq3','sky watcher 150pds eq3','skywatcher 150pds eq3','teleskop sky watcher 150pds eq3'],
   phrase=['150pds eq3','150 pds eq3'],
   neg=[('broad','goto'),('broad','synscan'),('phrase','eq3 pro'),('broad','eq5'),('broad','ota'),('broad','tubus'),('broad','150p'),('broad','150pl'),
        ('broad','1200'),('broad','heritage'),('broad','dobson'),('phrase','star discovery'),('broad','150i')],
   rsa_h=[('Sky-Watcher 150PDS EQ3','H1'),('Explorer-150PDS na montáži EQ3',''),('Newtonov reflektor 150/750',''),
          ('Dvojrýchlostné zaostrovanie',''),('Hliníkový statív v balení',''),('Kúpte v Sonata Optics',''),('Obchod s optikou','')],
   rsa_d=['Sky-Watcher Explorer-150PDS 150/750 na montáži EQ3 s hliníkovým statívom.',
          'Manuálna montáž EQ3, bez GoTo. Objednajte online v Sonata Optics.'],
   cond=[('Cena {CUSTOMIZER.cena}','price customizer'),('Skladom','only with live stock sync')]),
}
CAMPAIGN_NEG = [('broad','bazár'),('broad','bazar'),('broad','použitý'),('broad','pouzity')]

def neg_hit(q, kind, term):
    qq, t = norm(q), norm(term)
    qd, td = norm(q, True), norm(term, True)
    for a, b in ((qq, t), (qd, td)):   # diacritic-insensitive check shown as separate flag
        qt, tt = a.split(), b.split()
        if kind == 'exact' and a == b: return True
        if kind == 'phrase' and (' ' + b + ' ') in (' ' + a + ' '): return True
        if kind == 'broad' and all(x in qt for x in tt): return True
    return False

TESTS = [
 ('T01','leica trinovid 10x42 hd','AG_103933_Leica_Trinovid_10x42_HD'),
 ('T02','leica trinovid 10x42 hd cena','AG_103933_Leica_Trinovid_10x42_HD'),
 ('T03','ďalekohľad leica trinovid 10x42','AG_103933_Leica_Trinovid_10x42_HD'),
 ('T04','dalekohlad leica trinovid 10x42','AG_103933_Leica_Trinovid_10x42_HD'),
 ('T05','leica trinovid 8x42 hd','NONE'),
 ('T06','leica trinovid 10x25 bca','NONE'),
 ('T07','leica trinovid 10 x 42 hd','AG_103933_Leica_Trinovid_10x42_HD'),
 ('T08','levenhuk vegas ed 10x42','AG_26113_Levenhuk_Vegas_ED_10x42'),
 ('T09','levenhuk new vegas ed 10x42','AG_103640_Levenhuk_New_Vegas_ED_10x42'),
 ('T10','levenhuk vegas ed 10x42 cena','AG_26113_Levenhuk_Vegas_ED_10x42'),
 ('T11','levenhuk vegas ed 10x50 monokular','NONE'),
 ('T12','new vegas ed 10x50','NONE'),
 ('T13','levenhuk vegas 10x42','UNROUTED_BY_DESIGN'),
 ('T14','sky watcher explorer 150pds eq3','AG_47420_SkyWatcher_Explorer_150PDS_EQ3'),
 ('T15','skywatcher explorer-150pds eq3','AG_47420_SkyWatcher_Explorer_150PDS_EQ3'),
 ('T16','sky-watcher 150pds eq3 goto','NONE'),
 ('T17','sky watcher 150p eq3','NONE'),
 ('T18','150pds eq3 cena','AG_47420_SkyWatcher_Explorer_150PDS_EQ3'),
 ('T19','150pds eq3 pro synscan','NONE'),
 ('T20','skywatcher 150pds ota','NONE'),
 ('T21','teleskop 150 pds eq3','AG_47420_SkyWatcher_Explorer_150PDS_EQ3'),
 ('T22','leica trinovid 10x42 hd bazár','NONE'),
 ('T23','ďalekohľad','NONE'),
 ('T24','teleskop pre začiatočníkov','NONE'),
]
def route(q):
    if any(neg_hit(q, k, t) for k, t in CAMPAIGN_NEG): return 'NONE', 'campaign negative'
    cands = []; blocks = []
    for ag, g in G.items():
        blocked = [f'{ag}:{k}:{t}' for k, t in g['neg'] if neg_hit(q, k, t)]
        lit = 0 if norm(q) in [norm(x) for x in g['exact']] else (1 if any((' ' + norm(p) + ' ') in (' ' + norm(q) + ' ') for p in g['phrase']) else None)
        if blocked:
            blocks.extend(blocked)
            continue
        if lit is not None: cands.append((lit, ag, 'identical exact' if lit == 0 else 'phrase contains'))
    if not cands:
        return 'NONE', ('blocked by negatives ' + '; '.join(blocks)) if blocks else 'no literal match (close variants not simulated)'
    cands.sort(); best = [c for c in cands if c[0] == cands[0][0]]
    if len(best) > 1: return 'AMBIGUOUS:' + '|'.join(c[1] for c in best), 'tie → Ad Rank decides'
    return best[0][1], best[0][2]

rows = []
for tid, q, exp in TESTS:
    r, why = route(q)
    ok = (r == exp) or (exp == 'UNROUTED_BY_DESIGN' and r == 'NONE')
    rows.append(dict(test_id=tid, query=q, expected=exp, simulated=r, reason=why, pass_=ok))
with open(f'{out}/search_routing_results.csv','w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
with open(f'{out}/search_keywords.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['ad_group','offer_id','final_url','keyword','match_type'])
    for ag,g in G.items():
        for k in g['exact']: w.writerow([ag,g['offer'],g['url'],k,'EXACT'])
        for k in g['phrase']: w.writerow([ag,g['offer'],g['url'],k,'PHRASE'])
with open(f'{out}/search_negatives.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['level','ad_group','negative','match_type'])
    for k,t in CAMPAIGN_NEG: w.writerow(['campaign','*',t,k.upper()])
    for ag,g in G.items():
        for k,t in g['neg']: w.writerow(['ad_group',ag,t,k.upper()])
problems = 0
with open(f'{out}/search_rsa.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['ad_group','asset_type','text','chars','limit','pin','status','conditional_note'])
    for ag,g in G.items():
        hs=g['rsa_h']; ds=g['rsa_d']
        assert len(hs)>=3 and len(ds)>=2, ag
        assert len({h for h,_ in hs})==len(hs), 'duplicate headline '+ag
        for h,p in hs:
            ok=len(h)<=30; problems += not ok
            w.writerow([ag,'HEADLINE',h,len(h),30,p,'OK' if ok else 'TOO_LONG',''])
        for d in ds:
            ok=len(d)<=90; problems += not ok
            w.writerow([ag,'DESCRIPTION',d,len(d),90,'','OK' if ok else 'TOO_LONG',''])
        for c,note in g['cond']:
            w.writerow([ag,'CONDITIONAL_HEADLINE',c,len(c),30,'','NOT_ACTIVE_UNTIL_SYNC',note])
        for p in ('path1','path2'): pass
print('RSA length problems:', problems)
for r in rows: print(r['test_id'], r['pass_'], r['simulated'], '|', r['reason'])
