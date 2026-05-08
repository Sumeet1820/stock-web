// ══ Intraday & Options JS ══
let _idSym = 'NIFTY', _idTf = '15m';
let _ocSym = 'NIFTY', _pcrSym = 'NIFTY';
let _autoTimer = null;
let _alerts = JSON.parse(localStorage.getItem('id_alerts') || '[]');
let _alertCheckTimer = null;

function initIntradayPage() {
  switchIntradayTab('signals');
  startAlertChecker();
}

function switchIntradayTab(tab, btn) {
  ['signals','optionchain','pcr','alerts','settings'].forEach(t => {
    const el = document.getElementById('intraday-tab-' + t);
    if (el) el.style.display = t === tab ? '' : 'none';
  });
  document.querySelectorAll('#intraday-tabs .pill').forEach(p => p.classList.remove('active'));
  if (btn) btn.classList.add('active');
  else {
    const idx = ['signals','optionchain','pcr','alerts','settings'].indexOf(tab);
    const pills = document.querySelectorAll('#intraday-tabs .pill');
    if (pills[idx]) pills[idx].classList.add('active');
  }
  history.replaceState(null, '', '#intraday-' + tab);
  sessionStorage.setItem('prev_hash', 'intraday-' + tab);
  // Load data for the tab — use current symbol state
  if (tab === 'optionchain') loadOptionChain();
  if (tab === 'pcr') loadPcrOi();
  if (tab === 'alerts') renderAlerts();
  if (tab === 'settings') loadUpstoxSettings();
}

