/* ============================================================
   20 BUDGET PLANNER — import a bank statement (CSV)
   The file is read inside the browser and is never uploaded. The pure
   functions at the top have no page dependencies so they can be tested
   with Node (see tests/test_statement_js.py).
   ============================================================ */
const STMT_RULES = [
  // [category, kind, pattern]; the first match wins
  ["Credit card bill", "need", /credit ?card|cc payment|cred club|cred\.club|\bcred\b|billdesk.*card/i],
  ["Rent", "need", /\brent\b|landlord|nobroker/i],
  ["Loan EMI", "need", /\bemi\b|loan|bajaj fin|hdfc ltd|home loan|car loan|interest charged|finance ltd/i],
  ["Groceries", "need", /bigbasket|blinkit|zepto|dmart|d mart|grofers|jiomart|reliance fresh|more retail|grocery|kirana|vegetable|instamart|milk/i],
  ["Bills & utilities", "need", /electric|bescom|mseb|msedcl|tata power|adani electric|water bill|piped gas|mahanagar gas|indane|bharat gas|airtel|\bjio\b|vodafone|\bvi\b|bsnl|broadband|act fibernet|hathway|\bdth\b|tata play|recharge|postpaid|bbps|municipal|gas bill/i],
  ["Transport", "need", /uber|\bola\b|rapido|irctc|redbus|metro|petrol|diesel|fuel|hpcl|bpcl|iocl|indian oil|fastag|parking|railway|indigo|air india|spicejet|namma yatri|toll/i],
  ["Health", "need", /hospital|clinic|pharm|apollo|medplus|1mg|netmeds|diagnostic|doctor|dental|\blab\b/i],
  ["Insurance", "need", /\blic\b|insurance|premium|hdfc life|sbi life|max life/i],
  ["Education", "need", /school|college|tuition|university|\bfees?\b|byju|unacademy|coursera|udemy/i],
  ["Subscriptions", "want", /netflix|spotify|hotstar|prime video|amazon prime|youtube|sony ?liv|zee5|apple\.com|google (play|one)|microsoft|adobe|openai|chatgpt|subscription|audible/i],
  ["Dining out", "want", /swiggy|zomato|restaurant|cafe|starbucks|mcdonald|dominos|domino's|kfc|pizza|burger|eatsure|dineout|brewery|bakery|food/i],
  ["Shopping", "want", /amazon|flipkart|myntra|ajio|nykaa|meesho|decathlon|westside|lifestyle|croma|zudio|shopping|tata cliq|reliance retail/i],
  ["Entertainment & travel", "want", /bookmyshow|pvr|inox|movie|makemytrip|goibibo|cleartrip|oyo|airbnb|hotel|resort|holiday/i],
  ["Cash withdrawal", "want", /\batm\b|cash wd|cash withdrawal|\bnwd\b|cash w\/d/i],
  ["Investments (SIP, stocks, FD)", "saving", /\bsip\b|mutual fund|zerodha|groww|upstox|kuvera|smallcase|\bppf\b|\bnps\b|nippon|axis mf|sbi mf|hdfc mf|parag parikh|mirae|fixed deposit|\bfd\b|recurring deposit|sgb|indian clearing|nse clearing|\betf\b/i],
];
const STMT_INCOME = /salary|payroll|stipend|wages|freelance|consult|invoice|bonus/i;
const STMT_SKIP = /\bself\b|own account|from savings|to savings|transfer to \d{4}x/i;       // moves between your own accounts
const MONTHS = {jan:1,feb:2,mar:3,apr:4,may:5,jun:6,jul:7,aug:8,sep:9,oct:10,nov:11,dec:12};

function parseCsv(text){
  text = text.replace(/^﻿/, "");
  const first = text.split(/\r?\n/).slice(0, 15).join("\n");
  const delim = [",", ";", "\t", "|"].map(d=>[d, first.split(d).length]).sort((a,b)=>b[1]-a[1])[0][0];
  const rows = []; let row = [], cell = "", quoted = false;
  for(let i = 0; i < text.length; i++){
    const c = text[i];
    if(quoted){
      if(c === '"' && text[i+1] === '"'){ cell += '"'; i++; }
      else if(c === '"') quoted = false;
      else cell += c;
    }else if(c === '"') quoted = true;
    else if(c === delim){ row.push(cell); cell = ""; }
    else if(c === "\n" || c === "\r"){
      if(c === "\r" && text[i+1] === "\n") i++;
      row.push(cell); cell = "";
      if(row.some(x=>x.trim() !== "")) rows.push(row);
      row = [];
    }else cell += c;
  }
  row.push(cell);
  if(row.some(x=>x.trim() !== "")) rows.push(row);
  return rows;
}

function findHeader(rows){
  for(let i = 0; i < Math.min(rows.length, 40); i++){
    const cells = rows[i].map(c=>c.toLowerCase().trim());
    if(cells.length >= 3 && cells.some(c=>c.includes("date")) && cells.some(c=>/debit|withdraw|\bdr\b|amount|credit|deposit|\bcr\b/.test(c))) return i;
  }
  return -1;
}

function mapColumns(header){
  const h = header.map(c=>c.toLowerCase().trim());
  const find = (...res)=>{ for(const re of res){ const i = h.findIndex(c=>re.test(c)); if(i >= 0) return i; } return -1; };
  return {
    date: find(/^(txn|transaction|tran|posting)\s*date/, /^date$/, /date/),
    desc: find(/narration|description|particulars|transaction remarks|remarks|details/),
    debit: find(/debit|withdraw|paid out|\bdr\b(?!\/)/),
    credit: find(/credit|deposit|paid in|received|\bcr\b(?!\/)/),
    amount: find(/^(transaction )?amount/, /amount/),
    type: find(/dr\s*\/\s*cr|cr\s*\/\s*dr|debit\/credit|^type$|indicator/),
  };
}

function parseAmount(s){
  if(s == null) return null;
  let t = String(s).trim();
  if(!t) return null;
  let sign = 1;
  if(/\(.*\)/.test(t)) sign = -1;
  if(/\bdr\b|debit/i.test(t)) sign = -1;
  if(/^-/.test(t)) sign = -1;
  t = t.replace(/[^0-9.]/g, "");
  if(!t || t === ".") return null;
  const n = parseFloat(t);
  return isNaN(n) ? null : sign * n;
}

function parseDate(s){
  s = String(s || "").trim();
  let m = s.match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2,4})/);
  if(m){ let y = +m[3]; if(y < 100) y += 2000; return validDate(y, +m[2], +m[1]); }
  m = s.match(/^(\d{4})[\/\-.](\d{1,2})[\/\-.](\d{1,2})/);
  if(m) return validDate(+m[1], +m[2], +m[3]);
  m = s.match(/^(\d{1,2})[\s\-\/]([A-Za-z]{3})[a-z]*[\s\-\/,]*(\d{2,4})/);
  if(m && MONTHS[m[2].toLowerCase()]){ let y = +m[3]; if(y < 100) y += 2000; return validDate(y, MONTHS[m[2].toLowerCase()], +m[1]); }
  return null;
}
function validDate(y, mo, d){ return mo >= 1 && mo <= 12 && d >= 1 && d <= 31 && y >= 1990 && y <= 2100 ? {y, m: mo, d} : null; }

