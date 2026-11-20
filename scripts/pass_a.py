"""PASS A (Arizona 2022 vs 2026 governor). Independent code path A:
  2022 votes/ballots : official SOS canvass PDF parsed by WORD POSITION (pdfplumber x-coordinates -> county columns)
  2026 votes/ballots : SOS results API JSON (app.enhancedvoting.com .../{county}/110326GeneralElection/data), one file per county
  registration       : SOS 'State Voter Registration' CSV files (2022 General, November 2026), ACTIVE, G.E. row
Writes verification/passA_counties.csv and passA_statewide.json. Reads ONLY files under /workspace/az-clean/raw."""
import csv, json, re, pdfplumber
R='/workspace/az-clean/raw/'; V='/workspace/az-clean/verification/'
COUNTIES=['Apache','Cochise','Coconino','Gila','Graham','Greenlee','La Paz','Maricopa','Mohave','Navajo','Pima','Pinal','Santa Cruz','Yavapai','Yuma']
num=lambda s:int(s.replace(',',''))
out={c:{} for c in COUNTIES}

# ---- 2022 canvass, word positions
pdf=pdfplumber.open(R+'2022/2022dec05_general_election_canvass_web.pdf')
def page_lines(pg):
    W=pg.extract_words(); hdr=[w for w in W if 60<w['top']<68]; cols={}
    for w in hdr:
        if w['text'] in names: cols[names[w['text']]]=w['x1']
    assert len(cols)==16, cols
    L={}
    for w in W: L.setdefault(round(w['top']),[]).append(w)
    return cols,L
names={'Apache':'Apache','Cochise':'Cochise','Coconino':'Coconino','Gila':'Gila','Graham':'Graham','Greenlee':'Greenlee','Paz':'La Paz','Maricopa':'Maricopa','Mohave':'Mohave','Navajo':'Navajo','Pima':'Pima','Pinal':'Pinal','Cruz':'Santa Cruz','Yavapai':'Yavapai','Yuma':'Yuma','TOTAL':'TOTAL'}
def row_values(ws,cols):
    vals={}
    for w in ws:
        if re.fullmatch(r'[\d,]+',w['text']) and w['x0']>150:
            c=min(cols,key=lambda k:abs(cols[k]-w['x1'])); assert abs(cols[c]-w['x1'])<6, (w,c)
            assert c not in vals; vals[c]=num(w['text'])
    return vals
def label(ws): return ' '.join(w['text'] for w in sorted(ws,key=lambda w:w['x0']) if w['x0']<150)
cols0,L0=page_lines(pdf.pages[0])
for t in sorted(L0):
    l=label(L0[t])
    if l=='Total Ballots Cast': BAL=row_values(L0[t],cols0)
    if l=='Total Eligible Registration': REGC=row_values(L0[t],cols0)
gp=[i for i,p in enumerate(pdf.pages) if any(w['text']=='Governor' and w['x0']<30 for w in p.extract_words())]; assert len(gp)==1
cols,L=page_lines(pdf.pages[gp[0]]); tops=sorted(L)
gov_top=[t for t in tops if label(L[t])=='Governor'][0]
ends=[t for t in tops if t>gov_top and label(L[t]) and not row_values(L[t],cols) and not label(L[t]).startswith('(') and not label(L[t]).endswith('In)')]
gov_end=min(ends) if ends else 9999
gov_rows=[]; pend=None
for t in tops:
    if gov_top<t<gov_end:
        l=label(L[t]); v=row_values(L[t],cols)
        if l.startswith('('): pend=l
        if v:
            gov_rows.append((l if l.startswith('(') else pend, v))
for l,v in gov_rows: assert len(v)==16 and sum(v[c] for c in COUNTIES)==v['TOTAL'], (l,v)
cand=[r for r in gov_rows]
dem=[v for l,v in cand if l.startswith('(DEM) Katie Hobbs')]; rep=[v for l,v in cand if l.startswith('(REP) Kari Lake')]
assert len(dem)==1 and len(rep)==1
for c in COUNTIES:
    out[c]['ballots_2022']=BAL[c]; out[c]['dem_2022']=dem[0][c]; out[c]['rep_2022']=rep[0][c]
    out[c]['govtotal_2022']=sum(v[c] for l,v in cand); out[c]['canvass_reg_2022']=REGC[c]
st22=dict(ballots=BAL['TOTAL'],dem=dem[0]['TOTAL'],rep=rep[0]['TOTAL'],govtotal=sum(v['TOTAL'] for l,v in cand),canvass_reg=REGC['TOTAL'],gov_rows=[l for l,v in cand])

# ---- 2026 API JSON
st=json.load(open(R+'2026/az2026_data.json'))
asof=st['election']['asOf']; off=st['election']['isOfficialResults']
for loc in st['jurisdiction']['childLocalities']:
    c=loc['name'][0]['text'].replace(' County','')
    d=json.load(open(R+f"2026/counties/{loc['shortName']}.json"))
    g=[b for b in d['ballotItems'] if b['name'][0]['text']=='Governor and Lieutenant Governor']; assert len(g)==1
    o=g[0]['summaryResults']['ballotOptions']
    out[c]['dem_2026']=[x['voteCount'] for x in o if x['party'] and x['party']['abbreviation']=='DEM' and 'Hobbs' in x['name'][0]['text']][0]
    out[c]['rep_2026']=[x['voteCount'] for x in o if 'Biggs' in x['name'][0]['text']][0]
    out[c]['govtotal_2026']=sum(x['voteCount'] for x in o); assert out[c]['govtotal_2026']==g[0]['voteTotal']
    out[c]['ballots_2026']=int(d['election']['ballotsCast'])
    out[c]['api_reg_total_2026']=int(d['election']['totalVoters'])
