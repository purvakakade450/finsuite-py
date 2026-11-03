const CHARTS = {};
const PALETTE = ["#1F3A68","#9C7A3C","#5B7DB1","#2E7D4F","#A63232","#7A6A9E","#C49A52","#8A94A8","#3F6E78","#B5654A"];
function themeColors(){
  const cs = getComputedStyle(document.documentElement);
  return { muted: cs.getPropertyValue("--muted").trim() || "#64708A", grid: cs.getPropertyValue("--border").trim() || "#E3E8F0",
           card: cs.getPropertyValue("--card").trim() || "#fff" };
}
function destroyChart(k){ if(CHARTS[k]){ CHARTS[k].destroy(); delete CHARTS[k]; } }
function makeChart(canvasId, key, config){
  destroyChart(key);
  CHARTS[key] = new Chart(document.getElementById(canvasId), config);
  return CHARTS[key];
}
function barChart(canvasId, key, labels, data, opts={}){
  const t = themeColors();
  const datasets = opts.datasets || [{ data, backgroundColor: opts.color||"#1F3A68", borderRadius:5, maxBarThickness:50 }];
  return makeChart(canvasId, key, {
    type:"bar",
    data:{ labels, datasets },
    options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:!!opts.datasets, labels:{color:t.muted,font:{size:11}}}},
      scales:{ x:{ticks:{color:t.muted},grid:{display:false}}, y:{ticks:{color:t.muted},grid:{color:t.grid},beginAtZero:true} } }
  });
}
function lineChart(canvasId, key, labels, datasets, opts={}){
  const t = themeColors();
  return makeChart(canvasId, key, {
    type:"line",
    data:{ labels, datasets },
    options:{ responsive:true, maintainAspectRatio:false, interaction:{mode:"index", intersect:false},
      plugins:{legend:{labels:{color:t.muted,font:{size:11}}}},
      scales:{ x:{ticks:{color:t.muted,maxTicksLimit:8},grid:{display:false}}, y:{ticks:{color:t.muted},grid:{color:t.grid}, ...(opts.y||{})} } }
  });
}
function doughnutChart(canvasId, key, labels, data){
  const t = themeColors();
  return makeChart(canvasId, key, {
    type:"doughnut",
    data:{ labels, datasets:[{ data, backgroundColor: labels.map((_,i)=>PALETTE[i%PALETTE.length]), borderColor:t.card, borderWidth:2 }] },
    options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{position:"right", labels:{color:t.muted,font:{size:11},boxWidth:12}}} }
  });
}
// Re-colour axes and legends of every chart already drawn (after a theme switch).
function applyChartTheme(){
  const t = themeColors();
  Object.values(CHARTS).forEach(c=>{
    const o = c.options;
    if(o.plugins && o.plugins.legend && o.plugins.legend.labels) o.plugins.legend.labels.color = t.muted;
    Object.values(o.scales||{}).forEach(sc=>{ if(sc.ticks) sc.ticks.color = t.muted; if(sc.grid && sc.grid.color) sc.grid.color = t.grid; });
    if(c.config.type === "doughnut") c.data.datasets.forEach(d=>d.borderColor = t.card);
    c.update("none");
  });
}
async function api(method, path, body){
  const headers = {};
  if(body) headers["Content-Type"] = "application/json";
  if(AUTH.token) headers["Authorization"] = "Bearer " + AUTH.token;
  const res = await fetch(path, {
    method,
    headers,
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

/* ---------------- tabs, grouped menu, saved settings ---------------- */
// localStorage can be missing or blocked (private mode); the app still works without it.
const LS = {
  get(k, fallback=null){ try{ const v = localStorage.getItem(k); return v===null ? fallback : JSON.parse(v); }catch(e){ return fallback; } },
  set(k, v){ try{ localStorage.setItem(k, JSON.stringify(v)); }catch(e){} },
  del(k){ try{ localStorage.removeItem(k); }catch(e){} },
};
const AUTH = { token: LS.get("fs-token"), user: null, emailDelivery: false };

function closeNavMenus(except){ document.querySelectorAll(".nav-group.open").forEach(g=>{ if(g!==except) g.classList.remove("open"); }); }
function showTab(name, opts={}){
  const btn = document.querySelector(`.tab[data-tab="${name}"]`);
  const panel = document.getElementById("panel-"+name);
  if(!btn || !panel) return;
  document.querySelectorAll(".tab").forEach(b=>b.classList.remove("active"));
  document.querySelectorAll(".panel").forEach(p=>p.classList.remove("active"));
  document.querySelectorAll(".nav-group").forEach(g=>{ g.classList.remove("has-active"); g.querySelector(".nav-current").textContent = ""; });
  btn.classList.add("active");
  panel.classList.add("active");
  const group = btn.closest(".nav-group");
  group.classList.add("has-active");
  const label = btn.childNodes[0].textContent.trim();
  group.querySelector(".nav-current").textContent = "· " + label;
  document.getElementById("navCurrent").textContent = label;
  closeNavMenus(); document.body.classList.remove("nav-open");
  document.getElementById("navToggle").setAttribute("aria-expanded","false");
  LS.set("fs-tab", name);
  if(!opts.noHash) history.replaceState(null, "", "#"+name);
  if(!opts.keepScroll) window.scrollTo({top:0});
  runAutoRefresh(true);
  if(typeof onTabShown === "function") onTabShown(name);
}
document.querySelectorAll(".tab").forEach(btn=> btn.addEventListener("click", ()=> showTab(btn.dataset.tab)));
document.querySelectorAll(".nav-group").forEach(g=>{
  g.querySelector(".nav-group-btn").addEventListener("click", e=>{ e.stopPropagation(); closeNavMenus(g); g.classList.toggle("open"); });
});
document.addEventListener("click", e=>{ if(!e.target.closest(".nav-group")) closeNavMenus(); });
document.addEventListener("keydown", e=>{ if(e.key==="Escape"){ closeNavMenus(); document.body.classList.remove("nav-open"); } });
document.getElementById("navToggle").addEventListener("click", ()=>{
  const open = document.body.classList.toggle("nav-open");
  document.getElementById("navToggle").setAttribute("aria-expanded", String(open));
});

/* ---------------- dark mode ---------------- */
function currentTheme(){
  const set = document.documentElement.dataset.theme;
  return set || "light";   // light unless the user picks dark
}
function paintThemeButton(){
  const dark = currentTheme()==="dark";
  const b = document.getElementById("themeToggle");
  b.innerHTML = dark ? '<svg class="ico" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>' : '<svg class="ico" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>';
  b.title = dark ? "Switch to light mode" : "Switch to dark mode";
  if(window.Chart){ Chart.defaults.color = themeColors().muted; applyChartTheme(); }
}
document.getElementById("themeToggle").addEventListener("click", ()=>{
  const next = currentTheme()==="dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try{ localStorage.setItem("fs-theme", next); }catch(e){}
  paintThemeButton();
});
paintThemeButton();

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
  const box = document.getElementById("hsResult");
  try{ const r = await api("POST","/ratios/health",{roe:+document.getElementById("hsRoe").value});
    box.textContent = `Health: ${r.health}`; }catch(e){ box.textContent = "Error: "+e.message; }
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
    LAST.report = { inputs: readInputs({Income:"repIncome", Expenses:"repExpenses", Savings:"repSavings", Debt:"repDebt", Equity:"repEquity"}), r };
    showExport("report");
  }catch(e){ out.innerHTML = `<div class="result-box">Error: ${e.message}</div>`; showExport("report", false); }
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
addMsg("Ask me about any finance term, such as ROE, ROA, EMI, SIP, inflation, assets, liabilities or equity.", "bot");

async function calcAssistant(){
  const box = document.getElementById("assistantInsight");
  try{
    const r = await api("POST","/assistant/snapshot",{
      income:+document.getElementById("asIncome").value, expenses:+document.getElementById("asExpenses").value,
      savings:+document.getElementById("asSavings").value, borrowed:+document.getElementById("asBorrowed").value,
      owned:+document.getElementById("asOwned").value,
    });
    barChart("assistantChart","assistant", ["ROE %","ROA %","Borrowed/Owned %","Savings Ratio %"], [r.roe, r.roa, r.borrowed_to_owned*100, r.savings_ratio]);
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
  LAST.loans = r.rows; showExport("loans");
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
  try{
    const r = await api("POST","/risk",{
      name:document.getElementById("riskName").value||"This customer",
      income:+document.getElementById("riskIncome").value||null, emi:+document.getElementById("riskEmi").value||null,
      score:+document.getElementById("riskScore").value,
    });
    out.className = `result-box ${r.band}`;
    out.textContent = `${r.name}: ${r.level}`;
    document.getElementById("riskInsightText").textContent = r.insight;
    box.style.display = "block";
  }catch(e){ out.className="result-box"; out.textContent = "Error: "+e.message; box.style.display="none"; }
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
      { label:"Projected corpus", data:r.schedule.map(y=>y.projected_corpus), borderColor:"#1F3A68", backgroundColor:"rgba(31,58,104,.12)", fill:true, tension:.25, pointRadius:2 },
      { label:"Inflation-adjusted target", data:r.schedule.map(y=>y.target), borderColor:"#B9840E", borderDash:[6,4], pointRadius:0 },
    ]);
    document.getElementById("goalInsightText").textContent = r.insight;
    document.getElementById("goalInsight").style.display = "block";
    LAST.goals = { inputs: readInputs({"Goal":"goalName", "Target amount today (Rs)":"goalTarget", "Years":"goalYears", "Current savings (Rs)":"goalCurrent",
                                       "Expected return (%/yr)":"goalReturn", "Inflation (%/yr)":"goalInflation", "Monthly income (Rs)":"goalIncome"}), r };
    showExport("goals");
  }catch(e){
    showExport("goals", false);
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
  const list = document.getElementById("kcList");
  try{
    const r = await api("GET","/knowledge/glossary");
    let group = null, groupEl = null;
    r.glossary.forEach(item=>{
      indexGlossaryItem(item);
      if(item.group !== group){
        group = item.group;
        groupEl = document.createElement("div");
        groupEl.className = "kc-group";
        groupEl.innerHTML = `<h3 class="kc-title">${escapeHtml(group)}</h3>`;
        list.appendChild(groupEl);
      }
      const el = document.createElement("div");
      el.className = "acc-item";
      el.dataset.term = item.term;
      el.dataset.text = (item.q+" "+item.a+" "+(item.example||"")+" "+(item.also||[]).join(" ")).toLowerCase();
      el.innerHTML = `<button class="acc-q"><span>${escapeHtml(item.q)}</span><span class="chev">+</span></button>` +
        `<div class="acc-a"><p>${escapeHtml(item.a)}</p>` +
        (item.example ? `<p><b>Example:</b> ${escapeHtml(item.example)}</p>` : "") +
        (item.where ? `<p class="muted"><b>Where in FinSuite:</b> ${escapeHtml(item.where)}</p>` : "") + `</div>`;
      el.querySelector(".acc-q").addEventListener("click", ()=> el.classList.toggle("open"));
      groupEl.appendChild(el);
    });
    const empty = document.createElement("div");
    empty.className = "muted"; empty.hidden = true; empty.textContent = "No matching term. Try a different word.";
    list.appendChild(empty);
    document.getElementById("kcSearch").addEventListener("input", e=>{
      const q = e.target.value.trim().toLowerCase();
      let shown = 0;
      list.querySelectorAll(".kc-group").forEach(g=>{
        let any = false;
        g.querySelectorAll(".acc-item").forEach(it=>{
          const hit = !q || it.dataset.text.includes(q);
          it.hidden = !hit; any = any || hit; if(hit) shown++;
          if(q && hit) it.classList.add("open"); else if(!q) it.classList.remove("open");
        });
        g.hidden = !any;
      });
      empty.hidden = shown > 0;
    });
  }catch(e){ list.textContent = "Could not load the Knowledge Center: "+e.message; }
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
      (q.asOf ? `<div class="muted" style="margin-top:4px;">Last trade: ${new Date(q.asOf).toLocaleString()}</div>` : "");
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
    const prices = document.getElementById("sipPrices").value.split(",").map(s=>s.trim()).filter(s=>s!=="").map(Number);
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
    box.innerHTML = `Position in range: <b>${r.range_position_pct.toFixed(1)}%</b><br>From 52w high: <b class="badge-warn">${r.from_high_pct.toFixed(2)}%</b><br>From 52w low: <b class="${r.from_low_pct>=0?'badge-good':'badge-warn'}">${r.from_low_pct>=0?"+":""}${r.from_low_pct.toFixed(2)}%</b>`;
  }catch(e){ box.textContent = "Error: "+e.message; }
}