function setIdxSymbol(sym, btn) {
  if (!sym) return;
  _idSym = sym.trim().toUpperCase();
  document.querySelectorAll('.id-idx-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  // Clear custom input if preset button clicked
  if (btn) {
    const inp = document.getElementById('id-custom-sym');
    if (inp) inp.value = '';
    const dd = document.getElementById('id-sym-dd');
    if (dd) dd.style.display = 'none';
  }
}

let _idSymTimer = null;
async function idSearchFno(q) {
  clearTimeout(_idSymTimer);
  const dd = document.getElementById('id-sym-dd');
  if (!dd) return;
  if (!q || q.length < 1) { dd.style.display = 'none'; return; }
  _idSymTimer = setTimeout(async () => {
    try {
      const r = await fetch(`/api/search?q=${encodeURIComponent(q)}&fno=1`);
      const stocks = await r.json();
      if (!stocks || !stocks.length) { dd.style.display = 'none'; return; }
      dd.innerHTML = stocks.slice(0, 10).map(s => {
        const sym = s.symbol || s.name || '';
        const name = s.name || sym;
        const fnoBadge = s.is_fno ? `<span style="font-size:10px;background:rgba(0,230,168,0.2);color:var(--green);border-radius:3px;padding:1px 4px;margin-left:4px">F&O</span>` : '';
        return `<div style="padding:7px 12px;cursor:pointer;font-size:13px;color:var(--text);display:flex;align-items:center;gap:6px"
          onmousedown="document.getElementById('id-custom-sym').value='${sym}';document.getElementById('id-sym-dd').style.display='none';setIdxSymbol('${sym}',null);runIntradayAnalysis()"
          onmouseover="this.style.background='var(--card)'" onmouseout="this.style.background=''">
          <b style="color:var(--accent);min-width:80px">${escHTML(sym)}</b>${fnoBadge}
          <span style="color:var(--subtext);font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escHTML(name !== sym ? name : '')}</span>
        </div>`;
      }).join('');
      dd.style.display = 'block';
    } catch { dd.style.display = 'none'; }
  }, 200);
}

function setTimeframe(tf, btn) {
  _idTf = tf;
  document.querySelectorAll('.id-tf-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
}

function setOcSymbol(sym, btn) {
  if (!sym || !sym.trim()) return;
  _ocSym = sym.trim().toUpperCase();
  // Remove active from all OC index buttons
  document.querySelectorAll('#intraday-tab-optionchain .id-idx-btn').forEach(b => b.classList.remove('active'));
  if (btn) {
    btn.classList.add('active');
    const inp = document.getElementById('oc-custom-sym');
    if (inp) inp.value = '';
  }
  // Always load immediately when symbol changes
  loadOptionChain();
}

let _ocFnoTimer = null;
async function ocSearchFno(q) {
  clearTimeout(_ocFnoTimer);
  const dd = document.getElementById('oc-fno-dd');
  if (!dd) return;
  if (!q || q.length < 1) { dd.style.display = 'none'; return; }
  _ocFnoTimer = setTimeout(async () => {
    try {
      const r = await fetch(`/api/fno_stocks?q=${encodeURIComponent(q)}`);
      const stocks = await r.json();
      if (!stocks.length) { dd.style.display = 'none'; return; }
      dd.innerHTML = stocks.slice(0, 10).map(s =>
        `<div style="padding:7px 12px;cursor:pointer;font-size:13px;color:var(--text);font-weight:600"
          onmousedown="document.getElementById('oc-custom-sym').value='${s}';document.getElementById('oc-fno-dd').style.display='none';setOcSymbol('${s}',null)"
          onmouseover="this.style.background='var(--card)'" onmouseout="this.style.background=''">${s}</div>`
      ).join('');
      dd.style.display = 'block';
    } catch { dd.style.display = 'none'; }
  }, 200);
}

function setPcrSymbol(sym, btn) {
  if (!sym || !sym.trim()) return;
  _pcrSym = sym.trim().toUpperCase();
  // Remove active from all PCR index buttons
  document.querySelectorAll('#intraday-tab-pcr .id-idx-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  // Always load immediately when symbol changes
  loadPcrOi();
}
// ── Auto Refresh ──────────────────────────────────────────────────────────────
function toggleAutoRefresh() {
  const btn = document.getElementById('btn-auto-refresh');
  if (_autoTimer) {
    clearInterval(_autoTimer);
    _autoTimer = null;
    if (btn) { btn.textContent = '▶ Auto'; btn.style.background = 'rgba(0,230,168,0.1)'; }
  } else {
    runIntradayAnalysis();
    _autoTimer = setInterval(runIntradayAnalysis, 60000);
    if (btn) { btn.textContent = '⏹ Stop'; btn.style.background = 'rgba(255,61,92,0.15)'; btn.style.borderColor = 'var(--red)'; btn.style.color = 'var(--red)'; }
    showToast('Auto refresh ON — every 1 min');
  }
}

// ── Main Signal Analysis ──────────────────────────────────────────────────────
async function runIntradayAnalysis() {
  const area = document.getElementById('id-signal-area');
  if (!area) return;
  area.innerHTML = '<div class="loading-box">⏳ ' + _idSym + ' ' + _idTf + ' data fetch ho raha hai...</div>';
  try {
    const res  = await fetch('/api/intraday/signals?sym=' + _idSym + '&tf=' + _idTf);
    const data = await res.json();
    if (data.error) {
      area.innerHTML = '<div class="loading-box" style="color:var(--red)">❌ ' + escHTML(data.error) + '</div>';
      return;
    }
    area.innerHTML = renderSignals(data);
  } catch(e) {
    area.innerHTML = '<div class="loading-box" style="color:var(--red)">❌ ' + escHTML(e.message) + '</div>';
  }
}

function renderSignals(d) {
  const vColors = { strong_buy:'var(--green)', buy:'#00CC88', neutral:'var(--yellow)', sell:'var(--orange)', strong_sell:'var(--red)' };
  const vColor = vColors[d.verdict_type] || 'var(--text)';
  const score = d.score || 0;
  const barW  = score + '%';
  const barC  = score >= 60 ? 'var(--green)' : score >= 40 ? 'var(--yellow)' : 'var(--red)';

  const bull = (d.bull_reasons || []).map(r => '<div class="id-reason bull">✅ ' + escHTML(r) + '</div>').join('');
  const bear = (d.bear_reasons || []).map(r => '<div class="id-reason bear">❌ ' + escHTML(r) + '</div>').join('');

  const orb = d.orb ? '<div class="id-card"><div class="id-card-title">📐 Opening Range Breakout</div><div class="id-orb-row"><span>High: <b style="color:var(--green)">'+d.orb.high+'</b></span><span>Low: <b style="color:var(--red)">'+d.orb.low+'</b></span><span style="font-weight:700">'+escHTML(d.orb.status)+'</span></div></div>' : '';

  const vwapRow = d.vwap ? '<div class="id-metric"><span class="id-m-label">VWAP</span><span class="id-m-val" style="color:'+(d.cur>d.vwap?'var(--green)':'var(--red)')+'">'+d.vwap+'</span></div>' : '';

  return `
    <div class="id-header-bar">
      <div class="id-sym-badge">${escHTML(d.sym)} <span style="color:var(--subtext);font-size:12px">${escHTML(d.tf)}</span></div>
      <div class="id-ltp">₹${fmtNum(d.cur)}</div>
      <div class="id-verdict" style="color:${vColor}">${escHTML(d.verdict)}</div>
    </div>

    <div class="id-score-bar-wrap">
      <div style="display:flex;justify-content:space-between;margin-bottom:4px">
        <span style="font-size:12px;color:var(--subtext)">Signal Score</span>
        <span style="font-weight:700;color:${barC}">${score}/100</span>
      </div>
      <div class="id-score-track"><div class="id-score-fill" style="width:${barW};background:${barC}"></div></div>
    </div>

    <div class="id-option-hint">${escHTML(d.option_hint || '')}</div>

    <div class="id-metrics-grid">
      <div class="id-metric"><span class="id-m-label">RSI (14)</span><span class="id-m-val" style="color:${d.rsi>70?'var(--red)':d.rsi<30?'var(--orange)':'var(--green)'}">${d.rsi}</span></div>
      <div class="id-metric"><span class="id-m-label">EMA 9</span><span class="id-m-val">${d.ema9}</span></div>
      <div class="id-metric"><span class="id-m-label">EMA 21</span><span class="id-m-val">${d.ema21}</span></div>
      ${vwapRow}
      <div class="id-metric"><span class="id-m-label">MACD</span><span class="id-m-val" style="color:${d.macd_cross==='Bullish'?'var(--green)':'var(--red)'}">${d.macd} (${escHTML(d.macd_cross)})</span></div>
      <div class="id-metric"><span class="id-m-label">Supertrend</span><span class="id-m-val" style="color:${d.supertrend_signal==='BUY'?'var(--green)':'var(--red)'}">${d.supertrend} ${escHTML(d.supertrend_signal)}</span></div>
      <div class="id-metric"><span class="id-m-label">ATR</span><span class="id-m-val">${d.atr}</span></div>
      <div class="id-metric"><span class="id-m-label">BB %</span><span class="id-m-val">${d.bb_pct != null ? d.bb_pct+'%' : '—'}</span></div>
      <div class="id-metric"><span class="id-m-label">Vol Ratio</span><span class="id-m-val" style="color:${d.vol_ratio>=1.5?'var(--green)':'var(--subtext)'}">${d.vol_ratio}x</span></div>
    </div>

    ${orb}

    <div class="id-sl-tgt-grid">
      <div class="id-sl-card buy">
        <div class="id-sl-title">📈 BUY Setup</div>
        <div>Entry: <b>₹${fmtNum(d.cur)}</b></div>
        <div>SL: <b style="color:var(--red)">₹${fmtNum(d.sl_buy)}</b></div>
        <div>Target: <b style="color:var(--green)">₹${fmtNum(d.tgt_buy)}</b></div>
        <div style="font-size:11px;color:var(--subtext);margin-top:4px">R:R = 1:${d.atr>0?((d.tgt_buy-d.cur)/(d.cur-d.sl_buy)).toFixed(1):'—'}</div>
      </div>
      <div class="id-sl-card sell">
        <div class="id-sl-title">📉 SELL Setup</div>
        <div>Entry: <b>₹${fmtNum(d.cur)}</b></div>
        <div>SL: <b style="color:var(--red)">₹${fmtNum(d.sl_sell)}</b></div>
        <div>Target: <b style="color:var(--green)">₹${fmtNum(d.tgt_sell)}</b></div>
        <div style="font-size:11px;color:var(--subtext);margin-top:4px">R:R = 1:${d.atr>0?((d.cur-d.tgt_sell)/(d.sl_sell-d.cur)).toFixed(1):'—'}</div>
      </div>
    </div>

    <div class="id-reasons-grid">
      <div><div class="id-reasons-title" style="color:var(--green)">🐂 Bullish Signals</div>${bull||'<div class="id-reason" style="color:var(--subtext)">Koi bullish signal nahi</div>'}</div>
      <div><div class="id-reasons-title" style="color:var(--red)">🐻 Bearish Signals</div>${bear||'<div class="id-reason" style="color:var(--subtext)">Koi bearish signal nahi</div>'}</div>
    </div>

    ${renderHedgeAdvisor(d)}

    <div class="id-disclaimer">⚠️ Ye sirf educational analysis hai. Trading apni research aur risk tolerance ke basis pe karo. Past performance future results guarantee nahi karta.</div>`;
}

// ── Hedge Advisor ─────────────────────────────────────────────────────────────
function renderHedgeAdvisor(d) {
  const score  = d.score  || 0;
  const vtype  = d.verdict_type || 'neutral';
  const cur    = d.cur    || 0;
  const atr    = d.atr    || 0;
  const rsi    = d.rsi    || 50;
  const stSig  = d.supertrend_signal || 'SELL';
  const macd   = d.macd_cross || 'Bearish';
  const vwap   = d.vwap;

  // ── Determine market bias ──────────────────────────────────────────────────
  let bias = 'neutral';
  if (score >= 65 && stSig === 'BUY' && macd === 'Bullish') bias = 'strong_bull';
  else if (score >= 50 && (stSig === 'BUY' || macd === 'Bullish')) bias = 'bull';
  else if (score <= 35 && stSig === 'SELL' && macd === 'Bearish') bias = 'strong_bear';
  else if (score <= 45 && (stSig === 'SELL' || macd === 'Bearish')) bias = 'bear';
  else bias = 'neutral';

  // ── Strike suggestions (ATM ± 1 step) ─────────────────────────────────────
  // Round to nearest 50 for indices, 10/20/50 for stocks
  const step = cur > 20000 ? 50 : cur > 5000 ? 100 : cur > 1000 ? 50 : cur > 500 ? 20 : 10;
  const atm   = Math.round(cur / step) * step;
  const otm1  = atm + step;   // 1 step OTM call
  const otm1p = atm - step;   // 1 step OTM put

  // ── Build strategies based on bias ────────────────────────────────────────
  let strategies = [];

  if (bias === 'strong_bull') {
    strategies = [
      {
        action: 'CALL BUY',
        color: 'var(--green)',
        bg: 'rgba(0,230,168,0.08)',
        border: 'var(--green)',
        icon: '📈',
        strike: `ATM ${atm} CE`,
        reason: `Strong bullish — Score ${score}/100, Supertrend BUY, MACD Bullish`,
        risk: 'Limited (premium paid)',
        reward: 'Unlimited upside',
        when: 'Expiry tak hold karo agar trend continue kare',
        sl: `SL: ₹${fmtNum(d.sl_buy)} (stock/index pe)`,
      },
      {
        action: 'PUT SELL',
        color: '#00CC88',
        bg: 'rgba(0,204,136,0.06)',
        border: '#00CC88',
        icon: '💰',
        strike: `OTM ${otm1p} PE`,
        reason: `Strong trend — premium collect karo, put expire hoga`,
        risk: 'High (unlimited loss if reversal)',
        reward: 'Premium income',
        when: 'Sirf agar confident ho trend mein',
        sl: `Cover karo agar price ${otm1p} ke neeche jaaye`,
      },
    ];
  } else if (bias === 'bull') {
    strategies = [
      {
        action: 'CALL BUY',
        color: 'var(--green)',
        bg: 'rgba(0,230,168,0.08)',
        border: 'var(--green)',
        icon: '📈',
        strike: `ATM ${atm} CE`,
        reason: `Bullish bias — Score ${score}/100`,
        risk: 'Limited (premium paid)',
        reward: 'Good upside potential',
        when: 'Confirmation ke baad enter karo',
        sl: `SL: ₹${fmtNum(d.sl_buy)}`,
      },
      {
        action: 'BULL CALL SPREAD',
        color: 'var(--accent)',
        bg: 'rgba(77,142,255,0.08)',
        border: 'var(--accent)',
        icon: '🔀',
        strike: `BUY ${atm} CE + SELL ${otm1} CE`,
        reason: `Cost kam karo — limited upside but cheaper entry`,
        risk: 'Limited (net debit)',
        reward: `Max profit: ${step} points`,
        when: 'Moderate bullish view ke liye best',
        sl: `Exit agar ${atm} CE 50% loss ho`,
      },
    ];
  } else if (bias === 'strong_bear') {
    strategies = [
      {
        action: 'PUT BUY',
        color: 'var(--red)',
        bg: 'rgba(255,61,92,0.08)',
        border: 'var(--red)',
        icon: '📉',
        strike: `ATM ${atm} PE`,
        reason: `Strong bearish — Score ${score}/100, Supertrend SELL, MACD Bearish`,
        risk: 'Limited (premium paid)',
        reward: 'Unlimited downside capture',
        when: 'Expiry tak hold karo agar trend continue kare',
        sl: `SL: ₹${fmtNum(d.sl_sell)} (stock/index pe)`,
      },
      {
        action: 'CALL SELL',
        color: 'var(--orange)',
        bg: 'rgba(255,149,0,0.08)',
        border: 'var(--orange)',
        icon: '💰',
        strike: `OTM ${otm1} CE`,
        reason: `Bearish trend — call expire hoga, premium collect karo`,
        risk: 'High (unlimited loss if reversal)',
        reward: 'Premium income',
        when: 'Sirf agar confident ho bearish trend mein',
        sl: `Cover karo agar price ${otm1} ke upar jaaye`,
      },
    ];
  } else if (bias === 'bear') {
    strategies = [
      {
        action: 'PUT BUY',
        color: 'var(--red)',
        bg: 'rgba(255,61,92,0.08)',
        border: 'var(--red)',
        icon: '📉',
        strike: `ATM ${atm} PE`,
        reason: `Bearish bias — Score ${score}/100`,
        risk: 'Limited (premium paid)',
        reward: 'Good downside capture',
        when: 'Confirmation ke baad enter karo',
        sl: `SL: ₹${fmtNum(d.sl_sell)}`,
      },
      {
        action: 'BEAR PUT SPREAD',
        color: 'var(--accent)',
        bg: 'rgba(77,142,255,0.08)',
        border: 'var(--accent)',
        icon: '🔀',
        strike: `BUY ${atm} PE + SELL ${otm1p} PE`,
        reason: `Cost kam karo — limited downside but cheaper entry`,
        risk: 'Limited (net debit)',
        reward: `Max profit: ${step} points`,
        when: 'Moderate bearish view ke liye best',
        sl: `Exit agar ${atm} PE 50% loss ho`,
      },
    ];
  } else {
    // Neutral — suggest straddle/strangle or wait
    strategies = [
      {
        action: 'WAIT / NO TRADE',
        color: 'var(--yellow)',
        bg: 'rgba(255,214,0,0.08)',
        border: 'var(--yellow)',
        icon: '⏳',
        strike: '—',
        reason: `Mixed signals — Score ${score}/100. Clear direction nahi hai.`,
        risk: 'N/A',
        reward: 'N/A',
        when: 'Breakout ya breakdown ka wait karo',
        sl: 'N/A',
      },
      {
        action: 'SHORT STRADDLE',
        color: 'var(--subtext)',
        bg: 'rgba(139,146,184,0.08)',
        border: 'var(--subtext)',
        icon: '🎯',
        strike: `SELL ${atm} CE + SELL ${atm} PE`,
        reason: `Range-bound market — dono side premium collect karo`,
        risk: 'High (if big move happens)',
        reward: 'Double premium income',
        when: 'Sirf low volatility + expiry near ho tab',
        sl: `Exit agar price ${atm - step*2} ya ${atm + step*2} jaaye`,
      },
    ];
  }

  const biasLabels = {
    strong_bull: { text: '🚀 STRONG BULLISH', col: 'var(--green)' },
    bull:        { text: '📈 BULLISH',         col: '#00CC88' },
    neutral:     { text: '⏸️ NEUTRAL',          col: 'var(--yellow)' },
    bear:        { text: '📉 BEARISH',          col: 'var(--orange)' },
    strong_bear: { text: '🔴 STRONG BEARISH',   col: 'var(--red)' },
  };
  const bl = biasLabels[bias] || biasLabels.neutral;

  const cards = strategies.map(s => `
    <div style="background:${s.bg};border:1px solid ${s.border};border-radius:10px;padding:14px;flex:1;min-width:260px">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
        <span style="font-size:20px">${s.icon}</span>
        <div>
          <div style="font-weight:800;font-size:15px;color:${s.color}">${s.action}</div>
          <div style="font-size:12px;color:var(--subtext)">${escHTML(s.strike)}</div>
        </div>
      </div>
      <div style="font-size:12px;line-height:1.7;color:var(--text)">
        <div>📌 <b>Why:</b> ${escHTML(s.reason)}</div>
        <div>⚠️ <b>Risk:</b> <span style="color:var(--red)">${escHTML(s.risk)}</span></div>
        <div>💰 <b>Reward:</b> <span style="color:var(--green)">${escHTML(s.reward)}</span></div>
        <div>🕐 <b>Hold:</b> ${escHTML(s.when)}</div>
        <div style="margin-top:6px;padding:6px 8px;background:rgba(0,0,0,0.2);border-radius:5px;font-size:11px;color:var(--yellow)">🛑 ${escHTML(s.sl)}</div>
      </div>
    </div>`).join('');

  return `
    <div style="margin:16px 0;background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden">
      <div style="padding:12px 16px;background:var(--card2);border-bottom:1px solid var(--border);display:flex;align-items:center;gap:12px">
        <span style="font-size:18px">🛡️</span>
        <div>
          <div style="font-weight:700;font-size:14px">Options Hedge Advisor</div>
          <div style="font-size:12px;color:var(--subtext)">Expiry tak ke liye suggested strategies</div>
        </div>
        <div style="margin-left:auto;font-weight:700;color:${bl.col};font-size:13px">${bl.text}</div>
      </div>
      <div style="padding:14px;display:flex;gap:12px;flex-wrap:wrap">
        ${cards}
      </div>
      <div style="padding:8px 16px;font-size:11px;color:var(--subtext);border-top:1px solid var(--border);background:var(--card2)">
        ⚠️ ATM Strike: <b style="color:var(--yellow)">${atm}</b> | Current: <b>₹${fmtNum(cur)}</b> | ATR: <b>₹${atr}</b> | Ye suggestions educational hain — apna judgment use karo
      </div>
    </div>`;
}

// ── Option Chain ──────────────────────────────────────────────────────────────
async function loadOptionChain() {
  const cont = document.getElementById('oc-content');
  if (!cont) return;
  cont.innerHTML = '<div class="loading-box">⏳ Option chain fetch ho rahi hai... (' + _ocSym + ')</div>';
  try {
    const res  = await fetch('/api/intraday/optionchain?sym=' + encodeURIComponent(_ocSym));
    const data = await res.json();
    if (data.error) {
      cont.innerHTML = `<div style="padding:20px;background:var(--card);border:1px solid var(--orange);border-radius:10px">
        <div style="color:var(--orange);font-weight:700;margin-bottom:10px">⚠️ Option Chain Load Nahi Hua — ${escHTML(_ocSym)}</div>
        <div style="color:var(--subtext);font-size:13px">${escHTML(data.error)}</div>
      </div>`;
      return;
    }
    cont.innerHTML = renderOptionChain(data);
  } catch(e) {
    cont.innerHTML = '<div class="loading-box" style="color:var(--red)">❌ ' + escHTML(e.message) + '</div>';
  }
}

function renderOptionChain(d) {
  const spot = d.spot || 0;
  const atm  = d.atm  || 0;
  const chain = d.chain || [];
  const near = chain.filter(x => Math.abs(x.strike - spot) <= spot * 0.03);

  const rows = near.map(x => {
    const isAtm = x.strike === atm;
    const atmCls = isAtm ? 'oc-atm-row' : '';
    const ceColor = x.ce_chg_oi > 0 ? 'var(--green)' : x.ce_chg_oi < 0 ? 'var(--red)' : '';
    const peColor = x.pe_chg_oi > 0 ? 'var(--green)' : x.pe_chg_oi < 0 ? 'var(--red)' : '';
    return `<tr class="${atmCls}">
      <td style="color:var(--accent);font-weight:600">${fmtNum(x.ce_ltp)}</td>
      <td style="color:${ceColor}">${fmtVol(x.ce_oi)}</td>
      <td style="font-size:11px;color:${ceColor}">${x.ce_chg_oi>0?'+':''}${fmtVol(x.ce_chg_oi)}</td>
      <td style="color:var(--subtext);font-size:11px">${x.ce_iv?x.ce_iv.toFixed(1)+'%':'—'}</td>
      <td style="font-weight:700;${isAtm?'color:var(--yellow);font-size:15px':''}">${x.strike}</td>
      <td style="color:var(--subtext);font-size:11px">${x.pe_iv?x.pe_iv.toFixed(1)+'%':'—'}</td>
      <td style="font-size:11px;color:${peColor}">${x.pe_chg_oi>0?'+':''}${fmtVol(x.pe_chg_oi)}</td>
      <td style="color:${peColor}">${fmtVol(x.pe_oi)}</td>
      <td style="color:var(--accent);font-weight:600">${fmtNum(x.pe_ltp)}</td>
    </tr>`;
  }).join('');

  return `
    <div class="oc-summary">
      <div class="oc-sum-item"><span>Spot</span><b>₹${fmtNum(spot)}</b></div>
      <div class="oc-sum-item"><span>ATM</span><b style="color:var(--yellow)">${atm}</b></div>
      <div class="oc-sum-item"><span>PCR</span><b style="color:${d.pcr>1?'var(--green)':'var(--red)'}">${d.pcr}</b></div>
      <div class="oc-sum-item"><span>Max Pain</span><b style="color:var(--orange)">${d.max_pain}</b></div>
      <div class="oc-sum-item"><span>Expiry</span><b style="color:var(--subtext);font-size:12px">${escHTML(d.expiry||'')}</b></div>
    </div>
    <div style="overflow-x:auto;margin-top:12px">
      <table class="market-table oc-table">
        <thead><tr>
          <th colspan="4" style="text-align:center;color:var(--accent);background:rgba(77,142,255,0.1)">── CALL ──</th>
          <th style="text-align:center;color:var(--yellow)">STRIKE</th>
          <th colspan="4" style="text-align:center;color:var(--red);background:rgba(255,61,92,0.1)">── PUT ──</th>
        </tr>
        <tr>
          <th>LTP</th><th>OI</th><th>Chg OI</th><th>IV</th>
          <th style="color:var(--yellow)">Strike</th>
          <th>IV</th><th>Chg OI</th><th>OI</th><th>LTP</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
    <div style="font-size:11px;color:var(--subtext);margin-top:8px;padding:4px 8px">
      Showing ±3% strikes from spot. Total CE OI: ${fmtVol(d.total_ce_oi)} | Total PE OI: ${fmtVol(d.total_pe_oi)}
    </div>`;
}

// ── PCR & OI ──────────────────────────────────────────────────────────────────
async function loadPcrOi() {
  const cont = document.getElementById('pcr-content');
  if (!cont) return;
  cont.innerHTML = '<div class="loading-box">⏳ PCR & OI data fetch ho raha hai... (' + _pcrSym + ')</div>';
  try {
    const res  = await fetch('/api/intraday/pcr?sym=' + encodeURIComponent(_pcrSym));
    const data = await res.json();
    if (data.error) { cont.innerHTML = '<div class="loading-box" style="color:var(--red)">❌ ' + escHTML(data.error) + '</div>'; return; }
    cont.innerHTML = renderPcrOi(data);
  } catch(e) {
    cont.innerHTML = '<div class="loading-box" style="color:var(--red)">❌ ' + escHTML(e.message) + '</div>';
  }
}

function renderPcrOi(d) {
  const pcrColor = d.pcr > 1.2 ? 'var(--green)' : d.pcr > 0.8 ? 'var(--yellow)' : 'var(--red)';
  const ceRows = (d.top_ce_strikes||[]).map((x,i) =>
    `<tr><td>${i+1}</td><td style="color:var(--accent);font-weight:700">${x.strike}</td><td>${fmtVol(x.oi)}</td><td style="color:${x.chg>0?'var(--green)':'var(--red)'}">${x.chg>0?'+':''}${fmtVol(x.chg)}</td></tr>`).join('');
  const peRows = (d.top_pe_strikes||[]).map((x,i) =>
    `<tr><td>${i+1}</td><td style="color:var(--accent);font-weight:700">${x.strike}</td><td>${fmtVol(x.oi)}</td><td style="color:${x.chg>0?'var(--green)':'var(--red)'}">${x.chg>0?'+':''}${fmtVol(x.chg)}</td></tr>`).join('');

  return `
    <div class="pcr-hero">
      <div class="pcr-big">
        <div style="font-size:13px;color:var(--subtext);margin-bottom:4px">Put-Call Ratio (PCR)</div>
        <div style="font-size:48px;font-weight:900;color:${pcrColor}">${d.pcr}</div>
        <div style="font-size:14px;margin-top:6px">${escHTML(d.pcr_signal||'')}</div>
      </div>
      <div class="pcr-stats">
        <div class="pcr-stat"><span>Spot</span><b>₹${fmtNum(d.spot)}</b></div>
        <div class="pcr-stat"><span>Resistance (Max CE OI)</span><b style="color:var(--red)">₹${d.resistance||'—'}</b></div>
        <div class="pcr-stat"><span>Support (Max PE OI)</span><b style="color:var(--green)">₹${d.support||'—'}</b></div>
        <div class="pcr-stat"><span>Total CE OI</span><b style="color:var(--accent)">${fmtVol(d.ce_oi)}</b></div>
        <div class="pcr-stat"><span>Total PE OI</span><b style="color:var(--accent)">${fmtVol(d.pe_oi)}</b></div>
        <div class="pcr-stat"><span>CE OI Change</span><b style="color:${d.ce_chg_oi>0?'var(--green)':'var(--red)'}">${d.ce_chg_oi>0?'+':''}${fmtVol(d.ce_chg_oi)}</b></div>
        <div class="pcr-stat"><span>PE OI Change</span><b style="color:${d.pe_chg_oi>0?'var(--green)':'var(--red)'}">${d.pe_chg_oi>0?'+':''}${fmtVol(d.pe_chg_oi)}</b></div>
      </div>
    </div>
    <div class="pcr-tables">
      <div>
        <div class="id-reasons-title" style="color:var(--red);margin-bottom:8px">🔴 Top CALL OI (Resistance Levels)</div>
        <table class="market-table"><thead><tr><th>#</th><th>Strike</th><th>OI</th><th>Chg OI</th></tr></thead><tbody>${ceRows}</tbody></table>
      </div>
      <div>
        <div class="id-reasons-title" style="color:var(--green);margin-bottom:8px">🟢 Top PUT OI (Support Levels)</div>
        <table class="market-table"><thead><tr><th>#</th><th>Strike</th><th>OI</th><th>Chg OI</th></tr></thead><tbody>${peRows}</tbody></table>
      </div>
    </div>
    <div class="id-disclaimer">PCR > 1.2 = Bullish | PCR 0.8-1.2 = Neutral | PCR < 0.8 = Bearish. Max CE OI strike = resistance, Max PE OI strike = support.</div>`;
}

// ── Alerts ────────────────────────────────────────────────────────────────────
function addAlert() {
  const sym   = (document.getElementById('alert-sym').value||'').toUpperCase().trim();
  const price = parseFloat(document.getElementById('alert-price').value);
  const cond  = document.getElementById('alert-cond').value;
  if (!sym || !price) { showToast('Symbol aur price dono daalo'); return; }
  _alerts.push({ sym, price, cond, active: true, created: new Date().toLocaleTimeString() });
  localStorage.setItem('id_alerts', JSON.stringify(_alerts));
  document.getElementById('alert-sym').value = '';
  document.getElementById('alert-price').value = '';
  renderAlerts();
  showToast('Alert set: ' + sym + ' ' + cond + ' ' + price);
}

function removeAlert(i) {
  _alerts.splice(i, 1);
  localStorage.setItem('id_alerts', JSON.stringify(_alerts));
  renderAlerts();
}

function renderAlerts() {
  const cont = document.getElementById('alert-list');
  if (!cont) return;
  if (!_alerts.length) {
    cont.innerHTML = '<div style="color:var(--subtext);padding:20px 0">Koi alert set nahi hai</div>';
    return;
  }
  cont.innerHTML = _alerts.map((a, i) => `
    <div class="id-alert-item ${a.triggered?'triggered':''}">
      <div>
        <b style="color:var(--accent)">${escHTML(a.sym)}</b>
        <span style="color:var(--subtext);margin:0 8px">${escHTML(a.cond==='above'?'crosses ABOVE':'crosses BELOW')}</span>
        <b style="color:var(--yellow)">₹${fmtNum(a.price)}</b>
        ${a.triggered ? '<span style="color:var(--green);margin-left:8px">✅ TRIGGERED</span>' : ''}
      </div>
      <div style="display:flex;align-items:center;gap:8px">
        <span style="font-size:11px;color:var(--subtext)">${escHTML(a.created||'')}</span>
        <button class="del-btn" onclick="removeAlert(${i})">✕</button>
      </div>
    </div>`).join('');
}

async function startAlertChecker() {
  if (_alertCheckTimer) clearInterval(_alertCheckTimer);
  _alertCheckTimer = setInterval(checkAlerts, 30000);
}

async function checkAlerts() {
  const active = _alerts.filter(a => !a.triggered);
  if (!active.length) return;
  const syms = [...new Set(active.map(a => a.sym))];
  for (const sym of syms) {
    try {
      const r = await fetch('/api/live/' + sym);
      const d = await r.json();
      const ltp = parseFloat(d.ltp) || 0;
      if (!ltp) continue;
      _alerts.forEach((a, i) => {
        if (a.sym !== sym || a.triggered) return;
        const hit = (a.cond === 'above' && ltp >= a.price) || (a.cond === 'below' && ltp <= a.price);
        if (hit) {
          _alerts[i].triggered = true;
          _alerts[i].triggered_at = ltp;
          fireAlert(a, ltp);
        }
      });
    } catch {}
  }
  localStorage.setItem('id_alerts', JSON.stringify(_alerts));
  renderAlerts();
}

function fireAlert(a, ltp) {
  showToast('🔔 ALERT: ' + a.sym + ' @ ₹' + ltp + ' (' + (a.cond==='above'?'ABOVE':'BELOW') + ' ₹' + a.price + ')', 6000);
  try {
    const audio = new AudioContext();
    const osc = audio.createOscillator();
    const gain = audio.createGain();
    osc.connect(gain); gain.connect(audio.destination);
    osc.frequency.value = 880; gain.gain.value = 0.3;
    osc.start(); osc.stop(audio.currentTime + 0.4);
  } catch {}
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification('StockPro Alert', { body: a.sym + ' ' + (a.cond==='above'?'crossed above':'crossed below') + ' ₹' + a.price + ' | LTP: ₹' + ltp });
  } else if ('Notification' in window && Notification.permission !== 'denied') {
    Notification.requestPermission();
  }
}

// ── Cookie Setup ──────────────────────────────────────────────────────────────
function showCookieSetup() {
  const panel = document.getElementById('oc-cookie-panel');
  if (panel) panel.style.display = panel.style.display === 'none' ? '' : 'none';
  checkCookieStatus();
}

async function checkCookieStatus() {
  const el = document.getElementById('cookie-status');
  if (!el) return;
  try {
    const r = await fetch('/api/intraday/cookie_status');
    const d = await r.json();
    if (d.has_nsit) {
      el.innerHTML = '<span style="color:var(--green)">✅ Cookies set hain — nsit present. Option chain kaam karega.</span>';
    } else if (d.has_cookies) {
      el.innerHTML = '<span style="color:var(--yellow)">⚠️ Cookies hain lekin nsit missing — NSE pe dobara visit karo aur fresh cookies paste karo.</span>';
    } else {
      el.innerHTML = '<span style="color:var(--red)">❌ Koi cookies nahi — upar steps follow karo.</span>';
    }
  } catch {}
}

async function saveCookies() {
  const raw = (document.getElementById('oc-cookie-input').value || '').trim();
  if (!raw) { showToast('Cookie string paste karo pehle'); return; }

  // Parse "key=value; key2=value2" format
  const cookies = {};
  raw.split(';').forEach(part => {
    const idx = part.indexOf('=');
    if (idx > 0) {
      const k = part.slice(0, idx).trim();
      const v = part.slice(idx + 1).trim();
      if (k) cookies[k] = v;
    }
  });

  if (Object.keys(cookies).length === 0) {
    showToast('Invalid cookie format'); return;
  }

  try {
    const r = await fetch('/api/intraday/set_cookies', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cookies })
    });
    const d = await r.json();
    if (d.ok) {
      showToast('Cookies saved: ' + d.keys.join(', '));
      checkCookieStatus();
      document.getElementById('oc-cookie-input').value = '';
      setTimeout(loadOptionChain, 500);
    } else {
      showToast('Error: ' + (d.error || 'Unknown'));
    }
  } catch(e) {
    showToast('Error: ' + e.message);
  }
}

