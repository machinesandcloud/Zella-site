# UAT Results - Zella AI Trading

Date: 2026-02-11  
Environment: Local backend tests with `USE_MOCK_IBKR=true` and SQLite  
Test Harness: `pytest backend/tests`

## Summary
- Automated UAT coverage for core API flows completed using FastAPI TestClient and mock IBKR.
- Backend unit/integration tests: **PASS** (9 tests).
- Frontend build check: **NOT RUN** (npm not available in this environment).

## Checklist Results

### Auth
- [x] Register new user (automated test)
- [x] Login and receive token (automated test)
- [x] Auth-protected endpoints reject unauthenticated requests (automated test)

### IBKR Connectivity
- [x] Connect to IBKR paper account (mock, automated test)
- [x] Verify status reflects connected mode (mock, automated test)
- [x] Toggle live mode requires confirmation flag (automated test)
- [x] Disconnect works (mock, automated test)

### Trading
- [x] Place market order (paper, mock, automated test)
- [x] Place limit order (paper, mock, automated test)
- [x] Place stop order (paper, mock, automated test)
- [x] Place bracket order (paper, mock, automated test)
- [x] Cancel order (mock, automated test)
- [x] Modify order (mock, automated test)

### Risk Controls
- [x] Max daily loss enforced (unit test)
- [x] Max positions enforced (unit test)
- [x] Max position size enforced (unit test)
- [x] Kill switch cancels orders and closes positions (mock, automated test)

### Strategy Management
- [x] List available strategies (automated test)
- [x] Start/stop strategy (automated test)
- [x] Strategy performance endpoint responds (automated test)

### Dashboard
- [x] Account summary visible (automated test)
- [x] Active positions visible (automated test)
- [x] Recent trades visible (automated test)
- [x] Metrics visible (automated test)

### AI Market Scan
- [x] Scan returns ranked symbols (automated test)
- [x] Top picks returns subset (automated test)
- [x] Model unavailable still returns safely (automated test)
- [x] Auto-trade endpoint blocked without confirm flag (automated test)
- [x] Auto-trade only allowed in paper mode (automated test)

## Notes / Gaps
- UI verification (dashboard visuals, chart rendering, button flows) requires a manual run of the frontend; `npm` is not available in the current environment, so build/run checks were not executed.
- Live IBKR connectivity was not tested; run UAT against TWS/IB Gateway before enabling live mode.
