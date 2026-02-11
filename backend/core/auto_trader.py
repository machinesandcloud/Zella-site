from typing import Dict, List, Optional, Union

import pandas as pd

from ai.ml_model import MLSignalModel
from ai.screener import MarketScreener
from core.strategy_engine import StrategyEngine
from market.market_data_provider import MarketDataProvider


class AutoTrader:
    def __init__(
        self,
        data_provider: MarketDataProvider,
        strategy_engine: StrategyEngine,
        screener_config: Optional[Dict[str, float]] = None,
    ) -> None:
        self.data_provider = data_provider
        self.strategy_engine = strategy_engine
        self.model = MLSignalModel()
        self.model.load()
        screener_config = screener_config or {}
        self.screener = MarketScreener(self.model, **screener_config)

    def scan_market(self) -> List[Dict[str, Union[float, str]]]:
        market_data: Dict[str, pd.DataFrame] = {}
        for symbol in self.data_provider.get_universe():
            bars = self.data_provider.get_historical_bars(symbol, "1 D", "5 mins")
            if not bars:
                continue
            df = pd.DataFrame(bars)
            market_data[symbol] = df
        return self.screener.rank(market_data)

    def select_top(self, top_n: int = 5) -> List[Dict[str, Union[float, str]]]:
        ranked = self.scan_market()
        return ranked[:top_n]
