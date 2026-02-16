# Zella AI Trading

Zella AI Trading is a day-trading command center that integrates Interactive Brokers (IBKR) with a web-based dashboard. It supports paper trading and live trading (disabled by default) with risk controls, strategy execution, and real-time monitoring.

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Docker (Optional)

```bash
docker-compose up --build
```

## Configuration

Copy the env template and update values:

```bash
cp .env.example .env
```

Frontend env:

```bash
cp frontend/.env.example frontend/.env
```

For QA and local testing without TWS/IB Gateway, enable mock IBKR:

```
USE_MOCK_IBKR=true
```

### IBKR Placeholder Mode

This project defaults to **mock IBKR** so you can run everything without the real API.  
When you are ready to connect to IBKR:

```bash
pip install -r backend/requirements-ibkr.txt
```

Then set `USE_MOCK_IBKR=false` and connect to TWS/IB Gateway.

For headless IB Gateway on a server (DigitalOcean droplet), follow:
`docs/ibkr-droplet-setup.md`

Key settings:
- `IBKR_HOST`, `IBKR_PAPER_PORT`, `IBKR_LIVE_PORT`, `IBKR_CLIENT_ID`
- `DATABASE_URL` (PostgreSQL) and `SQLITE_URL` (local dev)
- `DEFAULT_TRADING_MODE` (PAPER by default)
- Risk limits (max daily loss, max position size, etc.)

## Safety Defaults

- Paper trading is the default trading mode.
- Live trading requires explicit manual toggle via API.
- Risk manager enforces position size, buying power, and max loss constraints.
- Kill switch placeholder is included in the risk manager (extend as needed).

## Multi-Asset Orders

The trading API supports `asset_type` and contract fields (expiry, strike, right, multiplier, exchange) for stocks, options, and futures. See `docs/API.md` for examples.

## Project Structure

```
backend/        FastAPI services, IBKR client wrapper, strategies, risk engine
frontend/       React + TypeScript UI
database/       Schema and migrations
docs/           Research, API docs, strategies, deployment
```

## Data Providers

The AI scanner uses a `MarketDataProvider` interface (`backend/market/`). IBKR is the default, and you can add new providers by implementing the protocol and wiring it in `backend/main.py`.

## Tests

```bash
cd backend
pytest
```

## Next Steps

- Connect TWS/IB Gateway and enable API access; verify `IBKR_*` env values.
- Add premium data feeds (Level 2, options flow, dark pool prints) if you plan to use advanced strategies.
- Harden deployment (secrets manager, TLS, monitoring) before enabling live mode.

## AI Model Training (Optional)

Train a baseline ML model from CSV bars placed in `backend/data/`:

```bash
python3 backend/ai/train_model.py
```
