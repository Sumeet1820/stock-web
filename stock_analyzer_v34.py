import tkinter as tk
from tkinter import ttk
import threading, requests, re, webbrowser, json, os, datetime
from bs4 import BeautifulSoup

# ── yfinance import + cache DISABLE (peewee corruption fix) ──────────────────
import os, glob, shutil

def _nuke_yf_cache():
    for base in [
        os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'py-yfinance'),
        os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'py-yfinance'),
        os.path.join(os.path.expanduser('~'), '.cache', 'py-yfinance'),
        os.path.join(os.path.expanduser('~'), 'Library', 'Caches', 'py-yfinance'),
    ]:
        if os.path.exists(base):
            try: shutil.rmtree(base)
            except:
                for f in glob.glob(os.path.join(base, '*.db')):
                    try: os.remove(f)
                    except: pass

_nuke_yf_cache()

try:
    import yfinance as yf
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'yfinance', '-q'])
    import yfinance as yf

# yfinance cache system COMPLETELY disable — har method cover karo
try:
    from yfinance import cache as _yf_cache

    class _NoCache:
        """Dummy cache — kuch store nahi karta, peewee/SQLite kabhi use nahi hota"""
        # Instance methods
        def lookup(self, ticker):        return None
        def store(self, ticker, tz):     pass
        def initialise(self):            pass
        def close(self):                 pass
        def get_tz_cache(self):          return self
        # Class/static method variants
        @classmethod
        def get_tz_cache(cls):           return cls()

    _no_cache_instance = _NoCache()

    # Patch every known entry point in yfinance.cache
    for _attr in dir(_yf_cache):
        _obj = getattr(_yf_cache, _attr, None)
        if _obj is None: continue
        # Replace any class that has lookup/initialise/get_tz_cache
        if isinstance(_obj, type) and any(
            hasattr(_obj, m) for m in ('lookup','initialise','get_tz_cache')):
            try: setattr(_yf_cache, _attr, _NoCache)
            except: pass
        # Replace any live instance
        elif hasattr(_obj, 'lookup') or hasattr(_obj, 'get_tz_cache'):
            try: setattr(_yf_cache, _attr, _no_cache_instance)
            except: pass

    # Also patch the module-level get_tz_cache function if it exists
    if hasattr(_yf_cache, 'get_tz_cache'):
        try: _yf_cache.get_tz_cache = lambda: _no_cache_instance
        except: pass

except Exception:
    pass  # Cache disable na ho to bhi chalta — folder already nuke kar diya


# ── COOKIES — update karo jab expire ho ──────────────────────────────────────
COOKIES = {
    'csrftoken': 'S5v8SsTXUMy0SrgIS4wvHBWkkQOpFc33', 
    'sessionid': 'wao3vnsbhmd9jv8rre730xmma6t540a3',
    'theme':     'dark',
}

# ── CHARTINK COOKIES — update karo jab expire ho ────────────────────────────
CHARTINK_COOKIES = {
    'ci_session':       'eyJpdiI6InpqVnMvVDM1aGV6em53WGR6eUo4cVE9PSIsInZhbHVlIjoiazY3SWU4bHh0NlAzOUlVNDE1ZU1ob3NhVnU0ZWNta3N0QVA4aFFSbVJEZFRMaWpQN0JrMnlONUpZRXQwMGtmbGxXM0Q3djVLNVZvcFc2K29lR3NUSkRSTlpvSkIwbDZkSk1mRk5HTDBpbWhpN051eFp5QUJiM041aEFidVloU1ciLCJtYWMiOiI1YzkyNzVhOWJjZmM3NzZlNWIyZmYzNjk0ODU5NTQ0ODliN2U4MGM1NDQ1NGRiMmU2NjNlZGU3MDllYTNkMGZlIiwidGFnIjoiIn0%3D',
    'XSRF-TOKEN':       'eyJpdiI6IlNGSFprMFdkb2NFTE1KQy9qWHZoOUE9PSIsInZhbHVlIjoiUTN5K25WekZoSEZmenlYVm1adWx0a1NzbkxHMGZjVGhXZktUR01QMWU2WmxXcFdndnNqRDkxdXNibktpK1BKVTRRalNpRmNVRWM5N3ZwaHRtdTR0M2JGU1hIMG42czMySlhScXFZOGxoaUIrQkw0VkFaRTNuNjhiazNncjVmRGQiLCJtYWMiOiJmYjgyMzY3NWNkOTc2N2Y1ZjNlMThjNjQ4ZjYzYTE3ZmExNzhmMWE5MzgyMzVkYzFhZTZkZDQ4YjJkMGVlODM0IiwidGFnIjoiIn0%3D',
    'remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d': 'eyJpdiI6IjYxQmhCT3lad3NBV3JjTDlkV0FpdVE9PSIsInZhbHVlIjoiNmoySFUxc2haM2JQa2tQNkNvNTcrRHh0Y2xsby94azV4bzU2NnIrODRiWXZkazA5bDNoK0RZOUFwUkhZS2QvakZnTWtNeGZHYVVXTDU2VVpFSElFeVBZZHhRMXJZOFRIOVRvWUpoWGNQNENuL2tjWGFUV2E1Y253ZlB4Ny9IcUVSZGdBWEJtdGNKRitpcU9VMjlrb1k4dW55TkREbFc5bjVKNVkzUk1jTjdZUXA0em5YTytkc1VLakxNZGZPU0Y0anRxU3B2T21NRGxCU20zQmVXVnNuK3FaM2I1UFd1NmxiWXlDUEdkSWVJcz0iLCJtYWMiOiJkYjM3MGFmNWFiZmJmOTFlNGQxNmQ5MGExNjU3ZTNmNDI1ZWMwYzI2ZDgyODMwMWQ3ODM4NWRmYjkxMThhZGIyIiwidGFnIjoiIn0%3D',
}

# ── COLORS ────────────────────────────────────────────────────────────────────
BG      = '#060912'   # Deeper black
CARD    = "#11162C"   # Card background
CARD2   = "#0C1121"   # Alternate row
ACCENT  = '#4D8EFF'   # Bright blue
GREEN   = '#00E6A8'   # Vivid teal green
RED     = '#FF3D5C'   # Vivid red
YELLOW  = '#FFD700'   # Pure gold yellow
ORANGE  = '#FF9500'   # Bright orange
TEXT    = '#F0F4FF'   # Near white — bright & clear
SUBTEXT = '#8B92B8'   # Brighter muted — was too dark
BORDER  = '#1C2240'   # Border
PURPLE  = '#9B6FE8'   # Brighter purple
GOLD    = '#FFD700'   # Gold

# ── PERSISTENT DATA (Watchlist + Notes) ──────────────────────────────────────
import sys

def get_data_file():
    if getattr(sys, 'frozen', False):
        # EXE mode → permanent location
        base = os.path.join(os.path.expanduser("~"), "Documents", "StockAnalyzer")
    else:
        # Python mode → current folder
        base = os.path.dirname(os.path.abspath(__file__))

    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "stock_data.json")

DATA_FILE = get_data_file()

def _load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except: pass
    return {'watchlist': {}, 'notes': {}, 'compare': []}

def _save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except: pass

APP_DATA = _load_data()

# ── SESSIONS ──────────────────────────────────────────────────────────────────
SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.screener.in/',
})
SESSION.cookies.update(COOKIES)

NSE_SESSION = requests.Session()
NSE_SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.nseindia.com/',
    'Accept': 'application/json',
})

# ── CHECKLIST CRITERIA ────────────────────────────────────────────────────────
# Format: (Display Name, data_key, condition_text, check_fn)
# NOTE: Sector Outlook + FII/DII increasing = manual check (❓ always)

CRITERIA = {
    'swing': [
        # Basic quality filters
        ('Market Cap',           'market_cap',           '> 1000 Cr',   lambda v: v > 1000),
        ('Net Profit',           'net_profit',           '> 0',         lambda v: v > 0),
        ('Net Profit Qtr',       'net_profit_qtr',       '> 0',         lambda v: v > 0),
        ('Debt to Equity',       'debt_to_equity',       '< 1',         lambda v: v < 1),
        ('Current Ratio',        'current_ratio',        '> 1',         lambda v: v > 1),
        ('Interest Coverage',    'interest_coverage',    '> 3',         lambda v: v > 3),
        ('Promoter Holding',     'promoter_holding',     '> 50%',       lambda v: v > 50),
        ('Pledged %',            'pledged',              '< 10%',       lambda v: v < 10),
        ('ROE',                  'roe',                  '> 12%',       lambda v: v > 12),
        ('Profit Growth 3Y',     'profit_growth_3y',     '> 10%',       lambda v: v > 10),
        # Manual checks (always ❓)
        ('Promoter Change?',     'promoter_change',      'No big fall >2%', lambda v: v > -2.0),
        ('FII/DII Chg (FII)',    'fii_change',           '>= 0 (not falling)', lambda v: v >= -1.0),
        ('Sector Outlook',       '_manual',              'Positive?',   None),
    ],
    'positional': [
        ('Market Cap',           'market_cap',           '> 1000 Cr',   lambda v: v > 1000),
        ('Net Profit',           'net_profit',           '> 0',         lambda v: v > 0),
        ('Net Profit Qtr',       'net_profit_qtr',       '> 0',         lambda v: v > 0),
        ('Debt to Equity',       'debt_to_equity',       '< 1',         lambda v: v < 1),
        ('Current Ratio',        'current_ratio',        '> 1.2',       lambda v: v > 1.2),
        ('Interest Coverage',    'interest_coverage',    '> 3',         lambda v: v > 3),
        ('Promoter Holding',     'promoter_holding',     '> 50%',       lambda v: v > 50),
        ('Pledged %',            'pledged',              '< 10%',       lambda v: v < 10),
        ('ROE',                  'roe',                  '> 15%',       lambda v: v > 15),
        ('ROCE',                 'roce',                 '> 15%',       lambda v: v > 15),
        ('Operating Margin',     'operating_margin',     '> 15%',       lambda v: v > 15),
        ('Sales Growth 3Y',      'sales_growth_3y',      '> 10%',       lambda v: v > 10),
        ('Profit Growth 3Y',     'profit_growth_3y',     '> 15%',       lambda v: v > 15),
        ('Promoter Change?',     'promoter_change',      'No big fall >2%', lambda v: v > -2.0),
        ('FII/DII Chg (FII)',    'fii_change',           '>= 0 (not falling)', lambda v: v >= -1.0),
        ('Sector Outlook',       '_manual',              'Positive?',   None),
    ],
    'longterm': [
        ('Market Cap',           'market_cap',           '> 2000 Cr',   lambda v: v > 2000),
        ('Net Profit',           'net_profit',           '> 0',         lambda v: v > 0),
        ('Net Profit Qtr',       'net_profit_qtr',       '> 0',         lambda v: v > 0),
        ('Debt to Equity',       'debt_to_equity',       '< 0.5',       lambda v: v < 0.5),
        ('Current Ratio',        'current_ratio',        '> 1.5',       lambda v: v > 1.5),
        ('Interest Coverage',    'interest_coverage',    '> 5',         lambda v: v > 5),
        ('Promoter Holding',     'promoter_holding',     '> 50%',       lambda v: v > 50),
        ('Pledged %',            'pledged',              '< 5%',        lambda v: v < 5),
        ('ROE',                  'roe',                  '> 20%',       lambda v: v > 20),
        ('ROCE',                 'roce',                 '> 20%',       lambda v: v > 20),
        ('Operating Margin',     'operating_margin',     '> 15%',       lambda v: v > 15),
        ('Net Profit Margin',    'net_margin',           '> 10%',       lambda v: v > 10),
        ('Sales Growth 3Y',      'sales_growth_3y',      '> 12%',       lambda v: v > 12),
        ('Profit Growth 3Y',     'profit_growth_3y',     '> 12%',       lambda v: v > 12),
        ('Sales Growth 5Y',      'sales_growth_5y',      '> 12%',       lambda v: v > 12),
        ('Profit Growth 5Y',     'profit_growth_5y',     '> 12%',       lambda v: v > 12),
        ('EPS Growth 5Y',        'eps_growth_5y',        '> 10%',       lambda v: v > 10),
        ('PEG Ratio',            'peg',                  '< 2',         lambda v: 0 < v < 2),
        ('Price to Book',        'price_to_book',        '< 10',        lambda v: 0 < v < 10),
        ('Dividend Yield',       'dividend_yield',       '> 0%',        lambda v: v >= 0),
        ('Promoter Change?',     'promoter_change',      'No big fall >2%', lambda v: v > -2.0),
        ('FII/DII Chg (FII)',    'fii_change',           '>= 0 (not falling)', lambda v: v >= -1.0),
        ('Sector Outlook',       '_manual',              'Positive?',   None),
    ],
}

# ── HELPER ────────────────────────────────────────────────────────────────────
def clean_num(text):
    """Parse numbers — handles negative, %, Cr, ₹, commas"""
    if text is None: return None
    t = str(text).strip()
    # Handle parentheses as negative: (123) → -123
    if t.startswith('(') and t.endswith(')'):
        t = '-' + t[1:-1]
    t = re.sub(r'[₹,\s]', '', t)
    t = re.sub(r'(Cr|cr)\.?$', '', t)
    t = t.replace('%', '').strip()
    if t in ['-', '', '--', 'N/A', 'na', 'NA', '—', '–']: return None
    try:    return float(t)
    except: return None

def latest_valid(cells, from_end=2):
    """cells list mein se last non-None value lo (TTM/latest avoid karne ke liye from_end=2)"""
    nums = [clean_num(c.get_text()) for c in cells[1:]]
    valid = [n for n in nums if n is not None]
    if not valid: return None
    # from_end=2 means prefer second-last (latest full year), fallback to last
    if len(valid) >= from_end:
        return valid[-from_end]
    return valid[-1]

def row_values(cells):
    """All numeric values from a row"""
    return [clean_num(c.get_text()) for c in cells[1:]]

# ── SCREENER PARSER ───────────────────────────────────────────────────────────
def scrape_screener(url):
    r    = SESSION.get(url, timeout=22)
    soup = BeautifulSoup(r.text, 'html.parser')

    d = {
        'name':'', 'page_url':r.url,
        'is_consolidated':'consolidated' in r.url,
        'nse_symbol': None,
        'sector': None, 'industry': None,
        # top ratios
        'market_cap':None,'current_price':None,'pe':None,'roe':None,'roce':None,
        'dividend_yield':None,'_book_value':None,
        # computed
        'debt_to_equity':None,'current_ratio':None,'peg':None,
        'price_to_book':None,'interest_coverage':None,
        # shareholding
        'promoter_holding':None,'pledged':None,
        'promoter_holding_prev':None,'promoter_change':None,
        'fii_holding':None,'dii_holding':None,
        'fii_change':None,'dii_change':None,
        # p&l
        'net_profit':None,'net_profit_qtr':None,
        'operating_margin':None,'net_margin':None,
        'operating_profit_annual':None,'interest_annual':None,
        # growth
        'sales_growth_3y':None,'sales_growth_5y':None,
        'profit_growth_3y':None,'profit_growth_5y':None,
        'eps_growth_5y':None,
    }

    # ── Company name ─────────────────────────────────────────────────────────
    for sel in ['h1.margin-0', '.company-name h1', 'h1']:
        el = soup.select_one(sel)
        if el: d['name'] = el.get_text(strip=True); break

    # ── NSE symbol ───────────────────────────────────────────────────────────
    m = re.search(r'/company/([^/]+)/', r.url)
    if m: d['nse_symbol'] = m.group(1).upper()

    # ── Sector & Industry ─────────────────────────────────────────────────────
    for el in soup.select('.company-links a, .sub-title a, a[href*="/company/"]'):
        href = el.get('href', '')
        txt  = el.get_text(strip=True)
        if '/sector/' in href or '/industry/' in href:
            if '/sector/' in href and not d['sector']:    d['sector']   = txt
            if '/industry/' in href and not d['industry']: d['industry'] = txt
    # Fallback: look for company-links div
    if not d['sector']:
        for el in soup.select('.company-links span, .company-info span'):
            txt = el.get_text(strip=True)
            if txt and len(txt) > 2 and len(txt) < 60:
                pass  # only set if confirmed sector link found above

    # ── TOP RATIOS — default fields (always in HTML) ──────────────────────
    for li in soup.select('#top-ratios li'):
        name_el = li.select_one('.name')
        num_el  = li.select_one('.number')
        if not name_el or not num_el: continue
        name = name_el.get_text(strip=True).lower().strip()
        val  = clean_num(num_el.get_text())
        if val is None: continue
        # Always overwrite — no None check needed, these are reliable
        if   'market cap'    in name: d['market_cap']    = val
        elif 'current price' in name: d['current_price'] = val
        elif 'stock p/e'     in name: d['pe']            = val
        elif name == 'roce':          d['roce']          = val
        elif name == 'roe':           d['roe']           = val
        elif 'book value'    in name: d['_book_value']   = val
        elif 'dividend yield'in name: d['dividend_yield']= val

    # Price to Book
    if d['_book_value'] and d['current_price'] and d['_book_value'] > 0:
        d['price_to_book'] = round(d['current_price'] / d['_book_value'], 2)

    # ── QUICK-RATIO API (login se extra fields milte hain) ───────────────────
    # warehouse-id se API try karo — blank ya 404 aaya toh HTML fallback
    _qd = {}
    try:
        info_el = soup.find(attrs={'data-warehouse-id': True})
        if info_el:
            wid = info_el['data-warehouse-id']
            cid = info_el.get('data-company-id','')
            for api_url in [
                f"https://www.screener.in/api/company/{wid}/quick_ratios/",
                f"https://www.screener.in/api/company/{cid}/quick_ratios/",
            ]:
                try:
                    api_r = SESSION.get(api_url, timeout=8)
                    if api_r.status_code == 200 and api_r.text.strip():
                        ct = api_r.headers.get('content-type','')
                        if 'json' in ct:
                            jdata = api_r.json()
                            items = jdata if isinstance(jdata, list) else jdata.get('ratios', jdata.get('quick_ratios',[]))
                            for item in (items or []):
                                n = (item.get('name') or item.get('title','')).strip()
                                v = item.get('value') or item.get('number','')
                                if n: _qd[n] = str(v)
                        elif 'html' in ct:
                            api_soup = BeautifulSoup(api_r.text, 'html.parser')
                            for li in api_soup.select('li'):
                                ne = li.select_one('.name'); ve = li.select_one('.number')
                                if ne and ve: _qd[ne.get_text(strip=True)] = ve.get_text(strip=True)
                        if _qd: break
                except Exception: continue
    except Exception: pass

    # Map quick-ratio fields → d dict
    QMAP = {
        'Debt to equity':'debt_to_equity', 'Price to book value':'price_to_book',
        'Current ratio':'current_ratio',   'PEG Ratio':'peg',
        'Int Coverage':'interest_coverage', 'Promoter holding':'promoter_holding',
        'Pledged percentage':'pledged',     'Change in Prom Hold':'promoter_change',
        'Profit Var 5Yrs':'profit_growth_5y','Profit Var 3Yrs':'profit_growth_3y',
        'Sales growth 5Years':'sales_growth_5y','EPS growth 5Years':'eps_growth_5y',
        'NPM latest quarter':'_npm_qtr',   'Net profit':'net_profit',
        'OPM':'operating_margin',          'Chg in FII Hold':'fii_change',
        'Chg in DII Hold':'dii_change',
    }
    for fname, dkey in QMAP.items():
        if fname in _qd:
            try:
                raw = str(_qd[fname]).replace(',','').replace('%','').replace('₹','').rstrip('x').strip()
                raw = raw.split('/')[0].strip()
                if raw.startswith('(') and raw.endswith(')'): raw = '-' + raw[1:-1]
                if raw: d[dkey] = float(raw)
            except: pass

    # ── SHAREHOLDING ─────────────────────────────────────────────────────────
    sh = soup.find('section', id='shareholding')
    if sh:
        tables = sh.select('table')
        if tables:
            for row in tables[0].select('tr'):
                cells = row.select('td')
                if not cells: continue
                label = cells[0].get_text(strip=True).lower()
                vals = []
                for c in cells[1:]:
                    v = clean_num(c.get_text(strip=True).replace('%',''))
                    if v is not None: vals.append(v)
                if not vals: continue
                if 'promoters' in label:
                    d['promoter_holding'] = vals[-1]
                    if len(vals) >= 2: d['promoter_holding_prev'] = vals[0]
                elif 'fii' in label or 'foreign' in label:
                    d['fii_holding'] = vals[-1]
                    if len(vals) >= 2: d['_fii_prev'] = vals[0]
                elif 'dii' in label or 'domestic' in label:
                    d['dii_holding'] = vals[-1]
                    if len(vals) >= 2: d['_dii_prev'] = vals[0]
                elif 'pledg' in label:
                    d['pledged'] = vals[-1]
    if d['pledged'] is None and d['promoter_holding'] is not None:
        d['pledged'] = 0.0

    # ── P&L TABLE ────────────────────────────────────────────────────────────
    pl = soup.find('section', id='profit-loss')
    if pl:
        mode = None
        rev_all = []; prf_all = []
        for row in pl.select('table tr'):
            cells = row.select('td, th')
            if not cells: continue
            label = cells[0].get_text(strip=True).lower()
            vals_text = [c.get_text(strip=True) for c in cells[1:]]
            # Growth sub-rows
            if 'compounded sales growth'  in label: mode = 'sales';  continue
            if 'compounded profit growth' in label: mode = 'profit'; continue
            if 'stock price cagr'         in label: mode = 'stock';  continue
            if 'return on equity'         in label: mode = 'roe_s';  continue
            if mode in ('sales','profit') and vals_text:
                val = clean_num(vals_text[0])
                if val is not None:
                    if   '5 year' in label:
                        if mode=='sales'  and d['sales_growth_5y']  is None: d['sales_growth_5y']  = val
                        if mode=='profit' and d['profit_growth_5y'] is None: d['profit_growth_5y'] = val
                    elif '3 year' in label:
                        if mode=='sales'  and d['sales_growth_3y']  is None: d['sales_growth_3y']  = val
                        if mode=='profit' and d['profit_growth_3y'] is None: d['profit_growth_3y'] = val
                continue
            mode = None
            nums  = [clean_num(v) for v in vals_text]
            valid = [n for n in nums if n is not None]
            if not valid: continue
            # Revenue — store all years for CAGR fallback
            if label in ('revenue+','revenue','sales+','sales','net sales','total revenue'):
                rev_all = [n for n in nums if n is not None]
            # Net profit
            elif label in ('net profit+','net profit','profit after tax'):
                if d['net_profit'] is None:
                    d['net_profit'] = valid[-2] if len(valid)>=2 else valid[-1]
                prf_all = [n for n in nums if n is not None]
            # Operating profit
            elif label in ('operating profit','operating profit+','ebit','ebitda'):
                d['operating_profit_annual'] = valid[-2] if len(valid)>=2 else valid[-1]
            # OPM %
            elif label == 'opm %':
                if d['operating_margin'] is None:
                    d['operating_margin'] = valid[-2] if len(valid)>=2 else valid[-1]
            # Interest
            elif label in ('interest','finance cost','finance costs','interest expense'):
                if d['interest_annual'] is None:
                    d['interest_annual'] = valid[-2] if len(valid)>=2 else valid[-1]
            # Net margin
            elif 'net profit %' in label or label == 'npm %':
                if d['net_margin'] is None:
                    d['net_margin'] = valid[-2] if len(valid)>=2 else valid[-1]

        # Interest Coverage (only if not from quick-ratio)
        if d['interest_coverage'] is None:
            op = d.get('operating_profit_annual')
            intr = d.get('interest_annual')
            np_ = d.get('net_profit')
            if intr and intr > 0:
                if op: d['interest_coverage'] = round(op/intr, 2)
                elif np_: d['interest_coverage'] = round((np_+intr)/intr, 2)
            elif op and not intr: d['interest_coverage'] = 999.0

        # Sales Growth CAGR fallback
        if rev_all:
            if len(rev_all)>=4 and d['sales_growth_3y'] is None:
                try: d['sales_growth_3y'] = round(((rev_all[-1]/rev_all[-4])**(1/3)-1)*100,1)
                except: pass
            if len(rev_all)>=5 and d['sales_growth_5y'] is None:
                try: d['sales_growth_5y'] = round(((rev_all[-1]/rev_all[-5])**(1/4)-1)*100,1)
                except: pass

        # Profit Growth CAGR fallback
        if prf_all:
            if len(prf_all)>=4 and d['profit_growth_3y'] is None:
                try:
                    if prf_all[-4]>0 and prf_all[-1]>0:
                        d['profit_growth_3y'] = round(((prf_all[-1]/prf_all[-4])**(1/3)-1)*100,1)
                except: pass
            if len(prf_all)>=5 and d['profit_growth_5y'] is None:
                try:
                    if prf_all[-5]>0 and prf_all[-1]>0:
                        d['profit_growth_5y'] = round(((prf_all[-1]/prf_all[-5])**(1/4)-1)*100,1)
                except: pass

        # Net margin fallback
        if d['net_margin'] is None and d['net_profit'] and rev_all:
            try: d['net_margin'] = round((d['net_profit']/rev_all[-1])*100,2)
            except: pass

    # ── QUARTERLY — latest quarter net profit ────────────────────────────────
    qr = soup.find('section', id='quarters')
    if qr:
        for row in qr.select('table tr'):
            cells = row.select('td, th')
            if not cells: continue
            label = cells[0].get_text(strip=True).lower()
            if 'net profit' in label:
                nums = [clean_num(c.get_text()) for c in cells[1:]]
                valid = [n for n in nums if n is not None]
                if valid: d['net_profit_qtr'] = valid[-1]; break

    # ── BALANCE SHEET ────────────────────────────────────────────────────────
    bs = soup.find('section', id='balance-sheet')
    if bs:
        eq_cap = res = borr = deposits = other_liab = other_assets = None
        for row in bs.select('table tr'):
            cells = row.select('td, th')
            if not cells: continue
            label = cells[0].get_text(strip=True).lower()
            nums  = [clean_num(c.get_text()) for c in cells[1:]]
            valid = [n for n in nums if n is not None]
            if not valid: continue
            if   'equity capital'    in label: eq_cap      = valid[-1]
            elif 'reserves'          in label: res         = valid[-1]
            elif label.startswith('borrowing'): borr       = valid[-1]
            elif 'deposits'          in label: deposits    = valid[-1]
            elif 'other liabilities' in label: other_liab  = valid[-1]
            elif 'other assets'      in label: other_assets= valid[-1]

        total_eq = (eq_cap or 0) + (res or 0)
        if d['debt_to_equity'] is None and total_eq > 0:
            if deposits is not None:
                d['debt_to_equity'] = round(((deposits or 0)+(borr or 0))/total_eq, 2)
            elif borr is not None:
                d['debt_to_equity'] = round(borr/total_eq,2) if borr>0 else 0.0
        if d['current_ratio'] is None and other_assets and other_liab:
            cl = (borr or 0) + other_liab
            if cl > 0: d['current_ratio'] = round(other_assets/cl,2)

    # ── RATIOS section ───────────────────────────────────────────────────────
    rt = soup.find('section', id='ratios')
    if rt:
        for row in rt.select('table tr'):
            cells = row.select('td, th')
            if not cells: continue
            label = cells[0].get_text(strip=True).lower().replace('%','').strip()
            nums  = [clean_num(c.get_text(strip=True).replace('%','').replace('x','')) for c in cells[1:]]
            valid = [n for n in nums if n is not None]
            if not valid: continue
            if   label in ('roe','return on equity'):
                if d['roe']  is None: d['roe']  = valid[-1]
            elif label in ('roce','return on capital employed'):
                if d['roce'] is None: d['roce'] = valid[-1]
            elif 'current ratio' in label and d['current_ratio'] is None:
                d['current_ratio'] = valid[-1]
            elif 'interest coverage' in label and d['interest_coverage'] is None:
                d['interest_coverage'] = valid[-1]
            elif 'debtor days' in label:
                d['_debtor_days'] = valid[-1]

    # ── FII/DII change ───────────────────────────────────────────────────────
    if d['fii_change'] is None and d.get('fii_holding') and d.get('_fii_prev'):
        d['fii_change'] = round(d['fii_holding'] - d['_fii_prev'], 2)
    if d['dii_change'] is None and d.get('dii_holding') and d.get('_dii_prev'):
        d['dii_change'] = round(d['dii_holding'] - d['_dii_prev'], 2)
    if d['promoter_change'] is None and d.get('promoter_holding') and d.get('promoter_holding_prev'):
        d['promoter_change'] = round(d['promoter_holding'] - d['promoter_holding_prev'], 2)

    # ── EPS growth fallback ──────────────────────────────────────────────────
    if d['eps_growth_5y'] is None:
        d['eps_growth_5y'] = d.get('profit_growth_5y') or d.get('profit_growth_3y')

    # ── PEG ─────────────────────────────────────────────────────────────────
    if d['peg'] is None and d.get('pe') and d.get('profit_growth_3y') and d['profit_growth_3y']>0:
        d['peg'] = round(d['pe']/d['profit_growth_3y'],2)

    return d


def fetch_stock(base_url):
    base = base_url.rstrip('/')
    try:
        data = scrape_screener(base + '/consolidated/')
        if data.get('market_cap') is not None:
            return data
    except: pass
    return scrape_screener(base + '/')

def search_stock(query):
    r = SESSION.get(
        f"https://www.screener.in/api/company/search/?q={query}&v=3&fts=1",
        timeout=10)
    return r.json()

# ── NSE LIVE DATA ─────────────────────────────────────────────────────────────
def fetch_nse_live(symbol):
    try:
        NSE_SESSION.get("https://www.nseindia.com", timeout=10)
        r  = NSE_SESSION.get(
            f"https://www.nseindia.com/api/quote-equity?symbol={symbol.upper()}",
            timeout=10)
        d  = r.json()
        pi = d.get('priceInfo', {})
        ti = d.get('marketDeptOrderBook', {}).get('tradeInfo', {})
        result = {
            'ltp':            pi.get('lastPrice'),
            'change_pct':     pi.get('pChange'),
            'high':           pi.get('intraDayHighLow', {}).get('max'),
            'low':            pi.get('intraDayHighLow', {}).get('min'),
            'week52_high':    pi.get('weekHighLow', {}).get('max'),
            'week52_low':     pi.get('weekHighLow', {}).get('min'),
            'upper_circuit':  pi.get('upperCP'),
            'lower_circuit':  pi.get('lowerCP'),
            'volume':         ti.get('totalTradedVolume'),
            'delivery_qty':   ti.get('deliveryQuantity'),
            'delivery_pct':   ti.get('deliveryToTradedQuantity'),
            'total_value':    ti.get('totalTradedValue'),
            'vwap':           pi.get('vwap'),
        }
        # Fetch ATH separately from 52W data (use 5Y high as proxy)
        try:
            r2 = NSE_SESSION.get(
                f"https://www.nseindia.com/api/chart-databyindex?index={symbol.upper()}EQN&indices=true",
                timeout=8)
            if r2.status_code == 200:
                gd = r2.json().get('grapthData', [])
                if gd:
                    all_h = [x[1] for x in gd if isinstance(x, list) and len(x)>1]
                    if all_h: result['ath'] = round(max(all_h), 2)
        except: pass
        return result
    except:
        return {}

def fetch_best_live_price(symbol):
    """
    Sabse accurate real-time price fetch karo — multiple sources try karta hai:
    1. yfinance fast_info  (sabse fresh — real-time)
    2. Google Finance      (fast & reliable)
    3. NSE API lastPrice   (fallback)
    Returns float or None
    """
    sym = symbol.upper().strip()

    # ── Source 1: yfinance fast_info (real-time, no cache) ───────────────────
    try:
        tk_obj = yf.Ticker(f"{sym}.NS")
        fi = tk_obj.fast_info
        price = fi.get('last_price') or fi.get('lastPrice')
        if price and float(price) > 0:
            return float(price)
    except Exception:
        pass

    # ── Source 2: Google Finance JSON (very fresh) ────────────────────────────
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}.NS?interval=1m&range=1d"
        r = requests.get(url, timeout=8, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        })
        if r.status_code == 200:
            meta = r.json().get('chart', {}).get('result', [{}])[0].get('meta', {})
            price = meta.get('regularMarketPrice') or meta.get('previousClose')
            if price and float(price) > 0:
                return float(price)
    except Exception:
        pass

    # ── Source 3: NSE API fallback ────────────────────────────────────────────
    try:
        nse = fetch_nse_live(sym)
        price = nse.get('ltp')
        if price and float(price) > 0:
            return float(price)
    except Exception:
        pass

    return None


def fetch_nse_market_data(data_type):
    """Fetch NSE market screener data — correct working endpoints"""

    # These are the ACTUAL working NSE API endpoints
    ENDPOINTS = {
        'gainers': "https://www.nseindia.com/api/live-analysis-variations?index=gainers&limit=50",
        'losers':  "https://www.nseindia.com/api/live-analysis-variations?index=loosers&limit=50",
        'volume':  "https://www.nseindia.com/api/live-analysis-variations?index=volumeSpurts&limit=50",
        'active':  "https://www.nseindia.com/api/live-analysis-variations?index=mostActiveSec&limit=50",
        '52high':  "https://www.nseindia.com/api/live-analysis-variations?index=nearWKH&limit=50",
        '52low':   "https://www.nseindia.com/api/live-analysis-variations?index=nearWKL&limit=50",
        'advance': "https://www.nseindia.com/api/live-analysis-variations?index=advances&limit=50",
        'decline': "https://www.nseindia.com/api/live-analysis-variations?index=declines&limit=50",
        'large':   "https://www.nseindia.com/api/block-deal",
        'index':   "https://www.nseindia.com/api/allIndices",
    }

    url = ENDPOINTS.get(data_type)
    if not url: return []

    def _normalize(item, data_type):
        """Extract fields from NSE item — handles all key variants"""
        sym  = (item.get('symbol') or item.get('nsecode') or
                item.get('ticker') or '').strip()
        name = (item.get('companyName') or item.get('name') or
                item.get('company') or sym)
        ltp  = (item.get('ltp') or item.get('lastPrice') or
                item.get('last') or item.get('ltP') or item.get('closePrice') or 0)
        chg  = (item.get('pChange') or item.get('perChange') or
                item.get('pchng') or item.get('percentChange') or
                item.get('per') or 0)
        vol  = (item.get('totalTradedVolume') or item.get('tradedVolume') or
                item.get('quantityTraded') or item.get('trdVol') or
                item.get('volume') or 0)
        try: ltp = float(str(ltp).replace(',',''))
        except: ltp = 0
        try: chg = float(str(chg).replace(',','').replace('%',''))
        except: chg = 0
        try: vol = float(str(vol).replace(',',''))
        except: vol = 0
        return {
            'symbol':     sym,
            'company':    name,
            'ltp':        ltp,
            'change_pct': chg,
            'volume':     vol,
            'high52':     item.get('week52High') or item.get('wkhi') or None,
            'low52':      item.get('week52Low')  or item.get('wklo') or None,
        }

    try:
        NSE_SESSION.headers.update({
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'X-Requested-With': 'XMLHttpRequest',
        })
        # Must visit homepage first to get valid cookies
        NSE_SESSION.get("https://www.nseindia.com", timeout=10)
        NSE_SESSION.get("https://www.nseindia.com/market-data/live-equity-market", timeout=8)

        r = NSE_SESSION.get(url, timeout=15)
        print(f"[DEBUG] {data_type} status={r.status_code} url={url}")
        if r.status_code != 200:
            return []
        raw = r.json()
        print(f"[DEBUG] {data_type} raw keys={list(raw.keys()) if isinstance(raw, dict) else type(raw).__name__} len={len(raw) if isinstance(raw, list) else '?'}")
        if isinstance(raw, dict):
            for k, v in raw.items():
                print(f"  key='{k}' type={type(v).__name__} len={len(v) if isinstance(v,(list,dict)) else v}")


        # ── INDEX ─────────────────────────────────────────────────────────────
        if data_type == 'index':
            rows = []
            for item in raw.get('data', []):
                rows.append({
                    'symbol':     item.get('indexSymbol', item.get('index', '')),
                    'company':    item.get('indexSymbol', item.get('index', '')),
                    'ltp':        item.get('last', item.get('lastPrice', 0)),
                    'change_pct': item.get('percentChange', item.get('pChange', 0)),
                    'volume':     0,
                    'is_index':   True,
                })
            return rows

        # ── LARGE / BLOCK DEALS ───────────────────────────────────────────────
        if data_type == 'large':
            items = raw.get('data', raw) if isinstance(raw, dict) else raw
            rows  = []
            for item in (items or []):
                sym = item.get('symbol', item.get('scripCode', ''))
                rows.append({
                    'symbol':     sym,
                    'company':    item.get('clientName', item.get('name', sym)),
                    'ltp':        item.get('tdTradePrice', item.get('price', 0)),
                    'change_pct': 0,
                    'volume':     item.get('tdTradedQty', item.get('quantity', 0)),
                    'extra':      f"Qty:{item.get('tdTradedQty','')}",
                })
            return rows

        # ── ALL OTHER live-analysis-variations ENDPOINTS ──────────────────────
        # NSE wraps data differently per index — try all known keys
        items = None
        for key in ['data', 'NIFTY500', 'advances', 'declines', 'gainers',
                    'loosers', 'volume', 'nearWKH', 'nearWKL', 'mostActiveSec',
                    'volumeSpurts']:
            val = raw.get(key)
            if isinstance(val, list) and val:
                items = val
                break
        if items is None:
            if isinstance(raw, list) and raw:
                items = raw

        if not items:
            return []

        rows = [_normalize(item, data_type) for item in items if item.get('symbol')]
        return rows[:50]

    except Exception:
        return []


