"""Build the Arizona wiki pages (local only). Every data number is inserted through v(key, fmt), which computes it from the
PASS-A outputs and records (page, key, fmt, display) in verification/wiki_manifest.json. Non-data numbers (years, dates, list
ordinals, template line numbers) go through s(text, reason) and are recorded as static. verify_wiki.py recomputes every
data number independently from pass A and from pass B and checks every numeric token on every page is accounted for."""
import pandas as pd, numpy as np, json, re
from decimal import Decimal, ROUND_HALF_UP
W='/workspace/az-clean/'; V=W+'verification/'; OUTD=W+'wiki/'
o=pd.read_pickle(W+'data/az_o.pkl'); J=json.load(open(W+'data/AZ_results_summary.json')); F=J['fits']; K=J['K']; PO=J['pooled']; TX=J['overballot']
REPO='https://github.com/mbenson8989/Arizona-Election-Analysis'; RAWB='https://raw.githubusercontent.com/mbenson8989/Arizona-Election-Analysis/main/'
CEDAR='https://github.com/mbenson8989/Nebraska-Election-Analysis-/wiki/Cedar-Audit'; NEWIKI='https://github.com/mbenson8989/Nebraska-Election-Analysis-/wiki'
PDFNAME='Arizona_15_County_Democratic_Registration_and_Vote_Change.pdf'
for y,t in (('2022','22'),('2026','26')):
    o['turnout'+t]=100*o[f'ballots_{y}']/o[f'regact_{y}']; o['nogov'+t]=o[f'ballots_{y}']-o[f'govtotal_{y}']
o['regact_chg']=o.regact_2026-o.regact_2022; o['share_ballots26']=100*o.ballots_2026/o.ballots_2026.sum()
BIG6=o.index[:6].tolist(); OTHER=o.index[6:].tolist()
# ---------- pass-A evaluator
def grp(cs,f):
    t=o.loc[cs].sum(numeric_only=True)
    S22=100*t.dem_2022/t.ballots_2022; S26=100*t.dem_2026/t.ballots_2026; P22=100*t.regdem_2022/t.regact_2022; P26=100*t.regdem_2026/t.regact_2026
    d=dict(S22=S22,S26=S26,P22=P22,P26=P26,dS=S26-S22,dP=P26-P22,dG=(S26-S22)-(P26-P22),G22=S22-P22,G26=S26-P26,implied=o.loc[cs,'implied_extra_votes'].sum(),
           median_dG=o.loc[cs,'dG'].median(),min_dG=o.loc[cs,'dG'].min(),max_dG=o.loc[cs,'dG'].max(),n=len(cs),share_ballots26=100*t.ballots_2026/o.ballots_2026.sum(),
           share_pop=100*t.pop2025/o.pop2025.sum())
    for k in ['ballots_2022','dem_2022','regdem_2022','regact_2022','ballots_2026','dem_2026','regdem_2026','regact_2026','rep_2022','rep_2026','govtotal_2022','govtotal_2026']: d[k]=t[k]
    for k in ('regdem','dem','ballots','regact'):
        d[k+'_chg']=t[k+'_2026']-t[k+'_2022']; d[k+'_chg_pct']=100*d[k+'_chg']/t[k+'_2022']
    d['turnout22']=100*t.ballots_2022/t.regact_2022; d['turnout26']=100*t.ballots_2026/t.regact_2026
    d['residual']=d['dG']-abs(d['dP']); d['implied_pooled']=d['dS']/100*t.ballots_2026; d['gap_reg_scaled']=o.loc[cs,'gap_reg_scaled'].sum()
    d['pred_dG']=F['dG_on_drop']['b']+F['dG_on_drop']['m']*(-d['dP'])
    d['implied_loss']=o.loc[[c for c in cs if o.loc[c,'loss']],'implied_extra_votes'].sum()
    return d[f]
def evalA(key):
    k=key.split('|')
    if k[0]=='c': return o.loc[k[1],k[2]]
    if k[0]=='g': return grp({'all':o.index.tolist(),'big6':BIG6,'other':OTHER}[k[1]],k[2])
    if k[0]=='fit':
        f=F[k[1]]; p=k[2]
        if p=='r2pct': return 100*f['r2']
        return {'b_ci_lo':f['b_ci'][0],'b_ci_hi':f['b_ci'][1],'m_ci_lo':f['m_ci'][0],'m_ci_hi':f['m_ci'][1]}.get(p,f.get(p))
    if k[0]=='k':
        n=k[1]
        if n=='n_counties': return len(o)
        if n=='n_dem_votes_fell': return int((o.dem_chg<0).sum())
        if n=='n_ballots_rose': return int((o.ballots_chg>0).sum())
        if n=='n_narrowed': return len(J['narrow']['counties'])
        if n=='n_big6': return 6
        if n=='n_other': return len(o)-6
        if n=='maricopa_share_implied': return 100*o.loc['Maricopa','implied_extra_votes']/o.implied_extra_votes.sum()
        if n=='cooks_cut': return 4/len(o)
        if n.startswith('size_'): a,b=n[5:].rsplit('_',1); return K['size_log10pop_'+a if a=='dG' else 'size_'+a][b]
        if n.startswith('spearman_'): return K['spearman_pop_dG'][n.split('_')[1]]
        if n.startswith('yi_'): return F['year_interaction'][n[3:]]
        if n.startswith('nar_'): _,c,f=n.split('_',2); return J['narrow']['detail'][c][f]
        if n.startswith('tx'): y,f=k[2],k[3]; v=TX[y][f]; return v if not isinstance(v,dict) else (v.get('votes',v.get('pct')))
        if n.startswith('nogov_lo') or n.startswith('nogov_hi'): return TX[k[2]]['nogov_pct_range'][0 if 'lo' in n else 1]
        return K[n]
    raise KeyError(key)
def q(x,nd): return Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-nd),rounding=ROUND_HALF_UP)
MINUS='−'
def fmt(x,f):
    if f in ('n','sn'):
        n=int(q(x,0)); s=f'{abs(n):,}'; return (MINUS+s if n<0 else ('+'+s if f=='sn' and n>0 else s))
    if f=='an': return fmt(abs(x),'n')
    if f=='a2': return fmt(abs(x),'f2')
    m=re.fullmatch(r'(s?)(p?)(?:f?)(\d)',f); sg,pc,nd=m.group(1),m.group(2),int(m.group(3))
    d=q(x,nd); s=f'{abs(d):.{nd}f}'+('%' if pc else '')
    return (MINUS+s if d<0 else ('+'+s if sg and d>0 else s))
