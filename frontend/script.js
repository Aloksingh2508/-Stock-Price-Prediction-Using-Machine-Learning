const API = "http://127.0.0.1:5000";
let allStocks = {}, selected = new Set(), chartInst = {}, compResults = [];
let watchlist = new Set(JSON.parse(localStorage.getItem('marketOracleWatchlist') || '[]'));
// ── Currency: USD → INR ───────────────────────────────────────────────
let INR_RATE = 84.0; // fallback; overwritten by live fetch on init

/** Convert USD amount → ₹ formatted string */
function fmt(usd) {
  if (usd === null || usd === undefined || usd === '—' || isNaN(parseFloat(usd))) return '—';
  const inr = parseFloat(usd) * INR_RATE;
  return '\u20B9' + inr.toLocaleString('en-IN', { maximumFractionDigits: 2 });
}

/** Fetch live USD→INR rate from backend */
async function loadExchangeRate() {
  const el = document.getElementById('inr-rate-display');
  try {
    const data = await fetch(`${API}/api/exchange_rate`).then(r => r.json());
    if (data.usd_to_inr && data.usd_to_inr > 50) {
      INR_RATE = data.usd_to_inr;
      const now = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
      if (el) el.textContent = `1 USD = \u20B9${INR_RATE} (${now})`;
    }
  } catch(e) {
    if (el) el.textContent = `1 USD = \u20B9${INR_RATE} (cached)`;
    console.warn('Could not fetch exchange rate:', e);
  }
}


// ── Chart explainer text per tab ─────────────────────────────────────
const CHART_EXPLAIN = {
  'price-tab':  "The solid line shows the real historical price. The dashed line is what the AI predicted — see how closely they match!",
  'rsi-tab':    "RSI measures buying/selling pressure (0–100). Below 30 = stock may be oversold (a buying opportunity). Above 70 = may be overbought (consider selling).",
  'macd-tab':   "When the blue MACD line crosses above the orange signal line, that's a bullish (upward) sign. Green bars = gaining momentum. Red bars = losing momentum.",
  'bb-tab':     "The white middle line is the 20-day average price. When price touches the lower blue band, it's unusually cheap. Upper gold band = unusually expensive.",
  'future-tab': "This is the AI's best guess for the next 7 days based on patterns it learned. Treat it as a direction indicator, not an exact price target."
};

// ── Human-friendly action labels ─────────────────────────────────────
const ACTION_EXPLAIN = {
  'STRONG BUY':  "Multiple strong signals suggest this is a great time to buy. The AI is quite confident about this.",
  'BUY':         "The signals lean positive. This stock looks like it could go up. Worth considering.",
  'HOLD':        "Mixed signals — not a clear buy or sell. If you own it, hold. If not, maybe wait for clearer direction.",
  'SELL':        "The signals suggest the price may be heading down. If you own this stock, it might be time to reconsider.",
  'STRONG SELL': "Multiple signals point strongly downward. The AI suggests caution — this stock may be in trouble."
};

// ── Chart default options ─────────────────────────────────────────────
const baseOpts = () => ({
  responsive: true, maintainAspectRatio: true,
  animation: { duration: 700, easing: 'easeInOutQuart' },
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: { labels: { color: '#7fc8bf', boxWidth: 12, font: { size: 12 } } },
    tooltip: { backgroundColor: '#04281e', borderColor: 'rgba(20,210,180,.25)', borderWidth: 1, titleColor: '#ecfdf5', bodyColor: '#5f7f78', padding: 10 }
  },
  scales: {
    x: { ticks: { color: '#4a6b65', maxTicksLimit: 10, maxRotation: 0, font: { size: 11 } }, grid: { color: 'rgba(20,210,180,.06)' } },
    y: { ticks: { color: '#4a6b65', font: { size: 11 } }, grid: { color: 'rgba(20,210,180,.06)' } }
  }
});

const COLORS = ['#3b82f6','#a855f7','#06b6d4','#f59e0b','#10b981'];

