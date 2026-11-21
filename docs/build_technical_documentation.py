"""Builds docs/FinSuite_Technical_Documentation.pdf (version 2.0) from this script and
docs/experiment_results.json (made by docs/run_experiment.py).

    python docs/build_technical_documentation.py

Needs Playwright with Chromium (pip install playwright; playwright install chromium).
"""
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = json.loads((HERE / "experiment_results.json").read_text(encoding="utf-8"))
MODELS = [("linear", "Linear"), ("ridge", "Ridge"), ("random_forest", "Random Forest"), ("gradient_boosting", "Gradient Boosting")]
e = html.escape
_table_no = 0
_figure_no = 0


def table(caption, header, rows, widths=None, small=False):
    global _table_no
    _table_no += 1
    cols = "".join(f"<col style='width:{w}'>" for w in widths) if widths else ""
    head = "".join(f"<th>{h}</th>" for h in header)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return (f"<div class='tblwrap'><p class='cap'>Table {_table_no}. {caption}</p>"
            f"<table class='{'small' if small else ''}'><colgroup>{cols}</colgroup><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>")


def figure(svg, caption):
    global _figure_no
    _figure_no += 1
    return f"<div class='fig'>{svg}<p class='cap figcap'>Figure {_figure_no}. {caption}</p></div>"


# --------------------------------------------------------------------------- figures
def box(x, y, w, h, title, lines=(), fill="#fff", bold=True):
    out = f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='{fill}' stroke='#000' stroke-width='1'/>"
    out += f"<text x='{x + w / 2}' y='{y + 15}' text-anchor='middle' font-size='10.5' font-weight='{'bold' if bold else 'normal'}'>{title}</text>"
    for i, t in enumerate(lines):
        out += f"<text x='{x + w / 2}' y='{y + 29 + i * 12}' text-anchor='middle' font-size='9'>{t}</text>"
    return out


def arrow(x1, y1, x2, y2):
    return f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='#000' stroke-width='1' marker-end='url(#a)'/>"


ARCH = ("<svg viewBox='0 0 620 400' width='100%' font-family='Times New Roman, serif'>"
        "<defs><marker id='a' markerWidth='8' markerHeight='8' refX='7' refY='4' orient='auto'><path d='M0,0 L8,4 L0,8 z'/></marker></defs>"
        "<text x='6' y='14' font-size='10' font-style='italic'>Layer 1. Browser</text>"
        + box(6, 20, 150, 52, "Pages and forms", ["HTML, CSS, one script per tool"], "#f3f3f3")
        + box(166, 20, 140, 52, "Charts and exports", ["Chart.js, jsPDF, SheetJS"], "#f3f3f3")
        + box(316, 20, 150, 52, "Service worker", ["offline shell, push alerts"], "#f3f3f3")
        + box(476, 20, 138, 52, "Installable app", ["manifest, icons"], "#f3f3f3")
        + arrow(310, 74, 310, 92)
        + "<text x='318' y='88' font-size='9' font-style='italic'>JSON over HTTP(S); the AI reply is streamed</text>"
        + "<text x='6' y='108' font-size='10' font-style='italic'>Layer 2. Application server (FastAPI, one process)</text>"
        + box(6, 114, 150, 52, "API routes", ["about 70 endpoints"])
        + box(166, 114, 140, 52, "Validation", ["Pydantic models"])
        + box(316, 114, 150, 52, "Limits and accounts", ["rate limits, sessions"])
        + box(476, 114, 138, 52, "Static files", ["versioned, gzip"])
        + arrow(310, 168, 310, 186)
        + "<text x='6' y='202' font-size='10' font-style='italic'>Layer 3. Services</text>"
        + box(6, 208, 100, 58, "Calculators", ["tax, EMI, FIRE,", "budget, ratios"])
        + box(112, 208, 100, 58, "Market", ["quotes, history,", "indicators, FX"])
        + box(218, 208, 100, 58, "Funds, tracker", ["AMFI NAVs, XIRR,", "portfolio value"])
        + box(324, 208, 100, 58, "ML module", ["4 models,", "walk-forward"])
        + box(430, 208, 100, 58, "AI assistant", ["16 tools, stream"])
        + box(536, 208, 78, 58, "Alert worker", ["every 5 min"])
        + arrow(310, 268, 310, 286)
        + "<text x='6' y='302' font-size='10' font-style='italic'>Layer 4. Storage and outside services</text>"
        + box(6, 308, 120, 58, "SQLite", ["accounts, saved data,", "alerts, counters"], "#f3f3f3")
        + box(132, 308, 120, 58, "Yahoo, Google News", ["prices, FX, headlines"], "#f3f3f3")
        + box(258, 308, 110, 58, "AMFI, mfapi.in", ["fund NAVs"], "#f3f3f3")
        + box(374, 308, 120, 58, "Anthropic API", ["AI model (optional)"], "#f3f3f3")
        + box(500, 308, 114, 58, "Email, Telegram,", ["Web Push (optional)"], "#f3f3f3")
        + "<text x='6' y='388' font-size='9' font-style='italic'>Hosting: a small Ubuntu server (nginx in front, systemd restarts the app) or a serverless host without the background worker.</text>"
        "</svg>")

