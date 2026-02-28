import asyncio
from datetime import datetime
from typing import Dict, List, Set, Any, Optional
import logging
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from market.fake_stream import DEFAULT_SYMBOLS, FakeMarketDataStream

router = APIRouter()
logger = logging.getLogger("websocket_market_data")

FAKE_STREAM = FakeMarketDataStream(DEFAULT_SYMBOLS)

# Heartbeat interval in seconds - must be less than Render's idle timeout (~60s)
HEARTBEAT_INTERVAL = 25


async def send_with_heartbeat(websocket: WebSocket, message: dict) -> bool:
    """
    Send a message via WebSocket with error handling.
    Returns True if successful, False if connection is dead.
    """
    try:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(message)
            return True
        return False
    except Exception as e:
        logger.debug(f"WebSocket send failed: {e}")
        return False


async def heartbeat_ping(websocket: WebSocket) -> bool:
    """
    Send a heartbeat ping to keep the connection alive.
    Returns True if connection is healthy.
    """
    try:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat()
            })
            return True
        return False
    except Exception:
        return False


# Connection manager for broadcasting updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.symbol_subscriptions: Dict[WebSocket, Set[str]] = {}
        self._heartbeat_tasks: Dict[WebSocket, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)
        self.symbol_subscriptions[websocket] = set()

        # Start heartbeat task for this connection
        task = asyncio.create_task(self._heartbeat_loop(websocket, channel))
        self._heartbeat_tasks[websocket] = task

    async def _heartbeat_loop(self, websocket: WebSocket, channel: str):
        """Send periodic heartbeats to keep connection alive."""
        try:
            while websocket in self.active_connections.get(channel, set()):
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                if not await heartbeat_ping(websocket):
                    logger.debug(f"Heartbeat failed for {channel}, removing connection")
                    self.disconnect(websocket, channel)
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Heartbeat loop error: {e}")

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
        if websocket in self.symbol_subscriptions:
            del self.symbol_subscriptions[websocket]
        # Cancel heartbeat task
        if websocket in self._heartbeat_tasks:
            self._heartbeat_tasks[websocket].cancel()
            del self._heartbeat_tasks[websocket]

    def subscribe_symbols(self, websocket: WebSocket, symbols: List[str]):
        if websocket in self.symbol_subscriptions:
            self.symbol_subscriptions[websocket].update(symbols)

    async def broadcast(self, channel: str, message: dict):
        if channel in self.active_connections:
            dead_connections = []
            for connection in list(self.active_connections[channel]):
                try:
                    if connection.client_state == WebSocketState.CONNECTED:
                        await connection.send_json(message)
                    else:
                        dead_connections.append(connection)
                except Exception as e:
                    logger.debug(f"Removing disconnected client from {channel}: {e}")
                    dead_connections.append(connection)

            # Clean up dead connections
            for conn in dead_connections:
                self.disconnect(conn, channel)


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
    """Real-time market data streaming at 200ms intervals for day trading. Uses REAL data only."""
    symbols_param = websocket.query_params.get("symbol") or websocket.query_params.get("symbols")
    if symbols_param:
        symbols = [item.strip().upper() for item in symbols_param.split(",") if item.strip()]
    else:
        symbols = ["AAPL", "TSLA", "NVDA", "AMD", "META", "MSFT", "GOOGL", "AMZN", "SPY", "QQQ"]

    interval = float(websocket.query_params.get("interval", "0.2"))  # 200ms default
    interval = max(0.1, min(interval, 2.0))  # Clamp between 100ms and 2s

    # Note: Not using ConnectionManager here, so we call accept() directly
    await websocket.accept()
    try:
        while True:
            provider = _get_market_provider()
            batch = []
            for symbol in symbols:
                snapshot = provider.get_market_snapshot(symbol) or {}
                price = snapshot.get("price", 0)
                # Only include symbols with real prices
                if price > 0:
                    batch.append({
                        "symbol": symbol,
                        "price": price,
                        "bid": snapshot.get("bid", 0),
                        "ask": snapshot.get("ask", 0),
                        "bid_size": snapshot.get("bid_size", 0),
                        "ask_size": snapshot.get("ask_size", 0),
                        "volume": snapshot.get("volume", 0),
                    })

            # Send all updates in a single message for efficiency
            message = {
                "channel": "market-data",
                "type": "batch",
                "data": batch,
                "symbols_requested": len(symbols),
                "symbols_with_data": len(batch),
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
    Uses REAL market data only - no fake prices.
    """
    symbols_param = websocket.query_params.get("symbols")
    if symbols_param:
        symbols = [s.strip().upper() for s in symbols_param.split(",") if s.strip()][:50]
    else:
        # Get ALL symbols from autonomous engine if available (scanner results + evaluations)
        symbols = []
        engine = _get_autonomous_engine()
        if engine:
            # Combine scanner results (passed) with top evaluations for complete view
            scanner_symbols = [r.get("symbol") for r in (engine.last_scanner_results or []) if r.get("symbol")]
            # Also include symbols from analyzed opportunities
            opp_symbols = [o.get("symbol") for o in (engine.last_analyzed_opportunities or []) if o.get("symbol")]
            # Combine and deduplicate, keeping order (scanner first, then opportunities)
            seen = set()
            for sym in scanner_symbols + opp_symbols:
                if sym and sym not in seen:
                    symbols.append(sym)
                    seen.add(sym)
            symbols = symbols[:50]  # Limit to 50 for performance

        if not symbols:
            # Default popular day trading stocks
            symbols = ["AAPL", "TSLA", "NVDA", "AMD", "META", "MSFT", "GOOGL", "AMZN", "SPY", "QQQ"]

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
    last_symbols_update = datetime.utcnow()

    try:
        while True:
            provider = _get_market_provider()
            tickers = []
            data_source = "real"

            # Dynamically update symbols from engine every 5 seconds
            now = datetime.utcnow()
            if (now - last_symbols_update).total_seconds() > 5:
                engine = _get_autonomous_engine()
                if engine:
                    scanner_symbols = [r.get("symbol") for r in (engine.last_scanner_results or []) if r.get("symbol")]
                    opp_symbols = [o.get("symbol") for o in (engine.last_analyzed_opportunities or []) if o.get("symbol")]
                    seen = set()
                    new_symbols = []
                    for sym in scanner_symbols + opp_symbols:
                        if sym and sym not in seen:
                            new_symbols.append(sym)
                            seen.add(sym)
                    if new_symbols:
                        symbols = new_symbols[:50]
                last_symbols_update = now

            # Use batch fetching if available (MUCH faster - single API call)
            if hasattr(provider, 'get_batch_snapshots'):
                snapshots = provider.get_batch_snapshots(symbols)
            else:
                # Fallback to individual fetching (slower)
                snapshots = {}
                for symbol in symbols:
                    snap = provider.get_market_snapshot(symbol)
                    if snap:
                        snapshots[symbol] = snap

            # Process all snapshots
            for symbol in symbols:
                snapshot = snapshots.get(symbol, {})
                current_price = snapshot.get("price", 0)

                # Only include symbols with real data (price > 0)
                if current_price > 0:
                    prev_price = last_prices.get(symbol, current_price)
                    tick_change = current_price - prev_price
                    tick_change_pct = (tick_change / prev_price * 100) if prev_price else 0
                    last_prices[symbol] = current_price

                    # Calculate day change from previous close
                    prev_close = snapshot.get("prev_close", 0)
                    day_change = snapshot.get("change", 0)
                    day_change_pct = snapshot.get("change_pct", 0)

                    # If day_change not provided, calculate from price and prev_close
                    if day_change == 0 and prev_close > 0:
                        day_change = current_price - prev_close
                        day_change_pct = (day_change / prev_close) * 100

                    tickers.append({
                        "symbol": symbol,
                        "price": round(current_price, 2),
                        # Today's open and previous close
                        "open": round(snapshot.get("open", 0), 2),
                        "prev_close": round(prev_close, 2),
                        # Day's range
                        "high": round(snapshot.get("high", 0), 2),
                        "low": round(snapshot.get("low", 0), 2),
                        "vwap": round(snapshot.get("vwap", 0), 2),
                        # Day change (from prev close)
                        "day_change": round(day_change, 2),
                        "day_change_pct": round(day_change_pct, 2),
                        "bid": round(snapshot.get("bid", 0), 2),
                        "ask": round(snapshot.get("ask", 0), 2),
                        "spread": round(snapshot.get("ask", 0) - snapshot.get("bid", 0), 2),
                        # Tick change (from last update)
                        "change": round(tick_change, 2),
                        "change_pct": round(tick_change_pct, 4),
                        "direction": "up" if tick_change > 0 else "down" if tick_change < 0 else "flat",
                        "bid_size": snapshot.get("bid_size", 0),
                        "ask_size": snapshot.get("ask_size", 0),
                        "volume": snapshot.get("volume", 0),
                    })

            # If no real data available, indicate market may be closed
            if not tickers:
                data_source = "unavailable"

            await websocket.send_json({
                "channel": "live-ticker",
                "type": "update",
                "data": tickers,
                "data_source": data_source,
                "symbols_requested": len(symbols),
                "symbols_with_data": len(tickers),
                "timestamp": datetime.utcnow().isoformat(),
            })

            await asyncio.sleep(1.0)  # 1 second between updates (Yahoo has rate limits)
    except WebSocketDisconnect:
        return


@router.websocket("/ws/bot-activity")
async def bot_activity_ws(websocket: WebSocket) -> None:
    """
    Real-time bot activity stream showing autonomous engine decisions.
    Streams: current status, scan results, trade decisions, position updates

    Includes heartbeat mechanism to detect and handle stale connections.
    """
    await websocket.accept()

    await websocket.send_json({
        "channel": "bot-activity",
        "type": "connected",
        "timestamp": datetime.utcnow().isoformat(),
    })

    last_decision_count = 0
    last_scan_time: Optional[str] = None
    heartbeat_counter = 0
    HEARTBEAT_INTERVAL = 50  # Send heartbeat every 50 iterations (25 seconds at 500ms)

    try:
        while True:
            # Check if connection is still alive
            if websocket.client_state != WebSocketState.CONNECTED:
                logger.debug("Bot activity WebSocket client disconnected")
                break

            heartbeat_counter += 1
            engine = _get_autonomous_engine()

            if engine:
                current_scan_time = engine.last_scan_time.isoformat() if engine.last_scan_time else None
                current_decision_count = len(engine.decisions)

                # Build activity update with detailed strategy data for "Under the Hood" visualization
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
                        # Enhanced data for "Under the Hood" visualization
                        "active_strategies": list(engine.all_strategies.keys()) if hasattr(engine, 'all_strategies') else [],
                        "analyzed_opportunities": [
                            {
                                "symbol": opp.get("symbol"),
                                "price": opp.get("last_price", 0),
                                "signals": opp.get("strategy_signals", []),
                                "final_action": opp.get("recommended_action", "HOLD"),
                                "aggregate_confidence": opp.get("confidence", 0),
                                "num_strategies": opp.get("num_strategies", 0),
                                "strategies": opp.get("strategies", []),
                                "reasoning": opp.get("reasoning", ""),
                                "ml_score": opp.get("ml_score", 0),
                                "momentum_score": opp.get("momentum_score", 0),
                                "combined_score": opp.get("combined_score", 0),
                                "relative_volume": opp.get("relative_volume", 0),
                                "atr": opp.get("atr", 0),
                                "pattern": opp.get("pattern"),
                            }
                            for opp in (engine.last_analyzed_opportunities or [])[:20]
                        ],
                        # ALL scanner results (stocks that passed screening)
                        "scanner_results": [
                            {
                                "symbol": r.get("symbol"),
                                "combined_score": r.get("combined_score", 0),
                                "ml_score": r.get("ml_score", 0),
                                "momentum_score": r.get("momentum_score", 0),
                                "price": r.get("last_price", 0),
                                "relative_volume": r.get("relative_volume", 0),
                                "atr": r.get("atr", 0),
                                "atr_percent": r.get("atr_percent", 0),
                                "pattern": r.get("pattern"),
                                "news_catalyst": r.get("news_catalyst"),
                                "float_millions": r.get("float_millions"),
                            }
                            for r in (engine.last_scanner_results or [])[:30]
                        ],
                        # ALL evaluated stocks (including those that failed filters)
                        "all_evaluations": [
                            {
                                "symbol": e.get("symbol"),
                                "passed": e.get("passed", False),
                                "filters": e.get("filters", {}),
                                "scores": e.get("scores", {}),
                                "data": {
                                    "price": e.get("data", {}).get("price", 0),
                                    "volume": e.get("data", {}).get("avg_volume", 0),
                                    "relative_volume": e.get("data", {}).get("relative_volume", 0),
                                }
                            }
                            for e in (engine.all_evaluations or [])[:50]
                        ],
                        "strategy_performance": engine.strategy_performance if hasattr(engine, 'strategy_performance') else {},
                        # Always include filter_summary if available
                        "filter_summary": engine.filter_summary if hasattr(engine, 'filter_summary') else None,
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                }

                # If new scan happened, mark it
                if current_scan_time and current_scan_time != last_scan_time:
                    activity["data"]["new_scan"] = True
                    last_scan_time = current_scan_time

                # If new decisions, send them
                if current_decision_count > last_decision_count:
                    new_decisions = engine.decisions[:current_decision_count - last_decision_count]
                    activity["data"]["new_decisions"] = new_decisions
                    last_decision_count = current_decision_count

                # Add heartbeat flag periodically to help detect stale connections
                if heartbeat_counter >= HEARTBEAT_INTERVAL:
                    activity["heartbeat"] = True
                    heartbeat_counter = 0

                try:
                    await websocket.send_json(activity)
                except Exception as e:
                    logger.debug(f"Failed to send bot activity update: {e}")
                    break
            else:
                try:
                    await websocket.send_json({
                        "channel": "bot-activity",
                        "type": "error",
                        "message": "Autonomous engine not available",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                except Exception as e:
                    logger.debug(f"Failed to send bot activity error: {e}")
                    break

            await asyncio.sleep(0.5)  # 500ms for bot activity updates (balanced for responsiveness vs stability)
    except WebSocketDisconnect:
        logger.debug("Bot activity WebSocket disconnected normally")
    except Exception as e:
        logger.warning(f"Bot activity WebSocket error: {e}")
    finally:
        # Ensure clean disconnect
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close()
        except Exception:
            pass


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
