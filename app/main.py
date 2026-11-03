import sys
from pathlib import Path

# Allow `python app/main.py` (e.g. VS Code's Run button) as well as
# `uvicorn app.main:app`: put the project root on the path and treat this
# file as part of the `app` package so the imports below resolve.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "app"

import os
from contextlib import asynccontextmanager


def _load_env_file(path: Path) -> None:
    """Read KEY=VALUE lines from a local .env (e.g. SMTP settings) without
    overriding variables that are already set. The file is not committed."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(Path(__file__).resolve().parent.parent / ".env")

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from app import calculators as calc
from . import schemas as s
from . import market
from . import analysis, alerts, mf, planning, store, tracker
from .glossary import GLOSSARY


@asynccontextmanager
async def lifespan(_app):
    stop = alerts.start_worker()   # background price-alert checks (not on Vercel)
    yield
    if stop:
        stop.set()


app = FastAPI(
    title="FinSuite API",
    description="Python port of the FinSuite finance-suite calculators.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.middleware("http")
async def no_stale_frontend(request, call_next):
    # Make the browser re-check the page/JS/CSS on every load (cheap 304 if
    # unchanged), so code updates show up without a hard refresh.
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


def _wrap(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ---------------------------------------------------------------------------
# 16 Ratio calculators
# ---------------------------------------------------------------------------
@app.post("/ratios/roe", tags=["16 Ratios"])
def roe(body: s.ROEIn):
    return {"roe_pct": _wrap(calc.calc_roe, body.net_income, body.equity)}


@app.post("/ratios/roa", tags=["16 Ratios"])
def roa(body: s.ROAIn):
    return {"roa_pct": _wrap(calc.calc_roa, body.net_income, body.assets)}


@app.post("/ratios/debt-ratio", tags=["16 Ratios"])
def debt_ratio(body: s.DebtRatioIn):
    return {"debt_ratio": _wrap(calc.calc_debt_ratio, body.liabilities, body.assets)}


@app.post("/ratios/health", tags=["16 Ratios"])
def health(body: s.HealthIn):
    return {"health": calc.calc_health(body.roe)}


# ---------------------------------------------------------------------------
# 01 Personal finance report
# ---------------------------------------------------------------------------
@app.post("/report", tags=["01 Personal Finance Report"])
def report(body: s.ReportIn):
    return _wrap(calc.calc_report, body.income, body.expenses, body.savings, body.debt, body.equity)

# ---------------------------------------------------------------------------
# 02 AI Finance Assistant
# ---------------------------------------------------------------------------
@app.post("/assistant/snapshot", tags=["02 AI Finance Assistant"])
def assistant_snapshot(body: s.AssistantIn):
    return _wrap(calc.calc_assistant, body.income, body.expenses, body.savings, body.borrowed, body.owned)

@app.post("/assistant/chat", tags=["02 AI Finance Assistant"])
def assistant_chat(body: s.ChatIn):
    return {"answer": calc.chat_reply(body.question)}

# ---------------------------------------------------------------------------
# 17 Loan insight generator
# ---------------------------------------------------------------------------
@app.post("/loans/screen", tags=["17 Loan Insight Generator"])
def loans_screen(body: s.LoanScreenIn):
    rows = [r.model_dump() for r in body.rows]
    return {"rows": calc.screen_loans(rows)}

# ---------------------------------------------------------------------------
# 18 Credit score & risk dashboard
# ---------------------------------------------------------------------------
@app.post("/credit-score", tags=["18 Credit Score & Risk"])
def credit_score(body: s.CreditScoreIn):
    return _wrap(calc.calc_credit_score, body.score)


@app.post("/risk", tags=["18 Credit Score & Risk"])
def risk(body: s.RiskIn):
    return calc.calc_risk(body.score, body.income, body.emi, body.name)


# ---------------------------------------------------------------------------
# 19 Investment recommendation
# ---------------------------------------------------------------------------
@app.post("/invest", tags=["19 Investment Recommendation"])
def invest(body: s.InvestIn):
    return calc.calc_invest(body.revenue_growth, body.profit_margin, body.roa, body.roe)


# ---------------------------------------------------------------------------
# 20 Company performance
# ---------------------------------------------------------------------------
@app.post("/company-performance", tags=["20 Company Performance"])
def company_performance(body: s.CompanyPerfIn):
    return calc.analyze_company(body.name, body.revenue_growth, body.csat, body.retention)


# ---------------------------------------------------------------------------
# 21 Portfolio dashboard
# ---------------------------------------------------------------------------
@app.post("/portfolio", tags=["21 Portfolio Dashboard"])
def portfolio(body: s.PortfolioIn):
    rows = [c.model_dump() for c in body.companies]
    results = [calc.compute_company_metrics(r) for r in rows]
    results.sort(key=lambda r: r["score"], reverse=True)
    return {"companies": results}


# ---------------------------------------------------------------------------
# 06 Goal & retirement planner
# ---------------------------------------------------------------------------
@app.post("/goals/plan", tags=["06 Goal & Retirement Planner"])
def goals_plan(body: s.GoalPlanIn):
    return _wrap(calc.calc_goal_plan, body.target, body.years, body.ret, body.inflation,
                 body.current, body.income, body.name)


@app.post("/goals/emergency-fund", tags=["06 Goal & Retirement Planner"])
def goals_emergency_fund(body: s.EmergencyFundIn):
    return _wrap(calc.calc_emergency_fund, body.expenses, body.savings)


# ---------------------------------------------------------------------------
# 22 Knowledge center
# ---------------------------------------------------------------------------
@app.get("/knowledge/glossary", tags=["22 Knowledge Center"])
def knowledge_glossary():
    return {"glossary": GLOSSARY}


# ---------------------------------------------------------------------------
# 08 Stock market workspace — live data, no API key required (yfinance +
#    Google News RSS, see app/market.py)
# ---------------------------------------------------------------------------
def _market(fn, *args):
    try:
        return fn(*args)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream data source failed: {e}")


@app.get("/market/search", tags=["08 Stock Market"])
def market_search(q: str = Query(..., min_length=1), limit: int = Query(8, ge=1, le=20)):
    return {"query": q, "results": _market(market.search_symbols, q, limit)}


@app.get("/market/quote", tags=["08 Stock Market"])
def market_quote(symbol: str = Query(..., min_length=1)):
    return _market(market.get_quote, symbol)

@app.get("/market/daily", tags=["08 Stock Market"])
def market_daily(symbol: str = Query(..., min_length=1),
                 period: str = Query("3mo", pattern="^(1mo|3mo|6mo|1y|2y|5y|max)$")):
    return {"symbol": symbol, **_market(market.get_history, symbol, period)}


@app.get("/market/news", tags=["08 Stock Market"])
def market_news(symbols: str = Query("", description="Tickers or search text; empty = general market news"),
                limit: int = Query(10, ge=1, le=50)):
    """Headlines, each marked positive / neutral / negative, plus an overall mood."""
    return {"query": symbols, **_market(analysis.news_with_sentiment, symbols, limit)}


@app.get("/market/indicators", tags=["08 Stock Market"])
def market_indicators(symbol: str = Query(..., min_length=1),
                      period: str = Query("6mo", pattern="^(1mo|3mo|6mo|1y|2y|5y|max)$")):
    """20/50-day moving averages, 20-day EMA, Bollinger bands (20, 2) and 14-day RSI."""
    return _market(analysis.get_indicators, symbol, period)


# ---------------------------------------------------------------------------
# 13 Growth & target planner
# ---------------------------------------------------------------------------
@app.post("/planner/what-if", tags=["13 Growth & Target Planner"])
def planner_what_if(body: s.WhatIfIn):
    return _wrap(calc.calc_what_if, body.amount, body.price_then, body.price_now, body.days_held)


@app.post("/planner/target-plan", tags=["13 Growth & Target Planner"])
def planner_target_plan(body: s.TargetPlanIn):
    return _wrap(calc.calc_target_plan, body.entry, body.qty, body.target_pct, body.stop_pct)


# ---------------------------------------------------------------------------
# 14 Portfolio & tax tools
# ---------------------------------------------------------------------------
@app.post("/tools/sip-vs-lumpsum", tags=["14 Portfolio & Tax Tools"])
def tools_sip_vs_lumpsum(body: s.SipVsLumpIn):
    return _wrap(calc.compare_sip_lump_sum, body.total, body.months, body.start_price,
                 body.prices_by_month, body.last_price)


@app.post("/tools/capital-gains-tax", tags=["14 Portfolio & Tax Tools"])
def tools_capital_gains_tax(body: s.CapitalGainsTaxIn):
    return _wrap(calc.estimate_capital_gains_tax, body.buy_price, body.sell_price, body.qty,
                 body.buy_date, body.sell_date, body.other_ltcg)


@app.post("/tools/52-week-range", tags=["14 Portfolio & Tax Tools"])
def tools_52_week_range(body: s.Range52WIn):
    return _wrap(calc.check_52_week_range, body.current, body.high, body.low)


# ---------------------------------------------------------------------------
# 15 ML price prediction (next-day close, scikit-learn)
# ---------------------------------------------------------------------------
@app.get("/ml/predict", tags=["15 ML Price Prediction"])
def ml_predict(symbol: str = Query(..., min_length=1),
               period: str = Query("2y", pattern="^(1y|2y|5y)$")):
    try:
        from . import predict
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"ML libraries unavailable on this server: {e}")
    return _market(predict.predict_next_close, symbol, period)


# ---------------------------------------------------------------------------
# 04 Income tax: old vs new regime
# ---------------------------------------------------------------------------
@app.post("/tax/income", tags=["04 Income Tax"])
def tax_income(body: s.IncomeTaxIn):
    return _wrap(planning.calc_income_tax, **body.model_dump())


# ---------------------------------------------------------------------------
# 05 Loan EMI calculator
# ---------------------------------------------------------------------------
@app.post("/loans/emi", tags=["05 Loan EMI"])
def loans_emi(body: s.LoanEmiIn):
    return _wrap(planning.calc_loan_emi, **body.model_dump())


# ---------------------------------------------------------------------------
# 03 Budget planner (50/30/20)
# ---------------------------------------------------------------------------
@app.post("/budget", tags=["03 Budget Planner"])
def budget(body: s.BudgetIn):
    return _wrap(planning.calc_budget, body.income, [i.model_dump() for i in body.items])


# ---------------------------------------------------------------------------
# 12 Mutual funds & SIP tracker (AMFI NAV data, no API key)
# ---------------------------------------------------------------------------
@app.get("/mf/search", tags=["12 Mutual Funds"])
def mf_search(q: str = Query(..., min_length=2), limit: int = Query(15, ge=1, le=50)):
    return {"query": q, "results": _market(mf.search_funds, q, limit)}


@app.get("/mf/nav", tags=["12 Mutual Funds"])
def mf_nav(code: int, years: int = Query(5, ge=0, le=40)):
    return _market(mf.fund_nav_chart, code, years)


@app.post("/mf/sip", tags=["12 Mutual Funds"])
def mf_sip(body: s.MfSipIn):
    try:
        return mf.sip_returns(body.code, body.monthly, body.start, body.end)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream data source failed: {e}")


# ---------------------------------------------------------------------------
# 11 Portfolio tracker (live prices)
# ---------------------------------------------------------------------------
@app.post("/tracker/value", tags=["11 Portfolio Tracker"])
def tracker_value(body: s.TrackerIn):
    return _wrap(tracker.value_holdings, [h.model_dump() for h in body.holdings])


# ---------------------------------------------------------------------------
# 07 Retirement & FIRE
# ---------------------------------------------------------------------------
@app.post("/goals/fire", tags=["07 Retirement & FIRE"])
def goals_fire(body: s.FireIn):
    return _wrap(planning.calc_fire, **body.model_dump())


# ---------------------------------------------------------------------------
# 09 Currency converter & stock comparison
# ---------------------------------------------------------------------------
@app.get("/market/currencies", tags=["09 Currency & Compare"])
def market_currencies():
    return {"currencies": market.CURRENCIES}


@app.get("/market/fx", tags=["09 Currency & Compare"])
def market_fx(base: str = Query("USD", pattern="^[A-Za-z]{3}$"), quote: str = Query("INR", pattern="^[A-Za-z]{3}$"),
              amount: float = 1, period: str = Query("3mo", pattern="^(1mo|3mo|6mo|1y|5y)$")):
    return _market(market.convert_currency, amount, base, quote, period)


@app.get("/market/compare", tags=["09 Currency & Compare"])
def market_compare(a: str = Query(..., min_length=1), b: str = Query(..., min_length=1),
                   period: str = Query("1y", pattern="^(1mo|3mo|6mo|1y|2y|5y)$")):
    return _market(analysis.compare_stocks, a, b, period)


# ---------------------------------------------------------------------------
# 25 Accounts, saved data and background price alerts
# ---------------------------------------------------------------------------
def _token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Please log in.")
    return authorization[7:].strip()


def current_user(authorization: str | None = Header(None)) -> dict:
    user = store.user_for_token(_token(authorization))
    if not user:
        raise HTTPException(status_code=401, detail="Your session has expired. Please log in again.")
    return user


def _auth(fn, *args):
    try:
        return fn(*args)
    except store.AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/register", tags=["25 Account"])
def auth_register(body: s.RegisterIn):
    return _auth(store.register, body.email, body.password, body.name)


@app.post("/auth/login", tags=["25 Account"])
def auth_login(body: s.LoginIn):
    return _auth(store.login, body.email, body.password)


@app.post("/auth/logout", tags=["25 Account"])
def auth_logout(authorization: str | None = Header(None)):
    store.logout(_token(authorization))
    return {"ok": True}


@app.get("/auth/me", tags=["25 Account"])
def auth_me(user: dict = Depends(current_user)):
    return {"user": user, "email_delivery": alerts.email_configured()}


@app.patch("/auth/me", tags=["25 Account"])
def auth_settings(body: s.SettingsIn, user: dict = Depends(current_user)):
    return {"user": store.update_settings(user["id"], body.name, body.email_alerts)}


@app.post("/auth/test-email", tags=["25 Account"])
def auth_test_email(user: dict = Depends(current_user)):
    """Send a test message so the user can check that alert emails arrive."""
    if not alerts.email_configured():
        raise HTTPException(status_code=503, detail="Email sending is not set up on this server yet.")
    try:
        alerts.send_email(user["email"], "FinSuite: test email",
                          f"Hi {user['name']},\n\nThis is a test from FinSuite. Price alert emails will arrive "
                          "at this address when an alert fires.\n\nFinSuite")
    except Exception as e:
        raise HTTPException(status_code=502, detail=alerts.explain_smtp_error(e))
    return {"ok": True, "to": user["email"]}


@app.get("/user/data", tags=["25 Account"])
def user_data(user: dict = Depends(current_user)):
    return store.get_data(user["id"])


@app.put("/user/data/{key}", tags=["25 Account"])
def user_data_put(key: str, body: s.DataIn, user: dict = Depends(current_user)):
    return _wrap(store.put_data, user["id"], key, body.value)


@app.get("/alerts", tags=["25 Account"])
def alerts_list(user: dict = Depends(current_user)):
    return {"alerts": store.list_alerts(user["id"]), "email_delivery": alerts.email_configured(),
            "check_every_seconds": alerts.ALERT_INTERVAL}


@app.post("/alerts", tags=["25 Account"])
def alerts_add(body: s.AlertIn, user: dict = Depends(current_user)):
    return _wrap(store.add_alert, user["id"], body.symbol, body.type, body.price)


@app.post("/alerts/seen", tags=["25 Account"])
def alerts_seen(user: dict = Depends(current_user)):
    store.mark_alerts_seen(user["id"])
    return {"ok": True}


@app.post("/alerts/check", tags=["25 Account"])
def alerts_check_mine(user: dict = Depends(current_user)):
    """Check this user's alerts right now (the page calls this on each refresh)."""
    result = alerts.check_alerts(user["id"])
    return {**result, "alerts": store.list_alerts(user["id"])}


