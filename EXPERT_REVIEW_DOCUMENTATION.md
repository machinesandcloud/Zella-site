# Zella AI Trading Bot - Expert Review Documentation

> **Purpose**: This document provides a comprehensive technical analysis of the Zella AI autonomous trading bot for expert review. The bot has been experiencing consistent losses (approximately $100k -> $93k in one month) and requires professional evaluation to identify and fix the issues.

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Core Components](#2-core-components)
3. [Entry Logic (When/How Trades Are Opened)](#3-entry-logic)
4. [Exit Logic (When/How Trades Are Closed)](#4-exit-logic)
5. [Position Sizing](#5-position-sizing)
6. [Risk Management](#6-risk-management)
7. [Trading Strategies (37 Total)](#7-trading-strategies)
8. [Screening & Filtering Criteria](#8-screening--filtering-criteria)
9. [Configuration Settings](#9-configuration-settings)
10. [Known Issues & Recent Fixes](#10-known-issues--recent-fixes)
11. [Areas of Concern](#11-areas-of-concern)

---

## 1. System Architecture Overview

### Technology Stack
- **Backend**: Python with FastAPI (uvicorn server)
- **Broker**: Alpaca API (Paper/Live trading)
- **Data Feed**: IEX (free tier) or SIP (paid)
- **Database**: PostgreSQL (production) or SQLite (development)
- **Hosting**: Render.com (paid starter plan)

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS ENGINE (core)                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │
│  │   Market    │ │  Strategy   │ │    Risk     │ │  Position  │ │
│  │    Data     │ │   Engine    │ │   Manager   │ │  Manager   │ │
│  │  Provider   │ │ (37 strats) │ │             │ │            │ │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └─────┬──────┘ │
│         │               │               │              │        │
│         └───────────────┴───────────────┴──────────────┘        │
│                              │                                   │
│  ┌───────────────────────────┴────────────────────────────────┐ │
│  │                     ALPACA BROKER                          │ │
│  │  (Order Execution, Position Tracking, Account Info)        │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Main Files

| File | Lines | Purpose |
|------|-------|---------|
| `backend/core/autonomous_engine.py` | ~4100 | Main trading loop, decision making |
| `backend/core/risk_manager.py` | ~120 | Risk checks and position limits |
| `backend/core/elite_trade_system.py` | ~600 | Multi-timeframe analysis, scale-outs |
| `backend/market/alpaca_provider.py` | ~800 | Alpaca API integration |
| `backend/strategies/` | ~7000 | 37 trading strategies |
| `backend/utils/indicators.py` | ~365 | Technical indicators (ATR, VWAP, etc.) |
| `backend/config/settings.py` | ~145 | Configuration management |

---

## 2. Core Components

### 2.1 AutonomousEngine (`autonomous_engine.py`)

The main orchestrator that runs continuously during market hours:

```python
class AutonomousEngine:
    def __init__(self, ...):
        self.scan_interval = 10  # seconds between scans
        self.max_positions = 5   # max concurrent positions
        self.mode = "FULL_AUTO"  # ASSISTED, SEMI_AUTO, FULL_AUTO, GOD_MODE
        self.risk_posture = "BALANCED"  # DEFENSIVE, BALANCED, AGGRESSIVE
```

**Background Tasks Running**:
1. `main_trading_loop` - Scans market, analyzes, executes trades
2. `position_monitor` - Manages open positions (stops, scale-outs)
3. `eod_liquidation_monitor` - Closes all positions at 3:50 PM ET
4. `connection_keepalive` - Maintains broker connection
5. `task_supervisor` - Restarts failed tasks

### 2.2 RiskManager (`risk_manager.py`)

Controls trading risk with these checks:

```python
@dataclass
class RiskConfig:
    max_position_size_percent: float  # Default 10%
    max_daily_loss: float             # Default $500
    max_positions: int                # Default 5
    risk_per_trade_percent: float     # Default 2%
    max_trades_per_day: int           # Default 12
    max_consecutive_losses: int       # Default 3
```

### 2.3 EliteTradingSystem (`elite_trade_system.py`)

Institutional-grade analysis including:
- Multi-timeframe trend analysis (5m, 15m, 1h)
- Relative strength vs SPY
- Support/resistance detection
- Scale-out position management (1R, 2R, 3R levels)

---

## 3. Entry Logic

### 3.1 Trade Entry Flow

```
1. Market Scan (every 10 seconds)
   ↓
2. Screen Universe (~500 symbols)
   - Filter by volume, price, volatility, relative volume
   ↓
3. Strategy Analysis
   - Run all 37 strategies on filtered symbols
   - Each strategy outputs: action, confidence, stop, target
   ↓
4. Signal Aggregation
   - Count strategies agreeing on direction
   - Average confidence scores
   ↓
5. Quality Filters
   - Time-of-day thresholds
   - Minimum confidence checks
   - Minimum strategy agreement
   - High-risk symbol checks
   ↓
6. Risk Checks
   - Max positions limit
   - Max symbol exposure (15%)
   - Daily loss limit
   - Circuit breakers
   ↓
7. Order Execution
   - Calculate position size
   - Place market order via Alpaca
```

### 3.2 Time-of-Day Thresholds

The bot adjusts confidence requirements based on time:

```python
# autonomous_engine.py lines 2971-2978
if mins_open < 120:  # First 2 hours (9:30-11:30) - PRIME TIME
    min_confidence = 0.55 (AGGRESSIVE) / 0.60 (BALANCED) / 0.65 (DEFENSIVE)
    min_strategies = 2

elif mins_open < 270:  # Lunch chop (11:30-2:00)
    min_confidence = 0.65 (AGGRESSIVE) / 0.70 (BALANCED) / 0.75 (DEFENSIVE)
    min_strategies = 2

else:  # Afternoon (2:00-3:45)
    min_confidence = 0.60 (AGGRESSIVE) / 0.65 (BALANCED) / 0.70 (DEFENSIVE)
    min_strategies = 2
```

### 3.3 Entry Requirements Checklist

For a trade to be taken, ALL of these must pass:

| Check | Requirement |
|-------|-------------|
| Risk Manager | `can_trade()` returns True |
| Circuit Breakers | SPY < 3% move, < 5 consecutive losses |
| Time | Not first 5 mins, not last 15 mins |
| Confidence | >= time-of-day threshold |
| Strategies | >= 2 strategies agreeing |
| Symbol Exposure | < 15% of account in symbol |
| Relative Volume | >= 1.0 (1.5 for leveraged ETFs) |
| Not Halted | No LULD halt active |

### 3.4 High-Risk Symbol Handling

Leveraged ETFs require stricter criteria:

```python
HIGH_RISK_SYMBOLS = {
    "SOXS", "SOXL", "TQQQ", "SQQQ", "UVXY", "SVXY", ...
}

if is_high_risk:
    min_confidence += 0.10  # +10% confidence required
    if rvol < 1.5:          # Relative volume must be higher
        skip trade
```

---

## 4. Exit Logic

### 4.1 Exit Types

The bot has multiple exit mechanisms:

| Exit Type | Trigger | Location |
|-----------|---------|----------|
| ATR Take Profit | PnL >= ATR * 3.75 (~5%) | position_monitor |
| ATR Stop Loss | PnL <= -ATR * 1.5 (~-2%) | position_monitor |
| Time Stop | Held > 12 min AND PnL < 0.2% | position_monitor |
| Max Hold | Held > 25 min AND PnL <= 0% | position_monitor |
| Momentum Exit | Below EMA9 AND VWAP | position_monitor |
| Micro Trail | Broke last 3 bar lows | position_monitor |
| Scale-out 1R | Hit 1R target | elite_position_manager |
| Scale-out 2R | Hit 2R target | elite_position_manager |
| Scale-out 3R | Hit 3R target | elite_position_manager |
| Breakeven Stop | After 1R hit | elite_position_manager |
| Trailing Stop | After 2R hit | elite_position_manager |
| EOD Liquidation | 3:50 PM ET | eod_liquidation_monitor |

### 4.2 Scale-Out System (Elite Position Manager)

```python
# Position entered with 100 shares at $10, stop at $9.50
# Risk (R) = $0.50 per share

Scale Levels:
- 1R ($10.50): Sell 50% (50 shares), move stop to breakeven
- 2R ($11.00): Sell 25% (25 shares), activate trailing stop
- 3R ($11.50): Sell remaining 25% (25 shares)
```

### 4.3 Exit Code Locations

Position monitor (`autonomous_engine.py:1598-1812`):
```python
async def _position_monitor(self):
    while self.running:
        for position in positions:
            # Time stop check
            if held_minutes >= self.time_stop_minutes and pnl_percent < 0.2:
                await self._close_position(symbol, "Time stop")

            # Max hold check
            if held_minutes >= self.max_hold_minutes and pnl_percent <= 0:
                await self._close_position(symbol, "Max hold")

            # ATR-based stops/targets
            if pnl_percent >= profit_target:
                await self._close_position(symbol, "Take profit")
            elif pnl_percent <= -stop_target:
                await self._close_position(symbol, "Stop loss")
```

---

## 5. Position Sizing

### 5.1 ATR-Based Position Sizing Formula

```python
# utils/indicators.py lines 290-329
def calculate_position_size_atr(
    account_value: float,
    risk_percent: float,      # e.g., 0.02 = 2%
    entry_price: float,
    atr_value: float,
    atr_multiplier: float = 2.0,
    max_position_pct: float = 0.15  # Max 15% of account
) -> int:

    risk_amount = account_value * risk_percent  # e.g., $100k * 2% = $2,000
    stop_distance = atr_value * atr_multiplier  # e.g., $0.50 ATR * 2 = $1.00

    shares = int(risk_amount / stop_distance)   # e.g., $2,000 / $1.00 = 2000 shares

    # CRITICAL CAP: Never exceed 15% of account
    max_shares = int((account_value * max_position_pct) / entry_price)
    shares = min(shares, max_shares)

    return shares
```

### 5.2 Position Sizing Example

```
Account: $100,000
Risk per trade: 2% ($2,000)
Stock price: $50
ATR: $1.00
ATR multiplier: 2.0
Stop distance: $2.00

Formula calculation:
  shares = $2,000 / $2.00 = 1,000 shares
  position value = 1,000 * $50 = $50,000 (50% of account!)

With 15% cap:
  max_shares = ($100,000 * 0.15) / $50 = 300 shares
  position value = 300 * $50 = $15,000 (15% of account) ✓
```

### 5.3 Symbol Exposure Tracking

```python
# autonomous_engine.py lines 2888-2895
MAX_SYMBOL_EXPOSURE_PCT = 0.15  # Never more than 15% in one symbol

symbol_exposure = {}
for pos in all_positions:
    sym = pos.get("symbol")
    qty = abs(float(pos.get("quantity", 0)))
    price = float(pos.get("currentPrice", 0))
    symbol_exposure[sym] = (qty * price) / account_value

# Skip if already at max exposure
if current_exposure >= MAX_SYMBOL_EXPOSURE_PCT:
    continue  # Don't add to position
```

---

## 6. Risk Management

### 6.1 Risk Configuration Defaults

From `settings.py`:

```python
max_position_size_percent: 10.0   # Max position = 10% of account
max_daily_loss: 500.0             # Stop trading if down $500
max_risk_per_trade: 2.0           # Risk 2% per trade
max_concurrent_positions: 5       # Max 5 open positions
max_trades_per_day: 12            # Max 12 trades per day
max_consecutive_losses: 3         # Pause after 3 losses in a row
```

### 6.2 TradingDisciplineEnforcer

From `elite_trade_system.py`:

```python
self.discipline = TradingDisciplineEnforcer(
    max_consecutive_losses=5,       # Extended pause after 5 losses
    loss_cooldown_minutes=2,        # 2 min cooldown after loss
    max_daily_winners=30,           # Don't cap winners
    daily_loss_limit=1000.0,        # Higher daily loss limit
    profit_protection_threshold=500.0,  # Protect after +$500
    max_drawdown_pct=40.0           # Allow 40% drawdown from peak
)
```

### 6.3 Circuit Breakers

```python
def _check_circuit_breakers(self) -> Tuple[bool, str]:
    # 1. SPY volatility check
    if spy_change_pct > 3.0:
        return False, "Circuit breaker: SPY moved >3%"

    # 2. Consecutive losses
    if consecutive_losses >= 5:
        return False, "Circuit breaker: 5+ consecutive losses"

    # 3. Daily loss limit
    if daily_pnl <= daily_pnl_limit:
        return False, "Circuit breaker: Daily loss limit hit"
```

### 6.4 Market Regime Detection

The bot detects market conditions:

```python
def _detect_market_regime(self) -> str:
    # Returns: TRENDING_UP, TRENDING_DOWN, CHOPPY, EXTREME_VOLATILITY, UNKNOWN

    if day_range_pct > 2.5:
        return "EXTREME_VOLATILITY"  # Don't trade

    if above_vwap and above_open and change_pct > 0.3:
        return "TRENDING_UP"         # Favor longs

    if not above_vwap and change_pct < -0.3:
        return "TRENDING_DOWN"       # Favor shorts

    if vwap_crosses >= 3:
        return "CHOPPY"              # Higher confidence required
```

---

## 7. Trading Strategies

### 7.1 All 37 Strategies

| Category | Strategy | Description |
|----------|----------|-------------|
| **Warrior Trading Core** | BullFlagStrategy | Flagpole + consolidation breakout |
| | ABCDPatternStrategy | A-B-C-D harmonic pattern |
| | FlatTopBreakoutStrategy | Multiple resistance touches breakout |
| | ORBStrategy | Opening Range Breakout (first 15 min) |
| **Trend Following** | BreakoutStrategy | Price breakout above resistance |
| | EMACrossStrategy | EMA crossover signals |
| | HTFEMAMomentumStrategy | Higher timeframe EMA momentum |
| | MomentumStrategy | Rate of change momentum |
| | TrendFollowStrategy | EMA trend following |
| | FirstHourTrendStrategy | First hour trend continuation |
| **Mean Reversion** | PullbackStrategy | Buy dips in uptrends |
| | RangeTradingStrategy | Trade support/resistance range |
| | RSIExhaustionStrategy | RSI overbought/oversold |
| | RSIExtremeReversalStrategy | Extreme RSI reversals |
| | VWAPBounceStrategy | Bounce off VWAP |
| | NineFortyFiveReversalStrategy | 9:45 AM reversal pattern |
| **Scalping** | ScalpingStrategy | Quick in/out trades |
| | RipAndDipStrategy | Trade rips and dips |
| | BigBidScalpStrategy | Large bid scalping |
| **Advanced Patterns** | RetailFakeoutStrategy | Fade retail breakouts |
| | StopHuntReversalStrategy | Stop hunt reversal |
| | BagholderBounceStrategy | Bounce off bagholder capitulation |
| | BrokenParabolicShortStrategy | Short broken parabolics |
| | FakeHaltTrapStrategy | Fake halt trap plays |
| **Institutional** | ClosingBellLiquidityGrabStrategy | EOD liquidity grabs |
| | DarkPoolFootprintsStrategy | Dark pool activity |
| | MarketMakerRefillStrategy | MM refill zones |
| | PremarketVWAPReclaimStrategy | Premarket VWAP reclaim |
| **Options-Based** | OptionsChainSpoofStrategy | Options chain spoofing |
| | GammaSqueezeStrategy | Gamma squeeze plays |
| | MaxPainFadeStrategy | Max pain fade |
| | OpenInterestFakeoutStrategy | OI fakeout |
| **Event-Based** | FOMCFadeStrategy | FOMC announcement fade |
| | EarningsOverreactionStrategy | Earnings overreaction |
| | MergerArbStrategy | Merger arbitrage |
| **Other** | AfterHoursLiquidityTrapStrategy | AH liquidity trap |

### 7.2 Strategy Signal Format

Each strategy outputs:

```python
{
    "action": "BUY" or "SELL",
    "confidence": 0.50 - 0.85,      # Higher = stronger signal
    "reason": "ORB Break: $150.50 > $150.00",
    "stop_loss": 149.50,
    "take_profit": 152.00,
    "indicators": {
        "range_high": 150.00,
        "range_low": 148.00,
        "volume_ratio": 2.5,
        "atr": 1.50
    }
}
```

### 7.3 Example Strategy: ORB (Opening Range Breakout)

```python
# strategies/orb_strategy.py

def generate_signals(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    # Calculate opening range (first 15 min = 3 x 5min bars)
    opening_range = df.iloc[:3]
    range_high = opening_range["high"].max()
    range_low = opening_range["low"].min()

    current_price = df.iloc[-1]["close"]

    # BUY: Price breaks above range high + buffer
    if current_price > range_high + 0.05:
        confidence = 0.50 + breakout_bonus + volume_bonus
        return {
            "action": "BUY",
            "confidence": min(0.85, confidence),
            "stop_loss": range_high - (range_size * 0.3),
            "take_profit": current_price + (range_size * 1.5)
        }
```

### 7.4 Example Strategy: Momentum

```python
# strategies/momentum.py

def generate_signals(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    # Calculate momentum over lookback period
    current_price = df["close"].iloc[-1]
    past_price = df["close"].iloc[-1 - self.momentum_lookback]  # 10 bars
    momentum = ((current_price - past_price) / past_price) * 100

    # BUY: Strong upward momentum >= 1.5%
    if momentum >= 1.5:
        return {
            "action": "BUY",
            "confidence": 0.50 + momentum_bonus + volume_bonus,
            "stop_loss": current_price - (atr * 1.5),
            "take_profit": current_price + (atr * 2.5)
        }
```

---

## 8. Screening & Filtering Criteria

### 8.1 Universe Building

The bot maintains a stock universe of ~500 symbols:

```python
# market/universe.py - Static list including:
# - Major tech: AAPL, MSFT, GOOGL, AMZN, META, NVDA
# - Volatile: TSLA, AMD, COIN, MARA, RIOT
# - ETFs: SPY, QQQ, IWM
# - Leveraged ETFs: TQQQ, SQQQ, SOXL, SOXS

# market/dynamic_universe.py - Adds symbols dynamically based on:
# - Top % gainers/losers
# - Volume spikes
# - News catalysts
```

### 8.2 Screener Settings

From `settings.py`:

```python
screener_min_avg_volume: 200000      # Minimum average volume
screener_min_price: 1.0              # Minimum price $1
screener_max_price: 500.0            # Maximum price $500
screener_min_volatility: 0.002       # Minimum daily volatility
screener_min_relative_volume: 1.5    # Min relative volume (vs 20-day avg)
screener_low_float_max: 20.0         # Low float < 20M shares
screener_mid_float_max: 500.0        # Mid float 20-500M shares
screener_in_play_min_rvol: 2.0       # "In play" relative volume threshold
screener_in_play_gap_percent: 2.0    # "In play" gap threshold
```

### 8.3 Screening Process

```python
# ai/screener.py - MarketScreener class

1. Volume Filter: avg_volume > screener_min_avg_volume
2. Price Filter: screener_min_price < price < screener_max_price
3. Volatility Filter: daily_volatility > screener_min_volatility
4. Relative Volume: current_vol / avg_vol > screener_min_relative_volume
5. Float-Based Adjustments:
   - Low float: Higher RVol required (2.0)
   - Large cap: Lower RVol acceptable (1.2)
6. "In Play" Check:
   - RVol > 2.0 OR
   - Gap > 2% OR
   - News catalyst present
```

### 8.4 Trade Frequency Profiles

```python
trade_frequency_profile = "balanced"  # Options: conservative | balanced | active

"active":
  - RVol threshold: 1.0-1.2
  - Confidence adjustment: -3%
  - Daily trend filter: DISABLED

"balanced":
  - RVol threshold: 1.2-1.4
  - Default confidence thresholds

"conservative":
  - RVol threshold: Higher
  - Confidence adjustment: +5%
  - Min strategies: 3
```

---

## 9. Configuration Settings

### 9.1 Environment Variables (render.yaml)

```yaml
envVars:
  - USE_MOCK_IBKR: "true"         # Using mock IBKR (Alpaca is actual broker)
  - USE_FREE_DATA: "true"         # Using IEX free data tier
  - DEFAULT_TRADING_MODE: PAPER   # Paper trading mode
  - MAX_POSITION_SIZE_PERCENT: 10 # 10% max position
  - MAX_DAILY_LOSS: 500           # $500 daily loss limit
  - MAX_RISK_PER_TRADE: 2         # 2% risk per trade
  - MAX_CONCURRENT_POSITIONS: 5   # 5 max positions
  - SCREENER_MIN_AVG_VOLUME: 100000
  - SCREENER_MIN_PRICE: 1
  - SCREENER_MAX_PRICE: 500
  - SCREENER_MIN_VOLATILITY: 0.002
  - SCREENER_MIN_RELATIVE_VOLUME: 1.0
```

### 9.2 Rate Limiting (Alpaca IEX Free Tier)

```python
# market/alpaca_provider.py
MAX_BACKOFF_SECONDS = 60
INITIAL_BACKOFF_SECONDS = 2
BATCH_SIZE = 25              # Fetch 25 symbols at a time
MIN_REQUEST_INTERVAL = 0.5   # 500ms between requests
```

---

## 10. Known Issues & Recent Fixes

### 10.1 Position Sizing Bug (CRITICAL - FIXED)

**Problem**: Bot was putting 100-270% of account in single positions.

**Root Cause**: `calculate_position_size_atr()` had no upper bound. With low ATR stocks:
- Risk amount: $2,000 (2% of $100k)
- Stop distance: $0.10 (very low ATR)
- Shares: 20,000 ($200,000 position = 200% of account!)

**Fix Applied**:
```python
# Added max_position_pct parameter (default 15%)
max_shares = int((account_value * max_position_pct) / entry_price)
shares = min(shares, max_shares)
```

### 10.2 Rate Limiting Errors (FIXED)

**Problem**: "Too many requests" errors from Alpaca IEX.

**Fix Applied**:
```python
# Reduced request rate:
BATCH_SIZE = 25      # Was 50
MIN_REQUEST_INTERVAL = 0.5  # Was 0.1
scan_interval = 10   # Was 1 second
```

### 10.3 Confidence Thresholds Too Low

**Problem**: Bot was taking low-quality trades (45-55% confidence).

**Partial Fix**: Raised minimum thresholds to 55-75% depending on time of day and risk posture.

### 10.4 Single Strategy Trades

**Problem**: Bot was entering trades with only 1 strategy agreeing.

**Fix Applied**: Now requires minimum 2 strategies to agree.

---

## 11. Areas of Concern

### 11.1 Potential Issues to Investigate

1. **Strategy Quality**: Are the 37 strategies actually profitable? Many seem to have simple logic that may not have edge in real markets.

2. **Confidence Calculation**: Each strategy calculates its own confidence (0.5 base + bonuses). These are then averaged. Is this a valid way to combine signals?

3. **No Backtesting Infrastructure**: There's no evidence of backtesting or strategy validation. Strategies appear to be implemented based on theory without validation.

4. **Execution Quality**: Market orders are used exclusively. No limit orders or execution algorithms.

5. **Slippage Not Accounted**: Position sizing doesn't account for slippage, which can be significant for the stocks being traded.

6. **Time-Based Exits**: The time stop (12 min) and max hold (25 min) may cut winners short or not cut losers fast enough.

7. **Scale-Out System**: The 50%/25%/25% scale-out may reduce profitability by exiting too early on big winners.

8. **Learning Engine**: There's a "learning engine" that adjusts strategy weights, but its effectiveness is unclear.

9. **Edge Engine**: References to "algo detection" and "stealth execution" that may not be implemented.

10. **Data Quality**: Using IEX free tier which has 15-minute delay for some data types and rate limits.

### 11.2 Questions for Expert Review

1. Is the ATR-based position sizing formula correct and appropriate for day trading?

2. Are the 37 strategies too many? Would focusing on 3-5 high-quality strategies be better?

3. Is requiring 2+ strategies to agree a valid signal confirmation method?

4. Should the time-of-day thresholds be more aggressive or conservative?

5. Is the scale-out system (1R, 2R, 3R) appropriate for the types of trades being taken?

6. Are the stop loss levels (1.5x ATR) too tight or too loose?

7. Should different strategies have different position sizing?

8. Is the market regime detection (SPY-based) sufficient?

9. Should there be different approaches for different market conditions?

10. Is 10-second scan interval appropriate, or should it be faster/slower?

### 11.3 Trade History Analysis

From recent logs (sample of losing trades):

| Symbol | Action | Qty | Entry | Exit | PnL | Hold Time | Issue |
|--------|--------|-----|-------|------|-----|-----------|-------|
| SOXS | BUY | 4500 | $33.50 | $33.20 | -$1,350 | 8 min | Leveraged ETF, huge position |
| TQQQ | BUY | 150 | $53.00 | $52.50 | -$75 | 12 min | Time stopped |
| NVDA | BUY | 80 | $125 | $123 | -$160 | 25 min | Max hold exit |

**Patterns Observed**:
- Many trades in leveraged ETFs (SOXS, SOXL, TQQQ)
- Position sizes too large relative to account
- Exits often at time stops rather than price stops

---

## Appendix A: File Structure

```
backend/
├── core/
│   ├── autonomous_engine.py    # Main trading loop
│   ├── risk_manager.py         # Risk checks
│   ├── elite_trade_system.py   # Multi-TF analysis
│   ├── position_manager.py     # Position tracking
│   ├── strategy_engine.py      # Strategy orchestration
│   ├── learning_engine.py      # ML-based learning
│   ├── edge_engine.py          # Competitive edge
│   └── pro_trade_filters.py    # Professional filters
├── strategies/
│   ├── base_strategy.py        # Base class
│   ├── orb_strategy.py         # ORB strategy
│   ├── momentum.py             # Momentum strategy
│   └── ... (35 more strategies)
├── market/
│   ├── alpaca_provider.py      # Alpaca API
│   ├── market_data_provider.py # Data abstraction
│   ├── universe.py             # Static symbol list
│   └── dynamic_universe.py     # Dynamic symbols
├── utils/
│   ├── indicators.py           # Technical indicators
│   └── market_hours.py         # Market hours helpers
├── config/
│   └── settings.py             # Configuration
└── main.py                     # FastAPI app entry
```

---

## Appendix B: Key Code Snippets

### B.1 Main Trading Loop

```python
# autonomous_engine.py:1391-1580 (simplified)
async def _main_trading_loop(self):
    while self.running:
        # 1. Check market hours
        if not is_market_open():
            await asyncio.sleep(60)
            continue

        # 2. Scan market
        opportunities = await self._scan_market()

        # 3. Analyze with strategies
        analyzed = await self._analyze_opportunities(opportunities)

        # 4. Rank by quality
        top_picks = self._rank_opportunities(analyzed)

        # 5. Execute trades
        if not is_past_new_trade_cutoff():
            if self.daily_pnl > self.daily_pnl_limit:
                await self._execute_trades(top_picks)

        # 6. Wait for next scan
        await asyncio.sleep(self.scan_interval)
```

### B.2 Trade Execution

```python
# autonomous_engine.py:2826-3100 (simplified)
async def _execute_trades(self, opportunities):
    for opp in opportunities:
        # Skip if at max positions
        if current_positions >= self.max_positions:
            break

        # Skip if at max exposure for symbol
        if symbol_exposure[symbol] >= 0.15:
            continue

        # Check confidence threshold
        if confidence < min_confidence:
            continue

        # Check strategy agreement
        if num_strategies < min_strategies:
            continue

        # Calculate position size
        shares = calculate_position_size_atr(
            account_value, risk_percent, price, atr_value,
            max_position_pct=0.15
        )

        # Execute order
        self.broker.place_market_order(symbol, shares, action)
```

---

*Document generated for expert review - March 2026*
