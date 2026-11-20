"""PASS B (independent code path; shares no code with pass_a.py):
  2022 votes/ballots : official SOS canvass PDF converted with `pdftotext -layout` and parsed as PLAIN TEXT lines
  2026 votes/ballots : RENDERED public results pages (innerText of app.enhancedvoting.com/results/public/{county}/elections/110326GeneralElection),
                       never the JSON API files
  registration       : SOS 'State Voter Registration' PDF reports (2022 General, November 2026) via pdftotext, never the CSVs
Writes verification/passB_counties.csv and passB_statewide.json."""
import subprocess, re, json, os
from fractions import Fraction
RAW='/workspace/az-clean/raw/'; VER='/workspace/az-clean/verification/'
ORDER=['Apache','Cochise','Coconino','Gila','Graham','Greenlee','La Paz','Maricopa','Mohave','Navajo','Pima','Pinal','Santa Cruz','Yavapai','Yuma']
SLUG={c:c.lower().replace(' ','-')+'-county-az' for c in ORDER}
def txt(pdf): return subprocess.run(['pdftotext','-layout',pdf,'-'],capture_output=True,text=True,check=True).stdout
def ints(s): return [int(x.replace(',','')) for x in re.findall(r'(?<![\w.])\d{1,3}(?:,\d{3})*(?![\w.%])',s)]
rec={c:{} for c in ORDER}
# ---------- 2022 canvass, plain text
T=txt(RAW+'2022/2022dec05_general_election_canvass_web.pdf').split('\n')
hdr=[l for l in T if l.strip().startswith('Apache') and 'TOTAL' in l][0]
assert re.sub(r'\s+',' ',hdr).strip()=='Apache Cochise Coconino Gila Graham Greenlee La Paz Maricopa Mohave Navajo Pima Pinal Cruz Yavapai Yuma TOTAL'
def row16(line):
    v=ints(line.split('  ',1)[1] if '  ' in line else line); assert len(v)==16,(line,v); assert sum(v[:15])==v[15]; return v
bal=row16([l for l in T if l.startswith('Total Ballots Cast')][0])
gi=[i for i,l in enumerate(T) if l.strip()=='Governor'][0]
block=[]
for l in T[gi+1:]:
    if not l.strip(): break
    block.append(l)
cand=[]
for l in block:
    body=re.sub(r'^\(\w+\)\s.*?(?=\s{2,}\d)','',l) if l.startswith('(') else l
    v=ints(body)
    if len(v)==16: cand.append((l[:40].strip(),v))
dem=[v for n,v in cand if n.startswith('(DEM) Katie Hobbs')]; rep=[v for n,v in cand if n.startswith('(REP) Kari Lake')]
assert len(dem)==1 and len(rep)==1 and len(cand)==9, cand
for i,c in enumerate(ORDER):
    rec[c].update(ballots_2022=bal[i],dem_2022=dem[0][i],rep_2022=rep[0][i],govtotal_2022=sum(v[i] for n,v in cand))
sw22=dict(ballots=bal[15],dem=dem[0][15],rep=rep[0][15],govtotal=sum(v[15] for n,v in cand))
# ---------- registration PDFs
def reg_pdf(fn,tag):
    L=txt(fn).split('\n'); hi=[i for i,l in enumerate(L) if l.startswith('County') and 'Democratic' in l][0]
    parties=re.findall(r'Democratic|Green|Libertarian|No Labels|Republican|Other|Total',L[hi])
    res={}; cur=None; pending=''
    for l in L[hi+1:]:
        if l.startswith('Active') or 'District' in l[:10]: break
        m=re.match(r'^([A-Z][a-z]+(?: [A-Z][a-z]+)?:?)\s+[\d,]+\s+(APR|PE|P\.E\.|GE|G\.E\.)',l)
        if m and 'APR' in l: pending=m.group(1); cur=pending
        elif m: cur=(pending+' '+m.group(1)).strip() if pending in ('Santa',) else cur
        if re.search(r'\s'+re.escape(tag)+r'\s',l):
            nm={'Santa Cruz':'Santa Cruz','Totals:':'TOTAL'}.get(cur,cur)
            v=ints(l.split(tag,1)[1]); assert len(v)==len(parties),(l,v,parties)
            res[nm]=dict(zip(parties,v))
            if nm=='TOTAL': break
    return res
g22=reg_pdf(RAW+'registration/State_Voter_Registration_2022_General.pdf','G.E. 2022')
g26=reg_pdf(RAW+'registration/State-Voter-Registration-November-2026.pdf','GE 2026')
assert set(g22)==set(ORDER+['TOTAL'])==set(g26), (sorted(g22),sorted(g26))
for c in ORDER:
    rec[c].update(regdem_2022=g22[c]['Democratic'],regrep_2022=g22[c]['Republican'],regact_2022=g22[c]['Total'],
                  regdem_2026=g26[c]['Democratic'],regrep_2026=g26[c]['Republican'],regact_2026=g26[c]['Total'])
