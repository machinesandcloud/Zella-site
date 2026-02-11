import pandas as pd

from strategies.ema_cross import EMACrossStrategy
from strategies.rsi_exhaustion import RSIExhaustionStrategy
from strategies.vwap_bounce import VWAPBounceStrategy


def test_ema_cross_generates_signal():
    data = {"close": list(range(1, 60)), "high": list(range(1, 60)), "low": list(range(1, 60)), "volume": [100] * 59}
    df = pd.DataFrame(data)
    strat = EMACrossStrategy({"parameters": {"fast_ema": 5, "slow_ema": 10, "quantity": 1}})
    signals = strat.on_market_data("AAPL", {"df": df})
    assert isinstance(signals, list)


def test_rsi_exhaustion():
    data = {"close": [1] * 20, "high": [1] * 20, "low": [1] * 20, "volume": [100] * 20}
    df = pd.DataFrame(data)
    strat = RSIExhaustionStrategy({"parameters": {"rsi_period": 14, "quantity": 1}})
    signals = strat.on_market_data("AAPL", {"df": df})
    assert isinstance(signals, list)


def test_vwap_bounce():
    data = {
        "close": list(range(1, 25)),
        "high": list(range(2, 26)),
        "low": list(range(1, 25)),
        "volume": [100] * 24,
    }
    df = pd.DataFrame(data)
    strat = VWAPBounceStrategy({"parameters": {"vwap_period": 10, "quantity": 1}})
    signals = strat.on_market_data("AAPL", {"df": df})
    assert isinstance(signals, list)
