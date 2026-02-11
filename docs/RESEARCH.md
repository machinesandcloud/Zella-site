# Research Notes - Zella AI Trading

This document summarizes core research sources and translates them into implementation notes for the trading system.

## Sources Consulted
- Sarwa: How to Begin Day Trading (principles, risk, testing) - https://www.sarwa.co/blog/how-to-begin-day-trading/
- Sarwa: Successful Day Trading Strategies (9 strategies) - https://www.sarwa.co/blog/successful-day-trading-strategies/
- IBKR TWS API Intro - https://interactivebrokers.github.io/tws-api/introduction.html
- IBKR TWS API Initial Setup - https://interactivebrokers.github.io/tws-api/initial_setup.html
- IBKR Campus TWS API Doc Hub (minimum Python version, requirements) - https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/
- Investor.gov: Types of Orders (market, limit, stop) - https://www.investor.gov/introduction-investing/investing-basics/how-stock-markets-work/types-orders
- Britannica Money: VWAP - https://www.britannica.com/money/volume-weighted-average-price
- Britannica Money: SMA vs EMA - https://www.britannica.com/money/simple-vs-exponential-moving-averages
- Wikipedia: RSI - https://en.wikipedia.org/wiki/Relative_strength_index
- Britannica Money: Price Action Trading - https://www.britannica.com/money/price-action-trading-explained
- Wikipedia: Order Flow Trading - https://en.wikipedia.org/wiki/Order_flow_trading
- Wikipedia: Backtesting - https://en.wikipedia.org/wiki/Backtesting
- Investopedia: Technical Analysis learning (backtesting + overfitting mentions) - https://www.investopedia.com/trading/best-ways-learn-technical-analysis/
- TradingMetrics: Position sizing formula examples - https://docs.tradingmetrics.com/en/technical-analysis/risk-management/position-sizing

---

## A. Day Trading Fundamentals

### Sarwa - How to Begin Day Trading (Key Principles)
1) Stock selection: prioritize liquidity (high volume), volatility (intraday movement), and responsiveness to news.
2) Have a clear strategy with defined entry, exit, and stop rules.
3) Test strategies using paper trading or small-size live trading; ensure wins outweigh losses and payoff is positive.
4) Risk management: Sarwa highlights the 3-5-7 rule (limit risk per trade, limit sector exposure, maintain positive risk-reward).
5) Always set target profit and stop loss levels to avoid greed and cap losses.
6) Emotional discipline: avoid fear/greed and stick to the plan; pause if strategy degrades.

### Sarwa - Successful Day Trading Strategies (9 Strategies)
1) Trend trading: trade in direction of clear trend; use trend confirmation (higher highs/lows or moving averages).
2) Range trading: buy support, sell resistance; use oscillators (e.g., RSI) for overbought/oversold confirmation.
3) Momentum trading: enter when momentum is strong; exit when momentum weakens (RSI/ADX/MACD are common tools).
4) Breakout trading: trade after support/resistance breaks; confirm with price action to avoid false breakouts.
5) Pullback trading: a trend-following variant; enter on temporary retracements within a trend.
6) Gap trading: trade price gaps at market open after news or strong moves.
7) Price action trading: read price behavior with minimal indicators; use support/resistance and pattern recognition.
8) Scalping: very short-term trades; high frequency, small gains per trade, often requires automation.
9) News trading: trade around earnings or macro news; higher risk due to surprise outcomes.

### Technical Indicators (Implementation Notes)
- SMA vs EMA: SMAs smooth price data equally across the period; EMAs weight recent prices more heavily, reacting faster to changes. Use EMA for responsive trend detection and SMA for smoothing longer-term trend direction.
- VWAP: calculated as cumulative (price * volume) / cumulative volume for the session; often used as an intraday fair-value reference and dynamic support/resistance.
- RSI: a momentum oscillator (0-100); common thresholds are 70 (overbought) and 30 (oversold), but should be adapted to the strategy.

### Price Action Trading (Implementation Notes)
- Price action focuses on reading raw price movement, trend structure, and key levels without heavy indicator reliance.
- Use price action signals for entry/exit confirmation around support, resistance, and trendlines.

