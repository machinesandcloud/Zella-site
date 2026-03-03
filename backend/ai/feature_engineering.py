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
    if features.empty:
        close = df["close"].dropna() if "close" in df else pd.Series(dtype=float)
        last_close = float(close.iloc[-1]) if len(close) > 0 else 0.0
        prev_close = float(close.iloc[-2]) if len(close) > 1 else last_close
        returns = ((last_close - prev_close) / prev_close) if prev_close else 0.0
        vol_series = close.pct_change().rolling(5).std() if len(close) > 0 else pd.Series(dtype=float)
        volatility = float(vol_series.iloc[-1]) if len(vol_series) > 0 and pd.notna(vol_series.iloc[-1]) else 0.0
        vwap_series = vwap(df) if len(df) > 0 else pd.Series(dtype=float)
        vwap_val = float(vwap_series.iloc[-1]) if len(vwap_series) > 0 and pd.notna(vwap_series.iloc[-1]) else last_close
        ema20 = ema(close, 20).iloc[-1] if len(close) > 0 else last_close
        ema50 = ema(close, 50).iloc[-1] if len(close) > 0 else last_close
        rsi14 = rsi(close, 14).iloc[-1] if len(close) > 0 else 50.0
        return {
            "ema_20": float(ema20) if pd.notna(ema20) else last_close,
            "ema_50": float(ema50) if pd.notna(ema50) else last_close,
            "rsi_14": float(rsi14) if pd.notna(rsi14) else 50.0,
            "vwap": float(vwap_val),
            "returns": float(returns),
            "volatility": float(volatility),
        }

    last = features.iloc[-1]
    return {
        "ema_20": float(last["ema_20"]),
        "ema_50": float(last["ema_50"]),
        "rsi_14": float(last["rsi_14"]),
        "vwap": float(last["vwap"]),
        "returns": float(last["returns"]),
        "volatility": float(last["volatility"]),
    }