MAN=[]; PAGE=None
def v(key,f): disp=fmt(evalA(key),f); MAN.append(dict(page=PAGE,kind='data',key=key,fmt=f,display=disp)); return disp
def s(text,reason): MAN.append(dict(page=PAGE,kind='static',display=text,reason=reason)); return text
def esc(t): return t.replace('*','\\*')
def C(c,f,fm): return v(f'c|{c}|{f}',fm)
# ---------- shared blocks
def banner():
    return (f"> **{s('2026','year')} UNOFFICIAL.** \\*{s('2026','year')} figures are UNOFFICIAL. The Arizona Secretary of State (SOS) results site (results.arizona.vote, served by app.enhancedvoting.com) labels the "
            f"Nov {s('3','election date')}, {s('2026','year')} general election results \"Unofficial Results\" (data as of Nov {s('19','date')}, {s('2026','year')}, {s('4:35','time')} PM CST; pulled Nov {s('19','date')}, {s('2026','year')}). "
            f"All {v('k|n_counties','n')} counties report fully. The statewide canvass is scheduled for Nov {s('23','date')}, {s('2026','year')}, so these pages need a re-run after it. "
            f"{s('2022','year')} figures are the official SOS canvass of Dec {s('5','date')}, {s('2022','year')}. **P** = Democratic share of ACTIVE registered voters, from the G.E. (general election) row of the SOS State Voter Registration reports "
            f"({s('2022','year')} General Election and November {s('2026','year')}). Governor race only. Votes are votes for the Democratic candidate, not a count of registered Democrats who voted. "
            f"These pages measure a pattern; they make no claim about intent, fraud or cause.\n")
def related(cur):
    L=[('Home','Home'),('Bottom-Up Reverse Math','Reverse-Math'),('Locked Arizona Formula','Locked-Arizona-Formula'),('Floor and Ceiling Counties','Floor-and-Ceiling'),('Graphs','Graphs'),('Arizona County PDF Information','Arizona-County-PDF-Information')]
    return '\n---\n**Related:** '+' · '.join(f'[{a}]({b})' for a,b in L if b!=cur)+f' · [Cedar County Audit (Nebraska)]({CEDAR})\n'
pages={}
# ================= HOME
PAGE='Home'
T=lambda f,fm: v(f'g|all|{f}',fm)
h=banner()+f"""
# Arizona {s('2022','year')} vs {s('2026','year')}\\* Governor Race: ΔG Method

Method developed by Morissa Benson (CD3 Vice Chair, Nebraska GOP). It began with her [Cedar County Audit]({CEDAR}) on the [Nebraska Election Analysis wiki]({NEWIKI}). That audit is where the ΔG method and the reverse step come from. This wiki applies the same arithmetic to all {v('k|n_counties','n')} Arizona counties. Arizona has party registration, so it uses the registration baseline, as the Nevada, North Carolina, Kansas and Pennsylvania analyses do. Data: Arizona Secretary of State results, official canvass and voter registration reports ([azsos.gov](https://azsos.gov/elections/election-information/voter-registration-counts), [results.arizona.vote](https://results.arizona.vote/)). Population comes from the U.S. Census Bureau. Compiled Nov {s('19','date')}, {s('2026','year')}. Code and data: [Arizona-Election-Analysis]({REPO}).

## Pages

{s('1','list ordinal')}. [Cedar County Audit]({CEDAR}) (Nebraska wiki): where the method started
{s('2','list ordinal')}. [Bottom-Up Reverse Math](Reverse-Math): Maricopa → the six largest counties → all {v('k|n_counties','n')} counties, then solved backward for implied extra votes
{s('3','list ordinal')}. [Locked Arizona Formula](Locked-Arizona-Formula): the statewide fitted equation, a blank template, a worked example and the Arizona-only constants
{s('4','list ordinal')}. [Floor and Ceiling Counties](Floor-and-Ceiling): the floor and ceiling counties, the counties narrowed out of the fit, and the over-ballot check
{s('5','list ordinal')}. [Graphs](Graphs): ΔG by population, the locked-formula scatter, slope chart, ΔS and ΔP components, forward fit, residuals and the over-ballot check
{s('6','list ordinal')}. [Arizona County PDF Information](Arizona-County-PDF-Information): the {v('k|n_counties','n')}-county PDF table (registration, votes and ballots, {s('2022','year')} vs {s('2026','year')}\\*) and what each column means

## Statewide at a glance

| Measure | {s('2022','year')} | {s('2026','year')}\\* | Change |
|---|---|---|---|
| Democratic active registered voters (G.E. row) | {T('regdem_2022','n')} | {T('regdem_2026','n')} | {T('regdem_chg','sn')} ({T('regdem_chg_pct','sp1')}) |
| All active registered voters (G.E. row) | {T('regact_2022','n')} | {T('regact_2026','n')} | {T('regact_chg','sn')} |
| **P**: Democratic share of active registration | {T('P22','p2')} | {T('P26','p2')} | {T('dP','s2')} pts |
| Democratic governor votes | {T('dem_2022','n')} | {T('dem_2026','n')} | {T('dem_chg','sn')} ({T('dem_chg_pct','sp1')}) |
| Total ballots cast | {T('ballots_2022','n')} | {T('ballots_2026','n')} | {T('ballots_chg','sn')} ({T('ballots_chg_pct','sp1')}) |
| **S**: Democratic share of ballots cast | {T('S22','p2')} | {T('S26','p2')} | {T('dS','s2')} pts |
| **G** = S − P | {T('G22','s2')} | {T('G26','s2')} | ΔG {T('dG','s2')} |
| Republican governor votes | {T('rep_2022','n')} | {T('rep_2026','n')} | |
| All governor votes (incl. write-ins) | {T('govtotal_2022','n')} | {T('govtotal_2026','n')} | |

Candidates: {s('2022','year')} Katie Hobbs (D) and Kari Lake (R), plus write-ins. {s('2026','year')}\\* Katie Hobbs (D, incumbent; running mate John Giles), Andy Biggs (R), Risa Lombardo (Green), Teri Ann Hourihan (No Labels), plus write-ins.

## County results in brief

- **Democratic active registration fell in {v('k|n_loss','n')} of {v('k|n_counties','n')} counties** ({T('regdem_2022','n')} → {T('regdem_2026','n')} statewide), while all active registration rose {T('regact_chg','sn')}. Pinal is the exception: its Democratic active registration rose {C('Pinal','regdem_chg','sn')}. P fell in all {v('k|n_P_fell','n')} counties, from {C('Yavapai','dP','s2')} (Yavapai) to {C('Santa Cruz','dP','s2')} (Santa Cruz).
- **S rose in all {v('k|n_S_rose','n')} counties**, from {C('Apache','dS','s2')} (Apache) to {C('Yuma','dS','s2')} (Yuma). Democratic governor votes rose in {v('k|n_dem_votes_rose','n')} counties and fell in {v('k|n_dem_votes_fell','n')} (Gila, Greenlee).
- **ΔG rose in all {v('k|n_pos','n')} counties.** The ceiling is **Yuma** at {C('Yuma','dG','s2')}; the lowest ΔG is **Yavapai** at {C('Yavapai','dG','s2')}. County median {v('k|median_dG','s2')}; statewide pooled {T('dG','s2')}.
- **Implied extra votes** (votes above what the {s('2022','year')} Democratic share of ballots would give on {s('2026','year')}\\* turnout) sum to {T('implied','sn')} across the {v('k|n_counties','n')} counties; Maricopa alone is {C('Maricopa','implied_extra_votes','sn')} ({v('k|maricopa_share_implied','p1')}).
- **Locked Arizona formula:** ΔG = {v('fit|dG_on_drop|b','f2')} + {v('fit|dG_on_drop|m','f2')} × (drop in Democratic registration share, points), R² {v('fit|dG_on_drop|r2','f2')}, n = {v('fit|dG_on_drop|n','n')}. See [Locked Arizona Formula](Locked-Arizona-Formula).

## County PDF

The [Arizona County PDF Information](Arizona-County-PDF-Information) page describes the {v('k|n_counties','n')}-county PDF and links the download: **[{PDFNAME}]({RAWB}{PDFNAME})**.
"""+related('Home')
pages['Home']=h
# ================= REVERSE MATH
PAGE='Reverse-Math'
def cc(c,f,fm): return C(c,f,fm)
G=lambda g,f,fm: v(f'g|{g}|{f}',fm)
rm=banner()+f"""
The same arithmetic at three levels: one county, then the six largest, then the whole state. It is then solved backward for implied extra votes. Denominator: Democratic governor votes ÷ total ballots cast. The method comes from the [Cedar County Audit]({CEDAR}) in Nebraska.

## Step {s('1','step ordinal')}: Maricopa County (the largest county)

| Step | Value |
|---|---|
| Democratic share of ballots (S) | {cc('Maricopa','S22','p2')} ({s('2022','year')}: {cc('Maricopa','dem_2022','n')} of {cc('Maricopa','ballots_2022','n')}) → {cc('Maricopa','S26','p2')} ({s('2026','year')}\\*: {cc('Maricopa','dem_2026','n')} of {cc('Maricopa','ballots_2026','n')}): **{cc('Maricopa','dS','s2')} points** |
| Democratic active-registration share (P) | {cc('Maricopa','P22','p2')} ({cc('Maricopa','regdem_2022','n')} of {cc('Maricopa','regact_2022','n')}) → {cc('Maricopa','P26','p2')} ({cc('Maricopa','regdem_2026','n')} of {cc('Maricopa','regact_2026','n')}): **{cc('Maricopa','dP','s2')} points** |
| ΔG = ΔS − ΔP | **{cc('Maricopa','dG','s2')} points** |
| Reverse step: ΔG − registration-share loss | **{cc('Maricopa','residual','s2')}** (the residual) |
| Implied extra votes | {cc('Maricopa','dem_2026','n')} − {cc('Maricopa','S22','p2')} × {cc('Maricopa','ballots_2026','n')} = **about {cc('Maricopa','implied_extra_votes','sn')}** |
| Registration-scaled gap (Nebraska "gap in votes", for comparison) | {cc('Maricopa','dem_2026','n')} − {cc('Maricopa','dem_2022','n')} × ({cc('Maricopa','regdem_2026','n')} ÷ {cc('Maricopa','regdem_2022','n')}) = about {cc('Maricopa','gap_reg_scaled','sn')} |

Maricopa is the largest county ({cc('Maricopa','pop2025','n')} people, {v('k|maricopa_share_implied','p1')} of the statewide implied extra votes). Its Democratic active registration fell by {cc('Maricopa','regdem_chg','an')} while its active rolls grew by {cc('Maricopa','regact_chg','n')}, so P fell {cc('Maricopa','dP','a2')} points; its S rose {cc('Maricopa','dS','f2')} points.

## Step {s('2','step ordinal')}: the six largest counties

Largest to smallest population (U.S. Census Bureau, Vintage {s('2025','census vintage year')} estimates).

| County | Population | P {s('2022','year')} | P {s('2026','year')}\\* | S {s('2022','year')} | S {s('2026','year')}\\* | ΔS (pts) | ΔP (pts) | ΔG (pts) | Implied extra votes |
|---|---|---|---|---|---|---|---|---|---|
"""
for c in BIG6:
    rm+=f"| {c} | {cc(c,'pop2025','n')} | {cc(c,'P22','p2')} | {cc(c,'P26','p2')} | {cc(c,'S22','p2')} | {cc(c,'S26','p2')} | {cc(c,'dS','s2')} | {cc(c,'dP','s2')} | {cc(c,'dG','s2')} | {cc(c,'implied_extra_votes','sn')} |\n"
