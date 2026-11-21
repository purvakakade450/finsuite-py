/* ============================================================
   22 PORTFOLIO TRACKER -> POST /tracker/value
   ============================================================ */
const HOLDINGS = LS.get("fs-portfolio", []);
let PF_SEQ = 0;
function saveHoldings(){
  LS.set("fs-portfolio", HOLDINGS);
  if(AUTH.user) api("PUT","/user/data/portfolio",{value:HOLDINGS}).catch(()=>{});
}
function addHolding(){
  const symbol = document.getElementById("pfSymbol").value.trim();
  if(!symbol){ document.querySelector("#pfPicker .picker-btn").click(); return; }
  const qty = val("pfQty"), avg = val("pfAvg");
  if(qty <= 0 || avg < 0){ alert("Enter a quantity above 0 and a buy price of 0 or more."); return; }
  const same = HOLDINGS.find(h=>h.symbol===symbol);
  if(same){ same.avg_price = (same.avg_price*same.qty + avg*qty) / (same.qty + qty); same.qty += qty; }   // buying more averages the price
  else HOLDINGS.push({symbol, qty, avg_price: avg});
  saveHoldings(); renderHoldings(); valuePortfolio();
}
function removeHolding(i){ HOLDINGS.splice(i,1); saveHoldings(); if(LAST.tracker) LAST.tracker = null; renderHoldings(); if(HOLDINGS.length) valuePortfolio(); }
function loadSampleHoldings(){
  HOLDINGS.splice(0, HOLDINGS.length, {symbol:"TCS.NS", qty:10, avg_price:2700}, {symbol:"HDFCBANK.NS", qty:40, avg_price:690},
    {symbol:"RELIANCE.NS", qty:15, avg_price:1250}, {symbol:"INFY.NS", qty:12, avg_price:1300}, {symbol:"AAPL", qty:5, avg_price:210});
  saveHoldings(); renderHoldings(); valuePortfolio();
}
function renderHoldings(){
  const t = document.getElementById("pfTable");
  const live = LAST.tracker ? Object.fromEntries(LAST.tracker.rows.map(r=>[r.symbol, r])) : {};
  if(!HOLDINGS.length){
    t.innerHTML = `<tr><td class="muted">No holdings yet. Add a stock above, or load the sample portfolio.</td></tr>`;
    setHidden(["pfStats","pfCharts","pfInsight"], true); showExport("tracker", false); return;
  }
  t.innerHTML = `<tr><th>Stock</th><th class="num">Qty</th><th class="num">Avg buy</th><th class="num">Live price</th><th class="num">Invested</th><th class="num">Value</th><th class="num">P/L</th><th class="num">Today</th><th class="num">Weight</th><th></th></tr>` +
    HOLDINGS.map((h,i)=>{
      const r = live[h.symbol], cur = currencySymbol(r && r.currency || "INR");
      const m = v => v==null ? "—" : cur + (+v).toLocaleString("en-IN",{maximumFractionDigits:2});
      if(r && r.error && r.price==null) return `<tr><td><b>${escapeHtml(h.symbol)}</b><div class="badge-warn" style="font-size:11.5px;white-space:normal;max-width:260px;">${escapeHtml(r.error)}</div></td><td class="num">${h.qty}</td><td class="num">${m(h.avg_price)}</td><td colspan="6"></td><td><button class="btn secondary sm" onclick="removeHolding(${i})">Remove</button></td></tr>`;
      return `<tr><td><b>${escapeHtml(r&&r.yahooSymbol||h.symbol)}</b>${r&&r.name?`<div class="muted" style="margin:0;font-size:12px;">${escapeHtml(r.name)}</div>`:""}</td>
        <td class="num">${h.qty}</td><td class="num">${m(h.avg_price)}</td><td class="num">${r?m(r.price):"…"}</td><td class="num">${r?m(r.invested):"—"}</td><td class="num">${r?m(r.value):"—"}</td>
        <td class="num ${r&&r.pnl>=0?"badge-good":"badge-warn"}">${r?`${signed(r.pnl, v=>m(v))}<br>${pct(r.pnl_pct)}`:"—"}</td>
        <td class="num ${r&&r.day_change>=0?"badge-good":"badge-warn"}">${r&&r.day_change_pct!=null?`${r.day_change>=0?"+":""}${r.day_change_pct}%`:"—"}</td>
        <td class="num">${r&&r.weight_pct!=null?pct(r.weight_pct,1):"—"}</td><td><button class="btn secondary sm" onclick="removeHolding(${i})">Remove</button></td></tr>`;
    }).join("");
}
async function valuePortfolio(silent=false){
  if(!HOLDINGS.length){ renderHoldings(); return; }
  const my = ++PF_SEQ, status = document.getElementById("pfStatus");
  if(!silent){ status.hidden = false; status.className = "result-box"; status.textContent = "Fetching live prices…"; }
  try{
    const r = await api("POST","/tracker/value",{holdings: HOLDINGS});
    if(my !== PF_SEQ) return;
    status.hidden = true;
    LAST.tracker = r;
    document.getElementById("pfStats").innerHTML = `
      <div class="stat">Invested<b>${rupees(r.invested)}</b></div>
      <div class="stat">Current value<b>${rupees(r.value)}</b></div>
      <div class="stat">Total profit / loss<b class="${r.pnl>=0?"badge-good":"badge-warn"}">${signed(r.pnl)} (${pct(r.pnl_pct)})</b></div>
      <div class="stat">Today<b class="${r.day_change>=0?"badge-good":"badge-warn"}">${signed(r.day_change)}</b></div>`;
    renderHoldings();
    const priced = r.rows.filter(x=>x.value_base!=null);
    doughnutChart("pfPie","pfpie", priced.map(x=>x.name||x.symbol), priced.map(x=>Math.round(x.value_base)));
    barChart("pfBar","pfbar", priced.map(x=>x.yahooSymbol||x.symbol), priced.map(x=>+x.pnl_pct.toFixed(2)), {color: priced.map(x=>x.pnl_pct>=0?"#1F9D6B":"#C43D3D")});
    CHARTS.pfbar.options.scales.y.beginAtZero = false; CHARTS.pfbar.options.plugins.tooltip = {callbacks:{label:c=>`P/L ${c.raw}%`}}; CHARTS.pfbar.update();
    document.getElementById("pfInsightText").textContent = r.insight + ` Values in ${r.base}; foreign stocks converted at the live exchange rate.`;
    setHidden(["pfStats","pfCharts","pfInsight"], false);
    showExport("tracker");
  }catch(e){ if(my !== PF_SEQ) return; status.hidden = false; status.className = "result-box sell"; status.textContent = "Error: " + e.message; }
}


// Fill a planner field (retirement or goal savings) from the portfolio's current value.
async function usePortfolioFor(inputId){
  if(!HOLDINGS.length){ toast("Your Portfolio Tracker is empty. Add your holdings there first.", "warn"); showTab("tracker"); return; }
  try{
    let r = LAST.tracker;
    if(!r){ toast("Valuing your portfolio…"); r = await api("POST","/tracker/value",{holdings: HOLDINGS}); LAST.tracker = r; }
    document.getElementById(inputId).value = Math.round(r.value);
    toast(`Filled in with your portfolio value, ${rupees(r.value)}.`);
  }catch(e){ toast(e.message, "warn"); }
}
