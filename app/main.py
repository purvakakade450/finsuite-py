from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app import calculators as calc
from . import schemas as s
from . import market
from .glossary import GLOSSARY

app = FastAPI(
    title="FinSuite API",
    description="Python port of the FinSuite finance-suite calculators.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def _wrap(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ---------------------------------------------------------------------------
# 01 Ratio calculators
# ---------------------------------------------------------------------------
@app.post("/ratios/roe", tags=["01 Ratios"])
def roe(body: s.ROEIn):
    return {"roe_pct": _wrap(calc.calc_roe, body.net_income, body.equity)}


@app.post("/ratios/roa", tags=["01 Ratios"])
def roa(body: s.ROAIn):
    return {"roa_pct": _wrap(calc.calc_roa, body.net_income, body.assets)}


@app.post("/ratios/debt-ratio", tags=["01 Ratios"])
def debt_ratio(body: s.DebtRatioIn):
    return {"debt_ratio": _wrap(calc.calc_debt_ratio, body.liabilities, body.assets)}


@app.post("/ratios/health", tags=["01 Ratios"])
def health(body: s.HealthIn):
    return {"health": calc.calc_health(body.roe)}


# ---------------------------------------------------------------------------
# 02 Personal finance report
# ---------------------------------------------------------------------------
@app.post("/report", tags=["02 Personal Finance Report"])
def report(body: s.ReportIn):
    return _wrap(calc.calc_report, body.income, body.expenses, body.savings, body.debt, body.equity)


# ---------------------------------------------------------------------------
# 03 AI Finance Assistant
# ---------------------------------------------------------------------------
@app.post("/assistant/snapshot", tags=["03 AI Finance Assistant"])
def assistant_snapshot(body: s.AssistantIn):
    return _wrap(calc.calc_assistant, body.income, body.expenses, body.savings, body.borrowed, body.owned)


@app.post("/assistant/chat", tags=["03 AI Finance Assistant"])
def assistant_chat(body: s.ChatIn):
    return {"answer": calc.chat_reply(body.question)}


# ---------------------------------------------------------------------------
# 04 Loan insight generator
# ---------------------------------------------------------------------------
@app.post("/loans/screen", tags=["04 Loan Insight Generator"])
def loans_screen(body: s.LoanScreenIn):
    rows = [r.model_dump() for r in body.rows]
    return {"rows": calc.screen_loans(rows)}


# ---------------------------------------------------------------------------
# 05 Credit score & risk dashboard
# ---------------------------------------------------------------------------
@app.post("/credit-score", tags=["05 Credit Score & Risk"])
def credit_score(body: s.CreditScoreIn):
    return _wrap(calc.calc_credit_score, body.score)


@app.post("/risk", tags=["05 Credit Score & Risk"])
def risk(body: s.RiskIn):
    return calc.calc_risk(body.score, body.income, body.emi, body.name)


# ---------------------------------------------------------------------------
# 06 Investment recommendation
# ---------------------------------------------------------------------------
@app.post("/invest", tags=["06 Investment Recommendation"])
def invest(body: s.InvestIn):
    return calc.calc_invest(body.revenue_growth, body.profit_margin, body.roa, body.roe)


# ---------------------------------------------------------------------------
# 07 Company performance
# ---------------------------------------------------------------------------
@app.post("/company-performance", tags=["07 Company Performance"])
def company_performance(body: s.CompanyPerfIn):
    return calc.analyze_company(body.name, body.revenue_growth, body.csat, body.retention)


# ---------------------------------------------------------------------------
# 08 Portfolio dashboard
# ---------------------------------------------------------------------------
@app.post("/portfolio", tags=["08 Portfolio Dashboard"])
def portfolio(body: s.PortfolioIn):
    rows = [c.model_dump() for c in body.companies]
    results = [calc.compute_company_metrics(r) for r in rows]
    results.sort(key=lambda r: r["score"], reverse=True)
    return {"companies": results}


# ---------------------------------------------------------------------------
# 09 Goal & retirement planner
# ---------------------------------------------------------------------------
@app.post("/goals/plan", tags=["09 Goal & Retirement Planner"])
def goals_plan(body: s.GoalPlanIn):
    return _wrap(calc.calc_goal_plan, body.target, body.years, body.ret, body.inflation,
                 body.current, body.income, body.name)


@app.post("/goals/emergency-fund", tags=["09 Goal & Retirement Planner"])
def goals_emergency_fund(body: s.EmergencyFundIn):
    return _wrap(calc.calc_emergency_fund, body.expenses, body.savings)


# ---------------------------------------------------------------------------
# 10 Knowledge center
# ---------------------------------------------------------------------------
@app.get("/knowledge/glossary", tags=["10 Knowledge Center"])
def knowledge_glossary():
    return {"glossary": GLOSSARY}


# ---------------------------------------------------------------------------
# 11 Stock market workspace — live data, no API key required (



@app.post("/planner/target-plan", tags=["12 Growth & Target Planner"])
def planner_target_plan(body: s.TargetPlanIn):
    return _wrap(calc.calc_target_plan, body.entry, body.qty, body.target_pct, body.stop_pct)


# ---------------------------------------------------------------------------
# 13 Portfolio & tax tools
# ---------------------------------------------------------------------------
@app.post("/tools/sip-vs-lumpsum", tags=["13 Portfolio & Tax Tools"])
def tools_sip_vs_lumpsum(body: s.SipVsLumpIn):
    return _wrap(calc.compare_sip_lump_sum, body.total, body.months, body.start_price,
                 body.prices_by_month, body.last_price)


@app.post("/tools/capital-gains-tax", tags=["13 Portfolio & Tax Tools"])
def tools_capital_gains_tax(body: s.CapitalGainsTaxIn):
    return _wrap(calc.estimate_capital_gains_tax, body.buy_price, body.sell_price, body.qty,
                 body.buy_date, body.sell_date, body.other_ltcg)


@app.post("/tools/52-week-range", tags=["13 Portfolio & Tax Tools"])
def tools_52_week_range(body: s.Range52WIn):
    return _wrap(calc.check_52_week_range, body.current, body.high, body.low)


# ---------------------------------------------------------------------------
# 15 API key directory (mirrors the web app's reference page)
# ---------------------------------------------------------------------------
@app.get("/api-keys", tags=["15 API Key Directory"])
def api_keys():
    return {
        "keys": [],
        "note": (
            "No external API keys are required. Live quotes and daily OHLCV history "
            "come from yfinance (public Yahoo Finance data, no signup), and news "
            "headlines come from Google News' public RSS feed. Both are free and "
            "keyless — nothing to paste in here."
        ),
    }


@app.get("/api/status", tags=["Meta"])
def api_status():
    return {"status": "ok", "docs": "/docs"}


app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", tags=["Meta"])
def root():
    return FileResponse(str(FRONTEND_DIR / "index.html"))
