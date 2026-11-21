/* ============================================================
   11 STOCK MARKET — technical indicators on the history chart
   ============================================================ */
let INDSEQ = 0;
const indOn = k => document.querySelector(`#indicatorChips input[data-ind="${k}"]`).checked;
async function drawHistoryChart(){
  if(!HISTORY) return;
  const my = ++INDSEQ;
  const {rows, ticker} = HISTORY;
  const closeSet = (labels, data)=>({ label:`${ticker} close`, data, borderColor:"#1F3A68", backgroundColor:"rgba(31,58,104,.10)", fill:!indOn("bb"), tension:.15, pointRadius:0, borderWidth:2 });
  const any = ["sma20","sma50","ema20","bb","rsi"].some(indOn);
  if(!any){
    lineChart("historyChart","history", rows.map(r=>r.Date), [closeSet(null, rows.map(r=>r.Close))]);
    setHidden(["rsiChartBox","indicatorSignals"], true); destroyChart("rsi");
    return;
  }
  if(!CHARTS.history) lineChart("historyChart","history", rows.map(r=>r.Date), [closeSet(null, rows.map(r=>r.Close))]);
  try{
    const d = await api("GET", `/market/indicators?symbol=${encodeURIComponent(ticker)}&period=${document.getElementById("historyPeriod").value}`);
    if(my !== INDSEQ) return;
    const line = (label, data, color, extra={}) => ({ label, data, borderColor:color, borderWidth:1.4, pointRadius:0, tension:.15, fill:false, spanGaps:true, ...extra });
    const sets = [closeSet(null, d.close)];
    if(indOn("sma20")) sets.push(line("SMA 20", d.sma20, "#B9840E"));
    if(indOn("sma50")) sets.push(line("SMA 50", d.sma50, "#7A4CC2"));
    if(indOn("ema20")) sets.push(line("EMA 20", d.ema20, "#2C6FB0", {borderDash:[5,3]}));
    if(indOn("bb")){
      sets.push(line("Bollinger upper", d.bb_upper, "#8A94A8", {borderDash:[3,3]}));
      sets.push(line("Bollinger lower", d.bb_lower, "#8A94A8", {borderDash:[3,3], fill:"-1", backgroundColor:"rgba(138,148,168,.12)"}));
    }
    lineChart("historyChart","history", d.dates, sets);
    const rsiBox = document.getElementById("rsiChartBox");
    rsiBox.hidden = !indOn("rsi");
    if(indOn("rsi")){
      lineChart("rsiChart","rsi", d.dates, [
        line("RSI 14", d.rsi14, "#C2477A", {borderWidth:1.6}),
        line("70 overbought", d.dates.map(()=>70), "#C43D3D", {borderDash:[4,4], borderWidth:1}),
        line("30 oversold", d.dates.map(()=>30), "#1F9D6B", {borderDash:[4,4], borderWidth:1}),
      ], {y:{min:0, max:100}});
    }else destroyChart("rsi");
    document.getElementById("indicatorSignals").hidden = false;
    document.getElementById("indicatorSignalsText").innerHTML = d.signals.map(t=>`<div style="margin-top:4px;">• ${escapeHtml(t)}</div>`).join("");
  }catch(e){
    if(my !== INDSEQ) return;
    document.getElementById("indicatorSignals").hidden = false;
    document.getElementById("indicatorSignalsText").textContent = "Indicators unavailable: " + e.message;
  }
}
document.querySelectorAll("#indicatorChips input").forEach(i=>i.addEventListener("change", ()=>{ LS.set("fs-ind", [...document.querySelectorAll("#indicatorChips input")].filter(x=>x.checked).map(x=>x.dataset.ind)); drawHistoryChart(); }));
(function restoreIndicators(){
  const saved = LS.get("fs-ind");
  if(saved) document.querySelectorAll("#indicatorChips input").forEach(i=>i.checked = saved.includes(i.dataset.ind));
})();

