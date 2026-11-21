"""Adds "Chapter 9: Version 2.0" (before the References) and "Appendix D: Screens of the
version 2.0 tools" (at the end) to docs/FinSuite_Project_Report.docx.

    python docs/update_project_report.py <folder with the d*.png screenshots>

Afterwards open the file in Word, or run docs/export_report_pdf.ps1, to refresh the table
of contents and write the PDF. Run it once: running it again adds the chapter again.
"""
import json
import sys
from pathlib import Path

import docx
from docx.shared import Mm
from PIL import Image

HERE = Path(__file__).resolve().parent
SHOTS = Path(sys.argv[1])
RESULTS = json.loads((HERE / "experiment_results.json").read_text(encoding="utf-8"))
d = docx.Document(HERE / "FinSuite_Project_Report.docx")

if any(p.text.startswith("Chapter 9:") for p in d.paragraphs):
    sys.exit("Chapter 9 is already in this report; nothing to do.")
refs = next(p for p in d.paragraphs if p.style.name == "Heading 1" and p.text.strip() == "References")
table_style = d.tables[1].style if len(d.tables) > 1 else None
moved = []   # elements built at the end of the file, moved in front of the References


def keep(el):
    moved.append(el)
    return el


def heading(text, level):
    return keep(d.add_heading(text, level=level)._p)


def para(text, style=None):
    return keep(d.add_paragraph(text, style=style)._p)


def bullets(items):
    for t in items:
        keep(d.add_paragraph(t, style="List Bullet")._p)


_tables = [0]


def tbl(caption, header, rows):
    _tables[0] += 1
    cap = d.add_paragraph(f"Table 9.{_tables[0]}: {caption}", style="Caption"); keep(cap._p)
    t = d.add_table(rows=1, cols=len(header))
    if table_style is not None:
        t.style = table_style
    for i, h in enumerate(header):
        t.rows[0].cells[i].text = h
        for r in t.rows[0].cells[i].paragraphs[0].runs:
            r.bold = True
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = str(v)
    keep(t._tbl)
    keep(d.add_paragraph("")._p)


# ------------------------------------------------------------------ Chapter 9
heading("Chapter 9: Version 2.0: AI Assistant, Accounts, Alerts and New Tools", 1)
heading("9.1 Scope of the second phase", 2)
para("After the first version was completed, the system was extended in a second phase (November 2026). The extension has four aims: to widen what the site can do "
     "(seven new tools and a conversational assistant), to keep what a user saves (optional accounts, alerts that work when no page is open), to protect the system and its "
     "operator (limits on use, backups, monitoring, automated tests), and to reach more people (phone and keyboard use, an installable offline app, Hindi and Marathi). "
     "The number of tools grew from seventeen to twenty-four, the menu was grouped into four drop-down menus, and the tools were renumbered 01 to 24 in menu order.")
heading("9.2 New tools", 2)
tbl("Tools added in version 2.0.", ["Tool", "What it does", "Method"], [
    ("Income Tax", "Old and new regime for FY 2025-26 side by side; shows which saves more and the deductions at which the old regime would win; adds tax on share-market gains.",
     "Slab tables, rebate with marginal relief, surcharge, 4% cess; break-even found by bisection."),
    ("Loan EMI", "EMI, month-by-month or year-by-year repayment table, interest saved by a one-time or monthly prepayment.", "Standard EMI formula and an amortisation loop."),
    ("Budget Planner", "Compares spending with the 50/30/20 rule; can fill itself from a bank statement (CSV).", "Rule-based categories; the statement is read in the browser and never uploaded."),
    ("Mutual Funds and SIP", "Search every Indian scheme; NAV chart; returns of a monthly SIP with XIRR.", "AMFI daily file and mfapi.in; XIRR by bisection."),
    ("Portfolio Tracker", "Values holdings at live prices; foreign holdings are converted to rupees.", "Yahoo Finance quotes and exchange rates."),
    ("Retirement and FIRE", "Corpus needed, required monthly SIP, financial-independence age, whether the money lasts.", "Present value of a growing annuity at the real return."),
    ("Currency and Compare", "Live exchange rates; two stocks rebased to 100 with return, volatility, drawdown and correlation.", "Yahoo Finance history."),
])
para("Existing tools were also improved. The stock chart can show 20 and 50 day averages, a 20 day exponential average, Bollinger bands and the 14 day RSI, with a plain-language reading of each. "
     "News headlines are marked positive, neutral or negative from a finance word list, and the forecasting tab shows whether the news mood agrees with the forecast. "
     "A portfolio value can be copied into the retirement and goal planners. Every result that is worth keeping (finance report, goal plan, loan table, income tax, EMI schedule, budget, "
     "portfolio, retirement plan and SIP result) can be downloaded as a PDF or an Excel file, and an information icon next to a term opens its Knowledge Center entry.")
