"""Generates realistic-looking (but fake) daily OHLCV data for practice,
and deliberately plants a few missing values / duplicate rows so the
cleaning step has something real to fix."""
import random
from datetime import date, timedelta

COMPANY_PROFILE = {
    "RELIANCE.NS": {"name": "Reliance Industries", "base": 2800, "drift": 0.0004, "vol": 0.018, "volume_base": 6_200_000},
    "TCS.NS":      {"name": "Tata Consultancy Services", "base": 3800, "drift": 0.0003, "vol": 0.014, "volume_base": 2_100_000},
    "INFY.NS":     {"name": "Infosys", "base": 1700, "drift": 0.00035, "vol": 0.016, "volume_base": 5_400_000},
}


def _trading_days(years: float) -> list[date]:
    n_days_needed = round(years * 252)
    dates = []
    cursor = date.today() - timedelta(days=round(years * 365))
    while len(dates) < n_days_needed:
        cursor += timedelta(days=1)
        if cursor.weekday() < 5:  # Mon-Fri
            dates.append(cursor)
    return dates


def generate_series(ticker: str, years: float = 3) -> list[dict]:
    if ticker not in COMPANY_PROFILE:
        raise ValueError(f"Unknown ticker '{ticker}'. Choose one of {list(COMPANY_PROFILE)}.")
    profile = COMPANY_PROFILE[ticker]
    rows = []
    prev_close = profile["base"]
    for d in _trading_days(years):
        ret = (profile["drift"] - 0.5 * profile["vol"] ** 2) + profile["vol"] * random.gauss(0, 1)
        close = round(prev_close * pow(2.718281828, ret), 2)
        open_ = round(prev_close * (1 + (random.random() - 0.5) * 0.006), 2)
        high = round(max(open_, close) * (1 + random.random() * 0.008), 2)
        low = round(min(open_, close) * (1 - random.random() * 0.008), 2)
        volume = round(profile["volume_base"] * (0.6 + random.random() * 0.8))
        rows.append({
            "Date": d.isoformat(), "Open": open_, "High": high,
            "Low": low, "Close": close, "Volume": volume,
        })
        prev_close = close
    return rows


def mess_up(rows: list[dict]) -> list[dict]:
    """Returns a copy with a few missing Close values and duplicated rows."""
    messy = [dict(r) for r in rows]

    missing_count = max(4, round(len(messy) * 0.012))
    for _ in range(missing_count):
        messy[random.randrange(len(messy))]["Close"] = None

    dupe_count = max(2, round(len(messy) * 0.006))
    for _ in range(dupe_count):
        idx = random.randrange(len(messy))
        messy.insert(idx, dict(messy[idx]))

    return messy