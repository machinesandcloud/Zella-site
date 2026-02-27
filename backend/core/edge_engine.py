"""
EDGE ENGINE - The Competitive Advantage Layer

This is what separates #1 from #5.

The #1 trader's edge:
- Knows how BOTS trade (and exploits their patterns)
- Knows how HUMANS trade (and exploits their emotions)
- Hides his own patterns (so nobody can counter him)
- Positions BEFORE signals (not after)

This engine provides:
1. ALGO DETECTION - Identify competing bots and their patterns
2. FLOW PREDICTION - Predict order flow before it happens
3. SENTIMENT PULSE - Real-time human psychology exploitation
4. STEALTH EXECUTION - Hide our patterns from detection
5. ADAPTIVE EDGE - Learn what's working NOW, not yesterday
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from threading import Lock
import hashlib

logger = logging.getLogger("edge_engine")


# ==================== DATA STRUCTURES ====================

@dataclass
class AlgoFingerprint:
    """Detected pattern of a competing algorithm"""
    fingerprint_id: str
    first_seen: datetime
    last_seen: datetime

    # Timing patterns
    typical_entry_times: List[int] = field(default_factory=list)  # Minutes from market open
    typical_exit_times: List[int] = field(default_factory=list)
    avg_hold_duration_minutes: float = 0.0

    # Size patterns
    typical_position_sizes: List[int] = field(default_factory=list)
    size_clustering: float = 0.0  # How consistent are sizes (0-1)

    # Behavior patterns
    stops_at_round_numbers: bool = False
    entries_at_vwap: bool = False
    entries_at_ema: bool = False
    uses_market_orders: bool = False

    # Predictability
    predictability_score: float = 0.0  # 0-1, how easy to predict

    # Counter-strategy
    counter_action: str = ""  # "FADE", "FOLLOW", "AVOID"


@dataclass
class FlowPrediction:
    """Predicted order flow for the next N minutes"""
    symbol: str
    timestamp: datetime

    # Directional prediction
    predicted_direction: str  # "UP", "DOWN", "NEUTRAL"
    confidence: float  # 0-1

    # Magnitude prediction
    predicted_move_percent: float
    predicted_volume: int

    # Timing
    expected_trigger_minutes: int  # When the move should start

    # Basis
    signals_used: List[str] = field(default_factory=list)


@dataclass
class SentimentPulse:
    """Real-time human psychology state"""
    symbol: str
    timestamp: datetime

    # Fear/Greed
    fear_level: float  # 0-1
    greed_level: float  # 0-1

    # Retail behavior
    retail_fomo_active: bool = False
    retail_panic_active: bool = False
    retail_trapped_long: bool = False
    retail_trapped_short: bool = False

    # Volume characteristics
    capitulation_volume: bool = False  # Unusually high with price drop
    euphoria_volume: bool = False  # Unusually high with price spike

    # Actionable signal
    exploit_signal: str = ""  # "BUY_PANIC", "SELL_EUPHORIA", "FADE_FOMO", ""


@dataclass
class StealthOrder:
    """Order designed to hide our patterns"""
    original_quantity: int
    slices: List[int]  # Split into multiple orders
    timing_delays_ms: List[int]  # Random delays between slices
    price_offsets: List[float]  # Slight price variations
    order_types: List[str]  # Mix of MARKET/LIMIT

    # Anti-detection
    randomization_seed: int = 0
    looks_like: str = "RETAIL"  # "RETAIL", "INSTITUTIONAL", "NOISE"


# ==================== ALGO DETECTION ENGINE ====================

class AlgoDetector:
    """
    Detects competing algorithms by analyzing trade patterns.

    Key insight: Bots are PREDICTABLE. They:
    - Enter at the same times
    - Use the same position sizes
    - Place stops at the same levels
    - React to the same signals

    If we can detect them, we can EXPLOIT them.
    """

    def __init__(self):
        self._fingerprints: Dict[str, AlgoFingerprint] = {}
        self._trade_history: deque = deque(maxlen=10000)
        self._lock = Lock()

        # Detection thresholds
        self.size_cluster_threshold = 0.8  # Same size 80%+ = algo
        self.time_cluster_threshold = 0.7  # Same time 70%+ = algo
        self.round_number_threshold = 0.6  # Stops at round numbers 60%+ = algo

        logger.info("Algo Detector initialized - hunting for patterns")

    def ingest_trade(self, trade: Dict[str, Any]) -> Optional[str]:
        """
        Analyze a trade for algo fingerprints.
        Returns fingerprint_id if this looks like an algo.
        """
        with self._lock:
            self._trade_history.append({
                **trade,
                "ingested_at": datetime.now()
            })

            # Need enough history
            if len(self._trade_history) < 100:
                return None

            return self._detect_patterns(trade)

    def _detect_patterns(self, trade: Dict[str, Any]) -> Optional[str]:
        """Analyze trade patterns to detect algos"""
        symbol = trade.get("symbol", "")
        quantity = trade.get("quantity", 0)
        price = trade.get("price", 0)
        timestamp = trade.get("timestamp", datetime.now())

        # Get recent trades for this symbol
        symbol_trades = [
            t for t in self._trade_history
            if t.get("symbol") == symbol
        ]

        if len(symbol_trades) < 20:
            return None

        # DETECTION 1: Size clustering (algos use consistent sizes)
        sizes = [t.get("quantity", 0) for t in symbol_trades[-50:]]
        size_mode = max(set(sizes), key=sizes.count)
        size_cluster_ratio = sizes.count(size_mode) / len(sizes)

        # DETECTION 2: Time clustering (algos trade at same times)
        times = [t.get("timestamp", datetime.now()).minute for t in symbol_trades[-50:]]
        time_mode = max(set(times), key=times.count)
        time_cluster_ratio = times.count(time_mode) / len(times)

        # DETECTION 3: Round number stops (retail algos love round numbers)
        prices = [t.get("price", 0) for t in symbol_trades[-50:]]
        round_count = sum(1 for p in prices if p % 1 == 0 or p % 0.5 == 0)
        round_ratio = round_count / len(prices)

        # Calculate fingerprint
        is_algo = (
            size_cluster_ratio > self.size_cluster_threshold or
            time_cluster_ratio > self.time_cluster_threshold or
            round_ratio > self.round_number_threshold
        )

        if is_algo:
            # Generate fingerprint ID
            fp_data = f"{symbol}:{size_mode}:{time_mode}"
            fp_id = hashlib.md5(fp_data.encode()).hexdigest()[:8]

            # Create or update fingerprint
            if fp_id not in self._fingerprints:
                self._fingerprints[fp_id] = AlgoFingerprint(
                    fingerprint_id=fp_id,
                    first_seen=timestamp,
                    last_seen=timestamp,
                    typical_position_sizes=[size_mode],
                    size_clustering=size_cluster_ratio,
                    stops_at_round_numbers=round_ratio > 0.5,
                    predictability_score=max(size_cluster_ratio, time_cluster_ratio, round_ratio)
                )

                # Determine counter-strategy
                if size_cluster_ratio > 0.9:
                    # Highly predictable size = FADE their entries
                    self._fingerprints[fp_id].counter_action = "FADE"
                elif round_ratio > 0.7:
                    # Round number stops = HUNT their stops
                    self._fingerprints[fp_id].counter_action = "HUNT_STOPS"
                else:
                    # Less predictable = AVOID
                    self._fingerprints[fp_id].counter_action = "AVOID"

                logger.info(f"NEW ALGO DETECTED: {fp_id} - Counter: {self._fingerprints[fp_id].counter_action}")
            else:
                self._fingerprints[fp_id].last_seen = timestamp

            return fp_id

        return None

    def get_counter_strategy(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get counter-strategy for detected algos on this symbol"""
        with self._lock:
            relevant = [
                fp for fp in self._fingerprints.values()
                if (datetime.now() - fp.last_seen).seconds < 3600  # Active in last hour
            ]

            if not relevant:
                return None

            # Most predictable algo
            most_predictable = max(relevant, key=lambda x: x.predictability_score)

            return {
                "fingerprint_id": most_predictable.fingerprint_id,
                "counter_action": most_predictable.counter_action,
                "predictability": most_predictable.predictability_score,
                "typical_sizes": most_predictable.typical_position_sizes,
                "stops_at_round": most_predictable.stops_at_round_numbers
            }


