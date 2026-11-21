/* ============================================================
   11 STOCK MARKET WORKSPACE -> GET /market/quote|daily|news
   No API key needed — quotes/history via yfinance, news via Google News RSS.
   ============================================================ */
function currencySymbol(code){ return ({INR:"₹",USD:"$",EUR:"€",GBP:"£",JPY:"¥"})[code] || (code ? code+" " : ""); }
function escapeHtml(s){ return String(s).replace(/[&<>"']/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]); }
function timeAgo(iso){
  const mins = Math.round((Date.now() - new Date(iso)) / 60000);
  if(mins < 60) return `${Math.max(mins,1)} min ago`;
  if(mins < 1440) return `${Math.round(mins/60)} h ago`;
  return new Date(iso).toLocaleDateString();
}
// Bumped per request: a slow reply for a previously selected stock must not
// overwrite the one the user picked since.
const REQ = { quote:0, history:0, news:0 };
async function getQuote(){
  const my = ++REQ.quote;   // ignore replies to older requests
  const box = document.getElementById("marketStatus");
  box.textContent = "Fetching live quote…";
  try{
    const symbol = document.getElementById("marketSymbol").value.trim();
    if(!symbol){ box.textContent = "Choose a company above."; return; }
    const q = await api("GET", `/market/quote?symbol=${encodeURIComponent(symbol)}`);
    if(my !== REQ.quote) return;
    const input = document.getElementById("marketSymbol");
    if(input.value.trim() === symbol){
      input.value = q.yahooSymbol;                       // e.g. "samsung" -> "005930.KS"
      setPickerLabel("marketPicker", q.name, q.yahooSymbol);
      const news = document.getElementById("newsSymbols");
      if(news.value.trim() === symbol) news.value = q.yahooSymbol;
    }
    const cur = currencySymbol(q.currency);
    box.innerHTML = `<b>${escapeHtml(q.name)}</b> <span class="muted">(${escapeHtml(q.yahooSymbol)})</span>: <b>${cur}${q.price}</b>` +
      (q.change!=null ? ` <span class="${q.change>=0?'badge-good':'badge-warn'}">${q.change>=0?"+":""}${q.change} (${q.changePercent}%)</span>` : "") +
      (q.previousClose!=null ? `<br>Prev close ${cur}${q.previousClose}` : "") +
      (q.open!=null ? ` · Open ${cur}${q.open} · Day range ${cur}${q.dayLow} – ${cur}${q.dayHigh} · Volume ${q.volume.toLocaleString()}` : "") +
      (q.asOf ? `<div class="muted" style="margin-top:4px;">Last trade: ${new Date(q.asOf).toLocaleString()}</div>` : "") +
      (q.stale ? `<div class="stale-note">Live data is unavailable right now. Showing the last saved price from ${Math.max(Math.round(q.staleSeconds/60),1)} min ago.</div>` : "");
  }catch(e){ if(my !== REQ.quote) return; box.textContent = "Error: "+e.message; }
}
async function getDailyHistory(){
  const my = ++REQ.history;   // ignore replies to older requests
  const status = document.getElementById("historyStatus");
  status.textContent = "Fetching daily history…";
  try{
    const symbol = document.getElementById("marketSymbol").value.trim();
    const period = document.getElementById("historyPeriod").value;
    const raw = await api("GET", `/market/daily?symbol=${encodeURIComponent(symbol)}&period=${period}`);
    if(my !== REQ.history) return;
    const rows = raw.rows || [];
    if(!rows.length){ status.textContent = "No history returned — check the symbol."; return; }
    const first = rows[0].Close, last = rows[rows.length-1].Close, pct = (last-first)/first*100;
    const ticker = raw.yahooSymbol || symbol;
    status.innerHTML = `<b>${escapeHtml(raw.name||ticker)}</b> (${escapeHtml(ticker)}) · ${rows.length} trading days, ` +
      `${fmtDate(rows[0].Date)} → ${fmtDate(rows[rows.length-1].Date)} · ` +
      `<b class="${pct>=0?'badge-good':'badge-warn'}">${pct>=0?"+":""}${pct.toFixed(2)}%</b> over the period` +
      (raw.currency ? ` · prices in ${escapeHtml(raw.currency)}` : "");
    document.getElementById("historyChartBox").hidden = false;
    HISTORY = { rows, currency: raw.currency, showAll: false, ticker };
    renderHistoryTable();
    drawHistoryChart();
  }catch(e){ if(my !== REQ.history) return; status.textContent = "Error: "+e.message; }
}

/* Daily OHLCV table: newest first, prices in the stock's currency,
   day-on-day change, readable volume, and a legend for each column. */
let HISTORY = null;
const HISTORY_COLS = [
  ["Date",   "Trading day (exchange's local date)"],
  ["Open",   "First traded price when the market opened that day"],
  ["High",   "Highest price traded during the day"],
  ["Low",    "Lowest price traded during the day"],
  ["Close",  "Last traded price when the market closed — the day's official price"],
  ["Change", "Close compared with the previous trading day's close"],
  ["Volume", "Number of shares traded during the day"],
];
function fmtDate(iso){
  return new Date(iso+"T00:00:00").toLocaleDateString("en-IN", {weekday:"short", day:"2-digit", month:"short", year:"numeric"});
}
function renderHistoryTable(){
  const {rows, currency, showAll} = HISTORY;
  const cur = currencySymbol(currency), locale = currency==="INR" ? "en-IN" : "en-US";
  const money = v => v==null ? "—" : cur + v.toLocaleString(locale, {minimumFractionDigits:2, maximumFractionDigits:2});
  const latest = rows.map((r,i)=>({...r, prev: i ? rows[i-1].Close : null})).reverse();
  const shown = showAll ? latest : latest.slice(0, 30);
  document.getElementById("marketTable").innerHTML =
    `<tr>${HISTORY_COLS.map(([c,tip])=>`<th title="${tip}"${c!=="Date"?' class="num"':""}>${c}</th>`).join("")}</tr>` +
    shown.map(r=>{
      const ch = r.prev ? r.Close - r.prev : null, chPct = r.prev ? ch / r.prev * 100 : null;
      const cls = ch==null ? "" : ch>=0 ? "badge-good" : "badge-warn";
      return `<tr><td>${fmtDate(r.Date)}</td><td class="num">${money(r.Open)}</td><td class="num">${money(r.High)}</td>` +
        `<td class="num">${money(r.Low)}</td><td class="num"><b>${money(r.Close)}</b></td>` +
        `<td class="num ${cls}">${ch==null ? "—" : `${ch>=0?"▲ +":"▼ "}${ch.toFixed(2)} (${chPct>=0?"+":""}${chPct.toFixed(2)}%)`}</td>` +
        `<td class="num">${r.Volume ? r.Volume.toLocaleString(locale) : "—"}</td></tr>`;
    }).join("");
  const more = document.getElementById("historyMore");
  more.hidden = latest.length <= 30;
  more.textContent = showAll ? "Show latest 30 days only" : `Show all ${latest.length} days`;
  document.getElementById("historyLegend").hidden = false;
}
function toggleHistoryRows(){ if(HISTORY){ HISTORY.showAll = !HISTORY.showAll; renderHistoryTable(); } }
async function getNews(){
  const my = ++REQ.news;   // ignore replies to older requests
  const out = document.getElementById("newsOut");
  out.textContent = "Fetching news…";
  try{
    const symbols = document.getElementById("newsSymbols").value;
    const raw = await api("GET", `/market/news?symbols=${encodeURIComponent(symbols)}&limit=10`);
    if(my !== REQ.news) return;
    const items = raw.data || [];
    const sm = raw.summary;
    out.innerHTML = items.length ? (sm ? `<div class="result-box"><b>Overall mood: ${escapeHtml(sm.mood)}</b> · <span class="badge positive">${sm.positive} positive</span> <span class="badge neutral">${sm.neutral} neutral</span> <span class="badge negative">${sm.negative} negative</span></div>` : "") +
      items.map(a=>{ const st = a.sentiment || {label:"neutral", words:[]};
        return `<div class="result-box news-item"><span class="badge ${st.label}" title="${st.words.length ? "Words found: "+escapeHtml(st.words.join(", ")) : "No strong words found"}">${st.label}</span><div><a href="${escapeHtml(a.link)}" target="_blank" rel="noopener"><b>${escapeHtml(a.title)}</b></a><div class="muted" style="margin-top:4px;margin-bottom:0;">${escapeHtml(a.source||"")}${a.published_at?" · "+timeAgo(a.published_at):""}</div></div></div>`; }).join("")
      : "No news in the last 7 days for that query.";
  }catch(e){ if(my !== REQ.news) return; out.textContent = "Error: "+e.message; }
}

