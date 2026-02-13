from typing import Dict, List, Optional, Union

import pandas as pd

from ai.feature_engineering import latest_feature_vector
from ai.ml_model import MLSignalModel


class MarketScreener:
    def __init__(
        self,
        model: MLSignalModel,
        min_avg_volume: float = 500000,
        min_price: float = 5.0,
        max_price: float = 1000.0,
        min_volatility: float = 0.005,
        min_relative_volume: float = 2.0,
    ) -> None:
        self.model = model
        self.min_avg_volume = min_avg_volume
        self.min_price = min_price
        self.max_price = max_price
        self.min_volatility = min_volatility
        self.min_relative_volume = min_relative_volume

    def score_symbol(self, symbol: str, df: pd.DataFrame) -> Optional[Dict[str, Union[float, str]]]:
        features = latest_feature_vector(df)
        last_price = float(df["close"].iloc[-1])
        avg_volume = float(df["volume"].tail(20).mean())
        last_volume = float(df["volume"].iloc[-1])
        relative_volume = last_volume / avg_volume if avg_volume else 0.0
        if avg_volume < self.min_avg_volume:
            return None
        if not (self.min_price <= last_price <= self.max_price):
            return None
        if features["volatility"] < self.min_volatility:
            return None
        if relative_volume < self.min_relative_volume:
            return None
        ml_score = self.model.predict(features)
        momentum_score = float((df["close"].iloc[-1] - df["close"].iloc[-5]) / df["close"].iloc[-5])
        combined = (ml_score * 0.6) + (momentum_score * 0.4)
        return {
            "symbol": symbol,
            "ml_score": ml_score,
            "momentum_score": momentum_score,
            "combined_score": combined,
            "last_price": last_price,
            "avg_volume": avg_volume,
            "relative_volume": relative_volume,
        }

    def rank(self, market_data: Dict[str, pd.DataFrame]) -> List[Dict[str, Union[float, str]]]:
        results: List[Dict[str, Union[float, str]]] = []
        for symbol, df in market_data.items():
            scored = self.score_symbol(symbol, df)
            if scored:
                results.append(scored)
        return sorted(results, key=lambda x: x["combined_score"], reverse=True)
