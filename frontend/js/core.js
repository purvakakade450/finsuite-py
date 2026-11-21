const CHARTS = {};
const PALETTE = ["#1F3A68","#9C7A3C","#5B7DB1","#2E7D4F","#A63232","#7A6A9E","#C49A52","#8A94A8","#3F6E78","#B5654A"];
function themeColors(){
  const cs = getComputedStyle(document.documentElement);
  return { muted: cs.getPropertyValue("--muted").trim() || "#64708A", grid: cs.getPropertyValue("--border").trim() || "#E3E8F0",
           card: cs.getPropertyValue("--card").trim() || "#fff" };
}
function destroyChart(k){ if(CHARTS[k]){ CHARTS[k].destroy(); delete CHARTS[k]; } }
function makeChart(canvasId, key, config){
  destroyChart(key);
  CHARTS[key] = new Chart(document.getElementById(canvasId), config);
  return CHARTS[key];
}
function barChart(canvasId, key, labels, data, opts={}){
  const t = themeColors();
  const datasets = opts.datasets || [{ data, backgroundColor: opts.color||"#1F3A68", borderRadius:5, maxBarThickness:50 }];
  return makeChart(canvasId, key, {
    type:"bar",
    data:{ labels, datasets },
    options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:!!opts.datasets, labels:{color:t.muted,font:{size:11}}}},
      scales:{ x:{ticks:{color:t.muted},grid:{display:false}}, y:{ticks:{color:t.muted},grid:{color:t.grid},beginAtZero:true} } }
  });
}
function lineChart(canvasId, key, labels, datasets, opts={}){
  const t = themeColors();
  return makeChart(canvasId, key, {
    type:"line",
    data:{ labels, datasets },
    options:{ responsive:true, maintainAspectRatio:false, interaction:{mode:"index", intersect:false},
      plugins:{legend:{labels:{color:t.muted,font:{size:11}}}},
      scales:{ x:{ticks:{color:t.muted,maxTicksLimit:8},grid:{display:false}}, y:{ticks:{color:t.muted},grid:{color:t.grid}, ...(opts.y||{})} } }
  });
}
function doughnutChart(canvasId, key, labels, data){
  const t = themeColors();
  return makeChart(canvasId, key, {
    type:"doughnut",
    data:{ labels, datasets:[{ data, backgroundColor: labels.map((_,i)=>PALETTE[i%PALETTE.length]), borderColor:t.card, borderWidth:2 }] },
    options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{position:"right", labels:{color:t.muted,font:{size:11},boxWidth:12}}} }
  });
}
// Re-colour axes and legends of every chart already drawn (after a theme switch).
function applyChartTheme(){
  const t = themeColors();
  Object.values(CHARTS).forEach(c=>{
    const o = c.options;
    if(o.plugins && o.plugins.legend && o.plugins.legend.labels) o.plugins.legend.labels.color = t.muted;
    Object.values(o.scales||{}).forEach(sc=>{ if(sc.ticks) sc.ticks.color = t.muted; if(sc.grid && sc.grid.color) sc.grid.color = t.grid; });
    if(c.config.type === "doughnut") c.data.datasets.forEach(d=>d.borderColor = t.card);
    c.update("none");
  });
}
async function api(method, path, body){
  const headers = {};
  if(body) headers["Content-Type"] = "application/json";
  if(AUTH.token) headers["Authorization"] = "Bearer " + AUTH.token;
  const res = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if(!res.ok){
    const e = await res.json().catch(()=>({detail:res.statusText}));
    throw new Error(typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail));
  }
  return res.json();
}
function renderTable(id, rows, cols, limit=20){
  const table = document.getElementById(id);
  const shown = rows.slice(0, limit);
  table.innerHTML = `<tr>${cols.map(c=>`<th>${c}</th>`).join("")}</tr>` +
    shown.map(r=>`<tr>${cols.map(c=>`<td>${r[c]===null||r[c]===undefined?"—":r[c]}</td>`).join("")}</tr>`).join("") +
    (rows.length>limit ? `<tr><td colspan="${cols.length}" style="text-align:center;color:var(--muted);">…and ${rows.length-limit} more</td></tr>` : "");
}

