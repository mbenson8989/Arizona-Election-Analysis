import pandas as pd, numpy as np, json, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
W='/workspace/az-clean/'; C=W+'charts/'
o=pd.read_pickle(W+'data/az_o.pkl'); J=json.load(open(W+'data/AZ_results_summary.json')); F=J['fits']; K=J['K']
NOTE='*2026 UNOFFICIAL (AZ SOS results site, data as of Nov 19, 2026 4:35 PM CST; statewide canvass Nov 23, 2026).\nGovernor race. Measures a pattern; no claim about intent, fraud or cause.'
plt.rcParams.update({'font.size':10,'figure.dpi':110})
def fin(fig,fn):
    fig.text(0.01,0.005,NOTE,fontsize=7,style='italic',ha='left',va='bottom'); fig.tight_layout(rect=(0,0.055,1,1)); fig.savefig(C+fn); plt.close(fig)
lab=[f"{c}\n{p/1000:,.0f}k" for c,p in zip(o.index,o.pop2025)]
x=np.arange(len(o))
# 1 ΔG by population
fig,ax=plt.subplots(figsize=(12,5.5)); col=['#c0392b' if c in K['ceiling'] else ('#2e86c1' if c in K['floor'] else '#7f8c8d') for c in o.index]
for c in o.index:
    if c in K['ceiling'] and c in K['floor']: col[list(o.index).index(c)]='#8e44ad'
b=ax.bar(x,o.dG,color=col); ax.bar_label(b,[f'+{v:.2f}' for v in o.dG],fontsize=8); ax.axhline(J['pooled']['dG'],ls='--',color='k',lw=1); ax.text(len(o)-0.5,J['pooled']['dG']+0.2,f"statewide pooled ΔG +{J['pooled']['dG']:.2f}",ha='right',fontsize=8)
ax.set_xticks(x,lab,fontsize=8); ax.set_ylabel('ΔG (points) = ΔS − ΔP'); ax.set_title(f"Arizona ΔG by county, largest to smallest population (2025 Census est.)\nceiling {K['ceiling_by_dG']} +{o.dG.max():.2f}, floor by ΔG {K['floor_by_dG']} +{o.dG.min():.2f}. Red = ceiling 5, blue = floor 5 (lowest 2022 P), purple = both")
fin(fig,'AZ_DeltaG_by_Population.png')
# 2 ΔG vs drop scatter with locked equation
f=F['dG_on_drop']; fig,ax=plt.subplots(figsize=(9,6.5)); ax.scatter(o.regdrop,o.dG,s=np.sqrt(o.ballots_2026)/3,alpha=.6,color='#2e86c1')
for c in o.index: ax.annotate(c,(o.regdrop[c],o.dG[c]),fontsize=8,xytext=(4,3),textcoords='offset points')
xx=np.linspace(0,o.regdrop.max()*1.05,50); ax.plot(xx,f['b']+f['m']*xx,'k-',lw=1.2)
ax.set_xlabel('Drop in Democratic share of active registration, 2022→2026* (points)'); ax.set_ylabel('ΔG (points)')
ax.set_title(f"Locked Arizona formula: ΔG = {f['b']:.2f} + {f['m']:.2f} × drop   (R² {f['r2']:.2f}, n=15)\nslope SE {f['m_se']:.2f}, intercept SE {f['b_se']:.2f}; bubble size ∝ √ballots 2026*")
fin(fig,'AZ_DeltaG_vs_RegShareDrop_Scatter.png')
# 3 slope chart G22->G26 (labels spread so none overlap)
def spread(vals,gap):
    idx=sorted(vals,key=lambda k:vals[k]); pos={}; last=-1e9
    for k in idx: pos[k]=max(vals[k],last+gap); last=pos[k]
    return pos
fig,ax=plt.subplots(figsize=(8,9)); L=spread(o.G22.to_dict(),0.62); R=spread(o.G26.to_dict(),0.62)
for c in o.index:
    cl='#c0392b' if c in K['ceiling'] else '#7f8c8d'
    ax.plot([0,1],[o.G22[c],o.G26[c]],'-o',color=cl,lw=1.2)
    ax.annotate(f'{c} {o.G22[c]:+.2f}',(0,o.G22[c]),xytext=(-0.04,L[c]),ha='right',va='center',fontsize=7.5,arrowprops=dict(arrowstyle='-',lw=.4,color='#999'))
    ax.annotate(f'{o.G26[c]:+.2f} {c}',(1,o.G26[c]),xytext=(1.04,R[c]),ha='left',va='center',fontsize=7.5,arrowprops=dict(arrowstyle='-',lw=.4,color='#999'))
