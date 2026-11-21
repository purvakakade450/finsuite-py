/* ============================================================
   18 INCOME TAX -> POST /tax/income
   ============================================================ */
async function calcIncomeTax(){
  const out = document.getElementById("itOut");
  try{
    const r = await api("POST","/tax/income",{
      gross_income: val("itIncome"), salaried: document.getElementById("itSalaried").value==="1", age_group: document.getElementById("itAge").value,
      sec80c: val("it80c"), sec80d: val("it80d"), nps_80ccd1b: val("itNps"), home_loan_interest: val("itHome"), hra_exemption: val("itHra"), other_deductions: val("itOther"),
      stcg_equity: val("itStcg"), ltcg_equity: val("itLtcg"),
    });
    const n = r.new, o = r.old;
    const win = r.better === "same" ? "Both regimes cost about the same" : `The <b>${r.better} regime</b> saves you <b>${rupees(r.savings)}</b> a year`;
    const row = (label, k, f=rupees, cls="") => `<tr><td>${label}</td><td class="num ${cls}">${f(n[k])}</td><td class="num ${cls}">${f(o[k])}</td></tr>`;
    const slabTable = x => `<table><tr><th>Income band</th><th class="num">Rate</th><th class="num">Tax</th></tr>` +
      x.slabs.map(s=>`<tr><td>${rupees(s.from)} – ${s.to==null?"above":rupees(s.to)}</td><td class="num">${s.rate}%</td><td class="num">${rupees(s.tax)}</td></tr>`).join("") + `</table>`;
    const hasGains = n.capital_gains.stcg > 0 || n.capital_gains.ltcg > 0;
    const gainsRow = hasGains ? `<tr><td>Included above: tax on share-market gains (with cess)</td><td class="num">${rupees(n.capital_gains.total)}</td><td class="num">${rupees(o.capital_gains.total)}</td></tr>` : "";
    out.innerHTML = `
      <div class="result-box ${r.better==="same"?"hold":"buy"}" style="font-size:15px;">${win}.</div>
      <div class="stat-strip">
        <div class="stat">New regime tax<b>${rupees(n.total_tax)}</b></div>
        <div class="stat">Old regime tax<b>${rupees(o.total_tax)}</b></div>
        <div class="stat">You save<b class="badge-good">${rupees(r.savings)}/yr</b></div>
        <div class="stat">Old regime wins only above<b>${r.break_even_deductions==null?"never":rupees(r.break_even_deductions)}</b><span class="meta">of deductions</span></div>
      </div>
      <div class="table-wrap"><table>
        <tr><th></th><th class="num">New regime</th><th class="num">Old regime</th></tr>
        ${row("Gross income","gross_income")}${row("Standard deduction","standard_deduction")}${row("Deductions (80C, 80D, HRA…)","deductions")}
        ${row("<b>Taxable income</b>","taxable_income")}${row("Tax on slabs","tax_on_slabs")}${row(`Rebate 87A<span class="info" data-term="Tax rebate" tabindex="0" role="button"></span>`,"rebate")}
        ${row(`Surcharge<span class="info" data-term="Surcharge" tabindex="0" role="button"></span>`,"surcharge")}${row("Health &amp; education cess 4%","cess")}
        ${row("<b>Total tax</b>","total_tax", v=>`<b>${rupees(v)}</b>`)}${row(`Effective tax rate<span class="info" data-term="Effective tax rate" tabindex="0" role="button"></span>`,"effective_rate", v=>pct(v))}
        ${row("Monthly take-home after tax","monthly_take_home")}
        ${gainsRow}
      </table></div>
      <details><summary>Show slab-by-slab working</summary><div class="grid-2" style="margin-top:8px;"><div><div class="sub">New regime</div>${slabTable(n)}</div><div><div class="sub">Old regime</div>${slabTable(o)}</div></div></details>
      <div class="chart-box short"><canvas id="itChart"></canvas></div>
      <div class="insight-box"><span class="lbl">Insight</span>${escapeHtml(r.insight)}</div>`;
    barChart("itChart","incometax", ["New regime","Old regime"], [Math.round(n.total_tax), Math.round(o.total_tax)], {color:["#1F3A68","#B9840E"]});
    LAST.incometax = { inputs: readInputs({"Annual gross income (Rs)":"itIncome", "Age group":"itAge", "Salaried (1 = yes)":"itSalaried", "80C (Rs)":"it80c", "80D (Rs)":"it80d",
      "NPS 80CCD(1B) (Rs)":"itNps", "Home loan interest (Rs)":"itHome", "HRA exemption (Rs)":"itHra", "Other deductions (Rs)":"itOther", "Short-term gains (Rs)":"itStcg", "Long-term gains (Rs)":"itLtcg"}), r };
    showExport("incometax");
  }catch(e){ out.innerHTML = `<div class="result-box sell">Error: ${escapeHtml(e.message)}</div>`; showExport("incometax", false); }
}

