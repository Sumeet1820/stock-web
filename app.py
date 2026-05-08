"""
Stock Analyzer Pro — Flask Web Backend
stock_analyzer_v34.py ki saari logic ka web wrapper.
"""
import sys, os, threading, json, datetime, re, hashlib, secrets
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import unittest.mock as _m
for _mod in ['tkinter','tkinter.ttk','tkinter.font','tkinter.messagebox']:
    sys.modules.setdefault(_mod, _m.MagicMock())

from stock_analyzer_v34 import (
    scrape_screener, fetch_stock, search_stock,
    fetch_nse_live, fetch_best_live_price,
    fetch_nse_market_data, fetch_chartink,
    fetch_nse_etf_list, fetch_nse_etf_screener,
    CRITERIA, APP_DATA, _save_data,
    NSE_SESSION,
)

# ── Screener.in saved screens integration ─────────────────────────────────────
from screener import (
    run_screener as _run_screener_in,
    load_results as _load_screener_results,
    get_progress as _get_screener_progress,
    results_are_fresh as _screener_results_fresh,
    _set_progress as _set_screener_progress,
)
from screener_scraper import (
    EXPLORE_SCREENS,
    fetch_explore_screen,
    cookies_valid as _screener_cookies_valid,
)
_screener_thread_lock = threading.Lock()
_explore_cache = {}  # key → {'data': [...], 'ts': datetime}

from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import requests as _req

app = Flask(__name__)
# Permanent secret key — restart pe session expire nahi hoga
_sk_file = os.path.join(BASE, '.secret_key')
if os.path.exists(_sk_file):
    with open(_sk_file) as f: app.secret_key = f.read().strip()
else:
    _sk = secrets.token_hex(32)
    with open(_sk_file, 'w') as f: f.write(_sk)
    app.secret_key = _sk
from datetime import timedelta
app.permanent_session_lifetime = timedelta(days=365)

# ── FNO Stocks List (Options Trading Enabled) ────────────────────────────────
FNO_STOCKS = {
    # Indices
    'NIFTY','BANKNIFTY','FINNIFTY','MIDCPNIFTY',
    # Top FNO Stocks (alphabetically)
    'ABB','ABBOTINDIA','ABCAPITAL','ABFRL','ACC','ADANIENT','ADANIPORTS','ALKEM','AMBUJACEM','APOLLOHOSP','APOLLOTYRE','ASHOKLEY','ASIANPAINT','ASTRAL','ATUL','AUBANK','AUROPHARMA','AXISBANK','BAJAJ-AUTO','BAJAJFINSV','BAJFINANCE','BALKRISIND','BALRAMCHIN','BANDHANBNK','BANKBARODA','BATAINDIA','BEL','BERGEPAINT','BHARATFORG','BHARTIARTL','BHEL','BIOCON','BOSCHLTD','BPCL','BRITANNIA','BSOFT','CANBK','CANFINHOME','CHAMBLFERT','CHOLAFIN','CIPLA','COALINDIA','COFORGE','COLPAL','CONCOR','COROMANDEL','CROMPTON','CUB','CUMMINSIND','DABUR','DALBHARAT','DEEPAKNTR','DELTACORP','DIVISLAB','DIXON','DLF','DRREDDY','EICHERMOT','ESCORTS','EXIDEIND','FEDERALBNK','GAIL','GLENMARK','GMRINFRA','GNFC','GODREJCP','GODREJPROP','GRANULES','GRASIM','GUJGASLTD','HAL','HAVELLS','HCLTECH','HDFCAMC','HDFCBANK','HDFCLIFE','HEROMOTOCO','HINDALCO','HINDCOPPER','HINDPETRO','HINDUNILVR','IBULHSGFIN','ICICIBANK','ICICIGI','ICICIPRULI','IDEA','IDFC','IDFCFIRSTB','IEX','IGL','INDHOTEL','INDIACEM','INDIAMART','INDIGO','INDUSINDBK','INDUSTOWER','INFY','IOC','IPCALAB','IRCTC','ITC','JINDALSTEL','JKCEMENT','JSWSTEEL','JUBLFOOD','KOTAKBANK','L&TFH','LALPATHLAB','LAURUSLABS','LICHSGFIN','LT','LTI','LTTS','LUPIN','M&M','M&MFIN','MANAPPURAM','MARICO','MARUTI','MCDOWELL-N','MCX','METROPOLIS','MFSL','MGL','MOTHERSON','MPHASIS','MRF','MUTHOOTFIN','NATIONALUM','NAUKRI','NAVINFLUOR','NESTLEIND','NMDC','NTPC','OBEROIRLTY','OFSS','ONGC','PAGEIND','PEL','PERSISTENT','PETRONET','PFC','PIDILITIND','PIIND','PNB','POLYCAB','POWERGRID','PVRINOX','RAIN','RAMCOCEM','RBLBANK','RECLTD','RELIANCE','SAIL','SBICARD','SBILIFE','SBIN','SHREECEM','SIEMENS','SRF','SUNPHARMA','SUNTV','SYNGENE','TATACHEM','TATACOMM','TATACONSUM','TATAMOTORS','TATAPOWER','TATASTEEL','TCS','TECHM','TITAN','TORNTPHARM','TORNTPOWER','TRENT','TVSMOTOR','UBL','ULTRACEMCO','UPL','VEDL','VOLTAS','WIPRO','ZEEL','ZYDUSLIFE'
}

BROAD = {'NIFTY 50','NIFTY NEXT 50','NIFTY 100','NIFTY 200','NIFTY 500','NIFTY MIDCAP 50','NIFTY MIDCAP 100','NIFTY MIDCAP 150','NIFTY SMLCAP 50','NIFTY SMLCAP 100','NIFTY SMLCAP 250','NIFTY MIDSML 400','NIFTY LARGEMID250','NIFTY MID SELECT','NIFTY MICROCAP250','NIFTY TOTAL MKT','INDIA VIX','NIFTY500 MULTICAP','NIFTY500 LMS EQL','NIFTY FPI 150'}
SECTORAL = {'NIFTY AUTO','NIFTY BANK','NIFTY FIN SERVICE','NIFTY FINSRV25 50','NIFTY FMCG','NIFTY IT','NIFTY MEDIA','NIFTY METAL','NIFTY PHARMA','NIFTY PSU BANK','NIFTY REALTY','NIFTY PVT BANK','NIFTY HEALTHCARE','NIFTY CONSR DURBL','NIFTY OIL AND GAS','NIFTY MIDSML HLTH','NIFTY CHEMICALS','NIFTY500 HEALTH','NIFTY FINSEREXBNK','NIFTY MS IT TELCM','NIFTY MS FIN SERV'}
THEMATIC = {'NIFTY COMMODITIES','NIFTY CONSUMPTION','NIFTY CPSE','NIFTY ENERGY','NIFTY INFRA','NIFTY MNC','NIFTY PSE','NIFTY SERV SECTOR','NIFTY100 LIQ 15','NIFTY MID LIQ 15','NIFTY IND DIGITAL','NIFTY100 ESG','NIFTY100ESGSECLDR','NIFTY INDIA MFG','NIFTY TATA 25 CAP','NIFTY MULTI MFG','NIFTY MULTI INFRA','NIFTY IND DEFENCE','NIFTY IND TOURISM','NIFTY CAPITAL MKT','NIFTY EV','NIFTY NEW CONSUMP','NIFTY CORP MAATR','NIFTY MOBILITY','NIFTY100 ENH ESG','NIFTY COREHOUSING','NIFTY HOUSING','NIFTY IPO','NIFTY MS IND CONS','NIFTY NONCYC CONS','NIFTY RURAL','NIFTY SHARIAH 25','NIFTY TRANS LOGIS','NIFTY50 SHARIAH','NIFTY500 SHARIAH','NIFTY SME EMERGE','NIFTY INTERNET','NIFTY WAVES','NIFTY INFRALOG','NIFTY RAILWAYSPSU','NIFTYCONGLOMERATE'}
STRATEGY = {'NIFTY DIV OPPS 50','NIFTY50 VALUE 20','NIFTY100 QUALTY30','NIFTY50 EQL WGT','NIFTY100 EQL WGT','NIFTY100 LOWVOL30','NIFTY ALPHA 50','NIFTY200 QUALTY30','NIFTY ALPHALOWVOL','NIFTY200MOMENTM30','NIFTY M150 QLTY50','NIFTY200 ALPHA 30','NIFTYM150MOMNTM50','NIFTY500MOMENTM50','NIFTYMS400 MQ 100','NIFTYSML250MQ 100','NIFTY TOP 10 EW','NIFTY AQL 30','NIFTY AQLV 30','NIFTY HIGHBETA 50','NIFTY LOW VOL 50','NIFTY QLTY LV 30','NIFTY SML250 Q50','NIFTY TOP 15 EW','NIFTY100 ALPHA 30','NIFTY200 VALUE 30','NIFTY500 EW','NIFTY MULTI MQ 50','NIFTY500 VALUE 50','NIFTY TOP 20 EW','NIFTY500 QLTY50','NIFTY500 LOWVOL50','NIFTY500 MQVLV50','NIFTY500 FLEXICAP','NIFTY TMMQ 50','NIFTY GROWSECT 15','NIFTY50 USD'}
SKIP_INDICES = {'NIFTY GS 8 13YR','NIFTY GS 10YR','NIFTY GS 10YR CLN','NIFTY GS 4 8YR','NIFTY GS 11 15YR','NIFTY GS 15YRPLUS','NIFTY GS COMPSITE','BHARATBOND-APR30','BHARATBOND-APR31','BHARATBOND-APR32','BHARATBOND-APR33','NIFTY50 TR 2X LEV','NIFTY50 PR 2X LEV','NIFTY50 TR 1X INV','NIFTY50 PR 1X INV','NIFTY50 DIV POINT'}

def _cat(sym):
    if sym in BROAD: return 'broad'
    if sym in SECTORAL: return 'sectoral'
    if sym in THEMATIC: return 'thematic'
    if sym in STRATEGY: return 'strategy'
    return 'thematic'

def _clean(v):
    import math
    if isinstance(v,bool): return bool(v)   # bool pehle check karo (bool is subclass of int)
    if isinstance(v,float) and (math.isnan(v) or math.isinf(v)): return None
    return v

def _clean_dict(d):
    if isinstance(d,dict): return {k:_clean_dict(v) for k,v in d.items()}
    if isinstance(d,list): return [_clean_dict(i) for i in d]
    return _clean(d)

def _evaluate_checklist(data, tab):
    crit=CRITERIA.get(tab,[]); items=[]; passed=0; total=0
    for name,key,cond,fn in crit:
        if fn is None:
            items.append({'name':name,'condition':cond,'status':'manual','value':None,'icon':'❓'}); continue
        total+=1; val=data.get(key)
        if val is None:
            items.append({'name':name,'condition':cond,'status':'nodata','value':None,'icon':'⚠️'})
        else:
            try:
                ok=fn(float(val))
                if ok: passed+=1
                items.append({'name':name,'condition':cond,'status':'pass' if ok else 'fail','value':round(float(val),2),'icon':'✅' if ok else '❌'})
            except:
                items.append({'name':name,'condition':cond,'status':'nodata','value':val,'icon':'⚠️'})
    return {'items':items,'passed':passed,'total':total,'score':round(passed/total*100) if total else 0}

