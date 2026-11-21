/* ============================================================
   10 KNOWLEDGE CENTER -> GET /knowledge/glossary?lang=en|hi|mr
   Hindi and Marathi are translated once by the AI model and kept on the
   server; until an entry is ready its English text is shown.
   ============================================================ */
const KC_TEXT = {
  en: {example:"Example:", where:"Where in FinSuite:", empty:"No matching term. Try a different word."},
  hi: {example:"उदाहरण:", where:"FinSuite में कहाँ:", empty:"कोई शब्द नहीं मिला। कोई दूसरा शब्द आज़माइए।"},
  mr: {example:"उदाहरण:", where:"FinSuite मध्ये कुठे:", empty:"कोणताही शब्द सापडला नाही. दुसरा शब्द वापरून पहा."},
};
const KC_GROUPS = {
  hi: {"1. Money basics":"1. पैसे की बुनियादी बातें","2. Ratios and financial health":"2. अनुपात और वित्तीय सेहत","3. Loans and credit":"3. लोन और क्रेडिट",
       "4. The stock market":"4. शेयर बाज़ार","5. Planning your goals":"5. अपने लक्ष्यों की योजना","6. Machine learning prediction":"6. मशीन लर्निंग पूर्वानुमान",
       "7. Tax, loans and budgeting":"7. टैक्स, लोन और बजट","8. Mutual funds, portfolios and retirement":"8. म्यूचुअल फंड, पोर्टफोलियो और रिटायरमेंट","9. Charts, news and currencies":"9. चार्ट, खबरें और मुद्राएँ"},
  mr: {"1. Money basics":"1. पैशांची मूलतत्त्वे","2. Ratios and financial health":"2. गुणोत्तर आणि आर्थिक आरोग्य","3. Loans and credit":"3. कर्ज आणि क्रेडिट",
       "4. The stock market":"4. शेअर बाजार","5. Planning your goals":"5. तुमच्या ध्येयांचे नियोजन","6. Machine learning prediction":"6. मशीन लर्निंग अंदाज",
       "7. Tax, loans and budgeting":"7. कर, कर्ज आणि बजेट","8. Mutual funds, portfolios and retirement":"8. म्युच्युअल फंड, पोर्टफोलियो आणि निवृत्ती","9. Charts, news and currencies":"9. चार्ट, बातम्या आणि चलने"},
};
let KC_SEQ = 0, KC_TIMER = null;

async function loadKnowledge(lang){
  lang = lang || LS.get("fs-lang", "en");
  const my = ++KC_SEQ, list = document.getElementById("kcList"), note = document.getElementById("kcLangNote");
  clearTimeout(KC_TIMER);
  const t = KC_TEXT[lang] || KC_TEXT.en;
  try{
    const r = await api("GET", `/knowledge/glossary?lang=${lang}`);
    if(my !== KC_SEQ) return;
    const wasOpen = new Set([...list.querySelectorAll(".acc-item.open")].map(e=>e.dataset.term));
    list.innerHTML = "";
    Object.keys(GMAP).forEach(k=>delete GMAP[k]);          // the ⓘ pop-ups follow the chosen language too
    let group = null, groupEl = null;
    r.glossary.forEach(item=>{
      indexGlossaryItem(item);
      if(item.group !== group){
        group = item.group;
        groupEl = document.createElement("div");
        groupEl.className = "kc-group";
        groupEl.innerHTML = `<h3 class="kc-title">${escapeHtml((KC_GROUPS[lang] || {})[group] || group)}</h3>`;
        list.appendChild(groupEl);
      }
      const el = document.createElement("div");
      el.className = "acc-item" + (wasOpen.has(item.term) ? " open" : "");
      el.dataset.term = item.term;
      el.dataset.text = (item.q+" "+item.a+" "+(item.example||"")+" "+(item.also||[]).join(" ")+" "+item.term).toLowerCase();
      el.innerHTML = `<button class="acc-q" aria-expanded="${wasOpen.has(item.term)}"><span>${escapeHtml(item.q)}</span><span class="chev" aria-hidden="true">+</span></button>` +
        `<div class="acc-a"><p>${escapeHtml(item.a)}</p>` +
        (item.example ? `<p><b>${t.example}</b> ${escapeHtml(item.example)}</p>` : "") +
        (item.where ? `<p class="muted"><b>${t.where}</b> ${escapeHtml(item.where)}</p>` : "") + `</div>`;
      const q = el.querySelector(".acc-q");
      q.addEventListener("click", ()=>{ el.classList.toggle("open"); q.setAttribute("aria-expanded", String(el.classList.contains("open"))); });
      groupEl.appendChild(el);
    });
    const empty = document.createElement("div");
    empty.className = "muted kc-empty"; empty.hidden = true; empty.textContent = t.empty;
    list.appendChild(empty);
    applyKnowledgeFilter();

    note.hidden = lang === "en";
    if(lang !== "en"){
      if(!r.available) note.textContent = "Hindi and Marathi translations are made by the AI service, which is not switched on on this server. Showing English.";
      else if(r.translated < r.total){
        note.textContent = `Translating… ${r.translated} of ${r.total} entries are ready; the rest are shown in English for now.`;
        if(r.pending) KC_TIMER = setTimeout(()=>loadKnowledge(lang), 8000);
      }else note.textContent = "Translated by AI. The wording may not be perfect; the English version is the reference.";
    }
  }catch(e){ if(my === KC_SEQ) list.textContent = "Could not load the Knowledge Center: " + e.message; }
}

function applyKnowledgeFilter(){
  const list = document.getElementById("kcList");
  const q = document.getElementById("kcSearch").value.trim().toLowerCase();
  let shown = 0;
  list.querySelectorAll(".kc-group").forEach(g=>{
    let any = false;
    g.querySelectorAll(".acc-item").forEach(it=>{
      const hit = !q || it.dataset.text.includes(q);
      it.hidden = !hit; any = any || hit; if(hit) shown++;
      if(q && hit) it.classList.add("open"); else if(!q && it.dataset.searchOpened){ it.classList.remove("open"); }
      if(q && hit) it.dataset.searchOpened = "1"; else delete it.dataset.searchOpened;
    });
    g.hidden = !any;
  });
  const empty = list.querySelector(".kc-empty");
  if(empty) empty.hidden = shown > 0;
}
document.getElementById("kcSearch").addEventListener("input", applyKnowledgeFilter);
document.getElementById("kcLang").addEventListener("change", e=>setLanguage(e.target.value));
document.getElementById("kcLang").value = LS.get("fs-lang", "en");
document.addEventListener("DOMContentLoaded", ()=>loadKnowledge());   // after every script has run