ax.set_xlim(-0.6,1.6); ax.set_xticks([0,1],['G 2022','G 2026*']); ax.set_ylabel('G = S − P (points)'); ax.set_title('G rose in all 15 counties (red = five ceiling counties)\nG = Dem share of ballots − Dem share of active registration')
fin(fig,'AZ_Slope_G2022_to_G2026.png')
# 4 forward fits
fig,ax=plt.subplots(figsize=(9,6.5))
for t,cl,k in (('22','#2e86c1','G22_on_P22'),('26','#c0392b','G26_on_P26')):
    ax.scatter(o['P'+t],o['G'+t],color=cl,label=f"20{t}{'*' if t=='26' else ''}: G = {F[k]['b']:.2f} + {F[k]['m']:.3f}·P  (R² {F[k]['r2']:.2f})")
    xx=np.linspace(o['P'+t].min(),o['P'+t].max(),20); ax.plot(xx,F[k]['b']+F[k]['m']*xx,color=cl,lw=1)
    for c in o.index: ax.annotate(c,(o['P'+t][c],o['G'+t][c]),fontsize=7,color=cl,xytext=(3,2),textcoords='offset points')
ax.set_xlabel('P = Democratic share of active registration (%)'); ax.set_ylabel('G = S − P (points)'); ax.legend(fontsize=8); ax.set_title('Forward fit, G vs P, 2022 and 2026*')
fin(fig,'AZ_Forward_Fit_G_vs_P_2022_2026.png')
# 5 components
fig,ax=plt.subplots(figsize=(12,5.5)); w=.4
b1=ax.bar(x-w/2,o.dS,w,label='ΔS (Dem share of ballots)',color='#2e86c1'); b2=ax.bar(x+w/2,-o.dP,w,label='−ΔP (drop in Dem registration share)',color='#e67e22')
ax.bar_label(b1,[f'{v:+.2f}' for v in o.dS],fontsize=7); ax.bar_label(b2,[f'{v:.2f}' for v in -o.dP],fontsize=7)
ax.set_xticks(x,lab,fontsize=8); ax.set_ylabel('points'); ax.legend(); ax.set_title('ΔG = ΔS + (registration-share drop), by county, largest to smallest population')
fin(fig,'AZ_DeltaG_Components_dS_vs_dP_by_Population.png')
# 6 stacked share & registration
fig,ax=plt.subplots(figsize=(12,5.5))
ax.bar(x-w/2,o.S22,w,label='S 2022',color='#85c1e9'); ax.bar(x+w/2,o.S26,w,label='S 2026*',color='#1f618d')
ax.plot(x-w/2,o.P22,'_',ms=18,mew=2.5,color='#e67e22',label='P 2022'); ax.plot(x+w/2,o.P26,'_',ms=18,mew=2.5,color='#a04000',label='P 2026*')
ax.set_xticks(x,lab,fontsize=8); ax.set_ylabel('%'); ax.legend(ncol=4,fontsize=8); ax.set_title('Democratic share of ballots (bars) vs Democratic share of active registration (ticks), 2022 and 2026*')
fin(fig,'AZ_Share_and_Registration_by_Population.png')
# 7 residual and implied votes
fig,(a1,a2)=plt.subplots(2,1,figsize=(12,8),sharex=True)
r=o.residual.fillna(0); bb=a1.bar(x,r,color=['#bbb' if np.isnan(v) else '#8e44ad' for v in o.residual]); a1.bar_label(bb,['n/a (Dem reg rose)' if np.isnan(v) else f'{v:+.2f}' for v in o.residual],fontsize=7)
a1.set_ylabel('residual = ΔG − |ΔP| (pts)'); a1.set_title('Residual step (counties that lost Democratic registration) and implied extra votes')
bb=a2.bar(x,o.implied_extra_votes,color='#16a085'); a2.bar_label(bb,[f'{v:+,.0f}' for v in o.implied_extra_votes],fontsize=7); a2.set_yscale('log')
a2.set_ylabel('implied extra votes (log scale)'); a2.set_xticks(x,lab,fontsize=8)
fin(fig,'AZ_Residual_and_Implied_Votes_by_Population.png')
# 8 overballot
fig,ax=plt.subplots(figsize=(12,5.5))
for y,cl,dx in (('2022','#85c1e9',-w/2),('2026','#1f618d',w/2)):
    v=100*o[f'ballots_{y}']/o[f'regact_{y}']; bb=ax.bar(x+dx,v,w,color=cl,label=f'ballots ÷ active registration {y}{"*" if y=="2026" else ""}'); ax.bar_label(bb,[f'{q:.0f}' for q in v],fontsize=7)
ax.axhline(100,color='r',ls='--',lw=1); ax.set_ylim(0,110); ax.set_xticks(x,lab,fontsize=8); ax.legend(fontsize=8)
ax.set_title('Over-ballot check: no county had more ballots than active registrants or more governor votes than ballots, either year'); ax.set_ylabel('%')
fin(fig,'AZ_Overballot_Check_by_Population.png')
print('ok')
