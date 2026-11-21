/* ============================================================
   AUTO-REFRESH for live market data (sections 11 & 14)
   Each job only runs while its tab is open, the browser tab is visible
   and its checkbox is ticked — so nothing is fetched in the background.
   ============================================================ */
const AUTO_JOBS = [
  { panel:"market",    toggle:"quoteAuto", every:30*1000,   run:getQuote,         last:0 },
  { panel:"market",    toggle:"quoteAuto", every:10*60*1000, run:getDailyHistory, last:0 },
  { panel:"market",    toggle:"newsAuto",  every:5*60*1000, run:getNews,          last:0 },
  { panel:"watchlist", toggle:"wlAuto",    every:30*1000,   run:()=>WATCHLIST.length && refreshWatchlist(), last:0 },
  { panel:"tracker",   toggle:"pfAuto",    every:60*1000,   run:()=>HOLDINGS.length && valuePortfolio(true), last:0 },
  // Alerts are also checked while any other tab is open.
  { panel:null,        toggle:null,        every:60*1000,   run:()=>!document.getElementById("panel-watchlist").classList.contains("active") && checkAlertsNow(), last:Date.now() },
];
function runAutoRefresh(force=false){
  if(document.hidden) return;
  const now = Date.now();
  for(const job of AUTO_JOBS){
    if(job.panel){
      const panel = document.getElementById("panel-"+job.panel);
      const toggle = document.getElementById(job.toggle);
      if(!panel || !panel.classList.contains("active") || !toggle || !toggle.checked) continue;
    }
    if(force || now - job.last >= job.every){ job.last = now; job.run(); }
  }
}
setInterval(runAutoRefresh, 5000);
document.addEventListener("visibilitychange", ()=>runAutoRefresh());

