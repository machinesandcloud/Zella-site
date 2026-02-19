import pandas as pd
import numpy as np


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average"""
    return series.rolling(window=period).mean()


def vwap(df: pd.DataFrame) -> pd.Series:
    if "price" in df.columns:
        price = df["price"]
    else:
        price = df["close"]
    volume = df["volume"]
    return (price * volume).cumsum() / volume.cumsum()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Average True Range (ATR) - Key indicator for volatility-based stops
    Used by Warrior Trading for dynamic stop losses and position sizing

    True Range = max of:
      - Current High - Current Low
      - abs(Current High - Previous Close)
      - abs(Current Low - Previous Close)
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]

    # Calculate True Range components
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))

    # True Range is the maximum of the three
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # ATR is the smoothed average of True Range
    return true_range.rolling(window=period, min_periods=1).mean()


def atr_stop_loss(df: pd.DataFrame, multiplier: float = 2.0, period: int = 14) -> float:
    """
    Calculate ATR-based stop loss distance
    Warrior Trading recommends 1.5-2x ATR for stop placement
    """
    current_atr = atr(df, period).iloc[-1]
    return current_atr * multiplier


def atr_take_profit(df: pd.DataFrame, multiplier: float = 3.0, period: int = 14) -> float:
    """
    Calculate ATR-based take profit distance
    Typically 1.5-2x the stop loss (2:1 or 3:1 risk/reward)
    """
    current_atr = atr(df, period).iloc[-1]
    return current_atr * multiplier


def is_bull_flag(df: pd.DataFrame, lookback: int = 20, consolidation_bars: int = 5) -> dict:
    """
    Detect Bull Flag pattern - A key Warrior Trading momentum pattern

    Bull Flag = Strong upward move (flagpole) followed by consolidation (flag)

    Criteria:
    1. Flagpole: Strong upward move (>5% in lookback period)
    2. Flag: Tight consolidation with lower highs (pullback <50% of flagpole)
    3. Volume: Decreasing during consolidation
    """
    if len(df) < lookback + consolidation_bars:
        return {"detected": False}

    # Flagpole phase (strong move up)
    pole_start = df.iloc[-(lookback + consolidation_bars)]
    pole_end = df.iloc[-consolidation_bars]
    pole_gain = (pole_end["close"] - pole_start["close"]) / pole_start["close"]

    if pole_gain < 0.05:  # Need at least 5% move for flagpole
        return {"detected": False}

    # Consolidation phase (the flag)
    flag_bars = df.tail(consolidation_bars)
    flag_high = flag_bars["high"].max()
    flag_low = flag_bars["low"].min()
    flag_range = flag_high - flag_low

    # Flag should retrace less than 50% of the pole
    pole_height = pole_end["high"] - pole_start["low"]
    retracement = (pole_end["high"] - flag_low) / pole_height if pole_height > 0 else 1

    if retracement > 0.5:  # Too much retracement
        return {"detected": False}

    # Volume should decrease during consolidation
    pole_volume = df.iloc[-(lookback + consolidation_bars):-consolidation_bars]["volume"].mean()
    flag_volume = flag_bars["volume"].mean()
    volume_declining = flag_volume < pole_volume * 0.7

    # Consolidation should be tight (range < 3% of price)
    tight_consolidation = (flag_range / flag_bars["close"].mean()) < 0.03

    if volume_declining and tight_consolidation:
        return {
            "detected": True,
            "pattern": "BULL_FLAG",
            "breakout_level": flag_high,
            "stop_level": flag_low,
            "pole_gain": pole_gain,
            "confidence": min(0.9, 0.6 + pole_gain)  # Higher pole = higher confidence
        }

    return {"detected": False}


def is_flat_top_breakout(df: pd.DataFrame, lookback: int = 10, tolerance: float = 0.005) -> dict:
    """
    Detect Flat Top Breakout pattern - Key Warrior Trading pattern

    Flat Top = Multiple tests of the same resistance level

    Criteria:
    1. At least 2-3 touches of resistance within tolerance
    2. Strong volume on breakout attempt
    3. Price consolidating just below resistance
    """
    if len(df) < lookback:
        return {"detected": False}

    recent = df.tail(lookback)
    highs = recent["high"].values

    # Find the resistance level (highest high)
    resistance = highs.max()

    # Count touches of resistance (within tolerance)
    touches = sum(1 for h in highs if abs(h - resistance) / resistance <= tolerance)

    if touches < 2:  # Need at least 2 touches
        return {"detected": False}

    # Current price should be near resistance
    current_price = df.iloc[-1]["close"]
    near_resistance = (resistance - current_price) / resistance <= 0.02  # Within 2%

    if not near_resistance:
        return {"detected": False}

    # Volume should be building
    early_volume = recent.head(lookback // 2)["volume"].mean()
    late_volume = recent.tail(lookback // 2)["volume"].mean()
    volume_building = late_volume > early_volume

    if touches >= 2 and near_resistance:
        return {
            "detected": True,
            "pattern": "FLAT_TOP",
            "breakout_level": resistance * 1.002,  # Slight buffer above resistance
            "stop_level": recent["low"].min(),
            "touches": touches,
            "confidence": min(0.9, 0.5 + (touches * 0.15))
        }

    return {"detected": False}


def calculate_position_size_atr(
    account_value: float,
    risk_percent: float,
    entry_price: float,
    atr_value: float,
    atr_multiplier: float = 2.0
) -> int:
    """
    Calculate position size based on ATR stop loss
    Warrior Trading formula: position_size = risk_amount / stop_loss_distance

    Args:
        account_value: Total account value
        risk_percent: Risk per trade (e.g., 0.01 for 1%)
        entry_price: Expected entry price
        atr_value: Current ATR value
        atr_multiplier: Multiplier for ATR stop (default 2x)

    Returns:
        Number of shares to trade
    """
    risk_amount = account_value * risk_percent
    stop_distance = atr_value * atr_multiplier

    if stop_distance <= 0:
        return 0

    shares = int(risk_amount / stop_distance)
    return max(shares, 1)  # At least 1 share


def is_power_hour(hour: int, minute: int = 0) -> bool:
    """
    Check if current time is during power hour (9:30-10:30 AM ET)
    Warrior Trading emphasizes this as the most volatile, profitable hour
    """
    if hour == 9 and minute >= 30:
        return True
    if hour == 10 and minute <= 30:
        return True
    return False


def power_hour_multiplier(hour: int, minute: int = 0) -> float:
    """
    Return signal strength multiplier based on time of day
    Power hour signals get boosted, afternoon signals get reduced
    """
    if hour == 9 and minute >= 30:
        return 1.5  # First 30 mins - highest volatility
    if hour == 10 and minute <= 30:
        return 1.3  # Still power hour
    if hour == 10:
        return 1.1  # Late morning - still good
    if hour == 11:
        return 1.0  # Normal
    if hour >= 12 and hour < 14:
        return 0.8  # Lunch lull - reduce
    if hour >= 14 and hour < 15:
        return 0.9  # Afternoon pickup
    if hour >= 15:
        return 1.1  # Last hour - increased activity
    return 1.0