function categorise(desc){
  for(const [category, kind, re] of STMT_RULES) if(re.test(desc)) return {category, kind};
  return null;
}

function merchantOf(desc){
  const words = desc.replace(/[0-9@\/\\*_\-:.]+/g, " ").replace(/\b(upi|neft|imps|rtgs|pos|ach|nach|txn|ref|to|from|by|payment|paid|dr|cr)\b/gi, " ")
    .split(/\s+/).filter(w=>w.length > 2).slice(0, 3).join(" ");
  return words || desc.slice(0, 24);
}

function analyseStatement(text){
  const rows = parseCsv(text);
  const hi = findHeader(rows);
  if(hi < 0) return {ok:false, error:"I could not find the column titles. The file needs a date column and either debit and credit columns or one amount column."};
  const col = mapColumns(rows[hi]);
  if(col.date < 0 || col.desc < 0 || (col.debit < 0 && col.credit < 0 && col.amount < 0))
    return {ok:false, error:"The statement needs date, description and amount columns (debit and credit, or a single amount)."};

  const monthKeys = new Set(), cats = {}, other = {};
  let income = 0, salary = 0, debits = 0, count = 0, from = null, to = null, skipped = 0;
  for(const r of rows.slice(hi + 1)){
    const date = parseDate(r[col.date]);
    if(!date) continue;                                   // balance rows, totals, footers
    const desc = (r[col.desc] || "").replace(/\s+/g, " ").trim();
    let debit = col.debit >= 0 ? parseAmount(r[col.debit]) : null;
    let credit = col.credit >= 0 ? parseAmount(r[col.credit]) : null;
    if(debit === null && credit === null && col.amount >= 0){
      const a = parseAmount(r[col.amount]);
      const t = col.type >= 0 ? String(r[col.type]).toLowerCase() : "";
      if(a !== null){
        if(/cr|credit/.test(t) && !/dr|debit/.test(t)) credit = Math.abs(a);
        else if(/dr|debit/.test(t)) debit = Math.abs(a);
        else if(a < 0) debit = -a; else credit = a;      // no type column: a minus sign means money out
      }
    }
    if(debit !== null) debit = Math.abs(debit);
    if(credit !== null) credit = Math.abs(credit);
    if(!debit && !credit) continue;
    count++;
    monthKeys.add(date.y * 100 + date.m);
    const key = date.y * 10000 + date.m * 100 + date.d;
    if(from === null || key < from) from = key;
    if(to === null || key > to) to = key;
    if(STMT_SKIP.test(desc)){ skipped++; continue; }
    if(credit){ income += credit; if(STMT_INCOME.test(desc)) salary += credit; continue; }
    debits += debit;
    const c = categorise(desc);
    if(c){
      const e = cats[c.category] || (cats[c.category] = {category:c.category, kind:c.kind, total:0, count:0, examples:{}});
      e.total += debit; e.count++; const mname = merchantOf(desc); e.examples[mname] = (e.examples[mname] || 0) + debit;
    }else{
      const mname = merchantOf(desc);
      const e = other[mname] || (other[mname] = {name:mname, total:0, count:0}); e.total += debit; e.count++;
    }
  }
  if(!count) return {ok:false, error:"No transactions with a readable date and amount were found in this file."};
  const months = Math.max(monthKeys.size, 1);
  const top = obj => Object.entries(obj).sort((a,b)=>b[1]-a[1]).slice(0, 3).map(x=>x[0]);
  const categories = Object.values(cats).map(e=>({category:e.category, kind:e.kind, total:e.total, count:e.count,
    monthly: e.total / months, examples: top(e.examples)})).sort((a,b)=>b.total - a.total);
  const otherList = Object.values(other).sort((a,b)=>b.total - a.total);
  const otherTotal = otherList.reduce((s,e)=>s + e.total, 0);
  const incomeUsed = salary > 0 ? salary : income;
  return {ok:true, transactions:count, months, skipped,
    period:{from, to}, income_monthly: incomeUsed / months, income_source: salary > 0 ? "salary credits" : "all credits",
    debits_monthly: debits / months, categories,
    other:{total: otherTotal, monthly: otherTotal / months, count: otherList.reduce((s,e)=>s + e.count, 0), examples: otherList.slice(0, 6).map(e=>e.name)}};
}