# Hardcoded scan_clauses for each screener — fetched from Network tab
# Ye Vue.js se dynamically render hote hain, HTML mein nahi milte
CHARTINK_SCAN_CLAUSES = {
    "fresh-52-week-highs":
        "( {cash} (  daily high >  1 day ago max( 240 ,  daily close ) and  daily close >  20 and  daily volume >  5000 and  daily close >  1 day ago close and  daily sma(  daily volume , 20 ) *  daily sma( close,20 ) >  20000000 ) )",
    "52-week-high-breakout":
        "( {cash} (  daily close >  1 day ago max( 240 ,  daily high ) ) )",
    "claude-swing-trading-screener":
        "( {cash} (  daily close >  daily ema(  daily close , 21 ) and  daily ema(  daily close , 21 ) >  daily ema(  daily close , 50 ) and  daily rsi( 14 ) >  50 and  daily rsi( 14 ) <  70 and  daily volume >  daily sma(  daily volume , 20 ) and  daily low <=  daily ema(  daily close , 21 ) *  1.02 and  market cap >  500 ) )",
    "claude-positinal-screener":
        "( {cash} (  weekly close >  weekly ema(  weekly close , 10 ) and  weekly ema(  weekly close , 10 ) >  weekly ema(  weekly close , 40 ) and  weekly rsi( 14 ) >  55 and  weekly rsi( 14 ) <  75 and  weekly volume >  weekly sma(  weekly volume , 20 ) and  weekly low <=  weekly ema(  weekly close , 10 ) *  1.02 and  market cap >  1000 ) )",
    "claude-long-term":
        "( {cash} (  monthly close >  monthly ema(  monthly close , 10 ) and  monthly ema(  monthly close , 10 ) >  monthly ema(  monthly close , 40 ) and  monthly rsi( 14 ) >  50 and  monthly close >  monthly open and  monthly volume >  monthly sma(  monthly volume , 12 ) and  monthly low <=  monthly ema(  monthly close , 10 ) *  1.03 and  market cap >  2000 ) )",
    "44-ma-swing-stocks-3":
        "( {cash} (  daily close >  daily sma(  daily close , 44 ) and  daily sma(  daily close , 44 ) >  1 day ago sma(  daily close , 44 ) and  daily sma(  daily close , 44 ) >  daily ema(  daily close , 200 ) and  daily low <=  daily sma(  daily close , 44 ) *  1.02 and  market cap >  500 ) )",
    "copy-stock-near-5-of-52-week-high-36691":
        "( {cash} (  daily close >=  daily max( 252 ,  daily high ) *  .95 and  daily close /  65 days ago close >  1 and  daily close >  10 and  daily ema(  daily close , 20 ) >  daily ema(  daily close , 50 ) and  daily close >  daily ema(  daily close , 21 ) and( {cash} (  yearly return on capital employed percentage >  15 and  yearly return on net worth percentage >=  15 ) ) and  market cap >  1000 and  quarterly net sales >=  1 quarter ago net sales ) )",
    "copy-rb-stockexploder-322":
        "( {cash} (  daily wma( close,1 ) >  monthly wma( close,2 ) +  1 and  monthly wma( close,2 ) >  monthly wma( close,4 ) +  2 and  daily wma( close,1 ) >  weekly wma( close,6 ) +  2 and  weekly wma( close,6 ) >  weekly wma( close,12 ) +  2 and  daily wma( close,1 ) >  4 days ago wma( close,12 ) +  2 and  daily wma( close,1 ) >  2 days ago wma( close,20 ) +  2 and  daily close >  25 and  daily close <=  500 and  weekly volume >  85000 and  quarterly net sales >=  1 quarter ago net sales ) )",
    "copy-vcp-stockexploder-223":
        "( {cash} (  daily avg true range( 14 ) <  10 days ago avg true range( 14 ) and  daily avg true range( 14 ) /  daily close <  0.08 and  daily close >  (  weekly max( 52 ,  weekly close ) *  0.75 ) and  daily ema(  daily close , 50 ) >  daily ema(  daily close , 150 ) and  daily ema(  daily close , 150 ) >  daily ema(  daily close , 200 ) and  daily close >  daily ema(  daily close , 50 ) and  daily close >  10 and  daily close *  daily volume >  1000000 and  quarterly net sales >=  1 quarter ago net sales ) )",
    "copy-breakouts-in-short-term-5280":
        "( {cash} (  daily max( 5 ,  daily close ) >  6 days ago max( 120 ,  daily close ) *  1.05 and  daily volume >  daily sma( volume,5 ) and  daily close >  1 day ago close and  quarterly net sales >=  1 quarter ago net sales ) )",
    "badiya-vala-scanner":
        "( {cash} (  daily volume >  daily sma(  daily volume , 20 ) and  daily close >  daily upper bollinger band( 20 , 2 ) and  weekly close >  weekly upper bollinger band( 20 , 2 ) and  monthly close >  monthly upper bollinger band( 20 , 2 ) and  daily rsi( 14 ) >  60 and  weekly rsi( 14 ) >  60 and  monthly rsi( 14 ) >  60 and  monthly wma(  monthly close , 30 ) >  monthly wma(  monthly close , 50 ) and  1 month ago  wma(  monthly close , 30 )<=  1 month ago  wma(  monthly close , 50 ) and  monthly wma(  monthly close , 30 ) >  60 and  monthly wma(  monthly close , 50 ) >  60 ) )",
    "swing-scanner-20102336":
        "( {cash} (  daily open >=  1 day ago close and  daily close >=  daily ema(  daily close , 20 ) and  daily ema(  daily close , 10 ) >=  daily ema(  daily close , 20 ) and  daily macd line( 26 , 12 , 9 ) >  daily macd signal( 26 , 12 , 9 ) and  1 day ago  macd line( 26 , 12 , 9 ) <=  1 day ago  macd signal( 26 , 12 , 9 ) and  daily rsi( 14 ) >=  59 and  market cap >=  2000 and  quarterly net sales >=  1 quarter ago net sales ) )",
    # ── ETF Screeners ──────────────────────────────────────────────────────────
    "etf-50-rsi-crossover":
        "( {cash} (  daily rsi( 14 ) >  50 and  1 day ago  rsi( 14 ) <  50 ) )",
    "etf-scanner-7993":
        "( {cash} (  daily volume >  100000 and  daily close >  daily ema(  daily close , 50 ) and  daily rsi( 14 ) >  55 and  daily close >  1 day ago max( 20 ,  daily high ) ) )",
}

