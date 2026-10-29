/* events.js — StockPro Events Calendar (self-contained panel)
   index.html me </body> se pehle add karo:
   <script src="/static/js/events.js"></script>
   Sidebar me "📅 Events" item khud add ho jayega (Intraday ke neeche). Na mile to floating button aayega. */
(function () {
  const TYPES = {
    results:   ['📊 Results', '#3b82f6'],
    dividend:  ['💰 Dividend', '#10b981'],
    split:     ['✂️ Split', '#f59e0b'],
    bonus:     ['🎁 Bonus', '#a855f7'],
    rights:    ['📜 Rights', '#06b6d4'],
    buyback:   ['🔁 Buyback', '#ec4899'],
    agm:       ['🏛️ AGM', '#94a3b8'],
    fundraise: ['🏦 Fund Raise', '#f97316'],
    other:     ['📌 Other', '#64748b'],
  };
  let state = { type: 'all', mine: false, data: null, q: '' };

  const css = `
  #ev-panel{position:fixed;inset:0;background:#070b14;z-index:9999;overflow:auto;color:#e5e7eb;font-family:inherit;display:none}
  #ev-panel .ev-wrap{max-width:1000px;margin:0 auto;padding:14px}
  #ev-panel .ev-top{display:flex;align-items:center;gap:10px;justify-content:space-between;flex-wrap:wrap}
  #ev-panel button.ev-chip{background:#101a2e;border:1px solid #1e2b47;color:#cbd5e1;border-radius:999px;padding:6px 12px;font-size:13px;cursor:pointer}
  #ev-panel button.ev-chip.on{background:#2563eb;border-color:#2563eb;color:#fff}
  #ev-panel .ev-chips{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}
  #ev-panel input{background:#101a2e;border:1px solid #1e2b47;color:#e5e7eb;border-radius:8px;padding:7px 10px;width:100%;max-width:260px}
  #ev-panel .ev-day{margin:16px 0 6px;font-weight:700;font-size:14px;color:#93c5fd;position:sticky;top:0;background:#070b14;padding:4px 0}
  #ev-panel .ev-day.today{color:#34d399}
  #ev-panel .ev-row{display:flex;gap:10px;align-items:flex-start;background:#0d1526;border:1px solid #16223b;border-radius:10px;padding:9px 11px;margin-bottom:6px}
  #ev-panel .ev-row.mine{border-color:#f59e0b;box-shadow:0 0 0 1px #f59e0b55}
  #ev-panel .ev-sym{font-weight:700;color:#60a5fa;min-width:92px;cursor:pointer}
  #ev-panel .ev-tag{font-size:11px;padding:2px 8px;border-radius:999px;color:#fff;white-space:nowrap}
  #ev-panel .ev-sub{font-size:12px;color:#94a3b8;margin-top:3px}
  #ev-panel .ev-past{opacity:.7}
  #ev-float{position:fixed;right:14px;bottom:70px;z-index:9998;background:#2563eb;color:#fff;border:0;border-radius:999px;padding:10px 14px;cursor:pointer}`;
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  const panel = document.createElement('div'); panel.id = 'ev-panel';
  panel.innerHTML = `<div class="ev-wrap">
    <div class="ev-top"><h2 style="margin:0">📅 Events Calendar <span style="font-size:12px;color:#94a3b8;font-weight:400">(pichle 15 din → agle 30 din)</span></h2>
      <div><button class="ev-chip" id="ev-refresh">🔄 Refresh</button> <button class="ev-chip" id="ev-close">✕ Close</button></div></div>
    <div class="ev-chips" id="ev-chips"></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center"><input id="ev-q" placeholder="Symbol search..."><button class="ev-chip" id="ev-mine">⭐ Sirf meri Watchlist/Trades</button><span id="ev-upd" style="font-size:12px;color:#64748b"></span></div>
    <div id="ev-list" style="margin-top:6px">Loading...</div></div>`;
  document.body.appendChild(panel);

  function chips() {
    const box = panel.querySelector('#ev-chips');
    const all = [['all', 'Sab']].concat(Object.keys(TYPES).map(k => [k, TYPES[k][0]]));
    box.innerHTML = all.map(([k, l]) => `<button class="ev-chip ${state.type === k ? 'on' : ''}" data-t="${k}">${l}</button>`).join('');
    box.querySelectorAll('button').forEach(b => b.onclick = () => { state.type = b.dataset.t; chips(); render(); });
  }
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  function render() {
    const list = panel.querySelector('#ev-list');
    if (!state.data) return;
    const today = state.data.today;
    let ev = state.data.events.filter(e =>
      (state.type === 'all' || e.type === state.type) &&
      (!state.mine || e.mine) &&
      (!state.q || (e.symbol + ' ' + e.company).toLowerCase().includes(state.q)));
    panel.querySelector('#ev-upd').textContent = `${ev.length} events • updated ${state.data.updated}`;
    if (!ev.length) { list.innerHTML = '<p style="color:#94a3b8">Koi event nahi mila.</p>'; return; }
    let html = '', cur = '';
    ev.forEach(e => {
      if (e.date !== cur) {
        cur = e.date;
        const d = new Date(e.date + 'T00:00:00');
        const diff = Math.round((d - new Date(today + 'T00:00:00')) / 864e5);
        const lbl = diff === 0 ? 'AAJ' : diff > 0 ? `${diff} din baad` : `${-diff} din pehle`;
        html += `<div class="ev-day ${diff === 0 ? 'today' : ''}">${d.toDateString().slice(0, 10)} • ${lbl}</div>`;
      }
      const [tl, tc] = TYPES[e.type] || TYPES.other;
      const past = e.date < today ? 'ev-past' : '';
      html += `<div class="ev-row ${e.mine ? 'mine' : ''} ${past}">
        <div class="ev-sym" data-s="${esc(e.symbol)}">${esc(e.symbol)}${e.mine ? ' ⭐' : ''}</div>
        <div style="flex:1"><span class="ev-tag" style="background:${tc}">${tl}</span>
          <span class="ev-tag" style="background:${e.status === 'confirmed' ? '#047857' : '#475569'}">${e.status === 'confirmed' ? 'Confirmed' : 'Intimation'}</span>
          <div style="margin-top:4px">${esc(e.title)}</div>
          <div class="ev-sub">${esc(e.company)}${e.detail ? ' • ' + esc(e.detail) : ''}</div></div></div>`;
    });
    list.innerHTML = html;
    list.querySelectorAll('.ev-sym').forEach(el => el.onclick = () => {
      panel.style.display = 'none';
      // Tumhare app ka stock-open function yahan call karo; fallback = search box
      const inp = document.querySelector('input[placeholder*="Stock search"]');
      if (inp) { inp.value = el.dataset.s; inp.dispatchEvent(new Event('input', { bubbles: true })); inp.focus(); }
    });
  }

  async function load(refresh) {
    panel.querySelector('#ev-list').textContent = 'Loading...';
    try {
      const r = await fetch('/api/events?back=15&fwd=30' + (refresh ? '&refresh=1' : ''));
      if (r.status === 401) { location.href = '/login'; return; }
      state.data = await r.json(); render();
    } catch (e) { panel.querySelector('#ev-list').textContent = 'Events load nahi hue: ' + e; }
  }

  function open() { panel.style.display = 'block'; chips(); if (!state.data) load(); }
  panel.querySelector('#ev-close').onclick = () => panel.style.display = 'none';
  panel.querySelector('#ev-refresh').onclick = () => load(true);
  panel.querySelector('#ev-mine').onclick = function () { state.mine = !state.mine; this.classList.toggle('on', state.mine); render(); };
  panel.querySelector('#ev-q').oninput = e => { state.q = e.target.value.toLowerCase(); render(); };

  window.openEventsCalendar = open;

  // Sidebar me item add karo (Intraday ko clone karke)
  window.addEventListener('load', () => {
    const cand = [...document.querySelectorAll('a,li,div,button')].filter(el => el.children.length <= 3 && /^\s*\S*\s*Intraday\s*$/.test(el.textContent));
    const base = cand[cand.length - 1];
    if (base && base.parentElement) {
      const n = base.cloneNode(true);
      n.removeAttribute('onclick'); n.classList.remove('active');
      n.innerHTML = n.innerHTML.replace(/Intraday/, 'Events').replace(/⚡/, '📅');
      n.addEventListener('click', e => { e.preventDefault(); e.stopPropagation(); open(); });
      base.parentElement.appendChild(n);
    } else {
      const b = document.createElement('button'); b.id = 'ev-float'; b.textContent = '📅 Events';
      b.onclick = open; document.body.appendChild(b);
    }
  });
})();
