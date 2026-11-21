/* ============================================================
   ACCOUNT — log in, password reset, saved data, alert channels
   (email, browser push, Telegram) and account deletion
   ============================================================ */
let AUTH_MODE = "login", RESET_TOKEN = null, MODAL_OPENER = null, TG_TIMER = null;

function openAccount(){
  MODAL_OPENER = document.activeElement;
  renderAccount();
  if(!AUTH.user && !RESET_TOKEN) showAuthForm("login");        // always start from the log-in form
  document.getElementById("accountModal").hidden = false;
  setTimeout(()=>{ const f = document.querySelector(AUTH.user ? "#accountEmailAlerts" : (RESET_TOKEN ? "#resetPassword" : "#authEmail")); f && f.focus(); }, 30);
}
function closeAccount(){
  document.getElementById("accountModal").hidden = true;
  clearTimeout(TG_TIMER);
  RESET_TOKEN = null; document.getElementById("resetMsg").textContent = "";
  if(MODAL_OPENER && MODAL_OPENER.focus) MODAL_OPENER.focus();
  MODAL_OPENER = null;
}
document.getElementById("accountModal").addEventListener("mousedown", e=>{ if(e.target.id === "accountModal") closeAccount(); });
document.addEventListener("keydown", e=>{
  const modal = document.getElementById("accountModal");
  if(modal.hidden) return;
  if(e.key === "Escape") closeAccount();
  if(e.key === "Tab"){                                    // keep keyboard focus inside the window
    const f = [...modal.querySelectorAll("a[href],button,input,select,textarea,summary,[tabindex]:not([tabindex='-1'])")]
      .filter(el=>!el.disabled && el.offsetParent !== null);
    if(!f.length) return;
    const first = f[0], last = f[f.length - 1];
    if(e.shiftKey && document.activeElement === first){ e.preventDefault(); last.focus(); }
    else if(!e.shiftKey && document.activeElement === last){ e.preventDefault(); first.focus(); }
  }
});

function setAuthMode(mode){
  AUTH_MODE = mode;
  document.getElementById("segLogin").classList.toggle("on", mode==="login");
  document.getElementById("segRegister").classList.toggle("on", mode==="register");
  document.getElementById("authNameField").hidden = mode !== "register";
  document.getElementById("forgotLink").hidden = mode !== "login";
  document.getElementById("authSubmit").textContent = mode==="login" ? "Log in" : "Create account";
  document.getElementById("authPassword").autocomplete = mode==="login" ? "current-password" : "new-password";
  document.getElementById("authError").textContent = "";
}
function showAuthForm(which){
  document.getElementById("authMain").hidden = which !== "login";
  document.getElementById("forgotForm").hidden = which !== "forgot";
  document.getElementById("resetForm").hidden = which !== "reset";
  const target = {login:"#authEmail", forgot:"#forgotEmail", reset:"#resetPassword"}[which];
  setTimeout(()=>{ const el = document.querySelector(target); el && el.focus(); }, 30);
}

function renderAccount(){
  const u = AUTH.user;
  document.getElementById("accountGuest").hidden = !!u;
  document.getElementById("accountUser").hidden = !u;
  document.getElementById("accountLabel").textContent = u ? u.name : "Log in";
  if(u){
    document.getElementById("accountName").textContent = u.name;
    document.getElementById("accountEmail").textContent = u.email;
    document.getElementById("accountVerify").innerHTML = u.email_verified ? `<span class="verified-badge">✓ Email confirmed</span>`
      : (AUTH.emailDelivery ? `Email not confirmed yet. <button type="button" class="btn link" style="padding:0;" onclick="sendVerification()">Send the confirmation email</button>` : "");
    document.getElementById("accountEmailAlerts").checked = u.email_alerts;
    document.getElementById("accountEmailNote").textContent = AUTH.emailDelivery ? "" : "Email sending is not set up on this server yet, so fired alerts show in the app instead.";
    document.getElementById("testEmailBtn").hidden = !AUTH.emailDelivery;
    const tgRow = document.getElementById("tgRow");
    tgRow.hidden = !AUTH.telegramAvailable;
    document.getElementById("tgStatus").textContent = u.telegram_linked ? "Linked. Alerts also go to your Telegram chat." : "Get alerts as Telegram messages.";
    document.getElementById("tgBtn").textContent = u.telegram_linked ? "Unlink" : "Link Telegram";
    if(u.telegram_linked) document.getElementById("tgLinkBox").hidden = true;
  }
  renderAlertMode();
  refreshPushUi();
}

