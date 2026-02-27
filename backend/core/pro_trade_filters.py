"""
Pro-Level Trade Filters for Zella AI Trading

These filters implement techniques used by professional day traders to avoid
common traps and improve trade quality. A retail bot without these filters
is easy prey for market makers and algorithms.

Key principles:
1. Don't trade wide spreads - you're giving away edge
2. Don't trade the open - let chaos settle
3. Don't stack correlated positions - diversify sector exposure
4. Protect profits - don't give back a winning day
5. Adapt to volatility - different markets need different rules
"""

from __future__ import annotations

import logging
from typing import Dict, List, Set, Optional, Any
from datetime import datetime

logger = logging.getLogger("pro_trade_filters")

# Sector mappings for correlation detection
SECTOR_MAP: Dict[str, str] = {
    # Technology / Semiconductors
    "NVDA": "SEMIS", "AMD": "SEMIS", "INTC": "SEMIS", "MU": "SEMIS",
    "AVGO": "SEMIS", "QCOM": "SEMIS", "TSM": "SEMIS", "AMAT": "SEMIS",
    "LRCX": "SEMIS", "KLAC": "SEMIS", "MRVL": "SEMIS", "ON": "SEMIS",
    "SMCI": "SEMIS", "ARM": "SEMIS",

    # Big Tech
    "AAPL": "BIGTECH", "MSFT": "BIGTECH", "GOOGL": "BIGTECH", "GOOG": "BIGTECH",
    "AMZN": "BIGTECH", "META": "BIGTECH", "NFLX": "BIGTECH",

    # EV / Clean Energy
    "TSLA": "EV", "RIVN": "EV", "LCID": "EV", "NIO": "EV", "LI": "EV",
    "XPEV": "EV", "FSR": "EV", "PLUG": "EV", "FCEL": "EV", "BLNK": "EV",
    "CHPT": "EV", "QS": "EV",

    # Financials
    "JPM": "BANKS", "BAC": "BANKS", "WFC": "BANKS", "C": "BANKS",
    "GS": "BANKS", "MS": "BANKS", "SCHW": "BANKS",

    # Biotech / Pharma
    "MRNA": "BIOTECH", "BNTX": "BIOTECH", "PFE": "BIOTECH", "JNJ": "BIOTECH",
    "LLY": "BIOTECH", "ABBV": "BIOTECH", "BMY": "BIOTECH",

    # Energy / Oil
    "XOM": "OIL", "CVX": "OIL", "OXY": "OIL", "SLB": "OIL",
    "COP": "OIL", "DVN": "OIL", "MRO": "OIL",

    # Retail
    "WMT": "RETAIL", "TGT": "RETAIL", "COST": "RETAIL", "HD": "RETAIL",
    "LOW": "RETAIL", "DG": "RETAIL", "DLTR": "RETAIL",

    # Airlines
    "AAL": "AIRLINES", "DAL": "AIRLINES", "UAL": "AIRLINES", "LUV": "AIRLINES",

    # Crypto-related
    "COIN": "CRYPTO", "MARA": "CRYPTO", "RIOT": "CRYPTO", "MSTR": "CRYPTO",

    # Indices / ETFs
    "SPY": "INDEX", "QQQ": "INDEX", "IWM": "INDEX", "DIA": "INDEX",
}


def check_spread_quality(
    bid: float,
    ask: float,
    price: float,
    max_spread_percent: float = 0.15
) -> Dict[str, Any]:
    """
    Check if the bid-ask spread is acceptable for entry.

    PRO TIP: Wide spreads mean you're already losing money the moment you enter.
    Market makers widen spreads on illiquid stocks to trap retail traders.

    Args:
        bid: Current bid price
        ask: Current ask price
        price: Reference price (usually last trade)
        max_spread_percent: Maximum acceptable spread as % of price (default 0.15%)

    Returns:
        Dict with 'acceptable' bool and details
    """
    if bid <= 0 or ask <= 0 or price <= 0:
        return {
            "acceptable": False,
            "reason": "Invalid price data",
            "spread": 0,
            "spread_percent": 0
        }

    spread = ask - bid
    spread_percent = (spread / price) * 100

    # Tighter standards for lower-priced stocks
    if price < 10:
        effective_max = max_spread_percent * 1.5  # Allow slightly wider for penny stocks
    elif price < 50:
        effective_max = max_spread_percent
    else:
        effective_max = max_spread_percent * 0.75  # Tighter for expensive stocks

    acceptable = spread_percent <= effective_max

    return {
        "acceptable": acceptable,
        "spread": round(spread, 4),
        "spread_percent": round(spread_percent, 4),
        "max_allowed": round(effective_max, 4),
        "reason": None if acceptable else f"Spread {spread_percent:.2f}% exceeds max {effective_max:.2f}%"
    }


