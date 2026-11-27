import csv,json,re,sys,pathlib,collections
ROOT=pathlib.Path(sys.argv[1]); OUT=pathlib.Path(sys.argv[2])
def read(n): return list(csv.DictReader((ROOT/n).open()))
checks=[]
def check(ok,msg): checks.append({'pass':bool(ok),'check':msg})
kw,rsa,neg,sem,land,manifest,changes,ba=[read(n) for n in ['search_keywords.csv','search_rsa.csv','search_negatives.csv','search_semantic_tests.csv','search_landing_check.csv','launch_manifest.csv','changed_groups.csv','search_rsa_before_after.csv']]
key=lambda r:(r['campaign'],r['ad_group'])
check((len(kw),len(rsa),len(neg),len(sem))==(533,68,514,69),'published counts')
check(len({(*key(r),r['keyword'].lower(),r['match_type']) for r in kw})==len(kw),'keyword uniqueness')
check(not any(r['keyword']=='mikroskop popis' for r in kw),'popis positive removed')
check(any(r['keyword']=='mikroskop cena' for r in kw),'cena positive retained')
check(not any(r['negative']=='popis' for r in neg),'no popis negative in Search CSV')
expected={('Model | Sky-Watcher Explorer 130/900 EQ2','H1'):'Sky-Watcher 130/900 EQ2',('Teleskopy | National Geographic','H2'):'National Geographic | Sonata',('Teleskopy | Explore Scientific','H2'):'Explore Scientific | Sonata',('Ďalekohľady | National Geographic','H1'):'National Geographic binokuláre',('Ďalekohľady | National Geographic','H2'):'Optika National Geographic'}
for (g,f),v in expected.items(): check(next(r[f] for r in rsa if r['ad_group']==g)==v,f'exact 21b text {g}/{f}')
for r in rsa:
 h=[r[f'H{i}'] for i in range(1,16) if r[f'H{i}']]; d=[r[f'D{i}'] for i in range(1,5) if r[f'D{i}']]
 check(all(len(t)<=30 for t in h) and all(len(t)<=90 for t in d),f'lengths {key(r)}')
 check(3<=len(h)<=15 and len(set(h))==len(h) and 2<=len(d)<=4,f'asset counts and unique H {key(r)}')
 if r['campaign'].endswith('Kategórie'):
  t=' '.join(h+d); sizes=set(re.findall(r'\d+x\d+',t)); own=set(re.findall(r'\d+x\d+',r['ad_group']))
  check(not re.search(r'Leica|Zeiss|Meopta|Celestron|Sky-Watcher|Vortex|Bresser|Levenhuk|USB|LCD|odolné|ľahké|Jednoduché ovládanie',t) and sizes<=own,f'category copy has no foreign claims/brands/sizes {key(r)}')
check(set(map(key,changes))==set(map(key,ba)) and len(changes)==27,'exact changed group list')
new={key(r):r for r in rsa}
check(all(new[key(r)].get(r['field'],'')==r['after (move 22)'] for r in ba),'before-after values match final RSA')
old_path=ROOT.parent/'19_claude_code_attachments/search_rsa.csv'
if not old_path.exists():old_path=ROOT.parent/'p19/search_rsa.csv'
old=list(csv.DictReader(old_path.open()))
oldmap={key(r):r for r in old}
actual={(key(r),f) for r in rsa for f in r if f.startswith(('H','D')) and r[f]!=oldmap[key(r)][f]}
check(actual=={(key(r),r['field']) for r in ba},'before-after covers ALL changed fields relative to move19')
check(all(oldmap[key(r)].get(r['field'],'')==r['before (move 19)'] for r in ba),'before values match move19')
for g in ['Ďalekohľady | Vortex','Model | Vortex Crossfire HD 12x50']:
 check(any(r['ad_group (empty = campaign level)']==g and r['negative']=='montaz' for r in neg),f'local montaz {g}')
check(all(r['ad_group (empty = campaign level)'] in ['Ďalekohľady | Vortex','Model | Vortex Crossfire HD 12x50'] for r in neg if r['negative']=='scope'),'scope stays local')
statuses=collections.Counter(r['status'] for r in manifest)
check(statuses=={'READY_AFTER_OWNER_YES':9,'READY_PENDING_OWN_POLICY':65,'HOLD_POLICY':3,'HOLD':1,'DO_NOT_TOUCH_UNTIL_APPEAL_DECIDED':1,'REQUIRED':1},'manifest exact statuses')
search=[r for r in manifest if r['scope']=='new Search group']
check({r['object'] for r in search}=={r['campaign']+' / '+r['ad_group'] for r in rsa},'manifest covers exactly all 68 Search groups')
check(all('THIN ASSORTMENT' in r['gate before ENABLE'] for r in search if r['object'].endswith('/ Detské ďalekohľady')),'thin assortment gate')
urls={r['final_url'] for r in kw+rsa}
check(urls=={r['url'] for r in land} and len(land)==62,'landing inventory exact coverage')
check(all(r['result']=='PASS' for r in land),'published landing report PASS (not fresh live proof)')
# Independent literal matcher against final CSV; no dependency on Code router.
def hit(q,t,m):
 q=q.lower().split();t=t.lower().split()
 if m=='EXACT':return q==t
 if m=='BROAD':return set(t)<=set(q)
 return any(q[i:i+len(t)]==t for i in range(len(q)-len(t)+1))
inputs=ROOT if (ROOT/'account_level_negatives_2026-11-26.json').exists() else ROOT.parent/'07_claude_code_attachments'
acc=json.loads((inputs/'account_level_negatives_2026-11-26.json').read_text())['keywords']
diff=list(csv.DictReader((inputs/'negatives_account_diff.csv').open()))
remove={(r['match_type'],r['text']) for r in diff if r['action']=='REMOVE'}
account=[(r['match_type'],r['text']) for r in acc if (r['match_type'],r['text']) not in remove]
account +=[(r['match_type'],r['text']) for r in diff if r['action']=='ADD']
def route(q):
 if any(hit(q,t,m) for m,t in account):return set()
 return {(r['ad_group'],r['final_url']) for r in kw if hit(q,r['keyword'],r['match_type']) and not any(n['campaign']==r['campaign'] and n['ad_group (empty = campaign level)'] in ('',r['ad_group']) and hit(q,n['negative'],n['match_type']) for n in neg)}
for s in sem:
 r=route(s['query']); got=next(iter(r))[1] if len(r)==1 else '(no ad)' if not r else 'AMBIGUOUS'
 check(got==s['expected'],f'independent CSV route: {s["query"]}')
for base in ['vortex crossfire','vortex crossfire hd 12x50']:
 for term in ['montaz','montáž','scope','rifle scope','puškohľad','mrad','bdc']:
  for q in [base+' '+term,term+' '+base]:check(not route(q),f'independent weapon exclusion {q}')
for base in ['predajna mikroskopov','osobny odber dalekohlad','dalekohlad 10x42 bratislava','teleskop celestron bratislava']:
 for term in ['okuliare','na pusku','puškohľad']:
  check(not route(base+' '+term),f'independent store exclusion {base} {term}')
OUT.write_text(json.dumps({'passed':sum(x['pass'] for x in checks),'total':len(checks),'checks':checks},ensure_ascii=False,indent=2))
print(f"Independent checks: {sum(x['pass'] for x in checks)}/{len(checks)}")
for c in checks:
 if not c['pass']:print('FAIL',c['check'])
sys.exit(any(not c['pass'] for c in checks))
