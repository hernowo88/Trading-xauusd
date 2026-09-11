from __future__ import annotations
import argparse, lzma, struct
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
REC=struct.Struct('>IIIff'); UTC=timezone.utc

def decode(path,hour_start,scale):
    raw=lzma.decompress(path.read_bytes(),format=lzma.FORMAT_AUTO)
    if len(raw)%REC.size: raise ValueError(f'Invalid BI5 length: {path}')
    base=int(hour_start.timestamp()*1000)
    for i in range(0,len(raw),REC.size):
        ms,ask_i,bid_i,ask_v,bid_v=REC.unpack_from(raw,i)
        yield pd.Timestamp(base+ms,unit='ms',tz='UTC'),ask_i/scale,bid_i/scale,float(ask_v),float(bid_v)

def build(month,output,scale):
    buckets=defaultdict(lambda:{'bid':[],'ask':[],'bv':0.0,'av':0.0})
    for path in sorted(month.glob('*.bi5')):
        day,hour=map(int,path.stem.split('_')); start=datetime(int(month.parent.name),int(month.name),day,hour,tzinfo=UTC)
        for ts,ask,bid,av,bv in decode(path,start,scale):
            b=buckets[ts.floor('min')]; b['bid'].append(bid); b['ask'].append(ask); b['bv']+=bv; b['av']+=av
    rows=[]
    for ts,b in sorted(buckets.items()):
        bid,ask=b['bid'],b['ask']
        if not bid: continue
        rows.append({'timestamp':ts,'open':(bid[0]+ask[0])/2,'high':(max(bid)+max(ask))/2,'low':(min(bid)+min(ask))/2,'close':(bid[-1]+ask[-1])/2,'volume':b['bv']+b['av'],'ticks':len(bid),'bid_open':bid[0],'bid_high':max(bid),'bid_low':min(bid),'bid_close':bid[-1],'ask_open':ask[0],'ask_high':max(ask),'ask_low':min(ask),'ask_close':ask[-1],'bid_volume':b['bv'],'ask_volume':b['av']})
    if rows:
        pd.DataFrame(rows).to_parquet(output,index=False)
    return len(rows)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--data-dir',default='data'); p.add_argument('--price-scale',type=float,default=1000); a=p.parse_args()
    root=Path(a.data_dir)/'raw'/'dukascopy'/'XAUUSD'; out=Path(a.data_dir)/'processed'/'xauusd'/'m1'; out.mkdir(parents=True,exist_ok=True)
    total=0
    for month in sorted(root.glob('[0-9][0-9][0-9][0-9]/[0-9][0-9]')):
        n=build(month,out/f'xauusd_m1_{month.parent.name}_{month.name}.parquet',a.price_scale); print(month,n); total+=n
    print('TOTAL',total); return 0
if __name__=='__main__': raise SystemExit(main())
