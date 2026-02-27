"""
Machine Learning Engine for Zella AI Trading

This engine learns from trade outcomes to improve over time:
1. Tracks trade results with full context (strategy, conditions, etc.)
2. Analyzes patterns in winning vs losing trades
3. Adjusts strategy weights based on performance
4. Tunes confidence thresholds and position sizes
5. Persists learning data to survive restarts
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from threading import Lock

import numpy as np

logger = logging.getLogger("learning_engine")


@dataclass
class TradeRecord:
    """Record of a completed trade with full context."""
    symbol: str
    strategy: str
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    entry_time: datetime
    exit_time: datetime
    # Optional context fields with defaults
    action: str = "BUY"
    pnl_percent: float = 0.0
    duration_minutes: int = 0
    confidence: float = 0.5
    setup_grade: str = "B"
    volatility_regime: str = "normal"
    time_of_day: str = "midday"
    day_of_week: int = 0
    market_trend: str = "sideways"
    market_condition: str = "ranging"
    relative_volume: float = 1.0
    atr_percent: float = 2.0
    num_strategies_agreed: int = 1
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        # Calculate derived fields
        if self.entry_price > 0:
            self.pnl_percent = ((self.exit_price - self.entry_price) / self.entry_price) * 100
        if isinstance(self.entry_time, datetime) and isinstance(self.exit_time, datetime):
            self.duration_minutes = int((self.exit_time - self.entry_time).total_seconds() / 60)
            self.day_of_week = self.exit_time.weekday()


@dataclass
class StrategyPerformance:
    """Performance metrics for a single strategy."""
    name: str
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    weight: float = 1.0  # Adaptive weight (1.0 = neutral)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class LearningState:
    """Persistent learning state."""
    trade_history: List[Dict] = field(default_factory=list)
    strategy_performance: Dict[str, Dict] = field(default_factory=dict)
    confidence_adjustments: Dict[str, float] = field(default_factory=dict)
    optimal_parameters: Dict[str, Any] = field(default_factory=dict)
    learning_cycles: int = 0
    last_learning_time: str = ""
    version: str = "1.0"


class LearningEngine:
    """
    Machine Learning Engine that improves trading performance over time.

    Key features:
    - Tracks all trades with full context
    - Identifies winning patterns (strategy + conditions)
    - Adjusts strategy weights based on real performance
    - Tunes confidence thresholds adaptively
    - Persists learning across restarts
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.data_dir / "learning_state.json"
        self._lock = Lock()

        # Load or initialize state
        self.state = self._load_state()

        # Strategy performance cache
        self.strategy_stats: Dict[str, StrategyPerformance] = {}
        self._rebuild_strategy_stats()

        # Learning parameters
        self.min_trades_for_adjustment = 10  # Min trades before adjusting weights
        self.weight_adjustment_rate = 0.1  # How fast weights change
        self.max_weight = 2.0  # Max strategy weight multiplier
        self.min_weight = 0.3  # Min strategy weight multiplier

        logger.info(f"Learning Engine initialized - {len(self.state.trade_history)} historical trades")

    def _load_state(self) -> LearningState:
        """Load learning state from disk."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    return LearningState(
                        trade_history=data.get("trade_history", []),
                        strategy_performance=data.get("strategy_performance", {}),
                        confidence_adjustments=data.get("confidence_adjustments", {}),
                        optimal_parameters=data.get("optimal_parameters", {}),
                        learning_cycles=data.get("learning_cycles", 0),
                        last_learning_time=data.get("last_learning_time", ""),
                        version=data.get("version", "1.0")
                    )
        except Exception as e:
            logger.error(f"Error loading learning state: {e}")

        return LearningState()

    def _save_state(self):
        """Save learning state to disk."""
        try:
            with self._lock:
                data = {
                    "trade_history": self.state.trade_history,
                    "strategy_performance": self.state.strategy_performance,
                    "confidence_adjustments": self.state.confidence_adjustments,
                    "optimal_parameters": self.state.optimal_parameters,
                    "learning_cycles": self.state.learning_cycles,
                    "last_learning_time": self.state.last_learning_time,
                    "version": self.state.version
                }
                with open(self.state_file, 'w') as f:
                    json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving learning state: {e}")

    def _rebuild_strategy_stats(self):
        """Rebuild strategy statistics from trade history."""
        self.strategy_stats.clear()

        for trade in self.state.trade_history:
            strategy = trade.get("strategy", "unknown")
            if strategy not in self.strategy_stats:
                self.strategy_stats[strategy] = StrategyPerformance(name=strategy)

            stats = self.strategy_stats[strategy]
            stats.total_trades += 1
            pnl = trade.get("pnl", 0)
            stats.total_pnl += pnl

            if pnl > 0:
                stats.wins += 1
            elif pnl < 0:
                stats.losses += 1

        # Calculate derived metrics
        for name, stats in self.strategy_stats.items():
            if stats.total_trades > 0:
                stats.win_rate = (stats.wins / stats.total_trades) * 100

            # Get win/loss averages from trades
            wins = [t["pnl"] for t in self.state.trade_history
                   if t.get("strategy") == name and t.get("pnl", 0) > 0]
            losses = [abs(t["pnl"]) for t in self.state.trade_history
                     if t.get("strategy") == name and t.get("pnl", 0) < 0]

            stats.avg_win = np.mean(wins) if wins else 0
            stats.avg_loss = np.mean(losses) if losses else 0
            stats.profit_factor = stats.avg_win / stats.avg_loss if stats.avg_loss > 0 else 0

            # Load saved weight if exists
            if name in self.state.strategy_performance:
                stats.weight = self.state.strategy_performance[name].get("weight", 1.0)

    def record_trade(self, trade: TradeRecord):
        """Record a completed trade for learning."""
        with self._lock:
            self.state.trade_history.append(asdict(trade))

            # Limit history size (keep last 1000 trades)
            if len(self.state.trade_history) > 1000:
                self.state.trade_history = self.state.trade_history[-1000:]

        # Update strategy stats
        if trade.strategy not in self.strategy_stats:
            self.strategy_stats[trade.strategy] = StrategyPerformance(name=trade.strategy)

        stats = self.strategy_stats[trade.strategy]
        stats.total_trades += 1
        stats.total_pnl += trade.pnl

        if trade.pnl > 0:
            stats.wins += 1
        elif trade.pnl < 0:
            stats.losses += 1

        # Recalculate metrics
        if stats.total_trades > 0:
            stats.win_rate = (stats.wins / stats.total_trades) * 100

        self._save_state()
        logger.info(f"Recorded trade: {trade.symbol} via {trade.strategy} = ${trade.pnl:.2f}")

    def run_learning_cycle(self) -> Dict[str, Any]:
        """
        Run a learning cycle to analyze trades and adjust parameters.

        Returns:
            Summary of adjustments made
        """
        logger.info("Running learning cycle...")

        adjustments = {
            "strategy_weights": {},
            "confidence_adjustments": {},
            "insights": []
        }

        # 1. Adjust strategy weights based on performance
        for name, stats in self.strategy_stats.items():
            if stats.total_trades < self.min_trades_for_adjustment:
                continue

            old_weight = stats.weight

            # Increase weight for profitable strategies
            if stats.profit_factor > 1.5 and stats.win_rate > 55:
                new_weight = min(old_weight * (1 + self.weight_adjustment_rate), self.max_weight)
                adjustments["insights"].append(f"📈 {name}: Strong performer, weight increased")
            elif stats.profit_factor < 0.8 or stats.win_rate < 40:
                new_weight = max(old_weight * (1 - self.weight_adjustment_rate), self.min_weight)
                adjustments["insights"].append(f"📉 {name}: Underperforming, weight decreased")
            else:
                new_weight = old_weight

            if new_weight != old_weight:
                stats.weight = new_weight
                adjustments["strategy_weights"][name] = {
                    "old": round(old_weight, 2),
                    "new": round(new_weight, 2)
                }

        # 2. Analyze winning vs losing trade patterns
        recent_trades = self.state.trade_history[-100:]  # Last 100 trades

        if len(recent_trades) >= 20:
            wins = [t for t in recent_trades if t.get("pnl", 0) > 0]
            losses = [t for t in recent_trades if t.get("pnl", 0) < 0]

            # Analyze confidence levels
            if wins and losses:
                avg_win_confidence = np.mean([t.get("confidence", 0.7) for t in wins])
                avg_loss_confidence = np.mean([t.get("confidence", 0.7) for t in losses])

                if avg_win_confidence > avg_loss_confidence + 0.05:
                    new_threshold = (avg_win_confidence + avg_loss_confidence) / 2
                    adjustments["confidence_adjustments"]["recommended_threshold"] = round(new_threshold, 2)
                    adjustments["insights"].append(
                        f"💡 Winners avg confidence: {avg_win_confidence:.2f}, "
                        f"Losers: {avg_loss_confidence:.2f} - Consider raising threshold"
                    )

            # Analyze time of day patterns
            time_stats = {}
            for t in recent_trades:
                tod = t.get("time_of_day", "UNKNOWN")
                if tod not in time_stats:
                    time_stats[tod] = {"wins": 0, "losses": 0}
                if t.get("pnl", 0) > 0:
                    time_stats[tod]["wins"] += 1
                else:
                    time_stats[tod]["losses"] += 1

            for tod, s in time_stats.items():
                total = s["wins"] + s["losses"]
                if total >= 5:
                    win_rate = (s["wins"] / total) * 100
                    if win_rate > 65:
                        adjustments["insights"].append(f"✅ {tod}: {win_rate:.0f}% win rate - favorable time")
                    elif win_rate < 35:
                        adjustments["insights"].append(f"❌ {tod}: {win_rate:.0f}% win rate - avoid trading")

            # Analyze grade patterns
            grade_stats = {}
            for t in recent_trades:
                grade = t.get("setup_grade", "B")
                if grade not in grade_stats:
                    grade_stats[grade] = {"wins": 0, "losses": 0, "pnl": 0}
                grade_stats[grade]["pnl"] += t.get("pnl", 0)
                if t.get("pnl", 0) > 0:
                    grade_stats[grade]["wins"] += 1
                else:
                    grade_stats[grade]["losses"] += 1

            for grade, s in grade_stats.items():
                total = s["wins"] + s["losses"]
                if total >= 5:
                    win_rate = (s["wins"] / total) * 100
                    adjustments["insights"].append(
                        f"Grade {grade}: {win_rate:.0f}% win rate, ${s['pnl']:.0f} total P&L"
                    )

        # Save updated state
        for name, stats in self.strategy_stats.items():
            self.state.strategy_performance[name] = {
                "weight": stats.weight,
                "win_rate": stats.win_rate,
                "profit_factor": stats.profit_factor,
                "total_trades": stats.total_trades
            }

        # Save recent insights for later retrieval
        self.state.optimal_parameters["recent_insights"] = adjustments["insights"]

        self.state.learning_cycles += 1
        self.state.last_learning_time = datetime.now().isoformat()
        self._save_state()

        logger.info(f"Learning cycle complete - {len(adjustments['insights'])} insights")

        # Return in format expected by autonomous_engine
        weight_changes = {}
        for name, change in adjustments["strategy_weights"].items():
            weight_changes[name] = change["new"] - change["old"]

        return {
            "insights": adjustments["insights"],
            "weight_changes": weight_changes,
            "trades_analyzed": len(recent_trades) if 'recent_trades' in dir() else 0,
            "strategies_adjusted": len(adjustments["strategy_weights"])
        }

    def get_strategy_weight(self, strategy: str) -> float:
        """Get the learned weight for a strategy."""
        if strategy in self.strategy_stats:
            return self.strategy_stats[strategy].weight
        return 1.0  # Default weight

    def get_recommended_confidence_threshold(self) -> float:
        """Get the learned recommended confidence threshold."""
        return self.state.confidence_adjustments.get("recommended_threshold", 0.70)

    def should_trade_now(self, time_of_day: str) -> bool:
        """Check if trading is recommended for the current time based on learning."""
        # Analyze historical performance for this time
        recent = self.state.trade_history[-100:]
        tod_trades = [t for t in recent if t.get("time_of_day") == time_of_day]

        if len(tod_trades) < 5:
            return True  # Not enough data, allow trading

        wins = sum(1 for t in tod_trades if t.get("pnl", 0) > 0)
        win_rate = wins / len(tod_trades)

        return win_rate >= 0.35  # Don't trade if win rate < 35%

    def get_learning_summary(self) -> Dict[str, Any]:
        """Get a summary of what the bot has learned."""
        return {
            "total_trades_analyzed": len(self.state.trade_history),
            "learning_cycles_completed": self.state.learning_cycles,
            "last_learning": self.state.last_learning_time,
            "strategy_weights": {
                name: round(stats.weight, 2)
                for name, stats in self.strategy_stats.items()
            },
            "strategy_performance": {
                name: {
                    "trades": stats.total_trades,
                    "win_rate": round(stats.win_rate, 1),
                    "profit_factor": round(stats.profit_factor, 2),
                    "total_pnl": round(stats.total_pnl, 2)
                }
                for name, stats in self.strategy_stats.items()
            },
            "recommended_confidence": self.get_recommended_confidence_threshold()
        }

    def get_all_weights(self) -> Dict[str, float]:
        """Get all strategy weights for UI display."""
        return {
            name: round(stats.weight, 2)
            for name, stats in self.strategy_stats.items()
        }

    def get_recent_insights(self, limit: int = 5) -> List[str]:
        """Get recent learning insights for UI display."""
        insights = []

        # Get insights from recent learning cycle if available
        if self.state.optimal_parameters.get("recent_insights"):
            insights = self.state.optimal_parameters["recent_insights"][:limit]

        # If no saved insights, generate some from current data
        if not insights and self.strategy_stats:
            for name, stats in list(self.strategy_stats.items())[:limit]:
                if stats.total_trades >= 5:
                    if stats.win_rate > 60:
                        insights.append(f"📈 {name}: {stats.win_rate:.0f}% win rate - strong performer")
                    elif stats.win_rate < 40:
                        insights.append(f"📉 {name}: {stats.win_rate:.0f}% win rate - needs improvement")
                    else:
                        insights.append(f"➡️ {name}: {stats.win_rate:.0f}% win rate - neutral")

        return insights[:limit]


# Global instance
_learning_engine: Optional[LearningEngine] = None


def get_learning_engine() -> LearningEngine:
    """Get or create the global learning engine instance."""
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = LearningEngine()
    return _learning_engine
