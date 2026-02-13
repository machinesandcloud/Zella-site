import asyncio
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from market.fake_stream import DEFAULT_SYMBOLS, FakeMarketDataStream

router = APIRouter()

FAKE_STREAM = FakeMarketDataStream(DEFAULT_SYMBOLS)

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
            ticks = FAKE_STREAM.ticks(symbols)
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
            payload = FAKE_STREAM.order_book(symbol)
            message = {"channel": "order-book", **payload}
            await websocket.send_json(message)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return


@router.websocket("/ws/time-sales")
async def time_sales_ws(websocket: WebSocket) -> None:
    symbol = (websocket.query_params.get("symbol") or "AAPL").upper()
    await websocket.accept()
    try:
        while True:
            payload = FAKE_STREAM.time_sales(symbol)
            message = {"channel": "time-sales", **payload}
            await websocket.send_json(message)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return