LOOP = ("<svg viewBox='0 0 620 250' width='100%' font-family='Times New Roman, serif'>"
        "<defs><marker id='b' markerWidth='8' markerHeight='8' refX='7' refY='4' orient='auto'><path d='M0,0 L8,4 L0,8 z'/></marker></defs>"
        + "".join(f"<rect x='{x}' y='8' width='140' height='26' fill='#f3f3f3' stroke='#000'/><text x='{x + 70}' y='25' text-anchor='middle' font-size='11' font-weight='bold'>{t}</text>"
                  f"<line x1='{x + 70}' y1='34' x2='{x + 70}' y2='244' stroke='#000' stroke-dasharray='3,3'/>"
                  for x, t in [(10, "Browser"), (170, "FinSuite server"), (330, "AI model"), (480, "FinSuite tools")])
        + "".join(f"<line x1='{a}' y1='{y}' x2='{b}' y2='{y}' stroke='#000' marker-end='url(#b)'/><text x='{(a + b) / 2}' y='{y - 4}' text-anchor='middle' font-size='9'>{t}</text>"
                  for a, b, y, t in [(80, 240, 62, "1. question + history"), (240, 400, 82, "2. prompt, tool list, user context"),
                                     (400, 240, 106, "3. tool call (e.g. calculate_income_tax)"), (240, 550, 130, "4. validate input, run the tool"),
                                     (550, 240, 150, "5. result (numbers from FinSuite)"), (240, 400, 172, "6. result sent back to the model"),
                                     (400, 240, 196, "7. final answer, written piece by piece"), (240, 80, 220, "8. streamed to the page")])
        + "</svg>")


def walk_chart():
    """Grouped bars: walk-forward error of each model divided by the naive error. Below 1 beats the naive guess."""
    syms = list(RESULTS)
    W, H, left, top, bottom = 620, 270, 50, 20, 52
    ymax = 1.35
    def y(v): return top + (H - top - bottom) * (1 - v / ymax)
    colors = {"linear": "#444", "ridge": "#888", "random_forest": "#bbb", "gradient_boosting": "#ddd"}
    out = [f"<svg viewBox='0 0 {W} {H}' width='100%' font-family='Times New Roman, serif'>"]
    for v in (0, 0.25, 0.5, 0.75, 1.0, 1.25):
        out.append(f"<line x1='{left}' y1='{y(v)}' x2='{W - 10}' y2='{y(v)}' stroke='#ccc' stroke-width='0.6'/><text x='{left - 6}' y='{y(v) + 3}' text-anchor='end' font-size='9'>{v:.2f}</text>")
    out.append(f"<line x1='{left}' y1='{y(1.0)}' x2='{W - 10}' y2='{y(1.0)}' stroke='#000' stroke-width='1.2' stroke-dasharray='5,3'/>")
    out.append(f"<text x='{W - 12}' y='{y(1.0) - 4}' text-anchor='end' font-size='9' font-style='italic'>naive guess = 1.00</text>")
    group_w = (W - left - 20) / len(syms)
    for gi, sym in enumerate(syms):
        wf = RESULTS[sym]["walk"]
        gx = left + gi * group_w + 14
        bw = (group_w - 28) / 4
        for mi, (key, label) in enumerate(MODELS):
            ratio = wf["models"][key]["mae"] / wf["naive_mae"]
            bx = gx + mi * bw
            out.append(f"<rect x='{bx:.1f}' y='{y(ratio):.1f}' width='{bw - 3:.1f}' height='{y(0) - y(ratio):.1f}' fill='{colors[key]}' stroke='#000' stroke-width='0.6'/>")
            out.append(f"<text x='{bx + (bw - 3) / 2:.1f}' y='{y(ratio) - 3:.1f}' text-anchor='middle' font-size='8'>{ratio:.2f}</text>")
        out.append(f"<text x='{gx + 2 * bw - 2:.1f}' y='{H - bottom + 14}' text-anchor='middle' font-size='10'>{e(sym)}</text>")
    lx = left
    for key, label in MODELS:
        out.append(f"<rect x='{lx}' y='{H - 18}' width='10' height='10' fill='{colors[key]}' stroke='#000' stroke-width='0.6'/><text x='{lx + 14}' y='{H - 9}' font-size='9.5'>{label}</text>")
        lx += 110
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------------- tables
MODULES = [
    ("01", "Finance Report", "Income, expenses, savings and debt turned into ratios and tips; PDF and Excel download.", "Calculation"),
    ("02", "AI Assistant", "Chat with a language model that uses FinSuite's own tools and live data; English, Hindi, Marathi.", "AI"),
    ("03", "Budget Planner", "50/30/20 check with charts; fills itself from a bank statement (CSV read in the browser).", "Calculation"),
    ("04", "Income Tax", "Old and new regime for FY 2025-26 side by side, deductions, share-market gains.", "Calculation"),
    ("05", "Loan EMI", "EMI, repayment table, interest saved by prepaying.", "Calculation"),
    ("06", "Goals and Retirement", "Monthly saving for a goal with inflation; emergency fund.", "Calculation"),
    ("07", "Retirement and FIRE", "Corpus needed, required SIP, age of financial independence.", "Calculation"),
    ("08", "Stock Market", "Search any listed company; quote, history, SMA/EMA/Bollinger/RSI, news with sentiment.", "Live data"),
    ("09", "Currency and Compare", "Live exchange rates; two-stock comparison.", "Live data"),
    ("10", "Watchlist and Alerts", "Saved watchlist; price alerts by email, push and Telegram.", "Live data"),
    ("11", "Portfolio Tracker", "Holdings valued at live prices, profit or loss in rupees.", "Live data"),
    ("12", "Mutual Funds and SIP", "Search every Indian scheme, NAV chart, SIP returns with XIRR.", "Live data"),
    ("13", "Growth and Target", "What-if growth; target and stop-loss planning.", "Calculation"),
    ("14", "Portfolio and Tax", "SIP versus lump sum, capital-gains tax, 52-week range.", "Calculation"),
    ("15", "ML Prediction", "Next-day close from four models, tested hold-out and walk-forward.", "ML"),
    ("16", "Ratios", "ROE, ROA, debt ratio, health label.", "Calculation"),
    ("17", "Loan Insights", "Comment on each customer in a loan table.", "Rule-based"),
    ("18", "Credit and Risk", "Credit-score category and risk level.", "Rule-based"),
    ("19", "Investment Call", "BUY, HOLD or AVOID from four checks.", "Rule-based"),
    ("20", "Company Performance", "Score out of 100 from growth, satisfaction, retention.", "Rule-based"),
    ("21", "Portfolio Dashboard", "Scores and ranks several companies.", "Rule-based"),
    ("22", "Knowledge Center", "One hundred plain-language entries with examples; search; Hindi and Marathi.", "Reference"),
    ("23", "Data Sources", "Where the data comes from, with a live status check.", "Reference"),
    ("24", "About", "Project, designer and guide.", "Reference"),
]


