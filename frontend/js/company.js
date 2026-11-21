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

