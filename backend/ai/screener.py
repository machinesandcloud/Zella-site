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
# In production, this should be fetched from a data provider
LOW_FLOAT_STOCKS = {
    # Penny stocks and small caps with low float
    "GME": 75, "AMC": 85, "BBBY": 60, "BB": 40, "CLOV": 35,
    "WISH": 45, "WKHS": 25, "RIDE": 30, "SKLZ": 40, "SPCE": 50,
    # Biotech (often low float)
    "MRNA": 95, "BNTX": 35, "NVAX": 45, "VXRT": 30, "INO": 40,
    # Recent IPOs and SPACs (typically low float)
    "RIVN": 90, "LCID": 85, "IONQ": 25, "RKLB": 30, "ASTR": 20,
    # Cannabis
    "TLRY": 65, "CGC": 55, "SNDL": 80, "ACB": 45,
    # Crypto-related
    "COIN": 85, "MARA": 50, "RIOT": 45, "CLSK": 35, "MSTR": 40,
    # High volume large caps (not low float, but tradeable)
    "AAPL": 500, "MSFT": 400, "NVDA": 350, "TSLA": 300, "AMZN": 450,
    "AMD": 200, "META": 380, "GOOGL": 420,
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
        min_avg_volume: float = 500000,
        min_price: float = 5.0,
        max_price: float = 1000.0,
        min_volatility: float = 0.005,
        min_relative_volume: float = 2.0,
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

    def get_float(self, symbol: str) -> Optional[float]:
        """
        Get float for a symbol (in millions of shares)
        Returns None if unknown (will skip float filter)
        """
        return LOW_FLOAT_STOCKS.get(symbol)

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

        # Basic filters
        if avg_volume < self.min_avg_volume:
            return None
        if not (self.min_price <= last_price <= self.max_price):
            return None
        if features["volatility"] < self.min_volatility:
            return None
        if relative_volume < self.min_relative_volume:
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

        # Combined Score with Warrior Trading weighting
        # ML: 30%, Momentum: 20%, Float: 15%, Pattern: 15%, News: 10%, ATR: 10%
        base_score = (
            (ml_score * 0.30) +
            (momentum_score * 0.20) +
            (float_score * 0.15) +
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
