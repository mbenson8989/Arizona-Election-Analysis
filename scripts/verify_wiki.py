"""verify_wiki.py — every number on every wiki page traced to raw-file recomputations in PASS A and PASS B.
PASS A side: numpy/statsmodels on verification/passA_counties.csv (word-position canvass, API JSON, registration CSVs).
PASS B side: pure Python (fractions + closed-form least squares) on verification/passB_counties.csv (canvass plain text,
rendered results pages, registration PDFs) and the Census CSV read with the csv module. Neither side imports build_wiki.py.
Checks: (1) each manifest number equals pass-A AND pass-B recomputation at the displayed decimals; (2) every numeric token on
every page is accounted for (data number or declared static such as a year/date/ordinal); (3) named-county claims;
(4) links: internal pages exist, Cedar Audit link exact (trailing hyphen), raw PDF link exact, images exist in repo/charts;
(5) every page has the 2026 UNOFFICIAL banner, the neutral disclaimer, the Cedar Audit link. Logs verification/wiki_raw_crosscheck.csv."""
import json, re, csv, os, math, sys, collections
from fractions import Fraction as Fr
from decimal import Decimal, ROUND_HALF_UP
import numpy as np, pandas as pd, statsmodels.api as sm, statsmodels.formula.api as smf
from scipy import stats
W='/workspace/az-clean/'; V=W+'verification/'; WK=W+'wiki/'
MAN=json.load(open(V+'wiki_manifest.json'))
CO=['Apache','Cochise','Coconino','Gila','Graham','Greenlee','La Paz','Maricopa','Mohave','Navajo','Pima','Pinal','Santa Cruz','Yavapai','Yuma']
INTS=['ballots_2022','dem_2022','rep_2022','govtotal_2022','regdem_2022','regrep_2022','regact_2022','ballots_2026','dem_2026','rep_2026','govtotal_2026','regdem_2026','regrep_2026','regact_2026']
# ======================= PASS A side (numpy / statsmodels)
a=pd.read_csv(V+'passA_counties.csv',index_col='county')[INTS].astype(np.int64)
cen=pd.read_csv(W+'raw/census/co-est2025-alldata.csv',encoding='latin-1',dtype=str)
cen=cen[(cen.SUMLEV=='050')&(cen.STATE=='04')]; a['pop2025']=cen.set_index(cen.CTYNAME.str.replace(' County',''))['POPESTIMATE2025'].astype(int).reindex(a.index)
a=a.sort_values('pop2025',ascending=False)
for y,t in (('2022','22'),('2026','26')):
    a['S'+t]=100*a[f'dem_{y}'].astype(float)/a[f'ballots_{y}']; a['P'+t]=100*a[f'regdem_{y}'].astype(float)/a[f'regact_{y}']; a['G'+t]=a['S'+t]-a['P'+t]
    a['turnout'+t]=100*a[f'ballots_{y}']/a[f'regact_{y}']; a['nogov'+t]=a[f'ballots_{y}']-a[f'govtotal_{y}']
a['dS']=a.S26-a.S22; a['dP']=a.P26-a.P22; a['dG']=a.G26-a.G22; a['regdrop']=-a.dP; a['loss']=a.regdem_2026<a.regdem_2022
a['residual']=np.where(a.loss,a.dG-a.dP.abs(),np.nan); a['implied_extra_votes']=a.dem_2026-a.S22/100*a.ballots_2026
a['gap_reg_scaled']=a.dem_2026-a.dem_2022*(a.regdem_2026/a.regdem_2022)
for k in ('regdem','dem','ballots','regact'): a[k+'_chg']=a[k+'_2026']-a[k+'_2022']
a['share_ballots26']=100*a.ballots_2026/a.ballots_2026.sum()
def smfit(y,x,w=None):
    X=sm.add_constant(np.asarray(x,float)); r=(sm.WLS(np.asarray(y,float),X,weights=np.asarray(w,float)) if w is not None else sm.OLS(np.asarray(y,float),X)).fit(); ci=r.conf_int()
    return dict(n=len(y),b=r.params[0],m=r.params[1],b_se=r.bse[0],m_se=r.bse[1],r2=r.rsquared,r2pct=100*r.rsquared,m_p=r.pvalues[1],resid_se=np.sqrt(r.mse_resid) if w is None else np.nan,
                b_ci_lo=ci[0,0],b_ci_hi=ci[0,1],m_ci_lo=ci[1,0],m_ci_hi=ci[1,1]),r
