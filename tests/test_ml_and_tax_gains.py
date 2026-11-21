"""The price-prediction pipeline (on synthetic prices) and capital gains in the tax calculator."""
import math
import random
from datetime import date, timedelta

import pytest

from app import market, planning, predict


def _history(n=420, seed=1):
    rnd = random.Random(seed)
    rows, price, d = [], 200.0, date(2024, 1, 1)
    for i in range(n):
        while d.weekday() >= 5:
            d += timedelta(days=1)
        price *= 1 + 0.0004 + 0.012 * math.sin(i / 7) * 0.5 + rnd.gauss(0, 0.008)
        rows.append({"Date": d.isoformat(), "Open": price, "High": price * 1.01, "Low": price * 0.99,
                     "Close": round(price, 2), "Volume": 100_000 + rnd.randint(0, 50_000)})
        d += timedelta(days=1)
    return {"yahooSymbol": "SYN.NS", "name": "Synthetic Ltd", "currency": "INR", "rows": rows}


@pytest.fixture()
def synthetic(monkeypatch):
    monkeypatch.setattr(market, "get_history", lambda symbol, period="2y": _history())


def test_prediction_has_four_models_and_a_baseline(synthetic):
    d = predict.predict_next_close("SYN.NS")
    keys = [m["key"] for m in d["models"]]
    assert keys == ["linear", "ridge", "random_forest", "gradient_boosting"]
    assert set(d["metrics"]) == set(keys) | {"naive"}
    n = len(d["test"]["actual"])
    for k in keys + ["naive"]:
        assert len(d["test"][k]) == n
        assert d["metrics"][k]["mae"] >= 0
    assert d["best_model"] in keys
    assert d["beats_baseline"] == (d["metrics"][d["best_model"]]["mae"] < d["metrics"]["naive"]["mae"])


def test_forecast_is_a_sensible_price_for_every_model(synthetic):
    d = predict.predict_next_close("SYN.NS")
    last = d["forecast"]["last_close"]
    for m in d["models"]:
        p = d["forecast"][m["key"]]
        assert 0.7 * last < p < 1.3 * last, (m["key"], p, last)
        assert d["forecast"][m["key"] + "_change_pct"] == pytest.approx((p - last) / last * 100, abs=0.01)


def test_walk_forward_summary(synthetic):
    wf = predict.predict_next_close("SYN.NS")["walk_forward"]
    assert wf["folds"] == 5 and wf["days_per_fold"] >= 5 and wf["naive_mae"] > 0
    for stats in wf["models"].values():
        assert 0 <= stats["folds_beating_naive"] <= wf["folds"]
        assert 0 <= stats["direction_accuracy"] <= 100


def test_prediction_is_repeatable(synthetic):
    a, b = predict.predict_next_close("SYN.NS"), predict.predict_next_close("SYN.NS")
    assert a["forecast"] == b["forecast"] and a["metrics"] == b["metrics"]


def test_new_input_columns_are_used(synthetic):
    d = predict.predict_next_close("SYN.NS")
    assert {"RSI14", "Ret5", "VolRatio"} <= set(d["features"])
    assert set(d["feature_importances"]) == set(d["features"])


def test_too_little_history_is_a_clear_error(monkeypatch):
    short = _history(60)
    monkeypatch.setattr(market, "get_history", lambda s, p="2y": short)
    with pytest.raises(ValueError, match="at least"):
        predict.predict_next_close("SYN.NS")


def test_index_without_volume_still_works(monkeypatch):
    h = _history()
    for r in h["rows"]:
        r["Volume"] = 0
    monkeypatch.setattr(market, "get_history", lambda s, p="2y": h)
    assert predict.predict_next_close("^SYN")["models"]


# ------------------------------------------------------------- capital gains
def test_gains_are_taxed_on_top_in_both_regimes():
    base = planning.calc_income_tax(1_500_000)
    r = planning.calc_income_tax(1_500_000, stcg_equity=100_000, ltcg_equity=325_000)
    # short term 20% of 1 L = 20,000; long term 12.5% of (3.25 L - 1.25 L) = 25,000; plus 4% cess
    assert r["new"]["capital_gains"]["total"] == pytest.approx(46_800)
    assert r["new"]["total_tax"] == pytest.approx(base["new"]["total_tax"] + 46_800)
    assert r["old"]["total_tax"] == pytest.approx(base["old"]["total_tax"] + 46_800)
    assert "Share-market gains" in r["insight"]


def test_long_term_gains_up_to_1_25_lakh_are_tax_free():
    assert planning.calc_income_tax(1_500_000, ltcg_equity=125_000)["new"]["capital_gains"]["total"] == 0


def test_low_income_shields_gains_up_to_the_basic_limit():
    # normal income 3 L is 1 L below the new-regime limit of 4 L, so 1 L of short-term gains is tax free
    r = planning.calc_income_tax(300_000, stcg_equity=100_000)
    assert r["new"]["capital_gains"]["total"] == 0


def test_negative_gains_are_rejected():
    with pytest.raises(ValueError):
        planning.calc_income_tax(1_000_000, stcg_equity=-5)


def test_gains_over_the_api(client):
    r = client.post("/tax/income", json={"gross_income": 1_500_000, "stcg_equity": 100_000, "ltcg_equity": 325_000}).json()
    assert round(r["new"]["total_tax"]) == 144_300
    assert client.post("/tax/income", json={"gross_income": 1, "stcg_equity": -1}).status_code == 422
