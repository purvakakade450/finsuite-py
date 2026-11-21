"""ML next-day close prediction for any symbol Yahoo Finance lists.

Pipeline (backend/services): clean -> technical features -> chronological
80/20 split -> four scikit-learn models (Linear, Ridge, Random Forest,
Gradient Boosting) -> a walk-forward test over several stretches of history.
Each model is judged against the naive "tomorrow = today" baseline, so the
user can see whether it adds anything.
"""
from __future__ import annotations

from . import market

MIN_ROWS = 120


def _errors(actual: list[float], pred: list[float]) -> dict:
    n = len(actual)
    abs_err = [abs(a - p) for a, p in zip(actual, pred)]
    mae = sum(abs_err) / n
    rmse = (sum((a - p) ** 2 for a, p in zip(actual, pred)) / n) ** 0.5
    mape = sum(e / a for e, a in zip(abs_err, actual) if a) / n * 100
    return {"mae": round(mae, 2), "rmse": round(rmse, 2), "mape": round(mape, 2)}


def predict_next_close(symbol: str, period: str = "2y") -> dict:
    from backend.services import features, ml_models   # lazy: keeps app start-up light

    hist = market.get_history(symbol, period)
    rows = hist["rows"]
    if len(rows) < MIN_ROWS:
        raise ValueError(f"Only {len(rows)} trading days of history for {symbol}; need at least {MIN_ROWS} "
                         "to train the models. Choose a longer period or a longer-listed stock.")

    cleaned = features.clean(rows)
    featured = features.engineer_features(cleaned["rows"])
    ds = features.prepare_ml_dataset(featured)
    ml_rows = ds["rows"]
    train, test = ml_rows[: ds["train_count"]], ml_rows[ds["train_count"]:]
    if len(train) < 30 or len(test) < 10:
        raise ValueError("Not enough usable history after computing indicators; choose a longer period.")

    res = ml_models.evaluate_all(train, test)
    actual = res["actual"]
    naive = [round(t, 2) for t in res["today"]]                   # "tomorrow = today"

    latest = featured[-1]
    if any(latest.get(f) is None for f in ml_models.FEATURES):
        raise ValueError("Latest day has incomplete indicators; try a longer period.")
    nxt = ml_models.forecast_next_close(ml_rows, latest)
    last_close = float(latest["Close"])

    def move(p): return round((p - last_close) / last_close * 100, 2)

    metrics = {"naive": _errors(actual, naive)}
    metrics.update({k: _errors(actual, res["predictions"][k]) for k in ml_models.MODEL_ORDER})
    best = min(ml_models.MODEL_ORDER, key=lambda k: metrics[k]["mae"])
    beats = metrics[best]["mae"] < metrics["naive"]["mae"]

    forecast = {"last_date": latest["Date"], "last_close": round(last_close, 2)}
    for k in ml_models.MODEL_ORDER:
        forecast[k] = nxt[k]
        forecast[f"{k}_change_pct"] = move(nxt[k])

    return {
        "symbol": symbol,
        "yahooSymbol": hist["yahooSymbol"],
        "name": hist["name"],
        "currency": hist["currency"],
        "period": period,
        "data": {"days": len(rows), "usable": ds["total"], "train": ds["train_count"], "test": ds["test_count"],
                 "duplicates_removed": cleaned["duplicates_removed"], "missing_removed": cleaned["missing_removed"]},
        "models": [{"key": k, "label": ml_models.LABELS[k]} for k in ml_models.MODEL_ORDER],
        "features": ml_models.FEATURES,
        "metrics": metrics,
        "direction_accuracy": {k: ml_models.direction_accuracy(res["today"], actual, res["predictions"][k])
                               for k in ml_models.MODEL_ORDER},
        "best_model": best,
        "beats_baseline": beats,
        "walk_forward": ml_models.walk_forward(ml_rows),
        "test": {"dates": res["dates"], "actual": actual, "naive": naive, **res["predictions"]},
        "forecast": forecast,
        "feature_importances": res["feature_importances"],
    }
