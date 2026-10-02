const CHARTS = {};
function destroyChart(k){ if(CHARTS[k]){ CHARTS[k].destroy(); delete CHARTS[k]; } }
function barChart(canvasId, key, labels, data, opts={}){
  destroyChart(key);
  CHARTS[key] = new Chart(document.getElementById(canvasId), {
    type:"bar",
    data:{ labels, datasets:[{ data, backgroundColor: opts.color||"#0E7C7B", borderRadius:5, maxBarThickness:50 }] },
    options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}},
      scales:{ x:{ticks:{color:"#64708A"},grid:{display:false}}, y:{ticks:{color:"#64708A"},grid:{color:"#E3E8F0"},beginAtZero:true} } }
  });
}
function lineChart(canvasId, key, labels, datasets){
  destroyChart(key);
  CHARTS[key] = new Chart(document.getElementById(canvasId), {
    type:"line",
    data:{ labels, datasets },
    options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{labels:{color:"#64708A",font:{size:11}}}},
      scales:{ x:{ticks:{color:"#64708A",maxTicksLimit:8},grid:{display:false}}, y:{ticks:{color:"#64708A"},grid:{color:"#E3E8F0"}} } }
  });
}
async function api(method, path, body){
  const res = await fetch(path, {
    method,
    headers: body ? {"Content-Type":"application/json"} : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if(!res.ok){
    const e = await res.json().catch(()=>({detail:res.statusText}));
    throw new Error(typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail));
  }
  return res.json();
}
function renderTable(id, rows, cols, limit=20){
  const table = document.getElementById(id);
  const shown = rows.slice(0, limit);
  table.innerHTML = `<tr>${cols.map(c=>`<th>${c}</th>`).join("")}</tr>` +
    shown.map(r=>`<tr>${cols.map(c=>`<td>${r[c]===null||r[c]===undefined?"—":r[c]}</td>`).join("")}</tr>`).join("") +
    (rows.length>limit ? `<tr><td colspan="${cols.length}" style="text-align:center;color:var(--muted);">…and ${rows.length-limit} more</td></tr>` : "");
}

/* ---------------- tabs ---------------- */
document.querySelectorAll(".tab").forEach(btn=>{
  btn.addEventListener("click", ()=>{
    document.querySelectorAll(".tab").forEach(b=>b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach(p=>p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("panel-"+btn.dataset.tab).classList.add("active");
    runAutoRefresh(true);
  });
});

/* ============================================================
   01 RATIOS  ->  POST /ratios/roe|roa|debt-ratio|health
   ============================================================ */
async function calcROE(){
  const box = document.getElementById("roeResult");
  try{ const r = await api("POST","/ratios/roe",{net_income:+document.getElementById("roeIncome").value, equity:+document.getElementById("roeEquity").value});
    box.textContent = `ROE = ${r.roe_pct.toFixed(2)}%`; }catch(e){ box.textContent = "Error: "+e.message; }
}
async function calcROA(){
  const box = document.getElementById("roaResult");
  try{ const r = await api("POST","/ratios/roa",{net_income:+document.getElementById("roaIncome").value, assets:+document.getElementById("roaAssets").value});
    box.textContent = `ROA = ${r.roa_pct.toFixed(2)}%`; }catch(e){ box.textContent = "Error: "+e.message; }
}
async function calcDebtRatio(){
  const box = document.getElementById("drResult");
  try{ const r = await api("POST","/ratios/debt-ratio",{liabilities:+document.getElementById("drLiab").value, assets:+document.getElementById("drAssets").value});
    box.textContent = `Debt Ratio = ${r.debt_ratio.toFixed(2)}`; }catch(e){ box.textContent = "Error: "+e.message; }
}
async function calcHealth(){
  const r = await api("POST","/ratios/health",{roe:+document.getElementById("hsRoe").value});
  document.getElementById("hsResult").textContent = `Health: ${r.health}`;
}

/* ============================================================
   02 PERSONAL FINANCE REPORT -> POST /report
   ============================================================ */
async function calcReport(){
  const out = document.getElementById("reportOut");
  try{
    const r = await api("POST","/report",{
      income:+document.getElementById("repIncome").value, expenses:+document.getElementById("repExpenses").value,
      savings:+document.getElementById("repSavings").value, debt:+document.getElementById("repDebt").value,
      equity:+document.getElementById("repEquity").value,
    });
    out.innerHTML = `
      <div class="stat-strip">
        <div class="stat">Net Profit<b>₹${r.net_profit.toLocaleString()}</b></div>
        <div class="stat">ROE<b>${r.roe.toFixed(1)}%</b></div>
        <div class="stat">ROA<b>${r.roa.toFixed(1)}%</b></div>
        <div class="stat">Current Ratio<b>${r.current_ratio.toFixed(2)}</b></div>
        <div class="stat">Debt-to-Equity<b>${r.debt_to_equity.toFixed(2)}</b></div>
      </div>
      <div class="insight-box"><span class="lbl">Tips</span>${r.tips.map(t=>`<div style="margin-top:5px;">• ${t}</div>`).join("")}</div>`;
  }catch(e){ out.innerHTML = `<div class="result-box">Error: ${e.message}</div>`; }
}

/* ============================================================
   03 AI ASSISTANT -> POST /assistant/chat, POST /assistant/snapshot
   ============================================================ */
function addMsg(text, who){
  const log = document.getElementById("chatLog");
  const div = document.createElement("div");
  div.className = `msg ${who}`;
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}
async function sendChat(){
  const input = document.getElementById("chatInput");
  const q = input.value.trim();
  if(!q) return;
  addMsg(q, "user"); input.value = "";
  const r = await api("POST","/assistant/chat",{question:q});
  addMsg(r.answer, "bot");
}
document.getElementById("chatInput").addEventListener("keydown", e=>{ if(e.key==="Enter") sendChat(); });
addMsg("Ask me about any finance term — ROE, ROA, GDP, inflation, assets, liabilities, equity and more.", "bot");

async function calcAssistant(){
  const box = document.getElementById("assistantInsight");
  try{
    const r = await api("POST","/assistant/snapshot",{
      income:+document.getElementById("asIncome").value, expenses:+document.getElementById("asExpenses").value,
      savings:+document.getElementById("asSavings").value, borrowed:+document.getElementById("asBorrowed").value,
      owned:+document.getElementById("asOwned").value,
    });
    barChart("assistantChart","assistant", ["ROE %","ROA %","Borrowed/Owned","Savings Ratio %"], [r.roe, r.roa, r.borrowed_to_owned*100, r.savings_ratio]);
    document.getElementById("assistantInsightText").textContent = r.insight;
    box.style.display = "block";
  }catch(e){ box.style.display="none"; alert(e.message); }
}

/* ============================================================
   04 LOAN INSIGHT GENERATOR -> POST /loans/screen
   ============================================================ */
let LOAN_ROWS = [];
function addLoanRow(){
  LOAN_ROWS.push({
    customer_name: document.getElementById("loanName").value,
    income: +document.getElementById("loanIncome").value,
    loan_amount: +document.getElementById("loanAmount").value,
    emi: +document.getElementById("loanEmi").value,
    credit_score: +document.getElementById("loanScore").value,
  });
  renderTable("loanTable", LOAN_ROWS, ["customer_name","income","loan_amount","emi","credit_score"]);
}
function loadLoanSample(){
  LOAN_ROWS = [
    {customer_name:"R. Verma", income:65000, loan_amount:500000, emi:12000, credit_score:810},
    {customer_name:"S. Iyer", income:48000, loan_amount:300000, emi:9000, credit_score:760},
    {customer_name:"P. Nair", income:32000, loan_amount:250000, emi:11000, credit_score:690},
    {customer_name:"A. Khan", income:28000, loan_amount:400000, emi:15000, credit_score:580},
  ];
  renderTable("loanTable", LOAN_ROWS, ["customer_name","income","loan_amount","emi","credit_score"]);
}
async function screenLoans(){
  if(!LOAN_ROWS.length){ alert("Add at least one customer first."); return; }
  const r = await api("POST","/loans/screen",{rows:LOAN_ROWS});
  renderTable("loanTable", r.rows, ["customer_name","income","loan_amount","emi","credit_score","ai_insight","ai_recommendation"]);
}

/* ============================================================
   05 CREDIT SCORE & RISK -> POST /credit-score, POST /risk
   ============================================================ */
async function calcCreditScore(){
  const out = document.getElementById("csResult"), box = document.getElementById("csInsight");
  try{
    const r = await api("POST","/credit-score",{score:+document.getElementById("csScore").value});
    out.className = `result-box ${r.level}`;
    out.textContent = `${r.category} · ${r.risk}`;
    document.getElementById("csInsightText").textContent = r.insight;
    box.style.display = "block";
  }catch(e){ out.className="result-box"; out.textContent = "Error: "+e.message; box.style.display="none"; }
}
async function calcRisk(){
  const out = document.getElementById("riskResult"), box = document.getElementById("riskInsight");
  const r = await api("POST","/risk",{
    name:document.getElementById("riskName").value||"This customer",
    income:+document.getElementById("riskIncome").value||null, emi:+document.getElementById("riskEmi").value||null,
    score:+document.getElementById("riskScore").value,
  });
  out.className = `result-box ${r.band}`;
  out.textContent = `${r.name}: ${r.level}`;
  document.getElementById("riskInsightText").textContent = r.insight;
  box.style.display = "block";
}

/* ============================================================
   06 INVESTMENT RECOMMENDATION -> POST /invest
   ============================================================ */
async function calcInvest(){
  const r = await api("POST","/invest",{
    revenue_growth:+document.getElementById("invRevenue").value||0, profit_margin:+document.getElementById("invProfit").value||0,
    roa:+document.getElementById("invRoa").value||0, roe:+document.getElementById("invRoe").value||0,
  });
  const out = document.getElementById("invResult");
  out.className = `result-box ${r.band}`;
  out.textContent = `${r.label} (score ${r.score}/4)`;
  barChart("investChart","invest", ["Revenue Growth","Profit Margin","ROA","ROE"],
    [+document.getElementById("invRevenue").value, +document.getElementById("invProfit").value, +document.getElementById("invRoa").value, +document.getElementById("invRoe").value]);
}
calcInvest();

/* ============================================================
   07 COMPANY PERFORMANCE -> POST /company-performance
   ============================================================ */
async function calcPerf(){
  const out = document.getElementById("perfOut");
  const r = await api("POST","/company-performance",{
    name:document.getElementById("perfName").value, revenue_growth:+document.getElementById("perfRevenue").value,
    csat:+document.getElementById("perfCsat").value, retention:+document.getElementById("perfRetention").value,
  });
  out.innerHTML = `
    <div class="result-box ${r.band}" style="font-size:16px;">${r.name}: ${r.status} (${r.score}/100)</div>
    <div class="insight-box"><span class="lbl">AI summary</span>${r.recommendations.map(t=>`<div style="margin-top:5px;">• ${t}</div>`).join("")}</div>`;
}

/* ============================================================
   08 PORTFOLIO DASHBOARD -> POST /portfolio
   ============================================================ */
let DASH_ROWS = [];
const PF_STATE = { companies: [], selected: null };
function addDashRow(){
  DASH_ROWS.push({
    company: document.getElementById("dashCompany").value,
    roe: +document.getElementById("dashRoe").value,
    roa: +document.getElementById("dashRoa").value,
    revenue_growth: +document.getElementById("dashRevGrowth").value,
    profit_margin: +document.getElementById("dashMargin").value,
  });
  document.getElementById("dashScoreboard").innerHTML = `<div class="stat">Companies queued<b>${DASH_ROWS.length}</b></div>`;
}
function loadDashSample(){
  DASH_ROWS = [
    {company:"JP Morgan", roe:20, roa:14, revenue_growth:18, profit_margin:22},
    {company:"Tesla",     roe:11, roa:8,  revenue_growth:10, profit_margin:12},
    {company:"ABC Ltd",   roe:3,  roa:2,  revenue_growth:3,  profit_margin:4},
    {company:"Google",    roe:21, roa:15, revenue_growth:20, profit_margin:24},
    {company:"Infosys",   roe:17, roa:12, revenue_growth:14, profit_margin:18},
  ];
  document.getElementById("dashScoreboard").innerHTML = `<div class="stat">Companies queued<b>${DASH_ROWS.length}</b></div>`;
}
async function screenPortfolio(){
  if(!DASH_ROWS.length){ alert("Add at least one company first."); return; }
  const r = await api("POST","/portfolio",{companies:DASH_ROWS});
  PF_STATE.companies = r.companies.filter(c=>c.has_data);
  PF_STATE.selected = PF_STATE.companies.length ? 0 : null;
  renderDash();
}
function renderDash(){
  const has = PF_STATE.companies.length>0;
  document.getElementById("dashWorkspace").style.display = has ? "grid" : "none";
  if(!has) return;
  const buy = PF_STATE.companies.filter(c=>c.recommendation==="buy").length;
  const hold = PF_STATE.companies.filter(c=>c.recommendation==="hold").length;
  const sell = PF_STATE.companies.filter(c=>c.recommendation==="sell").length;
  document.getElementById("dashScoreboard").innerHTML = `
    <div class="stat">Companies<b>${PF_STATE.companies.length}</b></div>
    <div class="stat">Buy<b class="badge-good">${buy}</b></div>
    <div class="stat">Hold<b>${hold}</b></div>
    <div class="stat">Sell<b class="badge-warn">${sell}</b></div>`;
  const rowsEl = document.getElementById("dashRows");
  rowsEl.innerHTML = "";
  PF_STATE.companies.forEach((c,i)=>{
    const row = document.createElement("div");
    row.className = `company-row${i===PF_STATE.selected?" sel":""}`;
    row.innerHTML = `<div><div class="name">${c.company}</div><div class="score">Score ${c.score}/100</div></div><span class="badge ${c.recommendation}">${c.recommendation.toUpperCase()}</span>`;
    row.addEventListener("click", ()=>{ PF_STATE.selected=i; renderDash(); });
    rowsEl.appendChild(row);
  });
  renderDashDetail();
}
function renderDashDetail(){
  const panel = document.getElementById("dashDetail");
  if(PF_STATE.selected===null){ panel.innerHTML = `<div style="color:var(--muted);text-align:center;padding:30px 10px;">Select a company to see its full breakdown.</div>`; return; }
  const m = PF_STATE.companies[PF_STATE.selected];
  const card = (label,val)=> val===null||val===undefined ? `<div class="result-box">${label}: —</div>` : `<div class="result-box"><b>${label}</b>: ${val.toFixed(1)}%</div>`;
  panel.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;">
      <div><h3 style="margin:0;">${m.company}</h3>${m.health?`<div style="font-size:11.5px;color:var(--muted);margin-top:3px;">Health: ${m.health}</div>`:""}</div>
      <span class="badge ${m.recommendation}" style="font-size:12.5px;padding:6px 12px;">${m.recommendation.toUpperCase()} · ${m.score}/100</span>
    </div>
    <div class="stat-strip">${card("ROE",m.roe)}${card("ROA",m.roa)}${card("Rev Growth",m.revenue_growth)}${card("Margin",m.profit_margin)}</div>
    <div style="margin-top:10px;font-size:12.5px;color:var(--muted);">Risk level: <b style="color:var(--text)">${m.risk}</b></div>`;
  const labels=[], data=[];
  if(m.roe!==null){labels.push("ROE");data.push(m.roe);}
  if(m.roa!==null){labels.push("ROA");data.push(m.roa);}
  if(m.revenue_growth!==null){labels.push("Rev Growth");data.push(m.revenue_growth);}
  if(m.profit_margin!==null){labels.push("Margin");data.push(m.profit_margin);}
  barChart("dashChart","dash", labels, data);
}

/* ============================================================
   09 GOALS -> POST /goals/plan, POST /goals/emergency-fund
   ============================================================ */
async function calcGoalPlan(){
  const errEl = document.getElementById("goalError");
  try{
    const r = await api("POST","/goals/plan",{
      name:document.getElementById("goalName").value, target:+document.getElementById("goalTarget").value,
      years:+document.getElementById("goalYears").value, current:+document.getElementById("goalCurrent").value||0,
      ret:+document.getElementById("goalReturn").value, inflation:+document.getElementById("goalInflation").value,
      income:+document.getElementById("goalIncome").value||null,
    });
    errEl.style.display = "none";
    document.getElementById("goalStats").style.display = "flex";
    document.getElementById("goalStats").innerHTML = `
      <div class="stat">Future value needed<b>₹${Math.round(r.future_value_goal).toLocaleString()}</b></div>
      <div class="stat">Monthly SIP<b>₹${Math.round(r.monthly_sip).toLocaleString()}/mo</b></div>
      <div class="stat">Total invested<b>₹${Math.round(r.total_invested).toLocaleString()}</b></div>
      <div class="stat">Projected gain<b>₹${Math.round(r.gain).toLocaleString()}</b></div>`;
    document.getElementById("goalChartWrap").style.display = "block";
    lineChart("goalChart","goal", r.schedule.map(y=>`Yr ${y.year}`), [
      { label:"Projected corpus", data:r.schedule.map(y=>y.projected_corpus), borderColor:"#0E7C7B", backgroundColor:"rgba(14,124,123,.12)", fill:true, tension:.25, pointRadius:2 },
      { label:"Inflation-adjusted target", data:r.schedule.map(y=>y.target), borderColor:"#B9840E", borderDash:[6,4], pointRadius:0 },
    ]);
    document.getElementById("goalInsightText").textContent = r.insight;
    document.getElementById("goalInsight").style.display = "block";
  }catch(e){
    errEl.style.display = "block"; errEl.textContent = e.message;
    document.getElementById("goalStats").style.display = "none";
    document.getElementById("goalChartWrap").style.display = "none";
    document.getElementById("goalInsight").style.display = "none";
  }
}
async function calcEmergencyFund(){
  const wrap = document.getElementById("efResult");
  try{
    const r = await api("POST","/goals/emergency-fund",{expenses:+document.getElementById("efExpenses").value, savings:+document.getElementById("efSavings").value||0});
    wrap.style.display = "block";
    document.getElementById("efFill").className = `progress-fill ${r.level}`;
    document.getElementById("efFill").style.width = r.progress_pct+"%";
    document.getElementById("efMonths").textContent = `${r.months_covered.toFixed(1)} months covered`;
    document.getElementById("efInsightText").textContent = r.insight;
  }catch(e){ wrap.style.display = "none"; alert(e.message); }
}

/* ============================================================
   10 KNOWLEDGE CENTER -> GET /knowledge/glossary
   ============================================================ */
(async function loadGlossary(){
  try{
    const r = await api("GET","/knowledge/glossary");
    const kcList = document.getElementById("kcList");
    r.glossary.forEach(item=>{
      const el = document.createElement("div");
      el.className = "acc-item";
      el.innerHTML = `<button class="acc-q"><span>${item.q}</span><span class="chev">+</span></button><div class="acc-a"><p>${item.a}</p></div>`;
      el.querySelector(".acc-q").addEventListener("click", ()=> el.classList.toggle("open"));
      kcList.appendChild(el);
    });
  }catch(e){ document.getElementById("kcList").textContent = "Could not load glossary: "+e.message; }
})();

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
async function getQuote(){
  const box = document.getElementById("marketStatus");
  box.textContent = "Fetching live quote…";
  try{
    const symbol = document.getElementById("marketSymbol").value.trim();
    if(!symbol){ box.textContent = "Type a company name or ticker above."; return; }
    const q = await api("GET", `/market/quote?symbol=${encodeURIComponent(symbol)}`);
    const input = document.getElementById("marketSymbol");
    if(document.activeElement !== input && input.value.trim() === symbol && q.yahooSymbol !== symbol){
      input.value = q.yahooSymbol;                       // e.g. "samsung" -> "005930.KS"
      const news = document.getElementById("newsSymbols");
      if(news.value.trim() === symbol) news.value = q.yahooSymbol;
    }
    const cur = currencySymbol(q.currency);
    box.innerHTML = `<b>${escapeHtml(q.name)}</b> <span class="muted">(${escapeHtml(q.yahooSymbol)})</span>: <b>${cur}${q.price}</b>` +
      (q.change!=null ? ` <span class="${q.change>=0?'badge-good':'badge-warn'}">${q.change>=0?"+":""}${q.change} (${q.changePercent}%)</span>` : "") +
      (q.previousClose!=null ? `<br>Prev close ${cur}${q.previousClose}` : "") +
      (q.open!=null ? ` · Open ${cur}${q.open} · Day range ${cur}${q.dayLow} – ${cur}${q.dayHigh} · Volume ${q.volume.toLocaleString()}` : "") +
      (q.asOf ? `<div class="muted" style="margin-top:4px;">Last trade: ${new Date(q.asOf).toLocaleString()}</div>` : "");
  }catch(e){ box.textContent = "Error: "+e.message; }
}
async function getDailyHistory(){
  const status = document.getElementById("historyStatus");
  status.textContent = "Fetching daily history…";
  try{
    const symbol = document.getElementById("marketSymbol").value.trim();
    const period = document.getElementById("historyPeriod").value;
    const raw = await api("GET", `/market/daily?symbol=${encodeURIComponent(symbol)}&period=${period}`);
    const rows = raw.rows || [];
    if(!rows.length){ status.textContent = "No history returned — check the symbol."; return; }
    const first = rows[0].Close, last = rows[rows.length-1].Close, pct = (last-first)/first*100;
    status.innerHTML = `${escapeHtml(symbol)}: ${rows.length} trading days, ${rows[0].Date} → ${rows[rows.length-1].Date} · ` +
      `<b class="${pct>=0?'badge-good':'badge-warn'}">${pct>=0?"+":""}${pct.toFixed(2)}%</b> over the period (table shows latest 30).`;
    document.getElementById("historyChartBox").hidden = false;
    lineChart("historyChart","history", rows.map(r=>r.Date), [
      { label:`${symbol} close`, data:rows.map(r=>r.Close), borderColor:"#0E7C7B", backgroundColor:"rgba(14,124,123,.10)", fill:true, tension:.15, pointRadius:0, borderWidth:2 },
    ]);
    renderTable("marketTable", rows.slice(-30).reverse(), ["Date","Open","High","Low","Close","Volume"], 30);
  }catch(e){ status.textContent = "Error: "+e.message; }
}
async function getNews(){
  const out = document.getElementById("newsOut");
  out.textContent = "Fetching news…";
  try{
    const symbols = document.getElementById("newsSymbols").value;
    const raw = await api("GET", `/market/news?symbols=${encodeURIComponent(symbols)}&limit=10`);
    const items = raw.data || [];
    out.innerHTML = items.length ? items.map(a=>`<div class="result-box"><a href="${escapeHtml(a.link)}" target="_blank" rel="noopener"><b>${escapeHtml(a.title)}</b></a><div class="muted" style="margin-top:4px;">${escapeHtml(a.source||"")}${a.published_at?" · "+timeAgo(a.published_at):""}</div></div>`).join("") : "No news in the last 7 days for that query.";
  }catch(e){ out.textContent = "Error: "+e.message; }
}

/* ============================================================
   12 GROWTH & TARGET PLANNER -> POST /planner/what-if, /planner/target-plan
   ============================================================ */
async function calcWhatIf(){
  const box = document.getElementById("wiResult");
  try{
    const r = await api("POST","/planner/what-if",{
      amount:+document.getElementById("wiAmount").value, price_then:+document.getElementById("wiThen").value,
      price_now:+document.getElementById("wiNow").value, days_held:+document.getElementById("wiDays").value,
    });
    box.innerHTML = `Shares: <b>${r.shares.toFixed(4)}</b><br>Value now: <b>₹${r.value_now.toFixed(2)}</b><br>Gain: <b class="${r.gain>=0?'badge-good':'badge-warn'}">₹${r.gain.toFixed(2)} (${r.gain_pct.toFixed(2)}%)</b>${r.cagr!==null?`<br>CAGR: <b>${r.cagr.toFixed(2)}%</b>`:""}`;
  }catch(e){ box.textContent = "Error: "+e.message; }
}
async function calcTargetPlan(){
  const box = document.getElementById("tpResult");
  try{
    const r = await api("POST","/planner/target-plan",{
      entry:+document.getElementById("tpEntry").value, qty:+document.getElementById("tpQty").value,
      target_pct:+document.getElementById("tpTarget").value, stop_pct:+document.getElementById("tpStop").value,
    });
    box.className = `result-box ${r.band||""}`;
    box.innerHTML = `Target price: <b class="badge-good">₹${r.target_price.toFixed(2)}</b><br>Stop-loss price: <b class="badge-warn">₹${r.stop_price.toFixed(2)}</b><br>Potential gain: ₹${r.gain_amount.toFixed(2)} · Potential loss: ₹${r.loss_amount.toFixed(2)}${r.risk_reward!==null?`<br>Risk-Reward: <b>${r.risk_reward.toFixed(2)}</b>`:""}<br><span class="muted">${r.verdict}</span>`;
  }catch(e){ box.className="result-box"; box.textContent = "Error: "+e.message; }
}

/* ============================================================
   13 PORTFOLIO & TAX TOOLS
   ============================================================ */
async function calcSip(){
  const box = document.getElementById("sipResult");
  try{
    const prices = document.getElementById("sipPrices").value.split(",").map(s=>+s.trim()).filter(n=>!isNaN(n));
    const r = await api("POST","/tools/sip-vs-lumpsum",{
      total:+document.getElementById("sipTotal").value, months:+document.getElementById("sipMonths").value,
      start_price:+document.getElementById("sipStart").value, prices_by_month:prices, last_price:+document.getElementById("sipLast").value,
    });
    box.innerHTML = `Lump sum value: <b>₹${r.lump_sum_value.toFixed(2)}</b><br>SIP value: <b>₹${r.sip_value.toFixed(2)}</b><br>Winner: <b class="badge-good">${r.winner==="lump_sum"?"Lump Sum":"SIP"}</b> by ₹${r.difference.toFixed(2)}`;
  }catch(e){ box.textContent = "Error: "+e.message; }
}
async function calcTax(){
  const box = document.getElementById("taxResult");
  try{
    const r = await api("POST","/tools/capital-gains-tax",{
      buy_price:+document.getElementById("taxBuy").value, sell_price:+document.getElementById("taxSell").value,
      qty:+document.getElementById("taxQty").value, buy_date:document.getElementById("taxBuyDate").value,
      sell_date:document.getElementById("taxSellDate").value, other_ltcg:+document.getElementById("taxOtherLtcg").value||0,
    });
    box.innerHTML = `Holding period: <b>${r.holding_days} days</b> → <b>${r.tax_type}</b><br>Gross gain: <b>₹${r.gain.toFixed(2)}</b><br>Estimated tax (incl. cess): <b class="badge-warn">₹${r.tax.toFixed(2)}</b><br>Net proceeds: <b class="badge-good">₹${r.net_proceeds.toFixed(2)}</b>`;
  }catch(e){ box.textContent = "Error: "+e.message; }
}
async function calcRange(){
  const box = document.getElementById("rangeResult");
  try{
    const r = await api("POST","/tools/52-week-range",{
      current:+document.getElementById("rangeCurrent").value, high:+document.getElementById("rangeHigh").value, low:+document.getElementById("rangeLow").value,
    });
    box.innerHTML = `Position in range: <b>${r.range_position_pct.toFixed(1)}%</b><br>From 52w high: <b class="badge-warn">${r.from_high_pct.toFixed(2)}%</b><br>From 52w low: <b class="badge-good">+${r.from_low_pct.toFixed(2)}%</b>`;
  }catch(e){ box.textContent = "Error: "+e.message; }
}

/* ============================================================
   14 WATCHLIST & PRICE ALERTS (reuses GET /market/quote)
   ============================================================ */
const WATCHLIST = [];
const ALERTS = [];
function addWatchlistSymbol(){
  const input = document.getElementById("wlSymbol");
  const symbol = input.value.trim().toUpperCase();
  if(!symbol){ input.focus(); return; }
  input.value = "";
  if(!WATCHLIST.some(w=>w.symbol===symbol)) WATCHLIST.push({symbol, price:null, change:null, changePercent:null, day:null});
  renderWatchlist(); refreshAlertSymbolSelect(); refreshWatchlist();
}
function removeWatchlistSymbol(i){ WATCHLIST.splice(i,1); renderWatchlist(); refreshAlertSymbolSelect(); }
function renderWatchlist(){
  const table = document.getElementById("wlTable");
  table.innerHTML = `<tr><th>Symbol</th><th>Price</th><th>Change</th><th>%</th><th>As of</th><th></th></tr>` +
    WATCHLIST.map((w,i)=>`<tr><td><b>${escapeHtml(w.symbol)}</b>${w.name?`<div class="muted" style="margin:0;font-size:12px;">${escapeHtml(w.name)}</div>`:""}</td><td>${w.price??"—"}</td><td>${w.change??"—"}</td><td>${w.changePercent??"—"}</td><td>${w.day??"—"}</td><td><button class="btn secondary" onclick="removeWatchlistSymbol(${i})">Remove</button></td></tr>`).join("");
}
async function refreshWatchlist(){
  for(const w of WATCHLIST){
    try{
      const q = await api("GET", `/market/quote?symbol=${encodeURIComponent(w.symbol)}`);
      if(q && q.price!=null) Object.assign(w, { name:q.name, price:q.price, change:q.change, changePercent:q.changePercent, day:q.asOf?new Date(q.asOf).toLocaleString():"" });
      else w.price = "no data";
    }catch(e){ w.price = "Error"; }
  }
  renderWatchlist();
  checkAlerts();
}
function refreshAlertSymbolSelect(){
  const sel = document.getElementById("alertSymbol");
  sel.innerHTML = WATCHLIST.map(w=>`<option value="${w.symbol}">${w.symbol}</option>`).join("") || `<option value="">Add a symbol to the watchlist first</option>`;
}
function addPriceAlert(){
  const symbol = document.getElementById("alertSymbol").value;
  if(!symbol){ alert("Add a symbol to the watchlist first."); return; }
  ALERTS.push({ symbol, type:document.getElementById("alertType").value, price:+document.getElementById("alertPrice").value, triggered:false });
  renderAlerts();
}
function removePriceAlert(i){ ALERTS.splice(i,1); renderAlerts(); }
function renderAlerts(){
  const table = document.getElementById("alertTable");
  table.innerHTML = `<tr><th>Symbol</th><th>Condition</th><th>Status</th><th></th></tr>` +
    ALERTS.map((a,i)=>`<tr><td>${a.symbol}</td><td>${a.type==="above"?"Rises above":"Falls below"} ₹${a.price}</td><td>${a.triggered?'<b class="badge-warn">Alert triggered</b>':"Watching"}</td><td><button class="btn secondary" onclick="removePriceAlert(${i})">Remove</button></td></tr>`).join("");
}
function checkAlerts(){
  ALERTS.forEach(a=>{
    const w = WATCHLIST.find(x=>x.symbol===a.symbol);
    if(!w || typeof w.price !== "number") return;
    a.triggered = a.type==="above" ? w.price > a.price : w.price < a.price;
  });
  renderAlerts();
}
refreshAlertSymbolSelect();

/* ============================================================
   15 API KEY DIRECTORY -> GET /api-keys
   ============================================================ */
(async function loadKeys(){
  try{
    const r = await api("GET","/api-keys");
    if(!r.keys || !r.keys.length){
      document.getElementById("keysOut").innerHTML = `<div class="result-box">${r.note || "No API keys required."}</div>`;
      return;
    }
    document.getElementById("keysOut").innerHTML = r.keys.map(k=>`
      <div class="key-card">
        <h3>${k.name}</h3>
        <div>${k.function}</div>
        <div class="meta">Used in: ${k.used_in.join(", ")} · Free tier: ${k.free_tier}</div>
        <div class="meta"><a href="${k.get_key_url}" target="_blank">Get a key →</a></div>
      </div>`).join("");
  }catch(e){ document.getElementById("keysOut").textContent = "Could not load: "+e.message; }
})();

/* ============================================================
   16 ABOUT -> GET /about
   ============================================================ */
(async function loadAbout(){
  try{
    const r = await api("GET","/about");
    document.getElementById("aboutOut").innerHTML = `
      <div class="result-box">${r.about_text}</div>
      <div class="card" style="margin-top:12px;background:rgba(14,124,123,.06);">
        <h3 style="margin-top:0;">Why this matters</h3>
        <p style="margin:0;">${r.why_it_matters}</p>
      </div>
      <div class="row" style="margin-top:12px;">
        <div class="field"><label>Version</label><div>${r.version}</div></div>
        <div class="field"><label>Endpoints</label><div>${r.endpoint_count} across ${r.sections.length} sections</div></div>
      </div>
      <div class="meta" style="margin-top:8px;">Tech stack: ${r.tech_stack.join(", ")}</div>`;
  }catch(e){ document.getElementById("aboutOut").textContent = "Could not load: "+e.message; }
})();

/* ============================================================
   AUTO-REFRESH for live market data (sections 11 & 14)
   Each job only runs while its tab is open, the browser tab is visible
   and its checkbox is ticked — so nothing is fetched in the background.
   ============================================================ */
const AUTO_JOBS = [
  { panel:"market",    toggle:"quoteAuto", every:30*1000,   run:getQuote,         last:0 },
  { panel:"market",    toggle:"quoteAuto", every:10*60*1000, run:getDailyHistory, last:0 },
  { panel:"market",    toggle:"newsAuto",  every:5*60*1000, run:getNews,          last:0 },
  { panel:"watchlist", toggle:"wlAuto",    every:30*1000,   run:()=>WATCHLIST.length && refreshWatchlist(), last:0 },
];
function runAutoRefresh(force=false){
  if(document.hidden) return;
  const now = Date.now();
  for(const job of AUTO_JOBS){
    const panel = document.getElementById("panel-"+job.panel);
    const toggle = document.getElementById(job.toggle);
    if(!panel || !panel.classList.contains("active") || !toggle || !toggle.checked) continue;
    if(force || now - job.last >= job.every){ job.last = now; job.run(); }
  }
}
setInterval(runAutoRefresh, 5000);
document.addEventListener("visibilitychange", ()=>runAutoRefresh());

/* ============================================================
   SYMBOL SEARCH DROPDOWN — click to browse popular stocks, or type
   any company name / ticker to search every listed company via
   GET /market/search. Enter picks the highlighted (or first) match.
   ============================================================ */
const POPULAR = [
  ["Indices", [
    ["^NSEI","NIFTY 50","NSE"], ["^BSESN","S&P BSE SENSEX","BSE"], ["^NSEBANK","NIFTY Bank","NSE"], ["^CNXIT","NIFTY IT","NSE"],
    ["^GSPC","S&P 500","US"], ["^IXIC","NASDAQ Composite","US"], ["^DJI","Dow Jones Industrial Average","US"],
  ]],
  ["India — NSE", [
    ["RELIANCE.NS","Reliance Industries"], ["TCS.NS","Tata Consultancy Services"], ["HDFCBANK.NS","HDFC Bank"],
    ["ICICIBANK.NS","ICICI Bank"], ["INFY.NS","Infosys"], ["BHARTIARTL.NS","Bharti Airtel"], ["SBIN.NS","State Bank of India"],
    ["ITC.NS","ITC"], ["HINDUNILVR.NS","Hindustan Unilever"], ["LT.NS","Larsen & Toubro"], ["KOTAKBANK.NS","Kotak Mahindra Bank"],
    ["AXISBANK.NS","Axis Bank"], ["BAJFINANCE.NS","Bajaj Finance"], ["BAJAJFINSV.NS","Bajaj Finserv"], ["HCLTECH.NS","HCL Technologies"],
    ["WIPRO.NS","Wipro"], ["TECHM.NS","Tech Mahindra"], ["ASIANPAINT.NS","Asian Paints"], ["MARUTI.NS","Maruti Suzuki"],
    ["TMPV.NS","Tata Motors Passenger Vehicles"], ["TMCV.NS","Tata Motors (Commercial Vehicles)"], ["M&M.NS","Mahindra & Mahindra"],
    ["BAJAJ-AUTO.NS","Bajaj Auto"], ["HEROMOTOCO.NS","Hero MotoCorp"], ["EICHERMOT.NS","Eicher Motors"],
    ["SUNPHARMA.NS","Sun Pharmaceutical"], ["DRREDDY.NS","Dr. Reddy's Laboratories"], ["CIPLA.NS","Cipla"], ["APOLLOHOSP.NS","Apollo Hospitals"],
    ["TITAN.NS","Titan Company"], ["ULTRACEMCO.NS","UltraTech Cement"], ["GRASIM.NS","Grasim Industries"], ["NESTLEIND.NS","Nestlé India"],
    ["BRITANNIA.NS","Britannia Industries"], ["TATACONSUM.NS","Tata Consumer Products"], ["POWERGRID.NS","Power Grid Corporation"],
    ["NTPC.NS","NTPC"], ["ONGC.NS","Oil & Natural Gas Corporation"], ["COALINDIA.NS","Coal India"], ["TATASTEEL.NS","Tata Steel"],
    ["JSWSTEEL.NS","JSW Steel"], ["HINDALCO.NS","Hindalco Industries"], ["ADANIENT.NS","Adani Enterprises"], ["ADANIPORTS.NS","Adani Ports & SEZ"],
    ["INDUSINDBK.NS","IndusInd Bank"], ["SBILIFE.NS","SBI Life Insurance"], ["HDFCLIFE.NS","HDFC Life Insurance"], ["LICI.NS","Life Insurance Corporation of India"],
    ["ETERNAL.NS","Eternal (Zomato)"], ["TRENT.NS","Trent"], ["DMART.NS","Avenue Supermarts (DMart)"], ["BEL.NS","Bharat Electronics"],
    ["HAL.NS","Hindustan Aeronautics"], ["SHRIRAMFIN.NS","Shriram Finance"], ["JIOFIN.NS","Jio Financial Services"], ["IRCTC.NS","IRCTC"],
    ["PIDILITIND.NS","Pidilite Industries"], ["PAYTM.NS","Paytm (One 97 Communications)"], ["NYKAA.NS","Nykaa (FSN E-Commerce)"],
  ].map(([s,n])=>[s,n,"NSE"])],
  ["US & Global", [
    ["AAPL","Apple","NASDAQ"], ["MSFT","Microsoft","NASDAQ"], ["GOOGL","Alphabet (Google)","NASDAQ"], ["AMZN","Amazon","NASDAQ"],
    ["NVDA","NVIDIA","NASDAQ"], ["META","Meta Platforms","NASDAQ"], ["TSLA","Tesla","NASDAQ"], ["NFLX","Netflix","NASDAQ"],
    ["IBM","IBM","NYSE"], ["005930.KS","Samsung Electronics","Korea"], ["TM","Toyota Motor","NYSE"],
  ]],
].map(([group, rows])=>({ group, rows: rows.map(([symbol,name,exchange])=>({symbol,name,exchange,type:"EQUITY"})) }));

function attachSymbolSearch(inputId, boxId, onPick){
  const input = document.getElementById(inputId), box = document.getElementById(boxId);
  const toggle = input.parentElement.querySelector(".suggest-toggle");
  let timer = null, items = [], active = -1, seq = 0;
  const norm = s=>s.toLowerCase().replace(/[^a-z0-9]/g,"");
  const close = ()=>{ box.hidden = true; active = -1; };
  const pick = (symbol)=>{ input.value = symbol; close(); input.blur(); onPick(symbol); };

  // sections: [{group, rows}] — flattened into `items` for keyboard navigation
  const render = (sections, note="")=>{
    items = sections.flatMap(s=>s.rows);
    let i = 0;
    box.innerHTML = sections.filter(s=>s.rows.length).map(s=>
      `<div class="suggest-group">${escapeHtml(s.group)}</div>` +
      s.rows.map(r=>{ const k = i++; return `<div class="suggest-item${k===active?" active":""}" data-i="${k}"><span class="sym">${escapeHtml(r.symbol)}</span><span class="nm">${escapeHtml(r.name)}</span><span class="exch">${escapeHtml(r.exchange)}${r.type && r.type!=="EQUITY"?" · "+escapeHtml(r.type):""}</span></div>`; }).join("")
    ).join("") + (note ? `<div class="suggest-empty">${note}</div>` : "");
    box.hidden = false;
    const el = box.querySelector(".suggest-item.active"); if(el) el.scrollIntoView({block:"nearest"});
  };
  let sections = [];
  const show = (secs, note)=>{ sections = secs; render(secs, note); };
  const showPopular = ()=>{ active = -1; show(POPULAR); };
  const localMatches = q=>{
    const n = norm(q);
    return POPULAR.flatMap(s=>s.rows).filter(r=>norm(r.name).includes(n) || norm(r.symbol).startsWith(n)).slice(0,6);
  };

  input.addEventListener("focus", ()=>{ input.select(); showPopular(); });
  input.addEventListener("click", ()=>{ if(box.hidden) showPopular(); });
  if(toggle) toggle.addEventListener("mousedown", e=>{ e.preventDefault(); if(box.hidden){ input.focus(); showPopular(); } else close(); });

  input.addEventListener("input", ()=>{
    clearTimeout(timer);
    const q = input.value.trim();
    active = -1;
    if(!q){ showPopular(); return; }
    const local = localMatches(q);
    show([{group:"Popular", rows:local}], "Searching all listed companies…");
    timer = setTimeout(async ()=>{
      const my = ++seq;
      try{
        const r = await api("GET", `/market/search?q=${encodeURIComponent(q)}`);
        if(my !== seq || document.activeElement !== input) return;   // a newer keystroke won
        const seen = new Set(local.map(x=>x.symbol));
        const more = (r.results||[]).filter(x=>!seen.has(x.symbol));
        show([{group:"Popular", rows:local}, {group:"All markets", rows:more}],
             local.length || more.length ? "" : `No company found for “${escapeHtml(q)}”. Check the spelling, or press Enter to try it as a ticker.`);
      }catch(e){ if(my === seq) show(sections.slice(0,1), "Search is unavailable right now — press Enter to try it as a ticker."); }
    }, 250);
  });
  input.addEventListener("keydown", e=>{
    const open = !box.hidden && items.length;
    if(e.key === "ArrowDown"){ if(box.hidden) showPopular(); else if(open){ active = (active+1) % items.length; render(sections); } e.preventDefault(); }
    else if(e.key === "ArrowUp" && open){ active = (active-1+items.length) % items.length; render(sections); e.preventDefault(); }
    else if(e.key === "Enter"){
      e.preventDefault();
      const v = input.value.trim();
      if(open && active >= 0) pick(items[active].symbol);
      else if(open && v) pick(items[0].symbol);        // best match for what was typed
      else if(v) pick(v);                              // backend resolves names/tickers itself
    }
    else if(e.key === "Escape") close();
  });
  box.addEventListener("mousedown", e=>{ e.preventDefault(); const el = e.target.closest(".suggest-item"); if(el) pick(items[+el.dataset.i].symbol); });
  input.addEventListener("blur", ()=>setTimeout(close, 120));
}

function selectMarketSymbol(symbol){
  document.getElementById("marketSymbol").value = symbol;
  document.getElementById("newsSymbols").value = symbol;
  AUTO_JOBS.forEach(j=>{ if(j.panel==="market") j.last = Date.now(); });   // we're refreshing right now
  getQuote(); getDailyHistory(); getNews();
}
attachSymbolSearch("marketSymbol", "marketSuggest", selectMarketSymbol);
attachSymbolSearch("wlSymbol", "wlSuggest", ()=>addWatchlistSymbol());
document.getElementById("historyPeriod").addEventListener("change", getDailyHistory);
