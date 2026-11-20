"""Arizona governor 2022 vs 2026 ΔG analysis (Nebraska Cedar baseline method). Runs on the pass-A table only after
asserting compare_report CLEAN (pass A == pass B on every figure)."""
import pandas as pd, numpy as np, json, statsmodels.api as sm, statsmodels.formula.api as smf
from scipy import stats
W='/workspace/az-clean/'; V=W+'verification/'; D=W+'data/'
rep=json.load(open(V+'compare_report.json')); assert rep['CLEAN']
o=pd.read_csv(V+'passA_counties.csv',index_col='county'); N=len(o); assert N==15
c=pd.read_csv(W+'raw/census/co-est2025-alldata.csv',encoding='latin-1',dtype={'STATE':str,'COUNTY':str,'SUMLEV':str})
c=c[(c.SUMLEV=='050')&(c.STATE=='04')]; c.index=c.CTYNAME.str.replace(' County','')
o['pop2025']=c.POPESTIMATE2025.reindex(o.index); assert o.pop2025.notna().all()
o=o.sort_values('pop2025',ascending=False)
o['loss']=o.regdem_2026<o.regdem_2022
o['regdrop']=-o.dP   # registration-share drop, points (positive = fell)
def fit(y,x,w=None):
    X=sm.add_constant(np.asarray(x,float)); r=(sm.WLS(np.asarray(y,float),X,weights=w) if w is not None else sm.OLS(np.asarray(y,float),X)).fit()
    ci=r.conf_int(); res=np.asarray(y)-r.fittedvalues
    return dict(n=int(len(y)),b=float(r.params[0]),b_se=float(r.bse[0]),b_ci=[float(ci[0,0]),float(ci[0,1])],m=float(r.params[1]),m_se=float(r.bse[1]),m_ci=[float(ci[1,0]),float(ci[1,1])],
                m_p=float(r.pvalues[1]),r2=float(r.rsquared),resid_se=float(np.sqrt(np.sum(res**2)/(len(y)-2)))),r
F={}
F['dG_on_drop'],rD=fit(o.dG,o.regdrop)                         # LOCKED statewide equation: ΔG = b + m × drop (points)
F['dG_on_drop_wtd'],_=fit(o.dG,o.regdrop,o.ballots_2026)
F['G22_on_P22'],r22=fit(o.G22,o.P22); F['G26_on_P26'],r26=fit(o.G26,o.P26)   # forward fits, P in points
F['G22_on_P22_wtd'],_=fit(o.G22,o.P22,o.ballots_2022); F['G26_on_P26_wtd'],_=fit(o.G26,o.P26,o.ballots_2026)
L=pd.DataFrame(dict(G=np.r_[o.G22,o.G26],P=np.r_[o.P22,o.P26],yr=np.r_[np.zeros(N),np.ones(N)]))
ri=smf.ols('G~P*yr',L).fit(); F['year_interaction']=dict(d_intercept=float(ri.params['yr']),p_d_intercept=float(ri.pvalues['yr']),d_slope=float(ri.params['P:yr']),p_d_slope=float(ri.pvalues['P:yr']))
o['fit_dG']=np.asarray(rD.fittedvalues); o['res_dG']=o.dG-o.fit_dG
o['fit22']=np.asarray(r22.fittedvalues); o['res22']=o.G22-o.fit22; o['fit26']=np.asarray(r26.fittedvalues); o['res26']=o.G26-o.fit26
# influence / narrowed fit
inf=rD.get_influence(); cut=4/N
NAR=pd.DataFrame(dict(cooks=inf.cooks_distance[0],stud=inf.resid_studentized_external),index=o.index)
flag=NAR.index[(NAR.cooks>cut)|(NAR.stud.abs()>2.5)].tolist()
k=o.drop(index=flag); F['dG_on_drop_narrowed'],_=fit(k.dG,k.regdrop)
NARROW=dict(rule=f"Cook's distance > 4/n ({cut:.3f}) or |externally studentized residual| > 2.5 in the ΔG-on-drop fit",counties=flag,detail=NAR.loc[flag].round(4).to_dict('index'))
# floor / ceiling (Nevada/Nebraska definitions)
FLOOR=o.sort_values('P22').head(5).index.tolist(); CEIL=o.sort_values('dG',ascending=False).head(5).index.tolist()
lr=stats.linregress(np.log10(o.pop2025),o.dG); lrS=stats.linregress(np.log10(o.pop2025),o.dS); lrP=stats.linregress(np.log10(o.pop2025),o.dP)
sp=stats.spearmanr(o.pop2025,o.dG)
K=dict(floor_rule='five lowest 2022 Democratic active-registration share P2022',floor=FLOOR,ceiling_rule='five largest ΔG',ceiling=CEIL,
       floor_by_dG=o.dG.idxmin(),ceiling_by_dG=o.dG.idxmax(),lowest5_dG=o.sort_values('dG').head(5).index.tolist(),lowest5_S22=o.sort_values('S22').head(5).index.tolist(),
       mean_dG=float(o.dG.mean()),median_dG=float(o.dG.median()),sd_dG=float(o.dG.std()),n_pos=int((o.dG>0).sum()),n_P_fell=int((o.dP<0).sum()),n_S_rose=int((o.dS>0).sum()),
       n_loss=int(o.loss.sum()),loss_counties=o.index[o.loss].tolist(),nonloss_counties=o.index[~o.loss].tolist(),
       n_dem_votes_rose=int((o.dem_chg>0).sum()),
       size_log10pop_dG=dict(slope=float(lr.slope),r=float(lr.rvalue),p=float(lr.pvalue)),size_dS=dict(r=float(lrS.rvalue),p=float(lrS.pvalue)),size_dP=dict(r=float(lrP.rvalue),p=float(lrP.pvalue)),
       spearman_pop_dG=dict(rho=float(sp.statistic),p=float(sp.pvalue)),median_residual=float(o.residual.median()))
