/* ══════════════════════════════════════════════
   Stock Analyzer Pro — Frontend JavaScript
   Handles all UI, API calls, rendering
══════════════════════════════════════════════ */

// ── State ──────────────────────────────────────
let currentData   = null;
let currentSym    = null;
let currentUrl    = null;
let currentPriceChart = null;
let searchTimer   = null;
let rpIndicesLoaded = false;
let ipoAllData    = [];
let heatmapHistory = [];  // for index heatmap back navigation

// ── User ID — identifies this user across devices ──
let _userId = localStorage.getItem('user_id_v1') || '';

function getUserId() { return _userId; }

function setUserId(id) {
  _userId = id.trim();
  localStorage.setItem('user_id_v1', _userId);
}

// Add user ID to all fetch calls automatically
const _origFetch = window.fetch;
window.fetch = function(url, opts = {}) {
  const uid = getUserId();
  if (uid && typeof url === 'string' && url.startsWith('/api/')) {
    opts.headers = { ...(opts.headers || {}), 'X-User-ID': uid };
  }
  return _origFetch(url, opts);
};

// ── Init ───────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Check login status first
  setupAuth(() => {
    updateClock();
    setInterval(updateClock, 60000);
    loadIndices();
    migrateServerDataToLocal();
    try { switchHomeTab('tradelog'); } catch(e) { console.error('switchHomeTab error:', e); }
    try { loadRpIndices(); } catch(e) { console.error('loadRpIndices error:', e); }
  });
});

// ── Auth Setup ─────────────────────────────────
async function setupAuth(callback) {
  try {
    const res  = await fetch('/api/me');
    const data = await res.json();
    if (data.logged_in) {
      setUserId(data.email);
      showUserBadge(data.name, data.email);

      // Restore last visited page/tab/stock from URL hash
      const hash = window.location.hash.replace('#', '');
      const validPages = ['home','market','screener','watchlist','etf','ipo'];
      const homeTabs   = ['tradelog','broad','sectoral','thematic','strategy'];

      if (hash.startsWith('stock-sym-')) {
        // Refresh on stock page — reload same stock
        const sym = decodeURIComponent(hash.replace('stock-sym-', ''));
        callback();
        setTimeout(() => loadStockBySymbol(sym), 100);
        return;
      } else if (hash.startsWith('stock-url-')) {
        // Refresh on stock page (URL based)
        const url = decodeURIComponent(hash.replace('stock-url-', ''));
        callback();
        setTimeout(() => loadStockByUrl(url, ''), 100);
        return;
      } else if (hash.startsWith('home-')) {
        const tab = hash.replace('home-', '');
        if (homeTabs.includes(tab)) {
          callback();
          setTimeout(() => switchHomeTab(tab), 50);
          return;
        }
      } else if (hash && validPages.includes(hash) && hash !== 'home') {
        callback();
        setTimeout(() => showPage(hash), 50);
        return;
      }

      callback();
    } else {
      window.location.href = '/login';
    }
  } catch(e) {
    callback();
  }
}

function setupUserId(callback) { callback(); } // kept for compat

function showUserBadge(name, email) {
  const topbar = document.querySelector('.topbar-right');
  if (!topbar) return;
  let badge = document.getElementById('user-badge');
  if (!badge) {
    badge = document.createElement('div');
    badge.id = 'user-badge';
    badge.style.cssText = 'display:flex;align-items:center;gap:8px;margin-right:8px';
    topbar.insertBefore(badge, topbar.firstChild);
  }
  badge.innerHTML = `
    <span style="font-size:12px;color:#8B92B8;padding:4px 8px;border-radius:4px;border:1px solid #1C2240">
      👤 ${escHTML(name || email || 'User')}
    </span>
    <a href="/logout" style="font-size:11px;color:#FF3D5C;text-decoration:none;padding:4px 8px;border:1px solid rgba(255,61,92,0.3);border-radius:4px"
       onclick="return confirm('Logout karna chahte ho?')">
      Logout
    </a>`;
}

// ── One-time migration from server → localStorage ──
async function migrateServerDataToLocal() {
  // Load fresh data from server on every startup (for cross-device sync)
  await loadFromServer();
}

// ── Clock ──────────────────────────────────────
function updateClock() {
  const now = new Date();
  const ist = new Date(now.toLocaleString('en-US', {timeZone: 'Asia/Kolkata'}));
  const h = ist.getHours(), m = ist.getMinutes();
  const timeStr = `${h.toString().padStart(2,'0')}:${m.toString().padStart(2,'0')} IST`;
  document.getElementById('market-clock').textContent = `🕐 ${timeStr}`;

  const isWeekday = ist.getDay() > 0 && ist.getDay() < 6;
  const isOpen    = isWeekday && (h > 9 || (h === 9 && m >= 15)) && h < 15;
  const badge     = document.getElementById('market-status');
  if (badge) {
    badge.textContent = isOpen ? '● Market Open' : '● Market Closed';
    badge.style.color = isOpen ? 'var(--green)' : 'var(--red)';
    badge.style.background = isOpen ? 'rgba(0,230,168,0.1)' : 'rgba(255,61,92,0.1)';
  }
}

// ── Page Navigation ────────────────────────────
function showPage(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  document.getElementById('nav-' + page).classList.add('active');

  history.replaceState(null, '', '#' + page);
  sessionStorage.setItem('prev_hash', page); // for closeAnalysis restore

  if (window.innerWidth <= 900) {
    document.getElementById('sidebar').classList.remove('open');
    const ov = document.getElementById('sidebar-overlay');
    if (ov) ov.classList.remove('show');
  }

  if (page === 'market')    loadMarket('gainers');
  if (page === 'screener')  loadScreenerList();
  if (page === 'watchlist') loadWatchlist();
  if (page === 'etf')       loadEtf('list');
  if (page === 'ipo')       loadIpo();
}

function switchHomeTab(tab, btn) {
  document.querySelectorAll('#home-tabs .atab').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  else {
    const btns = document.querySelectorAll('#home-tabs .atab');
    const idx = ['tradelog','broad','sectoral','thematic','strategy'].indexOf(tab);
    if (idx >= 0 && btns[idx]) btns[idx].classList.add('active');
  }
  history.replaceState(null, '', '#home-' + tab);
  sessionStorage.setItem('prev_hash', 'home-' + tab); // for closeAnalysis restore

  if (tab === 'tradelog') renderTradeLog();
  else loadHeatmap(tab);
}

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  sidebar.classList.toggle('open');
  // Show/hide overlay
  let overlay = document.getElementById('sidebar-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'sidebar-overlay';
    overlay.className = 'sidebar-overlay';
    overlay.onclick = () => {
      sidebar.classList.remove('open');
      overlay.classList.remove('show');
    };
    document.body.appendChild(overlay);
  }
  overlay.classList.toggle('show', sidebar.classList.contains('open'));
}

// ── Indices Strip ──────────────────────────────
async function loadIndices() {
  try {
    // Use /api/indices which returns proper index data with categories
    const res = await fetch('/api/indices');
    const rows = await res.json();
    const strip = document.getElementById('indices-strip');
    if (!rows || rows.error || !rows.length) {
      strip.innerHTML = '<div class="loading-strip">⚠️ Indices unavailable</div>';
      return;
    }

    // Show key indices in strip
    const mainNames = ['NIFTY 50','NIFTY BANK','NIFTY IT','NIFTY MIDCAP 100','NIFTY NEXT 50','INDIA VIX','NIFTY FMCG','NIFTY AUTO'];
    let display = rows.filter(r => mainNames.includes(r.name));
    if (display.length < 3) display = rows.filter(r => r.cat === 'broad');
    if (display.length < 3) display = rows;
    display = display.slice(0, 8);

    strip.innerHTML = display.map(r => {
      const chg = parseFloat(r.chg) || 0;
      const cls   = chg >= 0 ? 'idx-up' : 'idx-down';
      const arrow = chg >= 0 ? '▲' : '▼';
      const disp  = r.name.replace(/^NIFTY\s*/i,'').substring(0, 14);
      return `<div class="index-card" onclick="loadIndexStocksFromRp('${escHTML(r.name)}')">
        <div class="idx-name">${escHTML(disp)}</div>
        <div class="idx-val">${fmtNum(r.last)}</div>
        <div class="idx-chg ${cls}">${arrow} ${Math.abs(chg).toFixed(2)}%</div>
      </div>`;
    }).join('');
  } catch(e) {
    document.getElementById('indices-strip').innerHTML = '<div class="loading-strip">⚠️ Index data load nahi hua</div>';
  }
}

// ── Search ─────────────────────────────────────
function onSearchInput() {
  clearTimeout(searchTimer);
  const q = document.getElementById('search-input').value.trim();
  if (q.length < 2) { closeDropdown(); return; }
  // Pass query as-is — backend handles case-insensitive search
  searchTimer = setTimeout(() => fetchSuggestions(q), 300);
}

async function fetchSuggestions(q) {
  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    showDropdown(data);
  } catch { closeDropdown(); }
}

