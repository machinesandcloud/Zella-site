from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class IBKRWebAPIClient:
    def __init__(
        self,
        base_url: str,
        account_id: Optional[str] = None,
        verify_ssl: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.account_id = account_id
        self.verify_ssl = verify_ssl
        self._client = httpx.Client(timeout=10.0, verify=verify_ssl)

    def _url(self, path: str) -> str:
        if path.startswith("/"):
            path = path[1:]
        return f"{self.base_url}/{path}"

    def auth_status(self) -> Dict[str, Any]:
        response = self._client.get(self._url("/iserver/auth/status"))
        response.raise_for_status()
        return response.json()

    def is_connected(self) -> bool:
        try:
            status = self.auth_status()
            return bool(status.get("authenticated", False) and status.get("connected", False))
        except Exception as e:
            logger.debug(f"IBKR Web API connection check failed: {e}")
            return False

    def tickle(self) -> Dict[str, Any]:
        """Keep the session alive. Should be called every 5 minutes to prevent timeout."""
        try:
            response = self._client.post(self._url("/tickle"))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def _fetch_accounts(self) -> List[str]:
        endpoints = ["/iserver/accounts", "/portfolio/accounts"]
        for endpoint in endpoints:
            try:
                response = self._client.get(self._url(endpoint))
                response.raise_for_status()
                data = response.json()
                if isinstance(data, list):
                    accounts = [item.get("accountId") or item.get("id") for item in data]
                    accounts = [acct for acct in accounts if acct]
                    if accounts:
                        return accounts
                if isinstance(data, dict):
                    accounts = data.get("accounts") or data.get("accountIds") or []
                    if accounts:
                        return accounts
            except Exception as e:
                logger.debug(f"Failed to fetch accounts from {endpoint}: {e}")
                continue
        return []

    def get_account_id(self) -> Optional[str]:
        if self.account_id:
            return self.account_id
        accounts = self._fetch_accounts()
        if accounts:
            self.account_id = accounts[0]
        return self.account_id

    def resolve_conid(self, symbol: str) -> Optional[int]:
        response = self._client.get(self._url("/iserver/secdef/search"), params={"symbol": symbol})
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and data:
            conid = data[0].get("conid")
            return int(conid) if conid else None
        if isinstance(data, dict):
            conids = data.get("conids") or []
            if conids:
                return int(conids[0])
        return None

    def get_market_snapshot(self, symbol: str) -> Dict[str, Any]:
        conid = self.resolve_conid(symbol)
        if not conid:
            return {}
        fields = "31,55,84,86"
        response = self._client.get(
            self._url("/iserver/marketdata/snapshot"),
            params={"conids": conid, "fields": fields},
        )
        response.raise_for_status()
        data = response.json()
        if not data:
            return {}
        snap = data[0]
        return {
            "symbol": symbol,
            "price": float(snap.get("31", 0) or 0),
            "volume": float(snap.get("55", 0) or 0),
            "bid": float(snap.get("84", 0) or 0),
            "ask": float(snap.get("86", 0) or 0),
        }

    def get_historical_bars(self, symbol: str, period: str = "1d", bar: str = "5min") -> List[Dict[str, Any]]:
        conid = self.resolve_conid(symbol)
        if not conid:
            return []
        response = self._client.get(
            self._url("/iserver/marketdata/history"),
            params={"conid": conid, "period": period, "bar": bar, "outsideRth": True},
        )
        response.raise_for_status()
        data = response.json()
        bars = []
        for item in data.get("data", []) if isinstance(data, dict) else []:
            bars.append(
                {
                    "date": item.get("t"),
                    "open": item.get("o"),
                    "high": item.get("h"),
                    "low": item.get("l"),
                    "close": item.get("c"),
                    "volume": item.get("v"),
                }
            )
        return bars

    def get_account_summary(self) -> Dict[str, Any]:
        account_id = self.get_account_id()
        if not account_id:
            return {}
        response = self._client.get(self._url(f"/portfolio/{account_id}/summary"))
        response.raise_for_status()
        data = response.json()
        return {
            "NetLiquidation": data.get("netLiquidation") or data.get("NetLiquidation"),
            "BuyingPower": data.get("buyingPower") or data.get("BuyingPower"),
            "CashBalance": data.get("cashBalance") or data.get("CashBalance"),
            "RealizedPnL": data.get("realizedPnL") or data.get("RealizedPnL"),
            "UnrealizedPnL": data.get("unrealizedPnL") or data.get("UnrealizedPnL"),
        }

    def get_positions(self) -> List[Dict[str, Any]]:
        account_id = self.get_account_id()
        if not account_id:
            return []
        response = self._client.get(self._url(f"/portfolio/{account_id}/positions"))
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []

    def place_order(self, symbol: str, quantity: int, side: str, order_type: str, price: Optional[float] = None) -> Dict[str, Any]:
        account_id = self.get_account_id()
        if not account_id:
            raise RuntimeError("Account ID unavailable")
        conid = self.resolve_conid(symbol)
        if not conid:
            raise RuntimeError("Could not resolve conid")
        order = {
            "conid": conid,
            "secType": "STK",
            "orderType": order_type,
            "side": side,
            "quantity": quantity,
            "tif": "DAY",
        }
        if price is not None:
            order["price"] = price
        response = self._client.post(
            self._url(f"/iserver/account/{account_id}/orders"),
            json={"orders": [order]},
        )
        response.raise_for_status()
        return response.json()