T=o.sum(numeric_only=True)
PO=dict(S22=100*T.dem_2022/T.ballots_2022,S26=100*T.dem_2026/T.ballots_2026,P22=100*T.regdem_2022/T.regact_2022,P26=100*T.regdem_2026/T.regact_2026)
PO.update(G22=PO['S22']-PO['P22'],G26=PO['S26']-PO['P26']); PO['dS']=PO['S26']-PO['S22']; PO['dP']=PO['P26']-PO['P22']; PO['dG']=PO['G26']-PO['G22']
PO['residual_pooled']=PO['dG']-abs(PO['dP']); PO['implied_extra_sum']=float(o.implied_extra_votes.sum()); PO['implied_extra_pooled']=PO['dS']/100*T.ballots_2026
PO['implied_extra_sum_loss']=float(o.implied_extra_votes[o.loss].sum()); PO['implied_extra_maricopa']=float(o.loc['Maricopa','implied_extra_votes'])
PO['gap_reg_scaled_sum']=float(o.gap_reg_scaled.sum()); PO['dG_from_equation_at_pooled_drop']=F['dG_on_drop']['b']+F['dG_on_drop']['m']*(-PO['dP'])
PO['totals']={k_:int(T[k_]) for k_ in ['ballots_2022','dem_2022','rep_2022','govtotal_2022','regdem_2022','regact_2022','ballots_2026','dem_2026','rep_2026','govtotal_2026','regdem_2026','regact_2026']}
TX={}
for y in ('2022','2026'):
    m1=o[f'ballots_{y}']-o[f'govtotal_{y}']
    TX[y]=dict(gov_gt_ballots=o.index[m1<0].tolist(),ballots_gt_active_reg=o.index[o[f'ballots_{y}']>o[f'regact_{y}']].tolist(),
               min_ballots_minus_gov=dict(county=m1.idxmin(),votes=int(m1.min())),nogov_pct_range=[float((100*m1/o[f'ballots_{y}']).min()),float((100*m1/o[f'ballots_{y}']).max())],
               max_turnout_active=dict(county=(o[f'ballots_{y}']/o[f'regact_{y}']).idxmax(),pct=float(100*(o[f'ballots_{y}']/o[f'regact_{y}']).max())),
               statewide_turnout_active=float(100*T[f'ballots_{y}']/T[f'regact_{y}']))
o['flag']=''
for c_ in FLOOR: o.loc[c_,'flag']='floor'
for c_ in CEIL: o.loc[c_,'flag']=(o.loc[c_,'flag']+'; ' if o.loc[c_,'flag'] else '')+'ceiling'
for c_ in flag: o.loc[c_,'flag']=(o.loc[c_,'flag']+'; ' if o.loc[c_,'flag'] else '')+'narrowed-out'
o.to_pickle('/workspace/az-clean/data/az_o.pkl')
out=o.copy(); out.insert(0,'status_2026','2026 UNOFFICIAL (SOS results site, data as of 2026-11-19 4:35 PM CST); statewide canvass scheduled 2026-11-23')
out.round(6).to_csv(D+'AZ_Governor_2022_2026_DeltaG_by_County.csv')
J=dict(fits=F,narrow=NARROW,K=K,pooled=PO,overballot=TX)
json.dump(J,open(D+'AZ_results_summary.json','w'),indent=1,default=lambda x: x.item() if hasattr(x,'item') else str(x))
print(json.dumps(J,indent=0,default=lambda x: x.item() if hasattr(x,'item') else str(x))[:6000])
print(o[['pop2025','P22','S22','G22','P26','S26','G26','dS','dP','dG','loss','residual','implied_extra_votes','gap_reg_scaled','flag']].round(2).to_string())
