from __future__ import annotations

import asyncio
import logging
from typing import Dict, Iterable, Optional

import httpx

logger = logging.getLogger("short_interest_provider")


class ShortInterestProvider:
    """Fetch short interest data from Polygon's short interest endpoint."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.polygon.io",
        max_concurrency: int = 5,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_concurrency = max(1, max_concurrency)

    async def fetch_short_interest(self, symbols: Iterable[str]) -> Dict[str, Dict[str, float]]:
        if not self.api_key:
            return {}

        semaphore = asyncio.Semaphore(self.max_concurrency)
        results: Dict[str, Dict[str, float]] = {}

        async def fetch_symbol(client: httpx.AsyncClient, symbol: str) -> Optional[Dict[str, float]]:
            async with semaphore:
                try:
                    params = {
                        "ticker": symbol,
                        "limit": 1,
                        "sort": "settlement_date.desc",
                        "apiKey": self.api_key,
                    }
                    url = f"{self.base_url}/stocks/v1/short-interest"
                    response = await client.get(url, params=params)
                    if response.status_code != 200:
                        return None
                    payload = response.json()
                    items = payload.get("results") or []
                    if not items:
                        return None
                    item = items[0]
                    return {
                        "short_interest": float(item.get("short_interest", 0.0) or 0.0),
                        "avg_daily_volume": float(item.get("avg_daily_volume", 0.0) or 0.0),
                        "days_to_cover": float(item.get("days_to_cover", 0.0) or 0.0),
                    }
                except Exception as exc:
                    logger.debug(f"Short interest fetch failed for {symbol}: {exc}")
                    return None

        symbols_list = [s.upper() for s in symbols if s]
        if not symbols_list:
            return {}

        async with httpx.AsyncClient(timeout=10.0) as client:
            tasks = [fetch_symbol(client, symbol) for symbol in symbols_list]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

        for symbol, data in zip(symbols_list, responses):
            if isinstance(data, dict):
                results[symbol] = data

        return results
