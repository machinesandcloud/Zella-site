from typing import Dict

import joblib
import numpy as np


class MLSignalModel:
    def __init__(self, model_path: str = "backend/ai/model.joblib") -> None:
        self.model_path = model_path
        self.model = None

    def load(self) -> None:
        try:
            self.model = joblib.load(self.model_path)
        except FileNotFoundError:
            self.model = None

    def predict(self, features: Dict[str, float]) -> float:
        if self.model is None:
            return 0.0
        X = np.array([[
            features["ema_20"],
            features["ema_50"],
            features["rsi_14"],
            features["vwap"],
            features["returns"],
            features["volatility"],
        ]])
        return float(self.model.predict_proba(X)[0][1])
