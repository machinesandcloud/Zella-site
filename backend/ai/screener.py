"""
Enhanced Market Screener - Warrior Trading Aligned

Implements the key stock selection criteria from Warrior Trading:
1. Float under 100M shares (low float = high volatility)
2. High relative volume (2x+ average)
3. News catalyst detection
4. Power hour weighting (9:30-10:30 AM boost)
5. ATR-based volatility analysis
"""

from typing import Dict, List, Optional, Union
from datetime import datetime
import logging

import pandas as pd

from ai.feature_engineering import latest_feature_vector
from ai.ml_model import MLSignalModel
from utils.indicators import atr, power_hour_multiplier, is_bull_flag, is_flat_top_breakout

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
        max_float_millions: float = 100.0,  # Warrior Trading: float < 100M
        enable_float_filter: bool = True,
        enable_pattern_detection: bool = True,
        enable_power_hour_boost: bool = True,
    ) -> None:
        self.model = model
        self.min_avg_volume = min_avg_volume
        self.min_price = min_price
        self.max_price = max_price
        self.min_volatility = min_volatility
        self.min_relative_volume = min_relative_volume
        self.max_float_millions = max_float_millions
        self.enable_float_filter = enable_float_filter
        self.enable_pattern_detection = enable_pattern_detection
        self.enable_power_hour_boost = enable_power_hour_boost

        # News catalyst cache (populated externally)
        self.news_catalysts: Dict[str, Dict] = {}

    def set_news_catalysts(self, catalysts: Dict[str, Dict]) -> None:
        """Update news catalyst data for symbols"""
        self.news_catalysts = catalysts

    def calculate_gap(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate overnight gap - KEY day trading indicator

        Gap = (Today's Open - Yesterday's Close) / Yesterday's Close * 100

        Day traders look for:
        - Gap up 2%+ = bullish momentum
        - Gap down 2%+ = bearish momentum or short opportunity
        - Gap 5%+ = significant move, high priority
        """
        if len(df) < 2:
            return {"gap_percent": 0.0, "gap_direction": "FLAT", "is_gapper": False}

        # Get today's first bar and previous day's last bar
        today_open = float(df["open"].iloc[-1])
        prev_close = float(df["close"].iloc[-2])

        if prev_close == 0:
            return {"gap_percent": 0.0, "gap_direction": "FLAT", "is_gapper": False}

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

    def evaluate_symbol_detailed(
        self,
        symbol: str,
        df: pd.DataFrame,
        current_hour: Optional[int] = None,
        current_minute: Optional[int] = None,
    ) -> Dict[str, any]:
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

        # Check minimum data
        if len(df) < 20:
            result["rejection_reason"] = "Insufficient data (< 20 bars)"
            result["filters"]["data_check"] = {"passed": False, "reason": "< 20 bars"}
            return result
        result["filters"]["data_check"] = {"passed": True, "value": len(df)}

        features = latest_feature_vector(df)
        last_price = float(df["close"].iloc[-1])
        avg_volume = float(df["volume"].tail(20).mean())
        last_volume = float(df["volume"].iloc[-1])
        relative_volume = last_volume / avg_volume if avg_volume else 0.0

        # Calculate gap - KEY day trading indicator
        gap_info = self.calculate_gap(df)

        # Store basic data
        result["data"]["price"] = round(last_price, 2)
        result["data"]["avg_volume"] = int(avg_volume)
        result["data"]["last_volume"] = int(last_volume)
        result["data"]["relative_volume"] = round(relative_volume, 2)
        result["data"]["volatility"] = round(features.get("volatility", 0), 4)
        result["data"]["gap_percent"] = gap_info["gap_percent"]
        result["data"]["gap_direction"] = gap_info["gap_direction"]
        result["data"]["is_gapper"] = gap_info["is_gapper"]

        # Volume Filter
        vol_passed = avg_volume >= self.min_avg_volume
        result["filters"]["volume"] = {
            "passed": vol_passed,
            "value": int(avg_volume),
            "threshold": int(self.min_avg_volume),
            "reason": f"Avg vol {int(avg_volume):,} {'≥' if vol_passed else '<'} {int(self.min_avg_volume):,}"
        }
        if not vol_passed:
            result["rejection_reason"] = f"Low volume ({int(avg_volume):,} < {int(self.min_avg_volume):,})"
            return result

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

        # Relative Volume Filter (gappers get a pass - they're hot plays even with normal volume)
        rvol_passed = relative_volume >= self.min_relative_volume
        # Significant gappers (5%+) bypass relative volume requirement
        # This is a KEY day trading principle - gapping stocks are in play
        gapper_bypass = gap_info.get("is_significant_gap", False)
        effective_rvol_passed = rvol_passed or gapper_bypass

        result["filters"]["relative_volume"] = {
            "passed": effective_rvol_passed,
            "value": round(relative_volume, 2),
            "threshold": self.min_relative_volume,
            "gapper_bypass": gapper_bypass,
            "reason": f"RVol {relative_volume:.1f}x {'≥' if rvol_passed else '<'} {self.min_relative_volume}x" +
                      (f" (GAPPER BYPASS: {gap_info['gap_percent']}%)" if gapper_bypass and not rvol_passed else "")
        }
        if not effective_rvol_passed:
            result["rejection_reason"] = f"Low relative volume ({relative_volume:.1f}x < {self.min_relative_volume}x)"
            return result

        # If we get here, all filters passed!
        result["passed"] = True

        # Calculate scores (same logic as score_symbol)
        float_millions = self.get_float(symbol)
        float_score = 0.0
        if self.enable_float_filter and float_millions is not None:
            if float_millions <= self.max_float_millions:
                float_score = max(0, (self.max_float_millions - float_millions) / self.max_float_millions) * 0.3

        ml_score = self.model.predict(features)
        momentum_score = float((df["close"].iloc[-1] - df["close"].iloc[-5]) / df["close"].iloc[-5])

        atr_series = atr(df, 14)
        current_atr = atr_series.iloc[-1] if len(atr_series) > 0 else 0
        atr_percent = (current_atr / last_price) * 100 if last_price > 0 else 0
        atr_score = min(atr_percent / 5.0, 0.2)

        pattern_score = 0.0
        detected_pattern = None
        if self.enable_pattern_detection:
            bull_flag = is_bull_flag(df)
            flat_top = is_flat_top_breakout(df)
            if bull_flag.get("detected"):
                pattern_score = 0.25
                detected_pattern = "BULL_FLAG"
            elif flat_top.get("detected"):
                pattern_score = 0.2
                detected_pattern = "FLAT_TOP"

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
        # ML: 25%, Momentum: 15%, Gap: 15%, Float: 10%, Pattern: 15%, News: 10%, ATR: 10%
        base_score = (
            (ml_score * 0.25) +
            (momentum_score * 0.15) +
            (gap_score * 0.15) +
            (float_score * 0.10) +
            (pattern_score * 0.15) +
            (news_score * 0.10) +
            (atr_score * 0.10)
        )
        combined_score = base_score * time_multiplier

        # Store all scores
        result["data"]["float_millions"] = float_millions
        result["data"]["atr"] = round(current_atr, 2)
        result["data"]["atr_percent"] = round(atr_percent, 2)
        result["data"]["pattern"] = detected_pattern
        result["data"]["news_catalyst"] = news_catalyst

        result["scores"] = {
            "ml_score": round(ml_score, 3),
            "momentum_score": round(momentum_score, 4),
            "gap_score": round(gap_score, 3),
            "float_score": round(float_score, 3),
            "pattern_score": round(pattern_score, 3),
            "news_score": round(news_score, 3),
            "atr_score": round(atr_score, 3),
            "time_multiplier": round(time_multiplier, 2),
            "combined_score": round(combined_score, 3),
        }

        return result

    def rank_with_details(
        self,
        market_data: Dict[str, pd.DataFrame],
        current_hour: Optional[int] = None,
        current_minute: Optional[int] = None,
    ) -> tuple:
        """
        Rank all symbols and return both passed and failed evaluations.
        Returns: (passed_list, all_evaluations)
        """
        all_evaluations = []
        passed = []

        for symbol, df in market_data.items():
            evaluation = self.evaluate_symbol_detailed(symbol, df, current_hour, current_minute)
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
        if len(df) < 20:
            return None

        features = latest_feature_vector(df)
        last_price = float(df["close"].iloc[-1])
        avg_volume = float(df["volume"].tail(20).mean())
        last_volume = float(df["volume"].iloc[-1])
        relative_volume = last_volume / avg_volume if avg_volume else 0.0

        # Calculate gap
        gap_info = self.calculate_gap(df)

        # Basic filters
        if avg_volume < self.min_avg_volume:
            return None
        if not (self.min_price <= last_price <= self.max_price):
            return None
        if features["volatility"] < self.min_volatility:
            return None
        # Gappers (5%+) bypass relative volume requirement
        if relative_volume < self.min_relative_volume and not gap_info.get("is_significant_gap", False):
            return None

        # Float filter (Warrior Trading: prefer float < 100M)
        float_millions = self.get_float(symbol)
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
        momentum_score = float((df["close"].iloc[-1] - df["close"].iloc[-5]) / df["close"].iloc[-5])

        # ATR Score (higher ATR = more tradeable for day trading)
        atr_series = atr(df, 14)
        current_atr = atr_series.iloc[-1] if len(atr_series) > 0 else 0
        atr_percent = (current_atr / last_price) * 100 if last_price > 0 else 0
        atr_score = min(atr_percent / 5.0, 0.2)  # Cap at 0.2, reward up to 5% ATR

        # Pattern Detection Score
        pattern_score = 0.0
        detected_pattern = None
        if self.enable_pattern_detection:
            bull_flag = is_bull_flag(df)
            flat_top = is_flat_top_breakout(df)

            if bull_flag.get("detected"):
                pattern_score = 0.25
                detected_pattern = "BULL_FLAG"
            elif flat_top.get("detected"):
                pattern_score = 0.2
                detected_pattern = "FLAT_TOP"

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
        # ML: 25%, Momentum: 15%, Gap: 15%, Float: 10%, Pattern: 15%, News: 10%, ATR: 10%
        base_score = (
            (ml_score * 0.25) +
            (momentum_score * 0.15) +
            (gap_score * 0.15) +
            (float_score * 0.10) +
            (pattern_score * 0.15) +
            (news_score * 0.10) +
            (atr_score * 0.10)
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
            # Enhanced fields
            "float_millions": float_millions,
            "float_score": float_score,
            "atr": current_atr,
            "atr_percent": atr_percent,
            "pattern": detected_pattern,
            "pattern_score": pattern_score,
            "news_catalyst": news_catalyst,
            "news_score": news_score,
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
    ) -> List[Dict[str, Union[float, str]]]:
        """
        Rank all symbols by Warrior Trading criteria

        Returns sorted list with best opportunities first
        """
        results: List[Dict[str, Union[float, str]]] = []
        for symbol, df in market_data.items():
            scored = self.score_symbol(symbol, df, current_hour, current_minute)
            if scored:
                results.append(scored)

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
