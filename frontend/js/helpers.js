/* ============================================================
   SHARED HELPERS (phase 2)
   ============================================================ */
const LAST = {};   // latest result of each tool, used by the download buttons
const rupees = v => v==null || isNaN(v) ? "—" : "₹" + Math.round(v).toLocaleString("en-IN");
const pct = (v, d=2) => v==null || isNaN(v) ? "—" : `${(+v).toFixed(d)}%`;
const signed = (v, f=rupees) => v==null ? "—" : (v>=0 ? "+" : "−") + f(Math.abs(v));
const val = id => +document.getElementById(id).value || 0;
function readInputs(map){ return Object.entries(map).map(([label,id])=>[label, document.getElementById(id).value]); }
function showExport(key, on=true){ const el = document.getElementById("export-"+key); if(el) el.hidden = !on; }
function toast(msg, kind=""){
  const el = document.createElement("div");
  el.className = "toast " + kind; el.textContent = msg;
  document.getElementById("toasts").appendChild(el);
  setTimeout(()=>el.remove(), 8000);
}
function showError(id, e){ const el = document.getElementById(id); el.hidden = !e; if(e){ el.className = "result-box sell"; el.textContent = "Error: " + (e.message||e); } }
function setHidden(ids, hidden){ ids.forEach(id=>{ const el = document.getElementById(id); if(el) el.hidden = hidden; }); }

