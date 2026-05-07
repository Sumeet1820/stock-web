"""
Screener.in saved screens fetcher
Directly aapke 3 saved screens se data fetch karta hai.
No individual stock pages needed — sab ek hi request mein.
"""
import requests
import re
import time
from bs4 import BeautifulSoup

# ── COOKIES ───────────────────────────────────────────────────────────────────
COOKIES = {
    'csrftoken': 'cpbc8YWupQ9GW6MpSTd46mbz7p4MNX3b',
    'sessionid': 'gbt9m8dzpgseo1qwzxdf2loz2zrmxzxq',
}

# ── AAPKE SAVED SCREENS ───────────────────────────────────────────────────────
SCREEN_URLS = {
    # ── Aapke OG screens ──────────────────────────────────────────────────────
    'swing':      'https://www.screener.in/screens/3644250/my-og-swing-scanner/',
    'positional': 'https://www.screener.in/screens/3644263/my-og-positional-scanner/',
    'longterm':   'https://www.screener.in/screens/3644287/my-og-longterm-scanner/',
}

# ── EXPLORE SCREENS (optional extra categories) ───────────────────────────────
EXPLORE_SCREENS = {
    'piotroski':       ('Piotroski Score 9',    'https://www.screener.in/screens/2/piotroski-scan/'),
    'magic_formula':   ('Magic Formula',         'https://www.screener.in/screens/59/magic-formula/'),
    'coffee_can':      ('Coffee Can Portfolio',  'https://www.screener.in/screens/57601/coffee-can-portfolio/'),
    'quarterly_grow':  ('Quarterly Growers',     'https://www.screener.in/screens/86/quarterly-growers/'),
    'fii_buying':      ('FII Buying',            'https://www.screener.in/screens/343087/fii-buying/'),
    'bull_cartel':     ('The Bull Cartel',       'https://www.screener.in/screens/1/the-bull-cartel/'),
    'darvas':          ('Darvas Scan',           'https://www.screener.in/screens/4928/darvas-scan/'),
    'golden_cross':    ('Golden Crossover',      'https://www.screener.in/screens/336509/golden-crossover/'),
    'capacity_exp':    ('Capacity Expansion',    'https://www.screener.in/screens/97687/capacity-expansion/'),
    'debt_reduction':  ('Debt Reduction',        'https://www.screener.in/screens/126864/debt-reduction/'),
    'new_high':        ('52W New High',          'https://www.screener.in/screens/214283/companies-creating-new-high/'),
    'rsi_oversold':    ('RSI Oversold',          'https://www.screener.in/screens/985942/rsi-oversold-stocks/'),
    'growth_nodilute': ('Growth No Dilution',    'https://www.screener.in/screens/226712/growth-without-dilution/'),
    'price_volume':    ('Price Volume Action',   'https://www.screener.in/screens/440753/price-volume-action/'),
    # Aapke AI screens
    'chatgpt_swing':   ('ChatGPT Swing',         'https://www.screener.in/screens/3400408/chat-gpt-swing-scanner/'),
    'chatgpt_pos':     ('ChatGPT Positional',    'https://www.screener.in/screens/3400436/chat-gpt-positional/'),
    'chatgpt_lt':      ('ChatGPT Long Term',     'https://www.screener.in/screens/3400867/chat-gpt-longterm/'),
    'claude_swing':    ('Claude Swing',          'https://www.screener.in/screens/3533180/claude-swing-screener/'),
    'claude_pos':      ('Claude Positional',     'https://www.screener.in/screens/3533147/claude-positinal-screener/'),
    'claude_lt':       ('Claude Long Term',      'https://www.screener.in/screens/3533134/claude-long-term-scanner/'),
    'fund_swing':      ('Fundamental Swing',     'https://www.screener.in/screens/3317414/fundamental-for-swing/'),
    'fund_lt':         ('Fundamental Long Term', 'https://www.screener.in/screens/3318047/fundamental-screener/'),
}

