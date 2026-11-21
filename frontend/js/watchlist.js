/* ============================================================
   14 WATCHLIST & PRICE ALERTS (reuses GET /market/quote)
   The watchlist is saved in this browser and, when logged in, in the
   account (PUT /user/data/watchlist). Guest alerts live in this browser and
   are checked while FinSuite is open; a logged-in user's alerts are stored
   on the server (/alerts) and also checked in the background with email.
   Each alert fires once, then waits to be re-armed.
   ============================================================ */
const WATCHLIST = LS.get("fs-watchlist", []).map(symbol=>({symbol, price:null, change:null, changePercent:null, day:null}));
let ALERTS = AUTH.token ? [] : LS.get("fs-alerts", []);
function saveWatchlist(){
  const symbols = WATCHLIST.map(w=>w.symbol);
  LS.set("fs-watchlist", symbols);
  if(AUTH.user) api("PUT","/user/data/watchlist",{value:symbols}).catch(()=>{});
}
function saveLocalAlerts(){ if(!AUTH.user) LS.set("fs-alerts", ALERTS); }
function addWatchlistSymbol(picked){
  const symbol = (picked || document.getElementById("wlSymbol").value).trim();
  if(!symbol){ document.querySelector("#wlPicker .picker-btn").click(); return; }
  if(!WATCHLIST.some(w=>w.symbol===symbol)){ WATCHLIST.push({symbol, price:null, change:null, changePercent:null, day:null}); saveWatchlist(); }
  renderWatchlist(); refreshAlertSymbolSelect(); refreshWatchlist();
}
function removeWatchlistSymbol(i){ WATCHLIST.splice(i,1); saveWatchlist(); renderWatchlist(); refreshAlertSymbolSelect(); }
function renderWatchlist(){
  const table = document.getElementById("wlTable");
  table.innerHTML = `<tr><th>Symbol</th><th>Price</th><th>Change</th><th>%</th><th>As of</th><th></th></tr>` +
    (WATCHLIST.length ? WATCHLIST.map((w,i)=>`<tr><td><b>${escapeHtml(w.symbol)}</b>${w.name?`<div class="muted" style="margin:0;font-size:12px;">${escapeHtml(w.name)}</div>`:""}</td><td>${w.price??"—"}${w.stale?` <span class="stale-note" title="Live data is unavailable; this is the last saved price">delayed</span>`:""}</td><td>${w.change??"—"}</td><td>${w.changePercent??"—"}</td><td>${w.day??"—"}</td><td><button class="btn secondary sm" onclick="removeWatchlistSymbol(${i})">Remove</button></td></tr>`).join("")
      : `<tr><td colspan="6" class="muted">Your watchlist is empty. Choose a company above to add it.</td></tr>`);
}
async function refreshWatchlist(){
  for(const w of WATCHLIST){
    try{
      const q = await api("GET", `/market/quote?symbol=${encodeURIComponent(w.symbol)}`);
      if(q && q.price!=null) Object.assign(w, { name:q.name, currency:q.currency, price:q.price, change:q.change, changePercent:q.changePercent, stale:!!q.stale, day:q.asOf?new Date(q.asOf).toLocaleString():"" });
      else w.price = "no data";
    }catch(e){ w.price = "Error"; }
  }
  renderWatchlist();
  checkAlerts();
}
function refreshAlertSymbolSelect(){
  const sel = document.getElementById("alertSymbol");
  sel.innerHTML = WATCHLIST.map(w=>`<option value="${escapeHtml(w.symbol)}">${escapeHtml(w.symbol)}</option>`).join("") || `<option value="">Add a symbol to the watchlist first</option>`;
}
async function addPriceAlert(){
  const symbol = document.getElementById("alertSymbol").value;
  if(!symbol){ alert("Add a symbol to the watchlist first."); return; }
  const a = { symbol, type:document.getElementById("alertType").value, price:+document.getElementById("alertPrice").value };
  if(!(a.price > 0)){ alert("Enter a target price above 0."); return; }
  if(AUTH.user){
    try{ ALERTS.push(await api("POST","/alerts",a)); }catch(e){ alert(e.message); return; }
  }else{
    ALERTS.push({ ...a, id:"l"+Date.now(), triggered_at:null, triggered_price:null });
    saveLocalAlerts();
  }
  renderAlerts();
  checkAlerts();
}
async function removePriceAlert(i){
  const a = ALERTS[i];
  if(AUTH.user && typeof a.id === "number") await api("DELETE", `/alerts/${a.id}`).catch(()=>{});
  ALERTS.splice(i,1); saveLocalAlerts(); renderAlerts();
}
async function rearmAlert(i){
  const a = ALERTS[i];
  if(AUTH.user && typeof a.id === "number") await api("POST", `/alerts/${a.id}/rearm`).catch(()=>{});
  Object.assign(a, { triggered_at:null, triggered_price:null, seen:0 });
  saveLocalAlerts(); renderAlerts(); checkAlerts();
}
function renderAlerts(){
  const table = document.getElementById("alertTable");
  const cur = sym => currencySymbol((WATCHLIST.find(x=>x.symbol===sym)||{}).currency || "INR");
  table.innerHTML = `<tr><th>Symbol</th><th>Condition</th><th>Status</th><th></th></tr>` +
    (ALERTS.length ? ALERTS.map((a,i)=>`<tr><td>${escapeHtml(a.symbol)}</td><td>${a.type==="above"?"Rises above":"Falls below"} ${cur(a.symbol)}${a.price}</td>` +
      `<td>${a.triggered_at ? `<b class="badge-warn">Triggered</b> at ${cur(a.symbol)}${a.triggered_price} · ${new Date(a.triggered_at).toLocaleString()}` : "Watching"}</td>` +
      `<td>${a.triggered_at?`<button class="btn secondary sm" onclick="rearmAlert(${i})">Re-arm</button> `:""}<button class="btn secondary sm" onclick="removePriceAlert(${i})">Remove</button></td></tr>`).join("")
      : `<tr><td colspan="4" class="muted">No alerts yet.</td></tr>`);
}
function renderAlertMode(){
  if(typeof refreshPushUi === "function") refreshPushUi();
  const box = document.getElementById("alertMode");
  if(AUTH.user){
    box.innerHTML = `<span class="lbl">Background alerts are on</span>Your alerts are saved to your account and checked on the server every few minutes, even when FinSuite is closed. ` +
      (AUTH.emailDelivery ? (AUTH.user.email_alerts ? `When one fires, we email <b>${escapeHtml(AUTH.user.email)}</b>.` : `Email is switched off in your account settings.`)
                          : `Email delivery is not set up on this server yet, so fired alerts are shown here the next time you open FinSuite.`);
  }else{
    box.innerHTML = `<span class="lbl">Alerts while this page is open</span>Your alerts are saved in this browser and checked about once a minute while FinSuite is open. ` +
      `<button class="btn link" onclick="openAccount()">Log in or create an account</button> to have them checked in the background and emailed to you.`;
  }
  const nb = document.getElementById("notifyBtn");
  if(!("Notification" in window)) nb.hidden = true;
  else if(Notification.permission === "granted"){ nb.textContent = "Desktop notifications on"; nb.disabled = true; }
}
function enableNotifications(){
  if(!("Notification" in window)) return;
  Notification.requestPermission().then(()=>renderAlertMode());
}
function notifyAlert(a){
  const word = a.type==="above" ? "rose above" : "fell below";
  const msg = `${a.symbol} ${word} ${a.price} (now ${a.triggered_price}).`;
  toast("Price alert: " + msg, "warn");
  try{ if("Notification" in window && Notification.permission === "granted") new Notification("FinSuite price alert", { body: msg }); }catch(e){}
}
// Replace the alert list with the server's copy; announce fired alerts not seen yet.
function mergeServerAlerts(list){
  ALERTS = list;
  const fresh = list.filter(a=>a.triggered_at && !a.seen);
  fresh.forEach(a=>{ notifyAlert(a); a.seen = 1; });
  if(fresh.length) api("POST","/alerts/seen").catch(()=>{});
  renderAlerts();
}
async function checkAlerts(){
  if(AUTH.user){
    if(!ALERTS.some(a=>!a.triggered_at)) return;
    try{ mergeServerAlerts((await api("POST","/alerts/check")).alerts); }catch(e){}
    return;
  }
  let changed = false;
  ALERTS.forEach(a=>{
    const w = WATCHLIST.find(x=>x.symbol===a.symbol);
    if(a.triggered_at || !w || typeof w.price !== "number") return;
    if(a.type==="above" ? w.price > a.price : w.price < a.price){
      Object.assign(a, { triggered_at:new Date().toISOString(), triggered_price:w.price });
      notifyAlert(a); changed = true;
    }
  });
  if(changed) saveLocalAlerts();
  renderAlerts();
}
// Used while other tabs are open: fetch prices only for symbols with a pending alert.
async function checkAlertsNow(){
  const pending = ALERTS.filter(a=>!a.triggered_at);
  if(!pending.length) return;
  if(!AUTH.user){
    for(const sym of new Set(pending.map(a=>a.symbol))){
      const w = WATCHLIST.find(x=>x.symbol===sym);
      if(!w) continue;
      try{ const q = await api("GET", `/market/quote?symbol=${encodeURIComponent(sym)}`); if(q.price!=null) Object.assign(w, {price:q.price, currency:q.currency, name:q.name}); }catch(e){}
    }
  }
  checkAlerts();
}
refreshAlertSymbolSelect();