def check_sector_correlation(
    symbol: str,
    current_positions: List[Dict[str, Any]],
    max_sector_positions: int = 2
) -> Dict[str, Any]:
    """
    Check if adding this position would over-concentrate in one sector.

    PRO TIP: Being long NVDA, AMD, and SMCI isn't 3 positions - it's ONE bet
    on semiconductors with 3x the risk. Diversify or you'll get wiped out
    when the sector turns.

    Args:
        symbol: Symbol to check
        current_positions: List of current position dicts with 'symbol' key
        max_sector_positions: Max positions allowed in same sector

    Returns:
        Dict with 'acceptable' bool and details
    """
    new_sector = SECTOR_MAP.get(symbol, "OTHER")

    # Count positions in same sector
    sector_count = 0
    sector_symbols = []

    for pos in current_positions:
        pos_symbol = pos.get("symbol", "")
        pos_sector = SECTOR_MAP.get(pos_symbol, "OTHER")

        if pos_sector == new_sector and new_sector != "OTHER":
            sector_count += 1
            sector_symbols.append(pos_symbol)

    acceptable = sector_count < max_sector_positions

    return {
        "acceptable": acceptable,
        "sector": new_sector,
        "existing_count": sector_count,
        "existing_symbols": sector_symbols,
        "max_allowed": max_sector_positions,
        "reason": None if acceptable else f"Already have {sector_count} positions in {new_sector}: {sector_symbols}"
    }


def check_profit_protection(
    daily_pnl: float,
    daily_high_pnl: float,
    protection_threshold: float = 300.0,
    drawdown_limit_percent: float = 30.0
) -> Dict[str, Any]:
    """
    Check if we should stop trading to protect profits.

    PRO TIP: The hardest part of trading is keeping your gains. If you're up
    $500 on the day and keep trading until you're flat, you've turned a great
    day into nothing. Protect your profits.

    Args:
        daily_pnl: Current daily P&L
        daily_high_pnl: Highest P&L reached today
        protection_threshold: P&L amount that triggers protection mode
        drawdown_limit_percent: Max drawdown from peak before halting

    Returns:
        Dict with 'should_halt' bool and details
    """
    # Haven't hit protection threshold yet
    if daily_high_pnl < protection_threshold:
        return {
            "should_halt": False,
            "reason": f"Peak P&L ${daily_high_pnl:.2f} below protection threshold ${protection_threshold:.2f}",
            "daily_pnl": daily_pnl,
            "daily_high": daily_high_pnl
        }

    # Calculate drawdown from peak
    drawdown = daily_high_pnl - daily_pnl
    drawdown_percent = (drawdown / daily_high_pnl) * 100 if daily_high_pnl > 0 else 0

    should_halt = drawdown_percent >= drawdown_limit_percent

    return {
        "should_halt": should_halt,
        "daily_pnl": round(daily_pnl, 2),
        "daily_high": round(daily_high_pnl, 2),
        "drawdown": round(drawdown, 2),
        "drawdown_percent": round(drawdown_percent, 2),
        "limit_percent": drawdown_limit_percent,
        "reason": f"Drawdown {drawdown_percent:.1f}% from peak exceeds {drawdown_limit_percent}% limit" if should_halt else None
    }


def check_volatility_regime(
    vix_level: float,
    atr_percent: float
) -> Dict[str, Any]:
    """
    Determine market volatility regime and adjust parameters.

    PRO TIP: The same stop loss that works in a calm market will get you
    stopped out constantly in high volatility. Adapt your parameters.

    Args:
        vix_level: Current VIX level (or 0 if unavailable)
        atr_percent: Stock's ATR as percentage of price

    Returns:
        Dict with regime and recommended adjustments
    """
    # Determine regime based on VIX
    if vix_level > 30:
        regime = "HIGH_VOLATILITY"
        position_size_mult = 0.5  # Half size
        stop_mult = 1.5  # Wider stops
        min_confidence = 0.80  # Higher bar for entry
    elif vix_level > 20:
        regime = "ELEVATED"
        position_size_mult = 0.75
        stop_mult = 1.25
        min_confidence = 0.75
    elif vix_level > 0:
        regime = "NORMAL"
        position_size_mult = 1.0
        stop_mult = 1.0
        min_confidence = 0.70
    else:
        # VIX not available, use ATR
        if atr_percent > 5:
            regime = "HIGH_VOLATILITY"
            position_size_mult = 0.5
            stop_mult = 1.5
            min_confidence = 0.80
        elif atr_percent > 3:
            regime = "ELEVATED"
            position_size_mult = 0.75
            stop_mult = 1.25
            min_confidence = 0.75
        else:
            regime = "NORMAL"
            position_size_mult = 1.0
            stop_mult = 1.0
            min_confidence = 0.70

    return {
        "regime": regime,
        "vix_level": vix_level,
        "atr_percent": round(atr_percent, 2),
        "position_size_multiplier": position_size_mult,
        "stop_loss_multiplier": stop_mult,
        "min_confidence_required": min_confidence
    }


