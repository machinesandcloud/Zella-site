"""
Enhanced Market Screener - Warrior Trading Aligned

Implements the key stock selection criteria from Warrior Trading:
1. Float under 100M shares (low float = high volatility)
2. High relative volume (2x+ average)
3. News catalyst detection
4. Power hour weighting (9:30-10:30 AM boost)
5. ATR-based volatility analysis
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import logging

import pandas as pd

from ai.feature_engineering import latest_feature_vector
from ai.ml_model import MLSignalModel
from utils.indicators import atr, power_hour_multiplier, is_bull_flag, is_flat_top_breakout, is_abcd_pattern, sma
from utils.market_hours import market_session

logger = logging.getLogger("market_screener")


# Low float stocks database (in millions of shares)
# These are stocks known for low float and high volatility
# Updated 2024 - removed delisted stocks, added current momentum plays
# In production, this should be fetched from a data provider dynamically
LOW_FLOAT_STOCKS = {
    # Popular day trading stocks with known low float
    "GME": 75, "AMC": 85, "BB": 40, "CLOV": 35,
    "WKHS": 25, "RIDE": 30, "SPCE": 50, "OPEN": 60,
    # Biotech (often low float, high volatility)
    "MRNA": 95, "BNTX": 35, "NVAX": 45, "VXRT": 30, "INO": 40,
    "SAVA": 35, "AGEN": 30, "APLS": 45, "CRSP": 40, "EDIT": 35,
    # EV & Clean Energy (popular momentum plays)
    "RIVN": 90, "LCID": 85, "NIO": 80, "XPEV": 60, "LI": 70,
    "FFIE": 20, "MULN": 15, "GOEV": 25, "FSR": 30, "BLNK": 35,
    # Tech SPACs & Recent IPOs
    "IONQ": 25, "RKLB": 30, "JOBY": 35, "LILM": 25, "ASTS": 30,
    # Cannabis
    "TLRY": 65, "CGC": 55, "SNDL": 80, "ACB": 45,
    # Crypto-related
    "COIN": 85, "MARA": 50, "RIOT": 45, "CLSK": 35, "MSTR": 40,
    "HUT": 30, "BITF": 25, "CORZ": 20,
    # AI & Tech momentum plays
    "PLTR": 80, "AI": 50, "SOUN": 25, "BBAI": 20, "UPST": 45,
    "PATH": 40, "S": 35, "CFLT": 30,
    # High volume large caps (higher float but very liquid)
    "AAPL": 500, "MSFT": 400, "NVDA": 350, "TSLA": 300, "AMZN": 450,
    "AMD": 200, "META": 380, "GOOGL": 420, "NFLX": 200, "GOOG": 420,
}


class MarketScreener:
    """
    Enhanced Market Screener implementing Warrior Trading stock selection criteria

    Warrior Trading Key Criteria:
    - Float < 100M shares for momentum/penny plays
    - Relative Volume >= 2x average
    - Breaking news catalyst
    - Strong daily chart (above key MAs)
    - High ATR for volatility
    """

    def __init__(
        self,
        model: MLSignalModel,
        min_avg_volume: float = 100000,  # Lowered for pre-market/early trading
        min_price: float = 1.0,  # Allow penny stocks
        max_price: float = 500.0,  # Focus on tradeable range
        min_volatility: float = 0.002,  # Lower volatility threshold
        min_relative_volume: float = 1.0,  # Allow stocks at normal volume
        min_avg_volume_low_float: Optional[float] = None,
        min_avg_volume_mid_float: Optional[float] = None,
        min_avg_volume_large_float: Optional[float] = None,
        min_relative_volume_low_float: Optional[float] = None,
        min_relative_volume_mid_float: Optional[float] = None,
        min_relative_volume_large_float: Optional[float] = None,
        min_premarket_volume: float = 50000,  # Require some premarket liquidity for gappers
        max_float_millions: float = 100.0,  # Warrior Trading: float < 100M
        low_float_max: float = 20.0,
        mid_float_max: float = 500.0,
        in_play_min_rvol: float = 2.0,
        in_play_gap_percent: float = 2.0,
        in_play_volume_multiplier: float = 0.5,
        enable_float_filter: bool = True,
        enable_pattern_detection: bool = True,
        enable_power_hour_boost: bool = True,
        require_premarket_volume: bool = True,
        require_daily_trend: bool = True,
    ) -> None:
        self.model = model
        self.min_avg_volume = min_avg_volume
        self.min_price = min_price
        self.max_price = max_price
        self.min_volatility = min_volatility
        self.min_relative_volume = min_relative_volume
        self.min_avg_volume_low_float = min_avg_volume_low_float if min_avg_volume_low_float is not None else min_avg_volume
        self.min_avg_volume_mid_float = min_avg_volume_mid_float if min_avg_volume_mid_float is not None else min_avg_volume
        self.min_avg_volume_large_float = min_avg_volume_large_float if min_avg_volume_large_float is not None else min_avg_volume
        self.min_relative_volume_low_float = (
            min_relative_volume_low_float if min_relative_volume_low_float is not None else min_relative_volume
        )
        self.min_relative_volume_mid_float = (
            min_relative_volume_mid_float if min_relative_volume_mid_float is not None else min_relative_volume
        )
        self.min_relative_volume_large_float = (
            min_relative_volume_large_float if min_relative_volume_large_float is not None else min_relative_volume
        )
        self.min_premarket_volume = min_premarket_volume
        self.max_float_millions = max_float_millions
        self.low_float_max = low_float_max
        self.mid_float_max = mid_float_max
        self.in_play_min_rvol = in_play_min_rvol
        self.in_play_gap_percent = in_play_gap_percent
        self.in_play_volume_multiplier = in_play_volume_multiplier
        self.enable_float_filter = enable_float_filter
        self.enable_pattern_detection = enable_pattern_detection
        self.enable_power_hour_boost = enable_power_hour_boost
        self.require_premarket_volume = require_premarket_volume
        self.require_daily_trend = require_daily_trend

        # News catalyst cache (populated externally)
        self.news_catalysts: Dict[str, Dict] = {}
        self.short_interest: Dict[str, Dict[str, float]] = {}
        self._load_short_interest()

    def set_news_catalysts(self, catalysts: Dict[str, Dict]) -> None:
        """Update news catalyst data for symbols"""
        self.news_catalysts = catalysts

    def _load_short_interest(self) -> None:
        """Load short interest data from data/short_interest.json if present."""
        try:
            from pathlib import Path
            import json

            data_file = Path("data/short_interest.json")
            if data_file.exists():
                with open(data_file, "r") as f:
                    payload = json.load(f)
                    if isinstance(payload, dict):
                        normalized: Dict[str, Dict[str, float]] = {}
                        for key, value in payload.items():
                            if value is None:
                                continue
                            symbol = str(key).upper()
                            if isinstance(value, dict):
                                normalized[symbol] = {
                                    "short_interest_pct": float(value.get("short_interest_pct", 0.0) or 0.0),
                                    "short_interest": float(value.get("short_interest", 0.0) or 0.0),
                                    "days_to_cover": float(value.get("days_to_cover", 0.0) or 0.0),
                                }
                            else:
                                normalized[symbol] = {"short_interest_pct": float(value)}
                        self.short_interest = normalized
        except Exception as e:
            logger.debug(f"Failed to load short interest data: {e}")

    def set_short_interest_data(self, data: Dict[str, Dict[str, float]]) -> None:
        """Update short interest data from provider."""
        for symbol, entry in data.items():
            if not symbol:
                continue
            short_interest_shares = float(entry.get("short_interest", 0.0) or 0.0)
            short_interest_pct = float(entry.get("short_interest_pct", 0.0) or 0.0)
            if short_interest_pct <= 0 and short_interest_shares:
                float_millions = self.get_float(symbol.upper())
                if float_millions:
                    short_interest_pct = (short_interest_shares / (float_millions * 1_000_000)) * 100
            self.short_interest[symbol.upper()] = {
                "short_interest_pct": short_interest_pct,
                "short_interest": short_interest_shares,
                "days_to_cover": float(entry.get("days_to_cover", 0.0) or 0.0),
            }

    def _short_interest_score(self, symbol: str) -> tuple[float, float, float]:
        """Return (short_interest_pct, score 0-1, days_to_cover)."""
        entry = self.short_interest.get(symbol, {})
        pct = float(entry.get("short_interest_pct", 0.0) or 0.0)
        days_to_cover = float(entry.get("days_to_cover", 0.0) or 0.0)

        if pct <= 0 and entry.get("short_interest"):
            float_millions = self.get_float(symbol)
            if float_millions:
                pct = (float(entry.get("short_interest")) / (float_millions * 1_000_000)) * 100

        score = 0.0
        if pct > 0:
            # Score starts at 10% SI and maxes near 40%
            score = min(max((pct - 10.0) / 30.0, 0.0), 1.0)
        elif days_to_cover > 0:
            # Use days-to-cover as a fallback signal (1-6 days -> 0-1 scale)
            score = min(max((days_to_cover - 1.0) / 5.0, 0.0), 1.0)

        return pct, score, days_to_cover

    def _daily_trend_metrics(self, daily_df: Optional[pd.DataFrame]) -> Dict[str, Any]:
        """Compute daily trend metrics using SMA20/50."""
        if daily_df is None:
            return {"available": False}
        df_clean = daily_df.dropna(subset=["open", "high", "low", "close", "volume"])
        if len(df_clean) < 50:
            return {"available": False}
        close = df_clean["close"]
        sma20 = sma(close, 20).iloc[-1]
        sma50 = sma(close, 50).iloc[-1]
        last_close = float(close.iloc[-1])
        trend_ok = last_close >= sma20 and sma20 >= sma50
        return {
            "available": True,
            "last_close": last_close,
            "sma20": float(sma20),
            "sma50": float(sma50),
            "trend_ok": trend_ok,
        }

    def calculate_gap(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate overnight gap - KEY day trading indicator

        Gap = (Today's Open - Yesterday's Close) / Yesterday's Close * 100

        Day traders look for:
        - Gap up 2%+ = bullish momentum
        - Gap down 2%+ = bearish momentum or short opportunity
        - Gap 5%+ = significant move, high priority
        """
        if "open" not in df or "close" not in df or len(df) < 2:
            return {"gap_percent": 0.0, "gap_direction": "FLAT", "is_gapper": False, "is_significant_gap": False}

        # Get today's first bar and previous day's last bar
        try:
            if "date" in df:
                date_key = df["date"].astype(str).str.slice(0, 10)
                groups = df.groupby(date_key, sort=True)
                dates = list(groups.groups.keys())
                if len(dates) >= 2:
                    prev_day = groups.get_group(dates[-2])
                    today = groups.get_group(dates[-1])
                    today_open = float(today["open"].iloc[0])
                    prev_close = float(prev_day["close"].iloc[-1])
                else:
                    today_open = float(df["open"].iloc[-1])
                    prev_close = float(df["close"].iloc[-2])
            else:
                today_open = float(df["open"].iloc[-1])
                prev_close = float(df["close"].iloc[-2])
        except Exception:
            return {"gap_percent": 0.0, "gap_direction": "FLAT", "is_gapper": False, "is_significant_gap": False}

        if prev_close == 0:
            return {"gap_percent": 0.0, "gap_direction": "FLAT", "is_gapper": False, "is_significant_gap": False}

        gap_percent = ((today_open - prev_close) / prev_close) * 100

        # Determine gap direction and significance
        if gap_percent >= 2.0:
            direction = "GAP_UP"
            is_gapper = True
        elif gap_percent <= -2.0:
            direction = "GAP_DOWN"
            is_gapper = True
        else:
            direction = "FLAT"
            is_gapper = False

        return {
            "gap_percent": round(gap_percent, 2),
            "gap_direction": direction,
            "is_gapper": is_gapper,
            "is_significant_gap": abs(gap_percent) >= 5.0  # 5%+ is very significant
        }

    def get_float(self, symbol: str) -> Optional[float]:
        """
        Get float for a symbol (in millions of shares)
        Returns None if unknown (will skip float filter)
        """
        return LOW_FLOAT_STOCKS.get(symbol)

    def _float_bucket(self, float_millions: Optional[float]) -> str:
        if float_millions is None:
            return "UNKNOWN"
        if float_millions <= self.low_float_max:
            return "LOW"
        if float_millions <= self.mid_float_max:
            return "MID"
        return "LARGE"

    def _thresholds_for_float(self, float_millions: Optional[float]) -> tuple[float, float, str]:
        bucket = self._float_bucket(float_millions)
        if bucket == "LOW":
            return self.min_avg_volume_low_float, self.min_relative_volume_low_float, bucket
        if bucket == "MID":
            return self.min_avg_volume_mid_float, self.min_relative_volume_mid_float, bucket
        if bucket == "LARGE":
            return self.min_avg_volume_large_float, self.min_relative_volume_large_float, bucket
        return self.min_avg_volume, self.min_relative_volume, bucket

    def _in_play_flags(
        self,
        symbol: str,
        gap_info: Dict[str, Any],
        relative_volume: float,
        premarket_volume: float,
    ) -> tuple[bool, str]:
        reasons = []
        if symbol in self.news_catalysts:
            reasons.append("CATALYST")
        if gap_info.get("is_gapper") and abs(gap_info.get("gap_percent", 0.0)) >= self.in_play_gap_percent:
            reasons.append("GAP")
        if relative_volume >= self.in_play_min_rvol:
            reasons.append("RVOL")
        if premarket_volume >= self.min_premarket_volume:
            reasons.append("PREMARKET")
        return (len(reasons) > 0, ", ".join(reasons))

    def _volume_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Compute volume metrics consistently for 5m bars."""
        bars_per_day = 78  # 6.5 trading hours * 12 (5-min bars)

        avg_volume_bar = float(df["volume"].tail(20).mean()) if "volume" in df else 0.0
        last_volume = float(df["volume"].iloc[-1]) if "volume" in df and len(df) > 0 else 0.0

        avg_daily_volume = 0.0
        today_cum_volume = 0.0
        avg_cum_volume = 0.0
        rvol_tod = 0.0
        premarket_volume = 0.0

        if "date" in df and "volume" in df and len(df) > 0:
            try:
                ts = pd.to_datetime(df["date"], utc=True, errors="coerce")
                ts_et = ts.dt.tz_convert("America/New_York")
                date_key = ts_et.dt.date
                daily_groups = df.groupby(date_key)
                daily_volumes = daily_groups["volume"].sum()
                if len(daily_volumes) > 0:
                    avg_daily_volume = float(daily_volumes.mean())

                    # Time-of-day relative volume: compare today's cumulative volume
                    # vs average cumulative volume at the same bar index.
                    last_date = daily_volumes.index[-1]
                    today_df = daily_groups.get_group(last_date)
                    bar_index = max(len(today_df) - 1, 0)
                    today_cum_volume = float(today_df["volume"].iloc[: bar_index + 1].sum())

                    # Premarket volume (ET)
                    ts_today = ts_et[date_key == last_date]
                    if len(ts_today) == len(today_df):
                        premarket_mask = ts_today.dt.time < datetime.strptime("09:30", "%H:%M").time()
                        premarket_volume = float(today_df.loc[premarket_mask, "volume"].sum())

                    prev_dates = [d for d in daily_volumes.index[:-1]]
                    if prev_dates:
                        prev_cums = []
                        for d in prev_dates:
                            ddf = daily_groups.get_group(d)
                            if len(ddf) == 0:
                                continue
                            idx = min(bar_index, len(ddf) - 1)
                            prev_cums.append(float(ddf["volume"].iloc[: idx + 1].sum()))
                        if prev_cums:
                            avg_cum_volume = float(sum(prev_cums) / len(prev_cums))
                            if avg_cum_volume > 0:
                                rvol_tod = today_cum_volume / avg_cum_volume
            except Exception:
                avg_daily_volume = 0.0

        if avg_daily_volume <= 0:
            avg_daily_volume = avg_volume_bar * bars_per_day

        if rvol_tod <= 0 and avg_volume_bar > 0:
            rvol_tod = last_volume / avg_volume_bar

        return {
            "avg_volume_bar": avg_volume_bar,
            "avg_daily_volume": avg_daily_volume,
            "last_volume": last_volume,
            "today_cum_volume": today_cum_volume,
            "avg_cum_volume": avg_cum_volume,
            "rvol_tod": rvol_tod,
            "premarket_volume": premarket_volume,
        }

    def evaluate_symbol_detailed(
        self,
        symbol: str,
        df: pd.DataFrame,
        current_hour: Optional[int] = None,
        current_minute: Optional[int] = None,
        daily_df: Optional[pd.DataFrame] = None,
        market_status: Optional[Dict[str, Any]] = None,
        session_info: Optional[Dict[str, Any]] = None,
        bypass_volume: bool = False,
    ) -> Dict[str, Any]:
        """
        Evaluate a symbol and return DETAILED results including pass/fail for each filter.
        This is used for UI display to show why each stock was included or excluded.
        """
        result = {
            "symbol": symbol,
            "passed": False,
            "filters": {},
            "data": {},
            "rejection_reason": None,
        }

        df_clean = df.dropna(subset=["open", "high", "low", "close", "volume"])
        has_timestamp = "date" in df_clean.columns

        # Check minimum data
        if len(df_clean) < 20:
            result["rejection_reason"] = "Insufficient data (< 20 bars)"
            result["filters"]["data_check"] = {"passed": False, "reason": "< 20 bars"}
            return result
        result["filters"]["data_check"] = {"passed": True, "value": len(df_clean)}

        features = latest_feature_vector(df_clean)
        last_price = float(df_clean["close"].iloc[-1])
        volumes = self._volume_metrics(df_clean)
        avg_volume_bar = volumes["avg_volume_bar"]
        avg_volume = volumes["avg_daily_volume"]
        last_volume = volumes["last_volume"]
        relative_volume = volumes["rvol_tod"]
        premarket_volume = volumes["premarket_volume"]

        # Calculate gap - KEY day trading indicator
        gap_info = self.calculate_gap(df_clean)

        # ATR metrics (for logging + scoring)
        atr_series = atr(df_clean, 14)
        current_atr = float(atr_series.iloc[-1]) if len(atr_series) > 0 else 0.0
        atr_percent = (current_atr / last_price) * 100 if last_price > 0 else 0.0

        float_millions = self.get_float(symbol)
        volume_floor, rvol_floor, float_bucket = self._thresholds_for_float(float_millions)
        in_play, in_play_reason = self._in_play_flags(symbol, gap_info, relative_volume, premarket_volume)
        in_play_volume_floor = volume_floor * self.in_play_volume_multiplier

        # Store basic data
        result["data"]["price"] = round(last_price, 2)
        result["data"]["avg_volume"] = int(avg_volume)
        result["data"]["avg_volume_bar"] = int(avg_volume_bar)
        result["data"]["last_volume"] = int(last_volume)
        result["data"]["relative_volume"] = round(relative_volume, 2)
        result["data"]["rvol_tod"] = round(relative_volume, 2)
        result["data"]["today_volume"] = int(volumes["today_cum_volume"])
        result["data"]["avg_cum_volume"] = int(volumes["avg_cum_volume"])
        result["data"]["premarket_volume"] = int(premarket_volume)
        result["data"]["volatility"] = round(features.get("volatility", 0), 4)
        result["data"]["gap_percent"] = gap_info["gap_percent"]
        result["data"]["gap_direction"] = gap_info["gap_direction"]
        result["data"]["is_gapper"] = gap_info["is_gapper"]
        result["data"]["atr"] = round(current_atr, 2)
        result["data"]["atr_percent"] = round(atr_percent, 2)
        result["data"]["float_bucket"] = float_bucket
        result["data"]["in_play"] = in_play
        result["data"]["in_play_reason"] = in_play_reason
        result["data"]["volume_floor"] = int(volume_floor)
        result["data"]["rvol_floor"] = round(rvol_floor, 2)

        # Volume Filter
        vol_passed = avg_volume >= volume_floor
        if not vol_passed and in_play:
            vol_passed = avg_volume >= in_play_volume_floor
        if not vol_passed and bypass_volume:
            vol_passed = True
        result["filters"]["volume"] = {
            "passed": vol_passed,
            "value": int(avg_volume),
            "threshold": int(volume_floor),
            "in_play_floor": int(in_play_volume_floor),
            "in_play": in_play,
            "bypass_volume": bypass_volume,
            "reason": (
                f"Avg vol {int(avg_volume):,} {'≥' if vol_passed else '<'} {int(volume_floor):,}"
                + (f" (in-play floor {int(in_play_volume_floor):,})" if in_play else "")
                + (" (TOP-N VOLUME BYPASS)" if bypass_volume and avg_volume < volume_floor else "")
            ),
        }
        if not vol_passed:
            result["rejection_reason"] = f"Low volume ({int(avg_volume):,} < {int(volume_floor):,})"
            return result

        # Market status filter (halts / LULD)
        halted = bool(market_status.get("halted", False)) if market_status else False
        luld = market_status.get("luld") if market_status else None
        luld_indicator = None
        luld_active = False
        if isinstance(luld, dict):
            luld_indicator = luld.get("indicator")
            luld_active = bool(luld_indicator) and str(luld_indicator).lower() not in {"n", "normal"}
        if halted or luld_active:
            result["filters"]["market_status"] = {
                "passed": False,
                "halted": halted,
                "luld_indicator": luld_indicator,
            }
            result["data"]["halted"] = halted
            result["data"]["luld_indicator"] = luld_indicator
            result["rejection_reason"] = "Trading halt/LULD active"
            return result
        result["filters"]["market_status"] = {"passed": True, "halted": halted, "luld_indicator": luld_indicator}
        result["data"]["halted"] = halted
        result["data"]["luld_indicator"] = luld_indicator

        # Premarket Volume Filter (for gappers or during premarket)
        session = session_info or market_session()
        premarket_required = has_timestamp and (session.get("premarket", False) or gap_info.get("is_gapper", False))
        if self.require_premarket_volume and premarket_required:
            premarket_passed = premarket_volume >= self.min_premarket_volume
            result["filters"]["premarket_volume"] = {
                "passed": premarket_passed,
                "value": int(premarket_volume),
                "threshold": int(self.min_premarket_volume),
                "reason": f"Premarket {int(premarket_volume):,} {'≥' if premarket_passed else '<'} {int(self.min_premarket_volume):,}",
            }
            if not premarket_passed:
                result["rejection_reason"] = f"Low premarket volume ({int(premarket_volume):,} < {int(self.min_premarket_volume):,})"
                return result
        else:
            result["filters"]["premarket_volume"] = {"passed": True, "skipped": True}

        # Price Filter
        price_passed = self.min_price <= last_price <= self.max_price
        result["filters"]["price"] = {
            "passed": price_passed,
            "value": round(last_price, 2),
            "range": [self.min_price, self.max_price],
            "reason": f"${last_price:.2f} {'within' if price_passed else 'outside'} ${self.min_price}-${self.max_price}"
        }
        if not price_passed:
            result["rejection_reason"] = f"Price ${last_price:.2f} outside range ${self.min_price}-${self.max_price}"
            return result

        # Volatility Filter
        vol_check_passed = features["volatility"] >= self.min_volatility
        result["filters"]["volatility"] = {
            "passed": vol_check_passed,
            "value": round(features["volatility"], 4),
            "threshold": self.min_volatility,
            "reason": f"Volatility {features['volatility']:.4f} {'≥' if vol_check_passed else '<'} {self.min_volatility}"
        }
        if not vol_check_passed:
            result["rejection_reason"] = f"Low volatility ({features['volatility']:.4f} < {self.min_volatility})"
            return result

        # Daily Trend Filter (SMA20/50 on daily bars)
        daily_metrics = self._daily_trend_metrics(daily_df)
        if self.require_daily_trend and daily_metrics.get("available"):
            trend_passed = daily_metrics.get("trend_ok", False)
            bypass = False
            if not trend_passed and (gap_info.get("is_significant_gap") or symbol in self.news_catalysts):
                trend_passed = True
                bypass = True
            result["filters"]["daily_trend"] = {
                "passed": trend_passed,
                "bypass": bypass,
                "last_close": round(daily_metrics.get("last_close", 0), 2),
                "sma20": round(daily_metrics.get("sma20", 0), 2),
                "sma50": round(daily_metrics.get("sma50", 0), 2),
                "reason": "Trend OK" if trend_passed else "Below SMA trend",
            }
            result["data"]["daily_trend"] = result["filters"]["daily_trend"]
            if not trend_passed:
                result["rejection_reason"] = "Weak daily trend"
                return result
        else:
            result["filters"]["daily_trend"] = {"passed": True, "skipped": True}

        # Relative Volume Filter (gappers get a pass - they're hot plays even with normal volume)
        rvol_passed = relative_volume >= rvol_floor
        gapper_bypass = gap_info.get("is_gapper", False) and abs(gap_info.get("gap_percent", 0.0)) >= self.in_play_gap_percent
        catalyst_bypass = symbol in self.news_catalysts
        effective_rvol_passed = rvol_passed or gapper_bypass or catalyst_bypass

        result["filters"]["relative_volume"] = {
            "passed": effective_rvol_passed,
            "value": round(relative_volume, 2),
            "threshold": rvol_floor,
            "gapper_bypass": gapper_bypass,
            "catalyst_bypass": catalyst_bypass,
            "reason": (
                f"RVol(ToD) {relative_volume:.1f}x {'≥' if rvol_passed else '<'} {rvol_floor}x"
                + (f" (GAP BYPASS: {gap_info['gap_percent']}%)" if gapper_bypass and not rvol_passed else "")
                + (" (CATALYST BYPASS)" if catalyst_bypass and not rvol_passed else "")
            ),
        }
        if not effective_rvol_passed:
            result["rejection_reason"] = f"Low relative volume ({relative_volume:.1f}x < {rvol_floor}x)"
            return result

        # If we get here, all filters passed!
        result["passed"] = True

        # Calculate scores (same logic as score_symbol)
        float_score = 0.0
        if self.enable_float_filter and float_millions is not None:
            if float_millions <= self.max_float_millions:
                float_score = max(0, (self.max_float_millions - float_millions) / self.max_float_millions) * 0.3

        ml_score = self.model.predict(features)
        momentum_score = float((df_clean["close"].iloc[-1] - df_clean["close"].iloc[-5]) / df_clean["close"].iloc[-5])

        atr_score = min(atr_percent / 5.0, 0.2)

        pattern_score = 0.0
        detected_pattern = None
        if self.enable_pattern_detection:
            bull_flag = is_bull_flag(df_clean)
            flat_top = is_flat_top_breakout(df_clean)
            abcd = is_abcd_pattern(df_clean)
            candidates = []
            if bull_flag.get("detected"):
                candidates.append(("BULL_FLAG", 0.25, bull_flag))
            if flat_top.get("detected"):
                candidates.append(("FLAT_TOP", 0.2, flat_top))
            if abcd.get("detected"):
                candidates.append((abcd.get("pattern", "ABCD"), 0.22, abcd))
            if candidates:
                detected_pattern, pattern_score, _ = max(candidates, key=lambda x: x[1])

        news_score = 0.0
        news_catalyst = None
        if symbol in self.news_catalysts:
            catalyst_data = self.news_catalysts[symbol]
            catalyst_type = catalyst_data.get("catalyst", "OTHER")
            if catalyst_type == "EARNINGS":
                news_score = 0.3
            elif catalyst_type == "FDA":
                news_score = 0.35
            elif catalyst_type == "M&A":
                news_score = 0.25
            elif catalyst_type == "ANALYST":
                news_score = 0.15
            else:
                news_score = 0.1
            news_catalyst = catalyst_type

        short_interest_pct, short_interest_score, short_interest_days = self._short_interest_score(symbol)

        if current_hour is None:
            current_hour = datetime.now().hour
        if current_minute is None:
            current_minute = datetime.now().minute
        time_multiplier = power_hour_multiplier(current_hour, current_minute) if self.enable_power_hour_boost else 1.0

        # Gap Score - KEY day trading indicator
        # Stocks that gap significantly are "in play" and get priority
        gap_score = 0.0
        gap_abs = abs(gap_info["gap_percent"])
        if gap_abs >= 10.0:
            gap_score = 0.35  # Massive gap - very high priority
        elif gap_abs >= 5.0:
            gap_score = 0.25  # Significant gap
        elif gap_abs >= 2.0:
            gap_score = 0.15  # Notable gap
        elif gap_abs >= 1.0:
            gap_score = 0.05  # Small gap

        # Adjusted scoring with gap as a factor
        # ML: 23%, Momentum: 14%, Gap: 14%, Float: 9%, Pattern: 14%, News: 9%, ATR: 12%, Short Interest: 5%
        base_score = (
            (ml_score * 0.23) +
            (momentum_score * 0.14) +
            (gap_score * 0.14) +
            (float_score * 0.09) +
            (pattern_score * 0.14) +
            (news_score * 0.09) +
            (atr_score * 0.12) +
            (short_interest_score * 0.05)
        )
        combined_score = base_score * time_multiplier

        # Store all scores
        result["data"]["float_millions"] = float_millions
        result["data"]["pattern"] = detected_pattern
        result["data"]["news_catalyst"] = news_catalyst
        result["data"]["short_interest_pct"] = round(short_interest_pct, 2)
        result["data"]["short_interest_days_to_cover"] = round(short_interest_days, 2)

        result["scores"] = {
            "ml_score": round(ml_score, 3),
            "momentum_score": round(momentum_score, 4),
            "gap_score": round(gap_score, 3),
            "float_score": round(float_score, 3),
            "pattern_score": round(pattern_score, 3),
            "news_score": round(news_score, 3),
            "atr_score": round(atr_score, 3),
            "short_interest_score": round(short_interest_score, 3),
            "time_multiplier": round(time_multiplier, 2),
            "combined_score": round(combined_score, 3),
        }

        return result

    def rank_with_details(
        self,
        market_data: Dict[str, pd.DataFrame],
        current_hour: Optional[int] = None,
        current_minute: Optional[int] = None,
        daily_data: Optional[Dict[str, pd.DataFrame]] = None,
        market_status: Optional[Dict[str, Dict[str, Any]]] = None,
        session_info: Optional[Dict[str, Any]] = None,
        guarantee_top_n_volume: int = 10,
    ) -> tuple:
        """
        Rank all symbols and return both passed and failed evaluations.
        Returns: (passed_list, all_evaluations)

        guarantee_top_n_volume: Always bypass the absolute volume threshold for the top N
        symbols by actual current volume. This ensures the highest-volume stocks in the
        universe always get fully evaluated even when market-wide volume is depressed.
        Other filters (trend, rvol, ATR, etc.) still apply to them.
        """
        # Pre-rank universe by actual volume so the top N are never blocked by the
        # absolute volume threshold alone. We use avg daily volume from the raw bars.
        volume_ranked: List[str] = []
        if guarantee_top_n_volume > 0:
            vol_estimates: List[tuple] = []
            for symbol, df in market_data.items():
                try:
                    df_clean = df.dropna(subset=["volume"])
                    if len(df_clean) >= 5:
                        avg_vol = float(df_clean["volume"].mean())
                        vol_estimates.append((symbol, avg_vol))
                except Exception:
                    pass
            vol_estimates.sort(key=lambda x: x[1], reverse=True)
            volume_ranked = [s for s, _ in vol_estimates[:guarantee_top_n_volume]]
            if volume_ranked:
                logger.info(
                    f"Volume guarantee: top {len(volume_ranked)} by volume will bypass absolute threshold: {volume_ranked}"
                )

        all_evaluations = []
        passed = []

        for symbol, df in market_data.items():
            daily_df = daily_data.get(symbol) if daily_data else None
            bypass_vol = symbol in volume_ranked
            try:
                evaluation = self.evaluate_symbol_detailed(
                    symbol,
                    df,
                    current_hour,
                    current_minute,
                    daily_df=daily_df,
                    market_status=market_status.get(symbol) if market_status else None,
                    session_info=session_info,
                    bypass_volume=bypass_vol,
                )
            except Exception as e:
                logger.warning(f"Screener evaluation failed for {symbol}: {e}")
                evaluation = {
                    "symbol": symbol,
                    "passed": False,
                    "filters": {"data_check": {"passed": False, "reason": "evaluation_error"}},
                    "data": {},
                    "rejection_reason": f"Evaluation error: {str(e)}",
                }
            all_evaluations.append(evaluation)
            if evaluation["passed"]:
                passed.append(evaluation)

        # Sort passed by combined score
        passed = sorted(passed, key=lambda x: x["scores"]["combined_score"], reverse=True)

        return passed, all_evaluations

    def score_symbol(
        self,
        symbol: str,
        df: pd.DataFrame,
        current_hour: Optional[int] = None,
        current_minute: Optional[int] = None,
        daily_df: Optional[pd.DataFrame] = None,
    ) -> Optional[Dict[str, Union[float, str]]]:
        """
        Score a symbol based on Warrior Trading criteria

        Returns enhanced scoring with:
        - ML score
        - Momentum score
        - Pattern detection (bull flag, flat top)
        - Power hour boost
        - News catalyst boost
        - Float score
        """
        df_clean = df.dropna(subset=["open", "high", "low", "close", "volume"])
        if len(df_clean) < 20:
            return None
        has_timestamp = "date" in df_clean.columns

        features = latest_feature_vector(df_clean)
        last_price = float(df_clean["close"].iloc[-1])
        volumes = self._volume_metrics(df_clean)
        avg_volume_bar = volumes["avg_volume_bar"]
        avg_volume = volumes["avg_daily_volume"]
        last_volume = volumes["last_volume"]
        relative_volume = volumes["rvol_tod"]
        premarket_volume = volumes["premarket_volume"]

        # Calculate gap
        gap_info = self.calculate_gap(df_clean)

        float_millions = self.get_float(symbol)
        volume_floor, rvol_floor, float_bucket = self._thresholds_for_float(float_millions)
        in_play, in_play_reason = self._in_play_flags(symbol, gap_info, relative_volume, premarket_volume)
        in_play_volume_floor = volume_floor * self.in_play_volume_multiplier

        # Premarket volume filter (only if timestamps exist and we're in premarket or a gapper)
        session = market_session()
        premarket_required = has_timestamp and (session.get("premarket", False) or gap_info.get("is_gapper", False))
        if self.require_premarket_volume and premarket_required:
            if premarket_volume < self.min_premarket_volume:
                return None

        # Basic filters
        if avg_volume < volume_floor and not (in_play and avg_volume >= in_play_volume_floor):
            return None
        if not (self.min_price <= last_price <= self.max_price):
            return None
        if features["volatility"] < self.min_volatility:
            return None

        # Daily Trend Filter (SMA20/50 on daily bars)
        daily_metrics = self._daily_trend_metrics(daily_df)
        if self.require_daily_trend and daily_metrics.get("available"):
            trend_passed = daily_metrics.get("trend_ok", False)
            if not trend_passed and (gap_info.get("is_significant_gap") or symbol in self.news_catalysts):
                trend_passed = True
            if not trend_passed:
                return None

        rvol_passed = relative_volume >= rvol_floor
        gapper_bypass = gap_info.get("is_gapper", False) and abs(gap_info.get("gap_percent", 0.0)) >= self.in_play_gap_percent
        catalyst_bypass = symbol in self.news_catalysts
        # Gappers/catalysts bypass relative volume requirement
        if not (rvol_passed or gapper_bypass or catalyst_bypass):
            return None

        # Float filter (Warrior Trading: prefer float < 100M)
        float_score = 0.0
        if self.enable_float_filter and float_millions is not None:
            if float_millions <= self.max_float_millions:
                # Lower float = higher score (more volatile)
                float_score = max(0, (self.max_float_millions - float_millions) / self.max_float_millions) * 0.3
            else:
                # Large float stocks can still be traded but get lower priority
                float_score = 0.0

        # ML Score
        ml_score = self.model.predict(features)

        # Momentum Score (5-bar momentum)
        momentum_score = float((df_clean["close"].iloc[-1] - df_clean["close"].iloc[-5]) / df_clean["close"].iloc[-5])

        # ATR Score (higher ATR = more tradeable for day trading)
        atr_series = atr(df_clean, 14)
        current_atr = atr_series.iloc[-1] if len(atr_series) > 0 else 0
        atr_percent = (current_atr / last_price) * 100 if last_price > 0 else 0
        atr_score = min(atr_percent / 5.0, 0.2)  # Cap at 0.2, reward up to 5% ATR

        # Pattern Detection Score
        pattern_score = 0.0
        detected_pattern = None
        if self.enable_pattern_detection:
            bull_flag = is_bull_flag(df_clean)
            flat_top = is_flat_top_breakout(df_clean)
            abcd = is_abcd_pattern(df_clean)
            candidates = []
            if bull_flag.get("detected"):
                candidates.append(("BULL_FLAG", 0.25))
            if flat_top.get("detected"):
                candidates.append(("FLAT_TOP", 0.2))
            if abcd.get("detected"):
                candidates.append((abcd.get("pattern", "ABCD"), 0.22))
            if candidates:
                detected_pattern, pattern_score = max(candidates, key=lambda x: x[1])

        # News Catalyst Score
        news_score = 0.0
        news_catalyst = None
        if symbol in self.news_catalysts:
            catalyst_data = self.news_catalysts[symbol]
            catalyst_type = catalyst_data.get("catalyst", "OTHER")
            # Earnings and FDA catalysts are highest impact
            if catalyst_type == "EARNINGS":
                news_score = 0.3
            elif catalyst_type == "FDA":
                news_score = 0.35
            elif catalyst_type == "M&A":
                news_score = 0.25
            elif catalyst_type == "ANALYST":
                news_score = 0.15
            else:
                news_score = 0.1
            news_catalyst = catalyst_type

        short_interest_pct, short_interest_score, short_interest_days = self._short_interest_score(symbol)

        # Power Hour Multiplier (9:30-10:30 AM boost)
        time_multiplier = 1.0
        if self.enable_power_hour_boost:
            if current_hour is None:
                current_hour = datetime.now().hour
            if current_minute is None:
                current_minute = datetime.now().minute
            time_multiplier = power_hour_multiplier(current_hour, current_minute)

        # Gap Score - KEY day trading indicator
        gap_score = 0.0
        gap_abs = abs(gap_info["gap_percent"])
        if gap_abs >= 10.0:
            gap_score = 0.35  # Massive gap
        elif gap_abs >= 5.0:
            gap_score = 0.25  # Significant gap
        elif gap_abs >= 2.0:
            gap_score = 0.15  # Notable gap
        elif gap_abs >= 1.0:
            gap_score = 0.05  # Small gap

        # Combined Score with gap included
        # ML: 23%, Momentum: 14%, Gap: 14%, Float: 9%, Pattern: 14%, News: 9%, ATR: 12%, Short Interest: 5%
        base_score = (
            (ml_score * 0.23) +
            (momentum_score * 0.14) +
            (gap_score * 0.14) +
            (float_score * 0.09) +
            (pattern_score * 0.14) +
            (news_score * 0.09) +
            (atr_score * 0.12) +
            (short_interest_score * 0.05)
        )

        # Apply time multiplier
        combined = base_score * time_multiplier

        return {
            "symbol": symbol,
            "ml_score": ml_score,
            "momentum_score": momentum_score,
            "combined_score": combined,
            "last_price": last_price,
            "avg_volume": avg_volume,
            "relative_volume": relative_volume,
            "float_bucket": float_bucket,
            "in_play": in_play,
            "in_play_reason": in_play_reason,
            # Enhanced fields
            "float_millions": float_millions,
            "float_score": float_score,
            "atr": current_atr,
            "atr_percent": atr_percent,
            "pattern": detected_pattern,
            "pattern_score": pattern_score,
            "news_catalyst": news_catalyst,
            "news_score": news_score,
            "short_interest_pct": short_interest_pct,
            "short_interest_score": short_interest_score,
            "short_interest_days_to_cover": short_interest_days,
            "time_multiplier": time_multiplier,
            # Gap fields - KEY day trading indicator
            "gap_percent": gap_info["gap_percent"],
            "gap_direction": gap_info["gap_direction"],
            "gap_score": gap_score,
            "is_gapper": gap_info["is_gapper"],
        }

    def rank(
        self,
        market_data: Dict[str, pd.DataFrame],
        current_hour: Optional[int] = None,
        current_minute: Optional[int] = None,
        daily_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> List[Dict[str, Union[float, str]]]:
        """
        Rank all symbols by Warrior Trading criteria

        Returns sorted list with best opportunities first
        """
        results: List[Dict[str, Union[float, str]]] = []
        for symbol, df in market_data.items():
            daily_df = daily_data.get(symbol) if daily_data else None
            try:
                scored = self.score_symbol(symbol, df, current_hour, current_minute, daily_df=daily_df)
                if scored:
                    results.append(scored)
            except Exception as e:
                logger.debug(f"Screener score failed for {symbol}: {e}")

        # Sort by combined score (highest first)
        ranked = sorted(results, key=lambda x: x["combined_score"], reverse=True)

        # Log top picks
        if ranked:
            top_3 = ranked[:3]
            logger.info(f"Top 3 opportunities: {[r['symbol'] for r in top_3]}")
            for r in top_3:
                logger.debug(
                    f"  {r['symbol']}: score={r['combined_score']:.3f}, "
                    f"rvol={r['relative_volume']:.1f}x, pattern={r.get('pattern')}, "
                    f"news={r.get('news_catalyst')}"
                )

        return ranked

    def get_low_float_movers(
        self,
        market_data: Dict[str, pd.DataFrame],
        max_results: int = 10
    ) -> List[Dict[str, Union[float, str]]]:
        """
        Get specifically low float stocks with high momentum
        Warrior Trading bread and butter plays
        """
        results = []
        for symbol, df in market_data.items():
            float_millions = self.get_float(symbol)
            if float_millions is None or float_millions > 50:  # Very low float only
                continue

            scored = self.score_symbol(symbol, df)
            if scored and scored["relative_volume"] >= 2.5:  # Higher rvol threshold
                results.append(scored)

        return sorted(results, key=lambda x: x["combined_score"], reverse=True)[:max_results]
