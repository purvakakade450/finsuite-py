"""
AI finance assistant: a chat model (Claude, via the Anthropic API) that can
call FinSuite's own calculators and live-data functions as tools, so answers
use real numbers instead of guesses.

Needs ANTHROPIC_API_KEY (in .env locally, or the host's environment
variables). Without it the chat falls back to the Knowledge Center lookup.

The reply is streamed to the browser as newline-delimited JSON events:
    {"type": "text", "text": "..."}     a piece of the answer
    {"type": "tool", "label": "..."}    the assistant is using a tool
    {"type": "error", "message": "..."}
    {"type": "done"}
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date
from typing import Iterator, Optional

from pydantic import BaseModel, Field, ValidationError

from . import analysis, calculators, market, mf, planning, tracker

log = logging.getLogger("finsuite.ai")

MODEL = os.environ.get("FINSUITE_AI_MODEL", "claude-opus-5-5")
MAX_TOOL_ROUNDS = 8
MAX_HISTORY = 24          # earlier messages sent back with each question

SYSTEM_PROMPT = """You are the FinSuite AI assistant, built into FinSuite, a finance web app made for Indian users (students, first-time investors, small savers) by Purva Gajanan Kakade under the guidance of Prof. Ashish Singh, SJMSOM, IIT Bombay.