if(typeof module !== "undefined") module.exports = {parseCsv, findHeader, mapColumns, parseAmount, parseDate, categorise, merchantOf, analyseStatement};

/* ---------------------- page part (browser only) ---------------------- */
let STMT_LAST = null;
function importStatement(input){
  const file = input.files && input.files[0];
  const out = document.getElementById("stmtOut");
  if(!file) return;
  out.hidden = false;
  if(file.size > 5 * 1024 * 1024){ out.innerHTML = `<div class="result-box sell">That file is over 5 MB. Export a shorter period, such as the last 3 months.</div>`; return; }
  const reader = new FileReader();
  reader.onload = ()=>{
    let r;
    try{ r = analyseStatement(String(reader.result)); }catch(e){ r = {ok:false, error:"I could not read that file: " + e.message}; }
    STMT_LAST = r;
    renderStatementResult();
  };
  reader.onerror = ()=>{ out.innerHTML = `<div class="result-box sell">The file could not be read.</div>`; };
  reader.readAsText(file);
}
function renderStatementResult(){
  const out = document.getElementById("stmtOut"), r = STMT_LAST;
  if(!r.ok){ out.innerHTML = `<div class="result-box sell">${escapeHtml(r.error)}</div>`; return; }
  const kinds = ["need","want","saving"], label = {need:"Need", want:"Want", saving:"Saving"};
  const rows = r.categories.map((c,i)=>`<tr><td>${escapeHtml(c.category)}<div class="meta" style="white-space:normal;">${escapeHtml(c.examples.join(", "))}</div></td>
      <td><select aria-label="Type of ${escapeHtml(c.category)}" onchange="STMT_LAST.categories[${i}].kind=this.value">${kinds.map(k=>`<option value="${k}"${k===c.kind?" selected":""}>${label[k]}</option>`).join("")}</select></td>
      <td class="num">${rupees(c.monthly)}</td></tr>`).join("");
  const o = r.other;
  const fmt = k => `${String(k).slice(6)}/${String(k).slice(4,6)}/${String(k).slice(0,4)}`;
  out.innerHTML = `
    <div class="insight-box"><span class="lbl">What I found</span>
      ${r.transactions} transactions from ${fmt(r.period.from)} to ${fmt(r.period.to)} (${r.months} month${r.months>1?"s":""}).
      Average monthly income: <b>${rupees(r.income_monthly)}</b> (from ${escapeHtml(r.income_source)}); average spending: <b>${rupees(r.debits_monthly)}</b>.
      ${r.skipped ? `<br><span class="meta">${r.skipped} transfers between your own accounts were ignored.</span>` : ""}</div>
    <div class="table-wrap"><table><tr><th>Category (examples)</th><th>Type</th><th class="num">Per month</th></tr>${rows}
      ${o.total ? `<tr><td>Other spending<div class="meta" style="white-space:normal;">${escapeHtml(o.examples.join(", "))}</div></td><td>Want</td><td class="num">${rupees(o.monthly)}</td></tr>` : ""}
    </table></div>
    <p class="meta">Check the types, then add them to your budget. You can still edit every line there. Payments I could not name (mostly UPI to people) are grouped as "Other spending".</p>
    <div class="btn-row"><button class="btn" onclick="applyStatement()">Use these in my budget</button></div>`;
}
function applyStatement(){
  const r = STMT_LAST;
  if(!r || !r.ok) return;
  const round10 = v=>Math.max(Math.round(v / 10) * 10, 0);
  BUDGET = r.categories.map(c=>({category:c.category, amount:round10(c.monthly), kind:c.kind}));
  if(r.other.total) BUDGET.push({category:"Other spending", amount:round10(r.other.monthly), kind:"want"});
  saveBudget(); renderBudgetItems();
  if(r.income_monthly > 0) document.getElementById("budIncome").value = round10(r.income_monthly);
  document.getElementById("stmtBox").open = false;
  toast("Budget filled from your statement. Press Analyse budget to see how it compares with the 50/30/20 rule.");
  document.getElementById("budItems").scrollIntoView({behavior:"smooth", block:"start"});
}
function downloadSampleStatement(){
  const lines = ["Date,Narration,Withdrawal Amt.,Deposit Amt.,Closing Balance",
    "01/09/25,SALARY CREDIT ACME PVT LTD,,85000.00,92000.00", "02/09/25,UPI-LANDLORD RENT SEPT,22000.00,,70000.00",
    "03/09/25,UPI-BIGBASKET,2350.50,,67649.50", "05/09/25,UPI-SWIGGY ORDER,640.00,,67009.50", "07/09/25,NACH HDFC HOME LOAN EMI,14500.00,,52509.50",
    "10/09/25,BESCOM ELECTRICITY BILL,1850.00,,50659.50", "12/09/25,NETFLIX.COM,649.00,,50010.50", "15/09/25,ZERODHA SIP MUTUAL FUND,10000.00,,40010.50",
    "18/09/25,AMAZON PAY INDIA,3200.00,,36810.50", "21/09/25,UPI-UBER TRIP,420.00,,36390.50", "01/10/25,SALARY CREDIT ACME PVT LTD,,85000.00,121390.50",
    "02/10/25,UPI-LANDLORD RENT OCT,22000.00,,99390.50", "04/10/25,UPI-BLINKIT,1890.00,,97500.50", "09/10/25,ATM CASH WDL,5000.00,,92500.50",
    "13/10/25,NACH HDFC HOME LOAN EMI,14500.00,,78000.50", "16/10/25,UPI-ZOMATO,780.00,,77220.50", "20/10/25,UPI-RAHUL SHARMA,1500.00,,75720.50"];
  const url = URL.createObjectURL(new Blob([lines.join("\n")], {type:"text/csv"}));
  const a = document.createElement("a"); a.href = url; a.download = "sample_bank_statement.csv"; a.click();
  setTimeout(()=>URL.revokeObjectURL(url), 1000);
}
