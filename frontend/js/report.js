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