BASE = 'https://www.screener.in'

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
    'Referer':    'https://www.screener.in/',
    'Accept':     'text/html,application/xhtml+xml,*/*',
})
SESSION.cookies.update(COOKIES)

# ── COLUMN MAP: screener header → our key ────────────────────────────────────
COL_MAP = {
    'name':                  'name',
    'cmp':                   'current_price',
    'current price':         'current_price',
    'mar cap':               'market_cap',
    'market cap':            'market_cap',
    'market capitalization': 'market_cap',
    'debt / eq':             'debt_to_equity',
    'debt to equity':        'debt_to_equity',
    'pledged':               'pledged',
    'pledged %':             'pledged',
    'pledged percentage':    'pledged',
    'profit var 5yrs':       'profit_growth_5y',
    'profit var 5y':         'profit_growth_5y',
    'profit growth 5years':  'profit_growth_5y',
    'profit growth 5yrs':    'profit_growth_5y',
    'sales var 5yrs':        'sales_growth_5y',
    'sales var 5y':          'sales_growth_5y',
    'sales growth 5years':   'sales_growth_5y',
    'profit var 3yrs':       'profit_growth_3y',
    'profit var 3y':         'profit_growth_3y',
    'profit growth 3years':  'profit_growth_3y',
    'sales var 3yrs':        'sales_growth_3y',
    'sales var 3y':          'sales_growth_3y',
    'sales growth 3years':   'sales_growth_3y',
    'roe':                   'roe',
    'return on equity':      'roe',
    'roce':                  'roce',
    'return on capital employed': 'roce',
    'peg':                   'peg',
    'current ratio':         'current_ratio',
    'p/e':                   'pe',
    'price to earning':      'pe',
    'ind pe':                'ind_pe',
    'prom. hold.':           'promoter_holding',
    'promoter holding':      'promoter_holding',
    'change in prom hold':   'promoter_change',
    'eps 12m':               'eps',
    'np 12m':                'net_profit',
    'net profit':            'net_profit',
    'np qtr':                'net_profit_qtr',
    'net profit qtr':        'net_profit_qtr',
    'opm':                   'operating_margin',
    'npm':                   'net_margin',
    'interest coverage':     'interest_coverage',
    'int coverage':          'interest_coverage',
    'price to book':         'price_to_book',
    'p/b':                   'price_to_book',
    'chg in fii hold':       'fii_change',
    'chg in dii hold':       'dii_change',
    'sales growth 5years':   'sales_growth_5y',
    'int cov':               'interest_coverage',
}


def _clean_num(text):
    if text is None:
        return None
    t = str(text).strip()
    if t.startswith('(') and t.endswith(')'):
        t = '-' + t[1:-1]
    t = re.sub(r'[₹,\s]', '', t)
    t = re.sub(r'(Cr|cr)\.?', '', t)
    t = t.replace('%', '').strip()
    if t in ['-', '', '--', 'N/A', 'na', 'NA', '—', '–', 'None']:
        return None
    try:
        return float(t)
    except:
        return None


def _normalize_header(raw):
    """Clean header text for matching"""
    h = raw.strip().lower()
    h = re.sub(r'\s+', ' ', h)
    # Remove units like Rs., Cr., %
    h = re.sub(r'rs\.?|cr\.?', '', h).strip()
    return h


def cookies_valid():
    """Check if cookies still work"""
    try:
        r = SESSION.get(
            'https://www.screener.in/screens/3644250/my-og-swing-scanner/',
            timeout=12, allow_redirects=True
        )
        return r.status_code == 200 and 'register' not in r.url and 'login' not in r.url
    except Exception:
        return False


def fetch_screen(category, page=1):
    """Aapke 3 main screens fetch karo"""
    base_url = SCREEN_URLS.get(category, '')
    if not base_url:
        return [], 0
    return _fetch_page(base_url, page)


