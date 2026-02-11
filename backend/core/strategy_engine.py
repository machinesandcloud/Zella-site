import logging
from typing import Any, Dict, List, Optional

from core.ibkr_client import IBKRClient
from core.position_manager import PositionManager
from core.risk_manager import RiskManager
from core.signals import Signal
from strategies.base_strategy import BaseStrategy
from strategies.ema_cross import EMACrossStrategy
from strategies.vwap_bounce import VWAPBounceStrategy
from strategies.rsi_exhaustion import RSIExhaustionStrategy
from strategies.orb_strategy import ORBStrategy
from strategies.trend_follow import TrendFollowStrategy
from strategies.range_trading import RangeTradingStrategy
from strategies.momentum import MomentumStrategy
from strategies.breakout import BreakoutStrategy
from strategies.pullback import PullbackStrategy
from strategies.scalping import ScalpingStrategy
from strategies.htf_ema_momentum import HTFEMAMomentumStrategy
from strategies.first_hour_trend import FirstHourTrendStrategy
from strategies.broken_parabolic_short import BrokenParabolicShortStrategy
from strategies.fake_halt_trap import FakeHaltTrapStrategy
from strategies.rsi_extreme_reversal import RSIExtremeReversalStrategy
from strategies.stop_hunt_reversal import StopHuntReversalStrategy
from strategies.market_maker_refill import MarketMakerRefillStrategy
from strategies.dark_pool_footprints import DarkPoolFootprintsStrategy
from strategies.rip_and_dip import RipAndDipStrategy
from strategies.big_bid_scalp import BigBidScalpStrategy
from strategies.options_chain_spoof import OptionsChainSpoofStrategy
from strategies.fomc_fade import FOMCFadeStrategy
from strategies.earnings_overreaction import EarningsOverreactionStrategy
from strategies.merger_arb import MergerArbStrategy
from strategies.bagholder_bounce import BagholderBounceStrategy
from strategies.retail_fakeout import RetailFakeoutStrategy
from strategies.nine_forty_five_reversal import NineFortyFiveReversalStrategy
from strategies.gamma_squeeze import GammaSqueezeStrategy
from strategies.max_pain_fade import MaxPainFadeStrategy
from strategies.open_interest_fakeout import OpenInterestFakeoutStrategy
from strategies.premarket_vwap_reclaim import PremarketVWAPReclaimStrategy
from strategies.after_hours_liquidity_trap import AfterHoursLiquidityTrapStrategy
from strategies.closing_bell_liquidity_grab import ClosingBellLiquidityGrabStrategy


STRATEGY_REGISTRY = {
    "ema_cross": EMACrossStrategy,
    "vwap_bounce": VWAPBounceStrategy,
    "rsi_exhaustion": RSIExhaustionStrategy,
    "orb_strategy": ORBStrategy,
    "trend_follow": TrendFollowStrategy,
    "range_trading": RangeTradingStrategy,
    "momentum": MomentumStrategy,
    "breakout": BreakoutStrategy,
    "pullback": PullbackStrategy,
    "scalping": ScalpingStrategy,
    "htf_ema_momentum": HTFEMAMomentumStrategy,
    "first_hour_trend": FirstHourTrendStrategy,
    "broken_parabolic_short": BrokenParabolicShortStrategy,
    "fake_halt_trap": FakeHaltTrapStrategy,
    "rsi_extreme_reversal": RSIExtremeReversalStrategy,
    "stop_hunt_reversal": StopHuntReversalStrategy,
    "market_maker_refill": MarketMakerRefillStrategy,
    "dark_pool_footprints": DarkPoolFootprintsStrategy,
    "rip_and_dip": RipAndDipStrategy,
    "big_bid_scalp": BigBidScalpStrategy,
    "options_chain_spoof": OptionsChainSpoofStrategy,
    "fomc_fade": FOMCFadeStrategy,
    "earnings_overreaction": EarningsOverreactionStrategy,
    "merger_arb": MergerArbStrategy,
    "bagholder_bounce": BagholderBounceStrategy,
    "retail_fakeout": RetailFakeoutStrategy,
    "nine_forty_five_reversal": NineFortyFiveReversalStrategy,
    "gamma_squeeze": GammaSqueezeStrategy,
    "max_pain_fade": MaxPainFadeStrategy,
    "open_interest_fakeout": OpenInterestFakeoutStrategy,
    "premarket_vwap_reclaim": PremarketVWAPReclaimStrategy,
    "after_hours_liquidity_trap": AfterHoursLiquidityTrapStrategy,
    "closing_bell_liquidity_grab": ClosingBellLiquidityGrabStrategy,
}


