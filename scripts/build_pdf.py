"""Build Arizona_15_County_Democratic_Registration_and_Vote_Change.pdf (layout modeled on the Nebraska 93-county PDF).
Values come from the pass-A table, only after compare_report.json is CLEAN (pass A == pass B on every figure)."""
import json, pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
W='/workspace/az-clean/'; V=W+'verification/'
assert json.load(open(V+'compare_report.json'))['CLEAN']
FD='/usr/share/fonts/truetype/sand-box/google/Carlito/'
pdfmetrics.registerFont(TTFont('Carlito',FD+'Carlito-Regular.ttf')); pdfmetrics.registerFont(TTFont('Carlito-Bold',FD+'Carlito-Bold.ttf')); pdfmetrics.registerFont(TTFont('Carlito-Italic',FD+'Carlito-Italic.ttf'))
d=pd.read_csv(V+'passA_counties.csv',index_col='county')
d=d.sort_values('P26',ascending=False)
T=d[['regdem_2022','regdem_2026','dem_2022','dem_2026','ballots_2022','ballots_2026','regact_2022','regact_2026']].sum()
def r(x,nd): return Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-nd),rounding=ROUND_HALF_UP)
def pct(x,nd=1,sign=False):
    q=r(x,nd); s=f'{q:.{nd}f}%'; return ('+'+s if q>0 and sign else s)
def n(x,sign=False):
    x=int(x); s=f'{abs(x):,}'; return ('-'+s if x<0 else ('+'+s if sign and x>0 else s))
def pts(x): q=r(x,2); return ('+' if q>0 else '')+f'{q:.2f}'
ASOF='Nov 19, 2026, 4:35 PM CST'
UNOFF=f'*2026 figures are UNOFFICIAL and not certified: Arizona Secretary of State (SOS) results site (results.arizona.vote / app.enhancedvoting.com), data as of {ASOF}. The statewide canvass is scheduled for Nov 23, 2026; figures may change.'
SRC=('2022 votes and ballots: SOS 2022 General Election Official Canvass (Dec 5, 2022). Registration: SOS State Voter Registration reports, ACTIVE voters, '
     '"G.E." (general election) row: 2022 General Election report and November 2026 report. Votes are votes for the Democratic governor candidate '
     '(Katie Hobbs in both years), not a count of registered Democrats who voted.')
S=lambda name,**k: ParagraphStyle(name,fontName=k.pop('f','Carlito'),fontSize=k.pop('s',8),leading=k.pop('l',10),**k)
title=S('t',f='Carlito-Bold',s=14,l=17); sub=S('s',f='Carlito-Italic',s=8.5,l=10.5); disc=S('d',f='Carlito-Italic',s=8,l=10)
banner=S('b',f='Carlito-Bold',s=9,l=11,textColor=colors.HexColor('#8a1c1c'))
NAVY=colors.HexColor('#1f2d4d'); BLUE=colors.HexColor('#dbe9f6'); PEACH=colors.HexColor('#fbe3d6')
rose=d.index[d.regdem_2026>d.regdem_2022].tolist(); fell=d.index[d.dem_2026<d.dem_2022].tolist()
def footer(c,doc):
    c.saveState(); c.setFont('Carlito-Italic',8)
    c.drawString(36,24,'*2026 figures UNOFFICIAL, not SOS-certified (data as of '+ASOF+'; statewide canvass Nov 23, 2026)')
    c.drawRightString(792-36,24,f'Page {doc.page} of 3'); c.restoreState()
def head(story,t,s):
    story+= [Paragraph(t,title),Spacer(1,3),Paragraph(s,sub),Spacer(1,4),Paragraph('2026 UNOFFICIAL — not certified by the Arizona Secretary of State',banner),Spacer(1,3),Paragraph(UNOFF+' '+SRC,disc),Spacer(1,6)]
