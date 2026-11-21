/* ============================================================
   12 GROWTH & TARGET PLANNER -> POST /planner/what-if, /planner/target-plan
   ============================================================ */
async function calcWhatIf(){
  const box = document.getElementById("wiResult");
  try{
    const r = await api("POST","/planner/what-if",{
      amount:+document.getElementById("wiAmount").value, price_then:+document.getElementById("wiThen").value,
      price_now:+document.getElementById("wiNow").value, days_held:+document.getElementById("wiDays").value,
    });
    box.innerHTML = `Shares: <b>${r.shares.toFixed(4)}</b><br>Value now: <b>₹${r.value_now.toFixed(2)}</b><br>Gain: <b class="${r.gain>=0?'badge-good':'badge-warn'}">₹${r.gain.toFixed(2)} (${r.gain_pct.toFixed(2)}%)</b>${r.cagr!==null?`<br>CAGR: <b>${r.cagr.toFixed(2)}%</b>`:""}`;
  }catch(e){ box.textContent = "Error: "+e.message; }
}
async function calcTargetPlan(){
  const box = document.getElementById("tpResult");
  try{
    const r = await api("POST","/planner/target-plan",{
      entry:+document.getElementById("tpEntry").value, qty:+document.getElementById("tpQty").value,
      target_pct:+document.getElementById("tpTarget").value, stop_pct:+document.getElementById("tpStop").value,
    });
    box.className = `result-box ${r.band||""}`;
    box.innerHTML = `Target price: <b class="badge-good">₹${r.target_price.toFixed(2)}</b><br>Stop-loss price: <b class="badge-warn">₹${r.stop_price.toFixed(2)}</b><br>Potential gain: ₹${r.gain_amount.toFixed(2)} · Potential loss: ₹${r.loss_amount.toFixed(2)}${r.risk_reward!==null?`<br>Risk-Reward: <b>${r.risk_reward.toFixed(2)}</b>`:""}<br><span class="muted">${r.verdict}</span>`;
  }catch(e){ box.className="result-box"; box.textContent = "Error: "+e.message; }
}

/* ============================================================
   13 PORTFOLIO & TAX TOOLS
   ============================================================ */
async function calcSip(){
  const box = document.getElementById("sipResult");
  try{
    const prices = document.getElementById("sipPrices").value.split(",").map(s=>s.trim()).filter(s=>s!=="").map(Number);
    const r = await api("POST","/tools/sip-vs-lumpsum",{
      total:+document.getElementById("sipTotal").value, months:+document.getElementById("sipMonths").value,
      start_price:+document.getElementById("sipStart").value, prices_by_month:prices, last_price:+document.getElementById("sipLast").value,
    });
    box.innerHTML = `Lump sum value: <b>₹${r.lump_sum_value.toFixed(2)}</b><br>SIP value: <b>₹${r.sip_value.toFixed(2)}</b><br>Winner: <b class="badge-good">${r.winner==="lump_sum"?"Lump Sum":"SIP"}</b> by ₹${r.difference.toFixed(2)}`;
  }catch(e){ box.textContent = "Error: "+e.message; }
}
async function calcTax(){
  const box = document.getElementById("taxResult");
  try{
    const r = await api("POST","/tools/capital-gains-tax",{
      buy_price:+document.getElementById("taxBuy").value, sell_price:+document.getElementById("taxSell").value,
      qty:+document.getElementById("taxQty").value, buy_date:document.getElementById("taxBuyDate").value,
      sell_date:document.getElementById("taxSellDate").value, other_ltcg:+document.getElementById("taxOtherLtcg").value||0,
    });
    box.innerHTML = `Holding period: <b>${r.holding_days} days</b> → <b>${r.tax_type}</b><br>Gross gain: <b>₹${r.gain.toFixed(2)}</b><br>Estimated tax (incl. cess): <b class="badge-warn">₹${r.tax.toFixed(2)}</b><br>Net proceeds: <b class="badge-good">₹${r.net_proceeds.toFixed(2)}</b>`;
  }catch(e){ box.textContent = "Error: "+e.message; }
}
async function calcRange(){
  const box = document.getElementById("rangeResult");
  try{
    const r = await api("POST","/tools/52-week-range",{
      current:+document.getElementById("rangeCurrent").value, high:+document.getElementById("rangeHigh").value, low:+document.getElementById("rangeLow").value,
    });
    box.innerHTML = `Position in range: <b>${r.range_position_pct.toFixed(1)}%</b><br>From 52w high: <b class="badge-warn">${r.from_high_pct.toFixed(2)}%</b><br>From 52w low: <b class="${r.from_low_pct>=0?'badge-good':'badge-warn'}">${r.from_low_pct>=0?"+":""}${r.from_low_pct.toFixed(2)}%</b>`;
  }catch(e){ box.textContent = "Error: "+e.message; }
}

