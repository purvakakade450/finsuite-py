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
          line("Surcharge","surcharge"), line("Cess 4%","cess"), ["Tax on share-market gains (incl. cess)", Math.round(n.capital_gains.total), Math.round(o.capital_gains.total)], line("Total tax","total_tax"), ["Effective rate (%)", r2(n.effective_rate), r2(o.effective_rate)],
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