def _compute_technical(sym, fdata=None):
    import math, statistics as _stats
    try:
        import yfinance as yf, numpy as np
        hist=yf.download(f"{sym}.NS",period="1y",interval="1d",auto_adjust=True,progress=False)
        if hist is None or hist.empty:
            hist=yf.Ticker(f"{sym}.NS").history(period="1y",auto_adjust=True,actions=False)
        if hist is None or hist.empty: return {'error':f'{sym} ka data nahi mila'}
        if hasattr(hist.columns,'levels'): hist.columns=hist.columns.get_level_values(0)
        try: hist.index=hist.index.tz_localize(None) if hist.index.tzinfo else hist.index
        except: pass
        hist=hist.dropna(subset=['Close','High','Low','Volume'])
        if len(hist)<20: return {'error':'Data bahut kam hai'}
        c=hist['Close'].values.astype(float); h=hist['High'].values.astype(float)
        l=hist['Low'].values.astype(float); v=hist['Volume'].values.astype(float)
        valid=~(np.isnan(c)|np.isnan(h)|np.isnan(l))
        c,h,l,v=c[valid],h[valid],l[valid],v[valid]; n=len(c)
        if n<20: return {'error':'Valid data bahut kam hai'}
        has_open='Open' in hist.columns
        o_arr=hist['Open'].values.astype(float)[valid] if has_open else None

        def ema(arr,period):
            k=2/(period+1); e=[arr[0]]
            for x in arr[1:]: e.append(x*k+e[-1]*(1-k))
            return e

        def rsi_calc(arr,p=14):
            deltas=[arr[i]-arr[i-1] for i in range(1,len(arr))]
            gains=[max(d,0) for d in deltas]; losses=[abs(min(d,0)) for d in deltas]
            ag=sum(gains[:p])/p; al=sum(losses[:p])/p
            for i in range(p,len(deltas)):
                ag=(ag*(p-1)+gains[i])/p; al=(al*(p-1)+losses[i])/p
            if al==0: return 100
            return round(100-(100/(1+ag/al)),1)

        rsi_val=rsi_calc(c.tolist())
        ema12=ema(c.tolist(),12); ema26=ema(c.tolist(),26)
        macd_line=[ema12[i]-ema26[i] for i in range(n)]
        signal_line=ema(macd_line[25:],9) if n>25 else []
        macd_val=round(macd_line[-1],2); signal_val=round(signal_line[-1],2) if signal_line else 0
        macd_cross="Bullish" if macd_val>signal_val else "Bearish"
        ema20a=ema(c.tolist(),20); ema50a=ema(c.tolist(),50)
        ema200a=ema(c.tolist(),200) if n>=200 else None
        cur=float(c[-1]); e20=round(ema20a[-1],2); e50=round(ema50a[-1],2)
        e200=round(ema200a[-1],2) if ema200a else None
        ema_align=bool((cur>e20>e50) and (e200 is None or e50>e200))
        bb_upper=bb_lower=bb_mid=None; bb_pct=50
        if n>=20:
            window=[float(x) for x in c[-20:]]
            bb_mid=round(sum(window)/20,2); bb_std=_stats.stdev(window)
            bb_upper=round(bb_mid+2*bb_std,2); bb_lower=round(bb_mid-2*bb_std,2)
            bb_pct=round((cur-bb_lower)/(bb_upper-bb_lower)*100,1) if (bb_upper-bb_lower)>0 else 50
        tr_list=[max(h[-i]-l[-i],abs(h[-i]-c[-i-1]),abs(l[-i]-c[-i-1])) for i in range(1,min(15,n))]
        atr=round(sum(tr_list)/len(tr_list),2) if tr_list else 0; atr_pct=round(atr/cur*100,2) if cur else 0
        avg_vol_20=sum(v[-20:])/20 if n>=20 else sum(v)/n
        vol_ratio=round(v[-1]/avg_vol_20,2) if avg_vol_20>0 else 1; vol_surge=bool(vol_ratio>=1.5)
        pivot=(h[-1]+l[-1]+c[-1])/3
        r1=round(2*pivot-l[-1],2); r2=round(pivot+(h[-1]-l[-1]),2)
        s1=round(2*pivot-h[-1],2); s2=round(pivot-(h[-1]-l[-1]),2); pivot=round(pivot,2)
        high52=round(max(h.tolist()),2); low52=round(min(l.tolist()),2)
        pct_from_52h=round((cur-high52)/high52*100,1)
        sl_atr=round(cur-2*atr,2); tgt1_atr=round(cur+2*atr,2); tgt2_atr=round(cur+4*atr,2)
        rr_ratio=round((tgt1_atr-cur)/(cur-sl_atr),2) if (cur-sl_atr)>0 else 0

        patterns=[]
        if n>=3 and o_arr is not None:
            body=abs(c[-1]-o_arr[-1]); rng_c=h[-1]-l[-1]
            if rng_c>0 and body/rng_c<0.1: patterns.append({'name':'Doji','icon':'⚖️','signal':'neutral','desc':'Indecision — wait for confirmation'})
            lw=min(o_arr[-1],c[-1])-l[-1]; uw=h[-1]-max(o_arr[-1],c[-1])
            if rng_c>0 and lw>2*body and uw<body: patterns.append({'name':'Hammer','icon':'🔨','signal':'bullish','desc':'Bullish reversal signal'})
            if rng_c>0 and uw>2*body and lw<body: patterns.append({'name':'Shooting Star','icon':'⭐','signal':'bearish','desc':'Bearish reversal signal'})
            if n>=2:
                pb=c[-2]-o_arr[-2]; cb=c[-1]-o_arr[-1]
                if pb<0 and cb>0 and cb>abs(pb): patterns.append({'name':'Bullish Engulfing','icon':'🟢','signal':'bullish','desc':'Strong bullish signal'})
                if pb>0 and cb<0 and abs(cb)>pb: patterns.append({'name':'Bearish Engulfing','icon':'🔴','signal':'bearish','desc':'Strong bearish signal'})
            if n>=3:
                if c[-3]<o_arr[-3] and abs(c[-2]-o_arr[-2])<0.3*(h[-2]-l[-2]) and c[-1]>o_arr[-1]: patterns.append({'name':'Morning Star','icon':'🌅','signal':'bullish','desc':'Bullish reversal — 3-candle'})
                if c[-3]>o_arr[-3] and abs(c[-2]-o_arr[-2])<0.3*(h[-2]-l[-2]) and c[-1]<o_arr[-1]: patterns.append({'name':'Evening Star','icon':'🌇','signal':'bearish','desc':'Bearish reversal — 3-candle'})
        if not patterns: patterns.append({'name':'No Strong Pattern','icon':'➖','signal':'neutral','desc':'Neutral — no clear signal'})

        chart_patterns=[]
        if n>=30:
            ranges=[h[-i]-l[-i] for i in range(1,31)]
            if sum(ranges[:15])/15<sum(ranges[15:])/15*0.7 and vol_ratio<1.0:
                chart_patterns.append({'name':'VCP — Volatility Contraction','icon':'🔺','signal':'bullish','desc':'Breakout ready!'})
        if pct_from_52h>=-3: chart_patterns.append({'name':'Near 52W High Breakout','icon':'🚀','signal':'bullish','desc':f'{abs(pct_from_52h):.1f}% below 52W high'})
        if n>=10:
            cp=(max(h[-10:])-min(l[-10:]))/cur*100 if cur else 100
            if cp<8: chart_patterns.append({'name':'Consolidation / Base Building','icon':'📦','signal':'neutral','desc':f'{cp:.1f}% range — tight base'})
        if n>=60:
            lh_=max(h[-60:-40].tolist()); bot=min(l[-40:-15].tolist()); rz=max(h[-15:].tolist())
            depth=(lh_-bot)/lh_*100
            if 10<depth<35 and rz>lh_*0.95: chart_patterns.append({'name':'Cup & Handle','icon':'☕','signal':'bullish','desc':f'Cup depth {depth:.1f}%'})
        if not chart_patterns: chart_patterns.append({'name':'No Major Chart Pattern','icon':'➖','signal':'neutral','desc':'Wait karo'})

        score=0; rb=[]; bear=[]
        if 40<=rsi_val<=70:
            score+=20
            if rsi_val>55: rb.append(f"RSI {rsi_val} — bullish zone")
        elif rsi_val>70: score+=8; bear.append(f"RSI {rsi_val} — overbought")
        else: score+=5; bear.append(f"RSI {rsi_val} — weak momentum")
        if macd_cross=="Bullish": score+=20; rb.append("MACD bullish crossover")
        else: bear.append("MACD bearish")
        if ema_align: score+=25; rb.append(f"EMA20>EMA50{'>EMA200' if e200 else ''} — uptrend")
        elif cur>e20: score+=12; rb.append("Price EMA20 ke upar")
        else: bear.append("Price EMAs ke neeche")
        if vol_surge: score+=15; rb.append(f"Volume {vol_ratio}x — strong interest")
        else: score+=5
        if bb_pct>60: score+=10; rb.append("Bollinger upper band — momentum")
        elif bb_pct<30: score+=3; bear.append("Bollinger lower band — weak")
        else: score+=6
        if pct_from_52h>=-5: score+=10; rb.append(f"52W high ke paas")
        elif pct_from_52h<-20: bear.append(f"52W high se {abs(pct_from_52h):.1f}% neeche")
        score=min(score,100)

        fd=fdata or {}
        fund_score=int(bool(fd.get('net_profit',0) and fd['net_profit']>0))+int(bool(fd.get('roe',0) and fd['roe']>15))+int(bool(fd.get('debt_to_equity') is not None and fd['debt_to_equity']<1))+int(bool(fd.get('promoter_holding',0) and fd['promoter_holding']>50))
        # Verdict purely on technical score — fdata optional hai
        if score>=75: verdict="⚡ STRONG BUY"; vtype="strong_buy"; vreason=f"Technical score {score}/100 — Strong momentum!"
        elif score>=60: verdict="✅ BUY with Caution"; vtype="buy"; vreason=f"Technical score {score}/100 — Decent setup. Volume aur S/R confirm karo."
        elif score>=45: verdict="⏳ WAIT / WATCH"; vtype="wait"; vreason=f"Technical score {score}/100 — Mixed signals. Breakout ka wait karo."
        else: verdict="❌ AVOID for Now"; vtype="avoid"; vreason=f"Technical score {score}/100 — Weak momentum."

        # Valuation
        pe=fd.get('pe')
        if pe:
            if pe<15: val_label="Cheap 🟢"; val_type="cheap"
            elif pe<25: val_label="Fair 🟡"; val_type="fair"
            elif pe<40: val_label="Expensive 🔴"; val_type="expensive"
            else: val_label="Very Expensive ❌"; val_type="very_expensive"
        else: val_label="P/E N/A"; val_type="unknown"

        price_history=[]
        try:
            dates=hist.index[-90:].strftime('%d %b').tolist()
            closes=[round(float(x),2) for x in hist['Close'].values[-90:]]
            price_history=[{'date':d,'price':p} for d,p in zip(dates,closes)]
        except: pass

        returns={}
        try:
            today=datetime.date.today(); ep_val=float(c[-1])
            def pct(sd):
                try:
                    mask=hist.index.date>=sd; sub=hist.loc[mask,'Close'].dropna()
                    if sub.empty: return None
                    sp=float(sub.iloc[0])
                    return round((ep_val-sp)/sp*100,2) if sp>0 else None
                except: return None
            for lbl,sd in [('1D',today-datetime.timedelta(days=1)),('1W',today-datetime.timedelta(weeks=1)),('1M',today-datetime.timedelta(days=30)),('YTD',datetime.date(today.year,1,1)),('1Y',today-datetime.timedelta(days=365)),('3Y',today-datetime.timedelta(days=365*3)),('5Y',today-datetime.timedelta(days=365*5))]:
                returns[lbl]=pct(sd)
        except: pass

        return _clean_dict({'rsi':rsi_val,'macd':macd_val,'signal':signal_val,'macd_cross':macd_cross,'ema20':e20,'ema50':e50,'ema200':e200,'ema_align':ema_align,'cur':round(cur,2),'bb_upper':bb_upper,'bb_lower':bb_lower,'bb_mid':bb_mid,'bb_pct':bb_pct,'atr':atr,'atr_pct':atr_pct,'vol_ratio':vol_ratio,'vol_surge':vol_surge,'pivot':pivot,'r1':r1,'r2':r2,'s1':s1,'s2':s2,'high52':high52,'low52':low52,'pct_from_52h':pct_from_52h,'sl':sl_atr,'tgt1':tgt1_atr,'tgt2':tgt2_atr,'rr':rr_ratio,'patterns':patterns,'chart_patterns':chart_patterns,'score':score,'reasons_bull':rb,'reasons_bear':bear,'verdict':verdict,'verdict_type':vtype,'verdict_reason':vreason,'val_label':val_label,'val_type':val_type,'price_history':price_history,'returns':returns})
    except Exception as ex:
        import traceback; traceback.print_exc()
        return {'error':str(ex)}

def _fetch_all_indices():
    rows=[]
    try:
        NSE_SESSION.get("https://www.nseindia.com",timeout=8)
        r=NSE_SESSION.get("https://www.nseindia.com/api/allIndices",timeout=12)
        if r.status_code!=200: return rows
        for item in r.json().get('data',[]):
            sym=(item.get('indexSymbol') or item.get('index','')).strip()
            if not sym or sym in SKIP_INDICES: continue
            try: chg=float(item.get('percentChange',item.get('pChange',0)))
            except: chg=0.0
            try: last=float(item.get('last',item.get('lastPrice',0)))
            except: last=0.0
            rows.append({'name':sym,'last':last,'chg':chg,'cat':_cat(sym)})
    except Exception as ex: print(f"[allIndices] {ex}")
    return rows

def _calc_ipo_score(ipo):
    score=0; reasons=[]
    gmp=ipo.get('gmp'); price_num=ipo.get('price_num',0) or 0
    sub=ipo.get('subscription') or 0; issue_size=ipo.get('issue_size',0) or 0
    category=ipo.get('category',''); registrar=(ipo.get('registrar') or '').lower()
    if gmp is not None and price_num>0:
        gp=(gmp/price_num)*100
        if gp>20: score+=2; reasons.append(f"✅ GMP {gp:.0f}% > 20%")
        elif gp>0: score+=1; reasons.append(f"✅ GMP {gp:.0f}% > 0%")
        else: reasons.append(f"❌ GMP negative ({gp:.0f}%)")
    else: reasons.append("❓ GMP unknown")
    if sub>10: score+=2; reasons.append(f"✅ Subscribed {sub:.1f}x > 10x")
    elif sub>2: score+=1; reasons.append(f"✅ Subscribed {sub:.1f}x > 2x")
    elif sub>0: reasons.append(f"❌ Only {sub:.1f}x subscribed")
    else: reasons.append("❓ Subscription data nahi")
    if price_num and 0<price_num<=500: score+=1; reasons.append(f"✅ Price ≤ ₹500")
    elif price_num and price_num>500: reasons.append(f"⚠️ Price ₹{price_num:.0f} > 500")
    if category=='Mainboard': score+=1; reasons.append("✅ Mainboard IPO")
    else: reasons.append(f"⚠️ {category or 'SME'} IPO")
    if issue_size>=500: score+=1; reasons.append(f"✅ Issue ≥ 500Cr")
    elif issue_size>=100: reasons.append(f"⚠️ Issue ₹{issue_size:.0f}Cr")
    else: reasons.append("❌ Small issue size")
    if any(r in registrar for r in ['link intime','kfintech','bigshare','skyline','cameo']):
        score+=1; reasons.append(f"✅ Reputed Registrar")
    else: reasons.append(f"❓ Registrar: {ipo.get('registrar','') or 'Unknown'}")
    return min(score,10), reasons

