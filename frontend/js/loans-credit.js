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