// ── Clock ─────────────────────────────────────────────────────────────
function startClock() {
  const el = document.getElementById('clock');
  setInterval(() => { el.textContent = new Date().toLocaleTimeString(); }, 1000);
}

// ── Ticker Strip ──────────────────────────────────────────────────────
function buildTickerHTML(data) {
  const inner = document.getElementById('ticker-inner');
  let html = '';
  Object.entries(data).forEach(([t, info]) => {
    if (!info.price) return;
    const cls  = (info.change_pct || 0) >= 0 ? 'tick-up' : 'tick-down';
    const sign = (info.change_pct || 0) >= 0 ? '+' : '';
    html += `<span class="tick-item"><b>${info.flag||''} ${t}</b> <span class="${cls}">${fmt(info.price)} (${sign}${info.change_pct}%)</span></span>`;
  });
  if (html) inner.innerHTML = html + html;
}

async function loadTickerStrip() {
  // Reuse already-fetched live data if available, else fetch
  if (Object.values(_liveData).some(d => d.price)) {
    buildTickerHTML(_liveData);
    return;
  }
  try {
    const data = await fetch(`${API}/api/live_batch`).then(r => r.json());
    Object.assign(_liveData, data);
    buildTickerHTML(data);
  } catch(e) {
    document.getElementById('ticker-inner').textContent = 'Live prices loading…';
  }
}

// ── Market Grid — loads catalog instantly, fetches prices in background ──
let _liveData = {};

async function loadMarketGrid() {
  const grid = document.getElementById('market-grid');
  grid.innerHTML = '<p class="loading-msg">⏳ Loading companies…</p>';
  try {
    // Step 1: Load catalog INSTANTLY (no price data yet)
    allStocks = await fetch(`${API}/api/stocks`).then(r => r.json());
    // Build skeleton cards with no prices
    const skeleton = {};
    Object.entries(allStocks).forEach(([t, info]) => {
      skeleton[t] = { price: null, change_pct: 0, ...info };
    });
    _liveData = skeleton;
    renderMarketGrid(_liveData, 'all');
    setupSectorFilter();
    renderStockList();

    // Step 2: Fetch prices in background (non-blocking)
    fetchLivePrices();
  } catch(e) {
    grid.innerHTML = '<p style="color:#fb7185;padding:20px">❌ Cannot reach server. Make sure Flask is running on port 5000, then refresh.</p>';
  }
}

async function fetchLivePrices() {
  try {
    const data = await fetch(`${API}/api/live_batch`).then(r => r.json());
    Object.assign(_liveData, data);
    const activeBtn = document.querySelector('.sector-btn.active');
    const sector = activeBtn ? activeBtn.dataset.sector : 'all';
    renderMarketGrid(_liveData, sector);
    // Also update ticker strip with real prices
    buildTickerHTML(_liveData);
  } catch(e) { console.warn('Live prices unavailable'); }
}

function renderMarketGrid(data, sector) {
  const grid = document.getElementById('market-grid');
  grid.innerHTML = '';
  Object.entries(data).forEach(([ticker, info]) => {
    if (sector === 'watchlist') {
      if (!watchlist.has(ticker)) return;
    } else if (sector !== 'all' && info.sector !== sector) return;

    const isUp = (info.change_pct || 0) >= 0;
    const priceStr = info.price ? fmt(info.price) : '<span style="color:var(--muted);font-size:13px">Loading…</span>';
    const card = document.createElement('div');
    const isStarred = watchlist.has(ticker);
    card.className = 'market-card' + (selected.has(ticker) ? ' selected' : '');
    card.dataset.ticker = ticker;
    card.innerHTML = `
      <button class="star-btn ${isStarred ? 'starred' : ''}" onclick="window.toggleWatchlist(event, '${ticker}')" title="${isStarred ? 'Remove from Watchlist' : 'Add to Watchlist'}">★</button>
      <div class="mc-flag">${info.flag || '📊'}</div>
      <div class="mc-ticker">${ticker}</div>
      <div class="mc-name">${info.name || ticker}</div>
      <div class="mc-price">${priceStr}</div>
      <div class="mc-change ${isUp ? 'up' : 'down'}">${info.price ? (isUp ? '▲' : '▼') + ' ' + (isUp ? '+' : '') + info.change_pct + '% today' : ''}</div>
      <div class="mc-sector">${info.sector || ''}</div>
      ${selected.has(ticker) ? '<div class="mc-selected-badge">✓ Added to analysis</div>' : ''}
    `;
    card.addEventListener('click', () => toggleStock(ticker, card));
    grid.appendChild(card);
  });
}

