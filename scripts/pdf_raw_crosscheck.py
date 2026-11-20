"""THIRD independent checker for the county PDF. Shares no code with pass_a.py / pass_b.py / build_pdf.py.
1) Re-parses the raw SOS files itself:
   - 2022 canvass PDF via pdfplumber page.extract_text() (A used word x-positions, B used pdftotext -layout)
   - 2022/2026 registration REPORT PDFs via pdfplumber extract_text() (A used the CSVs, B used pdftotext)
   - 2026: Democratic governor votes from each county API file selected by party abbreviation DEM; ballots cast from the STATEWIDE
     API file's localityElections[].ballotsCast (A used each county file's election.ballotsCast; B used rendered pages)
2) Recomputes every PDF cell with exact rational arithmetic, rounds half-up to the displayed precision,
3) Extracts the PDF's own text with pdftotext and compares every cell. Logs each cell to verification/pdf_raw_crosscheck.csv."""
import pdfplumber, json, re, subprocess, csv, sys
from fractions import Fraction as Fr
from decimal import Decimal, ROUND_HALF_UP
RAW='/workspace/az-clean/raw/'; OUT='/workspace/az-clean/verification/'
PDF='/workspace/az-clean/pdf/Arizona_15_County_Democratic_Registration_and_Vote_Change.pdf'
CO=['Apache','Cochise','Coconino','Gila','Graham','Greenlee','La Paz','Maricopa','Mohave','Navajo','Pima','Pinal','Santa Cruz','Yavapai','Yuma']
toint=lambda s:int(s.replace(',',''))
raw={c:{} for c in CO}
# 2022 canvass
pages=[p.extract_text().split('\n') for p in pdfplumber.open(RAW+'2022/2022dec05_general_election_canvass_web.pdf').pages[:3]]
def nums16(line):
    v=re.findall(r'(?:^|\s)(\d[\d,]*)(?=\s|$)',line)[-16:]; v=[toint(x) for x in v]; assert len(v)==16 and sum(v[:15])==v[15],line; return v
tb=[l for l in pages[0] if l.startswith('Total Ballots Cast')][0]; tbv=nums16(tb)
gl=[l for p in pages for l in p if l.startswith('(DEM) Katie Hobbs')]; assert len(gl)==1; hv=nums16(gl[0])
for i,c in enumerate(CO): raw[c]['ballots_2022']=tbv[i]; raw[c]['dem_2022']=hv[i]
# registration report PDFs
def regpdf(fn,tag):
    L=pdfplumber.open(fn).pages[0].extract_text().split('\n')
    hdr=[l for l in L if l.startswith('County Precincts')][0].split()[3:]
    hdr=' '.join(hdr).replace('No Labels','No_Labels').split()
    ge=[l for l in L if re.search(r'\b'+re.escape(tag)+r'\b',l)]
    rows=[]
    for l in ge:
        if l.startswith('Percentages') or '.' in l.split(tag,1)[1]: continue
        v=[toint(x) for x in l.split(tag,1)[1].split()]; assert len(v)==len(hdr); rows.append(dict(zip(hdr,v)))
    assert len(rows)==16, len(rows)  # 15 counties + Totals, in alphabetical order as printed
    return {c:rows[i] for i,c in enumerate(CO)}, rows[15]
r22,t22=regpdf(RAW+'registration/State_Voter_Registration_2022_General.pdf','G.E. 2022')
r26,t26=regpdf(RAW+'registration/State-Voter-Registration-November-2026.pdf','GE 2026')
for c in CO:
    raw[c].update(regdem_2022=r22[c]['Democratic'],regact_2022=r22[c]['Total'],regdem_2026=r26[c]['Democratic'],regact_2026=r26[c]['Total'])
assert sum(raw[c]['regdem_2022'] for c in CO)==t22['Democratic'] and sum(raw[c]['regdem_2026'] for c in CO)==t26['Democratic']
# 2026 API
st=json.load(open(RAW+'2026/az2026_data.json'))
names={l['jurisdictionId'].lower():None for l in st['localityElections']}
for loc in st['jurisdiction']['childLocalities']:
    c=loc['name'][0]['text'].replace(' County',''); 
    le=[l for l in st['localityElections'] if l['jurisdictionId'].lower()==loc['id'].lower()][0]; raw[c]['ballots_2026']=int(le['ballotsCast'])
    d=json.load(open(RAW+f"2026/counties/{loc['shortName']}.json"))
    opts=[o for b in d['ballotItems'] if b['name'][0]['text'].startswith('Governor') for o in b['summaryResults']['ballotOptions'] if (o.get('party') or {}).get('abbreviation')=='DEM']
    assert len(opts)==1; raw[c]['dem_2026']=opts[0]['voteCount']
# expected display strings
def hu(x,nd): return Decimal(x.numerator)/Decimal(x.denominator) if False else None
def rnd(fr,nd):
    q=(Decimal(fr.numerator)/Decimal(fr.denominator)) if isinstance(fr,Fr) else Decimal(fr)
    # exact: scale by 10^nd as a Fraction, round half up away from zero
    s=fr*10**nd; sign=-1 if s<0 else 1; a=abs(s); n=int(a); n+= 1 if a-n>=Fr(1,2) else 0; return sign*n
def fmt_pct(fr,nd=1,sign=False):
    n=rnd(fr,nd); s=f'{abs(n)/10**nd:.{nd}f}%'; return ('-' if n<0 else ('+' if sign and n>0 else ''))+s
def fmt_pts(fr):
    n=rnd(fr,2); return ('-' if n<0 else ('+' if n>0 else ''))+f'{abs(n)/100:.2f}'
