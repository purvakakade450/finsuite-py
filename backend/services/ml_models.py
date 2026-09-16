"""Model V1 (Linear Regression) and Model V2 (Random Forest) — Day 13 to 15.
Real scikit-learn models, not a hand-rolled version — this is the one part
of the app where a real Python backend is a genuine upgrade over the
browser-only JavaScript version."""
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error

FEATURES = ["Close", "MA7", "MA30", "DailyReturn", "Volatility"]


def _to_xy(rows: list[dict]):
    X = np.array([[r[f] for f in FEATURES] for r in rows], dtype=float)
    y = np.array([r["TargetNextClose"] for r in rows], dtype=float)
    return X, y


def train_linear_regression(train_rows: list[dict], test_rows: list[dict]) -> dict:
    X_train, y_train = _to_xy(train_rows)
    X_test, y_test = _to_xy(test_rows)

    scaler = StandardScaler().fit(X_train)
    X_train_s, X_test_s = scaler.transform(X_train), scaler.transform(X_test)

    model = LinearRegression().fit(X_train_s, y_train)
    preds = model.predict(X_test_s)

    mae = mean_absolute_error(y_test, preds)
    rmse = mean_squared_error(y_test, preds) ** 0.5

    return {
        "model": "Linear Regression",
        "mae": round(float(mae), 2),
        "rmse": round(float(rmse), 2),
        "coefficients": dict(zip(FEATURES, [round(c, 4) for c in model.coef_])),
        "intercept": round(float(model.intercept_), 4),
        "predictions": [round(float(p), 2) for p in preds],
        "actual": [round(float(a), 2) for a in y_test],
        "dates": [r["Date"] for r in test_rows],
    }


def train_random_forest(train_rows: list[dict], test_rows: list[dict],
                         n_estimators: int = 200, max_depth: int = 8) -> dict:
    X_train, y_train = _to_xy(train_rows)
    X_test, y_test = _to_xy(test_rows)

    model = RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=42,
        n_jobs=-1,
    ).fit(X_train, y_train)
    preds = model.predict(X_test)

    mae = mean_absolute_error(y_test, preds)
    rmse = mean_squared_error(y_test, preds) ** 0.5

    importances = dict(zip(FEATURES, [round(float(i), 4) for i in model.feature_importances_]))

    return {
        "model": "Random Forest",
        "mae": round(float(mae), 2),
        "rmse": round(float(rmse), 2),
        "feature_importances": importances,
        "predictions": [round(float(p), 2) for p in preds],
        "actual": [round(float(a), 2) for a in y_test],
        "dates": [r["Date"] for r in test_rows],
        "n_estimators": n_estimators,
    }