class StrategyEngine:
    def __init__(
        self,
        ibkr_client: IBKRClient,
        risk_manager: RiskManager,
        position_manager: PositionManager,
    ) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.ibkr_client = ibkr_client
        self.risk_manager = risk_manager
        self.position_manager = position_manager
        self.active_strategies: Dict[str, BaseStrategy] = {}

    # Strategy lifecycle
    def load_strategy(self, strategy_name: str, config: Dict[str, Any]) -> BaseStrategy:
        if strategy_name not in STRATEGY_REGISTRY:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        strategy_class = STRATEGY_REGISTRY[strategy_name]
        strategy = strategy_class(config)
        return strategy

    def start_strategy(self, strategy_id: str, strategy_name: str, config: Dict[str, Any]) -> None:
        strategy = self.load_strategy(strategy_name, config)
        self.active_strategies[strategy_id] = strategy
        self.logger.info("Started strategy %s (%s)", strategy_id, strategy_name)

    def stop_strategy(self, strategy_id: str) -> None:
        if strategy_id in self.active_strategies:
            self.active_strategies.pop(strategy_id)
            self.logger.info("Stopped strategy %s", strategy_id)

    def get_active_strategies(self) -> List[str]:
        return list(self.active_strategies.keys())

    # Signal processing
    def process_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        signals: List[Signal] = []
        for strategy in self.active_strategies.values():
            strategy_signals = strategy.on_market_data(symbol, data)
            signals.extend(strategy_signals)
        return signals

    def generate_signals(self) -> List[Signal]:
        # Placeholder for scheduled signal generation
        return []

    def validate_signal(self, signal: Signal, account_value: float, buying_power: float, price: float) -> bool:
        if not self.risk_manager.check_daily_loss_limit():
            return False
        if not self.risk_manager.check_max_positions():
            return False
        if not self.risk_manager.check_buying_power(signal.quantity * price, buying_power):
            return False
        if not self.risk_manager.check_position_size_limit(signal.symbol, signal.quantity, price, account_value):
            return False
        return True

    # Execution
    def execute_signal(self, signal: Signal) -> Optional[int]:
        self.logger.info("Executing signal: %s", signal)
        if signal.order_type == "MKT":
            return self.ibkr_client.place_market_order(signal.symbol, signal.quantity, signal.action)
        if signal.order_type == "LMT":
            if signal.limit_price is None:
                raise ValueError("limit_price required for limit order")
            return self.ibkr_client.place_limit_order(
                signal.symbol, signal.quantity, signal.action, signal.limit_price
            )
        if signal.order_type == "STP":
            if signal.stop_price is None:
                raise ValueError("stop_price required for stop order")
            return self.ibkr_client.place_stop_order(
                signal.symbol, signal.quantity, signal.action, signal.stop_price
            )
        if signal.order_type == "BRACKET":
            if signal.take_profit is None or signal.stop_loss is None:
                raise ValueError("take_profit and stop_loss required for bracket order")
            self.ibkr_client.place_bracket_order(
                signal.symbol,
                signal.quantity,
                signal.action,
                signal.take_profit,
                signal.stop_loss,
            )
            return None
        raise ValueError("Unsupported order type")

    def manage_active_positions(self) -> None:
        # Placeholder for position updates
        return None

    def update_stop_loss_take_profit(self) -> None:
        # Placeholder for SL/TP management
        return None

    # Monitoring
    def get_strategy_performance(self, strategy_id: str) -> Dict[str, Any]:
        if strategy_id not in self.active_strategies:
            return {}
        return self.active_strategies[strategy_id].get_performance()

    def get_strategy_logs(self, strategy_id: str) -> List[str]:
        if strategy_id not in self.active_strategies:
            return []
        return self.active_strategies[strategy_id].get_logs()
