# FinSuite

An AI-assisted personal finance and live stock market analysis platform — a
FastAPI backend with a plain HTML/CSS/JavaScript frontend. Built as an
internship project ("AI in Finance") by **Purva Gajanan Kakade** under the
guidance of **Prof. Ashish Singh (SJMSOM, IIT Bombay)**.

Full project report: [docs/FinSuite_Project_Report.pdf](docs/FinSuite_Project_Report.pdf)
(editable version: `docs/FinSuite_Project_Report.docx`).

## Features

24 tools in one console, grouped into four menus (Personal finance, Markets &
investing, Business & credit, Learn & info), each backed by a documented REST endpoint:

| Menu | # | Tool |
|---|---|---|
| Personal finance | 01 | Personal finance report |
|  | 02 | Finance assistant (snapshot + term lookup) |
|  | 03 | Budget planner (50/30/20 rule) |
|  | 04 | Income tax: old vs new regime (FY 2025-26) |
|  | 05 | Loan EMI, repayment table, prepayment savings |
|  | 06 | Goal planner, emergency fund |
|  | 07 | Retirement & FIRE planner |
| Markets & investing | 08 | Live stock market: quotes, chart with SMA/EMA/Bollinger/RSI, OHLC history, news with sentiment |
|  | 09 | Currency converter and two-stock comparison |
|  | 10 | Watchlist & price alerts (saved, background checks, email) |
|  | 11 | Portfolio tracker at live prices (P&L in INR) |
|  | 12 | Mutual fund search, NAV chart, SIP returns (XIRR) |
|  | 13 | What-if growth, target / stop-loss planner |
|  | 14 | SIP vs lump sum, capital gains tax (India), 52-week range |
|  | 15 | ML price prediction, with news mood next to the forecast |
| Business & credit | 16 | Ratio calculators (ROE, ROA, debt ratio, health) |
|  | 17 | Loan insight generator |
|  | 18 | Credit score & customer risk |
|  | 19 | Investment BUY / HOLD / AVOID |
|  | 20 | Company performance score |
|  | 21 | Multi-company portfolio screener |
| Learn & info | 22 | Knowledge centre (95 plain-language entries) |
|  | 23 | Data sources |
|  | 24 | About |

Across the app: dark mode, a phone-friendly menu, ⓘ icons that open the
Knowledge Centre explanation of a term, and PDF / Excel downloads for the
finance report, goal plan, loan table, income tax, EMI schedule, budget,
portfolio, retirement plan and SIP results.

**Accounts (optional).** Creating an account saves the watchlist, portfolio and
price alerts on the server (SQLite, passwords stored as salted PBKDF2 hashes).
Without an account they are kept in the browser. For logged-in users a
background worker checks alerts every 5 minutes and emails them if SMTP is
configured (see `deploy/HOSTINGER.md`).

Live data needs **no API key**: quotes, history, exchange rates and company
search come from Yahoo Finance via `yfinance`, news from Google News RSS, and
mutual fund NAVs from AMFI (history via the free mfapi.in mirror).

## Run it

```bash
python -m venv agentic_env
agentic_env\Scripts\activate          # Windows  (source agentic_env/bin/activate on macOS/Linux)
pip install -r requirements.txt
python app/main.py                    # or: uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 for the app and http://127.0.0.1:8000/docs for the
interactive API documentation. Set `PORT` to use a different port.

Quick check of the market-data layer without the server:

```bash
python -m app.market TCS
```

### Settings (environment variables, all optional)

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Turns on the AI Assistant (Claude with FinSuite's calculators and live data as tools); without it the chat answers from the Knowledge Center |
| `FINSUITE_AI_MODEL` | Model for the AI Assistant (default `claude-opus-5-5`) |
| `FINSUITE_DB` | SQLite file for accounts and saved data (default `data/finsuite.db`) |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Email delivery for price alerts |
| `ALERT_INTERVAL` | Seconds between background alert checks (default 300) |
| `FINSUITE_ALERT_WORKER=0` | Turn the background worker off |
| `CRON_SECRET` | Enables `POST /alerts/run-check` for hosts without a background worker |

On Vercel the project folder is read-only and `/tmp` is wiped, so accounts there
are temporary (the app says so in the login box) and the background worker does
not run. For permanent accounts and background alerts, use the VPS setup in
`deploy/HOSTINGER.md`, or point `FINSUITE_DB` at persistent storage and call
`/alerts/run-check` from a cron job.

## Project structure

```
app/
  main.py          FastAPI app: routes, error mapping, serves the frontend
  calculators.py   Pure financial formulas for the calculator modules
  market.py        Live data: company search, symbol resolution, quotes,
                   history, news, in-memory TTL cache
  predict.py       ML next-day prediction pipeline (uses backend/services)
  ai_assistant.py  AI chat: Claude with FinSuite functions as tools, streamed
  planning.py      Income tax, loan EMI, 50/30/20 budget, retirement / FIRE
  analysis.py      Chart indicators, two-stock comparison, headline sentiment
  mf.py            Mutual fund NAVs (AMFI) and SIP returns with XIRR
  tracker.py       Portfolio valuation at live prices, converted to INR
  store.py         Accounts, saved data and alerts (SQLite)
  alerts.py        Background price-alert worker and email
  schemas.py       Pydantic request models
  glossary.py      Knowledge-centre Q&A
backend/services/
  features.py      Data cleaning + technical features (MA7/MA30, returns,
                   volatility, RSI)
  ml_models.py     Linear Regression and Random Forest (scikit-learn)
  simulate.py      Synthetic OHLCV generator for practice
frontend/
  index.html, app.js, style.css
docs/
  FinSuite_Project_Report.docx / .pdf
```

## Notes

- Yahoo Finance data via `yfinance` is unofficial and may be delayed; this is
  an educational tool, not investment advice.
- The ML tab (`GET /ml/predict`) trains on the stock's own history and is shown
  next to a naive "tomorrow = today" baseline; short-term prices are hard to
  predict, so treat forecasts as educational, not as trading signals.
