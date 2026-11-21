/* ============================================================
   START-UP: accessibility, installable app, first-visit work
   ============================================================ */
attachSymbolPicker("pfPicker", "pfSymbol", ()=>document.getElementById("pfQty").focus());
attachSymbolPicker("cmpPickerA", "cmpA", ()=>compareStocks());
attachSymbolPicker("cmpPickerB", "cmpB", ()=>compareStocks());

const FIRST_SHOWN = new Set();
function onTabShown(name){
  if(name === "sources") loadLiveStatus();                // fresh every visit (the server caches it for a minute)
  if(FIRST_SHOWN.has(name)) return;
  FIRST_SHOWN.add(name);
  if(name === "invest") calcInvest();                     // draws its chart only when the tab is first opened
  if(name === "fx"){ convertFx(); compareStocks(); }
  if(name === "mf"){ if(!document.getElementById("mfQuery").value) document.getElementById("mfQuery").value = "parag parikh flexi cap"; searchFunds(); }
  if(name === "tracker" && HOLDINGS.length) valuePortfolio();
}

/* ---------- accessibility ---------- */
function enhanceAccessibility(root){
  root = root || document;
  // every field label points at its input, so screen readers announce it and a click on the label focuses the input
  let n = 0;
  root.querySelectorAll(".field").forEach(f=>{
    const label = f.querySelector(":scope > label"), ctl = f.querySelector("input, select, textarea");
    if(label && ctl && !label.htmlFor){ if(!ctl.id) ctl.id = "fld" + (++n) + "-" + Math.random().toString(36).slice(2, 6); label.htmlFor = ctl.id; }
  });
  root.querySelectorAll("th:not([scope])").forEach(th=>th.setAttribute("scope", "col"));
  root.querySelectorAll("canvas:not([role])").forEach(c=>{
    const h = c.closest(".card") && c.closest(".card").querySelector("h2");
    c.setAttribute("role", "img");
    c.setAttribute("aria-label", "Chart: " + ((h && h.textContent.trim()) || (c.closest("#mfFundCard") ? "mutual fund NAV and SIP growth" : "data")));
  });
  root.querySelectorAll(".result-box:not([aria-live]), .insight-box:not([aria-live])").forEach(el=>el.setAttribute("aria-live", "polite"));
}
(function setupAccessibility(){
  document.querySelectorAll(".panel").forEach(p=>{
    p.tabIndex = -1;
    const btn = document.querySelector(`.tab[data-tab="${p.id.replace("panel-", "")}"]`);
    if(btn){ p.setAttribute("role", "region"); p.setAttribute("aria-label", btn.childNodes[0].textContent.trim()); }
  });
  document.querySelectorAll(".nav-group-btn").forEach(b=>{ b.setAttribute("aria-haspopup", "true"); b.setAttribute("aria-expanded", "false"); });
  enhanceAccessibility();
  // tables and charts are drawn later by the tools, so tidy those up as they appear
  let queued = false;
  new MutationObserver(()=>{ if(!queued){ queued = true; requestAnimationFrame(()=>{ queued = false; enhanceAccessibility(document.getElementById("main")); }); } })
    .observe(document.getElementById("main"), {childList: true, subtree: true});
})();

/* ---------- installable app + offline ---------- */
let INSTALL_EVENT = null;
if("serviceWorker" in navigator && window.isSecureContext){
  window.addEventListener("load", ()=>navigator.serviceWorker.register("/sw.js").then(()=>refreshPushUi()).catch(()=>{}));
}
window.addEventListener("beforeinstallprompt", e=>{ e.preventDefault(); INSTALL_EVENT = e; document.getElementById("installBtn").hidden = false; });
document.getElementById("installBtn").addEventListener("click", async ()=>{
  if(!INSTALL_EVENT) return;
  INSTALL_EVENT.prompt();
  await INSTALL_EVENT.userChoice;
  INSTALL_EVENT = null; document.getElementById("installBtn").hidden = true;
});
window.addEventListener("appinstalled", ()=>toast("FinSuite is installed. Open it from your home screen or start menu."));

/* ---------- go ---------- */
(function startup(){
  const d = new Date(); d.setFullYear(d.getFullYear() - 3);
  document.getElementById("mfStart").value = d.toISOString().slice(0,10);
  renderBudgetItems(); renderHoldings(); renderWatchlist(); renderAlerts(); renderAccount();
  renderChat();
  handleAuthHash();                                       // links from emails: reset password, confirm email
  const first = location.hash.slice(1) || LS.get("fs-tab") || "report";
  showTab(document.getElementById("panel-"+first) ? first : "report", {noHash:!location.hash, keepScroll:true});
  window.addEventListener("hashchange", ()=>{
    if(handleAuthHash()) return;
    const t = location.hash.slice(1);
    if(t && document.getElementById("panel-"+t)) showTab(t, {noHash:true});
  });
  if(AUTH.token) startSession(null, false);
  api("GET","/api/status").then(st=>{ document.getElementById("accountTempNote").hidden = st.accounts_persistent !== false; }).catch(()=>{});
})();