/* ============================================================
   14 WATCHLIST & PRICE ALERTS (reuses GET /market/quote)
   The watchlist is saved in this browser and, when logged in, in the
   account (PUT /user/data/watchlist). Guest alerts live in this browser and
   are checked while FinSuite is open; a logged-in user's alerts are stored
   on the server (/alerts) and also checked in the background with email.
   Each alert fires once, then waits to be re-armed.
   ============================================================ */
const WATCHLIST = LS.get("fs-watchlist", []).map(symbol=>({symbol, price:null, change:null, changePercent:null, day:null}));
let ALERTS = AUTH.token ? [] : LS.get("fs-alerts", []);
function saveWatchlist(){
  const symbols = WATCHLIST.map(w=>w.symbol);
  LS.set("fs-watchlist", symbols);
  if(AUTH.user) api("PUT","/user/data/watchlist",{value:symbols}).catch(()=>{});
}
function saveLocalAlerts(){ if(!AUTH.user) LS.set("fs-alerts", ALERTS); }
function addWatchlistSymbol(picked){
  const symbol = (picked || document.getElementById("wlSymbol").value).trim();
  if(!symbol){ document.querySelector("#wlPicker .picker-btn").click(); return; }
  if(!WATCHLIST.some(w=>w.symbol===symbol)){ WATCHLIST.push({symbol, price:null, change:null, changePercent:null, day:null}); saveWatchlist(); }
  renderWatchlist(); refreshAlertSymbolSelect(); refreshWatchlist();
}
function removeWatchlistSymbol(i){ WATCHLIST.splice(i,1); saveWatchlist(); renderWatchlist(); refreshAlertSymbolSelect(); }
function renderWatchlist(){
  const table = document.getElementById("wlTable");
  table.innerHTML = `<tr><th>Symbol</th><th>Price</th><th>Change</th><th>%</th><th>As of</th><th></th></tr>` +
    (WATCHLIST.length ? WATCHLIST.map((w,i)=>`<tr><td><b>${escapeHtml(w.symbol)}</b>${w.name?`<div class="muted" style="margin:0;font-size:12px;">${escapeHtml(w.name)}</div>`:""}</td><td>${w.price??"—"}</td><td>${w.change??"—"}</td><td>${w.changePercent??"—"}</td><td>${w.day??"—"}</td><td><button class="btn secondary sm" onclick="removeWatchlistSymbol(${i})">Remove</button></td></tr>`).join("")
      : `<tr><td colspan="6" class="muted">Your watchlist is empty. Choose a company above to add it.</td></tr>`);
}
async function refreshWatchlist(){
  for(const w of WATCHLIST){
    try{
      const q = await api("GET", `/market/quote?symbol=${encodeURIComponent(w.symbol)}`);
      if(q && q.price!=null) Object.assign(w, { name:q.name, currency:q.currency, price:q.price, change:q.change, changePercent:q.changePercent, day:q.asOf?new Date(q.asOf).toLocaleString():"" });
      else w.price = "no data";
    }catch(e){ w.price = "Error"; }
  }
  renderWatchlist();
  checkAlerts();
}
function refreshAlertSymbolSelect(){
  const sel = document.getElementById("alertSymbol");
  sel.innerHTML = WATCHLIST.map(w=>`<option value="${escapeHtml(w.symbol)}">${escapeHtml(w.symbol)}</option>`).join("") || `<option value="">Add a symbol to the watchlist first</option>`;
}
async function addPriceAlert(){
  const symbol = document.getElementById("alertSymbol").value;
  if(!symbol){ alert("Add a symbol to the watchlist first."); return; }
  const a = { symbol, type:document.getElementById("alertType").value, price:+document.getElementById("alertPrice").value };
  if(!(a.price > 0)){ alert("Enter a target price above 0."); return; }
  if(AUTH.user){
    try{ ALERTS.push(await api("POST","/alerts",a)); }catch(e){ alert(e.message); return; }
  }else{
    ALERTS.push({ ...a, id:"l"+Date.now(), triggered_at:null, triggered_price:null });
    saveLocalAlerts();
  }
  renderAlerts();
  checkAlerts();
}
async function removePriceAlert(i){
  const a = ALERTS[i];
  if(AUTH.user && typeof a.id === "number") await api("DELETE", `/alerts/${a.id}`).catch(()=>{});
  ALERTS.splice(i,1); saveLocalAlerts(); renderAlerts();
}
async function rearmAlert(i){
  const a = ALERTS[i];
  if(AUTH.user && typeof a.id === "number") await api("POST", `/alerts/${a.id}/rearm`).catch(()=>{});
  Object.assign(a, { triggered_at:null, triggered_price:null, seen:0 });
  saveLocalAlerts(); renderAlerts(); checkAlerts();
}
function renderAlerts(){
  const table = document.getElementById("alertTable");
  const cur = sym => currencySymbol((WATCHLIST.find(x=>x.symbol===sym)||{}).currency || "INR");
  table.innerHTML = `<tr><th>Symbol</th><th>Condition</th><th>Status</th><th></th></tr>` +
    (ALERTS.length ? ALERTS.map((a,i)=>`<tr><td>${escapeHtml(a.symbol)}</td><td>${a.type==="above"?"Rises above":"Falls below"} ${cur(a.symbol)}${a.price}</td>` +
      `<td>${a.triggered_at ? `<b class="badge-warn">Triggered</b> at ${cur(a.symbol)}${a.triggered_price} · ${new Date(a.triggered_at).toLocaleString()}` : "Watching"}</td>` +
      `<td>${a.triggered_at?`<button class="btn secondary sm" onclick="rearmAlert(${i})">Re-arm</button> `:""}<button class="btn secondary sm" onclick="removePriceAlert(${i})">Remove</button></td></tr>`).join("")
      : `<tr><td colspan="4" class="muted">No alerts yet.</td></tr>`);
}
function renderAlertMode(){
  const box = document.getElementById("alertMode");
  if(AUTH.user){
    box.innerHTML = `<span class="lbl">Background alerts are on</span>Your alerts are saved to your account and checked on the server every few minutes, even when FinSuite is closed. ` +
      (AUTH.emailDelivery ? (AUTH.user.email_alerts ? `When one fires, we email <b>${escapeHtml(AUTH.user.email)}</b>.` : `Email is switched off in your account settings.`)
                          : `Email delivery is not set up on this server yet, so fired alerts are shown here the next time you open FinSuite.`);
  }else{
    box.innerHTML = `<span class="lbl">Alerts while this page is open</span>Your alerts are saved in this browser and checked about once a minute while FinSuite is open. ` +
      `<button class="btn link" onclick="openAccount()">Log in or create an account</button> to have them checked in the background and emailed to you.`;
  }
  const nb = document.getElementById("notifyBtn");
  if(!("Notification" in window)) nb.hidden = true;
  else if(Notification.permission === "granted"){ nb.textContent = "Desktop notifications on"; nb.disabled = true; }
}
function enableNotifications(){
  if(!("Notification" in window)) return;
  Notification.requestPermission().then(()=>renderAlertMode());
}
function notifyAlert(a){
  const word = a.type==="above" ? "rose above" : "fell below";
  const msg = `${a.symbol} ${word} ${a.price} (now ${a.triggered_price}).`;
  toast("Price alert: " + msg, "warn");
  try{ if("Notification" in window && Notification.permission === "granted") new Notification("FinSuite price alert", { body: msg }); }catch(e){}
}
// Replace the alert list with the server's copy; announce fired alerts not seen yet.
function mergeServerAlerts(list){
  ALERTS = list;
  const fresh = list.filter(a=>a.triggered_at && !a.seen);
  fresh.forEach(a=>{ notifyAlert(a); a.seen = 1; });
  if(fresh.length) api("POST","/alerts/seen").catch(()=>{});
  renderAlerts();
}
async function checkAlerts(){
  if(AUTH.user){
    if(!ALERTS.some(a=>!a.triggered_at)) return;
    try{ mergeServerAlerts((await api("POST","/alerts/check")).alerts); }catch(e){}
    return;
  }
  let changed = false;
  ALERTS.forEach(a=>{
    const w = WATCHLIST.find(x=>x.symbol===a.symbol);
    if(a.triggered_at || !w || typeof w.price !== "number") return;
    if(a.type==="above" ? w.price > a.price : w.price < a.price){
      Object.assign(a, { triggered_at:new Date().toISOString(), triggered_price:w.price });
      notifyAlert(a); changed = true;
    }
  });
  if(changed) saveLocalAlerts();
  renderAlerts();
}
// Used while other tabs are open: fetch prices only for symbols with a pending alert.
async function checkAlertsNow(){
  const pending = ALERTS.filter(a=>!a.triggered_at);
  if(!pending.length) return;
  if(!AUTH.user){
    for(const sym of new Set(pending.map(a=>a.symbol))){
      const w = WATCHLIST.find(x=>x.symbol===sym);
      if(!w) continue;
      try{ const q = await api("GET", `/market/quote?symbol=${encodeURIComponent(sym)}`); if(q.price!=null) Object.assign(w, {price:q.price, currency:q.currency, name:q.name}); }catch(e){}
    }
  }
  checkAlerts();
}
refreshAlertSymbolSelect();

/* ============================================================
   16 ABOUT -> GET /about
   ============================================================ */
