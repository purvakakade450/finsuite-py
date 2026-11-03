"""
Portfolio tracker: value a list of holdings at live prices and work out
profit or loss. Holdings in other currencies (e.g. US stocks) are converted
to rupees with the live exchange rate so the totals add up.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from . import market


def _quote(symbol: str):
    try:
        return market.get_quote(symbol), None
    except Exception as e:          # one bad symbol must not break the whole portfolio
        return None, str(e)


def value_holdings(holdings: list[dict], base: str = "INR") -> dict:
    if not holdings:
        raise ValueError("add at least one holding")
    with ThreadPoolExecutor(max_workers=6) as pool:
        quotes = list(pool.map(lambda h: _quote(h["symbol"]), holdings))

    fx_cache: dict[str, float | None] = {base: 1.0}

    def fx(cur: str):
        if cur not in fx_cache:
            try:
                fx_cache[cur] = market.get_fx_rate(cur, base)["rate"]
            except Exception:
                fx_cache[cur] = None
        return fx_cache[cur]

    rows, invested, value, day_change = [], 0.0, 0.0, 0.0
    for h, (q, err) in zip(holdings, quotes):
        row = {"symbol": h["symbol"], "qty": h["qty"], "avg_price": h["avg_price"], "error": err}
        if q:
            rate = fx(q["currency"])
            cost, now = h["qty"] * h["avg_price"], h["qty"] * q["price"]
            row.update(name=q["name"], yahooSymbol=q["yahooSymbol"], currency=q["currency"], price=q["price"],
                       invested=cost, value=now, pnl=now - cost, pnl_pct=(now - cost) / cost * 100 if cost else None,
                       day_change=h["qty"] * (q["change"] or 0), day_change_pct=q["changePercent"], fx_rate=rate)
            if rate is not None:
                row["value_base"] = now * rate
                invested += cost * rate
                value += now * rate
                day_change += row["day_change"] * rate
            else:
                row["error"] = f"No {q['currency']}→{base} exchange rate available, left out of totals."
        rows.append(row)

    for r in rows:
        r["weight_pct"] = r["value_base"] / value * 100 if value and "value_base" in r else None
    pnl = value - invested
    priced = [r for r in rows if r.get("pnl_pct") is not None]
    best = max(priced, key=lambda r: r["pnl_pct"], default=None)
    worst = min(priced, key=lambda r: r["pnl_pct"], default=None)
    insight = (f"Your portfolio is worth {base} {value:,.0f} against {invested:,.0f} invested, "
               f"a {'profit' if pnl >= 0 else 'loss'} of {abs(pnl):,.0f} ({pnl / invested * 100 if invested else 0:+.2f}%).")
    if best and worst and best is not worst:
        insight += (f" Best performer: {best['name']} ({best['pnl_pct']:+.1f}%). "
                    f"Weakest: {worst['name']} ({worst['pnl_pct']:+.1f}%).")
    top = max((r for r in rows if r.get("weight_pct")), key=lambda r: r["weight_pct"], default=None)
    if top and top["weight_pct"] > 40 and len(rows) > 1:
        insight += f" {top['name']} is {top['weight_pct']:.0f}% of the portfolio; spreading money out lowers risk."
    return {"base": base, "rows": rows, "invested": invested, "value": value, "pnl": pnl,
            "pnl_pct": pnl / invested * 100 if invested else 0.0, "day_change": day_change, "insight": insight}
