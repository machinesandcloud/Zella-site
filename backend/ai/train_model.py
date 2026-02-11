import glob
from typing import List

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from ai.feature_engineering import build_features


def load_csvs(pattern: str = "backend/data/*.csv") -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    for path in glob.glob(pattern):
        df = pd.read_csv(path)
        frames.append(df)
    if not frames:
        raise FileNotFoundError("No CSV files found in backend/data")
    return pd.concat(frames, ignore_index=True)


def build_labels(df: pd.DataFrame) -> pd.Series:
    future_return = df["close"].pct_change().shift(-1)
    return (future_return > 0).astype(int)


def main() -> None:
    df = load_csvs()
    features = build_features(df)
    labels = build_labels(df).loc[features.index]

    X = features[["ema_20", "ema_50", "rsi_14", "vwap", "returns", "volatility"]]
    y = labels

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=500)),
        ]
    )
    pipeline.fit(X_train, y_train)

    score = pipeline.score(X_test, y_test)
    print(f"Model accuracy: {score:.3f}")
    joblib.dump(pipeline, "backend/ai/model.joblib")


if __name__ == "__main__":
    main()