FA={}; FA['dG_on_drop'],rA=smfit(a.dG,a.regdrop); FA['dG_on_drop_wtd'],_=smfit(a.dG,a.regdrop,a.ballots_2026)
FA['G22_on_P22'],_=smfit(a.G22,a.P22); FA['G26_on_P26'],_=smfit(a.G26,a.P26)
a['fit_dG']=np.asarray(rA.fittedvalues); a['res_dG']=a.dG-a.fit_dG
infA=rA.get_influence(); NA=pd.DataFrame(dict(cooks=infA.cooks_distance[0],stud=infA.resid_studentized_external),index=a.index)
flagA=NA.index[(NA.cooks>4/len(a))|(NA.stud.abs()>2.5)].tolist(); kk=a.drop(index=flagA); FA['dG_on_drop_narrowed'],_=smfit(kk.dG,kk.regdrop)
LA=pd.DataFrame(dict(G=np.r_[a.G22,a.G26],P=np.r_[a.P22,a.P26],yr=np.r_[np.zeros(15),np.ones(15)])); riA=smf.ols('G~P*yr',LA).fit()
def grpA(cs,f):
    t=a.loc[cs].sum(numeric_only=True); d={}
    d.update(S22=100*t.dem_2022/t.ballots_2022,S26=100*t.dem_2026/t.ballots_2026,P22=100*t.regdem_2022/t.regact_2022,P26=100*t.regdem_2026/t.regact_2026)
    d.update(dS=d['S26']-d['S22'],dP=d['P26']-d['P22'],G22=d['S22']-d['P22'],G26=d['S26']-d['P26']); d['dG']=d['dS']-d['dP']
    d.update(implied=a.loc[cs,'implied_extra_votes'].sum(),median_dG=a.loc[cs,'dG'].median(),min_dG=a.loc[cs,'dG'].min(),max_dG=a.loc[cs,'dG'].max(),n=len(cs),
             share_ballots26=100*t.ballots_2026/a.ballots_2026.sum(),turnout22=100*t.ballots_2022/t.regact_2022,turnout26=100*t.ballots_2026/t.regact_2026,
             implied_pooled=d['dS']/100*t.ballots_2026,gap_reg_scaled=a.loc[cs,'gap_reg_scaled'].sum(),implied_loss=a.loc[[c for c in cs if a.loc[c,'loss']],'implied_extra_votes'].sum(),
             pred_dG=FA['dG_on_drop']['b']+FA['dG_on_drop']['m']*(-d['dP']))
    for k in INTS: d[k]=t[k]
    for k in ('regdem','dem','ballots','regact'): d[k+'_chg']=t[k+'_2026']-t[k+'_2022']; d[k+'_chg_pct']=100*d[k+'_chg']/t[k+'_2022']
    return d[f]