// ── Cookie Setup (legacy) ─────────────────────────────────────────────────────
async function checkCookieStatus() {
  const el = document.getElementById('cookie-status');
  if (!el) return;
  el.innerHTML = '<span style="color:var(--subtext)">Checking...</span>';
  try {
    const r = await fetch('/api/intraday/cookie_status');
    const d = await r.json();
    if (d.working) {
      el.innerHTML = '<span style="color:var(--green)">✅ Cookies kaam kar rahi hain! Option chain load hoga.</span>';
    } else if (d.has_nsit) {
      el.innerHTML = '<span style="color:var(--yellow)">⚠️ nsit cookie hai lekin API kaam nahi kar rahi — cookies expire ho gayi hain. Dobara copy karo.</span>';
    } else if (d.has_cookies) {
      el.innerHTML = '<span style="color:var(--orange)">⚠️ Cookies hain (' + d.keys.join(', ') + ') lekin nsit missing. Network tab se copy karo.</span>';
    } else {
      el.innerHTML = '<span style="color:var(--red)">❌ Koi cookies nahi — neeche steps follow karo.</span>';
    }
  } catch(e) {
    el.innerHTML = '<span style="color:var(--red)">Error: ' + escHTML(e.message) + '</span>';
  }
}

// ── Upstox Settings ───────────────────────────────────────────────────────────
async function loadUpstoxSettings() {
  checkUpstoxStatus();
  loadInstrumentsStatus();
}

