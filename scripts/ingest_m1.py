from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
from xauusd.database import connect,insert_candles

def main():
    p=argparse.ArgumentParser(); p.add_argument('--data-dir',default='data'); p.add_argument('--db',default='data/xauusd.sqlite'); a=p.parse_args()
    files=sorted((Path(a.data_dir)/'processed'/'xauusd'/'m1').glob('xauusd_m1_*.parquet'))
    with connect(a.db) as con:
        total=0
        for f in files:
            df=pd.read_parquet(f).sort_values('timestamp')
            rows=[]
            for r in df.itertuples(index=False):
                rows.append(('dukascopy','XAUUSD','M1',pd.Timestamp(r.timestamp).isoformat(),float(r.open),float(r.high),float(r.low),float(r.close),float(r.volume),int(r.ticks),float(r.bid_open),float(r.bid_high),float(r.bid_low),float(r.bid_close),float(r.ask_open),float(r.ask_high),float(r.ask_low),float(r.ask_close),float(r.bid_volume),float(r.ask_volume)))
            n=insert_candles(con,rows); print(f.name,n); total+=n
    print('TOTAL INSERTED',total); return 0
if __name__=='__main__': raise SystemExit(main())