hs=S('h',f='Carlito-Bold',s=8,l=9.5,textColor=colors.white,alignment=1)
def tbl(hdr,rows,widths,shade):
    data=[[Paragraph(h,hs) for h in hdr]]+rows
    t=Table(data,colWidths=widths,repeatRows=1)
    st=[('FONT',(0,1),(-1,-1),'Carlito',8.5),('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,0),'MIDDLE'),('ALIGN',(1,1),(-1,-1),'RIGHT'),
        ('GRID',(0,0),(-1,-1),0.25,colors.HexColor('#c8c8c8')),('FONT',(0,-1),(-1,-1),'Carlito-Bold',8.5),('LINEABOVE',(0,-1),(-1,-1),1,colors.black),
        ('TOPPADDING',(0,1),(-1,-1),2.5),('BOTTOMPADDING',(0,1),(-1,-1),2.5)]
    for i,c in enumerate(d.index,1):
        if c in shade.get('blue',[]): st.append(('BACKGROUND',(0,i),(-1,i),BLUE))
        if c in shade.get('peach',[]): st.append(('BACKGROUND',(0,i),(-1,i),PEACH))
    t.setStyle(TableStyle(st)); return t
story=[]
sortline=('Sorted by 2026 Democratic share of registration (Democratic active registered voters ÷ all active registered voters, SOS November 2026 report, G.E. row), highest first. '
          f'{d.index[0]} leads by share; {d.regdem_2026.idxmax()} leads by raw Democratic registration.')
head(story,'Arizona 15 Counties — Democratic Registration, Democratic Governor Votes and Total Ballots, 2022 vs 2026*',sortline)
leg=Table([['Legend:',f"Democratic registration rose ({', '.join(rose)})",f"Democratic governor votes fell ({', '.join(fell)})"]],colWidths=[50,260,260])
leg.setStyle(TableStyle([('FONT',(0,0),(0,0),'Carlito-Bold',8),('FONT',(1,0),(-1,0),'Carlito',8),('BACKGROUND',(1,0),(1,0),BLUE),('BACKGROUND',(2,0),(2,0),PEACH)]))
story+=[leg,Spacer(1,6)]
H1=['County','Dem Reg Share 2026 %','Dem Reg 2022 (G.E.)','Dem Reg 2026 (G.E.)','Reg Change #','Reg Change %','Dem Gov Votes 2022','Dem Gov Votes 2026*','Vote Change #','Vote Change % (on 2022 base)','Total Ballots 2022','Total Ballots 2026*','Ballot Change #','Ballot Change %']
rows=[]
def row1(name,x):
    return [name,pct(100*x.regdem_2026/x.regact_2026),n(x.regdem_2022),n(x.regdem_2026),n(x.regdem_2026-x.regdem_2022,True),pct(100*(x.regdem_2026-x.regdem_2022)/x.regdem_2022,1,True),
            n(x.dem_2022),n(x.dem_2026),n(x.dem_2026-x.dem_2022,True),pct(100*(x.dem_2026-x.dem_2022)/x.dem_2022,1,True),n(x.ballots_2022),n(x.ballots_2026),n(x.ballots_2026-x.ballots_2022,True),pct(100*(x.ballots_2026-x.ballots_2022)/x.ballots_2022,1,True)]
for c,x in d.iterrows(): rows.append(row1(c,x))
rows.append(row1('Statewide total',T))
story.append(tbl(H1,rows,[70]+[52.3]*13,{'blue':rose,'peach':fell}))
story.append(PageBreak())
head(story,'Democratic Governor Votes as a Share of Total Ballots, and Democratic Share of Registration, 2022 vs 2026*',sortline+
     ' Share of ballots = Democratic governor votes ÷ total ballots cast. Share of registration = Democratic active registered voters ÷ all active registered voters. Change (pts) = 2026 share minus 2022 share, in percentage points.')
H2=['County','Dem Share of Ballots 2022 %','Dem Share of Ballots 2026* %','Change (pts)','Dem Share of Registration 2022 %','Total Active Registered 2022 (G.E.)','Dem Share of Registration 2026 %','Total Active Registered 2026 (G.E.)','Registration Share Change (pts)']
def row2(name,x):
    s22=100*x.dem_2022/x.ballots_2022; s26=100*x.dem_2026/x.ballots_2026; p22=100*x.regdem_2022/x.regact_2022; p26=100*x.regdem_2026/x.regact_2026
    return [name,pct(s22),pct(s26),pts(s26-s22),pct(p22),n(x.regact_2022),pct(p26),n(x.regact_2026),pts(p26-p22)]
rows2=[row2(c,x) for c,x in d.iterrows()]+[row2('Statewide total',T)]
story.append(tbl(H2,rows2,[90]+[80]*8,{}))
story.append(PageBreak())
head(story,'Notes, Sources and Column Definitions','Arizona 15-county summary, governor race, 2022 vs 2026*.')
B=S('n',s=9,l=12); BB=S('nb',f='Carlito-Bold',s=10,l=13)
notes=[('Columns',None),
 (None,'<b>Dem Reg Share 2026 %</b>: Democratic active registered voters ÷ all active registered voters, SOS November 2026 report, G.E. 2026 row. The table is sorted on this column, highest first.'),
 (None,'<b>Dem Reg 2022 / 2026</b>: Democratic ACTIVE registered voters in the G.E. (general election) row of the SOS State Voter Registration report for each year. <b>Reg Change #</b> = 2026 minus 2022; <b>Reg Change %</b> = that change ÷ the 2022 figure.'),
 (None,'<b>Dem Gov Votes 2022 / 2026*</b>: votes for the Democratic candidate for governor (Katie Hobbs both years; 2026 ticket Hobbs / Giles). <b>Vote Change</b> # and % as above, on the 2022 base.'),
 (None,'<b>Total Ballots 2022 / 2026*</b>: total ballots cast in the county (2022: canvass "Total Ballots Cast" row; 2026*: "Ballots Cast" on the SOS results site). <b>Ballot Change</b> # and % as above.'),
 (None,'<b>Dem Share of Ballots</b> (page 2) = Democratic governor votes ÷ total ballots cast; this is S in the ΔG method. <b>Dem Share of Registration</b> = P. <b>Change (pts)</b> = 2026 minus 2022, in percentage points.'),
 (None,f'<b>Shading</b>: blue = Democratic active registration rose ({", ".join(rose)}); peach = Democratic governor votes fell ({", ".join(fell)}).'),
 (None,'<b>Statewide total</b> row: the sum of the 15 counties; shares in that row are computed from those sums. 2022 sums equal the SOS canvass TOTAL column and the registration report Totals row; 2026* sums equal the SOS statewide governor totals.'),
 ('Sources (all retrieved Nov 19, 2026)',None),
 (None,'2022 Official Canvass: apps.azsos.gov/election/2022/General/canvass/2022dec05_general_election_canvass_web.pdf (Report Date 12/5/2022).'),
 (None,'2026* results: app.enhancedvoting.com/results/public/api/elections/{county}/110326GeneralElection/data (the SOS results site linked from results.arizona.vote), marked "UNOFFICIAL RESULTS", data as of '+ASOF+'. Cochise and Coconino county pages show their county canvass as official; the statewide result is not certified.'),
 (None,'Registration: apps.azsos.gov/election/VoterReg/2022/State_Voter_Registration_2022_General (CSV and PDF) and apps.azsos.gov/election/VoterReg/2026/State-Voter-Registration-November-2026 (CSV and PDF), ACTIVE voters.'),
 ('Verification',None),
 (None,'Every figure was computed twice by independent code (pass A: canvass word positions, results API JSON, registration CSVs; pass B: canvass plain text, rendered results pages, registration PDFs), and every cell of this PDF was recomputed a third time directly from the raw files and compared with the printed text at the displayed precision.'),
 ('Read this before using the numbers',None),
 (None,'These tables measure a pattern; they make no claim about intent, fraud or cause. Registration share and vote share measure different things: unaffiliated and other-party voters, Republicans who voted for the Democratic candidate, turnout and candidate choice all move these numbers. 2026* figures are unofficial and may change at the Nov 23, 2026 statewide canvass.'),
 (None,'Method: the ΔG method from the Cedar County Audit on the Nebraska Election Analysis wiki (github.com/mbenson8989/Nebraska-Election-Analysis-/wiki/Cedar-Audit).')]
for h,t in notes:
    story.append(Paragraph(h,BB) if h else Paragraph(t,B)); story.append(Spacer(1,3))
out=W+'pdf/Arizona_15_County_Democratic_Registration_and_Vote_Change.pdf'
doc=SimpleDocTemplate(out,pagesize=landscape(letter),leftMargin=36,rightMargin=36,topMargin=30,bottomMargin=40,title='Arizona 15 Counties — Democratic Registration and Vote Change, 2022 vs 2026*',author='Arizona Election Analysis')
doc.build(story,onFirstPage=footer,onLaterPages=footer); print(out)