@app.post("/alerts/run-check", tags=["25 Account"])
def alerts_run_check(authorization: str | None = Header(None)):
    """For a cron job on hosts without a background worker (e.g. Vercel Cron)."""
    secret = os.environ.get("CRON_SECRET")
    if not secret or _token(authorization) != secret:
        raise HTTPException(status_code=403, detail="Set CRON_SECRET and send it as a Bearer token.")
    return alerts.check_alerts()


@app.delete("/alerts/{alert_id}", tags=["25 Account"])
def alerts_delete(alert_id: int, user: dict = Depends(current_user)):
    store.delete_alert(user["id"], alert_id)
    return {"ok": True}


@app.post("/alerts/{alert_id}/rearm", tags=["25 Account"])
def alerts_rearm(alert_id: int, user: dict = Depends(current_user)):
    store.rearm_alert(user["id"], alert_id)
    return {"ok": True}


@app.get("/api/status", tags=["Meta"])
def api_status():
    return {"status": "ok", "docs": "/docs", "accounts_persistent": store.PERSISTENT,
            "email_delivery": alerts.email_configured()}


@app.get("/about", tags=["24 About"])
def about():
    tag_counts = {}
    for route in app.routes:
        for tag in getattr(route, "tags", []) or []:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    sections = [t for t in sorted(tag_counts) if t[:2].isdigit()]
    return {
        "name": app.title,
        "description": app.description,
        "version": app.version,
        "sections": sections,
        "endpoint_count": sum(tag_counts.values()),
        "about_text": (
            "FinSuite is a complete finance web application covering personal finance ratios, "
            "AI assisted analysis, loan and credit risk screening, portfolio and goal planning, "
            "live stock market data with technical indicators and news sentiment, a currency converter, "
            "a stock comparison chart, a mutual fund SIP tracker, a live portfolio tracker, an income tax "
            "calculator (old vs new regime), a loan EMI planner, a 50/30/20 budget planner, a retirement "
            "and FIRE planner, a saved watchlist with background price alerts, machine learning price "
            "forecasts for the next trading day, and a built in finance glossary, all in one console. "
            "Every calculator and data lookup on this site is powered by a documented backend service, "
            "and this page simply sends your inputs to it and shows the results."
        ),
        "why_it_matters": (
            "Most people make financial decisions, such as whether to buy a stock, whether they can afford "
            "a loan, or how much to save each month, without the tools professionals use to answer them. "
            "FinSuite closes that gap by putting real financial ratio calculations, risk scoring, and "
            "goal projections in one free and easy to use console. A student, a first time "
            "investor, or a small saver can run the same kind of analysis a bank or analyst would, "
            "understand exactly why a result came out the way it did (every tool explains its formula), "
            "and make a more informed decision instead of guessing or relying on someone else's tip."
        ),
        "developed_by": "Purva Gajanan Kakade",
        "guidance": "Prof. Ashish Singh, Professor, SJMSOM, IIT Bombay",
    }


app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", tags=["Meta"])
def root():
    # Stamp the JS/CSS URLs with their file-modified time so a browser can
    # never pair a fresh page with a stale cached script or stylesheet.
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    for name in ("app.js", "style.css"):
        version = int((FRONTEND_DIR / name).stat().st_mtime)
        html = html.replace(f"/static/{name}\"", f"/static/{name}?v={version}\"")
    return HTMLResponse(html, headers={"Cache-Control": "no-cache"})


if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    print(f"FinSuite running at http://127.0.0.1:{port}  (API docs: /docs) - press Ctrl+C to stop")
    uvicorn.run(app, host="127.0.0.1", port=port)
