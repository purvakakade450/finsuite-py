/* ============================================================
   16 ABOUT -> GET /about
   ============================================================ */
(async function loadAbout(){
  try{
    const r = await api("GET","/about");
    document.getElementById("aboutOut").innerHTML = `
      <div class="result-box">${r.about_text}</div>
      <div class="card" style="margin-top:12px;background:rgba(31,58,104,.06);">
        <h3 style="margin-top:0;">Why this matters</h3>
        <p style="margin:0;">${r.why_it_matters}</p>
      </div>
      <div class="row" style="margin-top:12px;">
        <div class="field"><span class="field-label">Version</span><div>${r.version}</div></div>
      </div>`;
  }catch(e){ document.getElementById("aboutOut").textContent = "Could not load: "+e.message; }
})();


async function loadLiveStatus(){
  const box = document.getElementById("liveStatus");
  box.textContent = "Checking the data sources…";
  const item = (state, title, text)=>`<div class="status-item"><span class="dot ${state}"></span><div><b>${escapeHtml(title)}</b>${text}</div></div>`;
  try{
    const h = await api("GET", "/api/health?deep=1");
    box.innerHTML = Object.entries(h.sources).map(([name, s])=>
        item(s.ok ? "ok" : "bad", name, s.ok ? `Working (${s.ms} ms)` : `Not responding${s.error ? ": " + escapeHtml(s.error) : ""}`)).join("") +
      item(h.ai_assistant ? "ok" : "off", "AI assistant", h.ai_assistant ? "On" : "Off, answers come from the Knowledge Center") +
      item(h.email_alerts ? "ok" : "off", "Email alerts", h.email_alerts ? "On" : "Not set up on this server") +
      item(h.accounts_persistent ? "ok" : "off", "Saved accounts", h.accounts_persistent ? "Stored permanently" : "Temporary on this host");
  }catch(e){ box.textContent = "Could not check: " + e.message; }
}