async function submitAuth(e){
  e.preventDefault();
  const err = document.getElementById("authError"), btn = document.getElementById("authSubmit");
  err.textContent = ""; btn.disabled = true;
  try{
    const body = { email: document.getElementById("authEmail").value, password: document.getElementById("authPassword").value };
    if(AUTH_MODE === "register") body.name = document.getElementById("authName").value;
    const r = await api("POST", AUTH_MODE==="login" ? "/auth/login" : "/auth/register", body);
    await finishLogin(r, AUTH_MODE === "register" ? `Welcome, ${r.user.name}! Your watchlist, portfolio and alerts are now saved to your account.` : `Welcome back, ${r.user.name}!`);
    document.getElementById("authPassword").value = "";
  }catch(ex){ err.textContent = ex.message; }
  finally{ btn.disabled = false; }
}
async function finishLogin(r, message){
  AUTH.token = r.token; LS.set("fs-token", r.token);
  await startSession(r.user, true);
  closeAccount();
  toast(message);
}
async function submitForgot(e){
  e.preventDefault();
  const msg = document.getElementById("forgotMsg"), btn = document.getElementById("forgotSubmit");
  msg.textContent = ""; btn.disabled = true;
  try{ const r = await api("POST","/auth/forgot",{email: document.getElementById("forgotEmail").value}); msg.style.color = "var(--good)"; msg.textContent = r.message; }
  catch(ex){ msg.style.color = ""; msg.textContent = ex.message; }
  finally{ btn.disabled = false; }
}
async function submitReset(e){
  e.preventDefault();
  const msg = document.getElementById("resetMsg"), btn = document.getElementById("resetSubmit");
  msg.textContent = ""; btn.disabled = true;
  try{
    const r = await api("POST","/auth/reset",{token: RESET_TOKEN, password: document.getElementById("resetPassword").value});
    RESET_TOKEN = null; document.getElementById("resetPassword").value = "";
    showAuthForm("login");
    await finishLogin(r, "Your password was changed and you are logged in.");
  }catch(ex){ msg.textContent = ex.message; }
  finally{ btn.disabled = false; }
}
// Links in emails open the site with #reset=..., #verified or #verify-failed.
function handleAuthHash(){
  const h = location.hash, clean = ()=>history.replaceState(null, "", location.pathname + location.search);
  const m = h.match(/^#reset=(.+)$/);
  if(m){ RESET_TOKEN = decodeURIComponent(m[1]); clean(); openAccount(); showAuthForm("reset"); return true; }
  if(h === "#verified"){ clean(); toast("Email confirmed. Thank you!"); if(AUTH.user){ AUTH.user.email_verified = true; renderAccount(); } return true; }
  if(h === "#verify-failed"){ clean(); toast("That confirmation link is invalid or has expired. You can ask for a new one in your account.", "warn"); return true; }
  return false;
}

async function logout(){
  await api("POST","/auth/logout").catch(()=>{});
  AUTH.token = null; AUTH.user = null; LS.del("fs-token");
  ALERTS = LS.get("fs-alerts", []);
  renderAlerts(); renderAccount(); closeAccount();
  toast("Logged out. Your watchlist and portfolio stay saved in this browser.");
}
async function deleteAccount(){
  if(!confirm("Delete your FinSuite account and everything saved in it (watchlist, portfolio, chats, alerts)? This cannot be undone.")) return;
  try{
    const sub = await currentPushSub().catch(()=>null);
    if(sub) await sub.unsubscribe().catch(()=>{});
    await api("DELETE","/auth/me");
  }catch(e){ toast(e.message, "warn"); return; }
  AUTH.token = null; AUTH.user = null; LS.del("fs-token");
  ALERTS = LS.get("fs-alerts", []);
  renderAlerts(); renderAccount(); closeAccount();
  toast("Your account was deleted. Data kept in this browser, such as your watchlist, is still here.");
}
async function sendVerification(){
  try{ await api("POST","/auth/verify/send"); toast("We sent a confirmation link to " + AUTH.user.email + ". Check your inbox and spam folder."); }
  catch(e){ toast(e.message, "warn"); }
}
async function sendTestEmail(){
  const out = document.getElementById("testEmailResult"), btn = document.getElementById("testEmailBtn");
  btn.disabled = true; out.textContent = "Sending…";
  try{ const r = await api("POST","/auth/test-email"); out.textContent = `Sent to ${r.to}. Check your inbox (and the spam folder).`; }
  catch(e){ out.textContent = e.message; }
  finally{ btn.disabled = false; }
}
async function saveEmailAlerts(){
  try{ AUTH.user = (await api("PATCH","/auth/me",{email_alerts: document.getElementById("accountEmailAlerts").checked})).user; renderAccount(); }catch(e){ toast(e.message, "warn"); }
}

/* ---------- browser push notifications ---------- */
function pushSupported(){ return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window && window.isSecureContext; }
function urlBase64ToUint8Array(b64){
  const s = (b64 + "=".repeat((4 - b64.length % 4) % 4)).replace(/-/g, "+").replace(/_/g, "/");
  return Uint8Array.from(atob(s), c=>c.charCodeAt(0));
}
async function currentPushSub(){
  if(!pushSupported()) return null;
  const reg = await navigator.serviceWorker.getRegistration();
  return reg ? reg.pushManager.getSubscription() : null;
}
async function enablePush(){
  if(!AUTH.user){ toast("Log in first: push alerts are sent from your account."); openAccount(); return; }
  if(!pushSupported()){ toast("Push notifications need a secure (https) address and a browser that supports them.", "warn"); return; }
  if(await Notification.requestPermission() !== "granted"){ toast("Notifications are blocked for this site. Allow them in the browser's site settings.", "warn"); return; }
  const key = await api("GET","/push/key");
  if(!key.enabled){ toast("Push notifications are not available on this server.", "warn"); return; }
  const reg = await navigator.serviceWorker.ready;
  const sub = (await reg.pushManager.getSubscription()) ||
    await reg.pushManager.subscribe({userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(key.publicKey)});
  const j = sub.toJSON();
  await api("POST","/push/subscribe",{endpoint: j.endpoint, keys: j.keys});
  toast("Push notifications are on for this device.");
}
async function disablePush(){
  const sub = await currentPushSub();
  if(sub){ await api("POST","/push/unsubscribe",{endpoint: sub.endpoint}).catch(()=>{}); await sub.unsubscribe(); }
  toast("Push notifications are off for this device.");
}
async function togglePush(){
  try{ (await currentPushSub()) ? await disablePush() : await enablePush(); }
  catch(e){ toast("Push notifications: " + e.message, "warn"); }
  refreshPushUi();
}
async function refreshPushUi(){
  const available = !!AUTH.user && AUTH.pushAvailable && pushSupported();
  document.getElementById("pushRow").hidden = !available;
  const watch = document.getElementById("pushBtn2");
  watch.hidden = !available;
  if(!available) return;
  const on = !!(await currentPushSub().catch(()=>null));
  document.getElementById("pushStatus").textContent = on ? "On for this device, even when FinSuite is closed." : "Get alerts on this device even when FinSuite is closed.";
  document.getElementById("pushBtn").textContent = on ? "Turn off" : "Turn on";
  watch.textContent = on ? "Turn off push notifications" : "Turn on push notifications";
}

/* ---------- Telegram ---------- */
async function toggleTelegram(){
  try{
    if(AUTH.user.telegram_linked){
      await api("DELETE","/auth/telegram"); AUTH.user.telegram_linked = false; renderAccount(); toast("Telegram unlinked."); return;
    }
    const r = await api("POST","/auth/telegram/link");
    const box = document.getElementById("tgLinkBox");
    document.getElementById("tgLink").href = r.url;
    document.getElementById("tgCode").textContent = r.code;
    box.hidden = false;
    pollTelegram(Date.now() + r.expires_minutes * 60000);
  }catch(e){ toast(e.message, "warn"); }
}
function pollTelegram(deadline){
  clearTimeout(TG_TIMER);
  TG_TIMER = setTimeout(async ()=>{
    if(!AUTH.user || document.getElementById("accountModal").hidden || Date.now() > deadline) return;
    try{
      const me = await api("GET","/auth/me");
      AUTH.user = me.user;
      if(me.user.telegram_linked){ renderAccount(); toast("Telegram linked. Price alerts will also arrive there."); return; }
    }catch(e){}
    pollTelegram(deadline);
  }, 4000);
}

/* ---------- start-up: bring local and account data together ---------- */
// After login (fresh) or on page load with a saved session.
async function startSession(user, fresh){
  AUTH.user = user;
  try{
    const me = await api("GET","/auth/me");
    AUTH.user = me.user; AUTH.emailDelivery = me.email_delivery;
    AUTH.pushAvailable = me.push_available; AUTH.telegramAvailable = me.telegram_available;
    const data = await api("GET","/user/data");
    const serverWl = data.watchlist ? data.watchlist.value : null;
    const localWl = WATCHLIST.map(w=>w.symbol);
    const merged = fresh || !serverWl ? [...new Set([...(serverWl||[]), ...localWl])] : serverWl;
    WATCHLIST.splice(0, WATCHLIST.length, ...merged.map(symbol=>WATCHLIST.find(w=>w.symbol===symbol) || {symbol, price:null, change:null, changePercent:null, day:null}));
    saveWatchlist();
    if(data.portfolio && data.portfolio.value && data.portfolio.value.length){
      HOLDINGS.splice(0, HOLDINGS.length, ...data.portfolio.value); LS.set("fs-portfolio", HOLDINGS);
    }else if(HOLDINGS.length) saveHoldings();
    // the AI chat follows the user: take the saved one on a new device, otherwise keep this device's
    if(data.chat && Array.isArray(data.chat.value) && data.chat.value.length && !CHAT.history.length){
      CHAT.history = data.chat.value; LS.set("fs-chat", CHAT.history); renderChat();
    }else if(CHAT.history.length) syncChat();
    // move alerts made before logging in into the account
    const local = LS.get("fs-alerts", []).filter(a=>!a.triggered_at);
    for(const a of local) await api("POST","/alerts",{symbol:a.symbol, type:a.type, price:a.price}).catch(()=>{});
    if(local.length) LS.del("fs-alerts");
    mergeServerAlerts((await api("GET","/alerts")).alerts);
  }catch(e){
    if(/log in/i.test(e.message)){ AUTH.token = null; AUTH.user = null; LS.del("fs-token"); ALERTS = LS.get("fs-alerts", []); }
  }
  renderWatchlist(); refreshAlertSymbolSelect(); renderAlerts(); renderHoldings(); renderAccount();
}
