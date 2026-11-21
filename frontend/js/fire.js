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
    const progress = Math.min(r.projected_corpus / r.corpus_needed * 100, 100);
    document.getElementById("fiProgress").hidden = false;
    document.getElementById("fiProgress").innerHTML = `<div class="bar-label"><b>Your current plan reaches ${progress.toFixed(0)}% of what you need</b><span class="muted" style="margin:0;">${rupees(r.projected_corpus)} of ${rupees(r.corpus_needed)}</span></div>
      <div class="progress-track" role="progressbar" aria-valuenow="${progress.toFixed(0)}" aria-valuemin="0" aria-valuemax="100"><div class="progress-fill ${progress >= 100 ? "buy" : progress >= 60 ? "hold" : "sell"}" style="width:${progress}%"></div></div>`;
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
  }catch(e){ showError("fiError", e); setHidden(["fiStats","fiChartBox","fiInsight","fiProgress"], true); showExport("fire", false); }
}

