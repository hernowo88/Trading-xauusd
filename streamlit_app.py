import os
import streamlit as st
import pandas as pd
from xauusd.data import CloudData
from xauusd.indicators import add_indicators
from xauusd.decision import decide

st.set_page_config(page_title='XAUUSD Trading',page_icon='📈',layout='wide')
st.title('XAUUSD Trading')
st.caption('M1 scalping • EMA 9/21/100 • MTF H4/H1/M15/M5/M1')

# Supports both Streamlit Secrets and environment variables.
if 'supabase' in st.secrets:
    os.environ.setdefault('SUPABASE_URL', st.secrets['supabase'].get('url',''))
    os.environ.setdefault('SUPABASE_KEY', st.secrets['supabase'].get('key',''))
os.environ.setdefault('SUPABASE_URL', st.secrets.get('SUPABASE_URL','') if hasattr(st,'secrets') else '')
os.environ.setdefault('SUPABASE_KEY', st.secrets.get('SUPABASE_KEY','') if hasattr(st,'secrets') else '')

cloud=CloudData()
if not cloud.ready:
    st.warning('Database cloud belum terhubung. Isi SUPABASE_URL dan SUPABASE_KEY di Streamlit Secrets. Skema database sudah disiapkan di repository: supabase/schema.sql.')
    st.code('SUPABASE_URL = "https://PROJECT.supabase.co"\nSUPABASE_KEY = "YOUR_ANON_KEY"',language='toml')
    st.stop()

bars=st.sidebar.selectbox('Data M1 untuk analisis',[1000,3000,6000,12000,24000],index=3)
if st.sidebar.button('🔄 Refresh data'):
    st.cache_data.clear(); st.rerun()

@st.cache_data(ttl=30,show_spinner=False)
def load(n): return cloud.latest('M1',n)

df=load(bars)
if df.empty:
    st.error('Database terhubung tetapi belum berisi candle XAUUSD M1.')
    st.stop()
try: d=decide(df)
except Exception as e: st.error(str(e)); st.stop()

c1,c2,c3,c4=st.columns(4)
c1.metric('Sinyal',d.action); c2.metric('Confidence',f'{d.confidence:.1f}%'); c3.metric('Harga',f'{d.price:,.2f}'); c4.metric('Score',f'{d.score:+.2f}')
if d.action!='WAIT':
    a,b,c=st.columns(3); a.metric('Stop Loss',f'{d.stop_loss:,.2f}'); b.metric('TP 1',f'{d.take_profit_1:,.2f}'); c.metric('TP 2',f'{d.take_profit_2:,.2f}')

st.subheader('Multi-timeframe')
mtf=pd.DataFrame([['H4',d.trend_h4],['H1',d.trend_h1],['M15',d.setup_m15],['M5',d.setup_m5],['M1',d.trigger_m1]],columns=['TF','Status'])
st.dataframe(mtf,use_container_width=True,hide_index=True)
st.info(d.reason)

a=add_indicators(df); chart=a.set_index('timestamp')[['close','ema9','ema21','ema100']].tail(min(1500,len(a)))
st.subheader('Chart M1'); st.line_chart(chart)

count=cloud.count('M1'); st.subheader('Statistik histori cloud')
q1,q2,q3=st.columns(3); q1.metric('Total M1 tersimpan',f'{count:,}' if count is not None else '—'); q2.metric('Awal data dimuat',str(df.timestamp.iloc[0])); q3.metric('Bar terakhir',str(df.timestamp.iloc[-1]))
st.caption('Sinyal adalah alat riset/backtest, bukan jaminan profit atau instruksi order otomatis.')