# ==================== FLOW PREDICTION ENGINE ====================

class FlowPredictor:
    """
    Predicts order flow BEFORE it happens.

    Key insight: Order flow is NOT random. It follows patterns:
    - Institutional rebalancing at specific times
    - Retail piles in AFTER moves, not before
    - Market makers hedge option gamma
    - News flow triggers predictable responses

    If we can predict flow, we can position BEFORE everyone else.
    """

    def __init__(self):
        self._predictions: Dict[str, FlowPrediction] = {}
        self._historical_flows: deque = deque(maxlen=5000)
        self._lock = Lock()

        # Time-based patterns (minutes from market open)
        self.institutional_times = [30, 60, 180, 330]  # 10:00, 10:30, 12:30, 3:30
        self.retail_times = [5, 15, 375]  # 9:35, 9:45, 3:55 (open and close rush)

        logger.info("Flow Predictor initialized - anticipating the market")

    def predict_next_flow(self, symbol: str, current_data: pd.DataFrame) -> Optional[FlowPrediction]:
        """
        Predict order flow for the next 5-15 minutes.
        """
        if current_data is None or len(current_data) < 50:
            return None

        now = datetime.now()
        minutes_from_open = (now.hour - 9) * 60 + now.minute - 30

        signals = []
        direction_score = 0  # Positive = UP, Negative = DOWN
        confidence = 0.0

        # SIGNAL 1: Volume precursor (volume spikes before price moves)
        recent_vol = current_data["volume"].iloc[-5:].mean()
        avg_vol = current_data["volume"].iloc[-50:].mean()
        vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1

        if vol_ratio > 2.0:
            # High volume = something's coming
            signals.append("VOLUME_SPIKE")
            # Direction from price action
            price_change = (current_data["close"].iloc[-1] - current_data["close"].iloc[-5]) / current_data["close"].iloc[-5]
            direction_score += 1 if price_change > 0 else -1
            confidence += 0.2

        # SIGNAL 2: Bid-ask imbalance (if available)
        if "bid_size" in current_data.columns and "ask_size" in current_data.columns:
            bid_total = current_data["bid_size"].iloc[-10:].sum()
            ask_total = current_data["ask_size"].iloc[-10:].sum()
            imbalance = (bid_total - ask_total) / (bid_total + ask_total) if (bid_total + ask_total) > 0 else 0

            if abs(imbalance) > 0.3:
                signals.append("ORDER_IMBALANCE")
                direction_score += 1 if imbalance > 0 else -1
                confidence += 0.25

        # SIGNAL 3: Institutional time (rebalancing periods)
        for inst_time in self.institutional_times:
            if abs(minutes_from_open - inst_time) < 5:
                signals.append("INSTITUTIONAL_TIME")
                confidence += 0.15
                break

        # SIGNAL 4: Momentum continuation (strong trends continue)
        sma_20 = current_data["close"].rolling(20).mean().iloc[-1]
        sma_50 = current_data["close"].rolling(50).mean().iloc[-1]
        price = current_data["close"].iloc[-1]

        if price > sma_20 > sma_50:
            signals.append("UPTREND_MOMENTUM")
            direction_score += 0.5
            confidence += 0.15
        elif price < sma_20 < sma_50:
            signals.append("DOWNTREND_MOMENTUM")
            direction_score -= 0.5
            confidence += 0.15

        # SIGNAL 5: Gap fill tendency
        if "open" in current_data.columns:
            day_open = current_data["open"].iloc[0]
            prev_close = current_data["close"].iloc[0]  # Approximation
            gap_pct = (day_open - prev_close) / prev_close if prev_close > 0 else 0

            if abs(gap_pct) > 0.02 and minutes_from_open < 120:
                # Gaps tend to fill in first 2 hours
                signals.append("GAP_FILL_TENDENCY")
                direction_score += -1 if gap_pct > 0 else 1  # Counter-gap direction
                confidence += 0.2

        # Calculate final prediction
        if not signals or confidence < 0.3:
            return None

        direction = "UP" if direction_score > 0 else "DOWN" if direction_score < 0 else "NEUTRAL"

        # Estimate move magnitude
        atr = self._calculate_atr(current_data)
        predicted_move = atr * abs(direction_score) * 0.5 / price * 100  # As percentage

        prediction = FlowPrediction(
            symbol=symbol,
            timestamp=now,
            predicted_direction=direction,
            confidence=min(confidence, 0.85),  # Cap at 85%
            predicted_move_percent=predicted_move,
            predicted_volume=int(avg_vol * vol_ratio),
            expected_trigger_minutes=5 if vol_ratio > 2 else 15,
            signals_used=signals
        )

        with self._lock:
            self._predictions[symbol] = prediction

        logger.debug(f"Flow prediction for {symbol}: {direction} ({confidence:.0%}) - Signals: {signals}")
        return prediction

    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        if len(data) < period:
            return 0.0

        high = data["high"]
        low = data["low"]
        close = data["close"]

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean().iloc[-1]


