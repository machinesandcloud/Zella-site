import asyncio
from datetime import datetime
from typing import Dict, List, Set, Any, Optional
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from market.fake_stream import DEFAULT_SYMBOLS, FakeMarketDataStream

router = APIRouter()
logger = logging.getLogger("websocket_market_data")

FAKE_STREAM = FakeMarketDataStream(DEFAULT_SYMBOLS)

# Connection manager for broadcasting updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.symbol_subscriptions: Dict[WebSocket, Set[str]] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)
        self.symbol_subscriptions[websocket] = set()

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
        if websocket in self.symbol_subscriptions:
            del self.symbol_subscriptions[websocket]

    def subscribe_symbols(self, websocket: WebSocket, symbols: List[str]):
        if websocket in self.symbol_subscriptions:
            self.symbol_subscriptions[websocket].update(symbols)

    async def broadcast(self, channel: str, message: dict):
        if channel in self.active_connections:
            for connection in list(self.active_connections[channel]):
                try:
                    await connection.send_json(message)
                except Exception:
                    self.active_connections[channel].discard(connection)


manager = ConnectionManager()


def _get_market_provider():
    from main import app
    return app.state.market_data_provider


def _get_autonomous_engine():
    from main import app
    return getattr(app.state, "autonomous_engine", None)


async def _stream(websocket: WebSocket, channel: str) -> None:
    await websocket.accept()
    try:
        while True:
            message = {
                "channel": channel,
                "timestamp": datetime.utcnow().isoformat(),
            }
            await websocket.send_json(message)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return


@router.websocket("/ws/market-data")
async def market_data_ws(websocket: WebSocket) -> None:
    """Real-time market data streaming at 200ms intervals for day trading."""
    symbols_param = websocket.query_params.get("symbol") or websocket.query_params.get("symbols")
    if symbols_param:
        symbols = [item.strip().upper() for item in symbols_param.split(",") if item.strip()]
    else:
        symbols = DEFAULT_SYMBOLS[:10]  # Limit to 10 for faster updates

    interval = float(websocket.query_params.get("interval", "0.2"))  # 200ms default
    interval = max(0.1, min(interval, 2.0))  # Clamp between 100ms and 2s

    await websocket.accept()
    try:
        while True:
            provider = _get_market_provider()
            batch = []
            for symbol in symbols:
                snapshot = provider.get_market_snapshot(symbol) or {}
                if snapshot:
                    batch.append({
                        "symbol": symbol,
                        "price": snapshot.get("price", 0),
                        "bid": snapshot.get("bid", 0),
                        "ask": snapshot.get("ask", 0),
                        "bid_size": snapshot.get("bid_size", 0),
                        "ask_size": snapshot.get("ask_size", 0),
                        "volume": snapshot.get("volume", 0),
                    })
                else:
                    ticks = FAKE_STREAM.ticks([symbol])
                    for tick in ticks:
                        batch.append(tick)

            # Send all updates in a single message for efficiency
            message = {
                "channel": "market-data",
                "type": "batch",
                "data": batch,
                "timestamp": datetime.utcnow().isoformat(),
            }
            await websocket.send_json(message)
            await asyncio.sleep(interval)
    except WebSocketDisconnect:
        return


