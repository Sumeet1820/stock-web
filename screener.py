"""
Stock Screener - Screener.in saved screens se direct data
3 screens → 3 columns, no individual stock pages needed
"""
import json, os, time, threading
from datetime import datetime

from screener_scraper import fetch_all_screens, cookies_valid

# ── CRITERIA (for display/info only — screener.in already filters) ────────────
CRITERIA = {
    'swing': [
        ('Market Cap',        'market_cap',        '> 1000 Cr',   lambda v: v > 1000),
        ('Net Profit',        'net_profit',         '> 0',         lambda v: v > 0),
        ('Net Profit Qtr',    'net_profit_qtr',     '> 0',         lambda v: v > 0),
        ('Debt to Equity',    'debt_to_equity',     '< 1',         lambda v: v < 1),
        ('Current Ratio',     'current_ratio',      '> 1',         lambda v: v > 1),
        ('Interest Coverage', 'interest_coverage',  '> 3',         lambda v: v > 3),
        ('Promoter Holding',  'promoter_holding',   '> 50%',       lambda v: v > 50),
        ('ROE',               'roe',                '> 12%',       lambda v: v > 12),
        ('Profit Growth 3Y',  'profit_growth_3y',   '> 10%',       lambda v: v > 10),
    ],
    'positional': [
        ('Market Cap',        'market_cap',        '> 1000 Cr',   lambda v: v > 1000),
        ('Net Profit',        'net_profit',         '> 0',         lambda v: v > 0),
        ('Net Profit Qtr',    'net_profit_qtr',     '> 0',         lambda v: v > 0),
        ('Debt to Equity',    'debt_to_equity',     '< 1',         lambda v: v < 1),
        ('Current Ratio',     'current_ratio',      '> 1.2',       lambda v: v > 1.2),
        ('Interest Coverage', 'interest_coverage',  '> 3',         lambda v: v > 3),
        ('Promoter Holding',  'promoter_holding',   '> 50%',       lambda v: v > 50),
        ('ROE',               'roe',                '> 15%',       lambda v: v > 15),
        ('ROCE',              'roce',               '> 15%',       lambda v: v > 15),
        ('Operating Margin',  'operating_margin',   '> 15%',       lambda v: v > 15),
        ('Sales Growth 3Y',   'sales_growth_3y',    '> 10%',       lambda v: v > 10),
        ('Profit Growth 3Y',  'profit_growth_3y',   '> 15%',       lambda v: v > 15),
    ],
    'longterm': [
        ('Market Cap',        'market_cap',        '> 2000 Cr',   lambda v: v > 2000),
        ('Net Profit',        'net_profit',         '> 0',         lambda v: v > 0),
        ('Net Profit Qtr',    'net_profit_qtr',     '> 0',         lambda v: v > 0),
        ('Debt to Equity',    'debt_to_equity',     '< 0.5',       lambda v: v < 0.5),
        ('Current Ratio',     'current_ratio',      '> 1.5',       lambda v: v > 1.5),
        ('Interest Coverage', 'interest_coverage',  '> 5',         lambda v: v > 5),
        ('Promoter Holding',  'promoter_holding',   '> 50%',       lambda v: v > 50),
        ('ROE',               'roe',                '> 20%',       lambda v: v > 20),
        ('ROCE',              'roce',               '> 20%',       lambda v: v > 20),
        ('Operating Margin',  'operating_margin',   '> 15%',       lambda v: v > 15),
        ('Net Profit Margin', 'net_margin',         '> 10%',       lambda v: v > 10),
        ('Sales Growth 3Y',   'sales_growth_3y',    '> 12%',       lambda v: v > 12),
        ('Profit Growth 3Y',  'profit_growth_3y',   '> 12%',       lambda v: v > 12),
        ('Sales Growth 5Y',   'sales_growth_5y',    '> 12%',       lambda v: v > 12),
        ('Profit Growth 5Y',  'profit_growth_5y',   '> 12%',       lambda v: v > 12),
        ('PEG Ratio',         'peg',                '< 2',         lambda v: 0 < v < 2),
        ('Price to Book',     'price_to_book',      '< 10',        lambda v: 0 < v < 10),
    ],
}

RESULTS_FILE = os.path.join(os.path.dirname(__file__), 'screener_results.json')
RESULTS_TTL  = 6 * 3600

_progress = {
    'running': False, 'total': 0, 'done': 0,
    'status': 'idle', 'message': '', 'started_at': None,
    'cookies_ok': None,
}
_progress_lock = threading.Lock()

def get_progress():
    with _progress_lock:
        return dict(_progress)

def _set_progress(**kwargs):
    with _progress_lock:
        _progress.update(kwargs)


def run_screener(symbols=None, batch_size=None, delay=1.0):
    _set_progress(
        running=True, total=3, done=0,
        status='running', message='Checking screener.in login...',
        started_at=datetime.now().isoformat(),
    )

    # Check cookies
    if not cookies_valid():
        _set_progress(
            running=False, status='error', cookies_ok=False,
            message='❌ Screener.in cookies expired! screener_scraper.py mein update karo.',
        )
        return

    _set_progress(cookies_ok=True, message='✅ Login OK. Fetching screens...')

    def _cb(msg):
        _set_progress(message=msg)

    data = fetch_all_screens(progress_cb=_cb)

    if data is None:
        _set_progress(
            running=False, status='error', cookies_ok=False,
            message='❌ Cookies expired during fetch! Please update.',
        )
        return

    # Build results
    results = {
        'swing':         _format(data.get('swing', [])),
        'positional':    _format(data.get('positional', [])),
        'longterm':      _format(data.get('longterm', [])),
        'timestamp':     datetime.now().isoformat(),
        'total_scanned': sum(len(v) for v in data.values()),
    }

    _save_results(results)
    _set_progress(
        running=False, done=3, status='done',
        message=(
            f'✅ Done! '
            f'Swing: {len(results["swing"])}, '
            f'Positional: {len(results["positional"])}, '
            f'Long Term: {len(results["longterm"])}'
        ),
    )


def _format(stocks):
    """Normalize stock list for frontend"""
    out = []
    for s in stocks:
        out.append({
            'symbol':        s.get('symbol', ''),
            'name':          s.get('name', ''),
            'sector':        s.get('sector', ''),
            'current_price': s.get('current_price'),
            'market_cap':    s.get('market_cap'),
            'roe':           s.get('roe'),
            'roce':          s.get('roce'),
            'pe':            s.get('pe'),
            'debt_to_equity':s.get('debt_to_equity'),
            'promoter_holding': s.get('promoter_holding'),
            'profit_growth_5y': s.get('profit_growth_5y'),
        })
    return out


def _save_results(results):
    try:
        with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'[Save Error] {e}')


def load_results():
    if not os.path.exists(RESULTS_FILE):
        return None
    try:
        with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


def results_are_fresh():
    if not os.path.exists(RESULTS_FILE):
        return False
    try:
        with open(RESULTS_FILE, 'r') as f:
            d = json.load(f)
        ts = datetime.fromisoformat(d.get('timestamp', '2000-01-01'))
        return (datetime.now() - ts).total_seconds() < RESULTS_TTL
    except:
        return False

# Legacy stubs
def fetch_nse_large_caps(min_cap_cr=500): return []
def fetch_nse_all_symbols_fallback(): return []
PER_STOCK_DELAY = 1.0
