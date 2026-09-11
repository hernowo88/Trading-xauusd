from __future__ import annotations
import argparse,sqlite3
import pandas as pd

def main():
    p=argparse.ArgumentParser(); p.add_argument('--db',default='data/xauusd.sqlite'); a=p.parse_args()
    con=sqlite3.connect(a.db); df=pd.read_sql_query("SELECT timestamp,open,high,low,close FROM candles WHERE source='dukascopy' AND symbol='XAUUSD' AND timeframe='M1' ORDER BY timestamp",con,parse_dates=['timestamp']); con.close()
    if df.empty: print('NO DATA'); return 2
    bad=((df.high<df.open)|(df.high<df.close)|(df.high<df.low)|(df.low>df.open)|(df.low>df.close)).sum(); dup=df.timestamp.duplicated().sum(); delta=df.timestamp.diff().dropna().dt.total_seconds()/60
    print(f'rows={len(df):,}'); print('first=',df.timestamp.iloc[0].isoformat()); print('last=',df.timestamp.iloc[-1].isoformat()); print('bad_ohlc=',int(bad)); print('duplicates=',int(dup)); print('gaps_gt_1m=',int((delta>1).sum())); print('non_positive=',int((delta<=0).sum()))
    return 0 if bad==0 and dup==0 and (delta<=0).sum()==0 else 1
if __name__=='__main__': raise SystemExit(main())
