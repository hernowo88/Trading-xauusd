from __future__ import annotations

import io
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="XAUUSD Trading", page_icon="📈", layout="wide")

TIMEFRAMES = {"M1": "1min", "M5": "5min", "M15": "15min", "M30": "30min", "H1": "1h", "H4": "4h"}


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    cols = {c.lower().strip(): c for c in x.columns}
    rename = {}
    for wanted in ["timestamp", "open", "high", "low", "close", "volume"]:
        if wanted not in cols:
            raise ValueError(f"Kolom wajib tidak ditemukan: {wanted}")
        rename[cols[wanted]] = wanted
    x = x.rename(columns=rename)
    x["timestamp"] = pd.to_datetime(x["timestamp"], utc=True, errors="coerce")
    for c in ["open", "high", "low", "close"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    if "volume" not in x:
        x["volume"] = 0.0
    x["volume"] = pd.to_numeric(x["volume"], errors="coerce").fillna(0.0)
    x = x.dropna(subset=["timestamp", "open", "high", "low", "close"])
    x = x.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    return x


def indicators(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    c = x["close"].astype(float)
    x["ema9"] = c.ewm(span=9, adjust=False).mean()
    x["ema21"] = c.ewm(span=21, adjust=False).mean()
    x["ema100"] = c.ewm(span=100, adjust=False).mean()
    d = c.diff()
    gain = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    x["rsi14"] = (100 - 100 / (1 + rs)).fillna(100)
    tr = pd.concat([(x.high-x.low), (x.high-c.shift()).abs(), (x.low-c.shift()).abs()], axis=1).max(axis=1)
    x["atr14"] = tr.ewm(alpha=1/14, adjust=False).mean()
    return x


def resample(df: pd.DataFrame, rule: str, cutoff: pd.Timestamp | None = None) -> pd.DataFrame:
    x = df.set_index("timestamp")
    out = x.resample(rule, label="left", closed="left").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    if cutoff is not None:
        duration = pd.Timedelta(rule)
        out = out[(out.index + duration) <= cutoff]
    return out.reset_index()


def state(df: pd.DataFrame, kind: str) -> str:
    if len(df) < 100: return "UNKNOWN"
    r = indicators(df).iloc[-1]
    if kind == "trend":
        if r.ema9 > r.ema21 and r.close > r.ema100: return "UP"
        if r.ema9 < r.ema21 and r.close < r.ema100: return "DOWN"
        return "MIXED"
    if r.ema9 > r.ema21: return "BULLISH"
    if r.ema9 < r.ema21: return "BEARISH"
    return "NEUTRAL"


def pattern_search(df: pd.DataFrame, window=30, top_k=20, forward=20, max_candidates=6000):
    if len(df) < 300 + window + forward: return pd.DataFrame(), {"samples":0,"up_pct":None,"down_pct":None,"avg":None}
    w = indicators(df.reset_index(drop=True))
    def feat(a):
        p = a.close.replace(0, np.nan).ffill().bfill()
        ret = a.close.pct_change().fillna(0).to_numpy(float)
        atrp = (a.atr14/p).replace([np.inf,-np.inf], np.nan).bfill().fillna(.001).to_numpy(float)
        return np.column_stack([ret/np.maximum(atrp,1e-9), ((a.ema9-a.ema21)/p).to_numpy(float)])
    target = feat(w.tail(window))
    last = len(w)-window-forward
    starts = np.linspace(100, last, min(max_candidates, max(1,last-100+1)), dtype=int)
    rows=[]
    for s in np.unique(starts):
        h=w.iloc[s:s+window]
        if len(h)<window: continue
        f=feat(h)
        dist=float(np.linalg.norm(target-f)/max(np.linalg.norm(target),np.linalg.norm(f),1e-12))
        entry=float(h.close.iloc[-1]); exitp=float(w.close.iloc[s+window+forward-1]); ch=(exitp/entry-1)*100
        rows.append({"match_start":h.timestamp.iloc[0],"match_end":h.timestamp.iloc[-1],"distance":dist,"forward_change_pct":ch,"direction":"UP" if ch>0 else "DOWN" if ch<0 else "FLAT"})
    m=pd.DataFrame(rows).sort_values("distance").head(top_k).reset_index(drop=True) if rows else pd.DataFrame()
    if m.empty: return m,{"samples":0,"up_pct":None,"down_pct":None,"avg":None}
    return m,{"samples":len(m),"up_pct":round((m.direction=="UP").mean()*100,2),"down_pct":round((m.direction=="DOWN").mean()*100,2),"avg":round(m.forward_change_pct.mean(),4)}


def decision(df: pd.DataFrame):
    x = indicators(df)
    r = x.iloc[-1]
    cutoff = x.timestamp.iloc[-1]
    m5 = resample(df,"5min",cutoff); m15=resample(df,"15min",cutoff); m30=resample(df,"30min",cutoff); h1=resample(df,"1h",cutoff); h4=resample(df,"4h",cutoff)
    t4,t1 = state(h4,"trend"),state(h1,"trend")
    s15,s5 = state(m15,"setup"),state(m5,"setup")
    s30 = state(m30,"setup")
    trig = "BULLISH" if r.ema9>r.ema21 else "BEARISH" if r.ema9<r.ema21 else "NEUTRAL"
    score={"UP":2,"DOWN":-2,"MIXED":0,"UNKNOWN":0}[t4]+{"UP":1.5,"DOWN":-1.5,"MIXED":0,"UNKNOWN":0}[t1]+{"BULLISH":1,"BEARISH":-1,"NEUTRAL":0,"UNKNOWN":0}[s15]+{"BULLISH":.75,"BEARISH":-.75,"NEUTRAL":0,"UNKNOWN":0}[s5]+{"BULLISH":1,"BEARISH":-1,"NEUTRAL":0}[trig]
    if 50<=r.rsi14<=70 and score>0: score += .5
    if 30<=r.rsi14<=50 and score<0: score -= .5
    matches,patt=pattern_search(df)
    if patt["samples"]:
        if patt["up_pct"]>=65: score += 1
        elif patt["down_pct"]>=65: score -= 1
    action="BUY" if score>=3 else "SELL" if score<=-3 else "WAIT"
    price=float(r.close); atr=float(r.atr14)
    sl=tp1=tp2=None
    if action=="BUY": sl,tp1,tp2=price-1.5*atr,price+1.5*atr,price+3*atr
    elif action=="SELL": sl,tp1,tp2=price+1.5*atr,price-1.5*atr,price-3*atr
    conf=min(95,50+min(abs(score),7)/7*45)
    return action,score,conf,price,atr,sl,tp1,tp2,(t4,t1,s15,s30,s5,trig),patt,matches,x


def backtest(df: pd.DataFrame, stop_atr=1.5, target_atr=3.0):
    if len(df)<150: raise ValueError("Minimal 150 candle M1")
    w=indicators(df.reset_index(drop=True)); pos=0; entry=stop=target=0.0; trades=[]
    for i in range(1,len(w)):
        row,prev=w.iloc[i],w.iloc[i-1]
        cross=0
        if prev.ema9>prev.ema21 and w.iloc[i-2].ema9<=w.iloc[i-2].ema21 if i>=2 else False: cross=1
        if prev.ema9<prev.ema21 and w.iloc[i-2].ema9>=w.iloc[i-2].ema21 if i>=2 else False: cross=-1
        if pos==0 and cross:
            pos=cross; entry=float(row.open); atr=max(float(prev.atr14),1e-9)
            stop=entry-stop_atr*atr if pos>0 else entry+stop_atr*atr; target=entry+target_atr*atr if pos>0 else entry-target_atr*atr; continue
        if pos:
            ep=None; why=None
            if pos>0:
                if row.low<=stop: ep,why=stop,"SL"
                elif row.high>=target: ep,why=target,"TP"
            else:
                if row.high>=stop: ep,why=stop,"SL"
                elif row.low<=target: ep,why=target,"TP"
            if ep is not None:
                ret=(ep/entry-1)*100*pos; trades.append({"entry_time":row.timestamp,"side":"BUY" if pos>0 else "SELL","entry":entry,"exit":ep,"return_pct":ret,"reason":why}); pos=0
    if not trades: return pd.DataFrame()
    return pd.DataFrame(trades)


st.title("📈 XAUUSD Trading")
st.caption("Research dashboard • M1 scalping • EMA 9/21/100 • RSI14 • ATR14 • MTF")

with st.sidebar:
    st.header("Data")
    uploaded = st.file_uploader("Upload histori XAUUSD", type=["csv","parquet"])
    st.caption("Kolom: timestamp, open, high, low, close, volume (volume boleh kosong).")
    source_note = st.info("Belum ada database histori cloud terhubung. Data yang tampil harus berasal dari file histori nyata yang kamu masukkan.")

if uploaded is None:
    st.warning("Dashboard sudah aktif, tetapi database histori XAUUSD belum dimasukkan ke deployment. Saya sengaja tidak membuat data contoh/palsu.")
    st.subheader("Arsitektur data")
    st.write("GitHub = kode • Streamlit = dashboard • database/object storage = histori besar • Dukascopy = sumber akuisisi historis.")
    st.markdown("**Target histori:** D1 sejak periode terdalam yang tersedia; tick/M1 mulai dari ketersediaan intraday nyata, dengan gap tetap sebagai gap.")
    st.stop()

try:
    raw = uploaded.getvalue()
    df = pd.read_csv(io.BytesIO(raw)) if uploaded.name.lower().endswith(".csv") else pd.read_parquet(io.BytesIO(raw))
    df = prepare(df)
except Exception as e:
    st.error(f"Gagal membaca data: {e}")
    st.stop()

if len(df)<250:
    st.warning(f"Data terbaca {len(df):,} candle. Minimal 250 candle M1 diperlukan untuk MTF.")
    st.stop()

st.success(f"Data valid: {len(df):,} candle • {df.timestamp.iloc[0]} → {df.timestamp.iloc[-1]}")
action,score,conf,price,atr,sl,tp1,tp2,states,patt,matches,ind = decision(df)

c1,c2,c3,c4 = st.columns(4)
c1.metric("SIGNAL",action); c2.metric("Score",f"{score:.2f}"); c3.metric("Confidence",f"{conf:.1f}%"); c4.metric("Harga",f"{price:.2f}")

if action != "WAIT":
    p1,p2,p3,p4 = st.columns(4)
    p1.metric("Entry",f"{price:.2f}"); p2.metric("SL",f"{sl:.2f}"); p3.metric("TP1",f"{tp1:.2f}"); p4.metric("TP2",f"{tp2:.2f}")
else:
    st.info("WAIT: belum ada konfirmasi skor yang cukup untuk BUY/SELL.")

st.subheader("Multi-timeframe")
labels=["H4 Trend","H1 Trend","M15 Setup","M30 Setup","M5 Setup","M1 Trigger"]
cols=st.columns(6)
for col,label,val in zip(cols,labels,states): col.metric(label,val)

st.subheader("M1 Chart")
chart=ind.set_index("timestamp")[["close","ema9","ema21","ema100"]].tail(2000)
st.line_chart(chart)

st.subheader("Indikator terakhir")
st.dataframe(pd.DataFrame([{"Close":price,"EMA9":ind.ema9.iloc[-1],"EMA21":ind.ema21.iloc[-1],"EMA100":ind.ema100.iloc[-1],"RSI14":ind.rsi14.iloc[-1],"ATR14":atr}]),use_container_width=True)

st.subheader("Pola historis yang mirip")
if patt["samples"]:
    a,b,c=st.columns(3); a.metric("Samples",patt["samples"]); b.metric("Historis naik",f"{patt['up_pct']:.1f}%"); c.metric("Historis turun",f"{patt['down_pct']:.1f}%")
    st.dataframe(matches,use_container_width=True)
else: st.info("Belum cukup histori untuk pencarian pola.")

st.subheader("Backtest EMA 9/21")
if st.button("Jalankan backtest"):
    with st.spinner("Menghitung..."):
        ledger=backtest(df.tail(100000))
    if ledger.empty: st.info("Tidak ada transaksi yang memenuhi aturan backtest.")
    else:
        ret=ledger.return_pct; wins=(ret>0).sum(); loss=(ret<=0).sum(); eq=ret.cumsum(); dd=eq-eq.cummax()
        a,b,c,d=st.columns(4); a.metric("Trades",len(ledger)); b.metric("Win rate",f"{wins/len(ledger)*100:.1f}%"); c.metric("Net return",f"{ret.sum():.3f}%"); d.metric("Max DD",f"{-dd.min():.3f}%")
        st.dataframe(ledger.tail(200),use_container_width=True)

st.caption("⚠️ Research/backtest only. Bukan jaminan profit dan bukan instruksi order otomatis.")
