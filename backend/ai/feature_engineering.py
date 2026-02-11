from typing import Dict

import pandas as pd

from utils.indicators import ema, rsi, vwap


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ema_20"] = ema(df["close"], 20)
    df["ema_50"] = ema(df["close"], 50)
    df["rsi_14"] = rsi(df["close"], 14)
    df["vwap"] = vwap(df)
    df["returns"] = df["close"].pct_change()
    df["volatility"] = df["returns"].rolling(20).std()
    df = df.dropna()
    return df


def latest_feature_vector(df: pd.DataFrame) -> Dict[str, float]:
    features = build_features(df)
    last = features.iloc[-1]
    return {
        "ema_20": float(last["ema_20"]),
        "ema_50": float(last["ema_50"]),
        "rsi_14": float(last["rsi_14"]),
        "vwap": float(last["vwap"]),
        "returns": float(last["returns"]),
        "volatility": float(last["volatility"]),
    }
