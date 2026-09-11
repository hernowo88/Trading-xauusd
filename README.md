# XAUUSD Trading Research

Dashboard Streamlit untuk riset XAUUSD, fokus M1 scalping dan konfirmasi M5/M15/M30/H1/H4.

## Engine
- EMA 9, EMA 21, EMA 100
- RSI 14
- ATR 14
- MTF trend/setup
- historical pattern matching tanpa menggunakan candle masa depan untuk sinyal saat ini
- backtest EMA 9/21 dengan entry candle berikutnya dan aturan SL/TP ATR

## Data
Sumber utama akuisisi historis: Dukascopy. Target intraday dimulai dari ketersediaan M1/tick nyata dan target D1 mencakup periode lebih tua. Data kosong tidak diisi dengan data buatan.

Pipeline lokal:

```text
Dukascopy tick -> raw immutable -> build M1 Parquet -> SQLite append-only -> validation -> Streamlit
```

Downloader:

```bash
python scripts/dukascopy_ticks.py --start 2003-05-05 --end 2026-09-11
python scripts/build_m1.py
python scripts/ingest_m1.py
python scripts/validate_m1.py
```

D1:

```bash
python scripts/download_daily.py --start-year 1999 --end-year 2026
```

## Integrity
- raw archive tidak ditimpa
- manifest mencatat hasil akuisisi
- database memakai primary key source/symbol/timeframe/timestamp
- duplicate import diabaikan
- gap pasar tetap gap
- tidak ada synthetic candle

Dashboard yang online tidak mengklaim seluruh histori sudah tersedia sampai database benar-benar diisi dan divalidasi.
