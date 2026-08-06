"""
Market Regime Detector — classifies current market conditions.

Regimes: TRENDING_UP, TRENDING_DOWN, RANGING, VOLATILE, QUIET
The AI ensemble uses regime as context to weight its predictions differently.
"""

import pandas as pd
import numpy as np
from typing import Optional
from ta.trend import ADXIndicator, EMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands


class RegimeDetector:
    """
    Detect market regime from OHLCV data.

    Uses a combination of:
    - ADX for trend strength
    - ATR percentile for volatility level
    - Bollinger Band squeeze for consolidation
    - EMA alignment for trend direction
    """

    # Regime labels
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    QUIET = "QUIET"

    @classmethod
    def detect(cls, df: pd.DataFrame) -> str:
        """
        Detect the current market regime.

        Args:
            df: DataFrame with OHLCV columns, minimum 100 rows.

        Returns:
            Regime string: TRENDING_UP, TRENDING_DOWN, RANGING, VOLATILE, or QUIET
        """
        if df is None or len(df) < 100:
            return cls.RANGING  # Default when insufficient data

        close = df["close"]
        high = df["high"]
        low = df["low"]

        # ── ADX: trend strength ─────────────────────────────
        try:
            adx_indicator = ADXIndicator(high=high, low=low, close=close, window=14)
            adx = adx_indicator.adx().iloc[-1]
            di_plus = adx_indicator.adx_pos().iloc[-1]
            di_minus = adx_indicator.adx_neg().iloc[-1]
        except Exception:
            adx = 20
            di_plus = 20
            di_minus = 20

        # ── ATR percentile: volatility level ────────────────
        try:
            atr = AverageTrueRange(high=high, low=low, close=close, window=14)
            atr_values = atr.average_true_range()
            atr_percentile = atr_values.rank(pct=True).iloc[-1]
        except Exception:
            atr_percentile = 0.5

        # ── Bollinger Band squeeze ──────────────────────────
        try:
            bb = BollingerBands(close=close, window=20, window_dev=2)
            bb_width = ((bb.bollinger_hband() - bb.bollinger_lband()) /
                        bb.bollinger_mavg())
            avg_width = bb_width.rolling(50).mean()
            squeeze = bb_width.iloc[-1] < avg_width.iloc[-1] * 0.75
        except Exception:
            squeeze = False

        # ── EMA alignment ───────────────────────────────────
        try:
            ema_8 = EMAIndicator(close=close, window=8).ema_indicator().iloc[-1]
            ema_21 = EMAIndicator(close=close, window=21).ema_indicator().iloc[-1]
            ema_50 = EMAIndicator(close=close, window=50).ema_indicator().iloc[-1]

            bullish_aligned = ema_8 > ema_21 > ema_50
            bearish_aligned = ema_8 < ema_21 < ema_50
        except Exception:
            bullish_aligned = False
            bearish_aligned = False

        # ── Classify regime ─────────────────────────────────
        is_trending = adx > 25
        is_strong_trend = adx > 35
        is_high_vol = atr_percentile > 0.75
        is_low_vol = atr_percentile < 0.25

        # VOLATILE: high volatility + no clear trend or very high ATR
        if is_high_vol and not is_strong_trend:
            return cls.VOLATILE

        # QUIET: low volatility + BB squeeze
        if is_low_vol and squeeze:
            return cls.QUIET

        # TRENDING_UP: ADX > 25 + EMAs bullish aligned + DI+ > DI-
        if is_trending and bullish_aligned and di_plus > di_minus:
            return cls.TRENDING_UP

        # TRENDING_DOWN: ADX > 25 + EMAs bearish aligned + DI- > DI+
        if is_trending and bearish_aligned and di_minus > di_plus:
            return cls.TRENDING_DOWN

        # RANGING: default when no strong trend detected
        return cls.RANGING

    @classmethod
    def get_regime_features(cls, df: pd.DataFrame) -> dict:
        """
        Get regime as numeric features for the AI model.

        Returns dict with regime one-hot encoding + regime confidence scores.
        """
        regime = cls.detect(df)

        return {
            "regime": regime,
            "is_trending_up": 1 if regime == cls.TRENDING_UP else 0,
            "is_trending_down": 1 if regime == cls.TRENDING_DOWN else 0,
            "is_ranging": 1 if regime == cls.RANGING else 0,
            "is_volatile": 1 if regime == cls.VOLATILE else 0,
            "is_quiet": 1 if regime == cls.QUIET else 0,
        }

    @classmethod
    def should_trade(cls, regime: str) -> bool:
        """
        Should we trade in this regime?

        QUIET regime = about to break out, but direction unclear → skip
        Other regimes are tradeable with regime-specific adjustments.
        """
        return regime != cls.QUIET

    @classmethod
    def get_regime_adjustments(cls, regime: str) -> dict:
        """
        Get trading parameter adjustments for the current regime.

        Returns multipliers for SL/TP and confidence threshold adjustments.
        """
        adjustments = {
            cls.TRENDING_UP: {
                "sl_multiplier": 1.2,   # Tighter SL in clear trends
                "tp_multiplier": 1.5,   # Let winners run → ~1:3 R:R
                "confidence_bonus": 0.05,
                "favor_direction": "BUY",
            },
            cls.TRENDING_DOWN: {
                "sl_multiplier": 1.2,   # Tighter SL in clear trends
                "tp_multiplier": 1.5,   # Let winners run → ~1:3 R:R
                "confidence_bonus": 0.05,
                "favor_direction": "SELL",
            },
            cls.RANGING: {
                "sl_multiplier": 1.0,   # Tight SL — range trades are short
                "tp_multiplier": 0.9,   # Smaller TP — take profit before reversal
                "confidence_bonus": 0.0,
                "favor_direction": None,
            },
            cls.VOLATILE: {
                "sl_multiplier": 1.8,   # Wider SL — price swings more
                "tp_multiplier": 1.2,   # Decent TP to compensate wider SL
                "confidence_bonus": -0.05,  # Higher bar required
                "favor_direction": None,
            },
            cls.QUIET: {
                "sl_multiplier": 1.2,
                "tp_multiplier": 1.0,
                "confidence_bonus": -0.10,  # Very high bar — usually skip
                "favor_direction": None,
            },
        }

        return adjustments.get(regime, adjustments[cls.RANGING])