### Order Flow Analysis (Implementation Notes)
- Order flow focuses on how executed trades and order-book dynamics reflect buyer/seller pressure.
- Can be used to identify imbalances, absorption, or exhaustion near key price levels.

### Risk Management & Position Sizing
- Use defined stop loss and take profit levels; stop orders become market orders when the stop price is reached.
- Position sizing formula (risk-based): Position Size = Risk per Trade / Stop Loss Distance.
- Sarwa highlights limiting risk per trade and maintaining a positive risk-reward ratio; the system should enforce risk limits at order time.

---

## B. IBKR API Documentation (Key Capabilities)

### Core Notes
- TWS API connects to Trader Workstation (TWS) or IB Gateway; one must be running for the API to connect.
- Headless operation is not supported; GUI login is required for authentication.
- TWS API can request market data and monitor account balance and portfolio in real time.
- Default socket ports: 7496 (live) and 7497 (paper), configurable in TWS API settings.
- Read-only mode can be enabled to block order placement; it is enabled by default for safety.
- IBKR provides paper trading accounts for testing strategies in simulated conditions.
- IBKR Campus docs list minimum supported Python version (3.11+) and API/TWS version alignment guidance.
- TWS has a client message rate limit (50 messages per second).

### Capability Mapping to Trading Strategies
- Real-time data + historical data: drive indicator calculations (EMA/VWAP/RSI), price action, and order flow signals.
- Order types: market, limit, stop, bracket orders enable disciplined entry/exit risk control.
- Account endpoints: enforce buying power checks and risk constraints before trades.
- Callbacks/events: handle fills, order status, market data, and disconnects.

---

## C. Algorithmic Trading Best Practices

### Backtesting & Validation
- Backtesting simulates strategy performance on historical data; it is limited by data quality and overfitting risks.
- Avoid look-ahead bias and over-optimization; consider walk-forward testing and out-of-sample validation.

### Risk Management Systems
- Enforce position sizing, max daily loss, max open positions, and emergency kill switch.
- Validate each signal against current risk constraints before placing orders.

### Error Handling & Fail-Safes
- Retry/auto-reconnect for IBKR connection drops.
- Circuit breakers when data feed is stale or latency spikes.
- Persist audit logs for orders, strategy decisions, and configuration changes.

### Logging & Monitoring
- Structured logs for orders, fills, errors, and strategy actions.
- KPIs: win rate, average win/loss, drawdown, Sharpe ratio, and profit factor.

---

## D. Reddit Strategy Document (El1teM1ndset thread)

Note: The Reddit post is a curated list of ideas. It explicitly states the author does not know all strategies work. These are treated as hypotheses that require backtesting and risk controls.

### 1) Ride the trend
- **HTF EMA bias + LTF momentum**: Use 100 EMA on 1H for bias; trade 1m/5m with momentum in that direction.  
  **Implementation**: `HTFEMAMomentumStrategy` expects `htf_df` (1H) and `df` (LTF) data.
- **VWAP bounce (smart way)**: Wait for wick + high volume + no follow-through near VWAP before entry.  
  **Implementation**: `VWAPBounceStrategy` uses VWAP, volume spike, and wick check.
- **First-hour trend lock**: Direction of first 30–60 minutes defines the trend for the session.  
  **Implementation**: `FirstHourTrendStrategy` expects `first_hour_df` or `session_open/close`.

### 2) Mean reversion (buy panic, sell euphoria)
- **Broken parabolic short**: After 5+ green 1m candles, first red engulfing triggers a short.  
  **Implementation**: `BrokenParabolicShortStrategy` checks consecutive greens + engulfing.
- **Fake halt trap**: Spike without an actual halt, then short.  
  **Implementation**: `FakeHaltTrapStrategy` expects `halted` flag and spike %.
- **RSI extreme reversal**: RSI > 90 or < 10, then first reversal candle.  
  **Implementation**: `RSIExtremeReversalStrategy` uses RSI + reversal candle.

