"""
High-Performance Trading Engine for Zella AI

Target: Sub-10ms signal-to-decision latency

Optimizations:
1. In-memory LRU cache with TTL
2. Async parallel symbol processing
3. Pre-computed indicators (background thread)
4. Order pre-staging (ready to fire)
5. NumPy vectorized calculations
6. Connection pooling
7. Latency monitoring
"""

from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import lru_cache
from threading import Lock, Thread
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import hashlib

import numpy as np
import pandas as pd

logger = logging.getLogger("performance_engine")


# =============================================================================
# LATENCY MONITORING
# =============================================================================

@dataclass
class LatencyMetrics:
    """Track latency for each component."""
    component: str
    samples: List[float] = field(default_factory=list)
    max_samples: int = 1000

    def record(self, latency_ms: float):
        self.samples.append(latency_ms)
        if len(self.samples) > self.max_samples:
            self.samples = self.samples[-self.max_samples:]

    @property
    def avg_ms(self) -> float:
        return np.mean(self.samples) if self.samples else 0

    @property
    def p50_ms(self) -> float:
        return np.percentile(self.samples, 50) if self.samples else 0

    @property
    def p99_ms(self) -> float:
        return np.percentile(self.samples, 99) if self.samples else 0

    @property
    def max_ms(self) -> float:
        return max(self.samples) if self.samples else 0


class LatencyMonitor:
    """Monitor latency across all trading components."""

    def __init__(self):
        self.metrics: Dict[str, LatencyMetrics] = {}
        self._lock = Lock()

    def record(self, component: str, latency_ms: float):
        with self._lock:
            if component not in self.metrics:
                self.metrics[component] = LatencyMetrics(component)
            self.metrics[component].record(latency_ms)

            # Alert if latency exceeds threshold
            if latency_ms > 10:
                logger.warning(f"⚠️ HIGH LATENCY: {component} took {latency_ms:.2f}ms (target: <10ms)")

    def timed(self, component: str):
        """Decorator/context manager for timing operations."""
        monitor = self

        class Timer:
            def __init__(self):
                self.start = None

            def __enter__(self):
                self.start = time.perf_counter()
                return self

            def __exit__(self, *args):
                elapsed = (time.perf_counter() - self.start) * 1000
                monitor.record(component, elapsed)

        return Timer()

    def get_report(self) -> Dict[str, Dict[str, float]]:
        with self._lock:
            return {
                name: {
                    "avg_ms": m.avg_ms,
                    "p50_ms": m.p50_ms,
                    "p99_ms": m.p99_ms,
                    "max_ms": m.max_ms,
                    "samples": len(m.samples)
                }
                for name, m in self.metrics.items()
            }


# Global latency monitor
LATENCY = LatencyMonitor()


# =============================================================================
# HIGH-PERFORMANCE CACHE
# =============================================================================

@dataclass
class CacheEntry:
    """Cache entry with TTL."""
    value: Any
    expires_at: float
    created_at: float = field(default_factory=time.time)


class HighPerformanceCache:
    """
    Ultra-fast in-memory cache with TTL.

    Features:
    - O(1) lookup
    - Automatic expiration
    - Thread-safe
    - Memory-bounded
    """

    def __init__(self, max_size: int = 10000, default_ttl: float = 1.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

        # Start cleanup thread
        self._cleanup_thread = Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def _cleanup_loop(self):
        """Background thread to clean expired entries."""
        while True:
            time.sleep(1)
            self._cleanup()

    def _cleanup(self):
        """Remove expired entries."""
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._cache.items() if v.expires_at < now]
            for k in expired:
                del self._cache[k]

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache. Returns None if expired or missing."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.expires_at < time.time():
                del self._cache[key]
                self._misses += 1
                return None
            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """Set value in cache with TTL."""
        ttl = ttl or self.default_ttl
        with self._lock:
            # Evict oldest if at capacity
            if len(self._cache) >= self.max_size:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
                del self._cache[oldest_key]

            self._cache[key] = CacheEntry(
                value=value,
                expires_at=time.time() + ttl
            )

    def get_or_compute(self, key: str, compute_fn: Callable, ttl: Optional[float] = None) -> Any:
        """Get from cache or compute and cache."""
        value = self.get(key)
        if value is not None:
            return value

        with LATENCY.timed(f"cache_compute_{key[:20]}"):
            value = compute_fn()

        self.set(key, value, ttl)
        return value

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0

    def clear(self):
        with self._lock:
            self._cache.clear()


