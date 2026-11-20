"""Fetch a URL into az-clean/raw and append to fetch_log.csv (url, local, timestamp, http status, bytes, sha256)."""
import sys, hashlib, datetime, subprocess, csv, os, time
url, out = sys.argv[1], sys.argv[2]
time.sleep(float(os.environ.get('PACE','2')))
t=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
r=subprocess.run(['curl','-sSL','-A','Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36','-o',out,'-w','%{http_code}',url],capture_output=True,text=True)
code=r.stdout.strip()
b=open(out,'rb').read() if os.path.exists(out) else b''
h=hashlib.sha256(b).hexdigest()
log='/workspace/az-clean/raw/fetch_log.csv'; new=not os.path.exists(log)
with open(log,'a',newline='') as f:
    w=csv.writer(f)
    if new: w.writerow(['url','local_path','fetched_at_local','http_status','bytes','sha256'])
    w.writerow([url,out,t,code,len(b),h])
print(code,len(b),h,out, r.stderr)