How to help:
- Answer finance questions clearly, in plain language a beginner understands. Explain jargon the first time you use it.
- Prefer real numbers: when a question involves a stock, index, fund, currency, tax, loan, goal, budget or portfolio, call the matching tool rather than estimating. Use several tools if that helps (for example quote + indicators + news for "should I look at TCS?").
- Indian context by default: rupees (₹) with Indian digit grouping (₹1,50,000), lakh and crore, NSE tickers ending in .NS, Indian tax rules for FY 2025-26. If the user clearly means another market, follow them.
- Show the key figures, then a short explanation of what they mean for the user. Use short paragraphs, bullet points, and small markdown tables when comparing options. Keep answers focused; don't pad.
- If a needed detail is missing (income, loan tenure and so on), make a sensible stated assumption and invite the user to correct it, or ask one short question when an assumption would be misleading.
- Mention the relevant FinSuite tab when it lets the user explore further (for example "Open 04 Income Tax to change the deductions").
- You are educational, not a licensed adviser. Never tell someone to buy or sell a specific security as a recommendation; you can explain what the data shows, the risks, and what to consider. Remind users of this only when they ask for buy/sell calls or predictions, briefly.
- Market data comes from Yahoo Finance and can be delayed; news sentiment is a simple word count, and ML forecasts are rough. Say so when it matters.
- Stay on finance, economics and using FinSuite. Politely decline unrelated tasks."""


# ---------------------------------------------------------------------------
# Tool inputs (validated before anything runs)
# ---------------------------------------------------------------------------
class SymbolIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)


class IndicatorsIn(SymbolIn):
    period: str = Field("6mo", pattern="^(1mo|3mo|6mo|1y|2y|5y)$")


class CompareIn(BaseModel):
    symbol_a: str = Field(min_length=1, max_length=40)
    symbol_b: str = Field(min_length=1, max_length=40)
    period: str = Field("1y", pattern="^(1mo|3mo|6mo|1y|2y|5y)$")


class QueryIn(BaseModel):
    query: str = Field(min_length=1, max_length=120)


class NewsIn(BaseModel):
    query: str = Field("", max_length=120)


class FxIn(BaseModel):
    amount: float = 1
    from_currency: str = Field(pattern="^[A-Za-z]{3}$")
    to_currency: str = Field(pattern="^[A-Za-z]{3}$")


class TaxIn(BaseModel):
    gross_income: float = Field(ge=0)
    salaried: bool = True
    age_group: str = Field("below60", pattern="^(below60|60to79|80plus)$")
    sec80c: float = 0
    sec80d: float = 0
    nps_80ccd1b: float = 0
    home_loan_interest: float = 0
    hra_exemption: float = 0
    other_deductions: float = 0


class EmiIn(BaseModel):
    principal: float
    annual_rate: float
    tenure_months: int
    prepay_amount: float = 0
    prepay_month: int = 0
    extra_monthly: float = 0


class GoalIn(BaseModel):
    target: float
    years: float
    expected_return: float = 12
    inflation: float = 6
    current_savings: float = 0
    monthly_income: Optional[float] = None


class FireIn(BaseModel):
    current_age: float
    retire_age: float
    life_expectancy: float = 85
    monthly_expenses: float
    inflation: float = 6
    return_pre: float = 12
    return_post: float = 8
    current_corpus: float = 0
    monthly_investment: float = 0
    withdrawal_rate: float = 4


class BudgetItemIn(BaseModel):
    category: str
    amount: float
    kind: str = Field(pattern="^(need|want|saving)$")


class BudgetIn(BaseModel):
    income: float
    items: list[BudgetItemIn]


class FundSipIn(BaseModel):
    scheme_code: int
    monthly: float
    start_date: date


class HoldingIn(BaseModel):
    symbol: str
    qty: float = Field(gt=0)
    avg_price: float = Field(ge=0)


class PortfolioIn(BaseModel):
    holdings: list[HoldingIn] = Field(min_length=1, max_length=50)


class TermIn(BaseModel):
    term: str = Field(min_length=1, max_length=80)


# ---------------------------------------------------------------------------
# Tool implementations: call FinSuite functions, return compact JSON
# ---------------------------------------------------------------------------
def _r(x, d=2):
    return None if x is None else round(float(x), d)


def _quote(a: SymbolIn):
    q = market.get_quote(a.symbol)
    return {k: q.get(k) for k in ("name", "yahooSymbol", "price", "change", "changePercent", "previousClose",
                                  "open", "dayHigh", "dayLow", "volume", "currency", "asOf")}


def _indicators(a: IndicatorsIn):
    d = analysis.get_indicators(a.symbol, a.period)
    last = lambda k: next((v for v in reversed(d[k]) if v is not None), None)
    closes = [c for c in d["close"] if c is not None]
    return {"name": d["name"], "symbol": d["yahooSymbol"], "currency": d["currency"], "period": a.period,
            "latest_close": last("close"), "sma20": last("sma20"), "sma50": last("sma50"), "ema20": last("ema20"),
            "bollinger_upper": last("bb_upper"), "bollinger_lower": last("bb_lower"), "rsi14": last("rsi14"),
            "period_return_pct": _r((closes[-1] / closes[0] - 1) * 100) if len(closes) > 1 else None,
            "period_high": max(closes) if closes else None, "period_low": min(closes) if closes else None,
            "signals": d["signals"]}


def _compare(a: CompareIn):
    d = analysis.compare_stocks(a.symbol_a, a.symbol_b, a.period)
    strip = lambda s: {k: v for k, v in s.items() if k not in ("rebased", "close")}
    return {"period": a.period, "a": strip(d["a"]), "b": strip(d["b"]), "correlation": d["correlation"],
            "trading_days": len(d["dates"]), "summary": d["summary"]}


def _news(a: NewsIn):
    d = analysis.news_with_sentiment(a.query, 8)
    return {"summary": d["summary"],
            "headlines": [{"title": n["title"], "source": n["source"], "published_at": n["published_at"][:16],
                           "sentiment": n["sentiment"]["label"]} for n in d["data"]]}


def _search(a: QueryIn):
    return market.search_symbols(a.query, 6)


def _fx(a: FxIn):
    r = market.get_fx_rate(a.from_currency, a.to_currency)
    return {**r, "amount": a.amount, "converted": _r(a.amount * r["rate"], 4)}


def _tax(a: TaxIn):
    r = planning.calc_income_tax(**a.model_dump())
    keep = ("gross_income", "standard_deduction", "deductions", "taxable_income", "tax_on_slabs", "rebate",
            "surcharge", "cess", "total_tax", "effective_rate", "monthly_take_home")
    return {"new_regime": {k: _r(r["new"][k]) for k in keep}, "old_regime": {k: _r(r["old"][k]) for k in keep},
            "better": r["better"], "savings": _r(r["savings"]), "break_even_deductions": _r(r["break_even_deductions"]),
            "deductions_allowed": r["deductions_allowed"], "insight": r["insight"]}


def _emi(a: EmiIn):
    r = planning.calc_loan_emi(**a.model_dump())
    out = {"emi": _r(r["emi"]), "total_interest": _r(r["total_interest"]), "total_payment": _r(r["total_payment"]),
           "months": r["months"], "first_year": {k: _r(v) for k, v in r["yearly"][0].items()}, "insight": r["insight"]}
    if r["prepayment"]:
        p = r["prepayment"]
        out["with_prepayment"] = {"months": p["months"], "total_interest": _r(p["total_interest"]),
                                  "interest_saved": _r(p["interest_saved"]), "months_saved": p["months_saved"]}
    return out


def _goal(a: GoalIn):
    r = calculators.calc_goal_plan(a.target, a.years, a.expected_return, a.inflation, a.current_savings,
                                   a.monthly_income, "Your goal")
    return {k: (_r(v) if isinstance(v, float) else v) for k, v in r.items() if k != "schedule"}


def _fire(a: FireIn):
    r = planning.calc_fire(**a.model_dump())
    return {k: (_r(v) if isinstance(v, float) else v) for k, v in r.items() if k != "schedule"}


def _budget(a: BudgetIn):
    return planning.calc_budget(a.income, [i.model_dump() for i in a.items])


def _fund_search(a: QueryIn):
    return [{k: f[k] for k in ("code", "name", "nav", "date", "category")} for f in mf.search_funds(a.query, 8)]


def _fund_sip(a: FundSipIn):
    r = mf.sip_returns(a.scheme_code, a.monthly, a.start_date)
    return {k: (_r(v) if isinstance(v, float) else v) for k, v in r.items() if k != "series"}


def _portfolio(a: PortfolioIn):
    r = tracker.value_holdings([h.model_dump() for h in a.holdings])
    cols = ("symbol", "name", "qty", "avg_price", "price", "currency", "pnl", "pnl_pct", "weight_pct", "error")
    return {"rows": [{k: (_r(x.get(k)) if isinstance(x.get(k), float) else x.get(k)) for k in cols} for x in r["rows"]],
            **{k: _r(r[k]) for k in ("invested", "value", "pnl", "pnl_pct", "day_change")}, "currency": r["base"],
            "insight": r["insight"]}


def _predict(a: SymbolIn):
    from . import predict
    d = predict.predict_next_close(a.symbol, "2y")
    return {"name": d["name"], "symbol": d["yahooSymbol"], "currency": d["currency"], "forecast": d["forecast"],
            "best_model": d["best_model"], "beats_naive_baseline": d["beats_baseline"],
            "test_error": {k: {"mae": v["mae"], "mape_pct": v["mape"]} for k, v in d["metrics"].items()}}


def _term(a: TermIn):
    return {"answer": calculators.chat_reply(a.term)}


def _schema(model: type[BaseModel]) -> dict:
    """JSON schema for a tool's input, with nested models inlined and titles dropped."""
    s = model.model_json_schema()
    defs = s.pop("$defs", {})

    def clean(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return clean(defs[node["$ref"].split("/")[-1]])
            return {k: clean(v) for k, v in node.items() if k != "title"}
        if isinstance(node, list):
            return [clean(v) for v in node]
        return node
    return clean(s)


TOOLS = {
    # name: (description, input model, function, label shown in the chat while it runs)
    "get_stock_quote": ("Live price snapshot of a stock, index or ETF: price, day change, day range, volume. "
                        "Accepts tickers (TCS.NS, AAPL, ^NSEI) or company names.", SymbolIn, _quote, "Fetching the live price"),
    "get_technical_indicators": ("Moving averages (SMA20/50, EMA20), Bollinger bands, 14-day RSI, period return and "
                                 "plain-language signals for a stock.", IndicatorsIn, _indicators, "Reading the chart indicators"),
    "compare_two_stocks": ("Compare two stocks over a period: return, volatility, max drawdown, best/worst day, "
                           "correlation.", CompareIn, _compare, "Comparing the two stocks"),
    "get_news_sentiment": ("Latest headlines (last 7 days) with a positive/neutral/negative label each and an overall mood. "
                           "query = a ticker like RELIANCE.NS, a topic, or empty for general Indian market news.",
                           NewsIn, _news, "Reading the latest news"),
    "search_company": ("Find tickers for a company name across NSE, BSE, US and other markets.", QueryIn, _search,
                       "Looking up the company"),
    "convert_currency": ("Live exchange rate and conversion between two currencies (ISO codes like USD, INR, EUR).",
                         FxIn, _fx, "Checking the exchange rate"),
    "calculate_income_tax": ("Indian income tax for FY 2025-26 under both the new and old regimes, with which saves more. "
                             "gross_income is yearly. age_group: below60, 60to79 or 80plus. Deductions apply to the old "
                             "regime only.", TaxIn, _tax, "Working out income tax"),
    "calculate_loan_emi": ("Loan EMI, total interest and the effect of prepayments (one-time amount in a given month and/or "
                           "extra every month). annual_rate in %.", EmiIn, _emi, "Calculating the EMI"),
    "plan_goal": ("Monthly SIP needed to reach a goal amount (in today's money) after some years, with inflation.",
                  GoalIn, _goal, "Planning the goal"),
    "plan_retirement": ("Retirement / FIRE plan: corpus needed, FIRE number, required monthly SIP, financial "
                        "independence age, and whether the money lasts.", FireIn, _fire, "Planning retirement"),
    "analyse_budget": ("Check monthly spending against the 50/30/20 rule. kind is need, want or saving.", BudgetIn, _budget,
                       "Analysing the budget"),
    "search_mutual_funds": ("Search Indian mutual fund schemes (AMFI data) by name; returns scheme codes and latest NAV.",
                            QueryIn, _fund_search, "Searching mutual funds"),
    "mutual_fund_sip_returns": ("What a monthly SIP in a mutual fund scheme would be worth today, with XIRR and 1/3/5-year "
                                "fund returns. Get scheme_code from search_mutual_funds first.", FundSipIn, _fund_sip,
                                "Calculating SIP returns"),
    "value_portfolio": ("Value stock holdings at live prices with profit/loss and weights (totals in INR).",
                        PortfolioIn, _portfolio, "Valuing the portfolio"),
    "predict_next_day_price": ("Machine-learning forecast of the next trading day's close (Linear Regression and Random "
                               "Forest on 2 years of prices), with test errors vs a naive baseline. Slow (up to a minute).",
                               SymbolIn, _predict, "Training the price model"),
    "lookup_finance_term": ("FinSuite Knowledge Center definition of a finance term, with an example.", TermIn, _term,
                            "Checking the Knowledge Center"),
}

TOOL_DEFS = [{"name": name, "description": desc, "input_schema": _schema(model), "eager_input_streaming": True}
             for name, (desc, model, _fn, _label) in TOOLS.items()]


def run_tool(name: str, args) -> tuple[str, bool]:
    """Validate the model's arguments, run the tool, return (json text, is_error)."""
    if name not in TOOLS:
        return json.dumps({"error": f"unknown tool {name}"}), True
    _desc, model, fn, _label = TOOLS[name]
    try:
        parsed = model.model_validate(args if isinstance(args, dict) else {})
    except ValidationError as e:
        return json.dumps({"INVALID_INPUT": e.errors(include_url=False, include_context=False)}, default=str), True
    try:
        return json.dumps(fn(parsed), default=str), False
    except ValueError as e:
        return json.dumps({"error": str(e)}), True
    except Exception as e:  # upstream data source down etc. - let the model explain it
        log.warning("tool %s failed: %s", name, e)
        return json.dumps({"error": f"data source failed: {e}"}), True


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
def enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _event(**kw) -> str:
    return json.dumps(kw) + "\n"


def _context_note(context: dict | None) -> str | None:
    if not context:
        return None
    parts = [f"Today is {date.today():%d %B %Y}."]
    if context.get("watchlist"):
        parts.append("User's watchlist: " + ", ".join(map(str, context["watchlist"][:30])) + ".")
    if context.get("portfolio"):
        rows = [f"{h.get('symbol')} x{h.get('qty')} @ {h.get('avg_price')}" for h in context["portfolio"][:30]]
        parts.append("User's saved holdings (symbol x qty @ average buy price): " + "; ".join(rows) + ".")
    if context.get("tab"):
        parts.append(f"The user is on the FinSuite tab: {context['tab']}.")
    return " ".join(parts)


def chat_stream(history: list[dict], context: dict | None = None) -> Iterator[str]:
    """Stream the assistant's reply to the last user message in `history`."""
    if not enabled():
        question = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
        yield _event(type="notice", message="AI mode is off on this server (no API key), so this is a Knowledge Center answer.")
        yield _event(type="text", text=calculators.chat_reply(question))
        yield _event(type="done")
        return

    import anthropic

    client = anthropic.Anthropic()
    messages: list[dict] = [{"role": m["role"], "content": m["content"]} for m in history[-MAX_HISTORY:]]
    note = _context_note(context)
    if note:
        # Operator-side facts about this user, after their latest message.
        messages.append({"role": "system", "content": note})

    try:
        for _round in range(MAX_TOOL_ROUNDS):
            try:
                with client.beta.messages.stream(
                    model=MODEL,
                    max_tokens=64000,
                    system=SYSTEM_PROMPT,
                    tools=TOOL_DEFS,
                    messages=messages,
                    output_config={"effort": "medium"},
                    cache_control={"type": "ephemeral"},
                    betas=["server-side-fallback-2026-07-01"],
                    fallbacks="default",
                ) as stream:
                    for ev in stream:
                        if ev.type == "content_block_delta" and ev.delta.type == "text_delta":
                            yield _event(type="text", text=ev.delta.text)
                        elif ev.type == "content_block_start" and ev.content_block.type == "tool_use":
                            label = TOOLS.get(ev.content_block.name, ("", None, None, "Working"))[3]
                            yield _event(type="tool", name=ev.content_block.name, label=label)
                    response = stream.get_final_message()
            except ValueError:
                # Tool input JSON the SDK could not parse at all: ask again.
                continue

            if response.stop_reason == "refusal":
                yield _event(type="text", text="\n\nI can't help with that one. Try asking it a different way.")
                break
            if response.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": response.content})
                continue
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if not tool_uses:
                break
            if response.stop_reason == "max_tokens":
                yield _event(type="text", text="\n\n(The answer got too long and was cut off.)")
                break
            results = []
            for block in tool_uses:
                text, is_error = run_tool(block.name, block.input)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": text, "is_error": is_error})
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": results})
            yield _event(type="text", text="\n\n")
        else:
            yield _event(type="text", text="\n\n(Stopped after several data lookups; please narrow the question.)")
    except anthropic.AuthenticationError:
        yield _event(type="error", message="The AI service rejected the API key. Check ANTHROPIC_API_KEY.")
    except anthropic.RateLimitError:
        yield _event(type="error", message="The AI service is busy right now. Please try again in a minute.")
    except anthropic.APIStatusError as e:
        log.warning("AI chat failed: %s", e)
        yield _event(type="error", message=f"The AI service returned an error ({e.status_code}). Please try again.")
    except anthropic.APIConnectionError:
        yield _event(type="error", message="Could not reach the AI service. Check the internet connection.")
    yield _event(type="done")