window.toggleWatchlist = function(e, ticker) {
  e.stopPropagation();
  if (watchlist.has(ticker)) watchlist.delete(ticker);
  else watchlist.add(ticker);
  localStorage.setItem('marketOracleWatchlist', JSON.stringify([...watchlist]));
  const activeBtn = document.querySelector('.sector-btn.active');
  renderMarketGrid(_liveData, activeBtn ? activeBtn.dataset.sector : 'all');
};

function setupSectorFilter() {
  document.querySelectorAll('.sector-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.sector-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderMarketGrid(_liveData, btn.dataset.sector);
    });
  });
}

// ── Stock selection ───────────────────────────────────────────────────
function toggleStock(ticker, cardEl) {
  if (selected.has(ticker)) {
    selected.delete(ticker);
    cardEl?.classList.remove('selected');
  } else {
    if (selected.size >= 5) { showToast('⚠️ You can analyse up to 5 stocks at a time.'); return; }
    selected.add(ticker);
    cardEl?.classList.add('selected');
  }
  renderChips(); renderStockList(); updateCount();
}

function renderChips() {
  const wrap = document.getElementById('selected-chips');
  if (!selected.size) {
    wrap.innerHTML = '<span class="chips-placeholder">👆 Pick companies from the left or the market grid above</span>';
    return;
  }
  wrap.innerHTML = '';
  selected.forEach(ticker => {
    const meta = allStocks[ticker] || {};
    const chip = document.createElement('span');
    chip.className = 'chip';
    chip.innerHTML = `${meta.flag || '📊'} ${ticker} <span class="chip-remove" title="Remove">×</span>`;
    chip.querySelector('.chip-remove').addEventListener('click', () => {
      toggleStock(ticker);
      document.querySelector(`.market-card[data-ticker="${ticker}"]`)?.classList.remove('selected');
    });
    wrap.appendChild(chip);
  });
}

function renderStockList(filter = '') {
  const listEl = document.getElementById('stock-list');
  if (!listEl) return;
  listEl.innerHTML = '';
  Object.keys(allStocks)
    .filter(t => !filter || t.includes(filter.toUpperCase()) || (allStocks[t].name || '').toLowerCase().includes(filter.toLowerCase()))
    .forEach(ticker => {
      const btn = document.createElement('button');
      btn.className = 'stock-chip-sel' + (selected.has(ticker) ? ' active' : '');
      btn.textContent = ticker;
      btn.title = allStocks[ticker]?.name || ticker;
      btn.addEventListener('click', () => {
        toggleStock(ticker);
        const mc = document.querySelector(`.market-card[data-ticker="${ticker}"]`);
        if (mc) selected.has(ticker) ? mc.classList.add('selected') : mc.classList.remove('selected');
      });
      listEl.appendChild(btn);
    });
}

function updateCount() {
  document.getElementById('selected-count').textContent = selected.size;
}

document.getElementById('stock-search').addEventListener('input', e => renderStockList(e.target.value.trim()));

// ── Run predictions ───────────────────────────────────────────────────
document.getElementById('predict-btn').addEventListener('click', runPredictions);

