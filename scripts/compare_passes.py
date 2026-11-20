"""Compare pass A vs pass B figure by figure (every county, every raw input and derived figure) + statewide totals vs SOS published totals."""
import pandas as pd, json, csv, math, re
V='/workspace/az-clean/verification/'; RAW='/workspace/az-clean/raw/'
A=pd.read_csv(V+'passA_counties.csv',index_col='county'); B=pd.read_csv(V+'passB_counties.csv',index_col='county')
INT=['ballots_2022','dem_2022','rep_2022','govtotal_2022','regdem_2022','regrep_2022','regact_2022','ballots_2026','dem_2026','rep_2026','govtotal_2026','regdem_2026','regrep_2026','regact_2026','regdem_chg','dem_chg','ballots_chg']
FLT=['S22','S26','P22','P26','G22','G26','dS','dP','dG','residual','implied_extra_votes','gap_reg_scaled','regdem_chg_pct','dem_chg_pct','ballots_chg_pct']
rows=[]; bad=[]
for c in A.index:
    for k in INT+FLT:
        a,b=A.loc[c,k],B.loc[c,k]
        if k in INT: ok=int(a)==int(b); disp=(f'{int(a):,}',f'{int(b):,}')
        else:
            if (pd.isna(a) or a=='None') and (pd.isna(b) or b=='None'): ok=True; disp=('n/a','n/a')
            else:
                a,b=float(a),float(b); ok=abs(a-b)<1e-9 and f'{a:.2f}'==f'{b:.2f}' and f'{a:.1f}'==f'{b:.1f}' and f'{a:.0f}'==f'{b:.0f}'; disp=(f'{a:.6f}',f'{b:.6f}')
        rows.append([c,k,disp[0],disp[1],'MATCH' if ok else 'MISMATCH']);
        if not ok: bad.append((c,k,disp))
# extra independent cross-sources
SA=json.load(open(V+'passA_statewide.json')); SB=json.load(open(V+'passB_statewide.json'))
ext=[]
def chk(name,x,y):
    ok=(x==y) if not isinstance(x,float) else abs(x-y)<1e-9
    ext.append([name,x,y,'MATCH' if ok else 'MISMATCH'])
    if not ok: bad.append(('statewide',name,(x,y)))
s22=SA['sos2022']; b22=SB['sos2022_total_column']
for k in ('ballots','dem','rep','govtotal'):
    chk(f'2022 canvass TOTAL column {k}: passA word-position vs passB text',s22[k],b22[k])
    chk(f'2022 sum of 15 counties {k} (passA) vs canvass TOTAL column',SA['sums'][k+'_2022'],s22[k])
chk('2022 canvass Total Eligible Registration (passA) vs registration report G.E. Total (CSV)',s22['canvass_reg'],SA['reg2022_total']['Total'])
for c in A.index: chk(f'2022 {c} canvass registration vs CSV active total',int(A.loc[c,'canvass_reg_2022']),int(A.loc[c,'regact_2022']))
for y,kA,kB in (('2022','reg2022_total','g22'),('2026','reg2026_total','g26')):
    chk(f'{y} registration TOTAL row: CSV vs PDF',SA[kA],SB['sos_registration_totals'][kB])
    chk(f'{y} registration Dem: sum of counties vs SOS Totals row',SA['sums'][f'regdem_{y}'],SA[kA]['Democratic'])
    chk(f'{y} registration Active total: sum of counties vs SOS Totals row',SA['sums'][f'regact_{y}'],SA[kA]['Total'])
s26=SA['sos2026']
chk('2026 statewide Hobbs (API statewide) vs sum of 15 county API files',s26['dem'],SA['sums']['dem_2026'])
chk('2026 statewide Biggs (API statewide) vs sum of counties',s26['rep'],SA['sums']['rep_2026'])
chk('2026 statewide governor voteTotal vs sum of counties',s26['govtotal'],SA['sums']['govtotal_2026'])
chk('2026 statewide ballots: API localityElections sum vs county files sum',s26['ballots_sum_localities'],SA['sums']['ballots_2026'])
for c in A.index: chk(f'2026 {c} API registered (totalVoters) vs SOS Nov 2026 active GE total',int(A.loc[c,'api_reg_total_2026']),int(A.loc[c,'regact_2026']))
# rendered statewide page governor block
t=open(RAW+'2026/rendered/Arizona.txt').read().split('\n'); g=t.index('Governor and Lieutenant Governor')
seg=t[g:g+80]; hv=int(seg[seg.index('Votes',seg.index('Katie Hobbs (DEM) / John Giles (PND)'))+1].replace(',',''))
chk('2026 statewide Hobbs: rendered state page vs API',hv,s26['dem'])
# published percentages in SOS registration report (2 dp) vs our P at 2dp
P22=100*SA['reg2022_total']['Democratic']/SA['reg2022_total']['Total']; P26=100*SA['reg2026_total']['Democratic']/SA['reg2026_total']['Total']
chk('2022 statewide P (2dp) vs SOS printed Percentages 30.66',f'{P22:.2f}','30.66'); chk('2026 statewide P (2dp) vs SOS printed Percentages 28.33',f'{P26:.2f}','28.33')
# statewide derived A vs B
for k,v in SA['statewide_derived'].items():
    chk(f'statewide derived {k}: A vs B',float(v),float(SB['statewide'][k]))
with open(V+'compare_A_B_figure_by_figure.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['county','figure','passA','passB','result']); w.writerows(rows)
with open(V+'statewide_crosschecks.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['check','value_1','value_2','result']); w.writerows(ext)
rep=dict(county_figures_total=len(rows),county_figures_matched=sum(r[4]=='MATCH' for r in rows),statewide_checks_total=len(ext),statewide_checks_matched=sum(r[3]=='MATCH' for r in ext),mismatches=[str(b) for b in bad],CLEAN=not bad)
json.dump(rep,open(V+'compare_report.json','w'),indent=1); print(json.dumps(rep,indent=1))
