# Zella AI Trading - QA Issues Report

**Date:** 2026-02-20
**QA Engineer:** Claude (AI-assisted)
**Status:** Pre-Production Review

---

## Executive Summary

The Zella AI Trading platform has been reviewed for production readiness. **1 critical bug was found and fixed**, and **several additional issues** were identified that should be addressed before going live with real customer money.

---

## BUGS FIXED IN THIS SESSION

### BUG-001: WebSocket Message Format Mismatch (CRITICAL - FIXED)

**File:** `frontend/src/components/AI/BotStockAnalysisLive.tsx`

**Problem:** The frontend was expecting `message.type === "bot_activity"` and `message.activity`, but the backend sends `message.type === "status"` and `message.data`.

**Impact:** The new Bot Stock Analysis component would never receive any data - completely broken functionality.

**Fix Applied:**
```typescript
// Before (broken):
if (message.type === "bot_activity" && message.activity) {

// After (fixed):
if (message.type === "status" && message.data) {
```

**Status:** ✅ FIXED

---

## ISSUES REQUIRING ATTENTION

### CRITICAL PRIORITY (Must fix before production)

#### ISSUE-001: Hardcoded Default Credentials
**Files:** `backend/config/settings.py`
- Line 12: Database URL with `user:password` placeholder
- Line 18: JWT secret key = `"your-secret-key-here"`
- Line 26: Admin password = `"zella-auto-login-2024"`

**Risk:** If `.env` file is missing or incomplete, system runs with insecure defaults.

**Recommendation:** Add startup validation that fails if security-critical values are defaults.

---

#### ISSUE-002: Silent Exception Handling
**Files:** Multiple files across codebase

| File | Line | Impact |
|------|------|--------|
| `api/routes/news.py` | 53 | Empty list returned on any error |
| `api/websocket/market_data.py` | 43 | Client disconnects unlogged |
| `core/ibkr_webapi.py` | 34, 62 | Connection errors hidden |
| `core/autonomous_engine.py` | 321, 544, 727 | Trading calculations fail silently |

**Risk:** Debugging becomes impossible when errors are swallowed without logging.

**Recommendation:** Add `logger.exception(e)` to all exception handlers.

---

### HIGH PRIORITY (Should fix before production)

#### ISSUE-003: No Error Handling in Order Execution
**File:** `backend/api/routes/trading.py` (Lines 95-231)
**File:** `backend/core/autonomous_engine.py` (Lines 682-793)

**Problem:** Broker calls are made without try-catch. If broker disconnects mid-trade, exception propagates as 500 error.

**Risk:** Customer sees cryptic error message, trade status unknown.

**Recommendation:** Wrap all broker operations in try-catch with proper error responses.

---

#### ISSUE-004: Order Result Not Validated
**File:** `backend/core/autonomous_engine.py` (Line 764)

**Problem:** After `broker.place_market_order()`, code assumes success without checking response.

**Risk:** Failed orders may be recorded as successful trades.

**Recommendation:** Validate order response before recording trade.

---

#### ISSUE-005: WebSocket Double Accept
**File:** `backend/api/websocket/market_data.py`

**Problem:** `websocket.accept()` called twice (once in `ConnectionManager.connect()` and again in route handler).

**Lines Affected:** 86, 140, 225, 357, 380

**Risk:** Potential protocol violation, may cause issues with some clients.

**Recommendation:** Remove duplicate `accept()` calls.

---

### MEDIUM PRIORITY (Should fix in next sprint)

#### ISSUE-006: Position Monitor Race Condition
**File:** `backend/core/autonomous_engine.py` (Lines 299-373)

**Problem:** Position iteration without locking. Position data could change between read and action.

**Risk:** Stale data used for stop-loss calculations.

**Recommendation:** Add mutex/lock around position operations.

---

#### ISSUE-007: No WebSocket Heartbeat
**File:** `backend/api/websocket/market_data.py`

**Problem:** No ping/pong mechanism to detect dead connections early.

**Risk:** Stale connections accumulate, wasting resources.

**Recommendation:** Implement heartbeat every 30 seconds.

---

#### ISSUE-008: Hardcoded Test Data in Production Endpoints
**File:** `backend/api/routes/news.py` (Lines 18-42)

**Problem:** `news_feed()` returns hardcoded mock data instead of real news.

**Risk:** Users see fake data without realizing it.

**Recommendation:** Either fetch real data or clearly mark as demo mode.

---

### LOW PRIORITY (Nice to have)

#### ISSUE-009: Console Print Statements
**File:** `backend/ai/train_model.py`

**Problem:** Uses `print()` instead of logger.

**Recommendation:** Replace with proper logging.

---

#### ISSUE-010: No Graceful WebSocket Shutdown
**File:** `backend/api/websocket/market_data.py`

**Problem:** `ConnectionManager` has no shutdown method. Clients not notified on server shutdown.

**Recommendation:** Add shutdown notification to connected clients.

---

## TEST COVERAGE GAPS

### Missing Tests
1. WebSocket connection/disconnection scenarios
2. Order execution error paths
3. Position monitor stop-loss triggers
4. Multi-broker failover
5. Rate limiting validation
6. JWT token expiration handling

### Existing Test Files
- `test_uat_flow.py` - Basic smoke test ✅
- `test_strategies.py` - Strategy execution ✅
- `test_risk_manager.py` - Risk validation ✅
- `test_alerts_risk.py` - Alert management ✅
- `test_ibkr_client.py` - Minimal coverage ⚠️
- `test_ai_screener.py` - Basic coverage ⚠️

---

## ENVIRONMENT CHECKLIST

Before production deployment, ensure:

- [ ] `.env` file created from `.env.example`
- [ ] `SECRET_KEY` changed to secure random value
- [ ] `ADMIN_PASSWORD` changed from default
- [ ] `DATABASE_URL` points to production database
- [ ] `USE_MOCK_IBKR=false` for real trading
- [ ] `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` set
- [ ] `ALPACA_PAPER=false` for live trading (when ready)
- [ ] SSL certificates configured
- [ ] CORS origins limited to production domains
- [ ] Rate limiting enabled
- [ ] Logging to persistent storage

---

## RECOMMENDATIONS FOR GO-LIVE

### Phase 1: Critical Fixes (Before any real money)
1. Fix all CRITICAL issues
2. Fix all HIGH priority issues
3. Add comprehensive error logging
4. Validate order execution results

### Phase 2: Stability (Before public launch)
1. Fix MEDIUM priority issues
2. Add WebSocket heartbeat
3. Implement proper shutdown handling
4. Add missing test coverage

### Phase 3: Polish (Post-launch improvements)
1. Fix LOW priority issues
2. Add monitoring/alerting
3. Performance optimization
4. Documentation updates

---

## SIGN-OFF

| Check | Status |
|-------|--------|
| UAC Document Created | ✅ |
| Critical Bug Fixed | ✅ |
| Issues Documented | ✅ |
| Recommendations Provided | ✅ |

---

*Report generated by QA review on 2026-02-20*