async function runPredictions() {
  if (!selected.size) { showToast('👆 Please select at least one company first.'); return; }
  const btn  = document.getElementById('predict-btn');
  const text = btn.querySelector('.btn-text');
  const spin = btn.querySelector('.btn-loader');
  btn.disabled = true; spin.hidden = false; text.textContent = 'AI is learning…';
  showProgress(); setProgress(0, '🧠 Starting up the neural network…');

  compResults = [];
  const tickers = [...selected];
  let priceDatasets = [], labels = [];

  for (let i = 0; i < tickers.length; i++) {
    const ticker = tickers[i];
    setProgress(Math.round(((i + 0.5) / tickers.length) * 95),
      `📈 Training the AI on ${allStocks[ticker]?.name || ticker} (${i+1} of ${tickers.length})…`);
    try {
      const data = await fetch(`${API}/api/predict?stock=${ticker}`).then(r => r.json());
      if (data.error) { showToast(`⚠️ ${ticker}: ${data.error}`); continue; }
      compResults.push({ ticker, data });
      if (i === 0) {
        labels = data.dates;
        renderAIBanner(ticker, data.ai_suggestion);
        renderKPIs(ticker, data);
        renderIndicatorCharts(data);
        renderForecastChart(data);
        fetchAndRenderNews(ticker);
      }
      const col = COLORS[i % COLORS.length];
      priceDatasets.push({ label: `${ticker} — Real price`, data: data.actual, borderColor: col, borderWidth: 2, fill: false, tension: 0.3, pointRadius: 0 });
      priceDatasets.push({ label: `${ticker} — AI predicted`, data: data.predicted, borderColor: col, borderDash: [6, 4], borderWidth: 2, fill: false, tension: 0.3, pointRadius: 0, borderDashOffset: 0 });
    } catch(e) { showToast(`❌ Could not get data for ${ticker}.`); }
  }

  setProgress(100, '✅ Analysis complete!');
  if (priceDatasets.length) {
    renderPriceChart(labels, priceDatasets);
    renderComparisonTable();
    document.getElementById('results-section').hidden = false;
    document.getElementById('results-section').scrollIntoView({ behavior: 'smooth' });
  }
  setTimeout(() => {
    hideProgress(); btn.disabled = false; spin.hidden = true; text.textContent = 'Analyse & Predict';
  }, 900);
}

// ── AI Banner ─────────────────────────────────────────────────────────
function renderAIBanner(ticker, ai) {
  if (!ai) return;
  const color = ai.color || '#f59e0b';
  document.documentElement.style.setProperty('--signal-color', color);

  document.getElementById('ai-ticker-name').textContent = allStocks[ticker]?.name || ticker;
  const actionEl = document.getElementById('ai-action');
  actionEl.textContent = ai.action;
  actionEl.style.color = color;

  document.getElementById('ai-explanation').textContent =
    `${ACTION_EXPLAIN[ai.action] || ''} (AI confidence: ${ai.confidence}% · Current price: ${fmt(ai.current_price)} → Predicted tomorrow: ${fmt(ai.predicted_next)}, ${ai.predicted_change_pct >= 0 ? '+' : ''}${ai.predicted_change_pct}%)`;

  const ring = document.getElementById('ring-progress');
  ring.style.strokeDashoffset = 163.36 - (ai.confidence / 100) * 163.36;
  ring.style.stroke = color;
  document.getElementById('ring-pct').textContent = ai.confidence + '%';

  document.getElementById('ai-signals-list').innerHTML =
    (ai.signals || []).map(s => `<span class="ai-signal-item">${s}</span>`).join('');
}