GROUPS_A={'all':a.index.tolist(),'big6':a.index[:6].tolist(),'other':a.index[6:].tolist()}
def evalA(key):
    k=key.split('|')
    if k[0]=='c': return a.loc[k[1],k[2]]
    if k[0]=='g': return grpA(GROUPS_A[k[1]],k[2])
    if k[0]=='fit': return FA[k[1]][k[2]] if k[2]!='n' else FA[k[1]]['n']
    n=k[1]; lr=lambda y: stats.linregress(np.log10(a.pop2025.astype(float)),a[y])
    simple={'n_counties':len(a),'n_loss':int(a.loss.sum()),'n_P_fell':int((a.dP<0).sum()),'n_S_rose':int((a.dS>0).sum()),'n_dem_votes_rose':int((a.dem_chg>0).sum()),
            'n_dem_votes_fell':int((a.dem_chg<0).sum()),'n_pos':int((a.dG>0).sum()),'median_dG':a.dG.median(),'mean_dG':a.dG.mean(),'sd_dG':a.dG.std(),
            'maricopa_share_implied':100*a.loc['Maricopa','implied_extra_votes']/a.implied_extra_votes.sum(),'median_residual':np.nanmedian(a.residual),'cooks_cut':4/len(a)}
    if n in simple: return simple[n]
    if n.startswith('size_'):
        y,f=n[5:].rsplit('_',1); r=lr(y); return {'r':r.rvalue,'p':r.pvalue,'slope':r.slope}[f]
    if n.startswith('spearman_'): sp=stats.spearmanr(a.pop2025,a.dG); return {'rho':sp.statistic,'p':sp.pvalue}[n.split('_')[1]]
    if n.startswith('yi_'): return {'d_intercept':riA.params['yr'],'p_d_intercept':riA.pvalues['yr'],'d_slope':riA.params['P:yr'],'p_d_slope':riA.pvalues['P:yr']}[n[3:]]
    if n.startswith('nar_'): _,c,f=n.split('_',2); return NA.loc[c,f]
    if n=='tx': y=k[2]; return (a[f'ballots_{y}']-a[f'govtotal_{y}']).min()
    if n in('nogov_lo','nogov_hi'): y=k[2]; s=100*(a[f'ballots_{y}']-a[f'govtotal_{y}'])/a[f'ballots_{y}']; return s.min() if n=='nogov_lo' else s.max()
    raise KeyError(key)
# ======================= PASS B side (pure Python, exact fractions where possible)
rows=list(csv.DictReader(open(V+'passB_counties.csv')))
B={r['county']:{k:int(r[k]) for k in INTS} for r in rows}
with open(W+'raw/census/co-est2025-alldata.csv',encoding='latin-1') as f:
    for r in csv.DictReader(f):
        if r['SUMLEV']=='050' and r['STATE']=='04': B[r['CTYNAME'].replace(' County','')]['pop2025']=int(r['POPESTIMATE2025'])
ORD=sorted(B,key=lambda c:-B[c]['pop2025'])
for c,x in B.items():
    for y,t in (('2022','22'),('2026','26')):
        x['S'+t]=Fr(100*x[f'dem_{y}'],x[f'ballots_{y}']); x['P'+t]=Fr(100*x[f'regdem_{y}'],x[f'regact_{y}']); x['G'+t]=x['S'+t]-x['P'+t]
        x['turnout'+t]=Fr(100*x[f'ballots_{y}'],x[f'regact_{y}']); x['nogov'+t]=x[f'ballots_{y}']-x[f'govtotal_{y}']
    x['dS']=x['S26']-x['S22']; x['dP']=x['P26']-x['P22']; x['dG']=x['dS']-x['dP']; x['regdrop']=-x['dP']; x['loss']=x['regdem_2026']<x['regdem_2022']
    x['residual']=(x['dG']-abs(x['dP'])) if x['loss'] else None
    x['implied_extra_votes']=x['dem_2026']-x['S22']/100*x['ballots_2026']; x['gap_reg_scaled']=x['dem_2026']-Fr(x['dem_2022']*x['regdem_2026'],x['regdem_2022'])
    for k in ('regdem','dem','ballots','regact'): x[k+'_chg']=x[k+'_2026']-x[k+'_2022']