def build() -> str:
    t = []
    a = t.append
    a("<h1 class='title'>FinSuite</h1>")
    a("<p class='subtitle'>A Web Platform for Financial Analysis, Live Market Data, an AI Assistant and Price Alerts</p>")
    a("<p class='author'><b>Purva Kakade</b><br><i>Research Intern, Indian Institute of Technology Bombay</i></p>")
    a("<p class='author'>Under the guidance of <b>Prof. Ashish Singh</b><br><i>Shailesh J. Mehta School of Management, IIT Bombay</i></p>")
    a("<p class='author'><i>System documentation and evaluation, version 2.0, November 2026</i></p><hr>")
    a("<div class='abstract'><p class='abshead'>Abstract</p><p>FinSuite is a free website that brings twenty-four finance tools together: calculators for tax, loans, budgets and retirement, live stock and mutual-fund data, "
      "a conversational assistant, and price alerts that reach a user by email, push notification or Telegram. This version of the document describes how the system grew from the "
      "seventeen tools of version 1.0, how it is built, where its data comes from, how each result is computed, how access to the paid and shared parts is limited, and how the work was checked. "
      "A forecasting experiment is repeated with four models and a walk-forward test on four instruments. As before, no model beat the naive guess &ldquo;tomorrow equals today&rdquo; "
      "consistently: the few hold-out wins disappeared or became mixed when the test was repeated over several stretches of history, and the direction of the next move was called right "
      "about as often as a coin toss. The website reports this to its users.</p>"
      "<p><b>Keywords:</b> personal finance tools; open data; price forecasting; walk-forward validation; tool-using language model; web push; software verification</p></div><hr>")

    a("<h2>1. Introduction</h2><h3>1.1 Background and problem</h3>"
      "<p>Decisions about loans, savings, tax and shares are often made without the analytical tools that professionals use. Many existing tools are paid, need an account or an API key, "
      "or give a number without showing how it was obtained. For a beginner it is then hard to judge whether a result is right, or what it means.</p>"
      "<h3>1.2 Objectives</h3><p>The system keeps the five objectives of version 1.0 and adds two. It should be free to run, so live data comes from public sources without registration. "
      "Every result should be explainable: each tool states its formula and a Knowledge Center defines each term. Calculations should be correct, which is checked with values worked out by hand "
      "and with an automated test suite. The system should state its limits where a result is weak. Personal data should be kept to the minimum: an account is optional and everything "
      "works without one. The two additions are that the system should <i>protect itself and its operators</i> (limits on use, backups, monitoring, a budget for the paid AI service) "
      "and that it should be <i>usable by more people</i> (phone and keyboard use, dark mode, installable offline app, Hindi and Marathi).</p>"
      "<h3>1.3 What changed since version 1.0</h3>"
      "<p>Seven tools were added (income tax, loan EMI, budget planner, mutual funds, portfolio tracker, retirement and FIRE planning, currency and stock comparison). The AI Assistant, which in version 1.0 "
      "only looked up stored definitions, now uses a language model that calls the system's own functions as tools. Optional accounts store the watchlist, portfolio, alerts and chat history; "
      "a background worker checks alerts when no page is open. Charts gained technical indicators, news headlines are marked positive, neutral or negative, and the forecasting tab compares four models "
      "with a walk-forward test. The code was reorganised into one script per tool, and the project gained 122 automated tests, a daily backup and an uptime check.</p>"
      "<h3>1.4 Contributions</h3><p>This document contributes (i) the architecture and the data pipeline, (ii) the formulas and rules behind every result, (iii) the design of the AI assistant and the limits that bound its cost, "
      "(iv) the account, alert and notification design, (v) a forecasting experiment with a walk-forward test, (vi) a record of verification including the defects found and corrected, and "
      "(vii) instructions for running and operating the system.</p>")

    a("<h2>2. System Overview</h2><p>The website has twenty-four tools, grouped in four menus (Personal finance; Markets and investing; Business and credit; Learn and information). "
      "Table 1 lists them with the kind of processing each performs: calculation (formulas applied to numbers typed by the user), rule-based (fixed scoring rules), live data, "
      "AI, ML (machine learning) and reference (static text).</p>")
    a(table("The twenty-four tools of FinSuite, numbered as in the menu.", ["No.", "Tool", "Function", "Kind"],
            [(n, e(m), e(f), k) for n, m, f, k in MODULES], ["6%", "20%", "58%", "16%"], small=True))

    a("<h2>3. System Architecture</h2><p>FinSuite has four layers (Figure 1). The browser shows pages and sends requests. The application server validates each request, applies limits and routes it. "
      "A services layer does the work: the formulas, market-data handling, forecasting, the AI assistant and the alert worker. The last layer is a small database and the outside services.</p>")
    a(figure(ARCH, "System architecture. Requests pass down through the layers and replies return the same way."))
    a("<h3>3.1 Layers</h3><p>The browser code is plain HTML, CSS and JavaScript with the Chart.js library; there is no framework and no build step. Since version 1.0 the script has been split into "
      "thirty small files, one for each tool, loaded in a fixed order. A service worker lets the site open without a connection and receive push messages. "
      "The server is written in Python with FastAPI and exposes about seventy endpoints. Each endpoint validates its input with Pydantic models and turns failures into clear messages. "
      "The services layer is a set of Python modules. Accounts, saved data, alerts and usage counters live in one SQLite file.</p>")
    a("<h3>3.2 Design decisions</h3>")
    a(table("Principal design decisions and their trade-offs.", ["Decision", "Rationale", "Trade-off"], [
        ("Python and FastAPI", "Financial mathematics, machine learning and the AI client share one language; inputs are validated automatically.", "Needs a Python runtime for hosting."),
        ("No front-end framework", "Small code base, no build step, easy to read and to test with Node.", "More manual code in the page."),
        ("Accounts are optional", "Everything works without one; guests keep data in their browser.", "Two storage paths to keep in step."),
        ("SQLite", "No separate database server; a backup is one file.", "One server only; not for heavy write loads."),
        ("Tools instead of free text for the AI", "Numbers come from tested functions, so the assistant does not invent them.", "Each new tool needs a schema and tests."),
        ("Limits on every costly path", "Protects the paid AI service and the shared data sources.", "A heavy user may meet a limit."),
        ("Public data, no keys", "Anyone can reproduce the system at no cost.", "The sources are unofficial and may be delayed."),
        ("Versioned files, long caching", "Changed files get a new address, so browsers never mix old and new code.", "None of note."),
    ], ["22%", "46%", "32%"], small=True))

    a("<h2>4. Data Collection</h2><h3>4.1 Sources</h3>")
    a(table("Data sources and how they are read.", ["Source", "Data", "Access", "Used by"], [
        ("Yahoo Finance", "Company search, quotes, daily history, exchange rates", "yfinance library, no key", "08, 09, 10, 11, 15"),
        ("Google News", "Headlines from the last seven days", "Public RSS feed, no key", "08, 15"),
        ("AMFI", "Latest net asset value of every mutual-fund scheme", "Public text file, no key", "12"),
        ("mfapi.in", "Historical NAVs of a scheme", "Free public API, no key", "12"),
        ("Anthropic API", "Language model for the assistant and for translations", "API key (optional)", "02, 22"),
        ("Email, Telegram, Web Push", "Delivery of alerts", "Mail account, bot token, browser keys (optional)", "10"),
        ("The user", "Numbers typed into forms, an optional bank statement", "Statement read in the browser, never uploaded", "most tools"),
    ], ["18%", "34%", "30%", "18%"], small=True))
    a("<h3>4.2 Live quotes and the cache</h3><p>A quote request first asks an in-memory cache. If nothing younger than 30 seconds is stored, the server asks Yahoo Finance for daily bars (to find the previous close) "
      "and the latest one-minute bars (to find the last trade and its time), stores the result and replies. If Yahoo fails, the last good value is returned and marked <i>stale</i>, "
      "and the page then says that live data is unavailable and how old the price is. Rows that Yahoo returns half-filled during a session are dropped before use.</p>")
    a("<h3>4.3 Mutual funds</h3><p>The AMFI file lists every scheme with its latest NAV; the server parses it (it has two layouts) and caches it for six hours. "
      "The history of one scheme is fetched from mfapi.in on demand. A SIP is simulated by buying a fixed amount on the first available NAV on or after each monthly date.</p>")
    a("<h3>4.4 What is stored about a user</h3><p>Without an account, the watchlist, portfolio, budget and chat stay in the browser. With an account, the server stores the email, a salted password hash, the watchlist, "
      "holdings, alerts, the chat history (trimmed to 90 kB), push subscriptions and an optional Telegram chat number. A bank statement is never sent to the server. "
      "An account and all its data can be deleted from the account window.</p>")

    a("<h2>5. Methods</h2><h3>5.1 Formulas</h3>")
    a(table("Principal formulas used by the tools.", ["Quantity", "Formula", "Notes"], [
        ("Loan EMI", "P&middot;i&middot;(1+i)<sup>n</sup> / ((1+i)<sup>n</sup> &minus; 1)", "i is the monthly rate, n the months; i = 0 gives P/n."),
        ("Repayment row", "interest = balance &times; i; principal = EMI &minus; interest", "A prepayment lowers the balance; the EMI stays, so the loan ends earlier."),
        ("Goal SIP", "Remaining target / [((1+i)<sup>n</sup> &minus; 1)/i &times; (1+i)]", "Target is first raised by inflation."),
        ("Retirement corpus", "E<sub>1</sub>&middot;(1 &minus; (1+r)<sup>&minus;N</sup>)/r &times; (1+r)", "E<sub>1</sub> first-year spending at retirement; r real return after retirement; N years."),
        ("FIRE number", "Yearly spending at retirement / withdrawal rate", "4% rule gives 25 times yearly spending."),
        ("XIRR", "&Sigma; CF<sub>k</sub> / (1+r)<sup>(d<sub>k</sub> &minus; d<sub>0</sub>)/365</sup> = 0", "Solved by bisection."),
        ("RSI (14)", "100 &minus; 100/(1+RS), RS = average gain / average loss", "Simple 14-day averages; above 70 overbought, below 30 oversold."),
        ("Bollinger bands", "SMA<sub>20</sub> &plusmn; 2&sigma;<sub>20</sub>", "&sigma; is the 20-day standard deviation of closes."),
        ("Volatility", "&sigma;(daily returns) &times; &radic;252", "Annualised."),
        ("Maximum drawdown", "min<sub>t</sub> (P<sub>t</sub> / max<sub>s&le;t</sub> P<sub>s</sub> &minus; 1)", "Worst fall from a peak."),
        ("Headline sentiment", "(positive &minus; negative) / (positive + negative)", "Word lists; a negator before a word flips it; above +0.1 positive, below &minus;0.1 negative."),
        ("50/30/20", "Needs 50%, wants 30%, saving 20% of income", "Unspent money counts as saving."),
    ], ["19%", "42%", "39%"], small=True))
    a("<h3>5.2 Income tax</h3><p>The tool follows the rules for FY 2025-26 as modelled here. Under the <b>new regime</b>, taxable income is gross income less a standard deduction of &#8377;75,000 (for salary or pension), "
      "taxed in slabs of 0% to &#8377;4 lakh, 5% to 8, 10% to 12, 15% to 16, 20% to 20, 25% to 24 and 30% above. Tax is nil if taxable income is up to &#8377;12 lakh; "
      "just above it, the tax is limited to the income above &#8377;12 lakh (marginal relief). Under the <b>old regime</b>, the standard deduction is &#8377;50,000 and deductions for Section 80C "
      "(limit &#8377;1.5 lakh), 80D, NPS 80CCD(1B) (&#8377;50,000), home-loan interest (&#8377;2 lakh), HRA and others are subtracted; slabs depend on age; tax is nil up to &#8377;5 lakh of taxable income. "
      "A surcharge applies at higher incomes (10%, 15%, 25%, with 37% in the old regime only, with marginal relief) and 4% cess is added. "
      "The tool also finds by bisection the amount of old-regime deductions at which both regimes cost the same. Gains on listed shares are taxed at 20% (short term) and 12.5% above &#8377;1.25 lakh (long term), "
      "plus cess, and unused basic exemption is set against them; surcharge on these gains is not included. The output is an estimate and not tax advice.</p>")
    a("<h3>5.3 Rule-based scores</h3><p>The credit, investment and company scores are the expert rules of version 1.0 with conventional thresholds (for example, a BUY needs at least three of four checks: "
      "growth, margin, ROA and ROE above set levels). They were not fitted to data; their purpose is to teach, and each rule is shown to the user.</p>")

    a("<h2>6. The AI Assistant</h2><h3>6.1 Design</h3><p>The assistant is a language model (Claude Opus 5.5 by default, configurable) that can call sixteen tools. "
      "The tools wrap functions that already exist in FinSuite: live quote, technical indicators, two-stock comparison, news with sentiment, company and fund search, currency conversion, "
      "income tax, loan EMI, goal and retirement planning, budget analysis, SIP returns, portfolio valuation, price forecast and a Knowledge Center lookup. "
      "Figure 2 shows one question. The model decides which tools to call; FinSuite validates every tool input with the same Pydantic rules as the website, runs the tool, and returns the result. "
      "Up to eight rounds of tool calls are allowed. The answer is streamed to the page as it is written and shown as sanitised Markdown.</p>")
    a(figure(LOOP, "One question to the assistant. Numbers in the answer come from steps 4 and 5, not from the model's memory."))
    a("<h3>6.2 Guard rails</h3>")
    a(table("Limits that protect the service and its budget (defaults; each can be changed by an environment setting).", ["Limit", "Default", "Purpose"], [
        ("AI questions per minute", "6 per address", "Stops rapid automated use."),
        ("AI questions per day", "30 guest, 100 logged-in user, 500 in total", "Bounds the cost of the paid service."),
        ("Answer length", "8,000 tokens", "Bounds the cost of one answer."),
        ("Conversation size", "40,000 characters, 24 earlier messages sent", "Bounds the input cost."),
        ("Any API call", "240 per minute per address", "General protection."),
        ("Price forecast", "5 per minute per address", "It trains models and is the heaviest call."),
        ("Log in", "10 per minute per address; 8 per 15 minutes per email", "Slows password guessing."),
        ("Create account", "6 per hour per address", "Stops mass sign-ups."),
        ("Reset or confirmation emails", "4 per hour per address and per email", "Stops the system being used to send spam."),
    ], ["28%", "37%", "35%"], small=True))
    a("<p>The assistant is told to stay on finance, to use the tools for numbers, to state assumptions, and not to give personal buy or sell advice. A user's question, the conversation so far and, to personalise answers, "
      "the symbols in the saved watchlist and portfolio are sent to the model provider; this is stated on the Data Sources page. If no key is set, the chat answers from the stored definitions instead. "
      "If the model refuses a request, the platform's fallback to another model is switched on. Hindi and Marathi answers are produced by an instruction in the prompt; "
      "the Knowledge Center is translated once by the model and kept in the database, and untranslated entries appear in English.</p>")

    a("<h2>7. Accounts, Alerts and Operations</h2><h3>7.1 Accounts and security</h3><p>Passwords are stored as PBKDF2-HMAC-SHA256 hashes with 200,000 rounds and a random 16-byte salt (RFC 8018). "
      "A session token is 256 random bits; only its SHA-256 hash is stored. Password-reset links (valid 30 minutes), email-confirmation links (3 days) and Telegram link codes (10 minutes) are one-time tokens, stored hashed. "
      "Resetting a password ends all sessions. Browsers may call the API only from FinSuite's own addresses. Text produced by the AI is sanitised before it is shown.</p>")
    a("<h3>7.2 Alerts and notification channels</h3><p>An alert is a symbol, a direction and a price. A worker checks pending alerts every five minutes (a database claim ensures that only one process runs each check). "
      "An alert fires once, with a conditional update so that two workers cannot both fire it, and then waits to be re-armed. A fired alert goes to every channel the user has set up: email, Web Push "
      "(RFC 8030, VAPID keys per RFC 8292, generated on first use and kept in the database) and Telegram (a bot, linked with a one-time code). A failing channel never blocks the others. "
      "WhatsApp is not supported because it requires a verified business account with its provider.</p>")
    a("<h3>7.3 Operations</h3><p>On the server, the application runs as a systemd service behind nginx. A cron job copies the database with SQLite's online backup once a day, checks its integrity, compresses it and keeps the latest fourteen copies. "
      "Another job asks the health endpoint every five minutes and emails the administrator after two failures in a row, and again on recovery. "
      "The Data Sources page shows the live status of each outside source, which is checked at most once a minute. Settings are environment variables (Table 5).</p>")
    a(table("Environment settings (all optional).", ["Setting", "Effect"], [
        ("ANTHROPIC_API_KEY", "Turns on the AI assistant and the translations."),
        ("SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM", "Email for alerts, resets and confirmations."),
        ("TELEGRAM_BOT_TOKEN", "Turns on Telegram alerts."),
        ("FINSUITE_DB", "Location of the SQLite file."),
        ("AI_PER_IP_DAILY, AI_PER_USER_DAILY, AI_DAILY_LIMIT, AI_MAX_TOKENS", "AI budget limits."),
        ("CORS_ORIGINS, PUBLIC_URL", "Allowed websites; address used in emailed links."),
        ("ADMIN_EMAIL", "Receives the uptime alerts."),
    ], ["50%", "50%"], small=True))

    # ---- experiment
    a("<h2>8. Forecasting Experiment</h2><h3>8.1 Method</h3><p>Version 1.0 compared two models on a single hold-out period. This version uses four models and a second test. "
      "For each of four instruments (two Indian shares, the NIFTY 50 index and one US share) about five years of daily data (1,236 to 1,255 trading days) were downloaded. "
      "Eight inputs were computed for each day: close, 7-day and 30-day averages, daily return, 21-day volatility, 14-day RSI, 5-day return and volume relative to its 20-day average. "
      "The target is the next day's close. The models are Linear Regression, Ridge Regression (Hoerl and Kennard, 1970), Random Forest (Breiman, 2001) and Gradient Boosting (Friedman, 2001); "
      "the tree models learn the next-day <i>change</i> because trees cannot predict prices outside the range they have seen. "
      "Two tests were run. In the <b>hold-out</b> test the models train on the first 80% of days and are tested on the last 20%. In the <b>walk-forward</b> test the history is cut into five consecutive "
      "stretches of about 120 days after the first half; for each stretch the models are trained only on earlier days and tested on that stretch (Bergmeir and Ben&iacute;tez, 2012). "
      "All results are compared with the naive guess that tomorrow's close equals today's. The measures are mean absolute error (MAE), the share of days on which the direction of the next close was called correctly, "
      "and, in the walk-forward test, the number of stretches in which a model's error was below the naive error.</p>")
    rows = []
    for sym, v in RESULTS.items():
        m = v["metrics"]
        cells = [e(sym), f"{m['naive']['mae']:,.2f}"]
        for key, _ in MODELS:
            mark = "<b>" if m[key]["mae"] < m["naive"]["mae"] else ""
            end = "</b>" if mark else ""
            cells.append(f"{mark}{m[key]['mae']:,.2f}{end}")
        rows.append(cells)
    a("<h3>8.2 Hold-out results</h3>")
    a(table("Hold-out test: mean absolute error on the last 20% of days (about 240 days) in the instrument's currency. Bold means better than the naive guess.",
            ["Instrument", "Naive"] + [l for _, l in MODELS], rows, ["22%", "14%", "16%", "16%", "16%", "16%"], small=True))
    wrows = []
    for sym, v in RESULTS.items():
        wf = v["walk"]
        cells = [e(sym), f"{wf['naive_mae']:,.2f}"]
        for key, _ in MODELS:
            w = wf["models"][key]
            cells.append(f"{w['mae']:,.2f} ({w['folds_beating_naive']}/{wf['folds']}; {w['direction_accuracy']:.0f}%)")
        wrows.append(cells)
    a("<h3>8.3 Walk-forward results</h3>")
    a(table("Walk-forward test: average error over five stretches, with (stretches in which the model beat the naive guess; share of days with the direction right).",
            ["Instrument", "Naive"] + [l for _, l in MODELS], wrows, ["16%", "12%", "18%", "18%", "18%", "18%"], small=True))
    a(figure(walk_chart(), "Walk-forward error of each model divided by the naive error. A bar below the dashed line beats the naive guess; none is clearly below it."))
    a("<h3>8.4 Discussion</h3><p>On the hold-out test the best model beat the naive guess on two of the four instruments (Linear Regression on Reliance and a Random Forest on the NIFTY 50), but by less than two percent of the error. "
      "The walk-forward test shows that such wins are not reliable: Linear Regression beat the naive guess in four of five stretches for Reliance and three of five for the NIFTY 50, but in none or one of five for the other instruments, "
      "and the Random Forest, the best hold-out model for the NIFTY 50, beat it in only one stretch. The more flexible models, Random Forest and Gradient Boosting, were usually worse than the naive guess, which is "
      "what over-fitting to noisy prices would produce. The direction of the next close was called right on roughly 44% to 56% of days, which is consistent with chance. These findings agree with the weak form of the efficient-market hypothesis "
      "(Fama, 1970): past prices and volume alone carry almost no usable information about the next day. The website therefore shows the baseline beside every model, the walk-forward table and a plain statement when no model wins.</p>"
      "<p><b>Limits of the experiment.</b> It uses four instruments at one point in time, only price and volume inputs, no trading costs, and no formal significance test; five stretches are few. It shows the absence of a consistent advantage; it does not prove that none exists.</p>")

    a("<h2>9. Verification</h2><h3>9.1 Automated tests</h3><p>The project has 122 automated tests (Table 8). They run without the internet, using made-up price data and a temporary database, "
      "and are run by the repository's continuous-integration workflow on every push, together with a syntax check of every script.</p>")
    a(table("The automated test suite.", ["File", "Tests", "What is checked"], [
        ("test_calculators.py", "22", "Tax on 15 lakh (&#8377;97,500), the rebate boundary, marginal relief, caps, break-even; EMI (&#8377;21,696 on 25 lakh at 8.5% for 20 years); budget; FIRE; goals."),
        ("test_market_data.py", "16", "Indicators, comparison, sentiment, AMFI parsing (both layouts), XIRR, SIP, tracker with foreign holdings, stale-cache flag."),
        ("test_accounts.py", "22", "Sign-up, login, one-use tokens, password reset, email confirmation, alerts firing once, limits, account deletion, health."),
        ("test_api_and_ai.py", "17", "Endpoints, CORS, compression, caching, tab numbering, every information icon, tool schemas, AI daily caps."),
        ("test_channels_and_i18n.py", "14", "Push keys and delivery, Telegram linking, a failing channel, Hindi and Marathi translation cache."),
        ("test_ml_and_tax_gains.py", "12", "Four models, forecast range, walk-forward, repeatability, share-market gains in tax."),
        ("test_statement_js.py", "19", "Bank-statement import run under Node: dates, amounts, quoted fields, two statement layouts."),
    ], ["25%", "8%", "67%"], small=True))
    a("<p>A browser test with Playwright opens all twenty-four tools and checks, among other things, that every field label is linked to its input, focus moves to a new section, "
      "the statement import fills the budget, the tax tool includes gains, the AI chat works in Hindi, the account window behaves, and that the phone layout has no sideways scrolling. "
      "The AI integration was tested against a local stand-in that speaks the same streaming protocol; the behaviour of the live model is not part of the automated tests, "
      "because it needs a paid key and its answers vary.</p>")
    a("<h3>9.2 Defects found and corrected</h3>")
    a(table("Defects found while building this version.", ["Defect", "Found by", "Correction"], [
        ("A new module named <i>health</i> hid an older function of the same name, so the health endpoint failed.", "Automated test", "Module imported under another name."),
        ("A half-filled price row from Yahoo (not a number) broke the comparison and history responses.", "Browser test on live data", "Such rows are dropped at the source."),
        ("A sample portfolio used prices from before a share split and showed a false loss of 51%.", "Reading the screen", "Sample prices corrected."),
        ("The HTML <i>hidden</i> attribute was overridden by a button style, so a button showed before email was set up.", "User report", "A rule makes <i>hidden</i> always win."),
        ("Charts without a heading (a fund chart) raised a script error while labelling charts.", "Browser test", "Label code no longer assumes a heading."),
        ("After a password reset, the account window reopened on the reset form.", "Browser test", "The window always starts at log in."),
        ("Daily counters were shared between tests, so a cap test failed.", "Automated test", "Test database is cleared per test."),
    ], ["50%", "20%", "30%"], small=True))
    a("<h3>9.3 Accessibility</h3><p>Measures taken: a skip link, labelled fields, labelled sections and charts, visible keyboard focus, focus moved into a newly opened section, a focus trap in the account window, "
      "table headings marked as column headings, and reduced motion when the user asks for it. No audit with assistive technology or against the full WCAG 2.2 criteria has been done.</p>")

    a("<h2>10. Running and Deploying</h2><p>To run locally: create a virtual environment, install <i>requirements.txt</i>, optionally put settings in a <i>.env</i> file (not committed), and start "
      "<i>python app/main.py</i>. To test: install <i>requirements-dev.txt</i> and run <i>python -m pytest</i>. The deployed system runs on a small Ubuntu server (about 1 GB of memory, with a 2 GB swap file) "
      "using the scripts in the <i>deploy</i> folder: <i>setup.sh</i> installs the service, nginx, the firewall, the backup and the uptime check; <i>update.sh</i> pulls the latest code and restarts. "
      "A serverless deployment also works, with two differences: stored accounts can be reset when the host recycles its storage, and the background worker does not run, so alerts are checked only while a page is open.</p>"
      "<p>Browsers allow service workers, installation and push notifications only on secure (HTTPS) addresses, so these features need a domain name with a certificate.</p>")

    a("<h2>11. Limitations and Future Work</h2><p>Market data comes from unofficial sources and can be delayed or unavailable. The tax tool is a simplified model; it does not cover every income type or the surcharge on share gains. "
      "The assistant can make mistakes and its tax and investment statements should be checked in the calculators. Hindi and Marathi texts are machine translations that have not been reviewed by a person. "
      "SQLite limits the system to one server. No study with real users has been carried out. Future work includes human review of the translations, an accessibility audit, a second data source for prices, "
      "and a larger forecasting study with more instruments and a significance test.</p>")
    a("<h2>12. Conclusion</h2><p>FinSuite now offers twenty-four explained tools, a tool-using assistant, optional accounts with alerts on three channels, and an installable offline app, "
      "while keeping each result checkable. The additions were made with limits on cost and use, backups and monitoring, and 122 automated tests. The forecasting experiment again found no consistent advantage over the naive guess, "
      "and the website says so.</p>")

    a("<h2>References</h2><ol class='refs'>"
      "<li>Bergmeir, C. and Ben&iacute;tez, J. M. (2012). On the use of cross-validation for time series predictor evaluation. <i>Information Sciences</i>, 191, 192&ndash;213.</li>"
      "<li>Bollinger, J. (2001). <i>Bollinger on Bollinger Bands</i>. McGraw-Hill.</li>"
      "<li>Breiman, L. (2001). Random forests. <i>Machine Learning</i>, 45(1), 5&ndash;32.</li>"
      "<li>Fama, E. F. (1970). Efficient capital markets: a review of theory and empirical work. <i>The Journal of Finance</i>, 25(2), 383&ndash;417.</li>"
      "<li>Friedman, J. H. (2001). Greedy function approximation: a gradient boosting machine. <i>The Annals of Statistics</i>, 29(5), 1189&ndash;1232.</li>"
      "<li>Hoerl, A. E. and Kennard, R. W. (1970). Ridge regression: biased estimation for nonorthogonal problems. <i>Technometrics</i>, 12(1), 55&ndash;67.</li>"
      "<li>Loughran, T. and McDonald, B. (2011). When is a liability not a liability? Textual analysis, dictionaries, and 10-Ks. <i>The Journal of Finance</i>, 66(1), 35&ndash;65.</li>"
      "<li>Moriarty, K., Kaliski, B. and Rusch, A. (2017). PKCS #5: Password-Based Cryptography Specification Version 2.1. RFC 8018. IETF.</li>"
      "<li>Pedregosa, F. et al. (2011). Scikit-learn: machine learning in Python. <i>Journal of Machine Learning Research</i>, 12, 2825&ndash;2830.</li>"
      "<li>Thomson, M., Damaggio, E. and Raymor, B. (2016). Generic Event Delivery Using HTTP Push. RFC 8030. IETF.</li>"
      "<li>Thomson, M. and Beverloo, P. (2017). Voluntary Application Server Identification (VAPID) for Web Push. RFC 8292. IETF.</li>"
      "<li>Wilder, J. W. (1978). <i>New Concepts in Technical Trading Systems</i>. Trend Research.</li>"
      "<li>World Wide Web Consortium (2023). Web Content Accessibility Guidelines (WCAG) 2.2.</li>"
      "<li>Association of Mutual Funds in India. Daily NAV file (NAVAll.txt), amfiindia.com; and mfapi.in, free mutual fund NAV API.</li>"
      "<li>Government of India. Income-tax Act, 1961, as amended by the Finance Act, 2025 (slabs, rebate under section 87A, capital-gains rates).</li>"
      "<li>Anthropic (2026). Claude API documentation (messages, tool use, streaming), platform.claude.com/docs.</li>"
      "<li>FastAPI documentation, fastapi.tiangolo.com; yfinance library, github.com/ranaroussi/yfinance; Chart.js, chartjs.org.</li></ol>")
    return "".join(t)


