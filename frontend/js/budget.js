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