// ── KPI Cards with plain explanations ────────────────────────────────
function renderKPIs(ticker, data) {
  const ai = data.ai_suggestion || {}, ind = data.indicators || {};
  const rsi = ind.current_rsi !== undefined ? ind.current_rsi.toFixed(1) : 'N/A';
  const rsiClass = ind.current_rsi < 30 ? 'green' : ind.current_rsi > 70 ? 'red' : 'yellow';
  const chgPct = ai.predicted_change_pct || 0;

  const kpis = [
    { label: 'Company',                  val: allStocks[ticker]?.name || ticker, cls: '',       explain: 'The company you analysed' },
    { label: 'AI Recommendation',        val: ai.action || '—',                   cls: ai.action?.includes('BUY') ? 'green' : ai.action?.includes('SELL') ? 'red' : 'yellow', explain: 'What the AI thinks you should do right now' },
    { label: 'AI Confidence',            val: data.confidence_score + '%',        cls: 'green',  explain: 'How sure the AI is, based on how well it fitted historical data' },
    { label: 'Price Right Now (₹)',     val: fmt(ai.current_price),              cls: '',       explain: 'Latest closing price from Yahoo Finance, converted to Indian Rupees' },
    { label: 'AI Predicts Tomorrow (₹)', val: fmt(ai.predicted_next),            cls: chgPct >= 0 ? 'green' : 'red', explain: 'LSTM model’s forecast for tomorrow’s price, shown in ₹' },
    { label: 'Expected Change',          val: (chgPct >= 0 ? '+' : '') + chgPct + '%', cls: chgPct >= 0 ? 'green' : 'red', explain: 'Predicted percentage move from today to tomorrow' },
    { label: 'Momentum (RSI)',           val: rsi,                                cls: rsiClass, explain: rsi < 30 ? 'Below 30 — possibly oversold. Buying opportunity.' : rsi > 70 ? 'Above 70 — possibly overbought. Could dip soon.' : 'Between 30–70 — neutral zone.' },
    { label: 'Model Accuracy (RMSE ₹)',  val: fmt(data.rmse),                    cls: '',       explain: 'Average prediction error in ₹. Lower = more accurate model.' },
  ];

  document.getElementById('kpi-row').innerHTML = kpis.map(k => `
    <div class="kpi-card" title="${k.explain}">
      <div class="kpi-label">${k.label}</div>
      <div class="kpi-val ${k.cls}">${k.val}</div>
      <div class="kpi-explain">${k.explain}</div>
    </div>
  `).join('');
}

// ── Charts ────────────────────────────────────────────────────────────
function destroyChart(id) { if (chartInst[id]) { chartInst[id].destroy(); delete chartInst[id]; } }

function renderPriceChart(labels, datasets) {
  destroyChart('price-chart');
  chartInst['price-chart'] = new Chart(document.getElementById('price-chart').getContext('2d'), {
    type: 'line', data: { labels, datasets },
    options: { ...baseOpts(), plugins: { ...baseOpts().plugins, title: { display: true, text: 'Real Price (solid) vs AI Predicted Price (dashed)', color: '#e2e8f0', font: { size: 14 } } } }
  });
}