/* ---------------- tabs, grouped menu, saved settings ---------------- */
// localStorage can be missing or blocked (private mode); the app still works without it.
const LS = {
  get(k, fallback=null){ try{ const v = localStorage.getItem(k); return v===null ? fallback : JSON.parse(v); }catch(e){ return fallback; } },
  set(k, v){ try{ localStorage.setItem(k, JSON.stringify(v)); }catch(e){} },
  del(k){ try{ localStorage.removeItem(k); }catch(e){} },
};
const AUTH = { token: LS.get("fs-token"), user: null, emailDelivery: false, pushAvailable: false, telegramAvailable: false };

function closeNavMenus(except){ document.querySelectorAll(".nav-group.open").forEach(g=>{ if(g!==except){ g.classList.remove("open"); g.querySelector(".nav-group-btn").setAttribute("aria-expanded","false"); } }); }
function showTab(name, opts={}){
  const btn = document.querySelector(`.tab[data-tab="${name}"]`);
  const panel = document.getElementById("panel-"+name);
  if(!btn || !panel) return;
  document.querySelectorAll(".tab").forEach(b=>{ b.classList.remove("active"); b.removeAttribute("aria-current"); });
  document.querySelectorAll(".panel").forEach(p=>p.classList.remove("active"));
  document.querySelectorAll(".nav-group").forEach(g=>{ g.classList.remove("has-active"); g.querySelector(".nav-current").textContent = ""; });
  btn.classList.add("active"); btn.setAttribute("aria-current","page");
  panel.classList.add("active");
  if(opts.focus) panel.focus({preventScroll:true});      // keyboard and screen-reader users land in the new section
  const group = btn.closest(".nav-group");
  group.classList.add("has-active");
  const label = btn.childNodes[0].textContent.trim();
  group.querySelector(".nav-current").textContent = "· " + label;
  document.getElementById("navCurrent").textContent = label;
  closeNavMenus(); document.body.classList.remove("nav-open");
  document.getElementById("navToggle").setAttribute("aria-expanded","false");
  LS.set("fs-tab", name);
  if(!opts.noHash) history.replaceState(null, "", "#"+name);
  if(!opts.keepScroll) window.scrollTo({top:0});
  runAutoRefresh(true);
  if(typeof onTabShown === "function") onTabShown(name);
}
document.querySelectorAll(".tab").forEach(btn=> btn.addEventListener("click", ()=> showTab(btn.dataset.tab, {focus:true})));
document.querySelectorAll(".nav-group").forEach(g=>{
  g.querySelector(".nav-group-btn").addEventListener("click", e=>{ e.stopPropagation(); closeNavMenus(g); g.classList.toggle("open"); e.currentTarget.setAttribute("aria-expanded", String(g.classList.contains("open"))); });
});
document.addEventListener("click", e=>{ if(!e.target.closest(".nav-group")) closeNavMenus(); });
document.addEventListener("keydown", e=>{ if(e.key==="Escape"){ closeNavMenus(); document.body.classList.remove("nav-open"); } });
document.getElementById("navToggle").addEventListener("click", ()=>{
  const open = document.body.classList.toggle("nav-open");
  document.getElementById("navToggle").setAttribute("aria-expanded", String(open));
});

/* ---------------- dark mode ---------------- */
function currentTheme(){
  const set = document.documentElement.dataset.theme;
  return set || "light";   // light unless the user picks dark
}
function paintThemeButton(){
  const dark = currentTheme()==="dark";
  const b = document.getElementById("themeToggle");
  b.innerHTML = dark ? '<svg class="ico" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>' : '<svg class="ico" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>';
  b.title = dark ? "Switch to light mode" : "Switch to dark mode";
  if(window.Chart){ Chart.defaults.color = themeColors().muted; applyChartTheme(); }
}
document.getElementById("themeToggle").addEventListener("click", ()=>{
  const next = currentTheme()==="dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try{ localStorage.setItem("fs-theme", next); }catch(e){}
  paintThemeButton();
});
paintThemeButton();

