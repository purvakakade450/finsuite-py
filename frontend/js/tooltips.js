/* ============================================================
   ⓘ TOOLTIPS linked to the Knowledge Center
   ============================================================ */
const GMAP = {};
function indexGlossaryItem(item){
  const m = item.term.match(/^(.*?)\s*\((.*)\)\s*$/);
  [item.term, ...(m ? [m[1], m[2]] : []), ...(item.also||[])].forEach(k=>{
    k = k.toLowerCase().trim();
    if(k && !GMAP[k]) GMAP[k] = item;
  });
}
function findTerm(t){
  const k = t.toLowerCase().trim();
  if(GMAP[k]) return GMAP[k];
  const hit = Object.keys(GMAP).find(x=>x.startsWith(k));
  return hit ? GMAP[hit] : null;
}
function showInfo(el){
  const pop = document.getElementById("infoPop");
  const item = findTerm(el.dataset.term);
  pop.innerHTML = `<button class="x" aria-label="Close" onclick="hideInfo()">×</button>` + (item
    ? `<h4>${escapeHtml(item.q)}</h4><p>${escapeHtml(item.a)}</p>${item.example?`<p class="meta"><b>Example:</b> ${escapeHtml(item.example)}</p>`:""}` +
      `<button class="btn link" style="padding:0;" onclick="openKnowledge('${escapeHtml(item.term).replace(/'/g,"\\'")}')">Open in Knowledge Center →</button>`
    : `<h4>${escapeHtml(el.dataset.term)}</h4><p class="muted">Loading the Knowledge Center… try again in a moment.</p>`);
  pop.hidden = false;
  const r = el.getBoundingClientRect();
  const w = Math.min(340, window.innerWidth - 24);
  pop.style.top = (r.bottom + window.scrollY + 6) + "px";
  pop.style.left = Math.max(12, Math.min(r.left + window.scrollX - 10, window.scrollX + window.innerWidth - w - 12)) + "px";
  pop.dataset.for = el.dataset.term;
}
function hideInfo(){ document.getElementById("infoPop").hidden = true; }
function openKnowledge(term){
  hideInfo();
  showTab("knowledge");
  const search = document.getElementById("kcSearch");
  if(search.value){ search.value = ""; search.dispatchEvent(new Event("input")); }
  const el = [...document.querySelectorAll(".acc-item")].find(x=>x.dataset.term === term);
  if(!el) return;
  el.classList.add("open", "flash");
  setTimeout(()=>{ el.scrollIntoView({block:"center", behavior:"smooth"}); }, 50);
  setTimeout(()=>el.classList.remove("flash"), 2200);
}
document.addEventListener("click", e=>{
  const icon = e.target.closest(".info");
  if(icon){
    e.preventDefault(); e.stopPropagation();          // don't toggle a checkbox or focus an input
    const pop = document.getElementById("infoPop");
    if(!pop.hidden && pop.dataset.for === icon.dataset.term) hideInfo(); else showInfo(icon);
    return;
  }
  if(!e.target.closest("#infoPop")) hideInfo();
}, true);
document.addEventListener("keydown", e=>{
  if((e.key==="Enter" || e.key===" ") && e.target.classList && e.target.classList.contains("info")){ e.preventDefault(); showInfo(e.target); }
  if(e.key==="Escape") hideInfo();
});

