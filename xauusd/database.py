from __future__ import annotations
import sqlite3
from pathlib import Path
SCHEMA='''CREATE TABLE IF NOT EXISTS candles(source TEXT NOT NULL,symbol TEXT NOT NULL,timeframe TEXT NOT NULL,timestamp TEXT NOT NULL,open REAL NOT NULL,high REAL NOT NULL,low REAL NOT NULL,close REAL NOT NULL,volume REAL,ticks INTEGER,bid_open REAL,bid_high REAL,bid_low REAL,bid_close REAL,ask_open REAL,ask_high REAL,ask_low REAL,ask_close REAL,bid_volume REAL,ask_volume REAL,PRIMARY KEY(source,symbol,timeframe,timestamp));CREATE INDEX IF NOT EXISTS idx_candles_lookup ON candles(symbol,timeframe,timestamp);CREATE TABLE IF NOT EXISTS gaps(source TEXT NOT NULL,symbol TEXT NOT NULL,timeframe TEXT NOT NULL,start_ts TEXT NOT NULL,end_ts TEXT NOT NULL,expected_bars INTEGER,actual_bars INTEGER,reason TEXT,PRIMARY KEY(source,symbol,timeframe,start_ts,end_ts));'''
def connect(path='data/xauusd.sqlite'):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); con=sqlite3.connect(p); con.execute('PRAGMA journal_mode=WAL'); con.execute('PRAGMA synchronous=NORMAL'); con.executescript(SCHEMA); return con

def insert_candles(con,rows):
    sql='INSERT OR IGNORE INTO candles(source,symbol,timeframe,timestamp,open,high,low,close,volume,ticks,bid_open,bid_high,bid_low,bid_close,ask_open,ask_high,ask_low,ask_close,bid_volume,ask_volume) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
    before=con.total_changes; con.executemany(sql,rows); con.commit(); return con.total_changes-before