rm+=f"""
ΔG is positive in all six. Together they cast {G('big6','share_ballots26','p1')} of {s('2026','year')}\\* ballots. Five of the six lost Democratic active registrants; Pinal gained {cc('Pinal','regdem_chg','n')}, so Pinal skips the residual step below.

## Step {s('3','step ordinal')}: all {v('k|n_counties','n')} counties

| Group | Counties | S {s('2022','year')} | S {s('2026','year')}\\* | P {s('2022','year')} | P {s('2026','year')}\\* | ΔS | ΔP | Pooled ΔG | County median ΔG (range) | Implied extra votes |
|---|---|---|---|---|---|---|---|---|---|---|
"""
for g,name in (('big6','Six largest counties'),('other','Other nine counties'),('all','All Arizona counties')):
    rm+=f"| {name} | {G(g,'n','n')} | {G(g,'S22','p2')} | {G(g,'S26','p2')} | {G(g,'P22','p2')} | {G(g,'P26','p2')} | {G(g,'dS','s2')} | {G(g,'dP','s2')} | {G(g,'dG','s2')} | {G(g,'median_dG','s2')} ({G(g,'min_dG','s2')} to {G(g,'max_dG','s2')}) | {G(g,'implied','sn')} |\n"
rm+=f"""
- ΔG rose in {v('k|n_pos','n')} of {v('k|n_counties','n')} counties. The county-level SD of ΔG is {v('k|sd_dG','f2')} points; the mean is {v('k|mean_dG','s2')}.
- **County size.** ΔG against log population: r = {v('k|size_dG_r','f2')} (p = {v('k|size_dG_p','f2')}), not significant with {v('k|n_counties','n')} counties; Spearman rank correlation {v('k|spearman_rho','f2')} (p = {v('k|spearman_p','f2')}). ΔS: r = {v('k|size_dS_r','f2')} (p = {v('k|size_dS_p','f2')}); ΔP: r = {v('k|size_dP_r','f2')} (p = {v('k|size_dP_p','f2')}): larger counties lost less registration share.
- **Pooled solve-back.** Statewide S rose {G('all','dS','f2')} points; applied to {s('2026','year')}\\* ballots ({G('all','ballots_2026','n')}) that is about {G('all','implied_pooled','sn')} votes. The county-by-county sum is {G('all','implied','sn')}, of which the {v('k|n_loss','n')} counties that lost Democratic registration account for {G('all','implied_loss','sn')}.
- **Nebraska-style registration-scaled gap**, summed over all counties: {G('all','gap_reg_scaled','sn')} (Democratic governor votes {s('2026','year')}\\* minus {s('2022','year')} votes scaled by each county's change in Democratic active registration).

## Residual step: the {v('k|n_loss','n')} counties that lost Democratic active registrants

Residual = ΔG − |ΔP|. Pinal is left out because its Democratic active registration rose ({cc('Pinal','regdem_2022','n')} → {cc('Pinal','regdem_2026','n')}). Median residual {v('k|median_residual','s2')}.

| County | Population | Dem active reg {s('2022','year')} | Dem active reg {s('2026','year')}\\* | P change | ΔG | Residual = ΔG − \\|ΔP\\| | Implied extra votes |
|---|---|---|---|---|---|---|---|
"""
for c in o.index:
    if not o.loc[c,'loss']: continue
    rm+=f"| {c} | {cc(c,'pop2025','n')} | {cc(c,'regdem_2022','n')} | {cc(c,'regdem_2026','n')} | {cc(c,'dP','s2')} | {cc(c,'dG','s2')} | {cc(c,'residual','s2')} | {cc(c,'implied_extra_votes','sn')} |\n"