heading("9.3 The AI Assistant", 2)
para("In version 1.0 the assistant only looked up stored definitions. In version 2.0 it is a language model that can call sixteen tools, each wrapping a function that already exists in FinSuite "
     "(live quote, indicators, comparison, news sentiment, company and fund search, currency, income tax, EMI, goal and retirement planning, budget, SIP returns, portfolio valuation, "
     "price forecast and a Knowledge Center lookup). The model chooses the tools; FinSuite validates every tool input, runs the tool and returns the result, so the numbers in an answer come from tested code "
     "and not from the model's memory. The answer is streamed to the page and shown as sanitised Markdown. The assistant can answer in English, Hindi or Marathi, knows the user's saved watchlist and portfolio, "
     "and keeps its chat history in the browser and, for logged-in users, in the account. Without an API key it falls back to the stored definitions.")
tbl("Limits that bound the cost of the AI service.", ["Limit", "Default"], [
    ("Questions per minute", "6 per address"),
    ("Questions per day", "30 for a guest, 100 for a logged-in user, 500 for the whole site"),
    ("Answer length", "8,000 tokens"),
    ("Conversation size", "40,000 characters; the last 24 messages are sent"),
    ("Tool rounds per question", "8"),
])
heading("9.4 Accounts, alerts and notifications", 2)
para("An account is optional. It stores the watchlist, portfolio, alerts and chat history in a SQLite file; passwords are kept as PBKDF2-HMAC-SHA256 hashes with a random salt and 200,000 rounds. "
     "Password-reset and email-confirmation links and Telegram link codes are one-time tokens stored as hashes. A user can delete the account and all its data. "
     "A background worker checks every pending price alert every five minutes, even when no page is open. An alert fires once and is then re-armed by the user. "
     "A fired alert is sent to every channel the user has set up: email, browser push notification (Web Push with VAPID keys) and Telegram (through a bot linked with a one-time code). "
     "A failing channel does not stop the others. WhatsApp is not supported because it needs a verified business account.")
heading("9.5 Reliability and security", 2)
bullets([
    "Rate limits on every costly path: any call (240 a minute per address), price forecast (5 a minute), log in (10 a minute per address and 8 per 15 minutes per email), account creation, and emails sent.",
    "Browsers may call the API only from FinSuite's own addresses; text from the AI is sanitised before display.",
    "Responses are compressed, and files carry a version in their address so that they can be cached for a year without ever being stale.",
    "If Yahoo Finance fails, the last good price is shown and marked as delayed instead of an error.",
    "A daily online backup of the database (checked and compressed, fourteen copies kept) and an uptime check every five minutes that emails the administrator after two failures.",
    "A live status panel on the Data Sources tab shows whether each outside source is responding.",
])
heading("9.6 Access for more people", 2)
para("The interface was redesigned with a formal look and a dark mode. On a phone the four menus become one menu. The site has a skip link, labelled fields, labelled sections and charts, "
     "visible keyboard focus, and respects the reduced-motion setting. It can be installed as an app, opens its last page without a connection, and can show push alerts. "
     "The AI assistant answers in Hindi and Marathi, and the Knowledge Center is translated once by the model into both languages and stored. "
     "These are machine translations that have not been reviewed by a person. Installation and push notifications need a secure (HTTPS) address.")
heading("9.7 Revised forecasting experiment", 2)
para("The forecasting experiment of Chapter 5 was repeated with four models (Linear, Ridge, Random Forest and Gradient Boosting), eight inputs (adding RSI, the 5-day return and relative volume) "
     "and a second test, a walk-forward test over five stretches of about 120 days in which each model is trained only on earlier days. Four instruments and about five years of daily data were used. "
     "Table 9.3 gives the average walk-forward error with, in brackets, the number of the five stretches in which the model beat the naive guess that tomorrow's close equals today's.")
rows = []
for sym, v in RESULTS.items():
    wf = v["walk"]
    cells = [sym, f"{wf['naive_mae']:,.2f}"]
    for key in ("linear", "ridge", "random_forest", "gradient_boosting"):
        w = wf["models"][key]
        cells.append(f"{w['mae']:,.2f} ({w['folds_beating_naive']}/5)")
    rows.append(cells)
tbl("Walk-forward results: average absolute error (stretches beating the naive guess).", ["Instrument", "Naive", "Linear", "Ridge", "Random Forest", "Gradient Boosting"], rows)
para("The result is the same as in version 1.0. Two models beat the naive guess on a single hold-out test (Linear Regression on Reliance and a Random Forest on the NIFTY 50), but by less than two percent, "
     "and the walk-forward test showed that these wins were not consistent. The tree models were usually worse than the naive guess, which is what over-fitting to noisy prices would produce, "
     "and the direction of the next close was called right on about 44% to 56% of days, close to chance. The website shows the naive baseline and the walk-forward table next to every forecast and says so when no model wins.")