def fetch_chartink(url):
    """Fetch Chartink screener — uses pre-fetched scan_clause + session cookies"""
    import re as _re, json as _json
    try:
        # Extract slug from URL
        slug = url.rstrip("/").split("/")[-1]

        cs = requests.Session()
        cs.headers.update({
            "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        for cname, cval in CHARTINK_COOKIES.items():
            cs.cookies.set(cname, cval, domain="chartink.com")

        # GET page just for fresh CSRF token
        r = cs.get(url, timeout=18, allow_redirects=True)
        if "login" in r.url.lower():
            print("[Chartink] Cookies expired!")
            return []

        soup = BeautifulSoup(r.text, "html.parser")
        csrf = ""
        meta = soup.find("meta", {"name": "csrf-token"})
        if meta: csrf = meta.get("content", "")

        # Get scan_clause — use hardcoded if available, else try extract from page
        scan_clause = CHARTINK_SCAN_CLAUSES.get(slug, "")

        # If not hardcoded, try JSON pattern in page
        if not scan_clause:
            m = _re.search(r'"scan_clause"\s*:\s*"((?:[^"\\]|\\.)+)"', r.text)
            if m:
                scan_clause = m.group(1).replace('\\"', '"')
                print(f"[Chartink] scan_clause from page JSON: {scan_clause[:60]}")

        print(f"[Chartink] slug={slug} clause_len={len(scan_clause)} csrf={'OK' if csrf else 'MISSING'}")

        if not scan_clause:
            print(f"[Chartink] No scan_clause for slug '{slug}' — add it to CHARTINK_SCAN_CLAUSES!")
            return []

        # POST as JSON (confirmed from network tab)
        cs.headers.update({
            "X-CSRF-TOKEN":     csrf,
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type":     "application/json",
            "Accept":           "application/json, text/plain, */*",
            "Origin":           "https://chartink.com",
            "Referer":          url,
        })
        post_r = cs.post("https://chartink.com/screener/process",
                         data=_json.dumps({"scan_clause": scan_clause}),
                         timeout=25)
        print(f"[Chartink] POST {post_r.status_code} | {post_r.text[:200]}")

        # Fallback to form-encoded if JSON fails
        if post_r.status_code != 200 or post_r.json().get("scan_error"):
            cs.headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
            post_r = cs.post("https://chartink.com/screener/process",
                             data={"scan_clause": scan_clause}, timeout=25)
            print(f"[Chartink] POST(form) {post_r.status_code} | {post_r.text[:200]}")

        if post_r.status_code != 200: return []

        items = post_r.json().get("data", [])
        print(f"[Chartink] {len(items)} stocks")
        return _parse_chartink_items(items)

    except Exception as ex:
        print(f"[Chartink Error] {ex}")
        import traceback; traceback.print_exc()
        return []


def _parse_chartink_items(items):
    rows = []
    for item in items:
        sym  = (item.get("nsecode") or item.get("symbol") or item.get("ticker") or "").strip()
        name = (item.get("name") or item.get("company") or sym).strip()
        ltp  = item.get("close",  item.get("ltp",   item.get("price", 0)))
        chg  = item.get("per_chg", item.get("pChange", item.get("per",  0)))
        vol  = item.get("volume",  item.get("vol",   0))
        try: ltp = float(str(ltp).replace(",",""))
        except: ltp = 0
        try: chg = float(str(chg).replace(",","").replace("%",""))
        except: chg = 0
        try: vol = float(str(vol).replace(",",""))
        except: vol = 0
        if sym:
            rows.append({"symbol":sym,"company":name,"ltp":ltp,"change_pct":chg,"volume":vol})
    return rows



# ── ETF DATA ──────────────────────────────────────────────────────────────────
def fetch_nse_etf_list():
    """
    NSE ETF list — deduplicated by symbol, sorted % high→low.
    NSE /api/etf returns same symbol multiple times (different schemes).
    We keep only the entry with the best/most data per symbol.
    
    Actual NSE API fields (verified from live response):
      symbol, meta.companyName, lastPrice, pChange, change,
      previousClose, open, dayHigh, dayLow,
      totalTradedVolume, totalTradedValue, yearHigh, yearLow
    """
    import time as _t

    def _f(v):
        if v is None:
            return 0.0
        if isinstance(v, dict):
            for key in ('value', 'amount', 'price', 'lastPrice', 'close'):
                if key in v:
                    return _f(v[key])
            return 0.0
        t = str(v).strip()
        if t in ['', '-', '--', 'N/A', 'na', 'NA', '—', '–', 'null', 'nil']:
            return 0.0
        t = t.replace('₹', '').replace('+', '').replace('−', '-')
        t = t.replace(',', '').replace('%', '').strip()
        try:
            return float(t)
        except:
            return 0.0

    # ── Warm up session (MUST before any API call) ────────────────────────
    try:
        NSE_SESSION.get('https://www.nseindia.com', timeout=12)
        _t.sleep(0.5)
        NSE_SESSION.get(
            'https://www.nseindia.com/market-data/exchange-traded-funds-etf',
            timeout=10)
        _t.sleep(0.5)
    except: pass

    raw_items = []

    # ── Fetch /api/etf ────────────────────────────────────────────────────
    try:
        r = NSE_SESSION.get(
            'https://www.nseindia.com/api/etf',
            headers={
                'Accept':           'application/json, text/plain, */*',
                'Referer':          'https://www.nseindia.com/market-data/exchange-traded-funds-etf',
                'X-Requested-With': 'XMLHttpRequest',
            }, timeout=20)
        print(f'[ETF] status={r.status_code} len={len(r.content)}')
        if r.status_code == 200 and len(r.content) > 100:
            data = r.json()
            raw_items = data if isinstance(data, list) else data.get('data', [])
            if raw_items:
                print(f'[ETF] {len(raw_items)} raw items | '
                      f'keys={list(raw_items[0].keys())[:12]}')
    except Exception as ex:
        print(f'[ETF fetch] {ex}')

    # ── Parse + deduplicate by symbol ─────────────────────────────────────
    best = {}
    for item in raw_items:
        sym = str(item.get('symbol') or '').strip()
        if not sym: continue

        meta = item.get('meta') or {}
        name = str(
            meta.get('companyName') or
            item.get('companyName') or
            item.get('underlyingAsset') or sym
        ).strip()

        ltp = _f(
            item.get('ltP') or
            item.get('lastPrice') or
            item.get('ltp') or
            item.get('nav')
        )
        # 'per' = % change, 'chn' = absolute ₹ change in NSE ETF API
        raw_chg = _f(
            item.get('per') or              # ✅ NSE actual % key (verified)
            item.get('pChange') or
            item.get('perChange') or
            item.get('percentageChange')
        )
        chg = raw_chg if abs(raw_chg) <= 50 else 0

        # previousClose — strictly yesterday's close only
        prev = _f(
            item.get('previousClose') or item.get('prevClose') or
            item.get('previousClosePrice') or item.get('prev_close')
        )
        # If prev missing, derive from ltp and chn (absolute ₹ change)
        if prev == 0:
            chn = _f(item.get('chn') or item.get('change') or 0)
            if ltp > 0 and chn != 0:
                prev = round(ltp - chn, 2)

        vol = _f(
            item.get('qty') or              # ✅ NSE actual volume key (verified)
            item.get('totalTradedVolume') or
            item.get('tradedVolume') or
            item.get('quantity') or
            item.get('volume')
        )

        entry = {'symbol': sym, 'name': name,
                 'ltp': ltp, 'chg': chg, 'vol': vol,
                 '_prev': prev}

        if sym not in best or ltp > best[sym]['ltp']:
            best[sym] = entry

    etfs = list(best.values())

    # ── Use NSE's own per field as chg (most accurate — official NSE data) ─────
    # NSE 'per' = official % change from previous close (same as NSE website shows)
    # Only recalculate if per was 0 or missing
    for e in etfs:
        if e.get('chg') == 0:
            ltp_v  = e.get('ltp', 0)
            prev_v = e.get('_prev', 0)
            if ltp_v > 0 and prev_v > 0:
                e['chg'] = round((ltp_v - prev_v) / prev_v * 100, 2)
    print(f'[ETF] NSE dedup: {len(etfs)} | ltp>{sum(1 for e in etfs if e["ltp"]>0)} | prev>{sum(1 for e in etfs if e.get("_prev",0)>0)}')

    # ── Fix using yfinance for ETFs where prev=0 (can't calc % without prev) ─
    need_fix = [e for e in etfs if e.get('_prev', 0) == 0 and e['ltp'] > 0]
    if need_fix:
        print(f'[ETF] yfinance prev_close needed for {len(need_fix)} ETFs')
        try:
            syms_yf = ' '.join(f"{e['symbol']}.NS" for e in need_fix[:80])
            tickers  = yf.Tickers(syms_yf)
            for e in need_fix[:80]:
                try:
                    fi  = tickers.tickers.get(f"{e['symbol']}.NS")
                    if not fi: continue
                    inf = fi.fast_info
                    prev_close = getattr(inf, 'previous_close', None)
                    cur        = getattr(inf, 'last_price', None)
                    if prev_close and prev_close > 0:
                        e['_prev'] = round(float(prev_close), 2)
                    if cur and e['ltp'] == 0:
                        e['ltp'] = round(float(cur), 2)
                except: pass
        except Exception as ex:
            print(f'[ETF yf prev] {ex}')

    return etfs

def fetch_nse_etf_screener():
    all_etfs = fetch_nse_etf_list()
    if not all_etfs: return []

    def _pct(e):
        ltp  = e.get('ltp', 0)
        prev = e.get('_prev', 0)
        if ltp > 0 and prev > 0:
            return round((ltp - prev) / prev * 100, 2)
        return 0

    screened = [e for e in all_etfs
                if e.get('ltp', 0) > 0
                and e.get('vol', 0) >= 10000
                and _pct(e) > -5]
    screened.sort(key=_pct, reverse=True)
    return screened


class App:
    def __init__(self, root):
        self.root  = root
        root.title("📊 Stock Fundamental Analyzer")
        root.geometry("1100x800")
        root.minsize(800, 600)
        root.resizable(True, True)
        root.configure(bg=BG)
        self._tabs = {}
        self._hm_content = None
        self._hm_tabs    = {}
        self._nav_stack  = []   # Navigation history: list of (type, args) tuples
        self._current_chartink = None   # Currently shown chartink list state
        self._build()

    def _build(self):
        # ── TOP BAR ──────────────────────────────────────────────────────────
        top = tk.Frame(self.root, bg=CARD, pady=0)
        top.pack(fill='x')

        # Left — Logo + title
        lf = tk.Frame(top, bg=CARD); lf.pack(side='left', padx=18, pady=12)
        tk.Label(lf, text="📊", font=('Arial', 20), bg=CARD, fg=ACCENT).pack(side='left')
        tf2 = tk.Frame(lf, bg=CARD); tf2.pack(side='left', padx=10)
        tk.Label(tf2, text="Stock Analyzer", font=('Arial', 15, 'bold'),
                 bg=CARD, fg=TEXT).pack(anchor='w')
        tk.Label(tf2, text="Screener.in + NSE Live",
                 font=('Arial', 9), bg=CARD, fg=ACCENT).pack(anchor='w')

        # Right — Search bar + Close button
        rf2 = tk.Frame(top, bg=CARD); rf2.pack(side='right', padx=12, pady=10)

        # ✕ Close app button — right side of topbar
        tk.Button(rf2, text="✕", font=('Arial', 12, 'bold'),
                  bg='#2A0D1A', fg=RED, relief='flat',
                  padx=12, pady=7, cursor='hand2',
                  command=self.root.destroy).pack(side='right', padx=(8,0))

        sf = tk.Frame(rf2, bg='#141C35',
                      highlightbackground=ACCENT,
                      highlightthickness=1)
        sf.pack(side='right')
        self.q = tk.StringVar()
        en = tk.Entry(sf, textvariable=self.q, font=('Arial', 12),
                      bg='#141C35', fg=TEXT, insertbackground=ACCENT,
                      relief='flat', width=30)
        en.pack(side='left', padx=(14,4), ipady=8)
        en.bind('<Return>', lambda _: self._search())
        en.bind('<KeyRelease>', self._on_key_suggest)
        self._entry = en
        self._dd_win = None
        tk.Button(sf, text="  🔍 Search  ", font=('Arial', 10, 'bold'),
                  bg=ACCENT, fg='white', relief='flat',
                  padx=14, pady=7, cursor='hand2',
                  command=self._search).pack(side='left')

        # Divider
        tk.Frame(self.root, bg=ACCENT, height=2).pack(fill='x')

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill='both', expand=True, padx=10, pady=8)

        self.sidebar = tk.Frame(body, bg=CARD, width=195)
        self.sidebar.pack(side='left', fill='y', padx=(0, 6))
        self.sidebar.pack_propagate(False)

        # ── Watchlist button ──────────────────────────────────────────────────
        wl_count = len(APP_DATA.get('watchlist', {}))
        self._wl_btn = tk.Button(self.sidebar,
                  text=f"⭐  My Watchlist  ({wl_count})",
                  font=('Arial', 9, 'bold'), bg='#1A1400', fg=YELLOW,
                  relief='flat', padx=8, pady=9, cursor='hand2', anchor='w',
                  command=self._show_watchlist)
        self._wl_btn.pack(fill='x', padx=6, pady=(10,4))
        tk.Frame(self.sidebar, bg=BORDER, height=1).pack(fill='x', padx=8, pady=(0,4))

        # ── ETF Section button ────────────────────────────────────────────────
        tk.Button(self.sidebar,
                  text="📦  NSE ETF Explorer",
                  font=('Arial', 9, 'bold'), bg='#0D1A30', fg='#4FC3F7',
                  relief='flat', padx=8, pady=9, cursor='hand2', anchor='w',
                  command=self._show_etf_section).pack(fill='x', padx=6, pady=(0,4))
        tk.Frame(self.sidebar, bg=BORDER, height=1).pack(fill='x', padx=8, pady=(0,4))

        # ── IPO Tab button ────────────────────────────────────────────────────
        tk.Button(self.sidebar,
                  text="🚀  IPO Hub & Score",
                  font=('Arial', 9, 'bold'), bg='#1A0D30', fg='#C678FF',
                  relief='flat', padx=8, pady=9, cursor='hand2', anchor='w',
                  command=self._show_ipo_section).pack(fill='x', padx=6, pady=(0,4))
        tk.Frame(self.sidebar, bg=BORDER, height=1).pack(fill='x', padx=8, pady=(0,4))

        # ── Chartink Screeners label ──────────────────────────────────────────
        tk.Label(self.sidebar, text="📡  Chartink Screeners",
                 font=('Arial', 9, 'bold'), bg=CARD, fg=TEXT
                 ).pack(anchor='w', padx=10, pady=(8,5))
        tk.Frame(self.sidebar, bg=ACCENT, height=1).pack(fill='x', padx=8, pady=(0,4))

        mkt_links = [
            ("🏔️ 52W High",              "https://chartink.com/screener/fresh-52-week-highs"),
            ("📈 52W High Breakout",      "https://chartink.com/screener/52-week-high-breakout"),
            ("📊 Near 52W High",          "https://chartink.com/screener/copy-stock-near-5-of-52-week-high-36691"),
            ("🔵 Swing Scanner",          "https://chartink.com/screener/claude-swing-trading-screener"),
            ("🟡 Positional Scanner",     "https://chartink.com/screener/claude-positinal-screener"),
            ("🟢 Long Term Scanner",      "https://chartink.com/screener/claude-long-term"),
            ("📐 44 MA Scanner",          "https://chartink.com/screener/44-ma-swing-stocks-3"),
            ("🚀 Rocket Base",            "https://chartink.com/screener/copy-rb-stockexploder-322"),
            ("🌀 VCP Scanner",            "https://chartink.com/screener/copy-vcp-stockexploder-223"),
            ("💥 Breakout Short Term",    "https://chartink.com/screener/copy-breakouts-in-short-term-5280"),
            ("⭐ Badiya Scanner",         "https://chartink.com/screener/badiya-vala-scanner"),
            ("🔍 Swing Scanner 2",        "https://chartink.com/screener/swing-scanner-20102336"),
        ]

        mkt_scroll_c = tk.Canvas(self.sidebar, bg=CARD, highlightthickness=0)
        mkt_sb = ttk.Scrollbar(self.sidebar, orient='vertical', command=mkt_scroll_c.yview)
        mkt_scroll_c.configure(yscrollcommand=mkt_sb.set)
        mkt_frame = tk.Frame(mkt_scroll_c, bg=CARD)
        mkt_scroll_c.create_window((0,0), window=mkt_frame, anchor='nw', tags='mf')
        mkt_frame.bind('<Configure>',
            lambda e: mkt_scroll_c.configure(scrollregion=mkt_scroll_c.bbox('all')))
        mkt_scroll_c.bind('<Configure>',
            lambda e: mkt_scroll_c.itemconfig('mf', width=e.width))
        mkt_scroll_c.bind('<MouseWheel>',
            lambda e: mkt_scroll_c.yview_scroll(-1*(e.delta//120), 'units'))
        mkt_sb.pack(side='right', fill='y')
        mkt_scroll_c.pack(fill='both', expand=True, padx=3)

        for label, url in mkt_links:
            btn = tk.Button(mkt_frame, text=label,
                            font=('Arial', 9, 'bold'), bg=CARD2, fg=TEXT,
                            relief='flat', padx=8, pady=8,
                            cursor='hand2', anchor='w',
                            command=lambda u=url, l=label: self._open_chartink(u, l))
            btn.pack(fill='x', pady=2, padx=4)
            btn.bind('<Enter>', lambda e, b=btn: b.config(bg='#1E285A', fg=ACCENT))
            btn.bind('<Leave>', lambda e, b=btn: b.config(bg=CARD2, fg=TEXT))

        self.main = tk.Frame(body, bg=BG)
        self.main.pack(side='left', fill='both', expand=True)

        # Right panel — News + Docs
        self.rpanel = tk.Frame(body, bg=CARD, width=260)
        self.rpanel.pack(side='right', fill='y', padx=(6, 0))
        self.rpanel.pack_propagate(False)
        self._build_rpanel()

        self._welcome()

    def _build_rpanel(self):
        """Right panel — default: Sectors + Indices. Stock load hone par: News + Docs"""
        for w in self.rpanel.winfo_children(): w.destroy()

        # Header row with refresh button
        hrow = tk.Frame(self.rpanel, bg=CARD); hrow.pack(fill='x', pady=(8,2), padx=6)
        tk.Label(hrow, text="📰  News & Documents",
                 font=('Arial', 10, 'bold'), bg=CARD, fg=TEXT
                 ).pack(side='left', padx=4)
        tk.Button(hrow, text="🔄", font=('Arial', 9),
                  bg=CARD2, fg=ACCENT, relief='flat', padx=6, pady=2,
                  cursor='hand2',
                  command=lambda: self._load_rpanel(
                      getattr(self,'_rpanel_sym',''),
                      getattr(self,'_rpanel_name',''))
                  ).pack(side='right', padx=2)

        tk.Frame(self.rpanel, bg=ACCENT, height=1).pack(fill='x', padx=8)

        # Scrollable content
        rcanvas = tk.Canvas(self.rpanel, bg=CARD, highlightthickness=0)
        rsb = ttk.Scrollbar(self.rpanel, orient='vertical', command=rcanvas.yview)
        self.rcontent = tk.Frame(rcanvas, bg=CARD)
        self.rcontent.bind('<Configure>',
            lambda e: rcanvas.configure(scrollregion=rcanvas.bbox('all')))
        rcanvas.create_window((0,0), window=self.rcontent, anchor='nw', tags='rc')
        rcanvas.configure(yscrollcommand=rsb.set)
        rcanvas.bind('<Configure>', lambda e: rcanvas.itemconfig('rc', width=e.width))
        rcanvas.bind('<MouseWheel>', lambda e: rcanvas.yview_scroll(-1*(e.delta//120),'units'))
        rsb.pack(side='right', fill='y')
        rcanvas.pack(side='left', fill='both', expand=True)

        # Default content: Sectors + Indices
        self._render_sectors_default()

    def _render_sectors_default(self):
        """Default right panel — Live NSE Broad Market + Sectoral indices with % change"""
        for w in self.rcontent.winfo_children(): w.destroy()

        # Loading indicator
        load_lbl = tk.Label(self.rcontent, text="⏳ Indices load ho rahi hain...",
                            font=('Arial', 8), bg=CARD, fg=SUBTEXT)
        load_lbl.pack(pady=12)

        # Fetch in background
        threading.Thread(target=self._fetch_indices_data, daemon=True).start()

    def _fetch_indices_data(self):
        """Fetch allIndices from NSE API — split into 4 categories"""
        all_rows = self._nse_fetch_all_indices()
        broad_rows    = [r for r in all_rows if r.get('cat') == 'broad']
        sectoral_rows = [r for r in all_rows if r.get('cat') == 'sectoral']
        thematic_rows = [r for r in all_rows if r.get('cat') == 'thematic']
        strategy_rows = [r for r in all_rows if r.get('cat') == 'strategy']
        self.root.after(0, lambda: self._render_indices(
            broad_rows, sectoral_rows, thematic_rows, strategy_rows))

    def _nse_fetch_all_indices(self):
        """Core NSE allIndices fetch — exact names from NSE API debug output"""

        BROAD = {
            'NIFTY 50', 'NIFTY NEXT 50', 'NIFTY 100', 'NIFTY 200', 'NIFTY 500',
            'NIFTY MIDCAP 50', 'NIFTY MIDCAP 100', 'NIFTY MIDCAP 150',
            'NIFTY SMLCAP 50', 'NIFTY SMLCAP 100', 'NIFTY SMLCAP 250',
            'NIFTY MIDSML 400', 'NIFTY LARGEMID250', 'NIFTY MID SELECT',
            'NIFTY MICROCAP250', 'NIFTY TOTAL MKT', 'INDIA VIX',
            'NIFTY500 MULTICAP', 'NIFTY500 LMS EQL', 'NIFTY FPI 150',
        }
        SECTORAL = {
            'NIFTY AUTO', 'NIFTY BANK', 'NIFTY FIN SERVICE', 'NIFTY FINSRV25 50',
            'NIFTY FMCG', 'NIFTY IT', 'NIFTY MEDIA', 'NIFTY METAL',
            'NIFTY PHARMA', 'NIFTY PSU BANK', 'NIFTY REALTY', 'NIFTY PVT BANK',
            'NIFTY HEALTHCARE', 'NIFTY CONSR DURBL', 'NIFTY OIL AND GAS',
            'NIFTY MIDSML HLTH', 'NIFTY CHEMICALS', 'NIFTY500 HEALTH',
            'NIFTY FINSEREXBNK', 'NIFTY MS IT TELCM', 'NIFTY MS FIN SERV',
        }
        THEMATIC = {
            'NIFTY COMMODITIES', 'NIFTY CONSUMPTION', 'NIFTY CPSE', 'NIFTY ENERGY',
            'NIFTY INFRA', 'NIFTY MNC', 'NIFTY PSE', 'NIFTY SERV SECTOR',
            'NIFTY100 LIQ 15', 'NIFTY MID LIQ 15', 'NIFTY IND DIGITAL',
            'NIFTY100 ESG', 'NIFTY100ESGSECLDR', 'NIFTY INDIA MFG',
            'NIFTY TATA 25 CAP', 'NIFTY MULTI MFG', 'NIFTY MULTI INFRA',
            'NIFTY IND DEFENCE', 'NIFTY IND TOURISM', 'NIFTY CAPITAL MKT',
            'NIFTY EV', 'NIFTY NEW CONSUMP', 'NIFTY CORP MAATR',
            'NIFTY MOBILITY', 'NIFTY100 ENH ESG', 'NIFTY COREHOUSING',
            'NIFTY HOUSING', 'NIFTY IPO', 'NIFTY MS IND CONS',
            'NIFTY NONCYC CONS', 'NIFTY RURAL', 'NIFTY SHARIAH 25',
            'NIFTY TRANS LOGIS', 'NIFTY50 SHARIAH', 'NIFTY500 SHARIAH',
            'NIFTY SME EMERGE', 'NIFTY INTERNET', 'NIFTY WAVES',
            'NIFTY INFRALOG', 'NIFTY RAILWAYSPSU', 'NIFTYCONGLOMERATE',
        }
        STRATEGY = {
            'NIFTY DIV OPPS 50', 'NIFTY50 VALUE 20', 'NIFTY100 QUALTY30',
            'NIFTY50 EQL WGT', 'NIFTY100 EQL WGT', 'NIFTY100 LOWVOL30',
            'NIFTY ALPHA 50', 'NIFTY200 QUALTY30', 'NIFTY ALPHALOWVOL',
            'NIFTY200MOMENTM30', 'NIFTY M150 QLTY50', 'NIFTY200 ALPHA 30',
            'NIFTYM150MOMNTM50', 'NIFTY500MOMENTM50', 'NIFTYMS400 MQ 100',
            'NIFTYSML250MQ 100', 'NIFTY TOP 10 EW', 'NIFTY AQL 30',
            'NIFTY AQLV 30', 'NIFTY HIGHBETA 50', 'NIFTY LOW VOL 50',
            'NIFTY QLTY LV 30', 'NIFTY SML250 Q50', 'NIFTY TOP 15 EW',
            'NIFTY100 ALPHA 30', 'NIFTY200 VALUE 30', 'NIFTY500 EW',
            'NIFTY MULTI MQ 50', 'NIFTY500 VALUE 50', 'NIFTY TOP 20 EW',
            'NIFTY500 QLTY50', 'NIFTY500 LOWVOL50', 'NIFTY500 MQVLV50',
            'NIFTY500 FLEXICAP', 'NIFTY TMMQ 50', 'NIFTY GROWSECT 15',
            'NIFTY50 USD',
        }
        # Bond/other indices — skip these
        SKIP = {
            'NIFTY GS 8 13YR', 'NIFTY GS 10YR', 'NIFTY GS 10YR CLN',
            'NIFTY GS 4 8YR', 'NIFTY GS 11 15YR', 'NIFTY GS 15YRPLUS',
            'NIFTY GS COMPSITE', 'BHARATBOND-APR30', 'BHARATBOND-APR31',
            'BHARATBOND-APR32', 'BHARATBOND-APR33',
            'NIFTY50 TR 2X LEV', 'NIFTY50 PR 2X LEV',
            'NIFTY50 TR 1X INV', 'NIFTY50 PR 1X INV', 'NIFTY50 DIV POINT',
        }

        rows = []
        try:
            NSE_SESSION.get("https://www.nseindia.com", timeout=8)
            r = NSE_SESSION.get("https://www.nseindia.com/api/allIndices", timeout=12)
            if r.status_code != 200:
                return rows

            for item in r.json().get('data', []):
                sym  = (item.get('indexSymbol') or item.get('index', '')).strip()
                if not sym or sym in SKIP: continue
                chg  = item.get('percentChange', item.get('pChange', 0))
                last = item.get('last', item.get('lastPrice', 0))
                try: chg  = float(chg)
                except: chg  = 0.0
                try: last = float(last)
                except: last = 0.0

                if   sym in BROAD:    cat = 'broad'
                elif sym in SECTORAL: cat = 'sectoral'
                elif sym in THEMATIC: cat = 'thematic'
                elif sym in STRATEGY: cat = 'strategy'
                else:
                    # New index NSE ne add kiya — print karo
                    print(f"[NEW INDEX] {sym!r} — thematic mein dala")
                    cat = 'thematic'

                rows.append({'name': sym, 'last': last, 'chg': chg, 'cat': cat})

        except Exception as ex:
            print(f"[DEBUG] allIndices error: {ex}")
        return rows

    def _render_indices(self, broad_rows, sectoral_rows,
                        thematic_rows=None, strategy_rows=None):
        """Right panel — 4 collapsible sections, each index row clickable → center heatmap"""
        thematic_rows = thematic_rows or []
        strategy_rows = strategy_rows or []

        for w in self.rcontent.winfo_children(): w.destroy()

        sections = [
            ("📊 Broad Market Indices",  broad_rows,    '#1565C0'),
            ("🏭 Sectoral Indices",      sectoral_rows, '#6A1B9A'),
            ("🎯 Thematic Indices",      thematic_rows, '#00695C'),
            ("⚙️ Strategy Indices",     strategy_rows, '#E65100'),
        ]

        for title, rows, hdr_color in sections:
            count = len(rows)

            # ── Section header (collapsible) ──────────────────────────────────
            hf = tk.Frame(self.rcontent, bg=hdr_color, cursor='hand2')
            hf.pack(fill='x', padx=0, pady=(4, 0))

            # State: expanded by default for Broad, collapsed for others
            is_broad = 'Broad' in title
            state    = {'expanded': is_broad}

            # Container for rows
            body = tk.Frame(self.rcontent, bg=CARD)
            if is_broad:
                body.pack(fill='x', padx=0)
            # else stays hidden

            arrow_var = tk.StringVar(value='▾' if is_broad else '▸')
            arr_lbl = tk.Label(hf, textvariable=arrow_var, font=('Arial', 9, 'bold'),
                               bg=hdr_color, fg='white', padx=4)
            arr_lbl.pack(side='left', padx=(6, 0), pady=5)
            tk.Label(hf, text=title, font=('Arial', 8, 'bold'),
                     bg=hdr_color, fg='white', padx=4, pady=5).pack(side='left')
            cnt_lbl = tk.Label(hf, text=f"({count})", font=('Arial', 8),
                               bg=hdr_color, fg='#DDDDDD', padx=4)
            cnt_lbl.pack(side='right', padx=6)

            def toggle(b=body, s=state, av=arrow_var):
                if s['expanded']:
                    b.pack_forget()
                    av.set('▸')
                    s['expanded'] = False
                else:
                    b.pack(fill='x', padx=0)
                    av.set('▾')
                    s['expanded'] = True

            for w2 in [hf, arr_lbl, cnt_lbl]:
                w2.bind('<Button-1>', lambda e, t=toggle: t())
            for child in hf.winfo_children():
                child.bind('<Button-1>', lambda e, t=toggle: t())

            # ── Index rows ────────────────────────────────────────────────────
            if not rows:
                tk.Label(body, text="  Data nahi mili", font=('Arial', 8),
                         bg=CARD, fg=SUBTEXT).pack(anchor='w', padx=8, pady=4)
                continue

            # Column headers
            ch = tk.Frame(body, bg=BORDER)
            ch.pack(fill='x')
            tk.Label(ch, text="Index", font=('Arial', 7, 'bold'),
                     bg=BORDER, fg=SUBTEXT, anchor='w', padx=6, pady=3
                     ).pack(side='left', expand=True, fill='x')
            tk.Label(ch, text="Chg%", font=('Arial', 7, 'bold'),
                     bg=BORDER, fg=SUBTEXT, anchor='e', padx=6, pady=3, width=7
                     ).pack(side='right')

            # Sort: gainers first
            sorted_rows = sorted(rows, key=lambda x: x['chg'], reverse=True)

            for i, row in enumerate(sorted_rows):
                name    = row['name']
                chg     = row['chg']
                chg_col = GREEN if chg >= 0 else RED
                row_bg  = CARD if i % 2 == 0 else CARD2

                rf = tk.Frame(body, bg=row_bg, cursor='hand2')
                rf.pack(fill='x')

                # Short symbol
                disp = name
                for pfx in ('NIFTY ', 'NIFTY500 '):
                    if disp.upper().startswith(pfx):
                        disp = disp[len(pfx):]
                        break
                disp = disp.replace(' INDEX','').replace(' Index','').strip()
                if len(disp) > 22: disp = disp[:21] + '…'

                tk.Label(rf, text=disp, font=('Arial', 8),
                         bg=row_bg, fg=TEXT, anchor='w', padx=6, pady=4
                         ).pack(side='left', expand=True, fill='x')
                chg_str = f"{chg:+.2f}%" if chg else "—"
                tk.Label(rf, text=chg_str, font=('Arial', 8, 'bold'),
                         bg=row_bg, fg=chg_col, anchor='e', padx=6, width=7
                         ).pack(side='right')

                # Click → center heatmap for this specific index
                rf.bind('<Button-1>',
                        lambda e, n=name: self._show_index_heatmap(n))
                for child in rf.winfo_children():
                    child.bind('<Button-1>',
                               lambda e, n=name: self._show_index_heatmap(n))
                rf.bind('<Enter>', lambda e, f=rf, bg=row_bg: f.config(bg='#1E1E3A'))
                rf.bind('<Leave>', lambda e, f=rf, bg=row_bg: f.config(bg=bg))

        # Refresh button
        tk.Frame(self.rcontent, bg=BORDER, height=1).pack(fill='x', padx=6, pady=(8,2))
        tk.Button(self.rcontent, text="🔄 Refresh Indices",
                  font=('Arial', 8), bg=BORDER, fg=ACCENT,
                  relief='flat', padx=8, pady=5, cursor='hand2',
                  command=self._render_sectors_default
                  ).pack(fill='x', padx=6, pady=(0,6))

    def _show_index_heatmap(self, index_name):
        """Index tile/row click → stocks ka heatmap center mein"""
        # If _hm_content doesn't exist (stock view open hai), rebuild welcome first
        if not self._hm_content or not self._hm_content.winfo_exists():
            self._welcome()

        # Current tab track karo taaki back button wahan wapas le jaaye
        # Find active tab
        active_tab = 'home'
        for k, (b, _) in self._hm_tabs.items():
            try:
                if b.cget('highlightthickness') == 2:
                    active_tab = k
                    break
            except: pass
        self._nav_stack.append(('tab', active_tab))
        self._current_chartink = None  # Index heatmap mein chartink state clear

        # Switch center panel to loading
        for w in self._hm_content.winfo_children(): w.destroy()
        lf = tk.Frame(self._hm_content, bg=BG)
        lf.pack(fill='both', expand=True)
        tk.Label(lf, text=f"⏳ {index_name} ke stocks load ho rahe hain...",
                 font=('Arial', 13), bg=BG, fg=SUBTEXT).pack(pady=60)

        threading.Thread(
            target=self._fetch_index_stocks,
            args=(index_name,), daemon=True).start()

    def _fetch_index_stocks(self, index_name):
        """Fetch constituents of a specific NSE index and render heatmap"""
        rows = []
        try:
            NSE_SESSION.get("https://www.nseindia.com", timeout=8)
            enc = requests.utils.quote(index_name)
            url = f"https://www.nseindia.com/api/equity-stockIndices?index={enc}"
            r = NSE_SESSION.get(url, timeout=15)
            if r.status_code == 200:
                data = r.json().get('data', [])
                for item in data:
                    sym = (item.get('symbol') or '').strip()
                    if not sym or sym == index_name: continue
                    chg = item.get('pChange', item.get('perChange', 0))
                    ltp = item.get('lastPrice', item.get('ltp', 0))
                    try: chg = float(chg)
                    except: chg = 0.0
                    try: ltp = float(str(ltp).replace(',',''))
                    except: ltp = 0.0
                    rows.append({'symbol': sym, 'ltp': ltp, 'chg': chg})
        except Exception as ex:
            print(f"[IndexStocks] {ex}")

        self.root.after(0, lambda: self._render_index_heatmap(index_name, rows))

    def _render_index_heatmap(self, index_name, rows):
        """Render stock-level heatmap for a specific index in center panel"""
        for w in self._hm_content.winfo_children(): w.destroy()

        if not rows:
            tk.Label(self._hm_content,
                     text=f"❌ {index_name} ke stocks load nahi hue\nRefresh karo",
                     font=('Arial', 12), bg=BG, fg=RED, justify='center').pack(pady=60)
            tk.Button(self._hm_content, text="🔄 Retry",
                      font=('Arial', 10), bg=BORDER, fg=ACCENT,
                      relief='flat', padx=14, pady=6, cursor='hand2',
                      command=lambda: self._show_index_heatmap(index_name)).pack()
            return

        # ── Header ───────────────────────────────────────────────────────────
        hdr = tk.Frame(self._hm_content, bg=CARD)
        hdr.pack(fill='x', padx=6, pady=(6,4))

        # Short display label
        disp_name = index_name
        for pfx in ('NIFTY ', 'NIFTY500 '):
            if disp_name.upper().startswith(pfx):
                disp_name = disp_name[len(pfx):]
                break

        tk.Label(hdr, text=f"📊 {index_name}  ({len(rows)} stocks)",
                 font=('Arial', 12, 'bold'), bg=CARD, fg=ACCENT
                 ).pack(side='left', padx=10)
        tk.Button(hdr, text="◀ Back", font=('Arial', 8),
                  bg=BORDER, fg=TEXT, relief='flat', padx=8, pady=3, cursor='hand2',
                  command=self._go_back
                  ).pack(side='right', padx=4)
        tk.Button(hdr, text="🔄 Refresh", font=('Arial', 8),
                  bg=BORDER, fg=SUBTEXT, relief='flat', padx=8, pady=3, cursor='hand2',
                  command=lambda: self._show_index_heatmap(index_name)
                  ).pack(side='right', padx=4)
        tk.Label(hdr, text="↑ Stock click → Checklist",
                 font=('Arial', 8), bg=CARD, fg=SUBTEXT).pack(side='right', padx=8)

        # ── Scrollable tile area ──────────────────────────────────────────────
        outer = tk.Frame(self._hm_content, bg=BG)
        outer.pack(fill='both', expand=True)
        vsb = ttk.Scrollbar(outer, orient='vertical'); vsb.pack(side='right', fill='y')
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0, yscrollcommand=vsb.set)
        canvas.pack(fill='both', expand=True)
        vsb.config(command=canvas.yview)
        canvas.bind('<MouseWheel>', lambda e: canvas.yview_scroll(-1*(e.delta//120), 'units'))

        tile_frame = tk.Frame(canvas, bg=BG)
        canvas.create_window((0,0), window=tile_frame, anchor='nw', tags='tf')
        tile_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfig('tf', width=e.width))

        def tile_color(chg):
            if   chg >=  3: return '#005000', '#FFFFFF'
            elif chg >=  1: return '#1B5E20', '#FFFFFF'
            elif chg >=  0: return '#2E7D32', '#FFFFFF'
            elif chg >= -1: return '#7B1A1A', '#FFFFFF'
            elif chg >= -3: return '#B71C1C', '#FFFFFF'
            else:           return '#4A0000', '#FFFFFF'

        rows_sorted = sorted(rows, key=lambda x: x['chg'], reverse=True)
        COLS = 6
        for i, row in enumerate(rows_sorted):
            sym  = row['symbol']
            chg  = row['chg']
            ltp  = row['ltp']
            tile_bg, tile_fg = tile_color(chg)

            col   = i % COLS
            r_idx = i // COLS

            tile = tk.Frame(tile_frame, bg=tile_bg, relief='flat', bd=1,
                            highlightbackground='#333355', highlightthickness=1)
            tile.grid(row=r_idx, column=col, padx=3, pady=3, sticky='nsew')
            tile_frame.columnconfigure(col, weight=1, minsize=80)

            tk.Label(tile, text=sym, font=('Arial', 8, 'bold'),
                     bg=tile_bg, fg=tile_fg,
                     wraplength=100, justify='center').pack(pady=(6,1), padx=3)
            if ltp:
                tk.Label(tile, text=f"₹{ltp:,.0f}", font=('Arial', 7),
                         bg=tile_bg, fg=tile_fg).pack()
            chg_str = f"{chg:+.2f}%"
            tk.Label(tile, text=chg_str, font=('Arial', 9, 'bold'),
                     bg=tile_bg, fg=tile_fg).pack(pady=(1,6))

            # Click tile → seedha screener se load karo (search nahi)
            for w in [tile] + tile.winfo_children():
                w.bind('<Button-1>', lambda e, s=sym: self._direct_load(s))
            tile.bind('<Enter>', lambda e, t=tile, bg=tile_bg: t.config(bg='#1E1E3A') or [
                c.config(bg='#1E1E3A') for c in t.winfo_children()])
            tile.bind('<Leave>', lambda e, t=tile, bg=tile_bg: t.config(bg=bg) or [
                c.config(bg=bg) for c in t.winfo_children()])

    def _load_rpanel(self, sym, company_name=''):
        """Load news + docs for given stock symbol into right panel"""
        if not sym: return
        self._rpanel_sym  = sym
        self._rpanel_name = company_name
        # Agar rcontent exist nahi karta toh rpanel rebuild karo
        if not hasattr(self, 'rcontent') or not self.rcontent.winfo_exists():
            self._build_rpanel()
        for w in self.rcontent.winfo_children(): w.destroy()
        tk.Label(self.rcontent, text="⏳ Loading...",
                 font=('Arial', 9), bg=CARD, fg=SUBTEXT).pack(pady=20)
        threading.Thread(
            target=self._fetch_rpanel_data,
            args=(sym, company_name), daemon=True).start()

    def _fetch_rpanel_data(self, sym, company_name):
        """Fetch NSE Announcements (top 5) + Annual Report PDFs"""
        news_items = []
        docs_items = []
        annual_pdf_url = None

        # ── NSE cookie warm-up (mandatory before any NSE API call) ──────────
        try:
            NSE_SESSION.get("https://www.nseindia.com", timeout=8)
            NSE_SESSION.get(
                f"https://www.nseindia.com/get-quote/equity/{sym}", timeout=8)
        except Exception: pass

        # ── Top 5 NSE Corporate Announcements ───────────────────────────────
        # API confirmed: returns list with subject, exchdisstime, attchmntFile
        try:
            ann_url = (f"https://www.nseindia.com/api/corp-info"
                       f"?symbol={sym}&corpType=announcement&market=equities")
            r = NSE_SESSION.get(ann_url, timeout=12)
            if r.status_code == 200:
                raw   = r.json()
                items = raw if isinstance(raw, list) else raw.get('data', [])
                for item in (items or [])[:5]:
                    title = (item.get('subject') or item.get('desc') or '').strip()
                    date  = (item.get('exchdisstime') or item.get('bm_timestamp') or '')[:10]
                    att   = (item.get('attchmntFile') or item.get('attchmntText') or '').strip()
                    # attchmntFile is relative path — prepend nsearchives host
                    if att:
                        link = att if att.startswith('http') \
                            else f"https://nsearchives.nseindia.com{att}"
                    else:
                        link = f"https://www.nseindia.com/get-quote/equity/{sym}#tabcorp-announcements"
                    if title:
                        news_items.append({
                            'title': title[:85],
                            'date':  date,
                            'link':  link,
                            'src':   'NSE'
                        })
        except Exception: pass

        # ── NSE Annual Report PDFs ───────────────────────────────────────────
        # Confirmed JSON: fromYr, toYr, fileName = full https nsearchives URL
        try:
            ar_url = f"https://www.nseindia.com/api/annual-reports?index=equities&symbol={sym}"
            r = NSE_SESSION.get(ar_url, timeout=12)
            if r.status_code == 200:
                raw     = r.json()
                reports = raw.get('data', raw) if isinstance(raw, dict) else raw
                for rep in (reports or [])[:3]:
                    fname  = (rep.get('fileName') or '').strip()
                    from_y = rep.get('fromYr', '')
                    to_y   = rep.get('toYr', '')
                    label  = f"FY {from_y}-{to_y}" if from_y and to_y else 'Annual Report'
                    if fname and fname.startswith('http'):
                        docs_items.append({
                            'title': f"Annual Report {label}",
                            'link':  fname
                        })
                        if not annual_pdf_url:
                            annual_pdf_url = fname
        except Exception: pass

        self.root.after(0, lambda: self._render_rpanel(
            news_items, docs_items, sym, annual_pdf_url, company_name))

    def _render_rpanel(self, news_items, docs_items, sym, annual_pdf_url=None, company_name=''):
        """Render news + annual report PDFs in right panel"""
        for w in self.rcontent.winfo_children(): w.destroy()

        def section_header(txt):
            f = tk.Frame(self.rcontent, bg=CARD)
            f.pack(fill='x', padx=6, pady=(10, 3))
            tk.Label(f, text=txt, font=('Arial', 8, 'bold'),
                     bg=CARD, fg=ACCENT).pack(anchor='w')
            tk.Frame(self.rcontent, bg=BORDER, height=1).pack(fill='x', padx=6)

        def clickable(frame, widgets, link):
            """Make frame + widgets open link on click"""
            for w in widgets:
                w.bind('<Button-1>', lambda e, l=link: webbrowser.open(l))
            frame.bind('<Enter>', lambda e: frame.config(bg='#1E1E3A'))
            frame.bind('<Leave>', lambda e: frame.config(bg=CARD2))

        # ── NEWS SECTION ─────────────────────────────────────────────────────
        section_header("📢 NSE Announcements  (Top 5)")
        if news_items:
            for item in news_items:
                f = tk.Frame(self.rcontent, bg=CARD2, cursor='hand2')
                f.pack(fill='x', padx=6, pady=2)
                hf = tk.Frame(f, bg=CARD2); hf.pack(fill='x', padx=6, pady=(5,0))
                src_lbl = tk.Label(hf, text=item['src'], font=('Arial', 7, 'bold'),
                                   bg=BORDER, fg=SUBTEXT, padx=3)
                src_lbl.pack(side='left')
                dt_lbl = tk.Label(hf, text=item['date'], font=('Arial', 7),
                                  bg=CARD2, fg=SUBTEXT)
                dt_lbl.pack(side='right')
                title_lbl = tk.Label(f, text=item['title'], font=('Arial', 8),
                                     bg=CARD2, fg=TEXT,
                                     wraplength=205, justify='left', anchor='w')
                title_lbl.pack(fill='x', padx=6, pady=(2, 6))
                if item.get('link'):
                    clickable(f, [hf, src_lbl, dt_lbl, title_lbl], item['link'])
        else:
            tk.Label(self.rcontent, text="Announcements load nahi hui",
                     font=('Arial', 8), bg=CARD, fg=SUBTEXT).pack(pady=8)

        # ── ANNUAL REPORTS SECTION ────────────────────────────────────────────
        section_header("📋 Annual Reports  (NSE)")
        if docs_items:
            for item in docs_items:
                f = tk.Frame(self.rcontent, bg=CARD2, cursor='hand2')
                f.pack(fill='x', padx=6, pady=3)
                icon_lbl = tk.Label(f, text="📄", font=('Arial', 11),
                                    bg=CARD2, fg=GREEN)
                icon_lbl.pack(side='left', padx=(8, 4), pady=8)
                title_lbl = tk.Label(f, text=item['title'], font=('Arial', 8, 'bold'),
                                     bg=CARD2, fg=GREEN,
                                     wraplength=170, justify='left', anchor='w')
                title_lbl.pack(side='left', fill='x', expand=True, pady=8)
                open_lbl = tk.Label(f, text="↗", font=('Arial', 10, 'bold'),
                                    bg=CARD2, fg=SUBTEXT)
                open_lbl.pack(side='right', padx=8)
                clickable(f, [icon_lbl, title_lbl, open_lbl], item['link'])
        else:
            tk.Label(self.rcontent, text="Reports load nahi hui",
                     font=('Arial', 8), bg=CARD, fg=SUBTEXT).pack(pady=8)

        # ── QUICK LINKS ───────────────────────────────────────────────────────
        tk.Frame(self.rcontent, bg=BORDER, height=1).pack(fill='x', padx=6, pady=(10,4))

        # NSE Corporate Filings — working URL (not get-quote which gives 404)
        tk.Button(self.rcontent,
                  text="🔗 NSE Corporate Filings",
                  font=('Arial', 8), bg='#1A2A4A', fg=ACCENT,
                  relief='flat', padx=6, pady=6, cursor='hand2',
                  command=lambda: webbrowser.open(
                      f"https://www.nseindia.com/companies-listing/corporate-filings-announcements"
                      f"?symbol={sym}")
                  ).pack(fill='x', padx=6, pady=2)

        # BSE — valid URL targets stock directly via symbol search
        tk.Button(self.rcontent,
                  text="🔗 BSE Announcements",
                  font=('Arial', 8), bg='#2A1A00', fg=YELLOW,
                  relief='flat', padx=6, pady=6, cursor='hand2',
                  command=lambda: webbrowser.open(
                      f"https://www.bseindia.com/corporates/ann.html"
                      f"?scripcd=&company={requests.utils.quote(company_name)}"
                      f"&Submit=Search&Category=&From=&To=")
                  ).pack(fill='x', padx=6, pady=2)

        # TradingView — direct chart for this stock
        tk.Button(self.rcontent,
                  text="📈 TradingView Chart",
                  font=('Arial', 8), bg='#1A2A1A', fg=GREEN,
                  relief='flat', padx=6, pady=6, cursor='hand2',
                  command=lambda: webbrowser.open(
                      f"https://www.tradingview.com/chart/?symbol=NSE%3A{sym}")
                  ).pack(fill='x', padx=6, pady=(2, 10))

    def _open_chartink(self, url, label):
        """Fetch Chartink screener data and show in main panel"""
        # Welcome pe push karo taaki back button se wapas aa sake
        self._nav_stack.append(('welcome',))
        # Right panel reset — stock data hatao, indices dikhao
        self._rpanel_sym = ''; self._rpanel_name = ''
        self._render_sectors_default()
        self._loading(f"Loading {label}...")
        threading.Thread(target=self._do_chartink, args=(url, label), daemon=True).start()

    def _do_chartink(self, url, label):
        rows = fetch_chartink(url)
        self.root.after(0, lambda: self._show_market(rows, label, url))

    def _open_market(self, dtype, label):
        pass  # kept for compatibility

    def _do_market(self, dtype, label):
        pass

    def _show_market(self, rows, label, source_url=''):
        # Chartink list state save karo — back button ke liye
        self._current_chartink = {'rows': rows, 'label': label, 'url': source_url}

        for w in self.main.winfo_children(): w.destroy()

        # ── Toolbar ───────────────────────────────────────────────────────────
        tb = tk.Frame(self.main, bg=CARD, pady=0)
        tb.pack(fill='x')
        tk.Button(tb, text="◀ Back", font=('Arial', 9, 'bold'),
                  bg=BORDER, fg=TEXT, relief='flat', padx=10, pady=8,
                  cursor='hand2', command=self._go_back
                  ).pack(side='left', padx=(8,2), pady=6)
        tk.Button(tb, text="🔄", font=('Arial', 10),
                  bg=BORDER, fg=ACCENT, relief='flat', padx=8, pady=8,
                  cursor='hand2',
                  command=lambda: self._open_chartink(source_url, label)
                  ).pack(side='left', padx=2, pady=6)
        tk.Label(tb, text=f"  {label}",
                 font=('Arial', 11, 'bold'), bg=CARD, fg=TEXT
                 ).pack(side='left', padx=6)
        tk.Label(tb, text=f"  {len(rows)} stocks  •  Chartink",
                 font=('Arial', 9), bg=CARD, fg=SUBTEXT
                 ).pack(side='left')
        tk.Button(tb, text="✕ Close", font=('Arial', 9),
                  bg=BORDER, fg=SUBTEXT, relief='flat', padx=10, pady=8,
                  cursor='hand2', command=self._welcome
                  ).pack(side='right', padx=8, pady=6)
        tk.Button(tb, text="🌐 Open", font=('Arial', 9),
                  bg='#1A2A4A', fg=ACCENT, relief='flat', padx=10, pady=8,
                  cursor='hand2', command=lambda: webbrowser.open(source_url)
                  ).pack(side='right', padx=2, pady=6)
        tk.Frame(self.main, bg=BORDER, height=1).pack(fill='x')

        if not rows:
            tk.Label(self.main,
                     text="❌ Data load nahi hua\n\nChartink login check karo ya Refresh karo",
                     font=('Arial', 12), bg=BG, fg=RED, justify='center'
                     ).pack(pady=60)
            return

        # ── Horizontal + Vertical scrollable table ────────────────────────────
        outer = tk.Frame(self.main, bg=BG)
        outer.pack(fill='both', expand=True)

        # Vertical scrollbar
        vsb = ttk.Scrollbar(outer, orient='vertical')
        vsb.pack(side='right', fill='y')

        # Horizontal scrollbar
        hsb = ttk.Scrollbar(outer, orient='horizontal')
        hsb.pack(side='bottom', fill='x')

        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0,
                           yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        canvas.pack(fill='both', expand=True)
        vsb.config(command=canvas.yview)
        hsb.config(command=canvas.xview)

        con = tk.Frame(canvas, bg=BG)
        canvas.create_window((0,0), window=con, anchor='nw', tags='con')
        con.bind('<Configure>',
                 lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<MouseWheel>',
                    lambda e: canvas.yview_scroll(-1*(e.delta//120), 'units'))

        # ── Column headers ────────────────────────────────────────────────────
        cols = [
            ('#',        4,  'center', SUBTEXT),
            ('Symbol',   13, 'w',      ACCENT),
            ('Company',  30, 'w',      TEXT),
            ('LTP ₹',    10, 'e',      TEXT),
            ('Chg %',    9,  'e',      TEXT),
            ('Volume',   11, 'e',      TEXT),
        ]
        hdr_f = tk.Frame(con, bg='#0A0E1E'); hdr_f.pack(fill='x', pady=(0,0))
        # Left border spacer
        tk.Frame(hdr_f, bg='#0A0E1E', width=3).pack(side='left', fill='y')
        for cname, cw, anchor, _ in cols:
            tk.Label(hdr_f, text=cname, font=('Arial', 8, 'bold'),
                     bg='#0A0E1E', fg=SUBTEXT,
                     width=cw, anchor=anchor, padx=8, pady=9
                     ).pack(side='left')
        tk.Frame(con, bg=BORDER, height=1).pack(fill='x')

        # ── Stock rows ────────────────────────────────────────────────────────
        for idx, row in enumerate(rows):
            sym     = row.get('symbol', '')
            company = row.get('company', sym)
            ltp     = row.get('ltp', 0)
            chg     = row.get('change_pct', 0)
            vol     = row.get('volume', 0)

            try: chg_f = float(chg)
            except: chg_f = 0
            chg_col = GREEN if chg_f >= 0 else RED
            row_bg  = CARD if idx % 2 == 0 else CARD2

            rf = tk.Frame(con, bg=row_bg, cursor='hand2')
            rf.pack(fill='x', padx=0, pady=0)

            # Colored left accent bar
            tk.Frame(rf, bg=chg_col if abs(chg_f)>0.5 else BORDER, width=3
                     ).pack(side='left', fill='y')

            # Sr no
            tk.Label(rf, text=str(idx+1), font=('Arial', 8),
                     bg=row_bg, fg=SUBTEXT, width=4, anchor='center', padx=4, pady=9
                     ).pack(side='left')

            # Symbol
            sym_lbl = tk.Label(rf, text=sym, font=('Arial', 9, 'bold'),
                               bg=row_bg, fg=ACCENT, width=13, anchor='w', padx=6)
            sym_lbl.pack(side='left')

            # Company
            co_short = company[:30]+'…' if len(company) > 30 else company
            tk.Label(rf, text=co_short, font=('Arial', 9),
                     bg=row_bg, fg=TEXT, width=30, anchor='w', padx=6
                     ).pack(side='left')

            # LTP
            ltp_str = f"₹{float(ltp):,.2f}" if ltp else "—"
            tk.Label(rf, text=ltp_str, font=('Arial', 9, 'bold'),
                     bg=row_bg, fg=TEXT, width=10, anchor='e', padx=8
                     ).pack(side='left')

            # Change %
            chg_str = f"{chg_f:+.2f}%" if chg else "—"
            tk.Label(rf, text=chg_str, font=('Arial', 9, 'bold'),
                     bg=row_bg, fg=chg_col, width=9, anchor='e', padx=6
                     ).pack(side='left')

            # Volume
            try:
                v = float(vol)
                vol_str = f"{v/1e7:.2f}Cr" if v>=1e7 else f"{v/1e5:.1f}L" if v>=1e5 else f"{int(v):,}"
            except: vol_str = str(vol) if vol else "—"
            tk.Label(rf, text=vol_str, font=('Arial', 9),
                     bg=row_bg, fg=SUBTEXT, width=11, anchor='e', padx=8
                     ).pack(side='left')

            # Hover effect
            def _enter(e, f=rf, bg=row_bg):
                f.config(bg='#1C2248')
                for c in f.winfo_children():
                    try: c.config(bg='#1C2248')
                    except: pass
            def _leave(e, f=rf, bg=row_bg):
                f.config(bg=bg)
                for c in f.winfo_children():
                    try: c.config(bg=bg)
                    except: pass
            rf.bind('<Enter>', _enter)
            rf.bind('<Leave>', _leave)

            # ✅ Click → seedha checklist (direct load, not search)
            def _on_click(e, s=sym):
                if not s: return
                self._direct_load(s)
            rf.bind('<Button-1>', _on_click)
            for child in rf.winfo_children():
                child.bind('<Button-1>', _on_click)

            # Divider
            tk.Frame(con, bg=BORDER, height=1).pack(fill='x')




    # ── SEARCH SUGGESTION DROPDOWN ────────────────────────────────────────────
    def _on_key_suggest(self, event):
        # Ignore navigation keys
        if event.keysym in ('Return', 'Escape', 'Up', 'Down', 'Tab'):
            if event.keysym == 'Escape': self._close_dd()
            return
        q = self.q.get().strip()
        if len(q) >= 2:
            threading.Thread(target=self._fetch_suggest, args=(q,), daemon=True).start()
        else:
            self._close_dd()

    def _fetch_suggest(self, q):
        try:
            res = search_stock(q)
            self.root.after(0, lambda: self._show_dd(res))
        except: pass

    def _show_dd(self, results):
        self._close_dd()
        if not results: return
        # Position dropdown directly below the search entry
        try:
            ex = self._entry.winfo_rootx()
            ey = self._entry.winfo_rooty() + self._entry.winfo_height() + 2
            ew = self._entry.winfo_width()
        except: return

        n = min(len(results), 10)
        win = tk.Toplevel(self.root)
        win.wm_overrideredirect(True)
        win.wm_geometry(f"{ew}x{n*36}+{ex}+{ey}")
        win.configure(bg=BORDER)
        win.lift()
        self._dd_win = win

        # Scrollable list inside dropdown
        c = tk.Canvas(win, bg=CARD2, highlightthickness=0)
        sb = ttk.Scrollbar(win, orient='vertical', command=c.yview)
        frm = tk.Frame(c, bg=CARD2)
        frm.bind('<Configure>', lambda e: c.configure(scrollregion=c.bbox('all')))
        c.create_window((0, 0), window=frm, anchor='nw', tags='f')
        c.bind('<Configure>', lambda e: c.itemconfig('f', width=e.width))
        c.configure(yscrollcommand=sb.set)
        if n > 8: sb.pack(side='right', fill='y')
        c.pack(fill='both', expand=True)

        for r in results[:15]:
            name = r.get('name', '') or r.get('company', '')
            url  = r.get('url', '')
            fr2  = tk.Frame(frm, bg=CARD2)
            fr2.pack(fill='x')
            btn = tk.Button(fr2, text=f"  🔎  {name}", font=('Arial', 9),
                            bg=CARD2, fg=TEXT, relief='flat', anchor='w',
                            padx=6, pady=7, cursor='hand2',
                            command=lambda u=url, n=name: self._dd_pick(u, n))
            btn.pack(fill='x')
            btn.bind('<Enter>', lambda e, b=btn: b.config(bg=BORDER))
            btn.bind('<Leave>', lambda e, b=btn: b.config(bg=CARD2))
            tk.Frame(frm, bg=BORDER, height=1).pack(fill='x')

        # Close dropdown when clicking anywhere else
        win.bind('<FocusOut>', lambda e: self.root.after(150, self._close_dd))

    def _dd_pick(self, url, name):
        self._close_dd()
        self.q.set('')
        self._load(url, name)

    def _close_dd(self):
        if self._dd_win:
            try: self._dd_win.destroy()
            except: pass
            self._dd_win = None

    def _go_back(self):
        """Ek step peeche jao — nav stack se"""
        if not self._nav_stack:
            self._welcome()
            self._build_rpanel()
            return
        prev = self._nav_stack.pop()
        kind = prev[0]
        if kind == 'welcome':
            self._welcome()
            self._build_rpanel()
        elif kind == 'chartink_list':
            # Chartink list pe wapas
            _, rows, label, url = prev
            self._current_chartink = {'rows': rows, 'label': label, 'url': url}
            self._show_market(rows, label, url)
        elif kind == 'tab':
            self._welcome()
            self._build_rpanel()
            self._show_tab(prev[1])
        elif kind == 'index_heatmap':
            # Index heatmap pe wapas — without pushing to stack again
            index_name = prev[1]
            if not self._hm_content or not self._hm_content.winfo_exists():
                self._welcome()
            for w in self._hm_content.winfo_children(): w.destroy()
            lf = tk.Frame(self._hm_content, bg=BG)
            lf.pack(fill='both', expand=True)
            tk.Label(lf, text=f"⏳ {index_name} ke stocks load ho rahe hain...",
                     font=('Arial', 13), bg=BG, fg=SUBTEXT).pack(pady=60)
            threading.Thread(
                target=self._fetch_index_stocks,
                args=(index_name,), daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    # WATCHLIST SCREEN
    # ══════════════════════════════════════════════════════════════════════════

    def _show_watchlist(self):
        """Show watchlist in main panel"""
        self._nav_stack.append(('welcome',))
        self._current_chartink = None
        for w in self.main.winfo_children(): w.destroy()
        self._hm_tabs = {}; self._hm_content = None
        # Right panel reset — stock data hatao, indices dikhao
        self._rpanel_sym = ''; self._rpanel_name = ''
        self._render_sectors_default()

        # Header
        hdr = tk.Frame(self.main, bg=CARD, pady=12); hdr.pack(fill='x')
        tk.Label(hdr, text="⭐  My Watchlist",
                 font=('Arial', 16, 'bold'), bg=CARD, fg=YELLOW).pack(side='left', padx=14)
        tk.Button(hdr, text="◀ Back", font=('Arial', 9, 'bold'),
                  bg=BORDER, fg=TEXT, relief='flat', padx=10, pady=6,
                  cursor='hand2', command=self._go_back).pack(side='right', padx=10)
        tk.Button(hdr, text="🗑 Clear All", font=('Arial', 9),
                  bg='#2A0A0A', fg=RED, relief='flat', padx=10, pady=6,
                  cursor='hand2', command=self._clear_watchlist).pack(side='right', padx=4)

        # Scrollable content
        outer = tk.Frame(self.main, bg=BG); outer.pack(fill='both', expand=True)
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        sb     = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        con    = tk.Frame(canvas, bg=BG)
        con.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0,0), window=con, anchor='nw', tags='con')
        canvas.bind('<Configure>', lambda e: canvas.itemconfig('con', width=e.width))
        canvas.bind('<MouseWheel>', lambda e: canvas.yview_scroll(-1*(e.delta//120), 'units'))
        sb.pack(side='right', fill='y'); canvas.pack(fill='both', expand=True)

        wl = APP_DATA.get('watchlist', {})
        if not wl:
            tk.Label(con, text="Watchlist khaali hai!\nKisi bhi stock ke detail page pe ⭐ click karo.",
                     font=('Arial', 13), bg=BG, fg=SUBTEXT, justify='center').pack(pady=60)
            return

        # Column headers
        hrow = tk.Frame(con, bg=BORDER); hrow.pack(fill='x', padx=8, pady=(8,2))
        for txt, w2 in [('Symbol',10),('Company',24),('Sector',18),('Added',12),('Entry ₹',10),('Live ₹',10),('Chg%',8),('Sparkline',16),('',6)]:
            tk.Label(hrow, text=txt, font=('Arial', 8, 'bold'), bg=BORDER, fg=SUBTEXT,
                     width=w2, anchor='w').pack(side='left', padx=4, pady=4)

        for idx, (sym, info) in enumerate(wl.items()):
            row_bg = CARD if idx%2==0 else CARD2
            rf = tk.Frame(con, bg=row_bg); rf.pack(fill='x', padx=8, pady=1)

            # Symbol (clickable)
            sym_btn = tk.Button(rf, text=sym, font=('Arial', 10, 'bold'),
                                bg=row_bg, fg=ACCENT, relief='flat', cursor='hand2', width=10, anchor='w',
                                command=lambda s=sym: self._direct_load(s))
            sym_btn.pack(side='left', padx=4, pady=6)

            tk.Label(rf, text=(info.get('name','') or '')[:22], font=('Arial', 9),
                     bg=row_bg, fg=TEXT, width=24, anchor='w').pack(side='left', padx=4)
            tk.Label(rf, text=(info.get('sector','') or '')[:16], font=('Arial', 8),
                     bg=row_bg, fg=SUBTEXT, width=18, anchor='w').pack(side='left', padx=4)
            tk.Label(rf, text=info.get('added',''), font=('Arial', 8),
                     bg=row_bg, fg=SUBTEXT, width=12, anchor='w').pack(side='left', padx=4)
            ep = info.get('price')
            tk.Label(rf, text=f"₹{ep:.0f}" if ep else "—", font=('Arial', 9),
                     bg=row_bg, fg=TEXT, width=10, anchor='w').pack(side='left', padx=4)

            # Live price + change placeholders — filled by thread
            live_lbl = tk.Label(rf, text="…", font=('Arial', 9, 'bold'),
                                bg=row_bg, fg=SUBTEXT, width=10, anchor='w')
            live_lbl.pack(side='left', padx=4)
            chg_lbl  = tk.Label(rf, text="…", font=('Arial', 9, 'bold'),
                                bg=row_bg, fg=SUBTEXT, width=8, anchor='w')
            chg_lbl.pack(side='left', padx=4)

            # Sparkline canvas
            spark_c = tk.Canvas(rf, bg=row_bg, width=120, height=32, highlightthickness=0)
            spark_c.pack(side='left', padx=4, pady=4)

            # Remove button
            def _remove(s=sym):
                APP_DATA.get('watchlist', {}).pop(s, None)
                _save_data(APP_DATA)
                # Update watchlist button count
                try: self._wl_btn.config(text=f"⭐  My Watchlist  ({len(APP_DATA.get('watchlist',{}))})")
                except: pass
                self._show_watchlist()
            tk.Button(rf, text='✕', font=('Arial', 9), bg=row_bg, fg=RED,
                      relief='flat', cursor='hand2', command=_remove, width=4
                      ).pack(side='right', padx=6)

            # Fetch live + sparkline in background
            threading.Thread(target=self._fetch_wl_row,
                             args=(sym, ep, live_lbl, chg_lbl, spark_c, row_bg),
                             daemon=True).start()

    def _fetch_wl_row(self, sym, entry_price, live_lbl, chg_lbl, spark_c, row_bg):
        """Background fetch for watchlist row: live price + sparkline"""
        try:
            nse = fetch_nse_live(sym)
            ltp = nse.get('ltp')
            chg = nse.get('change_pct')
            if ltp:
                chg_col = GREEN if (chg or 0) >= 0 else RED
                chg_str = f"{chg:+.2f}%" if chg is not None else "—"
                self.root.after(0, lambda: live_lbl.config(text=f"₹{ltp:.1f}", fg=chg_col))
                self.root.after(0, lambda: chg_lbl.config(text=chg_str, fg=chg_col))
        except: pass
        try:
            hist = yf.download(f"{sym}.NS", period="30d", interval="1d",
                               auto_adjust=True, progress=False)
            if hist is not None and not hist.empty:
                if hasattr(hist.columns, 'levels'):
                    hist.columns = hist.columns.get_level_values(0)
                closes = hist['Close'].values.astype(float).tolist()
                self.root.after(0, lambda c=closes: self._draw_sparkline(spark_c, c, row_bg))
        except: pass

    def _draw_sparkline(self, canvas, prices, bg):
        """Draw mini sparkline on canvas"""
        try:
            canvas.delete('all')
            w, h = 120, 32
            pad  = 4
            if len(prices) < 2: return
            mn, mx = min(prices), max(prices)
            rng = mx - mn if mx != mn else 1
            def yx(i, p):
                x = pad + (w - 2*pad) * i / (len(prices)-1)
                y = h - pad - (p - mn) / rng * (h - 2*pad)
                return x, y
            pts = [yx(i, p) for i, p in enumerate(prices)]
            col = GREEN if prices[-1] >= prices[0] else RED
            for i in range(len(pts)-1):
                canvas.create_line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1],
                                   fill=col, width=1.5, smooth=True)
            # Last dot
            lx, ly = pts[-1]
            canvas.create_oval(lx-2, ly-2, lx+2, ly+2, fill=col, outline='')
        except: pass

    def _clear_watchlist(self):
        APP_DATA['watchlist'] = {}
        _save_data(APP_DATA)
        try: self._wl_btn.config(text="⭐  My Watchlist  (0)")
        except: pass
        self._show_watchlist()

    # ══════════════════════════════════════════════════════════════════════════
    # ETF SECTION — NSE All ETFs + ETF Screener
    # ══════════════════════════════════════════════════════════════════════════

    def _show_etf_section(self):
        """Main ETF section — left: all ETFs list, right panel: ETF screener"""
        self._nav_stack.append(('welcome',))
        self._current_chartink = None

        for w in self.main.winfo_children(): w.destroy()
        self._hm_tabs = {}; self._hm_content = None
        # Right panel reset — stock data hatao, indices dikhao
        self._rpanel_sym = ''; self._rpanel_name = ''
        self._render_sectors_default()

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self.main, bg=CARD, pady=10); hdr.pack(fill='x')
        tk.Label(hdr, text="📦  NSE ETF Explorer",
                 font=('Arial', 15, 'bold'), bg=CARD, fg='#4FC3F7').pack(side='left', padx=14)
        tk.Button(hdr, text="🔄 Refresh", font=('Arial', 9),
                  bg=BORDER, fg=ACCENT, relief='flat', padx=10, pady=6,
                  cursor='hand2', command=self._show_etf_section).pack(side='right', padx=10)
        tk.Button(hdr, text="◀ Back", font=('Arial', 9, 'bold'),
                  bg=BORDER, fg=TEXT, relief='flat', padx=10, pady=6,
                  cursor='hand2', command=self._go_back).pack(side='right', padx=4)
        tk.Frame(self.main, bg='#4FC3F7', height=2).pack(fill='x')

        # ── Body — two columns: ETF List (left) + ETF Screener (right) ────────
        body = tk.Frame(self.main, bg=BG)
        body.pack(fill='both', expand=True)

        # Left — All ETFs list (70% width)
        left_frame = tk.Frame(body, bg=BG)
        left_frame.pack(side='left', fill='both', expand=True)

        # Right — ETF Screener (30% width)
        right_frame = tk.Frame(body, bg=CARD, width=280)
        right_frame.pack(side='right', fill='y', padx=(4,0))
        right_frame.pack_propagate(False)

        # ── Left: ETF list section ────────────────────────────────────────────
        lhdr = tk.Frame(left_frame, bg='#0D1A30', pady=6)
        lhdr.pack(fill='x')
        tk.Label(lhdr, text="  📋 All NSE ETFs  —  % High to Low",
                 font=('Arial', 10, 'bold'), bg='#0D1A30', fg='#4FC3F7').pack(side='left', padx=6)
        self._etf_count_lbl = tk.Label(lhdr, text="Loading...",
                                        font=('Arial', 9), bg='#0D1A30', fg=SUBTEXT)
        self._etf_count_lbl.pack(side='right', padx=10)

        # Column headers
        col_hdr = tk.Frame(left_frame, bg='#0A0E1E')
        col_hdr.pack(fill='x')
        for txt, w2, anch in [
            ('#', 4, 'center'), ('Symbol', 13, 'w'), ('ETF Name', 30, 'w'),
            ('Price ₹', 10, 'e'), ('Chg ₹', 9, 'e'), ('Chg %', 8, 'e'), ('Volume', 11, 'e'),
        ]:
            tk.Label(col_hdr, text=txt, font=('Arial', 8, 'bold'),
                     bg='#0A0E1E', fg=SUBTEXT,
                     width=w2, anchor=anch, padx=8, pady=8).pack(side='left')
        tk.Frame(left_frame, bg=BORDER, height=1).pack(fill='x')

        # Scrollable ETF rows container
        outer = tk.Frame(left_frame, bg=BG); outer.pack(fill='both', expand=True)
        vsb = ttk.Scrollbar(outer, orient='vertical'); vsb.pack(side='right', fill='y')
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0, yscrollcommand=vsb.set)
        canvas.pack(fill='both', expand=True)
        vsb.config(command=canvas.yview)
        canvas.bind('<MouseWheel>', lambda e: canvas.yview_scroll(-1*(e.delta//120), 'units'))
        etf_con = tk.Frame(canvas, bg=BG)
        etf_con.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0,0), window=etf_con, anchor='nw', tags='etfc')
        canvas.bind('<Configure>', lambda e: canvas.itemconfig('etfc', width=e.width))

        # Loading label
        load_lbl = tk.Label(etf_con, text="⏳ ETFs load ho rahi hain...",
                            font=('Arial', 12), bg=BG, fg=SUBTEXT, pady=40)
        load_lbl.pack()

        # ── Right: ETF Screener ───────────────────────────────────────────────
        self._build_etf_screener(right_frame)

        # Fetch ETFs in background
        threading.Thread(
            target=self._fetch_etf_list_data,
            args=(etf_con, canvas),
            daemon=True).start()

    def _fetch_etf_list_data(self, container, canvas):
        etfs = fetch_nse_etf_list()
        # Sort by % change high to low
        etfs.sort(key=lambda x: x['chg'], reverse=True)
        self.root.after(0, lambda: self._render_etf_list(etfs, container, canvas))

    def _render_etf_list(self, etfs, container, canvas):
        for w in container.winfo_children(): w.destroy()

        try: self._etf_count_lbl.config(text=f"{len(etfs)} ETFs")
        except: pass

        if not etfs:
            err = tk.Frame(container, bg=BG); err.pack(pady=60)
            tk.Label(err, text="❌ ETF data load nahi hua",
                     font=('Arial', 12, 'bold'), bg=BG, fg=RED).pack()
            tk.Label(err, text="NSE session warm-up fail hua.\nRefresh karo.",
                     font=('Arial', 9), bg=BG, fg=SUBTEXT, justify='center').pack(pady=4)
            tk.Button(err, text="🔄 Retry", font=('Arial', 9, 'bold'),
                      bg=BORDER, fg=ACCENT, relief='flat', padx=14, pady=6,
                      cursor='hand2', command=self._show_etf_section).pack(pady=8)
            return

        def _fv(v):
            if not v or v == 0: return '—'
            try:
                f = float(v)
                if f >= 1e7: return f'{f/1e7:.1f}Cr'
                if f >= 1e5: return f'{f/1e5:.1f}L'
                return f'{int(f):,}'
            except: return '—'

        for idx, etf in enumerate(etfs):
            sym  = etf.get('symbol', '')
            name = etf.get('name', sym)
            ltp  = etf.get('ltp', 0)
            prev = etf.get('_prev', 0)   # yesterday's close stored from NSE
            vol  = etf.get('vol', 0)

            # ── Calculate price change (₹) and % change correctly ─────────────
            # NSE 'chg' field = price change in ₹ (e.g. +21)
            # We need both:
            #   price_chg = ltp - prev_close  (₹ amount)
            #   pct_chg   = (ltp - prev_close) / prev_close * 100  (%)
            nse_chg = etf.get('chg', 0)   # this is ₹ change from NSE

            if prev > 0 and ltp > 0:
                price_chg = round(ltp - prev, 2)
                pct_chg   = round((ltp - prev) / prev * 100, 2)
            elif prev == 0 and ltp > 0 and abs(nse_chg) < ltp * 0.5:
                # nse_chg looks like ₹ change (not %)
                price_chg = nse_chg
                pct_chg   = round(nse_chg / (ltp - nse_chg) * 100, 2) if (ltp - nse_chg) > 0 else 0
            else:
                price_chg = 0
                pct_chg   = 0

            chg_col = GREEN if pct_chg >= 0 else RED
            row_bg  = CARD if idx % 2 == 0 else CARD2

            rf = tk.Frame(container, bg=row_bg, cursor='hand2'); rf.pack(fill='x')
            tk.Frame(rf, bg=chg_col if abs(pct_chg) > 0.05 else BORDER,
                     width=3).pack(side='left', fill='y')

            def _c(txt, w2, anch, fg=TEXT, bold=False, _rf=rf, _bg=row_bg):
                tk.Label(_rf, text=str(txt),
                         font=('Arial', 9, 'bold') if bold else ('Arial', 9),
                         bg=_bg, fg=fg, width=w2, anchor=anch,
                         padx=5, pady=7).pack(side='left')

            _c(idx + 1,                                       4,  'center', SUBTEXT)
            _c(sym,                                          13,  'w',      '#4FC3F7', bold=True)
            short = (name[:30] + '…') if len(name) > 30 else name
            _c(short,                                        30,  'w',      TEXT)
            _c(f'₹{ltp:,.2f}'      if ltp       else '—',  10,  'e',      TEXT,    bold=True)
            _c(f'{price_chg:+.2f}' if price_chg else '—',   9,  'e',      chg_col, bold=True)
            _c(f'{pct_chg:+.2f}%'  if pct_chg  else '—',   8,  'e',      chg_col, bold=True)
            _c(_fv(vol),                                     11,  'e',      SUBTEXT)

            # Hover
            def _enter(e, f=rf, bg=row_bg):
                f.config(bg='#1C2248')
                for c in f.winfo_children():
                    try: c.config(bg='#1C2248')
                    except: pass
            def _leave(e, f=rf, bg=row_bg):
                f.config(bg=bg)
                for c in f.winfo_children():
                    try: c.config(bg=bg)
                    except: pass
            rf.bind('<Enter>', _enter); rf.bind('<Leave>', _leave)

            def _click(e, s=sym, n=name, p=ltp, c=pct_chg, v=vol):
                self._show_etf_rpanel(s, n, p, c, v)
            rf.bind('<Button-1>', _click)
            for child in rf.winfo_children():
                child.bind('<Button-1>', _click)

            tk.Frame(container, bg=BORDER, height=1).pack(fill='x')

        canvas.configure(scrollregion=canvas.bbox('all'))

    def _build_etf_screener(self, parent):
        """Right panel — ETF Screener with smart filters"""
        # Header
        sh = tk.Frame(parent, bg='#0D2030', pady=8)
        sh.pack(fill='x')
        tk.Label(sh, text="🔍  ETF Screener",
                 font=('Arial', 10, 'bold'), bg='#0D2030', fg='#4FC3F7').pack(side='left', padx=8)
        tk.Button(sh, text="🔄", font=('Arial', 9),
                  bg='#0D2030', fg=ACCENT, relief='flat', padx=6, pady=2,
                  cursor='hand2',
                  command=lambda: self._run_etf_screener(screener_con)
                  ).pack(side='right', padx=6)
        tk.Frame(parent, bg='#4FC3F7', height=1).pack(fill='x')

        # Screener criteria info
        criteria_f = tk.Frame(parent, bg=CARD2, pady=8)
        criteria_f.pack(fill='x', padx=6, pady=4)
        tk.Label(criteria_f, text="Screener Criteria:",
                 font=('Arial', 8, 'bold'), bg=CARD2, fg=SUBTEXT).pack(anchor='w', padx=8)
        criteria_items = [
            "✅ Price > ₹0 (valid ETF)",
            "✅ Volume > 10,000 (liquid)",
            "✅ 1D Change > -5% (not crashing)",
            "📊 Sorted: % High → Low",
        ]
        for c in criteria_items:
            tk.Label(criteria_f, text=f"  {c}", font=('Arial', 8),
                     bg=CARD2, fg=TEXT).pack(anchor='w', padx=8)

        # Run screener button
        tk.Button(parent, text="▶  Run ETF Screener",
                  font=('Arial', 10, 'bold'), bg='#0D3A5A', fg='#4FC3F7',
                  relief='flat', padx=10, pady=10, cursor='hand2',
                  command=lambda: self._run_etf_screener(screener_con)
                  ).pack(fill='x', padx=6, pady=6)

        tk.Frame(parent, bg=BORDER, height=1).pack(fill='x', padx=6)
        self._etf_screener_count = tk.Label(parent, text="Click ▶ to run screener",
                                             font=('Arial', 8, 'italic'),
                                             bg=CARD, fg=SUBTEXT)
        self._etf_screener_count.pack(anchor='w', padx=10, pady=4)

        # Scrollable screener results
        scr_outer = tk.Frame(parent, bg=CARD); scr_outer.pack(fill='both', expand=True)
        scr_vsb = ttk.Scrollbar(scr_outer, orient='vertical'); scr_vsb.pack(side='right', fill='y')
        scr_canvas = tk.Canvas(scr_outer, bg=CARD, highlightthickness=0, yscrollcommand=scr_vsb.set)
        scr_canvas.pack(fill='both', expand=True)
        scr_vsb.config(command=scr_canvas.yview)
        scr_canvas.bind('<MouseWheel>', lambda e: scr_canvas.yview_scroll(-1*(e.delta//120), 'units'))
        screener_con = tk.Frame(scr_canvas, bg=CARD)
        screener_con.bind('<Configure>', lambda e: scr_canvas.configure(scrollregion=scr_canvas.bbox('all')))
        scr_canvas.create_window((0,0), window=screener_con, anchor='nw', tags='scc')
        scr_canvas.bind('<Configure>', lambda e: scr_canvas.itemconfig('scc', width=e.width))

        tk.Label(screener_con,
                 text="▶ Run the screener\nto see filtered ETFs",
                 font=('Arial', 9), bg=CARD, fg=SUBTEXT,
                 justify='center').pack(pady=30)

    def _run_etf_screener(self, container):
        for w in container.winfo_children(): w.destroy()
        tk.Label(container, text="⏳ Screening ETFs...",
                 font=('Arial', 9), bg=CARD, fg=SUBTEXT, pady=20).pack()
        try:
            self._etf_screener_count.config(text="Screening...")
        except: pass
        threading.Thread(
            target=self._fetch_etf_screener_data,
            args=(container,), daemon=True).start()

    def _fetch_etf_screener_data(self, container):
        results = fetch_nse_etf_screener()
        self.root.after(0, lambda: self._render_etf_screener(results, container))

    def _render_etf_screener(self, results, container):
        for w in container.winfo_children(): w.destroy()
        try:
            self._etf_screener_count.config(text=f"{len(results)} ETFs passed all filters")
        except: pass

        if not results:
            tk.Label(container, text="❌ Koi ETF\nfilters pass nahi kiya",
                     font=('Arial', 9), bg=CARD, fg=RED,
                     justify='center', pady=20).pack()
            return

        for idx, etf in enumerate(results):
            sym  = etf['symbol']
            name = etf['name']
            ltp  = etf.get('ltp', 0)
            prev = etf.get('_prev', 0)
            vol  = etf.get('vol', 0)

            # Compute correct % change
            if ltp > 0 and prev > 0:
                pct_chg = round((ltp - prev) / prev * 100, 2)
            else:
                pct_chg = etf.get('chg', 0)  # fallback

            chg_col = GREEN if pct_chg >= 0 else RED
            row_bg  = CARD2 if idx % 2 == 0 else CARD

            rf = tk.Frame(container, bg=row_bg, cursor='hand2', pady=4)
            rf.pack(fill='x', padx=2, pady=1)

            rank_col = '#FFD700' if idx < 3 else SUBTEXT
            tk.Label(rf, text=f"#{idx+1}", font=('Arial', 7, 'bold'),
                     bg=row_bg, fg=rank_col, width=4, anchor='center'
                     ).pack(side='left', padx=(4,0))

            info_f = tk.Frame(rf, bg=row_bg); info_f.pack(side='left', fill='x', expand=True, padx=4)

            top_f = tk.Frame(info_f, bg=row_bg); top_f.pack(fill='x')
            tk.Label(top_f, text=sym, font=('Arial', 9, 'bold'),
                     bg=row_bg, fg='#4FC3F7').pack(side='left')
            tk.Label(top_f, text=f"{pct_chg:+.2f}%", font=('Arial', 9, 'bold'),
                     bg=row_bg, fg=chg_col).pack(side='right', padx=4)

            bot_f = tk.Frame(info_f, bg=row_bg); bot_f.pack(fill='x')
            short_name = name[:22]+'…' if len(name)>22 else name
            tk.Label(bot_f, text=short_name, font=('Arial', 7),
                     bg=row_bg, fg=SUBTEXT).pack(side='left')
            tk.Label(bot_f, text=f"₹{ltp:,.2f}" if ltp else "—",
                     font=('Arial', 8, 'bold'), bg=row_bg, fg=TEXT
                     ).pack(side='right', padx=4)

            def _click_scr(e, s=sym, n=name, p=ltp, c=pct_chg, v=vol):
                self._show_etf_rpanel(s, n, p, c, v)
            rf.bind('<Button-1>', _click_scr)
            for child in rf.winfo_children():
                child.bind('<Button-1>', _click_scr)
            rf.bind('<Enter>', lambda e, f=rf, bg=row_bg: [f.config(bg='#1C2248')] + [c.config(bg='#1C2248') for c in f.winfo_children() if hasattr(c, 'winfo_children')])
            rf.bind('<Leave>', lambda e, f=rf, bg=row_bg: [f.config(bg=bg)] + [c.config(bg=bg) for c in f.winfo_children() if hasattr(c, 'winfo_children')])

            tk.Frame(container, bg=BORDER, height=1).pack(fill='x', padx=4)



    def _show_etf_rpanel(self, sym, name, ltp, chg, vol):
        """Show ETF info in right panel when ETF row is clicked"""
        # Rebuild rpanel with ETF-specific info
        for w in self.rpanel.winfo_children(): w.destroy()

        # Header
        hrow = tk.Frame(self.rpanel, bg=CARD); hrow.pack(fill='x', pady=(8,2), padx=6)
        tk.Label(hrow, text=f"📦 ETF Info",
                 font=('Arial', 10, 'bold'), bg=CARD, fg='#4FC3F7').pack(side='left', padx=4)
        tk.Frame(self.rpanel, bg='#4FC3F7', height=1).pack(fill='x', padx=8)

        # Scrollable content
        rcanvas = tk.Canvas(self.rpanel, bg=CARD, highlightthickness=0)
        rsb = ttk.Scrollbar(self.rpanel, orient='vertical', command=rcanvas.yview)
        rcontent = tk.Frame(rcanvas, bg=CARD)
        rcontent.bind('<Configure>', lambda e: rcanvas.configure(scrollregion=rcanvas.bbox('all')))
        rcanvas.create_window((0,0), window=rcontent, anchor='nw', tags='rc')
        rcanvas.configure(yscrollcommand=rsb.set)
        rcanvas.bind('<Configure>', lambda e: rcanvas.itemconfig('rc', width=e.width))
        rcanvas.bind('<MouseWheel>', lambda e: rcanvas.yview_scroll(-1*(e.delta//120), 'units'))
        rsb.pack(side='right', fill='y'); rcanvas.pack(fill='both', expand=True, pady=(4,0))

        chg_col = GREEN if chg >= 0 else RED

        # ETF Name card
        name_f = tk.Frame(rcontent, bg=CARD2, pady=10); name_f.pack(fill='x', padx=6, pady=(8,4))
        tk.Label(name_f, text=sym, font=('Arial', 14, 'bold'),
                 bg=CARD2, fg='#4FC3F7').pack(anchor='w', padx=10)
        short = name[:32]+'…' if len(name)>32 else name
        tk.Label(name_f, text=short, font=('Arial', 8),
                 bg=CARD2, fg=SUBTEXT, wraplength=220, justify='left').pack(anchor='w', padx=10, pady=(2,0))

        # Price + Change
        price_f = tk.Frame(rcontent, bg=CARD2, pady=10); price_f.pack(fill='x', padx=6, pady=2)
        tk.Label(price_f, text=f"₹{ltp:,.2f}" if ltp else "—",
                 font=('Arial', 20, 'bold'), bg=CARD2, fg=TEXT).pack(anchor='w', padx=10)
        chg_str = f"{chg:+.2f}% Today" if chg is not None else "—"
        tk.Label(price_f, text=chg_str, font=('Arial', 11, 'bold'),
                 bg=CARD2, fg=chg_col).pack(anchor='w', padx=10)

        # Volume
        try:
            v = float(vol)
            vol_str = f"{v/1e7:.2f} Cr" if v>=1e7 else f"{v/1e5:.1f} L" if v>=1e5 else f"{int(v):,}"
        except: vol_str = str(vol) if vol else "—"
        vol_f = tk.Frame(rcontent, bg=CARD2, pady=8); vol_f.pack(fill='x', padx=6, pady=2)
        tk.Label(vol_f, text="📊 Volume", font=('Arial', 8), bg=CARD2, fg=SUBTEXT).pack(anchor='w', padx=10)
        tk.Label(vol_f, text=vol_str, font=('Arial', 12, 'bold'),
                 bg=CARD2, fg=TEXT).pack(anchor='w', padx=10)

        # ── Quick Links ───────────────────────────────────────────────────────
        tk.Frame(rcontent, bg=BORDER, height=1).pack(fill='x', padx=6, pady=(10,4))
        tk.Label(rcontent, text="🔗 Quick Links", font=('Arial', 9, 'bold'),
                 bg=CARD, fg=TEXT).pack(anchor='w', padx=10, pady=(0,4))

        def _link_btn(txt, fg, bg, url):
            tk.Button(rcontent, text=txt, font=('Arial', 9, 'bold'),
                      bg=bg, fg=fg, relief='flat', padx=8, pady=8,
                      cursor='hand2',
                      command=lambda u=url: webbrowser.open(u)
                      ).pack(fill='x', padx=6, pady=2)

        # NSE ETF Detail page — correct URL format for ETF
        _link_btn("🟠 NSE ETF Detail Page", YELLOW, '#1A1200',
                  f"https://www.nseindia.com/get-quotes/equity?symbol={sym}")

        # NSE ETF full list
        _link_btn("📋 NSE All ETFs List", ACCENT, '#101A2A',
                  "https://www.nseindia.com/market-data/exchange-traded-funds-etf")

        # TradingView chart
        _link_btn("📈 TradingView Chart", GREEN, '#0A1A0A',
                  f"https://www.tradingview.com/chart/?symbol=NSE%3A{sym}")

        # ETF note
        tk.Frame(rcontent, bg=BORDER, height=1).pack(fill='x', padx=6, pady=(8,4))
        tk.Label(rcontent,
                 text="ℹ️ ETF = Index Fund jo stock\nki tarah NSE pe trade hota hai.\nNAV ≈ underlying index value.",
                 font=('Arial', 8, 'italic'), bg=CARD, fg=SUBTEXT,
                 wraplength=210, justify='left').pack(anchor='w', padx=10, pady=6)

    # ══════════════════════════════════════════════════════════════════════════
    # IPO SECTION — NSE IPOs with GMP + Score
    # ══════════════════════════════════════════════════════════════════════════

    def _show_ipo_section(self):
        """IPO Hub — upcoming + current IPOs with GMP and buy score"""
        self._nav_stack.append(('welcome',))
        self._current_chartink = None
        for w in self.main.winfo_children(): w.destroy()
        self._hm_tabs = {}; self._hm_content = None

        # Header
        hdr = tk.Frame(self.main, bg=CARD, pady=10); hdr.pack(fill='x')
        tk.Label(hdr, text="🚀  IPO Hub & Score",
                 font=('Arial', 15, 'bold'), bg=CARD, fg='#C678FF').pack(side='left', padx=14)
        tk.Button(hdr, text="🔄 Refresh", font=('Arial', 9),
                  bg=BORDER, fg=ACCENT, relief='flat', padx=10, pady=6,
                  cursor='hand2', command=self._show_ipo_section).pack(side='right', padx=10)
        tk.Button(hdr, text="◀ Back", font=('Arial', 9, 'bold'),
                  bg=BORDER, fg=TEXT, relief='flat', padx=10, pady=6,
                  cursor='hand2', command=self._go_back).pack(side='right', padx=4)
        tk.Frame(self.main, bg='#C678FF', height=2).pack(fill='x')

        # Score explanation card
        score_info = tk.Frame(self.main, bg='#130D1A', pady=8); score_info.pack(fill='x', padx=8, pady=4)
        tk.Label(score_info, text="📊 IPO Score System  (Max 10 Points)",
                 font=('Arial', 9, 'bold'), bg='#130D1A', fg='#C678FF').pack(anchor='w', padx=10)
        criteria_txt = (
            "  ✅ GMP > 20% (+2)   ✅ GMP > 0% (+1)   ✅ Subscription > 10x (+2)   "
            "✅ Subscription > 2x (+1)   ✅ Price Band ≤ ₹500 (+1)   "
            "✅ Category: Mainboard (+1)   ✅ Issue Size > 500Cr (+1)   ✅ Reputed Registrar (+1)"
        )
        tk.Label(score_info, text=criteria_txt, font=('Arial', 7),
                 bg='#130D1A', fg=SUBTEXT, wraplength=750, justify='left').pack(anchor='w', padx=10)

        # Body — IPO list
        outer = tk.Frame(self.main, bg=BG); outer.pack(fill='both', expand=True)
        vsb = ttk.Scrollbar(outer, orient='vertical'); vsb.pack(side='right', fill='y')
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0, yscrollcommand=vsb.set)
        canvas.pack(fill='both', expand=True)
        vsb.config(command=canvas.yview)
        canvas.bind('<MouseWheel>', lambda e: canvas.yview_scroll(-1*(e.delta//120), 'units'))
        con = tk.Frame(canvas, bg=BG)
        con.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0,0), window=con, anchor='nw', tags='ipo')
        canvas.bind('<Configure>', lambda e: canvas.itemconfig('ipo', width=e.width))

        # Loading label
        load_lbl = tk.Label(con, text="⏳ IPO data fetch ho raha hai...",
                            font=('Arial', 12), bg=BG, fg=SUBTEXT, pady=40)
        load_lbl.pack()

        threading.Thread(target=self._fetch_ipo_data, args=(con, canvas), daemon=True).start()

    def _show_ipo_section(self):
        """IPO Hub — Left: date-wise list | Right: details on click"""
        self._nav_stack.append(('welcome',))
        self._current_chartink = None
        for w in self.main.winfo_children(): w.destroy()
        self._hm_tabs = {}; self._hm_content = None
        # Right panel reset — stock data hatao, indices dikhao
        self._rpanel_sym = ''; self._rpanel_name = ''
        self._render_sectors_default()

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self.main, bg=CARD, pady=8); hdr.pack(fill='x')
        tk.Label(hdr, text="🚀  IPO Hub & Score",
                 font=('Arial', 14, 'bold'), bg=CARD, fg='#C678FF').pack(side='left', padx=14)
        tk.Button(hdr, text="🔄 Refresh", font=('Arial', 9),
                  bg=BORDER, fg=ACCENT, relief='flat', padx=10, pady=5,
                  cursor='hand2', command=self._show_ipo_section).pack(side='right', padx=10)
        tk.Button(hdr, text="◀ Back", font=('Arial', 9, 'bold'),
                  bg=BORDER, fg=TEXT, relief='flat', padx=10, pady=5,
                  cursor='hand2', command=self._go_back).pack(side='right', padx=4)
        tk.Frame(self.main, bg='#C678FF', height=2).pack(fill='x')

        # ── Body: LEFT list (250px) + RIGHT detail panel ──────────────────────
        body = tk.Frame(self.main, bg=BG); body.pack(fill='both', expand=True)

        # LEFT PANEL — IPO list
        left_outer = tk.Frame(body, bg=CARD, width=252)
        left_outer.pack(side='left', fill='y')
        left_outer.pack_propagate(False)

        # LEFT header
        lhdr = tk.Frame(left_outer, bg='#130D1A', pady=7)
        lhdr.pack(fill='x')
        tk.Label(lhdr, text="📋  IPO List", font=('Arial', 9, 'bold'),
                 bg='#130D1A', fg='#C678FF').pack(side='left', padx=8)

        # Filter buttons (All / Open / Upcoming / Closed)
        filter_row = tk.Frame(left_outer, bg=CARD)
        filter_row.pack(fill='x', padx=4, pady=4)
        self._ipo_filter   = tk.StringVar(value='All')
        self._ipo_list_ref = []      # all IPOs fetched
        self._ipo_selected = None    # currently selected IPO

        for fval, flbl, fcol in [
            ('All',      'All',      SUBTEXT),
            ('Open',     '🟢 Open',  GREEN),
            ('Upcoming', '🟡 Next',  YELLOW),
            ('Closed',   '⬛ Done',  '#888888'),
        ]:
            tk.Button(filter_row, text=flbl, font=('Arial', 7, 'bold'),
                      bg=BORDER, fg=fcol, relief='flat', padx=6, pady=3,
                      cursor='hand2',
                      command=lambda v=fval: self._ipo_apply_filter(v)
                      ).pack(side='left', padx=1)

        tk.Frame(left_outer, bg=BORDER, height=1).pack(fill='x')

        # Scrollable list
        lcanvas = tk.Canvas(left_outer, bg=CARD, highlightthickness=0, width=250)
        lsb = ttk.Scrollbar(left_outer, orient='vertical', command=lcanvas.yview)
        lsb.pack(side='right', fill='y')
        lcanvas.pack(fill='both', expand=True)
        lcanvas.configure(yscrollcommand=lsb.set)
        lcanvas.bind('<MouseWheel>', lambda e: lcanvas.yview_scroll(-1*(e.delta//120), 'units'))

        self._ipo_list_frame = tk.Frame(lcanvas, bg=CARD)
        self._ipo_list_frame.bind('<Configure>',
            lambda e: lcanvas.configure(scrollregion=lcanvas.bbox('all')))
        lcanvas.create_window((0,0), window=self._ipo_list_frame, anchor='nw', tags='ilf')
        lcanvas.bind('<Configure>', lambda e: lcanvas.itemconfig('ilf', width=e.width))

        # Loading row
        self._ipo_loading_lbl = tk.Label(self._ipo_list_frame,
                                          text="⏳ Loading...",
                                          font=('Arial', 9), bg=CARD, fg=SUBTEXT, pady=20)
        self._ipo_loading_lbl.pack()

        # RIGHT PANEL — detail view
        tk.Frame(body, bg=BORDER, width=1).pack(side='left', fill='y')
        self._ipo_right = tk.Frame(body, bg=BG)
        self._ipo_right.pack(side='left', fill='both', expand=True)

        # Right panel placeholder
        self._ipo_show_placeholder()

        # Start fetch in background
        threading.Thread(target=self._fetch_ipo_data_v2, daemon=True).start()

    def _ipo_show_placeholder(self):
        """Show welcome message in right panel"""
        for w in self._ipo_right.winfo_children(): w.destroy()
        ph = tk.Frame(self._ipo_right, bg=BG)
        ph.place(relx=0.5, rely=0.4, anchor='center')
        tk.Label(ph, text="🚀", font=('Arial', 36), bg=BG, fg='#C678FF').pack()
        tk.Label(ph, text="Koi IPO select karo",
                 font=('Arial', 13, 'bold'), bg=BG, fg=TEXT).pack(pady=(8,2))
        tk.Label(ph, text="Left panel se IPO pe click karo\nScore + details yahan dikhenge",
                 font=('Arial', 9), bg=BG, fg=SUBTEXT, justify='center').pack()

    def _fetch_ipo_data_v2(self):
        """Fetch from ipowatch: upcoming-ipo-list + ipo-gmp"""
        import datetime as _dt
        today = _dt.date.today()
        cutoff = today - _dt.timedelta(days=60)   # 2 months back

        HEADERS = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,*/*;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/',
        }

        def _sess():
            s = requests.Session(); s.headers.update(HEADERS); return s

        ipos = []

        # ── STEP 1: ipowatch upcoming-ipo-list ───────────────────────────────
        try:
            r = _sess().get("https://ipowatch.in/upcoming-ipo-list/", timeout=18)
            print(f"[ipo-list] {r.status_code} len={len(r.text)}")
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                for tbl in soup.select('table'):
                    ths = [th.get_text(strip=True) for th in tbl.select('th')]
                    ths_lower = [h.lower() for h in ths]
                    print(f"[ipo-list] raw headers={ths}")
                    if not any(w in ' '.join(ths_lower) for w in ['ipo','stock','company','date']):
                        continue

                    # ── Robust column detection ──────────────────────────────
                    # Actual ipowatch: Company(0) | IPO Date(1) | IPO Size(2) | IPO Price Band(3) | Application(4)
                    ci = {'name': 0, 'date': 1, 'type': -1, 'size': 2, 'price': 3}  # safe defaults
                    for i, h in enumerate(ths_lower):
                        if 'company' in h or 'stock' in h:      ci['name']  = i
                        elif 'date' in h:                        ci['date']  = i
                        elif 'size' in h:                        ci['size']  = i
                        elif 'price' in h or 'band' in h:       ci['price'] = i
                        elif 'type' in h:                        ci['type']  = i
                    print(f"[ipo-list] col map={ci}")

                    import re as _re2
                    DATE_PAT = _re2.compile(r'^\d+\s*[-–]\s*\d+\s+\w+$|^\d{1,2}\s+\w+\s+\d{4}$')

                    for row in tbl.select('tr')[1:]:
                        tds = row.select('td')
                        if len(tds) < 3: continue

                        def _cell(k, fallback=0):
                            idx = ci.get(k, fallback)
                            return tds[idx].get_text(strip=True) if idx < len(tds) else ''

                        name = _cell('name', 0)

                        # Safety: if name looks like a date ("5-7 May"), swap name/date columns
                        if DATE_PAT.match(name) and len(tds) > ci.get('date', 1):
                            # Columns are swapped — try next column as name
                            for alt_i in range(len(tds)):
                                alt = tds[alt_i].get_text(strip=True)
                                if alt and not DATE_PAT.match(alt) and len(alt) > 3 and not alt.replace('.','').replace(',','').replace('₹','').isnumeric():
                                    name = alt
                                    # Update ci for this table
                                    ci['name'] = alt_i
                                    # date is the one that matched DATE_PAT (original ci['name'])
                                    ci['date'] = 0 if ci['name'] != 0 else 1
                                    print(f"[ipo-list] ⚠️ Swapped: name col={ci['name']}, date col={ci['date']}")
                                    break

                        if not name or len(name) < 2 or DATE_PAT.match(name): continue

                        # Get detail URL
                        detail_url = ''
                        name_idx = ci.get('name', 0)
                        if name_idx < len(tds):
                            a = tds[name_idx].find('a')
                            if a and a.get('href'):
                                href = a['href']
                                detail_url = href if href.startswith('http') else 'https://ipowatch.in' + href

                        date_txt  = _cell('date',  1)
                        type_txt  = _cell('type',  -1) if ci.get('type', -1) >= 0 else ''
                        size_txt  = _cell('size',  2)
                        price_txt = _cell('price', 3)

                        # Parse dates
                        open_s, close_s, status, close_date_obj = self._ipo_parse_date(date_txt, today)

                        # Skip IPOs closed > 60 days ago
                        if status == 'Closed' and close_date_obj:
                            if close_date_obj < cutoff: continue

                        # Parse price — handles "₹95 to ₹100" or "₹95-₹100"
                        price_num = 0
                        try:
                            pb = price_txt.replace('₹','').replace(',','').replace(' to ','-').replace('to','-')
                            parts = [p.strip() for p in pb.split('-') if p.strip()]
                            price_num = float(parts[-1]) if parts else 0
                        except: pass

                        # Parse issue size — "₹3,405 Cr." → 3405
                        issue_size = 0
                        try:
                            st = size_txt.replace('₹','').replace(',','')
                            st = st.replace('Cr.','').replace('Cr','').strip()
                            # Sometimes has extra text like "45 Cr." after number
                            import re as _re4
                            m4 = _re4.search(r'[\d.]+', st)
                            if m4: issue_size = float(m4.group())
                        except: pass

                        # Category — use type col if available, else guess from issue size
                        category = 'Mainboard'
                        if type_txt:
                            tl = type_txt.lower()
                            if 'sme' in tl:      category = 'SME'
                            elif 'reit' in tl:   category = 'REIT'
                            elif 'invit' in tl:  category = 'InvIT'
                        else:
                            # No type col — SME typically < 250 Cr
                            if issue_size and issue_size < 250:
                                category = 'SME'

                        ipos.append({
                            'company':    name.strip(),
                            'symbol':     '',
                            'status':     status,
                            'price_band': price_txt,
                            'price_num':  price_num,
                            'open_date':  open_s,
                            'close_date': close_s,
                            'close_date_obj': close_date_obj,
                            'issue_size': issue_size,
                            'lot_size':   0,
                            'subscription': None,
                            'registrar':  '',
                            'category':   category,
                            'gmp':        None,
                            'detail_url': detail_url,
                            'review_url': '',
                        })
                    if ipos:
                        print(f"[ipo-list] ✅ {len(ipos)} IPOs")
                        break
        except Exception as ex:
            print(f"[ipo-list] ❌ {ex}")
            import traceback; traceback.print_exc()

        # ── STEP 1b: Fallback — chittorgarh if ipowatch gave nothing ──────────
        if not ipos:
            print("[ipo-list] Trying chittorgarh fallback...")
            try:
                r_c = _sess().get("https://www.chittorgarh.com/ipo/ipo_list.asp", timeout=15)
                if r_c.status_code == 200:
                    soup_c = BeautifulSoup(r_c.text, 'html.parser')
                    import re as _re3, datetime as _dt3
                    for tbl in soup_c.select('table'):
                        rows_c = tbl.select('tr')
                        if len(rows_c) < 3: continue
                        ths_c = [th.get_text(strip=True).lower() for th in rows_c[0].select('th,td')]
                        if not any('ipo' in h or 'stock' in h or 'company' in h for h in ths_c): continue
                        print(f"[chittorgarh] headers={ths_c[:6]}")
                        for row in rows_c[1:]:
                            tds = row.select('td')
                            if len(tds) < 4: continue
                            name = tds[0].get_text(strip=True)
                            if not name or len(name) < 3: continue
                            a = tds[0].find('a')
                            durl = ('https://www.chittorgarh.com' + a['href']) if a and a.get('href') else ''
                            open_raw  = tds[1].get_text(strip=True) if len(tds)>1 else ''
                            close_raw = tds[2].get_text(strip=True) if len(tds)>2 else ''
                            price_raw = tds[3].get_text(strip=True) if len(tds)>3 else ''
                            size_raw  = tds[5].get_text(strip=True) if len(tds)>5 else ''
                            type_raw  = tds[4].get_text(strip=True) if len(tds)>4 else ''

                            price_num = 0
                            try:
                                pb = price_raw.replace('₹','').replace(',','').split('-')
                                price_num = float(pb[-1].strip()) if pb else 0
                            except: pass
                            issue_size = 0
                            try:
                                st = size_raw.replace('₹','').replace(',','').replace('Cr','').strip()
                                issue_size = float(st) if st else 0
                            except: pass

                            # Dates: "Apr 27, 2026" format
                            open_s, close_s, status, close_obj = open_raw, close_raw, 'Upcoming', None
                            try:
                                od = _dt3.datetime.strptime(open_raw.strip(), '%b %d, %Y').date()
                                cd = _dt3.datetime.strptime(close_raw.strip(), '%b %d, %Y').date()
                                open_s  = od.strftime('%d %b %Y')
                                close_s = cd.strftime('%d %b %Y')
                                close_obj = cd
                                if od <= today <= cd:  status = 'Open'
                                elif today > cd:       status = 'Closed'
                                if status == 'Closed' and (today - cd).days > 60: continue
                            except: pass

                            cat = 'SME' if 'sme' in type_raw.lower() else 'Mainboard'
                            ipos.append({
                                'company': name, 'symbol': '', 'status': status,
                                'price_band': price_raw, 'price_num': price_num,
                                'open_date': open_s, 'close_date': close_s,
                                'close_date_obj': close_obj,
                                'issue_size': issue_size, 'lot_size': 0,
                                'subscription': None, 'registrar': '',
                                'category': cat, 'gmp': None,
                                'detail_url': durl, 'review_url': '',
                            })
                        if ipos:
                            print(f"[chittorgarh] ✅ {len(ipos)} IPOs")
                            break
            except Exception as ex2:
                print(f"[chittorgarh] ❌ {ex2}")

        # ── STEP 1c: NSE API — jo IPOs ipowatch/chittorgarh me nahi hain unhe add karo ──
        try:
            existing_names = set(i['company'].lower() for i in ipos)
            NSE_SESSION.get("https://www.nseindia.com", timeout=6)
            NSE_SESSION.get("https://www.nseindia.com/market-data/all-upcoming-issues-ipo", timeout=6)
            import re as _re_nse, datetime as _dt_nse
            for nse_list_url in [
                "https://www.nseindia.com/api/ipo-current-issue",
                "https://www.nseindia.com/api/ipo-upcoming-issue",
            ]:
                try:
                    rn = NSE_SESSION.get(nse_list_url, timeout=10)
                    if rn.status_code != 200: continue
                    nse_data = rn.json()
                    if isinstance(nse_data, dict):
                        nse_data = nse_data.get('data', nse_data.get('ipoList', []))
                    print(f"[nse-list] {nse_list_url.split('/')[-1]} → {len(nse_data or [])} items")
                    for ni in (nse_data or []):
                        cname = str(ni.get('companyName', ni.get('name', ''))).strip()
                        if not cname: continue
                        cname_lower = cname.lower()
                        cwords = [w for w in cname_lower.split() if len(w) > 3]
                        if any(any(w in en for w in cwords) for en in existing_names): continue

                        symbol  = ni.get('symbol', '')
                        pb_lo   = str(ni.get('priceLow', ni.get('issuePriceLow', ''))).strip()
                        pb_hi   = str(ni.get('priceHigh', ni.get('issuePriceHigh', ''))).strip()
                        pb      = f"₹{pb_lo} - ₹{pb_hi}" if pb_lo and pb_hi and pb_lo != pb_hi else (f"₹{pb_hi}" if pb_hi else 'N/A')
                        try: price_num = float(pb_hi.replace(',','')) if pb_hi else 0
                        except: price_num = 0

                        open_raw  = str(ni.get('openDate', ni.get('bidStartDate', ''))).strip()
                        close_raw = str(ni.get('closeDate', ni.get('bidEndDate', ''))).strip()
                        open_s = open_raw; close_s = close_raw; status = 'Upcoming'; close_obj = None
                        try:
                            for fmt in ['%d-%b-%Y', '%Y-%m-%d', '%d %b %Y', '%b %d, %Y']:
                                try:
                                    od = _dt_nse.datetime.strptime(open_raw, fmt).date()
                                    cd = _dt_nse.datetime.strptime(close_raw, fmt).date()
                                    open_s = od.strftime('%d %b %Y'); close_s = cd.strftime('%d %b %Y')
                                    close_obj = cd
                                    if od <= today <= cd: status = 'Open'
                                    elif today > cd:      status = 'Closed'
                                    break
                                except: pass
                        except: pass
                        if status == 'Closed' and close_obj and (today - close_obj).days > 60: continue

                        try: issue_size = float(str(ni.get('issueSize', ni.get('issueSizeInCr', 0))).replace(',','').replace('Cr','').strip())
                        except: issue_size = 0

                        cat_raw = str(ni.get('series', ni.get('issueType', ''))).upper()
                        cat = 'SME' if 'SM' in cat_raw or 'EMERGE' in cat_raw else 'Mainboard'
                        slug = _re_nse.sub(r'[^a-z0-9]+', '-', cname.lower()).strip('-')
                        detail_url = f"https://ipowatch.in/{slug}-ipo-date-review-price-allotment-details/"

                        ipos.append({
                            'company': cname, 'symbol': symbol, 'status': status,
                            'price_band': pb, 'price_num': price_num,
                            'open_date': open_s, 'close_date': close_s, 'close_date_obj': close_obj,
                            'issue_size': issue_size, 'lot_size': 0,
                            'subscription': None, 'registrar': '', 'category': cat,
                            'gmp': None, 'detail_url': detail_url, 'review_url': '',
                        })
                        existing_names.add(cname_lower)
                        print(f"[nse-list] ✅ Added: {cname} ({status})")
                except Exception as en_err:
                    print(f"[nse-list] {nse_list_url.split('/')[-1]} error: {en_err}")
        except Exception as e_nse_list:
            print(f"[nse-list] ❌ {e_nse_list}")

        # ── STEP 2: GMP page ──────────────────────────────────────────────────
        gmp_map = {}
        try:
            r2 = _sess().get("https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/", timeout=15)
            print(f"[gmp] {r2.status_code}")
            if r2.status_code == 200:
                soup2 = BeautifulSoup(r2.text, 'html.parser')
                for tbl in soup2.select('table'):
                    ths = [th.get_text(strip=True) for th in tbl.select('th')]
                    ths_l = [h.lower() for h in ths]
                    print(f"[gmp] raw headers={ths}")
                    if not any('gmp' in h or 'grey' in h for h in ths_l): continue

                    gcol = {'name': 0, 'price': 1, 'gmp': 2, 'listing': 3, 'sub': 4}
                    for i, h in enumerate(ths_l):
                        if 'stock' in h or ('ipo' in h and 'gmp' not in h): gcol['name']    = i
                        elif 'gmp' in h or 'grey' in h:                     gcol['gmp']     = i
                        elif 'listing' in h or 'est' in h:                  gcol['listing'] = i
                        elif 'sub' in h or 'times' in h:                    gcol['sub']     = i
                        elif 'price' in h and 'band' not in h:              gcol['price']   = i
                    print(f"[gmp] col map={gcol}")

                    for row in tbl.select('tr')[1:]:
                        tds = row.select('td')
                        if len(tds) < 2: continue
                        ni = gcol.get('name', 0)
                        name = tds[ni].get_text(strip=True) if ni < len(tds) else ''
                        if not name or len(name) < 2: continue

                        # Get price for sanity check
                        pi = gcol.get('price', 1)
                        pv = 0
                        if pi < len(tds):
                            try:
                                pt = tds[pi].get_text(strip=True).replace('₹','').replace(',','').strip()
                                import re as _gre
                                pnums = _gre.findall(r'\d+', pt)
                                if pnums: pv = float(pnums[-1])
                            except: pass

                        gv, lv, sv = None, '', None
                        gi = gcol.get('gmp', 2)
                        if gi < len(tds):
                            raw_gmp = tds[gi].get_text(strip=True)
                            raw_clean = raw_gmp.replace('₹','').replace('+','').replace(',','').strip()
                            candidate = clean_num(raw_clean)
                            # Sanity: reject year-like numbers and absurdly large values
                            if candidate is not None:
                                if 2000 <= candidate <= 2099:
                                    candidate = None  # year, not GMP
                                elif pv > 0 and abs(candidate) > pv * 3:
                                    candidate = None  # way too large
                            gv = candidate

                        li = gcol.get('listing', 3)
                        if li < len(tds):
                            lv = tds[li].get_text(strip=True)

                        si = gcol.get('sub', 4)
                        if si < len(tds):
                            sv_raw = tds[si].get_text(strip=True).replace('x','').replace(',','').strip()
                            sv_candidate = clean_num(sv_raw)
                            # Sanity: subscription 0-5000x
                            if sv_candidate is not None and 0 <= sv_candidate <= 5000:
                                sv = sv_candidate

                        gmp_map[name.lower()] = {'gmp': gv, 'listing': lv, 'sub': sv,
                                                  'price': pv, 'raw_name': name}
                    if gmp_map:
                        print(f"[gmp] ✅ {len(gmp_map)} entries, sample={list(gmp_map.items())[:2]}")
                        break
        except Exception as ex:
            print(f"[gmp] ❌ {ex}")

        # ── STEP 3: Merge GMP ────────────────────────────────────────────────
        def _fuzzy(name, dmap):
            nl = name.lower().strip()
            if nl in dmap: return dmap[nl]
            for k in dmap:
                if nl[:8] in k or k[:8] in nl: return dmap[k]
            words = set(nl.split())
            for k in dmap:
                if len(words & set(k.split())) >= 2: return dmap[k]
            return None

        for ipo in ipos:
            g = _fuzzy(ipo['company'], gmp_map)
            if g:
                ipo['gmp'] = g.get('gmp')
                ipo['est_listing'] = g.get('listing','')
                if not ipo.get('subscription'): ipo['subscription'] = g.get('sub')

        # Sort: Open first → Upcoming by open date → Closed
        import datetime as _dt2
        def _sort_key(x):
            order = {'Open': 0, 'Upcoming': 1, 'Closed': 2}
            base = order.get(x.get('status','Upcoming'), 1)
            # Sort upcoming by open date ascending
            try:
                od = _dt2.datetime.strptime(x['open_date'], '%d %b %Y').date()
                days = (od - _dt2.date.today()).days
            except: days = 999
            return (base, days)

        ipos.sort(key=_sort_key)
        self._ipo_list_ref = ipos
        print(f"[IPO v2] {len(ipos)} total → rendering list")
        self.root.after(0, lambda: self._ipo_render_left_list(ipos))

        # Prefetch detail for first 3 IPOs silently in background
        def _prefetch():
            for ipo in ipos[:3]:
                if not ipo.get('_detail_fetched'):
                    self._ipo_fetch_detail_page(ipo)
                    ipo['_detail_fetched'] = True
            if ipos:
                self.root.after(200, lambda: self._ipo_on_row_click(
                    ipos[0], self._ipo_row_btns.get(ipos[0].get('company',''))))
        threading.Thread(target=_prefetch, daemon=True).start()

    def _ipo_parse_date(self, date_txt, today):
        """Parse ipowatch date like '5-7 May' or '5-7 May 2026' → (open_str, close_str, status, close_date_obj)"""
        import datetime as _dt, re as _re
        date_txt = date_txt.strip()
        open_s = date_txt; close_s = ''; status = 'Upcoming'; close_obj = None
        try:
            # Pattern: "5-7 May" or "5-7 May 2026" or "30-5 May 2026" (cross-month)
            m = _re.match(r'(\d+)\s*[-–]\s*(\d+)\s+(\w+)\s*(\d{4})?', date_txt)
            if m:
                d1  = int(m.group(1))
                d2  = int(m.group(2))
                mon = m.group(3)
                year = int(m.group(4)) if m.group(4) else today.year

                od = None
                for fmt in ('%d %B %Y', '%d %b %Y'):
                    try:
                        od = _dt.datetime.strptime(f"{d1} {mon} {year}", fmt).date()
                        break
                    except: pass
                if od is None:
                    return date_txt, '', 'Upcoming', None

                # Close date — same month unless d2 < d1 (cross-month)
                cd = None
                for fmt in ('%d %B %Y', '%d %b %Y'):
                    try:
                        cd = _dt.datetime.strptime(f"{d2} {mon} {year}", fmt).date()
                        break
                    except: pass
                if cd is None: cd = od

                if d2 < d1:
                    # Cross-month: e.g. "30-5 May" → open Apr 30, close May 5
                    nm = (od.month % 12) + 1
                    ny = year if nm > 1 else year + 1
                    cd = _dt.date(ny, nm, d2)

                open_s    = od.strftime('%d %b %Y')
                close_s   = cd.strftime('%d %b %Y')
                close_obj = cd
                if od <= today <= cd:  status = 'Open'
                elif today > cd:       status = 'Closed'
        except Exception as ex:
            print(f"[date] '{date_txt}' → {ex}")
        return open_s, close_s, status, close_obj

    def _calc_ipo_score(self, ipo):
        """Calculate IPO buy score out of 10"""
        score = 0; reasons = []
        gmp        = ipo.get('gmp')
        price_num  = ipo.get('price_num', 0)
        sub        = ipo.get('subscription') or 0
        issue_size = ipo.get('issue_size', 0)
        category   = ipo.get('category', '')
        registrar  = (ipo.get('registrar') or '').lower()

        # GMP (max 2 pts)
        if gmp is not None and price_num and price_num > 0:
            gp = (gmp / price_num) * 100
            if gp > 20:  score += 2; reasons.append(f"✅ GMP {gp:.0f}% > 20%")
            elif gp > 0: score += 1; reasons.append(f"✅ GMP {gp:.0f}% > 0%")
            else:        reasons.append(f"❌ GMP negative ({gp:.0f}%)")
        else:
            reasons.append("❓ GMP unknown")

        # Subscription (max 2 pts)
        if sub > 10:   score += 2; reasons.append(f"✅ Subscribed {sub:.1f}x > 10x")
        elif sub > 2:  score += 1; reasons.append(f"✅ Subscribed {sub:.1f}x > 2x")
        elif sub > 0:  reasons.append(f"❌ Only {sub:.1f}x subscribed")
        else:          reasons.append("❓ Subscription data nahi")

        # Price ≤ 500 (1 pt)
        if price_num and 0 < price_num <= 500:
            score += 1; reasons.append(f"✅ Price ≤ ₹500 ({price_num:.0f})")
        elif price_num and price_num > 500:
            reasons.append(f"⚠️ Price ₹{price_num:.0f} > 500")

        # Mainboard (1 pt)
        if category == 'Mainboard':
            score += 1; reasons.append("✅ Mainboard IPO")
        else:
            reasons.append(f"⚠️ {category or 'SME'} IPO (risky)")

        # Issue size (1 pt)
        if issue_size >= 500:   score += 1; reasons.append(f"✅ Issue ₹{issue_size:.0f}Cr ≥ 500")
        elif issue_size >= 100: reasons.append(f"⚠️ Issue ₹{issue_size:.0f}Cr")
        else:                   reasons.append("❌ Small issue size")

        # Reputed registrar (1 pt)
        if any(r in registrar for r in ['link intime','kfintech','kfin tech','kfin technologies',
                                         'bigshare','skyline','cameo','mas services',
                                         'beetal','purva share','integrated registry']):
            score += 1; reasons.append(f"✅ Registrar: {ipo.get('registrar','')}")
        else:
            reasons.append(f"❓ Registrar: {ipo.get('registrar','') or 'Unknown'}")

        return min(score, 10), reasons

    def _ipo_apply_filter(self, fval):
        """Filter left list by status"""
        self._ipo_filter.set(fval)
        filtered = self._ipo_list_ref if fval == 'All' else [
            i for i in self._ipo_list_ref if i.get('status') == fval]
        self._ipo_render_left_list(filtered, keep_selection=True)

    def _ipo_render_left_list(self, ipos, keep_selection=False):
        """Render the left sidebar list rows"""
        for w in self._ipo_list_frame.winfo_children(): w.destroy()

        if not ipos:
            tk.Label(self._ipo_list_frame,
                     text="❌ Data load nahi hua\n\nInternet check karo\nya Refresh karo",
                     font=('Arial', 9), bg=CARD, fg=SUBTEXT,
                     justify='center', pady=30).pack()
            # Fallback links
            for lbl, url in [
                ("🌐 ipowatch.in", "https://ipowatch.in/"),
                ("📊 IPO GMP", "https://ipowatch.in/ipo-gmp/"),
            ]:
                tk.Button(self._ipo_list_frame, text=lbl, font=('Arial', 8),
                          bg=BORDER, fg=ACCENT, relief='flat', padx=8, pady=4,
                          cursor='hand2', command=lambda u=url: webbrowser.open(u)
                          ).pack(fill='x', padx=10, pady=2)
            return

        self._ipo_row_btns = {}
        status_colors = {
            'Open':     (GREEN,   '🟢'),
            'Upcoming': (YELLOW,  '🟡'),
            'Closed':   ('#888', '⬛'),
        }

        last_status = None
        for ipo in ipos:
            status = ipo.get('status', 'Upcoming')
            sc, icon = status_colors.get(status, (SUBTEXT, '◯'))

            # Section divider when status changes
            if status != last_status:
                sec_names = {'Open': 'Currently Open', 'Upcoming': 'Upcoming', 'Closed': 'Recently Closed'}
                div = tk.Frame(self._ipo_list_frame, bg='#0D0D1A', pady=3)
                div.pack(fill='x')
                tk.Label(div, text=f"  {icon} {sec_names.get(status, status)}",
                         font=('Arial', 7, 'bold'), bg='#0D0D1A', fg=sc).pack(anchor='w', padx=6)
                last_status = status

            # Row frame
            row_bg = CARD2
            row_f = tk.Frame(self._ipo_list_frame, bg=row_bg, pady=0,
                             highlightbackground=BORDER, highlightthickness=1)
            row_f.pack(fill='x', padx=3, pady=1)

            # Score badge color
            score, _ = self._calc_ipo_score(ipo)
            if score >= 7:   sbadge = (GREEN,  f"{score}/10")
            elif score >= 5: sbadge = (YELLOW, f"{score}/10")
            elif score >= 3: sbadge = (ORANGE, f"{score}/10")
            else:            sbadge = (RED,    f"{score}/10")

            inner = tk.Frame(row_f, bg=row_bg, pady=5, padx=6); inner.pack(fill='x')

            # Left: name + date
            lf = tk.Frame(inner, bg=row_bg); lf.pack(side='left', fill='x', expand=True)
            # Category badge
            cat = ipo.get('category','')
            cat_col = ACCENT if cat=='Mainboard' else ORANGE if cat=='SME' else '#888'
            tk.Label(lf, text=f" {cat} ", font=('Arial', 6, 'bold'),
                     bg=cat_col, fg='white').pack(anchor='w')
            # Company name (truncate)
            nm = ipo['company']
            nm_short = nm[:22]+'…' if len(nm)>22 else nm
            tk.Label(lf, text=nm_short, font=('Arial', 8, 'bold'),
                     bg=row_bg, fg=TEXT, anchor='w').pack(anchor='w', pady=(2,0))
            # Dates
            date_str = ipo.get('open_date','')
            if ipo.get('close_date'): date_str += f" → {ipo['close_date']}"
            tk.Label(lf, text=date_str, font=('Arial', 7),
                     bg=row_bg, fg=SUBTEXT).pack(anchor='w')
            # GMP if available
            gmp = ipo.get('gmp')
            pn  = ipo.get('price_num', 0)
            if gmp is not None and pn:
                gp = (gmp/pn)*100
                gmp_col = GREEN if gmp>0 else RED
                tk.Label(lf, text=f"GMP {gmp:+.0f} ({gp:+.1f}%)",
                         font=('Arial', 7, 'bold'), bg=row_bg, fg=gmp_col).pack(anchor='w')

            # Right: score badge
            rf = tk.Frame(inner, bg=row_bg); rf.pack(side='right')
            tk.Label(rf, text=sbadge[1], font=('Arial', 8, 'bold'),
                     bg=sbadge[0], fg='black', padx=6, pady=3).pack()

            # Click binding
            def _click(e, i=ipo, rf=row_f, inner=inner, lf=lf):
                self._ipo_on_row_click(i, rf)
            for w in [row_f, inner, lf] + list(inner.winfo_children()) + list(lf.winfo_children()):
                try: w.bind('<Button-1>', _click)
                except: pass
            row_f.bind('<Enter>', lambda e, r=row_f: r.config(bg='#1A1A2E') or
                       [c.config(bg='#1A1A2E') for c in r.winfo_children()])
            row_f.bind('<Leave>', lambda e, r=row_f, bg=row_bg: r.config(bg=bg) or
                       [c.config(bg=bg) for c in r.winfo_children()])

            self._ipo_row_btns[ipo['company']] = row_f

    def _ipo_fetch_detail_page(self, ipo):
        """
        ipowatch detail page se lot size, registrar, GMP, subscription, AUM fetch karo.
        ipowatch Lot table structure: Application | Lot Size | Shares | Amount
        We need 'Shares' column (col index 2), not 'Lot Size' (col index 1).
        Registrar is NOT in a table — it's under "IPO Registrar" heading as paragraph text.
        """
        import re as _re
        detail_url = ipo.get('detail_url', '')
        if not detail_url:
            slug = _re.sub(r'[^a-z0-9]+', '-', ipo.get('company','').lower()).strip('-')
            detail_url = f"https://ipowatch.in/{slug}-ipo-date-review-price-allotment-details/"
            ipo['detail_url'] = detail_url

        price_num = ipo.get('price_num', 0) or 0

        def _safe_gmp(val):
            if val is None: return None
            try:
                v = float(val)
                if 2000 <= v <= 2099: return None          # year reject
                if price_num > 0 and abs(v) > price_num * 5: return None  # too large
                return v
            except: return None

        try:
            from bs4 import BeautifulSoup as _BS
            HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'}
            r = requests.get(detail_url, headers=HEADERS, timeout=18)
            print(f"[detail] {ipo.get('company','')} → {r.status_code}")
            if r.status_code != 200: return
            soup = _BS(r.text, 'html.parser')
            full_text = soup.get_text(' ')

            # ══════════════════════════════════════════════════════════════════
            # LOT SIZE — ipowatch table:
            # Header row: Application | Lot Size | Shares | Amount
            # Data row:   Retail Min  |    1     |  150   | ₹15,000
            # We want the "Shares" column value (col 2), not "Lot Size" col (col 1)
            # ══════════════════════════════════════════════════════════════════
            lot_found = False
            for tbl in soup.select('table'):
                headers = [th.get_text(strip=True).lower()
                           for th in tbl.select('tr:first-child th, tr:first-child td')]
                # Check if this is the lot/market lot table
                has_lot  = any('lot' in h for h in headers)
                has_share= any('share' in h for h in headers)
                if not (has_lot or has_share): continue

                # Find "shares" column index
                shares_idx = None
                for i, h in enumerate(headers):
                    if 'share' in h and 'offered' not in h: shares_idx = i; break
                # Fallback: if no "shares" col, use last numeric col
                if shares_idx is None and has_lot:
                    shares_idx = 2  # default ipowatch position

                # Get first data row
                data_rows = tbl.select('tr')[1:]
                for drow in data_rows:
                    cells = drow.select('td')
                    if not cells: continue
                    # Try shares_idx first, then scan all cells for largest number ≤ 10000
                    candidates = []
                    for ci, cell in enumerate(cells):
                        txt = cell.get_text(strip=True).replace(',','')
                        nums = _re.findall(r'^\d+$', txt.strip())
                        if nums:
                            v = int(nums[0])
                            if 1 < v <= 10000:  # shares between 2 and 10000
                                candidates.append((ci, v))
                    if candidates:
                        # Prefer shares_idx, else largest value
                        preferred = [c for c in candidates if c[0] == shares_idx]
                        chosen = preferred[0][1] if preferred else max(candidates, key=lambda x: x[1])[1]
                        ipo['lot_size'] = chosen
                        lot_found = True
                        print(f"[detail] lot_size={chosen} from candidates={candidates}")
                        break
                if lot_found: break

            # ══════════════════════════════════════════════════════════════════
            # REGISTRAR — ipowatch has "IPO Registrar" as H2/H3 heading,
            # followed by paragraph with registrar name
            # e.g.: <h3>IPO Registrar</h3><p>Kfin Technologies Ltd.</p>
            # ══════════════════════════════════════════════════════════════════
            registrar = ''
            # Method 1: Find heading then next sibling text
            for heading in soup.find_all(['h2','h3','h4','strong','b']):
                if 'registrar' in heading.get_text(strip=True).lower():
                    # Look in next siblings
                    for sib in heading.find_next_siblings():
                        txt = sib.get_text(strip=True)
                        if txt and len(txt) > 3 and len(txt) < 100:
                            # Must look like a company name, not just numbers
                            if any(c.isalpha() for c in txt):
                                registrar = txt.split('\n')[0].strip()
                                break
                        if sib.name in ['h2','h3','h4']: break  # stop at next heading
                    if registrar: break

            # Method 2: Regex on full text — "Registrar: XYZ Ltd"
            if not registrar:
                rm = _re.search(
                    r'(?:ipo\s*)?registrar\s*[:\-–]?\s*([A-Za-z][A-Za-z\s\.&]+(?:Ltd|Limited|Pvt|Private|Services|Technologies|Intime|Fintech)[\.A-Za-z\s]*)',
                    full_text, _re.IGNORECASE)
                if rm:
                    registrar = rm.group(1).strip()[:60]

            # Method 3: Look for known registrar names in page text
            known_registrars = [
                'Link Intime India', 'KFin Technologies', 'Kfin Technologies',
                'Bigshare Services', 'Skyline Financial', 'Cameo Corporate',
                'Mas Services', 'Karvy Fintech', 'Beetal Financial',
                'Purva Sharegistry', 'Integrated Registry', 'CDSL Ventures',
            ]
            if not registrar:
                for kr in known_registrars:
                    if kr.lower() in full_text.lower():
                        registrar = kr; break

            if registrar:
                # Clean up — remove extra lines/text
                registrar = registrar.split('\n')[0].split('Phone')[0].split('Email')[0].strip()
                ipo['registrar'] = registrar
                print(f"[detail] registrar={registrar}")

            # ══════════════════════════════════════════════════════════════════
            # AUM — for REITs and InvITs (Assets Under Management)
            # ══════════════════════════════════════════════════════════════════
            aum_m = _re.search(
                r'(?:aum|assets?\s*under\s*management)[^₹\d]*[₹\s]*([\d,]+\.?\d*)\s*(?:cr|crore)?',
                full_text, _re.IGNORECASE)
            if aum_m:
                try:
                    aum_val = float(aum_m.group(1).replace(',',''))
                    if aum_val > 0:
                        ipo['aum'] = aum_val
                        print(f"[detail] aum={aum_val}")
                except: pass

            # ══════════════════════════════════════════════════════════════════
            # LISTING DATE — table or text
            # ══════════════════════════════════════════════════════════════════
            # Try key-value tables first
            for tbl in soup.select('table'):
                for row in tbl.select('tr'):
                    cells = row.select('td,th')
                    if len(cells) >= 2:
                        k = cells[0].get_text(strip=True).lower()
                        v = cells[1].get_text(strip=True)
                        if 'listing' in k and ('date' in k or 'day' in k):
                            if any(m in v for m in ['Jan','Feb','Mar','Apr','May','Jun',
                                                     'Jul','Aug','Sep','Oct','Nov','Dec',
                                                     '2025','2026','2027']):
                                ipo['est_listing'] = v
                                break
            # Text fallback
            if not ipo.get('est_listing'):
                lm = _re.search(
                    r'listing\s*(?:date|day)?\s*[:\-–]?\s*(\w+\s+\d{1,2},?\s*\d{4}|\d{1,2}\s+\w+\s+\d{4})',
                    full_text, _re.IGNORECASE)
                if lm:
                    ipo['est_listing'] = lm.group(1).strip()

            # ══════════════════════════════════════════════════════════════════
            # SUBSCRIPTION — dedicated page first, then text fallback
            # URL: ipowatch.in/{slug}-ipo-subscription-status/
            # ══════════════════════════════════════════════════════════════════
            def _extract_sub_from_text(txt):
                """Try regex patterns to extract total subscription times from text"""
                sub_patterns = [
                    r'total\s*subscription[^0-9]*(\d+\.?\d*)\s*(?:times|x)',
                    r'overall\s*(?:subscription|subscribed)[^0-9]*(\d+\.?\d*)\s*(?:times|x)?',
                    r'subscribed\s*(\d+\.?\d*)\s*(?:times|x)',
                    r'total\s*(?:issue\s*)?subscribed[^0-9]*(\d+\.?\d*)',
                ]
                for pat in sub_patterns:
                    sm = _re.search(pat, txt, _re.IGNORECASE)
                    if sm:
                        try:
                            sv = float(sm.group(1))
                            if 0 < sv <= 5000:
                                return sv
                        except: pass
                return None

            if not ipo.get('subscription'):
                company_name_raw = ipo.get('company', '')
                name_lower = company_name_raw.lower()
                name_words = [w for w in name_lower.split() if len(w) > 3]

                # ── Step 1: Chittorgarh subscription list page (static HTML) ──
                # URL: chittorgarh.com/report/ipo-subscription-status-live-bidding-data-bse-nse/21/
                try:
                    cg_sub_url = "https://www.chittorgarh.com/report/ipo-subscription-status-live-bidding-data-bse-nse/21/"
                    rc = requests.get(cg_sub_url, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0',
                        'Referer': 'https://www.chittorgarh.com/',
                    }, timeout=15)
                    print(f"[sub-cg] status={rc.status_code}")
                    if rc.status_code == 200:
                        csoup = _BS(rc.text, 'html.parser')
                        for tbl in csoup.select('table'):
                            ths = [th.get_text(strip=True).lower() for th in tbl.select('th')]
                            # Find table with company + subscription columns
                            has_name = any(w in ' '.join(ths) for w in ['company','ipo','stock','issue'])
                            has_sub  = any(w in ' '.join(ths) for w in ['sub','times','qib','total'])
                            if not (has_name and has_sub): continue
                            print(f"[sub-cg] table headers={ths}")

                            # Find name col and total/overall sub col
                            name_col = next((i for i,h in enumerate(ths) if any(w in h for w in ['company','ipo','stock','issue'])), 0)
                            sub_col  = next((i for i,h in enumerate(ths) if 'total' in h or 'overall' in h or ('sub' in h and 'qib' not in h and 'nii' not in h and 'retail' not in h)), None)
                            if sub_col is None:
                                sub_col = next((i for i,h in enumerate(ths) if 'sub' in h), None)

                            for row in tbl.select('tr')[1:]:
                                tds = row.select('td')
                                if len(tds) < 2: continue
                                row_name = tds[name_col].get_text(strip=True).lower() if name_col < len(tds) else ''
                                if not row_name: continue
                                # Fuzzy match
                                if name_words and any(w in row_name for w in name_words):
                                    if sub_col is not None and sub_col < len(tds):
                                        raw_s = tds[sub_col].get_text(strip=True)\
                                                .replace(',','').replace('x','').replace('X','').strip()
                                        try:
                                            sv2 = float(raw_s)
                                            if 0 < sv2 <= 5000:
                                                ipo['subscription'] = sv2
                                                print(f"[sub-cg] ✅ {company_name_raw}={sv2}x")
                                                break
                                        except: pass
                            if ipo.get('subscription'): break
                except Exception as cex:
                    print(f"[sub-cg] ❌ {cex}")

                # ── Step 2: ipowatch subscription page text (JS-rendered, try anyway) ──
                if not ipo.get('subscription'):
                    try:
                        slug = _re.sub(r'[^a-z0-9]+', '-', company_name_raw.lower()).strip('-')
                        sub_url = f"https://ipowatch.in/{slug}-ipo-subscription-status/"
                        rs = requests.get(sub_url, headers=HEADERS, timeout=12)
                        print(f"[sub-ipowatch] status={rs.status_code}")
                        if rs.status_code == 200:
                            ssoup = _BS(rs.text, 'html.parser')
                            sfull = ssoup.get_text(' ')
                            # Try table (may be empty due to JS)
                            for stbl in ssoup.select('table'):
                                sths = [th.get_text(strip=True).lower() for th in stbl.select('th')]
                                if not any(w in ' '.join(sths) for w in ['subscri','day','category','qib','nii']): continue
                                for srow in stbl.select('tr'):
                                    scells = srow.select('td')
                                    if not scells: continue
                                    if any(w in scells[0].get_text(strip=True).lower() for w in ['total','overall','grand']):
                                        for sc in reversed(scells[1:]):
                                            raw_s = sc.get_text(strip=True)\
                                                       .replace(',','').replace('x','').replace('X','')\
                                                       .replace('–','').replace('-','').strip()
                                            if not raw_s: continue
                                            try:
                                                sv3 = float(raw_s)
                                                if 0 < sv3 <= 5000:
                                                    ipo['subscription'] = sv3
                                                    print(f"[sub-ipowatch] ✅ table={sv3}x")
                                                    break
                                            except: pass
                                        if ipo.get('subscription'): break
                                if ipo.get('subscription'): break
                            # Text fallback
                            if not ipo.get('subscription'):
                                sv4 = _extract_sub_from_text(sfull)
                                if sv4:
                                    ipo['subscription'] = sv4
                                    print(f"[sub-ipowatch] ✅ text={sv4}x")
                    except Exception as sex:
                        print(f"[sub-ipowatch] ❌ {sex}")


            # Step 3: NSE ipo-detail API — bidDetails se Total subscription fetch
            # Log se confirmed: ipo-detail returns bidDetails list with category rows
            # Structure: [{category, noOfApplications, noOfSharesBid, noOfTimesOverall, ...}, ...]
            if not ipo.get('subscription'):
                try:
                    company_name_raw = ipo.get('company', '')
                    name_lower_n = company_name_raw.lower()
                    name_words_n = [w for w in name_lower_n.split() if len(w) > 3]

                    # Warm up NSE session
                    NSE_SESSION.get("https://www.nseindia.com", timeout=6)
                    NSE_SESSION.get("https://www.nseindia.com/market-data/all-upcoming-issues-ipo", timeout=6)

                    # Step 3a: Get symbol — try current + upcoming
                    nse_symbol = None
                    for _sym_url in [
                        "https://www.nseindia.com/api/ipo-current-issue",
                        "https://www.nseindia.com/api/ipo-upcoming-issue",
                    ]:
                        try:
                            r_curr = NSE_SESSION.get(_sym_url, timeout=10)
                            if r_curr.status_code != 200: continue
                            curr_items = r_curr.json()
                            if not isinstance(curr_items, list):
                                curr_items = curr_items.get('data', [])
                            for ci in (curr_items or []):
                                cname = str(ci.get('companyName', ci.get('symbol', ''))).lower()
                                if name_words_n and any(w in cname for w in name_words_n):
                                    nse_symbol = ci.get('symbol', '')
                                    print(f"[sub-nse] matched symbol={nse_symbol} for {company_name_raw}")
                                    break
                            if nse_symbol: break
                        except: pass

                    # Step 3b: ipo-detail → bidDetails → Total row → noOfTimesOverall
                    if nse_symbol:
                        try:
                            rb = NSE_SESSION.get(
                                f"https://www.nseindia.com/api/ipo-detail?symbol={nse_symbol}",
                                timeout=10)
                            print(f"[sub-nse] ipo-detail → {rb.status_code}")
                            if rb.status_code == 200 and rb.text.strip():
                                bdata = rb.json()
                                bid_rows = bdata.get('bidDetails', [])
                                print(f"[sub-nse] bidDetails rows={len(bid_rows)}, sample_keys={list(bid_rows[0].keys()) if bid_rows else []}")

                                def _parse_bid_rows(rows):
                                    """
                                    NSE bidDetails structure (confirmed from log):
                                    Each row has 'category' and subscription fields.
                                    We want the Total/Overall row's noOfTimesOverall.
                                    
                                    Known field names for times subscribed:
                                    noOfTimesOverall, noOfTimesTotal, timesSubscribed,
                                    subTimes, totalTimes, overallTimes, subscription
                                    
                                    IMPORTANT: Do NOT use noOfSharesBid or noOfApplications —
                                    those are raw counts, not subscription multiples.
                                    """
                                    sub_fields = [
                                        'noOfTimesOverall', 'noOfTimesTotal', 'timesSubscribed',
                                        'subTimes', 'totalTimes', 'overallTimes',
                                        'noOfTimesSubscription', 'totalSubscriptionTimes',
                                    ]
                                    # First pass: look for Total/Overall category row
                                    for row in rows:
                                        cat_val = str(row.get('category', row.get('investorCategory', ''))).lower()
                                        if any(w in cat_val for w in ['total', 'overall', 'grand', 'all']):
                                            for sf in sub_fields:
                                                try:
                                                    v = float(str(row.get(sf, 0)).replace(',','').replace('x',''))
                                                    if 0.01 <= v <= 5000:
                                                        print(f"[sub-nse] ✅ bidDetails Total row field={sf} v={v}x")
                                                        return v
                                                except: pass
                                            # Try any key with 'times' in name
                                            for k, v in row.items():
                                                if 'times' in k.lower() or 'subscri' in k.lower():
                                                    try:
                                                        fv = float(str(v).replace(',','').replace('x',''))
                                                        if 0.01 <= fv <= 5000:
                                                            print(f"[sub-nse] ✅ bidDetails Total row key={k} v={fv}x")
                                                            return fv
                                                    except: pass
                                    # Second pass: sum category rows if no total row
                                    # (sometimes total row is absent — only QIB/NII/RII rows)
                                    # In that case, use max value (most subscribed category proxy)
                                    candidates = []
                                    for row in rows:
                                        for sf in sub_fields:
                                            try:
                                                v = float(str(row.get(sf, 0)).replace(',','').replace('x',''))
                                                if 0.01 <= v <= 5000: candidates.append(v)
                                            except: pass
                                    if candidates:
                                        # Average of category rows ≈ overall (weighted equally)
                                        avg_v = sum(candidates) / len(candidates)
                                        print(f"[sub-nse] ℹ️ No Total row, using avg of {len(candidates)} cats={avg_v:.2f}x")
                                        return avg_v
                                    return None

                                sv5 = _parse_bid_rows(bid_rows)
                                if sv5:
                                    ipo['subscription'] = sv5
                                    print(f"[sub-nse] ✅ {company_name_raw}={sv5}x")
                        except Exception as be:
                            print(f"[sub-nse] ipo-detail parse error: {be}")
                            import traceback; traceback.print_exc()

                        # Step 3c: Fallback to other endpoints if bidDetails gave nothing
                        if not ipo.get('subscription'):
                            for burl in [
                                f"https://www.nseindia.com/api/ipo-subscription?symbol={nse_symbol}",
                                f"https://www.nseindia.com/api/ipo-bid-details?symbol={nse_symbol}",
                            ]:
                                try:
                                    rb2 = NSE_SESSION.get(burl, timeout=10)
                                    ep2 = burl.split('?')[0].split('/')[-1]
                                    print(f"[sub-nse] {ep2} → {rb2.status_code}")
                                    if rb2.status_code != 200 or not rb2.text.strip(): continue
                                    bd2 = rb2.json()
                                    # Only look for safe 'times' fields — skip shares/amounts
                                    def _safe_times(d, depth=0):
                                        if depth > 4: return None
                                        if isinstance(d, dict):
                                            for k, v in d.items():
                                                kl = k.lower()
                                                # Only use fields that contain 'times' or 'subscri'
                                                # Explicitly skip: shares, amount, bid, application
                                                if any(bad in kl for bad in ['shares','amount','bid','application','noofshares','noofappli']): continue
                                                if any(good in kl for good in ['times','subscri']):
                                                    try:
                                                        fv = float(str(v).replace(',','').replace('x',''))
                                                        if 0.01 <= fv <= 5000: return fv
                                                    except: pass
                                                r2 = _safe_times(v, depth+1)
                                                if r2: return r2
                                        elif isinstance(d, list):
                                            for item in d[:10]:
                                                r2 = _safe_times(item, depth+1)
                                                if r2: return r2
                                        return None
                                    sv6 = _safe_times(bd2)
                                    if sv6:
                                        ipo['subscription'] = sv6
                                        print(f"[sub-nse] ✅ {ep2} {company_name_raw}={sv6}x")
                                        break
                                except Exception as be2:
                                    print(f"[sub-nse] {ep2} error: {be2}")

                except Exception as nex:
                    print(f"[sub-nse] ❌ {nex}")

            # Step 4: Fallback — main detail page text
            if not ipo.get('subscription'):
                sv6 = _extract_sub_from_text(full_text)
                if sv6:
                    ipo['subscription'] = sv6
                    print(f"[detail] subscription={sv6} (text fallback)")

            # ══════════════════════════════════════════════════════════════════
            # GMP — from GMP-specific page or text patterns
            # ══════════════════════════════════════════════════════════════════
            # First try dedicated GMP table
            for tbl in soup.select('table'):
                ths = [th.get_text(strip=True).lower() for th in tbl.select('th')]
                if any('gmp' in h or 'grey' in h for h in ths):
                    gi = next((i for i,h in enumerate(ths) if 'gmp' in h or 'grey' in h), None)
                    for row in tbl.select('tr')[1:]:
                        tds = row.select('td')
                        if gi is not None and gi < len(tds):
                            raw_g = tds[gi].get_text(strip=True)\
                                    .replace('₹','').replace('+','').replace(',','').strip()
                            nums = _re.findall(r'-?[\d.]+', raw_g)
                            for n in nums:
                                gv = _safe_gmp(n)
                                if gv is not None:
                                    ipo['gmp'] = gv
                                    break
                        if ipo.get('gmp') is not None: break
                    if ipo.get('gmp') is not None: break

            # Text-based GMP (only short numbers — max 4 digits before decimal)
            if ipo.get('gmp') is None:
                for pat in [
                    r'(?:today\'?s?\s*)?gmp\s*(?:is\s*)?[₹\s]*([-+]?\d{1,4})',
                    r'grey\s*market\s*premium\s*(?:is\s*)?[₹\s]*([-+]?\d{1,4})',
                ]:
                    gm = _re.search(pat, full_text, _re.IGNORECASE)
                    if gm:
                        gv = _safe_gmp(gm.group(1))
                        if gv is not None:
                            ipo['gmp'] = gv
                            print(f"[detail] gmp from text={gv}")
                            break

            # ══════════════════════════════════════════════════════════════════
            # GMP FALLBACK — ipowatch dedicated GMP page
            # URL pattern: ipowatch.in/<slug>-ipo-gmp-grey-market-premium/
            # ══════════════════════════════════════════════════════════════════
            if ipo.get('gmp') is None:
                try:
                    slug = _re.sub(r'[^a-z0-9]+', '-', ipo.get('company','').lower()).strip('-')
                    gmp_url = f"https://ipowatch.in/{slug}-ipo-gmp-grey-market-premium/"
                    rg = requests.get(gmp_url, headers=HEADERS, timeout=12)
                    print(f"[gmp-page] {ipo.get('company','')} → {rg.status_code}")
                    if rg.status_code == 200:
                        gsoup = _BS(rg.text, 'html.parser')
                        gfull = gsoup.get_text(' ')
                        # Look for GMP table first
                        for gtbl in gsoup.select('table'):
                            gths = [th.get_text(strip=True).lower() for th in gtbl.select('th')]
                            if any('gmp' in h or 'grey' in h for h in gths):
                                gi2 = next((i for i,h in enumerate(gths) if 'gmp' in h), None)
                                # Get latest row (first data row = most recent date)
                                for grow in gtbl.select('tr')[1:]:
                                    gtds = grow.select('td')
                                    if gi2 is not None and gi2 < len(gtds):
                                        raw_g2 = gtds[gi2].get_text(strip=True)\
                                                .replace('₹','').replace('+','').replace(',','').replace('-','').strip()
                                        if raw_g2 and raw_g2 != '–':
                                            nums2 = _re.findall(r'[\d.]+', raw_g2)
                                            for n2 in nums2:
                                                gv2 = _safe_gmp(n2)
                                                if gv2 is not None:
                                                    ipo['gmp'] = gv2
                                                    print(f"[gmp-page] gmp={gv2}")
                                                    break
                                    if ipo.get('gmp') is not None: break
                                if ipo.get('gmp') is not None: break
                        # Text fallback on GMP page
                        if ipo.get('gmp') is None:
                            for gpat in [
                                r'gmp\s*(?:is\s*)?[₹\s]*([-+]?\d{1,4})',
                                r'grey\s*market\s*premium[^₹\d]*([-+]?\d{1,4})',
                            ]:
                                gm2 = _re.search(gpat, gfull, _re.IGNORECASE)
                                if gm2:
                                    gv2 = _safe_gmp(gm2.group(1))
                                    if gv2 is not None:
                                        ipo['gmp'] = gv2
                                        print(f"[gmp-page] gmp from text={gv2}")
                                        break
                except Exception as gex:
                    print(f"[gmp-page] ❌ {gex}")

        except Exception as ex:
            print(f"[detail] ❌ {ipo.get('company','')} → {ex}")
            import traceback; traceback.print_exc()

    def _ipo_on_row_click(self, ipo, row_frame):
        """When left list row is clicked — fetch detail then show"""
        for name, rf in self._ipo_row_btns.items():
            try:
                col = '#1D1040' if name == ipo['company'] else CARD2
                rf.config(bg=col)
                for c in rf.winfo_children(): c.config(bg=col)
            except: pass

        self._ipo_selected = ipo

        if not ipo.get('_detail_fetched'):
            # Show loading immediately
            for w in self._ipo_right.winfo_children(): w.destroy()
            tk.Label(self._ipo_right,
                     text=f"⏳ Loading details...",
                     font=('Arial', 11), bg=BG, fg=SUBTEXT,
                     justify='center').pack(expand=True)
            def _bg():
                self._ipo_fetch_detail_page(ipo)
                ipo['_detail_fetched'] = True
                self.root.after(0, lambda: self._ipo_show_detail(ipo))
                # Left list score badge refresh karo — detail fetch ke baad score accurate hoga
                self.root.after(50, lambda: self._ipo_refresh_row_score(ipo))
            threading.Thread(target=_bg, daemon=True).start()
        else:
            self._ipo_show_detail(ipo)

    def _ipo_refresh_row_score(self, ipo):
        """Left list me iss IPO ka score badge refresh karo after detail fetch"""
        try:
            row_f = self._ipo_row_btns.get(ipo['company'])
            if not row_f or not row_f.winfo_exists(): return
            score, _ = self._calc_ipo_score(ipo)
            if score >= 7:   sbadge_col, sbadge_txt = GREEN,  f"{score}/10"
            elif score >= 5: sbadge_col, sbadge_txt = YELLOW, f"{score}/10"
            elif score >= 3: sbadge_col, sbadge_txt = ORANGE, f"{score}/10"
            else:            sbadge_col, sbadge_txt = RED,    f"{score}/10"
            # Find score label inside row — it's the Label with bg matching a badge color
            for child in row_f.winfo_children():
                for gc in child.winfo_children():
                    try:
                        if gc.winfo_class() == 'Frame':
                            for ggc in gc.winfo_children():
                                if ggc.winfo_class() == 'Label' and '/10' in (ggc.cget('text') or ''):
                                    ggc.config(text=sbadge_txt, bg=sbadge_col)
                                    return
                        if gc.winfo_class() == 'Label' and '/10' in (gc.cget('text') or ''):
                            gc.config(text=sbadge_txt, bg=sbadge_col)
                            return
                    except: pass
        except: pass

    def _ipo_show_detail(self, ipo):
        """Render right panel with IPO full details + score + 2 buttons"""
        for w in self._ipo_right.winfo_children(): w.destroy()

        # Scrollable right panel
        rc = tk.Canvas(self._ipo_right, bg=BG, highlightthickness=0)
        rsb = ttk.Scrollbar(self._ipo_right, orient='vertical', command=rc.yview)
        rsb.pack(side='right', fill='y')
        rc.pack(fill='both', expand=True)
        rc.configure(yscrollcommand=rsb.set)
        rc.bind('<MouseWheel>', lambda e: rc.yview_scroll(-1*(e.delta//120), 'units'))

        con = tk.Frame(rc, bg=BG)
        con.bind('<Configure>', lambda e: rc.configure(scrollregion=rc.bbox('all')))
        rc.create_window((0,0), window=con, anchor='nw', tags='rcon')
        rc.bind('<Configure>', lambda e: rc.itemconfig('rcon', width=e.width))

        score, reasons = self._calc_ipo_score(ipo)

        # Score styling
        if score >= 7:   sc, verdict = GREEN,  "✅ APPLY karo!"
        elif score >= 5: sc, verdict = YELLOW, "⚠️ Consider karo"
        elif score >= 3: sc, verdict = ORANGE, "⚠️ Risky hai"
        else:            sc, verdict = RED,    "❌ Skip karo"

        status = ipo.get('status', '')
        sbadge_col = {'Open': GREEN, 'Upcoming': YELLOW, 'Closed': '#888'}.get(status, SUBTEXT)

        # ── TOP CARD: Name + Score ────────────────────────────────────────────
        top_card = tk.Frame(con, bg=CARD, pady=12,
                            highlightbackground=sc, highlightthickness=2)
        top_card.pack(fill='x', padx=10, pady=(10,4))

        top_inner = tk.Frame(top_card, bg=CARD); top_inner.pack(fill='x', padx=12)

        # Left: company name + badges
        lf = tk.Frame(top_inner, bg=CARD); lf.pack(side='left', fill='x', expand=True)

        badge_row = tk.Frame(lf, bg=CARD); badge_row.pack(anchor='w', pady=(0,4))
        tk.Label(badge_row, text=f" {status} ", font=('Arial', 8, 'bold'),
                 bg=sbadge_col, fg='black' if status=='Upcoming' else 'white',
                 padx=4, pady=1).pack(side='left', padx=(0,4))
        cat = ipo.get('category', '')
        cat_col = ACCENT if cat=='Mainboard' else ORANGE if cat=='SME' else '#888'
        tk.Label(badge_row, text=f" {cat} ", font=('Arial', 8, 'bold'),
                 bg=cat_col, fg='white', padx=4, pady=1).pack(side='left')

        tk.Label(lf, text=ipo['company'], font=('Arial', 14, 'bold'),
                 bg=CARD, fg=TEXT, wraplength=400, anchor='w', justify='left').pack(anchor='w')

        # Price band
        if ipo.get('price_band'):
            tk.Label(lf, text=f"💰 Price: {ipo['price_band']}",
                     font=('Arial', 10), bg=CARD, fg=ACCENT).pack(anchor='w', pady=(4,0))

        # Right: score
        rf = tk.Frame(top_inner, bg=CARD); rf.pack(side='right', padx=(12,0))
        score_box = tk.Frame(rf, bg=sc, padx=18, pady=10); score_box.pack()
        tk.Label(score_box, text=f"{score}", font=('Arial', 22, 'bold'),
                 bg=sc, fg='black').pack()
        tk.Label(score_box, text="/ 10", font=('Arial', 10),
                 bg=sc, fg='black').pack()
        tk.Label(rf, text=verdict, font=('Arial', 9, 'bold'),
                 bg=CARD, fg=sc).pack(pady=(6,0))

        # ── DATES ROW ──────────────────────────────────────────────────────────
        dates_f = tk.Frame(con, bg=CARD2); dates_f.pack(fill='x', padx=10, pady=2)
        dates_inner = tk.Frame(dates_f, bg=CARD2); dates_inner.pack(pady=8)
        for lbl, val, col in [
            ("📅 Open Date",  ipo.get('open_date','TBD'),  GREEN),
            ("  →  ", "", SUBTEXT),
            ("📅 Close Date", ipo.get('close_date','TBD'), RED),
        ]:
            tk.Label(dates_inner, text=lbl, font=('Arial', 8), bg=CARD2, fg=SUBTEXT).pack(side='left')
            tk.Label(dates_inner, text=val,  font=('Arial', 10, 'bold'), bg=CARD2, fg=col).pack(side='left', padx=(0,12))

        # ── INFO GRID ─────────────────────────────────────────────────────────
        info_f = tk.Frame(con, bg=BG); info_f.pack(fill='x', padx=10, pady=4)

        gmp = ipo.get('gmp')
        pn  = ipo.get('price_num', 0)
        if gmp is not None and pn:
            gp = (gmp/pn)*100
            gmp_str = f"₹{gmp:+.0f}  ({gp:+.1f}%)"
            gmp_col = GREEN if gmp>0 else RED
        else:
            gmp_str, gmp_col = "N/A", SUBTEXT

        sub = ipo.get('subscription')
        if sub:
            sub_str = f"{sub:.1f}x subscribed"
            sub_col = GREEN if sub>10 else YELLOW if sub>2 else RED
        else:
            sub_str, sub_col = "N/A", SUBTEXT

        est = ipo.get('est_listing','')

        grid_items = [
            ("📈 GMP (Grey Market)",     gmp_str,                                    gmp_col),
            ("📊 Subscription",          sub_str,                                    sub_col),
            ("🏢 Issue Size",            f"₹{ipo['issue_size']:.0f} Cr" if ipo.get('issue_size') else 'N/A', TEXT),
            ("📦 Lot Size",              f"{ipo['lot_size']} shares" if ipo.get('lot_size') else 'N/A', SUBTEXT),
            ("📋 Registrar",             ipo.get('registrar') or 'N/A',             SUBTEXT),
            ("🎯 Est. Listing",          est or 'N/A',                               ACCENT),
        ]
        # AUM — for REIT/InvIT
        if ipo.get('aum'):
            grid_items.append(("🏦 AUM", f"₹{ipo['aum']:,.0f} Cr", '#4FC3F7'))

        for i, (lbl, val, col) in enumerate(grid_items):
            r_i, c_i = divmod(i, 2)
            cell = tk.Frame(info_f, bg=CARD2, padx=10, pady=8)
            cell.grid(row=r_i, column=c_i, padx=3, pady=3, sticky='nsew')
            info_f.columnconfigure(c_i, weight=1)
            tk.Label(cell, text=lbl, font=('Arial', 8), bg=CARD2, fg=SUBTEXT).pack(anchor='w')
            tk.Label(cell, text=val, font=('Arial', 10, 'bold'), bg=CARD2, fg=col,
                     wraplength=220, anchor='w', justify='left').pack(anchor='w')

        # ── SCORE BREAKDOWN ───────────────────────────────────────────────────
        sb_f = tk.Frame(con, bg='#080B14', pady=8); sb_f.pack(fill='x', padx=10, pady=4)
        tk.Label(sb_f, text="📊 Score Breakdown",
                 font=('Arial', 9, 'bold'), bg='#080B14', fg='#C678FF').pack(anchor='w', padx=10, pady=(0,4))
        grid_sb = tk.Frame(sb_f, bg='#080B14'); grid_sb.pack(fill='x', padx=10)
        for i, reason in enumerate(reasons):
            r_i, c_i = divmod(i, 2)
            rc2 = GREEN if reason.startswith('✅') else RED if reason.startswith('❌') \
                  else YELLOW if reason.startswith('⚠️') else SUBTEXT
            tk.Label(grid_sb, text=reason, font=('Arial', 8),
                     bg='#080B14', fg=rc2, anchor='w', wraplength=250, justify='left'
                     ).grid(row=r_i, column=c_i, sticky='w', padx=6, pady=2)
            grid_sb.columnconfigure(c_i, weight=1)

        # ── SCORE LEGEND ──────────────────────────────────────────────────────
        legend_f = tk.Frame(con, bg='#0A0A18', pady=6); legend_f.pack(fill='x', padx=10, pady=(0,4))
        tk.Label(legend_f, text="ℹ️ Score logic:  GMP>20%(+2)  GMP>0%(+1)  Sub>10x(+2)  Sub>2x(+1)  Price≤₹500(+1)  Mainboard(+1)  Size>500Cr(+1)  Good Reg(+1)",
                 font=('Arial', 7), bg='#0A0A18', fg='#555', wraplength=560,
                 justify='left').pack(anchor='w', padx=10)

        # ── 2 ACTION BUTTONS ──────────────────────────────────────────────────
        tk.Frame(con, bg=BORDER, height=1).pack(fill='x', padx=10, pady=(8,0))
        btn_f = tk.Frame(con, bg=BG, pady=10); btn_f.pack(fill='x', padx=10)

        # Build URLs
        detail_url = ipo.get('detail_url', '')
        if not detail_url:
            slug = re.sub(r'[^a-z0-9]+', '-', ipo['company'].lower()).strip('-')
            detail_url = f"https://ipowatch.in/{slug}-ipo-date-review-price-allotment-details/"

        company_q  = ipo['company'].replace(' ', '%20')
        # NSE Corporate Filings — Annual Reports, financials after listing
        nse_filings_url = (
            f"https://www.nseindia.com/companies-listing/corporate-filings-annual-reports"
        )
        # NSE Search for this company
        nse_search_url = f"https://www.nseindia.com/get-quotes/equity?symbol={re.sub(r'[^A-Z0-9]','',ipo['company'].upper())[:10]}"

        # ── Button 1: IPO Full Details → ipowatch.in ─────────────────────────
        btn1 = tk.Frame(btn_f, bg='#0A1A35', pady=0)
        btn1.pack(fill='x', pady=4)
        tk.Button(btn1,
                  text="📋  IPO Full Details  →  ipowatch.in",
                  font=('Arial', 10, 'bold'), bg='#0A1A35', fg='#4FC3F7',
                  relief='flat', padx=14, pady=12, cursor='hand2', anchor='w',
                  command=lambda u=detail_url: webbrowser.open(u)
                  ).pack(fill='x')
        tk.Label(btn1,
                 text="  Review • Price • Allotment • GMP • Listing details",
                 font=('Arial', 8), bg='#0A1A35', fg=SUBTEXT
                 ).pack(anchor='w', padx=14, pady=(0,4))

        # ── Button 2: NSE Annual Reports & Corporate Filings ─────────────────
        btn2 = tk.Frame(btn_f, bg='#0A200A', pady=0)
        btn2.pack(fill='x', pady=4)
        tk.Button(btn2,
                  text="📊  NSE Annual Reports & Filings",
                  font=('Arial', 10, 'bold'), bg='#0A200A', fg=GREEN,
                  relief='flat', padx=14, pady=12, cursor='hand2', anchor='w',
                  command=lambda u=nse_filings_url: webbrowser.open(u)
                  ).pack(fill='x')
        tk.Label(btn2,
                 text="  NSE pe list hone ke baad Annual Reports milenge",
                 font=('Arial', 8), bg='#0A200A', fg=SUBTEXT
                 ).pack(anchor='w', padx=14, pady=(0,4))

        # ── Registrar info tooltip ────────────────────────────────────────────
        reg = ipo.get('registrar','')
        if reg:
            reg_f = tk.Frame(btn_f, bg='#0A0A18', pady=6)
            reg_f.pack(fill='x', pady=(0,4))
            tk.Label(reg_f,
                     text=f"ℹ️  Registrar kya karta hai?",
                     font=('Arial', 8, 'bold'), bg='#0A0A18', fg=SUBTEXT
                     ).pack(anchor='w', padx=10)
            tk.Label(reg_f,
                     text=f"  IPO allotment aur refund {reg} handle karta hai.\n"
                          f"  Allotment status check karne ke liye inki website pe jao.",
                     font=('Arial', 8), bg='#0A0A18', fg='#666',
                     justify='left', wraplength=520
                     ).pack(anchor='w', padx=10)
            # Registrar website button
            reg_urls = {
                'kfin': 'https://ipostatus.kfintech.com/',
                'link intime': 'https://linkintime.co.in/MIPO/Ipoallotment.html',
                'bigshare': 'https://www.bigshareonline.com/IPOStatus.aspx',
                'skyline': 'https://www.skylinerta.com/ipo.php',
                'cameo': 'https://www.cameoindia.com/ipo/',
            }
            reg_lower = reg.lower()
            reg_url = next((v for k,v in reg_urls.items() if k in reg_lower), None)
            if reg_url:
                tk.Button(reg_f,
                          text=f"🔗  Check Allotment Status — {reg}",
                          font=('Arial', 8, 'bold'), bg='#0A1A20', fg='#4FC3F7',
                          relief='flat', padx=10, pady=6, cursor='hand2', anchor='w',
                          command=lambda u=reg_url: webbrowser.open(u)
                          ).pack(fill='x', padx=10, pady=(4,0))

    def _welcome(self):
        for w in self.main.winfo_children(): w.destroy()
        self._hm_tabs    = {}
        self._hm_content = None
        self._nav_stack  = []   # Home pe aate hi history clear
        self._current_chartink = None  # Chartink state bhi clear

        # Tab bar — Home + 4 index categories
        tab_bar = tk.Frame(self.main, bg=CARD); tab_bar.pack(fill='x')
        tabs = [
            ('home',      '🏠 Home',           '#1A2A4A'),
            ('broad',     '📊 Broad Market',    '#1A3060'),
            ('sectoral',  '🏭 Sectoral',        '#2D1A50'),
            ('thematic',  '🎯 Thematic',        '#0D3030'),
            ('strategy',  '⚙️ Strategy',       '#3D1A00'),
        ]
        for key, lbl, color in tabs:
            b = tk.Button(tab_bar, text=lbl, font=('Arial', 9, 'bold'),
                          relief='flat', padx=16, pady=9, cursor='hand2',
                          command=lambda k=key: self._show_tab(k))
            b.pack(side='left', padx=1)
            self._hm_tabs[key] = (b, color)

        # Thin accent line under tab bar
        tk.Frame(self.main, bg=BORDER, height=1).pack(fill='x')

        # Content area
        self._hm_content = tk.Frame(self.main, bg=BG)
        self._hm_content.pack(fill='both', expand=True)

        self._show_tab('home')

    def _show_tab(self, key):
        """Switch center panel tab"""
        active_colors = {
            'home':     (ACCENT,   '#0D1A35'),
            'broad':    ('#3D7EFF', '#0A1535'),
            'sectoral': ('#9B59B6', '#1A0D35'),
            'thematic': ('#1ABC9C', '#0A2525'),
            'strategy': ('#E67E22', '#2A1000'),
        }
        for k, (b, _) in self._hm_tabs.items():
            if k == key:
                ac, bg_c = active_colors[k]
                b.config(bg=bg_c, fg=ac,
                         font=('Arial', 9, 'bold'),
                         relief='flat', bd=0,
                         highlightthickness=2,
                         highlightbackground=ac,
                         highlightcolor=ac)
            else:
                b.config(bg=CARD, fg=SUBTEXT,
                         font=('Arial', 9),
                         relief='flat', bd=0,
                         highlightthickness=0)

        for w in self._hm_content.winfo_children(): w.destroy()

        if key == 'home':
            self._show_home()
        else:
            lf = tk.Frame(self._hm_content, bg=BG)
            lf.pack(fill='both', expand=True)
            tk.Label(lf, text="⏳ Loading indices...",
                     font=('Arial', 13), bg=BG, fg=SUBTEXT).pack(pady=80)
            threading.Thread(target=self._fetch_category_heatmap,
                             args=(key, key), daemon=True).start()

    def _fetch_category_heatmap(self, tab_key, cat):
        """Fetch all indices for a category and render as heatmap tiles"""
        all_rows = self._nse_fetch_all_indices()
        rows = [r for r in all_rows if r.get('cat') == cat]
        self.root.after(0, lambda: self._render_category_heatmap(tab_key, rows))

    def _render_category_heatmap(self, tab_key, rows):
        """Render index-level heatmap tiles — click → stock heatmap"""
        for w in self._hm_content.winfo_children(): w.destroy()

        titles = {'broad': '📊 Broad Market Indices', 'sectoral': '🏭 Sectoral Indices',
                  'thematic': '🎯 Thematic Indices',  'strategy': '⚙️ Strategy Indices'}
        title = titles.get(tab_key, '')

        if not rows:
            tk.Label(self._hm_content,
                     text="❌ Data load nahi hua — Refresh karo",
                     font=('Arial', 12), bg=BG, fg=RED).pack(pady=60)
            tk.Button(self._hm_content, text="🔄 Retry",
                      font=('Arial', 10), bg=BORDER, fg=ACCENT,
                      relief='flat', padx=14, pady=6, cursor='hand2',
                      command=lambda: self._show_tab(tab_key)).pack()
            return

        # Header
        hdr = tk.Frame(self._hm_content, bg=CARD)
        hdr.pack(fill='x', padx=6, pady=(6,4))
        tk.Label(hdr, text=f"{title}  ({len(rows)})",
                 font=('Arial', 12, 'bold'), bg=CARD, fg=ACCENT).pack(side='left', padx=10)
        tk.Button(hdr, text="🔄 Refresh", font=('Arial', 8),
                  bg=BORDER, fg=SUBTEXT, relief='flat', padx=8, pady=3, cursor='hand2',
                  command=lambda: self._show_tab(tab_key)).pack(side='right', padx=8)
        tk.Label(hdr, text="↑ Index click karo → Stocks dekhो",
                 font=('Arial', 8), bg=CARD, fg=SUBTEXT).pack(side='right', padx=8)

        # Scrollable tile area
        outer = tk.Frame(self._hm_content, bg=BG); outer.pack(fill='both', expand=True)
        vsb = ttk.Scrollbar(outer, orient='vertical'); vsb.pack(side='right', fill='y')
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0, yscrollcommand=vsb.set)
        canvas.pack(fill='both', expand=True)
        vsb.config(command=canvas.yview)
        canvas.bind('<MouseWheel>', lambda e: canvas.yview_scroll(-1*(e.delta//120), 'units'))

        tf = tk.Frame(canvas, bg=BG)
        canvas.create_window((0,0), window=tf, anchor='nw', tags='tf')
        tf.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfig('tf', width=e.width))

        def tile_color(chg):
            if   chg >=  3: return '#005000', '#FFFFFF'
            elif chg >=  1: return '#1B5E20', '#FFFFFF'
            elif chg >=  0: return '#2E7D32', '#FFFFFF'
            elif chg >= -1: return '#7B1A1A', '#FFFFFF'
            elif chg >= -3: return '#B71C1C', '#FFFFFF'
            else:           return '#4A0000', '#FFFFFF'

        rows_sorted = sorted(rows, key=lambda x: x['chg'], reverse=True)
        COLS = 4
        for i, row in enumerate(rows_sorted):
            name = row['name']
            chg  = row['chg']
            last = row['last']
            tile_bg, tile_fg = tile_color(chg)

            disp = name
            for pfx in ('NIFTY ', 'NIFTY500 '):
                if disp.upper().startswith(pfx):
                    disp = disp[len(pfx):]
                    break
            disp = disp.replace(' INDEX','').strip()
            if len(disp) > 16: disp = disp[:15] + '…'

            col = i % COLS; r_idx = i // COLS
            tile = tk.Frame(tf, bg=tile_bg, relief='flat',
                            highlightbackground='#222', highlightthickness=1)
            tile.grid(row=r_idx, column=col, padx=4, pady=4, sticky='nsew')
            tf.columnconfigure(col, weight=1, minsize=130)

            tk.Label(tile, text=disp, font=('Arial', 9, 'bold'),
                     bg=tile_bg, fg=tile_fg, wraplength=150,
                     justify='center').pack(pady=(10,2), padx=6)
            tk.Label(tile, text=f"₹{last:,.2f}" if last else "",
                     font=('Arial', 8), bg=tile_bg, fg=tile_fg).pack()
            tk.Label(tile, text=f"{chg:+.2f}%", font=('Arial', 11, 'bold'),
                     bg=tile_bg, fg=tile_fg).pack(pady=(2,10))

            # Click → stock heatmap of this index
            for w in [tile] + tile.winfo_children():
                w.bind('<Button-1>', lambda e, n=name: self._show_index_heatmap(n))
            tile.bind('<Enter>', lambda e, t=tile, bg=tile_bg: [
                t.config(bg='#1E1E3A')] + [c.config(bg='#1E1E3A') for c in t.winfo_children()])
            tile.bind('<Leave>', lambda e, t=tile, bg=tile_bg: [
                t.config(bg=bg)] + [c.config(bg=bg) for c in t.winfo_children()])

    def _show_home(self):
        """Center panel — Trade Log summary + search hint"""
        for w in self._hm_content.winfo_children(): w.destroy()

        outer = tk.Frame(self._hm_content, bg=BG)
        outer.pack(fill='both', expand=True)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(outer, bg=CARD, pady=10)
        hdr.pack(fill='x', padx=0)
        tk.Label(hdr, text="📒  My Trade Log",
                 font=('Arial', 14, 'bold'), bg=CARD, fg=TEXT).pack(side='left', padx=14)
        tk.Label(hdr, text="(Stock search karo → Notes tab → trade add karo)",
                 font=('Arial', 9), bg=CARD, fg=SUBTEXT).pack(side='left', padx=4)
        tk.Button(hdr, text="🔄 Refresh", font=('Arial', 8),
                  bg=BORDER, fg=ACCENT, relief='flat', padx=8, pady=4,
                  cursor='hand2', command=self._show_home).pack(side='right', padx=10)
        tk.Frame(outer, bg=BORDER, height=1).pack(fill='x')

        # ── Gather all trades ─────────────────────────────────────────────────
        all_trades = APP_DATA.get('trades', {})

        # Scrollable area
        scroll_outer = tk.Frame(outer, bg=BG)
        scroll_outer.pack(fill='both', expand=True)
        vsb = ttk.Scrollbar(scroll_outer, orient='vertical')
        vsb.pack(side='right', fill='y')
        canvas = tk.Canvas(scroll_outer, bg=BG, highlightthickness=0,
                           yscrollcommand=vsb.set)
        canvas.pack(fill='both', expand=True)
        vsb.config(command=canvas.yview)
        canvas.bind('<MouseWheel>',
                    lambda e: canvas.yview_scroll(-1*(e.delta//120), 'units'))
        con = tk.Frame(canvas, bg=BG)
        con.bind('<Configure>',
                 lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=con, anchor='nw', tags='con')
        canvas.bind('<Configure>',
                    lambda e: canvas.itemconfig('con', width=e.width))

        if not all_trades:
            # Empty state
            ef = tk.Frame(con, bg=BG); ef.pack(expand=True, pady=80)
            tk.Label(ef, text="📒", font=('Arial', 48), bg=BG).pack()
            tk.Label(ef, text="Abhi koi trade log nahi",
                     font=('Arial', 16, 'bold'), bg=BG, fg=TEXT).pack(pady=8)
            tk.Label(ef, text="Kisi bhi stock ka naam search karo → Notes tab → trade add karo",
                     font=('Arial', 10), bg=BG, fg=SUBTEXT).pack()
            tk.Label(ef, text="Ya upar tabs se Index → Stocks dekho",
                     font=('Arial', 10), bg=BG, fg=SUBTEXT).pack(pady=(4, 0))
            return

        # ── Column header ─────────────────────────────────────────────────────
        col_hdr = tk.Frame(con, bg='#0A0E1E')
        col_hdr.pack(fill='x', padx=8, pady=(10, 2))
        for txt, w2, anch in [
            ('Symbol',  10, 'w'), ('Type', 8, 'w'),
            ('Price',   10, 'w'), ('Qty',  7, 'w'),
            ('Date',    12, 'w'), ('Reason', 24, 'w'),
            ('P&L est.', 10, 'w'), ('',    5,  'w'),
        ]:
            tk.Label(col_hdr, text=txt, font=('Arial', 8, 'bold'),
                     bg='#0A0E1E', fg=SUBTEXT, width=w2, anchor=anch,
                     padx=6, pady=7).pack(side='left')
        tk.Frame(con, bg=BORDER, height=1).pack(fill='x', padx=8)

        # ── All trades — newest first per stock ───────────────────────────────
        # Flatten: [(sym, trade_dict), ...]  sorted by logged time desc
        flat = []
        for sym, trades in all_trades.items():
            for t in trades:
                flat.append((sym, t))
        # Sort by 'logged' field desc (if present)
        flat.sort(key=lambda x: x[1].get('logged', ''), reverse=True)

        row_idx = 0
        for sym, t in flat:
            row_bg = CARD if row_idx % 2 == 0 else CARD2
            trow = tk.Frame(con, bg=row_bg, cursor='hand2')
            trow.pack(fill='x', padx=8, pady=1)

            tc = GREEN if t['type'] == 'BUY' else RED if t['type'] == 'SELL' else YELLOW

            # Symbol — clickable → load stock
            sym_btn = tk.Button(
                trow, text=sym, font=('Arial', 10, 'bold'),
                bg=row_bg, fg=ACCENT, relief='flat', cursor='hand2', width=10, anchor='w',
                command=lambda s=sym: self._direct_load(s))
            sym_btn.pack(side='left', padx=6, pady=6)

            tk.Label(trow, text=t['type'], font=('Arial', 9, 'bold'),
                     bg=row_bg, fg=tc, width=8, anchor='w').pack(side='left', padx=4)
            tk.Label(trow, text=f"₹{t['price']}", font=('Arial', 9),
                     bg=row_bg, fg=TEXT, width=10, anchor='w').pack(side='left', padx=4)
            tk.Label(trow, text=t.get('qty', ''), font=('Arial', 9),
                     bg=row_bg, fg=TEXT, width=7, anchor='w').pack(side='left', padx=4)
            tk.Label(trow, text=t.get('date', ''), font=('Arial', 9),
                     bg=row_bg, fg=SUBTEXT, width=12, anchor='w').pack(side='left', padx=4)
            tk.Label(trow, text=t.get('reason', '')[:30], font=('Arial', 9),
                     bg=row_bg, fg=SUBTEXT, width=24, anchor='w').pack(side='left', padx=4)

            # P&L — fetch live price in bg
            pnl_lbl = tk.Label(trow, text="...", font=('Arial', 9, 'bold'),
                               bg=row_bg, fg=SUBTEXT, width=10, anchor='w')
            pnl_lbl.pack(side='left', padx=4)

            # Delete button
            def _del_trade(s=sym, trade=t):
                trades_list = APP_DATA.get('trades', {}).get(s, [])
                if trade in trades_list:
                    trades_list.remove(trade)
                    if not trades_list:
                        APP_DATA.get('trades', {}).pop(s, None)
                    _save_data(APP_DATA)
                self._show_home()

            tk.Button(trow, text='✕', font=('Arial', 8), bg=row_bg, fg=RED,
                      relief='flat', cursor='hand2', command=_del_trade,
                      width=4).pack(side='right', padx=6)

            # Hover effect
            def _hover_on(e, f=trow, lbs=trow.winfo_children()):
                f.config(bg='#1E1E3A')
            def _hover_off(e, f=trow, bg=row_bg):
                f.config(bg=bg)
            trow.bind('<Enter>', _hover_on)
            trow.bind('<Leave>', _hover_off)

            # Fetch live P&L in background (yfinance > Yahoo > NSE — most accurate)
            def _fetch_pnl(s=sym, trade=t, lbl=pnl_lbl, rbg=row_bg):
                try:
                    cur_p = fetch_best_live_price(s)
                    if cur_p and trade.get('price') and trade['type'] in ('BUY', 'SELL'):
                        ep  = float(trade['price'])
                        qty = float(trade.get('qty') or 1)
                        pnl = (float(cur_p) - ep) * qty * (1 if trade['type'] == 'BUY' else -1)
                        col = GREEN if pnl >= 0 else RED
                        txt = f"{'+'if pnl>=0 else ''}₹{pnl:.0f}"
                        self.root.after(0, lambda lb=lbl, t=txt, c=col: lb.config(text=t, fg=c))
                    else:
                        self.root.after(0, lambda lb=lbl: lb.config(text="—", fg=SUBTEXT))
                except:
                    self.root.after(0, lambda lb=lbl: lb.config(text="—", fg=SUBTEXT))

            threading.Thread(target=_fetch_pnl, daemon=True).start()
            row_idx += 1

        # ── Summary footer ────────────────────────────────────────────────────
        total_buys  = sum(1 for _, t in flat if t['type'] == 'BUY')
        total_sells = sum(1 for _, t in flat if t['type'] == 'SELL')
        tk.Frame(con, bg=BORDER, height=1).pack(fill='x', padx=8, pady=(8, 2))
        sf = tk.Frame(con, bg=CARD2, pady=8)
        sf.pack(fill='x', padx=8, pady=(0, 10))
        tk.Label(sf, text=f"Total: {len(flat)} trades  •  {total_buys} BUY  •  {total_sells} SELL",
                 font=('Arial', 9), bg=CARD2, fg=SUBTEXT).pack(side='left', padx=12)
        tk.Label(sf, text="↑ Symbol click → stock detail open hoga",
                 font=('Arial', 9), bg=CARD2, fg=SUBTEXT).pack(side='right', padx=12)

    def _quick(self, name):
        self.q.set(name); self._search()

    def _direct_load(self, sym):
        """Stock tile se seedha load — search bypass karke screener URL dhundho"""
        # Pehle current view ka state save karo nav stack mein
        if hasattr(self, '_current_chartink') and self._current_chartink:
            # Chartink list view se aa rahe hain
            ct = self._current_chartink
            self._nav_stack.append(('chartink_list', ct['rows'], ct['label'], ct['url']))
        else:
            # Index heatmap se aa rahe hain — index naam dhundho
            self._push_index_heatmap_state()
        self._loading(f"Loading {sym}...")
        threading.Thread(target=self._do_direct_load, args=(sym,), daemon=True).start()

    def _push_index_heatmap_state(self):
        """Current heatmap mein jo index dikh raha hai uska naam nav stack mein push karo"""
        try:
            if self._hm_content and self._hm_content.winfo_exists():
                for child in self._hm_content.winfo_children():
                    if isinstance(child, tk.Frame):
                        for subchild in child.winfo_children():
                            if isinstance(subchild, tk.Label):
                                txt = subchild.cget('text')
                                # Header label format: "📊 NIFTY MICROCAP250  (250 stocks)"
                                import re as _re
                                m = _re.match(r'📊\s+(.+?)\s+\(', txt)
                                if m:
                                    self._nav_stack.append(('index_heatmap', m.group(1).strip()))
                                    return
        except Exception:
            pass

    def _do_direct_load(self, sym):
        try:
            # Screener search karo symbol se
            res = search_stock(sym)
            url = None

            if res:
                sym_up = sym.upper().strip()
                # Pass 1: exact NSE symbol match (screener URL mein symbol hota hai)
                for r in res:
                    r_url = (r.get('url') or '').upper()
                    # URL format: /company/RELIANCE/ ya /company/TCS/
                    import re as _re
                    m = _re.search(r'/COMPANY/([^/]+)/', r_url)
                    if m and m.group(1) == sym_up:
                        url = r.get('url', '')
                        break
                # Pass 2: name contains symbol
                if not url:
                    for r in res:
                        name = (r.get('name') or '').upper()
                        if sym_up in name:
                            url = r.get('url', '')
                            break
                # Pass 3: first result
                if not url:
                    url = res[0].get('url', '')

            if url:
                full = f"https://www.screener.in{url}"
                data = fetch_stock(full)
                nse  = fetch_nse_live(sym)
                data['nse'] = nse
                self.root.after(0, lambda: self._show(data))
            else:
                self.root.after(0, lambda: self._error(f"'{sym}' screener pe nahi mila"))
        except Exception as e:
            err = str(e)
            self.root.after(0, lambda msg=err: self._error(f"Load failed!\n{msg}"))

    def _search(self):
        q = self.q.get().strip()
        if not q: return
        self._close_dd()
        self._loading("Searching...")
        threading.Thread(target=self._do_search, args=(q,), daemon=True).start()

    def _do_search(self, q):
        try:
            res = search_stock(q)
            self.root.after(0, lambda: self._show_results(res))
        except Exception as e:
            err = str(e)
            self.root.after(0, lambda msg=err: self._error(f"Search failed!\n{msg}"))

    def _show_results(self, results):
        self._welcome()          # pehle screen rebuild karo
        self._show_dd(results)   # phir dropdown dikhao

    def _load(self, url, name):
        self.q.set('')
        self._close_dd()
        self._loading(f"Loading {name}...")
        full = f"https://www.screener.in{url}"
        threading.Thread(target=self._do_load, args=(full,), daemon=True).start()

    def _do_load(self, url):
        try:
            data = fetch_stock(url)
            sym  = data.get('nse_symbol')
            nse  = fetch_nse_live(sym) if sym else {}
            data['nse'] = nse
            self.root.after(0, lambda: self._show(data))
        except Exception as e:
            err = str(e)
            self.root.after(0, lambda msg=err: self._error(f"Load failed!\n{msg}"))

    def _loading(self, msg="Loading..."):
        for w in self.main.winfo_children(): w.destroy()
        self._hm_content = None
        self._hm_tabs    = {}
        f = tk.Frame(self.main, bg=BG)
        f.pack(expand=True, pady=80)
        tk.Label(f, text="⏳", font=('Arial', 42), bg=BG).pack()
        tk.Label(f, text=msg, font=('Arial', 13), bg=BG, fg=SUBTEXT).pack(pady=8)

    def _error(self, msg):
        for w in self.main.winfo_children(): w.destroy()
        self._hm_content = None
        self._hm_tabs    = {}
        tb = tk.Frame(self.main, bg=BG); tb.pack(fill='x')
        tk.Button(tb, text="◀ Back", font=('Arial', 9, 'bold'),
                  bg=BORDER, fg=TEXT, relief='flat', padx=10, pady=4,
                  cursor='hand2', command=self._welcome
                  ).pack(side='left', padx=8, pady=4)
        tk.Button(tb, text="✕ Close", font=('Arial', 9),
                  bg=BORDER, fg=SUBTEXT, relief='flat', padx=10, pady=4,
                  cursor='hand2', command=self._welcome
                  ).pack(side='right', padx=8, pady=4)
        f = tk.Frame(self.main, bg=BG)
        f.pack(expand=True, pady=60)
        tk.Label(f, text="❌", font=('Arial', 40), bg=BG).pack()
        tk.Label(f, text=msg, font=('Arial', 11), bg=BG, fg=RED,
                 wraplength=440, justify='center').pack(pady=8)
        tk.Button(f, text="◀ Back to Home", font=('Arial', 10, 'bold'),
                  bg=BORDER, fg=ACCENT, relief='flat', padx=14, pady=6,
                  cursor='hand2', command=self._welcome
                  ).pack(pady=12)

    def _fetch_performance(self, sym, frame):
        """Fetch price returns via yfinance — 1D 1W 1M YTD 1Y 3Y 5Y MAX"""
        import datetime, math
        try:
            hist = yf.download(f"{sym}.NS", period="max", interval="1d",
                               auto_adjust=True, progress=False)
            if hist is None or hist.empty:
                ticker = yf.Ticker(f"{sym}.NS")
                hist   = ticker.history(period="max", auto_adjust=True, actions=False)
            if hist is None or hist.empty:
                raise ValueError("No data")

            # Flatten multi-index
            if hasattr(hist.columns, 'levels'):
                try: hist = hist['Close'].to_frame(name='Close')
                except: pass
            if 'Close' not in hist.columns and 'close' in hist.columns:
                hist = hist.rename(columns={'close': 'Close'})

            # ── Drop NaN rows — market band hone ke baad NaN aata hai ──────────
            hist = hist[['Close']].dropna()
            if hist.empty:
                raise ValueError("All NaN")

            try:
                hist.index = hist.index.tz_localize(None) if hist.index.tzinfo else hist.index
            except: pass

            today = datetime.date.today()

            # ep = last VALID close (not today if market closed)
            ep_val = float(hist['Close'].iloc[-1])
            if math.isnan(ep_val):
                raise ValueError("ep is NaN")

            def pct(start_date):
                try:
                    mask = hist.index.date >= start_date
                    sub  = hist.loc[mask, 'Close'].dropna()
                    if sub.empty: return None
                    sp = float(sub.iloc[0])
                    ep = ep_val
                    if math.isnan(sp) or sp <= 0: return None
                    return round((ep - sp) / sp * 100, 2)
                except: return None

            periods = {
                '1D':  today - datetime.timedelta(days=1),
                '1W':  today - datetime.timedelta(weeks=1),
                '1M':  today - datetime.timedelta(days=30),
                'YTD': datetime.date(today.year, 1, 1),
                '1Y':  today - datetime.timedelta(days=365),
                '3Y':  today - datetime.timedelta(days=365*3),
                '5Y':  today - datetime.timedelta(days=365*5),
                'MAX': hist.index[0].date() if not hist.empty else None,
            }
            results = {lbl: pct(start) if start else None for lbl, start in periods.items()}
            self.root.after(0, lambda r=results: self._render_performance(frame, r))
        except Exception as ex:
            print(f"[returns] {ex}")
            self.root.after(0, lambda: self._render_performance(frame, {}))

    def _render_performance(self, frame, results):
        """Render performance % into the strip"""
        for w in frame.winfo_children(): w.destroy()
        labels = ['1D','1W','1M','YTD','1Y','3Y','5Y','MAX']
        for i, lbl in enumerate(labels):
            val = results.get(lbl)
            if val is not None:
                col  = GREEN if val >= 0 else RED
                text = f"{val:+.1f}%"
            else:
                col  = SUBTEXT
                text = "N/A"
            c2 = tk.Frame(frame, bg=CARD, padx=4, pady=6)
            c2.grid(row=0, column=i, padx=2, sticky='nsew')
            frame.columnconfigure(i, weight=1)
            tk.Label(c2, text=lbl,  font=('Arial', 7),          bg=CARD, fg=SUBTEXT).pack()
            tk.Label(c2, text=text, font=('Arial', 8, 'bold'),   bg=CARD, fg=col).pack()

    def _show(self, data):
        for w in self.main.winfo_children(): w.destroy()
        # Reset _hm_content so index heatmap won't try to use a stale frame
        self._hm_content = None
        self._hm_tabs    = {}

        sym  = data.get('nse_symbol','')
        name = data.get('name','')
        if sym: self._load_rpanel(sym, name)

        # ── Toolbar ───────────────────────────────────────────────────────────
        tb = tk.Frame(self.main, bg=CARD, pady=0)
        tb.pack(fill='x')
        tk.Button(tb, text="◀ Back", font=('Arial', 9, 'bold'),
                  bg=BORDER, fg=TEXT, relief='flat', padx=10, pady=8,
                  cursor='hand2', command=self._go_back
                  ).pack(side='left', padx=(8,4), pady=6)
        tk.Button(tb, text="🔄 Refresh", font=('Arial', 9),
                  bg=BORDER, fg=ACCENT, relief='flat', padx=10, pady=8,
                  cursor='hand2',
                  command=lambda u=data.get('page_url',''), s=sym: (
                      self._loading("Refreshing..."),
                      threading.Thread(target=lambda: self.root.after(
                          0, lambda: self._show({**fetch_stock(u),
                          'nse': fetch_nse_live(s)})), daemon=True).start()
                  ) if u else None
                  ).pack(side='left', padx=4, pady=6)
        tk.Button(tb, text="✕ Close", font=('Arial', 9),
                  bg=BORDER, fg=SUBTEXT, relief='flat', padx=10, pady=8,
                  cursor='hand2', command=lambda: (self._welcome(), self._build_rpanel())
                  ).pack(side='right', padx=8, pady=6)
        tk.Frame(self.main, bg=BORDER, height=1).pack(fill='x')

        # Scrollable content area — sb MUST be packed before canvas
        sb = ttk.Scrollbar(self.main, orient='vertical')
        sb.pack(side='right', fill='y')
        canvas = tk.Canvas(self.main, bg=BG, highlightthickness=0,
                           yscrollcommand=sb.set)
        sb.config(command=canvas.yview)
        canvas.pack(side='left', fill='both', expand=True)

        con = tk.Frame(canvas, bg=BG)
        con.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=con, anchor='nw', tags='con')
        canvas.bind('<Configure>', lambda e: canvas.itemconfig('con', width=e.width))
        canvas.bind('<MouseWheel>', lambda e: canvas.yview_scroll(-1 * (e.delta // 120), 'units'))

        sym = data.get('nse_symbol', '')
        nse = data.get('nse', {})

        # ── HEADER ────────────────────────────────────────────────────────────
        hdr = tk.Frame(con, bg=CARD, pady=14); hdr.pack(fill='x', pady=(0, 5))
        lh  = tk.Frame(hdr, bg=CARD); lh.pack(side='left', padx=14)
        tk.Label(lh, text=data.get('name', 'Unknown'),
                 font=('Arial', 18, 'bold'), bg=CARD, fg=TEXT).pack(anchor='w')

        # Sector badge + consolidated tag + symbol
        badge_f = tk.Frame(lh, bg=CARD); badge_f.pack(anchor='w')
        tag = "✅ Consolidated" if data.get('is_consolidated') else "⚠️ Standalone"
        tk.Label(badge_f, text=f"{tag}   •   NSE: {sym}",
                 font=('Arial', 10), bg=CARD, fg=SUBTEXT).pack(side='left')
        sector = data.get('sector') or data.get('industry')
        if sector:
            SECTOR_COLORS = {
                'Technology': '#1A3A6A', 'IT': '#1A3A6A', 'Software': '#1A3A6A',
                'Pharma': '#1A4A2A', 'Healthcare': '#1A4A2A',
                'Banking': '#3A1A1A', 'Finance': '#3A1A1A', 'NBFC': '#3A1A1A',
                'Auto': '#2A2A0A', 'Automobile': '#2A2A0A',
                'FMCG': '#3A2A0A', 'Consumer': '#3A2A0A',
                'Energy': '#2A1A3A', 'Power': '#2A1A3A', 'Oil': '#2A1A3A',
                'Metal': '#1A2A3A', 'Steel': '#1A2A3A', 'Mining': '#1A2A3A',
                'Realty': '#3A1A3A', 'Infrastructure': '#2A1A1A',
                'Chemicals': '#1A3A3A', 'Cement': '#2A2A1A',
            }
            s_bg = '#1C2240'
            for key, col in SECTOR_COLORS.items():
                if key.lower() in sector.lower():
                    s_bg = col; break
            tk.Label(badge_f, text=f"  •  🏭 {sector}",
                     font=('Arial', 10, 'bold'), bg=CARD, fg=ACCENT).pack(side='left', padx=(6,0))

        # Buttons (right side)
        rh = tk.Frame(hdr, bg=CARD); rh.pack(side='right', padx=10)

        # ⭐ Watchlist button
        in_wl = sym in APP_DATA.get('watchlist', {})
        wl_btn_text = ['⭐ Watchlist', '★ Saved'][int(in_wl)]
        wl_btn_col  = [SUBTEXT, YELLOW][int(in_wl)]
        wl_btn = tk.Button(rh, text=wl_btn_text, font=('Arial', 10, 'bold'),
                           bg=CARD2, fg=wl_btn_col, relief='flat', padx=12, pady=8,
                           cursor='hand2')
        wl_btn.pack(side='left', padx=4)

        def _toggle_watchlist():
            wl = APP_DATA.setdefault('watchlist', {})
            if sym in wl:
                del wl[sym]
                wl_btn.config(text='⭐ Watchlist', fg=SUBTEXT)
            else:
                wl[sym] = {
                    'name': data.get('name',''), 'sym': sym,
                    'added': datetime.datetime.now().strftime('%d %b %Y'),
                    'price': data.get('current_price') or (nse.get('ltp') if nse else None),
                    'sector': sector or '',
                }
                wl_btn.config(text='★ Saved', fg=YELLOW)
            _save_data(APP_DATA)
            # Update sidebar watchlist button count
            try: self._wl_btn.config(text=f"⭐  My Watchlist  ({len(APP_DATA.get('watchlist',{}))})")
            except: pass
        wl_btn.config(command=_toggle_watchlist)
        if data.get('page_url'):
            tk.Button(rh, text="🏦 Screener.in", font=('Arial', 10, 'bold'),
                      bg='#142040', fg=ACCENT, relief='flat', padx=14, pady=8,
                      cursor='hand2',
                      command=lambda: webbrowser.open(data['page_url'])
                      ).pack(side='left', padx=4)

            # Consolidated / Standalone toggle
            if data.get('is_consolidated'):
                alt_url  = data['page_url'].replace('/consolidated/', '/')
                alt_text = "📄 Standalone"
            else:
                alt_url  = data['page_url'].rstrip('/') + '/consolidated/'
                alt_text = "📄 Consolidated"
            tk.Button(rh, text=alt_text, font=('Arial', 10),
                      bg=CARD2, fg=TEXT, relief='flat', padx=12, pady=8,
                      cursor='hand2',
                      command=lambda u=alt_url: self._switch(u)
                      ).pack(side='left', padx=4)

        if sym:
            tk.Button(rh, text="📈 NSE Live", font=('Arial', 10, 'bold'),
                      bg='#2A1500', fg=ORANGE, relief='flat', padx=12, pady=8,
                      cursor='hand2',
                      command=lambda: webbrowser.open(
                          f"https://www.nseindia.com/get-quotes/equity?symbol={sym}")
                      ).pack(side='left', padx=4)

        # ── NSE LIVE STRIP ────────────────────────────────────────────────────
        nf = tk.Frame(con, bg=CARD2, pady=8); nf.pack(fill='x', pady=(0, 5), padx=2)
        tk.Label(nf, text="  📡  NSE Live",
                 font=('Arial', 9, 'bold'), bg=CARD2, fg=TEXT).pack(anchor='w', padx=10)
        if nse:
            nm = tk.Frame(nf, bg=CARD2); nm.pack(fill='x', padx=6, pady=3)
            ltp     = nse.get('ltp')
            chg_pct = nse.get('change_pct')
            chg_col = GREEN if (chg_pct or 0) >= 0 else RED
            del_pct = nse.get('delivery_pct')
            del_col = GREEN if del_pct and del_pct >= 50 else YELLOW if del_pct and del_pct >= 35 else RED if del_pct else SUBTEXT
            nse_items = [
                ('LTP',           f"₹{ltp:.2f}"              if ltp               else "N/A", chg_col),
                ('Change',        f"{chg_pct:+.2f}%"         if chg_pct is not None else "N/A", chg_col),
                ('VWAP',          f"₹{nse['vwap']:.2f}"      if nse.get('vwap')   else "N/A", YELLOW),
                ('Day High',      f"₹{nse['high']:.0f}"      if nse.get('high')   else "N/A", YELLOW),
                ('Day Low',       f"₹{nse['low']:.0f}"       if nse.get('low')    else "N/A", YELLOW),
                ('Delivery %',    f"{del_pct:.1f}%"          if del_pct else "N/A", del_col),
                ('52W High',      f"₹{nse['week52_high']:.0f}" if nse.get('week52_high') else "N/A", GREEN),
                ('52W Low',       f"₹{nse['week52_low']:.0f}"  if nse.get('week52_low')  else "N/A", RED),
                ('Upper Circuit', str(nse['upper_circuit'])   if nse.get('upper_circuit') else "N/A", GREEN),
                ('Lower Circuit', str(nse['lower_circuit'])   if nse.get('lower_circuit') else "N/A", RED),
            ]
            for i, (lbl, val, col) in enumerate(nse_items):
                c2 = tk.Frame(nm, bg=CARD, padx=6, pady=8)
                c2.grid(row=0, column=i, padx=2, sticky='nsew')
                nm.columnconfigure(i, weight=1)
                tk.Label(c2, text=lbl,  font=('Arial', 8),          bg=CARD, fg=SUBTEXT).pack()
                tk.Label(c2, text=val,  font=('Arial', 11, 'bold'),  bg=CARD, fg=col).pack()
            # Operator activity alert
            vol_nse = nse.get('volume', 0) or 0
            if del_pct and del_pct >= 60 and chg_pct and abs(chg_pct) >= 2:
                alert_f = tk.Frame(nf, bg='#1A0A00', pady=4); alert_f.pack(fill='x', padx=6, pady=(2,0))
                tk.Label(alert_f,
                         text=f"🔥 Operator/Institutional Activity — Delivery {del_pct:.0f}% + Move {chg_pct:+.1f}%  →  Strong confirmation!",
                         font=('Arial', 9, 'bold'), bg='#1A0A00', fg=ORANGE).pack()
        else:
            tk.Label(nf, text="  ⚠️  NSE Live data unavailable — market band ya weekend ho sakta hai",
                     font=('Arial', 9), bg=CARD2, fg=SUBTEXT).pack(anchor='w', padx=10, pady=4)

        # ── PERFORMANCE STRIP ─────────────────────────────────────────────────
        if sym:
            pf = tk.Frame(con, bg=CARD2, pady=6)
            pf.pack(fill='x', pady=(0, 5), padx=2)
            tk.Label(pf, text="  📊  Returns", font=('Arial', 9, 'bold'),
                     bg=CARD2, fg=TEXT).pack(anchor='w', padx=10)
            self._perf_frame = tk.Frame(pf, bg=CARD2)
            self._perf_frame.pack(fill='x', padx=6, pady=3)
            for i, lbl in enumerate(['1D','1W','1M','YTD','1Y','3Y','5Y','MAX']):
                c2 = tk.Frame(self._perf_frame, bg=CARD, padx=4, pady=8)
                c2.grid(row=0, column=i, padx=2, sticky='nsew')
                self._perf_frame.columnconfigure(i, weight=1)
                tk.Label(c2, text=lbl,  font=('Arial', 8),          bg=CARD, fg=SUBTEXT).pack()
                tk.Label(c2, text="...", font=('Arial', 9, 'bold'),  bg=CARD, fg=SUBTEXT).pack()
            threading.Thread(target=self._fetch_performance,
                             args=(sym, self._perf_frame), daemon=True).start()

        mf = tk.Frame(con, bg=BG); mf.pack(fill='x', pady=(0, 5))
        fii_trend = ""
        dii_trend = ""
        if data.get('fii_holding') is not None and data.get('_fii_prev') is not None:
            diff = round(data['fii_holding'] - data['_fii_prev'], 2)
            fii_trend = f" ({'↑' if diff > 0 else '↓'}{abs(diff):.1f}%)"
        if data.get('dii_holding') is not None and data.get('_dii_prev') is not None:
            diff = round(data['dii_holding'] - data['_dii_prev'], 2)
            dii_trend = f" ({'↑' if diff > 0 else '↓'}{abs(diff):.1f}%)"

        metrics = [
            ('Mkt Cap',     data.get('market_cap'),      'Cr'),
            ('Price',       data.get('current_price'),   '₹'),
            ('P/E',         data.get('pe'),              ''),
            ('ROE',         data.get('roe'),             '%'),
            ('ROCE',        data.get('roce'),            '%'),
            ('D/E',         data.get('debt_to_equity'),  ''),
            ('Int. Cover',  data.get('interest_coverage'),'x'),
            ('Promoter',    data.get('promoter_holding'),'%'),
            ('Pledged',     data.get('pledged'),         '%'),
            ('FII',         data.get('fii_holding'),     '%'),
            ('DII',         data.get('dii_holding'),     '%'),
        ]
        for i, (lbl, val, unit) in enumerate(metrics):
            c3 = tk.Frame(mf, bg=CARD, padx=5, pady=10)
            c3.grid(row=0, column=i, padx=2, sticky='nsew')
            mf.columnconfigure(i, weight=1)
            tk.Label(c3, text=lbl, font=('Arial', 8), bg=CARD, fg=SUBTEXT).pack()
            if val is not None:
                try:
                    fv = float(val)
                    if unit == 'Cr':  vs = f"{fv:.0f}Cr"
                    elif unit == '₹': vs = f"₹{fv:.0f}"
                    elif unit == 'x': vs = f"{fv:.1f}x"
                    elif unit == '%': vs = f"{fv:.1f}%"
                    else:             vs = f"{fv:.2f}"
                    if lbl == 'FII' and fii_trend: vs += fii_trend
                    if lbl == 'DII' and dii_trend: vs += dii_trend
                except: vs = str(val)
                co = ACCENT
            else:
                vs = "N/A"; co = SUBTEXT
            tk.Label(c3, text=vs, font=('Arial', 10, 'bold'), bg=CARD, fg=co).pack()

        # ── TABS ──────────────────────────────────────────────────────────────
        tb = tk.Frame(con, bg=BG); tb.pack(fill='x', pady=(6, 0))
        self.cp = tk.Frame(con, bg=BG); self.cp.pack(fill='both', expand=True)
        self._tabs = {}
        for key, lbl, period in [
            ('swing',      '🔵 Swing',      '2-3 Hafta'),
            ('positional', '🟡 Positional',  '3-12 Mahine'),
            ('longterm',   '🟢 Long Term',   '2-5 Saal'),
            ('technical',  '📊 Technical',   'Full Analysis'),
            ('notes',      '📝 Notes',       'My Notes'),
        ]:
            b = tk.Button(tb, text=f"{lbl}  ({period})",
                          font=('Arial', 10, 'bold'), relief='flat',
                          padx=12, pady=8, cursor='hand2',
                          command=lambda k=key: self._tab(k, data))
            b.pack(side='left', padx=2, expand=True, fill='x')
            self._tabs[key] = b
        self._tab('swing', data)

    def _switch(self, url):
        self._loading("Switching view...")
        threading.Thread(target=lambda: (
            self.root.after(0, lambda: self._show(
                {**fetch_stock(url), 'nse': fetch_nse_live(
                    re.search(r'/company/([^/]+)/', url).group(1).upper()
                    if re.search(r'/company/([^/]+)/', url) else ''
                )}
            ))
        ), daemon=True).start()

    def _tab(self, key, data):
        tbg = {'swing': '1565C0', 'positional': 'E65100', 'longterm': '2E7D32',
               'technical': '6A0DAD', 'notes': '1A6A5A'}
        for k, b in self._tabs.items():
            b.config(bg=f"#{tbg[k]}" if k == key else CARD2,
                     fg='white' if k == key else TEXT)
        for w in self.cp.winfo_children(): w.destroy()

        if key == 'technical':
            self._show_technical_tab(data)
            return
        if key == 'notes':
            self._show_notes_tab(data)
            return

        crit   = CRITERIA[key]
        passed = skipped = 0
        total_auto = sum(1 for _, dkey, _, fn in crit if fn is not None)

        rf = tk.Frame(self.cp, bg=BG); rf.pack(fill='x', padx=6, pady=8)

        for fname, dkey, cond, fn in crit:
            is_manual = (fn is None)
            val = data.get(dkey) if not is_manual else None

            if is_manual:
                ok = None  # always ❓ — user decide karega
            else:
                try:    ok = fn(float(val)) if val is not None else None
                except: ok = None

            if ok is True: passed += 1

            if is_manual:
                icon, fc = '❓', YELLOW
            elif ok is True:
                icon, fc = '✅', GREEN
            elif ok is False:
                icon, fc = '❌', RED
            else:
                icon, fc = '❓', YELLOW

            row = tk.Frame(rf, bg=CARD, pady=8); row.pack(fill='x', pady=2, padx=4)
            row.columnconfigure(1, weight=1)
            tk.Label(row, text=icon, font=('Arial', 13), bg=CARD
                     ).pack(side='left', padx=(10, 6))
            tk.Label(row, text=fname, font=('Arial', 11, 'bold'), bg=CARD, fg=TEXT,
                     anchor='w').pack(side='left', padx=(0,4))
            tk.Label(row, text=cond, font=('Arial', 10), bg=CARD, fg=SUBTEXT,
                     anchor='w').pack(side='left', expand=True, fill='x')

            if is_manual:
                disp = "Manual Check"; dc = YELLOW
            elif val is not None:
                try:
                    fv = float(val)
                    disp = f"{fv:.2f}"
                except: disp = str(val)
                dc = fc
            else:
                disp = "Data N/A"; dc = YELLOW

            tk.Label(row, text=disp, font=('Arial', 12, 'bold'), bg=CARD, fg=dc,
                     anchor='e').pack(side='right', padx=14)

        # Score
        pct = int(passed / total_auto * 100) if total_auto else 0
        sc, vd, vbg = (
            (GREEN,  '✅  ENTRY LO',        '#0D3020') if pct >= 80 else
            (YELLOW, '⚠️  CAREFULLY DEKHO', '#2A2000') if pct >= 60 else
            (RED,    '❌  SKIP KARO',        '#2A0A0A')
        )
        sf2 = tk.Frame(self.cp, bg=CARD, pady=14); sf2.pack(fill='x', padx=6, pady=6)
        tk.Label(sf2,
                 text=f"Auto Score: {passed}/{total_auto}  ({pct}%)   |   Manual checks: ❓ Khud dekho",
                 font=('Arial', 14, 'bold'), bg=CARD, fg=sc).pack(pady=(0, 8))
        vf = tk.Frame(sf2, bg=vbg, padx=28, pady=10); vf.pack()
        tk.Label(vf, text=vd, font=('Arial', 14, 'bold'), bg=vbg, fg='white').pack()

        # Progress bar
        pb = tk.Frame(self.cp, bg=BORDER, height=10); pb.pack(fill='x', padx=10, pady=(0,6))
        pb.update_idletasks()
        bw = int(pb.winfo_width() * pct / 100)
        if bw > 0: tk.Frame(pb, bg=sc, height=10, width=bw).place(x=0, y=0)

        # Notes
        notes = {
            'swing':      '⚡ Swing: Technical 80% | Fundamental 20% | Short holding, quick exit',
            'positional': '⚡ Positional: Technical 50% | Fundamental 50% | Dono strong chahiye',
            'longterm':   '⚡ Long Term: Fundamental 80% | Technical sirf entry timing ke liye',
        }
        nf = tk.Frame(self.cp, bg='#0A0D1A', pady=10); nf.pack(fill='x', padx=4, pady=4)
        tk.Label(nf, text=notes[key], font=('Arial', 10, 'italic'),
                 bg='#0A0D1A', fg=SUBTEXT).pack()

    # ══════════════════════════════════════════════════════════════════════════
    # NOTES TAB — Personal notes + trade log per stock
    # ══════════════════════════════════════════════════════════════════════════

    def _show_notes_tab(self, data):
        sym  = data.get('nse_symbol', '') or 'UNKNOWN'
        name = data.get('name', sym)

        outer = tk.Frame(self.cp, bg=BG); outer.pack(fill='both', expand=True, padx=8, pady=8)

        # ── My Note ───────────────────────────────────────────────────────────
        tk.Label(outer, text=f"📝  My Notes — {name} ({sym})",
                 font=('Arial', 12, 'bold'), bg=BG, fg=TEXT).pack(anchor='w', pady=(4,6))

        note_f = tk.Frame(outer, bg=CARD, pady=10); note_f.pack(fill='x')
        existing = APP_DATA.get('notes', {}).get(sym, {}).get('text', '')
        note_box = tk.Text(note_f, height=6, bg=CARD2, fg=TEXT, font=('Arial', 11),
                           insertbackground=TEXT, relief='flat', padx=10, pady=8,
                           wrap='word', bd=0)
        note_box.pack(fill='x', padx=10, pady=(6,4))
        if existing:
            note_box.insert('1.0', existing)

        def _save_note():
            txt = note_box.get('1.0', 'end').strip()
            APP_DATA.setdefault('notes', {})[sym] = {
                'text': txt,
                'name': name,
                'updated': datetime.datetime.now().strftime('%d %b %Y %H:%M'),
            }
            _save_data(APP_DATA)
            save_lbl.config(text="✅ Saved!", fg=GREEN)
            outer.after(2000, lambda: save_lbl.config(text=""))

        btn_row = tk.Frame(note_f, bg=CARD); btn_row.pack(fill='x', padx=10, pady=(0,6))
        tk.Button(btn_row, text="💾  Save Note", font=('Arial', 10, 'bold'),
                  bg=ACCENT, fg='white', relief='flat', padx=16, pady=6,
                  cursor='hand2', command=_save_note).pack(side='left')
        save_lbl = tk.Label(btn_row, text="", font=('Arial', 10), bg=CARD, fg=GREEN)
        save_lbl.pack(side='left', padx=10)
        last = APP_DATA.get('notes', {}).get(sym, {}).get('updated', '')
        if last:
            tk.Label(btn_row, text=f"Last saved: {last}", font=('Arial', 8),
                     bg=CARD, fg=SUBTEXT).pack(side='right', padx=6)

        # ── Trade Log ─────────────────────────────────────────────────────────
        tk.Label(outer, text="📒  Trade Log",
                 font=('Arial', 12, 'bold'), bg=BG, fg=TEXT).pack(anchor='w', pady=(16,6))

        log_f = tk.Frame(outer, bg=CARD, pady=10); log_f.pack(fill='x')

        # Entry form
        form_f = tk.Frame(log_f, bg=CARD); form_f.pack(fill='x', padx=10, pady=4)
        fields = {}
        form_items = [
            ('Type',   ['BUY', 'SELL', 'WATCH']),
            ('Price',  None), ('Qty', None), ('Date', None), ('Reason', None),
        ]
        for col_i, (lbl, opts) in enumerate(form_items):
            ff = tk.Frame(form_f, bg=CARD); ff.grid(row=0, column=col_i, padx=4, sticky='w')
            tk.Label(ff, text=lbl, font=('Arial', 8), bg=CARD, fg=SUBTEXT).pack(anchor='w')
            if opts:
                var = tk.StringVar(value=opts[0])
                dd  = tk.OptionMenu(ff, var, *opts)
                dd.config(bg=CARD2, fg=TEXT, font=('Arial', 10), relief='flat',
                          activebackground=BORDER, highlightthickness=0)
                dd['menu'].config(bg=CARD2, fg=TEXT)
                dd.pack(anchor='w')
                fields[lbl] = var
            else:
                default = datetime.datetime.now().strftime('%d/%m/%Y') if lbl == 'Date' else ''
                ent = tk.Entry(ff, bg=CARD2, fg=TEXT, font=('Arial', 10),
                               insertbackground=TEXT, relief='flat', width=10 if lbl!='Reason' else 18,
                               bd=4)
                ent.insert(0, default)
                ent.pack(anchor='w')
                fields[lbl] = ent

        def _add_trade():
            try:
                typ    = fields['Type'].get()
                price  = fields['Price'].get().strip()
                qty    = fields['Qty'].get().strip()
                date   = fields['Date'].get().strip()
                reason = fields['Reason'].get().strip() if hasattr(fields['Reason'], 'get') else ''
                if not price: return
                entry = {
                    'type': typ, 'price': price, 'qty': qty,
                    'date': date, 'reason': reason,
                    'logged': datetime.datetime.now().strftime('%d %b %Y %H:%M'),
                }
                trades = APP_DATA.setdefault('trades', {}).setdefault(sym, [])
                trades.insert(0, entry)
                _save_data(APP_DATA)
                _refresh_trades()
                # Clear entries
                for lbl2, w in fields.items():
                    if lbl2 not in ('Type', 'Date') and hasattr(w, 'delete'):
                        w.delete(0, 'end')
            except Exception as ex:
                print("Trade log error:", ex)

        tk.Button(form_f, text="➕ Add", font=('Arial', 10, 'bold'),
                  bg=GREEN, fg='#001A10', relief='flat', padx=12, pady=6,
                  cursor='hand2', command=_add_trade
                  ).grid(row=0, column=len(form_items), padx=(8,0), sticky='s')

        # Trade list
        trade_list_f = tk.Frame(log_f, bg=CARD); trade_list_f.pack(fill='x', padx=10, pady=(8,6))

        def _refresh_trades():
            for w in trade_list_f.winfo_children(): w.destroy()
            trades = APP_DATA.get('trades', {}).get(sym, [])
            if not trades:
                tk.Label(trade_list_f, text="Abhi koi trade log nahi — upar se add karo",
                         font=('Arial', 9), bg=CARD, fg=SUBTEXT).pack(pady=8)
                return
            # Header
            hdr2 = tk.Frame(trade_list_f, bg=BORDER); hdr2.pack(fill='x', pady=(0,2))
            for col_t, w_t in [('Type',8),('Price',10),('Qty',8),('Date',12),('Reason',22),('P&L est.',10),('',6)]:
                tk.Label(hdr2, text=col_t, font=('Arial', 8, 'bold'), bg=BORDER, fg=SUBTEXT,
                         width=w_t, anchor='w').pack(side='left', padx=4, pady=4)
            for idx, t in enumerate(trades):
                tc = GREEN if t['type']=='BUY' else RED if t['type']=='SELL' else YELLOW
                trow = tk.Frame(trade_list_f, bg=CARD2 if idx%2==0 else CARD)
                trow.pack(fill='x', pady=1)
                tk.Label(trow, text=t['type'],   font=('Arial', 9,'bold'), bg=trow.cget('bg'), fg=tc,    width=8,  anchor='w').pack(side='left', padx=4, pady=5)
                tk.Label(trow, text=f"₹{t['price']}", font=('Arial', 9), bg=trow.cget('bg'), fg=TEXT,   width=10, anchor='w').pack(side='left', padx=4)
                tk.Label(trow, text=t.get('qty',''), font=('Arial', 9), bg=trow.cget('bg'), fg=TEXT,    width=8,  anchor='w').pack(side='left', padx=4)
                tk.Label(trow, text=t.get('date',''), font=('Arial', 9), bg=trow.cget('bg'), fg=SUBTEXT, width=12, anchor='w').pack(side='left', padx=4)
                tk.Label(trow, text=t.get('reason','')[:28], font=('Arial', 9), bg=trow.cget('bg'), fg=SUBTEXT, width=22, anchor='w').pack(side='left', padx=4)
                # P&L — fetch best live price in background (yfinance > Yahoo > NSE)
                pnl_lbl = tk.Label(trow, text="...", font=('Arial', 9,'bold'), bg=trow.cget('bg'),
                                   fg=SUBTEXT, width=10, anchor='w')
                pnl_lbl.pack(side='left', padx=4)

                def _fetch_pnl_notes(s=sym, trade=t, lbl=pnl_lbl):
                    try:
                        cur_p = fetch_best_live_price(s)
                        if cur_p and trade.get('price') and trade['type'] in ('BUY', 'SELL'):
                            ep   = float(trade['price'])
                            qty2 = float(trade.get('qty') or 1)
                            pnl  = (float(cur_p) - ep) * qty2 * (1 if trade['type'] == 'BUY' else -1)
                            col  = GREEN if pnl >= 0 else RED
                            txt  = f"{'+'if pnl>=0 else ''}₹{pnl:.0f}"
                            self.root.after(0, lambda lb=lbl, t=txt, c=col: lb.config(text=t, fg=c))
                        else:
                            self.root.after(0, lambda lb=lbl: lb.config(text="—", fg=SUBTEXT))
                    except:
                        self.root.after(0, lambda lb=lbl: lb.config(text="—", fg=SUBTEXT))

                threading.Thread(target=_fetch_pnl_notes, daemon=True).start()

                def _del(i=idx):
                    APP_DATA.get('trades',{}).get(sym,[]).pop(i)
                    _save_data(APP_DATA); _refresh_trades()
                tk.Button(trow, text='✕', font=('Arial', 8), bg=trow.cget('bg'), fg=RED,
                          relief='flat', cursor='hand2', command=_del).pack(side='right', padx=6)

        _refresh_trades()

    # ══════════════════════════════════════════════════════════════════════════
    # TECHNICAL ANALYSIS TAB — Full Suite
    # ══════════════════════════════════════════════════════════════════════════

    def _show_technical_tab(self, data):
        """Full technical analysis — indicators, patterns, S/R, target, verdict"""
        sym = data.get('nse_symbol', '')
        if not sym:
            tk.Label(self.cp, text="❌ NSE Symbol nahi mila", bg=BG, fg=RED,
                     font=('Arial', 12)).pack(pady=40)
            return

        # ── Loading skeleton ──────────────────────────────────────────────────
        lf = tk.Frame(self.cp, bg=BG); lf.pack(fill='both', expand=True, pady=20)
        tk.Label(lf, text="⏳", font=('Arial', 36), bg=BG).pack()
        tk.Label(lf, text=f"Technical data fetch ho rahi hai — {sym}.NS",
                 font=('Arial', 12), bg=BG, fg=SUBTEXT).pack(pady=8)
        tk.Label(lf, text="RSI • MACD • EMA • Patterns • S/R • Target • AI Verdict",
                 font=('Arial', 10), bg=BG, fg=PURPLE).pack()

        threading.Thread(
            target=self._fetch_technical_data,
            args=(sym, data), daemon=True).start()

    def _fetch_technical_data(self, sym, fdata):
        """Fetch yfinance data and compute all technical indicators"""
        import math, statistics as _stats
        result = {}
        try:
            hist = yf.download(f"{sym}.NS", period="1y", interval="1d",
                               auto_adjust=True, progress=False)
            if hist is None or hist.empty:
                hist = yf.download(f"{sym}.NS", period="6mo", interval="1d",
                                   auto_adjust=True, progress=False)
            if hist is None or hist.empty:
                ticker = yf.Ticker(f"{sym}.NS")
                hist   = ticker.history(period="1y", auto_adjust=True, actions=False)

            if hist is None or hist.empty:
                self.root.after(0, lambda: self._render_technical(
                    {}, fdata, f"{sym} ka data nahi mila — NSE pe listed hai?"))
                return

            # Flatten multi-index
            if hasattr(hist.columns, 'levels'):
                hist.columns = hist.columns.get_level_values(0)

            try:
                hist.index = hist.index.tz_localize(None) if hist.index.tzinfo else hist.index
            except: pass

            # ── NaN rows drop karo — market band hone ke baad NaN aata hai ───
            hist = hist.dropna(subset=['Close','High','Low','Volume'])
            if len(hist) < 20:
                self.root.after(0, lambda: self._render_technical({}, fdata, "Data bahut kam hai"))
                return

            close  = hist['Close']
            high   = hist['High']
            low    = hist['Low']
            volume = hist['Volume']
            c      = close.values.astype(float)
            h      = high.values.astype(float)
            l      = low.values.astype(float)
            v      = volume.values.astype(float)

            # NaN values remove karo (market band / incomplete rows)
            import numpy as np
            valid  = ~(np.isnan(c) | np.isnan(h) | np.isnan(l))
            c, h, l, v = c[valid], h[valid], l[valid], v[valid]
            n = len(c)
            if n < 20:
                self.root.after(0, lambda: self._render_technical({}, fdata, "Valid data bahut kam hai"))
                return

            # ── EMA helper ───────────────────────────────────────────────────
            def ema(arr, period):
                k = 2 / (period + 1)
                e = [arr[0]]
                for x in arr[1:]:
                    e.append(x * k + e[-1] * (1 - k))
                return e

            # ── RSI (14) ─────────────────────────────────────────────────────
            def rsi(arr, p=14):
                deltas = [arr[i] - arr[i-1] for i in range(1, len(arr))]
                gains  = [max(d,0) for d in deltas]
                losses = [abs(min(d,0)) for d in deltas]
                avg_g  = sum(gains[:p]) / p
                avg_l  = sum(losses[:p]) / p
                for i in range(p, len(deltas)):
                    avg_g = (avg_g * (p-1) + gains[i]) / p
                    avg_l = (avg_l * (p-1) + losses[i]) / p
                if avg_l == 0: return 100
                rs = avg_g / avg_l
                return round(100 - (100 / (1 + rs)), 1)

            rsi_val = rsi(c.tolist())

            # ── MACD ─────────────────────────────────────────────────────────
            ema12 = ema(c.tolist(), 12)
            ema26 = ema(c.tolist(), 26)
            macd_line   = [ema12[i] - ema26[i] for i in range(n)]
            signal_line = ema(macd_line[25:], 9)
            macd_val    = round(macd_line[-1], 2)
            signal_val  = round(signal_line[-1], 2) if signal_line else 0
            macd_cross  = "Bullish" if macd_val > signal_val else "Bearish"

            # ── EMAs ─────────────────────────────────────────────────────────
            ema20  = ema(c.tolist(), 20)
            ema50  = ema(c.tolist(), 50)
            ema200 = ema(c.tolist(), 200) if n >= 200 else None
            cur    = c[-1]
            e20    = round(ema20[-1], 2)
            e50    = round(ema50[-1], 2)
            e200   = round(ema200[-1], 2) if ema200 else None

            ema_align = (cur > e20 > e50) and (e200 is None or e50 > e200)

            # ── Bollinger Bands (20, 2) ───────────────────────────────────────
            bb_upper, bb_lower, bb_mid = None, None, None
            if n >= 20:
                window   = [float(x) for x in c[-20:]]   # numpy → plain Python list
                bb_mid   = round(sum(window)/20, 2)
                bb_std   = _stats.stdev(window)
                bb_upper = round(bb_mid + 2*bb_std, 2)
                bb_lower = round(bb_mid - 2*bb_std, 2)
                bb_pct   = round((cur - bb_lower) / (bb_upper - bb_lower) * 100, 1) if (bb_upper - bb_lower) > 0 else 50
            else:
                bb_pct = 50

            # ── ATR (14) — volatility ─────────────────────────────────────────
            tr_list = []
            for i in range(1, min(15, n)):
                tr = max(h[-i] - l[-i], abs(h[-i] - c[-i-1]), abs(l[-i] - c[-i-1]))
                tr_list.append(tr)
            atr = round(sum(tr_list) / len(tr_list), 2) if tr_list else 0
            atr_pct = round(atr / cur * 100, 2) if cur else 0

            # ── Volume analysis ───────────────────────────────────────────────
            avg_vol_20 = sum(v[-20:]) / 20 if n >= 20 else sum(v) / n
            vol_ratio  = round(v[-1] / avg_vol_20, 2) if avg_vol_20 > 0 else 1
            vol_surge  = vol_ratio >= 1.5

            # ── Support & Resistance (pivot-based + swing highs/lows) ─────────
            # Last 50 bars — find local highs/lows
            window50_h = h[-50:].tolist() if n >= 50 else h.tolist()
            window50_l = l[-50:].tolist() if n >= 50 else l.tolist()
            window50_c = c[-50:].tolist() if n >= 50 else c.tolist()

            # Pivot point (classic)
            pivot  = (h[-1] + l[-1] + c[-1]) / 3
            r1     = round(2 * pivot - l[-1], 2)
            r2     = round(pivot + (h[-1] - l[-1]), 2)
            s1     = round(2 * pivot - h[-1], 2)
            s2     = round(pivot - (h[-1] - l[-1]), 2)
            pivot  = round(pivot, 2)

            # 52W high/low
            high52 = round(max(h.tolist()), 2)
            low52  = round(min(l.tolist()), 2)
            pct_from_52h = round((cur - high52) / high52 * 100, 1)

            # ── Target & Stop Loss ────────────────────────────────────────────
            # ATR-based: SL = cur - 2*ATR, Target = cur + 3*ATR (1:1.5 RR)
            sl_atr   = round(cur - 2 * atr, 2)
            tgt1_atr = round(cur + 2 * atr, 2)
            tgt2_atr = round(cur + 4 * atr, 2)
            rr_ratio = round((tgt1_atr - cur) / (cur - sl_atr), 2) if (cur - sl_atr) > 0 else 0

            # ── Candlestick Pattern Detection (last 3 candles) ────────────────
            patterns = []
            if n >= 3:
                o3, h3, l3, c3 = hist['Open'].values, h, l, c
                # Doji — body < 10% of range
                body  = abs(c3[-1] - o3[-1])
                rng   = h3[-1] - l3[-1]
                if rng > 0 and body / rng < 0.1:
                    patterns.append(('Doji', '⚖️', YELLOW, 'Indecision — wait for confirmation'))
                # Hammer (bullish)
                lower_wick = min(o3[-1], c3[-1]) - l3[-1]
                upper_wick = h3[-1] - max(o3[-1], c3[-1])
                if rng > 0 and lower_wick > 2 * body and upper_wick < body:
                    patterns.append(('Hammer', '🔨', GREEN, 'Bullish reversal signal'))
                # Shooting Star (bearish)
                if rng > 0 and upper_wick > 2 * body and lower_wick < body:
                    patterns.append(('Shooting Star', '⭐', RED, 'Bearish reversal signal'))
                # Bullish Engulfing
                if n >= 2:
                    prev_body = c3[-2] - o3[-2]
                    curr_body = c3[-1] - o3[-1]
                    if prev_body < 0 and curr_body > 0 and curr_body > abs(prev_body):
                        patterns.append(('Bullish Engulfing', '🟢', GREEN, 'Strong bullish signal'))
                # Bearish Engulfing
                if n >= 2:
                    prev_body = c3[-2] - o3[-2]
                    curr_body = c3[-1] - o3[-1]
                    if prev_body > 0 and curr_body < 0 and abs(curr_body) > prev_body:
                        patterns.append(('Bearish Engulfing', '🔴', RED, 'Strong bearish signal'))
                # Morning Star (3-candle bullish)
                if n >= 3 and (c3[-3] < o3[-3]) and (abs(c3[-2]-o3[-2]) < 0.3*(h3[-2]-l3[-2])) and (c3[-1] > o3[-1]):
                    patterns.append(('Morning Star', '🌅', GREEN, 'Bullish reversal — 3-candle pattern'))
                # Evening Star (3-candle bearish)
                if n >= 3 and (c3[-3] > o3[-3]) and (abs(c3[-2]-o3[-2]) < 0.3*(h3[-2]-l3[-2])) and (c3[-1] < o3[-1]):
                    patterns.append(('Evening Star', '🌇', RED, 'Bearish reversal — 3-candle pattern'))
                if not patterns:
                    patterns.append(('No Strong Pattern', '➖', SUBTEXT, 'Neutral — no clear signal today'))

            # ── Chart Pattern Detection ───────────────────────────────────────
            chart_patterns = []
            # VCP (Volatility Contraction Pattern) — narrowing price swings
            if n >= 30:
                ranges = [h[-i] - l[-i] for i in range(1, 31)]
                first_half  = sum(ranges[15:]) / 15
                second_half = sum(ranges[:15]) / 15
                if second_half < first_half * 0.7 and vol_ratio < 1.0:
                    chart_patterns.append(('VCP — Volatility Contraction', '🔺', GREEN,
                        'Price range sikud rahi hai — breakout ready!'))
            # Near 52W High Breakout
            if pct_from_52h >= -3:
                chart_patterns.append(('Near 52W High Breakout', '🚀', GREEN,
                    f'{abs(pct_from_52h):.1f}% below 52W high — breakout zone!'))
            # Consolidation (tight range last 10 days)
            if n >= 10:
                recent_high = max(h[-10:])
                recent_low  = min(l[-10:])
                consol_pct  = (recent_high - recent_low) / cur * 100 if cur else 100
                if consol_pct < 8:
                    chart_patterns.append(('Consolidation / Base Building', '📦', YELLOW,
                        f'Last 10 days mein sirf {consol_pct:.1f}% range — tight base!'))
            # Cup & Handle — simplified (price near prior high after rounding bottom)
            if n >= 60:
                left_high  = max(h[-60:-40].tolist())
                bottom     = min(l[-40:-15].tolist())
                right_zone = max(h[-15:].tolist())
                depth      = (left_high - bottom) / left_high * 100
                if 10 < depth < 35 and right_zone > left_high * 0.95:
                    chart_patterns.append(('Cup & Handle', '☕', GREEN,
                        f'Cup depth {depth:.1f}% — handle forming, watch for breakout!'))
            if not chart_patterns:
                chart_patterns.append(('No Major Chart Pattern', '➖', SUBTEXT,
                    'Clear pattern nahi dikh raha — wait karo'))

            # ── Valuation Meter ───────────────────────────────────────────────
            pe     = fdata.get('pe')
            roe    = fdata.get('roe')
            pb     = fdata.get('price_to_book')
            # Simple PE-based valuation
            if pe:
                if pe < 15:    val_label, val_col, val_score = "Cheap 🟢",   GREEN,  3
                elif pe < 25:  val_label, val_col, val_score = "Fair 🟡",    YELLOW, 2
                elif pe < 40:  val_label, val_col, val_score = "Expensive 🔴", RED,  1
                else:          val_label, val_col, val_score = "Very Expensive ❌", RED, 0
            else:
                val_label, val_col, val_score = "P/E Data N/A", SUBTEXT, 1

            # ── Technical Score (0-100) ───────────────────────────────────────
            score = 0
            reasons_bull = []
            reasons_bear = []

            # RSI
            if 40 <= rsi_val <= 70:
                score += 20
                if rsi_val > 55: reasons_bull.append(f"RSI {rsi_val} — bullish zone")
            elif rsi_val > 70:
                score += 8
                reasons_bear.append(f"RSI {rsi_val} — overbought, careful")
            else:
                score += 5
                reasons_bear.append(f"RSI {rsi_val} — weak momentum")

            # MACD
            if macd_cross == "Bullish":
                score += 20
                reasons_bull.append("MACD bullish crossover")
            else:
                reasons_bear.append("MACD bearish — selling pressure")

            # EMA alignment
            if ema_align:
                score += 25
                reasons_bull.append(f"EMA20 > EMA50{' > EMA200' if e200 else ''} — uptrend")
            elif cur > e20:
                score += 12
                reasons_bull.append("Price EMA20 ke upar — short-term bullish")
            else:
                reasons_bear.append("Price EMAs ke neeche — downtrend")

            # Volume
            if vol_surge:
                score += 15
                reasons_bull.append(f"Volume {vol_ratio}x average — strong interest")
            else:
                score += 5

            # BB position
            if bb_pct > 60:
                score += 10
                reasons_bull.append(f"Bollinger upper band ke paas — momentum strong")
            elif bb_pct < 30:
                score += 3
                reasons_bear.append("Bollinger lower band ke paas — weak")
            else:
                score += 6

            # 52W proximity
            if pct_from_52h >= -5:
                score += 10
                reasons_bull.append(f"52W high ke paas ({abs(pct_from_52h):.1f}% below)")
            elif pct_from_52h < -20:
                reasons_bear.append(f"52W high se {abs(pct_from_52h):.1f}% neeche")

            score = min(score, 100)

            # ── AI Verdict ────────────────────────────────────────────────────
            fund_score = 0
            if fdata.get('net_profit', 0) and fdata['net_profit'] > 0: fund_score += 1
            if fdata.get('roe', 0) and fdata['roe'] > 15:              fund_score += 1
            if fdata.get('debt_to_equity') is not None and fdata['debt_to_equity'] < 1: fund_score += 1
            if fdata.get('promoter_holding', 0) and fdata['promoter_holding'] > 50: fund_score += 1

            combined = score * 0.6 + fund_score * 10
            if combined >= 70 and score >= 60:
                verdict = "⚡ STRONG BUY"
                verdict_col = GREEN
                verdict_bg  = '#0A2A18'
                verdict_reason = f"Technical score {score}/100 + Fundamentals solid. Entry consider karo."
            elif combined >= 55:
                verdict = "✅ BUY with Caution"
                verdict_col = '#00CC88'
                verdict_bg  = '#082015'
                verdict_reason = f"Decent setup. Confirm karo: volume, S/R level check karo."
            elif combined >= 40:
                verdict = "⏳ WAIT / WATCH"
                verdict_col = YELLOW
                verdict_bg  = '#1E1800'
                verdict_reason = "Mixed signals. Breakout ya consolidation ka wait karo."
            else:
                verdict = "❌ AVOID for Now"
                verdict_col = RED
                verdict_bg  = '#200810'
                verdict_reason = f"Technical weak ({score}/100). Better opportunity ka wait karo."

            result = {
                'rsi': rsi_val, 'macd': macd_val, 'signal': signal_val,
                'macd_cross': macd_cross, 'ema20': e20, 'ema50': e50, 'ema200': e200,
                'ema_align': ema_align, 'cur': round(cur, 2),
                'bb_upper': bb_upper, 'bb_lower': bb_lower, 'bb_mid': bb_mid, 'bb_pct': bb_pct,
                'atr': atr, 'atr_pct': atr_pct,
                'vol_ratio': vol_ratio, 'vol_surge': vol_surge,
                'pivot': pivot, 'r1': r1, 'r2': r2, 's1': s1, 's2': s2,
                'high52': high52, 'low52': low52, 'pct_from_52h': pct_from_52h,
                'sl': sl_atr, 'tgt1': tgt1_atr, 'tgt2': tgt2_atr, 'rr': rr_ratio,
                'patterns': patterns, 'chart_patterns': chart_patterns,
                'val_label': val_label, 'val_col': val_col,
                'score': score, 'reasons_bull': reasons_bull, 'reasons_bear': reasons_bear,
                'verdict': verdict, 'verdict_col': verdict_col, 'verdict_bg': verdict_bg,
                'verdict_reason': verdict_reason,
            }

        except Exception as ex:
            import traceback; traceback.print_exc()
            result = {}

        self.root.after(0, lambda: self._render_technical(result, fdata))

    def _render_technical(self, r, fdata, err=None):
        """Render full technical analysis panel"""
        for w in self.cp.winfo_children(): w.destroy()

        if err or not r:
            tk.Label(self.cp, text=f"❌ {err or 'Data load nahi hua'}",
                     font=('Arial', 12), bg=BG, fg=RED).pack(pady=40)
            return

        # ════════════════════════════════════════════════════════════════
        # SECTION 1 — AI VERDICT (top — most important)
        # ════════════════════════════════════════════════════════════════
        vf = tk.Frame(self.cp, bg=r['verdict_bg'], pady=14)
        vf.pack(fill='x', padx=6, pady=(8, 4))
        tk.Label(vf, text="⚡  AI QUICK VERDICT",
                 font=('Arial', 9, 'bold'), bg=r['verdict_bg'], fg=SUBTEXT).pack()
        tk.Label(vf, text=r['verdict'],
                 font=('Arial', 20, 'bold'), bg=r['verdict_bg'], fg=r['verdict_col']).pack(pady=(4,2))
        tk.Label(vf, text=r['verdict_reason'],
                 font=('Arial', 10), bg=r['verdict_bg'], fg=TEXT, wraplength=700).pack()

        # ════════════════════════════════════════════════════════════════
        # SECTION 2 — Technical Score bar
        # ════════════════════════════════════════════════════════════════
        score = r['score']
        sc_col = GREEN if score >= 65 else YELLOW if score >= 45 else RED
        sf = tk.Frame(self.cp, bg=CARD, pady=10); sf.pack(fill='x', padx=6, pady=4)
        hrow = tk.Frame(sf, bg=CARD); hrow.pack(fill='x', padx=10)
        tk.Label(hrow, text="📊  Technical Score",
                 font=('Arial', 10, 'bold'), bg=CARD, fg=TEXT).pack(side='left')
        tk.Label(hrow, text=f"{score}/100",
                 font=('Arial', 14, 'bold'), bg=CARD, fg=sc_col).pack(side='right')
        pb = tk.Frame(sf, bg=BORDER, height=12); pb.pack(fill='x', padx=10, pady=(6,4))
        pb.update_idletasks()
        bw = int(pb.winfo_width() * score / 100)
        if bw > 0: tk.Frame(pb, bg=sc_col, height=12, width=bw).place(x=0, y=0)

        # Bull/Bear reasons
        br_f = tk.Frame(sf, bg=CARD); br_f.pack(fill='x', padx=10, pady=(4,0))
        bull_f = tk.Frame(br_f, bg=CARD); bull_f.pack(side='left', fill='both', expand=True)
        bear_f = tk.Frame(br_f, bg=CARD); bear_f.pack(side='right', fill='both', expand=True)
        tk.Label(bull_f, text="🟢 Bullish signals", font=('Arial', 9, 'bold'),
                 bg=CARD, fg=GREEN).pack(anchor='w')
        for reason in r.get('reasons_bull', []) or ['None detected']:
            tk.Label(bull_f, text=f"  • {reason}", font=('Arial', 8),
                     bg=CARD, fg=TEXT, anchor='w', wraplength=300).pack(anchor='w')
        tk.Label(bear_f, text="🔴 Bearish signals", font=('Arial', 9, 'bold'),
                 bg=CARD, fg=RED).pack(anchor='w')
        for reason in r.get('reasons_bear', []) or ['None detected']:
            tk.Label(bear_f, text=f"  • {reason}", font=('Arial', 8),
                     bg=CARD, fg=TEXT, anchor='w', wraplength=300).pack(anchor='w')

        # ════════════════════════════════════════════════════════════════
        # SECTION 3 — Indicators (RSI, MACD, EMAs, BB, ATR, Volume)
        # ════════════════════════════════════════════════════════════════
        ind_f = tk.Frame(self.cp, bg=CARD, pady=10); ind_f.pack(fill='x', padx=6, pady=4)
        tk.Label(ind_f, text="📈  Technical Indicators",
                 font=('Arial', 10, 'bold'), bg=CARD, fg=TEXT).pack(anchor='w', padx=10)
        tk.Frame(ind_f, bg=BORDER, height=1).pack(fill='x', padx=8, pady=(4,6))

        grid_f = tk.Frame(ind_f, bg=CARD); grid_f.pack(fill='x', padx=6)

        rsi_val = r['rsi']
        rsi_col = GREEN if 40 <= rsi_val <= 70 else YELLOW if rsi_val > 70 else RED
        rsi_tag = "Bullish" if 50 < rsi_val <= 70 else "Overbought" if rsi_val > 70 else "Oversold" if rsi_val < 30 else "Neutral"

        indicators = [
            ("RSI (14)",      f"{rsi_val}",
             f"{rsi_tag}",    rsi_col),
            ("MACD",          f"{r['macd']:+.2f}",
             r['macd_cross'], GREEN if r['macd_cross']=='Bullish' else RED),
            ("MACD Signal",   f"{r['signal']:+.2f}",
             "Above=Bullish", SUBTEXT),
            ("EMA 20",        f"₹{r['ema20']:.1f}",
             "Bullish" if r['cur'] > r['ema20'] else "Bearish",
             GREEN if r['cur'] > r['ema20'] else RED),
            ("EMA 50",        f"₹{r['ema50']:.1f}",
             "Bullish" if r['cur'] > r['ema50'] else "Bearish",
             GREEN if r['cur'] > r['ema50'] else RED),
            ("EMA 200",       f"₹{r['ema200']:.1f}" if r['ema200'] else "N/A",
             "Bullish" if r['ema200'] and r['cur'] > r['ema200'] else "Bearish" if r['ema200'] else "N/A",
             GREEN if r['ema200'] and r['cur'] > r['ema200'] else RED),
            ("BB Position",   f"{r['bb_pct']:.0f}%",
             "Upper" if r['bb_pct']>66 else "Middle" if r['bb_pct']>33 else "Lower",
             GREEN if r['bb_pct'] > 60 else RED if r['bb_pct'] < 30 else YELLOW),
            ("ATR (14)",      f"₹{r['atr']:.1f} ({r['atr_pct']:.1f}%)",
             "High Vol" if r['atr_pct']>3 else "Low Vol",
             ORANGE if r['atr_pct']>3 else SUBTEXT),
            ("Volume Ratio",  f"{r['vol_ratio']}x avg",
             "High Volume 🔥" if r['vol_surge'] else "Normal",
             GREEN if r['vol_surge'] else SUBTEXT),
            ("EMA Alignment", "✅ Aligned" if r['ema_align'] else "❌ Not Aligned",
             "Uptrend confirmed" if r['ema_align'] else "No clear trend",
             GREEN if r['ema_align'] else RED),
        ]

        for i, (name, val, tag, col) in enumerate(indicators):
            row_idx = i // 2
            col_idx = i % 2
            cell = tk.Frame(grid_f, bg=CARD2, padx=10, pady=8)
            cell.grid(row=row_idx, column=col_idx, padx=3, pady=3, sticky='nsew')
            grid_f.columnconfigure(col_idx, weight=1)
            name_f = tk.Frame(cell, bg=CARD2); name_f.pack(fill='x')
            tk.Label(name_f, text=name, font=('Arial', 8, 'bold'),
                     bg=CARD2, fg=SUBTEXT).pack(side='left')
            tk.Label(name_f, text=tag, font=('Arial', 8),
                     bg=CARD2, fg=col).pack(side='right')
            tk.Label(cell, text=val, font=('Arial', 12, 'bold'),
                     bg=CARD2, fg=col).pack(anchor='w')

        # ════════════════════════════════════════════════════════════════
        # SECTION 4 — Candlestick Patterns
        # ════════════════════════════════════════════════════════════════
        cp_f = tk.Frame(self.cp, bg=CARD, pady=10); cp_f.pack(fill='x', padx=6, pady=4)
        tk.Label(cp_f, text="🕯️  Candlestick Patterns (Last Candle)",
                 font=('Arial', 10, 'bold'), bg=CARD, fg=TEXT).pack(anchor='w', padx=10)
        tk.Frame(cp_f, bg=BORDER, height=1).pack(fill='x', padx=8, pady=(4,6))
        for pname, icon, col, desc in r['patterns']:
            prow = tk.Frame(cp_f, bg=CARD2, pady=8); prow.pack(fill='x', padx=8, pady=2)
            tk.Label(prow, text=icon, font=('Arial', 14), bg=CARD2).pack(side='left', padx=(10,6))
            tk.Label(prow, text=pname, font=('Arial', 11, 'bold'), bg=CARD2, fg=col).pack(side='left')
            tk.Label(prow, text=f"  —  {desc}", font=('Arial', 9), bg=CARD2, fg=SUBTEXT).pack(side='left')

        # ════════════════════════════════════════════════════════════════
        # SECTION 5 — Chart Patterns
        # ════════════════════════════════════════════════════════════════
        chp_f = tk.Frame(self.cp, bg=CARD, pady=10); chp_f.pack(fill='x', padx=6, pady=4)
        tk.Label(chp_f, text="📊  Chart Patterns",
                 font=('Arial', 10, 'bold'), bg=CARD, fg=TEXT).pack(anchor='w', padx=10)
        tk.Frame(chp_f, bg=BORDER, height=1).pack(fill='x', padx=8, pady=(4,6))
        for pname, icon, col, desc in r['chart_patterns']:
            prow = tk.Frame(chp_f, bg=CARD2, pady=8); prow.pack(fill='x', padx=8, pady=2)
            tk.Label(prow, text=icon, font=('Arial', 14), bg=CARD2).pack(side='left', padx=(10,6))
            tk.Label(prow, text=pname, font=('Arial', 11, 'bold'), bg=CARD2, fg=col).pack(side='left')
            tk.Label(prow, text=f"  —  {desc}", font=('Arial', 9), bg=CARD2, fg=SUBTEXT).pack(side='left')

        # ════════════════════════════════════════════════════════════════
        # SECTION 6 — Support & Resistance + Target/SL (side by side)
        # ════════════════════════════════════════════════════════════════
        bottom_row = tk.Frame(self.cp, bg=BG); bottom_row.pack(fill='x', padx=6, pady=4)
        bottom_row.columnconfigure(0, weight=1); bottom_row.columnconfigure(1, weight=1)

        # Support & Resistance
        sr_f = tk.Frame(bottom_row, bg=CARD, pady=10)
        sr_f.grid(row=0, column=0, padx=(0,3), sticky='nsew')
        tk.Label(sr_f, text="📉  Support & Resistance",
                 font=('Arial', 10, 'bold'), bg=CARD, fg=TEXT).pack(anchor='w', padx=10)
        tk.Frame(sr_f, bg=BORDER, height=1).pack(fill='x', padx=8, pady=(4,6))
        cur_price = r['cur']
        sr_items = [
            ('R2 (Strong)',   r['r2'],      RED,    '🔴'),
            ('R1 (Resistance)', r['r1'],    ORANGE, '🟠'),
            ('Pivot',         r['pivot'],   YELLOW, '🟡'),
            ('Current Price', cur_price,    ACCENT, '🔵'),
            ('S1 (Support)',  r['s1'],      GREEN,  '🟢'),
            ('S2 (Strong)',   r['s2'],      GREEN,  '🟢'),
            ('52W High',      r['high52'],  PURPLE, '⬆️'),
            ('52W Low',       r['low52'],   PURPLE, '⬇️'),
        ]
        for label, val, col, icon in sr_items:
            srow = tk.Frame(sr_f, bg=CARD2 if label == 'Current Price' else CARD)
            srow.pack(fill='x', padx=8, pady=1)
            tk.Label(srow, text=icon, font=('Arial', 9), bg=srow.cget('bg')).pack(side='left', padx=(8,4), pady=5)
            tk.Label(srow, text=label, font=('Arial', 9, 'bold' if label=='Current Price' else 'normal'),
                     bg=srow.cget('bg'), fg=TEXT).pack(side='left')
            tk.Label(srow, text=f"₹{val:.2f}", font=('Arial', 10, 'bold'),
                     bg=srow.cget('bg'), fg=col).pack(side='right', padx=10)

        # Target & Stop Loss
        tsl_f = tk.Frame(bottom_row, bg=CARD, pady=10)
        tsl_f.grid(row=0, column=1, padx=(3,0), sticky='nsew')
        tk.Label(tsl_f, text="🎯  Target Price & Stop Loss (ATR-based)",
                 font=('Arial', 10, 'bold'), bg=CARD, fg=TEXT).pack(anchor='w', padx=10)
        tk.Frame(tsl_f, bg=BORDER, height=1).pack(fill='x', padx=8, pady=(4,6))

        tsl_items = [
            ('Entry (Current)',     cur_price,    ACCENT,  '📍'),
            ('Stop Loss (2×ATR)',   r['sl'],      RED,     '🛑'),
            ('Target 1 (2×ATR)',   r['tgt1'],    GREEN,   '🎯'),
            ('Target 2 (4×ATR)',   r['tgt2'],    GREEN,   '🚀'),
            ('Risk:Reward',        f"1 : {r['rr']:.1f}", YELLOW if r['rr']>1.5 else RED, '⚖️'),
            ('ATR Value',          f"₹{r['atr']:.2f}", SUBTEXT, '📏'),
        ]
        for label, val, col, icon in tsl_items:
            trow = tk.Frame(tsl_f, bg=CARD2 if 'Entry' in label else CARD)
            trow.pack(fill='x', padx=8, pady=2)
            tk.Label(trow, text=icon, font=('Arial', 9), bg=trow.cget('bg')).pack(side='left', padx=(8,4), pady=6)
            tk.Label(trow, text=label, font=('Arial', 9), bg=trow.cget('bg'), fg=TEXT).pack(side='left')
            disp = val if isinstance(val, str) else f"₹{val:.2f}"
            tk.Label(trow, text=disp, font=('Arial', 11, 'bold'),
                     bg=trow.cget('bg'), fg=col).pack(side='right', padx=10)

        # RR quality note
        rr = r['rr']
        rr_note = "✅ Excellent RR!" if rr>=2 else "👍 Good RR" if rr>=1.5 else "⚠️ Weak RR — skip ya wait karo"
        tk.Label(tsl_f, text=rr_note, font=('Arial', 9, 'italic'),
                 bg=CARD, fg=GREEN if rr>=2 else YELLOW if rr>=1.5 else RED).pack(pady=(4,0))

        # ════════════════════════════════════════════════════════════════
        # SECTION 7 — Valuation Meter
        # ════════════════════════════════════════════════════════════════
        vm_f = tk.Frame(self.cp, bg=CARD, pady=12); vm_f.pack(fill='x', padx=6, pady=4)
        tk.Label(vm_f, text="💰  Valuation Meter",
                 font=('Arial', 10, 'bold'), bg=CARD, fg=TEXT).pack(anchor='w', padx=10)
        tk.Frame(vm_f, bg=BORDER, height=1).pack(fill='x', padx=8, pady=(4,6))
        vm_row = tk.Frame(vm_f, bg=CARD); vm_row.pack(fill='x', padx=8)

        val_items = [
            ('Valuation',        r['val_label'],
             r['val_col']),
            ('P/E Ratio',        f"{fdata.get('pe'):.1f}" if fdata.get('pe') else 'N/A',
             ACCENT),
            ('Price/Book',       f"{fdata.get('price_to_book'):.2f}x" if fdata.get('price_to_book') else 'N/A',
             ACCENT),
            ('ROE',              f"{fdata.get('roe'):.1f}%" if fdata.get('roe') else 'N/A',
             GREEN if (fdata.get('roe') or 0) > 15 else YELLOW),
            ('ROCE',             f"{fdata.get('roce'):.1f}%" if fdata.get('roce') else 'N/A',
             GREEN if (fdata.get('roce') or 0) > 15 else YELLOW),
            ('Profit Growth 3Y', f"{fdata.get('profit_growth_3y'):.1f}%" if fdata.get('profit_growth_3y') else 'N/A',
             GREEN if (fdata.get('profit_growth_3y') or 0) > 15 else YELLOW),
        ]
        for i, (lbl, val, col) in enumerate(val_items):
            vc = tk.Frame(vm_row, bg=CARD2, padx=10, pady=10)
            vc.grid(row=0, column=i, padx=3, sticky='nsew')
            vm_row.columnconfigure(i, weight=1)
            tk.Label(vc, text=lbl, font=('Arial', 8), bg=CARD2, fg=SUBTEXT).pack()
            tk.Label(vc, text=val, font=('Arial', 11, 'bold'), bg=CARD2, fg=col).pack()

        # ── Disclaimer ────────────────────────────────────────────────────────
        disc_f = tk.Frame(self.cp, bg='#0A0D1A', pady=8)
        disc_f.pack(fill='x', padx=4, pady=(4, 10))
        tk.Label(disc_f,
                 text="⚠️  Yeh analysis sirf educational purpose ke liye hai. "
                      "Investment decision apni research aur risk tolerance ke basis pe lo.",
                 font=('Arial', 8, 'italic'), bg='#0A0D1A', fg=SUBTEXT,
                 wraplength=800).pack()
        # Scroll to top after render
        try:
            p = self.cp.master
            while p:
                if isinstance(p, tk.Canvas):
                    self.root.after(100, lambda c=p: c.yview_moveto(0)); break
                p = getattr(p, 'master', None)
        except: pass


if __name__ == '__main__':
    root = tk.Tk()
    s = ttk.Style(); s.theme_use('clam')
    s.configure('Vertical.TScrollbar', background=BORDER, troughcolor=BG,
                arrowcolor=SUBTEXT, bordercolor=BG)
    App(root)
    root.mainloop()