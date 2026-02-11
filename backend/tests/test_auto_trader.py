from core.auto_trader import AutoTrader
from core.strategy_engine import StrategyEngine
from core.risk_manager import RiskManager, RiskConfig
from core.position_manager import PositionManager
from core.mock_ibkr_client import MockIBKRClient
from market.ibkr_provider import IBKRMarketDataProvider


def test_auto_trader_scan():
    ibkr = MockIBKRClient()
    ibkr.connect_to_ibkr("127.0.0.1", 7497, 1, True)
    provider = IBKRMarketDataProvider(ibkr, universe=["AAPL", "MSFT"], use_scanner=False)
    risk_manager = RiskManager(RiskConfig(10, 500, 5, 2))
    engine = StrategyEngine(ibkr, risk_manager, PositionManager())
    auto_trader = AutoTrader(provider, engine, screener_config={"min_avg_volume": 0, "min_volatility": 0})
    ranked = auto_trader.scan_market()
    assert isinstance(ranked, list)