rm+=f"""
## All {v('k|n_counties','n')} counties: full table

Largest to smallest population. D = Democratic governor votes, B = total ballots, R = Democratic active registered voters, A = all active registered voters.

| County | Population | D {s('2022','year')} | B {s('2022','year')} | S {s('2022','year')} | R {s('2022','year')} | A {s('2022','year')} | P {s('2022','year')} | D {s('2026','year')}\\* | B {s('2026','year')}\\* | S {s('2026','year')}\\* | R {s('2026','year')}\\* | A {s('2026','year')}\\* | P {s('2026','year')}\\* | ΔG | Registration-scaled gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
"""
for c in o.index:
    rm+=(f"| {c} | {cc(c,'pop2025','n')} | {cc(c,'dem_2022','n')} | {cc(c,'ballots_2022','n')} | {cc(c,'S22','f2')} | {cc(c,'regdem_2022','n')} | {cc(c,'regact_2022','n')} | {cc(c,'P22','f2')} | "
         f"{cc(c,'dem_2026','n')} | {cc(c,'ballots_2026','n')} | {cc(c,'S26','f2')} | {cc(c,'regdem_2026','n')} | {cc(c,'regact_2026','n')} | {cc(c,'P26','f2')} | {cc(c,'dG','s2')} | {cc(c,'gap_reg_scaled','sn')} |\n")
