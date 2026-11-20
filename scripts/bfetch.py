"""Fetch public AZ SOS URLs via a real (headed) Chrome page, since azsos.gov sits behind a Cloudflare JS challenge that rejects curl.
Usage: bfetch.py ORIGIN_PAGE OUTDIR url1 [url2 ...]. Each body is saved byte-for-byte; appends to raw/fetch_log.csv (url, file, time, status, bytes, sha256)."""
import sys, os, csv, hashlib, datetime, base64, re, time
from playwright.sync_api import sync_playwright
origin, out, urls = sys.argv[1], sys.argv[2], sys.argv[3:]
os.makedirs(out, exist_ok=True)
LOG='/workspace/az-clean/raw/fetch_log.csv'
JS='''async u=>{const r=await fetch(u,{credentials:'include'});const b=new Uint8Array(await r.arrayBuffer());let s='';for(let i=0;i<b.length;i+=32768)s+=String.fromCharCode.apply(null,b.subarray(i,i+32768));return {status:r.status,ct:r.headers.get('content-type'),b64:btoa(s)}}'''
with sync_playwright() as p:
    br=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=False,args=['--no-sandbox','--disable-blink-features=AutomationControlled'],ignore_default_args=['--enable-automation'])
    pg=br.new_context().new_page()
    pg.goto(origin,wait_until='load',timeout=90000); pg.wait_for_timeout(10000)
    print('origin title:',pg.title())
    if len(sys.argv)>3 and urls==['--html']: urls=[]
    if os.environ.get('SAVE_ORIGIN'):
        fn=os.path.join(out,os.environ['SAVE_ORIGIN']); open(fn,'w').write(pg.content()); print('saved origin html',fn)
    for u in urls:
        time.sleep(3)
        r=pg.evaluate(JS,u); body=base64.b64decode(r['b64'])
        fn=os.path.join(out,re.sub(r'[^A-Za-z0-9._-]','_',u.split('/')[-1].split('?')[0]) or 'index.html')
        open(fn,'wb').write(body)
        new=not os.path.exists(LOG)
        with open(LOG,'a',newline='') as f:
            w=csv.writer(f)
            if new: w.writerow(['url','local_path','fetched_at_local','http_status','bytes','sha256','content_type'])
            w.writerow([u,fn,datetime.datetime.now().astimezone().isoformat(timespec='seconds'),r['status'],len(body),hashlib.sha256(body).hexdigest(),r['ct']])
        print(r['status'],len(body),r['ct'],fn)
    br.close()