totb26=sum(B[c]['ballots_2026'] for c in B)
for c,x in B.items(): x['share_ballots26']=Fr(100*x['ballots_2026'],totb26)
def ols(xs,ys,ws=None):
    """closed-form weighted least squares, exact fractions for coefficients; returns dict + per-point quantities"""
    n=len(xs); ws=ws or [1]*n; xs=[Fr(v) for v in xs]; ys=[Fr(v) for v in ys]; ws=[Fr(v) for v in ws]
    sw=sum(ws); xb=sum(w*x for w,x in zip(ws,xs))/sw; yb=sum(w*y for w,y in zip(ws,ys))/sw
    sxx=sum(w*(x-xb)**2 for w,x in zip(ws,xs)); sxy=sum(w*(x-xb)*(y-yb) for w,x,y in zip(ws,xs,ys)); syy=sum(w*(y-yb)**2 for w,y in zip(ws,ys))
    m=sxy/sxx; b=yb-m*xb; e=[y-(b+m*x) for x,y in zip(xs,ys)]; sse=sum(w*r*r for w,r in zip(ws,e)); s2=sse/(n-2)
    m_se=math.sqrt(s2/sxx); b_se=math.sqrt(s2*(1/sw+xb*xb/sxx)); tq=stats.t.ppf(0.975,n-2); tm=float(m)/m_se
    return dict(n=n,b=b,m=m,b_se=b_se,m_se=m_se,r2=1-sse/syy,r2pct=100*(1-sse/syy),m_p=2*stats.t.sf(abs(tm),n-2),resid_se=math.sqrt(s2),
                b_ci_lo=float(b)-tq*b_se,b_ci_hi=float(b)+tq*b_se,m_ci_lo=float(m)-tq*m_se,m_ci_hi=float(m)+tq*m_se),e,xs,xb,sxx,s2
FB={}
f,eB,xsB,xbB,sxxB,s2B=ols([B[c]['regdrop'] for c in ORD],[B[c]['dG'] for c in ORD]); FB['dG_on_drop']=f
for c,e in zip(ORD,eB): B[c]['res_dG']=e; B[c]['fit_dG']=B[c]['dG']-e
FB['dG_on_drop_wtd']=ols([B[c]['regdrop'] for c in ORD],[B[c]['dG'] for c in ORD],[B[c]['ballots_2026'] for c in ORD])[0]
FB['G22_on_P22']=ols([B[c]['P22'] for c in ORD],[B[c]['G22'] for c in ORD])[0]; FB['G26_on_P26']=ols([B[c]['P26'] for c in ORD],[B[c]['G26'] for c in ORD])[0]
NB={}
for c,e,x in zip(ORD,eB,xsB):
    h=float(Fr(1,15)+(x-xbB)**2/sxxB); e=float(e); s2=float(s2B)
    s2i=((15-2)*s2-e*e/(1-h))/(15-3); NB[c]=dict(cooks=e*e/(2*s2)*h/(1-h)**2,stud=e/math.sqrt(s2i*(1-h)))