function showDropdown(results) {
  const dd = document.getElementById('search-dropdown');
  if (!results || !results.length) { closeDropdown(); return; }
  dd.innerHTML = results.map(r => {
    // Symbol: from r.symbol field (now enriched by backend), or extract from URL
    let sym = r.symbol || '';
    if (!sym && r.url) {
      const m = r.url.match(/\/company\/([^/]+)\//i);
      if (m) sym = m[1].toUpperCase();
    }
    if (!sym) sym = r.name.split(' ')[0].toUpperCase();
    return `<div class="dd-item" onclick="loadFromSearch('${escHTML(r.url)}','${escHTML(r.name)}')">
      <span class="sym">${escHTML(sym)}</span>
      <span class="name">${escHTML(r.name)}</span>
    </div>`;
  }).join('');
  dd.classList.add('open');
}

function closeDropdown() {
  document.getElementById('search-dropdown').classList.remove('open');
}

function onSearchKey(e) {
  if (e.key === 'Enter') {
    const q = document.getElementById('search-input').value.trim();
    if (q) { closeDropdown(); loadStockBySymbol(q.toUpperCase()); }
  }
  if (e.key === 'Escape') closeDropdown();
}

function loadFromSearch(url, name) {
  closeDropdown();
  document.getElementById('search-input').value = '';
  loadStockByUrl(url, name);
}

// ── Quick Load ─────────────────────────────────
function quickLoad(sym) {
  loadStockBySymbol(sym);
}

// ── Load Stock by Symbol ───────────────────────
async function loadStockBySymbol(sym) {
  openAnalysisPanel(sym);
  currentSym = sym.toUpperCase();
  currentUrl = null;
  // Save in hash so refresh restores this stock
  history.replaceState(null, '', '#stock-sym-' + encodeURIComponent(currentSym));
  try {
    const res = await fetch(`/api/analyze?sym=${encodeURIComponent(sym)}`);
    const data = await res.json();
    if (data.error) { showPanelError(data.error); return; }
    currentData = data;
    renderAnalysis(data);
  } catch(e) {
    showPanelError('Network error: ' + e.message);
  }
}

async function loadStockByUrl(url, name) {
  openAnalysisPanel(name);
  currentUrl = url;
  // Save in hash so refresh restores this stock
  history.replaceState(null, '', '#stock-url-' + encodeURIComponent(url));
  try {
    const res = await fetch(`/api/analyze?url=${encodeURIComponent(url)}`);
    const data = await res.json();
    if (data.error) { showPanelError(data.error); return; }
    currentData = data;
    currentSym  = data.nse_symbol || '';
    renderAnalysis(data);
  } catch(e) {
    showPanelError('Network error: ' + e.message);
  }
}

// ── Analysis Panel ────────────────────────────
// (defined later with full rpanel support)

function showPanelError(msg) {
  document.getElementById('panel-body').innerHTML = `
    <div class="loading-full" style="color:var(--red)">
      <div style="font-size:40px">❌</div>
      <div>${escHTML(msg)}</div>
    </div>`;
}

// ── Render Full Analysis ───────────────────────
function renderAnalysis(data) {
  const sym  = data.nse_symbol || '';
  const name = data.name || sym;
  const nse  = data.nse || {};

  document.getElementById('panel-title').textContent = `${name} (${sym})`;

  // Watchlist button
  const wlBtn = document.getElementById('wl-btn');
  if (wlBtn) checkWatchlistStatus(sym, wlBtn);

  // Consolidated button
  const consBtn = document.getElementById('cons-btn');
  if (consBtn) {
    consBtn.textContent = data.is_consolidated ? '✅ Consolidated' : '⚠️ Standalone';
    consBtn.style.background = data.is_consolidated ? 'rgba(0,230,168,0.1)' : 'rgba(255,149,0,0.1)';
    consBtn.style.borderColor = data.is_consolidated ? 'var(--green)' : 'var(--orange)';
    consBtn.style.color = data.is_consolidated ? 'var(--green)' : 'var(--orange)';
  }

  // Load news in right panel
  if (sym) loadRpNews(sym, name);

  let html = '';

  // ── Company Header
  const sector = data.sector || data.industry || '';
  html += `<div class="company-header">
    <div>
      <div class="company-name">${escHTML(name)}</div>
      <div class="company-meta">
        ${data.is_consolidated ? `<span class="badge badge-cons">✅ Consolidated</span>` : `<span class="badge badge-standalone">⚠️ Standalone</span>`}
        ${sym ? `<span class="badge" style="background:#1C2240;color:var(--accent)">NSE: ${escHTML(sym)}</span>` : ''}
        ${sector ? `<span class="badge badge-sector">🏭 ${escHTML(sector)}</span>` : ''}
      </div>
    </div>
  </div>`;

  // ── NSE Live
  if (nse && nse.ltp) {
    const chgPct = parseFloat(nse.change_pct) || 0;
    const chgCol = chgPct >= 0 ? 'var(--green)' : 'var(--red)';
    const delPct = nse.delivery_pct;
    const delCol = delPct >= 50 ? 'var(--green)' : delPct >= 35 ? 'var(--yellow)' : 'var(--red)';

    const liveItems = [
      ['LTP',          nse.ltp ? `₹${fmtNum(nse.ltp)}` : 'N/A',          chgCol],
      ['Change',       nse.change_pct !== undefined ? `${chgPct >= 0 ? '+' : ''}${chgPct.toFixed(2)}%` : 'N/A', chgCol],
      ['VWAP',         nse.vwap ? `₹${fmtNum(nse.vwap)}` : 'N/A',        'var(--yellow)'],
      ['Day High',     nse.high ? `₹${fmtNum(nse.high)}` : 'N/A',        'var(--yellow)'],
      ['Day Low',      nse.low ? `₹${fmtNum(nse.low)}` : 'N/A',          'var(--yellow)'],
      ['Delivery%',    delPct ? `${parseFloat(delPct).toFixed(1)}%` : 'N/A', delCol],
      ['52W High',     nse.week52_high ? `₹${fmtNum(nse.week52_high)}` : 'N/A', 'var(--green)'],
      ['52W Low',      nse.week52_low  ? `₹${fmtNum(nse.week52_low)}`  : 'N/A', 'var(--red)'],
      ['Upper Circuit',nse.upper_circuit ? `₹${fmtNum(nse.upper_circuit)}` : 'N/A', 'var(--green)'],
      ['Lower Circuit',nse.lower_circuit ? `₹${fmtNum(nse.lower_circuit)}` : 'N/A', 'var(--red)'],
    ];

    html += `<div class="live-strip">
      <div class="live-strip-title">📡 NSE LIVE</div>
      <div class="live-grid">
        ${liveItems.map(([l,v,c]) => `<div class="live-cell">
          <div class="lc-label">${l}</div>
          <div class="lc-val" style="color:${c}">${v}</div>
        </div>`).join('')}
      </div>
    </div>`;

    if (delPct && parseFloat(delPct) >= 60 && Math.abs(chgPct) >= 2) {
      html += `<div style="background:#1A0A00;border-radius:8px;padding:10px 16px;margin-bottom:12px;color:var(--orange);font-size:13px;font-weight:600">
        🔥 Operator/Institutional Activity — Delivery ${parseFloat(delPct).toFixed(0)}% + Move ${chgPct >= 0 ? '+' : ''}${chgPct.toFixed(1)}% → Strong confirmation!
      </div>`;
    }
  }

  // ── Returns Row
  const ret = data.returns || {};
  const retKeys = ['1D','1W','1M','YTD','1Y','3Y','5Y','MAX'];
  if (retKeys.some(k => ret[k] !== null && ret[k] !== undefined)) {
    html += `<div class="returns-strip">
      <div class="returns-strip-title">📈 Returns</div>
      <div class="returns-grid">
        ${retKeys.map(k => {
          const v = ret[k];
          const col = v === null || v === undefined ? 'var(--subtext)' : v >= 0 ? 'var(--green)' : 'var(--red)';
          const txt = v === null || v === undefined ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`;
          return `<div class="ret-cell">
            <div class="ret-label">${k}</div>
            <div class="ret-val" style="color:${col}">${txt}</div>
          </div>`;
        }).join('')}
      </div>
    </div>`;
  }

  // ── Key Metrics
  const metrics = [
    ['Mkt Cap',    data.market_cap,      'Cr'],
    ['Price',      data.current_price,   '₹'],
    ['P/E',        data.pe,              ''],
    ['ROE',        data.roe,             '%'],
    ['ROCE',       data.roce,            '%'],
    ['D/E',        data.debt_to_equity,  ''],
    ['Int. Cover', data.interest_coverage,'x'],
    ['Promoter',   data.promoter_holding,'%'],
    ['Pledged',    data.pledged,         '%'],
    ['FII',        data.fii_holding,     '%'],
    ['DII',        data.dii_holding,     '%'],
  ];

  html += `<div class="metrics-grid">
    ${metrics.map(([l,v,u]) => {
      let vs = 'N/A', col = 'var(--subtext)';
      if (v !== null && v !== undefined) {
        const fv = parseFloat(v);
        col = 'var(--accent)';
        if (u === 'Cr')  vs = `${fmtNum(fv)}Cr`;
        else if (u === '₹') vs = `₹${fmtNum(fv)}`;
        else if (u === 'x') vs = `${fv.toFixed(1)}x`;
        else if (u === '%') vs = `${fv.toFixed(1)}%`;
        else vs = fv.toFixed(2);
        if (l === 'Pledged') col = fv > 20 ? 'var(--red)' : fv > 10 ? 'var(--yellow)' : 'var(--green)';
        if (l === 'ROE' || l === 'ROCE') col = fv >= 15 ? 'var(--green)' : fv >= 8 ? 'var(--yellow)' : 'var(--red)';
        if (l === 'D/E') col = fv < 0.5 ? 'var(--green)' : fv < 1 ? 'var(--yellow)' : 'var(--red)';
      }
      return `<div class="metric-card"><div class="mc-label">${l}</div><div class="mc-val" style="color:${col}">${vs}</div></div>`;
    }).join('')}
  </div>`;

  // ── Analysis Tabs
  html += `<div class="analysis-tabs">
    <button class="atab active" onclick="switchAtab('swing',this)">🔵 Swing</button>
    <button class="atab" onclick="switchAtab('positional',this)">🟡 Positional</button>
    <button class="atab" onclick="switchAtab('longterm',this)">🟢 Long Term</button>
    <button class="atab" onclick="switchAtab('technical',this)">📊 Technical</button>
    <button class="atab" onclick="switchAtab('notes',this)">📝 Notes</button>
  </div>
  <div id="atab-content"></div>`;

  document.getElementById('panel-body').innerHTML = html;
  renderChecklist(data, 'swing');
}

// ── Tab Switcher ───────────────────────────────
function switchAtab(tab, btn) {
  document.querySelectorAll('.atab').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');

  if (tab === 'technical') {
    renderTechnical();
  } else if (tab === 'notes') {
    renderNotes();
  } else {
    renderChecklist(currentData, tab);
  }
}

// ── Checklist Render ───────────────────────────
function renderChecklist(data, tab) {
  const chk = data.checklist?.[tab];
  if (!chk) { document.getElementById('atab-content').innerHTML = '<div class="loading-box">⚠️ Data nahi mila</div>'; return; }

  const score = chk.score;
  const col = score >= 70 ? 'var(--green)' : score >= 50 ? 'var(--yellow)' : 'var(--red)';

  let html = `<div class="score-bar-wrap">
    <div class="score-num" style="color:${col}">${score}%</div>
    <div>
      <div style="font-weight:700;margin-bottom:6px">${chk.passed}/${chk.total} criteria pass</div>
      <div class="score-bar-bg"><div class="score-bar-fill" style="width:${score}%;background:${col}"></div></div>
    </div>
  </div>
  <div class="checklist-wrap">`;

  html += chk.items.map(item => {
    const cls = item.status === 'pass' ? 'chk-pass' :
                item.status === 'fail' ? 'chk-fail' :
                item.status === 'manual' ? 'chk-manual' : 'chk-nodata';
    return `<div class="chk-item ${cls}">
      <span class="chk-icon">${item.icon}</span>
      <span class="chk-name">${escHTML(item.name)}</span>
      <span class="chk-cond">${escHTML(item.condition)}</span>
      <span class="chk-val" style="color:${item.status === 'pass' ? 'var(--green)' : item.status === 'fail' ? 'var(--red)' : 'var(--subtext)'}">
        ${item.value !== null ? item.value : '–'}
      </span>
    </div>`;
  }).join('');

  html += '</div>';
  document.getElementById('atab-content').innerHTML = html;
}

// ── Technical Render ───────────────────────────
async function renderTechnical() {
  const sym = currentSym || (currentData && currentData.nse_symbol);
  if (!sym) {
    document.getElementById('atab-content').innerHTML = '<div class="loading-box">⚠️ Symbol nahi mila</div>';
    return;
  }

  document.getElementById('atab-content').innerHTML = `
    <div class="loading-full">
      <div class="spinner"></div>
      <div>Technical data calculate ho rahi hai — RSI • MACD • EMA • Patterns</div>
    </div>`;

  try {
    // Pass fundamental data (PE, ROE etc.) so valuation meter works
    const fd = currentData ? {
      pe:              currentData.pe,
      roe:             currentData.roe,
      roce:            currentData.roce,
      price_to_book:   currentData.price_to_book,
      profit_growth_3y:currentData.profit_growth_3y,
      net_profit:      currentData.net_profit,
      debt_to_equity:  currentData.debt_to_equity,
      promoter_holding:currentData.promoter_holding,
    } : {};
    const fdParam = Object.keys(fd).length ? '?fdata=' + encodeURIComponent(JSON.stringify(fd)) : '';
    const res = await fetch(`/api/technical/${encodeURIComponent(sym)}${fdParam}`);
    const r   = await res.json();

    if (r.error) {
      document.getElementById('atab-content').innerHTML = `<div class="loading-box" style="color:var(--red)">❌ ${escHTML(r.error)}</div>`;
      return;
    }

    // Verdict
    const vColors = {
      strong_buy: {bg:'#0A2A18', col:'var(--green)'},
      buy:        {bg:'#082015', col:'#00CC88'},
      wait:       {bg:'#1E1800', col:'var(--yellow)'},
      avoid:      {bg:'#200810', col:'var(--red)'},
    };
    const vc = vColors[r.verdict_type] || vColors.wait;

    let html = `<div class="verdict-box" style="background:${vc.bg}">
      <div>
        <div class="verdict-text" style="color:${vc.col}">${escHTML(r.verdict)}</div>
        <div class="verdict-reason">Technical Score: ${r.score}/100</div>
      </div>
    </div>`;

    // Score bar
    const scCol = r.score >= 70 ? 'var(--green)' : r.score >= 50 ? 'var(--yellow)' : 'var(--red)';
    html += `<div class="score-bar-wrap">
      <div class="score-num" style="color:${scCol}">${r.score}</div>
      <div style="flex:1">
        <div style="font-weight:700;margin-bottom:6px">Technical Score /100</div>
        <div class="score-bar-bg"><div class="score-bar-fill" style="width:${r.score}%;background:${scCol}"></div></div>
      </div>
    </div>`;

    // Key indicators
    html += `<div class="tech-grid">
      <div class="tech-card">
        <div class="tc-label">RSI (14)</div>
        <div class="tc-val" style="color:${r.rsi > 70 ? 'var(--red)' : r.rsi < 30 ? 'var(--green)' : 'var(--yellow)'}">${r.rsi}</div>
        <div class="tc-sub">${r.rsi > 70 ? 'Overbought' : r.rsi < 30 ? 'Oversold' : 'Normal Zone'}</div>
      </div>
      <div class="tech-card">
        <div class="tc-label">MACD</div>
        <div class="tc-val" style="color:${r.macd_cross === 'Bullish' ? 'var(--green)' : 'var(--red)'}">${r.macd}</div>
        <div class="tc-sub">Signal: ${r.signal} • ${r.macd_cross}</div>
      </div>
      <div class="tech-card">
        <div class="tc-label">EMA 20</div>
        <div class="tc-val" style="color:var(--accent)">₹${r.ema20}</div>
        <div class="tc-sub">Price ${r.cur > r.ema20 ? '▲ above' : '▼ below'} EMA20</div>
      </div>
      <div class="tech-card">
        <div class="tc-label">EMA 50</div>
        <div class="tc-val" style="color:var(--accent)">₹${r.ema50}</div>
        <div class="tc-sub">${r.ema_align ? '✅ EMA Aligned' : '⚠️ Not aligned'}</div>
      </div>
      ${r.ema200 ? `<div class="tech-card">
        <div class="tc-label">EMA 200</div>
        <div class="tc-val" style="color:var(--accent)">₹${r.ema200}</div>
        <div class="tc-sub">Long-term trend</div>
      </div>` : ''}
      <div class="tech-card">
        <div class="tc-label">Bollinger %B</div>
        <div class="tc-val" style="color:${r.bb_pct > 70 ? 'var(--orange)' : 'var(--accent)'}">${r.bb_pct}%</div>
        <div class="tc-sub">Upper: ₹${r.bb_upper} / Lower: ₹${r.bb_lower}</div>
      </div>
      <div class="tech-card">
        <div class="tc-label">ATR (14)</div>
        <div class="tc-val" style="color:var(--yellow)">₹${r.atr}</div>
        <div class="tc-sub">Volatility: ${r.atr_pct}%</div>
      </div>
      <div class="tech-card">
        <div class="tc-label">Volume</div>
        <div class="tc-val" style="color:${r.vol_surge ? 'var(--green)' : 'var(--subtext)'}">${r.vol_ratio}x</div>
        <div class="tc-sub">${r.vol_surge ? '🔥 Volume Surge!' : 'Normal volume'}</div>
      </div>
    </div>`;

    // Support / Resistance
    html += `<div class="section-hdr">📍 Support & Resistance</div>
    <div class="sr-grid">
      <div class="sr-card"><div class="sr-label">R2</div><div class="sr-val" style="color:var(--red)">₹${r.r2}</div></div>
      <div class="sr-card"><div class="sr-label">R1</div><div class="sr-val" style="color:var(--orange)">₹${r.r1}</div></div>
      <div class="sr-card"><div class="sr-label">Pivot</div><div class="sr-val" style="color:var(--yellow)">₹${r.pivot}</div></div>
      <div class="sr-card"><div class="sr-label">S1</div><div class="sr-val" style="color:var(--accent)">₹${r.s1}</div></div>
      <div class="sr-card"><div class="sr-label">S2</div><div class="sr-val" style="color:var(--green)">₹${r.s2}</div></div>
      <div class="sr-card"><div class="sr-label">52W High</div><div class="sr-val" style="color:var(--green)">₹${r.high52}</div></div>
    </div>`;

    // Target & SL
    html += `<div class="section-hdr">🎯 Target & Stop Loss (ATR-based)</div>
    <div class="tech-grid">
      <div class="tech-card">
        <div class="tc-label">Stop Loss</div>
        <div class="tc-val" style="color:var(--red)">₹${r.sl}</div>
        <div class="tc-sub">2× ATR below LTP</div>
      </div>
      <div class="tech-card">
        <div class="tc-label">Target 1</div>
        <div class="tc-val" style="color:var(--green)">₹${r.tgt1}</div>
        <div class="tc-sub">2× ATR above LTP</div>
      </div>
      <div class="tech-card">
        <div class="tc-label">Target 2</div>
        <div class="tc-val" style="color:var(--green)">₹${r.tgt2}</div>
        <div class="tc-sub">4× ATR above LTP</div>
      </div>
      <div class="tech-card">
        <div class="tc-label">R:R Ratio</div>
        <div class="tc-val" style="color:${r.rr >= 1.5 ? 'var(--green)' : 'var(--yellow)'}">${r.rr}:1</div>
        <div class="tc-sub">${r.rr >= 1.5 ? '✅ Good R:R' : '⚠️ Low R:R'}</div>
      </div>
    </div>`;

    // Bull/Bear reasons
    html += `<div class="section-hdr">📋 Analysis Reasons</div>
    <div class="reasons-wrap">
      <div class="reason-col" style="border-left:3px solid var(--green)">
        <div class="reason-col-title" style="color:var(--green)">🟢 Bullish Signals</div>
        ${r.reasons_bull.map(x => `<div class="reason-item" style="color:var(--text)">${escHTML(x)}</div>`).join('') || '<div class="reason-item" style="color:var(--subtext)">Koi bullish signal nahi</div>'}
      </div>
      <div class="reason-col" style="border-left:3px solid var(--red)">
        <div class="reason-col-title" style="color:var(--red)">🔴 Bearish Signals</div>
        ${r.reasons_bear.map(x => `<div class="reason-item" style="color:var(--text)">${escHTML(x)}</div>`).join('') || '<div class="reason-item" style="color:var(--subtext)">Koi bearish signal nahi</div>'}
      </div>
    </div>`;

    // Candlestick Patterns
    html += `<div class="section-hdr">🕯️ Candlestick Patterns</div>
    ${r.patterns.map(p => `<div class="pattern-item" style="border-left:3px solid ${p.signal === 'bullish' ? 'var(--green)' : p.signal === 'bearish' ? 'var(--red)' : 'var(--border)'}">
      <span class="pi-icon">${p.icon}</span>
      <div><div class="pi-name">${escHTML(p.name)}</div><div class="pi-desc">${escHTML(p.desc)}</div></div>
    </div>`).join('')}`;

    // Chart Patterns
    html += `<div class="section-hdr">📈 Chart Patterns</div>
    ${r.chart_patterns.map(p => `<div class="pattern-item" style="border-left:3px solid ${p.signal === 'bullish' ? 'var(--green)' : p.signal === 'bearish' ? 'var(--red)' : 'var(--border)'}">
      <span class="pi-icon">${p.icon}</span>
      <div><div class="pi-name">${escHTML(p.name)}</div><div class="pi-desc">${escHTML(p.desc)}</div></div>
    </div>`).join('')}`;

    // Valuation Meter (fundamental data from currentData)
    // fd already declared above with fundamental data
    const valType = r.val_type || 'unknown';
    const valLabel = r.val_label || 'N/A';
    const valColors = {
      cheap:         { col: 'var(--green)',  bg: 'rgba(0,230,168,0.08)'  },
      fair:          { col: 'var(--yellow)', bg: 'rgba(255,215,0,0.08)'  },
      expensive:     { col: 'var(--orange)', bg: 'rgba(255,149,0,0.08)'  },
      very_expensive:{ col: 'var(--red)',    bg: 'rgba(255,61,92,0.08)'  },
      unknown:       { col: 'var(--subtext)',bg: 'rgba(139,146,184,0.06)'},
    };
    const vc2 = valColors[valType] || valColors.unknown;

    const valMetrics = [
      { label: 'P/E Ratio',       val: fd.pe,              fmt: v => v.toFixed(1),          col: v => v < 15 ? 'var(--green)' : v < 25 ? 'var(--yellow)' : v < 40 ? 'var(--orange)' : 'var(--red)' },
      { label: 'Price/Book',      val: fd.price_to_book,   fmt: v => v.toFixed(2) + 'x',    col: v => v < 3 ? 'var(--green)' : v < 6 ? 'var(--yellow)' : 'var(--red)' },
      { label: 'ROE',             val: fd.roe,              fmt: v => v.toFixed(1) + '%',    col: v => v >= 20 ? 'var(--green)' : v >= 12 ? 'var(--yellow)' : 'var(--red)' },
      { label: 'ROCE',            val: fd.roce,             fmt: v => v.toFixed(1) + '%',    col: v => v >= 20 ? 'var(--green)' : v >= 12 ? 'var(--yellow)' : 'var(--red)' },
      { label: 'Profit Growth 3Y',val: fd.profit_growth_3y, fmt: v => v.toFixed(1) + '%',   col: v => v >= 15 ? 'var(--green)' : v >= 8 ? 'var(--yellow)' : 'var(--red)' },
    ];

    html += `<div class="section-hdr">📊 Valuation Meter</div>
    <div class="valuation-meter" style="background:${vc2.bg};border:1px solid ${vc2.col}33;border-radius:12px;padding:16px 20px;margin-bottom:14px">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px">
        <div style="font-size:13px;color:var(--subtext);font-weight:600">Valuation</div>
        <div style="font-size:16px;font-weight:800;color:${vc2.col}">${escHTML(valLabel)}</div>
      </div>
      <div class="val-metrics-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:10px">
        ${valMetrics.map(m => {
          const hasVal = m.val !== null && m.val !== undefined;
          const dispVal = hasVal ? m.fmt(parseFloat(m.val)) : 'N/A';
          const dispCol = hasVal ? m.col(parseFloat(m.val)) : 'var(--subtext)';
          return `<div style="background:rgba(255,255,255,0.03);border-radius:8px;padding:10px 12px;text-align:center">
            <div style="font-size:11px;color:var(--subtext);margin-bottom:4px">${m.label}</div>
            <div style="font-size:15px;font-weight:700;color:${dispCol}">${dispVal}</div>
          </div>`;
        }).join('')}
      </div>
      <div style="margin-top:10px;font-size:11px;color:var(--subtext)">⚠️ Yeh analysis sirf educational purpose ke liye hai. Investment decision apni research aur risk tolerance ke basis pe lo.</div>
    </div>`;

    // Price Chart
    if (r.price_history && r.price_history.length > 0) {
      html += `<div class="section-hdr">📉 Price Chart (60 days)</div>
      <div class="chart-wrap">
        <canvas id="price-chart" height="200"></canvas>
      </div>`;
    }

    document.getElementById('atab-content').innerHTML = html;

    // Draw chart
    if (r.price_history && r.price_history.length > 0) {
      const ctx = document.getElementById('price-chart').getContext('2d');
      if (currentPriceChart) currentPriceChart.destroy();
      const prices = r.price_history.map(d => d.price);
      const startP = prices[0], endP = prices[prices.length - 1];
      const lineCol = endP >= startP ? '#00E6A8' : '#FF3D5C';
      currentPriceChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: r.price_history.map(d => d.date),
          datasets: [{
            data: prices,
            borderColor: lineCol,
            borderWidth: 2,
            fill: true,
            backgroundColor: lineCol + '15',
            pointRadius: 0,
            tension: 0.3,
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: '#8B92B8', maxTicksLimit: 8 }, grid: { color: '#1C2240' } },
            y: { ticks: { color: '#8B92B8', callback: v => '₹' + fmtNum(v) }, grid: { color: '#1C2240' } }
          }
        }
      });
    }

  } catch(e) {
    document.getElementById('atab-content').innerHTML = `<div class="loading-box" style="color:var(--red)">❌ ${escHTML(e.message)}</div>`;
  }
}

// ── Notes Render ───────────────────────────────
// ══════════════════════════════════════════════
// LOCAL STORAGE HELPERS — Private data (watchlist, trades, notes)
// Data server pe User ID ke saath save hota hai.
// localStorage sirf cache ke liye — fast load ke liye.
// ══════════════════════════════════════════════

function lsGet(key, def) {
  try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : def; }
  catch { return def; }
}
function lsSet(key, val) {
  try { localStorage.setItem(key, JSON.stringify(val)); } catch {}
}

// Cache key includes user ID so different users on same browser get different data
function _cacheKey(k) { return `${k}_${getUserId()}`; }

// Watchlist: { SYM: {sym, name, price, sector, added} }
function wlGetAll()          { return lsGet(_cacheKey('wl_v1'), {}); }
function wlSave(wl)          { lsSet(_cacheKey('wl_v1'), wl); _syncToServer(); }
function wlAdd(sym, info)    { const wl = wlGetAll(); wl[sym] = {...info, sym, added: new Date().toLocaleDateString('en-IN')}; wlSave(wl); }
function wlRemove(sym)       { const wl = wlGetAll(); delete wl[sym]; wlSave(wl); }
function wlHas(sym)          { return !!wlGetAll()[sym]; }

// Trades: { SYM: [{type,price,qty,date,logged}, ...] }
function tradesGetAll()      { return lsGet(_cacheKey('trades_v1'), {}); }
function tradesGet(sym)      { return (tradesGetAll()[sym] || []); }
function tradesAdd(sym, t)   { const all = tradesGetAll(); all[sym] = [t, ...(all[sym]||[])]; lsSet(_cacheKey('trades_v1'), all); _syncToServer(); }
function tradesDel(sym, idx) { const all = tradesGetAll(); if(all[sym]) { all[sym].splice(idx,1); if(!all[sym].length) delete all[sym]; lsSet(_cacheKey('trades_v1'), all); _syncToServer(); } }
function tradesFlat()        { const all = tradesGetAll(); const flat=[]; for(const [sym,ts] of Object.entries(all)) ts.forEach(t=>flat.push({...t,sym})); return flat.sort((a,b)=>(b.logged||'').localeCompare(a.logged||'')); }

// Notes: { SYM: "note text" }
function notesGet(sym)       { return lsGet(_cacheKey('notes_v1'), {})[sym] || ''; }
function notesSave(sym, txt) { const n = lsGet(_cacheKey('notes_v1'), {}); n[sym] = txt; lsSet(_cacheKey('notes_v1'), n); _syncToServer(); }

// ── Sync to server (debounced) ─────────────────
let _syncTimer = null;
function _syncToServer() {
  clearTimeout(_syncTimer);
  _syncTimer = setTimeout(async () => {
    try {
      const data = {
        watchlist: wlGetAll(),
        trades:    tradesGetAll(),
        notes:     lsGet(_cacheKey('notes_v1'), {}),
      };
      await fetch('/api/userdata', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
    } catch(e) { console.log('Sync failed (offline?):', e.message); }
  }, 800);
}

// ── Load from server on startup ────────────────
async function loadFromServer() {
  try {
    const res  = await fetch('/api/userdata');
    const data = await res.json();
    if (!data || typeof data !== 'object') return;

    // Merge strategy: server data + local data combine karo
    // Local data ko priority do (user ne abhi kuch add kiya hoga)
    const localWl     = wlGetAll();
    const localTrades = tradesGetAll();
    const localNotes  = lsGet(_cacheKey('notes_v1'), {});

    // Server se data lo agar local empty hai
    if (data.watchlist && Object.keys(data.watchlist).length > 0) {
      const merged = { ...data.watchlist, ...localWl }; // local overrides server
      lsSet(_cacheKey('wl_v1'), merged);
    }
    if (data.trades && Object.keys(data.trades).length > 0) {
      const merged = { ...data.trades, ...localTrades }; // local overrides server
      lsSet(_cacheKey('trades_v1'), merged);
    }
    if (data.notes && Object.keys(data.notes).length > 0) {
      const merged = { ...data.notes, ...localNotes }; // local overrides server
      lsSet(_cacheKey('notes_v1'), merged);
    }

    // Ab local data server pe bhi save karo (sync)
    _syncToServer();
    console.log('[sync] Data merged from server ✅');
  } catch(e) {
    console.log('[sync] Server load failed (using local cache):', e.message);
  }
}

// ── Notes Tab ──────────────────────────────────
function renderNotes() {
  const sym = currentSym;
  if (!sym) return;

  const note   = notesGet(sym);
  const trades = tradesGet(sym);

  let html = `<div class="notes-area">
    <div class="section-hdr" style="margin-top:0">📝 My Notes — ${escHTML(sym)}</div>
    <textarea id="note-text" placeholder="Yahan notes likhho...">${escHTML(note)}</textarea>
    <button class="save-btn" onclick="saveNote()">💾 Save Note</button>
  </div>

  <div class="trade-form">
    <div class="section-hdr" style="margin-top:0">💼 Trade Tracker</div>
    <div class="trade-row">
      <input type="date" id="trade-date" value="${new Date().toISOString().split('T')[0]}">
      <select id="trade-type">
        <option value="BUY">BUY</option>
        <option value="SELL">SELL</option>
      </select>
      <input type="number" id="trade-qty"   placeholder="Qty" min="1">
      <input type="number" id="trade-price" placeholder="Price" step="0.01">
      <button class="add-btn" onclick="addTrade()">+ Add Trade</button>
    </div>
  </div>`;

  if (trades.length > 0) {
    html += `<div class="section-hdr">📊 Trade History</div>
    <table class="wl-table">
      <thead><tr><th>Date</th><th>Type</th><th>Qty</th><th>Price</th><th></th></tr></thead>
      <tbody>
        ${trades.map((t, i) => `<tr>
          <td>${escHTML(t.date || t.logged || '—')}</td>
          <td style="color:${t.type==='BUY'?'var(--green)':'var(--red)'};font-weight:700">${t.type}</td>
          <td>${t.qty}</td>
          <td>₹${t.price}</td>
          <td><button class="del-btn" onclick="deleteTrade(${i})">✕</button></td>
        </tr>`).join('')}
      </tbody>
    </table>`;
  }

  document.getElementById('atab-content').innerHTML = html;
}

function saveNote() {
  const sym  = currentSym;
  const note = document.getElementById('note-text').value;
  notesSave(sym, note);
  showToast('✅ Note saved!');
}

function addTrade() {
  const sym   = currentSym;
  const date  = document.getElementById('trade-date').value;
  const type  = document.getElementById('trade-type').value;
  const qty   = document.getElementById('trade-qty').value;
  const price = document.getElementById('trade-price').value;
  if (!qty || !price) { showToast('⚠️ Qty aur Price fill karo', true); return; }
  tradesAdd(sym, {
    date, type,
    qty:    parseInt(qty),
    price:  parseFloat(price),
    logged: new Date().toISOString()
  });
  showToast('✅ Trade added!');
  renderNotes();
}

function deleteTrade(idx) {
  tradesDel(currentSym, idx);
  renderNotes();
}

// ── Watchlist ──────────────────────────────────
function checkWatchlistStatus(sym, btn) {
  if (wlHas(sym)) { btn.textContent = '★ Saved'; btn.classList.add('saved'); }
  else            { btn.textContent = '⭐ Watchlist'; btn.classList.remove('saved'); }
}

function toggleWatchlist() {
  const sym  = currentSym;
  const data = currentData;
  if (!sym) return;
  const btn = document.getElementById('wl-btn');
  if (wlHas(sym)) {
    wlRemove(sym);
    btn.textContent = '⭐ Watchlist'; btn.classList.remove('saved');
    showToast('Watchlist se remove kiya');
  } else {
    wlAdd(sym, {name: data?.name||sym, price: data?.current_price, sector: data?.sector||''});
    btn.textContent = '★ Saved'; btn.classList.add('saved');
    showToast('⭐ Watchlist mein add kiya!');
  }
  // Update sidebar count
  const cnt = document.getElementById('wl-count');
  if (cnt) cnt.textContent = Object.keys(wlGetAll()).length;
}

async function loadWatchlist() {
  const cont = document.getElementById('watchlist-content');
  cont.innerHTML = '<div class="loading-box">⏳ Loading...</div>';
  const wl    = wlGetAll();
  const items = Object.values(wl);
  if (!items.length) {
    cont.innerHTML = '<div class="loading-box">⭐ Watchlist empty hai — stocks add karo analysis se</div>';
    return;
  }
  cont.innerHTML = `<div class="wl-table-wrap">
    <table class="wl-table">
      <thead><tr>
        <th>Symbol</th><th>Company</th><th>Sector</th><th>Added</th>
        <th>Entry ₹</th><th>Live ₹</th><th>Chg%</th><th>Sparkline</th><th></th>
      </tr></thead>
      <tbody>
        ${items.map(item => `<tr>
          <td class="wl-sym" onclick="quickLoad('${escHTML(item.sym)}')">${escHTML(item.sym)}</td>
          <td style="font-size:12px">${escHTML(item.name||'-')}</td>
          <td style="color:var(--subtext);font-size:11px">${escHTML(item.sector||'-')}</td>
          <td style="color:var(--subtext);font-size:12px">${escHTML(item.added||'-')}</td>
          <td>₹${item.price||'-'}</td>
          <td id="wl-live-${item.sym}" style="color:var(--subtext)">...</td>
          <td id="wl-pnl-${item.sym}"  style="color:var(--subtext)">...</td>
          <td><canvas id="wl-spark-${item.sym}" class="wl-spark"></canvas></td>
          <td><button class="del-btn" onclick="removeWatchlist('${escHTML(item.sym)}')">✕</button></td>
        </tr>`).join('')}
      </tbody>
    </table>
  </div>`;
  items.forEach(item => fetchWlLive(item));
}

async function fetchWlLive(item) {
  try {
    const res = await fetch(`/api/live/${item.sym}`);
    const nse = await res.json();
    const liveEl = document.getElementById('wl-live-' + item.sym);
    const pnlEl  = document.getElementById('wl-pnl-'  + item.sym);
    if (!liveEl) return;
    const ltp = nse.ltp, chg = nse.change_pct;
    if (ltp) {
      liveEl.textContent = `₹${fmtNum(ltp)}`;
      liveEl.style.color = (chg||0) >= 0 ? 'var(--green)' : 'var(--red)';
      if (item.price && pnlEl) {
        const pnl = ((ltp - item.price) / item.price * 100).toFixed(2);
        pnlEl.textContent = `${pnl >= 0 ? '+' : ''}${pnl}%`;
        pnlEl.style.color  = pnl >= 0 ? 'var(--green)' : 'var(--red)';
      }
    }
  } catch {}
  try {
    const res2 = await fetch(`/api/sparkline/${item.sym}`);
    const prices = await res2.json();
    if (prices && prices.length > 1) {
      const canvas = document.getElementById('wl-spark-' + item.sym);
      if (canvas) drawSparkline(canvas, prices);
    }
  } catch {}
}

function drawSparkline(canvas, prices) {
  const ctx = canvas.getContext('2d');
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  const mn = Math.min(...prices), mx = Math.max(...prices), rng = mx - mn || 1;
  const col = prices[prices.length-1] >= prices[0] ? '#00E6A8' : '#FF3D5C';
  ctx.strokeStyle = col; ctx.lineWidth = 1.5; ctx.beginPath();
  prices.forEach((p, i) => {
    const x = (i / (prices.length-1)) * w;
    const y = h - ((p - mn) / rng) * (h - 4) - 2;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function removeWatchlist(sym) {
  wlRemove(sym);
  loadWatchlist();
  showToast('Watchlist se hataya');
}

function refreshWatchlist() { loadWatchlist(); }

// ── Trade Log (Home Tab) ───────────────────────
function renderTradeLog() {
  const cont = document.getElementById('home-tab-content');
  if (!cont) return;
  const trades = tradesFlat();

  if (!trades.length) {
    cont.innerHTML = `<div class="trade-log-empty">
      <div class="tl-icon">📒</div>
      <div class="tl-title">Abhi koi trade log nahi</div>
      <div>Kisi bhi stock analyze karo → Notes tab → trade add karo</div>
    </div>`;
    return;
  }

  cont.innerHTML = `
    <div style="overflow-x:auto">
      <table class="trade-log-table">
        <thead><tr>
          <th>Symbol</th><th>Type</th><th>Buy Price</th><th>Qty</th>
          <th>Total Value</th><th>Date</th>
          <th>Live Price</th><th>P&amp;L (₹)</th><th>Gain %</th><th></th>
        </tr></thead>
        <tbody>
          ${trades.map((t, i) => {
            const tc  = t.type === 'BUY' ? 'var(--green)' : 'var(--red)';
            const pr  = parseFloat(t.price) || 0;
            const qty = parseFloat(t.qty)   || 0;
            const tv  = pr * qty;
            return `<tr>
              <td class="wl-sym" onclick="quickLoad('${escHTML(t.sym)}')">${escHTML(t.sym)}</td>
              <td style="color:${tc};font-weight:700">${escHTML(t.type)}</td>
              <td>₹${pr > 0 ? fmtNum(pr) : '—'}</td>
              <td>${qty > 0 ? qty : '—'}</td>
              <td style="color:var(--accent);font-weight:600">${tv > 0 ? '₹'+fmtNum(tv) : '—'}</td>
              <td style="color:var(--subtext);font-size:12px">${escHTML(t.date||t.logged||'—')}</td>
              <td id="tl-ltp-${i}" style="color:var(--subtext)">...</td>
              <td id="tl-pnl-${i}" style="font-weight:700">...</td>
              <td id="tl-pct-${i}" style="font-weight:700">...</td>
              <td><button class="del-btn" onclick="deleteTl(${i},'${escHTML(t.sym)}')">✕</button></td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
    </div>
    <div style="padding:10px 12px;color:var(--subtext);font-size:12px;background:var(--card2);border-radius:0 0 8px 8px;display:flex;gap:20px;flex-wrap:wrap">
      <span>Total: <b style="color:var(--text)">${trades.length} trades</b></span>
      <span>BUY: <b style="color:var(--green)">${trades.filter(t=>t.type==='BUY').length}</b></span>
      <span>SELL: <b style="color:var(--red)">${trades.filter(t=>t.type==='SELL').length}</b></span>
      <span>Invested: <b style="color:var(--accent)">₹${fmtNum(trades.filter(t=>t.type==='BUY').reduce((s,t)=>s+(parseFloat(t.price)||0)*(parseFloat(t.qty)||0),0))}</b></span>
    </div>`;

  trades.forEach((t, i) => fetchTlPnl(t, i));
}

function deleteTl(idx, sym) {
  // idx is index in flat array — find actual index in sym's array
  const symTrades = tradesGet(sym);
  const flat = tradesFlat();
  const trade = flat[idx];
  if (!trade) return;
  // Find position in sym's array
  const symIdx = symTrades.findIndex(t =>
    t.logged === trade.logged && t.price === trade.price && t.type === trade.type
  );
  if (symIdx >= 0) tradesDel(sym, symIdx);
  renderTradeLog();
  showToast('Trade deleted');
}

async function fetchTlPnl(trade, idx) {
  const ltpEl = document.getElementById('tl-ltp-' + idx);
  const pnlEl = document.getElementById('tl-pnl-' + idx);
  const pctEl = document.getElementById('tl-pct-' + idx);
  if (!pnlEl) return;

  try {
    // Try NSE live first, fallback to /api/price
    let ltp = 0;
    try {
      const r1 = await fetch(`/api/live/${trade.sym}`);
      const d1 = await r1.json();
      ltp = parseFloat(d1.ltp) || 0;
    } catch {}

    // Fallback: yfinance price
    if (!ltp) {
      try {
        const r2 = await fetch(`/api/price/${trade.sym}`);
        const d2 = await r2.json();
        ltp = parseFloat(d2.price) || 0;
      } catch {}
    }

    if (ltp > 0 && trade.price) {
      const buyPrice = parseFloat(trade.price) || 0;
      const qty      = parseFloat(trade.qty)   || 1;
      const sign     = trade.type === 'SELL' ? -1 : 1;

      if (ltpEl) {
        ltpEl.textContent = '₹' + fmtNum(ltp);
        ltpEl.style.color = ltp >= buyPrice ? 'var(--green)' : 'var(--red)';
      }
      const pnl = (ltp - buyPrice) * qty * sign;
      pnlEl.textContent = `${pnl >= 0 ? '+' : ''}₹${fmtNum(Math.abs(pnl))}`;
      pnlEl.style.color = pnl >= 0 ? 'var(--green)' : 'var(--red)';

      if (pctEl && buyPrice > 0) {
        const gainPct = ((ltp - buyPrice) / buyPrice) * 100 * sign;
        pctEl.textContent = `${gainPct >= 0 ? '+' : ''}${gainPct.toFixed(2)}%`;
        pctEl.style.color = gainPct >= 0 ? 'var(--green)' : 'var(--red)';
      }
    } else {
      if (ltpEl) { ltpEl.textContent = '—'; ltpEl.style.color = 'var(--subtext)'; }
      pnlEl.textContent = '—'; pnlEl.style.color = 'var(--subtext)';
      if (pctEl) { pctEl.textContent = '—'; pctEl.style.color = 'var(--subtext)'; }
    }
  } catch {
    if (ltpEl) ltpEl.textContent = '—';
    pnlEl.textContent = '—';
    if (pctEl) pctEl.textContent = '—';
  }
}

// ── Market ─────────────────────────────────────
async function loadMarket(type, btn) {
  if (btn) {
    document.querySelectorAll('#market-tabs .pill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  }

  const cont = document.getElementById('market-content');
  cont.innerHTML = '<div class="loading-box">⏳ NSE se data fetch ho rahi hai... (10-15 sec)</div>';

  try {
    const controller = new AbortController();
    const tid = setTimeout(() => controller.abort(), 20000); // 20s timeout
    const res = await fetch(`/api/market/${type}`, { signal: controller.signal });
    clearTimeout(tid);
    const rows = await res.json();

    if (!rows || rows.error || !rows.length) {
      cont.innerHTML = `<div class="loading-box">
        ⚠️ Data available nahi — Market closed ho sakta hai ya NSE session expire hua<br>
        <button class="btn-sm" style="margin-top:12px" onclick="loadMarket('${type}')">🔄 Retry</button>
      </div>`;
      return;
    }

    cont.innerHTML = `<div style="overflow-x:auto">
      <table class="market-table">
        <thead><tr>
          <th>#</th><th>Symbol</th><th>Company</th>
          <th>Price</th><th>Change %</th><th>Volume</th>
        </tr></thead>
        <tbody>
          ${rows.map((r, i) => {
            const chg = parseFloat(r.change_pct) || 0;
            const cls = chg >= 0 ? 'up-col' : 'dn-col';
            const arrow = chg >= 0 ? '▲' : '▼';
            return `<tr onclick="quickLoad('${escHTML(r.symbol)}')">
              <td style="color:var(--subtext)">${i+1}</td>
              <td class="sym-col">${escHTML(r.symbol)}</td>
              <td style="color:var(--subtext);font-size:12px">${escHTML(r.company || '-')}</td>
              <td>₹${fmtNum(r.ltp)}</td>
              <td class="${cls}">${arrow} ${Math.abs(chg).toFixed(2)}%</td>
              <td style="color:var(--subtext)">${fmtVol(r.volume)}</td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
    </div>`;
  } catch(e) {
    const msg = e.name === 'AbortError' ? 'Timeout — NSE server slow hai, retry karo' : escHTML(e.message);
    cont.innerHTML = `<div class="loading-box" style="color:var(--orange)">
      ⚠️ ${msg}<br>
      <button class="btn-sm" style="margin-top:12px" onclick="loadMarket('${type}')">🔄 Retry</button>
    </div>`;
  }
}

// ── Screener ───────────────────────────────────
async function loadScreenerList() {
  const list = document.getElementById('screener-list');
  try {
    const res     = await fetch('/api/chartink-list');
    const scanners = await res.json();
    list.innerHTML = scanners.map(s =>
      `<div class="screener-card" onclick="runScreener('${s.slug}')">
        <div class="sc-label">${escHTML(s.label)}</div>
      </div>`
    ).join('');
  } catch(e) {
    list.innerHTML = `<div class="loading-box" style="color:var(--red)">❌ Error loading screeners</div>`;
  }
}

async function runScreener(slug) {
  const result = document.getElementById('screener-result');
  result.innerHTML = '<div class="loading-box">⏳ Screener run ho rahi hai...</div>';
  result.scrollIntoView({behavior:'smooth'});
  try {
    const res  = await fetch(`/api/chartink/${slug}`);
    const rows = await res.json();

    if (!rows || rows.error || !rows.length) {
      result.innerHTML = '<div class="loading-box">⚠️ Koi result nahi mila</div>';
      return;
    }

    // Default sort: % change high → low
    rows.sort((a, b) => {
      const ca = parseFloat(a.per_chg || a.change_pct || 0);
      const cb = parseFloat(b.per_chg || b.change_pct || 0);
      return cb - ca;
    });

    const renderTable = (data, sortKey = 'pct', sortDir = 'desc') => {
      const sorted = [...data].sort((a, b) => {
        let va, vb;
        if (sortKey === 'pct') {
          va = parseFloat(a.per_chg || a.change_pct || 0);
          vb = parseFloat(b.per_chg || b.change_pct || 0);
        } else if (sortKey === 'price') {
          va = parseFloat(a.ltp || a.close || 0);
          vb = parseFloat(b.ltp || b.close || 0);
        } else if (sortKey === 'vol') {
          va = parseFloat(a.volume || a.vol || 0);
          vb = parseFloat(b.volume || b.vol || 0);
        } else {
          va = (a.symbol || '').toLowerCase();
          vb = (b.symbol || '').toLowerCase();
          return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
        }
        return sortDir === 'asc' ? va - vb : vb - va;
      });

      const arrow = (key) => {
        if (sortKey !== key) return '<span style="color:#444">⇅</span>';
        return sortDir === 'desc' ? '▼' : '▲';
      };

      return `
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;flex-wrap:wrap">
          <div class="section-hdr" style="margin:0">${data.length} stocks found</div>
          <div style="font-size:12px;color:var(--subtext)">Sort by:</div>
          <button class="btn-sm ${sortKey==='pct'?'active':''}" onclick="runScreenerSort('${slug}','pct','${sortKey==='pct'&&sortDir==='desc'?'asc':'desc'}')">% Change ${arrow('pct')}</button>
          <button class="btn-sm ${sortKey==='price'?'active':''}" onclick="runScreenerSort('${slug}','price','${sortKey==='price'&&sortDir==='desc'?'asc':'desc'}')">Price ${arrow('price')}</button>
          <button class="btn-sm ${sortKey==='vol'?'active':''}" onclick="runScreenerSort('${slug}','vol','${sortKey==='vol'&&sortDir==='desc'?'asc':'desc'}')">Volume ${arrow('vol')}</button>
          <button class="btn-sm ${sortKey==='sym'?'active':''}" onclick="runScreenerSort('${slug}','sym','${sortKey==='sym'&&sortDir==='asc'?'desc':'asc'}')">A-Z ${arrow('sym')}</button>
        </div>
        <div style="overflow-x:auto">
          <table class="market-table">
            <thead><tr>
              <th>#</th><th>Symbol</th><th>Company</th><th>Price</th><th>Change %</th><th>Volume</th>
            </tr></thead>
            <tbody>
              ${sorted.map((r, i) => {
                const chg   = parseFloat(r.per_chg || r.change_pct || 0);
                const cls   = chg >= 0 ? 'up-col' : 'dn-col';
                const arrow2 = chg >= 0 ? '▲' : '▼';
                const co    = (r.company || r.name || '').substring(0, 22);
                return `<tr onclick="quickLoad('${escHTML(r.symbol)}')">
                  <td style="color:var(--subtext)">${i+1}</td>
                  <td class="sym-col">${escHTML(r.symbol)}</td>
                  <td style="color:var(--subtext);font-size:12px">${escHTML(co)}</td>
                  <td>₹${fmtNum(r.ltp || r.close || 0)}</td>
                  <td class="${cls}" style="font-weight:700">${arrow2} ${Math.abs(chg).toFixed(2)}%</td>
                  <td style="color:var(--subtext)">${fmtVol(r.volume || r.vol || 0)}</td>
                </tr>`;
              }).join('')}
            </tbody>
          </table>
        </div>`;
    };

    // Store data globally for re-sort
    window._screenerData = rows;
    window._screenerSlug = slug;
    result.innerHTML = renderTable(rows, 'pct', 'desc');

  } catch(e) {
    result.innerHTML = `<div class="loading-box" style="color:var(--red)">❌ ${escHTML(e.message)}</div>`;
  }
}

function runScreenerSort(slug, key, dir) {
  const result = document.getElementById('screener-result');
  if (!window._screenerData) return;
  const data = window._screenerData;
  const sorted = [...data].sort((a, b) => {
    let va, vb;
    if (key === 'pct') {
      va = parseFloat(a.per_chg || a.change_pct || 0);
      vb = parseFloat(b.per_chg || b.change_pct || 0);
    } else if (key === 'price') {
      va = parseFloat(a.ltp || a.close || 0);
      vb = parseFloat(b.ltp || b.close || 0);
    } else if (key === 'vol') {
      va = parseFloat(a.volume || a.vol || 0);
      vb = parseFloat(b.volume || b.vol || 0);
    } else {
      va = (a.symbol || '').toLowerCase();
      vb = (b.symbol || '').toLowerCase();
      return dir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
    }
    return dir === 'asc' ? va - vb : vb - va;
  });

  const arrow = (k) => {
    if (key !== k) return '<span style="color:#444">⇅</span>';
    return dir === 'desc' ? '▼' : '▲';
  };

  result.innerHTML = `
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;flex-wrap:wrap">
      <div class="section-hdr" style="margin:0">${data.length} stocks found</div>
      <div style="font-size:12px;color:var(--subtext)">Sort by:</div>
      <button class="btn-sm ${key==='pct'?'active':''}" onclick="runScreenerSort('${slug}','pct','${key==='pct'&&dir==='desc'?'asc':'desc'}')">% Change ${arrow('pct')}</button>
      <button class="btn-sm ${key==='price'?'active':''}" onclick="runScreenerSort('${slug}','price','${key==='price'&&dir==='desc'?'asc':'desc'}')">Price ${arrow('price')}</button>
      <button class="btn-sm ${key==='vol'?'active':''}" onclick="runScreenerSort('${slug}','vol','${key==='vol'&&dir==='desc'?'asc':'desc'}')">Volume ${arrow('vol')}</button>
      <button class="btn-sm ${key==='sym'?'active':''}" onclick="runScreenerSort('${slug}','sym','${key==='sym'&&dir==='asc'?'desc':'asc'}')">A-Z ${arrow('sym')}</button>
    </div>
    <div style="overflow-x:auto">
      <table class="market-table">
        <thead><tr>
          <th>#</th><th>Symbol</th><th>Company</th><th>Price</th><th>Change %</th><th>Volume</th>
        </tr></thead>
        <tbody>
          ${sorted.map((r, i) => {
            const chg    = parseFloat(r.per_chg || r.change_pct || 0);
            const cls    = chg >= 0 ? 'up-col' : 'dn-col';
            const arr2   = chg >= 0 ? '▲' : '▼';
            const co     = (r.company || r.name || '').substring(0, 22);
            return `<tr onclick="quickLoad('${escHTML(r.symbol)}')">
              <td style="color:var(--subtext)">${i+1}</td>
              <td class="sym-col">${escHTML(r.symbol)}</td>
              <td style="color:var(--subtext);font-size:12px">${escHTML(co)}</td>
              <td>₹${fmtNum(r.ltp || r.close || 0)}</td>
              <td class="${cls}" style="font-weight:700">${arr2} ${Math.abs(chg).toFixed(2)}%</td>
              <td style="color:var(--subtext)">${fmtVol(r.volume || r.vol || 0)}</td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
    </div>`;
}

// ── ETF ────────────────────────────────────────
async function loadEtf(type, btn) {
  if (btn) {
    document.querySelectorAll('#page-etf .pill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  }
  const cont = document.getElementById('etf-content');
  cont.innerHTML = '<div class="loading-box">⏳ ETF data load ho rahi hai...</div>';

  try {
    const endpoint = type === 'screener' ? '/api/etf/screener' : '/api/etf/list';
    const res  = await fetch(endpoint);
    const etfs = await res.json();

    if (!etfs || etfs.error || !etfs.length) {
      cont.innerHTML = '<div class="loading-box">⚠️ ETF data available nahi</div>';
      return;
    }

    cont.innerHTML = `<div class="etf-table-wrap">
      <table class="market-table">
        <thead><tr>
          <th>#</th><th>Symbol</th><th>Name</th>
          <th>Price</th><th>Change %</th><th>Volume</th>
        </tr></thead>
        <tbody>
          ${etfs.map((e, i) => {
            const chg = parseFloat(e.chg) || 0;
            const cls = chg >= 0 ? 'up-col' : 'dn-col';
            const arrow = chg >= 0 ? '▲' : '▼';
            return `<tr onclick="quickLoad('${escHTML(e.symbol)}')">
              <td style="color:var(--subtext)">${i+1}</td>
              <td class="sym-col">${escHTML(e.symbol)}</td>
              <td style="color:var(--subtext);font-size:12px">${escHTML((e.name||'').substring(0,35))}</td>
              <td>₹${fmtNum(e.ltp)}</td>
              <td class="${cls}">${arrow} ${Math.abs(chg).toFixed(2)}%</td>
              <td style="color:var(--subtext)">${fmtVol(e.vol)}</td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
    </div>`;
  } catch(e) {
    cont.innerHTML = `<div class="loading-box" style="color:var(--red)">❌ ${escHTML(e.message)}</div>`;
  }
}

// ── IPO Page (loaded via nav if added) ────────
async function loadIpo() {
  const cont = document.getElementById('ipo-content');
  if (!cont) return;
  cont.innerHTML = '<div class="loading-box">⏳ IPO data load ho rahi hai...</div>';
  try {
    const res  = await fetch('/api/ipo');
    const ipos = await res.json();
    if (!ipos || ipos.error || !ipos.length) {
      cont.innerHTML = '<div class="loading-box">⚠️ IPO data nahi mila</div>';
      return;
    }
    cont.innerHTML = ipos.map(ipo => {
      const statusCol = ipo.status === 'Open' ? 'var(--green)' : ipo.status === 'Upcoming' ? 'var(--yellow)' : 'var(--subtext)';
      const scoreCol  = ipo.score >= 5 ? 'var(--green)' : ipo.score >= 3 ? 'var(--yellow)' : 'var(--red)';
      const gmpCol    = ipo.gmp > 0 ? 'var(--green)' : ipo.gmp < 0 ? 'var(--red)' : 'var(--subtext)';
      return `<div class="ipo-card" style="background:var(--card);border-radius:12px;padding:16px;margin-bottom:12px;border:1px solid var(--border)">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
          <div>
            <div style="font-size:16px;font-weight:700">${escHTML(ipo.company)}</div>
            <div style="font-size:12px;color:var(--subtext);margin-top:4px">
              ${escHTML(ipo.category)} • ${escHTML(ipo.open_date)} → ${escHTML(ipo.close_date)}
            </div>
          </div>
          <div style="text-align:right">
            <div style="font-size:13px;font-weight:700;color:${statusCol}">${escHTML(ipo.status)}</div>
            <div style="font-size:20px;font-weight:800;color:${scoreCol}">${ipo.score}/10</div>
          </div>
        </div>
        <div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:12px;font-size:13px">
          <div><span style="color:var(--subtext)">Price: </span><b>${escHTML(ipo.price_band || 'N/A')}</b></div>
          <div><span style="color:var(--subtext)">Size: </span><b>₹${ipo.issue_size || 'N/A'}Cr</b></div>
          <div><span style="color:var(--subtext)">GMP: </span><b style="color:${gmpCol}">${ipo.gmp !== null ? '₹'+ipo.gmp : 'N/A'}</b></div>
          <div><span style="color:var(--subtext)">Subscribed: </span><b>${ipo.subscription ? ipo.subscription.toFixed(1)+'x' : 'N/A'}</b></div>
        </div>
        <div style="margin-top:10px;font-size:11px;color:var(--subtext)">
          ${(ipo.score_reasons || []).join(' &nbsp;|&nbsp; ')}
        </div>
      </div>`;
    }).join('');
  } catch(e) {
    cont.innerHTML = `<div class="loading-box" style="color:var(--red)">❌ ${escHTML(e.message)}</div>`;
  }
}

// ── News & Docs (right panel) ──────────────────
async function loadNews(sym) {
  if (!sym) return;
  try {
    const res  = await fetch(`/api/news/${sym}`);
    const data = await res.json();
    const news = data.news || [];
    const docs = data.docs || [];

    let html = '';
    if (news.length) {
      html += `<div class="section-hdr" style="margin-top:8px">📰 Announcements</div>`;
      html += news.map(n => `<div style="padding:8px 4px;border-bottom:1px solid var(--border)">
        <a href="${escHTML(n.link)}" target="_blank" style="color:var(--text);text-decoration:none;font-size:12px;line-height:1.4">${escHTML(n.title)}</a>
        <div style="font-size:10px;color:var(--subtext);margin-top:3px">${escHTML(n.date)}</div>
      </div>`).join('');
    }
    if (docs.length) {
      html += `<div class="section-hdr" style="margin-top:12px">📄 Annual Reports</div>`;
      html += docs.map(d => `<div style="padding:8px 4px;border-bottom:1px solid var(--border)">
        <a href="${escHTML(d.link)}" target="_blank" style="color:var(--accent);text-decoration:none;font-size:12px">📥 ${escHTML(d.title)}</a>
      </div>`).join('');
    }
    if (!html) html = '<div style="padding:12px 4px;color:var(--subtext);font-size:12px">Koi news/docs nahi mili</div>';

    // Inject into panel body if news section exists
    const newsEl = document.getElementById('news-section');
    if (newsEl) newsEl.innerHTML = html;
  } catch {}
}

// ══════════════════════════════════════════════
// HEATMAP — Index categories + Stock heatmap
// ══════════════════════════════════════════════

async function loadHeatmap(cat) {
  const cont = document.getElementById('home-tab-content');
  cont.innerHTML = '<div class="loading-box">⏳ Indices load ho rahi hain...</div>';
  heatmapHistory = [];  // reset stack

  try {
    const res  = await fetch('/api/indices');
    const rows = await res.json();
    if (!rows || rows.error) {
      cont.innerHTML = '<div class="loading-box">⚠️ Indices data nahi mila</div>';
      return;
    }
    const filtered = rows.filter(r => r.cat === cat);
    renderIndexHeatmap(cat, filtered, cont);
  } catch(e) {
    cont.innerHTML = `<div class="loading-box" style="color:var(--red)">❌ ${escHTML(e.message)}</div>`;
  }
}

function renderIndexHeatmap(cat, rows, cont) {
  const titles = {
    broad: '📊 Broad Market Indices',
    sectoral: '🏭 Sectoral Indices',
    thematic: '🎯 Thematic Indices',
    strategy: '⚙️ Strategy Indices'
  };

  const sorted = [...rows].sort((a,b) => b.chg - a.chg);

  cont.innerHTML = `
    <div class="heatmap-section-hdr">
      <div style="font-size:15px;font-weight:700">${titles[cat] || cat} <span style="color:var(--subtext);font-size:12px">(${rows.length})</span></div>
      <div style="font-size:11px;color:var(--subtext)">Index click karo → Stocks dekhो</div>
    </div>
    <div class="heatmap-grid">
      ${sorted.map(r => {
        const chg = parseFloat(r.chg) || 0;
        const bg  = heatmapColor(chg);
        const disp = r.name.replace(/^NIFTY\s*/i,'').replace(/\s*INDEX$/i,'').substring(0,16);
        return `<div class="heatmap-tile" style="background:${bg}" onclick="loadIndexStocks('${escHTML(r.name)}')">
          <div class="ht-name">${escHTML(disp)}</div>
          <div class="ht-val">${r.last ? '₹'+fmtNum(r.last) : ''}</div>
          <div class="ht-chg">${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%</div>
        </div>`;
      }).join('')}
    </div>`;
}

async function loadIndexStocks(indexName) {
  const cont = document.getElementById('home-tab-content');
  heatmapHistory.push(cont.innerHTML);  // save for back button

  cont.innerHTML = `<div class="loading-box">⏳ ${escHTML(indexName)} ke stocks load ho rahe hain...</div>`;

  try {
    const res  = await fetch(`/api/index-stocks?index=${encodeURIComponent(indexName)}`);
    const rows = await res.json();

    if (!rows || rows.error || !rows.length) {
      cont.innerHTML = `<div class="loading-box">⚠️ ${escHTML(indexName)} ke stocks nahi mile</div>`;
      return;
    }

    const sorted = [...rows].sort((a,b) => b.chg - a.chg);

    cont.innerHTML = `
      <div class="heatmap-section-hdr">
        <button class="heatmap-back-btn" onclick="heatmapGoBack()">◀ Back</button>
        <div style="font-size:14px;font-weight:700">📊 ${escHTML(indexName)} <span style="color:var(--subtext);font-size:12px">(${rows.length} stocks)</span></div>
        <div style="font-size:11px;color:var(--subtext)">Stock click → Analyze</div>
      </div>
      <div class="stock-heatmap-grid">
        ${sorted.map(r => {
          const chg = parseFloat(r.chg) || 0;
          const bg  = heatmapColor(chg);
          return `<div class="stock-heatmap-tile" style="background:${bg}" onclick="quickLoad('${escHTML(r.symbol)}')">
            <div class="sht-sym">${escHTML(r.symbol)}</div>
            <div class="sht-ltp">${r.ltp ? '₹'+fmtNum(r.ltp) : ''}</div>
            <div class="sht-chg">${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%</div>
          </div>`;
        }).join('')}
      </div>`;
  } catch(e) {
    cont.innerHTML = `<div class="loading-box" style="color:var(--red)">❌ ${escHTML(e.message)}</div>`;
  }
}

function heatmapGoBack() {
  if (heatmapHistory.length > 0) {
    document.getElementById('home-tab-content').innerHTML = heatmapHistory.pop();
  }
}

function heatmapColor(chg) {
  if (chg >=  3) return '#005000';
  if (chg >=  1) return '#1B5E20';
  if (chg >=  0) return '#2E7D32';
  if (chg >= -1) return '#7B1A1A';
  if (chg >= -3) return '#B71C1C';
  return '#4A0000';
}

// ══════════════════════════════════════════════
// IPO HUB — Left list + Right detail
// ══════════════════════════════════════════════
let ipoSelected = null;

async function loadIpo() {
  const cont = document.getElementById('ipo-content');
  if (!cont) return;

  cont.innerHTML = `
    <div class="ipo-layout">
      <div class="ipo-left">
        <div style="background:#130D1A;padding:8px 10px;font-size:12px;font-weight:700;color:#C678FF;border-bottom:1px solid var(--border)">
          🚀 IPO List
        </div>
        <div class="ipo-filter-row" id="ipo-filters">
          <button class="ipo-filter-btn active" onclick="ipoFilter('All',this)">All</button>
          <button class="ipo-filter-btn" onclick="ipoFilter('Open',this)" style="color:var(--green)">🟢 Open</button>
          <button class="ipo-filter-btn" onclick="ipoFilter('Upcoming',this)" style="color:var(--yellow)">🟡 Next</button>
          <button class="ipo-filter-btn" onclick="ipoFilter('Closed',this)" style="color:#888">⬛ Done</button>
        </div>
        <div class="ipo-list-scroll" id="ipo-list-scroll">
          <div class="loading-box">⏳ Loading IPOs...</div>
        </div>
      </div>
      <div class="ipo-right" id="ipo-right">
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:var(--subtext);padding:40px">
          <div style="font-size:48px;margin-bottom:12px">🚀</div>
          <div style="font-size:16px;font-weight:600;color:var(--text);margin-bottom:8px">Koi IPO select karo</div>
          <div style="font-size:13px;text-align:center">Left panel se IPO pe click karo<br>Score + details yahan dikhenge</div>
        </div>
      </div>
    </div>`;

  try {
    const res  = await fetch('/api/ipo');
    ipoAllData = await res.json();
    if (!ipoAllData || ipoAllData.error) {
      document.getElementById('ipo-list-scroll').innerHTML = '<div class="loading-box">⚠️ IPO data nahi mila</div>';
      return;
    }
    renderIpoList(ipoAllData);
    // Auto-select first IPO
    if (ipoAllData.length > 0) renderIpoDetail(ipoAllData[0]);
  } catch(e) {
    document.getElementById('ipo-list-scroll').innerHTML = `<div class="loading-box" style="color:var(--red)">❌ ${escHTML(e.message)}</div>`;
  }
}

function ipoFilter(status, btn) {
  document.querySelectorAll('.ipo-filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const filtered = status === 'All' ? ipoAllData : ipoAllData.filter(i => i.status === status);
  renderIpoList(filtered);
}

function renderIpoList(ipos) {
  const cont = document.getElementById('ipo-list-scroll');
  if (!ipos || !ipos.length) {
    cont.innerHTML = '<div class="loading-box" style="font-size:12px">Koi IPO nahi mila</div>';
    return;
  }

  let lastStatus = null;
  const statusNames = {Open:'Currently Open', Upcoming:'Upcoming', Closed:'Recently Closed'};
  const statusIcons = {Open:'🟢', Upcoming:'🟡', Closed:'⬛'};

  cont.innerHTML = ipos.map(ipo => {
    const status = ipo.status || 'Upcoming';
    const sc = status === 'Open' ? 'var(--green)' : status === 'Upcoming' ? 'var(--yellow)' : '#888';
    const score = ipo.score || 0;
    const scoreCol = score >= 7 ? 'var(--green)' : score >= 5 ? 'var(--yellow)' : score >= 3 ? 'var(--orange)' : 'var(--red)';
    const catCol = ipo.category === 'Mainboard' ? 'var(--accent)' : 'var(--orange)';
    const gmp = ipo.gmp;
    const pn  = ipo.price_num || 0;
    let gmpHtml = '';
    if (gmp !== null && gmp !== undefined && pn) {
      const gp = (gmp/pn)*100;
      const gc = gmp > 0 ? 'var(--green)' : 'var(--red)';
      gmpHtml = `<div class="ipo-row-gmp" style="color:${gc}">GMP ₹${gmp > 0 ? '+' : ''}${gmp} (${gp > 0 ? '+' : ''}${gp.toFixed(1)}%)</div>`;
    }

    let divider = '';
    if (status !== lastStatus) {
      lastStatus = status;
      divider = `<div style="background:#0D0D1A;padding:5px 10px;font-size:10px;font-weight:700;color:${sc}">${statusIcons[status]} ${statusNames[status] || status}</div>`;
    }

    return `${divider}<div class="ipo-row" id="ipo-row-${escHTML(ipo.company.replace(/\s/g,'_'))}" onclick="selectIpo(this,'${escHTML(ipo.company)}')">
      <div style="display:flex;justify-content:space-between;align-items:flex-start">
        <div style="flex:1;min-width:0">
          <span class="ipo-cat-badge" style="background:${catCol}">${escHTML(ipo.category || 'IPO')}</span>
          <div class="ipo-row-name">${escHTML(ipo.company)}</div>
          <div class="ipo-row-date">${escHTML(ipo.open_date || '')} ${ipo.close_date ? '→ '+ipo.close_date : ''}</div>
          ${gmpHtml}
        </div>
        <div class="ipo-score-badge" style="background:${scoreCol};margin-left:8px;flex-shrink:0">${score}/10</div>
      </div>
    </div>`;
  }).join('');
}

function selectIpo(el, company) {
  document.querySelectorAll('.ipo-row').forEach(r => r.classList.remove('selected'));
  el.classList.add('selected');
  const ipo = ipoAllData.find(i => i.company === company);
  if (ipo) renderIpoDetail(ipo);
}

function renderIpoDetail(ipo) {
  const cont = document.getElementById('ipo-right');
  if (!cont) return;

  const score = ipo.score || 0;
  const scoreCol = score >= 7 ? 'var(--green)' : score >= 5 ? 'var(--yellow)' : score >= 3 ? 'var(--orange)' : 'var(--red)';
  const verdict  = score >= 7 ? '✅ APPLY karo!' : score >= 5 ? '⚠️ Consider karo' : score >= 3 ? '⚠️ Risky hai' : '❌ Skip karo';
  const statusCol = ipo.status === 'Open' ? 'var(--green)' : ipo.status === 'Upcoming' ? 'var(--yellow)' : '#888';
  const catCol    = ipo.category === 'Mainboard' ? 'var(--accent)' : 'var(--orange)';

  const gmp = ipo.gmp;
  const pn  = ipo.price_num || 0;
  let gmpStr = 'N/A', gmpCol = 'var(--subtext)';
  if (gmp !== null && gmp !== undefined && pn) {
    const gp = (gmp/pn)*100;
    gmpStr = `₹${gmp > 0 ? '+' : ''}${gmp} (${gp > 0 ? '+' : ''}${gp.toFixed(1)}%)`;
    gmpCol = gmp > 0 ? 'var(--green)' : 'var(--red)';
  }

  const sub = ipo.subscription;
  const subStr = sub ? `${sub.toFixed(1)}x subscribed` : 'N/A';
  const subCol = sub ? (sub > 10 ? 'var(--green)' : sub > 2 ? 'var(--yellow)' : 'var(--red)') : 'var(--subtext)';

  const detailUrl = ipo.detail_url || `https://ipowatch.in/${ipo.company.toLowerCase().replace(/\s+/g,'-')}-ipo-date-review-price-allotment-details/`;

  const reasons = ipo.score_reasons || [];

  cont.innerHTML = `
    <div style="padding:12px">
      <!-- Top card -->
      <div class="ipo-detail-card" style="border-color:${scoreCol}">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
          <div style="flex:1">
            <div style="display:flex;gap:6px;margin-bottom:6px;flex-wrap:wrap">
              <span class="ipo-cat-badge" style="background:${catCol}">${escHTML(ipo.category || 'IPO')}</span>
              <span style="font-size:11px;font-weight:700;color:${statusCol};background:rgba(0,0,0,0.3);padding:2px 8px;border-radius:4px">${escHTML(ipo.status)}</span>
            </div>
            <div style="font-size:20px;font-weight:800;margin-bottom:6px">${escHTML(ipo.company)}</div>
            ${ipo.price_band ? `<div style="font-size:14px;color:var(--accent)">💰 Price: ${escHTML(ipo.price_band)}</div>` : ''}
          </div>
          <div style="text-align:center;background:${scoreCol};padding:12px 18px;border-radius:10px;color:black">
            <div style="font-size:28px;font-weight:900">${score}</div>
            <div style="font-size:11px;font-weight:700">/ 10</div>
            <div style="font-size:11px;margin-top:4px;font-weight:700">${verdict}</div>
          </div>
        </div>
      </div>

      <!-- Dates -->
      <div style="background:var(--card2);border-radius:8px;padding:10px 14px;margin-bottom:8px;display:flex;gap:20px;flex-wrap:wrap">
        <div><span style="color:var(--subtext);font-size:11px">📅 Open: </span><b style="color:var(--green)">${escHTML(ipo.open_date || 'TBD')}</b></div>
        <div><span style="color:var(--subtext);font-size:11px">📅 Close: </span><b style="color:var(--red)">${escHTML(ipo.close_date || 'TBD')}</b></div>
        ${ipo.est_listing ? `<div><span style="color:var(--subtext);font-size:11px">🎯 Listing: </span><b style="color:var(--accent)">${escHTML(ipo.est_listing)}</b></div>` : ''}
      </div>

      <!-- Info grid -->
      <div class="ipo-info-grid">
        <div class="ipo-info-cell">
          <div class="ipo-info-label">📈 GMP (Grey Market)</div>
          <div class="ipo-info-val" style="color:${gmpCol}">${gmpStr}</div>
        </div>
        <div class="ipo-info-cell">
          <div class="ipo-info-label">📊 Subscription</div>
          <div class="ipo-info-val" style="color:${subCol}">${subStr}</div>
        </div>
        <div class="ipo-info-cell">
          <div class="ipo-info-label">🏢 Issue Size</div>
          <div class="ipo-info-val">${ipo.issue_size ? '₹'+ipo.issue_size.toFixed(0)+'Cr' : 'N/A'}</div>
        </div>
        <div class="ipo-info-cell">
          <div class="ipo-info-label">📦 Lot Size</div>
          <div class="ipo-info-val" style="color:var(--subtext)">${ipo.lot_size ? ipo.lot_size+' shares' : 'N/A'}</div>
        </div>
        <div class="ipo-info-cell">
          <div class="ipo-info-label">📋 Registrar</div>
          <div class="ipo-info-val" style="color:var(--subtext);font-size:12px">${escHTML(ipo.registrar || 'N/A')}</div>
        </div>
        <div class="ipo-info-cell">
          <div class="ipo-info-label">🏷️ Category</div>
          <div class="ipo-info-val" style="color:${catCol}">${escHTML(ipo.category || 'N/A')}</div>
        </div>
      </div>

      <!-- Score breakdown -->
      <div class="ipo-score-breakdown">
        <div style="font-size:12px;font-weight:700;color:#C678FF;margin-bottom:10px">📊 Score Breakdown</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px">
          ${reasons.map(r => {
            const col = r.startsWith('✅') ? 'var(--green)' : r.startsWith('❌') ? 'var(--red)' : r.startsWith('⚠️') ? 'var(--yellow)' : 'var(--subtext)';
            return `<div style="font-size:11px;color:${col};padding:3px 0">${escHTML(r)}</div>`;
          }).join('')}
        </div>
        <div style="font-size:10px;color:#444;margin-top:8px">
          Score logic: GMP>20%(+2) GMP>0%(+1) Sub>10x(+2) Sub>2x(+1) Price≤₹500(+1) Mainboard(+1) Size>500Cr(+1) Good Reg(+1)
        </div>
      </div>

      <!-- Action buttons -->
      <a href="${escHTML(detailUrl)}" target="_blank" class="ipo-action-btn" style="background:#0A1A35;color:#4FC3F7">
        📋 IPO Full Details → ipowatch.in
        <div style="font-size:11px;font-weight:400;color:var(--subtext);margin-top:3px">Review • Price • Allotment • GMP • Listing details</div>
      </a>
      <a href="https://www.nseindia.com/companies-listing/corporate-filings-annual-reports" target="_blank" class="ipo-action-btn" style="background:#0A200A;color:var(--green)">
        📊 NSE Annual Reports & Filings
        <div style="font-size:11px;font-weight:400;color:var(--subtext);margin-top:3px">NSE pe list hone ke baad Annual Reports milenge</div>
      </a>
      ${ipo.registrar ? `
      <div style="background:#0A0A18;border-radius:8px;padding:12px;margin-top:8px">
        <div style="font-size:11px;font-weight:700;color:var(--subtext);margin-bottom:6px">ℹ️ Registrar kya karta hai?</div>
        <div style="font-size:11px;color:#555">IPO allotment aur refund <b style="color:var(--subtext)">${escHTML(ipo.registrar)}</b> handle karta hai. Allotment status check karne ke liye inki website pe jao.</div>
        ${getRegistrarUrl(ipo.registrar) ? `<a href="${getRegistrarUrl(ipo.registrar)}" target="_blank" class="ipo-action-btn" style="background:#0A1A20;color:#4FC3F7;margin-top:8px;font-size:12px">🔗 Check Allotment Status — ${escHTML(ipo.registrar)}</a>` : ''}
      </div>` : ''}
    </div>`;
}

function getRegistrarUrl(reg) {
  if (!reg) return null;
  const r = reg.toLowerCase();
  if (r.includes('kfin'))       return 'https://ipostatus.kfintech.com/';
  if (r.includes('link intime')) return 'https://linkintime.co.in/MIPO/Ipoallotment.html';
  if (r.includes('bigshare'))   return 'https://www.bigshareonline.com/IPOStatus.aspx';
  if (r.includes('skyline'))    return 'https://www.skylinerta.com/ipo.php';
  if (r.includes('cameo'))      return 'https://www.cameoindia.com/ipo/';
  return null;
}

// ── NSE Live button ────────────────────────────
function openNSELive() {
  const sym = currentSym;
  if (sym) window.open(`https://www.nseindia.com/get-quotes/equity?symbol=${sym}`, '_blank');
}

function openScreenerIn() {
  const url = currentData?.page_url;
  if (url) window.open(url.startsWith('http') ? url : 'https://www.screener.in' + url, '_blank');
  else if (currentSym) window.open(`https://www.screener.in/company/${currentSym}/`, '_blank');
}

function toggleConsolidated() {
  if (!currentSym) return;
  const isCons = currentData?.is_consolidated;
  if (isCons) loadStockByUrl(`https://www.screener.in/company/${currentSym}/`, currentData?.name || currentSym);
  else loadStockByUrl(`https://www.screener.in/company/${currentSym}/consolidated/`, currentData?.name || currentSym);
}

// ── Analysis Panel ────────────────────────────
function openAnalysisPanel(title) {
  document.getElementById('analysis-panel').style.display = 'flex';
  document.getElementById('panel-title').textContent = title;
  document.getElementById('panel-body').innerHTML = `
    <div class="loading-full">
      <div class="spinner"></div>
      <div>Stock data fetch ho rahi hai — <b>${escHTML(title)}</b></div>
    </div>`;
  document.getElementById('rpanel-indices').style.display = 'block';
  document.getElementById('rpanel-news').style.display = 'none';
}

function closeAnalysis() {
  document.getElementById('analysis-panel').style.display = 'none';
  currentData = null; currentSym = null; currentUrl = null;
  if (currentPriceChart) { currentPriceChart.destroy(); currentPriceChart = null; }
  // Restore previous page hash
  const prev = sessionStorage.getItem('prev_hash') || 'home';
  history.replaceState(null, '', '#' + prev);
}

// ── Panel Search (search bar inside analysis panel) ──
let panelSearchTimer = null;

function onPanelSearchInput() {
  clearTimeout(panelSearchTimer);
  const q = document.getElementById('panel-search-input').value.trim();
  if (q.length < 2) { closePanelDropdown(); return; }
  panelSearchTimer = setTimeout(() => fetchPanelSuggestions(q), 300);
}

async function fetchPanelSuggestions(q) {
  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    showPanelDropdown(data);
  } catch { closePanelDropdown(); }
}

function showPanelDropdown(results) {
  const dd = document.getElementById('panel-search-dropdown');
  if (!results || !results.length) { closePanelDropdown(); return; }
  dd.innerHTML = results.map(r => {
    let sym = r.symbol || '';
    if (!sym && r.url) { const m = r.url.match(/\/company\/([^/]+)\//i); if (m) sym = m[1].toUpperCase(); }
    if (!sym) sym = r.name.split(' ')[0].toUpperCase();
    return `<div class="dd-item" onclick="loadFromPanelSearch('${escHTML(r.url)}','${escHTML(r.name)}')">
      <span class="sym">${escHTML(sym)}</span>
      <span class="name">${escHTML(r.name)}</span>
    </div>`;
  }).join('');
  dd.classList.add('open');
}

function closePanelDropdown() {
  const dd = document.getElementById('panel-search-dropdown');
  if (dd) dd.classList.remove('open');
}

function onPanelSearchKey(e) {
  if (e.key === 'Enter') {
    const q = document.getElementById('panel-search-input').value.trim();
    if (q) { closePanelDropdown(); loadStockBySymbol(q.toUpperCase()); document.getElementById('panel-search-input').value = ''; }
  }
  if (e.key === 'Escape') closePanelDropdown();
}

function loadFromPanelSearch(url, name) {
  closePanelDropdown();
  document.getElementById('panel-search-input').value = '';
  loadStockByUrl(url, name);
}

// ══════════════════════════════════════════════
// RIGHT PANEL — Indices + News
// ══════════════════════════════════════════════
async function loadRpIndices() {
  if (rpIndicesLoaded) return;
  try {
    const res  = await fetch('/api/indices');
    const rows = await res.json();
    if (!rows || rows.error) return;

    const cats = {broad:'broad', sectoral:'sectoral', thematic:'thematic', strategy:'strategy'};
    for (const [cat, key] of Object.entries(cats)) {
      const filtered = rows.filter(r => r.cat === cat).sort((a,b) => b.chg - a.chg);
      const cntEl = document.getElementById(`rp-cnt-${cat}`);
      const rowsEl = document.getElementById(`rp-rows-${cat}`);
      if (cntEl) cntEl.textContent = filtered.length;
      if (rowsEl) {
        rowsEl.innerHTML = filtered.map(r => {
          const chg = parseFloat(r.chg) || 0;
          const col = chg >= 0 ? 'var(--green)' : 'var(--red)';
          const disp = r.name.replace(/^NIFTY\s*/i,'').replace(/\s*INDEX$/i,'').substring(0,20);
          return `<div class="rp-idx-row" onclick="loadIndexStocksFromRp('${escHTML(r.name)}')">
            <span class="rp-idx-name">${escHTML(disp)}</span>
            <span class="rp-idx-chg" style="color:${col}">${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%</span>
          </div>`;
        }).join('');
      }
    }
    rpIndicesLoaded = true;
  } catch(e) { console.log('rpanel indices error:', e); }
}

function refreshRpanel() {
  rpIndicesLoaded = false;
  if (currentSym) {
    loadRpNews(currentSym, currentData?.name || currentSym);
  } else {
    loadRpIndices();
  }
}

function toggleRpSection(cat) {
  const rows = document.getElementById(`rp-rows-${cat}`);
  const arr  = document.getElementById(`rp-arr-${cat}`);
  if (!rows) return;
  const isOpen = rows.style.display !== 'none';
  rows.style.display = isOpen ? 'none' : 'block';
  if (arr) arr.textContent = isOpen ? '▸' : '▾';
}

async function loadRpNews(sym, companyName) {
  // Switch rpanel to news mode
  document.getElementById('rpanel-indices').style.display = 'none';
  document.getElementById('rpanel-news').style.display = 'block';
  const cont = document.getElementById('rpanel-news');
  cont.innerHTML = '<div style="padding:16px;color:var(--subtext);font-size:12px">⏳ Loading...</div>';

  try {
    const res  = await fetch(`/api/news/${sym}`);
    const data = await res.json();
    const news = data.news || [];
    const docs = data.docs || [];

    let html = '';

    // NSE Announcements
    html += `<div style="background:#0A1A35;padding:7px 10px;font-size:11px;font-weight:700;color:var(--accent);border-bottom:1px solid var(--border)">📢 NSE Announcements (Top 5)</div>`;
    if (news.length) {
      html += news.map(n => `<div class="rp-news-item">
        <a href="${escHTML(n.link)}" target="_blank">${escHTML(n.title)}</a>
        <div class="rp-news-date">NSE &nbsp;•&nbsp; ${escHTML(n.date)}</div>
      </div>`).join('');
    } else {
      html += '<div style="padding:10px;color:var(--subtext);font-size:11px">Announcements load nahi hui</div>';
    }

    // Annual Reports
    html += `<div style="background:#0A2A0A;padding:7px 10px;font-size:11px;font-weight:700;color:var(--green);border-bottom:1px solid var(--border);margin-top:4px">📋 Annual Reports (NSE)</div>`;
    if (docs.length) {
      html += docs.map(d => `<div class="rp-doc-item">
        <a href="${escHTML(d.link)}" target="_blank">📄 ${escHTML(d.title)}</a>
      </div>`).join('');
    } else {
      html += '<div style="padding:10px;color:var(--subtext);font-size:11px">Reports load nahi hui</div>';
    }

    // Quick links
    html += `<div style="padding:8px 0;border-top:1px solid var(--border);margin-top:6px">`;
    const encSym = encodeURIComponent(sym);
    const encCo  = encodeURIComponent(companyName || sym);
    html += `<a href="https://www.nseindia.com/companies-listing/corporate-filings-announcements?symbol=${encSym}" target="_blank" class="rp-link-btn" style="background:#1A2A4A;color:var(--accent)">🔗 NSE Corporate Filings</a>`;
    html += `<a href="https://www.bseindia.com/corporates/ann.html?scripcd=&company=${encCo}&Submit=Search" target="_blank" class="rp-link-btn" style="background:#2A1A00;color:var(--yellow)">🔗 BSE Announcements</a>`;
    html += `<a href="https://www.tradingview.com/chart/?symbol=NSE%3A${encSym}" target="_blank" class="rp-link-btn" style="background:#1A2A1A;color:var(--green)">📈 TradingView Chart</a>`;
    html += `</div>`;

    // Back to indices button
    html += `<div style="padding:6px 8px;border-top:1px solid var(--border)">
      <button class="btn-sm" style="width:100%;text-align:center" onclick="showRpIndices()">📊 Back to Indices</button>
    </div>`;

    cont.innerHTML = html;
  } catch(e) {
    cont.innerHTML = `<div style="padding:12px;color:var(--red);font-size:11px">❌ ${escHTML(e.message)}</div>`;
  }
}

function showRpIndices() {
  document.getElementById('rpanel-indices').style.display = 'block';
  document.getElementById('rpanel-news').style.display = 'none';
  loadRpIndices();
}

function loadIndexStocksFromRp(indexName) {
  // Switch to home page and load heatmap
  showPage('home');
  // Find which tab this index belongs to and switch
  loadIndexStocks(indexName);
  // Also show in home tab content
  document.querySelectorAll('#home-tabs .atab').forEach(b => b.classList.remove('active'));
  document.getElementById('home-tab-content').innerHTML = `<div class="loading-box">⏳ ${escHTML(indexName)} ke stocks load ho rahe hain...</div>`;
  fetch(`/api/index-stocks?index=${encodeURIComponent(indexName)}`)
    .then(r => r.json())
    .then(rows => {
      if (!rows || rows.error || !rows.length) {
        document.getElementById('home-tab-content').innerHTML = '<div class="loading-box">⚠️ Data nahi mila</div>';
        return;
      }
      heatmapHistory = [];
      const sorted = [...rows].sort((a,b) => b.chg - a.chg);
      document.getElementById('home-tab-content').innerHTML = `
        <div class="heatmap-section-hdr">
          <button class="heatmap-back-btn" onclick="switchHomeTab('broad')">◀ Back</button>
          <div style="font-size:14px;font-weight:700">📊 ${escHTML(indexName)} <span style="color:var(--subtext);font-size:12px">(${rows.length} stocks)</span></div>
          <div style="font-size:11px;color:var(--subtext)">Stock click → Analyze</div>
        </div>
        <div class="stock-heatmap-grid">
          ${sorted.map(r => {
            const chg = parseFloat(r.chg) || 0;
            const bg  = heatmapColor(chg);
            return `<div class="stock-heatmap-tile" style="background:${bg}" onclick="quickLoad('${escHTML(r.symbol)}')">
              <div class="sht-sym">${escHTML(r.symbol)}</div>
              <div class="sht-ltp">${r.ltp ? '₹'+fmtNum(r.ltp) : ''}</div>
              <div class="sht-chg">${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%</div>
            </div>`;
          }).join('')}
        </div>`;
    }).catch(() => {});
}

// ── Toast ──────────────────────────────────────
function showToast(msg, isError = false) {
  let toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    toast.style.cssText = `
      position:fixed;bottom:24px;right:24px;z-index:9999;
      background:var(--card);border:1px solid var(--border);
      color:var(--text);padding:12px 20px;border-radius:10px;
      font-size:13px;font-weight:600;
      box-shadow:0 4px 20px rgba(0,0,0,0.5);
      transition:opacity 0.3s;pointer-events:none;
    `;
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.style.borderColor = isError ? 'var(--red)' : 'var(--green)';
  toast.style.opacity = '1';
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => { toast.style.opacity = '0'; }, 2500);
}

// ── Helpers ────────────────────────────────────
function fmtNum(v) {
  if (v === null || v === undefined || isNaN(v)) return '—';
  const n = parseFloat(v);
  if (n >= 1e7)  return (n/1e7).toFixed(2) + 'Cr';
  if (n >= 1e5)  return (n/1e5).toFixed(2) + 'L';
  if (n >= 1000) return n.toLocaleString('en-IN', {maximumFractionDigits:2});
  return n.toFixed(2);
}

function fmtVol(v) {
  if (!v) return '—';
  const n = parseFloat(v);
  if (n >= 1e7) return (n/1e7).toFixed(2) + 'Cr';
  if (n >= 1e5) return (n/1e5).toFixed(2) + 'L';
  if (n >= 1e3) return (n/1e3).toFixed(1) + 'K';
  return n.toString();
}

function escHTML(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;')
    .replace(/'/g,'&#39;');
}

// Close dropdown when clicking outside
document.addEventListener('click', e => {
  if (!e.target.closest('.search-wrap')) closeDropdown();
});