async function saveUpstoxToken() {
  const token = (document.getElementById('upstox-token-input')?.value || '').trim();
  if (!token) { showToast('Token paste karo pehle'); return; }
  const el = document.getElementById('upstox-token-status');
  if (el) el.innerHTML = '<span style="color:var(--subtext)">⏳ Saving...</span>';
  try {
    const r = await fetch('/api/upstox/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token })
    });
    const d = await r.json();
    if (d.ok) {
      if (el) el.innerHTML = '<span style="color:var(--green)">✅ Token saved! Instruments refresh karo agar pehli baar hai.</span>';
      document.getElementById('upstox-token-input').value = '';
      showToast('✅ Upstox token saved!');
      // Auto-refresh instruments if cache is empty
      loadInstrumentsStatus(true);
    } else {
      if (el) el.innerHTML = `<span style="color:var(--red)">❌ ${escHTML(d.error || 'Invalid token')}</span>`;
    }
  } catch(e) {
    if (el) el.innerHTML = `<span style="color:var(--red)">❌ ${escHTML(e.message)}</span>`;
  }
}

async function checkUpstoxStatus() {
  const el = document.getElementById('upstox-token-status');
  if (!el) return;
  el.innerHTML = '<span style="color:var(--subtext)">⏳ Checking...</span>';
  try {
    const r = await fetch('/api/upstox/status');
    const d = await r.json();
    if (d.ok) {
      el.innerHTML = `<span style="color:var(--green)">✅ Connected — NIFTY spot: ₹${fmtNum(d.nifty_spot || 0)}</span>`;
    } else {
      el.innerHTML = `<span style="color:var(--red)">❌ ${escHTML(d.message)}</span>`;
    }
  } catch(e) {
    el.innerHTML = `<span style="color:var(--red)">❌ ${escHTML(e.message)}</span>`;
  }
}