rm+=related('Reverse-Math'); pages['Reverse-Math']=rm
# ================= LOCKED FORMULA
PAGE='Locked-Arizona-Formula'
Fv=lambda n,p,fm: v(f'fit|{n}|{p}',fm)
lk=banner()+f"""
## Arizona fitted equation (statewide, locked)

```
Arizona equation:  ΔG = {Fv('dG_on_drop','b','s2')} + {Fv('dG_on_drop','m','f2')} × (Dem registration-share drop, points)
Four decimals:     ΔG = {Fv('dG_on_drop','b','s4')} + {Fv('dG_on_drop','m','f4')} × (Dem registration-share drop, points)
```

| Item | Rounded | {s('4','decimal places')} decimals | {s('95%','confidence level')} confidence interval |
|---|---|---|---|
| Constant (intercept) | {Fv('dG_on_drop','b','s2')} | {Fv('dG_on_drop','b','s4')} | {Fv('dG_on_drop','b_ci_lo','f2')} to {Fv('dG_on_drop','b_ci_hi','f2')} |
| Multiplier (slope) | {Fv('dG_on_drop','m','f2')} | {Fv('dG_on_drop','m','f4')} | {Fv('dG_on_drop','m_ci_lo','f2')} to {Fv('dG_on_drop','m_ci_hi','f2')} |
| Intercept standard error | {Fv('dG_on_drop','b_se','f2')} | {Fv('dG_on_drop','b_se','f4')} | |
| Slope standard error | {Fv('dG_on_drop','m_se','f2')} | {Fv('dG_on_drop','m_se','f4')} | |
| R² | {Fv('dG_on_drop','r2','f2')} | {Fv('dG_on_drop','r2','f4')} | |
| Slope p-value | {Fv('dG_on_drop','m_p','f3')} | | |
| Residual standard error (points) | {Fv('dG_on_drop','resid_se','f2')} | | |

Fitted by ordinary least squares across all {Fv('dG_on_drop','n','n')} counties (n = {Fv('dG_on_drop','n','n')}): {s('2022','year')} to {s('2026','year')}\\* governor race, **active** registration (SOS State Voter Registration reports, G.E. row), S denominator = total ballots cast, locked gap formula. Registration-share drop = P {s('2022','year')} − P {s('2026','year')}, in points. {s('2026','year')} figures are UNOFFICIAL. Computed in Pass A (statsmodels OLS) and re-derived in Pass B (closed-form, pure Python) by verify_wiki.py; both give the same values at every displayed decimal.

**What it means:** across Arizona's counties, each {s('1','unit (per one point)')}-point drop in Democratic registration share goes with about {Fv('dG_on_drop','m','f2')} points of ΔG, starting from about {Fv('dG_on_drop','b','s2')} when the share does not fall. The fit explains about {v('fit|dG_on_drop|r2pct','p0')} of the county-to-county differences in ΔG; with {Fv('dG_on_drop','n','n')} counties the slope is imprecise (standard error {Fv('dG_on_drop','m_se','f2')}).

**Statewide check.** At the pooled statewide drop of {G('all','dP','a2')} points the equation gives ΔG {G('all','pred_dG','s2')}; the pooled statewide ΔG is {G('all','dG','s2')}.

**Worked example: Maricopa.** P fell from {cc('Maricopa','P22','f2')} to {cc('Maricopa','P26','f2')}, a drop of {cc('Maricopa','regdrop','f4')} points. Predicted ΔG = {Fv('dG_on_drop','b','s4')} + {Fv('dG_on_drop','m','f4')} × {cc('Maricopa','regdrop','f4')} = {cc('Maricopa','fit_dG','s2')}. Actual ΔG = {cc('Maricopa','dG','s2')}\\*. Difference from the fitted line (actual − predicted) = {cc('Maricopa','res_dG','s2')}\\*. This difference is not the line-{s('11','template line number')} residual in the template below, which is ΔG minus the registration-share drop ({cc('Maricopa','residual','s2')}\\* for Maricopa).

## Robustness

| Fit | Constant (SE) | Multiplier (SE) | R² | n |
|---|---|---|---|---|
| Locked: ΔG on drop, unweighted | {Fv('dG_on_drop','b','s2')} ({Fv('dG_on_drop','b_se','f2')}) | {Fv('dG_on_drop','m','f2')} ({Fv('dG_on_drop','m_se','f2')}) | {Fv('dG_on_drop','r2','f2')} | {Fv('dG_on_drop','n','n')} |
| Weighted by {s('2026','year')}\\* ballots | {Fv('dG_on_drop_wtd','b','s2')} ({Fv('dG_on_drop_wtd','b_se','f2')}) | {Fv('dG_on_drop_wtd','m','f2')} ({Fv('dG_on_drop_wtd','m_se','f2')}) | {Fv('dG_on_drop_wtd','r2','f2')} | {Fv('dG_on_drop_wtd','n','n')} |
| Narrowed (Yuma left out) | {Fv('dG_on_drop_narrowed','b','s2')} ({Fv('dG_on_drop_narrowed','b_se','f2')}) | {Fv('dG_on_drop_narrowed','m','f2')} ({Fv('dG_on_drop_narrowed','m_se','f2')}) | {Fv('dG_on_drop_narrowed','r2','f2')} | {Fv('dG_on_drop_narrowed','n','n')} |

Weighting by ballots lets Maricopa ({cc('Maricopa','dG','s2')} ΔG on a {cc('Maricopa','regdrop','f2')}-point drop) dominate, and the slope is no longer distinguishable from zero (p = {Fv('dG_on_drop_wtd','m_p','f2')}). Yuma is narrowed out by the rule on the [Floor and Ceiling](Floor-and-Ceiling) page.

## Forward fits: G vs P, Arizona-only constants

G = b + m × P, with P in points.

| Year | Constant b (SE) | Slope m (SE) | R² | n |
|---|---|---|---|---|
| {s('2022','year')} | {Fv('G22_on_P22','b','s2')} ({Fv('G22_on_P22','b_se','f2')}) | {Fv('G22_on_P22','m','f3')} ({Fv('G22_on_P22','m_se','f3')}) | {Fv('G22_on_P22','r2','f2')} | {Fv('G22_on_P22','n','n')} |
| {s('2026','year')}\\* | {Fv('G26_on_P26','b','s2')} ({Fv('G26_on_P26','b_se','f2')}) | {Fv('G26_on_P26','m','f3')} ({Fv('G26_on_P26','m_se','f3')}) | {Fv('G26_on_P26','r2','f2')} | {Fv('G26_on_P26','n','n')} |

Neither forward slope is significant (p = {Fv('G22_on_P22','m_p','f2')} and {Fv('G26_on_P26','m_p','f2')}). Pooling both years with a year term, the {s('2026','year')}\\* line sits {v('k|yi_d_intercept','f2')} points higher at P = {s('0','x-axis origin')} (p = {v('k|yi_p_d_intercept','f2')}) and its slope differs by {v('k|yi_d_slope','f3')} (p = {v('k|yi_p_d_slope','f2')}).

## The equation

- **S** (Democratic vote share) = Democratic governor votes ÷ total ballots cast × {s('100','percent scale')}. {s('2022','year')}: the canvass "Total Ballots Cast" row; {s('2026','year')}\\*: "Ballots Cast" on the SOS results site.
- **P** (Democratic registration share) = Democratic ACTIVE registered voters ÷ all ACTIVE registered voters × {s('100','percent scale')}, from the G.E. row of the SOS State Voter Registration report for each year.
- **G** = S − P
- **ΔG** = G({s('2026','year')}) − G({s('2022','year')}) = (S2026 − S2022) − (P2026 − P2022)
- **Reverse step (residual).** Only where Democratic active registration fell: residual = ΔG − |P2026 − P2022|.
- **Solved backward: implied extra votes** = D2026 − (S2022 ÷ {s('100','percent scale')}) × ballots2026
- **Registration-scaled gap** (the Nebraska wiki's "gap in votes" line, for comparison) = D2026 − D2022 × (DemReg2026 ÷ DemReg2022)

### Why these files

- **Registration report.** The SOS State Voter Registration report for each general election has an "Active" county table with an APR, P.E. and G.E. row. The G.E. row is the registration for the general election itself; its {s('2022','year')} county totals equal the canvass "Total Eligible Registration" row, and its {s('2026','year')} totals equal the "Registered Voters" shown on the SOS results site for every county.
- **Write-ins.** Total governor votes include write-ins; they are used only in the over-vote check. S divides by ballots cast.

## Blank template

| Line | Item | {s('2022','year')} | {s('2026','year')} |
|---|---|---|---|
| {s('1','template line')} | Democratic governor votes | ______ | ______ |
| {s('2','template line')} | Total ballots cast | ______ | ______ |
| {s('3','template line')} | S = line {s('1','template line ref')} ÷ line {s('2','template line ref')} × {s('100','percent scale')} | ______ | ______ |
| {s('4','template line')} | Democratic active registered voters (SOS report, G.E. row) | ______ | ______ |
| {s('5','template line')} | All active registered voters (same row) | ______ | ______ |
| {s('6','template line')} | P = line {s('4','template line ref')} ÷ line {s('5','template line ref')} × {s('100','percent scale')} | ______ | ______ |
| {s('7','template line')} | G = line {s('3','template line ref')} − line {s('6','template line ref')} | ______ | ______ |
| {s('8','template line')} | ΔG = G {s('2026','year')} − G {s('2022','year')} |  | ______ |
| {s('9','template line')} | Registration-share drop = P {s('2022','year')} − P {s('2026','year')} |  | ______ |
| {s('10','template line')} | Did Democratic active registration fall? (line {s('4','template line ref')}: {s('2026','year')} < {s('2022','year')}) |  | Yes / No |
| {s('11','template line')} | If yes: residual = line {s('8','template line ref')} − line {s('9','template line ref')} |  | ______ |
| {s('12','template line')} | Implied extra votes = line {s('1','template line ref')} ({s('2026','year')}) − line {s('3','template line ref')} ({s('2022','year')}) ÷ {s('100','percent scale')} × line {s('2','template line ref')} ({s('2026','year')}) |  | ______ |
| {s('13','template line')} | Predicted ΔG = {Fv('dG_on_drop','b','s4')} + {Fv('dG_on_drop','m','f4')} × line {s('9','template line ref')} |  | ______ |
| {s('14','template line')} | Distance from the Arizona line = line {s('8','template line ref')} − line {s('13','template line ref')} |  | ______ |

## Worked example: Yuma (ceiling county)

| Line | Item | {s('2022','year')} | {s('2026','year')}\\* |
|---|---|---|---|
| {s('1','template line')} | Democratic governor votes | {cc('Yuma','dem_2022','n')} | {cc('Yuma','dem_2026','n')} |
| {s('2','template line')} | Total ballots cast | {cc('Yuma','ballots_2022','n')} | {cc('Yuma','ballots_2026','n')} |
| {s('3','template line')} | S | {cc('Yuma','S22','p2')} | {cc('Yuma','S26','p2')} |
| {s('4','template line')} | Democratic active registered voters | {cc('Yuma','regdem_2022','n')} | {cc('Yuma','regdem_2026','n')} |
| {s('5','template line')} | All active registered voters | {cc('Yuma','regact_2022','n')} | {cc('Yuma','regact_2026','n')} |
| {s('6','template line')} | P | {cc('Yuma','P22','p2')} | {cc('Yuma','P26','p2')} |
| {s('7','template line')} | G | {cc('Yuma','G22','s2')} | {cc('Yuma','G26','s2')} |
| {s('8','template line')} | ΔG | | {cc('Yuma','dG','s2')} |
| {s('9','template line')} | Registration-share drop | | {cc('Yuma','regdrop','f2')} |
| {s('10','template line')} | Democratic active registration fell? | | Yes |
| {s('11','template line')} | Residual | | {cc('Yuma','residual','s2')} |
| {s('12','template line')} | Implied extra votes | | {cc('Yuma','implied_extra_votes','sn')} |
| {s('13','template line')} | Predicted ΔG | | {cc('Yuma','fit_dG','s2')} |
| {s('14','template line')} | Distance from the Arizona line | | {cc('Yuma','res_dG','s2')} |

## Every county against the locked line

Largest to smallest population.

| County | Registration-share drop (pts) | Actual ΔG | Predicted ΔG | Actual − predicted |
|---|---|---|---|---|
"""
for c in o.index:
    lk+=f"| {c} | {cc(c,'regdrop','f2')} | {cc(c,'dG','s2')} | {cc(c,'fit_dG','s2')} | {cc(c,'res_dG','s2')} |\n"
