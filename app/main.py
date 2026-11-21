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
    if os.environ.get("FINSUITE_NO_ENV_FILE") or not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(Path(__file__).resolve().parent.parent / ".env")

import re
from datetime import date

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response, StreamingResponse
from starlette.middleware.gzip import GZipMiddleware

from app import calculators as calc
from . import schemas as s
from . import market
from . import ai_assistant, analysis, alerts, limits, mf, planning, push, store, telegram, tracker, translate
from . import health as healthcheck
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

# Only FinSuite's own sites may call the API from a browser. Override with
# CORS_ORIGINS="https://a.example,https://b.example" (or "*" to allow all).
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get(
    "CORS_ORIGINS",
    "https://finsuite.co.in,https://www.finsuite.co.in,https://iitbfinsuite.vercel.app,"
    "http://localhost:8000,http://127.0.0.1:8000").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["*"], allow_headers=["*"])


class SelectiveGZip:
    """Compress responses, except the AI chat stream, which must reach the browser piece by piece."""
    def __init__(self, inner):
        self.inner, self.gzip = inner, GZipMiddleware(inner, minimum_size=800)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].startswith("/assistant/ai-chat"):
            return await self.inner(scope, receive, send)
        return await self.gzip(scope, receive, send)


app.add_middleware(SelectiveGZip)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.middleware("http")
async def limits_and_caching(request, call_next):
    path = request.url.path
    is_static = path.startswith("/static/") or path == "/"
    if not is_static and path not in ("/api/health", "/api/status"):
        ok, retry = limits.check("all", limits.client_ip(request), limits.GENERAL_PER_MIN, 60)
        if not ok:
            return JSONResponse({"detail": f"Too many requests. Please wait {retry} seconds."}, status_code=429,
                                headers={"Retry-After": str(retry)})
    response = await call_next(request)
    if path.startswith("/static/") and "v" in request.query_params:
        # The page stamps every file with its modified time (?v=...), so a changed file has a new URL.
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif is_static:
        response.headers["Cache-Control"] = "no-cache"      # re-check on every load (cheap 304)
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


@app.get("/assistant/ai-status", tags=["02 AI Finance Assistant"])
def assistant_ai_status():
    return {"enabled": ai_assistant.enabled(), "model": ai_assistant.MODEL if ai_assistant.enabled() else None}