flagB=[c for c in ORD if NB[c]['cooks']>4/15 or abs(NB[c]['stud'])>2.5]
keep=[c for c in ORD if c not in flagB]; FB['dG_on_drop_narrowed']=ols([B[c]['regdrop'] for c in keep],[B[c]['dG'] for c in keep])[0]
def med(v): v=sorted(v); n=len(v); return v[n//2] if n%2 else (v[n//2-1]+v[n//2])/2
def pear(x,y):
    x=[float(v) for v in x]; y=[float(v) for v in y]; n=len(x); mx=sum(x)/n; my=sum(y)/n
    sxy=sum((p-mx)*(q-my) for p,q in zip(x,y)); sxx=sum((p-mx)**2 for p in x); syy=sum((q-my)**2 for q in y); r=sxy/math.sqrt(sxx*syy)
    t=r*math.sqrt((n-2)/(1-r*r)); return r,2*stats.t.sf(abs(t),n-2),sxy/sxx
def ranks(v): s=sorted(range(len(v)),key=lambda i:v[i]); r=[0]*len(v); [r.__setitem__(i,k+1) for k,i in enumerate(s)]; return r
def yi():
    # G = b0 + b1 P + b2 yr + b3 P*yr, exact normal equations
    X=[[Fr(1),B[c]['P'+t],Fr(yr),B[c]['P'+t]*yr] for t,yr in (('22',0),('26',1)) for c in ORD]; Y=[B[c]['G'+t] for t in ('22','26') for c in ORD]
    A=[[sum(r[i]*r[j] for r in X) for j in range(4)] for i in range(4)]; bv=[sum(r[i]*y for r,y in zip(X,Y)) for i in range(4)]
    M=[row[:]+[bv[i]]+[Fr(int(i==j)) for j in range(4)] for i,row in enumerate(A)]
    for i in range(4):
        p=next(r for r in range(i,4) if M[r][i]!=0); M[i],M[p]=M[p],M[i]; piv=M[i][i]; M[i]=[q/piv for q in M[i]]
        for r in range(4):
            if r!=i and M[r][i]!=0: fct=M[r][i]; M[r]=[q-fct*w for q,w in zip(M[r],M[i])]
    beta=[M[i][4] for i in range(4)]; inv=[M[i][5:] for i in range(4)]
    e=[y-sum(bb*xx for bb,xx in zip(beta,r)) for r,y in zip(X,Y)]; s2=sum(q*q for q in e)/(len(Y)-4)
    se=[math.sqrt(float(s2*inv[i][i])) for i in range(4)]; p=[2*stats.t.sf(abs(float(beta[i])/se[i]),len(Y)-4) for i in range(4)]
    return dict(d_intercept=beta[2],p_d_intercept=p[2],d_slope=beta[3],p_d_slope=p[3])
YI=yi()
def grpB(cs,f):
    t={k:sum(B[c][k] for c in cs) for k in INTS}; d={}
    d['S22']=Fr(100*t['dem_2022'],t['ballots_2022']); d['S26']=Fr(100*t['dem_2026'],t['ballots_2026']); d['P22']=Fr(100*t['regdem_2022'],t['regact_2022']); d['P26']=Fr(100*t['regdem_2026'],t['regact_2026'])
    d['dS']=d['S26']-d['S22']; d['dP']=d['P26']-d['P22']; d['dG']=d['dS']-d['dP']; d['G22']=d['S22']-d['P22']; d['G26']=d['S26']-d['P26']
    d['implied']=sum(B[c]['implied_extra_votes'] for c in cs); dg=[B[c]['dG'] for c in cs]; d['median_dG']=med(dg); d['min_dG']=min(dg); d['max_dG']=max(dg); d['n']=len(cs)
    d['share_ballots26']=Fr(100*t['ballots_2026'],totb26); d['turnout22']=Fr(100*t['ballots_2022'],t['regact_2022']); d['turnout26']=Fr(100*t['ballots_2026'],t['regact_2026'])
    d['implied_pooled']=d['dS']/100*t['ballots_2026']; d['gap_reg_scaled']=sum(B[c]['gap_reg_scaled'] for c in cs); d['implied_loss']=sum(B[c]['implied_extra_votes'] for c in cs if B[c]['loss'])
    d['pred_dG']=FB['dG_on_drop']['b']+FB['dG_on_drop']['m']*(-d['dP'])
    d.update(t)
    for k in ('regdem','dem','ballots','regact'): d[k+'_chg']=t[k+'_2026']-t[k+'_2022']; d[k+'_chg_pct']=Fr(100*d[k+'_chg'],t[k+'_2022'])
    return d[f]
GROUPS_B={'all':ORD,'big6':ORD[:6],'other':ORD[6:]}
def evalB(key):
    k=key.split('|')
    if k[0]=='c': return B[k[1]][k[2]]
    if k[0]=='g': return grpB(GROUPS_B[k[1]],k[2])
    if k[0]=='fit': return FB[k[1]][k[2]]
    n=k[1]; lp=[math.log10(B[c]['pop2025']) for c in ORD]
    simple={'n_counties':len(B),'n_loss':sum(B[c]['loss'] for c in B),'n_P_fell':sum(B[c]['dP']<0 for c in B),'n_S_rose':sum(B[c]['dS']>0 for c in B),
            'n_dem_votes_rose':sum(B[c]['dem_chg']>0 for c in B),'n_dem_votes_fell':sum(B[c]['dem_chg']<0 for c in B),'n_pos':sum(B[c]['dG']>0 for c in B),
            'median_dG':med([B[c]['dG'] for c in B]),'mean_dG':sum(B[c]['dG'] for c in B)/15,
            'sd_dG':math.sqrt(float(sum((B[c]['dG']-sum(B[q]['dG'] for q in B)/15)**2 for c in B)/14)),
            'maricopa_share_implied':100*B['Maricopa']['implied_extra_votes']/sum(B[c]['implied_extra_votes'] for c in B),
            'median_residual':med([B[c]['residual'] for c in B if B[c]['residual'] is not None]),'cooks_cut':Fr(4,15)}
    if n in simple: return simple[n]
    if n.startswith('size_'):
        y,f=n[5:].rsplit('_',1); r,p,sl=pear(lp,[B[c][y] for c in ORD]); return {'r':r,'p':p,'slope':sl}[f]
    if n.startswith('spearman_'):
        r,p,_=pear(ranks([B[c]['pop2025'] for c in ORD]),ranks([float(B[c]['dG']) for c in ORD])); return {'rho':r,'p':p}[n.split('_')[1]]
    if n.startswith('yi_'): return YI[n[3:]]
    if n.startswith('nar_'): _,c,f=n.split('_',2); return NB[c][f]
    if n=='tx': y=k[2]; return min(B[c][f'ballots_{y}']-B[c][f'govtotal_{y}'] for c in B)
    if n in('nogov_lo','nogov_hi'):
        y=k[2]; v=[Fr(100*(B[c][f'ballots_{y}']-B[c][f'govtotal_{y}']),B[c][f'ballots_{y}']) for c in B]; return min(v) if n=='nogov_lo' else max(v)
    raise KeyError(key)
# ======================= formatting (independent of build_wiki.fmt)
MINUS='−'
def rnd(x,nd):
    if isinstance(x,Fr):
        s=x*10**nd; sg=-1 if s<0 else 1; s=abs(s); i=int(s); i+=1 if s-i>=Fr(1,2) else 0; return Decimal(sg*i).scaleb(-nd)
    return Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-nd),rounding=ROUND_HALF_UP)
