"""
Personal planning calculators added in the second phase: income tax (old vs
new regime), loan EMI with prepayment, 50/30/20 budget and retirement / FIRE.
Pure functions with no network calls, in the same style as calculators.py.
"""
from __future__ import annotations
from typing import Optional

from .calculators import goal_corpus_at_month, goal_monthly_sip


# ---------------------------------------------------------------------------
# 18. Income tax: old vs new regime (India, FY 2025-26 / AY 2026-27)
# ---------------------------------------------------------------------------
LAKH = 100_000
NEW_SLABS = [(4 * LAKH, 0), (8 * LAKH, 5), (12 * LAKH, 10), (16 * LAKH, 15),
             (20 * LAKH, 20), (24 * LAKH, 25), (None, 30)]
OLD_SLABS = {   # basic exemption depends on age
    "below60": [(2.5 * LAKH, 0), (5 * LAKH, 5), (10 * LAKH, 20), (None, 30)],
    "60to79": [(3 * LAKH, 0), (5 * LAKH, 5), (10 * LAKH, 20), (None, 30)],
    "80plus": [(5 * LAKH, 0), (10 * LAKH, 20), (None, 30)],
}
SURCHARGE = [(5 * 10**7, 37), (2 * 10**7, 25), (10**7, 15), (50 * LAKH, 10)]   # highest first
CAPS = {"sec80c": 150_000, "sec80d": 100_000, "nps_80ccd1b": 50_000, "home_loan_interest": 200_000}


def _slab_tax(taxable: float, slabs) -> tuple[float, list[dict]]:
    tax, lower, rows = 0.0, 0.0, []
    for upper, rate in slabs:
        top = taxable if upper is None else min(taxable, upper)
        if top > lower:
            part = (top - lower) * rate / 100
            rows.append({"from": lower, "to": upper, "rate": rate, "amount": top - lower, "tax": part})
            tax += part
        if upper is None or taxable <= upper:
            break
        lower = upper
    return tax, rows


def _surcharge(taxable: float, tax: float, slabs, rebate_fn, cap: int) -> float:
    for threshold, rate in SURCHARGE:
        rate = min(rate, cap)
        if taxable > threshold:
            surcharge = tax * rate / 100
            # Marginal relief: crossing a threshold must not cost more in extra
            # tax than the extra income itself.
            base = rebate_fn(threshold, _slab_tax(threshold, slabs)[0])
            lower_rate = next((min(r, cap) for t, r in SURCHARGE if t < threshold), 0)
            limit = base * (1 + lower_rate / 100) + (taxable - threshold)
            return max(0.0, min(surcharge, limit - tax))
    return 0.0


def _regime(gross: float, std_deduction: float, deductions: float, slabs, rebate_fn,
            surcharge_cap: int) -> dict:
    taxable = max(gross - std_deduction - deductions, 0)
    slab_tax, rows = _slab_tax(taxable, slabs)
    after_rebate = rebate_fn(taxable, slab_tax)
    surcharge = _surcharge(taxable, after_rebate, slabs, rebate_fn, surcharge_cap)
    cess = (after_rebate + surcharge) * 0.04
    total = after_rebate + surcharge + cess
    return {
        "gross_income": gross, "standard_deduction": std_deduction, "deductions": deductions,
        "taxable_income": taxable, "slabs": rows, "tax_on_slabs": slab_tax,
        "rebate": slab_tax - after_rebate, "surcharge": surcharge, "cess": cess, "total_tax": total,
        "effective_rate": total / gross * 100 if gross else 0.0,
        "monthly_take_home": (gross - total) / 12,
    }


def _new_rebate(taxable: float, tax: float) -> float:
    # Section 87A: no tax up to ₹12 lakh; just above it, tax can't exceed the income above ₹12 lakh.
    if taxable <= 12 * LAKH:
        return 0.0
    return min(tax, taxable - 12 * LAKH)


def _old_rebate(taxable: float, tax: float) -> float:
    return max(tax - 12_500, 0.0) if taxable <= 5 * LAKH else tax


