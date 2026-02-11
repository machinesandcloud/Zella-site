# API Documentation

Base URL: `http://localhost:8000`

Most endpoints require a Bearer token from `/api/auth/login`.

## Authentication
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

## IBKR Connection
- `POST /api/ibkr/connect`
- `POST /api/ibkr/disconnect`
- `GET /api/ibkr/status`
- `PUT /api/ibkr/toggle-mode` (query params: `enable_paper`, `confirm_live`)

Note: When `USE_MOCK_IBKR=true`, these endpoints operate on the placeholder client (no real IBKR connection required).

## Account
- `GET /api/account/summary`
- `GET /api/account/positions`
- `GET /api/account/history`

## Trading
- `POST /api/trading/order`
- `DELETE /api/trading/order/{order_id}`
- `PUT /api/trading/order/{order_id}`
- `GET /api/trading/orders`
- `GET /api/trading/orders/open`
- `POST /api/trading/kill-switch`

## Strategies
- `GET /api/strategies`
- `GET /api/strategies/{id}`
- `POST /api/strategies/{id}/start`
- `POST /api/strategies/{id}/stop`
- `PUT /api/strategies/{id}/config`
- `GET /api/strategies/{id}/performance`

## Dashboard
- `GET /api/dashboard/overview`
- `GET /api/dashboard/metrics`
- `GET /api/dashboard/trades/recent`

## WebSocket
- `WS /ws/market-data`
- `WS /ws/orders`
- `WS /ws/account-updates`

Market data supports an optional query param:
- `/ws/market-data?symbol=AAPL` (or `symbols=AAPL,MSFT`)

Message shape:
```json
{
  "channel": "market-data",
  "symbol": "AAPL",
  "price": 123.45,
  "volume": 5000,
  "timestamp": "2026-02-11T18:10:00Z"
}
```

## QA
- `GET /api/qa/health`

## AI / Market Scan
- `GET /api/ai/scan`
- `GET /api/ai/top?limit=5`
- `POST /api/ai/auto-trade?limit=5&execute=true&confirm_execute=true`

## Example: Place Order

```json
POST /api/trading/order
{
  "symbol": "AAPL",
  "action": "BUY",
  "quantity": 10,
  "order_type": "MKT",
  "asset_type": "STK",
  "exchange": "SMART",
  "currency": "USD"
}
```