gs=[b for b in st['ballotItems'] if b['name'][0]['text']=='Governor and Lieutenant Governor'][0]
st26=dict(asOf_utc=asof,isOfficialResults=off,dem=[x['voteCount'] for x in gs['summaryResults']['ballotOptions'] if 'Hobbs' in x['name'][0]['text']][0],
          rep=[x['voteCount'] for x in gs['summaryResults']['ballotOptions'] if 'Biggs' in x['name'][0]['text']][0],govtotal=gs['voteTotal'],
          ballots_sum_localities=int(sum(le['ballotsCast'] for le in st['localityElections'])),
          candidates={x['name'][0]['text']:x['voteCount'] for x in gs['summaryResults']['ballotOptions']})

# ---- registration CSVs (first 'Active' county block, G.E. row)
def reg_csv(fn,ge_label):
    rows=list(csv.reader(open(fn,encoding='latin-1'))); hdr=None; cur=None; res={}
    for r in rows:
        if r and r[0]=='County': hdr=r; continue
        if hdr is None: continue
        if r and r[0].startswith('Totals'): cur='TOTAL'
        elif r and r[0] in COUNTIES: cur=r[0]
        if len(r)>3 and r[3].strip()==ge_label and cur:
            vals=[x for x in r[4:] if x.strip()]
            named={}
            hi=[h for h in hdr[4:] if h.strip()]
            for h,v in zip(hi,vals): named[h]=num(v)
            res[cur]=named
            if cur=='TOTAL': break
    return res
r22=reg_csv(R+'registration/State_Voter_Registration_2022_General.csv','G.E. 2022')
r26=reg_csv(R+'registration/State-Voter-Registration-November-2026.csv','GE 2026')
for c in COUNTIES:
    out[c]['regdem_2022']=r22[c]['Democratic']; out[c]['regact_2022']=r22[c]['Total']; out[c]['regrep_2022']=r22[c]['Republican']
    out[c]['regdem_2026']=r26[c]['Democratic']; out[c]['regact_2026']=r26[c]['Total']; out[c]['regrep_2026']=r26[c]['Republican']
# internal consistency: party columns sum to total
for rr in (r22,r26):
    for c,v in rr.items(): assert sum(x for k,x in v.items() if k!='Total')==v['Total'], (c,v)
F=['ballots_2022','dem_2022','rep_2022','govtotal_2022','canvass_reg_2022','regdem_2022','regrep_2022','regact_2022','ballots_2026','dem_2026','rep_2026','govtotal_2026','api_reg_total_2026','regdem_2026','regrep_2026','regact_2026']
with open(V+'passA_counties.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['county']+F)
    for c in COUNTIES: w.writerow([c]+[out[c][k] for k in F])
S=dict(sos2022=st22,sos2026=st26,reg2022_total=r22['TOTAL'],reg2026_total=r26['TOTAL'],
       sums={k:sum(out[c][k] for c in COUNTIES) for k in F})
json.dump(S,open(V+'passA_statewide.json','w'),indent=1)
print(json.dumps(S,indent=1)[:2500])

# ---- PASS A derived figures (pandas / float64; pass B uses exact fractions)
import pandas as pd, numpy as np
d=pd.read_csv(V+'passA_counties.csv',index_col='county')
for y,t in (('2022','22'),('2026','26')):
    d['S'+t]=d[f'dem_{y}']/d[f'ballots_{y}']*100.0
    d['P'+t]=d[f'regdem_{y}']/d[f'regact_{y}']*100.0
    d['G'+t]=d['S'+t]-d['P'+t]
d['dS']=d.S26-d.S22; d['dP']=d.P26-d.P22; d['dG']=d.G26-d.G22
d['residual']=np.where(d.regdem_2026<d.regdem_2022,d.dG-d.dP.abs(),np.nan)
d['implied_extra_votes']=d.dem_2026-d.S22/100.0*d.ballots_2026
d['gap_reg_scaled']=d.dem_2026-d.dem_2022*d.regdem_2026/d.regdem_2022
for k in ('regdem','dem','ballots'):
    d[f'{k}_chg']=d[f'{k}_2026']-d[f'{k}_2022']; d[f'{k}_chg_pct']=d[f'{k}_chg']/d[f'{k}_2022']*100.0
d.to_csv(V+'passA_counties.csv',float_format='%.17g')
t=d.sum(numeric_only=True)
sw=dict(S22=t.dem_2022/t.ballots_2022*100,S26=t.dem_2026/t.ballots_2026*100,P22=t.regdem_2022/t.regact_2022*100,P26=t.regdem_2026/t.regact_2026*100)
sw.update(dS=sw['S26']-sw['S22'],dP=sw['P26']-sw['P22']); sw['dG']=sw['dS']-sw['dP']
sw['implied_extra_sum']=float(d.implied_extra_votes.sum()); sw['implied_extra_pooled']=sw['dS']/100*t.ballots_2026
for k in ('regdem','dem','ballots'):
    sw[f'{k}_chg']=int(t[f'{k}_2026']-t[f'{k}_2022']); sw[f'{k}_chg_pct']=sw[f'{k}_chg']/t[f'{k}_2022']*100
S=json.load(open(V+'passA_statewide.json')); S['statewide_derived']={k:float(v) for k,v in sw.items()}
json.dump(S,open(V+'passA_statewide.json','w'),indent=1)
print(d[['S22','S26','P22','P26','dS','dP','dG','residual','implied_extra_votes']].round(2).to_string()); print(S['statewide_derived'])
