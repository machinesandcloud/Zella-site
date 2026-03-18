"""
Fully Autonomous Trading Engine for Zella AI
Continuously scans, analyzes, and trades using all available strategies

CRITICAL: Thread-safe context tracking for parallel trade management
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time
from typing import Any, Dict, List, Optional, Set, Tuple
from threading import Lock, RLock
from dataclasses import dataclass, field
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class TradeContext:
    """Immutable snapshot of context when a trade was initiated - NEVER LOSE THIS"""
    symbol: str
    strategy_name: str
    entry_time: datetime
    entry_price: float
    quantity: int
    confidence: float
    setup_grade: str
    trade_id: Optional[int] = None
    # Market state at entry
    spy_price: float = 0.0
    vwap: float = 0.0
    atr: float = 0.0
    # Account state at entry
    daily_pnl_at_entry: float = 0.0
    buying_power_at_entry: float = 0.0
    other_positions: List[str] = field(default_factory=list)
    # Strategy signals that triggered this trade
    signals_used: List[str] = field(default_factory=list)


@dataclass
class SymbolState:
    """Per-symbol state to prevent context leakage between parallel trades"""
    symbol: str
    last_signal: Optional[str] = None
    last_signal_time: Optional[datetime] = None
    current_position: Optional[TradeContext] = None
    pending_scale_outs: List[Dict] = field(default_factory=list)
    bars_cache: Optional[pd.DataFrame] = None
    bars_cache_time: Optional[datetime] = None
    last_seen: Optional[datetime] = None

from core.strategy_engine import StrategyEngine
from core.risk_manager import RiskManager
from core.position_manager import PositionManager
from market.market_data_provider import MarketDataProvider
from market.short_interest_provider import ShortInterestProvider
from ai.screener import MarketScreener
from ai.ml_model import MLSignalModel
from config.settings import settings
from strategies import (
    BreakoutStrategy,
    EMACrossStrategy,
    HTFEMAMomentumStrategy,
    MomentumStrategy,
    ORBStrategy,
    PullbackStrategy,
    RangeTradingStrategy,
    RetailFakeoutStrategy,
    RipAndDipStrategy,
    RSIExhaustionStrategy,
    RSIExtremeReversalStrategy,
    ScalpingStrategy,
    StopHuntReversalStrategy,
    TrendFollowStrategy,
    VWAPBounceStrategy,
    BigBidScalpStrategy,
    BagholderBounceStrategy,
    BrokenParabolicShortStrategy,
    ClosingBellLiquidityGrabStrategy,
    DarkPoolFootprintsStrategy,
    FakeHaltTrapStrategy,
    FirstHourTrendStrategy,
    MarketMakerRefillStrategy,
    NineFortyFiveReversalStrategy,
    PremarketVWAPReclaimStrategy,
    BullFlagStrategy,
    FlatTopBreakoutStrategy,
    ABCDPatternStrategy,
)
from utils.indicators import (
    atr,
    atr_stop_loss,
    atr_take_profit,
    calculate_position_size_atr,
    is_power_hour,
    power_hour_multiplier,
    ema,
    vwap,
)
from utils.market_hours import (
    is_past_new_trade_cutoff,
    is_eod_liquidation_time,
    minutes_until_close,
    is_opening_range,
    minutes_since_open,
    market_session,
    EASTERN,
)
from core.pro_trade_filters import ProTradeValidator
from core.elite_trade_system import (
    EliteTradingSystem,
    SetupGrade,
    TradingDisciplineEnforcer,
    PositionManager as ElitePositionManager,
)
from core.performance_engine import (
    PerformanceEngine,
    FastSignalProcessor,
    SystemIntegrationValidator,
    LATENCY,
)
from core.learning_engine import get_learning_engine, TradeRecord
from core.edge_engine import get_edge_engine, EdgeEngine

logger = logging.getLogger("autonomous_engine")

# Persistent decision log (last N decisions)
DECISION_LOG_FILE = Path("data/decision_log.json")


def retry_with_backoff(func, max_retries: int = 3, base_delay: float = 0.1):
    """
    Execute a function with exponential backoff retry.
    Used for critical trading operations that may fail due to transient errors.
    """
    import time as time_module
    last_error = None
    for attempt in range(max_retries):
        try:
            result = func()
            if result and not result.get("error"):
                return result
            last_error = result.get("error", "Unknown error") if result else "No response"
        except Exception as e:
            last_error = str(e)
        if attempt < max_retries - 1:
            delay = base_delay * (2 ** attempt)  # Exponential backoff: 0.1, 0.2, 0.4
            logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay:.2f}s: {last_error}")
            time_module.sleep(delay)
    return {"error": f"Failed after {max_retries} retries: {last_error}"}


class AutonomousEngine:
    """
    Fully autonomous trading engine that:
    - Continuously scans markets during trading hours
    - Analyzes opportunities using ALL available strategies
    - Makes intelligent autonomous trading decisions
    - Executes trades automatically
    - Monitors and manages positions
    - Maintains persistent connections
    """

    def __init__(
        self,
        market_data_provider: MarketDataProvider,
        strategy_engine: StrategyEngine,
        risk_manager: RiskManager,
        position_manager: PositionManager,
        broker_client: Any,  # AlpacaClient or IBKRClient
        config: Optional[Dict[str, Any]] = None,
    ):
        self.market_data = market_data_provider
        self.strategy_engine = strategy_engine
        self.risk_manager = risk_manager
        self.position_manager = position_manager
        self.broker = broker_client

        # Configuration
        self.config = config or {}
        self.enabled = self.config.get("enabled", False)
        self.mode = self.config.get("mode", "FULL_AUTO")  # ASSISTED, SEMI_AUTO, FULL_AUTO, GOD_MODE
        self.risk_posture = self.config.get("risk_posture", "BALANCED")  # DEFENSIVE, BALANCED, AGGRESSIVE
        self.scan_interval = self.config.get("scan_interval", 10)  # seconds between scans (10s for free tier rate limits)
        self.scan_watchdog_threshold = self.config.get("scan_watchdog_threshold", 60)  # seconds before restarting scan loop
        self.scan_timeout_seconds = self.config.get("scan_timeout_seconds", 45)
        self.analyze_timeout_seconds = self.config.get("analyze_timeout_seconds", 45)
        self.last_scan_heartbeat: Optional[datetime] = None
        self.max_decisions = self.config.get("max_decision_logs", 100)
        self._last_decision_flush: Optional[datetime] = None
        self.max_positions = self.config.get("max_positions", 5)
        self.enabled_strategies = self.config.get("enabled_strategies", "ALL")
        self.trade_frequency_profile = (
            self.config.get("trade_frequency_profile") or settings.trade_frequency_profile or "active"
        ).lower()
        # Quality over quantity - higher thresholds = better win rate
        if self.trade_frequency_profile == "active":
            self.min_confidence_threshold = 0.60  # Still require decent confidence
        elif self.trade_frequency_profile == "conservative":
            self.min_confidence_threshold = 0.75  # High quality only
        else:  # balanced
            self.min_confidence_threshold = 0.65  # Good balance
        self.time_stop_minutes = self.config.get("time_stop_minutes", 12)
        self.time_stop_min_pnl = self.config.get("time_stop_min_pnl", 0.2)  # percent
        self.max_hold_minutes = self.config.get("max_hold_minutes", 25)
        self.trailing_lookback_bars = self.config.get("trailing_lookback_bars", 3)
        self.trailing_min_pnl = self.config.get("trailing_min_pnl", 0.3)  # percent
        self.momentum_exit_min_pnl = self.config.get("momentum_exit_min_pnl", 0.4)  # percent
        self.momentum_exit_ema_period = self.config.get("momentum_exit_ema_period", 9)

        # State - THREAD SAFE with locks
        self.running = False
        self.last_scan_time: Optional[datetime] = None
        self.decisions: List[Dict[str, Any]] = []
        self.active_symbols: Set[str] = set()
        self.strategy_performance: Dict[str, Dict[str, Any]] = {}

        # CRITICAL: Store background task references to prevent garbage collection
        # Tasks stored in local variables may be GC'd before they run!
        self._background_tasks: List[asyncio.Task] = []
        self._task_registry: Dict[str, asyncio.Task] = {}
        self._task_backoff: Dict[str, int] = {}
        self._task_factories: Dict[str, Any] = {}

        # CRITICAL: Thread locks for concurrent access
        self._state_lock = RLock()  # Protects: daily_pnl, decisions, active_symbols
        self._position_lock = Lock()  # Protects: elite_position_manager, position operations
        self._cache_lock = Lock()  # Protects: spy_data_cache, bars caches

        # Per-symbol context isolation - prevents context leakage in parallel trades
        self._symbol_states: Dict[str, SymbolState] = {}
        self._symbol_lock = Lock()  # Protects _symbol_states

        # Trade context tracking - NEVER LOSE TRADE CONTEXT
        self._active_trade_contexts: Dict[str, TradeContext] = {}  # symbol -> context
        self._trade_context_lock = Lock()
        self._trade_user_id: Optional[int] = None

        # Scanner results (for UI display)
        self.last_scanner_results: List[Dict[str, Any]] = []  # Raw screener output
        self.last_analyzed_opportunities: List[Dict[str, Any]] = []  # After strategy analysis
        self.last_strategy_analyzed_count: int = 0  # Total symbols analyzed by strategies
        self.last_market_symbols: List[str] = []  # Last symbols with market data
        self.last_hotlist: List[str] = []  # Latest hotlist symbols
        self.last_hotlist_at: Optional[datetime] = None
        self.symbols_scanned: int = 0  # Count of symbols scanned
        self.all_evaluations: List[Dict[str, Any]] = []  # ALL stocks with pass/fail details
        self.filter_summary: Dict[str, int] = {}  # Summary of filter pass/fail counts
        self.watchlist_candidates: List[Dict[str, Any]] = []  # Broad watchlist results

        # Day trading safeguards
        self.eod_liquidation_done_today: bool = False  # Track if EOD liquidation ran today
        self.last_liquidation_date: Optional[str] = None  # Date string of last liquidation
        self.daily_pnl: float = 0.0  # Track daily P&L
        self.daily_pnl_limit: float = -500.0  # Stop trading if down this much

        # Pro-level trade validator (institutional-grade filters)
        self.pro_validator = ProTradeValidator(
            max_spread_percent=0.15,  # Max 0.15% spread
            max_sector_positions=2,   # Max 2 positions per sector
            profit_protection_threshold=300.0,  # Start protecting at +$300
            drawdown_limit_percent=30.0  # Halt if give back 30% of peak
        )

        # Elite trading system (institutional-grade analysis)
        self.elite_system = EliteTradingSystem()
        self.elite_position_manager = ElitePositionManager()
        # Active day trading requires higher limits
        # Pro traders make 20-30+ trades/day - don't cap winners artificially
        self.discipline = TradingDisciplineEnforcer(
            max_consecutive_losses=5,  # Allow more losses before extended cooldown
            loss_cooldown_minutes=2,   # Shorter cooldown - day trading is fast-paced
            max_daily_winners=30,      # Allow many winners - don't quit early
            daily_loss_limit=1000.0,   # Higher daily loss limit for active trading
            profit_protection_threshold=500.0,  # Higher threshold before profit protection
            max_drawdown_pct=40.0      # Allow more drawdown from peak
        )

        # Track SPY data for relative strength
        self._spy_data_cache: Optional[pd.DataFrame] = None
        self._spy_cache_time: Optional[datetime] = None
        self._daily_data_cache: Dict[str, pd.DataFrame] = {}
        self._daily_data_cache_time: Optional[datetime] = None
        self._daily_data_cache_ttl_seconds = 15 * 60
        self._positions_cache_count: int = 0
        self._positions_cache_time: Optional[datetime] = None
        self._short_interest_cache_time: Optional[datetime] = None
        self._short_interest_cache_ttl_seconds = 12 * 60 * 60
        self._symbol_cache_ttl_seconds = self.config.get("symbol_cache_ttl_seconds", 10 * 60)
        self._symbol_state_ttl_seconds = self.config.get("symbol_state_ttl_seconds", 30 * 60)
        self._short_interest_provider = ShortInterestProvider(
            settings.polygon_api_key, base_url=settings.polygon_base_url
        )

        # ML Model for screening
        self.ml_model = MLSignalModel()
        self.ml_model.load()
        self.screener = MarketScreener(
            self.ml_model,
            min_avg_volume=settings.screener_min_avg_volume,
            min_avg_volume_low_float=settings.screener_min_avg_volume_low_float,
            min_avg_volume_mid_float=settings.screener_min_avg_volume_mid_float,
            min_avg_volume_large_float=settings.screener_min_avg_volume_large_float,
            min_price=settings.screener_min_price,
            max_price=settings.screener_max_price,
            min_volatility=settings.screener_min_volatility,
            min_relative_volume=settings.screener_min_relative_volume,
            min_relative_volume_low_float=settings.screener_min_relative_volume_low_float,
            min_relative_volume_mid_float=settings.screener_min_relative_volume_mid_float,
            min_relative_volume_large_float=settings.screener_min_relative_volume_large_float,
            min_premarket_volume=settings.screener_min_premarket_volume,
            low_float_max=settings.screener_low_float_max,
            mid_float_max=settings.screener_mid_float_max,
            in_play_min_rvol=settings.screener_in_play_min_rvol,
            in_play_gap_percent=settings.screener_in_play_gap_percent,
            in_play_volume_multiplier=settings.screener_in_play_volume_multiplier,
            require_premarket_volume=settings.screener_require_premarket_volume,
            require_daily_trend=settings.screener_require_daily_trend,
        )
        self._screener_base = {
            "min_relative_volume": self.screener.min_relative_volume,
            "min_relative_volume_low_float": self.screener.min_relative_volume_low_float,
            "min_relative_volume_mid_float": self.screener.min_relative_volume_mid_float,
            "min_relative_volume_large_float": self.screener.min_relative_volume_large_float,
            "min_premarket_volume": self.screener.min_premarket_volume,
            "in_play_min_rvol": self.screener.in_play_min_rvol,
            "in_play_volume_multiplier": self.screener.in_play_volume_multiplier,
            "require_premarket_volume": self.screener.require_premarket_volume,
            "require_daily_trend": self.screener.require_daily_trend,
        }
        self._last_profile_log_time: Optional[datetime] = None

        # Initialize all available strategies
        self.all_strategies = self._initialize_strategies()

        # High-performance engine for sub-10ms execution
        # Default watchlist - will be updated dynamically from screener
        default_symbols = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "AMD", "TSLA",
            "SPY", "QQQ", "COIN", "MARA", "RIOT", "SMCI", "ARM", "AVGO"
        ]
        self.perf_engine = PerformanceEngine(market_data_provider, default_symbols)
        self.fast_signal_processor = FastSignalProcessor(self.perf_engine)
        self.integration_validator = SystemIntegrationValidator()
        self._integration_validated = False

        # Persistent state file
        self.state_file = Path("data/autonomous_state.json")
        self._load_state()

        # ML Learning Engine - learns from wins/losses to improve over time
        self.learning_engine = get_learning_engine()
        self._trades_since_learning_cycle = 0
        self._learning_cycle_threshold = 10  # Run learning cycle every 10 trades

        # === COMPETITIVE EDGE ENGINE ===
        # This is what separates #1 from #5
        # Provides: Algo detection, Flow prediction, Sentiment analysis, Stealth execution
        self.edge_engine: EdgeEngine = get_edge_engine()
        self._edge_lock = Lock()  # Thread-safe edge analysis

        logger.info(f"Autonomous Engine initialized - Mode: {self.mode}, Risk: {self.risk_posture}")
        logger.info(f"🚀 High-Performance Engine ready (target: <10ms latency)")
        logger.info(f"⚡ EDGE ENGINE ACTIVE - Operating on a different level")

        # Add initialization decision so user sees engine was created
        self._add_decision(
            "SYSTEM",
            f"🤖 Engine INITIALIZED - Mode: {self.mode}, Risk: {self.risk_posture}, Strategies: {len(self.all_strategies)}",
            "INFO",
            {
                "mode": self.mode,
                "risk_posture": self.risk_posture,
                "strategies": len(self.all_strategies),
                "scan_interval": self.scan_interval,
                "enabled": self.enabled
            }
        )

    def _initialize_strategies(self) -> Dict[str, Any]:
        """Initialize all 37+ trading strategies including Warrior Trading patterns"""
        # Default config for all strategies
        default_config = {"parameters": {}, "enabled": True}

        # ATR-enabled config for Warrior Trading strategies
        atr_config = {"parameters": {"use_atr_stops": True, "atr_multiplier": 2.0}, "enabled": True}

        strategies = {
            # === WARRIOR TRADING CORE PATTERNS (Priority) ===
            "bull_flag": BullFlagStrategy(atr_config),  # Primary momentum pattern
            "abcd_pattern": ABCDPatternStrategy(atr_config),  # ABCD continuation pattern
            "flat_top_breakout": FlatTopBreakoutStrategy(atr_config),  # Key resistance breakout
            "orb": ORBStrategy(default_config),  # Opening Range Breakout

            # Trend Following
            "breakout": BreakoutStrategy(default_config),
            "ema_cross": EMACrossStrategy(default_config),
            "htf_ema_momentum": HTFEMAMomentumStrategy(default_config),
            "momentum": MomentumStrategy(default_config),
            "trend_follow": TrendFollowStrategy(default_config),
            "first_hour_trend": FirstHourTrendStrategy(default_config),

            # Mean Reversion
            "pullback": PullbackStrategy(default_config),
            "range_trading": RangeTradingStrategy(default_config),
            "rsi_exhaustion": RSIExhaustionStrategy(default_config),
            "rsi_extreme_reversal": RSIExtremeReversalStrategy(default_config),
            "vwap_bounce": VWAPBounceStrategy(default_config),
            "nine_forty_five_reversal": NineFortyFiveReversalStrategy(default_config),

            # Scalping & Day Trading
            "scalping": ScalpingStrategy(default_config),
            "rip_and_dip": RipAndDipStrategy(default_config),
            "big_bid_scalp": BigBidScalpStrategy(default_config),

            # Advanced Pattern Recognition
            "retail_fakeout": RetailFakeoutStrategy(default_config),
            "stop_hunt_reversal": StopHuntReversalStrategy(default_config),
            "bagholder_bounce": BagholderBounceStrategy(default_config),
            "broken_parabolic_short": BrokenParabolicShortStrategy(default_config),
            "fake_halt_trap": FakeHaltTrapStrategy(default_config),

            # Institutional & Smart Money
            "closing_bell_liquidity_grab": ClosingBellLiquidityGrabStrategy(default_config),
            "dark_pool_footprints": DarkPoolFootprintsStrategy(default_config),
            "market_maker_refill": MarketMakerRefillStrategy(default_config),
            "premarket_vwap_reclaim": PremarketVWAPReclaimStrategy(default_config),
        }

        logger.info(f"Initialized {len(strategies)} trading strategies (including Warrior Trading patterns)")
        return strategies

    def _load_state(self):
        """Load persistent state from disk - ensures context is preserved across restarts/disconnections"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)

                    # Core configuration
                    self.enabled = state.get("enabled", self.enabled)
                    self.mode = state.get("mode", self.mode)
                    self.risk_posture = state.get("risk_posture", self.risk_posture)
                    self.strategy_performance = state.get("strategy_performance", {})

                    # Day trading state (critical for continuity)
                    self.daily_pnl = state.get("daily_pnl", 0.0)
                    self.eod_liquidation_done_today = state.get("eod_liquidation_done_today", False)
                    self.last_liquidation_date = state.get("last_liquidation_date", None)

                    # Decision history (for context continuity)
                    self.decisions = state.get("decisions", [])

                    # Active positions being tracked
                    active_symbols = state.get("active_symbols", [])
                    self.active_symbols = set(active_symbols)

                    # Scale-out plans (critical for position management)
                    scale_out_plans = state.get("scale_out_plans", {})
                    if scale_out_plans and hasattr(self, 'elite_position_manager'):
                        for symbol, plan_data in scale_out_plans.items():
                            self.elite_position_manager.restore_scale_plan(symbol, plan_data)

                    # Scanner results (for UI continuity)
                    self.last_scanner_results = state.get("last_scanner_results", [])
                    self.last_analyzed_opportunities = state.get("last_analyzed_opportunities", [])
                    self.symbols_scanned = state.get("symbols_scanned", 0)

                    # Check if this was a recovery from disconnection
                    last_updated = state.get("last_updated", "")
                    was_running = state.get("was_running", False)

                    logger.info(f"✅ Loaded state - Enabled: {self.enabled}, Mode: {self.mode}")
                    logger.info(f"   Daily P&L: ${self.daily_pnl:.2f}, Decisions: {len(self.decisions)}")
                    logger.info(f"   Active symbols: {len(self.active_symbols)}, Scale-out plans: {len(scale_out_plans)}")

                    if was_running and last_updated:
                        self._add_decision(
                            "RECOVERY",
                            f"Recovered from disconnection - State restored from {last_updated}",
                            "INFO",
                            {"decisions_recovered": len(self.decisions), "active_symbols": len(self.active_symbols)}
                        )

            # Load persisted decision log (if larger than state snapshot)
            if DECISION_LOG_FILE.exists():
                try:
                    with open(DECISION_LOG_FILE, "r") as f:
                        persisted = json.load(f)
                    if isinstance(persisted, list) and len(persisted) > len(self.decisions):
                        self.decisions = persisted
                    if len(self.decisions) > self.max_decisions:
                        self.decisions = self.decisions[: self.max_decisions]
                except Exception as e:
                    logger.debug(f"Failed to load decision log: {e}")

        except Exception as e:
            logger.error(f"Error loading state: {e}")

    def _save_state(self):
        """Save comprehensive state to disk for recovery from disconnections"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            # Get scale-out plans from elite position manager
            scale_out_plans = {}
            if hasattr(self, 'elite_position_manager'):
                for symbol, plan in self.elite_position_manager.positions.items():
                    # Extract take profit levels from scale_levels list
                    take_profit_1r = 0
                    take_profit_2r = 0
                    take_profit_3r = 0
                    scaled_1r = False
                    scaled_2r = False

                    for level in plan.scale_levels:
                        if level.get("level") == "1R":
                            take_profit_1r = level.get("price", 0)
                            scaled_1r = level.get("executed", False)
                        elif level.get("level") == "2R":
                            take_profit_2r = level.get("price", 0)
                            scaled_2r = level.get("executed", False)
                        elif level.get("level") == "3R":
                            take_profit_3r = level.get("price", 0)

                    scale_out_plans[symbol] = {
                        "quantity": plan.total_quantity,
                        "stop_loss": plan.original_stop,
                        "take_profit_1r": take_profit_1r,
                        "take_profit_2r": take_profit_2r,
                        "take_profit_3r": take_profit_3r,
                        "scaled_1r": scaled_1r,
                        "scaled_2r": scaled_2r,
                        "breakeven_activated": plan.breakeven_activated,
                        "trailing_activated": plan.trailing_activated,
                        "current_stop": plan.current_stop,
                    }

            state = {
                # Core configuration
                "enabled": self.enabled,
                "mode": self.mode,
                "risk_posture": self.risk_posture,
                "strategy_performance": self.strategy_performance,

                # Day trading state (critical)
                "daily_pnl": self.daily_pnl,
                "eod_liquidation_done_today": self.eod_liquidation_done_today,
                "last_liquidation_date": self.last_liquidation_date,

                # Decision history (keep last 50 for context)
                "decisions": self.decisions[:100],

                # Active tracking
                "active_symbols": list(self.active_symbols),
                "scale_out_plans": scale_out_plans,

                # Scanner results (for UI continuity)
                "last_scanner_results": self.last_scanner_results[:20],
                "last_analyzed_opportunities": self.last_analyzed_opportunities[:15],
                "symbols_scanned": self.symbols_scanned,

                # Recovery metadata
                "was_running": self.running,
                "last_updated": datetime.now().isoformat(),
            }

            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

            # Persist decisions for UI continuity
            self._persist_decisions()

        except Exception as e:
            logger.error(f"Error saving state: {e}")

    # ==================== THREAD-SAFE CONTEXT MANAGEMENT ====================

    def _get_symbol_state(self, symbol: str) -> SymbolState:
        """Get or create per-symbol state - THREAD SAFE"""
        with self._symbol_lock:
            if symbol not in self._symbol_states:
                self._symbol_states[symbol] = SymbolState(symbol=symbol)
            state = self._symbol_states[symbol]
            state.last_seen = datetime.now()
            return state

    def _prune_background_tasks(self) -> None:
        """Remove completed tasks to prevent unbounded task list growth."""
        if not self._background_tasks:
            return
        self._background_tasks = [t for t in self._background_tasks if not t.done()]

    def _cleanup_symbol_state_caches(self) -> None:
        """Clean up stale symbol state caches to control memory usage."""
        now = self._get_market_now()
        with self._symbol_lock:
            to_delete = []
            for symbol, state in self._symbol_states.items():
                # Clear stale bar caches for non-active symbols
                if symbol not in self.active_symbols and state.bars_cache_time:
                    age = (now - state.bars_cache_time).total_seconds()
                    if age > self._symbol_cache_ttl_seconds:
                        state.bars_cache = None
                        state.bars_cache_time = None
                # Drop entire symbol state if it hasn't been seen recently
                if state.last_seen and symbol not in self.active_symbols:
                    idle = (now - state.last_seen).total_seconds()
                    if idle > self._symbol_state_ttl_seconds:
                        to_delete.append(symbol)
            for symbol in to_delete:
                del self._symbol_states[symbol]

        # Guard daily data cache size in long sessions
        if len(self._daily_data_cache) > 500 and self.last_market_symbols:
            keep = set(self.last_market_symbols)
            self._daily_data_cache = {k: v for k, v in self._daily_data_cache.items() if k in keep}

    def _apply_trade_frequency_profile(self, current_hour: int, current_minute: int, now: Optional[datetime] = None) -> None:
        """Adjust screener thresholds based on trade-frequency profile and time-of-day."""
        profile = self.trade_frequency_profile
        base = self._screener_base
        mins_open = minutes_since_open(now=now)
        in_opening = 0 <= mins_open < 30
        in_midday = mins_open >= 120 if mins_open >= 0 else False

        # Default to baseline
        rvol = base["min_relative_volume"]
        rvol_low = base["min_relative_volume_low_float"]
        rvol_mid = base["min_relative_volume_mid_float"]
        rvol_large = base["min_relative_volume_large_float"]
        premarket_required = base["require_premarket_volume"]
        premarket_min = base["min_premarket_volume"]
        in_play_rvol = base["in_play_min_rvol"]
        in_play_mult = base["in_play_volume_multiplier"]

        if profile == "active":
            rvol = 1.0 if in_midday else 1.2
            rvol_low = max(1.4, rvol + 0.3)
            rvol_mid = max(1.1, rvol)
            rvol_large = 0.9 if in_midday else 1.0
            in_play_rvol = 1.6 if in_midday else 1.8
            in_play_mult = 0.4
            # Active profile: Disable daily trend filter - trade momentum, not trend
            self.screener.require_daily_trend = False
        elif profile == "balanced":
            rvol = 1.2 if in_midday else 1.4
            rvol_low = max(1.6, rvol + 0.4)
            rvol_mid = max(1.2, rvol)
            rvol_large = 1.0 if in_midday else 1.1
            in_play_rvol = 1.8 if in_midday else 2.0
            in_play_mult = 0.5

        # Premarket volume only during premarket or opening range
        premarket_required = premarket_required and (mins_open == -1 or in_opening)

        self.screener.min_relative_volume = rvol
        self.screener.min_relative_volume_low_float = rvol_low
        self.screener.min_relative_volume_mid_float = rvol_mid
        self.screener.min_relative_volume_large_float = rvol_large
        self.screener.in_play_min_rvol = in_play_rvol
        self.screener.in_play_volume_multiplier = in_play_mult
        self.screener.require_premarket_volume = premarket_required
        self.screener.min_premarket_volume = premarket_min

        # Throttled log
        now = datetime.now()
        if not self._last_profile_log_time or (now - self._last_profile_log_time).total_seconds() > 900:
            self._add_decision(
                "SYSTEM",
                f"Trade frequency profile: {profile}",
                "INFO",
                {
                    "profile": profile,
                    "rvol": rvol,
                    "rvol_large": rvol_large,
                    "in_play_rvol": in_play_rvol,
                    "premarket_required": premarket_required,
                    "minutes_since_open": mins_open,
                },
            )
            self._last_profile_log_time = now

    def _update_symbol_signal(self, symbol: str, signal: str) -> bool:
        """
        Update last signal for a symbol - prevents duplicate signals.
        Returns True if this is a NEW signal, False if duplicate.
        THREAD SAFE - per-symbol isolation prevents cross-contamination.
        """
        with self._symbol_lock:
            state = self._get_symbol_state(symbol)
            if state.last_signal == signal:
                # Same signal as before - ignore to prevent duplicate trades
                return False
            state.last_signal = signal
            state.last_signal_time = datetime.now()
            return True

    def _create_trade_context(
        self,
        symbol: str,
        strategy_name: str,
        entry_price: float,
        quantity: int,
        confidence: float,
        setup_grade: str,
        signals_used: List[str]
    ) -> TradeContext:
        """
        Create a complete snapshot of context when trade is initiated.
        This context is IMMUTABLE and preserved for the life of the trade.
        CRITICAL: Never lose this context during parallel operations.
        """
        # Get current market state
        spy_price = 0.0
        with self._cache_lock:
            if self._spy_data_cache is not None and len(self._spy_data_cache) > 0:
                spy_price = float(self._spy_data_cache.iloc[-1].get("close", 0))

        # Get VWAP and ATR for the symbol
        symbol_state = self._get_symbol_state(symbol)
        vwap = 0.0
        atr_val = 0.0
        if symbol_state.bars_cache is not None and len(symbol_state.bars_cache) > 0:
            vwap = float(symbol_state.bars_cache.iloc[-1].get("vwap", 0)) if "vwap" in symbol_state.bars_cache.columns else 0.0
            if len(symbol_state.bars_cache) >= 14:
                atr_series = atr(symbol_state.bars_cache)
                atr_val = float(atr_series.iloc[-1]) if len(atr_series) else 0.0
            else:
                atr_val = 0.0

        # Get account state
        buying_power = 0.0
        try:
            account = self.broker.get_account_summary()
            buying_power = float(account.get("BuyingPower", 0))
        except Exception:
            pass

        # Get other open positions
        other_positions = []
        with self._state_lock:
            other_positions = [s for s in self.active_symbols if s != symbol]
            daily_pnl_snapshot = self.daily_pnl

        context = TradeContext(
            symbol=symbol,
            strategy_name=strategy_name,
            entry_time=datetime.now(),
            entry_price=entry_price,
            quantity=quantity,
            confidence=confidence,
            setup_grade=setup_grade,
            spy_price=spy_price,
            vwap=vwap,
            atr=atr_val,
            daily_pnl_at_entry=daily_pnl_snapshot,
            buying_power_at_entry=buying_power,
            other_positions=other_positions,
            signals_used=signals_used
        )

        # Store context - NEVER LOSE THIS
        with self._trade_context_lock:
            self._active_trade_contexts[symbol] = context

        logger.info(f"📸 Trade context captured for {symbol}: {strategy_name}, ${entry_price:.2f} x {quantity}")
        return context

    def _get_default_user_id(self) -> Optional[int]:
        """Resolve the default user for trade persistence (admin or first user)."""
        if self._trade_user_id is not None:
            return self._trade_user_id
        try:
            from core.db import SessionLocal
            from models import User
            db = SessionLocal()
            try:
                user = None
                if settings.admin_username:
                    user = db.query(User).filter(User.username == settings.admin_username).first()
                if user is None:
                    user = db.query(User).order_by(User.id.asc()).first()
                self._trade_user_id = user.id if user else None
                return self._trade_user_id
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to resolve default user id: {e}")
            return None

    def _record_trade_entry(
        self,
        symbol: str,
        action: str,
        quantity: int,
        entry_price: float,
        strategies: List[str],
        stop_loss: float,
        take_profit: float,
        confidence: float,
        setup_grade: str,
        entry_reason: str | None = None,
    ) -> Optional[int]:
        """Persist trade entry to DB so history shows up."""
        user_id = self._get_default_user_id()
        if not user_id:
            return None
        try:
            from core.db import SessionLocal
            from models import Trade
            db = SessionLocal()
            try:
                trade = Trade(
                    user_id=user_id,
                    symbol=symbol,
                    strategy_name=strategies[0] if strategies else None,
                    action=action,
                    quantity=abs(int(quantity)),
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    confidence=confidence,
                    setup_grade=setup_grade,
                    strategies=",".join(strategies) if strategies else None,
                    entry_reason=entry_reason,
                    entry_time=datetime.utcnow(),
                    status="open",
                    is_paper_trade=bool(settings.alpaca_paper),
                )
                db.add(trade)
                db.commit()
                db.refresh(trade)
                return trade.id
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to persist trade entry for {symbol}: {e}")
            return None

    def _finalize_trade_record(
        self,
        symbol: str,
        exit_price: float,
        pnl: Optional[float],
    ) -> None:
        """Update the most recent open trade with exit info."""
        user_id = self._get_default_user_id()
        if not user_id:
            return
        try:
            from core.db import SessionLocal
            from models import Trade
            db = SessionLocal()
            try:
                trade = (
                    db.query(Trade)
                    .filter(
                        Trade.user_id == user_id,
                        Trade.symbol == symbol,
                        Trade.exit_time.is_(None),
                    )
                    .order_by(Trade.entry_time.desc())
                    .first()
                )
                if not trade:
                    return
                entry_price = float(trade.entry_price or 0)
                quantity = float(trade.quantity or 0)
                computed_pnl = pnl
                if computed_pnl is None and entry_price and quantity:
                    if (trade.action or "").upper() == "SELL":
                        computed_pnl = (entry_price - exit_price) * quantity
                    else:
                        computed_pnl = (exit_price - entry_price) * quantity
                pnl_percent = None
                if entry_price and quantity:
                    pnl_percent = ((computed_pnl or 0) / (entry_price * quantity)) * 100

                trade.exit_price = exit_price
                trade.exit_time = datetime.utcnow()
                trade.pnl = computed_pnl
                trade.pnl_percent = pnl_percent
                trade.status = "closed"
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to finalize trade record for {symbol}: {e}")

    def _get_trade_context(self, symbol: str) -> Optional[TradeContext]:
        """Get the trade context for a symbol - THREAD SAFE"""
        with self._trade_context_lock:
            return self._active_trade_contexts.get(symbol)

    def _clear_trade_context(self, symbol: str) -> Optional[TradeContext]:
        """Clear trade context when position is closed - returns the context for logging"""
        with self._trade_context_lock:
            return self._active_trade_contexts.pop(symbol, None)

    def _update_daily_pnl(self, pnl_change: float) -> float:
        """Thread-safe daily P&L update - returns new total"""
        with self._state_lock:
            self.daily_pnl += pnl_change
            return self.daily_pnl

    def _add_active_symbol(self, symbol: str):
        """Thread-safe add symbol to active set"""
        with self._state_lock:
            self.active_symbols.add(symbol)

    def _remove_active_symbol(self, symbol: str):
        """Thread-safe remove symbol from active set"""
        with self._state_lock:
            self.active_symbols.discard(symbol)

    def _reconcile_positions_with_broker(self) -> Dict[str, Any]:
        """
        Reconcile our tracked positions with broker's actual positions.
        CRITICAL: Run periodically to detect any desync.
        Returns discrepancies found.
        """
        discrepancies = {"missing_locally": [], "missing_at_broker": [], "quantity_mismatch": []}

        try:
            broker_positions = self.broker.get_positions()
            broker_symbols = {p["symbol"] for p in broker_positions}

            with self._state_lock:
                our_symbols = self.active_symbols.copy()

            # Check for positions at broker that we don't know about
            for bp in broker_positions:
                symbol = bp["symbol"]
                if symbol not in our_symbols:
                    discrepancies["missing_locally"].append({
                        "symbol": symbol,
                        "broker_qty": bp.get("quantity", 0),
                        "action": "WILL_TRACK"
                    })
                    # Auto-heal: start tracking this position
                    self._add_active_symbol(symbol)
                    logger.warning(f"⚠️ Position found at broker but not tracked: {symbol}")

            # Check for positions we think we have but broker doesn't
            for symbol in our_symbols:
                if symbol not in broker_symbols:
                    discrepancies["missing_at_broker"].append({
                        "symbol": symbol,
                        "our_qty": "tracked",
                        "action": "WILL_REMOVE"
                    })
                    # Auto-heal: stop tracking this position
                    self._remove_active_symbol(symbol)
                    self._clear_trade_context(symbol)
                    logger.warning(f"⚠️ Position tracked but not at broker: {symbol} - removing")

            if discrepancies["missing_locally"] or discrepancies["missing_at_broker"]:
                logger.warning(f"🔄 Position reconciliation found {len(discrepancies['missing_locally'])} missing locally, {len(discrepancies['missing_at_broker'])} missing at broker")

        except Exception as e:
            logger.error(f"Position reconciliation failed: {e}")

        return discrepancies

    async def start(self):
        """Start the autonomous trading engine"""
        if self.running:
            logger.warning("Engine already running")
            return

        self.running = True
        self.enabled = True
        self._save_state()
        logger.info("🤖 Autonomous Engine STARTED")

        # Add startup decision so user can see the engine started in logs
        self._add_decision(
            "SYSTEM",
            f"Autonomous Engine STARTED - Mode: {self.mode}, Risk: {self.risk_posture}",
            "SUCCESS",
            {"mode": self.mode, "risk_posture": self.risk_posture, "broker_connected": self.broker.is_connected()}
        )

        # =====================================================
        # CRITICAL: CHECK FOR AND CLOSE ANY OVERNIGHT POSITIONS
        # Day traders NEVER hold overnight - liquidate immediately!
        # =====================================================
        try:
            if self.broker.is_connected():
                positions = self.broker.get_positions()
                if positions:
                    logger.warning(f"🚨 FOUND {len(positions)} OVERNIGHT POSITIONS - LIQUIDATING NOW!")
                    self._add_decision(
                        "OVERNIGHT_LIQUIDATION",
                        f"🚨 Found {len(positions)} overnight positions - LIQUIDATING IMMEDIATELY (Day trading rule: NO overnight holds)",
                        "CRITICAL",
                        {"positions": [p.get("symbol") for p in positions]}
                    )
                    await self._liquidate_all_positions()
                    self._add_decision(
                        "OVERNIGHT_LIQUIDATION",
                        "✅ All overnight positions closed - Day trading rule enforced",
                        "SUCCESS",
                        {}
                    )
                else:
                    self._add_decision(
                        "SYSTEM",
                        "✅ No overnight positions found - clean slate for today",
                        "SUCCESS",
                        {}
                    )
        except Exception as e:
            logger.error(f"Error checking overnight positions: {e}")
            self._add_decision("ERROR", f"Could not check overnight positions: {str(e)}", "ERROR", {})

        # Skip integration validation on startup (too slow, can hang)
        self._integration_validated = True

        # Reset daily tracking
        today = datetime.now().strftime("%Y-%m-%d")
        if self.last_liquidation_date != today:
            self.eod_liquidation_done_today = False
            self.daily_pnl = 0.0
            try:
                self.discipline.reset_daily()
            except Exception as e:
                logger.warning(f"Failed to reset daily discipline counters: {e}")
            logger.info("📅 New trading day - daily counters reset")

        # =====================================================
        # START BACKGROUND TASKS
        # CRITICAL: Store task references to prevent garbage collection!
        # =====================================================
        def log_task_exception(task, name):
            """Log any exception from a background task"""
            try:
                exc = task.exception()
                if exc:
                    logger.error(f"❌ Task {name} failed: {exc}")
                    import traceback
                    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
                    logger.error(f"Traceback:\n{tb}")
                    self._add_decision("ERROR", f"Background task {name} crashed: {exc}", "ERROR", {"traceback": tb[:500]})
            except (asyncio.CancelledError, asyncio.InvalidStateError):
                pass

        def start_task(name: str, coro_factory):
            task = asyncio.create_task(coro_factory())
            task.add_done_callback(lambda t: log_task_exception(t, name))
            self._task_registry[name] = task
            self._background_tasks.append(task)

        # Clear any old tasks
        self._background_tasks = []
        self._task_registry = {}
        self._task_backoff = {}

        # Main trading loop - CRITICAL - store reference to prevent GC!
        logger.info("📍 Creating background tasks (storing references to prevent GC)...")

        self._task_factories = {
            "main_trading_loop": self._main_trading_loop,
            "eod_liquidation_monitor": self._eod_liquidation_monitor,
            "connection_keepalive": self._connection_keepalive,
            "position_monitor": self._position_monitor,
            "latency_monitor": self._latency_monitor,
            "periodic_state_save": self._periodic_state_save,
            "position_reconciliation": self._position_reconciliation_loop,
            "scan_watchdog": self._scan_watchdog,
        }

        for name, factory in self._task_factories.items():
            start_task(name, factory)

        # Supervisor task to restart failed tasks
        start_task("task_supervisor", self._task_supervisor)

        logger.info(f"✅ {len(self._background_tasks)} background tasks created and stored")

        # Give tasks a moment to start
        await asyncio.sleep(0.5)

        self._add_decision(
            "SYSTEM",
            "✅ Engine fully started - continuous scanning active",
            "SUCCESS",
            {"background_tasks": len(self._background_tasks), "mode": self.mode}
        )

    async def stop(self):
        """Stop the autonomous trading engine"""
        self.running = False
        self.enabled = False
        self._save_state()

        # Cancel all background tasks
        if hasattr(self, '_background_tasks'):
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()
            # Wait for tasks to finish cancelling
            if self._background_tasks:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)
            self._background_tasks = []

        # Stop performance engine background processes
        if hasattr(self, 'perf_engine'):
            self.perf_engine.stop()

        logger.info("🛑 Autonomous Engine STOPPED")

    async def _connection_keepalive(self):
        """
        Maintain persistent connection to broker.
        Checks every 30 seconds to stay within Render's idle timeout (~60s).
        Implements exponential backoff on reconnection failures.
        """
        reconnect_attempts = 0
        max_backoff = 60  # Max wait time between reconnect attempts

        while self.running:
            try:
                if not self.broker.is_connected():
                    reconnect_attempts += 1
                    backoff_time = min(5 * (2 ** (reconnect_attempts - 1)), max_backoff)

                    logger.warning(f"Connection lost - reconnecting (attempt {reconnect_attempts})...")

                    if hasattr(self.broker, "ensure_connected"):
                        connected = self.broker.ensure_connected()
                    else:
                        connected = self.broker.connect()

                    if connected:
                        logger.info("✓ Reconnected successfully")
                        self._add_decision("SYSTEM", "Reconnected to broker", "INFO", {"attempts": reconnect_attempts})
                        reconnect_attempts = 0  # Reset on success
                        # Save state after successful reconnection
                        self._save_state()
                    else:
                        logger.error(f"✗ Reconnection failed - retrying in {backoff_time}s")
                        self._add_decision("SYSTEM", "Reconnection failed", "ERROR", {"next_retry_seconds": backoff_time})
                        await asyncio.sleep(backoff_time)
                        continue  # Skip the normal sleep, go straight to retry
                else:
                    reconnect_attempts = 0  # Reset counter when connected

                # Check connection every 30 seconds to stay within Render's idle timeout
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Error in keepalive: {e}")
                await asyncio.sleep(10)  # Shorter sleep on error

    async def _periodic_state_save(self):
        """
        Periodically save state for recovery from disconnections.
        Runs every 60 seconds to ensure context is preserved.
        """
        while self.running:
            try:
                await asyncio.sleep(60)  # Save every 60 seconds
                self._save_state()
                logger.debug("📝 Periodic state save completed")
            except Exception as e:
                logger.error(f"Error in periodic state save: {e}")
                await asyncio.sleep(30)

    async def _task_supervisor(self):
        """
        Restart failed background tasks to keep the engine running continuously.
        """
        while self.running:
            try:
                await asyncio.sleep(10)
                self._prune_background_tasks()
                for name, task in list(self._task_registry.items()):
                    if name == "task_supervisor":
                        continue
                    if task.done():
                        exc = None
                        try:
                            exc = task.exception()
                        except Exception:
                            exc = None

                        backoff = min(self._task_backoff.get(name, 1) * 2, 60)
                        self._task_backoff[name] = backoff

                        logger.error(f"⚠️ Background task {name} stopped - restarting in {backoff}s")
                        self._add_decision(
                            "SYSTEM",
                            f"Restarting task {name} in {backoff}s",
                            "WARNING",
                            {"task": name, "error": str(exc) if exc else None, "backoff_seconds": backoff}
                        )

                        await asyncio.sleep(backoff)

                        factory = self._task_factories.get(name)
                        if factory and self.running:
                            new_task = asyncio.create_task(factory())
                            new_task.add_done_callback(lambda t, n=name: logger.error(f"❌ Task {n} failed again") if t.exception() else None)
                            self._task_registry[name] = new_task
                            self._background_tasks.append(new_task)
                        else:
                            logger.error(f"No factory found to restart task {name}")

            except Exception as e:
                logger.error(f"Task supervisor error: {e}")
                await asyncio.sleep(10)

    async def _scan_watchdog(self):
        """
        Watchdog to detect stalled scanning loops and restart the main trading loop.
        """
        while self.running:
            try:
                await asyncio.sleep(15)
                if not self.running:
                    continue
                if not self.last_scan_heartbeat:
                    continue

                stale_seconds = (datetime.utcnow() - self.last_scan_heartbeat).total_seconds()
                threshold = max(self.scan_watchdog_threshold, self.scan_interval * 4)
                if stale_seconds > threshold:
                    self._add_decision(
                        "SYSTEM",
                        f"⚠️ Scan stalled ({int(stale_seconds)}s) - restarting main loop",
                        "WARNING",
                        {"stale_seconds": int(stale_seconds), "threshold": int(threshold)},
                    )
                    await self._restart_task("main_trading_loop", f"stale {int(stale_seconds)}s")
                    # Reset heartbeat to avoid restart loops
                    self.last_scan_heartbeat = datetime.utcnow()
            except Exception as e:
                logger.error(f"Scan watchdog error: {e}")
                await asyncio.sleep(10)

    async def _restart_task(self, name: str, reason: str):
        """Cancel and restart a background task."""
        try:
            task = self._task_registry.get(name)
            if task and not task.done():
                task.cancel()
            factory = self._task_factories.get(name)
            if factory and self.running:
                new_task = asyncio.create_task(factory())
                new_task.add_done_callback(lambda t, n=name: logger.error(f"❌ Task {n} failed again") if t.exception() else None)
                self._task_registry[name] = new_task
                self._background_tasks.append(new_task)
                self._prune_background_tasks()
                logger.warning(f"🔁 Restarted task {name} ({reason})")
        except Exception as e:
            logger.error(f"Failed to restart task {name}: {e}")
    async def _position_reconciliation_loop(self):
        """
        Periodically reconcile our position tracking with broker's actual positions.
        CRITICAL: Prevents desync that could lead to orphaned positions or missed exits.
        Runs every 60 seconds during market hours.
        """
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every 60 seconds

                # Only reconcile during market hours
                if not self._is_market_hours():
                    continue

                discrepancies = self._reconcile_positions_with_broker()

                # Log any discrepancies found
                if discrepancies["missing_locally"] or discrepancies["missing_at_broker"]:
                    self._add_decision(
                        "RECONCILIATION",
                        f"Position sync: {len(discrepancies['missing_locally'])} found at broker, {len(discrepancies['missing_at_broker'])} removed",
                        "WARNING",
                        discrepancies
                    )

            except Exception as e:
                logger.error(f"Error in position reconciliation: {e}")
                await asyncio.sleep(30)

    async def _main_trading_loop(self):
        """Main autonomous trading loop - scans continuously for real-time UI updates"""
        try:
            # Log that we've entered the loop IMMEDIATELY
            logger.info("🤖 Main trading loop STARTED - beginning continuous scanning")
            self._add_decision(
                "SYSTEM",
                "🚀 Main trading loop ACTIVE - continuous scanning started",
                "SUCCESS",
                {"enabled": self.enabled, "running": self.running, "mode": self.mode}
            )

            loop_count = 0
            consecutive_errors = 0

            while self.running:
                try:
                    loop_count += 1
                    scan_start = datetime.now()
                    now = self._get_market_now()
                    self.last_scan_heartbeat = datetime.utcnow()

                    # Log every iteration so user can see activity
                    self._add_decision(
                        "THINKING",
                        f"🔄 Scan cycle #{loop_count} starting...",
                        "INFO",
                        {"cycle": loop_count, "time": scan_start.strftime("%H:%M:%S")}
                    )
                    logger.info(f"🔄 Scan cycle #{loop_count} starting...")

                    # Check basic requirements
                    if not self._should_trade_now():
                        self._add_decision(
                            "THINKING",
                            f"⏸️ Engine paused (enabled={self.enabled}, running={self.running})",
                            "WARNING",
                            {"enabled": self.enabled, "running": self.running}
                        )
                        await asyncio.sleep(10)
                        continue

                    # Determine scan interval based on market hours
                    is_market_open = self._is_market_hours()
                    current_scan_interval = self.scan_interval if is_market_open else 15
                    self.last_scan_time = datetime.now()

                    # 1. Scan market for opportunities
                    try:
                        opportunities = await asyncio.wait_for(
                            self._scan_market(),
                            timeout=self.scan_timeout_seconds,
                        )
                    except asyncio.TimeoutError:
                        logger.error("❌ Scan market timed out")
                        self._add_decision(
                            "ERROR",
                            f"Market scan timed out after {self.scan_timeout_seconds}s",
                            "ERROR",
                            {"timeout_seconds": self.scan_timeout_seconds},
                        )
                        opportunities = []
                    except Exception as scan_error:
                        logger.error(f"❌ Scan market failed: {scan_error}")
                        self._add_decision(
                            "ERROR",
                            f"Market scan failed: {str(scan_error)[:100]}",
                            "ERROR",
                            {"error": str(scan_error)}
                        )
                        opportunities = []

                    # 2. Analyze each opportunity with ALL strategies
                    try:
                        analyzed = await asyncio.wait_for(
                            self._analyze_opportunities(
                                opportunities,
                                analyze_symbols=self.last_market_symbols,
                                allowed_symbols={o.get("symbol") for o in opportunities if o.get("symbol")},
                            ),
                            timeout=self.analyze_timeout_seconds,
                        )
                    except asyncio.TimeoutError:
                        logger.error("❌ Analysis timed out")
                        self._add_decision(
                            "ERROR",
                            f"Analysis timed out after {self.analyze_timeout_seconds}s",
                            "ERROR",
                            {"timeout_seconds": self.analyze_timeout_seconds},
                        )
                        analyzed = []
                    except Exception as analyze_error:
                        logger.error(f"❌ Analysis failed: {analyze_error}")
                        self._add_decision(
                            "ERROR",
                            f"Analysis failed: {str(analyze_error)[:100]}",
                            "ERROR",
                            {"error": str(analyze_error)}
                        )
                        analyzed = []

                    # Log scan results so user can see activity
                    self._add_decision(
                        "SCAN",
                        f"Scanned {self.symbols_scanned} symbols - Found {len(opportunities)} opportunities, {self.last_strategy_analyzed_count} analyzed",
                        "INFO",
                        {
                            "symbols_scanned": self.symbols_scanned,
                            "opportunities": len(opportunities),
                            "analyzed": self.last_strategy_analyzed_count,
                            "market_open": is_market_open,
                            "top_symbols": [o.get("symbol") for o in opportunities[:5]]
                        }
                    )

                    # 3. Rank and select best opportunities
                    top_picks = self._rank_opportunities(analyzed)
                    ranked_full = sorted(
                        analyzed,
                        key=lambda x: (x.get("num_strategies", 0), x.get("confidence", 0)),
                        reverse=True
                    )
                    picked_symbols = {t.get("symbol") for t in top_picks if t.get("symbol")}

                    # Log signals that were not selected for execution
                    if ranked_full:
                        max_logs = len(ranked_full) if settings.screener_debug else min(len(ranked_full), 25)
                        for idx, opp in enumerate(ranked_full[:max_logs], start=1):
                            symbol = opp.get("symbol")
                            if not symbol or symbol in picked_symbols:
                                continue
                            self._add_decision(
                                "SKIPPED",
                                f"⏭️ {symbol}: Signal not selected (rank {idx}/{len(ranked_full)})",
                                "INFO",
                                {
                                    "symbol": symbol,
                                    "rank": idx,
                                    "total_signals": len(ranked_full),
                                    "num_strategies": opp.get("num_strategies", 0),
                                    "confidence": round(opp.get("confidence", 0), 3),
                                }
                            )

                    # =====================================================
                    # CRITICAL: EOD LIQUIDATION CHECK (redundant - for safety)
                    # Day traders MUST close all positions before market close
                    # =====================================================
                    if is_eod_liquidation_time(now=now) and not self.eod_liquidation_done_today:
                        logger.warning("⚠️ EOD LIQUIDATION TIME - Closing ALL positions!")
                        self._add_decision(
                            "EOD_LIQUIDATION",
                            "🚨 EOD LIQUIDATION - Day traders do NOT hold overnight!",
                            "CRITICAL",
                            {"time": datetime.now().isoformat()}
                        )
                        await self._liquidate_all_positions()
                        self.eod_liquidation_done_today = True
                        self.last_liquidation_date = datetime.now().strftime("%Y-%m-%d")
                        self._add_decision(
                            "EOD_LIQUIDATION",
                            "✅ All positions closed - Ready for tomorrow",
                            "SUCCESS",
                            {}
                        )

                    # 4. Execute trades ONLY during market hours and in auto modes
                    # DAY TRADING RULE: No new positions after 3:30 PM ET
                    if is_market_open and self.mode in ["FULL_AUTO", "GOD_MODE"]:
                        # Check broker connection before trading
                        if not self._can_execute_trades():
                            self._add_decision(
                                "SYSTEM",
                                f"Broker not connected - scanning only ({len(opportunities)} opportunities found)",
                                "WARNING",
                                {"opportunities": len(opportunities), "analyzed": self.last_strategy_analyzed_count, "broker_connected": False}
                            )
                            logger.warning("⚠️ Broker not connected - cannot execute trades")
                            for opp in top_picks[:10]:
                                symbol = opp.get("symbol")
                                if not symbol:
                                    continue
                                self._add_decision(
                                    "SKIPPED",
                                    f"⏸️ {symbol}: Signal ready but broker not connected",
                                    "WARNING",
                                    {"symbol": symbol, "reason": "broker_not_connected"}
                                )
                        elif is_past_new_trade_cutoff():
                            mins_left = minutes_until_close()
                            self._add_decision(
                                "CUTOFF",
                                f"Past 3:30 PM ET - No new trades ({mins_left} mins to close)",
                                "INFO",
                                {"minutes_to_close": mins_left}
                            )
                            logger.info(f"⏰ Past trade cutoff (3:30 PM) - {mins_left} mins until close, no new trades")
                            for opp in top_picks[:10]:
                                symbol = opp.get("symbol")
                                if not symbol:
                                    continue
                                self._add_decision(
                                    "SKIPPED",
                                    f"⏸️ {symbol}: Signal blocked by trade cutoff",
                                    "INFO",
                                    {"symbol": symbol, "reason": "trade_cutoff", "minutes_to_close": mins_left}
                                )
                        elif self.daily_pnl <= self.daily_pnl_limit:
                            self._add_decision(
                                "DAILY_LIMIT",
                                f"Daily loss limit hit (${self.daily_pnl:.2f}) - Trading halted",
                                "WARNING",
                                {"daily_pnl": self.daily_pnl, "limit": self.daily_pnl_limit}
                            )
                            logger.warning(f"🛑 Daily loss limit reached: ${self.daily_pnl:.2f}")
                            for opp in top_picks[:10]:
                                symbol = opp.get("symbol")
                                if not symbol:
                                    continue
                                self._add_decision(
                                    "SKIPPED",
                                    f"⏸️ {symbol}: Signal blocked by daily loss limit",
                                    "WARNING",
                                    {"symbol": symbol, "reason": "daily_loss_limit"}
                                )
                        else:
                            await self._execute_trades(top_picks)
                    elif not is_market_open and opportunities:
                        self._add_decision(
                            "SCAN",
                            f"Market closed - scan only mode ({len(opportunities)} opportunities)",
                            "INFO",
                            {"opportunities": len(opportunities), "analyzed": self.last_strategy_analyzed_count}
                        )
                        for opp in top_picks[:10]:
                            symbol = opp.get("symbol")
                            if not symbol:
                                continue
                            self._add_decision(
                                "SKIPPED",
                                f"⏸️ {symbol}: Signal noted but market is closed",
                                "INFO",
                                {"symbol": symbol, "reason": "market_closed"}
                            )

                    # Scan complete summary - always show what happened
                    scan_duration = (datetime.now() - scan_start).total_seconds()
                    if len(top_picks) > 0:
                        self._add_decision(
                            "THINKING",
                            f"✅ Scan #{loop_count} complete ({scan_duration:.1f}s): {len(top_picks)} actionable trades found",
                            "SUCCESS",
                            {"top_picks": [t.get("symbol") for t in top_picks[:5]], "duration": scan_duration}
                        )
                    elif len(analyzed) > 0:
                        self._add_decision(
                            "THINKING",
                            f"💭 Scan #{loop_count} complete ({scan_duration:.1f}s): {self.last_strategy_analyzed_count} analyzed, none meet criteria",
                            "INFO",
                            {"analyzed": self.last_strategy_analyzed_count, "duration": scan_duration}
                        )
                    else:
                        self._add_decision(
                            "THINKING",
                            f"💭 Scan #{loop_count} complete ({scan_duration:.1f}s): 0/{self.symbols_scanned} passed filters",
                            "INFO",
                            {"symbols_scanned": self.symbols_scanned, "duration": scan_duration}
                        )

                    # Reset error counter on success
                    consecutive_errors = 0
                    self.last_scan_heartbeat = datetime.utcnow()

                    # Periodic cache cleanup to prevent memory growth
                    if loop_count % 20 == 0:
                        self._cleanup_symbol_state_caches()

                    # 5. Wait for next scan
                    logger.info(f"⏳ Waiting {current_scan_interval}s for next scan...")
                    await asyncio.sleep(current_scan_interval)

                except Exception as e:
                    consecutive_errors += 1
                    logger.error(f"Error in trading loop (attempt {consecutive_errors}): {e}")
                    self._add_decision("ERROR", f"Trading loop error #{consecutive_errors}: {str(e)}", "ERROR", {})

                    # If too many consecutive errors, slow down
                    sleep_time = min(30 * consecutive_errors, 120)
                    await asyncio.sleep(sleep_time)

        except Exception as fatal_error:
            # This catches any error before the while loop starts
            import traceback
            tb = traceback.format_exc()
            logger.error(f"💀 FATAL ERROR in main trading loop: {fatal_error}")
            logger.error(f"Traceback:\n{tb}")
            self._add_decision(
                "ERROR",
                f"💀 FATAL ERROR in main loop: {str(fatal_error)[:200]}",
                "ERROR",
                {"error": str(fatal_error), "traceback": tb[:500]}
            )

    async def _position_monitor(self):
        """
        Monitor and manage existing positions using elite scale-out system.

        Elite Trading approach:
        - Scale out at 1R (50%), 2R (25%), 3R (25%)
        - Move stop to breakeven after 1R
        - Trail stop using ATR after 2R
        - Record wins/losses for discipline tracking
        """
        # Track ATR values for positions
        position_atr: Dict[str, float] = {}

        while self.running:
            try:
                positions = self.broker.get_positions()
                self._positions_cache_count = len(positions)
                self._positions_cache_time = datetime.now()

                for position in positions:
                    symbol = position.get("symbol")
                    current_price = position.get("currentPrice", 0)
                    entry_price = position.get("avgPrice", 0)
                    pnl_percent = position.get("unrealizedPnLPercent", 0)
                    unrealized_pnl = position.get("unrealizedPnL", 0)
                    quantity = position.get("quantity", 0)
                    is_long = quantity >= 0

                    if not symbol or current_price <= 0:
                        continue

                    df: Optional[pd.DataFrame] = None
                    try:
                        bars = self.market_data.get_historical_bars(symbol, "1 D", "5 mins")
                        if bars and len(bars) > 0:
                            df = pd.DataFrame(bars)
                    except Exception:
                        df = None

                    # Time-stop and max-hold exits to cut losers early
                    ctx = self._get_trade_context(symbol)
                    if ctx and ctx.entry_time:
                        held_minutes = (datetime.now() - ctx.entry_time).total_seconds() / 60
                        if held_minutes >= self.time_stop_minutes and pnl_percent < self.time_stop_min_pnl:
                            logger.warning(f"⏱️ TIME STOP: {symbol} {held_minutes:.0f}m, PnL {pnl_percent:.2f}%")
                            await self._close_position(symbol, f"Time stop {self.time_stop_minutes}m (PnL {pnl_percent:.2f}%)")
                            if symbol in position_atr:
                                del position_atr[symbol]
                            continue
                        if held_minutes >= self.max_hold_minutes and pnl_percent <= 0:
                            logger.warning(f"⏱️ MAX HOLD EXIT: {symbol} {held_minutes:.0f}m, PnL {pnl_percent:.2f}%")
                            await self._close_position(symbol, f"Max hold {self.max_hold_minutes}m (PnL {pnl_percent:.2f}%)")
                            if symbol in position_atr:
                                del position_atr[symbol]
                            continue

                    # Get ATR for this symbol if not cached
                    if symbol not in position_atr:
                        try:
                            if df is not None and len(df) > 0:
                                atr_series = atr(df, 14)
                                position_atr[symbol] = atr_series.iloc[-1] if len(atr_series) > 0 else current_price * 0.02
                            else:
                                position_atr[symbol] = current_price * 0.02  # Default 2% of price
                        except Exception as e:
                            logger.debug(f"ATR calculation failed for {symbol}, using 2% default: {e}")
                            position_atr[symbol] = current_price * 0.02

                    current_atr = position_atr.get(symbol, current_price * 0.02)

                    # === ELITE SCALE-OUT SYSTEM ===
                    # Check if we have a scale-out plan for this position
                    if symbol in self.elite_position_manager.positions:
                        scale_actions = self.elite_position_manager.check_scale_levels(
                            symbol, current_price, entry_price
                        )

                        for action in scale_actions:
                            if action["action"] == "SCALE_OUT_50_PCT":
                                scale_qty = action["quantity"]
                                logger.info(f"📈 SCALING OUT 50%: {symbol} - Selling {scale_qty} shares @ ${current_price:.2f} (1R hit)")
                                self.broker.place_market_order(symbol, scale_qty, "SELL")
                                self._add_decision("SCALE_OUT", f"50% scale-out {symbol} @ 1R", "SUCCESS", action)

                            elif action["action"] == "SCALE_OUT_25_PCT":
                                scale_qty = action["quantity"]
                                logger.info(f"📈 SCALING OUT 25%: {symbol} - Selling {scale_qty} shares @ ${current_price:.2f} (2R hit)")
                                self.broker.place_market_order(symbol, scale_qty, "SELL")
                                self._add_decision("SCALE_OUT", f"25% scale-out {symbol} @ 2R", "SUCCESS", action)

                            elif action["action"] == "CLOSE_REMAINING":
                                scale_qty = action["quantity"]
                                logger.info(f"🏆 CLOSING RUNNER: {symbol} - Selling {scale_qty} shares @ ${current_price:.2f} (3R hit)")
                                self.broker.place_market_order(symbol, scale_qty, "SELL")
                                self._add_decision("CLOSE_RUNNER", f"Runner closed {symbol} @ 3R", "SUCCESS", action)
                                # Record WIN in discipline tracker
                                self.discipline.record_trade(unrealized_pnl)

                            elif action["action"] == "MOVE_STOP_TO_BREAKEVEN":
                                logger.info(f"🛡️ BREAKEVEN STOP: {symbol} - Stop moved to ${entry_price:.2f}")
                                self._add_decision("BREAKEVEN", f"Stop moved to breakeven {symbol}", "INFO", action)

                            elif action["action"] == "ACTIVATE_TRAILING_STOP":
                                logger.info(f"📊 TRAILING ACTIVATED: {symbol}")

                        # Update trailing stop if active
                        new_stop = self.elite_position_manager.update_trailing_stop(
                            symbol, current_price, current_atr, trail_multiplier=1.0
                        )
                        if new_stop:
                            logger.info(f"📈 TRAILING STOP RAISED: {symbol} new stop ${new_stop:.2f}")

                    # TIGHTENED: ATR-based stop loss distance (1.5x ATR - tighter stops)
                    atr_stop_distance = current_atr * 1.5
                    atr_stop_percent = (atr_stop_distance / entry_price) * 100 if entry_price > 0 else 1.5

                    # ATR-based take profit (3.75x ATR for 2.5:1 risk/reward)
                    atr_profit_distance = current_atr * 3.75
                    atr_profit_percent = (atr_profit_distance / entry_price) * 100 if entry_price > 0 else 5.0

                    # Adjust targets based on risk posture
                    if self.risk_posture == "DEFENSIVE":
                        profit_target = atr_profit_percent * 0.8  # Take profit earlier
                        stop_target = atr_stop_percent * 0.8  # Tighter stop
                    elif self.risk_posture == "AGGRESSIVE":
                        profit_target = atr_profit_percent * 1.5  # Let winners run
                        stop_target = atr_stop_percent * 1.2  # Wider stop
                    else:  # BALANCED
                        profit_target = atr_profit_percent
                        stop_target = atr_stop_percent

                    # Check if position has scale-out plan with breakeven activated
                    has_breakeven = False
                    if symbol in self.elite_position_manager.positions:
                        plan = self.elite_position_manager.positions[symbol]
                        has_breakeven = plan.breakeven_activated
                        # Use the dynamic stop from scale-out plan
                        if has_breakeven:
                            stop_price = plan.current_stop
                            if current_price < stop_price:
                                logger.warning(f"🛑 STOP HIT: {symbol} @ ${current_price:.2f} (stop was ${stop_price:.2f})")
                                await self._close_position(symbol, f"Stop loss hit @ ${stop_price:.2f}")
                                # Record trade result
                                self.discipline.record_trade(unrealized_pnl)
                                if symbol in position_atr:
                                    del position_atr[symbol]
                                continue
                        if plan.trailing_activated and plan.current_stop:
                            if (is_long and current_price < plan.current_stop) or (not is_long and current_price > plan.current_stop):
                                logger.warning(f"🛑 TRAILING STOP HIT: {symbol} @ ${current_price:.2f} (stop was ${plan.current_stop:.2f})")
                                await self._close_position(symbol, f"Trailing stop hit @ ${plan.current_stop:.2f}")
                                self.discipline.record_trade(unrealized_pnl)
                                if symbol in position_atr:
                                    del position_atr[symbol]
                                continue

                    # Momentum failure + micro trailing exit (fast exits for fading trades)
                    if df is not None and len(df) >= max(10, self.trailing_lookback_bars):
                        try:
                            ema_series = ema(df["close"], self.momentum_exit_ema_period)
                            ema_value = float(ema_series.iloc[-1]) if len(ema_series) else 0.0
                            vwap_value = float(vwap(df).iloc[-1]) if len(df) else 0.0
                            recent_lows = df["low"].iloc[-self.trailing_lookback_bars:]
                            recent_highs = df["high"].iloc[-self.trailing_lookback_bars:]

                            if pnl_percent >= self.trailing_min_pnl:
                                if is_long and current_price < float(recent_lows.min()):
                                    logger.warning(f"📉 MICRO TRAIL EXIT: {symbol} broke last {self.trailing_lookback_bars} lows")
                                    await self._close_position(symbol, f"Micro trail: broke last {self.trailing_lookback_bars} lows")
                                    if symbol in position_atr:
                                        del position_atr[symbol]
                                    continue
                                if not is_long and current_price > float(recent_highs.max()):
                                    logger.warning(f"📈 MICRO TRAIL EXIT: {symbol} broke last {self.trailing_lookback_bars} highs")
                                    await self._close_position(symbol, f"Micro trail: broke last {self.trailing_lookback_bars} highs")
                                    if symbol in position_atr:
                                        del position_atr[symbol]
                                    continue

                            if pnl_percent >= self.momentum_exit_min_pnl and ema_value and vwap_value:
                                if is_long and current_price < ema_value and current_price < vwap_value:
                                    logger.warning(f"📉 MOMENTUM EXIT: {symbol} below EMA/VWAP")
                                    await self._close_position(symbol, "Momentum failure (below EMA/VWAP)")
                                    if symbol in position_atr:
                                        del position_atr[symbol]
                                    continue
                                if not is_long and current_price > ema_value and current_price > vwap_value:
                                    logger.warning(f"📈 MOMENTUM EXIT: {symbol} above EMA/VWAP")
                                    await self._close_position(symbol, "Momentum failure (above EMA/VWAP)")
                                    if symbol in position_atr:
                                        del position_atr[symbol]
                                    continue
                        except Exception as e:
                            logger.debug(f"Momentum/trailing exit check failed for {symbol}: {e}")

                    # Take profit at ATR-based target
                    if pnl_percent >= profit_target:
                        logger.info(f"Taking profit on {symbol}: +{pnl_percent:.2f}% (ATR target: {profit_target:.1f}%)")
                        await self._close_position(symbol, f"Take profit (ATR target {profit_target:.1f}%)")
                        if symbol in position_atr:
                            del position_atr[symbol]

                    # ATR-based stop loss
                    elif pnl_percent <= -stop_target:
                        logger.warning(f"ATR stop loss triggered for {symbol}: {pnl_percent:.2f}% (ATR stop: -{stop_target:.1f}%)")
                        await self._close_position(symbol, f"ATR stop loss (-{stop_target:.1f}%)")
                        if symbol in position_atr:
                            del position_atr[symbol]

                await asyncio.sleep(5)  # Check every 5 seconds

            except Exception as e:
                logger.error(f"Error in position monitor: {e}")
                await asyncio.sleep(5)

    async def _eod_liquidation_monitor(self):
        """
        CRITICAL DAY TRADING RULE: Close ALL positions before market close.

        This monitor runs continuously and will:
        - At 3:50 PM ET: Force close ALL open positions
        - Log all liquidations for audit trail
        - Prevent overnight risk exposure

        A real day trader NEVER holds overnight positions.
        """
        logger.info("📅 EOD Liquidation Monitor STARTED - Will close all positions at 3:50 PM ET")

        while self.running:
            try:
                now = self._get_market_now()
                today = now.strftime("%Y-%m-%d")

                # Reset flag for new trading day
                if self.last_liquidation_date != today:
                    self.eod_liquidation_done_today = False

                # Check if it's liquidation time (3:50 PM ET)
                if is_eod_liquidation_time(now=now) and not self.eod_liquidation_done_today:
                    logger.warning("⚠️ EOD LIQUIDATION TIME (3:50 PM ET) - Closing ALL positions!")
                    self._add_decision(
                        "EOD_LIQUIDATION",
                        "Mandatory end-of-day liquidation - Day traders do NOT hold overnight",
                        "CRITICAL",
                        {"time": datetime.now().isoformat()}
                    )

                    await self._liquidate_all_positions()

                    self.eod_liquidation_done_today = True
                    self.last_liquidation_date = today
                    logger.info("✓ EOD Liquidation complete - All positions closed")

                    # Run end-of-day learning cycle to analyze today's trades
                    logger.info("🧠 Running end-of-day ML learning cycle...")
                    await self._run_learning_cycle()

                # Check every 30 seconds
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Error in EOD liquidation monitor: {e}")
                await asyncio.sleep(30)

    async def _liquidate_all_positions(self):
        """
        Emergency liquidation of all open positions.
        Used for end-of-day close and emergency stops.

        CRITICAL: Must cancel all pending orders first, then liquidate.
        """
        try:
            # =====================================================
            # STEP 1: CANCEL ALL PENDING ORDERS FIRST
            # Shares held by pending orders cannot be sold
            # =====================================================
            if hasattr(self.broker, 'get_orders'):
                try:
                    open_orders = self.broker.get_orders(status="open")
                    if open_orders:
                        logger.warning(f"🚫 Cancelling {len(open_orders)} pending orders before liquidation...")
                        self._add_decision(
                            "LIQUIDATION",
                            f"Cancelling {len(open_orders)} pending orders first...",
                            "INFO",
                            {"order_count": len(open_orders)}
                        )
                        for order in open_orders:
                            order_id = order.get("id") or order.get("order_id")
                            symbol = order.get("symbol", "???")
                            if order_id:
                                try:
                                    self.broker.cancel_order(order_id)
                                    logger.info(f"Cancelled order {order_id} for {symbol}")
                                except Exception as cancel_err:
                                    logger.error(f"Failed to cancel order {order_id}: {cancel_err}")

                        # Wait for cancellations to process
                        import asyncio
                        await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"Error cancelling orders: {e}")

            # =====================================================
            # STEP 2: LIQUIDATE ALL POSITIONS
            # =====================================================
            positions = self.broker.get_positions()

            if not positions:
                logger.info("No positions to liquidate")
                return

            logger.warning(f"🔴 LIQUIDATING {len(positions)} POSITIONS")

            for position in positions:
                symbol = position.get("symbol")
                quantity = position.get("quantity", 0)
                current_price = position.get("currentPrice", 0)
                pnl = position.get("unrealizedPnL", 0)

                if symbol and quantity != 0:
                    try:
                        side = "SELL" if quantity > 0 else "BUY"
                        abs_qty = abs(quantity)

                        logger.warning(f"Liquidating {symbol}: {side} {abs_qty} shares @ ~${current_price:.2f} (P&L: ${pnl:.2f})")

                        if hasattr(self.broker, 'place_market_order'):
                            self.broker.place_market_order(symbol, abs_qty, side)
                        else:
                            self.strategy_engine.execute_order(symbol, side, abs_qty, "MARKET")

                        self._add_decision(
                            "LIQUIDATION",
                            f"EOD liquidation: {side} {abs_qty} {symbol} @ ${current_price:.2f}",
                            "EXECUTED",
                            {"symbol": symbol, "quantity": abs_qty, "side": side, "pnl": pnl}
                        )

                        # Track daily P&L
                        self.daily_pnl += pnl

                    except Exception as e:
                        error_str = str(e)
                        logger.error(f"Failed to liquidate {symbol}: {e}")

                        # If it's an "insufficient qty" error, try to cancel orders for this symbol
                        if "insufficient" in error_str.lower() or "held_for_orders" in error_str.lower():
                            self._add_decision(
                                "LIQUIDATION_FAILED",
                                f"⚠️ {symbol}: Shares blocked by pending orders - trying to cancel...",
                                "WARNING",
                                {"symbol": symbol, "error": error_str}
                            )
                            # Try to cancel orders for this specific symbol
                            if hasattr(self.broker, 'get_orders'):
                                try:
                                    all_orders = self.broker.get_orders(status="open")
                                    for order in all_orders:
                                        if order.get("symbol") == symbol:
                                            order_id = order.get("id") or order.get("order_id")
                                            if order_id:
                                                self.broker.cancel_order(order_id)
                                                logger.info(f"Cancelled blocking order {order_id} for {symbol}")
                                    # Wait and retry
                                    await asyncio.sleep(1)
                                    self.broker.place_market_order(symbol, abs_qty, side)
                                    self._add_decision(
                                        "LIQUIDATION",
                                        f"✅ {symbol} liquidated after cancelling blocking orders",
                                        "SUCCESS",
                                        {"symbol": symbol, "quantity": abs_qty}
                                    )
                                except Exception as retry_err:
                                    self._add_decision(
                                        "LIQUIDATION_FAILED",
                                        f"❌ {symbol}: Still cannot close - {str(retry_err)[:100]}",
                                        "ERROR",
                                        {"symbol": symbol}
                                    )
                        else:
                            self._add_decision(
                                "LIQUIDATION_FAILED",
                                f"Failed to close {symbol}: {error_str[:100]}",
                                "ERROR",
                                {"symbol": symbol, "error": error_str}
                            )

            logger.info(f"📊 Daily P&L after liquidation: ${self.daily_pnl:.2f}")

        except Exception as e:
            logger.error(f"Error in liquidate_all_positions: {e}")
            self._add_decision("ERROR", f"Liquidation error: {str(e)}", "ERROR", {})

    async def _scan_market(self) -> List[Dict[str, Any]]:
        """
        Scan market for trading opportunities using Warrior Trading criteria

        Enhanced scanning includes:
        - Power hour time weighting
        - News catalyst integration
        - Float filtering
        - Pattern detection (bull flag, flat top)
        - HIGH-PERFORMANCE: Uses cached data and parallel processing
        """
        logger.info("📊 _scan_market() called - beginning market scan")
        self._add_decision(
            "THINKING",
            "🔎 Starting market scan - fetching universe data...",
            "INFO",
            {"timestamp": datetime.now().isoformat()}
        )
        import time as time_module
        scan_start = time_module.perf_counter()

        try:
            universe = self._build_scan_universe()
            logger.info(f"Scanning {len(universe)} symbols...")
            self._add_decision(
                "THINKING",
                f"📈 Universe loaded: {len(universe)} symbols to scan",
                "INFO",
                {
                    "universe_size": len(universe),
                    "sample": universe[:5] if universe else [],
                    "hotlist_size": len(self.last_hotlist),
                    "hotlist_sample": self.last_hotlist[:5],
                }
            )

            # Get current time for power hour weighting
            now = self._get_market_now()
            current_hour = now.hour
            current_minute = now.minute
            in_power_hour = is_power_hour(current_hour, current_minute)

            if in_power_hour:
                logger.info("🔥 POWER HOUR ACTIVE - Signals will be boosted")

            market_data: Dict[str, pd.DataFrame] = {}

            # Scan ALL symbols - day traders need full market visibility
            # HIGH-PERFORMANCE: Use parallel processing for data fetching
            scan_limit = len(universe)  # Scan entire universe

            # Define fetch function for parallel processing
            def fetch_symbol_data(symbol: str) -> Optional[pd.DataFrame]:
                try:
                    # Try cache first from performance engine
                    cached_indicators = self.perf_engine.get_indicators_fast(symbol)
                    if cached_indicators:
                        # Add symbol to pre-computer watchlist
                        self.perf_engine.indicator_computer.add_symbol(symbol)

                    bars = self.market_data.get_historical_bars(symbol, "1 D", "5 mins")
                    if bars and len(bars) > 0:
                        return pd.DataFrame(bars)
                    return None
                except Exception:
                    return None

            # Fetch data in parallel using the performance engine's parallel processor
            with LATENCY.timed("parallel_data_fetch"):
                results = self.perf_engine.parallel_processor.process_symbols_sync(
                    universe[:scan_limit], fetch_symbol_data
                )

            # Collect valid results
            for symbol, df in results.items():
                if df is not None:
                    market_data[symbol] = df

            # Log how much data we got
            logger.info(f"📊 Got market data for {len(market_data)}/{len(universe)} symbols")
            self._add_decision(
                "THINKING",
                f"📊 Market data fetched: {len(market_data)}/{len(universe)} symbols have data",
                "INFO",
                {"symbols_with_data": len(market_data), "total_universe": len(universe)}
            )

            if not market_data:
                provider_error = getattr(self.market_data, "last_error", None)
                provider_error_at = getattr(self.market_data, "last_error_at", None)
                self.symbols_scanned = 0
                self.last_scanner_results = []
                self.last_analyzed_opportunities = []
                self._add_decision(
                    "SCAN",
                    "No market data returned. Check Alpaca credentials, market data subscription, and connectivity.",
                    "ERROR",
                    {
                        "symbols_scanned": 0,
                        "total_universe": len(universe),
                        "provider_error": provider_error,
                        "provider_error_at": provider_error_at,
                    },
                )
                return []

            # Record scan count as soon as we have valid market data
            self.symbols_scanned = len(market_data)
            self.last_market_symbols = list(market_data.keys())

            # Fetch daily bars for trend checks (cached to avoid rate limits)
            daily_data: Dict[str, pd.DataFrame] = {}
            try:
                now = datetime.now()
                refresh_daily = (
                    self._daily_data_cache_time is None
                    or (now - self._daily_data_cache_time).total_seconds() > self._daily_data_cache_ttl_seconds
                )
                daily_targets = list(market_data.keys()) if refresh_daily else [
                    sym for sym in market_data.keys() if sym not in self._daily_data_cache
                ]

                if daily_targets:
                    def fetch_daily_data(symbol: str) -> Optional[pd.DataFrame]:
                        try:
                            bars = self.market_data.get_historical_bars(symbol, "3 M", "1 day")
                            if bars and len(bars) > 0:
                                return pd.DataFrame(bars)
                            return None
                        except Exception:
                            return None

                    with LATENCY.timed("parallel_daily_fetch"):
                        daily_results = self.perf_engine.parallel_processor.process_symbols_sync(
                            daily_targets, fetch_daily_data
                        )

                    for symbol, df in daily_results.items():
                        if df is not None:
                            self._daily_data_cache[symbol] = df

                    if refresh_daily:
                        self._daily_data_cache_time = now

                if self._daily_data_cache and self._daily_data_cache_time is None:
                    self._daily_data_cache_time = now

                daily_data = {
                    sym: df for sym, df in self._daily_data_cache.items() if sym in market_data
                }

                self._add_decision(
                    "THINKING",
                    f"📅 Daily data cached: {len(daily_data)}/{len(market_data)} symbols",
                    "INFO",
                    {"symbols_with_daily": len(daily_data), "total_symbols": len(market_data)},
                )
            except Exception as e:
                logger.debug(f"Daily data fetch skipped: {e}")

            # Refresh short interest data (cached)
            try:
                await self._update_short_interest(list(market_data.keys()))
            except Exception as e:
                logger.debug(f"Short interest refresh skipped: {e}")

            # Fetch news catalysts for scanned symbols (async would be better)
            try:
                await self._update_news_catalysts(list(market_data.keys())[:50])  # Top 50 symbols
            except Exception as e:
                logger.debug(f"Could not fetch news catalysts: {e}")

            # Adjust screener thresholds based on profile/time
            self._apply_trade_frequency_profile(current_hour, current_minute, now=now)

            # Use enhanced ML screener with DETAILED evaluation
            try:
                session_info = self._get_market_session_info()
                market_status = {}
                if hasattr(self.market_data, "get_batch_snapshots"):
                    try:
                        market_status = self.market_data.get_batch_snapshots(list(market_data.keys()))
                    except Exception:
                        market_status = {}
                passed_list, all_evaluations = self.screener.rank_with_details(
                    market_data,
                    current_hour,
                    current_minute,
                    daily_data=daily_data,
                    market_status=market_status,
                    session_info=session_info,
                )
            except Exception as e:
                logger.error(f"Screener error: {e}")
                self.last_scanner_results = []
                self.last_analyzed_opportunities = []
                self.all_evaluations = []
                self.filter_summary = {}
                self._add_decision(
                    "SCAN",
                    "Screener failed while evaluating market data. Check logs for details.",
                    "ERROR",
                    {
                        "symbols_scanned": self.symbols_scanned,
                        "total_universe": len(universe),
                        "error": str(e),
                    },
                )
                return []

            # Store ALL evaluations for UI display (showing why each stock passed/failed)
            self.all_evaluations = all_evaluations  # Full list with pass/fail details

            # Calculate filter summary (how many failed at each filter)
            self.filter_summary = {
                "total": len(all_evaluations),
                "passed": len(passed_list),
                "failed_data": sum(1 for e in all_evaluations if e.get("filters", {}).get("data_check", {}).get("passed") == False),
                "failed_volume": sum(1 for e in all_evaluations if e.get("filters", {}).get("volume", {}).get("passed") == False),
                "failed_premarket": sum(1 for e in all_evaluations if e.get("filters", {}).get("premarket_volume", {}).get("passed") == False),
                "failed_price": sum(1 for e in all_evaluations if e.get("filters", {}).get("price", {}).get("passed") == False),
                "failed_volatility": sum(1 for e in all_evaluations if e.get("filters", {}).get("volatility", {}).get("passed") == False),
                "failed_daily_trend": sum(1 for e in all_evaluations if e.get("filters", {}).get("daily_trend", {}).get("passed") == False),
                "failed_rvol": sum(1 for e in all_evaluations if e.get("filters", {}).get("relative_volume", {}).get("passed") == False),
            }

            def is_watchlist_candidate(evaluation: Dict[str, Any]) -> bool:
                filters = evaluation.get("filters", {})
                premarket_filter = filters.get("premarket_volume", {})
                premarket_ok = premarket_filter.get("passed") or premarket_filter.get("skipped", False)
                return (
                    filters.get("data_check", {}).get("passed") is True
                    and filters.get("volume", {}).get("passed") is True
                    and premarket_ok is True
                    and filters.get("price", {}).get("passed") is True
                    and filters.get("volatility", {}).get("passed") is True
                )

            watchlist_evals = [e for e in all_evaluations if is_watchlist_candidate(e)]
            self.watchlist_candidates = [
                {
                    "symbol": e.get("symbol"),
                    "price": e.get("data", {}).get("price", 0),
                    "gap_percent": e.get("data", {}).get("gap_percent", 0),
                    "relative_volume": e.get("data", {}).get("relative_volume", 0),
                    "premarket_volume": e.get("data", {}).get("premarket_volume", 0),
                    "news_catalyst": e.get("data", {}).get("news_catalyst"),
                    "short_interest_pct": e.get("data", {}).get("short_interest_pct", 0),
                    "short_interest_days_to_cover": e.get("data", {}).get("short_interest_days_to_cover", 0),
                    "daily_trend": e.get("data", {}).get("daily_trend"),
                }
                for e in watchlist_evals
            ]
            self.filter_summary["watchlist"] = len(self.watchlist_candidates)

            # Log scan results
            pattern_count = sum(1 for e in passed_list if e.get("data", {}).get("pattern"))
            news_count = sum(1 for e in passed_list if e.get("data", {}).get("news_catalyst"))

            logger.info(f"Found {len(passed_list)} opportunities out of {len(all_evaluations)} evaluated")
            logger.info(f"  Patterns: {pattern_count}, News catalysts: {news_count}")

            # === DETAILED THINKING LOGS FOR UI ===
            # Log sample of FAILED stocks so user can see why they were rejected
            failed_stocks = [e for e in all_evaluations if not e.get("passed", False)]
            for fail in failed_stocks:  # Show all failures for full visibility
                symbol = fail.get("symbol", "???")
                filters = fail.get("filters", {})
                data = fail.get("data", {})

                # Find which filter failed
                fail_reasons = []
                if filters.get("data_check", {}).get("passed") == False:
                    fail_reasons.append("insufficient data")
                if filters.get("volume", {}).get("passed") == False:
                    actual = data.get("avg_volume", 0)
                    required = (
                        filters.get("volume", {}).get("threshold")
                        if filters.get("volume", {}).get("threshold") is not None
                        else filters.get("volume", {}).get("required", 0)
                    )
                    fail_reasons.append(f"volume {actual:,.0f} < {required:,.0f}")
                if filters.get("premarket_volume", {}).get("passed") == False:
                    actual = data.get("premarket_volume", 0)
                    required = filters.get("premarket_volume", {}).get("threshold", 0)
                    fail_reasons.append(f"premarket {actual:,.0f} < {required:,.0f}")
                if filters.get("price", {}).get("passed") == False:
                    price = data.get("price", 0)
                    fail_reasons.append(f"price ${price:.2f} outside range")
                if filters.get("volatility", {}).get("passed") == False:
                    atr_pct = data.get("atr_percent", 0)
                    fail_reasons.append(f"volatility {atr_pct:.1f}% too low")
                if filters.get("daily_trend", {}).get("passed") == False:
                    fail_reasons.append("daily trend below SMA")
                if filters.get("relative_volume", {}).get("passed") == False:
                    rvol = data.get("relative_volume", 0)
                    fail_reasons.append(f"rel.vol {rvol:.1f}x too low")

                reason_str = ", ".join(fail_reasons) if fail_reasons else "unknown"
                self._add_decision(
                    "THINKING",
                    f"❌ REJECTED {symbol}: {reason_str}",
                    "INFO",
                    {
                        "symbol": symbol,
                        "price": data.get("price", 0),
                        "volume": data.get("avg_volume", 0),
                        "rvol": data.get("relative_volume", 0),
                        "atr_pct": data.get("atr_percent", 0),
                        "reasons": fail_reasons,
                        **({
                            "debug": {
                                "data": data,
                                "filters": filters,
                            }
                        } if settings.screener_debug else {})
                    }
                )

            # Log PASSED stocks with their qualifying metrics
            for passed in passed_list:  # Show all qualifiers
                symbol = passed.get("symbol", "???")
                data = passed.get("data", {})
                scores = passed.get("scores", {})

                # Build qualification summary
                qualifications = []
                if scores.get("ml_score", 0) > 0.6:
                    qualifications.append(f"ML:{scores.get('ml_score', 0):.2f}")
                if data.get("relative_volume", 0) > 1.5:
                    qualifications.append(f"RVol:{data.get('relative_volume', 0):.1f}x")
                if data.get("pattern"):
                    qualifications.append(f"Pattern:{data.get('pattern')}")
                if data.get("news_catalyst"):
                    qualifications.append(f"News:{data.get('news_catalyst')}")
                if scores.get("momentum_score", 0) > 0.5:
                    qualifications.append(f"Mom:{scores.get('momentum_score', 0):.2f}")

                qual_str = " | ".join(qualifications) if qualifications else "baseline"
                self._add_decision(
                    "THINKING",
                    f"✅ QUALIFIED {symbol} @ ${data.get('price', 0):.2f}: {qual_str}",
                    "SUCCESS",
                    {
                        "symbol": symbol,
                        "price": data.get("price", 0),
                        "ml_score": scores.get("ml_score", 0),
                        "momentum_score": scores.get("momentum_score", 0),
                        "combined_score": scores.get("combined_score", 0),
                        "relative_volume": data.get("relative_volume", 0),
                        "atr_percent": data.get("atr_percent", 0),
                        "pattern": data.get("pattern"),
                        "news": data.get("news_catalyst"),
                        **({
                            "debug": {
                                "data": data,
                                "scores": scores,
                            }
                        } if settings.screener_debug else {})
                    }
                )

            # Store passed results in old format for compatibility
            self.last_scanner_results = [
                {
                    "symbol": e.get("symbol"),
                    "ml_score": e.get("scores", {}).get("ml_score", 0),
                    "momentum_score": e.get("scores", {}).get("momentum_score", 0),
                    "combined_score": e.get("scores", {}).get("combined_score", 0),
                    "last_price": e.get("data", {}).get("price", 0),
                    "avg_volume": e.get("data", {}).get("avg_volume", 0),
                    "today_volume": e.get("data", {}).get("today_volume", 0),
                    "relative_volume": e.get("data", {}).get("relative_volume", 0),
                    "float_millions": e.get("data", {}).get("float_millions"),
                    "float_score": e.get("scores", {}).get("float_score", 0),
                    "atr": e.get("data", {}).get("atr", 0),
                    "atr_percent": e.get("data", {}).get("atr_percent", 0),
                    "pattern": e.get("data", {}).get("pattern"),
                    "pattern_score": e.get("scores", {}).get("pattern_score", 0),
                    "news_catalyst": e.get("data", {}).get("news_catalyst"),
                    "news_score": e.get("scores", {}).get("news_score", 0),
                    "short_interest_pct": e.get("data", {}).get("short_interest_pct", 0),
                    "short_interest_score": e.get("scores", {}).get("short_interest_score", 0),
                    "short_interest_days_to_cover": e.get("data", {}).get("short_interest_days_to_cover", 0),
                    "gap_percent": e.get("data", {}).get("gap_percent", 0),
                    "time_multiplier": e.get("scores", {}).get("time_multiplier", 1.0),
                }
                for e in passed_list[:20]
            ]

            self._add_decision(
                "SCAN",
                f"Scanned {len(market_data)} symbols, watchlist {len(self.watchlist_candidates)}, found {len(passed_list)} opportunities",
                "INFO",
                {
                    "count": len(passed_list),
                    "watchlist_count": len(self.watchlist_candidates),
                    "total_evaluated": len(all_evaluations),
                    "patterns_detected": pattern_count,
                    "news_catalysts": news_count,
                    "power_hour": in_power_hour,
                    "top_symbols": [e.get("symbol") for e in passed_list[:5]],
                    "filter_summary": self.filter_summary,
                }
            )

            # Convert to old format for compatibility
            ranked = []
            for e in passed_list:
                ranked.append({
                    "symbol": e.get("symbol"),
                    "ml_score": e.get("scores", {}).get("ml_score", 0),
                    "momentum_score": e.get("scores", {}).get("momentum_score", 0),
                    "combined_score": e.get("scores", {}).get("combined_score", 0),
                    "last_price": e.get("data", {}).get("price", 0),
                    "avg_volume": e.get("data", {}).get("avg_volume", 0),
                    "today_volume": e.get("data", {}).get("today_volume", 0),
                    "relative_volume": e.get("data", {}).get("relative_volume", 0),
                    "float_millions": e.get("data", {}).get("float_millions"),
                    "float_score": e.get("scores", {}).get("float_score", 0),
                    "atr": e.get("data", {}).get("atr", 0),
                    "atr_percent": e.get("data", {}).get("atr_percent", 0),
                    "pattern": e.get("data", {}).get("pattern"),
                    "pattern_score": e.get("scores", {}).get("pattern_score", 0),
                    "news_catalyst": e.get("data", {}).get("news_catalyst"),
                    "news_score": e.get("scores", {}).get("news_score", 0),
                    "short_interest_pct": e.get("data", {}).get("short_interest_pct", 0),
                    "short_interest_score": e.get("scores", {}).get("short_interest_score", 0),
                    "short_interest_days_to_cover": e.get("data", {}).get("short_interest_days_to_cover", 0),
                    "gap_percent": e.get("data", {}).get("gap_percent", 0),
                    "time_multiplier": e.get("scores", {}).get("time_multiplier", 1.0),
                })

            return ranked

        except Exception as e:
            logger.error(f"Error scanning market: {e}")
            return []

    async def _update_short_interest(self, symbols: List[str]) -> None:
        """Fetch and update short interest data for symbols."""
        if not settings.polygon_api_key:
            return

        try:
            now = datetime.now()
            if (
                self._short_interest_cache_time is not None
                and (now - self._short_interest_cache_time).total_seconds() < self._short_interest_cache_ttl_seconds
            ):
                return

            unique_symbols = list(dict.fromkeys([s.upper() for s in symbols if s]))[:200]
            if not unique_symbols:
                return

            data = await self._short_interest_provider.fetch_short_interest(unique_symbols)
            if data:
                self.screener.set_short_interest_data(data)

                try:
                    data_file = Path("data/short_interest.json")
                    data_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(data_file, "w") as f:
                        json.dump(self.screener.short_interest, f, indent=2)
                except Exception as e:
                    logger.debug(f"Failed to persist short interest cache: {e}")

            self._short_interest_cache_time = now
            self._add_decision(
                "THINKING",
                f"🩳 Short interest updated: {len(data) if data else 0} symbols",
                "INFO",
                {"symbols_with_short_interest": len(data) if data else 0},
            )
        except Exception as e:
            logger.debug(f"Short interest update skipped: {e}")

    async def _update_news_catalysts(self, symbols: List[str]) -> None:
        """Fetch and update news catalysts for symbols"""
        import httpx
        import xml.etree.ElementTree as ET

        catalysts = {}
        user_agent = {"User-Agent": "ZellaAI/1.0"}

        for symbol in symbols[:20]:  # Limit to avoid rate limiting
            try:
                url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
                async with httpx.AsyncClient(timeout=5.0, headers=user_agent) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        root = ET.fromstring(response.text)
                        for item in root.findall(".//item")[:3]:
                            title = item.findtext("title") or ""
                            lower = title.lower()

                            # Categorize catalyst
                            catalyst = "OTHER"
                            if any(w in lower for w in ["earnings", "eps", "guidance", "revenue"]):
                                catalyst = "EARNINGS"
                            elif any(w in lower for w in ["fda", "approval", "clinical", "trial"]):
                                catalyst = "FDA"
                            elif any(w in lower for w in ["merger", "acquire", "acquisition", "buyout"]):
                                catalyst = "M&A"
                            elif any(w in lower for w in ["upgrade", "downgrade", "rating", "analyst"]):
                                catalyst = "ANALYST"

                            if catalyst != "OTHER":
                                catalysts[symbol] = {
                                    "catalyst": catalyst,
                                    "headline": title,
                                }
                                break
            except Exception as e:
                logger.debug(f"Failed to fetch news catalyst for {symbol}: {e}")
                continue

        # Update screener with catalysts
        self.screener.set_news_catalysts(catalysts)
        if catalysts:
            logger.info(f"Found {len(catalysts)} news catalysts: {list(catalysts.keys())}")

    async def _analyze_opportunities(
        self,
        opportunities: List[Dict[str, Any]],
        analyze_symbols: Optional[List[str]] = None,
        allowed_symbols: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Analyze each opportunity with ALL available strategies.

        HIGH-PERFORMANCE: Uses fast signal processor for sub-10ms processing.
        """
        import time as time_module
        analyze_start = time_module.perf_counter()
        analyzed = []
        analyzed_symbols = 0

        opp_by_symbol = {o.get("symbol"): o for o in opportunities if o.get("symbol")}
        symbols_to_analyze = analyze_symbols if analyze_symbols is not None else list(opp_by_symbol.keys())
        allowed = allowed_symbols if allowed_symbols is not None else set(symbols_to_analyze)

        for symbol in symbols_to_analyze:
            opp = opp_by_symbol.get(symbol, {"symbol": symbol})
            if not symbol:
                continue

            try:
                with LATENCY.timed(f"analyze_{symbol}"):
                    # HIGH-PERFORMANCE: Try pre-computed indicators first
                    cached_indicators = self.perf_engine.get_indicators_fast(symbol)

                    # Get data for this symbol
                    bars = self.market_data.get_historical_bars(symbol, "1 D", "5 mins")
                    if not bars:
                        continue

                    df = pd.DataFrame(bars)
                    current_price = df['close'].iloc[-1] if len(df) > 0 else 0

                    analyzed_symbols += 1

                # Test ALL strategies
                strategy_signals = []

                for strat_name, strategy in self.all_strategies.items():
                    if self.enabled_strategies != "ALL" and strat_name not in self.enabled_strategies:
                        continue

                    try:
                        signal = strategy.generate_signals(df)
                        if signal and signal.get("action") in ["BUY", "SELL"]:
                            # Apply learned weight multiplier from ML learning engine
                            base_confidence = signal.get("confidence", 0.5)
                            learned_weight = self.learning_engine.get_strategy_weight(strat_name)
                            adjusted_confidence = min(1.0, base_confidence * learned_weight)

                            strategy_signals.append({
                                "strategy": strat_name,
                                "action": signal.get("action"),
                                "confidence": adjusted_confidence,
                                "base_confidence": base_confidence,
                                "learned_weight": learned_weight,
                                "reason": signal.get("reason", ""),
                                # Include indicator data for UI visualization
                                "indicators": signal.get("indicators", {}),
                                "stop_loss": signal.get("stop_loss"),
                                "take_profit": signal.get("take_profit"),
                            })
                    except Exception as e:
                        logger.debug(f"Strategy {strat_name} failed for {symbol}: {e}")

                # Aggregate signals
                should_output = symbol in allowed

                if strategy_signals and should_output:
                    buy_signals = [s for s in strategy_signals if s["action"] == "BUY"]
                    sell_signals = [s for s in strategy_signals if s["action"] == "SELL"]

                    # Calculate aggregate confidence
                    if buy_signals:
                        avg_confidence = sum(s["confidence"] for s in buy_signals) / len(buy_signals)
                        strategy_names = [s["strategy"] for s in buy_signals]

                        # === DETAILED STRATEGY ANALYSIS LOG ===
                        top_reasons = [f"{s['strategy']}({s['confidence']:.0%})" for s in sorted(buy_signals, key=lambda x: x['confidence'], reverse=True)[:3]]
                        self._add_decision(
                            "ANALYZING",
                            f"🎯 {symbol} BUY signal: {len(buy_signals)} strategies agree ({', '.join(top_reasons)})",
                            "SUCCESS",
                            {
                                "symbol": symbol,
                                "action": "BUY",
                                "confidence": round(avg_confidence, 3),
                                "num_strategies": len(buy_signals),
                                "strategies": strategy_names,
                                "price": current_price,
                                "reasoning": [f"{s['strategy']}: {s['reason']}" for s in buy_signals[:5]]
                            }
                        )

                        analyzed.append({
                            **opp,
                            "recommended_action": "BUY",
                            "num_strategies": len(buy_signals),
                            "confidence": avg_confidence,
                            "strategies": strategy_names,
                            "strategy_signals": buy_signals,  # Include full signal data with indicators
                            "reasoning": " | ".join([f"{s['strategy']}: {s['reason']}" for s in buy_signals[:3]])
                        })
                    elif sell_signals:
                        avg_confidence = sum(s["confidence"] for s in sell_signals) / len(sell_signals)
                        strategy_names = [s["strategy"] for s in sell_signals]

                        # === DETAILED STRATEGY ANALYSIS LOG ===
                        top_reasons = [f"{s['strategy']}({s['confidence']:.0%})" for s in sorted(sell_signals, key=lambda x: x['confidence'], reverse=True)[:3]]
                        self._add_decision(
                            "ANALYZING",
                            f"🎯 {symbol} SELL signal: {len(sell_signals)} strategies agree ({', '.join(top_reasons)})",
                            "INFO",
                            {
                                "symbol": symbol,
                                "action": "SELL",
                                "confidence": round(avg_confidence, 3),
                                "num_strategies": len(sell_signals),
                                "strategies": strategy_names,
                                "price": current_price,
                                "reasoning": [f"{s['strategy']}: {s['reason']}" for s in sell_signals[:5]]
                            }
                        )

                        analyzed.append({
                            **opp,
                            "recommended_action": "SELL",
                            "num_strategies": len(sell_signals),
                            "confidence": avg_confidence,
                            "strategies": strategy_names,
                            "strategy_signals": sell_signals,  # Include full signal data with indicators
                            "reasoning": " | ".join([f"{s['strategy']}: {s['reason']}" for s in sell_signals[:3]])
                        })
                else:
                    # Log when no strategies fire - user wants to see this
                    if should_output and len(opportunities) <= 20:  # Only log for smaller sets to avoid spam
                        self._add_decision(
                            "THINKING",
                            f"📊 {symbol} @ ${current_price:.2f}: No strategy signals (0/{len(self.all_strategies)} strategies)",
                            "INFO",
                            {"symbol": symbol, "price": current_price, "strategies_tested": len(self.all_strategies)}
                        )

            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")

        # Store analyzed opportunities for UI display
        self.last_analyzed_opportunities = [
            {
                "symbol": a.get("symbol"),
                "recommended_action": a.get("recommended_action"),
                "num_strategies": a.get("num_strategies", 0),
                "confidence": round(a.get("confidence", 0), 3),
                "strategies": a.get("strategies", []),
                # Include full strategy signal data with indicators for Under The Hood visualization
                "strategy_signals": a.get("strategy_signals", []),
                "reasoning": a.get("reasoning", ""),
                "ml_score": round(a.get("ml_score", 0), 3),
                "momentum_score": round(a.get("momentum_score", 0), 3),
                "combined_score": round(a.get("combined_score", 0), 3),
                "last_price": round(a.get("last_price", 0), 2),
                "relative_volume": round(a.get("relative_volume", 0), 1),
                "pattern": a.get("pattern"),
                "news_catalyst": a.get("news_catalyst"),
                "atr": round(a.get("atr", 0), 2),
            }
            for a in analyzed[:15]
        ]
        self.last_strategy_analyzed_count = analyzed_symbols

        # Record total analysis time
        analyze_elapsed_ms = (time_module.perf_counter() - analyze_start) * 1000
        LATENCY.record("analyze_opportunities_total", analyze_elapsed_ms)
        logger.debug(
            f"Analysis completed in {analyze_elapsed_ms:.1f}ms for "
            f"{analyzed_symbols}/{len(opportunities)} opportunities"
        )

        return analyzed

    def _rank_opportunities(self, analyzed: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank opportunities by quality"""
        # Sort by number of strategies agreeing and confidence
        ranked = sorted(
            analyzed,
            key=lambda x: (x.get("num_strategies", 0), x.get("confidence", 0)),
            reverse=True
        )

        return ranked[:self.max_positions]

    def _check_circuit_breakers(self) -> Tuple[bool, str]:
        """
        Check circuit breakers for extreme market volatility.

        Returns:
            Tuple of (can_trade: bool, reason: str)
        """
        # Check SPY movement for market-wide volatility
        try:
            with self._cache_lock:
                spy_data = self._spy_data_cache
            if spy_data is not None and len(spy_data) >= 2:
                spy_open = float(spy_data.iloc[0].get("open", 0))
                spy_current = float(spy_data.iloc[-1].get("close", 0))
                if spy_open > 0:
                    spy_change_pct = abs((spy_current - spy_open) / spy_open * 100)
                    # Halt on >3% SPY move (extreme volatility)
                    if spy_change_pct > 3.0:
                        return False, f"Circuit breaker: SPY moved {spy_change_pct:.1f}% - extreme volatility"
                    # Reduce exposure on >2% SPY move
                    if spy_change_pct > 2.0:
                        logger.warning(f"⚠️ SPY moved {spy_change_pct:.1f}% - reducing position sizes")
        except Exception as e:
            logger.debug(f"Circuit breaker check error: {e}")

        # Check consecutive losses (already in discipline enforcer, but add hard limit here)
        if self.risk_manager.consecutive_losses >= 5:
            return False, "Circuit breaker: 5+ consecutive losses - cooling off"

        # Check daily loss limit hit
        if self.daily_pnl <= self.daily_pnl_limit:
            return False, f"Circuit breaker: Daily loss limit ${abs(self.daily_pnl_limit):.0f} hit"

        return True, ""

    def _detect_market_regime(self) -> str:
        """
        Detect current market regime based on SPY behavior.

        Returns:
            "TRENDING_UP" - Strong uptrend, favor longs
            "TRENDING_DOWN" - Strong downtrend, favor shorts
            "CHOPPY" - Range-bound, require higher confidence
            "EXTREME_VOLATILITY" - Don't trade
            "UNKNOWN" - Not enough data
        """
        try:
            with self._cache_lock:
                spy_data = self._spy_data_cache

            if spy_data is None or len(spy_data) < 20:
                return "UNKNOWN"

            # Calculate key metrics
            spy_close = spy_data["close"].astype(float)
            spy_high = spy_data["high"].astype(float)
            spy_low = spy_data["low"].astype(float)

            current_price = float(spy_close.iloc[-1])
            open_price = float(spy_data.iloc[0].get("open", current_price))

            # Calculate VWAP approximation (typical price * volume weighted)
            if "volume" in spy_data.columns:
                typical_price = (spy_high + spy_low + spy_close) / 3
                cumulative_tpv = (typical_price * spy_data["volume"].astype(float)).cumsum()
                cumulative_vol = spy_data["volume"].astype(float).cumsum()
                vwap_series = cumulative_tpv / cumulative_vol
                spy_vwap = float(vwap_series.iloc[-1])
            else:
                spy_vwap = current_price

            # Calculate intraday range
            day_high = float(spy_high.max())
            day_low = float(spy_low.min())
            day_range_pct = ((day_high - day_low) / day_low * 100) if day_low > 0 else 0

            # Calculate trend (price vs VWAP and open)
            above_vwap = current_price > spy_vwap
            above_open = current_price > open_price
            change_pct = ((current_price - open_price) / open_price * 100) if open_price > 0 else 0

            # EXTREME VOLATILITY: >2.5% range in single day
            if day_range_pct > 2.5:
                return "EXTREME_VOLATILITY"

            # TRENDING UP: Above VWAP, above open, >0.3% gain
            if above_vwap and above_open and change_pct > 0.3:
                return "TRENDING_UP"

            # TRENDING DOWN: Below VWAP, below open, >0.3% loss
            if not above_vwap and not above_open and change_pct < -0.3:
                return "TRENDING_DOWN"

            # CHOPPY: Price crossing VWAP multiple times or small range
            # Count VWAP crosses in last 10 bars
            if len(spy_close) >= 10 and len(vwap_series) >= 10:
                recent_close = spy_close.tail(10).values
                recent_vwap = vwap_series.tail(10).values
                crosses = 0
                for i in range(1, len(recent_close)):
                    if (recent_close[i] > recent_vwap[i]) != (recent_close[i-1] > recent_vwap[i-1]):
                        crosses += 1
                if crosses >= 3:  # 3+ VWAP crosses = choppy
                    return "CHOPPY"

            # Default to UNKNOWN if no clear regime
            if abs(change_pct) < 0.2:
                return "CHOPPY"

            return "UNKNOWN"

        except Exception as e:
            logger.debug(f"Market regime detection error: {e}")
            return "UNKNOWN"

    async def _execute_trades(self, opportunities: List[Dict[str, Any]]):
        """
        Execute trades for top opportunities using Warrior Trading position sizing

        Position sizing formula: shares = risk_amount / ATR_stop_distance
        This ensures consistent risk per trade regardless of stock volatility
        """
        if not self.risk_manager.can_trade():
            logger.warning("Risk manager blocks trading")
            return

        # Check circuit breakers for extreme volatility
        can_trade, circuit_reason = self._check_circuit_breakers()
        if not can_trade:
            logger.warning(f"🚨 {circuit_reason}")
            self._add_decision("CIRCUIT_BREAKER", circuit_reason, "HALT", {})
            return

        # TIME-OF-DAY FILTER: Avoid dangerous trading periods
        now = datetime.now()
        mins_open = minutes_since_open(now=now)

        # Avoid first 5 minutes (too volatile, spreads wide)
        if mins_open < 5:
            self._add_decision("TIME_FILTER", "Skipping first 5 minutes - spreads too wide", "INFO", {"minutes_open": mins_open})
            return

        # Avoid lunch chop (11:30-1:00 ET = 120-210 minutes after open)
        if 120 <= mins_open <= 210:
            # Still allow high-confidence trades during lunch
            opportunities = [o for o in opportunities if o.get("confidence", 0) >= 0.70]
            if not opportunities:
                self._add_decision("TIME_FILTER", "Lunch chop filter - only high confidence trades allowed", "INFO", {"minutes_open": mins_open})
                return

        # Avoid afternoon/EOD (3:00 PM onwards = 330 mins after 9:30 open)
        # This is when institutions close positions, causing erratic moves
        if mins_open >= 330:
            self._add_decision("TIME_FILTER", "No new entries after 3:00 PM ET - EOD risk", "INFO", {"minutes_open": mins_open})
            return

        # Avoid last 30 minutes completely (erratic, EOD orders, stop hunting)
        if mins_open >= 360:  # 6 hours = 360 minutes = 3:30 PM ET
            self._add_decision("TIME_FILTER", "Skipping last 30 minutes - extreme EOD volatility", "INFO", {"minutes_open": mins_open})
            return

        # MARKET REGIME DETECTION: Check SPY trend
        market_regime = self._detect_market_regime()
        if market_regime == "CHOPPY":
            # In choppy markets, require higher confidence
            opportunities = [o for o in opportunities if o.get("confidence", 0) >= 0.65]
            if not opportunities:
                self._add_decision("REGIME_FILTER", "Choppy market - only high confidence trades", "INFO", {"regime": market_regime})
                return
        elif market_regime == "EXTREME_VOLATILITY":
            # Don't trade in extreme conditions
            self._add_decision("REGIME_FILTER", "Extreme volatility detected - halting new entries", "HALT", {"regime": market_regime})
            return

        account = self.broker.get_account_summary()
        account_value = float(account.get("NetLiquidation", 0) or 0)
        buying_power = float(account.get("BuyingPower", 0) or 0)

        all_positions = self.broker.get_positions()
        current_positions = len(all_positions)

        # Build map of current exposure per symbol
        MAX_SYMBOL_EXPOSURE_PCT = 0.15  # Never more than 15% of account in one symbol
        symbol_exposure = {}
        for pos in all_positions:
            sym = pos.get("symbol")
            qty = abs(float(pos.get("quantity", 0) or 0))
            price = float(pos.get("currentPrice", 0) or pos.get("avgCost", 0) or 0)
            if sym and qty > 0 and price > 0:
                symbol_exposure[sym] = (qty * price) / account_value if account_value > 0 else 1.0

        # Check if we're in power hour for signal boost
        now = datetime.now()
        in_power_hour = is_power_hour(now.hour, now.minute)
        time_mult = power_hour_multiplier(now.hour, now.minute)

        for opp in opportunities:
            if current_positions >= self.max_positions:
                logger.info(f"Max positions ({self.max_positions}) reached")
                break

            symbol = opp.get("symbol")

            # CRITICAL: Check if we already have max exposure in this symbol
            current_exposure = symbol_exposure.get(symbol, 0)
            if current_exposure >= MAX_SYMBOL_EXPOSURE_PCT:
                self._add_decision(
                    "SKIPPED",
                    f"⛔ {symbol}: Already at max exposure ({current_exposure:.1%} >= {MAX_SYMBOL_EXPOSURE_PCT:.0%})",
                    "WARNING",
                    {"symbol": symbol, "current_exposure_pct": current_exposure, "max_allowed_pct": MAX_SYMBOL_EXPOSURE_PCT}
                )
                continue

            # DANGEROUS STOCK FILTER - Avoid leveraged ETFs and ultra-speculative names
            # These are designed to decay and are NOT suitable for algorithmic trading
            BLACKLISTED_SYMBOLS = {
                # 3x Leveraged ETFs (decay over time, extreme volatility)
                "SOXS", "SOXL", "TQQQ", "SQQQ", "UVXY", "SVXY", "SPXU", "SPXS",
                "UPRO", "SDOW", "UDOW", "TZA", "TNA", "LABU", "LABD", "JNUG", "JDST",
                "NUGT", "DUST", "ERX", "ERY", "FAS", "FAZ", "TECL", "TECS",
                # 2x Leveraged ETFs
                "SSO", "SDS", "QLD", "QID", "UCO", "SCO",
                # Penny stocks / meme stocks with extreme manipulation risk
                "AMC",  # Meme stock, heavily manipulated
            }
            if symbol in BLACKLISTED_SYMBOLS:
                self._add_decision(
                    "SKIPPED",
                    f"⛔ {symbol}: Blacklisted (leveraged ETF or high manipulation risk)",
                    "WARNING",
                    {"symbol": symbol, "reason": "blacklisted_dangerous_instrument"}
                )
                continue

            action = opp.get("recommended_action")
            confidence = opp.get("confidence", 0)
            num_strategies = opp.get("num_strategies", 0)
            strategies = opp.get("strategies", [])

            # Apply power hour boost to confidence
            adjusted_confidence = confidence * time_mult

            # Learning-aware time filter (avoid time windows with poor performance)
            try:
                minutes_open = minutes_since_open(now=now)
                time_of_day = "opening" if minutes_open < 30 else "morning" if minutes_open < 120 else "midday" if minutes_open < 240 else "afternoon" if minutes_open < 360 else "power_hour"
                if hasattr(self, "learning_engine") and not self.learning_engine.should_trade_now(time_of_day):
                    self._add_decision(
                        "SKIPPED",
                        f"⏸️ {symbol}: Learning recommends skipping {time_of_day}",
                        "INFO",
                        {"symbol": symbol, "time_of_day": time_of_day}
                    )
                    continue
            except Exception:
                pass

            # QUALITY THRESHOLDS - Win rate matters more than trade count
            # Key insight: 5 winning trades beats 20 losing ones
            if in_power_hour:
                # Power hour = more volatility = require stronger signals
                min_confidence = 0.65 if self.risk_posture == "AGGRESSIVE" else 0.70 if self.risk_posture == "BALANCED" else 0.75
                min_strategies = 2  # Require strategy agreement
            else:
                # Normal hours: Solid confidence required
                min_confidence = 0.60 if self.risk_posture == "AGGRESSIVE" else 0.65 if self.risk_posture == "BALANCED" else 0.70
                min_strategies = 2  # Require strategy agreement

            # Trade frequency profile adjustments (smaller adjustments)
            if self.trade_frequency_profile == "active":
                min_confidence -= 0.03  # Slightly more trades
                min_strategies = 2  # Still require agreement
            elif self.trade_frequency_profile == "conservative":
                min_confidence += 0.05  # Higher quality
                min_strategies = 3  # Strong consensus

            # Global minimum - never trade below this regardless of settings
            if adjusted_confidence < self.min_confidence_threshold:
                self._add_decision(
                    "CONSIDERING",
                    f"⚠️ {symbol}: Confidence {adjusted_confidence:.0%} below min threshold {self.min_confidence_threshold:.0%}",
                    "INFO",
                    {"symbol": symbol, "confidence": adjusted_confidence, "threshold": self.min_confidence_threshold, "reason": "below_global_min"}
                )
                continue

            # Learning-based confidence adjustment (use average, not max, to stay active)
            learned_threshold = None
            try:
                if hasattr(self, "learning_engine"):
                    learned_threshold = self.learning_engine.get_recommended_confidence_threshold()
            except Exception:
                learned_threshold = None
            if learned_threshold:
                # Average our threshold with learned threshold (weighted 60/40 toward our setting)
                # This prevents learning from making us too conservative
                min_confidence = (min_confidence * 0.6) + (learned_threshold * 0.4)

            if adjusted_confidence < min_confidence:
                self._add_decision(
                    "CONSIDERING",
                    f"⚠️ {symbol}: Confidence {adjusted_confidence:.0%} below {self.risk_posture} threshold {min_confidence:.0%}",
                    "INFO",
                    {"symbol": symbol, "confidence": adjusted_confidence, "required": min_confidence, "risk_posture": self.risk_posture, "learned_threshold": learned_threshold}
                )
                continue

            if num_strategies < min_strategies:
                self._add_decision(
                    "CONSIDERING",
                    f"⚠️ {symbol}: Only {num_strategies} strategies agree (need {min_strategies}+)",
                    "INFO",
                    {"symbol": symbol, "num_strategies": num_strategies, "required": min_strategies, "strategies": strategies}
                )
                continue
            elif min_strategies == 1 and num_strategies >= 1:
                self._add_decision(
                    "SYSTEM",
                    f"✅ {symbol}: Independent strategy mode (single strategy allowed)",
                    "INFO",
                    {"symbol": symbol, "num_strategies": num_strategies}
                )

            # Log that we're actively considering this trade
            self._add_decision(
                "CONSIDERING",
                f"🔍 {symbol}: Evaluating trade - {num_strategies} strategies @ {adjusted_confidence:.0%} confidence",
                "INFO",
                {"symbol": symbol, "action": action, "confidence": adjusted_confidence, "strategies": strategies}
            )

            try:
                price = opp.get("last_price", 0)
                if price <= 0:
                    continue

                # === PRO-LEVEL VALIDATION ===
                # These filters separate profitable traders from retail losers
                snapshot = {}
                if hasattr(self.market_data, "get_market_snapshot"):
                    try:
                        snapshot = self.market_data.get_market_snapshot(symbol) or {}
                    except Exception:
                        snapshot = {}

                halted = bool(snapshot.get("halted", False))
                luld_info = snapshot.get("luld") or {}
                luld_indicator = luld_info.get("indicator") if isinstance(luld_info, dict) else None
                if halted or (luld_indicator and str(luld_indicator).lower() not in {"n", "normal"}):
                    self._add_decision(
                        "SKIPPED",
                        f"⏸️ {symbol}: Trading halted/LULD active",
                        "INFO",
                        {
                            "symbol": symbol,
                            "halted": halted,
                            "luld_indicator": luld_indicator,
                        },
                    )
                    continue

                bid = snapshot.get("bid") or opp.get("bid") or (price * 0.999)
                ask = snapshot.get("ask") or opp.get("ask") or (price * 1.001)
                current_volume = (
                    snapshot.get("volume")
                    or opp.get("today_volume")
                    or opp.get("volume")
                    or 0
                )
                avg_volume = opp.get("avg_volume", current_volume)
                atr_percent = opp.get("atr_percent", 2.0)

                # Get current positions for correlation check
                current_pos_list = self.broker.get_positions()

                # Run pro validation
                validation = self.pro_validator.validate_trade(
                    symbol=symbol,
                    bid=bid,
                    ask=ask,
                    price=price,
                    current_volume=current_volume,
                    avg_volume=avg_volume,
                    atr_percent=atr_percent,
                    current_positions=current_pos_list,
                    daily_pnl=self.daily_pnl,
                    vix_level=0,  # TODO: Add VIX fetch
                    minutes_since_open=minutes_since_open(now=now)
                )

                if not validation["approved"]:
                    for rejection in validation["rejections"]:
                        logger.info(f"⛔ {symbol} REJECTED: {rejection}")
                    self._add_decision(
                        "REJECTED",
                        f"{symbol} failed pro validation",
                        "INFO",
                        {"rejections": validation["rejections"], "symbol": symbol}
                    )
                    continue

                # === ELITE SYSTEM GRADING ===
                # Check discipline (revenge trade prevention, max winners, etc.)
                can_trade, halt_reason = self.discipline.can_trade()
                if not can_trade:
                    logger.warning(f"🛑 Trading halted: {halt_reason}")
                    self._add_decision("HALTED", halt_reason, "WARNING", {})
                    break  # Stop processing all opportunities

                # Get multi-timeframe data if available
                try:
                    bars_5m = self.market_data.get_historical_bars(symbol, "1 D", "5 mins")
                    bars_15m = self.market_data.get_historical_bars(symbol, "2 D", "15 mins")
                    bars_1h = self.market_data.get_historical_bars(symbol, "5 D", "1 hour")

                    # Get SPY for relative strength
                    if self._spy_data_cache is None or (datetime.now() - self._spy_cache_time).seconds > 300:
                        spy_bars = self.market_data.get_historical_bars("SPY", "1 D", "5 mins")
                        if spy_bars:
                            self._spy_data_cache = pd.DataFrame(spy_bars)
                            self._spy_cache_time = datetime.now()

                    if bars_5m and bars_15m and bars_1h and self._spy_data_cache is not None:
                        df_5m = pd.DataFrame(bars_5m)
                        df_15m = pd.DataFrame(bars_15m)
                        df_1h = pd.DataFrame(bars_1h)

                        # Calculate risk/reward
                        atr_temp = opp.get("atr", price * 0.02)
                        risk = atr_temp * 1.5
                        reward = atr_temp * 3.75
                        rr_ratio = reward / risk if risk > 0 else 2.0

                        elite_analysis = self.elite_system.full_analysis(
                            symbol=symbol,
                            data_5m=df_5m,
                            data_15m=df_15m,
                            data_1h=df_1h,
                            spy_data=self._spy_data_cache,
                            current_price=price,
                            open_price=opp.get("open", price),
                            volume=current_volume,
                            avg_volume=avg_volume,
                            confidence=adjusted_confidence,
                            risk_reward_ratio=rr_ratio
                        )

                        setup_grade = elite_analysis.get("grade", "B")
                        elite_size_mult = elite_analysis.get("position_size_multiplier", 1.0)

                        # Only trade A+, A, or B setups
                        if setup_grade == "F":
                            factors = elite_analysis.get("grade_details", {}).get("factors", [])
                            factor_str = ", ".join(factors[:3]) if factors else "weak setup"
                            logger.info(f"⛔ {symbol} GRADE F - Setup rejected")
                            self._add_decision(
                                "REJECTED",
                                f"❌ {symbol} GRADE F: {factor_str}",
                                "WARNING",
                                {
                                    "symbol": symbol,
                                    "grade": setup_grade,
                                    "factors": factors,
                                    "analysis": elite_analysis.get("analysis", {})
                                }
                            )
                            continue
                        elif setup_grade == "C":
                            factors = elite_analysis.get("grade_details", {}).get("factors", [])
                            factor_str = ", ".join(factors[:3]) if factors else "marginal"
                            logger.info(f"⚠️ {symbol} GRADE C - Skipping marginal setup")
                            self._add_decision(
                                "CONSIDERING",
                                f"⚠️ {symbol} GRADE C: Skipping marginal setup ({factor_str})",
                                "INFO",
                                {"symbol": symbol, "grade": setup_grade, "factors": factors}
                            )
                            continue

                        # Passed elite grading - log the analysis
                        factors = elite_analysis.get("grade_details", {}).get("factors", [])
                        factor_str = ", ".join(factors[:3]) if factors else "solid setup"
                        logger.info(f"📊 {symbol} GRADE {setup_grade} - Elite analysis passed")
                        self._add_decision(
                            "CONSIDERING",
                            f"✅ {symbol} GRADE {setup_grade}: {factor_str}",
                            "SUCCESS",
                            {
                                "symbol": symbol,
                                "grade": setup_grade,
                                "factors": factors,
                                "size_multiplier": elite_size_mult
                            }
                        )

                        # Log key analysis points
                        analysis = elite_analysis.get("analysis", {})
                        mtf = analysis.get("multi_timeframe", {})
                        rs = analysis.get("relative_strength", {})
                        sr = analysis.get("support_resistance", {})

                        logger.info(f"   MTF: {mtf.get('trade_direction', 'N/A')} (alignment: {mtf.get('alignment_score', 0):.2f})")
                        logger.info(f"   RS: {rs.get('rs_ratio', 1):.2f}x SPY {'(LEADER)' if rs.get('is_leader') else '(LAGGARD)' if rs.get('is_laggard') else ''}")
                        logger.info(f"   S/R: Support ${sr.get('nearest_support', 0):.2f} | Resistance ${sr.get('nearest_resistance', 0):.2f}")
                    else:
                        elite_size_mult = 1.0
                        setup_grade = "B"  # Default if can't get data

                except Exception as e:
                    logger.debug(f"Elite analysis skipped for {symbol}: {e}")
                    elite_size_mult = 1.0
                    setup_grade = "B"

                # Apply volatility adjustments from pro validator
                vol_adjustments = validation.get("adjustments", {})
                position_size_mult = vol_adjustments.get("position_size_multiplier", 1.0)
                stop_mult = vol_adjustments.get("stop_loss_multiplier", 1.0)

                if validation.get("warnings"):
                    for warning in validation["warnings"]:
                        logger.warning(f"⚠️ {symbol}: {warning}")

                # Get ATR for position sizing (Warrior Trading method)
                atr_value = opp.get("atr", 0)
                if atr_value <= 0:
                    # Calculate ATR if not provided
                    try:
                        bars = self.market_data.get_historical_bars(symbol, "1 D", "5 mins")
                        if bars and len(bars) > 0:
                            df = pd.DataFrame(bars)
                            atr_series = atr(df, 14)
                            atr_value = atr_series.iloc[-1] if len(atr_series) > 0 else price * 0.02
                        else:
                            atr_value = price * 0.02  # Default 2% of price
                    except Exception as e:
                        logger.debug(f"ATR calculation failed for {symbol} in trade execution, using 2% default: {e}")
                        atr_value = price * 0.02

                # ATR-based position sizing (Warrior Trading formula)
                # TIGHTENED: Risk 0.5-1.5% of account, stop at 1.5x ATR
                # Smaller losses = more chances to be profitable
                base_risk_percent = 0.005 if self.risk_posture == "DEFENSIVE" else 0.01 if self.risk_posture == "BALANCED" else 0.015
                base_atr_multiplier = 1.5  # 1.5x ATR stop loss (tighter than before)

                # Apply volatility regime adjustments from pro validator
                # AND elite system grade multiplier (A=100%, B=75%, etc.)
                combined_size_mult = position_size_mult * elite_size_mult
                risk_percent = base_risk_percent * combined_size_mult
                atr_multiplier = base_atr_multiplier * stop_mult

                quantity = calculate_position_size_atr(
                    account_value=account_value,
                    risk_percent=risk_percent,
                    entry_price=price,
                    atr_value=atr_value,
                    atr_multiplier=atr_multiplier,
                    max_position_pct=MAX_SYMBOL_EXPOSURE_PCT  # Cap at 15% of account
                )

                if quantity <= 0:
                    continue

                # CRITICAL: Cap position to remaining allowed exposure for this symbol
                current_sym_exposure = symbol_exposure.get(symbol, 0)
                remaining_allowed_exposure = MAX_SYMBOL_EXPOSURE_PCT - current_sym_exposure
                if remaining_allowed_exposure <= 0:
                    continue  # Already at max (shouldn't happen due to check above, but safety)
                max_shares_by_exposure = int((account_value * remaining_allowed_exposure) / price)
                if max_shares_by_exposure < quantity:
                    logger.info(f"📉 {symbol}: Capping position from {quantity} to {max_shares_by_exposure} shares (exposure limit)")
                    quantity = max_shares_by_exposure
                    if quantity <= 0:
                        continue

                # Ensure we don't exceed buying power
                position_value = quantity * price
                if position_value > buying_power * 0.2:  # Max 20% of buying power per trade
                    quantity = int((buying_power * 0.2) / price)
                    if quantity <= 0:
                        continue

                # Calculate ATR-based stop loss and take profit prices
                # Using 2.5:1 risk/reward ratio for better profitability
                stop_loss_price = price - (atr_value * atr_multiplier)
                take_profit_price = price + (atr_value * atr_multiplier * 2.5)  # 2.5:1 risk/reward

                # Calculate scale-out levels (Pro exit strategy)
                # 1R = risk distance, 2R = 2x risk, 3R = 3x risk
                risk_distance = atr_value * atr_multiplier
                take_profit_1r = price + risk_distance  # 50% exit
                take_profit_2r = price + (risk_distance * 2)  # 25% exit
                take_profit_3r = price + (risk_distance * 2.5)  # Final 25%

                # === EDGE ENGINE ANALYSIS ===
                # This gives us the competitive advantage: algo detection, flow prediction, sentiment
                edge_analysis = None
                edge_action = None
                edge_boost = 0.0
                use_stealth = False

                try:
                    # Get data for edge analysis
                    symbol_state = self._get_symbol_state(symbol)
                    edge_data = symbol_state.bars_cache
                    if edge_data is None:
                        bars = self.market_data.get_historical_bars(symbol, "1 D", "5 mins")
                        if bars:
                            edge_data = pd.DataFrame(bars)
                            symbol_state.bars_cache = edge_data
                            symbol_state.bars_cache_time = datetime.now()

                    if edge_data is not None and len(edge_data) > 50:
                        with self._edge_lock:
                            edge_analysis = self.edge_engine.get_edge(symbol, edge_data)

                        if edge_analysis:
                            edge_action = edge_analysis.get("action", "HOLD")
                            edge_score = edge_analysis.get("edge_score", 0)

                            # Edge signals boost confidence
                            sentiment = edge_analysis.get("sentiment", {})
                            flow = edge_analysis.get("flow_prediction", {})

                            # STRONG BUY signals from sentiment (capitulation, panic)
                            if sentiment.get("exploit_signal") in ["BUY_CAPITULATION", "BUY_PANIC"]:
                                edge_boost = 0.15  # 15% confidence boost
                                logger.info(f"⚡ EDGE: {symbol} - {sentiment['exploit_signal']} detected! (+15% confidence)")

                            # Flow prediction alignment
                            if flow and flow.get("direction") == "UP" and action == "BUY" and flow.get("confidence", 0) > 0.5:
                                edge_boost += 0.10  # 10% boost for aligned flow
                                logger.info(f"⚡ EDGE: {symbol} - Flow predicting UP ({flow['confidence']:.0%}) - Aligned! (+10%)")

                            elif flow and flow.get("direction") == "DOWN" and action == "BUY" and flow.get("confidence", 0) > 0.6:
                                # Flow predicting DOWN but we want to BUY - reduce confidence
                                edge_boost -= 0.15
                                logger.warning(f"⚠️ EDGE: {symbol} - Flow predicting DOWN - Counter to our action (-15%)")

                            # FADE signal - we're countering retail FOMO
                            if sentiment.get("fomo_active") and action == "BUY":
                                edge_boost -= 0.20  # Don't chase FOMO
                                logger.warning(f"⚠️ EDGE: {symbol} - FOMO active! Don't chase. (-20%)")

                            # Algo detection - if predictable algos are present, we might have edge
                            algo_counter = edge_analysis.get("algo_counter", {})
                            if algo_counter and algo_counter.get("predictability", 0) > 0.7:
                                logger.info(f"⚡ EDGE: {symbol} - Algo detected (predictability: {algo_counter['predictability']:.0%})")

                            # Use stealth execution for better fills
                            use_stealth = edge_analysis.get("recommended_execution") == "STEALTH"

                            # Log edge summary
                            logger.info(f"   EDGE Score: {edge_score:.2f} | Action: {edge_action} | Boost: {edge_boost:+.0%}")

                except Exception as e:
                    logger.debug(f"Edge analysis skipped for {symbol}: {e}")

                # Apply edge boost to confidence
                final_confidence = adjusted_confidence + edge_boost

                # If edge strongly conflicts, skip the trade
                if edge_boost <= -0.15 and adjusted_confidence < 0.80:
                    logger.warning(f"⛔ {symbol} SKIPPED: Edge conflict (boost: {edge_boost:+.0%}, confidence would be {final_confidence:.0%})")
                    self._add_decision(
                        "EDGE_REJECTED",
                        f"{symbol} rejected due to edge conflict",
                        "INFO",
                        {"edge_boost": edge_boost, "original_confidence": adjusted_confidence, "edge_analysis": edge_analysis}
                    )
                    continue

                # Execute trade
                vol_regime = vol_adjustments.get("volatility_regime", "NORMAL")
                power_hour_tag = " [POWER HOUR]" if in_power_hour else ""
                vol_tag = f" [{vol_regime}]" if vol_regime != "NORMAL" else ""
                grade_tag = f" [GRADE {setup_grade}]"
                edge_tag = f" [EDGE +{edge_boost:.0%}]" if edge_boost > 0 else ""

                logger.info(f"🚀 EXECUTING{power_hour_tag}{vol_tag}{grade_tag}{edge_tag}: {action} {quantity} {symbol} @ ${price:.2f}")
                logger.info(f"   ATR: ${atr_value:.2f} | Stop: ${stop_loss_price:.2f}")
                logger.info(f"   Scale-out: 50% @ ${take_profit_1r:.2f} (1R) | 25% @ ${take_profit_2r:.2f} (2R) | 25% @ ${take_profit_3r:.2f} (3R)")
                logger.info(f"   Strategies: {', '.join(strategies)}")
                logger.info(f"   Confidence: {final_confidence:.2%} (base: {adjusted_confidence:.2%}, edge: {edge_boost:+.0%})")

                # HIGH-PERFORMANCE: Execute with latency monitoring
                import time as time_module
                exec_start = time_module.perf_counter()

                # === STEALTH EXECUTION ===
                # Split orders to avoid detection by competing algos
                if use_stealth and quantity > 50:
                    with self._edge_lock:
                        stealth_order = self.edge_engine.prepare_stealth_order(
                            symbol=symbol,
                            quantity=quantity,
                            side=action,
                            edge=edge_analysis or {}
                        )

                    # Execute slices with delays (simplified - full implementation would be async)
                    total_filled = 0
                    orders = []
                    for i, slice_qty in enumerate(stealth_order.slices):
                        if slice_qty <= 0:
                            continue
                        with LATENCY.timed(f"order_execution_{symbol}_slice_{i}"):
                            slice_order = self.broker.place_market_order(symbol, slice_qty, action)
                            if slice_order and not slice_order.get("error"):
                                orders.append(slice_order)
                                total_filled += slice_qty
                        # Small delay between slices (to avoid detection)
                        if i < len(stealth_order.slices) - 1:
                            time_module.sleep(stealth_order.timing_delays_ms[i] / 1000.0)

                    order = orders[0] if orders else None
                    if total_filled > 0:
                        logger.info(f"   STEALTH: Executed {total_filled} shares in {len(orders)} slices")
                else:
                    with LATENCY.timed(f"order_execution_{symbol}"):
                        order = retry_with_backoff(
                            lambda s=symbol, q=quantity, a=action: self.broker.place_market_order(s, q, a),
                            max_retries=3,
                            base_delay=0.1
                        )

                exec_elapsed_ms = (time_module.perf_counter() - exec_start) * 1000
                if exec_elapsed_ms > 10:
                    logger.warning(f"⚠️ Order execution took {exec_elapsed_ms:.1f}ms (target: <10ms)")

                # Validate order result
                if not order or order.get("error"):
                    error_msg = order.get("error", "Unknown error") if order else "No order response"
                    logger.error(f"Order failed for {symbol}: {error_msg}")
                    self._add_decision("ERROR", f"Order failed for {symbol}: {error_msg}", "ERROR", {})
                    continue

                order_id = order.get("orderId") or order.get("order_id") or order.get("id")

                # Create scale-out plan for this position
                self.elite_position_manager.create_scale_plan(
                    symbol=symbol,
                    entry_price=price,
                    quantity=quantity,
                    stop_loss=stop_loss_price,
                    take_profit_1r=take_profit_1r,
                    take_profit_2r=take_profit_2r,
                    take_profit_3r=take_profit_3r
                )

                # Persist trade entry for history + attach context
                trade_id = self._record_trade_entry(
                    symbol=symbol,
                    action=action,
                    quantity=quantity,
                    entry_price=price,
                    strategies=strategies,
                    stop_loss=stop_loss_price,
                    take_profit=take_profit_3r,
                    confidence=final_confidence,
                    setup_grade=setup_grade,
                    entry_reason=opp.get("reasoning"),
                )
                context = self._create_trade_context(
                    symbol=symbol,
                    strategy_name=strategies[0] if strategies else "UNKNOWN",
                    entry_price=price,
                    quantity=quantity,
                    confidence=final_confidence,
                    setup_grade=setup_grade,
                    signals_used=strategies,
                )
                context.trade_id = trade_id

                self._add_decision(
                    "TRADE",
                    f"{action} {quantity} {symbol} @ ${price:.2f} [GRADE {setup_grade}]",
                    "SUCCESS",
                    {
                        "strategies": strategies,
                        "confidence": final_confidence,
                        "base_confidence": adjusted_confidence,
                        "raw_confidence": confidence,
                        "edge_boost": edge_boost,
                        "num_strategies": num_strategies,
                        "relative_volume": opp.get("relative_volume"),
                        "atr_percent": opp.get("atr_percent"),
                        "order_id": order_id,
                        "setup_grade": setup_grade,
                        "atr": atr_value,
                        "stop_loss": stop_loss_price,
                        "scale_out": {
                            "1R": {"price": take_profit_1r, "quantity": int(quantity * 0.50)},
                            "2R": {"price": take_profit_2r, "quantity": int(quantity * 0.25)},
                            "3R": {"price": take_profit_3r, "quantity": quantity - int(quantity * 0.75)}
                        },
                        "power_hour": in_power_hour,
                        "position_sizing": f"ATR-based ({combined_size_mult:.0%})",
                        "edge_analysis": {
                            "action": edge_action,
                            "score": edge_analysis.get("edge_score", 0) if edge_analysis else 0,
                            "stealth_execution": use_stealth,
                            "sentiment": edge_analysis.get("sentiment", {}).get("exploit_signal") if edge_analysis else None,
                            "flow_direction": edge_analysis.get("flow_prediction", {}).get("direction") if edge_analysis else None
                        }
                    }
                )

                current_positions += 1

                # Update strategy performance
                for strat in strategies:
                    if strat not in self.strategy_performance:
                        self.strategy_performance[strat] = {"signals": 0, "trades": 0}
                    self.strategy_performance[strat]["signals"] += 1
                    self.strategy_performance[strat]["trades"] += 1

                # Feed trade data to algo detector for pattern learning
                # Over time, this helps detect competing algorithms
                try:
                    self.edge_engine.algo_detector.ingest_trade({
                        "symbol": symbol,
                        "quantity": quantity,
                        "price": price,
                        "side": action,
                        "timestamp": datetime.now(),
                        "order_type": "MARKET",
                        "is_our_trade": True  # Mark as our own trade
                    })
                except Exception as e:
                    logger.debug(f"Algo detector ingestion failed: {e}")

                self._save_state()

            except Exception as e:
                logger.error(f"Error executing trade for {symbol}: {e}")
                self._add_decision("ERROR", f"Failed to execute {symbol}: {str(e)}", "ERROR", {})

    async def _close_position(self, symbol: str, reason: str):
        """Close a position and track P&L for daily limits"""
        try:
            positions = self.broker.get_positions()
            position = next((p for p in positions if p.get("symbol") == symbol), None)

            if not position:
                return

            quantity = position.get("quantity", 0)
            current_price = position.get("currentPrice", 0)
            unrealized_pnl = position.get("unrealizedPnL", 0)

            logger.info(f"Closing {symbol}: {reason} (P&L: ${unrealized_pnl:.2f})")

            order = self.broker.place_market_order(symbol, abs(quantity), "SELL" if quantity > 0 else "BUY")

            # Validate order result
            if not order or order.get("error"):
                error_msg = order.get("error", "Unknown error") if order else "No order response"
                logger.error(f"Close order failed for {symbol}: {error_msg}")
                self._add_decision("ERROR", f"Close order failed for {symbol}: {error_msg}", "ERROR", {})
                return

            order_id = order.get("orderId") or order.get("order_id") or order.get("id")

            # Track daily P&L
            self.daily_pnl += unrealized_pnl
            logger.info(f"📊 Daily P&L updated: ${self.daily_pnl:.2f} (this trade: ${unrealized_pnl:.2f})")

            # Record trade result in risk manager
            self.risk_manager.record_trade_result(unrealized_pnl)

            # Record trade for ML learning
            await self._record_trade_for_learning(
                symbol=symbol,
                pnl=unrealized_pnl,
                entry_price=position.get("avgPrice", 0),
                exit_price=current_price,
                quantity=quantity
            )

            # Persist trade exit for history
            self._finalize_trade_record(
                symbol=symbol,
                exit_price=current_price,
                pnl=unrealized_pnl,
            )

            self._add_decision(
                "CLOSE",
                f"Closed {symbol}: {reason}",
                "INFO",
                {
                    "quantity": quantity,
                    "price": current_price,
                    "order_id": order_id,
                    "pnl": unrealized_pnl,
                    "daily_pnl": self.daily_pnl
                }
            )

        except Exception as e:
            logger.error(f"Error closing {symbol}: {e}")
            self._add_decision("ERROR", f"Failed to close {symbol}: {str(e)}", "ERROR", {})

    async def _record_trade_for_learning(
        self,
        symbol: str,
        pnl: float,
        entry_price: float,
        exit_price: float,
        quantity: int
    ):
        """Record a completed trade for ML learning system"""
        try:
            # Determine which strategies triggered this trade
            # Look through recent decisions to find the trade entry
            strategies_used = []
            setup_grade = "B"
            confidence = 0.5
            action = "BUY"
            num_strategies_agreed = 1
            relative_volume = 1.0
            atr_percent = 2.0

            for decision in self.decisions:
                if decision.get("type") == "TRADE" and symbol in decision.get("action", ""):
                    metadata = decision.get("metadata", {})
                    strategies_used = metadata.get("strategies", [])
                    setup_grade = metadata.get("setup_grade", "B")
                    confidence = metadata.get("confidence", 0.5)
                    action = (decision.get("action", "BUY").split()[0] if decision.get("action") else "BUY")
                    num_strategies_agreed = metadata.get("num_strategies", len(strategies_used) or 1)
                    relative_volume = float(metadata.get("relative_volume", 1.0) or 1.0)
                    atr_percent = float(metadata.get("atr_percent", 2.0) or 2.0)
                    break

            # Determine volatility regime and time of day
            now = datetime.now()
            hour = now.hour
            if hour < 10:
                time_of_day = "opening"
            elif hour < 12:
                time_of_day = "morning"
            elif hour < 14:
                time_of_day = "midday"
            elif hour < 15:
                time_of_day = "afternoon"
            else:
                time_of_day = "power_hour"

            # Get ATR for volatility context
            atr_value = 0
            try:
                bars = self.market_data.get_historical_bars(symbol, "1 D", "5 mins")
                if bars and len(bars) > 0:
                    df = pd.DataFrame(bars)
                    atr_series = atr(df, 14)
                    atr_value = atr_series.iloc[-1] if len(atr_series) > 0 else entry_price * 0.02
            except Exception:
                atr_value = entry_price * 0.02

            # Determine volatility regime based on ATR%
            atr_percent = (atr_value / entry_price) * 100 if entry_price > 0 else 2.0
            if atr_percent < 1.5:
                volatility_regime = "low"
            elif atr_percent < 3.0:
                volatility_regime = "normal"
            else:
                volatility_regime = "high"

            # Record trade for each strategy that was used
            for strategy in strategies_used:
                trade_record = TradeRecord(
                    symbol=symbol,
                    strategy=strategy,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    quantity=quantity,
                    pnl=pnl,
                    entry_time=now,  # Approximate
                    exit_time=now,
                    action=action,
                    confidence=confidence,
                    setup_grade=setup_grade,
                    volatility_regime=volatility_regime,
                    time_of_day=time_of_day,
                    market_condition="trending" if abs(pnl) > atr_value else "ranging",
                    relative_volume=relative_volume,
                    atr_percent=atr_percent,
                    num_strategies_agreed=num_strategies_agreed
                )

                self.learning_engine.record_trade(trade_record)
                logger.info(f"🧠 Recorded trade for learning: {symbol} via {strategy} (P&L: ${pnl:.2f})")

            # Increment trade counter and check for learning cycle
            self._trades_since_learning_cycle += 1

            if self._trades_since_learning_cycle >= self._learning_cycle_threshold:
                await self._run_learning_cycle()

        except Exception as e:
            logger.error(f"Error recording trade for learning: {e}")

    async def _run_learning_cycle(self):
        """Run ML learning cycle to adjust strategy weights"""
        try:
            logger.info("🧠 Running ML learning cycle...")

            results = self.learning_engine.run_learning_cycle()

            self._trades_since_learning_cycle = 0

            # Log learning results
            insights = results.get("insights", [])
            weight_changes = results.get("weight_changes", {})

            if insights:
                logger.info(f"🧠 Learning insights: {len(insights)} discoveries")
                for insight in insights[:5]:  # Log top 5 insights
                    logger.info(f"   - {insight}")

            if weight_changes:
                logger.info(f"🧠 Strategy weight adjustments:")
                for strategy, change in weight_changes.items():
                    direction = "↑" if change > 0 else "↓"
                    logger.info(f"   {strategy}: {direction} {abs(change):.1%}")

            self._add_decision(
                "LEARNING",
                f"ML learning cycle completed - {len(insights)} insights",
                "INFO",
                {
                    "insights": insights[:10],
                    "weight_changes": weight_changes,
                    "trades_analyzed": results.get("trades_analyzed", 0)
                }
            )

        except Exception as e:
            logger.error(f"Error in learning cycle: {e}")

    def _should_trade_now(self) -> bool:
        """Check if we should trade at this time - ALWAYS allow scanning for UI updates"""
        if not self.enabled or not self.running:
            return False

        # Always return True - we want to scan for UI updates even if broker is not connected
        # The trading logic itself will check broker connection before executing trades
        return True

    def _can_execute_trades(self) -> bool:
        """Check if we can actually execute trades (broker must be connected)"""
        return self.broker.is_connected()

    def _get_market_clock(self) -> Optional[Dict[str, Any]]:
        """Fetch Alpaca clock if broker supports it (best-effort)."""
        broker = getattr(self, "broker", None)
        if broker and hasattr(broker, "get_clock"):
            try:
                return broker.get_clock()
            except Exception:
                return None
        return None

    def _get_market_now(self) -> datetime:
        """Get market-aware current time (Alpaca clock if available)."""
        clock = self._get_market_clock()
        ts = clock.get("timestamp") if clock else None
        if isinstance(ts, datetime):
            if ts.tzinfo is None:
                return ts.replace(tzinfo=EASTERN)
            try:
                return ts.astimezone(EASTERN)
            except Exception:
                return ts
        return datetime.now()

    def _get_market_session_info(self) -> Dict[str, Any]:
        """Return market session info using Alpaca clock when possible."""
        now = self._get_market_now()
        session = market_session(now)
        clock = self._get_market_clock()
        if clock and clock.get("is_open") is not None:
            if clock["is_open"] and not session.get("regular"):
                session["regular"] = True
                session["session"] = "REGULAR"
            if not clock["is_open"] and session.get("regular"):
                session["regular"] = False
                session["session"] = "CLOSED"
            session["clock_source"] = "alpaca"
        else:
            session["clock_source"] = "local"
        return session

    def _build_scan_universe(self) -> List[str]:
        """Build scan universe with hotlist bias when available."""
        base_universe = self.market_data.get_universe()
        hotlist: List[str] = []
        if hasattr(self.market_data, "get_hotlist"):
            try:
                hotlist = self.market_data.get_hotlist(limit=50)
            except Exception:
                hotlist = []
        merged = list(dict.fromkeys(hotlist + base_universe))
        self.last_hotlist = hotlist
        self.last_hotlist_at = datetime.utcnow()
        return merged

    def _is_market_hours(self) -> bool:
        """Check if we're in regular market hours (ET)"""
        session = self._get_market_session_info()
        return session.get("regular", False)

    def _add_decision(self, decision_type: str, message: str, category: str, details: Dict[str, Any]):
        """Add decision to log - THREAD SAFE

        Args:
            decision_type: Type of decision (TRADE, SCAN, REJECTED, ERROR, etc.)
            message: Human-readable message describing the decision
            category: Status category (SUCCESS, INFO, WARNING, ERROR)
            details: Additional details dictionary
        """
        decision = {
            "id": f"d_{datetime.now().timestamp()}",
            "timestamp": datetime.utcnow().isoformat() + "Z",  # UTC with Z suffix for proper JS parsing
            "type": decision_type,
            "message": message,
            "category": category,
            "details": details
        }

        with self._state_lock:
            self.decisions.insert(0, decision)  # Add to front

            # Keep last N decisions
            if len(self.decisions) > self.max_decisions:
                self.decisions = self.decisions[: self.max_decisions]

        # Persist decisions with a light throttle to avoid excessive IO
        now = datetime.utcnow()
        if not self._last_decision_flush or (now - self._last_decision_flush).total_seconds() >= 5:
            self._persist_decisions()
            self._last_decision_flush = now

    def handle_trade_update(self, update: Dict[str, Any]) -> None:
        """Handle Alpaca trade update events for logging/diagnostics."""
        try:
            symbol = update.get("symbol") or "UNKNOWN"
            event = update.get("event") or "update"
            status = update.get("status") or ""
            filled_qty = update.get("filled_qty")
            fill_price = update.get("filled_avg_price")
            message = f"📥 {symbol}: trade update {event}"
            if status:
                message += f" ({status})"
            self._add_decision(
                "TRADE_UPDATE",
                message,
                "INFO",
                {
                    "symbol": symbol,
                    "event": event,
                    "status": status,
                    "filled_qty": filled_qty,
                    "filled_avg_price": fill_price,
                    "order_id": update.get("order_id"),
                },
            )
        except Exception as e:
            logger.debug(f"Failed to handle trade update: {e}")

    def _persist_decisions(self) -> None:
        """Persist recent decisions to disk for UI continuity."""
        try:
            DECISION_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(DECISION_LOG_FILE, "w") as f:
                json.dump(self.decisions[: self.max_decisions], f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to persist decisions: {e}")

    def _coerce_json(self, value: Any) -> Any:
        """Convert numpy/pandas scalars and containers into JSON-serializable types."""
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
        if isinstance(value, pd.Timedelta):
            return value.total_seconds()
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, dict):
            return {key: self._coerce_json(val) for key, val in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._coerce_json(item) for item in value]
        return value

    def get_status(self) -> Dict[str, Any]:
        """Get current engine status with detailed scanner information"""
        # Check power hour status
        now = self._get_market_now()
        session = self._get_market_session_info()
        in_power_hour = is_power_hour(now.hour, now.minute)
        time_mult = power_hour_multiplier(now.hour, now.minute)
        cached_positions = self._positions_cache_count
        cache_age = (datetime.now() - self._positions_cache_time).total_seconds() if self._positions_cache_time else None
        market_refresh = getattr(self.market_data, "cache_ttl", None)

        exit_rules = {
            "time_stop_minutes": self.time_stop_minutes,
            "time_stop_min_pnl": self.time_stop_min_pnl,
            "max_hold_minutes": self.max_hold_minutes,
            "trailing_lookback_bars": self.trailing_lookback_bars,
            "trailing_min_pnl": self.trailing_min_pnl,
            "momentum_exit_min_pnl": self.momentum_exit_min_pnl,
            "momentum_exit_ema_period": self.momentum_exit_ema_period,
            "atr_stop_multiplier": 1.5,
            "atr_profit_multiplier": 3.75,
            "scale_out": {
                "one_r_pct": 50,
                "two_r_pct": 25,
                "three_r_pct": 25,
                "breakeven_after": "1R",
                "trailing_after": "2R",
            },
        }

        position_exit_state: Dict[str, Any] = {}
        try:
            for symbol, plan in self.elite_position_manager.positions.items():
                position_exit_state[symbol] = {
                    "current_stop": plan.current_stop,
                    "original_stop": plan.original_stop,
                    "breakeven_activated": plan.breakeven_activated,
                    "trailing_activated": plan.trailing_activated,
                    "remaining_quantity": plan.remaining_quantity,
                    "scale_levels": plan.scale_levels,
                }
        except Exception:
            position_exit_state = {}

        status = {
            "enabled": self.enabled,
            "running": self.running,
            "mode": self.mode,
            "risk_posture": self.risk_posture,
            "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "active_positions": cached_positions,
            "positions_cache_age": cache_age,
            "decisions": self.decisions[:20],  # Last 20 decisions
            "strategy_performance": self.strategy_performance,
            "num_strategies": len(self.all_strategies),
            "connected": self.broker.is_connected(),
            # NEW: Detailed scanner data for UI
            "symbols_scanned": self.symbols_scanned,
            "scanner_results": self.last_scanner_results,  # Top stocks with full evaluation data
            "analyzed_opportunities": self.last_analyzed_opportunities,  # With strategy signals
            "market_session": session,
            "hotlist": {
                "symbols": self.last_hotlist[:50],
                "count": len(self.last_hotlist),
                "generated_at": self.last_hotlist_at.isoformat() if self.last_hotlist_at else None,
            },
            "timings": {
                "scan_interval_seconds": self.scan_interval,
                "scan_interval_off_hours_seconds": 15,
                "position_monitor_interval_seconds": 5,
                "bars_timeframe": "5 mins",
                "market_data_refresh_seconds": market_refresh,
                "daily_cache_ttl_seconds": self._daily_data_cache_ttl_seconds,
            },
            "exit_rules": exit_rules,
            "position_exit_state": position_exit_state,
            "power_hour": {
                "active": in_power_hour,
                "multiplier": time_mult,
            },
            "scoring_weights": {
                "ml_score": 0.23,
                "momentum_score": 0.14,
                "gap_score": 0.14,
                "float_score": 0.09,
                "pattern_score": 0.14,
                "news_score": 0.09,
                "atr_score": 0.12,
                "short_interest_score": 0.05,
            },
            # NEW: Detailed evaluation data for every stock
            "all_evaluations": self.all_evaluations[:50],  # First 50 for performance
            "filter_summary": self.filter_summary,
            "watchlist_candidates": self.watchlist_candidates[:100],
            # Active strategies list
            "active_strategies": list(self.all_strategies.keys()),
            # HIGH-PERFORMANCE: Latency metrics
            "performance": self.get_latency_report() if hasattr(self, 'perf_engine') else {},
            "integration_validated": self._integration_validated if hasattr(self, '_integration_validated') else False,
            # ML Learning status
            "learning": {
                "enabled": hasattr(self, 'learning_engine'),
                "trades_until_next_cycle": self._learning_cycle_threshold - self._trades_since_learning_cycle if hasattr(self, '_trades_since_learning_cycle') else 0,
                "strategy_weights": self.learning_engine.get_all_weights() if hasattr(self, 'learning_engine') else {},
                "recent_insights": self.learning_engine.get_recent_insights(5) if hasattr(self, 'learning_engine') else [],
            },
        }

        return self._coerce_json(status)

    def update_config(self, config: Dict[str, Any]):
        """Update engine configuration"""
        if "mode" in config:
            self.mode = config["mode"]
        if "risk_posture" in config:
            self.risk_posture = config["risk_posture"]
        if "enabled_strategies" in config:
            self.enabled_strategies = config["enabled_strategies"]
        if "max_positions" in config:
            self.max_positions = config["max_positions"]
        if "scan_interval" in config:
            self.scan_interval = config["scan_interval"]

        self._save_state()
        logger.info(f"Config updated: {config}")

    async def _latency_monitor(self):
        """
        Background task to monitor and report system latency.

        Logs latency metrics every 60 seconds and alerts if target exceeded.
        Target: <10ms for all critical operations.
        """
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every 60 seconds

                # Get latency report
                report = LATENCY.get_report()

                if not report:
                    continue

                # Check for high latency components
                high_latency_components = []
                for component, metrics in report.items():
                    p99 = metrics.get("p99_ms", 0)
                    if p99 > 10:  # Target is <10ms
                        high_latency_components.append(f"{component}: p99={p99:.1f}ms")

                if high_latency_components:
                    logger.warning(f"⚠️ HIGH LATENCY DETECTED: {', '.join(high_latency_components)}")
                else:
                    # Log summary of healthy latency
                    total_samples = sum(m.get("samples", 0) for m in report.values())
                    if total_samples > 0:
                        avg_p99 = sum(m.get("p99_ms", 0) for m in report.values()) / len(report)
                        logger.info(f"📊 Latency OK - avg p99: {avg_p99:.1f}ms across {len(report)} components")

                # Get cache hit rate from performance engine
                if hasattr(self, 'perf_engine'):
                    cache_hit_rate = self.perf_engine.cache.hit_rate
                    if cache_hit_rate < 0.5:
                        logger.warning(f"⚠️ Low cache hit rate: {cache_hit_rate:.1%}")
                    else:
                        logger.debug(f"Cache hit rate: {cache_hit_rate:.1%}")

            except Exception as e:
                logger.error(f"Error in latency monitor: {e}")
                await asyncio.sleep(30)

    def get_latency_report(self) -> Dict[str, Any]:
        """Get comprehensive latency and performance metrics."""
        if hasattr(self, 'perf_engine'):
            return self.perf_engine.get_latency_report()
        return {"latency": LATENCY.get_report()}
