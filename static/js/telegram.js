/* telegram.js — StockPro Telegram Alerts (self-contained panel)
   index.html me </body> se pehle add karo:
   <script src="/static/js/telegram.js"></script>
   Sidebar me "📨 Telegram" item khud add ho jayega (Sectors ke neeche). Na mile to floating button aayega.
   Kaam: Telegram connect karo -> tumhare price alerts (above/below, target, stoploss) server se seedha Telegram par aayenge,
   browser band ho tab bhi. */
(function () {
  const css = `
  #tg-panel{position:fixed;inset:0;background:#070b14;z-index:9999;overflow:auto;color:#e5e7eb;font-family:inherit;display:none}
  #tg-panel .tg-wrap{max-width:640px;margin:0 auto;padding:16px}
  #tg-panel .tg-top{display:flex;justify-content:space-between;align-items:center}
  #tg-panel .tg-card{background:#0d1526;border:1px solid #16223b;border-radius:12px;padding:12px 14px;margin:12px 0;font-size:14px;line-height:1.55}
  #tg-panel .tg-btn{background:#2563eb;border:0;color:#fff;border-radius:10px;padding:9px 14px;font-size:14px;cursor:pointer;margin:4px 6px 4px 0;text-decoration:none;display:inline-block}
  #tg-panel .tg-btn.sec{background:#101a2e;border:1px solid #1e2b47;color:#cbd5e1}
  #tg-panel .tg-btn.red{background:#7f1d1d}
  #tg-panel .ok{color:#34d399}#tg-panel .bad{color:#f87171}#tg-panel .dim{color:#94a3b8;font-size:12px}
  #tg-panel code{background:#101a2e;padding:1px 6px;border-radius:6px}
  #tg-float{position:fixed;right:14px;bottom:170px;z-index:9998;background:#0ea5e9;color:#fff;border:0;border-radius:999px;padding:10px 14px;cursor:pointer}`;
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  const panel = document.createElement('div'); panel.id = 'tg-panel';
  panel.innerHTML = `<div class="tg-wrap">
    <div class="tg-top"><h2 style="margin:0">📨 Telegram Alerts</h2><button class="tg-btn sec" id="tg-close">✕ Close</button></div>
    <div id="tg-body">Loading...</div>
  </div>`;
  document.body.appendChild(panel);
  const $ = id => panel.querySelector(id);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  async function api(path, method, body) {
    const r = await fetch(path, { method: method || 'GET', headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined });
    let j = {}; try { j = await r.json(); } catch (e) {}
    return { ok: r.ok, status: r.status, j };
  }

  const NOTE = `<div class="tg-card dim">ℹ️ Alerts server par <b>har 30 second</b> check hote hain (Mon-Fri, 9:10 AM - 3:35 PM IST). Browser band ho tab bhi chalta hai,
    bas server jaagta rehna chahiye. Price Upstox se aata hai (token na ho to yfinance se, thoda delay ke saath).</div>`;

  async function render(msg) {
    const body = $('#tg-body');
    const { j } = await api('/api/telegram/status');
    let h = msg ? `<div class="tg-card">${msg}</div>` : '';
    if (!j.bot_configured) {
      h += `<div class="tg-card"><b class="bad">⚠️ Bot abhi set nahi hai</b> (ye ek baar ka server setup hai)<ol style="padding-left:18px;margin:8px 0 0">
        <li>Telegram me <b>@BotFather</b> kholo &rarr; <code>/newbot</code> &rarr; naam do &rarr; <b>token</b> copy karo.</li>
        <li>Render &rarr; apni service &rarr; <b>Environment</b> me <code>TELEGRAM_BOT_TOKEN</code> naam se wo token daalo.</li>
        <li>Redeploy karo, phir ye panel dobara kholo.</li></ol></div>`;
    } else if (j.connected) {
      h += `<div class="tg-card"><b class="ok">✅ Telegram connected hai</b><br>Ab tumhare price alerts (above/below, target, stoploss) Telegram par aayenge.<br>
        <button class="tg-btn" id="tg-test">🔔 Test message bhejo</button><button class="tg-btn red" id="tg-off">Disconnect</button></div>` + NOTE;
    } else {
      h += `<div class="tg-card"><b>Connect kaise karein (30 second)</b><ol style="padding-left:18px;margin:8px 0 0">
        <li>Neeche <b>"Link banao"</b> dabao.</li><li>Jo link aaye use kholo &rarr; Telegram me <b>Start</b> dabao.</li>
        <li>Wapas yahan aakar <b>"Connect karo"</b> dabao.</li></ol>
        <div style="margin-top:8px"><button class="tg-btn" id="tg-link">1️⃣ Link banao</button><span id="tg-linkbox"></span></div>
        <div><button class="tg-btn sec" id="tg-conn">3️⃣ Connect karo</button></div></div>` + NOTE;
    }
    body.innerHTML = h;
    const on = (id, fn) => { const el = $(id); if (el) el.onclick = fn; };
    on('#tg-link', async () => {
      const r = await api('/api/telegram/link', 'POST');
      if (r.j.url) $('#tg-linkbox').innerHTML = `<a class="tg-btn" target="_blank" rel="noopener" href="${esc(r.j.url)}">2️⃣ Telegram kholo &rarr; Start dabao</a>`;
      else $('#tg-linkbox').innerHTML = `<div class="bad">${esc(r.j.error || 'Link nahi bana')}</div>`;
    });
    on('#tg-conn', async () => {
      const r = await api('/api/telegram/connect', 'POST', {});
      if (r.ok && r.j.connected) render('<span class="ok">✅ Connected! Telegram par welcome message gaya hoga.</span>');
      else render(`<span class="bad">${esc(r.j.error || 'Connect nahi hua')}</span>`);
    });
    on('#tg-test', async () => {
      const r = await api('/api/telegram/test', 'POST');
      render(r.ok && r.j.ok ? '<span class="ok">Test message bhej diya, Telegram check karo.</span>' : `<span class="bad">${esc(r.j.error || 'Message nahi gaya')}</span>`);
    });
    on('#tg-off', async () => { await api('/api/telegram/disconnect', 'POST'); render('Disconnect ho gaya.'); });
  }

  function open() { panel.style.display = 'block'; render(); }
  $('#tg-close').onclick = () => panel.style.display = 'none';
  window.openTelegramAlerts = open;

  function addNav() {
    if (document.getElementById('nav-telegram')) return;
    const base = document.getElementById('nav-sectors') || document.getElementById('nav-events') || document.getElementById('nav-intraday');
    if (base && base.parentElement) {
      const b = document.createElement('button');
      b.className = 'nav-btn'; b.id = 'nav-telegram'; b.innerHTML = '📨 <span>Telegram</span>';
      b.addEventListener('click', () => {
        const sb = document.getElementById('sidebar'); if (sb) sb.classList.remove('open');
        const ov = document.querySelector('.sidebar-overlay'); if (ov) ov.classList.remove('show');
        open();
      });
      base.insertAdjacentElement('afterend', b);
    } else {
      const b = document.createElement('button'); b.id = 'tg-float'; b.textContent = '📨 Telegram'; b.onclick = open; document.body.appendChild(b);
    }
  }
  const init = () => setTimeout(addNav, 700);   // events.js / sectors.js ke baad
  if (document.readyState === 'complete') init(); else window.addEventListener('load', init);
})();