lk+=related('Locked-Arizona-Formula'); pages['Locked-Arizona-Formula']=lk
# ================= FLOOR AND CEILING
PAGE='Floor-and-Ceiling'
fc=banner()+f"""
## How to read floor and ceiling counties

Look for the pattern at both ends. The ceiling counties have the highest ΔG. The floor counties are the most Republican baseline, where there were the fewest Democrats to move.

- **The ceiling**, the single county with the highest ΔG, is **Yuma** at {cc('Yuma','dG','s2')}. Its S rose {cc('Yuma','dS','f2')} points while its P fell {cc('Yuma','dP','a2')}.
- **The floor by ΔG**, the single county with the lowest ΔG, is **Yavapai** at {cc('Yavapai','dG','s2')}. Its S rose {cc('Yavapai','dS','f2')} points while its P fell {cc('Yavapai','dP','a2')}.

## Terminology

- **Ceiling counties** are the five largest ΔG: """+', '.join(f"{c} {cc(c,'dG','s2')}" for c in K['ceiling'])+". Their ΔS: "+', '.join(f"{c} {cc(c,'dS','s2')}" for c in K['ceiling'])+". Their ΔP: "+', '.join(f"{c} {cc(c,'dP','s2')}" for c in K['ceiling'])+f""".
- **Floor counties** are the most Republican baseline: the five lowest {s('2022','year')} P. """+', '.join(f"{c} {cc(c,'P22','p2')} (ΔG {cc(c,'dG','s2')})" for c in K['floor'])+f". Read by {s('2022','year')} Democratic share of ballots instead, the five lowest are "+', '.join(K['lowest5_S22'])+". Read by ΔG instead, the five lowest are "+', '.join(K['lowest5_dG'])+f""".
- **Graham** is both a floor and a ceiling county: a low {s('2022','year')} Democratic registration share ({cc('Graham','P22','p2')}) and one of the five largest ΔG ({cc('Graham','dG','s2')}).
- **Non-loss counties** had no drop in Democratic active registration: Pinal ({cc('Pinal','regdem_chg','sn')}).
- **Loss counties** (residual step): the other {v('k|n_loss','n')}.
- **Narrowed-out counties** distort the locked fit and are flagged below: Yuma.

## Ceiling and floor detail

Largest to smallest population.

| County | Group | Population | P {s('2022','year')} | P {s('2026','year')}\\* | S {s('2022','year')} | S {s('2026','year')}\\* | G {s('2022','year')} | G {s('2026','year')}\\* | ΔG | Implied extra votes |
|---|---|---|---|---|---|---|---|---|---|---|
"""
for c in o.index:
    if c not in K['floor'] and c not in K['ceiling']: continue
    grpn='Floor and ceiling' if (c in K['floor'] and c in K['ceiling']) else ('Floor' if c in K['floor'] else 'Ceiling')
    fc+=f"| {c} | {grpn} | {cc(c,'pop2025','n')} | {cc(c,'P22','p2')} | {cc(c,'P26','p2')} | {cc(c,'S22','p2')} | {cc(c,'S26','p2')} | {cc(c,'G22','s2')} | {cc(c,'G26','s2')} | {cc(c,'dG','s2')} | {cc(c,'implied_extra_votes','sn')} |\n"
fc+=f"""
## Regional constants

Not computed for Arizona. With {v('k|n_counties','n')} counties, a regional split leaves groups too small to fit a line, and Maricopa alone cast {cc('Maricopa','share_ballots26','p1')} of {s('2026','year')}\\* ballots. The narrowed fit below is the robustness check instead.

## Counties narrowed out of the fit

Rule: Cook's distance > {s('4','rule constant')}/n ({v('k|cooks_cut','f3')}) or |externally studentized residual| > {s('2.5','rule threshold')}, in the locked ΔG-on-drop fit.

| County | Cook's distance | Studentized residual | Registration-share drop | ΔG |
|---|---|---|---|---|
| Yuma | {v('k|nar_Yuma_cooks','f3')} | {v('k|nar_Yuma_stud','f2')} | {cc('Yuma','regdrop','f2')} | {cc('Yuma','dG','s2')} |

Without Yuma: ΔG = {Fv('dG_on_drop_narrowed','b','s2')} + {Fv('dG_on_drop_narrowed','m','f2')} × drop, R² {Fv('dG_on_drop_narrowed','r2','f2')}, n = {Fv('dG_on_drop_narrowed','n','n')}.

## County size

ΔG against log population: slope {v('k|size_dG_slope','s2')} per tenfold population, r = {v('k|size_dG_r','f2')} (p = {v('k|size_dG_p','f2')}). The largest county (Maricopa, {cc('Maricopa','dG','s2')}) sits near the statewide pooled ΔG ({G('all','dG','s2')}); the ceiling and floor both include small and mid-size counties.

## Over-ballot check

| Check | {s('2022','year')} | {s('2026','year')}\\* |
|---|---|---|
| Counties with more governor votes than ballots | none | none |
| Counties with more ballots than active registered voters | none | none |
| Smallest margin, ballots − governor votes | Greenlee, {v('k|tx|2022|min_ballots_minus_gov','n')} | Greenlee, {v('k|tx|2026|min_ballots_minus_gov','n')} |
| Ballots with no governor vote, share range | {v('k|nogov_lo|2022','p2')} to {v('k|nogov_hi|2022','p2')} | {v('k|nogov_lo|2026','p2')} to {v('k|nogov_hi|2026','p2')} |
| Highest turnout of active registration | Yavapai, {cc('Yavapai','turnout22','p2')} | Yavapai, {cc('Yavapai','turnout26','p2')} |
| Statewide turnout of active registration | {G('all','turnout22','p2')} | {G('all','turnout26','p2')} |

## All counties, turnout and blank governor lines

| County | Ballots {s('2022','year')} | Governor votes {s('2022','year')} | No governor vote {s('2022','year')} | Turnout {s('2022','year')} | Ballots {s('2026','year')}\\* | Governor votes {s('2026','year')}\\* | No governor vote {s('2026','year')}\\* | Turnout {s('2026','year')}\\* |
|---|---|---|---|---|---|---|---|---|
"""
for c in o.index:
    fc+=f"| {c} | {cc(c,'ballots_2022','n')} | {cc(c,'govtotal_2022','n')} | {cc(c,'nogov22','n')} | {cc(c,'turnout22','p2')} | {cc(c,'ballots_2026','n')} | {cc(c,'govtotal_2026','n')} | {cc(c,'nogov26','n')} | {cc(c,'turnout26','p2')} |\n"
