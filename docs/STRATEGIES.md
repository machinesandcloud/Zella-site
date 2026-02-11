# Strategy Library

This project includes baseline strategies plus the Reddit strategy list. Many of the Reddit-inspired strategies require enriched data (Level 2, options flow, dark pool prints, or event flags) and are implemented as signal generators that expect those inputs.

## Implemented Strategies

### EMA Cross
- Entry: fast EMA crosses above slow EMA (BUY)
- Exit: fast EMA crosses below slow EMA (SELL)

### VWAP Bounce
- Entry: price crosses above VWAP with volume confirmation
- Exit: price crosses below VWAP

### RSI Exhaustion
- Entry: RSI below oversold threshold (BUY)
- Exit: RSI above overbought threshold (SELL)

### ORB (Opening Range Breakout)
- Entry: price breaks above/below opening range high/low

### Trend Follow
- Entry: EMA trend direction

### Range Trading
- Entry: price near rolling support/resistance with RSI confirmation

### Momentum
- Entry: momentum exceeds threshold

### Breakout
- Entry: price breaks recent high/low with volume spike

### Pullback
- Entry: pullback from recent high in trend direction

### Scalping
- Entry: short-term price movement exceeds tick threshold

### HTF EMA Momentum (Reddit)
- Entry: 1H 100 EMA bias + lower-timeframe momentum in same direction

### First-Hour Trend Lock (Reddit)
- Entry: trade in the direction of the first 30–60 minutes

### Broken Parabolic Short (Reddit)
- Entry: 5+ green candles then first red engulfing candle

### Fake Halt Trap (Reddit)
- Entry: sharp spike without halt; fade the move

### RSI Extreme Reversal (Reddit)
- Entry: RSI >= 90 or <= 10 with reversal candle

### Stop-Hunt Reversal (Reddit)
- Entry: sweep previous day high/low then reverse

### Market Maker Refill (Reddit)
- Entry: volume spike with minimal movement

### Dark Pool Footprints (Reddit)
- Entry: trade near dark pool levels with bias

### 1-min Rip & Dip (Reddit)
- Entry: break premarket high, dip, then reclaim

### Big Bid Scalp (Reddit)
- Entry: large bid appears; buy just in front

### Options Chain Spoof (Reddit)
- Entry: call/put sweeps drive directional signal

### FOMC Fade (Reddit)
- Entry: fade the first large post-FOMC move

### Earnings Overreaction (Reddit)
- Entry: fade extreme first 5-minute earnings move

### Merger Arb Scalp (Reddit)
- Entry: price trades above deal price; short

### Bagholder Bounce (Reddit)
- Entry: large gap down then reversal bounce

### Retail Fakeouts (Reddit)
- Entry: breakdown/reclaim around key levels

### 9:45 AM Reversal (Reddit)
- Entry: reversal around 9:45 after initial move

### Gamma Squeeze Ignition (Reddit)
- Entry: OTM call sweep activity; buy

### Max Pain Friday Fade (Reddit)
- Entry: fade toward max pain on options expiry Friday

### Open Interest Fakeouts (Reddit)
- Entry: heavy OI strike break fails; trade reversal

### Premarket VWAP Reclaim (Reddit)
- Entry: reclaim VWAP with volume premarket

### After-Hours Liquidity Trap (Reddit)
- Entry: after-hours pump with fading volume; fade

### Closing Bell Liquidity Grab (Reddit)
- Entry: late selloff then last-minute rip

## Data Requirements

Some strategies rely on inputs outside standard OHLCV (Level 2, options flow, dark pool data, event flags). These are expected as fields in the market data payload used by the strategy engine.
