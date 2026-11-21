/* ============================================================
   COMPANY PICKER — dropdown of popular stocks with a search box that
   finds any listed company via GET /market/search.
   ============================================================ */
const POPULAR = [
  ["Indices", [
    ["^NSEI","NIFTY 50","NSE"], ["^BSESN","S&P BSE SENSEX","BSE"], ["^NSEBANK","NIFTY Bank","NSE"], ["^CNXIT","NIFTY IT","NSE"],
    ["^GSPC","S&P 500","US"], ["^IXIC","NASDAQ Composite","US"], ["^DJI","Dow Jones Industrial Average","US"],
  ]],
  ["India — NSE", [
    ["RELIANCE.NS","Reliance Industries"], ["TCS.NS","Tata Consultancy Services"], ["HDFCBANK.NS","HDFC Bank"],
    ["ICICIBANK.NS","ICICI Bank"], ["INFY.NS","Infosys"], ["BHARTIARTL.NS","Bharti Airtel"], ["SBIN.NS","State Bank of India"],
    ["ITC.NS","ITC"], ["HINDUNILVR.NS","Hindustan Unilever"], ["LT.NS","Larsen & Toubro"], ["KOTAKBANK.NS","Kotak Mahindra Bank"],
    ["AXISBANK.NS","Axis Bank"], ["BAJFINANCE.NS","Bajaj Finance"], ["BAJAJFINSV.NS","Bajaj Finserv"], ["HCLTECH.NS","HCL Technologies"],
    ["WIPRO.NS","Wipro"], ["TECHM.NS","Tech Mahindra"], ["ASIANPAINT.NS","Asian Paints"], ["MARUTI.NS","Maruti Suzuki"],
    ["TMPV.NS","Tata Motors Passenger Vehicles"], ["TMCV.NS","Tata Motors (Commercial Vehicles)"], ["M&M.NS","Mahindra & Mahindra"],
    ["BAJAJ-AUTO.NS","Bajaj Auto"], ["HEROMOTOCO.NS","Hero MotoCorp"], ["EICHERMOT.NS","Eicher Motors"],
    ["SUNPHARMA.NS","Sun Pharmaceutical"], ["DRREDDY.NS","Dr. Reddy's Laboratories"], ["CIPLA.NS","Cipla"], ["APOLLOHOSP.NS","Apollo Hospitals"],
    ["TITAN.NS","Titan Company"], ["ULTRACEMCO.NS","UltraTech Cement"], ["GRASIM.NS","Grasim Industries"], ["NESTLEIND.NS","Nestlé India"],
    ["BRITANNIA.NS","Britannia Industries"], ["TATACONSUM.NS","Tata Consumer Products"], ["POWERGRID.NS","Power Grid Corporation"],
    ["NTPC.NS","NTPC"], ["ONGC.NS","Oil & Natural Gas Corporation"], ["COALINDIA.NS","Coal India"], ["TATASTEEL.NS","Tata Steel"],
    ["JSWSTEEL.NS","JSW Steel"], ["HINDALCO.NS","Hindalco Industries"], ["ADANIENT.NS","Adani Enterprises"], ["ADANIPORTS.NS","Adani Ports & SEZ"],
    ["INDUSINDBK.NS","IndusInd Bank"], ["SBILIFE.NS","SBI Life Insurance"], ["HDFCLIFE.NS","HDFC Life Insurance"], ["LICI.NS","Life Insurance Corporation of India"],
    ["ETERNAL.NS","Eternal (Zomato)"], ["TRENT.NS","Trent"], ["DMART.NS","Avenue Supermarts (DMart)"], ["BEL.NS","Bharat Electronics"],
    ["HAL.NS","Hindustan Aeronautics"], ["SHRIRAMFIN.NS","Shriram Finance"], ["JIOFIN.NS","Jio Financial Services"], ["IRCTC.NS","IRCTC"],
    ["PIDILITIND.NS","Pidilite Industries"], ["PAYTM.NS","Paytm (One 97 Communications)"], ["NYKAA.NS","Nykaa (FSN E-Commerce)"],
  ].map(([s,n])=>[s,n,"NSE"])],
  ["US & Global", [
    ["AAPL","Apple","NASDAQ"], ["MSFT","Microsoft","NASDAQ"], ["GOOGL","Alphabet (Google)","NASDAQ"], ["AMZN","Amazon","NASDAQ"],
    ["NVDA","NVIDIA","NASDAQ"], ["META","Meta Platforms","NASDAQ"], ["TSLA","Tesla","NASDAQ"], ["NFLX","Netflix","NASDAQ"],
    ["IBM","IBM","NYSE"], ["005930.KS","Samsung Electronics","Korea"], ["TM","Toyota Motor","NYSE"],
  ]],
].map(([group, rows])=>({ group, rows: rows.map(([symbol,name,exchange])=>({symbol,name,exchange,type:"EQUITY"})) }));

/* Dropdown with a search box inside: the closed state shows the selected
   company; opening it focuses a search field above the list. With the
   field empty the list shows POPULAR; typing filters it and adds live
   GET /market/search results for every other listed company. */