fc+=related('Floor-and-Ceiling'); pages['Floor-and-Ceiling']=fc
# ================= GRAPHS
PAGE='Graphs'
CH=[('AZ_DeltaG_by_Population.png','ΔG by county, population order',f"ΔG for every county, largest population on the left. Red = the five ceiling counties, blue = the five floor counties (lowest {s('2022','year')} P), purple = Graham (both). Dashed line: statewide pooled ΔG {G('all','dG','s2')}."),
    ('AZ_DeltaG_vs_RegShareDrop_Scatter.png','The locked Arizona formula',f"ΔG against the drop in Democratic registration share, with the fitted line ΔG = {Fv('dG_on_drop','b','f2')} + {Fv('dG_on_drop','m','f2')} × drop (R² {Fv('dG_on_drop','r2','f2')}). Bubble size grows with {s('2026','year')}\\* ballots."),
    ('AZ_Slope_G2022_to_G2026.png',f"Slope chart: G, {s('2022','year')} → {s('2026','year')}\\*","G rose in every county. Red = ceiling counties."),
    ('AZ_DeltaG_Components_dS_vs_dP_by_Population.png','What ΔG is made of: ΔS vs ΔP','Blue: change in Democratic share of ballots. Orange: the drop in Democratic active-registration share. ΔG is their sum.'),
    ('AZ_Share_and_Registration_by_Population.png','Democratic share of ballots and P, population order',f"Bars: Democratic share of ballots in {s('2022','year')} and {s('2026','year')}\\*. Ticks: P in each year."),
    ('AZ_Forward_Fit_G_vs_P_2022_2026.png','Forward fit: Arizona-only constants',f"G against P with each year's fitted line ({s('2022','year')}: R² {Fv('G22_on_P22','r2','f2')}; {s('2026','year')}\\*: R² {Fv('G26_on_P26','r2','f2')})."),
    ('AZ_Residual_and_Implied_Votes_by_Population.png','Residuals and implied extra votes',f"Top: residual = ΔG − |ΔP| for the {v('k|n_loss','n')} counties that lost Democratic registration (Pinal shown as n/a). Bottom: implied extra votes, log scale."),
    ('AZ_Overballot_Check_by_Population.png','Over-ballot check',f"Ballots as a share of active registration, both years. No county is over the {s('100%','reference line')} line, and no county had more governor votes than ballots.")]
gp=banner()+f"\nEvery chart carries the {s('2026','year')} UNOFFICIAL label in its footer. Bars run left to right from the largest county to the smallest (Census Vintage {s('2025','census vintage year')}).\n"
for i,(fn,t,cap) in enumerate(CH,1):
    for tk in re.findall(r'(?<![\w.])[+−-]?\d+(?:,\d{3})*(?:\.\d+)?%?',t): s(tk,'repeat of heading static in image alt text')
    gp+=f"\n## {s(str(i),'section ordinal')}. {t}\n\n![{t}]({RAWB}{fn})\n\n*{cap}*\n"
gp+=related('Graphs'); pages['Graphs']=gp
# ================= PDF INFO
PAGE='Arizona-County-PDF-Information'
pi=banner()+f"""
# Arizona County PDF Information

A {s('3','page count')}-page PDF covering all {v('k|n_counties','n')} Arizona counties, {s('2022','year')} vs {s('2026','year')}\\*, modeled on Nebraska's {s('93','Nebraska county count (template name)')}-county summary PDF. Counties are sorted by {s('2026','year')} Democratic share of active registration, highest first (Apache, {cc('Apache','P26','p1')}). Every page carries the {s('2026','year')} UNOFFICIAL banner. Page {s('1','page number')} is the registration, vote and ballot table; page {s('2','page number')} gives the shares of ballots and registration; page {s('3','page number')} has the notes and sources.

**[Download the Arizona {v('k|n_counties','n')}-County Summary (PDF)]({RAWB}{PDFNAME})**

**Columns (page {s('1','page number')})**

- **Dem Reg Share {s('2026','year')} %:** Democratic active registered voters ÷ all active registered voters, SOS November {s('2026','year')} report, G.E. row. The sort column.
- **Dem Reg {s('2022','year')} / {s('2026','year')} (G.E.):** Democratic active registered voters, G.E. row of each year's SOS State Voter Registration report.
- **Reg Change (number and percent):** {s('2026','year')} minus {s('2022','year')}, and that change as a percent of the {s('2022','year')} figure.
- **Dem Gov Votes {s('2022','year')} / {s('2026','year')}\\*:** votes for the Democratic governor candidate, Katie Hobbs in both years ({s('2022','year')} official canvass; {s('2026','year')} UNOFFICIAL).
- **Vote Change (number and percent):** {s('2026','year')} minus {s('2022','year')}, and that change as a percent of the {s('2022','year')} figure.
- **Total Ballots {s('2022','year')} / {s('2026','year')}\\*:** total ballots cast in the county.
- **Ballot Change (number and percent):** {s('2026','year')} minus {s('2022','year')}, and that change as a percent of the {s('2022','year')} figure.
- **Shading:** blue = Democratic active registration rose (Pinal); peach = Democratic governor votes fell (Greenlee, Gila).

**Columns (page {s('2','page number')})**: Democratic share of ballots {s('2022','year')} and {s('2026','year')}\\* and the change in points; Democratic share of registration and total active registered voters for each year; registration-share change in points.

Statewide totals row: Democratic active registration {G('all','regdem_2022','n')} → {G('all','regdem_2026','n')}; Democratic governor votes {G('all','dem_2022','n')} → {G('all','dem_2026','n')}; total ballots {G('all','ballots_2022','n')} → {G('all','ballots_2026','n')}; {s('2026','year')} Democratic registration share {G('all','P26','p1')}.

## How the PDF was checked

Every cell was computed by two independent passes from the raw SOS files and then recomputed a third time by a separate checker that parses the raw files itself and compares against the PDF's own text at the displayed precision. The cell-by-cell log is `verification/pdf_raw_crosscheck.csv` in the [repository]({REPO}).

## Read this before using the numbers

- **{s('2026','year')} figures are UNOFFICIAL** until the Nov {s('23','date')}, {s('2026','year')} statewide canvass. Cochise and Coconino show their county canvass as official on the SOS site; the other counties are unofficial.
- **Registration share and vote share measure different things.** Unaffiliated and other-party voters, Republicans who voted for the Democratic candidate, turnout and candidate choice all move these numbers.
- **A change is not evidence of altered votes.**
"""+related('Arizona-County-PDF-Information'); pages['Arizona-County-PDF-Information']=pi
# ================= SIDEBAR
PAGE='_Sidebar'
sb=f"""**Arizona ΔG wiki**

{s('1','list ordinal')}. [Home](Home)
{s('2','list ordinal')}. [Bottom-Up Reverse Math](Reverse-Math)
{s('3','list ordinal')}. [Locked Arizona Formula](Locked-Arizona-Formula)
{s('4','list ordinal')}. [Floor and Ceiling Counties](Floor-and-Ceiling)
{s('5','list ordinal')}. [Graphs](Graphs)
{s('6','list ordinal')}. [Arizona County PDF Information](Arizona-County-PDF-Information)

Method origin: [Cedar County Audit (Nebraska)]({CEDAR})

*{s('2026','year')} UNOFFICIAL: {s('2026','year')} figures are unofficial until the Nov {s('23','date')}, {s('2026','year')} state canvass. Measures a pattern; no claim about intent, fraud or cause.*
"""
pages['_Sidebar']=sb

