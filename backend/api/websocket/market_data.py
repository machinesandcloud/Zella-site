import asyncio
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from market.fake_stream import DEFAULT_SYMBOLS, FakeMarketDataStream

router = APIRouter()

FAKE_STREAM = FakeMarketDataStream(DEFAULT_SYMBOLS)


def _get_market_provider():
    from main import app

    return app.state.market_data_provider


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
    symbols_param = websocket.query_params.get("symbol") or websocket.query_params.get("symbols")
    if symbols_param:
        symbols = [item.strip().upper() for item in symbols_param.split(",") if item.strip()]
    else:
        symbols = DEFAULT_SYMBOLS
    await websocket.accept()
    try:
        while True:
            provider = _get_market_provider()
            for symbol in symbols:
                snapshot = provider.get_market_snapshot(symbol) or {}
                if snapshot:
                    message = {
                        "channel": "market-data",
                        "symbol": symbol,
                        "price": snapshot.get("price", 0),
                        "volume": snapshot.get("volume", 0),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    await websocket.send_json(message)
                else:
                    ticks = FAKE_STREAM.ticks([symbol])
                    for tick in ticks:
                        message = {"channel": "market-data", **tick}
                        await websocket.send_json(message)
            await asyncio.sleep(1)
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