CSS = """
@page { size: A4; margin: 17mm 19mm 20mm 19mm; }
* { box-sizing: border-box; }
body { font-family: 'Times New Roman', Times, serif; font-size: 10.6pt; line-height: 1.36; color: #000; margin: 0; text-align: justify; }
h1.title { text-align: center; font-size: 25pt; margin: 6mm 0 2mm; }
.subtitle { text-align: center; font-style: italic; font-size: 12.5pt; margin: 0 0 6mm; }
.author { text-align: center; margin: 2mm 0; font-size: 10.6pt; }
hr { border: 0; border-top: 1px solid #000; margin: 5mm 0; }
.abstract { margin: 0 8mm; font-size: 10pt; }
.abshead { text-align: center; font-weight: bold; font-style: italic; margin: 0 0 2mm; }
h2 { font-size: 13.5pt; margin: 6mm 0 2mm; break-after: avoid; }
h3 { font-size: 11.2pt; font-style: italic; margin: 4mm 0 1.5mm; break-after: avoid; }
p { margin: 0 0 2.4mm; orphans: 3; widows: 3; }
.cap { font-size: 9.4pt; font-weight: bold; text-align: left; margin: 3mm 0 1mm; break-after: avoid; }
.figcap { text-align: center; font-weight: normal; font-style: italic; }
.tblwrap { margin: 2mm 0 4mm; }
table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 9.6pt; border-top: 1.5px solid #000; border-bottom: 1.5px solid #000; }
table.small { font-size: 8.8pt; }
th { border-bottom: 1px solid #000; padding: 1.2mm 1.6mm; text-align: left; font-weight: bold; }
td { padding: 1mm 1.6mm; vertical-align: top; text-align: left; border-bottom: 0.4px solid #bbb; overflow-wrap: anywhere; }
tr { break-inside: avoid; }
thead { display: table-header-group; }
.fig { margin: 3mm 0 4mm; break-inside: avoid; }
svg text { font-family: 'Times New Roman', serif; }
ol.refs { font-size: 9.6pt; padding-left: 6mm; text-align: left; }
ol.refs li { margin-bottom: 1.2mm; }
sub, sup { font-size: 70%; line-height: 0; }
"""


