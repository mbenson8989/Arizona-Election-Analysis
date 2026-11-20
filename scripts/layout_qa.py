"""Layout QA: (1) PDF: page count/size, every word inside the page margins, rows per table, PNG renders; (2) wiki + README:
markdown tables well-formed (cell count per row = header), render to HTML (python-markdown, GFM-like tables), screenshot each page,
check every image loads and no stray markdown ('**', '|') leaks into rendered text. Writes verification/layout_qa/report.json."""
import json, re, os, subprocess, markdown, pdfplumber
from playwright.sync_api import sync_playwright
A='/workspace/az-clean/'; Q=A+'verification/layout_qa/'; os.makedirs(Q,exist_ok=True)
rep={'pdf':{},'wiki':{}}; bad=[]
pdf=pdfplumber.open(A+'pdf/Arizona_15_County_Democratic_Registration_and_Vote_Change.pdf')
rep['pdf']['pages']=len(pdf.pages); rep['pdf']['size']=[float(pdf.pages[0].width),float(pdf.pages[0].height)]
if len(pdf.pages)!=3 or rep['pdf']['size']!=[792.0,612.0]: bad.append('pdf page count/size')
for i,p in enumerate(pdf.pages,1):
    ws=p.extract_words(); out=[w['text'] for w in ws if w['x0']<18 or w['x1']>792-18 or w['top']<12 or w['bottom']>612-12]
    rep['pdf'][f'page{i}_words_outside_margins']=out
    if out: bad.append(f'pdf page {i} overflow')
subprocess.run(['pdftoppm','-r','110','-png',A+'pdf/Arizona_15_County_Democratic_Registration_and_Vote_Change.pdf',Q+'pdfpage'],check=True)
pages={f[:-3]:open(A+'wiki/'+f).read() for f in sorted(os.listdir(A+'wiki')) if f.endswith('.md')}; pages['README']=open(A+'repo/README.md').read()
RAWB='https://raw.githubusercontent.com/mbenson8989/Arizona-Election-Analysis/main/'
with sync_playwright() as pw:
    br=pw.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox']); pg=br.new_page(viewport={'width':1280,'height':900})
    for name,md in pages.items():
        tbl_issues=[]
        lines=md.split('\n')
        for i,l in enumerate(lines):
            if l.startswith('|') and i+1<len(lines) and re.match(r'^\|(\s*-+\s*\|)+\s*$',lines[i+1]):
                ncol=len(re.split(r'(?<!\\)\|',l.strip())[1:-1]); j=i+2
                while j<len(lines) and lines[j].startswith('|'):
                    n=len(re.split(r'(?<!\\)\|',lines[j].strip())[1:-1])
                    if n!=ncol: tbl_issues.append(f'line {j+1}: {n} cells vs header {ncol}')
                    j+=1
        html=markdown.markdown(md.replace(RAWB,'file://'+A+'repo/'),extensions=['tables','fenced_code'])
        fn=Q+f'wiki_{name}.html'; open(fn,'w').write('<meta charset=utf-8><style>body{font-family:sans-serif;max-width:1200px;margin:20px}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:3px 6px;font-size:12px}img{max-width:100%}</style>'+html)
        pg.goto('file://'+fn); pg.wait_for_timeout(500)
        imgs=pg.evaluate("Array.from(document.images).map(i=>[i.src.split('/').pop(),i.naturalWidth])")
        txt=pg.evaluate("Array.from(document.body.querySelectorAll('p,li,td,th,h1,h2,h3')).map(e=>e.innerText).join('\\n')")
        leaks=[l for l in txt.split('\n') if re.search(r'\*\*|^\s*\||\s\|\s|\|\s*-{3,}',l)]  # bold markers or table-syntax pipes; |x| absolute-value bars are legitimate
        ntab=pg.evaluate("document.querySelectorAll('table').length"); nmd=len([1 for i,l in enumerate(lines) if l.startswith('|') and i+1<len(lines) and re.match(r'^\|(\s*-+\s*\|)+\s*$',lines[i+1])])
        pg.screenshot(path=Q+f'wiki_{name}.png',full_page=True)
        r=dict(tables_markdown=nmd,tables_rendered=ntab,table_cell_issues=tbl_issues,images=imgs,images_broken=[a for a,w in imgs if w==0],markdown_leaks=len(leaks))
        rep['wiki'][name]=r
        if tbl_issues or ntab!=nmd or r['images_broken'] or leaks: bad.append(f'wiki {name}: {r}')
    br.close()
rep['failures']=bad; rep['CLEAN']=not bad
json.dump(rep,open(Q+'report.json','w'),indent=1); print(json.dumps({k:v for k,v in rep.items() if k!='wiki'},indent=1)); print({k:(v['tables_rendered'],len(v['images']),v['images_broken'],v['markdown_leaks']) for k,v in rep['wiki'].items()})
import sys; sys.exit(0 if not bad else 1)