def calc_income_tax(gross_income: float, salaried: bool = True, age_group: str = "below60",
                    sec80c: float = 0, sec80d: float = 0, nps_80ccd1b: float = 0,
                    home_loan_interest: float = 0, hra_exemption: float = 0,
                    other_deductions: float = 0) -> dict:
    if gross_income < 0:
        raise ValueError("income must not be negative")
    if age_group not in OLD_SLABS:
        raise ValueError("age_group must be below60, 60to79 or 80plus")
    claimed = {"sec80c": sec80c, "sec80d": sec80d, "nps_80ccd1b": nps_80ccd1b,
               "home_loan_interest": home_loan_interest}
    if any(v < 0 for v in [*claimed.values(), hra_exemption, other_deductions]):
        raise ValueError("deductions must not be negative")
    allowed = {k: min(v, CAPS[k]) for k, v in claimed.items()}
    old_deductions = sum(allowed.values()) + hra_exemption + other_deductions

    new = _regime(gross_income, 75_000 if salaried else 0, 0, NEW_SLABS, _new_rebate, 25)
    old = _regime(gross_income, 50_000 if salaried else 0, old_deductions,
                  OLD_SLABS[age_group], _old_rebate, 37)

    # Old-regime deductions at which both regimes cost the same.
    lo, hi = 0.0, float(gross_income)
    if _regime(gross_income, old["standard_deduction"], hi, OLD_SLABS[age_group], _old_rebate, 37)["total_tax"] > new["total_tax"]:
        break_even = None   # even deducting everything can't beat the new regime
    else:
        for _ in range(60):
            mid = (lo + hi) / 2
            t = _regime(gross_income, old["standard_deduction"], mid, OLD_SLABS[age_group], _old_rebate, 37)["total_tax"]
            lo, hi = (mid, hi) if t > new["total_tax"] else (lo, mid)
        break_even = hi

    diff = old["total_tax"] - new["total_tax"]
    better = "new" if diff > 0.5 else "old" if diff < -0.5 else "same"
    if better == "same":
        insight = "Both regimes cost about the same for you, so the simpler new regime is usually the easier choice."
    else:
        insight = (f"The {better} regime saves you about ₹{abs(diff):,.0f} a year "
                   f"(₹{abs(diff) / 12:,.0f} a month).")
    if break_even is not None and better == "new":
        insight += (f" The old regime would only win if your deductions (80C, 80D, HRA, home loan "
                    f"and so on) were above about ₹{break_even:,.0f}; you entered ₹{old_deductions:,.0f}.")
    elif break_even is None:
        insight += " At this income no amount of old-regime deductions beats the new regime."
    capped = [k for k in claimed if claimed[k] > CAPS[k]]
    if capped:
        insight += " Some deductions were above their legal limit and were capped: " + ", ".join(capped) + "."

    return {"new": new, "old": old, "better": better, "savings": abs(diff),
            "break_even_deductions": break_even, "deductions_allowed": allowed, "insight": insight}


# ---------------------------------------------------------------------------
# 19. Loan EMI with repayment table and prepayment savings
# ---------------------------------------------------------------------------
def calc_emi_amount(principal: float, annual_rate: float, months: int) -> float:
    i = annual_rate / 12 / 100
    if i == 0:
        return principal / months
    return principal * i * (1 + i) ** months / ((1 + i) ** months - 1)


def _amortize(principal: float, annual_rate: float, emi: float, max_months: int,
              prepay_amount: float = 0, prepay_month: int = 0, extra_monthly: float = 0) -> list[dict]:
    i = annual_rate / 12 / 100
    balance, rows, month = principal, [], 0
    while balance > 0.005 and month < max_months:
        month += 1
        interest = balance * i
        principal_part = min(emi - interest, balance)
        balance -= principal_part
        extra = 0.0
        if balance > 0:
            extra = min(extra_monthly + (prepay_amount if month == prepay_month else 0), balance)
            balance -= extra
        rows.append({"month": month, "emi": interest + principal_part, "interest": interest,
                     "principal": principal_part, "prepayment": extra, "balance": max(balance, 0.0)})
    return rows


def _yearly(rows: list[dict]) -> list[dict]:
    years = {}
    for r in rows:
        y = years.setdefault((r["month"] - 1) // 12 + 1, {"year": (r["month"] - 1) // 12 + 1,
                                                        "emi": 0.0, "interest": 0.0, "principal": 0.0,
                                                        "prepayment": 0.0, "balance": 0.0})
        for k in ("emi", "interest", "principal", "prepayment"):
            y[k] += r[k]
        y["balance"] = r["balance"]
    return list(years.values())


