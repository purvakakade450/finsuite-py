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

