import pandas as pd

from ai.screener import MarketScreener
from ai.ml_model import MLSignalModel


def test_screener_scores_symbol():
    df = pd.DataFrame(
        {
            "close": list(range(100, 130)),
            "open": list(range(99, 129)),
            "high": list(range(101, 131)),
            "low": list(range(98, 128)),
            "volume": [1_000_000] * 30,
        }
    )
    model = MLSignalModel()
    model.model = None
    screener = MarketScreener(model, min_avg_volume=1000, min_price=1, max_price=1000, min_volatility=0)
    scored = screener.score_symbol("AAPL", df)
    assert scored is not None