def calc_loan_emi(principal: float, annual_rate: float, tenure_months: int,
                  prepay_amount: float = 0, prepay_month: int = 0, extra_monthly: float = 0) -> dict:
    if principal <= 0 or tenure_months <= 0:
        raise ValueError("loan amount and tenure must be positive")
    if annual_rate < 0 or prepay_amount < 0 or extra_monthly < 0:
        raise ValueError("rate and prepayments must not be negative")
    if tenure_months > 600:
        raise ValueError("tenure can be at most 600 months (50 years)")
    emi = calc_emi_amount(principal, annual_rate, tenure_months)
    base = _amortize(principal, annual_rate, emi, tenure_months)
    base_interest = sum(r["interest"] for r in base)
    out = {"emi": emi, "total_interest": base_interest, "total_payment": principal + base_interest,
           "months": len(base), "schedule": base, "yearly": _yearly(base), "prepayment": None}

    if prepay_amount > 0 or extra_monthly > 0:
        if prepay_amount > 0 and not 1 <= prepay_month <= tenure_months:
            raise ValueError("prepayment month must be within the loan tenure")
        pre = _amortize(principal, annual_rate, emi, tenure_months, prepay_amount, prepay_month, extra_monthly)
        pre_interest = sum(r["interest"] for r in pre)
        saved, months_saved = base_interest - pre_interest, len(base) - len(pre)
        out["prepayment"] = {
            "months": len(pre), "total_interest": pre_interest, "interest_saved": saved,
            "months_saved": months_saved, "schedule": pre, "yearly": _yearly(pre),
            "total_prepaid": sum(r["prepayment"] for r in pre),
        }
        out["insight"] = (f"Prepaying saves ₹{saved:,.0f} of interest and closes the loan "
                          f"{months_saved} month(s) early ({months_saved // 12} yr {months_saved % 12} mo), "
                          f"keeping the same EMI of ₹{emi:,.0f}.")
    else:
        out["insight"] = (f"You will pay ₹{base_interest:,.0f} in interest, which is "
                          f"{base_interest / principal * 100:.0f}% of the amount borrowed. "
                          "Add a prepayment to see how much interest it saves.")
    return out


# ---------------------------------------------------------------------------
# 20. Budget planner (50/30/20 rule)
# ---------------------------------------------------------------------------
BUCKETS = {"need": ("Needs", 50), "want": ("Wants", 30), "saving": ("Savings & debt repayment", 20)}


def calc_budget(income: float, items: list[dict]) -> dict:
    if income <= 0:
        raise ValueError("monthly income must be positive")
    totals = {k: 0.0 for k in BUCKETS}
    for it in items:
        if it["kind"] not in BUCKETS:
            raise ValueError("each item's kind must be need, want or saving")
        if it["amount"] < 0:
            raise ValueError("amounts must not be negative")
        totals[it["kind"]] += it["amount"]
    spent = totals["need"] + totals["want"]
    leftover = income - spent - totals["saving"]

    buckets, tips = [], []
    for k, (label, pct) in BUCKETS.items():
        actual = totals[k] + (max(leftover, 0) if k == "saving" else 0)   # unspent money counts as saved
        target = income * pct / 100
        diff = actual - target
        ok = diff <= 0 if k != "saving" else diff >= 0
        buckets.append({"kind": k, "label": label, "target_pct": pct, "target": target,
                        "actual": actual, "actual_pct": actual / income * 100, "difference": diff, "on_track": ok})
        if not ok and k == "need":
            tips.append(f"Needs take {actual / income * 100:.0f}% of income, above the 50% guide. "
                        "Look at rent, loan EMIs or bills that could be renegotiated.")
        elif not ok and k == "want":
            tips.append(f"Wants are ₹{diff:,.0f} over the 30% guide. Trimming dining out, shopping or "
                        "subscriptions frees money for savings.")
        elif not ok:
            tips.append(f"You are saving ₹{-diff:,.0f} less than the 20% guide (₹{target:,.0f}). "
                        "Try setting up an automatic SIP on salary day.")
    if leftover < 0:
        tips.insert(0, f"Your planned spending is ₹{-leftover:,.0f} more than your income. "
                       "Cut back before this turns into debt.")
    if not tips:
        tips.append("Great, your budget follows the 50/30/20 rule.")
    by_category = sorted(({"category": it["category"], "kind": it["kind"], "amount": it["amount"]}
                          for it in items if it["amount"] > 0), key=lambda r: -r["amount"])
    return {"income": income, "buckets": buckets, "leftover": leftover, "items": by_category, "tips": tips}


