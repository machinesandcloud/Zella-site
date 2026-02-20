# Zella AI Trading - User Acceptance Criteria (UAC)

## Overview
This document defines the acceptance criteria for all major features of the Zella AI Trading platform. Each criterion must pass before the system can be considered production-ready.

---

## 1. AUTHENTICATION & USER MANAGEMENT

### UAC-AUTH-001: User Auto-Login
| Criteria | Expected Result |
|----------|-----------------|
| System auto-logs in with default admin | JWT token returned, user profile accessible |
| Token expires after 24 hours | Re-authentication required |
| `/api/auth/me` returns user profile | Username, email, account info displayed |

### UAC-AUTH-002: Manual Login
| Criteria | Expected Result |
|----------|-----------------|
| Valid credentials accepted | 200 OK with JWT token |
| Invalid credentials rejected | 401 Unauthorized |
| Missing fields rejected | 422 Validation Error |

---

## 2. BROKER CONNECTIONS

### UAC-BROKER-001: Alpaca Connection
| Criteria | Expected Result |
|----------|-----------------|
| Connect with valid API keys | Status: connected, mode: paper/live |
| Invalid keys rejected | Connection error with message |
| Account balance retrieved | Cash, buying power, equity displayed |
| Positions list populated | All open positions with P&L |

### UAC-BROKER-002: IBKR Connection
| Criteria | Expected Result |
|----------|-----------------|
| Connect to TWS/Gateway | Status: connected |
| Paper/Live mode toggle works | Mode switches correctly |
| Account summary retrieved | Cash, margin, buying power |
| Disconnect graceful | Status: disconnected |

---

## 3. MARKET DATA & WEBSOCKETS

### UAC-WS-001: Live Ticker Feed
| Criteria | Expected Result |
|----------|-----------------|
| WebSocket connects to `/ws/live-ticker` | "subscribed" message received |
| Prices update every 100ms | Continuous price stream |
| Multiple symbols supported | Up to 20 symbols simultaneously |
| Reconnects on disconnect | Auto-reconnect within 3 seconds |

### UAC-WS-002: Bot Activity Feed
| Criteria | Expected Result |
|----------|-----------------|
| WebSocket connects to `/ws/bot-activity` | Connection established |
| Scanner results streamed | `scanner_results` array populated |
| All evaluations visible | `all_evaluations` with pass/fail |
| Filter summary accurate | Counts match actual filtering |

### UAC-WS-003: Market Data Stream
| Criteria | Expected Result |
|----------|-----------------|
| `/ws/market-data?symbols=AAPL,TSLA` | Batch updates received |
| Update interval configurable | 0.1s to 2.0s range |
| Bid/Ask spread accurate | Real market data |
| Volume updates in real-time | Current session volume |

---

## 4. TRADING OPERATIONS

### UAC-TRADE-001: Order Placement
| Criteria | Expected Result |
|----------|-----------------|
| Market order executes | Order filled at market price |
| Limit order creates | Order pending at limit price |
| Stop order creates | Order triggers at stop price |
| Bracket order creates | Entry + TP + SL orders linked |

### UAC-TRADE-002: Order Management
| Criteria | Expected Result |
|----------|-----------------|
| List all orders | Complete order history |
| List open orders only | Pending/working orders |
| Cancel order | Order status: cancelled |
| Modify limit price | Order updated correctly |

### UAC-TRADE-003: Position Management
| Criteria | Expected Result |
|----------|-----------------|
| Positions display correctly | Symbol, qty, avg cost, P&L |
| Close position (market) | Position closed, trade recorded |
| Close position (limit) | Limit sell order created |
| Kill switch stops all | All positions closed, engine stopped |

---

## 5. RISK MANAGEMENT

### UAC-RISK-001: Pre-Trade Validation
| Criteria | Expected Result |
|----------|-----------------|
| Exceeds max position size | Order REJECTED with reason |
| Exceeds daily loss limit | Order REJECTED with reason |
| Exceeds max concurrent positions | Order REJECTED with reason |
| Insufficient buying power | Order REJECTED with reason |

