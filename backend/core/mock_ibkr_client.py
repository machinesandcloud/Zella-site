import random
from typing import Any, Dict, List, Optional


class MockIBKRClient:
    def __init__(self) -> None:
        self._connected = False
        self._order_id = 1
        self._paper_trading_mode = True
        self._positions = [
            {"symbol": "AAPL", "position": 10, "avg_cost": 150.0},
            {"symbol": "TSLA", "position": -5, "avg_cost": 240.0},
        ]

    def connect_to_ibkr(self, host: str, port: int, client_id: int, is_paper_trading: bool) -> bool:
        self._connected = True
        self._paper_trading_mode = is_paper_trading
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def reconnect_with_retry(self, host: str, port: int, client_id: int, retries: int = 5) -> bool:
        return self.connect_to_ibkr(host, port, client_id, self._paper_trading_mode)

    def get_account_summary(self) -> Dict[str, Any]:
        return {
            "NetLiquidation": 100000,
            "CashBalance": 50000,
            "BuyingPower": 200000,
            "RealizedPnL": 1200,
            "UnrealizedPnL": 300,
        }

    def get_positions(self) -> List[Dict[str, Any]]:
        return list(self._positions)

    def close_position(self, symbol: str) -> None:
        self._positions = [pos for pos in self._positions if pos.get("symbol") != symbol]

    def get_cash_balance(self) -> float:
        return 50000.0

    def get_buying_power(self) -> float:
        return 200000.0

    def fetch_historical_data(self, symbol: str, duration: str, bar_size: str, what_to_show: str = "TRADES", timeout: int = 10) -> List[Dict[str, Any]]:
        random.seed(symbol)
        price = 100.0
        bars = []
        for i in range(60):
            change = random.uniform(-1, 1)
            close = price + change
            high = max(price, close) + random.uniform(0, 0.5)
            low = min(price, close) - random.uniform(0, 0.5)
            bars.append(
                {
                    "date": f"2024-01-01 10:{i:02d}:00",
                    "open": price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": random.randint(1000, 5000),
                }
            )
            price = close
        return bars

    def scan_top_movers(self, *args, **kwargs) -> List[str]:
        return ["AAPL", "MSFT", "NVDA", "TSLA", "AMD"]

    def place_market_order(self, symbol: str, quantity: int, action: str, contract_params: Optional[Dict[str, Any]] = None) -> int:
        order_id = self._order_id
        self._order_id += 1
        return order_id

    def place_limit_order(self, symbol: str, quantity: int, action: str, limit_price: float, contract_params: Optional[Dict[str, Any]] = None) -> int:
        return self.place_market_order(symbol, quantity, action, contract_params)

    def place_stop_order(self, symbol: str, quantity: int, action: str, stop_price: float, contract_params: Optional[Dict[str, Any]] = None) -> int:
        return self.place_market_order(symbol, quantity, action, contract_params)

    def place_bracket_order(self, symbol: str, quantity: int, action: str, take_profit: float, stop_loss: float, contract_params: Optional[Dict[str, Any]] = None) -> List[int]:
        return [self.place_market_order(symbol, quantity, action, contract_params)]

    def cancel_order(self, order_id: int) -> None:
        return None

    def modify_order(self, order_id: int, new_params: Dict[str, Any]) -> None:
        return None

    def get_open_orders(self) -> Dict[int, Dict[str, Any]]:
        return {}

    def get_order_status(self, order_id: int) -> Dict[str, Any]:
        return {}

    def set_paper_trading_mode(self, enable: bool) -> None:
        self._paper_trading_mode = enable

    def get_trading_mode(self) -> str:
        return "PAPER" if self._paper_trading_mode else "LIVE"

    def api_available(self) -> bool:
        return True

    def kill_switch(self) -> None:
        return None