### 3) Liquidity traps
- **Stop-loss hunting reversal**: Sweep previous day high/low then reverse.  
  **Implementation**: `StopHuntReversalStrategy` expects `prev_day_high/low`.
- **Market maker refill zones**: Volume spike with minimal movement implies absorption.  
  **Implementation**: `MarketMakerRefillStrategy` checks volume spike + tight range.
- **Dark pool footprints**: Dark pool buying/selling signals an incoming move.  
  **Implementation**: `DarkPoolFootprintsStrategy` expects `dark_pool_levels` and `dark_pool_bias`.

### 4) Scalping
- **1-min rip & dip**: Break premarket high, dip, then reclaim.  
  **Implementation**: `RipAndDipStrategy` expects `premarket_high`.
- **Big bid scalping**: Large hidden bid on Level 2; scalp bounce.  
  **Implementation**: `BigBidScalpStrategy` expects `bid_size`, `bid_price`, `last_price`.
- **Options chain spoofing**: Large call/put sweeps hint at direction.  
  **Implementation**: `OptionsChainSpoofStrategy` expects `options_flow` flags.

### 5) Trade the reaction, not the news
- **FOMC fade**: Fade the first big post-FOMC move.  
  **Implementation**: `FOMCFadeStrategy` expects `event=\"FOMC\"` and `initial_move_pct`.
- **Earnings overreaction reversal**: Fade extreme initial move.  
  **Implementation**: `EarningsOverreactionStrategy` expects `event=\"EARNINGS\"` and `first_move_pct`.
- **Merger arb scalp**: If price trades above deal price, short.  
  **Implementation**: `MergerArbStrategy` expects `deal_price` and `last_price`.

### 6) Psychological warfare
- **Bagholder bounce**: Gap down 20%+, flush, then bounce.  
  **Implementation**: `BagholderBounceStrategy` expects `gap_pct` and reversal candle.
- **Retail fakeouts**: Fake breakdown/reclaim around key levels.  
  **Implementation**: `RetailFakeoutStrategy` expects `support_level`/`resistance_level`.
- **9:45 AM reversal**: Initial retail move reverses around 9:45.  
  **Implementation**: `NineFortyFiveReversalStrategy` expects `timestamp` + `early_move`.

### 7) Options data
- **Gamma squeeze ignition**: OTM call sweep activity signals hedging.  
  **Implementation**: `GammaSqueezeStrategy` expects `options_flow`.
- **Max pain Friday fade**: Price gravitates toward max pain on expiry.  
  **Implementation**: `MaxPainFadeStrategy` expects `max_pain_price`, `last_price`, `timestamp`.
- **Open interest fakeouts**: Break of heavy OI then failure.  
  **Implementation**: `OpenInterestFakeoutStrategy` expects `oi_break`, `failed_break`, `break_direction`.

### 8) After-hours & premarket plays
- **Premarket VWAP reclaim**: Dip under VWAP premarket then reclaim on volume.  
  **Implementation**: `PremarketVWAPReclaimStrategy` expects `premarket_df`.
- **After-hours liquidity trap**: After-hours pump with fading volume; fade it.  
  **Implementation**: `AfterHoursLiquidityTrapStrategy` expects `after_hours`, `price_spike_pct`, `volume_drop`.
- **Closing bell liquidity grab**: Late selloff then last-minute rip.  
  **Implementation**: `ClosingBellLiquidityGrabStrategy` expects `time_to_close_minutes` and recent candles.

### Data Feeds & Practical Notes
- Many setups require Level 2 data, options flow, dark pool prints, or event flags not provided by IBKR alone.  
- These strategies are implemented as signal generators that expect enriched inputs from external data providers or custom preprocessing.

---

## E. System Architecture Decisions (Initial)

- Backend: FastAPI + IBKR TWS API (ibapi) with a strategy engine, risk manager, and order manager.
- Data: PostgreSQL for production trade history; SQLite for local development.
- Task Queue: Celery + Redis for asynchronous order management and scheduled tasks.
- Frontend: React + TypeScript with real-time updates via WebSockets.
- Safety: paper trading default; explicit confirmation for live mode; kill switch for immediate shutdown.
