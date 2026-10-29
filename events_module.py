"""
events_module.py — StockPro Events Calendar
Pichle 15 din + aane wale 30 din: Results, Dividend, Split, Bonus, Rights, Buyback, AGM, Board Meetings.

app.py me sirf ye 2 lines add karo (app = Flask(...) ke baad):
    from events_module import register_events
    register_events(app, NSE_SESSION, _login_required, _user_data)

NOTE: NSE ke endpoints unofficial hain — kabhi bhi change/block ho sakte hain.
Pehli baar chalake /api/events?debug=1 kholo aur check karo raw fields aa rahe hain ya nahi.
"""
import datetime, re, threading
from flask import jsonify, request

CACHE_TTL_SEC = 3 * 3600          # 3 ghante cache
_cache = {}                       # key -> {'ts': datetime, 'data': [...]}
_lock = threading.Lock()

NSE_HOME = "https://www.nseindia.com"
URL_BOARD = NSE_HOME + "/api/corporate-board-meetings"
URL_ACTIONS = NSE_HOME + "/api/corporates-corporateActions"
URL_CALENDAR = NSE_HOME + "/api/event-calendar"


def _pick(d, *keys):
    for k in keys:
        v = d.get(k)
        if v not in (None, '', '-'):
            return v
    return ''


def _parse_date(s):
    s = str(s).strip()
    for fmt in ('%d-%b-%Y', '%d-%m-%Y', '%Y-%m-%d', '%d-%b-%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%d %b %Y'):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None


def _classify(text):
    t = (text or '').lower()
    if 'dividend' in t: return 'dividend'
    if 'split' in t or 'sub-division' in t or 'subdivision' in t or 'sub division' in t: return 'split'
    if 'bonus' in t: return 'bonus'
    if 'rights' in t: return 'rights'
    if 'buyback' in t or 'buy back' in t or 'buy-back' in t: return 'buyback'
    if 'result' in t: return 'results'
    if 'general meeting' in t or 'agm' in t: return 'agm'
    if 'fund' in t or 'raising' in t: return 'fundraise'
    return 'other'