def _fetch_ipo_data_internal():
    import datetime as _dt
    today=_dt.date.today(); cutoff=today-_dt.timedelta(days=60)
    HEADERS={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0','Accept':'text/html,*/*;q=0.9','Referer':'https://www.google.com/'}
    def _sess():
        s=_req.Session(); s.headers.update(HEADERS); return s
    from bs4 import BeautifulSoup
    ipos=[]
    def _parse_date(date_txt):
        date_txt=date_txt.strip(); open_s=date_txt; close_s=''; status='Upcoming'; close_obj=None
        try:
            m=re.match(r'(\d+)\s*[-–]\s*(\d+)\s+(\w+)\s*(\d{4})?',date_txt)
            if m:
                d1=int(m.group(1)); d2=int(m.group(2)); mon=m.group(3); year=int(m.group(4)) if m.group(4) else today.year
                od=None
                for fmt in ('%d %B %Y','%d %b %Y'):
                    try: od=_dt.datetime.strptime(f"{d1} {mon} {year}",fmt).date(); break
                    except: pass
                if od is None: return date_txt,'','Upcoming',None
                cd=None
                for fmt in ('%d %B %Y','%d %b %Y'):
                    try: cd=_dt.datetime.strptime(f"{d2} {mon} {year}",fmt).date(); break
                    except: pass
                if cd is None: cd=od
                if d2<d1:
                    nm=(od.month%12)+1; ny=year if nm>1 else year+1; cd=_dt.date(ny,nm,d2)
                open_s=od.strftime('%d %b %Y'); close_s=cd.strftime('%d %b %Y'); close_obj=cd
                if od<=today<=cd: status='Open'
                elif today>cd: status='Closed'
        except: pass
        return open_s,close_s,status,close_obj

    try:
        r=_sess().get("https://ipowatch.in/upcoming-ipo-list/",timeout=18)
        if r.status_code==200:
            soup=BeautifulSoup(r.text,'html.parser')
            for tbl in soup.select('table'):
                ths=[th.get_text(strip=True) for th in tbl.select('th')]
                ths_lower=[h.lower() for h in ths]
                if not any(w in ' '.join(ths_lower) for w in ['ipo','stock','company','date']): continue
                ci={'name':0,'date':1,'size':2,'price':3,'type':-1}
                for i,h in enumerate(ths_lower):
                    if 'company' in h or 'stock' in h: ci['name']=i
                    elif 'date' in h: ci['date']=i
                    elif 'size' in h: ci['size']=i
                    elif 'price' in h or 'band' in h: ci['price']=i
                    elif 'type' in h: ci['type']=i
                for row in tbl.select('tr')[1:]:
                    tds=row.select('td')
                    if len(tds)<3: continue
                    def _cell(k,fb=0):
                        idx=ci.get(k,fb); return tds[idx].get_text(strip=True) if idx>=0 and idx<len(tds) else ''
                    name=_cell('name',0)
                    if not name or len(name)<2: continue
                    det_url=''; ni=ci.get('name',0)
                    if ni<len(tds):
                        a=tds[ni].find('a')
                        if a and a.get('href'):
                            h2=a['href']; det_url=h2 if h2.startswith('http') else 'https://ipowatch.in'+h2
                    date_txt=_cell('date',1); type_txt=_cell('type',-1) if ci.get('type',-1)>=0 else ''
                    size_txt=_cell('size',2); price_txt=_cell('price',3)
                    open_s,close_s,status,close_obj=_parse_date(date_txt)
                    if status=='Closed' and close_obj and close_obj<cutoff: continue
                    price_num=0
                    try:
                        pb=price_txt.replace('₹','').replace(',','').replace(' to ','-').replace('to','-')
                        parts=[p.strip() for p in pb.split('-') if p.strip()]
                        price_num=float(parts[-1]) if parts else 0
                    except: pass
                    issue_size=0
                    try:
                        st=size_txt.replace('₹','').replace(',','').replace('Cr.','').replace('Cr','').strip()
                        m4=re.search(r'[\d.]+',st)
                        if m4: issue_size=float(m4.group())
                    except: pass
                    category='SME' if (type_txt and 'sme' in type_txt.lower()) or (not type_txt and issue_size and issue_size<250) else 'Mainboard'
                    ipos.append({'company':name.strip(),'symbol':'','status':status,'price_band':price_txt,'price_num':price_num,'open_date':open_s,'close_date':close_s,'issue_size':issue_size,'lot_size':0,'subscription':None,'registrar':'','category':category,'gmp':None,'detail_url':det_url})
                if ipos: break
    except Exception as ex: print(f"[ipo-list] {ex}")

    gmp_map={}
    try:
        r2=_sess().get("https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/",timeout=15)
        if r2.status_code==200:
            soup2=BeautifulSoup(r2.text,'html.parser')
            for tbl in soup2.select('table'):
                rows2 = tbl.select('tr')
                if len(rows2) < 2: continue
                first_tds = rows2[0].select('td')
                if len(first_tds) < 4: continue
                # Column layout (confirmed from live scrape, no <th> headers):
                # 0=Company  1=GMP(₹)  2=Signal  3=Price  4=Est.Listing  5=Date  6=Type  7=Status
                # First row is a pseudo-header row with text like "IPO Name", "IPO GMP" — skip it
                for row in rows2:
                    tds = row.select('td')
                    if len(tds) < 4: continue
                    name = tds[0].get_text(strip=True)
                    # Skip header-like rows
                    if not name or len(name) < 2: continue
                    if 'ipo name' in name.lower() or 'company' in name.lower(): continue
                    # GMP — col 1
                    gv = None
                    try:
                        raw_gmp = tds[1].get_text(strip=True).replace('₹','').replace('+','').replace(',','').strip()
                        if raw_gmp and raw_gmp.lower() not in ('ipo gmp','gmp','n/a','-','–'):
                            gv = float(raw_gmp)
                            # Price — col 3 for sanity check
                            pv = 0
                            try:
                                pnums = re.findall(r'\d+', tds[3].get_text(strip=True).replace('₹',''))
                                if pnums: pv = float(pnums[-1])
                            except: pass
                            if 2000 <= gv <= 2099: gv = None
                            elif pv > 0 and abs(gv) > pv * 3: gv = None
                    except: gv = None
                    gmp_map[name.lower()] = {'gmp': gv, 'sub': None}
                if gmp_map: break
    except Exception as ex: print(f"[gmp] {ex}")

    def _fuzzy(name,dmap):
        nl=name.lower().strip()
        if nl in dmap: return dmap[nl]
        for k in dmap:
            if nl[:8] in k or k[:8] in nl: return dmap[k]
        words=set(nl.split())
        for k in dmap:
            if len(words & set(k.split()))>=2: return dmap[k]
        return None

    for ipo in ipos:
        g=_fuzzy(ipo['company'],gmp_map)
        if g:
            ipo['gmp']=g.get('gmp')
            if not ipo.get('subscription'): ipo['subscription']=g.get('sub')

    def _sort_key(x):
        order={'Open':0,'Upcoming':1,'Closed':2}; base=order.get(x.get('status','Upcoming'),1)
        try: days=(_dt.datetime.strptime(x['open_date'],'%d %b %Y').date()-today).days
        except: days=999
        return (base,days)
    ipos.sort(key=_sort_key)

    # ── NSE API: subscription (noOfTime) for current IPOs ────────────────────
    try:
        NSE_SESSION.get("https://www.nseindia.com", timeout=8)
        NSE_SESSION.get("https://www.nseindia.com/market-data/all-upcoming-issues-ipo", timeout=6)
        rn = NSE_SESSION.get("https://www.nseindia.com/api/ipo-current-issue", timeout=10)
        if rn.status_code == 200:
            nse_items = rn.json()
            if isinstance(nse_items, dict): nse_items = nse_items.get('data', [])
            # Build map: company_name_lower → {symbol, noOfTime}
            nse_map = {}
            for ni in (nse_items or []):
                cname = (ni.get('companyName') or '').lower().strip()
                sym_n = ni.get('symbol','')
                sub_t = ni.get('noOfTime')
                try: sub_t = float(sub_t) if sub_t else None
                except: sub_t = None
                if cname: nse_map[cname] = {'symbol': sym_n, 'sub': sub_t}
            # Fuzzy match IPOs to NSE data
            for ipo in ipos:
                nl = ipo['company'].lower().strip()
                match = None
                if nl in nse_map: match = nse_map[nl]
                else:
                    words = [w for w in nl.split() if len(w) > 3]
                    for k, v in nse_map.items():
                        if any(w in k for w in words):
                            match = v; break
                if match:
                    if not ipo.get('symbol') and match.get('symbol'):
                        ipo['symbol'] = match['symbol']
                    if not ipo.get('subscription') and match.get('sub') and match['sub'] > 0:
                        ipo['subscription'] = round(match['sub'], 2)
    except Exception as ex: print(f"[nse-sub] {ex}")

    # ── Detail page fetch: lot_size, registrar, subscription, gmp ────────────
    from bs4 import BeautifulSoup as _BS
    def _fetch_detail(ipo):
        try:
            det_url = ipo.get('detail_url','')
            if not det_url:
                slug = re.sub(r'[^a-z0-9]+','-',ipo['company'].lower()).strip('-')
                det_url = f"https://ipowatch.in/{slug}-ipo-date-review-price-allotment-details/"
            r = _sess().get(det_url, timeout=15)
            if r.status_code != 200: return
            soup = _BS(r.text,'html.parser')
            full_text = soup.get_text(' ')
            price_num = ipo.get('price_num',0) or 0

            # ── Lot Size ─────────────────────────────────────────────────
            for tbl in soup.select('table'):
                hdrs = [th.get_text(strip=True).lower() for th in tbl.select('tr:first-child th,tr:first-child td')]
                if not any('lot' in h or 'share' in h for h in hdrs): continue
                shares_idx = next((i for i,h in enumerate(hdrs) if 'share' in h and 'offered' not in h), 2)
                for drow in tbl.select('tr')[1:]:
                    cells = drow.select('td')
                    candidates = []
                    for ci2,cell in enumerate(cells):
                        txt = cell.get_text(strip=True).replace(',','')
                        nums = re.findall(r'^\d+$', txt.strip())
                        if nums:
                            v = int(nums[0])
                            if 1 < v <= 10000: candidates.append((ci2,v))
                    if candidates:
                        preferred = [c for c in candidates if c[0]==shares_idx]
                        ipo['lot_size'] = (preferred[0][1] if preferred else max(candidates,key=lambda x:x[1])[1])
                        break
                if ipo.get('lot_size'): break

            # ── Registrar ────────────────────────────────────────────────
            registrar = ''
            for heading in soup.find_all(['h2','h3','h4','strong','b']):
                if 'registrar' in heading.get_text(strip=True).lower():
                    for sib in heading.find_next_siblings():
                        txt = sib.get_text(strip=True)
                        if txt and 3 < len(txt) < 100 and any(c.isalpha() for c in txt):
                            registrar = txt.split('\n')[0].strip(); break
                        if sib.name in ['h2','h3','h4']: break
                    if registrar: break
            if not registrar:
                rm = re.search(r'(?:ipo\s*)?registrar\s*[:\-–]?\s*([A-Za-z][A-Za-z\s\.&]+(?:Ltd|Limited|Pvt|Services|Technologies|Intime|Fintech)[\.A-Za-z\s]*)',full_text,re.IGNORECASE)
                if rm: registrar = rm.group(1).strip()[:60]
            if not registrar:
                for kr in ['Link Intime India','KFin Technologies','Kfin Technologies','Bigshare Services','Skyline Financial','Cameo Corporate','Mas Services','Beetal Financial','Purva Sharegistry','Integrated Registry']:
                    if kr.lower() in full_text.lower(): registrar = kr; break
            if registrar:
                registrar = registrar.split('\n')[0].split('Phone')[0].split('Email')[0].strip()
                ipo['registrar'] = registrar

            # ── Subscription (text fallback) ──────────────────────────────
            if not ipo.get('subscription'):
                for pat in [r'total\s*subscription[^0-9]*(\d+\.?\d*)\s*(?:times|x)',
                             r'overall\s*(?:subscription|subscribed)[^0-9]*(\d+\.?\d*)\s*(?:times|x)?',
                             r'subscribed\s*(\d+\.?\d*)\s*(?:times|x)']:
                    sm = re.search(pat, full_text, re.IGNORECASE)
                    if sm:
                        try:
                            sv = float(sm.group(1))
                            if 0 < sv <= 5000: ipo['subscription'] = sv; break
                        except: pass

            # ── GMP from detail page (if still missing) ───────────────────
            if ipo.get('gmp') is None:
                for pat in [r'(?:today\'?s?\s*)?gmp\s*(?:is\s*)?[₹\s]*([-+]?\d{1,4})',
                             r'grey\s*market\s*premium\s*(?:is\s*)?[₹\s]*([-+]?\d{1,4})']:
                    gm = re.search(pat, full_text, re.IGNORECASE)
                    if gm:
                        try:
                            gv = float(gm.group(1))
                            if not (2000 <= gv <= 2099) and (price_num == 0 or abs(gv) <= price_num*3):
                                ipo['gmp'] = gv; break
                        except: pass

            # ── Listing date ──────────────────────────────────────────────
            if not ipo.get('est_listing'):
                lm = re.search(r'listing\s*(?:date|day)?\s*[:\-–]?\s*(\w+\s+\d{1,2},?\s*\d{4}|\d{1,2}\s+\w+\s+\d{4})',full_text,re.IGNORECASE)
                if lm: ipo['est_listing'] = lm.group(1).strip()

        except Exception as ex:
            print(f"[detail] {ipo.get('company','')} → {ex}")

    # Fetch details for all IPOs (parallel threads)
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        ex.map(_fetch_detail, ipos)

    for ipo in ipos:
        score,reasons=_calc_ipo_score(ipo)
        ipo['score']=score; ipo['score_reasons']=reasons
    return ipos

# ══════════════════════════════════════════════════════════════════════════════
# AUTH SYSTEM — Email + Password
# ══════════════════════════════════════════════════════════════════════════════

USERS_FILE = os.path.join(BASE, 'users.json')

def _load_users():
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except: pass
    return {}

def _save_users(users):
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except: pass

def _current_user_id():
    """Get logged-in user's ID from session"""
    return session.get('user_id', '')

def _login_required(f):
    """Decorator — redirect to login if not logged in"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Login required', 'redirect': '/login'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

# ── Auth Routes ───────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if session.get('user_id'):
        return redirect('/')
    if request.method == 'GET':
        return render_template('auth.html', mode='login')
    # POST — login
    data  = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    pwd   = data.get('password', '')
    if not email or not pwd:
        return jsonify({'error': 'Email aur password dono chahiye'}), 400
    users = _load_users()
    user  = users.get(email)
    if not user or not check_password_hash(user['password'], pwd):
        return jsonify({'error': 'Email ya password galat hai'}), 401
    session['user_id']    = email
    session['user_name']  = user.get('name', email.split('@')[0])
    session.permanent     = True
    return jsonify({'ok': True, 'name': session['user_name']})

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if session.get('user_id'):
        return redirect('/')
    if request.method == 'GET':
        return render_template('auth.html', mode='register')
    # POST — register
    data  = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    pwd   = data.get('password', '')
    name  = data.get('name', '').strip()
    if not email or not pwd or not name:
        return jsonify({'error': 'Naam, email aur password sab chahiye'}), 400
    if len(pwd) < 6:
        return jsonify({'error': 'Password kam se kam 6 characters ka hona chahiye'}), 400
    if '@' not in email or '.' not in email.split('@')[-1]:
        return jsonify({'error': 'Valid email address daalo'}), 400
    users = _load_users()
    if email in users:
        return jsonify({'error': 'Yeh email already registered hai'}), 409
    users[email] = {
        'name':     name,
        'email':    email,
        'password': generate_password_hash(pwd),
        'created':  datetime.datetime.now().isoformat(),
    }
    _save_users(users)
    session['user_id']   = email
    session['user_name'] = name
    session.permanent    = True
    return jsonify({'ok': True, 'name': name})

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/api/me')
def api_me():
    uid = session.get('user_id', '')
    if not uid:
        return jsonify({'logged_in': False})
    return jsonify({
        'logged_in': True,
        'email':     uid,
        'name':      session.get('user_name', uid.split('@')[0]),
    })

def _user_data():
    """Get data for logged-in user"""
    uid = _current_user_id()
    if not uid:
        # Fallback to X-User-ID header (backward compat)
        uid = request.headers.get('X-User-ID','').strip()
    if not uid:
        uid = 'default'
    uid = re.sub(r'[^a-zA-Z0-9_@.\-]', '', uid)[:60] or 'default'
    # Use email as filename (sanitized)
    safe = re.sub(r'[^a-zA-Z0-9_\-]', '_', uid)[:50]
    user_file = os.path.join(BASE, f'userdata_{safe}.json')
    try:
        if os.path.exists(user_file):
            with open(user_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except: pass
    return {'watchlist': {}, 'notes': {}, 'trades': {}}

def _save_user_data(data):
    """Save data for logged-in user"""
    uid = _current_user_id()
    if not uid:
        uid = request.headers.get('X-User-ID','').strip()
    if not uid:
        uid = 'default'
    safe = re.sub(r'[^a-zA-Z0-9_\-]', '_', uid)[:50]
    user_file = os.path.join(BASE, f'userdata_{safe}.json')
    try:
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except: pass

# ═══════════════════ ROUTES ═══════════════════════════════════════════════════

@app.route('/')
@_login_required
def home():
    return render_template('index.html')

@app.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip()
    fno_only = request.args.get('fno', '').lower() in ('1', 'true', 'yes')
    if not q: return jsonify([])

    q_up = q.upper()

    try:
        # ── Local FNO match first (instant, no network) ───────────────────
        local_fno = []
        for sym in sorted(FNO_STOCKS):
            if sym.startswith(q_up) or q_up in sym:
                local_fno.append({
                    'name': sym,
                    'symbol': sym,
                    'url': f'/company/{sym}/',
                    'is_fno': True,
                    '_local': True,
                })
        # Also check instruments cache for name match
        with _instruments_lock:
            inst_copy = dict(_upstox_instruments)
        for sym, ikey in inst_copy.items():
            if sym not in FNO_STOCKS and (sym.startswith(q_up) or q_up in sym):
                local_fno.append({
                    'name': sym,
                    'symbol': sym,
                    'url': f'/company/{sym}/',
                    'is_fno': False,
                    '_local': True,
                })

        # ── Screener.in search (network) ──────────────────────────────────
        remote = []
        try:
            results = search_stock(q)
            if not results: results = search_stock(q_up)
            if not results: results = search_stock(q.lower())
            for r in (results or [])[:12]:
                item = dict(r)
                url_sym = ''
                if item.get('url'):
                    m = re.search(r'/company/([^/]+)/', item['url'])
                    if m: url_sym = m.group(1).upper()
                item['symbol'] = url_sym or item.get('symbol', '')
                item['is_fno'] = item['symbol'] in FNO_STOCKS
                item['_local'] = False
                remote.append(item)
        except Exception as se:
            print(f'[search] screener error: {se}')

        # ── Merge: remote first, then local not already in remote ─────────
        seen_syms = {r['symbol'] for r in remote if r.get('symbol')}
        merged = list(remote)
        for item in local_fno:
            if item['symbol'] not in seen_syms:
                merged.append(item)
                seen_syms.add(item['symbol'])

        # FNO filter
        if fno_only:
            merged = [x for x in merged if x.get('is_fno')]

        # Sort: FNO first, then exact prefix match first
        def sort_key(x):
            sym = x.get('symbol', '')
            is_fno = x.get('is_fno', False)
            exact_prefix = sym.startswith(q_up)
            return (0 if is_fno else 1, 0 if exact_prefix else 1, sym)

        merged.sort(key=sort_key)
        return jsonify(merged[:15])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/fno_stocks')
def api_fno_stocks():
    """Return full FNO stocks list for option chain symbol picker"""
    q = request.args.get('q','').strip().upper()
    stocks = sorted(FNO_STOCKS)
    if q:
        stocks = [s for s in stocks if q in s]
    return jsonify(stocks)

@app.route('/api/analyze')
def api_analyze():
    url=request.args.get('url','').strip(); sym=request.args.get('sym','').strip().upper()
    if not url and not sym: return jsonify({'error':'url or sym required'}),400
    try:
        # Handle relative URLs from screener search results
        if url and url.startswith('/'):
            url = 'https://www.screener.in' + url
        if url: data=fetch_stock(url)
        else:
            data=fetch_stock(f"https://www.screener.in/company/{sym}/consolidated/")
            if not data.get('market_cap'): data=fetch_stock(f"https://www.screener.in/company/{sym}/")
        symbol=data.get('nse_symbol') or sym
        nse={}
        if symbol:
            try: nse=fetch_nse_live(symbol)
            except: pass
        data['nse']=nse
        data['checklist']={t:_evaluate_checklist(data,t) for t in ['swing','positional','longterm']}
        # Returns (1D/1W/1M/YTD/1Y/3Y/5Y/MAX)
        if symbol:
            try:
                import yfinance as yf
                hist=yf.download(f"{symbol}.NS",period="max",interval="1d",auto_adjust=True,progress=False)
                if hist is not None and not hist.empty:
                    if hasattr(hist.columns,'levels'): hist.columns=hist.columns.get_level_values(0)
                    try: hist.index=hist.index.tz_localize(None) if hist.index.tzinfo else hist.index
                    except: pass
                    hist=hist[['Close']].dropna()
                    ep=float(hist['Close'].iloc[-1]); today=datetime.date.today()
                    def _pct(sd):
                        try:
                            sub=hist.loc[hist.index.date>=sd,'Close'].dropna()
                            if sub.empty: return None
                            sp=float(sub.iloc[0]); return round((ep-sp)/sp*100,2) if sp>0 else None
                        except: return None
                    data['returns']={'1D':_pct(today-datetime.timedelta(days=1)),'1W':_pct(today-datetime.timedelta(weeks=1)),'1M':_pct(today-datetime.timedelta(days=30)),'YTD':_pct(datetime.date(today.year,1,1)),'1Y':_pct(today-datetime.timedelta(days=365)),'3Y':_pct(today-datetime.timedelta(days=365*3)),'5Y':_pct(today-datetime.timedelta(days=365*5)),'MAX':_pct(hist.index[0].date()) if not hist.empty else None}
            except: data['returns']={}
        return jsonify(_clean_dict(data))
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error':str(e)}),500

@app.route('/api/direct/<sym>')
def api_direct(sym):
    sym=sym.upper().strip()
    try:
        res=search_stock(sym); url=None
        if res:
            for r in res:
                m=re.search(r'/company/([^/]+)/',r.get('url','').upper())
                if m and m.group(1)==sym: url=r['url']; break
            if not url:
                for r in res:
                    if sym in (r.get('name','') or '').upper(): url=r['url']; break
            if not url: url=res[0].get('url','')
        if url:
            data=fetch_stock(f"https://www.screener.in{url}")
            nse=fetch_nse_live(sym)
            data['nse']=nse
            data['checklist']={t:_evaluate_checklist(data,t) for t in ['swing','positional','longterm']}
            return jsonify(_clean_dict(data))
        return jsonify({'error':f'{sym} screener pe nahi mila'}),404
    except Exception as e: return jsonify({'error':str(e)}),500

@app.route('/api/technical/<sym>')
def api_technical(sym):
    fd={}
    try:
        r=request.args.get('fdata','')
        if r: fd=json.loads(r)
    except: pass
    try: return jsonify(_compute_technical(sym.upper(),fd))
    except Exception as e: return jsonify({'error':str(e)}),500

@app.route('/api/returns/<sym>')
def api_returns(sym):
    try:
        import yfinance as yf
        hist=yf.download(f"{sym.upper()}.NS",period="max",interval="1d",auto_adjust=True,progress=False)
        if hist is None or hist.empty: hist=yf.Ticker(f"{sym.upper()}.NS").history(period="max",auto_adjust=True,actions=False)
        if hist is None or hist.empty: return jsonify({})
        if hasattr(hist.columns,'levels'): hist.columns=hist.columns.get_level_values(0)
        try: hist.index=hist.index.tz_localize(None) if hist.index.tzinfo else hist.index
        except: pass
        hist=hist[['Close']].dropna()
        if hist.empty: return jsonify({})
        ep=float(hist['Close'].iloc[-1]); today=datetime.date.today()
        def pct(sd):
            try:
                sub=hist.loc[hist.index.date>=sd,'Close'].dropna()
                if sub.empty: return None
                sp=float(sub.iloc[0]); return round((ep-sp)/sp*100,2) if sp>0 else None
            except: return None
        return jsonify({'1D':pct(today-datetime.timedelta(days=1)),'1W':pct(today-datetime.timedelta(weeks=1)),'1M':pct(today-datetime.timedelta(days=30)),'YTD':pct(datetime.date(today.year,1,1)),'1Y':pct(today-datetime.timedelta(days=365)),'3Y':pct(today-datetime.timedelta(days=365*3)),'5Y':pct(today-datetime.timedelta(days=365*5)),'MAX':pct(hist.index[0].date()) if not hist.empty else None})
    except Exception as e: return jsonify({'error':str(e)}),500

@app.route('/api/live/<sym>')
def api_live(sym):
    sym = sym.upper()
    # Try Upstox first for live LTP (faster + more accurate)
    if _upstox_token:
        try:
            import requests as _rq
            ikey = _get_instrument_key(sym)
            if ikey:
                ikey_enc = ikey.replace('|','%7C').replace(' ','%20')
                r = _rq.get(
                    f'https://api.upstox.com/v2/market-quote/ltp?instrument_key={ikey_enc}',
                    headers=_upstox_headers(), timeout=5)
                if r.status_code == 200:
                    qd = r.json().get('data', {})
                    if qd:
                        v = list(qd.values())[0]
                        ltp = v.get('last_price', 0) or v.get('ltp', 0)
                        if ltp:
                            return jsonify({'ltp': ltp, 'symbol': sym, 'source': 'upstox'})
        except Exception as ex:
            print(f'[Upstox live] {sym}: {ex}')
    # Fallback to NSE
    try: return jsonify(fetch_nse_live(sym))
    except Exception as e: return jsonify({'error':str(e)}),500

@app.route('/api/price/<sym>')
def api_price(sym):
    sym = sym.upper()
    # Try Upstox first
    if _upstox_token:
        try:
            import requests as _rq
            ikey = _get_instrument_key(sym)
            if ikey:
                ikey_enc = ikey.replace('|','%7C').replace(' ','%20')
                r = _rq.get(
                    f'https://api.upstox.com/v2/market-quote/ltp?instrument_key={ikey_enc}',
                    headers=_upstox_headers(), timeout=5)
                if r.status_code == 200:
                    qd = r.json().get('data', {})
                    if qd:
                        v = list(qd.values())[0]
                        ltp = v.get('last_price', 0) or v.get('ltp', 0)
                        if ltp:
                            return jsonify({'price': ltp, 'symbol': sym, 'source': 'upstox'})
        except: pass
    try:
        p=fetch_best_live_price(sym); return jsonify({'price':p,'symbol':sym})
    except Exception as e: return jsonify({'error':str(e)}),500

@app.route('/api/market/<dtype>')
def api_market(dtype):
    try:
        return jsonify(_fetch_market_data_new(dtype))
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error':str(e)}),500

def _fetch_market_data_new(dtype):
    """
    NSE market data — confirmed working endpoints (May 2026)
    gainers/losers: live-analysis-variations → allSec.data
    volume/active/52high/52low: equity-stockIndices → data (sorted client-side)
    """
    import math

    def _safe_float(v):
        try:
            f = float(str(v).replace(',',''))
            return None if (math.isnan(f) or math.isinf(f)) else f
        except: return None

    def _pct(ltp, prev):
        if ltp and prev and prev != 0:
            return round((ltp - prev) / prev * 100, 2)
        return 0.0

    # Warm up NSE session
    try:
        NSE_SESSION.get("https://www.nseindia.com", timeout=8)
    except: pass

    # ── GAINERS / LOSERS ─────────────────────────────────────────────────────
    if dtype in ('gainers', 'losers'):
        page_map = {
            'gainers': 'https://www.nseindia.com/market-data/top-gainers-losers',
            'losers':  'https://www.nseindia.com/market-data/top-gainers-losers',
        }
        idx_map = {'gainers': 'gainers', 'losers': 'loosers'}
        try:
            NSE_SESSION.get(page_map[dtype], timeout=8)
            r = NSE_SESSION.get(
                f"https://www.nseindia.com/api/live-analysis-variations?index={idx_map[dtype]}",
                timeout=15)
            if r.status_code != 200: return []
            data = r.json()
            # allSec.data has all-segment stocks
            items = []
            for key in ['allSec', 'NIFTY', 'SecGtr20', 'SecLwr20', 'FOSec']:
                v = data.get(key, {})
                if isinstance(v, dict):
                    raw = [x for x in v.get('data', []) if isinstance(x, dict)]
                    items.extend(raw)
            # Deduplicate by symbol
            seen = set(); rows = []
            for item in items:
                sym = item.get('symbol','')
                if sym and sym not in seen:
                    seen.add(sym)
                    ltp  = _safe_float(item.get('ltp'))
                    prev = _safe_float(item.get('prev_price'))
                    net  = _safe_float(item.get('net_price'))  # % change directly
                    chg  = net if net is not None else _pct(ltp, prev)
                    rows.append({
                        'symbol':     sym,
                        'company':    item.get('company_name', sym),
                        'ltp':        ltp or 0,
                        'change_pct': chg,
                        'volume':     _safe_float(item.get('trade_quantity')) or 0,
                        'high':       _safe_float(item.get('high_price')),
                        'low':        _safe_float(item.get('low_price')),
                        'prev':       prev,
                    })
            # Sort
            rows.sort(key=lambda x: x['change_pct'], reverse=(dtype == 'gainers'))
            return rows[:50]
        except Exception as ex:
            print(f"[market-{dtype}] {ex}")
            return []

    # ── VOLUME / ACTIVE / 52HIGH / 52LOW ─────────────────────────────────────
    # Use NIFTY 500 index constituents and sort by relevant metric
    page_map2 = {
        'volume':  'https://www.nseindia.com/market-data/volume-gainers-spurts',
        'active':  'https://www.nseindia.com/market-data/most-active-equities',
        '52high':  'https://www.nseindia.com/market-data/52-week-high-equity-market',
        '52low':   'https://www.nseindia.com/market-data/52-week-low-equity-market',
    }
    try:
        NSE_SESSION.get(page_map2.get(dtype, 'https://www.nseindia.com'), timeout=8)
        r = NSE_SESSION.get(
            "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20500",
            timeout=15)
        if r.status_code != 200: return []
        raw_items = r.json().get('data', [])
        rows = []
        for item in raw_items:
            sym = (item.get('symbol') or '').strip()
            if not sym or sym == 'NIFTY 500': continue
            ltp  = _safe_float(item.get('lastPrice'))
            prev = _safe_float(item.get('previousClose'))
            chg  = _safe_float(item.get('pChange')) or _pct(ltp, prev)
            vol  = _safe_float(item.get('totalTradedVolume')) or 0
            high52 = _safe_float(item.get('yearHigh'))
            low52  = _safe_float(item.get('yearLow'))
            rows.append({
                'symbol':     sym,
                'company':    item.get('meta', {}).get('companyName', sym) if isinstance(item.get('meta'), dict) else sym,
                'ltp':        ltp or 0,
                'change_pct': chg or 0,
                'volume':     vol,
                'high52':     high52,
                'low52':      low52,
            })

        if dtype == 'volume':
            rows.sort(key=lambda x: x['volume'], reverse=True)
        elif dtype == 'active':
            rows.sort(key=lambda x: abs(x['change_pct']), reverse=True)
        elif dtype == '52high':
            # Near 52W high — sort by proximity to 52W high
            def near_high(r):
                if r['high52'] and r['ltp']:
                    return (r['ltp'] / r['high52']) * 100
                return 0
            rows = [r for r in rows if r['high52'] and r['ltp'] and r['ltp'] >= r['high52'] * 0.95]
            rows.sort(key=near_high, reverse=True)
        elif dtype == '52low':
            def near_low(r):
                if r['low52'] and r['ltp']:
                    return (r['ltp'] / r['low52']) * 100
                return 999
            rows = [r for r in rows if r['low52'] and r['ltp'] and r['ltp'] <= r['low52'] * 1.05]
            rows.sort(key=near_low)

        return rows[:50]
    except Exception as ex:
        print(f"[market-{dtype}] {ex}")
        return []

@app.route('/api/indices')
def api_indices():
    try: return jsonify(_fetch_all_indices())
    except Exception as e: return jsonify({'error':str(e)}),500

@app.route('/api/index-stocks')
def api_index_stocks():
    idx=request.args.get('index','').strip()
    if not idx: return jsonify([])
    try:
        NSE_SESSION.get("https://www.nseindia.com",timeout=8)
        enc=_req.utils.quote(idx)
        r=NSE_SESSION.get(f"https://www.nseindia.com/api/equity-stockIndices?index={enc}",timeout=15)
        if r.status_code!=200: return jsonify([])
        rows=[]
        for item in r.json().get('data',[]):
            sym=(item.get('symbol') or '').strip()
            if not sym or sym==idx: continue
            try: chg=float(item.get('pChange',item.get('perChange',0)))
            except: chg=0.0
            try: ltp=float(str(item.get('lastPrice',item.get('ltp',0))).replace(',',''))
            except: ltp=0.0
            rows.append({'symbol':sym,'ltp':ltp,'chg':chg})
        return jsonify(rows)
    except Exception as e: return jsonify({'error':str(e)}),500

@app.route('/api/chartink-list')
def api_chartink_list():
    return jsonify([
        {'slug':'fresh-52-week-highs','label':'🏔️ 52W High','color':'#00E6A8'},
        {'slug':'52-week-high-breakout','label':'📈 52W High Breakout','color':'#4D8EFF'},
        {'slug':'copy-stock-near-5-of-52-week-high-36691','label':'📊 Near 52W High','color':'#9B6FE8'},
        {'slug':'claude-swing-trading-screener','label':'🔵 Swing Scanner','color':'#4D8EFF'},
        {'slug':'claude-positinal-screener','label':'🟡 Positional Scanner','color':'#FFD700'},
        {'slug':'claude-long-term','label':'🟢 Long Term Scanner','color':'#00E6A8'},
        {'slug':'44-ma-swing-stocks-3','label':'📐 44 MA Scanner','color':'#FF9500'},
        {'slug':'copy-rb-stockexploder-322','label':'🚀 Rocket Base','color':'#FF3D5C'},
        {'slug':'copy-vcp-stockexploder-223','label':'🌀 VCP Scanner','color':'#9B6FE8'},
        {'slug':'copy-breakouts-in-short-term-5280','label':'💥 Breakout Short Term','color':'#FF9500'},
        {'slug':'badiya-vala-scanner','label':'⭐ Badiya Scanner','color':'#FFD700'},
        {'slug':'swing-scanner-20102336','label':'🔍 Swing Scanner 2','color':'#4D8EFF'},
    ])

@app.route('/api/chartink/<slug>')
def api_chartink(slug):
    try: return jsonify(fetch_chartink(f"https://chartink.com/screener/{slug}"))
    except Exception as e: return jsonify({'error':str(e)}),500

@app.route('/api/etf/list')
def api_etf_list():
    try:
        etfs = fetch_nse_etf_list()
        etfs.sort(key=lambda x: x.get('chg', 0), reverse=True)
        for e in etfs:
            e['index_cat'] = _etf_index_category(e.get('symbol',''), e.get('name',''))
        return jsonify(etfs)
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/etf/screener')
def api_etf_screener():
    try: return jsonify(fetch_nse_etf_screener())
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/etf/rsi-screener')
def api_etf_rsi_screener():
    """ETFs where RSI just crossed above 50 — uses Chartink for speed.
    Chartink se RSI 50 crossover stocks fetch karo, phir ETF list se filter karo.
    Actual RSI values yfinance se calculate karo (sirf matched ETFs ke liye — fast)."""
    try:
        import yfinance as yf

        # Step 1: Chartink se RSI 50 crossover stocks fetch karo
        chartink_results = fetch_chartink("https://chartink.com/screener/etf-50-rsi-crossover")
        if not chartink_results:
            return jsonify({'error': 'Chartink se data nahi mila — cookies expire ho gayi hain'}), 503

        # Step 2: NSE ETF list fetch karo (symbols set)
        all_etfs = fetch_nse_etf_list()
        etf_map  = {e['symbol'].upper(): e for e in all_etfs}

        # Step 3: Chartink results mein se sirf ETF symbols rakhna
        matched = []
        for row in chartink_results:
            sym = (row.get('symbol') or row.get('nsecode') or '').upper().strip()
            if not sym: continue
            etf_data = etf_map.get(sym)
            if not etf_data: continue  # Not an ETF — skip
            matched.append({'sym': sym, 'etf': etf_data, 'row': row})

        print(f"[ETF RSI] Chartink: {len(chartink_results)} stocks → {len(matched)} ETFs matched")

        # Step 4: Actual RSI values fetch karo (sirf matched ETFs ke liye)
        results = []
        if matched:
            syms_ns = [f"{m['sym']}.NS" for m in matched]
            try:
                hist_data = yf.download(syms_ns, period='2mo', interval='1d',
                                        auto_adjust=True, progress=False, group_by='ticker')
            except: hist_data = None

            def _rsi(closes, p=14):
                if len(closes) < p+2: return None
                d = [closes[i]-closes[i-1] for i in range(1,len(closes))]
                g = [max(x,0) for x in d]; l = [abs(min(x,0)) for x in d]
                ag = sum(g[:p])/p; al = sum(l[:p])/p
                for i in range(p,len(d)):
                    ag=(ag*(p-1)+g[i])/p; al=(al*(p-1)+l[i])/p
                return round(100-(100/(1+ag/al)),1) if al>0 else 100.0

            for m in matched:
                sym = m['sym']; etf_data = m['etf']; row = m['row']
                rsi_now = rsi_prev = None
                try:
                    if hist_data is not None:
                        sym_ns = f"{sym}.NS"
                        if hasattr(hist_data.columns, 'levels'):
                            closes = hist_data[sym_ns]['Close'].dropna().values.astype(float)
                        elif len(matched) == 1:
                            closes = hist_data['Close'].dropna().values.astype(float)
                        else: closes = []
                        if len(closes) >= 16:
                            rsi_now  = _rsi(closes)
                            rsi_prev = _rsi(closes[:-1])
                except: pass

                ltp = etf_data.get('ltp') or row.get('ltp') or row.get('close') or 0
                chg = etf_data.get('chg') or row.get('per_chg') or 0
                vol = etf_data.get('vol') or row.get('volume') or 0

                # Signal with actual RSI values
                if rsi_now and rsi_prev:
                    signal = f'RSI {rsi_prev:.1f} → {rsi_now:.1f} (crossed 50 ✅)'
                else:
                    signal = 'RSI crossed above 50 ✅'

                results.append({
                    'symbol':    sym,
                    'name':      etf_data.get('name', sym),
                    'ltp':       ltp,
                    'chg':       chg,
                    'vol':       vol,
                    'index_cat': _etf_index_category(sym, etf_data.get('name', '')),
                    'rsi':       rsi_now or '>50',
                    'rsi_prev':  rsi_prev or '<50',
                    'signal':    signal,
                })

        results.sort(key=lambda x: float(x.get('chg') or 0), reverse=True)
        return jsonify(results)

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/etf/scanner')
def api_etf_scanner():
    """ETF Scanner — Volume > 100K, Close > EMA50, RSI > 55, Breakout"""
    try:
        chartink_results = fetch_chartink("https://chartink.com/screener/etf-scanner-7993")
        if not chartink_results:
            return jsonify({'error': 'Chartink se data nahi mila — cookies expire ho gayi hain'}), 503
        all_etfs = fetch_nse_etf_list()
        etf_map  = {e['symbol'].upper(): e for e in all_etfs}
        results  = []
        for row in chartink_results:
            sym = (row.get('symbol') or row.get('nsecode') or '').upper().strip()
            if not sym: continue
            etf_data = etf_map.get(sym)
            if not etf_data: continue
            ltp = etf_data.get('ltp') or row.get('ltp') or row.get('close') or 0
            chg = etf_data.get('chg') or row.get('per_chg') or 0
            vol = etf_data.get('vol') or row.get('volume') or 0
            results.append({
                'symbol':    sym,
                'name':      etf_data.get('name', sym),
                'ltp':       ltp,
                'chg':       chg,
                'vol':       vol,
                'index_cat': _etf_index_category(sym, etf_data.get('name', '')),
                'signal':    'Vol>100K + Close>EMA50 + RSI>55 + Breakout ✅',
            })
        results.sort(key=lambda x: float(x.get('chg') or 0), reverse=True)
        print(f"[ETF Scanner] Chartink: {len(chartink_results)} → {len(results)} ETFs")
        return jsonify(results)
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def _etf_index_category(symbol, name):
    """Detect which index/category an ETF belongs to based on symbol/name"""
    s = (symbol + ' ' + name).upper()
    if any(x in s for x in ['NIFTY50','NIFTY 50','N50','NIFTYBEES','JUNIORBEES']): return 'NIFTY 50'
    if any(x in s for x in ['NEXT50','NIFTYNXT','JUNIOR','NXTSMALL']): return 'NIFTY NEXT 50'
    if any(x in s for x in ['BANKBEES','BANKNIFTY','BANK','BANKIETF','PSUBNKBEES']): return 'BANK'
    if any(x in s for x in ['ITBEES','NIFTYIT','TECH','IT ETF','ITETF']): return 'IT'
    if any(x in s for x in ['MIDCAP','MID150','MID100','MIDSMALL','MAFANG']): return 'MIDCAP'
    if any(x in s for x in ['SMALLCAP','SMALL250','SMLCAP']): return 'SMALLCAP'
    if any(x in s for x in ['PHARMA','HEALTH','MEDICO']): return 'PHARMA'
    if any(x in s for x in ['FMCG','CONSUMPTION','CONSUM']): return 'FMCG'
    if any(x in s for x in ['AUTO','AUTOBEES']): return 'AUTO'
    if any(x in s for x in ['INFRA','INFRASTRUCTURE']): return 'INFRA'
    if any(x in s for x in ['METAL','STEEL']): return 'METAL'
    if any(x in s for x in ['ENERGY','OIL','GAS','POWER']): return 'ENERGY'
    if any(x in s for x in ['REALTY','REAL ESTATE']): return 'REALTY'
    if any(x in s for x in ['GOLD','GOLDBEES','SGOLD','GOLDCASE']): return 'GOLD'
    if any(x in s for x in ['SILVER','SILVERBEES']): return 'SILVER'
    if any(x in s for x in ['LIQUID','OVERNIGHT','MONEY','CASH']): return 'LIQUID'
    if any(x in s for x in ['DEBT','BOND','GILT','GSEC','BHARAT']): return 'DEBT'
    if any(x in s for x in ['NASDAQ','US','WORLD','GLOBAL','HANG','CHINA']): return 'INTL'
    if any(x in s for x in ['PSU','CPSE','GOVT']): return 'PSU'
    if any(x in s for x in ['DIVIDEND','DIV']): return 'DIVIDEND'
    if any(x in s for x in ['MOMENTUM','ALPHA','QUALITY','VALUE','LOWVOL']): return 'FACTOR'
    return 'OTHER'

@app.route('/api/news/<sym>')
def api_news(sym):
    sym=sym.upper(); news=[]; docs=[]
    try:
        NSE_SESSION.get("https://www.nseindia.com",timeout=8)
        NSE_SESSION.get(f"https://www.nseindia.com/get-quote/equity/{sym}",timeout=8)
    except: pass
    try:
        r=NSE_SESSION.get(f"https://www.nseindia.com/api/corp-info?symbol={sym}&corpType=announcement&market=equities",timeout=12)
        if r.status_code==200:
            raw=r.json(); items=raw if isinstance(raw,list) else raw.get('data',[])
            for item in (items or [])[:6]:
                title=(item.get('subject') or item.get('desc') or '').strip()
                date=(item.get('exchdisstime') or '')[:10]
                att=(item.get('attchmntFile') or '').strip()
                link=(att if att.startswith('http') else f"https://nsearchives.nseindia.com{att}") if att else f"https://www.nseindia.com/get-quotes/equity?symbol={sym}"
                if title: news.append({'title':title[:90],'date':date,'link':link})
    except: pass
    try:
        r=NSE_SESSION.get(f"https://www.nseindia.com/api/annual-reports?index=equities&symbol={sym}",timeout=12)
        if r.status_code==200:
            raw=r.json(); reports=raw.get('data',raw) if isinstance(raw,dict) else raw
            for rep in (reports or [])[:3]:
                fname=(rep.get('fileName') or '').strip()
                label=f"FY {rep.get('fromYr','')}-{rep.get('toYr','')}"
                if fname and fname.startswith('http'):
                    docs.append({'title':f"Annual Report {label}",'link':fname})
    except: pass
    return jsonify({'news':news,'docs':docs})

@app.route('/api/ipo')
def api_ipo():
    try: return jsonify(_fetch_ipo_data_internal())
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error':str(e)}),500

@app.route('/api/watchlist',methods=['GET'])
def api_watchlist_get():
    return jsonify(_user_data().get('watchlist',{}))

@app.route('/api/watchlist/<sym>',methods=['POST','DELETE'])
def api_watchlist_sym(sym):
    sym=sym.upper().strip()
    ud=_user_data()
    if request.method=='DELETE':
        ud.setdefault('watchlist',{}).pop(sym,None)
        _save_user_data(ud); return jsonify({'ok':True})
    body=request.get_json(silent=True) or {}
    ud.setdefault('watchlist',{})[sym]={
        'sym':sym,'name':body.get('name',sym),
        'price':body.get('price'),'sector':body.get('sector',''),
        'added':datetime.date.today().isoformat(),
    }
    _save_user_data(ud); return jsonify({'ok':True})

@app.route('/api/notes/<sym>',methods=['GET','POST'])
def api_notes(sym):
    sym=sym.upper().strip(); ud=_user_data()
    if request.method=='GET':
        return jsonify(ud.get('notes',{}).get(sym,{'note':'','trades':[]}))
    body=request.get_json(silent=True) or {}
    ud.setdefault('notes',{})[sym]=body
    _save_user_data(ud); return jsonify({'ok':True})

# ── Trade Log routes ──────────────────────────────────────────────────────────
@app.route('/api/trades')
def api_trades_all():
    all_trades=_user_data().get('trades',{})
    flat=[]
    for sym,trades in all_trades.items():
        for t in trades: flat.append({**t,'sym':sym})
    flat.sort(key=lambda x:x.get('logged',''),reverse=True)
    return jsonify(flat)

@app.route('/api/trades/<sym>',methods=['GET'])
def api_trades_get(sym):
    return jsonify(_user_data().get('trades',{}).get(sym.upper(),[]))

@app.route('/api/trades/<sym>',methods=['POST'])
def api_trades_add(sym):
    sym=sym.upper(); ud=_user_data()
    data=request.get_json(silent=True) or {}
    trades=ud.setdefault('trades',{}).setdefault(sym,[])
    data['logged']=datetime.datetime.now().isoformat()
    trades.insert(0,data); _save_user_data(ud)
    return jsonify({'ok':True,'count':len(trades)})

@app.route('/api/trades/<sym>/<int:idx>',methods=['DELETE'])
def api_trades_del(sym,idx):
    sym=sym.upper(); ud=_user_data()
    trades=ud.get('trades',{}).get(sym,[])
    if 0<=idx<len(trades):
        trades.pop(idx)
        if not trades: ud.get('trades',{}).pop(sym,None)
        _save_user_data(ud); return jsonify({'ok':True})
    return jsonify({'error':'not found'}),404

# ── Trade Alerts (server-side persistent) ────────────────────────────────────
@app.route('/api/trade_alerts', methods=['GET'])
def api_trade_alerts_get():
    """Get all trade alerts for current user"""
    return jsonify(_user_data().get('trade_alerts', []))

@app.route('/api/trade_alerts', methods=['POST'])
def api_trade_alerts_add():
    """Add a new trade alert"""
    ud = _user_data()
    data = request.get_json(silent=True) or {}
    sym = (data.get('sym') or '').upper().strip()
    price = data.get('price')
    cond = data.get('cond', 'above')  # above / below
    note = data.get('note', '')
    alert_type = data.get('type', 'price')  # price / target / stoploss
    if not sym or price is None:
        return jsonify({'error': 'sym aur price required'}), 400
    try: price = float(price)
    except: return jsonify({'error': 'Invalid price'}), 400
    alert = {
        'id': secrets.token_hex(6),
        'sym': sym,
        'price': price,
        'cond': cond,
        'type': alert_type,
        'note': note,
        'is_fno': sym in FNO_STOCKS,
        'triggered': False,
        'triggered_at': None,
        'created': datetime.datetime.now().isoformat(),
    }
    alerts = ud.setdefault('trade_alerts', [])
    alerts.insert(0, alert)
    _save_user_data(ud)
    return jsonify({'ok': True, 'alert': alert})

@app.route('/api/trade_alerts/<alert_id>', methods=['DELETE'])
def api_trade_alerts_del(alert_id):
    """Delete a trade alert by id"""
    ud = _user_data()
    alerts = ud.get('trade_alerts', [])
    new_alerts = [a for a in alerts if a.get('id') != alert_id]
    if len(new_alerts) == len(alerts):
        return jsonify({'error': 'Alert not found'}), 404
    ud['trade_alerts'] = new_alerts
    _save_user_data(ud)
    return jsonify({'ok': True})

@app.route('/api/trade_alerts/<alert_id>/reset', methods=['POST'])
def api_trade_alerts_reset(alert_id):
    """Reset a triggered alert back to active"""
    ud = _user_data()
    for a in ud.get('trade_alerts', []):
        if a.get('id') == alert_id:
            a['triggered'] = False
            a['triggered_at'] = None
            _save_user_data(ud)
            return jsonify({'ok': True})
    return jsonify({'error': 'Alert not found'}), 404

@app.route('/api/trade_alerts/<alert_id>/trigger', methods=['POST'])
def api_trade_alerts_trigger(alert_id):
    """Mark alert as triggered (called from frontend when price hit)"""
    ud = _user_data()
    body = request.get_json(silent=True) or {}
    ltp = body.get('ltp')
    for a in ud.get('trade_alerts', []):
        if a.get('id') == alert_id and not a.get('triggered'):
            a['triggered'] = True
            a['triggered_at'] = ltp
            a['triggered_time'] = datetime.datetime.now().isoformat()
            _save_user_data(ud)
            return jsonify({'ok': True})
    return jsonify({'ok': False, 'reason': 'not found or already triggered'})# ── User data sync API ────────────────────────────────────────────────────────
@app.route('/api/userdata', methods=['GET'])
def api_userdata_get():
    """Get all user data for sync"""
    return jsonify(_user_data())

@app.route('/api/userdata', methods=['POST'])
def api_userdata_set():
    """Save all user data (full replace — for sync from browser)"""
    body = request.get_json(silent=True) or {}
    if body:
        _save_user_data(body)
    return jsonify({'ok': True})

# ── Sparkline for watchlist ───────────────────────────────────────────────────
@app.route('/api/sparkline/<sym>')
def api_sparkline(sym):
    try:
        import yfinance as yf
        hist=yf.download(f"{sym.upper()}.NS",period="30d",interval="1d",auto_adjust=True,progress=False)
        if hist is None or hist.empty: return jsonify([])
        if hasattr(hist.columns,'levels'): hist.columns=hist.columns.get_level_values(0)
        closes=hist['Close'].dropna().values.astype(float).tolist()
        return jsonify([round(c,2) for c in closes])
    except: return jsonify([])

# ══════════════════════════════════════════════════════════════════════════════
# SCREENER.IN SAVED SCREENS — Swing / Positional / Long Term + Explore
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/screener/status')
def api_screener_status():
    """Screener progress + cookie status"""
    prog = _get_screener_progress()
    prog['cookies_ok'] = _screener_cookies_valid()
    return jsonify(prog)

@app.route('/api/screener/results')
def api_screener_results():
    """Return cached screener results (swing/positional/longterm)"""
    results = _load_screener_results()
    if not results:
        return jsonify({'swing': [], 'positional': [], 'longterm': [],
                        'timestamp': None, 'total_scanned': 0})
    return jsonify(results)

@app.route('/api/screener/start', methods=['POST'])
def api_screener_start():
    """Start a fresh screener.in scan in background"""
    prog = _get_screener_progress()
    if prog.get('running'):
        return jsonify({'ok': False, 'message': 'Scan already running'})

    def _run():
        _run_screener_in()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({'ok': True, 'message': 'Scan started'})

@app.route('/api/screener/explore')
def api_screener_explore_list():
    """List all available explore screens"""
    screens = []
    for key, (label, url) in EXPLORE_SCREENS.items():
        screens.append({'key': key, 'label': label, 'url': url})
    return jsonify(screens)

@app.route('/api/screener/explore/<key>')
def api_screener_explore_fetch(key):
    """Fetch a specific explore screen (cached 6h)"""
    import datetime as _dt
    if key not in EXPLORE_SCREENS:
        return jsonify({'error': f'Unknown screen: {key}'}), 404

    # Check cache
    cached = _explore_cache.get(key)
    if cached:
        age = (_dt.datetime.now() - cached['ts']).total_seconds()
        if age < 6 * 3600:
            return jsonify({'key': key, 'label': EXPLORE_SCREENS[key][0],
                            'stocks': cached['data'], 'cached': True})

    stocks = fetch_explore_screen(key)
    if stocks is None:
        return jsonify({'error': 'Screener.in cookies expired — screener_scraper.py mein update karo'}), 503

    _explore_cache[key] = {'data': stocks, 'ts': _dt.datetime.now()}
    return jsonify({'key': key, 'label': EXPLORE_SCREENS[key][0],
                    'stocks': stocks, 'cached': False})

# ══════════════════════════════════════════════════════════════════════════════
# INTRADAY & OPTIONS — NSE Option Chain + Signals
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/intraday/candles')
def api_intraday_candles():
    """yfinance se intraday candles — 1m/5m/15m/1h"""
    sym = request.args.get('sym', 'NIFTY').upper().strip()
    tf  = request.args.get('tf', '5m')   # 3m/5m/15m/1h

    tf_map = {'3m':'2m','5m':'5m','15m':'15m','1h':'60m'}
    period_map = {'3m':'1d','5m':'1d','15m':'5d','1h':'5d'}
    yf_tf  = tf_map.get(tf, '5m')
    period = period_map.get(tf, '1d')

    # Index symbols
    idx_map = {
        'NIFTY':'^NSEI','BANKNIFTY':'^NSEBANK',
        'FINNIFTY':'NIFTY_FIN_SERVICE.NS','SENSEX':'^BSESN',
    }
    yf_sym = idx_map.get(sym, f'{sym}.NS')

    try:
        import yfinance as yf
        hist = yf.download(yf_sym, period=period, interval=yf_tf,
                           auto_adjust=True, progress=False)
        if hist is None or hist.empty:
            return jsonify({'error': f'{sym} ka data nahi mila'}), 404

        if hasattr(hist.columns, 'levels'):
            hist.columns = hist.columns.get_level_values(0)
        try:
            hist.index = hist.index.tz_localize(None) if hist.index.tzinfo else hist.index
        except: pass

        hist = hist.dropna(subset=['Close'])
        candles = []
        for ts, row in hist.iterrows():
            candles.append({
                't': ts.strftime('%H:%M'),
                'o': round(float(row['Open']),  2),
                'h': round(float(row['High']),  2),
                'l': round(float(row['Low']),   2),
                'c': round(float(row['Close']), 2),
                'v': int(row.get('Volume', 0) or 0),
            })
        return jsonify({'sym': sym, 'tf': tf, 'candles': candles[-100:]})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/intraday/signals')
def api_intraday_signals():
    """Full intraday signal analysis — Upstox for all symbols (indices + stocks), yfinance fallback"""
    sym = request.args.get('sym', 'NIFTY').upper().strip()
    tf  = request.args.get('tf', '15m')

    import numpy as np, math

    candles_rs = None
    data_source = 'unknown'

    # ── Try Upstox first (works for indices + all NSE EQ stocks) ─────────────
    if _upstox_token:
        ikey = _get_instrument_key(sym)
        if ikey:
            import requests as _rq
            ikey_enc = ikey.replace('|', '%7C').replace(' ', '%20')
            try:
                r = _rq.get(
                    f'https://api.upstox.com/v2/historical-candle/intraday/{ikey_enc}/1minute',
                    headers=_upstox_headers(), timeout=15)
                if r.status_code == 200:
                    raw = r.json().get('data', {}).get('candles', [])
                    if raw:
                        tf_mins = {'3m': 3, '5m': 5, '15m': 15, '1h': 60}.get(tf, 15)
                        raw.reverse()  # oldest first

                        def resample(candles, mins):
                            if mins == 1: return candles
                            out = []; buf = []
                            for c in candles:
                                buf.append(c)
                                if len(buf) >= mins:
                                    out.append([buf[0][0], buf[0][1],
                                        max(x[2] for x in buf), min(x[3] for x in buf),
                                        buf[-1][4], sum(x[5] for x in buf), buf[-1][6]])
                                    buf = []
                            if buf:
                                out.append([buf[0][0], buf[0][1],
                                    max(x[2] for x in buf), min(x[3] for x in buf),
                                    buf[-1][4], sum(x[5] for x in buf), buf[-1][6]])
                            return out

                        candles_rs = resample(raw, tf_mins)
                        data_source = 'Upstox'
                elif r.status_code == 400:
                    print(f'[Upstox signals] 400 for {sym} ({ikey}): {r.text[:120]}')
            except Exception as ex:
                print(f'[Upstox signals] {sym}: {ex}')
        else:
            print(f'[Upstox] No instrument key for {sym} — falling back to yfinance')

    # ── yfinance fallback ─────────────────────────────────────────────────────
    if not candles_rs:
        try:
            import yfinance as yf
            tf_map     = {'3m': '2m', '5m': '5m', '15m': '15m', '1h': '60m'}
            period_map = {'3m': '1d', '5m': '1d',  '15m': '5d',  '1h': '5d'}
            yf_tf  = tf_map.get(tf, '15m')
            period = period_map.get(tf, '5d')
            idx_map = {
                'NIFTY': '^NSEI', 'BANKNIFTY': '^NSEBANK',
                'FINNIFTY': 'NIFTY_FIN_SERVICE.NS', 'SENSEX': '^BSESN',
                'MIDCPNIFTY': 'NIFTY_MID_SELECT.NS',
            }
            yf_sym = idx_map.get(sym, f'{sym}.NS')
            hist = yf.download(yf_sym, period=period, interval=yf_tf,
                               auto_adjust=True, progress=False)
            if hist is None or hist.empty:
                return jsonify({'error': f'{sym} ka data nahi mila — symbol check karo'}), 404
            if hasattr(hist.columns, 'levels'):
                hist.columns = hist.columns.get_level_values(0)
            try:
                hist.index = hist.index.tz_localize(None) if hist.index.tzinfo else hist.index
            except: pass
            hist = hist.dropna(subset=['Close', 'High', 'Low'])
            if len(hist) < 5:
                return jsonify({'error': f'{sym} ka data bahut kam — market band hoga'}), 404
            # Convert to candles_rs format: [ts, open, high, low, close, volume, 0]
            candles_rs = []
            for i, row in hist.iterrows():
                candles_rs.append([
                    str(i), float(row.get('Open', row['Close'])),
                    float(row['High']), float(row['Low']),
                    float(row['Close']),
                    float(row.get('Volume', 0)), 0
                ])
        except Exception as ex:
            import traceback; traceback.print_exc()
            return jsonify({'error': f'Data fetch failed: {str(ex)}'}), 500

    if not candles_rs or len(candles_rs) < 5:
        return jsonify({'error': f'{sym} ka data nahi mila — market band hoga ya symbol galat hai'}), 404

    try:
        c = np.array([x[4] for x in candles_rs], dtype=float)
        h = np.array([x[2] for x in candles_rs], dtype=float)
        l = np.array([x[3] for x in candles_rs], dtype=float)
        o = np.array([x[1] for x in candles_rs], dtype=float)
        v = np.array([x[5] for x in candles_rs], dtype=float)
        n = len(c)

        def ema(arr, p):
            k = 2/(p+1); e = [arr[0]]
            for x in arr[1:]: e.append(x*k + e[-1]*(1-k))
            return np.array(e)

        def rsi(arr, p=14):
            d = np.diff(arr)
            g = np.where(d>0,d,0); ls = np.where(d<0,-d,0)
            ag = np.mean(g[:p]); al = np.mean(ls[:p])
            for i in range(p, len(d)):
                ag=(ag*(p-1)+g[i])/p; al=(al*(p-1)+ls[i])/p
            return round(100-100/(1+ag/al),1) if al>0 else 100.0

        ema9=ema(c,9); ema21=ema(c,21)
        rsi_val = rsi(c) if n > 14 else 50.0

        # VWAP
        tp = (h+l+c)/3
        cum_vol = np.cumsum(v)
        vwap = round(float(np.sum(tp*v)/cum_vol[-1]),2) if cum_vol[-1]>0 else None

        # Supertrend
        atr_p=10; mult=3.0
        tr = np.array([max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) for i in range(1,n)])
        atr_arr=np.zeros(n); atr_arr[1]=tr[0] if len(tr)>0 else 0
        for i in range(2,n): atr_arr[i]=(atr_arr[i-1]*(atr_p-1)+tr[i-1])/atr_p
        ub=(h+l)/2+mult*atr_arr; lb=(h+l)/2-mult*atr_arr
        trend=np.ones(n)
        for i in range(1,n):
            if c[i]>ub[i-1]: trend[i]=1
            elif c[i]<lb[i-1]: trend[i]=-1
            else: trend[i]=trend[i-1]
        st=np.where(trend==1,lb,ub)
        st_signal='BUY' if trend[-1]==1 else 'SELL'
        st_val=round(float(st[-1]),2)

        # MACD
        ema12=ema(c,12); ema26=ema(c,26)
        macd_line=ema12-ema26
        sig_line=ema(macd_line[25:],9) if n>25 else np.array([0])
        macd_val=round(float(macd_line[-1]),2); sig_val=round(float(sig_line[-1]),2)
        macd_cross='Bullish' if macd_val>sig_val else 'Bearish'

        # ORB
        orb=None
        if n>=3:
            orb_h=float(np.max(h[:3])); orb_l=float(np.min(l[:3]))
            cur=float(c[-1])
            orb_status='ABOVE ORB 🚀' if cur>orb_h else ('BELOW ORB 📉' if cur<orb_l else 'INSIDE ORB ⏳')
            orb={'high':round(orb_h,2),'low':round(orb_l,2),'status':orb_status}

        # BB
        bb_mid=bb_upper=bb_lower=bb_pct=None
        if n>=20:
            w=c[-20:]; bb_mid=round(float(np.mean(w)),2); bb_std=float(np.std(w))
            bb_upper=round(bb_mid+2*bb_std,2); bb_lower=round(bb_mid-2*bb_std,2)
            rng=bb_upper-bb_lower
            bb_pct=round((float(c[-1])-bb_lower)/rng*100,1) if rng>0 else 50

        avg_vol=float(np.mean(v[-20:])) if n>=20 else float(np.mean(v))
        vol_ratio=round(float(v[-1])/avg_vol,2) if avg_vol>0 else 1.0
        atr_val=round(float(atr_arr[-1]),2)
        cur=float(c[-1])

        # Score
        score=0; bull=[]; bear=[]
        if 40<=rsi_val<=65: score+=20; bull.append(f'RSI {rsi_val} — momentum zone')
        elif rsi_val>65: score+=8; bear.append(f'RSI {rsi_val} — overbought')
        elif rsi_val<35: score+=5; bear.append(f'RSI {rsi_val} — oversold')
        else: score+=10
        if float(ema9[-1])>float(ema21[-1]): score+=20; bull.append('EMA9 > EMA21 — bullish')
        else: bear.append('EMA9 < EMA21 — bearish')
        if vwap:
            if cur>vwap: score+=20; bull.append(f'Price above VWAP ({vwap})')
            else: score+=5; bear.append(f'Price below VWAP ({vwap})')
        if st_signal=='BUY': score+=25; bull.append(f'Supertrend BUY @ {st_val}')
        else: bear.append(f'Supertrend SELL @ {st_val}')
        if macd_cross=='Bullish': score+=15; bull.append('MACD bullish')
        else: bear.append('MACD bearish')
        score=min(score,100)

        if score>=75: verdict='STRONG BUY'; vtype='strong_buy'; hint='CALL option consider karo'
        elif score>=60: verdict='BUY'; vtype='buy'; hint='CALL option — confirm karo pehle'
        elif score<=25: verdict='STRONG SELL'; vtype='strong_sell'; hint='PUT option consider karo'
        elif score<=40: verdict='SELL / AVOID'; vtype='sell'; hint='PUT option — confirm karo pehle'
        else: verdict='NEUTRAL / WAIT'; vtype='neutral'; hint='Sideline raho — clear signal nahi'

        sl_buy=round(cur-1.5*atr_val,2); tgt_buy=round(cur+2*atr_val,2)
        sl_sell=round(cur+1.5*atr_val,2); tgt_sell=round(cur-2*atr_val,2)

        chart_candles=[]
        for i in range(max(0,n-60),n):
            ts = candles_rs[i][0]
            if hasattr(ts, 'strftime'): ts = ts.strftime('%H:%M')
            elif isinstance(ts, str): ts = ts[:16].replace('T',' ').replace('+05:30','')
            chart_candles.append({
                't': ts, 'o':round(float(o[i]),2),'h':round(float(h[i]),2),
                'l':round(float(l[i]),2),'c':round(float(c[i]),2),
                'v':int(v[i]),
                'ema9':round(float(ema9[i]),2),'ema21':round(float(ema21[i]),2),
                'st':round(float(st[i]),2),'st_up':bool(trend[i]==1),'vwap':vwap,
            })

        data_source = 'Upstox' if data_source == 'Upstox' else 'yfinance'
        return jsonify({
            'sym':sym,'tf':tf,'cur':round(cur,2),
            'rsi':rsi_val,'ema9':round(float(ema9[-1]),2),'ema21':round(float(ema21[-1]),2),
            'vwap':vwap,'macd':macd_val,'macd_signal':sig_val,'macd_cross':macd_cross,
            'supertrend':st_val,'supertrend_signal':st_signal,
            'bb_upper':bb_upper,'bb_lower':bb_lower,'bb_mid':bb_mid,'bb_pct':bb_pct,
            'atr':atr_val,'vol_ratio':vol_ratio,'orb':orb,'score':score,
            'verdict':verdict,'verdict_type':vtype,'option_hint':hint,
            'bull_reasons':bull,'bear_reasons':bear,
            'sl_buy':sl_buy,'tgt_buy':tgt_buy,'sl_sell':sl_sell,'tgt_sell':tgt_sell,
            'candles':chart_candles,'data_source':data_source,
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500

        # raw format: [timestamp, open, high, low, close, volume, oi]
        # Resample to requested timeframe
        tf_mins = {'3m': 3, '5m': 5, '15m': 15, '1h': 60}.get(tf, 15)
        raw.reverse()  # oldest first

        def resample(candles, mins):
            if mins == 1: return candles
            out = []
            buf = []
            for c in candles:
                buf.append(c)
                if len(buf) >= mins:
                    out.append([
                        buf[0][0],
                        buf[0][1],           # open
                        max(x[2] for x in buf),  # high
                        min(x[3] for x in buf),  # low
                        buf[-1][4],          # close
                        sum(x[5] for x in buf),  # volume
                        buf[-1][6],          # oi
                    ])
                    buf = []
            if buf:  # partial last candle
                out.append([buf[0][0], buf[0][1], max(x[2] for x in buf),
                            min(x[3] for x in buf), buf[-1][4],
                            sum(x[5] for x in buf), buf[-1][6]])
            return out

        candles_rs = resample(raw, tf_mins)
        if len(candles_rs) < 20:
            return jsonify({'error': f'Data bahut kam ({len(candles_rs)} candles) — 15m ya 1h try karo'}), 400

        c = np.array([x[4] for x in candles_rs], dtype=float)
        h = np.array([x[2] for x in candles_rs], dtype=float)
        l = np.array([x[3] for x in candles_rs], dtype=float)
        o = np.array([x[1] for x in candles_rs], dtype=float)
        v = np.array([x[5] for x in candles_rs], dtype=float)
        n = len(c)

        def ema(arr, p):
            k = 2/(p+1); e = [arr[0]]
            for x in arr[1:]: e.append(x*k + e[-1]*(1-k))
            return np.array(e)

        def rsi(arr, p=14):
            d = np.diff(arr)
            g = np.where(d>0,d,0); ls = np.where(d<0,-d,0)
            ag = np.mean(g[:p]); al = np.mean(ls[:p])
            for i in range(p, len(d)):
                ag=(ag*(p-1)+g[i])/p; al=(al*(p-1)+ls[i])/p
            return round(100-100/(1+ag/al),1) if al>0 else 100.0

        ema9=ema(c,9); ema21=ema(c,21)
        rsi_val = rsi(c)

        # VWAP (today)
        tp = (h+l+c)/3
        cum_vol = np.cumsum(v)
        vwap = round(float(np.sum(tp*v)/cum_vol[-1]),2) if cum_vol[-1]>0 else None

        # Supertrend
        atr_p=10; mult=3.0
        tr = np.array([max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) for i in range(1,n)])
        atr_arr=np.zeros(n); atr_arr[1]=tr[0]
        for i in range(2,n): atr_arr[i]=(atr_arr[i-1]*(atr_p-1)+tr[i-1])/atr_p
        ub=(h+l)/2+mult*atr_arr; lb=(h+l)/2-mult*atr_arr
        trend=np.ones(n)
        for i in range(1,n):
            if c[i]>ub[i-1]: trend[i]=1
            elif c[i]<lb[i-1]: trend[i]=-1
            else: trend[i]=trend[i-1]
        st=np.where(trend==1,lb,ub)
        st_signal='BUY' if trend[-1]==1 else 'SELL'
        st_val=round(float(st[-1]),2)

        # MACD
        ema12=ema(c,12); ema26=ema(c,26)
        macd_line=ema12-ema26
        sig_line=ema(macd_line[25:],9) if n>25 else np.array([0])
        macd_val=round(float(macd_line[-1]),2); sig_val=round(float(sig_line[-1]),2)
        macd_cross='Bullish' if macd_val>sig_val else 'Bearish'

        # ORB (first 3 candles of day)
        orb=None
        if n>=3:
            orb_h=float(np.max(h[:3])); orb_l=float(np.min(l[:3]))
            cur=float(c[-1])
            orb_status='ABOVE ORB' if cur>orb_h else ('BELOW ORB' if cur<orb_l else 'INSIDE ORB')
            orb={'high':round(orb_h,2),'low':round(orb_l,2),'status':orb_status}

        # BB
        bb_mid=bb_upper=bb_lower=bb_pct=None
        if n>=20:
            w=c[-20:]; bb_mid=round(float(np.mean(w)),2); bb_std=float(np.std(w))
            bb_upper=round(bb_mid+2*bb_std,2); bb_lower=round(bb_mid-2*bb_std,2)
            rng=bb_upper-bb_lower
            bb_pct=round((float(c[-1])-bb_lower)/rng*100,1) if rng>0 else 50

        avg_vol=float(np.mean(v[-20:])) if n>=20 else float(np.mean(v))
        vol_ratio=round(float(v[-1])/avg_vol,2) if avg_vol>0 else 1.0
        atr_val=round(float(atr_arr[-1]),2)
        cur=float(c[-1])

        # Score
        score=0; bull=[]; bear=[]
        if 40<=rsi_val<=65: score+=20; bull.append(f'RSI {rsi_val} — momentum zone')
        elif rsi_val>65: score+=8; bear.append(f'RSI {rsi_val} — overbought')
        elif rsi_val<35: score+=5; bear.append(f'RSI {rsi_val} — oversold')
        else: score+=10
        if float(ema9[-1])>float(ema21[-1]): score+=20; bull.append('EMA9 > EMA21 — bullish')
        else: bear.append('EMA9 < EMA21 — bearish')
        if vwap:
            if cur>vwap: score+=20; bull.append(f'Price above VWAP ({vwap})')
            else: score+=5; bear.append(f'Price below VWAP ({vwap})')
        if st_signal=='BUY': score+=25; bull.append(f'Supertrend BUY @ {st_val}')
        else: bear.append(f'Supertrend SELL @ {st_val}')
        if macd_cross=='Bullish': score+=15; bull.append('MACD bullish')
        else: bear.append('MACD bearish')
        score=min(score,100)

        if score>=75: verdict='STRONG BUY'; vtype='strong_buy'; hint='CALL option consider karo'
        elif score>=60: verdict='BUY'; vtype='buy'; hint='CALL option — confirm karo pehle'
        elif score<=25: verdict='STRONG SELL'; vtype='strong_sell'; hint='PUT option consider karo'
        elif score<=40: verdict='SELL / AVOID'; vtype='sell'; hint='PUT option — confirm karo pehle'
        else: verdict='NEUTRAL / WAIT'; vtype='neutral'; hint='Sideline raho — clear signal nahi'

        sl_buy=round(cur-1.5*atr_val,2); tgt_buy=round(cur+2*atr_val,2)
        sl_sell=round(cur+1.5*atr_val,2); tgt_sell=round(cur-2*atr_val,2)

        chart_candles=[]
        for i in range(max(0,n-60),n):
            chart_candles.append({
                't': candles_rs[i][0][:16].replace('T',' ').replace('+05:30',''),
                'o':round(float(o[i]),2),'h':round(float(h[i]),2),
                'l':round(float(l[i]),2),'c':round(float(c[i]),2),
                'v':int(v[i]),
                'ema9':round(float(ema9[i]),2),'ema21':round(float(ema21[i]),2),
                'st':round(float(st[i]),2),'st_up':bool(trend[i]==1),'vwap':vwap,
            })

        return jsonify({
            'sym':sym,'tf':tf,'cur':round(cur,2),
            'rsi':rsi_val,'ema9':round(float(ema9[-1]),2),'ema21':round(float(ema21[-1]),2),
            'vwap':vwap,'macd':macd_val,'macd_signal':sig_val,'macd_cross':macd_cross,
            'supertrend':st_val,'supertrend_signal':st_signal,
            'bb_upper':bb_upper,'bb_lower':bb_lower,'bb_mid':bb_mid,'bb_pct':bb_pct,
            'atr':atr_val,'vol_ratio':vol_ratio,'orb':orb,'score':score,
            'verdict':verdict,'verdict_type':vtype,'option_hint':hint,
            'bull_reasons':bull,'bear_reasons':bear,
            'sl_buy':sl_buy,'tgt_buy':tgt_buy,'sl_sell':sl_sell,'tgt_sell':tgt_sell,
            'candles':chart_candles,
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# UPSTOX API — Token Management
# ══════════════════════════════════════════════════════════════════════════════
_UPSTOX_TOKEN_FILE = os.path.join(BASE, 'upstox_token.json')
_upstox_token = ''

def _load_upstox_token():
    global _upstox_token
    try:
        if os.path.exists(_UPSTOX_TOKEN_FILE):
            with open(_UPSTOX_TOKEN_FILE) as f:
                d = json.load(f)
                _upstox_token = d.get('token', '')
    except: pass

def _save_upstox_token(token):
    global _upstox_token
    _upstox_token = token
    try:
        with open(_UPSTOX_TOKEN_FILE, 'w') as f:
            json.dump({'token': token}, f)
    except: pass

_load_upstox_token()

def _upstox_headers():
    return {'Authorization': f'Bearer {_upstox_token}', 'Accept': 'application/json'}

# ── Upstox Instrument Key Cache ───────────────────────────────────────────────
# Format: { 'RELIANCE': 'NSE_EQ|INE002A01018', 'TCS': 'NSE_EQ|INE467B01029', ... }
_UPSTOX_INSTRUMENTS_FILE = os.path.join(BASE, 'upstox_instruments.json')
_upstox_instruments: dict = {}      # symbol → EQ instrument_key (for signals/live price)
_upstox_fo_instruments: dict = {}   # symbol → FO instrument_key (for option chain) — currently same as EQ
_instruments_lock = threading.Lock()

def _load_instruments_cache():
    global _upstox_instruments, _upstox_fo_instruments
    try:
        if os.path.exists(_UPSTOX_INSTRUMENTS_FILE):
            with open(_UPSTOX_INSTRUMENTS_FILE) as f:
                data = json.load(f)
            # Support both old format (flat dict) and new format ({'eq':..., 'fo':...})
            if isinstance(data, dict) and 'eq' in data:
                _upstox_instruments    = data.get('eq', {})
                _upstox_fo_instruments = data.get('fo', {})
            else:
                _upstox_instruments    = data  # old flat format
                _upstox_fo_instruments = {}
            print(f'[Upstox] Instruments cache loaded: {len(_upstox_instruments)} EQ symbols')
    except Exception as ex:
        print(f'[Upstox] Cache load error: {ex}')

def _save_instruments_cache():
    try:
        with open(_UPSTOX_INSTRUMENTS_FILE, 'w') as f:
            json.dump({'eq': _upstox_instruments, 'fo': _upstox_fo_instruments}, f)
    except Exception as ex:
        print(f'[Upstox] Cache save error: {ex}')

def _fetch_upstox_instruments():
    """
    Download Upstox NSE instruments CSV and build two maps:
    - _upstox_instruments:    symbol → EQ instrument_key  (for live price / signals / option chain)
    - _upstox_fo_instruments: symbol → lot_size           (for FNO info)
    Upstox public CSV (no auth needed):
      https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz
    instrument_type values: EQUITY, OPTSTK, OPTIDX, FUTSTK, FUTIDX, etc.
    """
    global _upstox_instruments, _upstox_fo_instruments
    import requests as _rq, gzip, io, csv

    url = 'https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz'
    print('[Upstox] Downloading instruments CSV...')
    try:
        r = _rq.get(url, timeout=30)
        if r.status_code != 200:
            print(f'[Upstox] Instruments download failed: {r.status_code}')
            return False

        with gzip.open(io.BytesIO(r.content), 'rt', encoding='utf-8') as gz:
            reader = csv.DictReader(gz)
            eq_map  = {}   # symbol → NSE_EQ instrument_key
            lot_map = {}   # symbol → lot_size (from FUTSTK rows)
            for row in reader:
                itype = row.get('instrument_type', '').strip().upper()
                sym   = row.get('tradingsymbol', '').strip().upper()
                ikey  = row.get('instrument_key', '').strip()
                if not sym or not ikey:
                    continue
                # EQUITY rows → EQ instrument key (used for signals + option chain)
                if itype == 'EQUITY':
                    eq_map[sym] = ikey
                # FUTSTK rows → get lot size for FNO stocks
                elif itype == 'FUTSTK':
                    try:
                        lot_map[sym] = int(float(row.get('lot_size', 0)))
                    except: pass

        with _instruments_lock:
            _upstox_instruments    = eq_map
            _upstox_fo_instruments = lot_map

        # Save both maps
        try:
            with open(_UPSTOX_INSTRUMENTS_FILE, 'w') as f:
                json.dump({'eq': eq_map, 'fo': lot_map}, f)
        except Exception as ex:
            print(f'[Upstox] Cache save error: {ex}')

        print(f'[Upstox] Instruments refreshed: {len(eq_map)} EQ symbols, {len(lot_map)} FNO stocks')
        return True
    except Exception as ex:
        import traceback; traceback.print_exc()
        print(f'[Upstox] Instruments fetch error: {ex}')
        return False

def _get_instrument_key(sym: str) -> str:
    """
    Return Upstox instrument_key for a symbol.
    Indices use hardcoded keys; stocks use the downloaded CSV cache.
    """
    # Indices — hardcoded
    idx_keys = {
        'NIFTY':      'NSE_INDEX|Nifty 50',
        'BANKNIFTY':  'NSE_INDEX|Nifty Bank',
        'FINNIFTY':   'NSE_INDEX|Nifty Fin Service',
        'MIDCPNIFTY': 'NSE_INDEX|NIFTY MID SELECT',
        'SENSEX':     'BSE_INDEX|SENSEX',
    }
    if sym in idx_keys:
        return idx_keys[sym]

    # Stocks — from CSV cache
    with _instruments_lock:
        key = _upstox_instruments.get(sym)
    if key:
        return key

    # Cache miss — try to refresh once
    if _upstox_instruments:
        return ''   # cache loaded but sym not found
    # Cache empty — download now (blocking, first time only)
    _fetch_upstox_instruments()
    with _instruments_lock:
        return _upstox_instruments.get(sym, '')

# Load cache on startup; refresh in background if stale (>1 day old)
_load_instruments_cache()

def _maybe_refresh_instruments():
    """Refresh instruments CSV in background if cache is empty or >24h old."""
    if not _upstox_instruments:
        threading.Thread(target=_fetch_upstox_instruments, daemon=True).start()
        return
    try:
        mtime = os.path.getmtime(_UPSTOX_INSTRUMENTS_FILE)
        age_h = (datetime.datetime.now().timestamp() - mtime) / 3600
        if age_h > 24:
            threading.Thread(target=_fetch_upstox_instruments, daemon=True).start()
    except: pass

_maybe_refresh_instruments()

# Upstox instrument keys (legacy — kept for compat, use _get_instrument_key() instead)
_UPSTOX_IDX = {
    'NIFTY':      'NSE_INDEX|Nifty 50',
    'BANKNIFTY':  'NSE_INDEX|Nifty Bank',
    'FINNIFTY':   'NSE_INDEX|Nifty Fin Service',
    'MIDCPNIFTY': 'NSE_INDEX|NIFTY MID SELECT',
    'SENSEX':     'BSE_INDEX|SENSEX',
}

# Upstox option chain instrument keys (different from quote keys)
_UPSTOX_OC_IDX = {
    'NIFTY':      'NSE_INDEX|Nifty 50',
    'BANKNIFTY':  'NSE_INDEX|Nifty Bank',
    'FINNIFTY':   'NSE_INDEX|Nifty Fin Service',
    'MIDCPNIFTY': 'NSE_INDEX|NIFTY MID SELECT',
    'SENSEX':     'BSE_INDEX|SENSEX',
}

@app.route('/api/upstox/refresh_instruments', methods=['POST'])
def api_refresh_instruments():
    """Manually refresh Upstox instruments CSV cache"""
    ok = _fetch_upstox_instruments()
    return jsonify({'ok': ok, 'count': len(_upstox_instruments)})

@app.route('/api/upstox/instruments_status')
def api_instruments_status():
    """Check instruments cache status"""
    age_h = None
    try:
        if os.path.exists(_UPSTOX_INSTRUMENTS_FILE):
            mtime = os.path.getmtime(_UPSTOX_INSTRUMENTS_FILE)
            age_h = round((datetime.datetime.now().timestamp() - mtime) / 3600, 1)
    except: pass
    with _instruments_lock:
        eq_count = len(_upstox_instruments)
        fo_count = len(_upstox_fo_instruments)
        sample   = dict(list(_upstox_instruments.items())[:5])
    return jsonify({
        'loaded':    bool(_upstox_instruments),
        'count':     eq_count,
        'fo_count':  fo_count,
        'age_hours': age_h,
        'sample':    sample,
    })

@app.route('/api/upstox/token', methods=['POST'])
def api_upstox_set_token():
    data = request.get_json(silent=True) or {}
    token = data.get('token', '').strip()
    if not token:
        return jsonify({'error': 'Token required'}), 400
    # Quick validate
    import requests as _rq
    r = _rq.get('https://api.upstox.com/v2/market-quote/quotes?instrument_key=NSE_INDEX|Nifty%2050',
                headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'}, timeout=8)
    if r.status_code != 200:
        return jsonify({'error': f'Token invalid — Upstox returned {r.status_code}'}), 400
    _save_upstox_token(token)
    return jsonify({'ok': True, 'message': 'Token saved!'})

@app.route('/api/upstox/status')
def api_upstox_status():
    if not _upstox_token:
        return jsonify({'ok': False, 'message': 'Token not set'})
    try:
        import requests as _rq
        r = _rq.get('https://api.upstox.com/v2/market-quote/quotes?instrument_key=NSE_INDEX|Nifty%2050',
                    headers=_upstox_headers(), timeout=8)
        if r.status_code == 200:
            d = r.json().get('data', {})
            spot = list(d.values())[0].get('ohlc', {}).get('close', 0) if d else 0
            return jsonify({'ok': True, 'message': 'Connected', 'nifty_spot': spot})
        return jsonify({'ok': False, 'message': f'Token expired or invalid ({r.status_code})'})
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)})
_OC_COOKIES_FILE = os.path.join(BASE, 'nse_oc_cookies.json')  # kept for compat

def _upstox_get_nearest_expiry(sym):
    """
    Get nearest expiry option chain from Upstox.
    For indices: use NSE_INDEX keys.
    For stocks: use NSE_EQ|ISIN key — Upstox option chain API accepts EQ keys for FNO stocks.
    Tries next 45 days to find a valid expiry.
    """
    import requests as _rq, datetime as _dt

    # Get the right instrument key
    ikey = _get_instrument_key(sym)
    if not ikey:
        print(f'[OC] No instrument key for {sym} — instruments cache empty? Refresh karo.')
        return None, []

    ikey_enc = ikey.replace('|', '%7C').replace(' ', '%20')
    today = _dt.date.today()

    print(f'[OC] Fetching option chain for {sym} using key: {ikey}')

    for delta in range(0, 45):
        exp = (today + _dt.timedelta(days=delta)).strftime('%Y-%m-%d')
        try:
            r = _rq.get(
                f'https://api.upstox.com/v2/option/chain?instrument_key={ikey_enc}&expiry_date={exp}',
                headers=_upstox_headers(), timeout=10)
            if r.status_code == 200:
                data = r.json().get('data', [])
                if data:
                    print(f'[OC] Found expiry {exp} for {sym} — {len(data)} strikes')
                    return exp, data
            elif r.status_code == 400:
                # Bad request — key might be wrong, log and stop
                print(f'[OC] 400 for {sym} ({ikey}): {r.text[:150]}')
                break
        except Exception as ex:
            print(f'[OC] {sym} expiry {exp}: {ex}')
            continue

    return None, []


@app.route('/api/intraday/set_cookies', methods=['POST'])
def api_set_oc_cookies():
    """Legacy — redirect to Upstox token setup"""
    return jsonify({'error': 'NSE cookies deprecated. Use /api/upstox/token instead'}), 410


@app.route('/api/intraday/cookie_status')
def api_oc_cookie_status():
    """Check Upstox token status"""
    if not _upstox_token:
        return jsonify({'has_cookies': False, 'has_nsit': False, 'working': False,
                        'message': 'Upstox token not set'})
    try:
        import requests as _rq
        r = _rq.get('https://api.upstox.com/v2/market-quote/quotes?instrument_key=NSE_INDEX|Nifty%2050',
                    headers=_upstox_headers(), timeout=8)
        working = r.status_code == 200
        return jsonify({'has_cookies': True, 'has_nsit': True, 'working': working,
                        'message': 'Upstox connected' if working else 'Token expired'})
    except Exception as e:
        return jsonify({'has_cookies': False, 'has_nsit': False, 'working': False, 'message': str(e)})


@app.route('/api/intraday/optionchain')
def api_option_chain():
    """Option Chain via Upstox API"""
    sym = request.args.get('sym', 'NIFTY').upper().strip()
    if not _upstox_token:
        return jsonify({'error': 'Upstox token not set — ⚙️ Upstox tab mein token add karo'}), 503

    # Check if we have instrument key
    ikey_check = _get_instrument_key(sym)
    if not ikey_check:
        return jsonify({'error': f'{sym} ka instrument key nahi mila — ⚙️ Upstox tab → "Refresh Instruments" click karo'}), 404

    try:
        import requests as _rq
        expiry, data = _upstox_get_nearest_expiry(sym)
        if not data:
            return jsonify({'error': f'{sym} ka option chain nahi mila. Possible reasons:\n1. {sym} FNO mein nahi hai\n2. Upstox token expire ho gaya — refresh karo\n3. Market band hai — expiry data unavailable'}), 404

        # Get spot price
        ikey = _get_instrument_key(sym) or _UPSTOX_IDX.get(sym, 'NSE_INDEX|Nifty 50')
        ikey_enc = ikey.replace('|','%7C').replace(' ','%20')
        spot = 0
        try:
            rq = _rq.get(f'https://api.upstox.com/v2/market-quote/quotes?instrument_key={ikey_enc}',
                         headers=_upstox_headers(), timeout=8)
            if rq.status_code == 200:
                qd = rq.json().get('data', {})
                if qd:
                    spot = list(qd.values())[0].get('ohlc', {}).get('close', 0)
        except: pass

        chain = []
        for item in data:
            ce = item.get('call_options', {}).get('market_data', {})
            pe = item.get('put_options',  {}).get('market_data', {})
            strike = item.get('strike_price', 0)
            ce_oi = ce.get('oi', 0) or 0
            pe_oi = pe.get('oi', 0) or 0
            ce_prev = ce.get('prev_oi', 0) or 0
            pe_prev = pe.get('prev_oi', 0) or 0
            chain.append({
                'strike':    strike,
                'ce_ltp':    ce.get('ltp', 0) or 0,
                'ce_oi':     ce_oi,
                'ce_chg_oi': round(ce_oi - ce_prev, 0),
                'ce_iv':     ce.get('iv', 0) or 0,
                'ce_vol':    ce.get('volume', 0) or 0,
                'pe_ltp':    pe.get('ltp', 0) or 0,
                'pe_oi':     pe_oi,
                'pe_chg_oi': round(pe_oi - pe_prev, 0),
                'pe_iv':     pe.get('iv', 0) or 0,
                'pe_vol':    pe.get('volume', 0) or 0,
            })

        chain.sort(key=lambda x: x['strike'])
        total_ce_oi = sum(x['ce_oi'] for x in chain)
        total_pe_oi = sum(x['pe_oi'] for x in chain)
        pcr = round(total_pe_oi / total_ce_oi, 3) if total_ce_oi > 0 else 0
        max_pain = _calc_max_pain(chain)
        atm = min(chain, key=lambda x: abs(x['strike'] - spot))['strike'] if chain and spot else 0

        return jsonify({
            'sym': sym, 'spot': spot, 'expiry': expiry,
            'expiry_dates': [expiry], 'atm': atm,
            'pcr': pcr, 'max_pain': max_pain,
            'total_ce_oi': total_ce_oi, 'total_pe_oi': total_pe_oi,
            'chain': chain,
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def _calc_max_pain(chain):
    if not chain: return 0
    strikes = [x['strike'] for x in chain]
    min_loss = float('inf'); max_pain = strikes[0]
    for s in strikes:
        loss = sum(max(0, k-s)*x['ce_oi'] + max(0, s-k)*x['pe_oi']
                   for x, k in [(x, x['strike']) for x in chain])
        if loss < min_loss:
            min_loss = loss; max_pain = s
    return max_pain


@app.route('/api/intraday/pcr')
def api_pcr_oi():
    """PCR + OI analysis via Upstox"""
    sym = request.args.get('sym', 'NIFTY').upper().strip()
    if not _upstox_token:
        return jsonify({'error': 'Upstox token not set'}), 503
    try:
        expiry, data = _upstox_get_nearest_expiry(sym)
        if not data:
            return jsonify({'error': f'{sym} ka data nahi mila — Upstox token expire ho gaya hoga. Token refresh karo.'}), 404

        ikey = _get_instrument_key(sym) or _UPSTOX_IDX.get(sym, 'NSE_INDEX|Nifty 50')
        ikey_enc = ikey.replace('|','%7C').replace(' ','%20')
        spot = 0
        try:
            import requests as _rq
            rq = _rq.get(f'https://api.upstox.com/v2/market-quote/quotes?instrument_key={ikey_enc}',
                         headers=_upstox_headers(), timeout=8)
            if rq.status_code == 200:
                qd = rq.json().get('data', {})
                if qd: spot = list(qd.values())[0].get('ohlc', {}).get('close', 0)
        except: pass

        ce_oi = pe_oi = ce_vol = pe_vol = ce_chg = pe_chg = 0
        top_ce = []; top_pe = []

        for item in data:
            ce = item.get('call_options', {}).get('market_data', {})
            pe = item.get('put_options',  {}).get('market_data', {})
            strike = item.get('strike_price', 0)
            c_oi = ce.get('oi', 0) or 0; p_oi = pe.get('oi', 0) or 0
            c_chg = c_oi - (ce.get('prev_oi', 0) or 0)
            p_chg = p_oi - (pe.get('prev_oi', 0) or 0)
            ce_oi += c_oi; pe_oi += p_oi
            ce_vol += ce.get('volume', 0) or 0
            pe_vol += pe.get('volume', 0) or 0
            ce_chg += c_chg; pe_chg += p_chg
            if c_oi > 0: top_ce.append({'strike': strike, 'oi': c_oi, 'chg': round(c_chg)})
            if p_oi > 0: top_pe.append({'strike': strike, 'oi': p_oi, 'chg': round(p_chg)})

        top_ce.sort(key=lambda x: x['oi'], reverse=True)
        top_pe.sort(key=lambda x: x['oi'], reverse=True)
        pcr = round(pe_oi / ce_oi, 3) if ce_oi > 0 else 0

        if pcr > 1.3:   pcr_signal = 'Bullish — Heavy PUT writing (market support)'
        elif pcr > 1.0: pcr_signal = 'Mildly Bullish'
        elif pcr > 0.7: pcr_signal = 'Neutral'
        elif pcr > 0.5: pcr_signal = 'Mildly Bearish'
        else:           pcr_signal = 'Bearish — Heavy CALL writing (market resistance)'

        return jsonify({
            'sym': sym, 'spot': spot, 'expiry': expiry,
            'pcr': pcr, 'pcr_signal': pcr_signal,
            'ce_oi': ce_oi, 'pe_oi': pe_oi,
            'ce_vol': ce_vol, 'pe_vol': pe_vol,
            'ce_chg_oi': ce_chg, 'pe_chg_oi': pe_chg,
            'resistance': top_ce[0]['strike'] if top_ce else None,
            'support':    top_pe[0]['strike'] if top_pe else None,
            'top_ce_strikes': top_ce[:5],
            'top_pe_strikes': top_pe[:5],
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ── Keep-Alive ping endpoint ──────────────────────────────────────────────────
@app.route('/ping')
def ping():
    return 'pong', 200

def _keep_alive():
    """Ping self every 14 min so Render free tier doesn't sleep"""
    import time, urllib.request
    app_url = os.environ.get('RENDER_EXTERNAL_URL', '').rstrip('/')
    if not app_url:
        return  # Only run on Render
    time.sleep(90)  # Wait 90s after startup
    while True:
        try:
            urllib.request.urlopen(f"{app_url}/ping", timeout=10)
            print("[keep-alive] pinged ✅")
        except Exception as ex:
            print(f"[keep-alive] {ex}")
        time.sleep(14 * 60)  # Every 14 minutes

# Start keep-alive on Render (gunicorn bhi use karta hai yeh)
if os.environ.get('RENDER_EXTERNAL_URL'):
    threading.Thread(target=_keep_alive, daemon=True).start()
    print("🔄 Keep-alive thread started")

if __name__=='__main__':
    print("🚀 Stock Analyzer Pro Web — http://localhost:5000")
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