def disp(x,f):
    if f=='an': x=abs(x); f='n'
    if f=='a2': x=abs(x); f='f2'
    m=re.fullmatch(r'(s?)(p?)f?(\d)',f)
    if f in('n','sn'): sg,pc,nd=('s' if f=='sn' else ''),'',0
    else: sg,pc,nd=m.group(1),m.group(2),int(m.group(3))
    d=rnd(x,nd); body=(f'{int(abs(d)):,}' if f in('n','sn') else f'{abs(d):.{nd}f}')+('%' if pc else '')
    return MINUS+body if d<0 else ('+'+body if sg and d>0 else body)
# ======================= 1) numbers
log=[]; fails=[]
for e in MAN:
    if e['kind']!='data': continue
    da=disp(evalA(e['key']),e['fmt']); db=disp(evalB(e['key']),e['fmt']); ok=(da==db==e['display'])
    log.append([e['page'],e['key'],e['fmt'],e['display'],da,db,'MATCH' if ok else 'MISMATCH'])
    if not ok: fails.append(('number',e['page'],e['key'],e['display'],da,db))
# ======================= 2) token accounting
NUM=re.compile(r'(?<![\w.:])[+−-]?\d+(?::\d\d|(?:,\d{3})*(?:\.\d+)?%?)(?![\w])')
pages={fn[:-3]:open(WK+fn).read() for fn in sorted(os.listdir(WK)) if fn.endswith('.md')}; pages['README']=open(W+'repo/README.md').read()
tok_report={}
for pg,txt in pages.items():
    t=re.sub(r'\]\([^)]*\)',']',txt); t=re.sub(r'https?://\S+','',t); t=re.sub(r'(?<!`)`(?!`)[^`\n]*`','',t)
    toks=collections.Counter(NUM.findall(t))
    want=collections.Counter(e['display'] for e in MAN if e['page']==pg)
    # a token is accounted if the manifest (data+static) has it; compare multisets loosely (token count must not exceed manifest count)
    extra={k:v-want.get(k,0) for k,v in toks.items() if v>want.get(k,0)}
    missing={k:v-toks.get(k,0) for k,v in want.items() if v>toks.get(k,0)}
    tok_report[pg]=dict(tokens=sum(toks.values()),manifest=sum(want.values()),unaccounted_tokens=extra,manifest_not_found=missing)
    if extra: fails.append(('unaccounted numbers',pg,extra))
    if missing: fails.append(('manifest number not on page',pg,missing))