def fetch_all_screens(progress_cb=None):
    """
    Teeno screens se saara data fetch karo (all pages).
    Returns: { 'swing': [...], 'positional': [...], 'longterm': [...] }
    """
    all_results = {}

    for cat in ('swing', 'positional', 'longterm'):
        if progress_cb:
            progress_cb(f'Fetching {cat} screen...')

        all_stocks = []
        page = 1

        while True:
            if progress_cb:
                progress_cb(f'[{cat}] Page {page}... ({len(all_stocks)} so far)')

            stocks, total = fetch_screen(cat, page)

            if stocks is None:
                return None   # cookies expired

            all_stocks.extend(stocks)

            # Check if done
            if len(stocks) < 50:
                break
            if total > 0 and len(all_stocks) >= total:
                break

            page += 1
            time.sleep(1.0)

        all_results[cat] = all_stocks
        if progress_cb:
            progress_cb(f'[{cat}] Done: {len(all_stocks)} stocks')

        time.sleep(1.5)   # pause between screens

    return all_results


# Legacy stubs for screener.py compatibility
SWING_QUERY      = ''
POSITIONAL_QUERY = ''
LONGTERM_QUERY   = ''

def fetch_all_screen(query, max_pages=60, delay=1.0, progress_cb=None):
    return []

def scrape_stock_detail(url):
    return {}


def fetch_explore_screen(key, max_pages=5):
    """
    Explore screen fetch karo by key.
    Returns list of stock dicts.
    """
    if key not in EXPLORE_SCREENS:
        return []
    label, url = EXPLORE_SCREENS[key]
    all_stocks = []
    for page in range(1, max_pages + 1):
        stocks, total = _fetch_page(url, page)
        if stocks is None:
            return None   # cookies expired
        all_stocks.extend(stocks)
        if len(stocks) < 50:
            break
        if total > 0 and len(all_stocks) >= total:
            break
        time.sleep(1.0)
    return all_stocks


def _fetch_page(base_url, page=1):
    """Generic page fetcher — used by both fetch_screen and fetch_explore_screen"""
    url = f'{base_url}?page={page}'
    try:
        r = SESSION.get(url, timeout=20)
        if r.status_code != 200 or 'register' in r.url or 'login' in r.url:
            return None, 0

        soup = BeautifulSoup(r.text, 'html.parser')

        # Total count
        total = 0
        for el in soup.select('#total-count, .count-total, .result-count, h2, h3, p'):
            m = re.search(r'(\d+)\s*(companies|stocks|results)', el.get_text(), re.I)
            if m:
                total = int(m.group(1))
                break

        table = soup.select_one('table.data-table')
        if not table:
            return [], total

        headers = []
        for th in table.select('th'):
            raw  = th.get_text(separator=' ', strip=True)
            norm = _normalize_header(raw)
            matched = None
            for col_key, our_key in COL_MAP.items():
                if col_key in norm or norm in col_key:
                    matched = our_key
                    break
            headers.append(matched or norm)

        stocks = []
        for tr in table.select('tr'):
            tds = tr.select('td')
            if not tds:
                continue
            stock = {}
            for i, td in enumerate(tds):
                if i >= len(headers):
                    break
                key = headers[i]
                if not key or key in ('s.no.', 'sno'):
                    continue
                if key == 'name':
                    a = td.select_one('a')
                    if a:
                        stock['name'] = a.get_text(strip=True)
                        href = a.get('href', '')
                        stock['url'] = href
                        m = re.search(r'/company/([^/]+)/', href)
                        if m:
                            stock['symbol'] = m.group(1).upper()
                else:
                    val = _clean_num(td.get_text(strip=True))
                    if val is not None:
                        stock[key] = val
            if stock.get('symbol') and stock.get('name'):
                stocks.append(stock)

        return stocks, total

    except Exception as e:
        print(f'[Page Error] {base_url} p{page}: {e}')
        return [], 0
