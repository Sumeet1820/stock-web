/* sectors.js — StockPro Sector Momentum (self-contained panel)
   index.html me </body> se pehle add karo:
   <script src="/static/js/sectors.js"></script>
   Sidebar me "🔥 Sectors" item khud add ho jayega (Events ke neeche). Na mile to floating button aayega.
   NOTE: Ye future predict nahi karta. Data-based momentum / rotation scan hai (Nifty ke muqable relative strength). */
(function () {
  const GROUPS = [
    ['boom',   '🔥 Booming Now',        'Lambe samay se Nifty se aage + trend mazboot',                      '#16a34a'],
    ['early',  '🌱 Early Rotation (nazar rakho)', 'Abhi-abhi Nifty se aage nikalna shuru — pehle peeche/barabar tha', '#2563eb'],
    ['fading', '⚠️ Fading (chase mat karo)',     'Pehle leader tha, ab strength kam ho rahi hai',                '#d97706'],
    ['weak',   '❄️ Weak / Peeche',      'Nifty se peeche ya trend kamzor',                                  '#64748b'],
  ];
  const state = { sort: 'score', data: null, open: {} };

  const css = `
  #sc-panel{position:fixed;inset:0;background:#070b14;z-index:9999;overflow:auto;color:#e5e7eb;font-family:inherit;display:none}
  #sc-panel .sc-wrap{max-width:1000px;margin:0 auto;padding:14px}
  #sc-panel .sc-top{display:flex;align-items:center;gap:10px;justify-content:space-between;flex-wrap:wrap}
  #sc-panel button.sc-chip{background:#101a2e;border:1px solid #1e2b47;color:#cbd5e1;border-radius:999px;padding:6px 12px;font-size:13px;cursor:pointer}
  #sc-panel button.sc-chip.on{background:#2563eb;border-color:#2563eb;color:#fff}
  #sc-panel .sc-chips{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}
  #sc-panel .sc-grp{margin:18px 0 6px;font-weight:700;font-size:15px}
  #sc-panel .sc-grp small{display:block;font-weight:400;font-size:12px;color:#94a3b8;margin-top:2px}
  #sc-panel .sc-card{background:#0d1526;border:1px solid #16223b;border-radius:12px;padding:10px 12px;margin-bottom:8px}
  #sc-panel .sc-head{display:flex;justify-content:space-between;align-items:center;gap:8px}
  #sc-panel .sc-name{font-weight:700;font-size:15px}
  #sc-panel .sc-score{font-size:12px;padding:2px 9px;border-radius:999px;color:#fff;font-weight:700}
  #sc-panel .sc-rets{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:8px 0 6px}
  #sc-panel .sc-ret{background:#101a2e;border-radius:8px;padding:5px 4px;text-align:center}
  #sc-panel .sc-ret span{display:block;font-size:10px;color:#94a3b8}
  #sc-panel .sc-ret b{font-size:13px}
  #sc-panel .sc-sub{font-size:12px;color:#94a3b8;margin-top:3px;line-height:1.45}
  #sc-panel .sc-flags{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
  #sc-panel .sc-flag{font-size:11px;padding:2px 8px;border-radius:999px;background:#101a2e;border:1px solid #1e2b47}
  #sc-panel .sc-btn{margin-top:8px;background:#101a2e;border:1px solid #1e2b47;color:#93c5fd;border-radius:8px;padding:6px 10px;font-size:12px;cursor:pointer}
  #sc-panel .sc-stocks{margin-top:8px;display:grid;grid-template-columns:repeat(2,1fr);gap:6px}
  #sc-panel .sc-stk{background:#101a2e;border-radius:8px;padding:6px 8px;display:flex;justify-content:space-between;font-size:12px;cursor:pointer}
  #sc-panel .sc-up{color:#34d399}#sc-panel .sc-dn{color:#f87171}
  #sc-float{position:fixed;right:14px;bottom:120px;z-index:9998;background:#16a34a;color:#fff;border:0;border-radius:999px;padding:10px 14px;cursor:pointer}`;
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  const panel = document.createElement('div'); panel.id = 'sc-panel';
  panel.innerHTML = `<div class="sc-wrap">
    <div class="sc-top"><h2 style="margin:0">🔥 Sector Momentum</h2>
      <div><button class="sc-chip" id="sc-refresh">🔄 Refresh</button> <button class="sc-chip" id="sc-close">✕ Close</button></div></div>
    <div id="sc-ctx" style="font-size:12px;color:#94a3b8;margin-top:6px"></div>
    <div class="sc-chips" id="sc-sort"></div>
    <div id="sc-list">Loading...</div>
    <div style="margin-top:18px;font-size:11px;color:#64748b;line-height:1.5">⚠️ Ye <b>future predict nahi karta</b>. Ye Nifty 50 ke muqable sector ki relative strength, trend (50/200 DMA) aur momentum par based data-scan hai. "Early Rotation" sirf nazar rakhne ki list hai, buy signal nahi. Stock chunne se pehle uska apna chart aur fundamentals check karo. Educational use only.</div>
  </div>`;
  document.body.appendChild(panel);

  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const pc = v => v == null ? '<b>—</b>' : `<b class="${v >= 0 ? 'sc-up' : 'sc-dn'}">${v >= 0 ? '+' : ''}${v.toFixed(1)}%</b>`;
  const sgn = v => (v >= 0 ? '+' : '') + v.toFixed(1);

  const SORTS = [['score', 'Score'], ['r1d', 'Aaj (1D)'], ['r1m', '1M'], ['r3m', '3M']];
  function chips() {
    const box = panel.querySelector('#sc-sort');
    box.innerHTML = '<span style="font-size:12px;color:#94a3b8;align-self:center">Sort:</span>' +
      SORTS.map(([k, l]) => `<button class="sc-chip ${state.sort === k ? 'on' : ''}" data-s="${k}">${l}</button>`).join('');
    box.querySelectorAll('button').forEach(b => b.onclick = () => { state.sort = b.dataset.s; chips(); render(); });
  }

  function card(r, color) {
    const flags = [
      `<span class="sc-flag">${r.above50 ? '✅' : '❌'} 50 DMA</span>`,
      r.above200 == null ? '' : `<span class="sc-flag">${r.above200 ? '✅' : '❌'} 200 DMA</span>`,
      `<span class="sc-flag">${r.rs_rising ? '📈 RS badh rahi' : '📉 RS gir rahi'}</span>`,
    ].join('');
    const stocks = state.open[r.name];
    let stHtml = '';
    if (stocks === 'loading') stHtml = '<div class="sc-sub">⏳ Stocks aa rahe hain...</div>';
    else if (stocks === 'error') stHtml = '<div class="sc-sub">Is sector ke stocks abhi nahi mile.</div>';
    else if (Array.isArray(stocks)) {
      stHtml = '<div class="sc-sub" style="margin-top:8px">Aaj ke top movers (tap karke analyze karo):</div><div class="sc-stocks">' +
        stocks.map(s => `<div class="sc-stk" data-s="${esc(s.symbol)}"><span>${esc(s.symbol)}</span><b class="${s.chg >= 0 ? 'sc-up' : 'sc-dn'}">${s.chg >= 0 ? '+' : ''}${Number(s.chg).toFixed(2)}%</b></div>`).join('') + '</div>';
    }
    return `<div class="sc-card" data-n="${esc(r.name)}">
      <div class="sc-head"><span class="sc-name">${esc(r.name)}</span><span class="sc-score" style="background:${color}">Score ${r.score}</span></div>
      <div class="sc-rets">
        <div class="sc-ret"><span>Aaj</span>${pc(r.r1d)}</div><div class="sc-ret"><span>1W</span>${pc(r.r1w)}</div>
        <div class="sc-ret"><span>1M</span>${pc(r.r1m)}</div><div class="sc-ret"><span>3M</span>${pc(r.r3m)}</div>
      </div>
      <div class="sc-sub">Nifty se fark: 1M <b>${sgn(r.rs1m)}%</b> · 3M <b>${sgn(r.rs3m)}%</b> · 6M <b>${sgn(r.rs6m || 0)}%</b></div>
      <div class="sc-sub">${esc(r.why)}</div>
      <div class="sc-flags">${flags}</div>
      <button class="sc-btn" data-idx="${esc(r.idx)}" data-n="${esc(r.name)}">📈 Top stocks dekho</button>
      ${stHtml}
    </div>`;
  }

  function render() {
    const list = panel.querySelector('#sc-list');
    if (!state.data) return;
    const d = state.data;
    panel.querySelector('#sc-ctx').textContent = `Nifty 50: 1M ${sgn(d.nifty_1m)}% • 3M ${sgn(d.nifty_3m)}% • updated ${d.updated}`;
    const rows = d.rows.slice().sort((a, b) => (b[state.sort] ?? -999) - (a[state.sort] ?? -999));
    let html = '';
    GROUPS.forEach(([key, title, sub, color]) => {
      const g = rows.filter(r => r.cat === key);
      html += `<div class="sc-grp" style="color:${color}">${title} (${g.length})<small>${sub}</small></div>`;
      html += g.length ? g.map(r => card(r, color)).join('') : '<div class="sc-sub">Abhi koi sector is category me nahi.</div>';
    });
    if (d.missing && d.missing.length) html += `<div class="sc-sub" style="margin-top:10px">Data nahi mila: ${esc(d.missing.join(', '))}</div>`;
    list.innerHTML = html;
    list.querySelectorAll('.sc-btn').forEach(b => b.onclick = () => loadStocks(b.dataset.n, b.dataset.idx));
    list.querySelectorAll('.sc-stk').forEach(el => el.onclick = () => openStock(el.dataset.s));
  }

  async function loadStocks(name, idx) {
    state.open[name] = 'loading'; render();
    try {
      const r = await fetch('/api/index-stocks?index=' + encodeURIComponent(idx));
      const j = await r.json();
      const arr = Array.isArray(j) ? j : [];
      arr.sort((a, b) => (b.chg || 0) - (a.chg || 0));
      state.open[name] = arr.length ? arr.slice(0, 8) : 'error';
    } catch (e) { state.open[name] = 'error'; }
    render();
  }

  function openStock(sym) {
    panel.style.display = 'none';
    // App ka stock-open function ho to wahi call karo; fallback = search box
    if (typeof window.openStock === 'function') { try { window.openStock(sym); return; } catch (e) {} }
    const inp = document.querySelector('input[placeholder*="Stock search"]');
    if (inp) { inp.value = sym; inp.dispatchEvent(new Event('input', { bubbles: true })); inp.focus(); }
  }

  async function load(refresh) {
    panel.querySelector('#sc-list').textContent = 'Loading... (pehli baar 20-30 sec lag sakte hain)';
    try {
      const r = await fetch('/api/sector-momentum' + (refresh ? '?refresh=1' : ''));
      if (r.status === 401) { location.href = '/login'; return; }
      const j = await r.json();
      if (j.error) { panel.querySelector('#sc-list').textContent = 'Sector data nahi aaya: ' + j.error; return; }
      state.data = j; render();
    } catch (e) { panel.querySelector('#sc-list').textContent = 'Load nahi hua: ' + e; }
  }

  function open() { panel.style.display = 'block'; chips(); if (!state.data) load(); }
  panel.querySelector('#sc-close').onclick = () => panel.style.display = 'none';
  panel.querySelector('#sc-refresh').onclick = () => load(true);
  window.openSectorMomentum = open;

  function addNav() {
    if (document.getElementById('nav-sectors')) return;
    const base = document.getElementById('nav-events') || document.getElementById('nav-intraday');
    if (base && base.parentElement) {
      const b = document.createElement('button');
      b.className = 'nav-btn'; b.id = 'nav-sectors'; b.innerHTML = '🔥 <span>Sectors</span>';
      b.addEventListener('click', () => {
        const sb = document.getElementById('sidebar'); if (sb) sb.classList.remove('open');
        const ov = document.querySelector('.sidebar-overlay'); if (ov) ov.classList.remove('show');
        open();
      });
      base.insertAdjacentElement('afterend', b);
    } else {
      const b = document.createElement('button'); b.id = 'sc-float'; b.textContent = '🔥 Sectors';
      b.onclick = open; document.body.appendChild(b);
    }
  }
  // events.js ka nav pehle ban jaye, isliye thoda late chalate hain
  const init = () => setTimeout(addNav, 400);
  if (document.readyState === 'complete') init(); else window.addEventListener('load', init);
})();
