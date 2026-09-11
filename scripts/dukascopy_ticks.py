from __future__ import annotations
import argparse, datetime as dt, hashlib, json, time
from pathlib import Path
import requests
BASE="https://datafeed.dukascopy.com/datafeed"; UTC=dt.timezone.utc

def url_for(symbol, when):
    return f"{BASE}/{symbol.upper()}/{when.year}/{when.month-1:02d}/{when.day:02d}/{when.hour:02d}h_ticks.bi5"

def main():
    p=argparse.ArgumentParser(); p.add_argument('--symbol',default='XAUUSD'); p.add_argument('--start',default='2003-05-05'); p.add_argument('--end',default='2026-09-11'); p.add_argument('--data-dir',default='data'); p.add_argument('--retries',type=int,default=4); a=p.parse_args()
    start=dt.datetime.strptime(a.start,'%Y-%m-%d').replace(tzinfo=UTC); end=dt.datetime.strptime(a.end,'%Y-%m-%d').replace(tzinfo=UTC)+dt.timedelta(days=1)
    root=Path(a.data_dir)/'raw'/'dukascopy'/a.symbol.upper(); root.mkdir(parents=True,exist_ok=True); manifest=root/'manifest.jsonl'; done=set()
    if manifest.exists():
        for line in manifest.read_text(encoding='utf-8').splitlines():
            try:
                r=json.loads(line)
                if r.get('status') in ('downloaded','empty','exists'): done.add(r.get('hour'))
            except Exception: pass
    s=requests.Session(); s.headers['User-Agent']='xauusd-history-engine/1.0'; cur=start
    while cur<end:
        key=cur.strftime('%Y-%m-%dT%H:00:00Z')
        if key in done: cur+=dt.timedelta(hours=1); continue
        d=root/f'{cur.year:04d}'/f'{cur.month:02d}'; d.mkdir(parents=True,exist_ok=True); target=d/f'{cur.day:02d}_{cur.hour:02d}.bi5'; url=url_for(a.symbol,cur)
        if target.exists() and target.stat().st_size: status={'hour':key,'status':'exists','path':str(target),'bytes':target.stat().st_size}
        else:
            status=None
            for attempt in range(a.retries):
                try:
                    r=s.get(url,timeout=60); r.raise_for_status()
                    if not r.content: status={'hour':key,'status':'empty','url':url}; break
                    tmp=target.with_suffix('.part'); tmp.write_bytes(r.content); tmp.replace(target)
                    status={'hour':key,'status':'downloaded','url':url,'path':str(target),'bytes':len(r.content),'sha256':hashlib.sha256(r.content).hexdigest()}; break
                except Exception as e:
                    if attempt==a.retries-1: status={'hour':key,'status':'failed','url':url,'error':repr(e)}
                    else: time.sleep(2*(attempt+1))
        with manifest.open('a',encoding='utf-8') as f: f.write(json.dumps(status)+'\n')
        cur+=dt.timedelta(hours=1)
    return 0
if __name__=='__main__': raise SystemExit(main())
