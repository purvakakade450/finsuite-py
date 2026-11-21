/* ============================================================
   17 ML PREDICTION — news mood next to the forecast
   ============================================================ */
async function showNewsMood(d, my){
  const box = document.getElementById("mlNews"), text = document.getElementById("mlNewsText");
  try{
    const n = await api("GET", `/market/news?symbols=${encodeURIComponent(d.yahooSymbol)}&limit=10`);
    if(my !== MLSEQ) return;
    const s = n.summary, total = s.positive + s.neutral + s.negative;
    if(!total){ box.style.display = "none"; return; }
    const best = d.best_model;
    const change = d.forecast[best + "_change_pct"];
    const up = change >= 0, mood = s.mood;
    const name = (d.models.find(x=>x.key === best) || {label: best}).label;
    let verdict;
    if(mood === "positive" && up || mood === "negative" && !up) verdict = "News and the model point the same way. That is some comfort, but neither is a guarantee.";
    else if(mood === "positive" || mood === "negative") verdict = "News and the model disagree, so be extra careful with this forecast. The model only sees past prices, not news.";
    else verdict = "The news gives no clear direction, so it neither supports nor contradicts the forecast.";
    text.innerHTML = `Last 7 days of headlines: <span class="badge positive">${s.positive} positive</span> <span class="badge neutral">${s.neutral} neutral</span> <span class="badge negative">${s.negative} negative</span> (mood: <b>${escapeHtml(mood)}</b>). ` +
      `The ${name} forecast points <b class="${up?"badge-good":"badge-warn"}">${up?"up":"down"} ${Math.abs(change).toFixed(2)}%</b>. ${verdict} ` +
      `<button class="btn link" onclick="document.getElementById('newsSymbols').value='${escapeHtml(d.yahooSymbol)}';showTab('market');getNews()">See the headlines →</button>`;
    box.style.display = "block";
  }catch(e){ if(my === MLSEQ) box.style.display = "none"; }
}

