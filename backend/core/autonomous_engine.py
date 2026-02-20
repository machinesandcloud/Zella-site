"""
Fully Autonomous Trading Engine for Zella AI
Continuously scans, analyzes, and trades using all available strategies
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time
from typing import Any, Dict, List, Optional, Set, Tuple
import json
from pathlib import Path

import pandas as pd

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

        # State
        self.running = False
        self.last_scan_time: Optional[datetime] = None
        self.decisions: List[Dict[str, Any]] = []
        self.active_symbols: Set[str] = set()
        self.strategy_performance: Dict[str, Dict[str, Any]] = {}

        # Scanner results (for UI display)
        self.last_scanner_results: List[Dict[str, Any]] = []  # Raw screener output
        self.last_analyzed_opportunities: List[Dict[str, Any]] = []  # After strategy analysis
        self.symbols_scanned: int = 0  # Count of symbols scanned
        self.all_evaluations: List[Dict[str, Any]] = []  # ALL stocks with pass/fail details
        self.filter_summary: Dict[str, int] = {}  # Summary of filter pass/fail counts

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

        # Persistent state file
        self.state_file = Path("data/autonomous_state.json")
        self._load_state()

        logger.info(f"Autonomous Engine initialized - Mode: {self.mode}, Risk: {self.risk_posture}")

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
        """Load persistent state from disk"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.enabled = state.get("enabled", self.enabled)
                    self.mode = state.get("mode", self.mode)
                    self.risk_posture = state.get("risk_posture", self.risk_posture)
                    self.strategy_performance = state.get("strategy_performance", {})
                    logger.info(f"Loaded state - Enabled: {self.enabled}, Mode: {self.mode}")
        except Exception as e:
            logger.error(f"Error loading state: {e}")

    def _save_state(self):
        """Save persistent state to disk"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            state = {
                "enabled": self.enabled,
                "mode": self.mode,
                "risk_posture": self.risk_posture,
                "strategy_performance": self.strategy_performance,
                "last_updated": datetime.now().isoformat(),
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {e}")

    async def start(self):
        """Start the autonomous trading engine"""
        if self.running:
            logger.warning("Engine already running")
            return

        self.running = True
        self.enabled = True
        self._save_state()
        logger.info("🤖 Autonomous Engine STARTED")

        # Start background tasks
        asyncio.create_task(self._main_trading_loop())
        asyncio.create_task(self._connection_keepalive())
        asyncio.create_task(self._position_monitor())

    async def stop(self):
        """Stop the autonomous trading engine"""
        self.running = False
        self.enabled = False
        self._save_state()
        logger.info("🛑 Autonomous Engine STOPPED")

    async def _connection_keepalive(self):
        """Maintain persistent connection to broker"""
        while self.running:
            try:
                if not self.broker.is_connected():
                    logger.warning("Connection lost - reconnecting...")
                    if self.broker.connect():
                        logger.info("✓ Reconnected successfully")
                        self._add_decision("SYSTEM", "Reconnected to broker", "INFO", {})
                    else:
                        logger.error("✗ Reconnection failed - retrying in 30s")
                        self._add_decision("SYSTEM", "Reconnection failed", "ERROR", {})

                # Send keepalive ping every 2 minutes
                await asyncio.sleep(120)

            except Exception as e:
                logger.error(f"Error in keepalive: {e}")
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
                if is_market_open and self.mode in ["FULL_AUTO", "GOD_MODE"]:
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
        Monitor and manage existing positions using ATR-based stops

        Warrior Trading approach:
        - Use ATR for dynamic stop losses (volatility-adjusted)
        - Trail stops as position moves in profit
        - Take profit at 2:1 or 3:1 risk/reward
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

                    # ATR-based stop loss distance (2x ATR)
                    atr_stop_distance = current_atr * 2.0
                    atr_stop_percent = (atr_stop_distance / entry_price) * 100 if entry_price > 0 else 2.0

                    # ATR-based take profit (3x ATR for 1.5:1 risk/reward)
                    atr_profit_distance = current_atr * 3.0
                    atr_profit_percent = (atr_profit_distance / entry_price) * 100 if entry_price > 0 else 6.0

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

                    # Dynamic trailing stop when in profit
                    if pnl_percent > profit_target / 2:  # Half way to target
                        # Trail stop to lock in some profit
                        trail_percent = max(1.0, atr_stop_percent * 0.7)  # Tighten to 70% of ATR
                        if pnl_percent > profit_target:
                            # Full target hit - trail very tight
                            trail_percent = max(0.5, atr_stop_percent * 0.5)
                        logger.info(f"Trailing stop for {symbol}: {trail_percent:.1f}% (ATR-based)")

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

    async def _scan_market(self) -> List[Dict[str, Any]]:
        """
        Scan market for trading opportunities using Warrior Trading criteria

        Enhanced scanning includes:
        - Power hour time weighting
        - News catalyst integration
        - Float filtering
        - Pattern detection (bull flag, flat top)
        """
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

            # Scan more symbols during power hour
            scan_limit = 150 if in_power_hour else 100

            for symbol in universe[:scan_limit]:
                try:
                    bars = self.market_data.get_historical_bars(symbol, "1 D", "5 mins")
                    if bars and len(bars) > 0:
                        df = pd.DataFrame(bars)
                        market_data[symbol] = df
                except Exception as e:
                    logger.debug(f"Could not get data for {symbol}: {e}")
                    continue

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
        """Analyze each opportunity with ALL available strategies"""
        analyzed = []

        for opp in opportunities:
            symbol = opp.get("symbol")
            if not symbol:
                continue

            try:
                # Get data for this symbol
                bars = self.market_data.get_historical_bars(symbol, "1 D", "5 mins")
                if not bars:
                    continue

                df = pd.DataFrame(bars)

                # Test ALL strategies
                strategy_signals = []

                for strat_name, strategy in self.all_strategies.items():
                    if self.enabled_strategies != "ALL" and strat_name not in self.enabled_strategies:
                        continue

                    try:
                        signal = strategy.generate_signals(df)
                        if signal and signal.get("action") in ["BUY", "SELL"]:
                            strategy_signals.append({
                                "strategy": strat_name,
                                "action": signal.get("action"),
                                "confidence": signal.get("confidence", 0.5),
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

            # Lower thresholds during power hour (more aggressive)
            if in_power_hour:
                min_confidence = 0.55 if self.risk_posture == "AGGRESSIVE" else 0.65 if self.risk_posture == "BALANCED" else 0.75
                min_strategies = 1 if self.risk_posture == "AGGRESSIVE" else 2 if self.risk_posture == "BALANCED" else 3
            else:
                min_confidence = 0.6 if self.risk_posture == "AGGRESSIVE" else 0.7 if self.risk_posture == "BALANCED" else 0.8
                min_strategies = 2 if self.risk_posture == "AGGRESSIVE" else 3 if self.risk_posture == "BALANCED" else 4

            if adjusted_confidence < min_confidence:
                continue

            if num_strategies < min_strategies:
                continue

            try:
                price = opp.get("last_price", 0)
                if price <= 0:
                    continue

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
                # Risk 1-2% of account, stop at 2x ATR
                risk_percent = 0.01 if self.risk_posture == "DEFENSIVE" else 0.015 if self.risk_posture == "BALANCED" else 0.02
                atr_multiplier = 2.0  # 2x ATR stop loss

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
                stop_loss_price = price - (atr_value * atr_multiplier)
                take_profit_price = price + (atr_value * atr_multiplier * 2)  # 2:1 risk/reward

                # Execute trade
                power_hour_tag = " [POWER HOUR]" if in_power_hour else ""
                logger.info(f"🚀 EXECUTING{power_hour_tag}: {action} {quantity} {symbol} @ ${price:.2f}")
                logger.info(f"   ATR: ${atr_value:.2f} | Stop: ${stop_loss_price:.2f} | Target: ${take_profit_price:.2f}")
                logger.info(f"   Strategies: {', '.join(strategies)}")
                logger.info(f"   Confidence: {adjusted_confidence:.2%} (raw: {confidence:.2%})")

                order = self.broker.place_market_order(symbol, quantity, action)

                # Validate order result
                if not order or order.get("error"):
                    error_msg = order.get("error", "Unknown error") if order else "No order response"
                    logger.error(f"Order failed for {symbol}: {error_msg}")
                    self._add_decision("ERROR", f"Order failed for {symbol}: {error_msg}", "ERROR", {})
                    continue

                order_id = order.get("orderId") or order.get("order_id") or order.get("id")

                self._add_decision(
                    "TRADE",
                    f"{action} {quantity} {symbol} @ ${price:.2f}",
                    "SUCCESS",
                    {
                        "strategies": strategies,
                        "confidence": adjusted_confidence,
                        "raw_confidence": confidence,
                        "num_strategies": num_strategies,
                        "order_id": order_id,
                        "atr": atr_value,
                        "stop_loss": stop_loss_price,
                        "take_profit": take_profit_price,
                        "power_hour": in_power_hour,
                        "position_sizing": "ATR-based"
                    }
                )

                current_positions += 1

                # Update strategy performance
                for strat in strategies:
                    if strat not in self.strategy_performance:
                        self.strategy_performance[strat] = {"signals": 0, "trades": 0}
                    self.strategy_performance[strat]["signals"] += 1
                    self.strategy_performance[strat]["trades"] += 1

                self._save_state()

            except Exception as e:
                logger.error(f"Error executing trade for {symbol}: {e}")
                self._add_decision("ERROR", f"Failed to execute {symbol}: {str(e)}", "ERROR", {})

    async def _close_position(self, symbol: str, reason: str):
        """Close a position"""
        try:
            positions = self.broker.get_positions()
            position = next((p for p in positions if p.get("symbol") == symbol), None)

            if not position:
                return

            quantity = position.get("quantity", 0)
            current_price = position.get("currentPrice", 0)

            logger.info(f"Closing {symbol}: {reason}")

            order = self.broker.place_market_order(symbol, abs(quantity), "SELL" if quantity > 0 else "BUY")

            # Validate order result
            if not order or order.get("error"):
                error_msg = order.get("error", "Unknown error") if order else "No order response"
                logger.error(f"Close order failed for {symbol}: {error_msg}")
                self._add_decision("ERROR", f"Close order failed for {symbol}: {error_msg}", "ERROR", {})
                return

            order_id = order.get("orderId") or order.get("order_id") or order.get("id")

            self._add_decision(
                "CLOSE",
                f"Closed {symbol}: {reason}",
                "INFO",
                {
                    "quantity": quantity,
                    "price": current_price,
                    "order_id": order_id
                }
            )

        except Exception as e:
            logger.error(f"Error closing {symbol}: {e}")
            self._add_decision("ERROR", f"Failed to close {symbol}: {str(e)}", "ERROR", {})

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
        """Add decision to log"""
        decision = {
            "id": f"d_{datetime.now().timestamp()}",
            "time": datetime.now().strftime("%H:%M:%S"),
            "type": decision_type,
            "action": action,
            "status": status,
            "metadata": metadata
        }

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