heading("9.8 Testing", 2)
para("The project now has 122 automated tests that run without the internet: 22 on the calculators, 16 on market data, mutual funds and the tracker, 22 on accounts and alerts, 17 on the API and the AI assistant, "
     "14 on push, Telegram and translations, 12 on the models and tax on gains, and 19 on the bank-statement importer (run under Node). They run on every push to the repository. "
     "A browser test opens all twenty-four tools and exercises the main new features. The AI integration was tested against a local stand-in that speaks the same streaming protocol; the live model's answers are not part of the automated tests.")
tbl("Defects found while building version 2.0.", ["Defect", "Found by", "Correction"], [
    ("A new module named health hid an older function of the same name.", "Automated test", "Module imported under another name."),
    ("A half-filled price row from Yahoo broke the comparison and history responses.", "Browser test on live data", "Such rows are dropped at the source."),
    ("A sample portfolio used pre-split prices and showed a false loss of 51%.", "Reading the screen", "Sample prices corrected."),
    ("A button style overrode the hidden attribute, so a button showed too early.", "User report", "A rule makes hidden always win."),
    ("A chart without a heading raised a script error.", "Browser test", "Label code no longer assumes a heading."),
    ("After a password reset the account window reopened on the reset form.", "Browser test", "The window always starts at log in."),
])
heading("9.9 Deployment", 2)
para("The system runs on a small Ubuntu server behind nginx and is restarted automatically by systemd; scripts in the deploy folder install it, update it, back it up and monitor it. "
     "A serverless deployment also works, but stored accounts there can be reset and the background alert worker does not run. "
     "Settings such as the AI key, the mail account and the Telegram bot token are environment variables and are never stored in the repository.")

# move chapter 9 in front of the References
for el in moved:
    refs._p.addprevious(el)

# ------------------------------------------------------------------ Abstract: one closing sentence
abstract_head = next(p for p in d.paragraphs if p.style.name == "Heading 1" and p.text.strip() == "Abstract")
nxt = abstract_head._p.getnext()
last = None
while nxt is not None and not (nxt.tag.endswith("}p") and "Heading" in (docx.text.paragraph.Paragraph(nxt, d).style.name or "")):
    if nxt.tag.endswith("}p") and docx.text.paragraph.Paragraph(nxt, d).text.strip():
        last = docx.text.paragraph.Paragraph(nxt, d)
    nxt = nxt.getnext()
if last is not None:
    last.add_run(" A second phase (version 2.0, November 2026, Chapter 9) added seven tools, a tool-using AI assistant, optional accounts with price alerts by email, push notification "
                 "and Telegram, limits and backups for safe operation, Hindi and Marathi, and 122 automated tests.")

# ------------------------------------------------------------------ Appendix D (at the end)
d.add_heading("Appendix D: Screens of the Version 2.0 Tools", 1)
shots = [
    ("d1_income_tax", "Income tax: old and new regime with deductions and share-market gains."),
    ("d2_loan_emi", "Loan EMI with the repayment table and the interest saved by a prepayment."),
    ("d3_budget", "Budget planner filled from a bank statement (CSV), with the 50/30/20 check."),
    ("d4_mutual_funds", "Mutual fund NAV chart and SIP returns."),
    ("d5_tracker", "Portfolio tracker valued at live prices."),
    ("d6_fire", "Retirement and FIRE planner."),
    ("d7_currency", "Currency converter with the three-month rate chart."),
    ("d8_ml", "Price prediction with four models, the naive baseline and the walk-forward test."),
    ("d9_market_indicators", "Stock chart with moving averages, Bollinger bands, RSI and the reading of each."),
    ("d10_status", "Data Sources tab with the live status of each outside source."),
    ("d11_account", "Account window: log in, create account, forgot password."),
]
for n, (name, caption) in enumerate(shots, 1):
    img = SHOTS / f"{name}.png"
    w, h = Image.open(img).size
    width_mm = min(150, 225 * w / h)
    p = d.add_paragraph(); p.alignment = 1
    p.add_run().add_picture(str(img), width=Mm(width_mm))
    d.add_paragraph(f"Figure D.{n}: {caption}", style="Caption")

# ask Word to refresh the table of contents and page numbers when the file is opened
settings = d.settings.element
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
if settings.find(qn("w:updateFields")) is None:
    el = OxmlElement("w:updateFields"); el.set(qn("w:val"), "true"); settings.append(el)

d.save(HERE / "FinSuite_Project_Report.docx")
print("saved; new elements:", len(moved), "pictures:", len(d.inline_shapes))