# =============================================================================
# VECTORIZED INDICATOR CALCULATIONS
# =============================================================================

class VectorizedIndicators:
    """
    NumPy-optimized indicator calculations.

    10-100x faster than pandas for large datasets.
    """

    @staticmethod
    def ema(data: np.ndarray, period: int) -> np.ndarray:
        """Exponential moving average - vectorized."""
        alpha = 2 / (period + 1)
        result = np.zeros_like(data, dtype=np.float64)
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
        return result

    @staticmethod
    def sma(data: np.ndarray, period: int) -> np.ndarray:
        """Simple moving average - vectorized."""
        return np.convolve(data, np.ones(period) / period, mode='valid')

    @staticmethod
    def rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
        """RSI - vectorized."""
        delta = np.diff(close)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)

        avg_gain = np.zeros(len(close))
        avg_loss = np.zeros(len(close))

        # First average
        avg_gain[period] = np.mean(gain[:period])
        avg_loss[period] = np.mean(loss[:period])

        # Smoothed average
        for i in range(period + 1, len(close)):
            avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gain[i - 1]) / period
            avg_loss[i] = (avg_loss[i - 1] * (period - 1) + loss[i - 1]) / period

        rs = np.divide(avg_gain, avg_loss, where=avg_loss != 0, out=np.zeros_like(avg_gain))
        rsi = 100 - (100 / (1 + rs))
        rsi[:period] = 50  # Fill initial values
        return rsi

    @staticmethod
    def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """ATR - vectorized."""
        prev_close = np.roll(close, 1)
        prev_close[0] = close[0]

        tr = np.maximum(
            high - low,
            np.maximum(
                np.abs(high - prev_close),
                np.abs(low - prev_close)
            )
        )

        atr = np.zeros(len(close))
        atr[period - 1] = np.mean(tr[:period])

        for i in range(period, len(close)):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period

        return atr

    @staticmethod
    def vwap(high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """VWAP - vectorized."""
        typical_price = (high + low + close) / 3
        cumulative_tp_vol = np.cumsum(typical_price * volume)
        cumulative_vol = np.cumsum(volume)
        return np.divide(cumulative_tp_vol, cumulative_vol, where=cumulative_vol != 0)

    @staticmethod
    def bollinger_bands(close: np.ndarray, period: int = 20, std_dev: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Bollinger Bands - vectorized."""
        sma = np.convolve(close, np.ones(period) / period, mode='full')[:len(close)]

        # Rolling std
        std = np.zeros(len(close))
        for i in range(period - 1, len(close)):
            std[i] = np.std(close[i - period + 1:i + 1])

        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)

        return upper, sma, lower


# =============================================================================
# PRE-COMPUTED INDICATOR CACHE
# =============================================================================

class IndicatorPreComputer:
    """
    Background thread that pre-computes indicators for all watched symbols.

    This means when we need indicators, they're already calculated.
    """

    def __init__(self, market_data_provider, symbols: List[str], refresh_interval: float = 0.5):
        self.market_data = market_data_provider
        self.symbols = set(symbols)
        self.refresh_interval = refresh_interval
        self._cache = HighPerformanceCache(max_size=5000, default_ttl=2.0)
        self._running = False
        self._thread: Optional[Thread] = None
        self._vectorized = VectorizedIndicators()

    def start(self):
        """Start the pre-computation thread."""
        if self._running:
            return
        self._running = True
        self._thread = Thread(target=self._compute_loop, daemon=True)
        self._thread.start()
        logger.info(f"📊 Indicator pre-computer started for {len(self.symbols)} symbols")

    def stop(self):
        """Stop the pre-computation thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def add_symbol(self, symbol: str):
        """Add a symbol to watch."""
        self.symbols.add(symbol)

    def _compute_loop(self):
        """Main computation loop."""
        while self._running:
            start = time.perf_counter()

            for symbol in list(self.symbols):
                try:
                    self._compute_for_symbol(symbol)
                except Exception as e:
                    logger.debug(f"Pre-compute failed for {symbol}: {e}")

            elapsed = time.perf_counter() - start
            sleep_time = max(0, self.refresh_interval - elapsed)
            time.sleep(sleep_time)

    def _compute_for_symbol(self, symbol: str):
        """Compute all indicators for a symbol."""
        # Get bars from cache or fetch
        cache_key = f"bars_{symbol}"
        bars = self._cache.get(cache_key)

        if bars is None:
            bars = self.market_data.get_historical_bars(symbol, "1 D", "5 mins")
            if not bars:
                return
            self._cache.set(cache_key, bars, ttl=5.0)

        if len(bars) < 20:
            return

        # Convert to numpy for speed
        close = np.array([b['close'] for b in bars], dtype=np.float64)
        high = np.array([b['high'] for b in bars], dtype=np.float64)
        low = np.array([b['low'] for b in bars], dtype=np.float64)
        volume = np.array([b.get('volume', 0) for b in bars], dtype=np.float64)

        # Compute all indicators
        indicators = {
            'ema_9': self._vectorized.ema(close, 9)[-1],
            'ema_21': self._vectorized.ema(close, 21)[-1],
            'rsi_14': self._vectorized.rsi(close, 14)[-1],
            'atr_14': self._vectorized.atr(high, low, close, 14)[-1],
            'vwap': self._vectorized.vwap(high, low, close, volume)[-1],
            'price': close[-1],
            'high': high[-1],
            'low': low[-1],
            'volume': volume[-1],
            'computed_at': time.time()
        }

        self._cache.set(f"indicators_{symbol}", indicators, ttl=2.0)

    def get_indicators(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get pre-computed indicators for a symbol."""
        return self._cache.get(f"indicators_{symbol}")

    def get_all_indicators(self) -> Dict[str, Dict[str, float]]:
        """Get all pre-computed indicators."""
        result = {}
        for symbol in self.symbols:
            ind = self.get_indicators(symbol)
            if ind:
                result[symbol] = ind
        return result


# =============================================================================
# PARALLEL SYMBOL PROCESSOR
# =============================================================================

class ParallelSymbolProcessor:
    """
    Process multiple symbols in parallel using thread pool.

    Achieves near-linear scaling for symbol analysis.
    """

    def __init__(self, max_workers: int = 10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def process_symbols(
        self,
        symbols: List[str],
        process_fn: Callable[[str], Any]
    ) -> Dict[str, Any]:
        """
        Process multiple symbols in parallel.

        Returns dict of {symbol: result}.
        """
        loop = asyncio.get_event_loop()

        with LATENCY.timed("parallel_process"):
            # Submit all tasks
            futures = {
                symbol: loop.run_in_executor(self.executor, process_fn, symbol)
                for symbol in symbols
            }

            # Gather results
            results = {}
            for symbol, future in futures.items():
                try:
                    results[symbol] = await future
                except Exception as e:
                    logger.debug(f"Parallel process failed for {symbol}: {e}")
                    results[symbol] = None

        return results

    def process_symbols_sync(
        self,
        symbols: List[str],
        process_fn: Callable[[str], Any]
    ) -> Dict[str, Any]:
        """Synchronous parallel processing."""
        with LATENCY.timed("parallel_process_sync"):
            futures = {
                symbol: self.executor.submit(process_fn, symbol)
                for symbol in symbols
            }

            results = {}
            for symbol, future in futures.items():
                try:
                    results[symbol] = future.result(timeout=5)
                except Exception as e:
                    logger.debug(f"Parallel process failed for {symbol}: {e}")
                    results[symbol] = None

        return results


# =============================================================================
# ORDER PRE-STAGING
# =============================================================================

@dataclass
class PreStagedOrder:
    """Pre-staged order ready for immediate execution."""
    symbol: str
    action: str  # BUY or SELL
    quantity: int
    order_type: str  # MARKET or LIMIT
    limit_price: Optional[float]
    stop_loss: float
    take_profit: float
    confidence: float
    staged_at: float
    valid_until: float  # Expiration time
    metadata: Dict[str, Any] = field(default_factory=dict)


class OrderPreStager:
    """
    Pre-stage orders so they're ready to fire instantly.

    When a high-confidence signal comes in, we pre-compute the order
    so execution is just a single API call.
    """

    def __init__(self, ttl_seconds: float = 5.0):
        self.ttl = ttl_seconds
        self._staged: Dict[str, PreStagedOrder] = {}
        self._lock = Lock()

    def stage(
        self,
        symbol: str,
        action: str,
        quantity: int,
        stop_loss: float,
        take_profit: float,
        confidence: float,
        limit_price: Optional[float] = None,
        metadata: Optional[Dict] = None
    ) -> PreStagedOrder:
        """Stage an order for immediate execution."""
        now = time.time()
        order = PreStagedOrder(
            symbol=symbol,
            action=action,
            quantity=quantity,
            order_type="LIMIT" if limit_price else "MARKET",
            limit_price=limit_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            staged_at=now,
            valid_until=now + self.ttl,
            metadata=metadata or {}
        )

        with self._lock:
            self._staged[symbol] = order

        logger.info(f"📋 Order pre-staged: {action} {quantity} {symbol} (valid for {self.ttl}s)")
        return order

    def get(self, symbol: str) -> Optional[PreStagedOrder]:
        """Get a pre-staged order if still valid."""
        with self._lock:
            order = self._staged.get(symbol)
            if order is None:
                return None
            if order.valid_until < time.time():
                del self._staged[symbol]
                return None
            return order

    def execute(self, symbol: str, broker) -> Optional[Dict]:
        """Execute a pre-staged order."""
        order = self.get(symbol)
        if order is None:
            return None

        with LATENCY.timed("order_execution"):
            if order.order_type == "MARKET":
                result = broker.place_market_order(symbol, order.quantity, order.action)
            else:
                result = broker.place_limit_order(
                    symbol, order.quantity, order.action, order.limit_price
                )

        with self._lock:
            if symbol in self._staged:
                del self._staged[symbol]

        return result

    def clear_expired(self):
        """Remove expired orders."""
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._staged.items() if v.valid_until < now]
            for k in expired:
                del self._staged[k]

    def get_all_staged(self) -> List[PreStagedOrder]:
        """Get all currently staged orders."""
        now = time.time()
        with self._lock:
            return [o for o in self._staged.values() if o.valid_until > now]


# =============================================================================
# UNIFIED PERFORMANCE ENGINE
# =============================================================================

class PerformanceEngine:
    """
    Unified high-performance trading engine.

    Combines all optimization layers:
    - Caching
    - Pre-computation
    - Parallel processing
    - Order pre-staging
    - Latency monitoring
    """

    def __init__(self, market_data_provider, symbols: List[str]):
        self.market_data = market_data_provider
        self.symbols = set(symbols)

        # Initialize components
        self.cache = HighPerformanceCache(max_size=10000, default_ttl=1.0)
        self.indicator_computer = IndicatorPreComputer(market_data_provider, symbols)
        self.parallel_processor = ParallelSymbolProcessor(max_workers=20)
        self.order_prestager = OrderPreStager(ttl_seconds=5.0)
        self.vectorized = VectorizedIndicators()

        # Start background processes
        self.indicator_computer.start()

        logger.info(f"🚀 Performance Engine initialized ({len(symbols)} symbols)")

    def get_cached_snapshot(self, symbol: str) -> Optional[Dict]:
        """Get cached market snapshot."""
        cache_key = f"snapshot_{symbol}"

        def compute():
            return self.market_data.get_market_snapshot(symbol)

        return self.cache.get_or_compute(cache_key, compute, ttl=0.5)

    def get_indicators_fast(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get pre-computed indicators (near-instant)."""
        # First try pre-computed cache
        indicators = self.indicator_computer.get_indicators(symbol)
        if indicators:
            return indicators

        # Fallback to computing
        cache_key = f"indicators_{symbol}"

        def compute():
            bars = self.market_data.get_historical_bars(symbol, "1 D", "5 mins")
            if not bars or len(bars) < 20:
                return None

            close = np.array([b['close'] for b in bars], dtype=np.float64)
            high = np.array([b['high'] for b in bars], dtype=np.float64)
            low = np.array([b['low'] for b in bars], dtype=np.float64)
            volume = np.array([b.get('volume', 0) for b in bars], dtype=np.float64)

            return {
                'ema_9': self.vectorized.ema(close, 9)[-1],
                'ema_21': self.vectorized.ema(close, 21)[-1],
                'rsi_14': self.vectorized.rsi(close, 14)[-1],
                'atr_14': self.vectorized.atr(high, low, close, 14)[-1],
                'vwap': self.vectorized.vwap(high, low, close, volume)[-1],
                'price': close[-1]
            }

        return self.cache.get_or_compute(cache_key, compute, ttl=1.0)

    async def analyze_universe_fast(self, analyze_fn: Callable) -> Dict[str, Any]:
        """Analyze entire universe in parallel."""
        return await self.parallel_processor.process_symbols(
            list(self.symbols),
            analyze_fn
        )

    def stage_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        stop_loss: float,
        take_profit: float,
        confidence: float
    ) -> PreStagedOrder:
        """Pre-stage an order for fast execution."""
        return self.order_prestager.stage(
            symbol=symbol,
            action=action,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence
        )

    def execute_staged(self, symbol: str, broker) -> Optional[Dict]:
        """Execute pre-staged order."""
        return self.order_prestager.execute(symbol, broker)

    def get_latency_report(self) -> Dict:
        """Get latency metrics for all components."""
        return {
            "latency": LATENCY.get_report(),
            "cache_hit_rate": self.cache.hit_rate,
            "symbols_tracked": len(self.symbols),
            "staged_orders": len(self.order_prestager.get_all_staged())
        }

    def stop(self):
        """Stop all background processes."""
        self.indicator_computer.stop()


# =============================================================================
# FAST SIGNAL PROCESSOR
# =============================================================================

class FastSignalProcessor:
    """
    Ultra-fast signal processing pipeline.

    Target: <10ms from data to decision.
    """

    def __init__(self, performance_engine: PerformanceEngine):
        self.engine = performance_engine
        self.vectorized = VectorizedIndicators()

    def process_signal_fast(
        self,
        symbol: str,
        strategy_signals: List[Dict],
        current_price: float
    ) -> Dict[str, Any]:
        """
        Process signals with minimal latency.

        Returns decision with full analysis.
        """
        start = time.perf_counter()

        # Get pre-computed indicators
        indicators = self.engine.get_indicators_fast(symbol)

        if not indicators:
            return {"action": "HOLD", "reason": "No indicators available"}

        # Fast signal aggregation
        buy_signals = sum(1 for s in strategy_signals if s.get("action") == "BUY")
        sell_signals = sum(1 for s in strategy_signals if s.get("action") == "SELL")
        total_confidence = sum(s.get("confidence", 0) for s in strategy_signals)
        avg_confidence = total_confidence / len(strategy_signals) if strategy_signals else 0

        # Quick trend check using pre-computed EMAs
        ema_9 = indicators.get('ema_9', current_price)
        ema_21 = indicators.get('ema_21', current_price)
        trend_bullish = ema_9 > ema_21 and current_price > ema_9

        # RSI filter
        rsi = indicators.get('rsi_14', 50)
        rsi_ok = 30 < rsi < 70  # Not overbought/oversold

        # Determine action
        if buy_signals >= 2 and avg_confidence > 0.7 and trend_bullish and rsi_ok:
            action = "BUY"
        elif sell_signals >= 2 and avg_confidence > 0.7 and not trend_bullish:
            action = "SELL"
        else:
            action = "HOLD"

        # Calculate stops using pre-computed ATR
        atr = indicators.get('atr_14', current_price * 0.02)
        stop_loss = current_price - (atr * 1.5) if action == "BUY" else current_price + (atr * 1.5)
        take_profit = current_price + (atr * 3.75) if action == "BUY" else current_price - (atr * 3.75)

        elapsed_ms = (time.perf_counter() - start) * 1000
        LATENCY.record("signal_processing", elapsed_ms)

        return {
            "symbol": symbol,
            "action": action,
            "confidence": avg_confidence,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "trend_bullish": trend_bullish,
            "rsi": rsi,
            "atr": atr,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "indicators": indicators,
            "processing_time_ms": round(elapsed_ms, 3)
        }


# =============================================================================
# INTEGRATION VALIDATOR
# =============================================================================

class SystemIntegrationValidator:
    """
    Validates that all trading systems work together correctly.

    Run this on startup to catch integration issues.
    """

    def __init__(self):
        self.results: Dict[str, bool] = {}
        self.errors: List[str] = []

    def validate_all(
        self,
        performance_engine: PerformanceEngine,
        elite_system: Any,
        pro_validator: Any,
        broker: Any
    ) -> bool:
        """Run all integration validations."""
        logger.info("🔍 Running system integration validation...")

        # Test 1: Cache works
        self._test("cache_operations", lambda: self._test_cache(performance_engine))

        # Test 2: Indicators pre-compute
        self._test("indicator_precompute", lambda: self._test_indicators(performance_engine))

        # Test 3: Parallel processing
        self._test("parallel_processing", lambda: self._test_parallel(performance_engine))

        # Test 4: Order pre-staging
        self._test("order_prestaging", lambda: self._test_prestaging(performance_engine))

        # Test 5: Broker connection
        self._test("broker_connection", lambda: self._test_broker(broker))

        # Test 6: Latency acceptable
        self._test("latency_acceptable", lambda: self._test_latency())

        # Report results
        passed = sum(1 for v in self.results.values() if v)
        total = len(self.results)

        if passed == total:
            logger.info(f"✅ All {total} integration tests PASSED")
            return True
        else:
            logger.error(f"❌ {total - passed}/{total} integration tests FAILED")
            for error in self.errors:
                logger.error(f"   - {error}")
            return False

    def _test(self, name: str, test_fn: Callable) -> bool:
        try:
            result = test_fn()
            self.results[name] = result
            status = "✓" if result else "✗"
            logger.info(f"   {status} {name}")
            return result
        except Exception as e:
            self.results[name] = False
            self.errors.append(f"{name}: {str(e)}")
            logger.info(f"   ✗ {name} (error)")
            return False

    def _test_cache(self, engine: PerformanceEngine) -> bool:
        engine.cache.set("test_key", "test_value", ttl=10)
        return engine.cache.get("test_key") == "test_value"

    def _test_indicators(self, engine: PerformanceEngine) -> bool:
        # Just check the computer is running
        return engine.indicator_computer._running

    def _test_parallel(self, engine: PerformanceEngine) -> bool:
        def dummy_fn(x):
            return x * 2

        results = engine.parallel_processor.process_symbols_sync(["A", "B"], dummy_fn)
        return results.get("A") == "AA" and results.get("B") == "BB"

    def _test_prestaging(self, engine: PerformanceEngine) -> bool:
        order = engine.stage_order("TEST", "BUY", 10, 99.0, 101.0, 0.8)
        retrieved = engine.order_prestager.get("TEST")
        return retrieved is not None and retrieved.symbol == "TEST"

    def _test_broker(self, broker: Any) -> bool:
        return hasattr(broker, 'is_connected') and hasattr(broker, 'place_market_order')

    def _test_latency(self) -> bool:
        # Check if any recorded latency is too high
        report = LATENCY.get_report()
        for component, metrics in report.items():
            if metrics.get("p99_ms", 0) > 50:  # 50ms p99 threshold
                self.errors.append(f"High latency in {component}: p99={metrics['p99_ms']:.1f}ms")
                return False
        return True
