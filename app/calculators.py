"""
Pure, side-effect-free calculation functions ported 1:1 from the formulas used
in finsuite.html. Each function mirrors the JS function of (roughly) the same
name so behaviour stays consistent between the web app and this API.
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import math


# ---------------------------------------------------------------------------
# 01. Ratio calculators
# ---------------------------------------------------------------------------
def calc_roe(net_income: float, equity: float) -> float:
    if equity == 0:
        raise ValueError("equity must not be zero")
    return (net_income / equity) * 100


def calc_roa(net_income: float, assets: float) -> float:
    if assets == 0:
        raise ValueError("assets must not be zero")
    return (net_income / assets) * 100


def calc_debt_ratio(liabilities: float, assets: float) -> float:
    if assets == 0:
        raise ValueError("assets must not be zero")
    return liabilities / assets


def calc_health(roe: float) -> str:
    if roe > 20:
        return "Excellent"
    if roe >= 10:
        return "Good"
    return "Weak"


# ---------------------------------------------------------------------------
# 02. Personal finance report
# ---------------------------------------------------------------------------
def calc_report(income: float, expenses: float, savings: float, debt: float, equity: float) -> dict:
    if equity == 0 or income == 0 or expenses == 0:
        raise ValueError("equity, income and expenses must not be zero")
    net_profit = income - expenses
    roe = (net_profit / equity) * 100
    roa = (net_profit / income) * 100
    current_ratio = savings / expenses
    debt_to_equity = debt / equity

    tips = []
    if net_profit < 0:
        tips.append("Expenses currently exceed income — the first priority is closing that gap before anything else.")
    if current_ratio < 1:
        tips.append("Savings are less than one month of expenses, which leaves little buffer for surprises.")
    if debt_to_equity > 1:
        tips.append("Debt is larger than what's owned outright — paying it down would reduce financial risk.")
    if roe > 15 and net_profit >= 0:
        tips.append("Equity is being put to good use — the surplus each month is meaningfully growing what's owned.")
    if not tips:
        tips.append("The numbers are broadly balanced — no immediate red flags in this snapshot.")

    return {
        "net_profit": net_profit, "roe": roe, "roa": roa,
        "current_ratio": current_ratio, "debt_to_equity": debt_to_equity, "tips": tips,
    }


# ---------------------------------------------------------------------------
# 03. AI Finance Assistant (ratio snapshot + glossary lookup)
# ---------------------------------------------------------------------------
def calc_assistant(income: float, expenses: float, savings: float, borrowed: float, owned: float) -> dict:
    if not income or not owned:
        raise ValueError("income and owned must be non-zero")
    net_profit = income - expenses
    roe = (net_profit / owned) * 100 if owned else 0
    roa = (net_profit / income) * 100 if income else 0
    borrowed_to_owned = (borrowed / owned) if owned else 0
    savings_ratio = (savings / income) * 100 if income else 0

    if borrowed_to_owned > 1:
        msg = "Borrowed money exceeds owned money — leverage is high, and paying down debt would strengthen the position."
    elif savings_ratio < 20:
        msg = "Savings are under 20% of income — building a larger buffer would help absorb unexpected expenses."
    else:
        msg = "The snapshot looks reasonably healthy — leverage is moderate and savings provide a decent cushion."

    return {
        "net_profit": net_profit, "roe": roe, "roa": roa,
        "borrowed_to_owned": borrowed_to_owned, "savings_ratio": savings_ratio, "insight": msg,
    }


TERMS = {
    "roe": "ROE (Return on Equity) = Net Income ÷ Equity × 100. It shows how much profit is generated for every rupee shareholders put in.",
    "roa": "ROA (Return on Assets) = Net Income ÷ Assets × 100. It shows how efficiently total assets are turned into profit.",
    "gdp": "GDP (Gross Domestic Product) is the total value of goods and services a country produces in a given period.",
    "inflation": "Inflation is the rate at which prices rise over time, which erodes how much a fixed amount of money can buy.",
    "assets": "Assets are everything a person or company owns that has value — cash, property, equipment, investments.",
    "liabilities": "Liabilities are what's owed to others — loans, bills, and other obligations.",
    "equity": "Equity is what's left over after subtracting liabilities from assets — the portion truly owned, free of debt.",
    "debt ratio": "Debt Ratio = Liabilities ÷ Assets. It shows what share of total assets is financed by debt rather than equity.",
    "debt-to-equity": "Debt-to-Equity = Debt ÷ Equity. A ratio above 1 means debt outweighs what's owned outright.",
    "profit margin": "Profit Margin = Net Income ÷ Revenue × 100. It shows how much of each rupee in sales is kept as profit.",
    "revenue growth": "Revenue Growth measures how much sales increased compared to a prior period — a signal of business momentum.",
    "current ratio": "Current Ratio = Savings ÷ Expenses. A simplified liquidity check for how many months of expenses your savings could cover.",
    "credit score": "Credit Score (roughly 300–900) summarises how reliably someone has repaid debt in the past.",
    "emi": "EMI (Equated Monthly Installment) is the fixed monthly payment made toward repaying a loan, covering principal and interest.",
    "net profit": "Net Profit = Income − Expenses. What's left over each period after covering all outgoing costs.",
    "net income": "Net Income is the profit left after all expenses, taxes, and costs are subtracted from revenue.",
    "revenue": "Revenue is the total money a company brings in from sales before any costs are deducted.",
    "customer satisfaction": "Customer Satisfaction is a percentage measure of how positively customers rate their experience with a company.",
    "employee retention": "Employee Retention is the percentage of employees who stay with a company over a given period.",
    "savings ratio": "Savings Ratio = (Savings ÷ Income) × 100 — what share of income is set aside rather than spent.",
    "borrowed-to-owned": "Borrowed-to-Owned Ratio = Borrowed Money ÷ Owned Money. Above 1 means you owe more than you outright own.",
}


def chat_reply(question: str) -> str:
    lower = question.lower()
    for term, definition in TERMS.items():
        if term in lower:
            return definition
    return "I don't have a definition for that yet — try asking about ROE, ROA, debt ratio, credit score, EMI, or similar finance terms."


# ---------------------------------------------------------------------------
# 04/05. Loan insight generator + credit score & risk
# ---------------------------------------------------------------------------
def credit_insight(score: float) -> str:
    if score >= 800:
        return "Excellent credit profile."
    if score >= 750:
        return "Good credit score."
    if score >= 650:
        return "Moderate credit profile."
    return "Loan approval risk is high."


def credit_recommendation(score: float) -> str:
    if score >= 800:
        return "Strong candidate for premium loan products."
    if score >= 750:
        return "Eligible for loan approval."
    if score >= 650:
        return "Consider reducing EMI burden."
    return "Improve credit score before applying."


def credit_category(score: float) -> dict:
    if score < 550:
        return {"category": "Poor", "risk": "Very High Risk", "level": "sell"}
    if score < 650:
        return {"category": "Fair", "risk": "High Risk", "level": "sell"}
    if score < 750:
        return {"category": "Good", "risk": "Medium Risk", "level": "hold"}
    if score < 800:
        return {"category": "Very Good", "risk": "Low Risk", "level": "buy"}
    return {"category": "Excellent", "risk": "Very Low Risk", "level": "buy"}


def calc_credit_score(score: float) -> dict:
    if score < 300 or score > 900:
        raise ValueError("score must be between 300 and 900")
    cat = credit_category(score)
    return {**cat, "insight": f"{credit_insight(score)} {credit_recommendation(score)}"}


def screen_loans(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        score = r.get("credit_score")
        out.append({
            **r,
            "ai_insight": credit_insight(score) if score is not None else "—",
            "ai_recommendation": credit_recommendation(score) if score is not None else "—",
        })
    return out


def calc_risk(score: float, income: Optional[float] = None, emi: Optional[float] = None, name: str = "This customer") -> dict:
    levels = ["Very High Risk", "High Risk", "Medium Risk", "Low Risk", "Very Low Risk"]
    if score < 550:
        idx = 0
    elif score < 650:
        idx = 1
    elif score < 750:
        idx = 2
    elif score < 800:
        idx = 3
    else:
        idx = 4

    bumped = False
    if income and emi and (emi / income) > 0.4 and idx > 0:
        idx -= 1
        bumped = True

    level = levels[idx]
    band = "sell" if idx <= 1 else "hold" if idx == 2 else "buy"

    parts = [f"Credit score {score} places this in the base risk band shown in the table."]
    if income and emi:
        parts.append(f"EMI is {(emi / income) * 100:.0f}% of income.")
    if bumped:
        parts.append("That repayment burden pushed the risk level up by one step.")

    return {"name": name, "level": level, "band": band, "insight": " ".join(parts)}


# ---------------------------------------------------------------------------
# 06. Investment recommendation (single company)
# ---------------------------------------------------------------------------
def calc_invest(revenue_growth: float, profit_margin: float, roa: float, roe: float) -> dict:
    score = 0
    if revenue_growth >= 15:
        score += 1
    if profit_margin >= 15:
        score += 1
    if roa >= 10:
        score += 1
    if roe >= 15:
        score += 1

    if score >= 3:
        band, label = "buy", "BUY"
    elif score >= 2:
        band, label = "hold", "HOLD"
    else:
        band, label = "sell", "AVOID"

    return {"score": score, "band": band, "label": label}


# ---------------------------------------------------------------------------
# 07. Company performance
# ---------------------------------------------------------------------------
def analyze_company(name: str, revenue_growth: float, csat: float, retention: float) -> dict:
    score = 0
    if revenue_growth > 15:
        score += 34
    if csat > 80:
        score += 33
    if retention > 85:
        score += 33

    if score >= 85:
        status, band = "Excellent", "buy"
    elif score >= 60:
        status, band = "Good", "hold"
    else:
        status, band = "Needs Improvement", "sell"

    recs = []
    if revenue_growth <= 15:
        recs.append("Revenue growth is below the 15% mark that usually signals strong expansion.")
    if csat <= 80:
        recs.append("Customer satisfaction has room to improve — service quality is a lever worth pulling.")
    if retention <= 85:
        recs.append("Employee retention is on the lower side, which can affect long-term stability.")
    if not recs:
        recs.append("All three indicators are strong — the focus now is sustaining this level of performance.")

    return {"name": name, "score": score, "status": status, "band": band, "recommendations": recs}


# ---------------------------------------------------------------------------
# 08. Portfolio dashboard (multi-company metrics + scoring)
# ---------------------------------------------------------------------------
def compute_company_metrics(row: dict) -> dict:
    company = row.get("company", "Unnamed")
    roe = row.get("roe")
    roa = row.get("roa")
    debt_ratio = row.get("debt_ratio")
    profit_margin = row.get("profit_margin")
    revenue_growth = row.get("revenue_growth")

    net_income = row.get("net_income")
    equity = row.get("equity")
    assets = row.get("assets")
    liabilities = row.get("liabilities")
    revenue = row.get("revenue")
    prev_revenue = row.get("previous_revenue")

    if roe is None and net_income is not None and equity:
        roe = (net_income / equity) * 100
    if roa is None and net_income is not None and assets:
        roa = (net_income / assets) * 100
    if debt_ratio is None and liabilities is not None and assets:
        debt_ratio = liabilities / assets
    if profit_margin is None and net_income is not None and revenue:
        profit_margin = (net_income / revenue) * 100
    if revenue_growth is None and revenue is not None and prev_revenue:
        revenue_growth = ((revenue - prev_revenue) / prev_revenue) * 100

    earned = possible = 0
    if roe is not None:
        possible += 30
        if roe > 15:
            earned += 30
    if roa is not None:
        possible += 25
        if roa > 10:
            earned += 25
    if revenue_growth is not None:
        possible += 25
        if revenue_growth > 10:
            earned += 25
    if profit_margin is not None:
        possible += 20
        if profit_margin > 15:
            earned += 20

    score = round((earned / possible) * 100) if possible > 0 else 0
    recommendation = "buy" if score >= 75 else "hold" if score >= 50 else "sell"
    risk = "Low" if score >= 75 else "Medium" if score >= 50 else "High"
    health = calc_health(roe) if roe is not None else None

    return {
        "company": company, "roe": roe, "roa": roa, "debt_ratio": debt_ratio,
        "profit_margin": profit_margin, "revenue_growth": revenue_growth,
        "score": score, "recommendation": recommendation, "risk": risk,
        "health": health, "has_data": possible > 0,
    }


# ---------------------------------------------------------------------------
# 09. Goal & retirement planner
# ---------------------------------------------------------------------------
def goal_monthly_sip(remaining_fv: float, annual_return_pct: float, years: float) -> float:
    n = round(years * 12)
    i = annual_return_pct / 12 / 100
    if n <= 0:
        return 0
    if i == 0:
        return remaining_fv / n
    factor = (((1 + i) ** n - 1) / i) * (1 + i)
    return remaining_fv / factor


def goal_corpus_at_month(sip: float, current_savings: float, annual_return_pct: float, months_elapsed: int) -> float:
    i = annual_return_pct / 12 / 100
    savings_grown = current_savings * ((1 + i) ** months_elapsed)
    if months_elapsed <= 0:
        sip_grown = 0
    elif i == 0:
        sip_grown = sip * months_elapsed
    else:
        sip_grown = sip * (((1 + i) ** months_elapsed - 1) / i) * (1 + i)
    return savings_grown + sip_grown


def calc_goal_plan(target: float, years: float, ret: float, inflation: float,
                    current: float = 0, income: Optional[float] = None, name: str = "Your goal") -> dict:
    if target <= 0 or years <= 0:
        raise ValueError("target and years must be positive")

    fv_goal = target * ((1 + inflation / 100) ** years)
    fv_current = current * ((1 + ret / 100) ** years)
    remaining = max(fv_goal - fv_current, 0)
    sip = goal_monthly_sip(remaining, ret, years)
    total_invested = current + sip * round(years * 12)
    gain = max(fv_goal - total_invested, 0)

    schedule = [
        {"year": y, "projected_corpus": round(goal_corpus_at_month(sip, current, ret, y * 12)), "target": round(fv_goal)}
        for y in range(round(years) + 1)
    ]

    parts = [f'To reach "{name}" in {years} year(s), accounting for {inflation}% annual inflation, '
             f"you'll need roughly {fv_goal:,.0f} at that point in time."]
    if remaining <= 0:
        parts.append("Your existing savings, growing at the expected return, are already projected to cover this.")
    else:
        parts.append(f"Investing {sip:,.0f} every month at an assumed {ret}% annual return gets you there.")
        if income:
            pct_income = (sip / income) * 100
            if pct_income > 50:
                parts.append(f"That's {pct_income:.0f}% of your monthly income — likely unaffordable; consider stretching the timeline.")
            elif pct_income > 30:
                parts.append(f"That's {pct_income:.0f}% of your monthly income — tight but workable.")
            else:
                parts.append(f"That's a manageable {pct_income:.0f}% of your monthly income.")

    return {
        "future_value_goal": fv_goal, "monthly_sip": sip, "total_invested": total_invested,
        "gain": gain, "schedule": schedule, "insight": " ".join(parts),
    }


def calc_emergency_fund(expenses: float, savings: float = 0) -> dict:
    if expenses <= 0:
        raise ValueError("expenses must be positive")
    months = savings / expenses
    pct = min((months / 6) * 100, 100)
    level = "buy" if months >= 6 else "hold" if months >= 3 else "sell"
    if months >= 6:
        msg = f"Well protected — {months:.1f} months of expenses in reserve meets the standard 6-month benchmark."
    elif months >= 3:
        msg = f"Building — {months:.1f} months covered. Keep topping this up; aim for 6 months."
    else:
        msg = f"Critical — only {months:.1f} months covered. Prioritize this before any other savings goal."
    return {"months_covered": months, "progress_pct": pct, "level": level, "insight": msg}


# ---------------------------------------------------------------------------
# 12. Investment growth & target planner (what-if, target/stop-loss)
# ---------------------------------------------------------------------------
def calc_what_if(amount: float, price_then: float, price_now: float, days_held: int) -> dict:
    if amount <= 0 or price_then <= 0:
        raise ValueError("amount and price_then must be positive")
    shares = amount / price_then
    value_now = shares * price_now
    gain = value_now - amount
    gain_pct = (gain / amount) * 100
    years = max(days_held, 1) / 365
    cagr = ((value_now / amount) ** (1 / years) - 1) * 100 if years >= 0.08 else None
    return {"shares": shares, "value_now": value_now, "gain": gain, "gain_pct": gain_pct, "cagr": cagr}


def calc_target_plan(entry: float, qty: float, target_pct: float, stop_pct: float) -> dict:
    if entry <= 0 or qty <= 0:
        raise ValueError("entry and qty must be positive")
    target_price = entry * (1 + target_pct / 100)
    stop_price = entry * (1 - stop_pct / 100)
    gain_amt = (target_price - entry) * qty
    loss_amt = (entry - stop_price) * qty
    rr = gain_amt / loss_amt if loss_amt > 0 else None

    if rr is None:
        verdict = "Set a stop-loss above 0% to see the risk-reward ratio."
        band = None
    else:
        band = "buy" if rr >= 2 else "hold" if rr >= 1 else "sell"
        verdict = ("a favorable setup — the potential reward is at least double the risk." if rr >= 2 else
                   "a workable but modest setup — reward and risk are close." if rr >= 1 else
                   "a weak setup — you're risking more than you stand to gain.")

    return {
        "target_price": target_price, "stop_price": stop_price, "gain_amount": gain_amt,
        "loss_amount": loss_amt, "risk_reward": rr, "band": band, "verdict": verdict,
    }


# ---------------------------------------------------------------------------
# 13. Portfolio & tax tools
# ---------------------------------------------------------------------------
def compare_sip_lump_sum(total: float, months: int, start_price: float, prices_by_month: list[float], last_price: float) -> dict:
    """prices_by_month: one representative price per calendar month in the window, in order."""
    if total <= 0 or months <= 0:
        raise ValueError("total and months must be positive")
    if len(prices_by_month) < months:
        raise ValueError("not enough monthly prices for that many months")

    lump_shares = total / start_price
    per_installment = total / months
    sip_shares = sum(per_installment / p for p in prices_by_month[:months])

    lump_final = lump_shares * last_price
    sip_final = sip_shares * last_price
    diff = lump_final - sip_final
    winner = "lump_sum" if diff >= 0 else "sip"

    return {"lump_sum_value": lump_final, "sip_value": sip_final, "winner": winner, "difference": abs(diff)}


def estimate_capital_gains_tax(buy_price: float, sell_price: float, qty: float,
                                buy_date: date, sell_date: date, other_ltcg: float = 0) -> dict:
    holding_days = (sell_date - buy_date).days
    if holding_days <= 0:
        raise ValueError("sell date must be after buy date")

    gain = (sell_price - buy_price) * qty
    is_long_term = holding_days > 365

    if not is_long_term:
        tax_type = "STCG (20%)"
        tax = gain * 0.20 if gain > 0 else 0
    else:
        tax_type = "LTCG (12.5%)"
        exemption_left = max(0, 125000 - other_ltcg)
        taxable_gain = max(0, gain - exemption_left)
        tax = taxable_gain * 0.125

    tax_with_cess = tax * 1.04  # 4% health & education cess
    net = (sell_price * qty) - tax_with_cess

    return {
        "gain": gain, "holding_days": holding_days, "tax_type": tax_type,
        "tax": tax_with_cess, "net_proceeds": net,
    }


def check_52_week_range(current: float, high: float, low: float) -> dict:
    if high == low:
        raise ValueError("52-week high and low must differ")
    pct = ((current - low) / (high - low)) * 100
    from_high = ((current - high) / high) * 100
    from_low = ((current - low) / low) * 100
    return {
        "current": current, "high": high, "low": low,
        "range_position_pct": max(2, min(100, pct)),
        "from_low_pct": from_low, "from_high_pct": from_high,
    }