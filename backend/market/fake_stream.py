from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import random
from typing import Dict, Iterable, List


DEFAULT_SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMD"]


@dataclass
class FakeSymbolState:
    price: float
    drift: float
    volatility: float


class FakeMarketDataStream:
    def __init__(self, symbols: Iterable[str], seed: int = 42) -> None:
        self._rng = random.Random(seed)
        self._states: Dict[str, FakeSymbolState] = {}
        for symbol in symbols:
            self._states[symbol] = self._make_state()

    def _make_state(self) -> FakeSymbolState:
        base = self._rng.uniform(20, 300)
        drift = self._rng.uniform(-0.0004, 0.0004)
        volatility = self._rng.uniform(0.001, 0.004)
        return FakeSymbolState(price=base, drift=drift, volatility=volatility)

    def _ensure_symbol(self, symbol: str) -> FakeSymbolState:
        state = self._states.get(symbol)
        if state is None:
            state = self._make_state()
            self._states[symbol] = state
        return state

    def tick(self, symbol: str) -> Dict[str, object]:
        state = self._ensure_symbol(symbol)
        shock = self._rng.gauss(0, state.volatility)
        state.price = max(0.5, state.price * (1 + state.drift + shock))
        volume = max(1, int(abs(self._rng.gauss(5000, 1500))))
        return {
            "symbol": symbol,
            "price": round(state.price, 2),
            "volume": volume,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def ticks(self, symbols: Iterable[str]) -> List[Dict[str, object]]:
        return [self.tick(symbol) for symbol in symbols]

    def order_book(self, symbol: str, depth: int = 10) -> Dict[str, object]:
        state = self._ensure_symbol(symbol)
        mid = state.price
        spread = max(0.01, mid * self._rng.uniform(0.0005, 0.002))
        bids = []
        asks = []
        for level in range(depth):
            price_offset = spread * (level + 1)
            bids.append(
                {
                    "price": round(mid - price_offset, 2),
                    "size": int(abs(self._rng.gauss(500, 200)) + 1),
                }
            )
            asks.append(
                {
                    "price": round(mid + price_offset, 2),
                    "size": int(abs(self._rng.gauss(500, 200)) + 1),
                }
            )
        return {
            "symbol": symbol,
            "mid": round(mid, 2),
            "spread": round(spread, 4),
            "bids": bids,
            "asks": asks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def time_sales(self, symbol: str) -> Dict[str, object]:
        tick = self.tick(symbol)
        side = self._rng.choice(["BUY", "SELL"])
        return {
            "symbol": symbol,
            "price": tick["price"],
            "size": int(abs(self._rng.gauss(300, 150)) + 1),
            "side": side,
            "timestamp": tick["timestamp"],
        }
