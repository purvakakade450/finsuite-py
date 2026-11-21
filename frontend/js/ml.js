/* ============================================================
   15 ML PRICE PREDICTION -> GET /ml/predict
   Four models (Linear, Ridge, Random Forest, Gradient Boosting) are tested on
   the latest 20% of days and again with a walk-forward test over several
   stretches of history, always against the naive guess "tomorrow = today".
   ============================================================ */
let MLSEQ = 0;
const ML_COLORS = {linear:"#B9840E", ridge:"#2E7D4F", random_forest:"#7A4CC2", gradient_boosting:"#C2477A"};
async function runPrediction(){
  const my = ++MLSEQ;
  const status = document.getElementById("mlStatus"), btn = document.getElementById("mlRun");
  const symbol = document.getElementById("mlSymbol").value.trim();
  if(!symbol){ status.textContent = "Choose a company above."; return; }
  status.textContent = "Fetching history and training four models… (can take up to a minute)";
  btn.disabled = true;
  ["mlStats","mlVerdict","mlNews"].forEach(id=>document.getElementById(id).style.display="none");
  document.getElementById("mlWalk").hidden = true;
  try{
    const d = await api("GET", `/ml/predict?symbol=${encodeURIComponent(symbol)}&period=${document.getElementById("mlPeriod").value}`);
    if(my !== MLSEQ) return;
    const cur = currencySymbol(d.currency), fmt = v => cur + v.toLocaleString(d.currency==="INR"?"en-IN":"en-US", {minimumFractionDigits:2, maximumFractionDigits:2});
    const f = d.forecast, m = d.metrics, names = Object.fromEntries(d.models.map(x=>[x.key, x.label]));
    const arrow = p => `<span class="${p>=0?'badge-good':'badge-warn'}">${p>=0?"▲ +":"▼ "}${p.toFixed(2)}%</span>`;
    status.innerHTML = `<b>${escapeHtml(d.name)}</b> <span class="muted">(${escapeHtml(d.yahooSymbol)})</span> · trained on ${d.data.train} days, tested on the latest ${d.data.test} days (${d.data.days} trading days downloaded)`;
    const stats = document.getElementById("mlStats");
    stats.style.display = "flex";
    stats.innerHTML = `<div class="stat">Last close (${fmtDate(f.last_date)})<b>${fmt(f.last_close)}</b></div>` +
      d.models.map(x=>`<div class="stat">${escapeHtml(x.label)} → next day<b>${fmt(f[x.key])}</b>${arrow(f[x.key+"_change_pct"])}</div>`).join("");
    const order = [["naive","Naive: tomorrow = today"], ...d.models.map(x=>[x.key, x.label])];
    document.getElementById("mlTable").innerHTML =
      `<tr><th>Model</th><th class="num">MAE (${escapeHtml(d.currency||"")})</th><th class="num">RMSE</th><th class="num">MAPE %</th><th class="num">Direction right</th></tr>` +
      order.map(([k,label])=>`<tr><td>${k===d.best_model?"<b>"+label+" ★</b>":label}</td><td class="num">${m[k].mae.toLocaleString()}</td><td class="num">${m[k].rmse.toLocaleString()}</td><td class="num">${m[k].mape.toFixed(2)}%</td><td class="num">${k==="naive"?"—":d.direction_accuracy[k]+"%"}</td></tr>`).join("");

    const gain = ((m.naive.mae - m[d.best_model].mae) / m.naive.mae * 100);
    const wf = d.walk_forward, bestWf = wf && wf.models[d.best_model];
    let verdict = d.beats_baseline
      ? `${names[d.best_model]} was the most accurate on unseen days, about ${gain.toFixed(1)}% closer than simply assuming tomorrow equals today.`
      : `No model beat the naive "tomorrow = today" guess on unseen days (best: ${names[d.best_model]}, ${Math.abs(gain).toFixed(1)}% ${gain<0?"worse":"better"}). That is common, because day-to-day prices are very hard to predict, so treat the forecast above as a rough guide, not a signal.`;
    if(bestWf) verdict += ` In the walk-forward test it beat the naive guess in ${bestWf.folds_beating_naive} of ${wf.folds} stretches` +
      (bestWf.folds_beating_naive >= wf.folds - 1 ? ", so the result looks consistent." : bestWf.folds_beating_naive <= 1 ? ", so the single good result may be luck." : ", a mixed record.");
    document.getElementById("mlVerdictText").textContent = verdict;
    document.getElementById("mlVerdict").style.display = "block";

    const walk = document.getElementById("mlWalk");
    if(wf){
      walk.hidden = false;
      walk.innerHTML = `<div class="sub" style="margin-top:16px;">Walk-forward test<span class="info" data-term="Walk-forward test" tabindex="0" role="button" aria-label="Explain walk-forward test"></span></div>
        <p class="muted" style="margin-top:0;">${wf.folds} stretches of ${wf.days_per_fold} trading days. Each model is trained only on the days before a stretch, then tested on it. The average error is compared with the naive guess (${cur}${wf.naive_mae.toLocaleString()}).</p>
        <div class="table-wrap"><table class="walk-table"><tr><th>Model</th><th class="num">Average error (MAE)</th><th class="num">Stretches beating naive</th><th class="num">Direction right</th></tr>` +
        d.models.map(x=>{ const w = wf.models[x.key]; return `<tr><td>${escapeHtml(x.label)}</td><td class="num ${w.mae < wf.naive_mae ? "good-cell" : ""}">${w.mae.toLocaleString()}</td><td class="num">${w.folds_beating_naive} of ${wf.folds}</td><td class="num">${w.direction_accuracy}%</td></tr>`; }).join("") +
        `</table></div>`;
    }
    document.getElementById("mlChartBox").hidden = false;
    lineChart("mlChart","ml", d.test.dates, [
      { label:"Actual close", data:d.test.actual, borderColor:"#1F3A68", borderWidth:2, pointRadius:0, tension:.1 },
      ...d.models.map((x,i)=>({ label:x.label, data:d.test[x.key], borderColor:ML_COLORS[x.key], borderWidth:1.4, borderDash:i%2 ? [5,3] : [], pointRadius:0, tension:.1 })),
    ]);
    document.getElementById("mlNote").hidden = false;
    showNewsMood(d, my);
  }catch(e){
    if(my !== MLSEQ) return;
    status.textContent = "Error: " + e.message;
    document.getElementById("mlChartBox").hidden = true; document.getElementById("mlNote").hidden = true;
    document.getElementById("mlTable").innerHTML = "";
  }finally{ if(my === MLSEQ) btn.disabled = false; }
}
attachSymbolPicker("mlPicker", "mlSymbol", ()=>runPrediction());