### UAC-RISK-002: Risk Dashboard
| Criteria | Expected Result |
|----------|-----------------|
| Daily P&L displays correctly | Current day's profit/loss |
| Position count accurate | X of Y max positions |
| Exposure metrics shown | Gross, net, by sector |
| Kill switch status visible | ON/OFF indicator |

### UAC-RISK-003: Risk Settings
| Criteria | Expected Result |
|----------|-----------------|
| Update max position size | Setting persists |
| Update daily loss limit | Setting persists |
| Update max positions | Setting persists |
| Settings apply to new trades | Validation uses new values |

---

## 6. AUTONOMOUS TRADING ENGINE

### UAC-AUTO-001: Engine Control
| Criteria | Expected Result |
|----------|-----------------|
| Start engine | Status: running, scanning begins |
| Stop engine | Status: stopped, no new scans |
| Status shows current state | All engine metrics visible |
| Config updates apply | New settings used in next scan |

### UAC-AUTO-002: Market Scanning
| Criteria | Expected Result |
|----------|-----------------|
| Scans 100+ symbols | symbols_scanned > 100 |
| Filters apply correctly | Only qualifying stocks pass |
| Filter summary accurate | Breakdown by filter type |
| Top opportunities ranked | By combined score descending |

### UAC-AUTO-003: Bot Stock Analysis Display
| Criteria | Expected Result |
|----------|-----------------|
| "Leveraged" view shows active | Stocks being traded/analyzed |
| "Passed" view shows qualified | Stocks that passed all filters |
| "All" view shows everything | Complete evaluation pipeline |
| Real-time updates via WebSocket | < 1 second latency |

### UAC-AUTO-004: Auto-Execution (Full Auto Mode)
| Criteria | Expected Result |
|----------|-----------------|
| Trades execute automatically | No manual confirmation needed |
| Risk limits respected | All trades within limits |
| Stop losses set | ATR-based stops on all entries |
| Take profits set | Target based on risk/reward |

---

## 7. STRATEGY ENGINE

### UAC-STRAT-001: Strategy Listing
| Criteria | Expected Result |
|----------|-----------------|
| List all strategies | 25+ strategies visible |
| Each has name & description | Clear strategy purpose |
| Category shown | Trend, Mean Reversion, etc. |
| Active status indicated | Enabled/Disabled state |

### UAC-STRAT-002: Strategy Execution
| Criteria | Expected Result |
|----------|-----------------|
| Generate signals | BUY/SELL/HOLD with confidence |
| Stop loss calculated | Based on ATR or fixed % |
| Take profit calculated | Based on risk/reward ratio |
| Reasoning provided | Clear explanation of signal |

### UAC-STRAT-003: Multi-Strategy Analysis
| Criteria | Expected Result |
|----------|-----------------|
| All strategies run per stock | 37 strategies evaluated |
| Agreement increases confidence | More strategies = higher score |
| Conflicting signals averaged | Weighted by confidence |
| Performance tracked per strategy | Win rate, profit factor |

---

## 8. DASHBOARD & ANALYTICS

### UAC-DASH-001: Account Overview
| Criteria | Expected Result |
|----------|-----------------|
| Account value displays | Total portfolio value |
| Cash balance shown | Available cash |
| Daily P&L calculated | Today's profit/loss |
| Buying power accurate | Available for new trades |

### UAC-DASH-002: Performance Metrics
| Criteria | Expected Result |
|----------|-----------------|
| Win rate calculated | Wins / Total trades |
| Profit factor calculated | Gross profit / Gross loss |
| Average win/loss shown | Mean P&L for each |
| Sharpe ratio components | Risk-adjusted returns |

### UAC-DASH-003: Trade History
| Criteria | Expected Result |
|----------|-----------------|
| Recent trades listed | Last 50 trades |
| P&L per trade shown | Entry, exit, profit/loss |
| Journaling fields work | Notes, tags, catalysts |
| Setup statistics accurate | Win rate by setup type |

