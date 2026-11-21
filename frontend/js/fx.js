/* ============================================================
   24 CURRENCY & COMPARE -> GET /market/fx, /market/compare
   ============================================================ */
const FX_LIST = ["INR","USD","EUR","GBP","JPY","AED","SGD","AUD","CAD","CHF","CNY","HKD","KRW","SAR"];
(function fillFx(){
  const opts = FX_LIST.map(c=>`<option value="${c}">${c}</option>`).join("");
  document.getElementById("fxFrom").innerHTML = opts; document.getElementById("fxTo").innerHTML = opts;
  document.getElementById("fxFrom").value = "USD"; document.getElementById("fxTo").value = "INR";
  ["fxFrom","fxTo"].forEach(id=>document.getElementById(id).addEventListener("change", convertFx));
  document.getElementById("fxAmount").addEventListener("keydown", e=>{ if(e.key==="Enter") convertFx(); });
})();
function swapFx(){ const a = document.getElementById("fxFrom"), b = document.getElementById("fxTo"); [a.value, b.value] = [b.value, a.value]; convertFx(); }
let FX_SEQ = 0;
async function convertFx(){
  const my = ++FX_SEQ, box = document.getElementById("fxResult");
  const from = document.getElementById("fxFrom").value, to = document.getElementById("fxTo").value, amount = val("fxAmount");
  box.textContent = "Fetching live rate…";
  try{
    const r = await api("GET", `/market/fx?base=${from}&quote=${to}&amount=${amount}`);
    if(my !== FX_SEQ) return;
    const n = (v, d=4) => (+v).toLocaleString("en-IN", {maximumFractionDigits:d});
    box.innerHTML = `<span style="font-size:18px;"><b>${n(amount,2)} ${from} = ${n(r.converted, 2)} ${to}</b></span><br>1 ${from} = ${n(r.rate)} ${to} · 1 ${to} = ${n(r.inverse, 6)} ${from}` +
      (r.changePercent!=null ? ` · today <span class="${r.change>=0?"badge-good":"badge-warn"}">${r.change>=0?"+":""}${r.changePercent}%</span>` : "") +
      (r.asOf ? `<div class="muted" style="margin:4px 0 0;">Rate as of ${new Date(r.asOf).toLocaleString()}</div>` : "");
    const box2 = document.getElementById("fxChartBox");
    box2.hidden = !r.history;
    if(r.history) lineChart("fxChart","fx", r.history.map(x=>x.Date), [{ label:`1 ${from} in ${to} (last 3 months)`, data:r.history.map(x=>x.Close), borderColor:"#2C6FB0", backgroundColor:"rgba(44,111,176,.1)", fill:true, pointRadius:0, borderWidth:2, tension:.15 }]);
  }catch(e){ if(my === FX_SEQ) box.textContent = "Error: " + e.message; }
}
let CMP_SEQ = 0;
async function compareStocks(){
  const my = ++CMP_SEQ, status = document.getElementById("cmpStatus");
  const a = document.getElementById("cmpA").value, b = document.getElementById("cmpB").value;
  status.hidden = false; status.className = "result-box"; status.textContent = "Fetching both price histories…";
  try{
    const r = await api("GET", `/market/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}&period=${document.getElementById("cmpPeriod").value}`);
    if(my !== CMP_SEQ) return;
    status.hidden = true;
    document.getElementById("cmpChartBox").hidden = false;
    lineChart("cmpChart","cmp", r.dates, [
      { label:`${r.a.name} (${r.a.symbol})`, data:r.a.rebased, borderColor:"#1F3A68", pointRadius:0, borderWidth:2, tension:.1 },
      { label:`${r.b.name} (${r.b.symbol})`, data:r.b.rebased, borderColor:"#B9840E", pointRadius:0, borderWidth:2, tension:.1 },
    ]);
    const cls = v => v>=0 ? "badge-good" : "badge-warn";
    const row = (label, k, f=v=>pct(v), c=null) => `<tr><td>${label}</td><td class="num ${c?c(r.a[k]):""}">${f(r.a[k], r.a)}</td><td class="num ${c?c(r.b[k]):""}">${f(r.b[k], r.b)}</td></tr>`;
    const price = (v, s) => currencySymbol(s.currency) + (+v).toLocaleString("en-IN",{maximumFractionDigits:2});
    document.getElementById("cmpTable").innerHTML = `<tr><th></th><th class="num">${escapeHtml(r.a.name)}</th><th class="num">${escapeHtml(r.b.name)}</th></tr>` +
      row("Return over period","return_pct",v=>pct(v),cls) + row(`Volatility (a year)<span class="info" data-term="Volatility" tabindex="0" role="button"></span>`,"volatility_pct") +
      row(`Max drawdown<span class="info" data-term="Maximum drawdown" tabindex="0" role="button"></span>`,"max_drawdown_pct",v=>pct(v),()=> "badge-warn") +
      row("Best day","best_day_pct",v=>pct(v),cls) + row("Worst day","worst_day_pct",v=>pct(v),cls) + row("Start price","start",price) + row("Latest price","end",price) +
      `<tr><td>Correlation of daily moves</td><td class="num" colspan="2" style="text-align:center;">${r.correlation ?? "—"}</td></tr>`;
    document.getElementById("cmpInsightText").textContent = r.summary;
    document.getElementById("cmpInsight").hidden = false;
  }catch(e){ if(my !== CMP_SEQ) return; status.className = "result-box sell"; status.textContent = "Error: " + e.message; }
}
document.getElementById("cmpPeriod").addEventListener("change", compareStocks);