async function loadInstrumentsStatus(autoRefreshIfEmpty = false) {
  const el  = document.getElementById('instruments-status');
  const det = document.getElementById('instruments-detail');
  if (!el) return;
  try {
    const r = await fetch('/api/upstox/instruments_status');
    const d = await r.json();
    if (d.loaded && d.count > 0) {
      const foStr = d.fo_count ? ` | ${d.fo_count} FNO stocks` : '';
      el.innerHTML = `<span style="color:var(--green)">✅ ${d.count.toLocaleString()} EQ symbols${foStr} cached</span>`;
      if (det) {
        const ageStr = d.age_hours != null ? `Cache age: ${d.age_hours}h ago` : '';
        const sample = Object.entries(d.sample || {}).slice(0,3).map(([k,v]) => `<code style="color:var(--accent)">${k}</code>`).join(', ');
        det.innerHTML = `${ageStr} | Sample: ${sample}`;
      }
      if (d.age_hours != null && d.age_hours > 24) {
        el.innerHTML += ' <span style="color:var(--yellow)">(stale — refresh karo)</span>';
      }
    } else {
      el.innerHTML = '<span style="color:var(--orange)">⚠️ Cache empty — Refresh Instruments click karo</span>';
      if (autoRefreshIfEmpty) refreshInstruments();
    }
  } catch(e) {
    el.innerHTML = `<span style="color:var(--red)">❌ ${escHTML(e.message)}</span>`;
  }
}

async function refreshInstruments() {
  const el  = document.getElementById('instruments-status');
  const det = document.getElementById('instruments-detail');
  if (el) el.innerHTML = '<span style="color:var(--subtext)">⏳ Downloading NSE instruments CSV... (10-20 sec)</span>';
  if (det) det.innerHTML = '';
  try {
    const r = await fetch('/api/upstox/refresh_instruments', { method: 'POST' });
    const d = await r.json();
    if (d.ok) {
      if (el) el.innerHTML = `<span style="color:var(--green)">✅ Done! ${d.count.toLocaleString()} symbols loaded</span>`;
      showToast(`✅ Instruments refreshed: ${d.count} symbols`);
      loadInstrumentsStatus();
    } else {
      if (el) el.innerHTML = '<span style="color:var(--red)">❌ Refresh failed — internet check karo</span>';
    }
  } catch(e) {
    if (el) el.innerHTML = `<span style="color:var(--red)">❌ ${escHTML(e.message)}</span>`;
  }
}