# ---------- 2026 rendered pages
asof=set()
for c in ORDER:
    t=open(RAW+f'2026/rendered/{SLUG[c]}.txt').read().split('\n')
    st=[l for l in t[:8] if l.endswith('OFFICIAL RESULTS')]; assert len(st)==1; rec[c]['county_page_status_2026']=st[0]
    asof.add([l for l in t if l.startswith('Last Updated')][0])
    bi=t.index('Ballots Cast'); rec[c]['ballots_2026']=int(t[bi+1].replace(',',''))
    rec[c]['reg_rendered_2026']=int(t[t.index('Registered Voters')+1].replace(',',''))
    g=t.index('Governor and Lieutenant Governor'); e=next(i for i in range(g,len(t)) if t[i].startswith('Precincts reporting'))
    seg=t[g:e]; votes={}
    for i,l in enumerate(seg):
        if l=='Candidate' and i+1<len(seg) and seg[i+1] not in ('Percentage',):
            name=seg[i+1]; j=seg.index('Votes',i+1); votes[name]=int(seg[j+1].replace(',',''))
    rec[c]['dem_2026']=[v for k,v in votes.items() if k.startswith('Katie Hobbs (DEM)')][0]
    rec[c]['rep_2026']=[v for k,v in votes.items() if k.startswith('Andy Biggs (REP)')][0]
    rec[c]['govtotal_2026']=sum(votes.values()); rec[c]['rendered_candidates_2026']=votes
# ---------- derived figures, exact rational arithmetic (pass A uses floating point)
def pct(a,b): return Fraction(a)*100/Fraction(b)
for c in ORDER:
    r=rec[c]
    S22,S26=pct(r['dem_2022'],r['ballots_2022']),pct(r['dem_2026'],r['ballots_2026'])
    P22,P26=pct(r['regdem_2022'],r['regact_2022']),pct(r['regdem_2026'],r['regact_2026'])
    dS,dP=S26-S22,P26-P22; dG=dS-dP
    d=dict(S22=S22,S26=S26,P22=P22,P26=P26,G22=S22-P22,G26=S26-P26,dS=dS,dP=dP,dG=dG,
           residual=(dG-abs(dP)) if r['regdem_2026']<r['regdem_2022'] else None,
           implied_extra_votes=Fraction(r['dem_2026'])-S22/100*r['ballots_2026'],
           gap_reg_scaled=Fraction(r['dem_2026'])-Fraction(r['dem_2022'])*Fraction(r['regdem_2026'],r['regdem_2022']))
    for k in ('regdem','dem','ballots'):
        d[f'{k}_chg']=r[f'{k}_2026']-r[f'{k}_2022']; d[f'{k}_chg_pct']=pct(d[f'{k}_chg'],r[f'{k}_2022'])
    r.update({k:(float(v) if isinstance(v,Fraction) else v) for k,v in d.items()})
tot={k:sum(rec[c][k] for c in ORDER) for k in ('ballots_2022','dem_2022','rep_2022','govtotal_2022','regdem_2022','regrep_2022','regact_2022','ballots_2026','dem_2026','rep_2026','govtotal_2026','regdem_2026','regrep_2026','regact_2026')}
S22,S26=pct(tot['dem_2022'],tot['ballots_2022']),pct(tot['dem_2026'],tot['ballots_2026']); P22,P26=pct(tot['regdem_2022'],tot['regact_2022']),pct(tot['regdem_2026'],tot['regact_2026'])
sw=dict(tot,S22=float(S22),S26=float(S26),P22=float(P22),P26=float(P26),dS=float(S26-S22),dP=float(P26-P22),dG=float((S26-S22)-(P26-P22)),
        implied_extra_sum=float(sum(Fraction(rec[c]['dem_2026'])-pct(rec[c]['dem_2022'],rec[c]['ballots_2022'])/100*rec[c]['ballots_2026'] for c in ORDER)),
        implied_extra_pooled=float((S26-S22)/100*tot['ballots_2026']))
for k in ('regdem','dem','ballots'):
    sw[f'{k}_chg']=tot[f'{k}_2026']-tot[f'{k}_2022']; sw[f'{k}_chg_pct']=float(pct(sw[f'{k}_chg'],tot[f'{k}_2022']))
json.dump(dict(county=rec,statewide=sw,sos2022_total_column=sw22,sos_registration_totals=dict(g22=g22['TOTAL'],g26=g26['TOTAL']),rendered_last_updated=sorted(asof)),open(VER+'passB_statewide.json','w'),indent=1)
import csv
K=[k for k in rec['Apache'] if k not in ('rendered_candidates_2026',)]
with open(VER+'passB_counties.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['county']+K)
    for c in ORDER: w.writerow([c]+[repr(rec[c][k]) if isinstance(rec[c][k],float) else rec[c][k] for k in K])
print('pass B ok', sorted(asof), json.dumps(sw,indent=0)[:1500])
