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
    score: float
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