def fmt_n(x,sign=False): return ('-' if x<0 else ('+' if sign and x>0 else ''))+f'{abs(x):,}'
def cells(x):
    P26=Fr(100*x['regdem_2026'],x['regact_2026']); P22=Fr(100*x['regdem_2022'],x['regact_2022'])
    S22=Fr(100*x['dem_2022'],x['ballots_2022']); S26=Fr(100*x['dem_2026'],x['ballots_2026'])
    ch=lambda k:x[k+'_2026']-x[k+'_2022']; cp=lambda k:Fr(100*ch(k),x[k+'_2022'])
    p1=[fmt_pct(P26),fmt_n(x['regdem_2022']),fmt_n(x['regdem_2026']),fmt_n(ch('regdem'),True),fmt_pct(cp('regdem'),1,True),fmt_n(x['dem_2022']),fmt_n(x['dem_2026']),fmt_n(ch('dem'),True),fmt_pct(cp('dem'),1,True),
        fmt_n(x['ballots_2022']),fmt_n(x['ballots_2026']),fmt_n(ch('ballots'),True),fmt_pct(cp('ballots'),1,True)]
    p2=[fmt_pct(S22),fmt_pct(S26),fmt_pts(S26-S22),fmt_pct(P22),fmt_n(x['regact_2022']),fmt_pct(P26),fmt_n(x['regact_2026']),fmt_pts(P26-P22)]
    return p1,p2,P26
C1=['Dem Reg Share 2026 %','Dem Reg 2022','Dem Reg 2026','Reg Change #','Reg Change %','Dem Gov Votes 2022','Dem Gov Votes 2026*','Vote Change #','Vote Change %','Total Ballots 2022','Total Ballots 2026*','Ballot Change #','Ballot Change %']
C2=['Dem Share of Ballots 2022 %','Dem Share of Ballots 2026* %','Change (pts)','Dem Share of Registration 2022 %','Total Active Registered 2022','Dem Share of Registration 2026 %','Total Active Registered 2026','Registration Share Change (pts)']
tot={k:sum(raw[c][k] for c in CO) for k in raw['Apache']}
exp={c:cells(raw[c]) for c in CO}; exp['Statewide total']=cells(tot)
order=sorted(CO,key=lambda c:-exp[c][2])+['Statewide total']
# same cells rebuilt from pass A and pass B parsed inputs (so the PDF must agree with raw checker AND both passes)
K=['ballots_2022','dem_2022','regdem_2022','regact_2022','ballots_2026','dem_2026','regdem_2026','regact_2026']
def load(fn):
    rr=list(csv.DictReader(open(OUT+fn))); return {r['county']:{k:int(float(r[k])) for k in K} for r in rr}
PA,PB=load('passA_counties.csv'),load('passB_counties.csv')
expA={c:cells(PA[c]) for c in CO}; expA['Statewide total']=cells({k:sum(PA[c][k] for c in CO) for k in K})
expB={c:cells(PB[c]) for c in CO}; expB['Statewide total']=cells({k:sum(PB[c][k] for c in CO) for k in K})
# PDF text
def pg(n): return subprocess.run(['pdftotext','-layout','-f',str(n),'-l',str(n),PDF,'-'],capture_output=True,text=True,check=True).stdout.split('\n')
def table_rows(lines,ncol):
    out=[]
    for l in lines:
        m=re.match(r'^\s*(Statewide total|[A-Z][a-z]+(?: [A-Z][a-z]+)?)\s{2,}(.*)$',l)
        if m and m.group(1) in order:
            v=m.group(2).split(); 
            if len(v)==ncol: out.append((m.group(1),v))
    return out
t1=table_rows(pg(1),13); t2=table_rows(pg(2),8)
log=[]; bad=[]
def cmp(page,rows,ci,cols):
    assert [r[0] for r in rows]==order, ('ROW ORDER',page,[r[0] for r in rows])
    for name,v in rows:
        e=exp[name][ci]; ea=expA[name][ci]; eb=expB[name][ci]
        for k,(col,got,want,wa,wb) in enumerate(zip(cols,v,e,ea,eb)):
            ok=got==want==wa==wb; log.append([page,name,col,want,wa,wb,got,'MATCH' if ok else 'MISMATCH'])
            if not ok: bad.append((page,name,col,want,got))
cmp(1,t1,0,C1); cmp(2,t2,1,C2)
# every page carries the unofficial marker
allp=[pg(i) for i in (1,2,3)]
for i,p in enumerate(allp,1):
    t='\n'.join(p); ok=('2026 UNOFFICIAL' in t) and ('*2026 figures UNOFFICIAL' in t)
    log.append([i,'(page)','2026 UNOFFICIAL banner + footer','present','','','present' if ok else 'MISSING','MATCH' if ok else 'MISMATCH'])
    if not ok: bad.append((i,'unofficial marker'))
with open(OUT+'pdf_raw_crosscheck.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['page','county','column','raw_checker_recompute','passA_recompute','passB_recompute','pdf_text','result']); w.writerows(log)
res=dict(cells_checked=sum(1 for r in log if r[1]!='(page)'),cells_matched=sum(1 for r in log if r[1]!='(page)' and r[7]=='MATCH'),page_marker_checks=sum(1 for r in log if r[1]=='(page)'),
         row_order='2026 Dem registration share descending, verified',mismatches=bad,CLEAN=not bad)
json.dump(res,open(OUT+'pdf_raw_crosscheck_report.json','w'),indent=1,default=str); print(json.dumps(res,indent=1,default=str))
sys.exit(0 if not bad else 1)