function attachSymbolPicker(pickerId, hiddenInputId, onPick){
  const root = document.getElementById(pickerId), hidden = document.getElementById(hiddenInputId);
  const btn = root.querySelector(".picker-btn"), panel = root.querySelector(".picker-panel");
  const search = root.querySelector(".picker-search input"), list = root.querySelector(".picker-list");
  let timer = null, items = [], sections = [], active = -1, seq = 0;
  const norm = s=>s.toLowerCase().replace(/[^a-z0-9]/g,"");

  const render = (secs, note="")=>{
    sections = secs;
    items = secs.flatMap(s=>s.rows);
    let i = 0;
    list.innerHTML = secs.filter(s=>s.rows.length).map(s=>
      `<div class="suggest-group">${escapeHtml(s.group)}</div>` +
      s.rows.map(r=>{ const k = i++; return `<div class="suggest-item${k===active?" active":""}${r.symbol===hidden.value?" selected":""}" data-i="${k}"><span class="sym">${escapeHtml(r.symbol)}</span><span class="nm">${escapeHtml(r.name)}</span><span class="exch">${escapeHtml(r.exchange)}${r.type && r.type!=="EQUITY"?" · "+escapeHtml(r.type):""}</span></div>`; }).join("")
    ).join("") + (note ? `<div class="suggest-empty">${note}</div>` : "");
    const el = list.querySelector(".suggest-item.active"); if(el) el.scrollIntoView({block:"nearest"});
  };
  const open = ()=>{
    panel.hidden = false; root.classList.add("open");
    search.value = ""; active = -1; render(POPULAR);
    search.focus();
  };
  const close = ()=>{ panel.hidden = true; root.classList.remove("open"); clearTimeout(timer); };
  const pick = (symbol, name)=>{
    hidden.value = symbol;
    setPickerLabel(pickerId, name || symbol, name ? symbol : "");
    close(); btn.focus();
    onPick(symbol);
  };

  btn.addEventListener("click", ()=> panel.hidden ? open() : close());
  btn.addEventListener("keydown", e=>{ if(e.key==="ArrowDown"){ e.preventDefault(); open(); } });
  document.addEventListener("mousedown", e=>{ if(!panel.hidden && !root.contains(e.target)) close(); });

  search.addEventListener("input", ()=>{
    clearTimeout(timer);
    const q = search.value.trim();
    active = -1;
    if(!q){ render(POPULAR); return; }
    const n = norm(q);
    const local = POPULAR.flatMap(s=>s.rows).filter(r=>norm(r.name).includes(n) || norm(r.symbol).startsWith(n)).slice(0,6);
    render([{group:"Popular", rows:local}], "Searching all listed companies…");
    timer = setTimeout(async ()=>{
      const my = ++seq;
      try{
        const r = await api("GET", `/market/search?q=${encodeURIComponent(q)}`);
        if(my !== seq || panel.hidden) return;                       // a newer keystroke won
        const seen = new Set(local.map(x=>x.symbol));
        const more = (r.results||[]).filter(x=>!seen.has(x.symbol));
        render([{group:"Popular", rows:local}, {group:"All markets", rows:more}],
               local.length || more.length ? "" : `No company found for “${escapeHtml(q)}”. Check the spelling, or press Enter to try it as a ticker.`);
      }catch(e){ if(my === seq) render(sections.slice(0,1), "Search is unavailable right now — press Enter to try it as a ticker."); }
    }, 250);
  });
  search.addEventListener("keydown", e=>{
    if(e.key === "ArrowDown" && items.length){ active = (active+1) % items.length; render(sections); e.preventDefault(); }
    else if(e.key === "ArrowUp" && items.length){ active = (active-1+items.length) % items.length; render(sections); e.preventDefault(); }
    else if(e.key === "Enter"){
      e.preventDefault();
      const v = search.value.trim();
      if(items.length && (active >= 0 || v)){ const r = items[Math.max(active,0)]; pick(r.symbol, r.name); }
      else if(v) pick(v);                                  // backend resolves names/tickers itself
    }
    else if(e.key === "Escape"){ close(); btn.focus(); }
  });
  list.addEventListener("mousedown", e=>{ e.preventDefault(); const el = e.target.closest(".suggest-item"); if(el){ const r = items[+el.dataset.i]; pick(r.symbol, r.name); } });
}
function setPickerLabel(pickerId, name, symbol){
  const root = document.getElementById(pickerId);
  root.querySelector(".picker-label").textContent = name;
  root.querySelector(".picker-sym").textContent = symbol || "";
}

function selectMarketSymbol(symbol){
  document.getElementById("marketSymbol").value = symbol;
  document.getElementById("newsSymbols").value = symbol;
  AUTO_JOBS.forEach(j=>{ if(j.panel==="market") j.last = Date.now(); });   // we're refreshing right now
  getQuote(); getDailyHistory(); getNews();
}
attachSymbolPicker("marketPicker", "marketSymbol", selectMarketSymbol);
attachSymbolPicker("wlPicker", "wlSymbol", symbol=>addWatchlistSymbol(symbol));
document.getElementById("historyPeriod").addEventListener("change", getDailyHistory);

