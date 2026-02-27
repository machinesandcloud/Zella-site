"""
Elite Day Trading System for Zella AI

This module implements institutional-grade trading logic used by professional
day traders and hedge funds. These are the techniques that separate consistently
profitable traders from the 90% who lose money.

Key Principles:
1. Trade WITH the trend, not against it (multi-timeframe)
2. Trade leaders, not laggards (relative strength)
3. Respect key levels (support/resistance)
4. Scale out of winners (partial profits)
5. Protect capital (breakeven stops)
6. Stay disciplined (revenge prevention)
7. Know when to quit (max winners)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd
import numpy as np

logger = logging.getLogger("elite_trade_system")


class TrendDirection(Enum):
    STRONG_UP = "STRONG_UP"
    UP = "UP"
    NEUTRAL = "NEUTRAL"
    DOWN = "DOWN"
    STRONG_DOWN = "STRONG_DOWN"


class SetupGrade(Enum):
    A_PLUS = "A+"  # Perfect setup - full size
    A = "A"        # Great setup - full size
    B = "B"        # Good setup - 75% size
    C = "C"        # Marginal - 50% size or skip
    F = "F"        # Bad setup - never trade


@dataclass
class TimeframeTrend:
    """Trend analysis for a single timeframe."""
    timeframe: str
    direction: TrendDirection
    ema_fast: float
    ema_slow: float
    price_vs_ema: float  # % above/below EMA
    momentum: float  # Rate of change


@dataclass
class MultiTimeframeAnalysis:
    """Combined analysis across multiple timeframes."""
    symbol: str
    trends: Dict[str, TimeframeTrend]
    alignment_score: float  # -1 to 1, positive = bullish alignment
    primary_trend: TrendDirection
    trade_with_trend: str  # "LONG", "SHORT", or "NEUTRAL"
    conflicts: List[str]


@dataclass
class RelativeStrength:
    """Relative strength vs benchmark (SPY)."""
    symbol: str
    rs_ratio: float  # > 1 = outperforming, < 1 = underperforming
    rs_momentum: float  # Change in RS over time
    is_leader: bool  # Top 20% performers
    is_laggard: bool  # Bottom 20% performers
    rank_percentile: float  # 0-100, higher = stronger


@dataclass
class SupportResistance:
    """Key support and resistance levels."""
    symbol: str
    current_price: float
    nearest_support: float
    nearest_resistance: float
    distance_to_support_pct: float
    distance_to_resistance_pct: float
    at_support: bool  # Within 0.5% of support
    at_resistance: bool  # Within 0.5% of resistance
    hod: float  # High of day
    lod: float  # Low of day
    premarket_high: float
    premarket_low: float
    previous_close: float


@dataclass
class GapAnalysis:
    """Gap analysis for gap-and-go vs gap-and-fade."""
    symbol: str
    gap_percent: float
    gap_type: str  # "GAP_UP", "GAP_DOWN", "NO_GAP"
    gap_filled: bool
    is_gap_and_go: bool  # Gap with momentum continuation
    is_gap_and_fade: bool  # Gap likely to fill


@dataclass
class PositionScaleOut:
    """Scaling out plan for a position."""
    symbol: str
    total_quantity: int
    remaining_quantity: int
    scale_levels: List[Dict[str, Any]]  # {price, quantity, executed}
    current_stop: float
    original_stop: float
    breakeven_activated: bool
    trailing_activated: bool


@dataclass
class TradingState:
    """Current trading session state for discipline enforcement."""
    date: str
    trades_today: int = 0
    winners_today: int = 0
    losers_today: int = 0
    consecutive_losses: int = 0
    last_loss_time: Optional[datetime] = None
    daily_pnl: float = 0.0
    daily_high_pnl: float = 0.0
    cooldown_until: Optional[datetime] = None
    halted: bool = False
    halt_reason: Optional[str] = None


class MultiTimeframeAnalyzer:
    """
    Analyze trend across multiple timeframes.

    RULE: Only trade when at least 2 of 3 timeframes agree on direction.
    Never fight the higher timeframe trend.
    """

    def __init__(self, fast_period: int = 9, slow_period: int = 21):
        self.fast_period = fast_period
        self.slow_period = slow_period

    def analyze_timeframe(self, df: pd.DataFrame, timeframe: str) -> TimeframeTrend:
        """Analyze trend for a single timeframe."""
        if len(df) < self.slow_period:
            return TimeframeTrend(
                timeframe=timeframe,
                direction=TrendDirection.NEUTRAL,
                ema_fast=0, ema_slow=0,
                price_vs_ema=0, momentum=0
            )

        close = df['close']
        ema_fast = close.ewm(span=self.fast_period).mean().iloc[-1]
        ema_slow = close.ewm(span=self.slow_period).mean().iloc[-1]
        current_price = close.iloc[-1]

        # Price vs slow EMA (trend reference)
        price_vs_ema = ((current_price - ema_slow) / ema_slow) * 100

        # Momentum: rate of change over last 5 periods
        if len(close) >= 5:
            momentum = ((close.iloc[-1] - close.iloc[-5]) / close.iloc[-5]) * 100
        else:
            momentum = 0

        # Determine trend direction
        if ema_fast > ema_slow and current_price > ema_fast:
            if price_vs_ema > 2:
                direction = TrendDirection.STRONG_UP
            else:
                direction = TrendDirection.UP
        elif ema_fast < ema_slow and current_price < ema_fast:
            if price_vs_ema < -2:
                direction = TrendDirection.STRONG_DOWN
            else:
                direction = TrendDirection.DOWN
        else:
            direction = TrendDirection.NEUTRAL

        return TimeframeTrend(
            timeframe=timeframe,
            direction=direction,
            ema_fast=ema_fast,
            ema_slow=ema_slow,
            price_vs_ema=price_vs_ema,
            momentum=momentum
        )

    def analyze_multiple(
        self,
        symbol: str,
        data_5m: pd.DataFrame,
        data_15m: pd.DataFrame,
        data_1h: pd.DataFrame
    ) -> MultiTimeframeAnalysis:
        """
        Analyze trend across 5-min, 15-min, and 1-hour timeframes.

        Returns alignment score and trading direction.
        """
        trend_5m = self.analyze_timeframe(data_5m, "5m")
        trend_15m = self.analyze_timeframe(data_15m, "15m")
        trend_1h = self.analyze_timeframe(data_1h, "1h")

        trends = {"5m": trend_5m, "15m": trend_15m, "1h": trend_1h}

        # Calculate alignment score
        # Higher timeframes get more weight
        weights = {"5m": 1, "15m": 2, "1h": 3}

        def direction_score(d: TrendDirection) -> float:
            scores = {
                TrendDirection.STRONG_UP: 1.0,
                TrendDirection.UP: 0.5,
                TrendDirection.NEUTRAL: 0,
                TrendDirection.DOWN: -0.5,
                TrendDirection.STRONG_DOWN: -1.0
            }
            return scores.get(d, 0)

        total_weight = sum(weights.values())
        alignment_score = sum(
            direction_score(trends[tf].direction) * weights[tf]
            for tf in trends
        ) / total_weight

        # Determine primary trend (weighted toward higher TF)
        if alignment_score > 0.3:
            primary_trend = TrendDirection.UP
            trade_with_trend = "LONG"
        elif alignment_score < -0.3:
            primary_trend = TrendDirection.DOWN
            trade_with_trend = "SHORT"
        else:
            primary_trend = TrendDirection.NEUTRAL
            trade_with_trend = "NEUTRAL"

        # Identify conflicts
        conflicts = []
        if trend_5m.direction in [TrendDirection.UP, TrendDirection.STRONG_UP]:
            if trend_1h.direction in [TrendDirection.DOWN, TrendDirection.STRONG_DOWN]:
                conflicts.append("5m bullish but 1h bearish - DANGER")
        if trend_5m.direction in [TrendDirection.DOWN, TrendDirection.STRONG_DOWN]:
            if trend_1h.direction in [TrendDirection.UP, TrendDirection.STRONG_UP]:
                conflicts.append("5m bearish but 1h bullish - DANGER")

        return MultiTimeframeAnalysis(
            symbol=symbol,
            trends=trends,
            alignment_score=alignment_score,
            primary_trend=primary_trend,
            trade_with_trend=trade_with_trend,
            conflicts=conflicts
        )


class RelativeStrengthAnalyzer:
    """
    Compare stock performance to benchmark (SPY).

    RULE: In uptrends, trade leaders (outperformers).
           In downtrends, short laggards (underperformers).
    """

    def __init__(self, lookback_periods: int = 20):
        self.lookback_periods = lookback_periods
        self._cache: Dict[str, RelativeStrength] = {}
        self._rankings: List[Tuple[str, float]] = []

    def calculate_rs(
        self,
        symbol: str,
        symbol_data: pd.DataFrame,
        spy_data: pd.DataFrame
    ) -> RelativeStrength:
        """Calculate relative strength vs SPY."""
        if len(symbol_data) < self.lookback_periods or len(spy_data) < self.lookback_periods:
            return RelativeStrength(
                symbol=symbol, rs_ratio=1.0, rs_momentum=0,
                is_leader=False, is_laggard=False, rank_percentile=50
            )

        # Calculate returns
        symbol_return = (symbol_data['close'].iloc[-1] / symbol_data['close'].iloc[-self.lookback_periods] - 1) * 100
        spy_return = (spy_data['close'].iloc[-1] / spy_data['close'].iloc[-self.lookback_periods] - 1) * 100

        # RS Ratio (stock return / benchmark return)
        if spy_return != 0:
            rs_ratio = symbol_return / spy_return if spy_return > 0 else symbol_return / abs(spy_return) * -1
        else:
            rs_ratio = 1.0 if symbol_return >= 0 else -1.0

        # RS Momentum (change in RS)
        if len(symbol_data) >= self.lookback_periods + 5:
            prev_symbol_ret = (symbol_data['close'].iloc[-5] / symbol_data['close'].iloc[-self.lookback_periods-5] - 1) * 100
            prev_spy_ret = (spy_data['close'].iloc[-5] / spy_data['close'].iloc[-self.lookback_periods-5] - 1) * 100
            prev_rs = prev_symbol_ret / prev_spy_ret if prev_spy_ret != 0 else 1.0
            rs_momentum = rs_ratio - prev_rs
        else:
            rs_momentum = 0

        return RelativeStrength(
            symbol=symbol,
            rs_ratio=round(rs_ratio, 3),
            rs_momentum=round(rs_momentum, 3),
            is_leader=rs_ratio > 1.2,  # 20% outperformance
            is_laggard=rs_ratio < 0.8,  # 20% underperformance
            rank_percentile=50  # Will be updated when ranking multiple stocks
        )

    def rank_universe(
        self,
        universe_data: Dict[str, pd.DataFrame],
        spy_data: pd.DataFrame
    ) -> List[Tuple[str, RelativeStrength]]:
        """Rank entire universe by relative strength."""
        rs_scores = []

        for symbol, data in universe_data.items():
            rs = self.calculate_rs(symbol, data, spy_data)
            rs_scores.append((symbol, rs))
            self._cache[symbol] = rs

        # Sort by RS ratio
        rs_scores.sort(key=lambda x: x[1].rs_ratio, reverse=True)

        # Assign percentile rankings
        n = len(rs_scores)
        for i, (symbol, rs) in enumerate(rs_scores):
            percentile = ((n - i) / n) * 100
            rs.rank_percentile = round(percentile, 1)
            rs.is_leader = percentile >= 80
            rs.is_laggard = percentile <= 20
            self._cache[symbol] = rs

        self._rankings = rs_scores
        return rs_scores


class SupportResistanceDetector:
    """
    Detect key support and resistance levels.

    RULE: Don't buy into resistance, don't sell into support.
          Breakouts of key levels are high-probability trades.
    """

    def __init__(self, lookback: int = 50, tolerance_pct: float = 0.5):
        self.lookback = lookback
        self.tolerance_pct = tolerance_pct

    def find_levels(self, df: pd.DataFrame, symbol: str) -> SupportResistance:
        """Find support, resistance, and key intraday levels."""
        if len(df) < 10:
            price = df['close'].iloc[-1] if len(df) > 0 else 0
            return SupportResistance(
                symbol=symbol, current_price=price,
                nearest_support=price * 0.98, nearest_resistance=price * 1.02,
                distance_to_support_pct=2, distance_to_resistance_pct=2,
                at_support=False, at_resistance=False,
                hod=price, lod=price,
                premarket_high=price, premarket_low=price,
                previous_close=price
            )

        current_price = df['close'].iloc[-1]
        high = df['high']
        low = df['low']
        close = df['close']

        # Find pivot points (local highs/lows)
        resistance_levels = []
        support_levels = []

        for i in range(2, min(len(df) - 2, self.lookback)):
            # Local high (resistance)
            if high.iloc[-i] > high.iloc[-i-1] and high.iloc[-i] > high.iloc[-i+1]:
                if high.iloc[-i] > high.iloc[-i-2] and high.iloc[-i] > high.iloc[-i+2]:
                    resistance_levels.append(high.iloc[-i])

            # Local low (support)
            if low.iloc[-i] < low.iloc[-i-1] and low.iloc[-i] < low.iloc[-i+1]:
                if low.iloc[-i] < low.iloc[-i-2] and low.iloc[-i] < low.iloc[-i+2]:
                    support_levels.append(low.iloc[-i])

        # Add obvious levels
        resistance_levels.extend([high.iloc[-self.lookback:].max()])
        support_levels.extend([low.iloc[-self.lookback:].min()])

        # Find nearest levels
        resistance_above = [r for r in resistance_levels if r > current_price]
        support_below = [s for s in support_levels if s < current_price]

        nearest_resistance = min(resistance_above) if resistance_above else current_price * 1.05
        nearest_support = max(support_below) if support_below else current_price * 0.95

        # Calculate distances
        dist_to_support = ((current_price - nearest_support) / current_price) * 100
        dist_to_resistance = ((nearest_resistance - current_price) / current_price) * 100

        # Get intraday levels (assuming last bar is today)
        hod = high.iloc[-1]
        lod = low.iloc[-1]
        previous_close = close.iloc[-2] if len(close) > 1 else close.iloc[-1]

        # Premarket levels (would need premarket data - using approximation)
        premarket_high = max(df['open'].iloc[-1], hod)
        premarket_low = min(df['open'].iloc[-1], lod)

        return SupportResistance(
            symbol=symbol,
            current_price=round(current_price, 2),
            nearest_support=round(nearest_support, 2),
            nearest_resistance=round(nearest_resistance, 2),
            distance_to_support_pct=round(dist_to_support, 2),
            distance_to_resistance_pct=round(dist_to_resistance, 2),
            at_support=dist_to_support <= self.tolerance_pct,
            at_resistance=dist_to_resistance <= self.tolerance_pct,
            hod=round(hod, 2),
            lod=round(lod, 2),
            premarket_high=round(premarket_high, 2),
            premarket_low=round(premarket_low, 2),
            previous_close=round(previous_close, 2)
        )


class GapAnalyzer:
    """
    Analyze gap behavior for gap-and-go vs gap-and-fade setups.

    RULE: Gap-and-go = gap with volume and momentum (continuation)
          Gap-and-fade = gap into resistance/exhaustion (reversal)
    """

    def __init__(self, min_gap_pct: float = 2.0):
        self.min_gap_pct = min_gap_pct

    def analyze(
        self,
        symbol: str,
        current_price: float,
        open_price: float,
        previous_close: float,
        volume: int,
        avg_volume: int,
        premarket_high: float,
        current_high: float
    ) -> GapAnalysis:
        """Analyze gap type and likely behavior."""
        gap_percent = ((open_price - previous_close) / previous_close) * 100

        if abs(gap_percent) < self.min_gap_pct:
            return GapAnalysis(
                symbol=symbol,
                gap_percent=round(gap_percent, 2),
                gap_type="NO_GAP",
                gap_filled=False,
                is_gap_and_go=False,
                is_gap_and_fade=False
            )

        gap_type = "GAP_UP" if gap_percent > 0 else "GAP_DOWN"

        # Check if gap is filled
        if gap_type == "GAP_UP":
            gap_filled = current_price <= previous_close
        else:
            gap_filled = current_price >= previous_close

        # Gap-and-go criteria:
        # 1. High volume (> 1.5x average)
        # 2. Price holding above premarket high (for gap up) or below premarket low
        # 3. Not filling the gap
        relative_volume = volume / avg_volume if avg_volume > 0 else 1

        if gap_type == "GAP_UP":
            is_gap_and_go = (
                relative_volume > 1.5 and
                current_price >= open_price * 0.99 and  # Holding near open
                current_high > premarket_high and  # Breaking premarket high
                not gap_filled
            )
            is_gap_and_fade = (
                current_price < open_price * 0.98 or  # Fading from open
                gap_filled
            )
        else:  # GAP_DOWN
            is_gap_and_go = (
                relative_volume > 1.5 and
                current_price <= open_price * 1.01 and
                not gap_filled
            )
            is_gap_and_fade = (
                current_price > open_price * 1.02 or
                gap_filled
            )

        return GapAnalysis(
            symbol=symbol,
            gap_percent=round(gap_percent, 2),
            gap_type=gap_type,
            gap_filled=gap_filled,
            is_gap_and_go=is_gap_and_go,
            is_gap_and_fade=is_gap_and_fade
        )


class PositionManager:
    """
    Manages position scaling and stop management.

    SCALING RULES:
    1. Take 50% profit at 1R (risk/reward 1:1)
    2. Move stop to breakeven after 1R
    3. Trail remaining 50% with ATR-based stop
    4. Take final 25% at 2R, let 25% run to 3R
    """

    def __init__(self):
        self.positions: Dict[str, PositionScaleOut] = {}

    def create_scale_plan(
        self,
        symbol: str,
        entry_price: float,
        quantity: int,
        stop_loss: float,
        take_profit_1r: float,
        take_profit_2r: float,
        take_profit_3r: float
    ) -> PositionScaleOut:
        """Create a scaling out plan for a new position."""
        risk = abs(entry_price - stop_loss)

        scale_levels = [
            {
                "level": "1R",
                "price": take_profit_1r,
                "quantity": int(quantity * 0.50),  # 50% at 1R
                "executed": False,
                "action": "SCALE_OUT_50_PCT"
            },
            {
                "level": "2R",
                "price": take_profit_2r,
                "quantity": int(quantity * 0.25),  # 25% at 2R
                "executed": False,
                "action": "SCALE_OUT_25_PCT"
            },
            {
                "level": "3R",
                "price": take_profit_3r,
                "quantity": quantity - int(quantity * 0.75),  # Remaining at 3R
                "executed": False,
                "action": "CLOSE_REMAINING"
            }
        ]

        plan = PositionScaleOut(
            symbol=symbol,
            total_quantity=quantity,
            remaining_quantity=quantity,
            scale_levels=scale_levels,
            current_stop=stop_loss,
            original_stop=stop_loss,
            breakeven_activated=False,
            trailing_activated=False
        )

        self.positions[symbol] = plan
        return plan

    def check_scale_levels(
        self,
        symbol: str,
        current_price: float,
        entry_price: float
    ) -> List[Dict[str, Any]]:
        """Check if any scale levels have been hit."""
        if symbol not in self.positions:
            return []

        plan = self.positions[symbol]
        actions = []

        for level in plan.scale_levels:
            if level["executed"]:
                continue

            # Check if price hit the level
            if current_price >= level["price"]:
                actions.append({
                    "action": level["action"],
                    "level": level["level"],
                    "quantity": level["quantity"],
                    "price": level["price"]
                })
                level["executed"] = True
                plan.remaining_quantity -= level["quantity"]

                # Activate breakeven after 1R
                if level["level"] == "1R" and not plan.breakeven_activated:
                    plan.current_stop = entry_price
                    plan.breakeven_activated = True
                    actions.append({
                        "action": "MOVE_STOP_TO_BREAKEVEN",
                        "new_stop": entry_price
                    })

                # Activate trailing after 2R
                if level["level"] == "2R" and not plan.trailing_activated:
                    plan.trailing_activated = True
                    actions.append({
                        "action": "ACTIVATE_TRAILING_STOP"
                    })

        return actions

    def update_trailing_stop(
        self,
        symbol: str,
        current_price: float,
        atr_value: float,
        trail_multiplier: float = 1.5
    ) -> Optional[float]:
        """Update trailing stop for active positions."""
        if symbol not in self.positions:
            return None

        plan = self.positions[symbol]

        if not plan.trailing_activated:
            return None

        # Calculate new potential stop
        new_stop = current_price - (atr_value * trail_multiplier)

        # Only raise stop, never lower it
        if new_stop > plan.current_stop:
            plan.current_stop = new_stop
            return new_stop

        return None

    def restore_scale_plan(self, symbol: str, plan_data: Dict[str, Any]) -> None:
        """
        Restore a scale-out plan from saved state.
        Used for recovery from disconnections/restarts.
        """
        try:
            # Recreate scale levels from saved data
            entry_price = plan_data.get("entry_price", 0)
            quantity = plan_data.get("quantity", 0)
            stop_loss = plan_data.get("stop_loss", 0)
            take_profit_1r = plan_data.get("take_profit_1r", 0)
            take_profit_2r = plan_data.get("take_profit_2r", 0)
            take_profit_3r = plan_data.get("take_profit_3r", 0)

            # Check which levels were already executed
            scaled_1r = plan_data.get("scaled_1r", False)
            scaled_2r = plan_data.get("scaled_2r", False)

            scale_levels = [
                {
                    "level": "1R",
                    "price": take_profit_1r,
                    "quantity": int(quantity * 0.50),
                    "executed": scaled_1r,
                    "action": "SCALE_OUT_50_PCT"
                },
                {
                    "level": "2R",
                    "price": take_profit_2r,
                    "quantity": int(quantity * 0.25),
                    "executed": scaled_2r,
                    "action": "SCALE_OUT_25_PCT"
                },
                {
                    "level": "3R",
                    "price": take_profit_3r,
                    "quantity": quantity - int(quantity * 0.75),
                    "executed": False,
                    "action": "CLOSE_REMAINING"
                }
            ]

            # Calculate remaining quantity
            remaining = quantity
            if scaled_1r:
                remaining -= int(quantity * 0.50)
            if scaled_2r:
                remaining -= int(quantity * 0.25)

            plan = PositionScaleOut(
                symbol=symbol,
                total_quantity=quantity,
                remaining_quantity=remaining,
                scale_levels=scale_levels,
                current_stop=plan_data.get("current_stop", stop_loss),
                original_stop=stop_loss,
                breakeven_activated=plan_data.get("breakeven_activated", False),
                trailing_activated=plan_data.get("trailing_activated", False)
            )

            self.positions[symbol] = plan
            logger.info(f"Restored scale-out plan for {symbol}: remaining={remaining}, breakeven={plan.breakeven_activated}")

        except Exception as e:
            logger.error(f"Failed to restore scale plan for {symbol}: {e}")


class TradingDisciplineEnforcer:
    """
    Enforces trading discipline rules.

    RULES:
    1. Max 3 consecutive losses = cooldown
    2. After any loss = 5 minute cooldown
    3. Max 5 winners = quit while ahead
    4. Daily loss limit = halt trading
    5. Profit protection = halt if give back 30%
    """

    def __init__(
        self,
        max_consecutive_losses: int = 3,
        loss_cooldown_minutes: int = 5,
        max_daily_winners: int = 5,
        daily_loss_limit: float = 500.0,
        profit_protection_threshold: float = 300.0,
        max_drawdown_pct: float = 30.0
    ):
        self.max_consecutive_losses = max_consecutive_losses
        self.loss_cooldown_minutes = loss_cooldown_minutes
        self.max_daily_winners = max_daily_winners
        self.daily_loss_limit = daily_loss_limit
        self.profit_protection_threshold = profit_protection_threshold
        self.max_drawdown_pct = max_drawdown_pct

        self.state = TradingState(date=datetime.now().strftime("%Y-%m-%d"))

    def new_day(self):
        """Reset state for new trading day."""
        today = datetime.now().strftime("%Y-%m-%d")
        if self.state.date != today:
            self.state = TradingState(date=today)
            logger.info("🌅 New trading day - discipline counters reset")

    def record_trade(self, pnl: float) -> Dict[str, Any]:
        """Record a completed trade and check discipline rules."""
        self.new_day()

        result = {
            "trade_allowed": True,
            "actions": [],
            "warnings": []
        }

        self.state.trades_today += 1
        self.state.daily_pnl += pnl

        if pnl > self.state.daily_high_pnl:
            self.state.daily_high_pnl = pnl

        if pnl > 0:
            self.state.winners_today += 1
            self.state.consecutive_losses = 0

            # Check max winners
            if self.state.winners_today >= self.max_daily_winners:
                self.state.halted = True
                self.state.halt_reason = f"Max daily winners ({self.max_daily_winners}) reached - quit while ahead!"
                result["actions"].append({
                    "action": "HALT_TRADING",
                    "reason": self.state.halt_reason
                })
                logger.info(f"🏆 {self.state.halt_reason}")
        else:
            self.state.losers_today += 1
            self.state.consecutive_losses += 1
            self.state.last_loss_time = datetime.now()

            # Set cooldown after loss
            self.state.cooldown_until = datetime.now() + timedelta(minutes=self.loss_cooldown_minutes)
            result["warnings"].append(f"Loss recorded - {self.loss_cooldown_minutes}min cooldown")

            # Check consecutive losses
            if self.state.consecutive_losses >= self.max_consecutive_losses:
                extended_cooldown = self.loss_cooldown_minutes * 3
                self.state.cooldown_until = datetime.now() + timedelta(minutes=extended_cooldown)
                result["actions"].append({
                    "action": "EXTENDED_COOLDOWN",
                    "minutes": extended_cooldown,
                    "reason": f"{self.state.consecutive_losses} consecutive losses"
                })
                logger.warning(f"😤 {self.state.consecutive_losses} consecutive losses - {extended_cooldown}min cooldown")

        # Check daily loss limit
        if self.state.daily_pnl <= -self.daily_loss_limit:
            self.state.halted = True
            self.state.halt_reason = f"Daily loss limit (${self.daily_loss_limit}) hit"
            result["actions"].append({
                "action": "HALT_TRADING",
                "reason": self.state.halt_reason
            })
            logger.warning(f"🛑 {self.state.halt_reason}")

        # Check profit protection
        if self.state.daily_high_pnl >= self.profit_protection_threshold:
            drawdown = self.state.daily_high_pnl - self.state.daily_pnl
            drawdown_pct = (drawdown / self.state.daily_high_pnl) * 100

            if drawdown_pct >= self.max_drawdown_pct:
                self.state.halted = True
                self.state.halt_reason = f"Profit protection: gave back {drawdown_pct:.1f}% from peak"
                result["actions"].append({
                    "action": "HALT_TRADING",
                    "reason": self.state.halt_reason
                })
                logger.warning(f"🛡️ {self.state.halt_reason}")

        return result

    def can_trade(self) -> Tuple[bool, Optional[str]]:
        """Check if trading is currently allowed."""
        self.new_day()

        if self.state.halted:
            return False, self.state.halt_reason

        if self.state.cooldown_until and datetime.now() < self.state.cooldown_until:
            remaining = (self.state.cooldown_until - datetime.now()).seconds // 60
            return False, f"Cooldown active - {remaining} minutes remaining"

        return True, None


class SetupGrader:
    """
    Grade trade setups from A+ to F.

    GRADING CRITERIA:
    - Multi-timeframe alignment
    - Relative strength
    - Position relative to S/R
    - Volume confirmation
    - Risk/reward ratio

    RULE: Only trade A and A+ setups for full size.
          B setups get 75% size. C and below = skip.
    """

    def grade_setup(
        self,
        mtf_analysis: MultiTimeframeAnalysis,
        rs: RelativeStrength,
        sr: SupportResistance,
        gap: GapAnalysis,
        confidence: float,
        risk_reward_ratio: float
    ) -> Tuple[SetupGrade, Dict[str, Any]]:
        """Grade a trade setup."""
        score = 0
        factors = []

        # Multi-timeframe alignment (0-25 points)
        if mtf_analysis.alignment_score > 0.5:
            score += 25
            factors.append("Strong MTF alignment (+25)")
        elif mtf_analysis.alignment_score > 0.2:
            score += 15
            factors.append("Moderate MTF alignment (+15)")
        elif len(mtf_analysis.conflicts) > 0:
            score -= 15
            factors.append(f"MTF conflict: {mtf_analysis.conflicts[0]} (-15)")

        # Relative strength (0-20 points)
        if rs.is_leader:
            score += 20
            factors.append("RS Leader (+20)")
        elif rs.is_laggard:
            score -= 10
            factors.append("RS Laggard (-10)")
        elif rs.rs_ratio > 1:
            score += 10
            factors.append("Outperforming SPY (+10)")

        # Support/Resistance positioning (0-20 points)
        if sr.at_support:
            score += 15
            factors.append("At support level (+15)")
        elif sr.at_resistance:
            score -= 20
            factors.append("At resistance - DANGER (-20)")
        elif sr.distance_to_resistance_pct > 3:
            score += 10
            factors.append("Room to resistance (+10)")

        # Gap analysis (0-15 points)
        if gap.is_gap_and_go:
            score += 15
            factors.append("Gap-and-go pattern (+15)")
        elif gap.is_gap_and_fade:
            score -= 10
            factors.append("Gap-and-fade risk (-10)")

        # Confidence (0-10 points)
        if confidence >= 0.85:
            score += 10
            factors.append("High confidence (+10)")
        elif confidence >= 0.75:
            score += 5
            factors.append("Good confidence (+5)")
        elif confidence < 0.65:
            score -= 10
            factors.append("Low confidence (-10)")

        # Risk/Reward (0-10 points)
        if risk_reward_ratio >= 3:
            score += 10
            factors.append("Excellent R:R 3:1+ (+10)")
        elif risk_reward_ratio >= 2:
            score += 5
            factors.append("Good R:R 2:1+ (+5)")
        elif risk_reward_ratio < 1.5:
            score -= 15
            factors.append("Poor R:R < 1.5:1 (-15)")

        # Determine grade
        if score >= 70:
            grade = SetupGrade.A_PLUS
        elif score >= 55:
            grade = SetupGrade.A
        elif score >= 40:
            grade = SetupGrade.B
        elif score >= 20:
            grade = SetupGrade.C
        else:
            grade = SetupGrade.F

        return grade, {
            "score": score,
            "grade": grade.value,
            "factors": factors,
            "position_size_multiplier": {
                SetupGrade.A_PLUS: 1.0,
                SetupGrade.A: 1.0,
                SetupGrade.B: 0.75,
                SetupGrade.C: 0.5,
                SetupGrade.F: 0
            }[grade]
        }


class EliteTradingSystem:
    """
    Complete elite trading system combining all components.

    This is what separates professional traders from amateurs.
    """

    def __init__(self):
        self.mtf_analyzer = MultiTimeframeAnalyzer()
        self.rs_analyzer = RelativeStrengthAnalyzer()
        self.sr_detector = SupportResistanceDetector()
        self.gap_analyzer = GapAnalyzer()
        self.position_manager = PositionManager()
        self.discipline = TradingDisciplineEnforcer()
        self.grader = SetupGrader()

        logger.info("🏆 Elite Trading System initialized")

    def full_analysis(
        self,
        symbol: str,
        data_5m: pd.DataFrame,
        data_15m: pd.DataFrame,
        data_1h: pd.DataFrame,
        spy_data: pd.DataFrame,
        current_price: float,
        open_price: float,
        volume: int,
        avg_volume: int,
        confidence: float,
        risk_reward_ratio: float
    ) -> Dict[str, Any]:
        """
        Run complete elite analysis on a potential trade.

        Returns comprehensive analysis with setup grade.
        """
        # Multi-timeframe analysis
        mtf = self.mtf_analyzer.analyze_multiple(symbol, data_5m, data_15m, data_1h)

        # Relative strength
        rs = self.rs_analyzer.calculate_rs(symbol, data_5m, spy_data)

        # Support/Resistance
        sr = self.sr_detector.find_levels(data_5m, symbol)

        # Gap analysis
        gap = self.gap_analyzer.analyze(
            symbol=symbol,
            current_price=current_price,
            open_price=open_price,
            previous_close=sr.previous_close,
            volume=volume,
            avg_volume=avg_volume,
            premarket_high=sr.premarket_high,
            current_high=sr.hod
        )

        # Grade the setup
        grade, grade_details = self.grader.grade_setup(
            mtf_analysis=mtf,
            rs=rs,
            sr=sr,
            gap=gap,
            confidence=confidence,
            risk_reward_ratio=risk_reward_ratio
        )

        # Check if trading allowed
        can_trade, halt_reason = self.discipline.can_trade()

        return {
            "symbol": symbol,
            "approved": can_trade and grade in [SetupGrade.A_PLUS, SetupGrade.A, SetupGrade.B],
            "grade": grade.value,
            "grade_details": grade_details,
            "position_size_multiplier": grade_details["position_size_multiplier"],
            "halt_reason": halt_reason,
            "analysis": {
                "multi_timeframe": {
                    "alignment_score": mtf.alignment_score,
                    "primary_trend": mtf.primary_trend.value,
                    "trade_direction": mtf.trade_with_trend,
                    "conflicts": mtf.conflicts,
                    "trends": {tf: t.direction.value for tf, t in mtf.trends.items()}
                },
                "relative_strength": {
                    "rs_ratio": rs.rs_ratio,
                    "is_leader": rs.is_leader,
                    "is_laggard": rs.is_laggard,
                    "rank_percentile": rs.rank_percentile
                },
                "support_resistance": {
                    "nearest_support": sr.nearest_support,
                    "nearest_resistance": sr.nearest_resistance,
                    "at_support": sr.at_support,
                    "at_resistance": sr.at_resistance,
                    "hod": sr.hod,
                    "lod": sr.lod
                },
                "gap": {
                    "gap_percent": gap.gap_percent,
                    "gap_type": gap.gap_type,
                    "is_gap_and_go": gap.is_gap_and_go,
                    "is_gap_and_fade": gap.is_gap_and_fade
                }
            }
        }
