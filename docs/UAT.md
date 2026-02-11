# User Acceptance Testing (UAT)

## Scope
All core workflows: authentication, IBKR connectivity, trading actions, risk controls, strategy management, dashboard visibility, AI market scan, and kill switch.

## Environment
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
 - Optional: set `USE_MOCK_IBKR=true` for QA without IBKR TWS/Gateway

## Acceptance Checklist

### Auth
- [ ] Register new user
- [ ] Login and receive token
- [ ] Auth-protected endpoints reject unauthenticated requests

### IBKR Connectivity
- [ ] Connect to IBKR paper account
- [ ] Verify status reflects connected mode
- [ ] Toggle live mode requires confirmation flag
- [ ] Disconnect works

### Trading
- [ ] Place market order (paper)
- [ ] Place limit order (paper)
- [ ] Place stop order (paper)
- [ ] Place bracket order (paper)
- [ ] Cancel order
- [ ] Modify order

### Risk Controls
- [ ] Max daily loss enforced
- [ ] Max positions enforced
- [ ] Max position size enforced
- [ ] Kill switch cancels orders and closes positions

### Strategy Management
- [ ] List available strategies
- [ ] Start/stop strategy
- [ ] Strategy performance endpoint responds

### Dashboard
- [ ] Account summary visible
- [ ] Active positions visible
- [ ] Recent trades visible
- [ ] Metrics visible

### AI Market Scan
- [ ] Scan returns ranked symbols
- [ ] Top picks returns subset
- [ ] Model unavailable still returns safely (score defaults to 0)
- [ ] Auto-trade endpoint blocked without confirm flag
- [ ] Auto-trade only allowed in paper mode

## Notes
- Most Reddit strategies require enriched data (Level 2, options flow, dark pool prints, event flags). Without these, they will no-op safely.
