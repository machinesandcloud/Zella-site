"""
Fully Autonomous Trading Engine for Zella AI
Continuously scans, analyzes, and trades using all available strategies
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time
from typing import Any, Dict, List, Optional, Set
import json
from pathlib import Path

import pandas as pd

from core.strategy_engine import StrategyEngine
from core.risk_manager import RiskManager
from core.position_manager import PositionManager
from market.market_data_provider import MarketDataProvider
from ai.screener import MarketScreener
from ai.ml_model import MLSignalModel
from strategies import (
    BreakoutStrategy,
    EmaCrossStrategy,
    HTFEmaMomentumStrategy,
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
        self.scan_interval = self.config.get("scan_interval", 60)  # seconds between scans
        self.max_positions = self.config.get("max_positions", 5)
        self.enabled_strategies = self.config.get("enabled_strategies", "ALL")

        # State
        self.running = False
        self.last_scan_time: Optional[datetime] = None
        self.decisions: List[Dict[str, Any]] = []
        self.active_symbols: Set[str] = set()
        self.strategy_performance: Dict[str, Dict[str, Any]] = {}

        # ML Model for screening
        self.ml_model = MLSignalModel()
        self.ml_model.load()
        self.screener = MarketScreener(self.ml_model)

        # Initialize all available strategies
        self.all_strategies = self._initialize_strategies()

        # Persistent state file
        self.state_file = Path("data/autonomous_state.json")
        self._load_state()

        logger.info(f"Autonomous Engine initialized - Mode: {self.mode}, Risk: {self.risk_posture}")

    def _initialize_strategies(self) -> Dict[str, Any]:
        """Initialize all 35+ trading strategies"""
        strategies = {
            # Trend Following
            "breakout": BreakoutStrategy(),
            "ema_cross": EmaCrossStrategy(),
            "htf_ema_momentum": HTFEmaMomentumStrategy(),
            "momentum": MomentumStrategy(),
            "trend_follow": TrendFollowStrategy(),
            "first_hour_trend": FirstHourTrendStrategy(),

            # Mean Reversion
            "pullback": PullbackStrategy(),
            "range_trading": RangeTradingStrategy(),
            "rsi_exhaustion": RSIExhaustionStrategy(),
            "rsi_extreme_reversal": RSIExtremeReversalStrategy(),
            "vwap_bounce": VWAPBounceStrategy(),
            "nine_forty_five_reversal": NineFortyFiveReversalStrategy(),

            # Scalping & Day Trading
            "scalping": ScalpingStrategy(),
            "orb": ORBStrategy(),
            "rip_and_dip": RipAndDipStrategy(),
            "big_bid_scalp": BigBidScalpStrategy(),

            # Advanced Pattern Recognition
            "retail_fakeout": RetailFakeoutStrategy(),
            "stop_hunt_reversal": StopHuntReversalStrategy(),
            "bagholder_bounce": BagholderBounceStrategy(),
            "broken_parabolic_short": BrokenParabolicShortStrategy(),
            "fake_halt_trap": FakeHaltTrapStrategy(),

            # Institutional & Smart Money
            "closing_bell_liquidity_grab": ClosingBellLiquidityGrabStrategy(),
            "dark_pool_footprints": DarkPoolFootprintsStrategy(),
            "market_maker_refill": MarketMakerRefillStrategy(),
            "premarket_vwap_reclaim": PremarketVWAPReclaimStrategy(),
        }

        logger.info(f"Initialized {len(strategies)} trading strategies")
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
        """Main autonomous trading loop"""
        while self.running:
            try:
                # Check if we should trade
                if not self._should_trade_now():
                    await asyncio.sleep(60)
                    continue

                logger.info("🔍 Starting autonomous scan cycle...")
                self.last_scan_time = datetime.now()

                # 1. Scan market for opportunities
                opportunities = await self._scan_market()

                # 2. Analyze each opportunity with ALL strategies
                analyzed = await self._analyze_opportunities(opportunities)

                # 3. Rank and select best opportunities
                top_picks = self._rank_opportunities(analyzed)

                # 4. Execute trades (if in FULL_AUTO or GOD_MODE)
                if self.mode in ["FULL_AUTO", "GOD_MODE"]:
                    await self._execute_trades(top_picks)

                # 5. Wait for next scan
                await asyncio.sleep(self.scan_interval)

            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                self._add_decision("ERROR", f"Trading loop error: {str(e)}", "ERROR", {})
                await asyncio.sleep(60)

    async def _position_monitor(self):
        """Monitor and manage existing positions"""
        while self.running:
            try:
                positions = self.broker.get_positions()

                for position in positions:
                    symbol = position.get("symbol")
                    current_price = position.get("currentPrice", 0)
                    entry_price = position.get("avgPrice", 0)
                    pnl_percent = position.get("unrealizedPnLPercent", 0)

                    # Dynamic stop loss adjustment
                    if pnl_percent > 5:  # In profit > 5%
                        # Trail stop loss
                        stop_price = current_price * 0.97  # 3% trailing stop
                        logger.info(f"Trailing stop for {symbol}: ${stop_price:.2f}")

                    # Take profit levels
                    if self.risk_posture == "DEFENSIVE" and pnl_percent > 3:
                        logger.info(f"Taking profit on {symbol}: +{pnl_percent:.2f}%")
                        await self._close_position(symbol, "Take profit (defensive)")
                    elif self.risk_posture == "BALANCED" and pnl_percent > 5:
                        logger.info(f"Taking profit on {symbol}: +{pnl_percent:.2f}%")
                        await self._close_position(symbol, "Take profit (balanced)")
                    elif self.risk_posture == "AGGRESSIVE" and pnl_percent > 8:
                        logger.info(f"Taking profit on {symbol}: +{pnl_percent:.2f}%")
                        await self._close_position(symbol, "Take profit (aggressive)")

                    # Stop loss
                    if pnl_percent < -2:
                        logger.warning(f"Stop loss triggered for {symbol}: {pnl_percent:.2f}%")
                        await self._close_position(symbol, "Stop loss")

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error in position monitor: {e}")
                await asyncio.sleep(30)

    async def _scan_market(self) -> List[Dict[str, Any]]:
        """Scan market for trading opportunities"""
        try:
            universe = self.market_data.get_universe()
            logger.info(f"Scanning {len(universe)} symbols...")

            market_data: Dict[str, pd.DataFrame] = {}

            for symbol in universe[:100]:  # Scan top 100 for performance
                try:
                    bars = self.market_data.get_historical_bars(symbol, "1 D", "5 mins")
                    if bars and len(bars) > 0:
                        df = pd.DataFrame(bars)
                        market_data[symbol] = df
                except Exception as e:
                    logger.debug(f"Could not get data for {symbol}: {e}")
                    continue

            # Use ML screener to rank
            ranked = self.screener.rank(market_data)

            logger.info(f"Found {len(ranked)} opportunities")
            self._add_decision("SCAN", f"Scanned {len(market_data)} symbols, found {len(ranked)} opportunities", "INFO", {"count": len(ranked)})

            return ranked

        except Exception as e:
            logger.error(f"Error scanning market: {e}")
            return []

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
                                "reason": signal.get("reason", "")
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
                            "reasoning": " | ".join([f"{s['strategy']}: {s['reason']}" for s in sell_signals[:3]])
                        })

            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")

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
        """Execute trades for top opportunities"""
        if not self.risk_manager.can_trade():
            logger.warning("Risk manager blocks trading")
            return

        account = self.broker.get_account_summary()
        account_value = float(account.get("NetLiquidation", 0) or 0)
        buying_power = float(account.get("BuyingPower", 0) or 0)

        current_positions = len(self.broker.get_positions())

        for opp in opportunities:
            if current_positions >= self.max_positions:
                logger.info(f"Max positions ({self.max_positions}) reached")
                break

            symbol = opp.get("symbol")
            action = opp.get("recommended_action")
            confidence = opp.get("confidence", 0)
            num_strategies = opp.get("num_strategies", 0)
            strategies = opp.get("strategies", [])

            # Only trade high confidence opportunities
            min_confidence = 0.6 if self.risk_posture == "AGGRESSIVE" else 0.7 if self.risk_posture == "BALANCED" else 0.8
            if confidence < min_confidence:
                continue

            # Require multiple strategies to agree
            min_strategies = 2 if self.risk_posture == "AGGRESSIVE" else 3 if self.risk_posture == "BALANCED" else 4
            if num_strategies < min_strategies:
                continue

            try:
                # Calculate position size
                price = opp.get("last_price", 0)
                if price <= 0:
                    continue

                # Risk-based position sizing
                risk_percent = 0.02 if self.risk_posture == "DEFENSIVE" else 0.03 if self.risk_posture == "BALANCED" else 0.05
                position_value = account_value * risk_percent
                quantity = int(position_value / price)

                if quantity <= 0:
                    continue

                # Execute trade
                logger.info(f"🚀 EXECUTING: {action} {quantity} {symbol} @ ${price:.2f}")
                logger.info(f"   Strategies: {', '.join(strategies)}")
                logger.info(f"   Confidence: {confidence:.2%}")

                order = self.broker.place_market_order(symbol, quantity, action)

                self._add_decision(
                    "TRADE",
                    f"{action} {quantity} {symbol} @ ${price:.2f}",
                    "SUCCESS",
                    {
                        "strategies": strategies,
                        "confidence": confidence,
                        "num_strategies": num_strategies,
                        "order_id": order.get("orderId")
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

            self._add_decision(
                "CLOSE",
                f"Closed {symbol}: {reason}",
                "INFO",
                {
                    "quantity": quantity,
                    "price": current_price,
                    "order_id": order.get("orderId")
                }
            )

        except Exception as e:
            logger.error(f"Error closing {symbol}: {e}")

    def _should_trade_now(self) -> bool:
        """Check if we should trade at this time"""
        if not self.enabled or not self.running:
            return False

        # Check market hours
        now = datetime.now().time()
        market_open = time(9, 30)
        market_close = time(16, 0)

        if not (market_open <= now <= market_close):
            return False

        # Check if broker connected
        if not self.broker.is_connected():
            return False

        return True

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
        """Get current engine status"""
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
            "connected": self.broker.is_connected()
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