---

## 9. ALERTS & NOTIFICATIONS

### UAC-ALERT-001: Alert Generation
| Criteria | Expected Result |
|----------|-----------------|
| Risk alerts trigger | When limits approached |
| Trade alerts trigger | On order fills |
| Strategy alerts trigger | On signal generation |
| System alerts trigger | On errors/warnings |

### UAC-ALERT-002: Alert Management
| Criteria | Expected Result |
|----------|-----------------|
| List alerts | Most recent 50 |
| Acknowledge alerts | Marks as read |
| Settings toggle types | In-app, email, sound |
| Unacknowledged count shown | Badge on notification icon |

---

## 10. UI/UX REQUIREMENTS

### UAC-UI-001: Responsive Design
| Criteria | Expected Result |
|----------|-----------------|
| Desktop (1920x1080) | Full layout, all panels |
| Laptop (1366x768) | Adjusted layout, scrollable |
| Tablet (768px) | Stacked panels |
| Mobile (< 480px) | Single column, navigation |

### UAC-UI-002: Real-Time Updates
| Criteria | Expected Result |
|----------|-----------------|
| Prices flash on change | Green up, red down |
| P&L updates live | No page refresh needed |
| Connection status shown | LIVE/OFF indicator |
| Last update timestamp | Visible on all feeds |

### UAC-UI-003: Error Handling
| Criteria | Expected Result |
|----------|-----------------|
| API errors show toast | User-friendly message |
| WebSocket reconnects | Auto-reconnect with indicator |
| Form validation | Inline error messages |
| Loading states | Spinners/skeletons shown |

---

## 11. SECURITY REQUIREMENTS

### UAC-SEC-001: Authentication Security
| Criteria | Expected Result |
|----------|-----------------|
| Passwords hashed (bcrypt) | Not stored in plain text |
| JWT tokens expire | 24-hour default |
| CORS configured | Only allowed origins |
| Rate limiting | Prevents brute force |

### UAC-SEC-002: Data Protection
| Criteria | Expected Result |
|----------|-----------------|
| API keys encrypted | Not visible in logs |
| Sensitive data masked | Partial display only |
| HTTPS enforced (prod) | No plain HTTP |
| SQL injection prevented | Parameterized queries |

---

## 12. PERFORMANCE REQUIREMENTS

### UAC-PERF-001: Response Times
| Criteria | Expected Result |
|----------|-----------------|
| API responses | < 500ms for 95th percentile |
| WebSocket latency | < 200ms for price updates |
| Page load time | < 3 seconds initial |
| Order execution | < 1 second to broker |

### UAC-PERF-002: Scalability
| Criteria | Expected Result |
|----------|-----------------|
| Concurrent WebSocket connections | 100+ supported |
| Symbols tracked simultaneously | 150+ in scanner |
| Historical data queries | 1000+ trades performant |
| Memory usage stable | No leaks over 24 hours |

---

## TEST EXECUTION CHECKLIST

### Pre-Requisites
- [ ] Backend running on port 8000
- [ ] Frontend running on port 5173 (or deployed)
- [ ] Database initialized
- [ ] Broker credentials configured (or mock mode)
- [ ] Environment variables set

### Critical Path Tests
- [ ] UAC-AUTH-001: Auto-login works
- [ ] UAC-BROKER-001 or 002: Broker connects
- [ ] UAC-WS-001: Live ticker streaming
- [ ] UAC-TRADE-001: Order placement works
- [ ] UAC-RISK-001: Risk validation works
- [ ] UAC-AUTO-001: Engine starts/stops
- [ ] UAC-AUTO-003: Bot analysis displays

### Regression Tests
- [ ] All 12 sections pass
- [ ] No console errors in browser
- [ ] No unhandled exceptions in backend logs
- [ ] WebSocket connections stable for 1 hour

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| QA Engineer | | | |
| Developer | | | |
| Product Owner | | | |

---

*Document Version: 1.0*
*Last Updated: 2026-02-20*
