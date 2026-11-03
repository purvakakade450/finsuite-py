from __future__ import annotations
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


# 01 Ratios
class ROEIn(BaseModel):
    net_income: float
    equity: float


class ROAIn(BaseModel):
    net_income: float
    assets: float


class DebtRatioIn(BaseModel):
    liabilities: float
    assets: float


class HealthIn(BaseModel):
    roe: float


# 02 Personal finance report
class ReportIn(BaseModel):
    income: float
    expenses: float
    savings: float
    debt: float
    equity: float


# 03 AI assistant
class AssistantIn(BaseModel):
    income: float
    expenses: float
    savings: float
    borrowed: float
    owned: float


class ChatIn(BaseModel):
    question: str


# 04/05 Loans & credit risk
class LoanRow(BaseModel):
    customer_name: Optional[str] = None
    income: Optional[float] = None
    loan_amount: Optional[float] = None
    emi: Optional[float] = None
    credit_score: Optional[float] = None


class LoanScreenIn(BaseModel):
    rows: list[LoanRow]


class CreditScoreIn(BaseModel):
    score: float = Field(ge=300, le=900)


class RiskIn(BaseModel):
    score: float = Field(ge=300, le=900)
    income: Optional[float] = None
    emi: Optional[float] = None
    name: str = "This customer"


# 06 Investment recommendation
class InvestIn(BaseModel):
    revenue_growth: float
    profit_margin: float
    roa: float
    roe: float


# 07 Company performance
class CompanyPerfIn(BaseModel):
    name: str
    revenue_growth: float
    csat: float
    retention: float


# 08 Portfolio dashboard
class CompanyRow(BaseModel):
    company: str = "Unnamed"
    roe: Optional[float] = None
    roa: Optional[float] = None
    debt_ratio: Optional[float] = None
    profit_margin: Optional[float] = None
    revenue_growth: Optional[float] = None
    net_income: Optional[float] = None
    equity: Optional[float] = None
    assets: Optional[float] = None
    liabilities: Optional[float] = None
    revenue: Optional[float] = None
    previous_revenue: Optional[float] = None


class PortfolioIn(BaseModel):
    companies: list[CompanyRow]


# 09 Goal planner
class GoalPlanIn(BaseModel):
    name: str = "Your goal"
    target: float
    years: float
    ret: float = Field(description="Expected annual return, %")
    inflation: float
    current: float = 0
    income: Optional[float] = None


class EmergencyFundIn(BaseModel):
    expenses: float
    savings: float = 0


# 12 What-if / target planner
class WhatIfIn(BaseModel):
    amount: float
    price_then: float
    price_now: float
    days_held: int


class TargetPlanIn(BaseModel):
    entry: float
    qty: float
    target_pct: float
    stop_pct: float


# 13 Portfolio & tax tools
class SipVsLumpIn(BaseModel):
    total: float
    months: int
    start_price: float
    prices_by_month: list[float]
    last_price: float


class CapitalGainsTaxIn(BaseModel):
    buy_price: float
    sell_price: float
    qty: float
    buy_date: date
    sell_date: date
    other_ltcg: float = 0


class Range52WIn(BaseModel):
    current: float
    high: float
    low: float

# 18 Income tax
class IncomeTaxIn(BaseModel):
    gross_income: float = Field(ge=0, description="Annual income before deductions, ₹")
    salaried: bool = True
    age_group: str = Field("below60", pattern="^(below60|60to79|80plus)$")
    sec80c: float = 0
    sec80d: float = 0
    nps_80ccd1b: float = 0
    home_loan_interest: float = 0
    hra_exemption: float = 0
    other_deductions: float = 0


# 19 Loan EMI
class LoanEmiIn(BaseModel):
    principal: float
    annual_rate: float
    tenure_months: int
    prepay_amount: float = 0
    prepay_month: int = 0
    extra_monthly: float = 0


# 20 Budget planner
class BudgetItem(BaseModel):
    category: str
    amount: float
    kind: str = Field(pattern="^(need|want|saving)$")


class BudgetIn(BaseModel):
    income: float
    items: list[BudgetItem]


# 21 Mutual funds
class MfSipIn(BaseModel):
    code: int
    monthly: float
    start: date
    end: Optional[date] = None


# 22 Portfolio tracker
class Holding(BaseModel):
    symbol: str = Field(min_length=1)
    qty: float = Field(gt=0)
    avg_price: float = Field(ge=0)


class TrackerIn(BaseModel):
    holdings: list[Holding] = Field(max_length=50)


# 23 Retirement & FIRE
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


# 25 Accounts, saved data and alerts
class RegisterIn(BaseModel):
    email: str
    password: str
    name: str = ""


class LoginIn(BaseModel):
    email: str
    password: str


class SettingsIn(BaseModel):
    name: Optional[str] = None
    email_alerts: Optional[bool] = None


class DataIn(BaseModel):
    value: object


class AlertIn(BaseModel):
    symbol: str = Field(min_length=1)
    type: str = Field(pattern="^(above|below)$")
    price: float = Field(gt=0)