def main() -> None:
    from playwright.sync_api import sync_playwright
    doc = f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>FinSuite technical documentation</title><style>{CSS}</style></head><body>{build()}</body></html>"
    (HERE / "technical_documentation.html").write_text(doc, encoding="utf-8")
    footer = ("<div style=\"width:100%;text-align:center;font-family:'Times New Roman',serif;font-size:9px;padding-bottom:6mm;\">"
              "Page <span class='pageNumber'></span> of <span class='totalPages'></span></div>")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(doc)
        page.pdf(path=str(HERE / "FinSuite_Technical_Documentation.pdf"), format="A4", print_background=True,
                 display_header_footer=True, header_template="<div></div>", footer_template=footer,
                 margin={"top": "17mm", "bottom": "20mm", "left": "19mm", "right": "19mm"})
        browser.close()
    add_border(HERE / "FinSuite_Technical_Documentation.pdf")
    print("written", HERE / "FinSuite_Technical_Documentation.pdf")


def add_border(path: Path) -> None:
    """Draw the double-line page border on every page of the finished PDF."""
    import pymupdf
    pdf = pymupdf.open(path)
    for page in pdf:
        r = page.rect
        page.draw_rect(pymupdf.Rect(r.x0 + 15, r.y0 + 15, r.x1 - 15, r.y1 - 15), color=(0, 0, 0), width=2.2)
        page.draw_rect(pymupdf.Rect(r.x0 + 20, r.y0 + 20, r.x1 - 20, r.y1 - 20), color=(0, 0, 0), width=0.7)
    tmp = path.with_suffix(".tmp.pdf")
    pdf.save(tmp)
    pdf.close()
    tmp.replace(path)


if __name__ == "__main__":
    main()
