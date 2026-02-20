import asyncio
from datetime import datetime
from typing import Dict, List, Set, Any, Optional
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from market.fake_stream import DEFAULT_SYMBOLS, FakeMarketDataStream

router = APIRouter()
logger = logging.getLogger("websocket_market_data")

FAKE_STREAM = FakeMarketDataStream(DEFAULT_SYMBOLS)

# Heartbeat interval in seconds - must be less than Render's 55s idle timeout
HEARTBEAT_INTERVAL = 30


class ConnectionManager:
    """
    Manages WebSocket connections with heartbeat support.
    Prevents connection drops due to idle timeouts.
    """

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.symbol_subscriptions: Dict[WebSocket, Set[str]] = {}
        self._heartbeat_tasks: Dict[WebSocket, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, channel: str) -> bool:
        """Connect and start heartbeat. Returns True if successful."""
        try:
            await websocket.accept()
            if channel not in self.active_connections:
                self.active_connections[channel] = set()
            self.active_connections[channel].add(websocket)
            self.symbol_subscriptions[websocket] = set()

            # Start heartbeat task for this connection
            self._heartbeat_tasks[websocket] = asyncio.create_task(
                self._heartbeat(websocket, channel)
            )
            logger.info(f"WebSocket connected to channel: {channel}")
            return True
        except Exception as e:
            logger.error(f"Failed to accept WebSocket connection: {e}")
            return False

    async def _heartbeat(self, websocket: WebSocket, channel: str):
        """Send periodic pings to keep connection alive."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                if websocket.client_state == WebSocketState.CONNECTED:
                    try:
                        # Send ping frame (WebSocket protocol level)
                        await websocket.send_json({
                            "type": "ping",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    except Exception as e:
                        logger.warning(f"Heartbeat failed for {channel}: {e}")
                        break
                else:
                    break
        except asyncio.CancelledError:
            pass  # Task cancelled during shutdown

    def disconnect(self, websocket: WebSocket, channel: str):
        """Clean up connection and cancel heartbeat."""
        # Cancel heartbeat task
        if websocket in self._heartbeat_tasks:
            self._heartbeat_tasks[websocket].cancel()
            del self._heartbeat_tasks[websocket]

        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
        if websocket in self.symbol_subscriptions:
            del self.symbol_subscriptions[websocket]
        logger.info(f"WebSocket disconnected from channel: {channel}")

    def subscribe_symbols(self, websocket: WebSocket, symbols: List[str]):
        if websocket in self.symbol_subscriptions:
            self.symbol_subscriptions[websocket].update(symbols)

    async def broadcast(self, channel: str, message: dict):
        if channel in self.active_connections:
            disconnected = []
            for connection in list(self.active_connections[channel]):
                try:
                    if connection.client_state == WebSocketState.CONNECTED:
                        await connection.send_json(message)
                    else:
                        disconnected.append(connection)
                except Exception as e:
                    logger.warning(f"Broadcast failed, removing client from {channel}: {e}")
                    disconnected.append(connection)

            # Clean up disconnected clients
            for conn in disconnected:
                self.disconnect(conn, channel)

    async def shutdown(self):
        """Gracefully close all connections."""
        logger.info("Shutting down WebSocket connections...")
        for channel, connections in list(self.active_connections.items()):
            for conn in list(connections):
                try:
                    await conn.close(code=1001, reason="Server shutting down")
                except Exception as e:
                    logger.debug(f"Error closing connection: {e}")
                self.disconnect(conn, channel)
        logger.info("All WebSocket connections closed")


manager = ConnectionManager()


def _get_market_provider():
    from main import app
    return app.state.market_data_provider


def _get_autonomous_engine():
    from main import app
    return getattr(app.state, "autonomous_engine", None)


async def _send_with_heartbeat(websocket: WebSocket, message: dict, channel: str):
    """Send message with automatic heartbeat management."""
    try:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(message)
            return True
    except Exception as e:
        logger.error(f"Send failed on {channel}: {e}")
    return False


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

    channel = "market-data"
    if not await manager.connect(websocket, channel):
        return

    last_heartbeat = datetime.utcnow()
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
                "channel": channel,
                "type": "batch",
                "data": batch,
                "symbols_requested": len(symbols),
                "symbols_with_data": len(batch),
                "timestamp": datetime.utcnow().isoformat(),
            }

            if not await _send_with_heartbeat(websocket, message, channel):
                break

            await asyncio.sleep(interval)
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from {channel}")
    except Exception as e:
        logger.error(f"Error in {channel} WebSocket: {e}")
    finally:
        manager.disconnect(websocket, channel)


@router.websocket("/ws/live-ticker")
async def live_ticker_ws(websocket: WebSocket) -> None:
    """
    High-frequency live ticker feed for day trading.
    Streams real-time prices at 1s intervals for selected symbols.
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

    channel = "live-ticker"
    if not await manager.connect(websocket, channel):
        return

    # Send initial subscription confirmation
    await websocket.send_json({
        "channel": channel,
        "type": "subscribed",
        "symbols": symbols,
        "interval_ms": 1000,
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

            message = {
                "channel": channel,
                "type": "update",
                "data": tickers,
                "data_source": data_source,
                "symbols_requested": len(symbols),
                "symbols_with_data": len(tickers),
                "timestamp": datetime.utcnow().isoformat(),
            }

            if not await _send_with_heartbeat(websocket, message, channel):
                break

            await asyncio.sleep(1.0)  # 1 second between updates (Yahoo has rate limits)
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from {channel}")
    except Exception as e:
        logger.error(f"Error in {channel} WebSocket: {e}")
    finally:
        manager.disconnect(websocket, channel)


@router.websocket("/ws/bot-activity")
async def bot_activity_ws(websocket: WebSocket) -> None:
    """
    Real-time bot activity stream showing autonomous engine decisions.
    Streams: current status, scan results, trade decisions, position updates
    """
    channel = "bot-activity"
    if not await manager.connect(websocket, channel):
        return

    await websocket.send_json({
        "channel": channel,
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

                # Build activity update with detailed strategy data for "Under the Hood" visualization
                activity = {
                    "channel": channel,
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

                if not await _send_with_heartbeat(websocket, activity, channel):
                    break
            else:
                message = {
                    "channel": channel,
                    "type": "error",
                    "message": "Autonomous engine not available",
                    "timestamp": datetime.utcnow().isoformat(),
                }
                if not await _send_with_heartbeat(websocket, message, channel):
                    break

            await asyncio.sleep(0.5)  # 500ms for bot activity updates (reduced from 100ms)
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from {channel}")
    except Exception as e:
        logger.error(f"Error in {channel} WebSocket: {e}")
    finally:
        manager.disconnect(websocket, channel)


@router.websocket("/ws/orders")
async def orders_ws(websocket: WebSocket) -> None:
    channel = "orders"
    if not await manager.connect(websocket, channel):
        return
    try:
        while True:
            message = {
                "channel": channel,
                "timestamp": datetime.utcnow().isoformat(),
            }
            if not await _send_with_heartbeat(websocket, message, channel):
                break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from {channel}")
    except Exception as e:
        logger.error(f"Error in {channel} WebSocket: {e}")
    finally:
        manager.disconnect(websocket, channel)


@router.websocket("/ws/account-updates")
async def account_updates_ws(websocket: WebSocket) -> None:
    channel = "account-updates"
    if not await manager.connect(websocket, channel):
        return
    try:
        while True:
            message = {
                "channel": channel,
                "timestamp": datetime.utcnow().isoformat(),
            }
            if not await _send_with_heartbeat(websocket, message, channel):
                break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from {channel}")
    except Exception as e:
        logger.error(f"Error in {channel} WebSocket: {e}")
    finally:
        manager.disconnect(websocket, channel)


@router.websocket("/ws/order-book")
async def order_book_ws(websocket: WebSocket) -> None:
    symbol = (websocket.query_params.get("symbol") or "AAPL").upper()
    channel = "order-book"
    if not await manager.connect(websocket, channel):
        return
    try:
        while True:
            message = {
                "channel": channel,
                "symbol": symbol,
                "status": "UNAVAILABLE",
                "reason": "Free data source does not provide Level 2 order book",
                "timestamp": datetime.utcnow().isoformat(),
                "bids": [],
                "asks": [],
                "mid": None,
                "spread": None,
            }
            if not await _send_with_heartbeat(websocket, message, channel):
                break
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from {channel}")
    except Exception as e:
        logger.error(f"Error in {channel} WebSocket: {e}")
    finally:
        manager.disconnect(websocket, channel)


@router.websocket("/ws/time-sales")
async def time_sales_ws(websocket: WebSocket) -> None:
    symbol = (websocket.query_params.get("symbol") or "AAPL").upper()
    channel = "time-sales"
    if not await manager.connect(websocket, channel):
        return
    try:
        while True:
            message = {
                "channel": channel,
                "symbol": symbol,
                "status": "UNAVAILABLE",
                "reason": "Free data source does not provide time & sales tape",
                "timestamp": datetime.utcnow().isoformat(),
                "price": None,
                "size": None,
                "side": None,
            }
            if not await _send_with_heartbeat(websocket, message, channel):
                break
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from {channel}")
    except Exception as e:
        logger.error(f"Error in {channel} WebSocket: {e}")
    finally:
        manager.disconnect(websocket, channel)


# Health check endpoint for WebSocket connections
@router.websocket("/ws/health")
async def health_ws(websocket: WebSocket) -> None:
    """WebSocket health check - responds to pings immediately."""
    channel = "health"
    if not await manager.connect(websocket, channel):
        return
    try:
        while True:
            # Wait for client message (ping)
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=60)
                if data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            except asyncio.TimeoutError:
                # Send keepalive ping if no message received
                await websocket.send_json({
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                })
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from {channel}")
    except Exception as e:
        logger.error(f"Error in {channel} WebSocket: {e}")
    finally:
        manager.disconnect(websocket, channel)
