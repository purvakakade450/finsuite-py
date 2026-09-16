"""Growth/target planner and portfolio & tax tools — pure calculations,
no network calls, so these always work even with zero API quota left."""
from datetime import date


def growth(invested_amount: float, price_then: float, price_now: float) -> dict:
    units = invested_amount / price_then
    value_now = units * price_now
    gain = value_now - invested_amount
    gain_pct = (gain / invested_amount) * 100
    return {
        "units": round(units, 4),
        "value_now": round(value_now, 2),
        "gain": round(gain, 2),
        "gain_percent": round(gain_pct, 2),
    }


def target_stop_loss(entry_price: float, target_percent: float, stop_loss_percent: float) -> dict:
    return {
        "target_price": round(entry_price * (1 + target_percent / 100), 2),
        "stop_loss_price": round(entry_price * (1 - stop_loss_percent / 100), 2),
    }


def fifty_two_week_range(daily_closes: list[float]) -> dict:
    if not daily_closes:
        return {"high": None, "low": None}
    return {"high": round(max(daily_closes), 2), "low": round(min(daily_closes), 2)}


def sip_vs_lumpsum(monthly_amount: float, months: int, monthly_prices: list[float]) -> dict:
    """monthly_prices[i] = price on the SIP purchase date of month i (oldest first)."""
    if len(monthly_prices) < months:
        raise ValueError("Not enough price points for the requested number of months.")
    prices = monthly_prices[-months:]

    # SIP: buy a fixed rupee amount every month
    sip_units = sum(monthly_amount / p for p in prices)
    sip_final_value = sip_units * prices[-1]
    sip_invested = monthly_amount * months

    # Lump sum: invest the whole amount on day one at the first price
    lumpsum_units = sip_invested / prices[0]
    lumpsum_final_value = lumpsum_units * prices[-1]

    return {
        "invested": round(sip_invested, 2),
        "sip_final_value": round(sip_final_value, 2),
        "sip_gain_percent": round((sip_final_value - sip_invested) / sip_invested * 100, 2),
        "lumpsum_final_value": round(lumpsum_final_value, 2),
        "lumpsum_gain_percent": round((lumpsum_final_value - sip_invested) / sip_invested * 100, 2),
    }


def capital_gains_tax(buy_price: float, sell_price: float, units: float,
                       buy_date: str, sell_date: str) -> dict:
    """Indian equity capital-gains rules (FY2024-25 onward):
       held > 12 months  -> Long-Term:  12.5% tax on gains above Rs 1.25 lakh/year exemption
       held <= 12 months -> Short-Term: 20% tax on the full gain
       (Simplified — a real filing should account for indexation-free LTCG
       rules, other gains that year, and STT already paid.)"""
    d_buy = date.fromisoformat(buy_date)
    d_sell = date.fromisoformat(sell_date)
    holding_days = (d_sell - d_buy).days
    gain = (sell_price - buy_price) * units

    if holding_days > 365:
        term = "Long-Term (LTCG)"
        taxable_gain = max(0, gain - 125_000)
        tax = taxable_gain * 0.125
    else:
        term = "Short-Term (STCG)"
        taxable_gain = max(0, gain)
        tax = taxable_gain * 0.20

    return {
        "holding_days": holding_days,
        "term": term,
        "gross_gain": round(gain, 2),
        "taxable_gain": round(taxable_gain, 2),
        "estimated_tax": round(tax, 2),
        "net_gain_after_tax": round(gain - tax, 2),
    }


def compare_stocks(entries: list[dict]) -> list[dict]:
    """entries: [{"symbol": ..., "closes": [..]}, ...] -> adds simple
    comparison stats (period return %, volatility %, 52-week range)."""
    import statistics
    results = []
    for e in entries:
        closes = e["closes"]
        if len(closes) < 2:
            continue
        period_return = (closes[-1] - closes[0]) / closes[0] * 100
        daily_returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))]
        vol = statistics.pstdev(daily_returns) * 100 if len(daily_returns) > 1 else 0
        results.append({
            "symbol": e["symbol"],
            "period_return_percent": round(period_return, 2),
            "volatility_percent": round(vol, 3),
            "high_52w": round(max(closes), 2),
            "low_52w": round(min(closes), 2),
        })
    return results