# ---------------------------------------------------------------------------
# 23. Retirement & FIRE (financial independence) planner
# ---------------------------------------------------------------------------
def _corpus_for_years(annual_expense: float, real_return_pct: float, years: float) -> float:
    """Money needed at retirement to pay an inflation-rising expense for `years`,
    withdrawn at the start of each year (present value of a growing annuity)."""
    r = real_return_pct / 100
    if abs(r) < 1e-9:
        return annual_expense * years
    return annual_expense * (1 - (1 + r) ** -years) / r * (1 + r)


def calc_fire(current_age: float, retire_age: float, life_expectancy: float, monthly_expenses: float,
              inflation: float = 6, return_pre: float = 12, return_post: float = 8,
              current_corpus: float = 0, monthly_investment: float = 0,
              withdrawal_rate: float = 4) -> dict:
    if not current_age < retire_age < life_expectancy:
        raise ValueError("ages must satisfy current age < retirement age < life expectancy")
    if monthly_expenses <= 0 or withdrawal_rate <= 0:
        raise ValueError("expenses and withdrawal rate must be positive")
    years = retire_age - current_age
    months = round(years * 12)
    expense_at_retire = monthly_expenses * (1 + inflation / 100) ** years
    real_post = ((1 + return_post / 100) / (1 + inflation / 100) - 1) * 100
    corpus_needed = _corpus_for_years(expense_at_retire * 12, real_post, life_expectancy - retire_age)
    fire_number = expense_at_retire * 12 / (withdrawal_rate / 100)
    fv_current = current_corpus * (1 + return_pre / 12 / 100) ** months
    required_sip = goal_monthly_sip(max(corpus_needed - fv_current, 0), return_pre, years)
    projected = goal_corpus_at_month(monthly_investment, current_corpus, return_pre, months)

    # Earliest age at which savings cover expenses forever at the chosen withdrawal rate.
    fi_age = None
    for m in range(0, round((100 - current_age) * 12) + 1):
        corpus = goal_corpus_at_month(monthly_investment, current_corpus, return_pre, m)
        need = monthly_expenses * (1 + inflation / 100) ** (m / 12) * 12 / (withdrawal_rate / 100)
        if corpus >= need:
            fi_age = current_age + m / 12
            break

    # Year by year: build up until retirement, then withdraw inflation-rising expenses.
    schedule, corpus, runs_out = [], current_corpus, None
    age = current_age
    while age <= life_expectancy + 1e-9:
        schedule.append({"age": round(age, 2), "corpus": round(max(corpus, 0))})
        if age < retire_age:
            corpus = goal_corpus_at_month(monthly_investment, corpus, return_pre, 12)
        else:
            expense = monthly_expenses * 12 * (1 + inflation / 100) ** (age - current_age)
            corpus = (corpus - expense) * (1 + return_post / 100)
            if corpus < 0 and runs_out is None:
                runs_out = age + 1
        age += 1

    gap = corpus_needed - projected
    if gap <= 0:
        insight = (f"On track: your current investing builds about ₹{projected:,.0f} by age {retire_age:g}, "
                   f"more than the ₹{corpus_needed:,.0f} needed to last until {life_expectancy:g}.")
    else:
        extra = max(required_sip - monthly_investment, 0)
        insight = (f"You need about ₹{corpus_needed:,.0f} by age {retire_age:g} but are on course for "
                   f"₹{projected:,.0f}. Investing ₹{required_sip:,.0f} a month (₹{extra:,.0f} more than now) closes the gap.")
        if runs_out:
            insight += f" At the current pace the money would run out around age {runs_out:g}."
    if fi_age is not None:
        insight += f" You reach financial independence ({withdrawal_rate:g}% rule) at about age {fi_age:.1f}."
    return {
        "years_to_retire": years, "expense_at_retirement": expense_at_retire,
        "corpus_needed": corpus_needed, "fire_number": fire_number, "required_sip": required_sip,
        "projected_corpus": projected, "gap": gap, "fi_age": fi_age, "money_runs_out_age": runs_out,
        "real_return_post": real_post, "schedule": schedule, "insight": insight,
    }
