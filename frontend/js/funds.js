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