@app.post("/assistant/ai-chat", tags=["02 AI Finance Assistant"])
def assistant_ai_chat(body: s.AiChatIn, request: Request, authorization: str | None = Header(None)):
    """Conversational AI assistant that can use FinSuite's calculators and live data.
    Streams newline-delimited JSON events (see app/ai_assistant.py)."""
    msgs = [m.model_dump() for m in body.messages]
    if msgs[0]["role"] != "user" or msgs[-1]["role"] != "user":
        raise HTTPException(status_code=422, detail="The conversation must start and end with a user message.")
    if sum(len(m["content"]) for m in msgs) > 40000:
        raise HTTPException(status_code=413, detail="This conversation is too long. Start a new chat.")
    if ai_assistant.enabled():       # every AI answer costs money, so cap use per minute, person and day
        limits.enforce_ip(request, "ai", limits.AI_PER_MIN, 60,
                          "You are asking very quickly. Please wait a few seconds and try again.")
        today, user = date.today().isoformat(), optional_user(authorization)
        who, cap = ((f"u{user['id']}", limits.AI_PER_USER_DAILY) if user
                    else (f"ip{limits.client_ip(request)}", limits.AI_PER_IP_DAILY))
        if limits.ENABLED:
            ok, _ = store.counter_add(f"ai:{today}:{who}", cap, today)
            if not ok:
                raise HTTPException(status_code=429, detail=f"You have reached today's limit of {cap} AI questions."
                                    + ("" if user else " Log in for a higher limit, or try again tomorrow."))
            ok, _ = store.counter_add(f"ai:{today}:all", limits.AI_DAILY_LIMIT, today)
            if not ok:
                raise HTTPException(status_code=429, detail="The AI assistant has reached its limit for today. Please try again tomorrow.")
    return StreamingResponse(ai_assistant.chat_stream(msgs, body.context, body.language),
                             media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

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
def knowledge_glossary(lang: str = Query("en", pattern="^(en|hi|mr)$")):
    """The glossary in English, or in Hindi / Marathi (translated once by the AI model and cached)."""
    if lang == "en":
        return {"glossary": GLOSSARY, "lang": "en"}
    return translate.glossary(lang)


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
def ml_predict(request: Request, symbol: str = Query(..., min_length=1),
               period: str = Query("2y", pattern="^(1y|2y|5y)$")):
    limits.enforce_ip(request, "ml", limits.ML_PER_MIN, 60,
                      "Training the price models takes a lot of computing. Please wait a minute and try again.")
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


def optional_user(authorization: str | None) -> dict | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return store.user_for_token(authorization[7:].strip())


def _public_url(request: Request) -> str:
    return (os.environ.get("PUBLIC_URL") or str(request.base_url)).rstrip("/")


def _send_mail_later(background: BackgroundTasks, to: str, subject: str, body: str) -> None:
    def job():
        try:
            alerts.send_email(to, subject, body)
        except Exception as e:                      # a failed email must never break the request
            alerts.log.warning("email to %s failed: %s", to, e)
    background.add_task(job)


def _verification_mail(background: BackgroundTasks, request: Request, user: dict) -> None:
    token = store.create_token(user["id"], "verify", 3 * 24 * 3600)
    _send_mail_later(background, user["email"], "Confirm your FinSuite email",
                     f"Hi {user['name']},\n\nConfirm your email address so FinSuite can send you price alerts and "
                     f"password resets:\n\n{_public_url(request)}/auth/verify?token={token}\n\n"
                     "The link works for 3 days. If you did not create a FinSuite account, ignore this message.\n\nFinSuite")


def _auth(fn, *args):
    try:
        return fn(*args)
    except store.AuthError as e:    
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/register", tags=["25 Account"])
def auth_register(body: s.RegisterIn, request: Request, background: BackgroundTasks):
    limits.enforce_ip(request, "register", limits.REGISTER_PER_HOUR, 3600,
                      "Too many accounts were created from this connection. Please try again later.")
    result = _auth(store.register, body.email, body.password, body.name)
    if alerts.email_configured():
        _verification_mail(background, request, result["user"])
    return result


@app.post("/auth/login", tags=["25 Account"])
def auth_login(body: s.LoginIn, request: Request):
    limits.enforce_ip(request, "login", limits.LOGIN_PER_MIN, 60, "Too many login attempts. Please wait a minute.")
    limits.enforce("login-email", body.email.strip().lower(), limits.LOGIN_PER_EMAIL, 900,
                   "Too many login attempts for this account. Please wait 15 minutes, or reset your password.")
    return _auth(store.login, body.email, body.password)


@app.post("/auth/forgot", tags=["25 Account"])
def auth_forgot(body: s.ForgotIn, request: Request, background: BackgroundTasks):
    """Email a password reset link. The answer is the same whether or not the address has an account."""
    if not alerts.email_configured():
        raise HTTPException(status_code=503, detail="Password reset by email is not set up on this server yet.")
    email = body.email.strip().lower()
    limits.enforce_ip(request, "forgot", limits.EMAIL_SEND_PER_HOUR, 3600)
    limits.enforce("forgot-email", email, limits.EMAIL_SEND_PER_HOUR, 3600)
    user = store.get_user_by_email(email)
    if user:
        token = store.create_token(user["id"], "reset", 30 * 60)
        _send_mail_later(background, email, "Reset your FinSuite password",
                         f"Hi {user['name']},\n\nSomeone asked to reset the password of your FinSuite account. "
                         f"Open this link within 30 minutes to choose a new one:\n\n{_public_url(request)}/#reset={token}\n\n"
                         "If it was not you, ignore this message; your password stays the same.\n\nFinSuite")
    return {"ok": True, "message": "If an account exists for that email, a reset link is on its way."}


@app.post("/auth/reset", tags=["25 Account"])
def auth_reset(body: s.ResetIn, request: Request):
    limits.enforce_ip(request, "reset", limits.LOGIN_PER_MIN, 60)
    user_id = store.consume_token(body.token, "reset")
    if not user_id:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired. Ask for a new one.")
    _auth(store.set_password, user_id, body.password)
    store.mark_verified(user_id)               # the link reached their inbox
    return store.start_session(user_id)


@app.post("/auth/verify/send", tags=["25 Account"])
def auth_verify_send(request: Request, background: BackgroundTasks, user: dict = Depends(current_user)):
    if not alerts.email_configured():
        raise HTTPException(status_code=503, detail="Email sending is not set up on this server yet.")
    limits.enforce("verify-email", user["email"], limits.EMAIL_SEND_PER_HOUR, 3600)
    _verification_mail(background, request, user)
    return {"ok": True}


@app.get("/auth/verify", tags=["25 Account"])
def auth_verify(token: str):
    user_id = store.consume_token(token, "verify")
    if user_id:
        store.mark_verified(user_id)
    return RedirectResponse(url="/#verified" if user_id else "/#verify-failed")


@app.post("/auth/logout", tags=["25 Account"])
def auth_logout(authorization: str | None = Header(None)):
    store.logout(_token(authorization))
    return {"ok": True}


@app.get("/auth/me", tags=["25 Account"])
def auth_me(user: dict = Depends(current_user)):
    return {"user": user, "email_delivery": alerts.email_configured(),
            "push_available": push.available(), "telegram_available": telegram.enabled()}


@app.get("/push/key", tags=["25 Account"])
def push_key():
    """Public key a browser needs to subscribe to push notifications."""
    if not push.available():
        return {"enabled": False}
    return {"enabled": True, "publicKey": push.public_key()}


@app.post("/push/subscribe", tags=["25 Account"])
def push_subscribe(body: s.PushSubIn, user: dict = Depends(current_user)):
    if not push.available():
        raise HTTPException(status_code=503, detail="Push notifications are not available on this server.")
    store.add_push_sub(user["id"], body.endpoint, body.keys.p256dh, body.keys.auth)
    return {"ok": True}


@app.post("/push/unsubscribe", tags=["25 Account"])
def push_unsubscribe(body: s.PushUnsubIn, user: dict = Depends(current_user)):
    store.remove_push_sub(body.endpoint, user["id"])
    return {"ok": True}


@app.post("/auth/telegram/link", tags=["25 Account"])
def telegram_link(user: dict = Depends(current_user)):
    """A one-time link that connects this account to a Telegram chat with the FinSuite bot."""
    if not telegram.enabled():
        raise HTTPException(status_code=503, detail="Telegram alerts are not set up on this server yet.")
    limits.enforce("telegram-link", str(user["id"]), 5, 3600)
    try:
        return telegram.new_link_code(user["id"])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not reach Telegram: {e}")


@app.delete("/auth/telegram", tags=["25 Account"])
def telegram_unlink(user: dict = Depends(current_user)):
    store.set_telegram(user["id"], None)
    return {"ok": True}


@app.delete("/auth/me", tags=["25 Account"])
def auth_delete(user: dict = Depends(current_user)):
    """Delete the account and everything saved with it."""
    store.delete_user(user["id"])
    return {"ok": True}


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


@app.get("/api/health", tags=["Meta"])
def api_health(deep: bool = False):
    """For uptime monitors (deep=false) and the Data Sources page (deep=true: also tests the data sources)."""
    result = healthcheck.report(deep)
    return JSONResponse(result, status_code=200 if result["status"] != "down" else 503)


@app.get("/api/status", tags=["Meta"])
def api_status():
    return {"status": "ok", "docs": "/docs", "accounts_persistent": store.PERSISTENT,
            "email_delivery": alerts.email_configured(), "push_available": push.available(),
            "telegram_available": telegram.enabled(), "ai_assistant": ai_assistant.enabled()}


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


def _build_stamp() -> int:
    return max((int(f.stat().st_mtime) for f in FRONTEND_DIR.rglob("*") if f.is_file()), default=0)


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    """The service worker must be served from the site root so it can control every page.
    The build stamp changes whenever any front-end file does, which makes browsers update it."""
    text = (FRONTEND_DIR / "sw.js").read_text(encoding="utf-8").replace("__BUILD__", str(_build_stamp()))
    return Response(text, media_type="application/javascript",
                    headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})


@app.get("/manifest.webmanifest", include_in_schema=False)
def web_manifest():
    return FileResponse(FRONTEND_DIR / "manifest.webmanifest", media_type="application/manifest+json",
                        headers={"Cache-Control": "no-cache"})


@app.get("/", tags=["Meta"])
def root():
    # Stamp the JS/CSS URLs with their file-modified time so a browser can
    # never pair a fresh page with a stale cached script or stylesheet.
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")

    def stamp(match):
        name = match.group(2)
        file = FRONTEND_DIR / name
        return f'{match.group(1)}/static/{name}?v={int(file.stat().st_mtime)}"' if file.is_file() else match.group(0)
    html = re.sub(r'((?:src|href)=")/static/([\w./-]+)"', stamp, html)
    return HTMLResponse(html, headers={"Cache-Control": "no-cache"})


if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    print(f"FinSuite running at http://127.0.0.1:{port}  (API docs: /docs) - press Ctrl+C to stop")
    uvicorn.run(app, host="127.0.0.1", port=port)
