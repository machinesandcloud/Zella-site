# Render Environment Variables

All environment variables configured in the Render dashboard for the Zella AI backend service.
Dashboard values override `render.yaml` — this file is the source of truth.

Last updated: 2026-04-08

---

## Authentication & Security

| Key | Value | Notes |
|-----|-------|-------|
| `SECRET_KEY` | `[secret]` | JWT signing key — must be strong random string in prod |
| `ADMIN_USERNAME` | `[secret]` | Dashboard admin login |
| `ADMIN_EMAIL` | `[secret]` | Dashboard admin email |
| `ADMIN_PASSWORD` | `[secret]` | Dashboard admin password |
| `AUTO_LOGIN_ENABLED` | `true` | Auto-login on dashboard open |
| `JWT_ALGORITHM` | `HS256` | |
| `JWT_EXPIRATION_HOURS` | `24` | |

---

## Database

| Key | Value | Notes |
|-----|-------|-------|
| `DATABASE_URL` | `[secret]` | Injected by Render from `zella-ai-db` PostgreSQL instance |
| `USE_SQLITE` | `false` | Always use Postgres in prod |

---

## Trading Broker (Alpaca)

| Key | Value | Notes |
|-----|-------|-------|
| `ALPACA_API_KEY` | `[secret]` | Alpaca paper/live API key |
| `ALPACA_SECRET_KEY` | `[secret]` | Alpaca paper/live secret |
| `ALPACA_PAPER` | `true` | `true` = paper trading, `false` = live money |
| `USE_ALPACA` | `true` | Enable Alpaca broker |
| `USE_FREE_DATA` | `false` | Use Alpaca data, not Yahoo fallback |
| `USE_MOCK_IBKR` | `false` | No mock broker |

---

## Trading Mode & Risk

| Key | Value | Notes |
|-----|-------|-------|
| `DEFAULT_TRADING_MODE` | `PAPER` | PAPER or LIVE |
| `MAX_DAILY_LOSS` | `2000` | Max daily drawdown in dollars before halt |
| `MAX_RISK_PER_TRADE` | `1.0` | Max risk per trade as % of account |
| `MAX_POSITION_SIZE_PERCENT` | `5.0` | Max single position as % of account |
| `MAX_CONCURRENT_POSITIONS` | `3` | Max open positions at once |
| `MIN_CONFIDENCE_THRESHOLD` | `0.70` | Global minimum signal confidence (70%) |
| `ENABLED_STRATEGY_MODE` | `PROVEN_ONLY` | Only run the 5 validated strategies |

---

## Screener — Volume (IEX-scale)

> Alpaca IEX feed reports ~0.3% of real exchange volume.
> AAPL's real 60M daily volume appears as ~200k on IEX.
> These thresholds are calibrated for IEX, not full SIP data.

| Key | Value | Notes |
|-----|-------|-------|
| `SCREENER_MIN_AVG_VOLUME` | `15000` | Floor for unknown/unlisted float |
| `SCREENER_MIN_AVG_VOLUME_LOW_FLOAT` | `10000` | Low float (<20M shares) |
| `SCREENER_MIN_AVG_VOLUME_MID_FLOAT` | `20000` | Mid float (20M–500M shares) |
| `SCREENER_MIN_AVG_VOLUME_LARGE_FLOAT` | `50000` | Large float (>500M) / ETFs |

---

## Screener — Relative Volume

| Key | Value | Notes |
|-----|-------|-------|
| `SCREENER_MIN_RELATIVE_VOLUME` | `1.5` | Default minimum relative volume |
| `SCREENER_MIN_RELATIVE_VOLUME_LOW_FLOAT` | `2.0` | Low float needs stronger confirmation |
| `SCREENER_MIN_RELATIVE_VOLUME_MID_FLOAT` | `1.5` | Mid float |
| `SCREENER_MIN_RELATIVE_VOLUME_LARGE_FLOAT` | `1.2` | Large caps move on lower relative vol |

---

## Screener — Price & Volatility

| Key | Value | Notes |
|-----|-------|-------|
| `SCREENER_MIN_PRICE` | `1` | Minimum stock price (blocks sub-$1 penny stocks) |
| `SCREENER_MAX_PRICE` | `500` | Maximum stock price |
| `SCREENER_MIN_VOLATILITY` | `0.2` | Minimum ATR% (changed from 0.002 std-dev units to 0.2%) |

---

## CORS

| Key | Value | Notes |
|-----|-------|-------|
| `CORS_ALLOWED_ORIGINS` | `https://zella-site.netlify.app,http://localhost:3000` | Frontend origins |

---

## Change Log

| Date | Key | Old Value | New Value | Reason |
|------|-----|-----------|-----------|--------|
| 2026-04-08 | `SCREENER_MIN_AVG_VOLUME` | `500000` | `15000` | Calibrate for Alpaca IEX feed (real vol × 0.003) |
| 2026-04-08 | `SCREENER_MIN_VOLATILITY` | `0.002` | `0.2` | Switch from std-dev units to ATR% — std-dev was near-zero pre-market |
| 2026-04-08 | `SCREENER_MIN_PRICE` | `5` | `1` | Was blocking $1–$5 stocks (BB, SNAP, etc.) |
| 2026-04-08 | `SCREENER_MIN_AVG_VOLUME_LOW_FLOAT` | _(not set)_ | `10000` | Added per-float-bucket thresholds |
| 2026-04-08 | `SCREENER_MIN_AVG_VOLUME_MID_FLOAT` | _(not set)_ | `20000` | Added per-float-bucket thresholds |
| 2026-04-08 | `SCREENER_MIN_AVG_VOLUME_LARGE_FLOAT` | _(not set)_ | `50000` | Added per-float-bucket thresholds |
| 2026-04-08 | `SCREENER_MIN_RELATIVE_VOLUME` | `1.0` | `1.5` | Was letting low-vol stocks through screener only to fail ProValidator |
| 2026-04-08 | `SCREENER_MIN_RELATIVE_VOLUME_LOW_FLOAT` | _(not set)_ | `2.0` | Added per-float-bucket rvol thresholds |
| 2026-04-08 | `SCREENER_MIN_RELATIVE_VOLUME_MID_FLOAT` | _(not set)_ | `1.5` | Added per-float-bucket rvol thresholds |
| 2026-04-08 | `SCREENER_MIN_RELATIVE_VOLUME_LARGE_FLOAT` | _(not set)_ | `1.2` | Added per-float-bucket rvol thresholds |
| 2026-04-08 | `MIN_CONFIDENCE_THRESHOLD` | _(not set)_ | `0.70` | Explicit override to match settings.py |
| 2026-04-08 | `ENABLED_STRATEGY_MODE` | _(not set)_ | `PROVEN_ONLY` | Explicit override — only 5 validated strategies |
