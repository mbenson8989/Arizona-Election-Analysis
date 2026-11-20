"""Pass-B source for 2026: render each county's public results page (app.enhancedvoting.com, the SOS results site that
results.arizona.vote links to) in headed Chrome and save the visible page text (innerText) + screenshot. Pass B parses
these texts; it never reads the JSON API files."""
import os, json, hashlib, datetime, sys
from playwright.sync_api import sync_playwright
OUT='/workspace/az-clean/raw/2026/rendered'
names=sys.argv[1:]
log=[]
with sync_playwright() as p:
    br=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=False,args=['--no-sandbox','--disable-blink-features=AutomationControlled'],ignore_default_args=['--enable-automation'])
    pg=br.new_context(viewport={'width':1400,'height':1200}).new_page()
    for n in names:
        url=f'https://app.enhancedvoting.com/results/public/{n}/elections/110326GeneralElection'
        pg.goto(url,wait_until='networkidle',timeout=120000); pg.wait_for_timeout(6000)
        txt=pg.evaluate('document.body.innerText')
        fn=os.path.join(OUT,n+'.txt'); open(fn,'w').write(txt)
        pg.screenshot(path=os.path.join(OUT,n+'.png'),full_page=False)
        b=txt.encode(); log.append(dict(url=url,file=fn,rendered_at=datetime.datetime.now().astimezone().isoformat(timespec='seconds'),chars=len(txt),sha256=hashlib.sha256(b).hexdigest()))
        print(n,len(txt)); pg.wait_for_timeout(3000)
    br.close()
lp=os.path.join(OUT,'render_log.json'); old=json.load(open(lp)) if os.path.exists(lp) else []
json.dump(old+log,open(lp,'w'),indent=1)