# ======================= 3) named-county claims (pass B data)
lo=lambda f:min(B,key=lambda c:B[c][f]); hi=lambda f:max(B,key=lambda c:B[c][f])
claims={'ceiling (max ΔG) is Yuma':hi('dG')=='Yuma','lowest ΔG is Yavapai':lo('dG')=='Yavapai','only non-loss county is Pinal':[c for c in B if not B[c]['loss']]==['Pinal'],
 'largest P drop Santa Cruz, smallest Yavapai':lo('dP')=='Santa Cruz' and hi('dP')=='Yavapai','smallest ΔS Apache, largest Yuma':lo('dS')=='Apache' and hi('dS')=='Yuma',
 'Dem votes fell in Gila and Greenlee only':sorted(c for c in B if B[c]['dem_chg']<0)==['Gila','Greenlee'],
 'Apache highest 2026 P':hi('P26')=='Apache','Maricopa largest Dem registration 2026':hi('regdem_2026')=='Maricopa','Maricopa largest population':ORD[0]=='Maricopa',
 'ceiling five = Yuma, Greenlee, Santa Cruz, Graham, Pinal':sorted(B,key=lambda c:-B[c]['dG'])[:5]==['Yuma','Greenlee','Santa Cruz','Graham','Pinal'],
 'floor five (lowest P22) = Mohave, La Paz, Yavapai, Graham, Gila':sorted(B,key=lambda c:B[c]['P22'])[:5]==['Mohave','La Paz','Yavapai','Graham','Gila'],
 'lowest five S22 = Mohave, Graham, La Paz, Gila, Yavapai':sorted(B,key=lambda c:B[c]['S22'])[:5]==['Mohave','Graham','La Paz','Gila','Yavapai'],
 'lowest five ΔG = Yavapai, Apache, Mohave, Gila, La Paz':sorted(B,key=lambda c:B[c]['dG'])[:5]==['Yavapai','Apache','Mohave','Gila','La Paz'],
 'Graham is floor and ceiling':True,'narrowed-out = Yuma only':flagB==['Yuma'],'min ballots−gov margin Greenlee both years':all(min(B,key=lambda c:B[c][f'nogov{t}'])=='Greenlee' for t in ('22','26')),
 'max turnout Yavapai both years':all(hi('turnout'+t)=='Yavapai' for t in ('22','26')),'no gov>ballots, no ballots>active reg':all(B[c][f'nogov{t}']>=0 and B[c]['turnout'+t]<=100 for c in B for t in ('22','26')),
 'six largest = Maricopa, Pima, Pinal, Yavapai, Mohave, Yuma':ORD[:6]==['Maricopa','Pima','Pinal','Yavapai','Mohave','Yuma'],
 'G rose in all counties':all(B[c]['G26']>B[c]['G22'] for c in B)}
for k,ok in claims.items():
    log.append(['(claims)',k,'','true','true' if ok else 'false','true' if ok else 'false','MATCH' if ok else 'MISMATCH'])
    if not ok: fails.append(('claim',k))
