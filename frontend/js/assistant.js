/* ============================================================
   03 AI ASSISTANT -> POST /assistant/chat, POST /assistant/snapshot
   ============================================================ */
/* AI chat -> POST /assistant/ai-chat (streams newline-delimited JSON events).
   The conversation is kept in this browser and sent back with each question. */
const CHAT = { history: LS.get("fs-chat", []), busy: false, ctrl: null, lang: LS.get("fs-lang", "en") };
const CHAT_I18N = {
  en: {
    hello: "Hello! I'm your FinSuite finance assistant. Ask me about stocks, mutual funds, tax, loans, budgeting, retirement or any finance term, and I'll work it out with live data where I can.",
    placeholder: "Ask a question, e.g. Which tax regime is better on a ₹18 lakh salary?", send: "Send", stop: "Stop", thinking: "Thinking…",
    suggestions: [
      "Is TCS overbought right now? Check the RSI and news.",
      "Old vs new tax regime on an ₹18 lakh salary with ₹1.5 lakh in 80C?",
      "EMI on a ₹30 lakh home loan at 8.5% for 20 years, and what if I prepay ₹2 lakh after a year?",
      "How is my saved portfolio doing today?",
      "What would a ₹5,000 monthly SIP in Parag Parikh Flexi Cap have become over 3 years?",
      "I'm 28, spend ₹45,000 a month and invest ₹25,000. When can I retire?",
    ],
  },
  hi: {
    hello: "नमस्ते! मैं आपका FinSuite वित्त सहायक हूँ। शेयर, म्यूचुअल फंड, टैक्स, लोन, बजट, रिटायरमेंट या किसी भी वित्तीय शब्द के बारे में पूछिए। जहाँ संभव होगा, मैं लाइव डेटा से जवाब निकालूँगा।",
    placeholder: "अपना सवाल लिखिए, जैसे: ₹18 लाख की सैलरी पर कौन सा टैक्स रिजीम बेहतर है?", send: "भेजें", stop: "रोकें", thinking: "सोच रहा हूँ…",
    suggestions: [
      "क्या TCS अभी ओवरबॉट है? RSI और खबरें देखिए।",
      "₹18 लाख की सैलरी और ₹1.5 लाख 80C पर पुराना या नया टैक्स रिजीम?",
      "₹30 लाख के होम लोन की EMI, 8.5% पर 20 साल के लिए। और 1 साल बाद ₹2 लाख प्रीपे करूँ तो?",
      "मेरा सेव किया हुआ पोर्टफोलियो आज कैसा चल रहा है?",
      "Parag Parikh Flexi Cap में ₹5,000 की मासिक SIP 3 साल में कितनी हो जाती?",
      "मैं 28 साल का हूँ, ₹45,000 महीना खर्च करता हूँ और ₹25,000 निवेश। मैं कब रिटायर हो सकता हूँ?",
    ],
  },
  mr: {
    hello: "नमस्कार! मी तुमचा FinSuite वित्त सहाय्यक आहे. शेअर्स, म्युच्युअल फंड, कर, कर्ज, बजेट, निवृत्ती किंवा कोणत्याही आर्थिक संज्ञेबद्दल विचारा. शक्य तिथे मी लाइव्ह डेटावरून उत्तर देईन.",
    placeholder: "तुमचा प्रश्न लिहा, उदा. ₹18 लाख पगारावर कोणती कर प्रणाली चांगली?", send: "पाठवा", stop: "थांबवा", thinking: "विचार करत आहे…",
    suggestions: [
      "TCS सध्या ओव्हरबॉट आहे का? RSI आणि बातम्या तपासा.",
      "₹18 लाख पगार आणि ₹1.5 लाख 80C असल्यास जुनी की नवी कर प्रणाली?",
      "₹30 लाखांच्या होम लोनचा EMI, 8.5% वर 20 वर्षांसाठी. आणि 1 वर्षानंतर ₹2 लाख प्रीपे केले तर?",
      "माझा सेव्ह केलेला पोर्टफोलिओ आज कसा आहे?",
      "Parag Parikh Flexi Cap मध्ये ₹5,000 ची मासिक SIP 3 वर्षांत किती झाली असती?",
      "मी 28 वर्षांचा आहे, महिन्याला ₹45,000 खर्च करतो आणि ₹25,000 गुंतवतो. मी कधी निवृत्त होऊ शकतो?",
    ],
  },
};
const T = ()=> CHAT_I18N[CHAT.lang] || CHAT_I18N.en;
// One language choice for the AI answers and the Knowledge Center.
function setLanguage(lang){
  if(!CHAT_I18N[lang]) lang = "en";
  CHAT.lang = lang; LS.set("fs-lang", lang);
  ["aiLang","kcLang"].forEach(id=>{ const el = document.getElementById(id); if(el) el.value = lang; });
  document.getElementById("chatInput").placeholder = T().placeholder;
  if(!CHAT.busy) document.getElementById("chatSend").textContent = T().send;
  renderChat();
  if(typeof loadKnowledge === "function") loadKnowledge(lang);
}
function renderMarkdown(text){
  if(window.marked && window.DOMPurify){
    const html = DOMPurify.sanitize(marked.parse(text, {breaks:true, gfm:true}));
    return html.replace(/<a /g, '<a target="_blank" rel="noopener" ');
  }
  return escapeHtml(text).replace(/\n/g, "<br>");
}
function chatBubble(role, html){
  const div = document.createElement("div");
  div.className = `msg ${role === "user" ? "user" : "bot"}`;
  div.innerHTML = html;
  document.getElementById("chatLog").appendChild(div);
  return div;
}
function scrollChat(){ const log = document.getElementById("chatLog"); log.scrollTop = log.scrollHeight; }
function renderChat(){
  const log = document.getElementById("chatLog");
  log.innerHTML = "";
  if(!CHAT.history.length){
    chatBubble("assistant", renderMarkdown(T().hello));
  }
  CHAT.history.forEach(m=> chatBubble(m.role, m.role === "user" ? escapeHtml(m.content).replace(/\n/g,"<br>") : renderMarkdown(m.content)));
  document.getElementById("chatSuggest").innerHTML = CHAT.history.length ? "" :
    T().suggestions.map((q,i)=>`<button type="button" class="chip" onclick="sendChat(T().suggestions[${i}])">${escapeHtml(q)}</button>`).join("");
  scrollChat();
}
let CHAT_SYNC = null;
function saveChat(){
  CHAT.history = CHAT.history.slice(-40); LS.set("fs-chat", CHAT.history);
  if(AUTH.user){ clearTimeout(CHAT_SYNC); CHAT_SYNC = setTimeout(syncChat, 1500); }      // logged-in users keep their chat on every device
}
function syncChat(){
  const h = CHAT.history.slice();
  while(h.length > 2 && JSON.stringify(h).length > 90000) h.shift();
  api("PUT","/user/data/chat",{value:h}).catch(()=>{});
}
function newChat(){ if(CHAT.ctrl) CHAT.ctrl.abort(); CHAT.history = []; saveChat(); renderChat(); document.getElementById("chatInput").focus(); }
function setChatBusy(busy){
  CHAT.busy = busy;
  const b = document.getElementById("chatSend");
  b.textContent = busy ? T().stop : T().send;
  b.classList.toggle("secondary", busy);
}
async function sendChat(preset){
  if(CHAT.busy){ if(CHAT.ctrl) CHAT.ctrl.abort(); return; }
  const input = document.getElementById("chatInput");
  const q = (preset || input.value).trim();
  if(!q) return;
  input.value = ""; input.style.height = "";
  CHAT.history.push({role:"user", content:q});
  saveChat(); renderChat();
  const bubble = chatBubble("assistant", `<span class="typing"><i></i><i></i><i></i></span>`);
  const status = document.createElement("div"); status.className = "ai-status";
  const body = document.createElement("div");
  bubble.innerHTML = ""; bubble.append(status, body);
  status.innerHTML = `<span class="typing"><i></i><i></i><i></i></span> ${T().thinking}`;
  scrollChat();
  let answer = "", notice = "", pending = false;
  const paint = ()=>{ pending = false; body.innerHTML = renderMarkdown(answer) + (notice ? `<p class="meta">${escapeHtml(notice)}</p>` : ""); scrollChat(); };
  const schedule = ()=>{ if(!pending){ pending = true; requestAnimationFrame(paint); } };
  setChatBusy(true);
  CHAT.ctrl = new AbortController();
  try{
    const res = await fetch("/assistant/ai-chat", {
      method:"POST", headers:{"Content-Type":"application/json"}, signal: CHAT.ctrl.signal,
      body: JSON.stringify({ language: CHAT.lang, messages: CHAT.history.map(m=>({role:m.role, content:m.content})),
        context: { watchlist: WATCHLIST.map(w=>w.symbol), portfolio: HOLDINGS, tab: document.getElementById("navCurrent").textContent } }),
    });
    if(!res.ok){ const e = await res.json().catch(()=>({detail:res.statusText})); throw new Error(typeof e.detail === "string" ? e.detail : "Request failed"); }
    const reader = res.body.getReader(), dec = new TextDecoder();
    let buf = "";
    for(;;){
      const {value, done} = await reader.read();
      if(done) break;
      buf += dec.decode(value, {stream:true});
      let nl;
      while((nl = buf.indexOf("\n")) >= 0){
        const line = buf.slice(0, nl).trim(); buf = buf.slice(nl + 1);
        if(!line) continue;
        const ev = JSON.parse(line);
        if(ev.type === "text"){ answer += ev.text; status.innerHTML = ""; schedule(); }
        else if(ev.type === "tool"){ status.innerHTML = `<span class="typing"><i></i><i></i><i></i></span> ${escapeHtml(ev.label)}…`; scrollChat(); }
        else if(ev.type === "notice"){ notice = ev.message; schedule(); }
        else if(ev.type === "error"){ answer += (answer ? "\n\n" : "") + "⚠ " + ev.message; schedule(); }
      }
    }
  }catch(e){
    answer += (answer ? "\n\n" : "") + (e.name === "AbortError" ? "_(Stopped.)_" : "⚠ " + e.message);
  }finally{
    status.remove(); paint(); setChatBusy(false); CHAT.ctrl = null;
    answer = answer.trim();
    if(answer) CHAT.history.push({role:"assistant", content:answer});
    saveChat();
  }
}
(function initChat(){
  const input = document.getElementById("chatInput");
  input.addEventListener("keydown", e=>{ if(e.key==="Enter" && !e.shiftKey){ e.preventDefault(); sendChat(); } });
  input.addEventListener("input", ()=>{ input.style.height = "auto"; input.style.height = Math.min(input.scrollHeight, 160) + "px"; });
  const sel = document.getElementById("aiLang");
  sel.value = CHAT.lang; input.placeholder = T().placeholder;
  sel.addEventListener("change", ()=>setLanguage(sel.value));
  fetch("/assistant/ai-status").then(r=>r.json()).then(r=>{
    const el = document.getElementById("aiMode");
    el.textContent = r.enabled ? "AI mode on" : "Basic mode";
    el.classList.toggle("on", r.enabled);
    el.title = r.enabled ? "Answers come from an AI model using FinSuite's live data and calculators."
                         : "No AI key is set on this server, so answers come from the Knowledge Center only.";
  }).catch(()=>{});
})();

async function calcAssistant(){
  const box = document.getElementById("assistantInsight");
  try{
    const r = await api("POST","/assistant/snapshot",{
      income:+document.getElementById("asIncome").value, expenses:+document.getElementById("asExpenses").value,
      savings:+document.getElementById("asSavings").value, borrowed:+document.getElementById("asBorrowed").value,
      owned:+document.getElementById("asOwned").value,
    });
    barChart("assistantChart","assistant", ["ROE %","ROA %","Borrowed/Owned %","Savings Ratio %"], [r.roe, r.roa, r.borrowed_to_owned*100, r.savings_ratio]);
    document.getElementById("assistantInsightText").textContent = r.insight;
    box.style.display = "block";
  }catch(e){ box.style.display="none"; alert(e.message); }
}