(async function loadAbout(){
  try{
    const r = await api("GET","/about");
    document.getElementById("aboutOut").innerHTML = `
      <div class="result-box">${r.about_text}</div>
      <div class="card" style="margin-top:12px;background:rgba(31,58,104,.06);">
        <h3 style="margin-top:0;">Why this matters</h3>
        <p style="margin:0;">${r.why_it_matters}</p>
      </div>
      <div class="row" style="margin-top:12px;">
        <div class="field"><label>Version</label><div>${r.version}</div></div>
      </div>`;
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
  { panel:"tracker",   toggle:"pfAuto",    every:60*1000,   run:()=>HOLDINGS.length && valuePortfolio(true), last:0 },
  // Alerts are also checked while any other tab is open.
  { panel:null,        toggle:null,        every:60*1000,   run:()=>!document.getElementById("panel-watchlist").classList.contains("active") && checkAlertsNow(), last:Date.now() },
];
function runAutoRefresh(force=false){
  if(document.hidden) return;
  const now = Date.now();
  for(const job of AUTO_JOBS){
    if(job.panel){
      const panel = document.getElementById("panel-"+job.panel);
      const toggle = document.getElementById(job.toggle);
      if(!panel || !panel.classList.contains("active") || !toggle || !toggle.checked) continue;
    }
    if(force || now - job.last >= job.every){ job.last = now; job.run(); }
  }
}
setInterval(runAutoRefresh, 5000);
document.addEventListener("visibilitychange", ()=>runAutoRefresh());

/* ============================================================
   COMPANY PICKER — dropdown of popular stocks with a search box that
   finds any listed company via GET /market/search.
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

/* Dropdown with a search box inside: the closed state shows the selected
   company; opening it focuses a search field above the list. With the
   field empty the list shows POPULAR; typing filters it and adds live
   GET /market/search results for every other listed company. */
function attachSymbolPicker(pickerId, hiddenInputId, onPick){
  const root = document.getElementById(pickerId), hidden = document.getElementById(hiddenInputId);
  const btn = root.querySelector(".picker-btn"), panel = root.querySelector(".picker-panel");
  const search = root.querySelector(".picker-search input"), list = root.querySelector(".picker-list");
  let timer = null, items = [], sections = [], active = -1, seq = 0;
  const norm = s=>s.toLowerCase().replace(/[^a-z0-9]/g,"");

  const render = (secs, note="")=>{
    sections = secs;
    items = secs.flatMap(s=>s.rows);
    let i = 0;
    list.innerHTML = secs.filter(s=>s.rows.length).map(s=>
      `<div class="suggest-group">${escapeHtml(s.group)}</div>` +
      s.rows.map(r=>{ const k = i++; return `<div class="suggest-item${k===active?" active":""}${r.symbol===hidden.value?" selected":""}" data-i="${k}"><span class="sym">${escapeHtml(r.symbol)}</span><span class="nm">${escapeHtml(r.name)}</span><span class="exch">${escapeHtml(r.exchange)}${r.type && r.type!=="EQUITY"?" · "+escapeHtml(r.type):""}</span></div>`; }).join("")
    ).join("") + (note ? `<div class="suggest-empty">${note}</div>` : "");
    const el = list.querySelector(".suggest-item.active"); if(el) el.scrollIntoView({block:"nearest"});
  };
  const open = ()=>{
    panel.hidden = false; root.classList.add("open");
    search.value = ""; active = -1; render(POPULAR);
    search.focus();
  };
  const close = ()=>{ panel.hidden = true; root.classList.remove("open"); clearTimeout(timer); };
  const pick = (symbol, name)=>{
    hidden.value = symbol;
    setPickerLabel(pickerId, name || symbol, name ? symbol : "");
    close(); btn.focus();
    onPick(symbol);
  };

  btn.addEventListener("click", ()=> panel.hidden ? open() : close());
  btn.addEventListener("keydown", e=>{ if(e.key==="ArrowDown"){ e.preventDefault(); open(); } });
  document.addEventListener("mousedown", e=>{ if(!panel.hidden && !root.contains(e.target)) close(); });

  search.addEventListener("input", ()=>{
    clearTimeout(timer);
    const q = search.value.trim();
    active = -1;
    if(!q){ render(POPULAR); return; }
    const n = norm(q);
    const local = POPULAR.flatMap(s=>s.rows).filter(r=>norm(r.name).includes(n) || norm(r.symbol).startsWith(n)).slice(0,6);
    render([{group:"Popular", rows:local}], "Searching all listed companies…");
    timer = setTimeout(async ()=>{
      const my = ++seq;
      try{
        const r = await api("GET", `/market/search?q=${encodeURIComponent(q)}`);
        if(my !== seq || panel.hidden) return;                       // a newer keystroke won
        const seen = new Set(local.map(x=>x.symbol));
        const more = (r.results||[]).filter(x=>!seen.has(x.symbol));
        render([{group:"Popular", rows:local}, {group:"All markets", rows:more}],
               local.length || more.length ? "" : `No company found for “${escapeHtml(q)}”. Check the spelling, or press Enter to try it as a ticker.`);
      }catch(e){ if(my === seq) render(sections.slice(0,1), "Search is unavailable right now — press Enter to try it as a ticker."); }
    }, 250);
  });
  search.addEventListener("keydown", e=>{
    if(e.key === "ArrowDown" && items.length){ active = (active+1) % items.length; render(sections); e.preventDefault(); }
    else if(e.key === "ArrowUp" && items.length){ active = (active-1+items.length) % items.length; render(sections); e.preventDefault(); }
    else if(e.key === "Enter"){
      e.preventDefault();
      const v = search.value.trim();
      if(items.length && (active >= 0 || v)){ const r = items[Math.max(active,0)]; pick(r.symbol, r.name); }
      else if(v) pick(v);                                  // backend resolves names/tickers itself
    }
    else if(e.key === "Escape"){ close(); btn.focus(); }
  });
  list.addEventListener("mousedown", e=>{ e.preventDefault(); const el = e.target.closest(".suggest-item"); if(el){ const r = items[+el.dataset.i]; pick(r.symbol, r.name); } });
}
function setPickerLabel(pickerId, name, symbol){
  const root = document.getElementById(pickerId);
  root.querySelector(".picker-label").textContent = name;
  root.querySelector(".picker-sym").textContent = symbol || "";
}

function selectMarketSymbol(symbol){
  document.getElementById("marketSymbol").value = symbol;
  document.getElementById("newsSymbols").value = symbol;
  AUTO_JOBS.forEach(j=>{ if(j.panel==="market") j.last = Date.now(); });   // we're refreshing right now
  getQuote(); getDailyHistory(); getNews();
}
attachSymbolPicker("marketPicker", "marketSymbol", selectMarketSymbol);
attachSymbolPicker("wlPicker", "wlSymbol", symbol=>addWatchlistSymbol(symbol));
document.getElementById("historyPeriod").addEventListener("change", getDailyHistory);

/* ============================================================
   17 ML PRICE PREDICTION -> GET /ml/predict
   ============================================================ */
let MLSEQ = 0;
async function runPrediction(){
  const my = ++MLSEQ;
  const status = document.getElementById("mlStatus"), btn = document.getElementById("mlRun");
  const symbol = document.getElementById("mlSymbol").value.trim();
  if(!symbol){ status.textContent = "Choose a company above."; return; }
  status.textContent = "Fetching history and training models… (can take up to a minute)";
  btn.disabled = true;
  ["mlStats","mlVerdict","mlNews"].forEach(id=>document.getElementById(id).style.display="none");
  try{
    const d = await api("GET", `/ml/predict?symbol=${encodeURIComponent(symbol)}&period=${document.getElementById("mlPeriod").value}`);
    if(my !== MLSEQ) return;
    const cur = currencySymbol(d.currency), fmt = v => cur + v.toLocaleString(d.currency==="INR"?"en-IN":"en-US", {minimumFractionDigits:2, maximumFractionDigits:2});
    const f = d.forecast, m = d.metrics, names = {linear:"Linear Regression", random_forest:"Random Forest"};
    const arrow = p => `<span class="${p>=0?'badge-good':'badge-warn'}">${p>=0?"▲ +":"▼ "}${p.toFixed(2)}%</span>`;
    status.innerHTML = `<b>${escapeHtml(d.name)}</b> <span class="muted">(${escapeHtml(d.yahooSymbol)})</span> · trained on ${d.data.train} days, tested on the latest ${d.data.test} days (${d.data.days} trading days downloaded)`;
    const stats = document.getElementById("mlStats");
    stats.style.display = "flex";
    stats.innerHTML = `
      <div class="stat">Last close (${fmtDate(f.last_date)})<b>${fmt(f.last_close)}</b></div>
      <div class="stat">Linear Regression → next day<b>${fmt(f.linear)}</b>${arrow(f.linear_change_pct)}</div>
      <div class="stat">Random Forest → next day<b>${fmt(f.random_forest)}</b>${arrow(f.random_forest_change_pct)}</div>`;
    const order = [["naive","Naive: tomorrow = today"],["linear",names.linear],["random_forest",names.random_forest]];
    document.getElementById("mlTable").innerHTML =
      `<tr><th>Model</th><th class="num">MAE (${escapeHtml(d.currency||"")})</th><th class="num">RMSE</th><th class="num">MAPE %</th></tr>` +
      order.map(([k,label])=>`<tr><td>${k===d.best_model?"<b>"+label+" ★</b>":label}</td><td class="num">${m[k].mae.toLocaleString()}</td><td class="num">${m[k].rmse.toLocaleString()}</td><td class="num">${m[k].mape.toFixed(2)}%</td></tr>`).join("");
    const gain = ((m.naive.mae - m[d.best_model].mae) / m.naive.mae * 100);
    document.getElementById("mlVerdictText").textContent = d.beats_baseline
      ? `${names[d.best_model]} was the most accurate on unseen days, about ${gain.toFixed(1)}% closer than simply assuming tomorrow equals today.`
      : `Neither model beat the naive "tomorrow = today" guess on unseen days (best: ${names[d.best_model]}, ${Math.abs(gain).toFixed(1)}% ${gain<0?"worse":"better"}). That is common — day-to-day prices are very hard to predict — so treat the forecast above as a rough guide, not a signal.`;
    document.getElementById("mlVerdict").style.display = "block";
    document.getElementById("mlChartBox").hidden = false;
    lineChart("mlChart","ml", d.test.dates, [
      { label:"Actual close", data:d.test.actual, borderColor:"#1F3A68", borderWidth:2, pointRadius:0, tension:.1 },
      { label:"Linear Regression", data:d.test.linear, borderColor:"#B9840E", borderWidth:1.5, pointRadius:0, tension:.1 },
      { label:"Random Forest", data:d.test.random_forest, borderColor:"#7A4CC2", borderWidth:1.5, borderDash:[5,3], pointRadius:0, tension:.1 },
    ]);
    document.getElementById("mlNote").hidden = false;
    showNewsMood(d, my);
  }catch(e){
    if(my !== MLSEQ) return;
    status.textContent = "Error: " + e.message;
    document.getElementById("mlChartBox").hidden = true; document.getElementById("mlNote").hidden = true;
    document.getElementById("mlTable").innerHTML = "";
  }finally{ if(my === MLSEQ) btn.disabled = false; }
}
attachSymbolPicker("mlPicker", "mlSymbol", ()=>runPrediction());

/* ============================================================
   SHARED HELPERS (phase 2)
   ============================================================ */
const LAST = {};   // latest result of each tool, used by the download buttons
const rupees = v => v==null || isNaN(v) ? "—" : "₹" + Math.round(v).toLocaleString("en-IN");
const pct = (v, d=2) => v==null || isNaN(v) ? "—" : `${(+v).toFixed(d)}%`;
const signed = (v, f=rupees) => v==null ? "—" : (v>=0 ? "+" : "−") + f(Math.abs(v));
const val = id => +document.getElementById(id).value || 0;
function readInputs(map){ return Object.entries(map).map(([label,id])=>[label, document.getElementById(id).value]); }
function showExport(key, on=true){ const el = document.getElementById("export-"+key); if(el) el.hidden = !on; }
function toast(msg, kind=""){
  const el = document.createElement("div");
  el.className = "toast " + kind; el.textContent = msg;
  document.getElementById("toasts").appendChild(el);
  setTimeout(()=>el.remove(), 8000);
}
function showError(id, e){ const el = document.getElementById(id); el.hidden = !e; if(e){ el.className = "result-box sell"; el.textContent = "Error: " + (e.message||e); } }
function setHidden(ids, hidden){ ids.forEach(id=>{ const el = document.getElementById(id); if(el) el.hidden = hidden; }); }

/* ============================================================
   ⓘ TOOLTIPS linked to the Knowledge Center
   ============================================================ */
const GMAP = {};
function indexGlossaryItem(item){
  const m = item.term.match(/^(.*?)\s*\((.*)\)\s*$/);
  [item.term, ...(m ? [m[1], m[2]] : []), ...(item.also||[])].forEach(k=>{
    k = k.toLowerCase().trim();
    if(k && !GMAP[k]) GMAP[k] = item;
  });
}
function findTerm(t){
  const k = t.toLowerCase().trim();
  if(GMAP[k]) return GMAP[k];
  const hit = Object.keys(GMAP).find(x=>x.startsWith(k));
  return hit ? GMAP[hit] : null;
}
function showInfo(el){
  const pop = document.getElementById("infoPop");
  const item = findTerm(el.dataset.term);
  pop.innerHTML = `<button class="x" aria-label="Close" onclick="hideInfo()">×</button>` + (item
    ? `<h4>${escapeHtml(item.q)}</h4><p>${escapeHtml(item.a)}</p>${item.example?`<p class="meta"><b>Example:</b> ${escapeHtml(item.example)}</p>`:""}` +
      `<button class="btn link" style="padding:0;" onclick="openKnowledge('${escapeHtml(item.term).replace(/'/g,"\\'")}')">Open in Knowledge Center →</button>`
    : `<h4>${escapeHtml(el.dataset.term)}</h4><p class="muted">Loading the Knowledge Center… try again in a moment.</p>`);
  pop.hidden = false;
  const r = el.getBoundingClientRect();
  const w = Math.min(340, window.innerWidth - 24);
  pop.style.top = (r.bottom + window.scrollY + 6) + "px";
  pop.style.left = Math.max(12, Math.min(r.left + window.scrollX - 10, window.scrollX + window.innerWidth - w - 12)) + "px";
  pop.dataset.for = el.dataset.term;
}
function hideInfo(){ document.getElementById("infoPop").hidden = true; }
function openKnowledge(term){
  hideInfo();
  showTab("knowledge");
  const search = document.getElementById("kcSearch");
  if(search.value){ search.value = ""; search.dispatchEvent(new Event("input")); }
  const el = [...document.querySelectorAll(".acc-item")].find(x=>x.dataset.term === term);
  if(!el) return;
  el.classList.add("open", "flash");
  setTimeout(()=>{ el.scrollIntoView({block:"center", behavior:"smooth"}); }, 50);
  setTimeout(()=>el.classList.remove("flash"), 2200);
}
document.addEventListener("click", e=>{
  const icon = e.target.closest(".info");
  if(icon){
    e.preventDefault(); e.stopPropagation();          // don't toggle a checkbox or focus an input
    const pop = document.getElementById("infoPop");
    if(!pop.hidden && pop.dataset.for === icon.dataset.term) hideInfo(); else showInfo(icon);
    return;
  }
  if(!e.target.closest("#infoPop")) hideInfo();
}, true);
document.addEventListener("keydown", e=>{
  if((e.key==="Enter" || e.key===" ") && e.target.classList && e.target.classList.contains("info")){ e.preventDefault(); showInfo(e.target); }
  if(e.key==="Escape") hideInfo();
});

/* ============================================================
   DOWNLOADS — PDF (jsPDF + AutoTable) and Excel (SheetJS), built in the
   browser from the latest result. Libraries load on first use only.
   ============================================================ */
const LIBS = {
  pdf: ["https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js",
        "https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.8.2/jspdf.plugin.autotable.min.js"],
  xlsx: ["https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"],
};
const LOADED = {};
function loadScript(url){
  return LOADED[url] ||= new Promise((ok, fail)=>{
    const s = document.createElement("script");
    s.src = url; s.onload = ok; s.onerror = ()=>{ delete LOADED[url]; fail(new Error("Could not load the download library. Check your internet connection.")); };
    document.head.appendChild(s);
  });
}
const r2 = v => v==null ? null : Math.round(v*100)/100;
const EXPORTS = {
  report(){ const {inputs, r} = LAST.report; return {
    title:"Personal Finance Report", file:"FinSuite_Finance_Report", meta: inputs,
    sections:[{ name:"Results", head:["Measure","Value"], rows:[["Net profit (Rs)", r2(r.net_profit)], ["ROE (%)", r2(r.roe)], ["ROA (%)", r2(r.roa)],
      ["Current ratio", r2(r.current_ratio)], ["Debt to equity", r2(r.debt_to_equity)]] }],
    notes: r.tips }; },
  goals(){ const {inputs, r} = LAST.goals; return {
    title:"Goal Plan", file:"FinSuite_Goal_Plan", meta: inputs,
    sections:[{ name:"Summary", head:["Measure","Value (Rs)"], rows:[["Future value needed", Math.round(r.future_value_goal)], ["Monthly SIP", Math.round(r.monthly_sip)],
        ["Total invested", Math.round(r.total_invested)], ["Projected gain", Math.round(r.gain)]] },
      { name:"Year by year", head:["Year","Projected corpus (Rs)","Inflation-adjusted target (Rs)"], rows: r.schedule.map(y=>[r2(y.year), y.projected_corpus, y.target]) }],
    notes:[r.insight], charts:["goalChart"] }; },
  loans(){ const cols = ["customer_name","income","loan_amount","emi","credit_score","ai_insight","ai_recommendation"]; return {
    title:"Loan Screening", file:"FinSuite_Loan_Table",
    sections:[{ name:"Customers", head:["Customer","Income (Rs/mo)","Loan amount (Rs)","EMI (Rs/mo)","Credit score","Insight","Recommendation"],
      rows: LAST.loans.map(r=>cols.map(c=>r[c] ?? "")) }] }; },
  incometax(){ const {inputs, r} = LAST.incometax; const n = r.new, o = r.old;
    const line = (l,k)=>[l, Math.round(n[k]), Math.round(o[k])];
    const slabs = (x)=> x.slabs.map(s=>[`${Math.round(s.from).toLocaleString("en-IN")} to ${s.to==null?"above":Math.round(s.to).toLocaleString("en-IN")}`, s.rate, Math.round(s.amount), Math.round(s.tax)]);
    return { title:"Income Tax: Old vs New Regime (FY 2025-26)", file:"FinSuite_Income_Tax", meta: inputs,
      sections:[{ name:"Comparison", head:["", "New regime (Rs)", "Old regime (Rs)"], rows:[line("Gross income","gross_income"), line("Standard deduction","standard_deduction"),
          line("Deductions","deductions"), line("Taxable income","taxable_income"), line("Tax on slabs","tax_on_slabs"), line("Rebate 87A","rebate"),
          line("Surcharge","surcharge"), line("Cess 4%","cess"), line("Total tax","total_tax"), ["Effective rate (%)", r2(n.effective_rate), r2(o.effective_rate)],
          line("Monthly take-home","monthly_take_home")] },
        { name:"New regime slabs", head:["Income band (Rs)","Rate %","Amount (Rs)","Tax (Rs)"], rows: slabs(n) },
        { name:"Old regime slabs", head:["Income band (Rs)","Rate %","Amount (Rs)","Tax (Rs)"], rows: slabs(o) }],
      notes:[r.insight, "Simplified estimate for normal income; not tax advice."], charts:["itChart"] }; },
  emi(){ const {inputs, r} = LAST.emi; const p = r.prepayment;
    const yr = list => list.map(y=>[y.year, Math.round(y.emi), Math.round(y.principal), Math.round(y.interest), Math.round(y.prepayment), Math.round(y.balance)]);
    const mo = list => list.map(m=>[m.month, r2(m.emi), r2(m.principal), r2(m.interest), r2(m.prepayment), r2(m.balance)]);
    const head = ["Year","EMI paid (Rs)","Principal (Rs)","Interest (Rs)","Prepaid (Rs)","Balance (Rs)"];
    const summary = [["Monthly EMI", Math.round(r.emi)], ["Total interest", Math.round(r.total_interest)], ["Total payment", Math.round(r.total_payment)], ["Months", r.months]];
    if(p) summary.push(["Interest with prepayment", Math.round(p.total_interest)], ["Interest saved", Math.round(p.interest_saved)], ["Months saved", p.months_saved]);
    const sections = [{ name:"Summary", head:["Measure","Value"], rows: summary }, { name:"Yearly schedule", head, rows: yr(r.yearly) }];
    if(p) sections.push({ name:"Yearly with prepayment", head, rows: yr(p.yearly) });
    sections.push({ name:"Monthly schedule", head:["Month", ...head.slice(1)], rows: mo(r.schedule), excelOnly:true });
    if(p) sections.push({ name:"Monthly with prepayment", head:["Month", ...head.slice(1)], rows: mo(p.schedule), excelOnly:true });
    return { title:"Loan EMI and Repayment Table", file:"FinSuite_Loan_EMI", meta: inputs, sections, notes:[r.insight], charts:["emiChart"] }; },
  budget(){ const r = LAST.budget; return {
    title:"Budget Plan (50/30/20)", file:"FinSuite_Budget", meta:[["Monthly income (Rs)", r.income]],
    sections:[{ name:"Buckets", head:["Bucket","Target %","Target (Rs)","Actual (Rs)","Actual %","On track"], rows: r.buckets.map(b=>[b.label, b.target_pct, Math.round(b.target), Math.round(b.actual), r2(b.actual_pct), b.on_track?"Yes":"No"]) },
      { name:"Items", head:["Category","Type","Amount (Rs)"], rows: r.items.map(i=>[i.category, i.kind, i.amount]) }],
    notes: r.tips, charts:["budPie","budBar"] }; },
  tracker(){ const r = LAST.tracker; return {
    title:"Portfolio Tracker", file:"FinSuite_Portfolio",
    sections:[{ name:"Summary", head:["Measure","Value (Rs)"], rows:[["Invested", Math.round(r.invested)], ["Current value", Math.round(r.value)], ["Profit / loss", Math.round(r.pnl)],
        ["Profit / loss %", r2(r.pnl_pct)], ["Today's change", Math.round(r.day_change)]] },
      { name:"Holdings", head:["Symbol","Name","Qty","Avg price","Price","Currency","Invested","Value","P/L","P/L %","Weight %"],
        rows: r.rows.map(x=>[x.yahooSymbol||x.symbol, x.name||"", x.qty, x.avg_price, x.price??"", x.currency||"", r2(x.invested), r2(x.value), r2(x.pnl), r2(x.pnl_pct), r2(x.weight_pct)]) }],
    notes:[r.insight, "Prices from Yahoo Finance; may be delayed."], charts:["pfPie"] }; },
  fire(){ const {inputs, r} = LAST.fire; return {
    title:"Retirement & FIRE Plan", file:"FinSuite_Retirement_Plan", meta: inputs,
    sections:[{ name:"Summary", head:["Measure","Value"], rows:[["Corpus needed at retirement (Rs)", Math.round(r.corpus_needed)], ["FIRE number (Rs)", Math.round(r.fire_number)],
        ["Projected corpus (Rs)", Math.round(r.projected_corpus)], ["Monthly SIP needed (Rs)", Math.round(r.required_sip)], ["Monthly expenses at retirement (Rs)", Math.round(r.expense_at_retirement)],
        ["Financial independence age", r.fi_age==null?"Not reached":r2(r.fi_age)], ["Money runs out at age", r.money_runs_out_age ?? "Lasts the whole plan"]] },
      { name:"By age", head:["Age","Corpus (Rs)"], rows: r.schedule.map(x=>[x.age, x.corpus]) }],
    notes:[r.insight], charts:["fiChart"] }; },
  mf(){ const {inputs, r} = LAST.mf; return {
    title:"Mutual Fund SIP Returns", file:"FinSuite_SIP_Returns", meta:[["Fund", r.scheme_name], ["Scheme code", r.scheme_code], ...inputs],
    sections:[{ name:"Summary", head:["Measure","Value"], rows:[["Instalments", r.installments], ["Invested (Rs)", Math.round(r.invested)], ["Value (Rs)", Math.round(r.value)],
        ["Gain (Rs)", Math.round(r.gain)], ["XIRR (%/yr)", r2(r.xirr)], ["Same money as a lump sum (Rs)", Math.round(r.lump_sum_value)], ["Latest NAV", r.latest_nav], ["NAV date", r.nav_date]] },
      { name:"Instalments", head:["Date","NAV","Total invested (Rs)","Value (Rs)"], rows: r.series.map(x=>[x.date, x.nav, x.invested, x.value]) }],
    notes:[r.insight, "Past returns do not guarantee future returns."], charts:["mfSipChart"] }; },
};
const pdfText = s => String(s ?? "").replace(/₹/g,"Rs ").replace(/[–—−]/g,"-").replace(/→/g,"->").replace(/▲/g,"+").replace(/▼/g,"-").replace(/[^\x00-\xFF]/g,"");
const fmtCell = v => typeof v === "number" ? v.toLocaleString("en-IN", {maximumFractionDigits:2}) : pdfText(v);
function chartImage(id){
  const c = document.getElementById(id);
  if(!c || !CHARTS[Object.keys(CHARTS).find(k=>CHARTS[k].canvas===c)] || !c.width) return null;
  const tmp = document.createElement("canvas"); tmp.width = c.width; tmp.height = c.height;
  const ctx = tmp.getContext("2d"); ctx.fillStyle = "#fff"; ctx.fillRect(0,0,tmp.width,tmp.height); ctx.drawImage(c,0,0);
  return { url: tmp.toDataURL("image/png"), ratio: c.height / c.width };
}
async function exportPDF(spec){
  for(const u of LIBS.pdf) await loadScript(u);
  const doc = new window.jspdf.jsPDF({unit:"pt", format:"a4"});
  const W = doc.internal.pageSize.getWidth(), H = doc.internal.pageSize.getHeight(), M = 40;
  let y = M;
  doc.setFillColor(15,34,64); doc.rect(0,0,W,56,"F"); doc.setFillColor(156,122,60); doc.rect(0,56,W,3,"F");
  doc.setTextColor(255); doc.setFontSize(16); doc.text("FinSuite", M, 35);
  doc.setFontSize(10); doc.text(new Date().toLocaleString("en-IN"), W-M, 35, {align:"right"});
  doc.setTextColor(20); doc.setFontSize(15); y = 84; doc.text(pdfText(spec.title), M, y); y += 16;
  const table = (head, body) => { doc.autoTable({ startY:y, head:[head.map(pdfText)], body: body.map(r=>r.map(fmtCell)), margin:{left:M, right:M},
    styles:{fontSize:8.5, cellPadding:4}, headStyles:{fillColor:[31,58,104]}, theme:"grid" }); y = doc.lastAutoTable.finalY + 14; };
  const heading = t => { if(y > H-80){ doc.addPage(); y = M; } doc.setFontSize(11.5); doc.setTextColor(19,34,74); doc.text(pdfText(t), M, y+4); doc.setTextColor(20); y += 12; };
  if(spec.meta && spec.meta.length){ heading("Inputs"); table(["Input","Value"], spec.meta); }
  for(const sec of spec.sections){ if(sec.excelOnly) continue; heading(sec.name); table(sec.head, sec.rows); }
  if(spec.notes && spec.notes.length){
    heading("Notes"); doc.setFontSize(9.5);
    for(const n of spec.notes){ const lines = doc.splitTextToSize("• " + pdfText(n), W-2*M); if(y + lines.length*12 > H-M){ doc.addPage(); y = M; } doc.text(lines, M, y+6); y += lines.length*12 + 4; }
    y += 6;
  }
  for(const id of spec.charts||[]){
    const img = chartImage(id); if(!img) continue;
    const w = W-2*M, h = w*img.ratio;
    if(y + h > H-M){ doc.addPage(); y = M; }
    doc.addImage(img.url, "PNG", M, y, w, h); y += h + 12;
  }
  const pages = doc.getNumberOfPages();
  for(let i=1;i<=pages;i++){ doc.setPage(i); doc.setFontSize(8); doc.setTextColor(120);
    doc.text("FinSuite - educational tool, not financial advice.", M, H-18); doc.text(`Page ${i} of ${pages}`, W-M, H-18, {align:"right"}); }
  doc.save(spec.file + ".pdf");
}
async function exportExcel(spec){
  await loadScript(LIBS.xlsx[0]);
  const wb = XLSX.utils.book_new(), used = new Set();
  const name = n => { let b = n.replace(/[\\/?*[\]:]/g,"").slice(0,31) || "Sheet", k = b, i = 2; while(used.has(k)) k = b.slice(0,28) + " " + i++; used.add(k); return k; };
  const summary = [[spec.title], ["Generated", new Date().toLocaleString("en-IN")], []];
  if(spec.meta && spec.meta.length) summary.push(["Input","Value"], ...spec.meta.map(([k,v])=>[k, isNaN(+v) || v==="" ? v : +v]), []);
  if(spec.notes && spec.notes.length) summary.push(["Notes"], ...spec.notes.map(n=>[n]));
  summary.push([], ["FinSuite - educational tool, not financial advice."]);
  const ws = XLSX.utils.aoa_to_sheet(summary); ws["!cols"] = [{wch:34},{wch:22}];
  XLSX.utils.book_append_sheet(wb, ws, name("Overview"));
  for(const sec of spec.sections){
    const sh = XLSX.utils.aoa_to_sheet([sec.head, ...sec.rows]);
    sh["!cols"] = sec.head.map((h,i)=>({wch: Math.min(60, Math.max(String(h).length, ...sec.rows.slice(0,50).map(r=>String(r[i]??"").length)) + 2)}));
    XLSX.utils.book_append_sheet(wb, sh, name(sec.name));
  }
  XLSX.writeFile(wb, spec.file + ".xlsx");
}
async function doExport(key, kind){
  if(!LAST[key]){ toast("Run the calculation first, then download."); return; }
  try{
    const spec = EXPORTS[key]();
    await (kind === "pdf" ? exportPDF(spec) : exportExcel(spec));
  }catch(e){ toast("Download failed: " + e.message, "warn"); }
}

/* ============================================================
   ACCOUNT — log in, saved data and alerts follow the user
   ============================================================ */
let AUTH_MODE = "login";
function openAccount(){ renderAccount(); document.getElementById("accountModal").hidden = false; setTimeout(()=>{ const f = document.querySelector(AUTH.user ? "#accountEmailAlerts" : "#authEmail"); f && f.focus(); }, 30); }
function closeAccount(){ document.getElementById("accountModal").hidden = true; }
document.getElementById("accountModal").addEventListener("mousedown", e=>{ if(e.target.id === "accountModal") closeAccount(); });
document.addEventListener("keydown", e=>{ if(e.key==="Escape") closeAccount(); });
function setAuthMode(mode){
  AUTH_MODE = mode;
  document.getElementById("segLogin").classList.toggle("on", mode==="login");
  document.getElementById("segRegister").classList.toggle("on", mode==="register");
  document.getElementById("authNameField").hidden = mode !== "register";
  document.getElementById("authSubmit").textContent = mode==="login" ? "Log in" : "Create account";
  document.getElementById("authPassword").autocomplete = mode==="login" ? "current-password" : "new-password";
  document.getElementById("authError").textContent = "";
}
function renderAccount(){
  const u = AUTH.user;
  document.getElementById("accountGuest").hidden = !!u;
  document.getElementById("accountUser").hidden = !u;
  document.getElementById("accountLabel").textContent = u ? u.name : "Log in";
  if(u){
    document.getElementById("accountName").textContent = u.name;
    document.getElementById("accountEmail").textContent = u.email;
    document.getElementById("accountEmailAlerts").checked = u.email_alerts;
    document.getElementById("accountEmailNote").textContent = AUTH.emailDelivery ? "" : "Note: email sending is not set up on this server yet; fired alerts show in the app instead.";
  }
  renderAlertMode();
}
async function submitAuth(e){
  e.preventDefault();
  const err = document.getElementById("authError"), btn = document.getElementById("authSubmit");
  err.textContent = ""; btn.disabled = true;
  try{
    const body = { email: document.getElementById("authEmail").value, password: document.getElementById("authPassword").value };
    if(AUTH_MODE === "register") body.name = document.getElementById("authName").value;
    const r = await api("POST", AUTH_MODE==="login" ? "/auth/login" : "/auth/register", body);
    AUTH.token = r.token; LS.set("fs-token", r.token);
    await startSession(r.user, true);
    document.getElementById("authPassword").value = "";
    closeAccount();
    toast(`Welcome${AUTH_MODE==="register"?"":" back"}, ${r.user.name}! Your watchlist, portfolio and alerts are now saved to your account.`);
  }catch(ex){ err.textContent = ex.message; }
  finally{ btn.disabled = false; }
}
async function logout(){
  await api("POST","/auth/logout").catch(()=>{});
  AUTH.token = null; AUTH.user = null; LS.del("fs-token");
  ALERTS = LS.get("fs-alerts", []);
  renderAlerts(); renderAccount(); closeAccount();
  toast("Logged out. Your watchlist and portfolio stay saved in this browser.");
}
async function saveEmailAlerts(){
  try{ AUTH.user = (await api("PATCH","/auth/me",{email_alerts: document.getElementById("accountEmailAlerts").checked})).user; renderAccount(); }catch(e){ toast(e.message, "warn"); }
}
// After login (fresh) or on page load with a saved session: bring local and account data together.
async function startSession(user, fresh){
  AUTH.user = user;
  try{
    const me = await api("GET","/auth/me"); AUTH.user = me.user; AUTH.emailDelivery = me.email_delivery;
    const data = await api("GET","/user/data");
    const serverWl = data.watchlist ? data.watchlist.value : null;
    const localWl = WATCHLIST.map(w=>w.symbol);
    const merged = fresh || !serverWl ? [...new Set([...(serverWl||[]), ...localWl])] : serverWl;
    WATCHLIST.splice(0, WATCHLIST.length, ...merged.map(symbol=>WATCHLIST.find(w=>w.symbol===symbol) || {symbol, price:null, change:null, changePercent:null, day:null}));
    saveWatchlist();
    if(data.portfolio && data.portfolio.value && data.portfolio.value.length){
      HOLDINGS.splice(0, HOLDINGS.length, ...data.portfolio.value); LS.set("fs-portfolio", HOLDINGS);
    }else if(HOLDINGS.length) saveHoldings();
    // move alerts made before logging in into the account
    const local = LS.get("fs-alerts", []).filter(a=>!a.triggered_at);
    for(const a of local) await api("POST","/alerts",{symbol:a.symbol, type:a.type, price:a.price}).catch(()=>{});
    if(local.length) LS.del("fs-alerts");
    mergeServerAlerts((await api("GET","/alerts")).alerts);
  }catch(e){
    if(/log in/i.test(e.message)){ AUTH.token = null; AUTH.user = null; LS.del("fs-token"); ALERTS = LS.get("fs-alerts", []); }
  }
  renderWatchlist(); refreshAlertSymbolSelect(); renderAlerts(); renderHoldings(); renderAccount();
}

/* ============================================================
   11 STOCK MARKET — technical indicators on the history chart
   ============================================================ */
let INDSEQ = 0;
const indOn = k => document.querySelector(`#indicatorChips input[data-ind="${k}"]`).checked;
async function drawHistoryChart(){
  if(!HISTORY) return;
  const my = ++INDSEQ;
  const {rows, ticker} = HISTORY;
  const closeSet = (labels, data)=>({ label:`${ticker} close`, data, borderColor:"#1F3A68", backgroundColor:"rgba(31,58,104,.10)", fill:!indOn("bb"), tension:.15, pointRadius:0, borderWidth:2 });
  const any = ["sma20","sma50","ema20","bb","rsi"].some(indOn);
  if(!any){
    lineChart("historyChart","history", rows.map(r=>r.Date), [closeSet(null, rows.map(r=>r.Close))]);
    setHidden(["rsiChartBox","indicatorSignals"], true); destroyChart("rsi");
    return;
  }
  if(!CHARTS.history) lineChart("historyChart","history", rows.map(r=>r.Date), [closeSet(null, rows.map(r=>r.Close))]);
  try{
    const d = await api("GET", `/market/indicators?symbol=${encodeURIComponent(ticker)}&period=${document.getElementById("historyPeriod").value}`);
    if(my !== INDSEQ) return;
    const line = (label, data, color, extra={}) => ({ label, data, borderColor:color, borderWidth:1.4, pointRadius:0, tension:.15, fill:false, spanGaps:true, ...extra });
    const sets = [closeSet(null, d.close)];
    if(indOn("sma20")) sets.push(line("SMA 20", d.sma20, "#B9840E"));
    if(indOn("sma50")) sets.push(line("SMA 50", d.sma50, "#7A4CC2"));
    if(indOn("ema20")) sets.push(line("EMA 20", d.ema20, "#2C6FB0", {borderDash:[5,3]}));
    if(indOn("bb")){
      sets.push(line("Bollinger upper", d.bb_upper, "#8A94A8", {borderDash:[3,3]}));
      sets.push(line("Bollinger lower", d.bb_lower, "#8A94A8", {borderDash:[3,3], fill:"-1", backgroundColor:"rgba(138,148,168,.12)"}));
    }
    lineChart("historyChart","history", d.dates, sets);
    const rsiBox = document.getElementById("rsiChartBox");
    rsiBox.hidden = !indOn("rsi");
    if(indOn("rsi")){
      lineChart("rsiChart","rsi", d.dates, [
        line("RSI 14", d.rsi14, "#C2477A", {borderWidth:1.6}),
        line("70 overbought", d.dates.map(()=>70), "#C43D3D", {borderDash:[4,4], borderWidth:1}),
        line("30 oversold", d.dates.map(()=>30), "#1F9D6B", {borderDash:[4,4], borderWidth:1}),
      ], {y:{min:0, max:100}});
    }else destroyChart("rsi");
    document.getElementById("indicatorSignals").hidden = false;
    document.getElementById("indicatorSignalsText").innerHTML = d.signals.map(t=>`<div style="margin-top:4px;">• ${escapeHtml(t)}</div>`).join("");
  }catch(e){
    if(my !== INDSEQ) return;
    document.getElementById("indicatorSignals").hidden = false;
    document.getElementById("indicatorSignalsText").textContent = "Indicators unavailable: " + e.message;
  }
}
document.querySelectorAll("#indicatorChips input").forEach(i=>i.addEventListener("change", ()=>{ LS.set("fs-ind", [...document.querySelectorAll("#indicatorChips input")].filter(x=>x.checked).map(x=>x.dataset.ind)); drawHistoryChart(); }));
(function restoreIndicators(){
  const saved = LS.get("fs-ind");
  if(saved) document.querySelectorAll("#indicatorChips input").forEach(i=>i.checked = saved.includes(i.dataset.ind));
})();

/* ============================================================
   17 ML PREDICTION — news mood next to the forecast
   ============================================================ */
async function showNewsMood(d, my){
  const box = document.getElementById("mlNews"), text = document.getElementById("mlNewsText");
  try{
    const n = await api("GET", `/market/news?symbols=${encodeURIComponent(d.yahooSymbol)}&limit=10`);
    if(my !== MLSEQ) return;
    const s = n.summary, total = s.positive + s.neutral + s.negative;
    if(!total){ box.style.display = "none"; return; }
    const best = d.best_model === "random_forest" ? "random_forest" : "linear";
    const change = d.forecast[best + "_change_pct"];
    const up = change >= 0, mood = s.mood;
    const name = best === "linear" ? "Linear Regression" : "Random Forest";
    let verdict;
    if(mood === "positive" && up || mood === "negative" && !up) verdict = "News and the model point the same way. That is some comfort, but neither is a guarantee.";
    else if(mood === "positive" || mood === "negative") verdict = "News and the model disagree, so be extra careful with this forecast. The model only sees past prices, not news.";
    else verdict = "The news gives no clear direction, so it neither supports nor contradicts the forecast.";
    text.innerHTML = `Last 7 days of headlines: <span class="badge positive">${s.positive} positive</span> <span class="badge neutral">${s.neutral} neutral</span> <span class="badge negative">${s.negative} negative</span> (mood: <b>${escapeHtml(mood)}</b>). ` +
      `The ${name} forecast points <b class="${up?"badge-good":"badge-warn"}">${up?"up":"down"} ${Math.abs(change).toFixed(2)}%</b>. ${verdict} ` +
      `<button class="btn link" onclick="document.getElementById('newsSymbols').value='${escapeHtml(d.yahooSymbol)}';showTab('market');getNews()">See the headlines →</button>`;
    box.style.display = "block";
  }catch(e){ if(my === MLSEQ) box.style.display = "none"; }
}

/* ============================================================
   18 INCOME TAX -> POST /tax/income
   ============================================================ */
async function calcIncomeTax(){
  const out = document.getElementById("itOut");
  try{
    const r = await api("POST","/tax/income",{
      gross_income: val("itIncome"), salaried: document.getElementById("itSalaried").value==="1", age_group: document.getElementById("itAge").value,
      sec80c: val("it80c"), sec80d: val("it80d"), nps_80ccd1b: val("itNps"), home_loan_interest: val("itHome"), hra_exemption: val("itHra"), other_deductions: val("itOther"),
    });
    const n = r.new, o = r.old;
    const win = r.better === "same" ? "Both regimes cost about the same" : `The <b>${r.better} regime</b> saves you <b>${rupees(r.savings)}</b> a year`;
    const row = (label, k, f=rupees, cls="") => `<tr><td>${label}</td><td class="num ${cls}">${f(n[k])}</td><td class="num ${cls}">${f(o[k])}</td></tr>`;
    const slabTable = x => `<table><tr><th>Income band</th><th class="num">Rate</th><th class="num">Tax</th></tr>` +
      x.slabs.map(s=>`<tr><td>${rupees(s.from)} – ${s.to==null?"above":rupees(s.to)}</td><td class="num">${s.rate}%</td><td class="num">${rupees(s.tax)}</td></tr>`).join("") + `</table>`;
    out.innerHTML = `
      <div class="result-box ${r.better==="same"?"hold":"buy"}" style="font-size:15px;">${win}.</div>
      <div class="stat-strip">
        <div class="stat">New regime tax<b>${rupees(n.total_tax)}</b></div>
        <div class="stat">Old regime tax<b>${rupees(o.total_tax)}</b></div>
        <div class="stat">You save<b class="badge-good">${rupees(r.savings)}/yr</b></div>
        <div class="stat">Old regime wins only above<b>${r.break_even_deductions==null?"never":rupees(r.break_even_deductions)}</b><span class="meta">of deductions</span></div>
      </div>
      <div class="table-wrap"><table>
        <tr><th></th><th class="num">New regime</th><th class="num">Old regime</th></tr>
        ${row("Gross income","gross_income")}${row("Standard deduction","standard_deduction")}${row("Deductions (80C, 80D, HRA…)","deductions")}
        ${row("<b>Taxable income</b>","taxable_income")}${row("Tax on slabs","tax_on_slabs")}${row(`Rebate 87A<span class="info" data-term="Tax rebate" tabindex="0" role="button"></span>`,"rebate")}
        ${row(`Surcharge<span class="info" data-term="Surcharge" tabindex="0" role="button"></span>`,"surcharge")}${row("Health &amp; education cess 4%","cess")}
        ${row("<b>Total tax</b>","total_tax", v=>`<b>${rupees(v)}</b>`)}${row(`Effective tax rate<span class="info" data-term="Effective tax rate" tabindex="0" role="button"></span>`,"effective_rate", v=>pct(v))}
        ${row("Monthly take-home after tax","monthly_take_home")}
      </table></div>
      <details><summary>Show slab-by-slab working</summary><div class="grid-2" style="margin-top:8px;"><div><div class="sub">New regime</div>${slabTable(n)}</div><div><div class="sub">Old regime</div>${slabTable(o)}</div></div></details>
      <div class="chart-box short"><canvas id="itChart"></canvas></div>
      <div class="insight-box"><span class="lbl">Insight</span>${escapeHtml(r.insight)}</div>`;
    barChart("itChart","incometax", ["New regime","Old regime"], [Math.round(n.total_tax), Math.round(o.total_tax)], {color:["#1F3A68","#B9840E"]});
    LAST.incometax = { inputs: readInputs({"Annual gross income (Rs)":"itIncome", "Age group":"itAge", "Salaried (1 = yes)":"itSalaried", "80C (Rs)":"it80c", "80D (Rs)":"it80d",
      "NPS 80CCD(1B) (Rs)":"itNps", "Home loan interest (Rs)":"itHome", "HRA exemption (Rs)":"itHra", "Other deductions (Rs)":"itOther"}), r };
    showExport("incometax");
  }catch(e){ out.innerHTML = `<div class="result-box sell">Error: ${escapeHtml(e.message)}</div>`; showExport("incometax", false); }
}

/* ============================================================
   19 LOAN EMI -> POST /loans/emi
   ============================================================ */
async function calcEmi(){
  try{
    const r = await api("POST","/loans/emi",{
      principal: val("emiPrincipal"), annual_rate: val("emiRate"), tenure_months: Math.round(val("emiYears")*12),
      prepay_amount: val("emiPrepay"), prepay_month: Math.round(val("emiPrepayMonth")), extra_monthly: val("emiExtra"),
    });
    showError("emiError", null);
    const p = r.prepayment;
    const st = document.getElementById("emiStats");
    st.innerHTML = `<div class="stat">Monthly EMI<b>${rupees(r.emi)}</b></div>
      <div class="stat">Total interest<b>${rupees(r.total_interest)}</b></div>
      <div class="stat">Total you pay<b>${rupees(r.total_payment)}</b></div>` +
      (p ? `<div class="stat">Interest saved by prepaying<b class="badge-good">${rupees(p.interest_saved)}</b></div>
            <div class="stat">Loan ends early by<b class="badge-good">${Math.floor(p.months_saved/12)} yr ${p.months_saved%12} mo</b></div>` : "");
    document.getElementById("emiInsightText").textContent = r.insight;
    setHidden(["emiStats","emiInsight","emiChartBox","emiTableWrap"], false);
    const years = r.yearly.map(y=>`Yr ${y.year}`);
    const sets = [{ label:"Balance without prepayment", data:r.yearly.map(y=>Math.round(y.balance)), borderColor:"#B9840E", pointRadius:2, tension:.2 }];
    if(p) sets.push({ label:"Balance with prepayment", data:r.yearly.map((_,i)=>p.yearly[i] ? Math.round(p.yearly[i].balance) : 0), borderColor:"#1F3A68", backgroundColor:"rgba(31,58,104,.12)", fill:true, pointRadius:2, tension:.2 });
    lineChart("emiChart","emi", years, sets, {y:{beginAtZero:true}});
    document.getElementById("emiPlan").hidden = !p;
    LAST.emi = { inputs: readInputs({"Loan amount (Rs)":"emiPrincipal", "Interest rate (%/yr)":"emiRate", "Tenure (years)":"emiYears",
      "One-time prepayment (Rs)":"emiPrepay", "Prepayment month":"emiPrepayMonth", "Extra every month (Rs)":"emiExtra"}), r };
    renderEmiTable();
    showExport("emi");
  }catch(e){ showError("emiError", e); setHidden(["emiStats","emiInsight","emiChartBox","emiTableWrap"], true); showExport("emi", false); }
}
function renderEmiTable(){
  if(!LAST.emi) return;
  const r = LAST.emi.r, usePre = r.prepayment && document.getElementById("emiPlan").value === "pre";
  const plan = usePre ? r.prepayment : r, monthly = document.getElementById("emiView").value === "monthly";
  const rows = monthly ? plan.schedule : plan.yearly;
  document.getElementById("emiTable").innerHTML =
    `<tr><th>${monthly?"Month":"Year"}</th><th class="num">EMI paid</th><th class="num">Principal</th><th class="num">Interest</th><th class="num">Prepaid</th><th class="num">Balance</th></tr>` +
    rows.map(x=>`<tr><td>${monthly?x.month:x.year}</td><td class="num">${rupees(x.emi)}</td><td class="num">${rupees(x.principal)}</td><td class="num">${rupees(x.interest)}</td><td class="num">${x.prepayment?rupees(x.prepayment):"—"}</td><td class="num">${rupees(x.balance)}</td></tr>`).join("");
}

/* ============================================================
   20 BUDGET PLANNER -> POST /budget
   ============================================================ */
const BUDGET_EXAMPLE = [
  {category:"Rent", amount:20000, kind:"need"}, {category:"Groceries", amount:8000, kind:"need"}, {category:"Electricity, phone & internet", amount:4000, kind:"need"},
  {category:"Transport", amount:3000, kind:"need"}, {category:"Loan EMI", amount:6000, kind:"need"}, {category:"Dining out & movies", amount:6000, kind:"want"},
  {category:"Shopping", amount:5000, kind:"want"}, {category:"Subscriptions", amount:1000, kind:"want"}, {category:"SIP / investments", amount:12000, kind:"saving"},
];
let BUDGET = LS.get("fs-budget", null) || BUDGET_EXAMPLE.map(x=>({...x}));
function saveBudget(){ LS.set("fs-budget", BUDGET); }
function renderBudgetItems(){
  document.getElementById("budItems").innerHTML = BUDGET.map((it,i)=>`<div class="list-row">
      <input type="text" value="${escapeHtml(it.category)}" aria-label="Category" oninput="BUDGET[${i}].category=this.value;saveBudget()">
      <input type="number" value="${it.amount}" aria-label="Amount" oninput="BUDGET[${i}].amount=+this.value||0;saveBudget()">
      <select aria-label="Type" onchange="BUDGET[${i}].kind=this.value;saveBudget()">${["need","want","saving"].map(k=>`<option value="${k}"${k===it.kind?" selected":""}>${k==="need"?"Need":k==="want"?"Want":"Saving"}</option>`).join("")}</select>
      <button class="btn secondary sm x" onclick="BUDGET.splice(${i},1);saveBudget();renderBudgetItems()" aria-label="Remove">✕</button></div>`).join("");
}
function addBudgetItem(){ BUDGET.push({category:"New item", amount:0, kind:"want"}); saveBudget(); renderBudgetItems(); }
function resetBudget(){ BUDGET = BUDGET_EXAMPLE.map(x=>({...x})); saveBudget(); renderBudgetItems(); }
async function calcBudget(){
  try{
    const r = await api("POST","/budget",{income: val("budIncome"), items: BUDGET.map(x=>({category:x.category||"Item", amount:+x.amount||0, kind:x.kind}))});
    showError("budError", null);
    document.getElementById("budOut").hidden = false;
    document.getElementById("budBuckets").innerHTML = r.buckets.map(b=>`<div class="bucket">
        <div class="bucket-head"><b>${escapeHtml(b.label)}</b><span>${rupees(b.actual)} (${b.actual_pct.toFixed(0)}%) · guide ${b.target_pct}% = ${rupees(b.target)} ${b.on_track?'<span class="badge-good">✓ on track</span>':'<span class="badge-warn">✗ off track</span>'}</span></div>
        <div class="progress-track"><div class="progress-fill ${b.on_track?"buy":"sell"}" style="width:${Math.min(b.actual/b.target*100,100)}%"></div></div></div>`).join("") +
      (r.leftover > 0 ? `<p class="meta" style="margin-top:8px;">${rupees(r.leftover)} is not assigned to anything, so it counts as savings.</p>` : "");
    doughnutChart("budPie","budpie", r.items.map(i=>i.category), r.items.map(i=>i.amount));
    barChart("budBar","budbar", r.buckets.map(b=>b.label.replace(" & debt repayment","")), null, { datasets:[
      { label:"50/30/20 guide", data:r.buckets.map(b=>Math.round(b.target)), backgroundColor:"rgba(138,148,168,.55)", borderRadius:5, maxBarThickness:40 },
      { label:"Your plan", data:r.buckets.map(b=>Math.round(b.actual)), backgroundColor:r.buckets.map(b=>b.on_track?"#1F9D6B":"#C43D3D"), borderRadius:5, maxBarThickness:40 } ]});
    document.getElementById("budTips").innerHTML = r.tips.map(t=>`<div style="margin-top:5px;">• ${escapeHtml(t)}</div>`).join("");
    LAST.budget = r; showExport("budget");
  }catch(e){ showError("budError", e); document.getElementById("budOut").hidden = true; showExport("budget", false); }
}

/* ============================================================
   21 MUTUAL FUNDS & SIP -> GET /mf/search, /mf/nav, POST /mf/sip
   ============================================================ */
let MF_FUND = null, MF_RESULTS = [];
async function searchFunds(){
  const q = document.getElementById("mfQuery").value.trim(), out = document.getElementById("mfResults");
  if(q.length < 2){ out.innerHTML = `<div class="muted">Type at least 2 letters of a fund name.</div>`; return; }
  out.innerHTML = `<div class="muted">Searching AMFI data…</div>`;
  try{
    MF_RESULTS = (await api("GET", `/mf/search?q=${encodeURIComponent(q)}&limit=12`)).results;
    out.innerHTML = MF_RESULTS.length ? MF_RESULTS.map((f,i)=>`<div class="fund-item${MF_FUND&&MF_FUND.code===f.code?" sel":""}" onclick="selectFund(${i})"><div class="nm">${escapeHtml(f.name)}</div>
        <div class="meta">NAV ₹${f.nav.toLocaleString("en-IN")} on ${escapeHtml(f.date)} · ${escapeHtml(f.category)} · ${escapeHtml(f.fund_house)} · code ${f.code}</div></div>`).join("")
      : `<div class="muted">No fund found for “${escapeHtml(q)}”. Try fewer words, e.g. “hdfc flexi”.</div>`;
  }catch(e){ out.innerHTML = `<div class="result-box sell">Error: ${escapeHtml(e.message)}</div>`; }
}
document.getElementById("mfQuery").addEventListener("keydown", e=>{ if(e.key==="Enter") searchFunds(); });
async function selectFund(i){
  MF_FUND = MF_RESULTS[i];
  document.querySelectorAll(".fund-item").forEach((el,k)=>el.classList.toggle("sel", k===i));
  document.getElementById("mfFundCard").hidden = false;
  document.getElementById("mfFundName").textContent = MF_FUND.name;
  document.getElementById("mfFundMeta").textContent = `${MF_FUND.fund_house} · ${MF_FUND.category} · latest NAV ₹${MF_FUND.nav} (${MF_FUND.date})`;
  setHidden(["mfSipStats","mfSipChartBox","mfSipInsight","mfSipError"], true); showExport("mf", false);
  document.getElementById("mfReturns").innerHTML = `<div class="stat">Loading NAV history…</div>`;
  try{
    const d = await api("GET", `/mf/nav?code=${MF_FUND.code}&years=5`);
    if(MF_FUND.code !== d.meta.scheme_code && String(MF_FUND.code) !== String(d.meta.scheme_code)) return;
    const ret = d.fund_returns;
    document.getElementById("mfReturns").innerHTML = ["1y","3y","5y"].map(k=>`<div class="stat">${k.replace("y"," year")} return (a year)<b class="${ret[k]==null?"":ret[k]>=0?"badge-good":"badge-warn"}">${ret[k]==null?"—":pct(ret[k],1)}</b></div>`).join("");
    lineChart("mfNavChart","mfnav", d.dates, [{ label:"NAV (₹)", data:d.nav, borderColor:"#1F3A68", backgroundColor:"rgba(31,58,104,.10)", fill:true, pointRadius:0, borderWidth:2, tension:.1 }]);
    document.getElementById("mfFundCard").scrollIntoView({behavior:"smooth", block:"start"});
  }catch(e){ document.getElementById("mfReturns").innerHTML = `<div class="stat">Could not load history: ${escapeHtml(e.message)}</div>`; }
}
async function calcFundSip(){
  if(!MF_FUND) return;
  try{
    const end = document.getElementById("mfEnd").value;
    const r = await api("POST","/mf/sip",{ code: MF_FUND.code, monthly: val("mfMonthly"), start: document.getElementById("mfStart").value, ...(end?{end}:{}) });
    showError("mfSipError", null);
    document.getElementById("mfSipStats").innerHTML = `
      <div class="stat">Invested (${r.installments} months)<b>${rupees(r.invested)}</b></div>
      <div class="stat">Value on ${new Date(r.nav_date).toLocaleDateString("en-IN")}<b>${rupees(r.value)}</b></div>
      <div class="stat">Gain<b class="${r.gain>=0?"badge-good":"badge-warn"}">${signed(r.gain)} (${pct(r.gain_pct,1)})</b></div>
      <div class="stat">XIRR (a year)<b>${r.xirr==null?"—":pct(r.xirr,1)}</b></div>
      <div class="stat">Same money as a lump sum<b>${rupees(r.lump_sum_value)}</b></div>`;
    lineChart("mfSipChart","mfsip", r.series.map(x=>x.date), [
      { label:"Value of your SIP", data:r.series.map(x=>x.value), borderColor:"#1F3A68", backgroundColor:"rgba(31,58,104,.12)", fill:true, pointRadius:0, borderWidth:2, tension:.15 },
      { label:"Money put in", data:r.series.map(x=>x.invested), borderColor:"#B9840E", borderDash:[6,4], pointRadius:0, borderWidth:1.5 },
    ]);
    document.getElementById("mfSipInsightText").textContent = r.insight;
    setHidden(["mfSipStats","mfSipChartBox","mfSipInsight"], false);
    LAST.mf = { inputs: readInputs({"Monthly SIP (Rs)":"mfMonthly", "Start date":"mfStart", "End date":"mfEnd"}), r };
    showExport("mf");
  }catch(e){ showError("mfSipError", e); setHidden(["mfSipStats","mfSipChartBox","mfSipInsight"], true); showExport("mf", false); }
}

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

/* ============================================================
   23 RETIREMENT & FIRE -> POST /goals/fire
   ============================================================ */
async function calcFire(){
  try{
    const r = await api("POST","/goals/fire",{
      current_age: val("fiAge"), retire_age: val("fiRetire"), life_expectancy: val("fiLife"), monthly_expenses: val("fiExpenses"),
      current_corpus: val("fiCorpus"), monthly_investment: val("fiMonthly"), inflation: val("fiInflation"),
      return_pre: val("fiPre"), return_post: val("fiPost"), withdrawal_rate: val("fiSwr"),
    });
    showError("fiError", null);
    const ok = r.gap <= 0;
    document.getElementById("fiStats").innerHTML = `
      <div class="stat">Needed at age ${val("fiRetire")}<b>${rupees(r.corpus_needed)}</b></div>
      <div class="stat">You are on course for<b class="${ok?"badge-good":"badge-warn"}">${rupees(r.projected_corpus)}</b></div>
      <div class="stat">Monthly SIP needed<b>${rupees(r.required_sip)}</b></div>
      <div class="stat">FIRE number (${val("fiSwr")}% rule)<b>${rupees(r.fire_number)}</b></div>
      <div class="stat">Financially independent at<b>${r.fi_age==null?"not before 100":"age "+r.fi_age.toFixed(1)}</b></div>
      <div class="stat">Money lasts until<b class="${r.money_runs_out_age?"badge-warn":"badge-good"}">${r.money_runs_out_age?"age "+r.money_runs_out_age:"beyond age "+val("fiLife")}</b></div>`;
    lineChart("fiChart","fire", r.schedule.map(x=>x.age), [
      { label:"Your money (current plan)", data:r.schedule.map(x=>x.corpus), borderColor:"#1F3A68", backgroundColor:"rgba(31,58,104,.12)", fill:true, pointRadius:0, tension:.2 },
      { label:"Needed at retirement", data:r.schedule.map(x=>x.age<=val("fiRetire")?Math.round(r.corpus_needed):null), borderColor:"#B9840E", borderDash:[6,4], pointRadius:0 },
    ], {y:{beginAtZero:true}});
    CHARTS.fire.options.scales.x.title = {display:true, text:"Age", color:themeColors().muted}; CHARTS.fire.update();
    document.getElementById("fiInsightText").textContent = r.insight;
    setHidden(["fiStats","fiChartBox","fiInsight"], false);
    LAST.fire = { inputs: readInputs({"Current age":"fiAge", "Retirement age":"fiRetire", "Plan until age":"fiLife", "Monthly expenses today (Rs)":"fiExpenses",
      "Savings invested (Rs)":"fiCorpus", "Investing every month (Rs)":"fiMonthly", "Inflation (%/yr)":"fiInflation", "Return before retiring (%/yr)":"fiPre",
      "Return after retiring (%/yr)":"fiPost", "Withdrawal rate (%)":"fiSwr"}), r };
    showExport("fire");
  }catch(e){ showError("fiError", e); setHidden(["fiStats","fiChartBox","fiInsight"], true); showExport("fire", false); }
}

/* ============================================================
   24 CURRENCY & COMPARE -> GET /market/fx, /market/compare
   ============================================================ */
const FX_LIST = ["INR","USD","EUR","GBP","JPY","AED","SGD","AUD","CAD","CHF","CNY","HKD","KRW","SAR"];
(function fillFx(){
  const opts = FX_LIST.map(c=>`<option value="${c}">${c}</option>`).join("");
  document.getElementById("fxFrom").innerHTML = opts; document.getElementById("fxTo").innerHTML = opts;
  document.getElementById("fxFrom").value = "USD"; document.getElementById("fxTo").value = "INR";
  ["fxFrom","fxTo"].forEach(id=>document.getElementById(id).addEventListener("change", convertFx));
  document.getElementById("fxAmount").addEventListener("keydown", e=>{ if(e.key==="Enter") convertFx(); });
})();
function swapFx(){ const a = document.getElementById("fxFrom"), b = document.getElementById("fxTo"); [a.value, b.value] = [b.value, a.value]; convertFx(); }
let FX_SEQ = 0;
async function convertFx(){
  const my = ++FX_SEQ, box = document.getElementById("fxResult");
  const from = document.getElementById("fxFrom").value, to = document.getElementById("fxTo").value, amount = val("fxAmount");
  box.textContent = "Fetching live rate…";
  try{
    const r = await api("GET", `/market/fx?base=${from}&quote=${to}&amount=${amount}`);
    if(my !== FX_SEQ) return;
    const n = (v, d=4) => (+v).toLocaleString("en-IN", {maximumFractionDigits:d});
    box.innerHTML = `<span style="font-size:18px;"><b>${n(amount,2)} ${from} = ${n(r.converted, 2)} ${to}</b></span><br>1 ${from} = ${n(r.rate)} ${to} · 1 ${to} = ${n(r.inverse, 6)} ${from}` +
      (r.changePercent!=null ? ` · today <span class="${r.change>=0?"badge-good":"badge-warn"}">${r.change>=0?"+":""}${r.changePercent}%</span>` : "") +
      (r.asOf ? `<div class="muted" style="margin:4px 0 0;">Rate as of ${new Date(r.asOf).toLocaleString()}</div>` : "");
    const box2 = document.getElementById("fxChartBox");
    box2.hidden = !r.history;
    if(r.history) lineChart("fxChart","fx", r.history.map(x=>x.Date), [{ label:`1 ${from} in ${to} (last 3 months)`, data:r.history.map(x=>x.Close), borderColor:"#2C6FB0", backgroundColor:"rgba(44,111,176,.1)", fill:true, pointRadius:0, borderWidth:2, tension:.15 }]);
  }catch(e){ if(my === FX_SEQ) box.textContent = "Error: " + e.message; }
}
let CMP_SEQ = 0;
async function compareStocks(){
  const my = ++CMP_SEQ, status = document.getElementById("cmpStatus");
  const a = document.getElementById("cmpA").value, b = document.getElementById("cmpB").value;
  status.hidden = false; status.className = "result-box"; status.textContent = "Fetching both price histories…";
  try{
    const r = await api("GET", `/market/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}&period=${document.getElementById("cmpPeriod").value}`);
    if(my !== CMP_SEQ) return;
    status.hidden = true;
    document.getElementById("cmpChartBox").hidden = false;
    lineChart("cmpChart","cmp", r.dates, [
      { label:`${r.a.name} (${r.a.symbol})`, data:r.a.rebased, borderColor:"#1F3A68", pointRadius:0, borderWidth:2, tension:.1 },
      { label:`${r.b.name} (${r.b.symbol})`, data:r.b.rebased, borderColor:"#B9840E", pointRadius:0, borderWidth:2, tension:.1 },
    ]);
    const cls = v => v>=0 ? "badge-good" : "badge-warn";
    const row = (label, k, f=v=>pct(v), c=null) => `<tr><td>${label}</td><td class="num ${c?c(r.a[k]):""}">${f(r.a[k], r.a)}</td><td class="num ${c?c(r.b[k]):""}">${f(r.b[k], r.b)}</td></tr>`;
    const price = (v, s) => currencySymbol(s.currency) + (+v).toLocaleString("en-IN",{maximumFractionDigits:2});
    document.getElementById("cmpTable").innerHTML = `<tr><th></th><th class="num">${escapeHtml(r.a.name)}</th><th class="num">${escapeHtml(r.b.name)}</th></tr>` +
      row("Return over period","return_pct",v=>pct(v),cls) + row(`Volatility (a year)<span class="info" data-term="Volatility" tabindex="0" role="button"></span>`,"volatility_pct") +
      row(`Max drawdown<span class="info" data-term="Maximum drawdown" tabindex="0" role="button"></span>`,"max_drawdown_pct",v=>pct(v),()=> "badge-warn") +
      row("Best day","best_day_pct",v=>pct(v),cls) + row("Worst day","worst_day_pct",v=>pct(v),cls) + row("Start price","start",price) + row("Latest price","end",price) +
      `<tr><td>Correlation of daily moves</td><td class="num" colspan="2" style="text-align:center;">${r.correlation ?? "—"}</td></tr>`;
    document.getElementById("cmpInsightText").textContent = r.summary;
    document.getElementById("cmpInsight").hidden = false;
  }catch(e){ if(my !== CMP_SEQ) return; status.className = "result-box sell"; status.textContent = "Error: " + e.message; }
}
document.getElementById("cmpPeriod").addEventListener("change", compareStocks);

/* ============================================================
   START-UP
   ============================================================ */
attachSymbolPicker("pfPicker", "pfSymbol", ()=>document.getElementById("pfQty").focus());
attachSymbolPicker("cmpPickerA", "cmpA", ()=>compareStocks());
attachSymbolPicker("cmpPickerB", "cmpB", ()=>compareStocks());
const FIRST_SHOWN = new Set();
function onTabShown(name){
  if(FIRST_SHOWN.has(name)) return;
  FIRST_SHOWN.add(name);
  if(name === "fx"){ convertFx(); compareStocks(); }
  if(name === "mf"){ if(!document.getElementById("mfQuery").value) document.getElementById("mfQuery").value = "parag parikh flexi cap"; searchFunds(); }
  if(name === "tracker" && HOLDINGS.length) valuePortfolio();
}
(function startup(){
  const d = new Date(); d.setFullYear(d.getFullYear() - 3);
  document.getElementById("mfStart").value = d.toISOString().slice(0,10);
  renderBudgetItems(); renderHoldings(); renderWatchlist(); renderAlerts(); renderAccount();
  const first = location.hash.slice(1) || LS.get("fs-tab") || "ratios";
  showTab(document.getElementById("panel-"+first) ? first : "ratios", {noHash:!location.hash, keepScroll:true});
  window.addEventListener("hashchange", ()=>{ const t = location.hash.slice(1); if(t && document.getElementById("panel-"+t)) showTab(t, {noHash:true}); });
  if(AUTH.token) startSession(null, false);
  api("GET","/api/status").then(st=>{ document.getElementById("accountTempNote").hidden = st.accounts_persistent !== false; }).catch(()=>{});
})();