function renderIndicatorCharts(data) {
  const ind = data.indicators || {};

  // RSI
  destroyChart('rsi-chart');
  const rLen = (ind.rsi || []).length;
  chartInst['rsi-chart'] = new Chart(document.getElementById('rsi-chart').getContext('2d'), {
    type: 'line',
    data: { labels: Array.from({length: rLen}, (_, i) => i), datasets: [
      { label: 'RSI (Momentum)', data: ind.rsi || [], borderColor: '#f59e0b', borderWidth: 2, fill: false, tension: 0.3, pointRadius: 0 },
      { label: 'Overbought line (70)', data: Array(rLen).fill(70), borderColor: '#ef4444', borderWidth: 1, borderDash: [4,4], fill: false, pointRadius: 0 },
      { label: 'Oversold line (30)',   data: Array(rLen).fill(30), borderColor: '#22c55e', borderWidth: 1, borderDash: [4,4], fill: false, pointRadius: 0 },
    ]},
    options: { ...baseOpts(), plugins: { ...baseOpts().plugins, title: { display: true, text: 'RSI — Momentum Indicator (below 30 = cheap signal, above 70 = expensive signal)', color: '#e2e8f0', font: { size: 13 } } }, scales: { ...baseOpts().scales, y: { ...baseOpts().scales.y, min: 0, max: 100 } } }
  });

  // MACD
  destroyChart('macd-chart');
  const mLen = (ind.macd || []).length;
  chartInst['macd-chart'] = new Chart(document.getElementById('macd-chart').getContext('2d'), {
    type: 'line',
    data: { labels: Array.from({length: mLen}, (_, i) => i), datasets: [
      { label: 'MACD Line', data: ind.macd || [], borderColor: '#3b82f6', borderWidth: 2, fill: false, tension: 0.3, pointRadius: 0 },
      { label: 'Signal Line', data: ind.macd_signal || [], borderColor: '#f59e0b', borderWidth: 2, fill: false, tension: 0.3, pointRadius: 0 },
      { label: 'Histogram (momentum bars)', data: ind.macd_hist || [], type: 'bar', backgroundColor: (ind.macd_hist||[]).map(v => v >= 0 ? 'rgba(34,197,94,.35)' : 'rgba(239,68,68,.35)') },
    ]},
    options: { ...baseOpts(), plugins: { ...baseOpts().plugins, title: { display: true, text: 'MACD — Trend Strength (blue above orange = bullish signal)', color: '#e2e8f0', font: { size: 13 } } } }
  });

  // Bollinger Bands
  destroyChart('bb-chart');
  const bLen = (ind.bb_upper || []).length;
  chartInst['bb-chart'] = new Chart(document.getElementById('bb-chart').getContext('2d'), {
    type: 'line',
    data: { labels: Array.from({length: bLen}, (_, i) => i), datasets: [
      { label: 'Upper Band (overpriced zone)', data: ind.bb_upper || [], borderColor: '#f59e0b', borderWidth: 1, borderDash: [4,4], fill: false, pointRadius: 0 },
      { label: 'Average Price (20-day)', data: ind.bb_mid || [], borderColor: '#ffffff', borderWidth: 1.5, fill: false, pointRadius: 0 },
      { label: 'Lower Band (underpriced zone)', data: ind.bb_lower || [], borderColor: '#06b6d4', borderWidth: 1, borderDash: [4,4], fill: '+1', backgroundColor: 'rgba(6,182,212,.06)', pointRadius: 0 },
    ]},
    options: { ...baseOpts(), plugins: { ...baseOpts().plugins, title: { display: true, text: 'Bollinger Bands — Price near lower band = potential buy opportunity', color: '#e2e8f0', font: { size: 13 } } } }
  });
}

function renderForecastChart(data) {
  destroyChart('future-chart');
  const last = (data.actual || []).slice(-1)[0];
  const futureData   = [last, ...(data.future_predicted || [])];
  const futureLabels = ['Today', ...(data.future_dates || [])];
  chartInst['future-chart'] = new Chart(document.getElementById('future-chart').getContext('2d'), {
    type: 'line',
    data: { labels: futureLabels, datasets: [{
      label: 'AI Price Forecast for Next 7 Days',
      data: futureData, borderColor: '#a855f7', backgroundColor: 'rgba(168,85,247,.12)',
      borderWidth: 2.5, fill: true, tension: 0.4, pointRadius: 5, pointBackgroundColor: '#a855f7'
    }]},
    options: { ...baseOpts(), plugins: { ...baseOpts().plugins, title: { display: true, text: '7-Day Price Forecast — Direction indicator, not an exact guarantee', color: '#e2e8f0', font: { size: 13 } } } }
  });
}

// ── Comparison table ──────────────────────────────────────────────────
function renderComparisonTable() {
  const section = document.getElementById('comparison-section');
  if (compResults.length < 2) { section.hidden = true; return; }
  section.hidden = false;
  document.getElementById('comparison-body').innerHTML = compResults.map(({ ticker, data }) => {
    const ai  = data.ai_suggestion || {}, ind = data.indicators || {};
    const sigCls = ai.action?.includes('BUY') ? 'sig-buy' : ai.action?.includes('SELL') ? 'sig-sell' : 'sig-hold';
    const chg    = ai.predicted_change_pct || 0;
    const rsi    = ind.current_rsi !== undefined ? ind.current_rsi.toFixed(1) : 'N/A';
    return `<tr>
      <td><b>${allStocks[ticker]?.flag || '📊'} ${allStocks[ticker]?.name || ticker}</b></td>
      <td><span class="signal-pill ${sigCls}">${ai.action || '—'}</span></td>
      <td>${ai.confidence || '—'}%</td>
      <td>${fmt(data.rmse)}</td>
      <td>${fmt(ai.current_price)}</td>
      <td>${fmt(ai.predicted_next)}</td>
      <td style="color:${chg >= 0 ? 'var(--green)' : 'var(--red)'};">${chg >= 0 ? '+' : ''}${chg}%</td>
      <td>${rsi}</td>
    </tr>`;
  }).join('');
}

