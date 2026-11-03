"""
Mutual fund NAVs and SIP returns, no API key needed.

  * Latest NAV of every scheme -> AMFI's public NAVAll.txt (published daily
    by the Association of Mutual Funds in India)
  * Full NAV history of a scheme -> api.mfapi.in, a free mirror of AMFI's
    historical NAV data
"""
from __future__ import annotations

from datetime import date, datetime

import requests

from .market import _cached

AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
HISTORY_URL = "https://api.mfapi.in/mf/{code}"
NAV_TTL = 6 * 60 * 60


def _get(url: str) -> requests.Response:
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    resp.raise_for_status()
    return resp


def _parse_navall(text: str) -> list[dict]:
    funds, category, house = [], "", ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("Scheme Code"):
            continue
        f = line.split(";")
        if len(f) < 6:
            if "Schemes" in line and "(" in line:
                category = line[line.find("(") + 1:line.rfind(")")] or line
            else:
                house = line
            continue
        if not f[0].isdigit():
            continue
        try:
            nav = float(f[-2])
        except ValueError:
            continue
        # Newer files split "Plan" and "Option" into their own columns.
        name = f[3] if len(f) == 6 else " - ".join(p for p in f[3:-2] if p and p != "-")
        funds.append({"code": int(f[0]), "name": name, "nav": nav, "date": f[-1],
                      "category": category, "fund_house": house})
    return funds


def all_funds() -> list[dict]:
    return _cached("amfi:navall", NAV_TTL,
                   lambda: _parse_navall(_get(AMFI_URL).content.decode("utf-8", "replace")))


def search_funds(query: str, limit: int = 15) -> list[dict]:
    words = query.lower().split()
    if not words:
        return []
    hits = [f for f in all_funds() if all(w in f["name"].lower() for w in words)]
    # Direct-plan growth options first: they are what most people track.
    hits.sort(key=lambda f: ("direct" not in f["name"].lower(), "growth" not in f["name"].lower(), len(f["name"])))
    return hits[:limit]


def fund_history(code: int) -> dict:
    def fetch():
        d = _get(HISTORY_URL.format(code=code)).json()
        if not d.get("data"):
            raise ValueError(f"No NAV history found for scheme code {code}.")
        rows = [{"date": datetime.strptime(r["date"], "%d-%m-%Y").date(), "nav": float(r["nav"])}
                for r in d["data"] if float(r["nav"]) > 0]
        rows.sort(key=lambda r: r["date"])
        return {"meta": d.get("meta", {}), "rows": rows}
    return _cached(f"mf:history:{code}", NAV_TTL, fetch)


def _nav_on_or_after(rows: list[dict], day: date, start: int = 0) -> int | None:
    for i in range(start, len(rows)):
        if rows[i]["date"] >= day:
            return i
    return None


def _xirr(flows: list[tuple[date, float]]) -> float | None:
    """Annual return that makes the dated cash flows add up to zero."""
    t0 = flows[0][0]
    def npv(r):
        return sum(v / (1 + r) ** ((d - t0).days / 365) for d, v in flows)
    lo, hi = -0.99, 10.0
    if npv(lo) * npv(hi) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if npv(mid) > 0 else (lo, mid)
    return (lo + hi) / 2 * 100


def _add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    year, month = d.year + y, m + 1
    for day in (d.day, 28):
        try:
            return date(year, month, min(day, 31))
        except ValueError:
            continue
    return date(year, month, 28)


def _point_return(rows: list[dict], years: int) -> float | None:
    last = rows[-1]
    try:
        target = last["date"].replace(year=last["date"].year - years)
    except ValueError:                      # 29 Feb
        target = last["date"].replace(year=last["date"].year - years, day=28)
    if rows[0]["date"] > target:
        return None
    i = _nav_on_or_after(rows, target)
    return ((last["nav"] / rows[i]["nav"]) ** (1 / years) - 1) * 100


def sip_returns(code: int, monthly: float, start: date, end: date | None = None) -> dict:
    if monthly <= 0:
        raise ValueError("monthly amount must be positive")
    h = fund_history(code)
    rows = h["rows"]
    end = min(end or rows[-1]["date"], rows[-1]["date"])
    if start < rows[0]["date"]:
        raise ValueError(f"This fund's NAV history starts on {rows[0]['date']:%d %b %Y}; pick a later start date.")
    if start >= end:
        raise ValueError("start date must be before the end date")

    units, invested, flows, series, idx, n = 0.0, 0.0, [], [], 0, 0
    while True:
        day = _add_months(start, n)
        if day > end:
            break
        idx = _nav_on_or_after(rows, day, idx)
        if idx is None or rows[idx]["date"] > end:
            break
        nav = rows[idx]["nav"]
        units += monthly / nav
        invested += monthly
        flows.append((rows[idx]["date"], -monthly))
        series.append({"date": rows[idx]["date"].isoformat(), "invested": round(invested, 2),
                       "value": round(units * nav, 2), "nav": nav})
        n += 1
    end_i = _nav_on_or_after(rows, end)
    if end_i is None:
        end_i = len(rows) - 1
    end_nav = rows[end_i]["nav"]
    value = units * end_nav
    flows.append((rows[end_i]["date"], value))
    xirr = _xirr(flows) if len(flows) > 1 else None

    first_nav = rows[_nav_on_or_after(rows, start)]["nav"]
    lump_value = invested / first_nav * end_nav
    years = (rows[end_i]["date"] - start).days / 365
    lump_cagr = ((lump_value / invested) ** (1 / years) - 1) * 100 if years > 0 else None

    meta = h["meta"]
    gain = value - invested
    insight = (f"Investing ₹{monthly:,.0f} a month for {n} months (₹{invested:,.0f} in total) would be worth "
               f"₹{value:,.0f} today, a {'gain' if gain >= 0 else 'loss'} of ₹{abs(gain):,.0f}")
    insight += f" ({xirr:.1f}% a year, XIRR)." if xirr is not None else "."
    insight += (f" Putting the same ₹{invested:,.0f} in all at once on the first date would be worth "
                f"₹{lump_value:,.0f}.")
    return {
        "scheme_code": code, "scheme_name": meta.get("scheme_name"), "fund_house": meta.get("fund_house"),
        "category": meta.get("scheme_category"), "installments": n, "invested": invested, "units": units,
        "value": value, "gain": gain, "gain_pct": gain / invested * 100 if invested else 0, "xirr": xirr,
        "latest_nav": end_nav, "nav_date": rows[end_i]["date"].isoformat(),
        "lump_sum_value": lump_value, "lump_sum_cagr": lump_cagr,
        "fund_returns": {f"{y}y": _point_return(rows, y) for y in (1, 3, 5)},
        "series": series, "insight": insight,
    }


def fund_nav_chart(code: int, years: int = 5) -> dict:
    h = fund_history(code)
    rows = h["rows"]
    cutoff = rows[-1]["date"].replace(year=rows[-1]["date"].year - years) if years else rows[0]["date"]
    shown = [r for r in rows if r["date"] >= cutoff]
    step = max(len(shown) // 400, 1)        # keep the chart light
    shown = shown[::step] + ([shown[-1]] if (len(shown) - 1) % step else [])
    return {"meta": h["meta"], "dates": [r["date"].isoformat() for r in shown], "nav": [r["nav"] for r in shown],
            "fund_returns": {f"{y}y": _point_return(rows, y) for y in (1, 3, 5)}}