# ================= README (repo) — numbers go through the same manifest and are verified like wiki pages
PAGE='README'
import csv as _csv, hashlib as _h
FL=list(_csv.DictReader(open(W+'raw/fetch_log.csv')))
def sha(u): return [r['sha256'] for r in FL if r['url']==u][-1]
U22='https://apps.azsos.gov/election/2022/General/canvass/2022dec05_general_election_canvass_web.pdf'
U26='https://app.enhancedvoting.com/results/public/api/elections/Arizona/110326GeneralElection/data'
UR22='https://apps.azsos.gov/election/VoterReg/2022/State_Voter_Registration_2022_General.csv'; UR22P=UR22[:-3]+'pdf'
UR26='https://apps.azsos.gov/election/VoterReg/2026/State-Voter-Registration-November-2026.csv'; UR26P=UR26[:-3]+'pdf'
UC='https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/counties/totals/co-est2025-alldata.csv'
rd=banner()+f"""
# Arizona Election Analysis: {s('2022','year')} vs {s('2026','year')}\\* governor race, ΔG method

Method developed by Morissa Benson (CD3 Vice Chair, Nebraska GOP), from her [Cedar County Audit]({CEDAR}) on the [Nebraska Election Analysis wiki]({NEWIKI}). This repository applies the same arithmetic to all {v('k|n_counties','n')} Arizona counties. Read the [wiki]({REPO}/wiki) for the full write-up.

## Headline (statewide, pooled)

| Measure | {s('2022','year')} | {s('2026','year')}\\* | Change |
|---|---|---|---|
| S: Democratic governor votes ÷ total ballots | {T('S22','p2')} | {T('S26','p2')} | {T('dS','s2')} pts |
| P: Democratic share of active registration | {T('P22','p2')} | {T('P26','p2')} | {T('dP','s2')} pts |
| G = S − P | {T('G22','s2')} | {T('G26','s2')} | ΔG {T('dG','s2')} |

Locked Arizona formula: ΔG = {Fv('dG_on_drop','b','f2')} + {Fv('dG_on_drop','m','f2')} × (drop in Democratic registration share, points); R² {Fv('dG_on_drop','r2','f2')}, n = {Fv('dG_on_drop','n','n')}. Implied extra votes, summed over counties: {T('implied','sn')}.

## Files

- `{PDFNAME}`: the {v('k|n_counties','n')}-county PDF table ([raw download]({RAWB}{PDFNAME}))
- `AZ_*.png`: charts used on the Graphs wiki page
- `data/AZ_Governor_2022_2026_DeltaG_by_County.csv`, `data/AZ_results_summary.json`: county table and fitted equations
- `raw/`: every source file exactly as downloaded, with `raw/fetch_log.csv` (URL, time, HTTP status, bytes, SHA-{s('256','hash algorithm name')}) and `raw/SHA256SUMS`
- `scripts/`: pass A, pass B, comparison, analysis, PDF build, independent PDF checker, wiki build and wiki verifier
- `verification/`: pass A vs pass B figure-by-figure comparison, PDF cell-by-cell raw cross-check, wiki number cross-check, layout QA renders

## Sources (retrieved Nov {s('19','date')}, {s('2026','year')})

| Source | URL | SHA-{s('256','hash algorithm name')} |
|---|---|---|
| {s('2022','year')} official canvass (Dec {s('5','date')}, {s('2022','year')}) | {U22} | `{sha(U22)}` |
| {s('2026','year')}\\* results, statewide (UNOFFICIAL, data as of Nov {s('19','date')}, {s('2026','year')} {s('4:35','time')} PM CST) | {U26} | `{sha(U26)}` |
| {s('2026','year')}\\* results, one file per county | same API, county short names | see `raw/fetch_log.csv` |
| Registration, {s('2022','year')} General (CSV) | {UR22} | `{sha(UR22)}` |
| Registration, {s('2022','year')} General (PDF) | {UR22P} | `{sha(UR22P)}` |
| Registration, November {s('2026','year')} (CSV) | {UR26} | `{sha(UR26)}` |
| Registration, November {s('2026','year')} (PDF) | {UR26P} | `{sha(UR26P)}` |
| Census population estimates, Vintage {s('2025','census vintage year')} | {UC} | `{sha(UC)}` |

## Verification

Pass A and pass B compute every figure by independent code from different renderings of the raw files (canvass word positions vs plain text; results API JSON vs rendered results pages; registration CSV vs registration PDF). A third checker re-parses the raw files itself and recomputes every PDF cell against the PDF's own text. `verify_wiki.py` recomputes every number on every wiki page (and this README) from pass A and pass B separately. See `verification/`.

**{s('2026','year')} figures are UNOFFICIAL** until the Nov {s('23','date')}, {s('2026','year')} statewide canvass; re-run `scripts/run_all.sh` after it.
"""
open(W+'repo/README.md','w').write(rd)

for k,t in pages.items(): open(OUTD+k+'.md','w').write(t)
json.dump(MAN,open(V+'wiki_manifest.json','w'),indent=0,ensure_ascii=False)
print({k:len(t) for k,t in pages.items()}, len(MAN))