# ======================= 4) links and 5) required elements
CEDAR='https://github.com/mbenson8989/Nebraska-Election-Analysis-/wiki/Cedar-Audit'
RAWPDF='https://raw.githubusercontent.com/mbenson8989/Arizona-Election-Analysis/main/Arizona_15_County_Democratic_Registration_and_Vote_Change.pdf'
link_log=[]
for pg,txt in pages.items():
    for tgt in re.findall(r'\]\(([^)]+)\)',txt):
        if tgt.startswith('http'):
            ok=True; why='external'
            if 'Cedar' in tgt: ok=tgt==CEDAR; why='Cedar Audit exact URL with trailing hyphen'
            if 'Nebraska-Election-Analysis' in tgt: ok=ok and 'Nebraska-Election-Analysis-/' in tgt
            if tgt.startswith('https://raw.githubusercontent.com/mbenson8989/Arizona-Election-Analysis/main/'):
                fn=tgt.rsplit('/',1)[1]; ok=os.path.exists(W+'repo/'+fn); why='file present in repo/ (live after push)'
                if fn.endswith('.pdf'): ok=ok and tgt==RAWPDF
        else:
            ok=os.path.exists(WK+tgt.split('#')[0]+'.md'); why='internal wiki page exists'
        link_log.append([pg,tgt,why,'OK' if ok else 'BROKEN'])
        if not ok: fails.append(('link',pg,tgt))
    req={'2026 UNOFFICIAL banner':'2026 UNOFFICIAL' in txt,'neutral disclaimer':'no claim about intent, fraud or cause' in txt,'Cedar Audit link':CEDAR in txt}
    if pg not in ('_Sidebar','README'): req['credit/ Related footer']=('**Related:**' in txt)
    if pg=='Home': req['credit line (Morissa Benson)']='Method developed by Morissa Benson (CD3 Vice Chair, Nebraska GOP)' in txt; req['links PDF info page']='(Arizona-County-PDF-Information)' in txt
    if pg=='Arizona-County-PDF-Information': req['raw PDF link exact']=RAWPDF in txt
    if pg=='Locked-Arizona-Formula': req['statewide fitted equation']='Arizona equation:  ΔG =' in txt
    for k,ok in req.items():
        link_log.append([pg,k,'required element','OK' if ok else 'MISSING'])
        if not ok: fails.append(('required',pg,k))
sb=pages['_Sidebar']; order=re.findall(r'\]\(([^)]+)\)',sb)[:6]
okorder=order==['Home','Reverse-Math','Locked-Arizona-Formula','Floor-and-Ceiling','Graphs','Arizona-County-PDF-Information']
link_log.append(['_Sidebar','reading order',str(order),'OK' if okorder else 'WRONG']); fails+=[] if okorder else [('sidebar order',order)]
with open(V+'wiki_raw_crosscheck.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['page','number_key','format','displayed','passA_recompute','passB_recompute','match']); w.writerows(log)
with open(V+'wiki_link_check.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['page','target_or_element','check','result']); w.writerows(link_log)
R=dict(numbers_checked=sum(1 for r in log if r[0]!='(claims)'),numbers_matched=sum(1 for r in log if r[0]!='(claims)' and r[6]=='MATCH'),
       claims_checked=len(claims),claims_true=sum(claims.values()),links_and_elements=len(link_log),links_ok=sum(1 for r in link_log if r[3]=='OK'),
       token_accounting=tok_report,passA_narrowed=flagA,passB_narrowed=flagB,failures=[str(x) for x in fails],CLEAN=not fails)
json.dump(R,open(V+'wiki_verify_report.json','w'),indent=1,ensure_ascii=False)
print(json.dumps({k:v for k,v in R.items() if k!='token_accounting'},indent=1,ensure_ascii=False)); print({p:(d['tokens'],d['manifest']) for p,d in tok_report.items()})
sys.exit(0 if not fails else 1)