@router.websocket("/ws/live-ticker")
async def live_ticker_ws(websocket: WebSocket) -> None:
    """
    High-frequency live ticker feed for day trading.
    Streams real-time prices at 100ms intervals for selected symbols.
    """
    symbols_param = websocket.query_params.get("symbols")
    if symbols_param:
        symbols = [s.strip().upper() for s in symbols_param.split(",") if s.strip()][:20]
    else:
        # Get top symbols from autonomous engine if available
        engine = _get_autonomous_engine()
        if engine and engine.last_scanner_results:
            symbols = [r.get("symbol") for r in engine.last_scanner_results[:10] if r.get("symbol")]
        else:
            symbols = DEFAULT_SYMBOLS[:10]

    await websocket.accept()

    # Send initial subscription confirmation
    await websocket.send_json({
        "channel": "live-ticker",
        "type": "subscribed",
        "symbols": symbols,
        "interval_ms": 100,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Track price changes for highlighting
    last_prices: Dict[str, float] = {}

    try:
        while True:
            provider = _get_market_provider()
            tickers = []

            for symbol in symbols:
                snapshot = provider.get_market_snapshot(symbol) or {}
                if snapshot:
                    current_price = snapshot.get("price", 0)
                    prev_price = last_prices.get(symbol, current_price)
                    change = current_price - prev_price
                    change_pct = (change / prev_price * 100) if prev_price else 0
                    last_prices[symbol] = current_price

                    tickers.append({
                        "symbol": symbol,
                        "price": round(current_price, 2),
                        "bid": round(snapshot.get("bid", 0), 2),
                        "ask": round(snapshot.get("ask", 0), 2),
                        "spread": round(snapshot.get("ask", 0) - snapshot.get("bid", 0), 2),
                        "change": round(change, 2),
                        "change_pct": round(change_pct, 4),
                        "direction": "up" if change > 0 else "down" if change < 0 else "flat",
                        "bid_size": snapshot.get("bid_size", 0),
                        "ask_size": snapshot.get("ask_size", 0),
                    })
                else:
                    # Fallback to fake data for testing
                    ticks = FAKE_STREAM.ticks([symbol])
                    for tick in ticks:
                        current_price = tick.get("price", 0)
                        prev_price = last_prices.get(symbol, current_price)
                        change = current_price - prev_price
                        last_prices[symbol] = current_price
                        tickers.append({
                            **tick,
                            "change": round(change, 2),
                            "change_pct": round((change / prev_price * 100) if prev_price else 0, 4),
                            "direction": "up" if change > 0 else "down" if change < 0 else "flat",
                        })

            await websocket.send_json({
                "channel": "live-ticker",
                "type": "update",
                "data": tickers,
                "timestamp": datetime.utcnow().isoformat(),
            })

            await asyncio.sleep(0.1)  # 100ms for real-time feel
    except WebSocketDisconnect:
        return


@router.websocket("/ws/bot-activity")
async def bot_activity_ws(websocket: WebSocket) -> None:
    """
    Real-time bot activity stream showing autonomous engine decisions.
    Streams: current status, scan results, trade decisions, position updates
    """
    await websocket.accept()

    await websocket.send_json({
        "channel": "bot-activity",
        "type": "connected",
        "timestamp": datetime.utcnow().isoformat(),
    })

    try:
        last_decision_count = 0
        last_scan_time: Optional[str] = None

        while True:
            engine = _get_autonomous_engine()

            if engine:
                current_scan_time = engine.last_scan_time.isoformat() if engine.last_scan_time else None
                current_decision_count = len(engine.decisions)

                # Build activity update
                activity = {
                    "channel": "bot-activity",
                    "type": "status",
                    "data": {
                        "running": engine.running,
                        "mode": engine.mode,
                        "risk_posture": engine.risk_posture,
                        "last_scan": current_scan_time,
                        "symbols_scanned": engine.symbols_scanned,
                        "opportunities_found": len(engine.last_scanner_results),
                        "active_positions": len(engine.broker.get_positions()) if engine.broker.is_connected() else 0,
                        "top_picks": [
                            {"symbol": r.get("symbol"), "score": r.get("combined_score", 0)}
                            for r in engine.last_scanner_results[:5]
                        ],
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                }

                # If new scan happened, send scan results
                if current_scan_time and current_scan_time != last_scan_time:
                    activity["data"]["new_scan"] = True
                    activity["data"]["filter_summary"] = engine.filter_summary
                    last_scan_time = current_scan_time

                # If new decisions, send them
                if current_decision_count > last_decision_count:
                    new_decisions = engine.decisions[:current_decision_count - last_decision_count]
                    activity["data"]["new_decisions"] = new_decisions
                    last_decision_count = current_decision_count

                await websocket.send_json(activity)
            else:
                await websocket.send_json({
                    "channel": "bot-activity",
                    "type": "error",
                    "message": "Autonomous engine not available",
                    "timestamp": datetime.utcnow().isoformat(),
                })

            await asyncio.sleep(0.5)  # 500ms for bot activity updates
    except WebSocketDisconnect:
        return


@router.websocket("/ws/orders")
async def orders_ws(websocket: WebSocket) -> None:
    await _stream(websocket, "orders")


@router.websocket("/ws/account-updates")
async def account_updates_ws(websocket: WebSocket) -> None:
    await _stream(websocket, "account-updates")


@router.websocket("/ws/order-book")
async def order_book_ws(websocket: WebSocket) -> None:
    symbol = (websocket.query_params.get("symbol") or "AAPL").upper()
    await websocket.accept()
    try:
        while True:
            message = {
                "channel": "order-book",
                "symbol": symbol,
                "status": "UNAVAILABLE",
                "reason": "Free data source does not provide Level 2 order book",
                "timestamp": datetime.utcnow().isoformat(),
                "bids": [],
                "asks": [],
                "mid": None,
                "spread": None,
            }
            await websocket.send_json(message)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return


@router.websocket("/ws/time-sales")
async def time_sales_ws(websocket: WebSocket) -> None:
    symbol = (websocket.query_params.get("symbol") or "AAPL").upper()
    await websocket.accept()
    try:
        while True:
            message = {
                "channel": "time-sales",
                "symbol": symbol,
                "status": "UNAVAILABLE",
                "reason": "Free data source does not provide time & sales tape",
                "timestamp": datetime.utcnow().isoformat(),
                "price": None,
                "size": None,
                "side": None,
            }
            await websocket.send_json(message)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return
