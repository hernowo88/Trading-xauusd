from __future__ import annotations
import pandas as pd

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    c = out["close"].astype(float)
    out["ema9"] = c.ewm(span=9, adjust=False).mean()
    out["ema21"] = c.ewm(span=21, adjust=False).mean()
    out["ema100"] = c.ewm(span=100, adjust=False).mean()
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, pd.NA)
    out["rsi14"] = (100 - (100 / (1 + rs))).fillna(100)
    tr = pd.concat([out["high"]-out["low"], (out["high"]-c.shift()).abs(), (out["low"]-c.shift()).abs()], axis=1).max(axis=1)
    out["atr14"] = tr.ewm(alpha=1/14, adjust=False).mean()
    out["ema_cross"] = ((out.ema9 > out.ema21) & (out.ema9.shift(1) <= out.ema21.shift(1))).astype(int) - ((out.ema9 < out.ema21) & (out.ema9.shift(1) >= out.ema21.shift(1))).astype(int)
    return out