def register_events(app, nse_session, login_required, user_data_fn):

    def nse_get(url, params):
        try:
            nse_session.get(NSE_HOME, timeout=8)  # cookies refresh
            r = nse_session.get(url, params=params, timeout=15)
            if r.status_code == 200:
                j = r.json()
                if isinstance(j, dict):
                    return j.get('data', []) or []
                return j or []
            print(f"[events] {url} -> HTTP {r.status_code}")
        except Exception as ex:
            print(f"[events] {url} -> {ex}")
        return []

    def build(frm, to, debug=False):
        p = {'index': 'equities',
             'from_date': frm.strftime('%d-%m-%Y'),
             'to_date': to.strftime('%d-%m-%Y')}
        events, raw = [], {}

        rows = nse_get(URL_BOARD, p); raw['board'] = rows[:2]
        for r in rows:
            d = _parse_date(_pick(r, 'bm_date', 'date'))
            if not d: continue
            purpose = str(_pick(r, 'bm_purpose', 'purpose'))
            desc = str(_pick(r, 'bm_desc', 'bm_description', 'desc'))
            events.append({'date': d.isoformat(), 'symbol': str(_pick(r, 'bm_symbol', 'symbol')).upper(),
                           'company': str(_pick(r, 'sm_name', 'comp', 'company')),
                           'type': _classify(purpose + ' ' + desc), 'title': purpose or 'Board Meeting',
                           'detail': desc[:220], 'status': 'intimation'})

        rows = nse_get(URL_CALENDAR, p); raw['calendar'] = rows[:2]
        for r in rows:
            d = _parse_date(_pick(r, 'date', 'bm_date'))
            if not d: continue
            purpose = str(_pick(r, 'purpose', 'bm_purpose'))
            desc = str(_pick(r, 'bm_desc', 'desc'))
            events.append({'date': d.isoformat(), 'symbol': str(_pick(r, 'symbol')).upper(),
                           'company': str(_pick(r, 'company', 'comp', 'sm_name')),
                           'type': _classify(purpose + ' ' + desc), 'title': purpose or 'Event',
                           'detail': desc[:220], 'status': 'intimation'})

        rows = nse_get(URL_ACTIONS, p); raw['actions'] = rows[:2]
        for r in rows:
            d = _parse_date(_pick(r, 'exDate', 'ex_date'))
            if not d: continue
            subject = str(_pick(r, 'subject', 'purpose'))
            rec = str(_pick(r, 'recDate', 'record_date'))
            events.append({'date': d.isoformat(), 'symbol': str(_pick(r, 'symbol')).upper(),
                           'company': str(_pick(r, 'comp', 'company')),
                           'type': _classify(subject), 'title': subject,
                           'detail': ('Ex-date. Record: ' + rec) if rec else 'Ex-date',
                           'status': 'confirmed'})

        # duplicates hatao (same date+symbol+type) — confirmed ko priority
        seen = {}
        for e in events:
            k = (e['date'], e['symbol'], e['type'])
            if k not in seen or e['status'] == 'confirmed':
                seen[k] = e
        out = sorted(seen.values(), key=lambda e: (e['date'], e['symbol']))
        return (out, raw) if debug else (out, None)

    def my_symbols():
        """Watchlist + trades ke symbols (data shape pata nahi, isliye defensive)."""
        syms = set()
        try:
            ud = user_data_fn() or {}
            wl = ud.get('watchlist', {})
            if isinstance(wl, dict): syms |= {str(k).upper() for k in wl.keys()}
            elif isinstance(wl, list): syms |= {str(x).upper() for x in wl if isinstance(x, str)}

            def walk(o):
                if isinstance(o, dict):
                    for k, v in o.items():
                        if k in ('symbol', 'sym') and isinstance(v, str): syms.add(v.upper())
                        else: walk(v)
                elif isinstance(o, list):
                    for i in o: walk(i)
            walk(ud.get('trades', {}))
            if isinstance(ud.get('trades'), dict):
                for k in ud['trades'].keys():
                    if re.fullmatch(r'[A-Za-z0-9&\-]{2,20}', str(k)): syms.add(str(k).upper())
        except Exception as ex:
            print(f"[events] my_symbols: {ex}")
        return syms

    @app.route('/api/events')
    @login_required
    def api_events():
        back = max(0, min(int(request.args.get('back', 15)), 60))
        fwd = max(0, min(int(request.args.get('fwd', 30)), 90))
        debug = request.args.get('debug') == '1'
        today = datetime.date.today()
        key = (back, fwd)

        with _lock:
            c = _cache.get(key)
            fresh = c and (datetime.datetime.now() - c['ts']).total_seconds() < CACHE_TTL_SEC
        if fresh and not debug and request.args.get('refresh') != '1':
            events, raw = c['data'], None
        else:
            events, raw = build(today - datetime.timedelta(days=back),
                                today + datetime.timedelta(days=fwd), debug)
            if events:  # khaali result se purana cache overwrite mat karo
                with _lock:
                    _cache[key] = {'ts': datetime.datetime.now(), 'data': events}
            elif c:
                events = c['data']  # NSE fail hua to purana data dikhao

        mine = my_symbols()
        out = []
        for e in events:
            e = dict(e); e['mine'] = e['symbol'] in mine
            out.append(e)
        if request.args.get('mine') == '1':
            out = [e for e in out if e['mine']]
        t = request.args.get('type', '')
        if t:
            wanted = set(t.split(','))
            out = [e for e in out if e['type'] in wanted]

        resp = {'today': today.isoformat(), 'count': len(out), 'events': out,
                'updated': datetime.datetime.now().strftime('%d %b %H:%M')}
        if debug: resp['raw_sample'] = raw
        return jsonify(resp)
