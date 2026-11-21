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

