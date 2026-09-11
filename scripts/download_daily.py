from __future__ import annotations
import argparse,datetime as dt,hashlib,json,lzma,struct
from pathlib import Path
import requests
BASE='https://datafeed.dukascopy.com/datafeed'; BAR=struct.Struct('>IIIIIf'); UTC=dt.timezone.utc

def main():
    p=argparse.ArgumentParser(); p.add_argument('--symbol',default='XAUUSD'); p.add_argument('--start-year',type=int,default=1999); p.add_argument('--end-year',type=int,default=2026); p.add_argument('--data-dir',default='data'); a=p.parse_args()
    root=Path(a.data_dir)/'daily'/'dukascopy'/a.symbol.upper(); root.mkdir(parents=True,exist_ok=True); man=root/'manifest.jsonl'; s=requests.Session()
    for year in range(a.start_year,a.end_year+1):
        url=f'{BASE}/{a.symbol.upper()}/{year}/BID_candles_day_1.bi5'; rawfile=root/f'{year}.bi5'
        try:
            if not rawfile.exists():
                r=s.get(url,timeout=60); r.raise_for_status(); rawfile.write_bytes(r.content)
            raw=lzma.decompress(rawfile.read_bytes()); rows=[]; base=dt.datetime(year,1,1,tzinfo=UTC)
            for i in range(0,len(raw),BAR.size):
                sec,op,cl,lo,hi,vol=BAR.unpack_from(raw,i); rows.append({'timestamp':(base+dt.timedelta(seconds=sec)).isoformat(),'open':op/1000,'high':hi/1000,'low':lo/1000,'close':cl/1000,'volume':float(vol)})
            out=root/f'xauusd_d1_{year}.jsonl'; out.write_text('\n'.join(json.dumps(r,separators=(',',':')) for r in rows)+'\n',encoding='utf-8'); man.open('a',encoding='utf-8').write(json.dumps({'year':year,'status':'ok','rows':len(rows),'sha256':hashlib.sha256(rawfile.read_bytes()).hexdigest()})+'\n'); print(year,len(rows))
        except Exception as e:
            with man.open('a',encoding='utf-8') as f: f.write(json.dumps({'year':year,'status':'failed','error':repr(e)})+'\n')
    return 0
if __name__=='__main__': raise SystemExit(main())
