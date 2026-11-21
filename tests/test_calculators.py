"""The money maths: every figure here was worked out by hand or from a published rule."""
import pytest

from app import calculators as calc
from app import planning


# ---------------------------------------------------------------- income tax
def test_new_regime_tax_on_15_lakh():
    r = planning.calc_income_tax(1_500_000)
    # taxable 14.25 L: 5% of 4 L + 10% of 4 L + 15% of 2.25 L = 93,750, plus 4% cess
    assert r["new"]["taxable_income"] == 1_425_000
    assert r["new"]["total_tax"] == pytest.approx(97_500)


def test_new_regime_is_tax_free_up_to_12_75_lakh_for_salaried():
    assert planning.calc_income_tax(1_275_000)["new"]["total_tax"] == 0


def test_marginal_relief_just_above_the_rebate_limit():
    r = planning.calc_income_tax(1_300_000)["new"]       # taxable 12.25 L
    assert r["total_tax"] == pytest.approx(26_000)        # income above 12 L (25,000) + 4% cess


def test_old_regime_is_tax_free_up_to_5_lakh_taxable():
    assert planning.calc_income_tax(550_000)["old"]["total_tax"] == 0


def test_deductions_are_capped_at_their_legal_limit():
    r = planning.calc_income_tax(2_000_000, sec80c=900_000)
    assert r["deductions_allowed"]["sec80c"] == 150_000
    assert "capped" in r["insight"]


def test_surcharge_applies_above_50_lakh():
    r = planning.calc_income_tax(6_000_000)["new"]
    assert r["surcharge"] > 0
    assert r["total_tax"] > r["tax_on_slabs"]


def test_break_even_deductions_make_both_regimes_equal():
    r = planning.calc_income_tax(1_800_000, sec80c=150_000)
    be = r["break_even_deductions"]
    assert be is not None
    again = planning.calc_income_tax(1_800_000, other_deductions=be)
    assert again["old"]["total_tax"] == pytest.approx(again["new"]["total_tax"], rel=0.01)


def test_tax_rejects_bad_input():
    with pytest.raises(ValueError):
        planning.calc_income_tax(-1)
    with pytest.raises(ValueError):
        planning.calc_income_tax(1_000_000, age_group="nope")


# ------------------------------------------------------------------ loan EMI
def test_emi_on_25_lakh_at_8_5_for_20_years():
    r = planning.calc_loan_emi(2_500_000, 8.5, 240)
    assert r["emi"] == pytest.approx(21_696, abs=2)
    assert r["schedule"][-1]["balance"] == pytest.approx(0, abs=1)
    assert r["total_payment"] == pytest.approx(r["emi"] * 240, rel=1e-4)


def test_zero_interest_loan_is_a_plain_split():
    assert planning.calc_loan_emi(120_000, 0, 12)["emi"] == 10_000


def test_prepayment_saves_interest_and_shortens_the_loan():
    base = planning.calc_loan_emi(2_500_000, 8.5, 240)
    pre = planning.calc_loan_emi(2_500_000, 8.5, 240, prepay_amount=200_000, prepay_month=12)
    p = pre["prepayment"]
    assert p["interest_saved"] > 0
    assert p["months"] < base["months"]
    assert p["schedule"][-1]["balance"] == pytest.approx(0, abs=1)
    assert p["total_interest"] == pytest.approx(base["total_interest"] - p["interest_saved"])


def test_emi_validates_input():
    with pytest.raises(ValueError):
        planning.calc_loan_emi(0, 8, 12)
    with pytest.raises(ValueError):
        planning.calc_loan_emi(100_000, 8, 12, prepay_amount=1000, prepay_month=99)


# -------------------------------------------------------------------- budget
def _items(*rows):
    return [{"category": c, "amount": a, "kind": k} for c, a, k in rows]


def test_budget_on_track():
    r = planning.calc_budget(80_000, _items(("Rent", 30_000, "need"), ("Fun", 15_000, "want"), ("SIP", 20_000, "saving")))
    assert all(b["on_track"] for b in r["buckets"])
    assert r["leftover"] == 15_000


def test_budget_flags_overspending_and_low_saving():
    r = planning.calc_budget(50_000, _items(("Rent", 35_000, "need"), ("Fun", 20_000, "want")))
    assert r["leftover"] == -5_000
    assert not any(b["on_track"] for b in r["buckets"] if b["kind"] in ("need", "saving"))
    assert "more than your income" in r["tips"][0]


def test_budget_rejects_unknown_kind():
    with pytest.raises(ValueError):
        planning.calc_budget(50_000, _items(("X", 10, "luxury")))


# ----------------------------------------------------------------- retirement
FIRE = dict(current_age=30, retire_age=50, life_expectancy=85, monthly_expenses=50_000,
            current_corpus=1_000_000)


def test_investing_more_builds_a_bigger_corpus():
    low = planning.calc_fire(**FIRE, monthly_investment=10_000)
    high = planning.calc_fire(**FIRE, monthly_investment=40_000)
    assert high["projected_corpus"] > low["projected_corpus"]
    assert high["gap"] < low["gap"]


def test_required_sip_closes_the_gap():
    r = planning.calc_fire(**FIRE, monthly_investment=0)
    again = planning.calc_fire(**FIRE, monthly_investment=r["required_sip"])
    assert again["projected_corpus"] == pytest.approx(again["corpus_needed"], rel=0.01)


def test_fire_number_is_25_times_yearly_expenses_at_4_percent():
    r = planning.calc_fire(**FIRE, monthly_investment=0, inflation=0)
    assert r["fire_number"] == pytest.approx(50_000 * 12 * 25)


def test_fire_rejects_impossible_ages():
    with pytest.raises(ValueError):
        planning.calc_fire(current_age=60, retire_age=50, life_expectancy=85, monthly_expenses=1000)


# ---------------------------------------------------- older calculators
def test_goal_plan_without_growth_or_inflation_is_a_straight_split():
    r = calc.calc_goal_plan(1_000_000, 10, 0, 0)
    assert r["monthly_sip"] == pytest.approx(1_000_000 / 120)


def test_ratios():
    assert calc.calc_roe(100, 500) == 20
    assert calc.calc_health(25) == "Excellent"
    assert calc.calc_health(5) == "Weak"
    with pytest.raises(ValueError):
        calc.calc_roe(1, 0)


def test_chat_lookup_finds_new_terms():
    assert "xirr" in calc.chat_reply("what is xirr").lower() or "different dates" in calc.chat_reply("what is xirr")
    assert "don't have a definition" in calc.chat_reply("zzzz qqqq")