// ── Chart tabs ────────────────────────────────────────────────────────
document.querySelectorAll('.chart-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.chart-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.chart-panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(tab.dataset.tab).classList.add('active');
    document.getElementById('chart-explain-text').textContent = CHART_EXPLAIN[tab.dataset.tab] || '';
  });
});

// ── Period tabs ───────────────────────────────────────────────────────
document.querySelectorAll('.period-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.period-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
  });
});

// ── Nav active ────────────────────────────────────────────────────────
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', () => {
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    link.classList.add('active');
  });
});

// ── Progress helpers ──────────────────────────────────────────────────
function showProgress() { document.getElementById('progress-wrap').hidden = false; }
function hideProgress() { document.getElementById('progress-wrap').hidden = true; }
function setProgress(pct, label) {
  document.getElementById('progress-bar').style.width = pct + '%';
  document.getElementById('progress-label').textContent = label;
}

// ── Toast ─────────────────────────────────────────────────────────────
function showToast(msg) {
  let t = document.getElementById('toast');
  if (!t) {
    t = document.createElement('div'); t.id = 'toast';
    Object.assign(t.style, { position:'fixed', bottom:'28px', right:'28px', background:'#0f2040', color:'#e2e8f0', padding:'14px 22px', borderRadius:'12px', border:'1px solid rgba(99,179,255,.25)', fontSize:'14px', boxShadow:'0 8px 24px rgba(0,0,0,.4)', zIndex:'9999', transition:'opacity .3s', opacity:'0', maxWidth:'320px', lineHeight:'1.5' });
    document.body.appendChild(t);
  }
  t.textContent = msg; t.style.opacity = '1';
  clearTimeout(t._t); t._t = setTimeout(() => { t.style.opacity = '0'; }, 3500);
}

// ── Init ──────────────────────────────────────────────────────────────
async function init() {
  startClock();
  // Load exchange rate & market catalog in parallel (both fast)
  await Promise.allSettled([
    loadExchangeRate(),
    loadMarketGrid()       // shows catalog instantly, prices load in background
  ]);
  setInterval(loadExchangeRate, 3_600_000);
}
init();

// ── News Fetching ─────────────────────────────────────────────────────
async function fetchAndRenderNews(ticker) {
  try {
    const data = await fetch(`${API}/api/news?stock=${ticker}`).then(r => r.json());
    const newsSec = document.getElementById('news-section');
    const newsGrid = document.getElementById('news-grid');
    if (!data || data.length === 0) {
      newsSec.hidden = true; return;
    }
    newsSec.hidden = false;
    document.getElementById('news-sub').textContent = `Recent news for ${allStocks[ticker]?.name || ticker}.`;
    newsGrid.innerHTML = data.map(item => `
      <a href="${item.link}" target="_blank" class="news-card">
        <div class="news-title">${item.title}</div>
        <div class="news-meta">
          <span class="news-source">${item.publisher}</span>
          <span>${new Date(item.providerPublishTime * 1000).toLocaleDateString()}</span>
        </div>
      </a>
    `).join('');
  } catch(e) { console.warn('News error', e); }
}

// ── Export Report ─────────────────────────────────────────────────────
const exportBtn = document.getElementById('export-report-btn');
if (exportBtn) {
  exportBtn.addEventListener('click', () => {
    window.print();
  });
}