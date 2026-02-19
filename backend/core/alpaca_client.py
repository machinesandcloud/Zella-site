"""Alpaca Trading API Client for Zella AI Trading."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

logger = logging.getLogger("alpaca_client")

# Request timeout in seconds (configured in httpx within alpaca-py)
DEFAULT_TIMEOUT = 10


class AlpacaClient:
    """
    Alpaca API client for trading and market data.

    Much simpler than IBKR - just needs API keys!
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        paper: bool = True,
    ) -> None:
        """
        Initialize Alpaca client.

        Args:
            api_key: Alpaca API key ID
            secret_key: Alpaca secret key
            paper: True for paper trading, False for live
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.paper = paper

        # Trading client
        self.trading_client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=paper
        )

        # Market data client (no auth needed for basic data)
        self.market_data_client = StockHistoricalDataClient(
            api_key=api_key,
            secret_key=secret_key
        )

        self._connected = False
        logger.info(f"Alpaca client initialized (paper={paper})")

    def connect(self) -> bool:
        """
        Connect to Alpaca (verify API keys work).

        Returns:
            True if connection successful
        """
        try:
            # Test connection by getting account info
            logger.info(f"Attempting Alpaca connection (paper={self.paper})...")
            account = self.trading_client.get_account()
            self._connected = True
            logger.info(f"✓ Connected to Alpaca successfully!")
            logger.info(f"  Account: {account.account_number}")
            logger.info(f"  Buying Power: ${account.buying_power}")
            logger.info(f"  Portfolio Value: ${account.portfolio_value}")
            logger.info(f"  Status: {account.status}")
            return True
        except Exception as e:
            # Log the full error details for debugging
            import traceback
            logger.error(f"✗ Alpaca connection failed:")
            logger.error(f"  Error Type: {type(e).__name__}")
            logger.error(f"  Error Message: {str(e)}")
            logger.error(f"  Paper Mode: {self.paper}")
            logger.error(f"  API Key (first 10): {self.api_key[:10] if len(self.api_key) >= 10 else 'TOO SHORT'}")
            logger.error(f"  Stack Trace:\n{traceback.format_exc()}")
            self._connected = False
            return False

    def is_connected(self) -> bool:
        """Check if connected to Alpaca."""
        return self._connected

    def disconnect(self) -> None:
        """Disconnect from Alpaca (no-op, but kept for API compatibility)."""
        self._connected = False
        logger.info("Disconnected from Alpaca")

    def get_trading_mode(self) -> str:
        """Get current trading mode."""
        return "PAPER" if self.paper else "LIVE"

    # ==================== Account Methods ====================

    def get_account_summary(self) -> Dict[str, Any]:
        """
        Get account summary.

        Returns:
            Account summary with balance, buying power, etc.
        """
        try:
            account = self.trading_client.get_account()
            return {
                "NetLiquidation": float(account.portfolio_value),
                "BuyingPower": float(account.buying_power),
                "CashBalance": float(account.cash),
                "RealizedPnL": 0.0,  # Not directly available in Alpaca
                "UnrealizedPnL": float(account.equity) - float(account.last_equity),
            }
        except Exception as e:
            logger.error(f"Error getting account summary: {e}")
            return {}

    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions.

        Returns:
            List of positions with symbol, quantity, avg price, etc.
        """
        try:
            positions = self.trading_client.get_all_positions()
            return [
                {
                    "symbol": pos.symbol,
                    "quantity": int(pos.qty),
                    "avgPrice": float(pos.avg_entry_price),
                    "currentPrice": float(pos.current_price),
                    "marketValue": float(pos.market_value),
                    "unrealizedPnL": float(pos.unrealized_pl),
                    "unrealizedPnLPercent": float(pos.unrealized_plpc) * 100,
                }
                for pos in positions
            ]
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    # ==================== Trading Methods ====================

    def place_market_order(
        self,
        symbol: str,
        quantity: int,
        side: str
    ) -> Dict[str, Any]:
        """
        Place a market order.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            quantity: Number of shares
            side: "BUY" or "SELL"

        Returns:
            Order details
        """
        try:
            order_side = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL

            request = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=order_side,
                time_in_force=TimeInForce.DAY
            )

            order = self.trading_client.submit_order(request)

            logger.info(f"Market order placed: {side} {quantity} {symbol} - Order ID: {order.id}")

            return {
                "orderId": str(order.id),
                "symbol": order.symbol,
                "quantity": int(order.qty),
                "side": order.side.value,
                "orderType": "MARKET",
                "status": order.status.value,
                "filledQty": int(order.filled_qty or 0),
            }
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            raise

    def place_limit_order(
        self,
        symbol: str,
        quantity: int,
        side: str,
        limit_price: float
    ) -> Dict[str, Any]:
        """
        Place a limit order.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            side: "BUY" or "SELL"
            limit_price: Limit price

        Returns:
            Order details
        """
        try:
            order_side = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL

            request = LimitOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=order_side,
                time_in_force=TimeInForce.DAY,
                limit_price=limit_price
            )

            order = self.trading_client.submit_order(request)

            logger.info(f"Limit order placed: {side} {quantity} {symbol} @ ${limit_price} - Order ID: {order.id}")

            return {
                "orderId": str(order.id),
                "symbol": order.symbol,
                "quantity": int(order.qty),
                "side": order.side.value,
                "orderType": "LIMIT",
                "limitPrice": float(order.limit_price),
                "status": order.status.value,
                "filledQty": int(order.filled_qty or 0),
            }
        except Exception as e:
            logger.error(f"Error placing limit order: {e}")
            raise

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID."""
        try:
            self.trading_client.cancel_order_by_id(order_id)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False

    def get_orders(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get orders.

        Args:
            status: Filter by status ("open", "closed", "all")

        Returns:
            List of orders
        """
        try:
            from alpaca.trading.requests import GetOrdersRequest
            from alpaca.trading.enums import QueryOrderStatus

            status_filter = None
            if status == "open":
                status_filter = QueryOrderStatus.OPEN
            elif status == "closed":
                status_filter = QueryOrderStatus.CLOSED

            request = GetOrdersRequest(status=status_filter) if status_filter else GetOrdersRequest()
            orders = self.trading_client.get_orders(filter=request)

            return [
                {
                    "orderId": str(order.id),
                    "symbol": order.symbol,
                    "quantity": int(order.qty),
                    "side": order.side.value,
                    "orderType": order.order_type.value,
                    "status": order.status.value,
                    "filledQty": int(order.filled_qty or 0),
                    "limitPrice": float(order.limit_price) if order.limit_price else None,
                    "createdAt": order.created_at.isoformat() if order.created_at else None,
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []

    # ==================== Market Data Methods ====================

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest quote for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Quote with bid, ask, last price
        """
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quotes = self.market_data_client.get_stock_latest_quote(request)
            quote = quotes[symbol]

            return {
                "symbol": symbol,
                "bid": float(quote.bid_price),
                "ask": float(quote.ask_price),
                "bidSize": int(quote.bid_size),
                "askSize": int(quote.ask_size),
                "last": float(quote.ask_price),  # Use ask as approximation
                "timestamp": quote.timestamp.isoformat() if quote.timestamp else None,
            }
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            return {}

    def get_bars(
        self,
        symbol: str,
        timeframe: str = "1Min",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get historical bars.

        Args:
            symbol: Stock symbol
            timeframe: Bar timeframe ("1Min", "5Min", "1Hour", "1Day")
            limit: Number of bars to return

        Returns:
            List of OHLCV bars
        """
        try:
            # Map timeframe string to Alpaca TimeFrame
            timeframe_map = {
                "1Min": TimeFrame.Minute,
                "5Min": TimeFrame(5, "Min"),
                "15Min": TimeFrame(15, "Min"),
                "1Hour": TimeFrame.Hour,
                "1Day": TimeFrame.Day,
            }

            tf = timeframe_map.get(timeframe, TimeFrame.Minute)

            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=tf,
                limit=limit,
                start=datetime.now() - timedelta(days=5)
            )

            bars = self.market_data_client.get_stock_bars(request)

            return [
                {
                    "timestamp": bar.timestamp.isoformat(),
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": int(bar.volume),
                }
                for bar in bars[symbol]
            ]
        except Exception as e:
            logger.error(f"Error getting bars for {symbol}: {e}")
            return []
