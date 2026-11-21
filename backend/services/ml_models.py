"""Next-day close models (scikit-learn): Linear Regression, Ridge Regression,
Random Forest and Gradient Boosting, plus a walk-forward test.

Every model is judged against the naive guess "tomorrow = today". Tree models
cannot predict prices outside the range they trained on, so they learn the
next-day CHANGE from today's close and that change is added back; the linear
models predict the next close directly.
"""
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ["Close", "MA7", "MA30", "DailyReturn", "Volatility", "RSI14", "Ret5", "VolRatio"]

MODEL_ORDER = ["linear", "ridge", "random_forest", "gradient_boosting"]
LABELS = {"linear": "Linear Regression", "ridge": "Ridge Regression",
          "random_forest": "Random Forest", "gradient_boosting": "Gradient Boosting"}


def _make(key: str, n_estimators: int):
    if key == "linear":
        return make_pipeline(StandardScaler(), LinearRegression()), "level"
    if key == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=10.0)), "level"
    if key == "random_forest":
        return RandomForestRegressor(n_estimators=n_estimators, max_depth=8, random_state=42, n_jobs=-1), "change"
    if key == "gradient_boosting":
        return GradientBoostingRegressor(n_estimators=max(n_estimators * 3 // 4, 40), learning_rate=0.05, max_depth=3,
                                         subsample=0.8, random_state=42), "change"
    raise KeyError(key)


def _to_xy(rows: list[dict]):
    X = np.array([[r[f] for f in FEATURES] for r in rows], dtype=float)
    y = np.array([r["TargetNextClose"] for r in rows], dtype=float)
    return X, y


def fit(key: str, X: np.ndarray, y: np.ndarray, n_estimators: int = 200):
    """Train one model. Returns (predict(X_new) -> prices, fitted estimator)."""
    model, mode = _make(key, n_estimators)
    model.fit(X, y - X[:, 0] if mode == "change" else y)
    if mode == "change":
        return (lambda X_new: X_new[:, 0] + model.predict(X_new)), model
    return model.predict, model


def evaluate_all(train_rows: list[dict], test_rows: list[dict], n_estimators: int = 200) -> dict:
    """Train every model on the training rows and predict the test rows."""
    X_train, y_train = _to_xy(train_rows)
    X_test, y_test = _to_xy(test_rows)
    preds, importances = {}, {}
    for key in MODEL_ORDER:
        predict, model = fit(key, X_train, y_train, n_estimators)
        preds[key] = [round(float(p), 2) for p in predict(X_test)]
        if key == "random_forest":
            importances = dict(zip(FEATURES, [round(float(i), 4) for i in model.feature_importances_]))
    return {"predictions": preds, "actual": [round(float(a), 2) for a in y_test],
            "today": [float(r["Close"]) for r in test_rows], "dates": [r["Date"] for r in test_rows],
            "feature_importances": importances}


def forecast_next_close(ml_rows: list[dict], latest_features: dict, n_estimators: int = 200) -> dict:
    """Fit every model on ALL labelled rows and predict the close after `latest_features`
    (the most recent trading day, which has no next-day label yet)."""
    X, y = _to_xy(ml_rows)
    x_new = np.array([[latest_features[f] for f in FEATURES]], dtype=float)
    return {key: round(float(fit(key, X, y, n_estimators)[0](x_new)[0]), 2) for key in MODEL_ORDER}


def direction_accuracy(today: list[float], actual: list[float], predicted: list[float]) -> float:
    """Share of days on which the model called the direction (up or down) of the next close right."""
    pairs = [(a - t, p - t) for t, a, p in zip(today, actual, predicted) if a != t]
    if not pairs:
        return 0.0
    return round(sum((da > 0) == (dp > 0) for da, dp in pairs) / len(pairs) * 100, 1)


def walk_forward(ml_rows: list[dict], folds: int = 5, n_estimators: int = 80) -> dict | None:
    """Expanding-window test: train on everything before a cut-off, test on the next block of days,
    then move the cut-off forward. Shows whether a model is consistently better than the naive guess
    or just lucky on one stretch. Returns None when there is too little data."""
    n = len(ml_rows)
    start = int(n * 0.5)
    block = (n - start) // folds
    if start < 40 or block < 5:
        return None
    maes = {k: [] for k in MODEL_ORDER + ["naive"]}
    hits = {k: [0, 0] for k in MODEL_ORDER}
    for f in range(folds):
        cut = start + f * block
        end = n if f == folds - 1 else cut + block
        train, test = ml_rows[:cut], ml_rows[cut:end]
        res = evaluate_all(train, test, n_estimators)
        actual = np.array(res["actual"])
        maes["naive"].append(float(np.mean(np.abs(actual - np.array(res["today"])))))
        for key in MODEL_ORDER:
            maes[key].append(float(np.mean(np.abs(actual - np.array(res["predictions"][key])))))
            d = direction_accuracy(res["today"], res["actual"], res["predictions"][key])
            hits[key][0] += d * len(actual)
            hits[key][1] += len(actual)
    out = {"folds": folds, "days_per_fold": block, "naive_mae": round(float(np.mean(maes["naive"])), 2), "models": {}}
    for key in MODEL_ORDER:
        out["models"][key] = {
            "mae": round(float(np.mean(maes[key])), 2),
            "folds_beating_naive": sum(m < nv for m, nv in zip(maes[key], maes["naive"])),
            "direction_accuracy": round(hits[key][0] / hits[key][1], 1) if hits[key][1] else None,
        }
    return out
