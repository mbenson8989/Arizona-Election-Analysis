"""Load the SOS results page in headed Chrome and record every JSON/XHR response (URL + body) to discover the public API."""
import sys, os, json, hashlib, datetime, re
from playwright.sync_api import sync_playwright
url, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
seen=[]
with sync_playwright() as p:
    br=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=False,args=['--no-sandbox','--disable-blink-features=AutomationControlled'],ignore_default_args=['--enable-automation'])
    pg=br.new_context(viewport={'width':1400,'height':1000}).new_page()
    def on(r):
        ct=r.headers.get('content-type','')
        if 'json' in ct or r.request.resource_type in ('xhr','fetch') or ('results.arizona.vote/app/' in r.url and r.url.split('?')[0].endswith(('.js','.html'))):
            try: b=r.body()
            except Exception: b=b''
            seen.append(dict(url=r.url,status=r.status,ct=ct,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),t=datetime.datetime.now().astimezone().isoformat(timespec='seconds')))
            fn=re.sub(r'[^A-Za-z0-9._-]','_',r.url.split('://')[-1])[-140:]
            open(os.path.join(out,fn),'wb').write(b)
    pg.on('response',on)
    pg.goto(url,wait_until='load',timeout=90000); pg.wait_for_timeout(15000)
    open(os.path.join(out,'page.html'),'w').write(pg.content()); pg.screenshot(path=os.path.join(out,'page.png'),full_page=True)
    print(pg.title(), pg.url)
    br.close()
json.dump(seen,open(os.path.join(out,'sniff_log.json'),'w'),indent=1)
for s in seen: print(s['status'],s['bytes'],s['url'][:200])
