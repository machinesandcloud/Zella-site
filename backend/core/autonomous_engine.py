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

from core.strategy_engine import StrategyEngine
from core.risk_manager import RiskManager
from core.position_manager import PositionManager
from market.market_data_provider import MarketDataProvider
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
)
from utils.indicators import (
    atr,
    atr_stop_loss,
    atr_take_profit,
    calculate_position_size_atr,
    is_power_hour,
    power_hour_multiplier,
)
from utils.market_hours import (
    is_past_new_trade_cutoff,
    is_eod_liquidation_time,
    minutes_until_close,
    is_opening_range,
    minutes_since_open,
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
        self.scan_interval = self.config.get("scan_interval", 1)  # seconds between scans (1s for real-time day trading)
        self.max_positions = self.config.get("max_positions", 5)
        self.enabled_strategies = self.config.get("enabled_strategies", "ALL")

        # State - THREAD SAFE with locks
        self.running = False
        self.last_scan_time: Optional[datetime] = None
        self.decisions: List[Dict[str, Any]] = []
        self.active_symbols: Set[str] = set()
        self.strategy_performance: Dict[str, Dict[str, Any]] = {}

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

        # Scanner results (for UI display)
        self.last_scanner_results: List[Dict[str, Any]] = []  # Raw screener output
        self.last_analyzed_opportunities: List[Dict[str, Any]] = []  # After strategy analysis
        self.symbols_scanned: int = 0  # Count of symbols scanned
        self.all_evaluations: List[Dict[str, Any]] = []  # ALL stocks with pass/fail details
        self.filter_summary: Dict[str, int] = {}  # Summary of filter pass/fail counts

        # Day trading safeguards
        self.eod_liquidation_done_today: bool = False  # Track if EOD liquidation ran today
        self.last_liquidation_date: Optional[str] = None  # Date string of last liquidation
        self.min_confidence_threshold: float = 0.65  # Minimum confidence to enter trades
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
        self.discipline = TradingDisciplineEnforcer(
            max_consecutive_losses=3,
            loss_cooldown_minutes=5,
            max_daily_winners=5,  # Quit while ahead
            daily_loss_limit=500.0,
            profit_protection_threshold=300.0,
            max_drawdown_pct=30.0
        )

        # Track SPY data for relative strength
        self._spy_data_cache: Optional[pd.DataFrame] = None
        self._spy_cache_time: Optional[datetime] = None

        # ML Model for screening
        self.ml_model = MLSignalModel()
        self.ml_model.load()
        self.screener = MarketScreener(
            self.ml_model,
            min_avg_volume=settings.screener_min_avg_volume,
            min_price=settings.screener_min_price,
            max_price=settings.screener_max_price,
            min_volatility=settings.screener_min_volatility,
            min_relative_volume=settings.screener_min_relative_volume,
        )

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

    def _initialize_strategies(self) -> Dict[str, Any]:
        """Initialize all 37+ trading strategies including Warrior Trading patterns"""
        # Default config for all strategies
        default_config = {"parameters": {}, "enabled": True}

        # ATR-enabled config for Warrior Trading strategies
        atr_config = {"parameters": {"use_atr_stops": True, "atr_multiplier": 2.0}, "enabled": True}

        strategies = {
            # === WARRIOR TRADING CORE PATTERNS (Priority) ===
            "bull_flag": BullFlagStrategy(atr_config),  # Primary momentum pattern
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
                "decisions": self.decisions[:50],

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

        except Exception as e:
            logger.error(f"Error saving state: {e}")

    # ==================== THREAD-SAFE CONTEXT MANAGEMENT ====================

    def _get_symbol_state(self, symbol: str) -> SymbolState:
        """Get or create per-symbol state - THREAD SAFE"""
        with self._symbol_lock:
            if symbol not in self._symbol_states:
                self._symbol_states[symbol] = SymbolState(symbol=symbol)
            return self._symbol_states[symbol]

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
            atr_val = float(atr(symbol_state.bars_cache)) if len(symbol_state.bars_cache) >= 14 else 0.0

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

        # Run system integration validation on first start
        if not self._integration_validated:
            logger.info("🔍 Running system integration validation...")
            validation_passed = self.integration_validator.validate_all(
                performance_engine=self.perf_engine,
                elite_system=self.elite_system,
                pro_validator=self.pro_validator,
                broker=self.broker
            )
            self._integration_validated = True
            if validation_passed:
                logger.info("✅ All systems validated and ready for trading")
            else:
                logger.warning("⚠️ Some integration tests failed - trading with caution")

        # Reset daily tracking
        today = datetime.now().strftime("%Y-%m-%d")
        if self.last_liquidation_date != today:
            self.eod_liquidation_done_today = False
            self.daily_pnl = 0.0
            self.discipline.reset_daily()  # Reset discipline counters too
            logger.info("📅 New trading day - daily counters reset")

        # Start background tasks
        asyncio.create_task(self._main_trading_loop())
        asyncio.create_task(self._eod_liquidation_monitor())  # Critical: close all positions before market close
        asyncio.create_task(self._connection_keepalive())
        asyncio.create_task(self._position_monitor())
        asyncio.create_task(self._latency_monitor())  # Monitor latency
        asyncio.create_task(self._periodic_state_save())  # Save state for recovery
        asyncio.create_task(self._position_reconciliation_loop())  # Reconcile with broker

    async def stop(self):
        """Stop the autonomous trading engine"""
        self.running = False
        self.enabled = False
        self._save_state()

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

                    if self.broker.connect():
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
        while self.running:
            try:
                # Check basic requirements
                if not self._should_trade_now():
                    await asyncio.sleep(10)  # Shorter sleep when not ready
                    continue

                # Determine scan interval based on market hours
                is_market_open = self._is_market_hours()
                current_scan_interval = self.scan_interval if is_market_open else 30  # 30s outside market hours

                logger.info(f"🔍 Starting autonomous scan cycle... (market_open={is_market_open})")
                self.last_scan_time = datetime.now()

                # 1. Scan market for opportunities (ALWAYS - for real-time UI)
                opportunities = await self._scan_market()

                # 2. Analyze each opportunity with ALL strategies
                analyzed = await self._analyze_opportunities(opportunities)

                # 3. Rank and select best opportunities
                top_picks = self._rank_opportunities(analyzed)

                # 4. Execute trades ONLY during market hours and in auto modes
                # DAY TRADING RULE: No new positions after 3:30 PM ET
                if is_market_open and self.mode in ["FULL_AUTO", "GOD_MODE"]:
                    if is_past_new_trade_cutoff():
                        mins_left = minutes_until_close()
                        self._add_decision(
                            "CUTOFF",
                            f"Past 3:30 PM ET - No new trades ({mins_left} mins to close)",
                            "INFO",
                            {"minutes_to_close": mins_left}
                        )
                        logger.info(f"⏰ Past trade cutoff (3:30 PM) - {mins_left} mins until close, no new trades")
                    elif self.daily_pnl <= self.daily_pnl_limit:
                        self._add_decision(
                            "DAILY_LIMIT",
                            f"Daily loss limit hit (${self.daily_pnl:.2f}) - Trading halted",
                            "WARNING",
                            {"daily_pnl": self.daily_pnl, "limit": self.daily_pnl_limit}
                        )
                        logger.warning(f"🛑 Daily loss limit reached: ${self.daily_pnl:.2f}")
                    else:
                        await self._execute_trades(top_picks)
                elif not is_market_open and opportunities:
                    self._add_decision(
                        "INFO",
                        f"Market closed - scan only mode ({len(opportunities)} opportunities)",
                        "INFO",
                        {"opportunities": len(opportunities), "analyzed": len(analyzed)}
                    )

                # 5. Wait for next scan
                await asyncio.sleep(current_scan_interval)

            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                self._add_decision("ERROR", f"Trading loop error: {str(e)}", "ERROR", {})
                await asyncio.sleep(30)

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

                for position in positions:
                    symbol = position.get("symbol")
                    current_price = position.get("currentPrice", 0)
                    entry_price = position.get("avgPrice", 0)
                    pnl_percent = position.get("unrealizedPnLPercent", 0)
                    unrealized_pnl = position.get("unrealizedPnL", 0)
                    quantity = position.get("quantity", 0)

                    if not symbol or current_price <= 0:
                        continue

                    # Get ATR for this symbol if not cached
                    if symbol not in position_atr:
                        try:
                            bars = self.market_data.get_historical_bars(symbol, "1 D", "5 mins")
                            if bars and len(bars) > 0:
                                df = pd.DataFrame(bars)
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

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error in position monitor: {e}")
                await asyncio.sleep(30)

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
                today = datetime.now().strftime("%Y-%m-%d")

                # Reset flag for new trading day
                if self.last_liquidation_date != today:
                    self.eod_liquidation_done_today = False

                # Check if it's liquidation time (3:50 PM ET)
                if is_eod_liquidation_time() and not self.eod_liquidation_done_today:
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
        """
        try:
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
                            f"EOD liquidation: {side} {abs_qty} {symbol}",
                            "EXECUTED",
                            {"symbol": symbol, "quantity": abs_qty, "side": side, "pnl": pnl}
                        )

                        # Track daily P&L
                        self.daily_pnl += pnl

                    except Exception as e:
                        logger.error(f"Failed to liquidate {symbol}: {e}")
                        self._add_decision(
                            "LIQUIDATION_FAILED",
                            f"Failed to close {symbol}: {str(e)}",
                            "ERROR",
                            {"symbol": symbol, "error": str(e)}
                        )

            logger.info(f"📊 Daily P&L after liquidation: ${self.daily_pnl:.2f}")

        except Exception as e:
            logger.error(f"Error in liquidate_all_positions: {e}")

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
        import time as time_module
        scan_start = time_module.perf_counter()

        try:
            universe = self.market_data.get_universe()
            logger.info(f"Scanning {len(universe)} symbols...")

            # Get current time for power hour weighting
            now = datetime.now()
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

            # Fetch news catalysts for scanned symbols (async would be better)
            try:
                await self._update_news_catalysts(list(market_data.keys())[:50])  # Top 50 symbols
            except Exception as e:
                logger.debug(f"Could not fetch news catalysts: {e}")

            # Use enhanced ML screener with DETAILED evaluation
            passed_list, all_evaluations = self.screener.rank_with_details(market_data, current_hour, current_minute)

            # Store ALL evaluations for UI display (showing why each stock passed/failed)
            self.symbols_scanned = len(market_data)
            self.all_evaluations = all_evaluations  # Full list with pass/fail details

            # Calculate filter summary (how many failed at each filter)
            self.filter_summary = {
                "total": len(all_evaluations),
                "passed": len(passed_list),
                "failed_data": sum(1 for e in all_evaluations if e.get("filters", {}).get("data_check", {}).get("passed") == False),
                "failed_volume": sum(1 for e in all_evaluations if e.get("filters", {}).get("volume", {}).get("passed") == False),
                "failed_price": sum(1 for e in all_evaluations if e.get("filters", {}).get("price", {}).get("passed") == False),
                "failed_volatility": sum(1 for e in all_evaluations if e.get("filters", {}).get("volatility", {}).get("passed") == False),
                "failed_rvol": sum(1 for e in all_evaluations if e.get("filters", {}).get("relative_volume", {}).get("passed") == False),
            }

            # Log scan results
            pattern_count = sum(1 for e in passed_list if e.get("data", {}).get("pattern"))
            news_count = sum(1 for e in passed_list if e.get("data", {}).get("news_catalyst"))

            logger.info(f"Found {len(passed_list)} opportunities out of {len(all_evaluations)} evaluated")
            logger.info(f"  Patterns: {pattern_count}, News catalysts: {news_count}")

            # Store passed results in old format for compatibility
            self.last_scanner_results = [
                {
                    "symbol": e.get("symbol"),
                    "ml_score": e.get("scores", {}).get("ml_score", 0),
                    "momentum_score": e.get("scores", {}).get("momentum_score", 0),
                    "combined_score": e.get("scores", {}).get("combined_score", 0),
                    "last_price": e.get("data", {}).get("price", 0),
                    "relative_volume": e.get("data", {}).get("relative_volume", 0),
                    "float_millions": e.get("data", {}).get("float_millions"),
                    "float_score": e.get("scores", {}).get("float_score", 0),
                    "atr": e.get("data", {}).get("atr", 0),
                    "atr_percent": e.get("data", {}).get("atr_percent", 0),
                    "pattern": e.get("data", {}).get("pattern"),
                    "pattern_score": e.get("scores", {}).get("pattern_score", 0),
                    "news_catalyst": e.get("data", {}).get("news_catalyst"),
                    "news_score": e.get("scores", {}).get("news_score", 0),
                    "time_multiplier": e.get("scores", {}).get("time_multiplier", 1.0),
                }
                for e in passed_list[:20]
            ]

            self._add_decision(
                "SCAN",
                f"Scanned {len(market_data)} symbols, found {len(passed_list)} opportunities",
                "INFO",
                {
                    "count": len(passed_list),
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
                    "relative_volume": e.get("data", {}).get("relative_volume", 0),
                    "float_millions": e.get("data", {}).get("float_millions"),
                    "float_score": e.get("scores", {}).get("float_score", 0),
                    "atr": e.get("data", {}).get("atr", 0),
                    "atr_percent": e.get("data", {}).get("atr_percent", 0),
                    "pattern": e.get("data", {}).get("pattern"),
                    "pattern_score": e.get("scores", {}).get("pattern_score", 0),
                    "news_catalyst": e.get("data", {}).get("news_catalyst"),
                    "news_score": e.get("scores", {}).get("news_score", 0),
                    "time_multiplier": e.get("scores", {}).get("time_multiplier", 1.0),
                })

            return ranked

        except Exception as e:
            logger.error(f"Error scanning market: {e}")
            return []

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

    async def _analyze_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze each opportunity with ALL available strategies.

        HIGH-PERFORMANCE: Uses fast signal processor for sub-10ms processing.
        """
        import time as time_module
        analyze_start = time_module.perf_counter()
        analyzed = []

        for opp in opportunities:
            symbol = opp.get("symbol")
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
                if strategy_signals:
                    buy_signals = [s for s in strategy_signals if s["action"] == "BUY"]
                    sell_signals = [s for s in strategy_signals if s["action"] == "SELL"]

                    # Calculate aggregate confidence
                    if buy_signals:
                        avg_confidence = sum(s["confidence"] for s in buy_signals) / len(buy_signals)
                        analyzed.append({
                            **opp,
                            "recommended_action": "BUY",
                            "num_strategies": len(buy_signals),
                            "confidence": avg_confidence,
                            "strategies": [s["strategy"] for s in buy_signals],
                            "strategy_signals": buy_signals,  # Include full signal data with indicators
                            "reasoning": " | ".join([f"{s['strategy']}: {s['reason']}" for s in buy_signals[:3]])
                        })
                    elif sell_signals:
                        avg_confidence = sum(s["confidence"] for s in sell_signals) / len(sell_signals)
                        analyzed.append({
                            **opp,
                            "recommended_action": "SELL",
                            "num_strategies": len(sell_signals),
                            "confidence": avg_confidence,
                            "strategies": [s["strategy"] for s in sell_signals],
                            "strategy_signals": sell_signals,  # Include full signal data with indicators
                            "reasoning": " | ".join([f"{s['strategy']}: {s['reason']}" for s in sell_signals[:3]])
                        })

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

        # Record total analysis time
        analyze_elapsed_ms = (time_module.perf_counter() - analyze_start) * 1000
        LATENCY.record("analyze_opportunities_total", analyze_elapsed_ms)
        logger.debug(f"Analysis completed in {analyze_elapsed_ms:.1f}ms for {len(opportunities)} opportunities")

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

    async def _execute_trades(self, opportunities: List[Dict[str, Any]]):
        """
        Execute trades for top opportunities using Warrior Trading position sizing

        Position sizing formula: shares = risk_amount / ATR_stop_distance
        This ensures consistent risk per trade regardless of stock volatility
        """
        if not self.risk_manager.can_trade():
            logger.warning("Risk manager blocks trading")
            return

        account = self.broker.get_account_summary()
        account_value = float(account.get("NetLiquidation", 0) or 0)
        buying_power = float(account.get("BuyingPower", 0) or 0)

        current_positions = len(self.broker.get_positions())

        # Check if we're in power hour for signal boost
        now = datetime.now()
        in_power_hour = is_power_hour(now.hour, now.minute)
        time_mult = power_hour_multiplier(now.hour, now.minute)

        for opp in opportunities:
            if current_positions >= self.max_positions:
                logger.info(f"Max positions ({self.max_positions}) reached")
                break

            symbol = opp.get("symbol")
            action = opp.get("recommended_action")
            confidence = opp.get("confidence", 0)
            num_strategies = opp.get("num_strategies", 0)
            strategies = opp.get("strategies", [])

            # Apply power hour boost to confidence
            adjusted_confidence = confidence * time_mult

            # TIGHTENED THRESHOLDS - Reduce losses by being more selective
            # Day trading requires HIGH conviction entries only
            if in_power_hour:
                # Still slightly lower during power hour but not reckless
                min_confidence = 0.65 if self.risk_posture == "AGGRESSIVE" else 0.72 if self.risk_posture == "BALANCED" else 0.80
                min_strategies = 2 if self.risk_posture == "AGGRESSIVE" else 2 if self.risk_posture == "BALANCED" else 3
            else:
                # Normal hours: Higher standards
                min_confidence = 0.70 if self.risk_posture == "AGGRESSIVE" else 0.75 if self.risk_posture == "BALANCED" else 0.85
                min_strategies = 2 if self.risk_posture == "AGGRESSIVE" else 3 if self.risk_posture == "BALANCED" else 4

            # Global minimum - never trade below this regardless of settings
            if adjusted_confidence < self.min_confidence_threshold:
                logger.debug(f"Skipping {symbol}: confidence {adjusted_confidence:.2f} below threshold {self.min_confidence_threshold}")
                continue

            if adjusted_confidence < min_confidence:
                continue

            if num_strategies < min_strategies:
                continue

            try:
                price = opp.get("last_price", 0)
                if price <= 0:
                    continue

                # === PRO-LEVEL VALIDATION ===
                # These filters separate profitable traders from retail losers
                bid = opp.get("bid", price * 0.999)
                ask = opp.get("ask", price * 1.001)
                current_volume = opp.get("volume", 0)
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
                    minutes_since_open=minutes_since_open()
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
                            logger.info(f"⛔ {symbol} GRADE F - Setup rejected")
                            self._add_decision(
                                "REJECTED",
                                f"{symbol} failed elite grading (F)",
                                "INFO",
                                {"grade": setup_grade, "factors": elite_analysis.get("grade_details", {}).get("factors", [])}
                            )
                            continue
                        elif setup_grade == "C":
                            logger.info(f"⚠️ {symbol} GRADE C - Skipping marginal setup")
                            continue

                        logger.info(f"📊 {symbol} GRADE {setup_grade} - Elite analysis passed")

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
                    atr_multiplier=atr_multiplier
                )

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
                        order = self.broker.place_market_order(symbol, quantity, action)

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

            for decision in self.decisions:
                if decision.get("type") == "TRADE" and symbol in decision.get("action", ""):
                    metadata = decision.get("metadata", {})
                    strategies_used = metadata.get("strategies", [])
                    setup_grade = metadata.get("setup_grade", "B")
                    confidence = metadata.get("confidence", 0.5)
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
                    confidence=confidence,
                    setup_grade=setup_grade,
                    volatility_regime=volatility_regime,
                    time_of_day=time_of_day,
                    market_condition="trending" if abs(pnl) > atr_value else "ranging"
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
        """Check if we should trade at this time"""
        if not self.enabled or not self.running:
            return False

        # Check if broker connected
        if not self.broker.is_connected():
            return False

        return True

    def _is_market_hours(self) -> bool:
        """Check if we're in regular market hours"""
        now = datetime.now().time()
        market_open = time(9, 30)
        market_close = time(16, 0)
        return market_open <= now <= market_close

    def _add_decision(self, decision_type: str, action: str, status: str, metadata: Dict[str, Any]):
        """Add decision to log - THREAD SAFE"""
        decision = {
            "id": f"d_{datetime.now().timestamp()}",
            "time": datetime.now().strftime("%H:%M:%S"),
            "type": decision_type,
            "action": action,
            "status": status,
            "metadata": metadata
        }

        with self._state_lock:
            self.decisions.insert(0, decision)  # Add to front

            # Keep last 100 decisions
            if len(self.decisions) > 100:
                self.decisions = self.decisions[:100]

    def get_status(self) -> Dict[str, Any]:
        """Get current engine status with detailed scanner information"""
        # Check power hour status
        now = datetime.now()
        in_power_hour = is_power_hour(now.hour, now.minute)
        time_mult = power_hour_multiplier(now.hour, now.minute)

        return {
            "enabled": self.enabled,
            "running": self.running,
            "mode": self.mode,
            "risk_posture": self.risk_posture,
            "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "active_positions": len(self.broker.get_positions()) if self.broker.is_connected() else 0,
            "decisions": self.decisions[:20],  # Last 20 decisions
            "strategy_performance": self.strategy_performance,
            "num_strategies": len(self.all_strategies),
            "connected": self.broker.is_connected(),
            # NEW: Detailed scanner data for UI
            "symbols_scanned": self.symbols_scanned,
            "scanner_results": self.last_scanner_results,  # Top stocks with full evaluation data
            "analyzed_opportunities": self.last_analyzed_opportunities,  # With strategy signals
            "power_hour": {
                "active": in_power_hour,
                "multiplier": time_mult,
            },
            "scoring_weights": {
                "ml_score": 0.30,
                "momentum_score": 0.20,
                "float_score": 0.15,
                "pattern_score": 0.15,
                "news_score": 0.10,
                "atr_score": 0.10,
            },
            # NEW: Detailed evaluation data for every stock
            "all_evaluations": self.all_evaluations[:50],  # First 50 for performance
            "filter_summary": self.filter_summary,
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