# ==================== SENTIMENT PULSE ENGINE ====================

class SentimentAnalyzer:
    """
    Real-time human psychology exploitation.

    Key insight: Humans are PREDICTABLE emotionally:
    - They FOMO at tops
    - They PANIC at bottoms
    - They revenge trade after losses
    - They get trapped and capitulate

    If we can detect these states, we can trade AGAINST the crowd.
    """

    def __init__(self):
        self._pulses: Dict[str, SentimentPulse] = {}
        self._lock = Lock()

        # Thresholds
        self.fomo_vol_threshold = 3.0  # 3x avg volume with price up
        self.panic_vol_threshold = 3.0  # 3x avg volume with price down
        self.capitulation_threshold = 5.0  # 5x volume = capitulation

        logger.info("Sentiment Analyzer initialized - reading the crowd")

    def analyze_sentiment(self, symbol: str, data: pd.DataFrame) -> Optional[SentimentPulse]:
        """
        Analyze current sentiment state for a symbol.
        """
        if data is None or len(data) < 50:
            return None

        now = datetime.now()

        # Recent vs average
        recent_vol = data["volume"].iloc[-5:].mean()
        avg_vol = data["volume"].iloc[-50:].mean()
        vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1

        # Price movement
        price_change_5 = (data["close"].iloc[-1] - data["close"].iloc[-5]) / data["close"].iloc[-5]
        price_change_20 = (data["close"].iloc[-1] - data["close"].iloc[-20]) / data["close"].iloc[-20]

        # RSI for oversold/overbought
        rsi = self._calculate_rsi(data)

        # Initialize sentiment
        pulse = SentimentPulse(
            symbol=symbol,
            timestamp=now,
            fear_level=0.5,
            greed_level=0.5
        )

        # DETECT: Retail FOMO (high volume + price up + RSI high)
        if vol_ratio > self.fomo_vol_threshold and price_change_5 > 0.02 and rsi > 70:
            pulse.greed_level = min(0.9, 0.5 + vol_ratio * 0.1)
            pulse.retail_fomo_active = True
            pulse.euphoria_volume = True
            pulse.exploit_signal = "FADE_FOMO"  # Sell into FOMO
            logger.info(f"{symbol}: FOMO DETECTED - Retail piling in. FADE signal.")

        # DETECT: Retail PANIC (high volume + price down + RSI low)
        elif vol_ratio > self.panic_vol_threshold and price_change_5 < -0.02 and rsi < 30:
            pulse.fear_level = min(0.9, 0.5 + vol_ratio * 0.1)
            pulse.retail_panic_active = True
            pulse.exploit_signal = "BUY_PANIC"  # Buy the panic
            logger.info(f"{symbol}: PANIC DETECTED - Retail dumping. BUY signal.")

        # DETECT: Capitulation (extreme volume + big drop)
        if vol_ratio > self.capitulation_threshold and price_change_20 < -0.05:
            pulse.fear_level = 0.95
            pulse.capitulation_volume = True
            pulse.exploit_signal = "BUY_CAPITULATION"  # Strong buy
            logger.info(f"{symbol}: CAPITULATION DETECTED - Maximum fear. STRONG BUY.")

        # DETECT: Trapped longs (rallied then dropped, holding bag)
        if price_change_20 > 0.05 and price_change_5 < -0.03:
            pulse.retail_trapped_long = True
            # They'll panic sell on next drop
            pulse.exploit_signal = "WAIT_FOR_CAPITULATION"
            logger.debug(f"{symbol}: Trapped longs detected - waiting for capitulation")

        # DETECT: Trapped shorts (dropped then rallied, shorts covering)
        if price_change_20 < -0.05 and price_change_5 > 0.03:
            pulse.retail_trapped_short = True
            # Short squeeze potential
            pulse.exploit_signal = "FOLLOW_SQUEEZE"
            logger.debug(f"{symbol}: Trapped shorts detected - potential squeeze")

        with self._lock:
            self._pulses[symbol] = pulse

        return pulse

    def _calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate RSI"""
        if len(data) < period + 1:
            return 50.0

        delta = data["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi.iloc[-1] if not np.isnan(rsi.iloc[-1]) else 50.0


# ==================== STEALTH EXECUTION ENGINE ====================

class StealthExecutor:
    """
    Hide our trading patterns from detection.

    Key insight: If other algos can detect us, they can COUNTER us.

    We hide by:
    - Splitting orders into variable sizes
    - Adding random timing delays
    - Using mixed order types
    - Making orders look like retail noise
    """

    def __init__(self):
        self._lock = Lock()
        self._last_orders: deque = deque(maxlen=100)

        # Randomization parameters
        self.min_slices = 2
        self.max_slices = 5
        self.min_delay_ms = 100
        self.max_delay_ms = 2000
        self.price_jitter_pct = 0.0002  # 0.02% price variation

        logger.info("Stealth Executor initialized - hiding in plain sight")

    def create_stealth_order(
        self,
        symbol: str,
        quantity: int,
        side: str,
        urgency: str = "NORMAL"
    ) -> StealthOrder:
        """
        Create a stealth order that's hard to detect as algorithmic.

        Args:
            symbol: Stock symbol
            quantity: Total shares to trade
            side: "BUY" or "SELL"
            urgency: "LOW", "NORMAL", "HIGH"
        """
        # Determine slice count based on quantity
        if quantity < 100:
            num_slices = 1  # Small orders don't need splitting
        elif quantity < 500:
            num_slices = np.random.randint(2, 4)
        else:
            num_slices = np.random.randint(self.min_slices, self.max_slices + 1)

        # Split quantity into variable slices (NOT equal!)
        slices = self._variable_split(quantity, num_slices)

        # Generate timing delays (faster for HIGH urgency)
        if urgency == "HIGH":
            delays = [np.random.randint(50, 200) for _ in range(num_slices)]
        elif urgency == "LOW":
            delays = [np.random.randint(500, 3000) for _ in range(num_slices)]
        else:
            delays = [np.random.randint(self.min_delay_ms, self.max_delay_ms) for _ in range(num_slices)]

        # Add price jitter (slight variations to look natural)
        offsets = [np.random.uniform(-self.price_jitter_pct, self.price_jitter_pct) for _ in range(num_slices)]

        # Mix order types (algos usually use only one type)
        order_types = self._randomize_order_types(num_slices, urgency)

        # Make it look retail (odd lots, round-ish numbers)
        slices = self._retailify_sizes(slices)

        order = StealthOrder(
            original_quantity=quantity,
            slices=slices,
            timing_delays_ms=delays,
            price_offsets=offsets,
            order_types=order_types,
            randomization_seed=np.random.randint(0, 1000000),
            looks_like="RETAIL"
        )

        with self._lock:
            self._last_orders.append({
                "symbol": symbol,
                "side": side,
                "order": order,
                "created_at": datetime.now()
            })

        logger.debug(f"Stealth order created: {quantity} {symbol} -> {num_slices} slices, looks like {order.looks_like}")
        return order

    def _variable_split(self, total: int, num_slices: int) -> List[int]:
        """Split quantity into variable (not equal) slices"""
        if num_slices == 1:
            return [total]

        # Generate random proportions
        proportions = np.random.dirichlet(np.ones(num_slices))
        slices = [int(total * p) for p in proportions]

        # Adjust for rounding errors
        diff = total - sum(slices)
        slices[0] += diff

        # Ensure no slice is 0
        slices = [max(1, s) for s in slices]

        return slices

    def _randomize_order_types(self, num_slices: int, urgency: str) -> List[str]:
        """Mix order types to look less algorithmic"""
        if urgency == "HIGH":
            # High urgency = mostly market orders
            return ["MARKET"] * num_slices

        types = []
        for _ in range(num_slices):
            if np.random.random() < 0.3:  # 30% limit orders
                types.append("LIMIT")
            else:
                types.append("MARKET")

        return types

    def _retailify_sizes(self, slices: List[int]) -> List[int]:
        """Make sizes look like retail orders (odd lots, round-ish)"""
        retailified = []
        for s in slices:
            if s >= 100:
                # Sometimes round to 10s or 25s (retail loves round numbers)
                if np.random.random() < 0.3:
                    s = round(s / 10) * 10
                elif np.random.random() < 0.2:
                    s = round(s / 25) * 25
            retailified.append(max(1, s))

        return retailified


# ==================== UNIFIED EDGE ENGINE ====================

class EdgeEngine:
    """
    The unified competitive advantage layer.

    Combines all edge systems to give Zella:
    1. SIGHT - See what competitors are doing
    2. FORESIGHT - Predict what's coming next
    3. INSIGHT - Understand human psychology
    4. INVISIBILITY - Hide our own patterns
    """

    def __init__(self):
        self.algo_detector = AlgoDetector()
        self.flow_predictor = FlowPredictor()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.stealth_executor = StealthExecutor()

        self._lock = Lock()

        logger.info("=== EDGE ENGINE INITIALIZED ===")
        logger.info("Now operating on a different level.")

    def get_edge(self, symbol: str, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Get complete edge analysis for a symbol.
        Returns actionable intelligence.
        """
        edge = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "algo_counter": None,
            "flow_prediction": None,
            "sentiment": None,
            "recommended_execution": None,
            "edge_score": 0.0,
            "action": "HOLD"
        }

        # 1. Check for competing algos
        algo_counter = self.algo_detector.get_counter_strategy(symbol)
        if algo_counter:
            edge["algo_counter"] = algo_counter
            edge["edge_score"] += algo_counter["predictability"] * 0.3

        # 2. Predict flow
        flow = self.flow_predictor.predict_next_flow(symbol, data)
        if flow:
            edge["flow_prediction"] = {
                "direction": flow.predicted_direction,
                "confidence": flow.confidence,
                "move_percent": flow.predicted_move_percent,
                "trigger_minutes": flow.expected_trigger_minutes,
                "signals": flow.signals_used
            }
            edge["edge_score"] += flow.confidence * 0.4

        # 3. Analyze sentiment
        sentiment = self.sentiment_analyzer.analyze_sentiment(symbol, data)
        if sentiment:
            edge["sentiment"] = {
                "fear": sentiment.fear_level,
                "greed": sentiment.greed_level,
                "fomo_active": sentiment.retail_fomo_active,
                "panic_active": sentiment.retail_panic_active,
                "exploit_signal": sentiment.exploit_signal
            }
            if sentiment.exploit_signal:
                edge["edge_score"] += 0.3

        # 4. Determine action
        edge["action"] = self._determine_action(edge)

        # 5. Prepare stealth execution
        if edge["action"] in ["BUY", "SELL"]:
            edge["recommended_execution"] = "STEALTH"

        return edge

    def _determine_action(self, edge: Dict[str, Any]) -> str:
        """Determine the recommended action based on all edge signals"""
        # Strong sentiment signals override
        sentiment = edge.get("sentiment", {})
        exploit = sentiment.get("exploit_signal", "")

        if exploit == "BUY_CAPITULATION":
            return "STRONG_BUY"
        elif exploit == "BUY_PANIC":
            return "BUY"
        elif exploit == "FADE_FOMO":
            return "SELL"
        elif exploit == "FOLLOW_SQUEEZE":
            return "BUY"

        # Flow prediction
        flow = edge.get("flow_prediction", {})
        if flow and flow.get("confidence", 0) > 0.6:
            direction = flow.get("direction", "")
            if direction == "UP":
                return "BUY"
            elif direction == "DOWN":
                return "SELL"

        # Algo counter-strategy
        algo = edge.get("algo_counter", {})
        if algo and algo.get("counter_action") == "FADE":
            # Fade detected algo entries
            return "FADE"

        return "HOLD"

    def prepare_stealth_order(
        self,
        symbol: str,
        quantity: int,
        side: str,
        edge: Dict[str, Any]
    ) -> StealthOrder:
        """
        Prepare a stealth order based on edge analysis.
        """
        # Determine urgency from edge signals
        urgency = "NORMAL"

        if edge.get("action") == "STRONG_BUY":
            urgency = "HIGH"
        elif edge.get("sentiment", {}).get("capitulation_volume"):
            urgency = "HIGH"  # Capitulation = get in fast
        elif edge.get("algo_counter", {}).get("counter_action") == "FADE":
            urgency = "LOW"  # Fading = don't rush

        return self.stealth_executor.create_stealth_order(
            symbol=symbol,
            quantity=quantity,
            side=side,
            urgency=urgency
        )


# Singleton instance
_edge_engine: Optional[EdgeEngine] = None


def get_edge_engine() -> EdgeEngine:
    """Get or create the global edge engine instance"""
    global _edge_engine
    if _edge_engine is None:
        _edge_engine = EdgeEngine()
    return _edge_engine
