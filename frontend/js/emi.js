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

