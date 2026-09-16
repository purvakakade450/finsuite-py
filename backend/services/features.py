"""Data cleaning, feature engineering, and ML-dataset prep — Day 6 to Day 10."""
import pandas as pd
import numpy as np


def clean(rows: list[dict]) -> dict:
    """Drops rows with a missing Close and duplicate dates. Returns the
    clean rows plus a summary of what was removed (for the UI to show)."""
    df = pd.DataFrame(rows)
    before = len(df)

    missing_mask = df["Close"].isna()
    missing_removed = int(missing_mask.sum())
    df = df[~missing_mask]

    dupe_mask = df.duplicated(subset="Date", keep="first")
    dupes_removed = int(dupe_mask.sum())
    df = df[~dupe_mask]

    df = df.sort_values("Date").reset_index(drop=True)

    return {
        "rows": df.to_dict(orient="records"),
        "before": before,
        "missing_removed": missing_removed,
        "duplicates_removed": dupes_removed,
        "after": len(df),
    }


def _rsi(closes: pd.Series, window: int = 14) -> pd.Series:
    """Classic Wilder RSI: 100 - 100/(1+RS), RS = avg gain / avg loss
    over `window` days, using a simple rolling mean (not the smoothed
    Wilder average — close enough for the app's purposes and easy to
    reason about)."""
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0, 100)          # no losses in window -> RSI 100
    rsi = rsi.where(~((avg_gain == 0) & (avg_loss == 0)), 50)  # flat market -> RSI 50
    return rsi


def engineer_features(rows: list[dict]) -> list[dict]:
    """Adds Daily Return, MA7, MA30, Price Change, 21-day rolling
    Volatility (std-dev of daily return), and 14-day RSI to a cleaned
    OHLCV series."""
    df = pd.DataFrame(rows).sort_values("Date").reset_index(drop=True)
    df["PrevClose"] = df["Close"].shift(1)
    df["DailyReturn"] = (df["Close"] - df["PrevClose"]) / df["PrevClose"]
    df["MA7"] = df["Close"].rolling(window=7).mean()
    df["MA30"] = df["Close"].rolling(window=30).mean()
    df["PriceChange"] = df["Close"] - df["PrevClose"]
    df["Volatility"] = df["DailyReturn"].rolling(window=21).std()
    df["RSI14"] = _rsi(df["Close"], window=14)
    df = df.replace({np.nan: None})
    return df.to_dict(orient="records")


def prepare_ml_dataset(featured_rows: list[dict]) -> dict:
    """Builds the ML-ready table: features = [Close, MA7, MA30,
    DailyReturn, Volatility], target = NEXT day's Close. Drops rows
    without a full feature history or without a next-day target, then
    does a chronological 80/20 train/test split (no shuffling — this is
    a time series, so the model must be tested on data that comes AFTER
    what it trained on)."""
    df = pd.DataFrame(featured_rows).sort_values("Date").reset_index(drop=True)
    df["TargetNextClose"] = df["Close"].shift(-1)

    needed = ["MA30", "Volatility", "DailyReturn", "TargetNextClose"]
    ml_df = df.dropna(subset=needed).reset_index(drop=True)

    split_at = round(len(ml_df) * 0.8)
    train = ml_df.iloc[:split_at]
    test = ml_df.iloc[split_at:]

    cols = ["Date", "Close", "MA7", "MA30", "DailyReturn", "Volatility", "TargetNextClose"]
    return {
        "rows": ml_df[cols].to_dict(orient="records"),
        "train_count": len(train),
        "test_count": len(test),
        "total": len(ml_df),
    }