def check_volume_quality(
    current_volume: int,
    avg_volume: int,
    min_relative_volume: float = 0.5,
    min_absolute_volume: int = 100000
) -> Dict[str, Any]:
    """
    Check if volume is sufficient for clean entry/exit.

    PRO TIP: Low volume = wide spreads, slippage, and trapped positions.
    Never trade a stock that doesn't have enough liquidity to exit quickly.

    Args:
        current_volume: Current session volume
        avg_volume: Average daily volume
        min_relative_volume: Minimum ratio of current to average
        min_absolute_volume: Minimum absolute volume required

    Returns:
        Dict with 'acceptable' bool and details
    """
    if avg_volume <= 0:
        return {
            "acceptable": False,
            "reason": "No average volume data",
            "relative_volume": 0
        }

    relative_volume = current_volume / avg_volume if avg_volume > 0 else 0

    volume_ok = current_volume >= min_absolute_volume
    relative_ok = relative_volume >= min_relative_volume

    acceptable = volume_ok and relative_ok

    reasons = []
    if not volume_ok:
        reasons.append(f"Volume {current_volume:,} below minimum {min_absolute_volume:,}")
    if not relative_ok:
        reasons.append(f"Relative volume {relative_volume:.2f}x below minimum {min_relative_volume}x")

    return {
        "acceptable": acceptable,
        "current_volume": current_volume,
        "avg_volume": avg_volume,
        "relative_volume": round(relative_volume, 2),
        "reason": "; ".join(reasons) if reasons else None
    }


class ProTradeValidator:
    """
    Comprehensive trade validator combining all pro-level filters.
    Use this before every trade entry.
    """

    def __init__(
        self,
        max_spread_percent: float = 0.15,
        max_sector_positions: int = 2,
        profit_protection_threshold: float = 300.0,
        drawdown_limit_percent: float = 30.0
    ):
        self.max_spread_percent = max_spread_percent
        self.max_sector_positions = max_sector_positions
        self.profit_protection_threshold = profit_protection_threshold
        self.drawdown_limit_percent = drawdown_limit_percent

        # Track daily high for profit protection
        self.daily_high_pnl = 0.0
        self.last_reset_date: Optional[str] = None

    def reset_daily(self):
        """Reset daily tracking at start of new day."""
        today = datetime.now().strftime("%Y-%m-%d")
        if self.last_reset_date != today:
            self.daily_high_pnl = 0.0
            self.last_reset_date = today
            logger.info("Pro validator daily tracking reset")

    def update_daily_high(self, current_pnl: float):
        """Update daily high P&L for profit protection."""
        if current_pnl > self.daily_high_pnl:
            self.daily_high_pnl = current_pnl
            logger.info(f"New daily P&L high: ${self.daily_high_pnl:.2f}")

    def validate_trade(
        self,
        symbol: str,
        bid: float,
        ask: float,
        price: float,
        current_volume: int,
        avg_volume: int,
        atr_percent: float,
        current_positions: List[Dict[str, Any]],
        daily_pnl: float,
        vix_level: float = 0,
        minutes_since_open: int = 60
    ) -> Dict[str, Any]:
        """
        Run all pro-level validations on a potential trade.

        Returns:
            Dict with 'approved' bool, 'rejections' list, and 'adjustments' dict
        """
        self.reset_daily()
        self.update_daily_high(daily_pnl)

        rejections = []
        warnings = []
        adjustments = {}

        # 1. Check opening range
        if minutes_since_open < 15:
            rejections.append(f"Opening range: Only {minutes_since_open} min since open, wait until 9:45 AM")

        # 2. Check spread
        spread_check = check_spread_quality(bid, ask, price, self.max_spread_percent)
        if not spread_check["acceptable"]:
            rejections.append(f"Spread: {spread_check['reason']}")

        # 3. Check volume
        volume_check = check_volume_quality(current_volume, avg_volume)
        if not volume_check["acceptable"]:
            rejections.append(f"Volume: {volume_check['reason']}")

        # 4. Check sector correlation
        correlation_check = check_sector_correlation(symbol, current_positions, self.max_sector_positions)
        if not correlation_check["acceptable"]:
            rejections.append(f"Correlation: {correlation_check['reason']}")

        # 5. Check profit protection
        profit_check = check_profit_protection(
            daily_pnl, self.daily_high_pnl,
            self.profit_protection_threshold, self.drawdown_limit_percent
        )
        if profit_check["should_halt"]:
            rejections.append(f"Profit protection: {profit_check['reason']}")

        # 6. Check volatility regime (for adjustments, not rejection)
        vol_check = check_volatility_regime(vix_level, atr_percent)
        adjustments["position_size_multiplier"] = vol_check["position_size_multiplier"]
        adjustments["stop_loss_multiplier"] = vol_check["stop_loss_multiplier"]
        adjustments["min_confidence"] = vol_check["min_confidence_required"]
        adjustments["volatility_regime"] = vol_check["regime"]

        if vol_check["regime"] == "HIGH_VOLATILITY":
            warnings.append(f"High volatility detected - reducing size 50%, widening stops")

        approved = len(rejections) == 0

        return {
            "approved": approved,
            "symbol": symbol,
            "rejections": rejections,
            "warnings": warnings,
            "adjustments": adjustments,
            "checks": {
                "spread": spread_check,
                "volume": volume_check,
                "correlation": correlation_check,
                "profit_protection": profit_check,
                "volatility": vol_check
            }
        }
