# FinSuite

An AI-assisted personal finance and live stock market analysis platform — a
FastAPI backend with a plain HTML/CSS/JavaScript frontend. Built as an
internship project ("AI in Finance") by **Purva Gajanan Kakade** under the
guidance of **Prof. Ashish Singh (SJMSOM, IIT Bombay)**.

Full project report: [docs/FinSuite_Project_Report.pdf](docs/FinSuite_Project_Report.pdf)
(editable version: `docs/FinSuite_Project_Report.docx`).

## Features

16 tools in one console, each backed by a documented REST endpoint:

| # | Module | # | Module |
|---|---|---|---|
| 01 | Ratio calculators (ROE, ROA, debt ratio, health) | 09 | Goal & retirement planner, emergency fund |
| 02 | Personal finance report | 10 | Knowledge centre (glossary) |
| 03 | Finance assistant (snapshot + term lookup) | 11 | **Live stock market** — any company, quotes, chart, OHLC history, news |
| 04 | Loan insight generator | 12 | What-if growth, target / stop-loss planner |
| 05 | Credit score & customer risk | 13 | SIP vs lump sum, capital gains tax (India), 52-week range |
| 06 | Investment BUY / HOLD / AVOID | 14 | Live watchlist & price alerts |
| 07 | Company performance score | 15 | API key directory (none needed) |
| 08 | Multi-company portfolio screener | 16 | About |

Live market data needs **no API key**: quotes, history and company search come
from Yahoo Finance via `yfinance`, and news from Google News RSS.

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

## Project structure

```
app/
  main.py          FastAPI app: routes, error mapping, serves the frontend
  calculators.py   Pure financial formulas for the calculator modules
  market.py        Live data: company search, symbol resolution, quotes,
                   history, news, in-memory TTL cache
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
- The ML pipeline in `backend/services` is used for offline experiments (see
  Chapter 5 of the report); it is not exposed in the UI.
