"""
Feature Engine — generates 70+ features across multiple timeframes.

Features include: trend indicators, momentum, volatility, price action,
session-aware, microstructure, and structural analysis.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from ta.trend import SMAIndicator, EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange

import config


class FeatureEngine:
    """Generate 70+ features for the AI ensemble from raw OHLCV data."""

    # Columns that are features (not metadata)
    FEATURE_COLUMNS = None  # Set dynamically after first build

    @classmethod
    def build_features(cls, candles_by_tf: Dict[str, pd.DataFrame],
                       symbol: str) -> Optional[pd.DataFrame]:
        """
        Build the full feature set from multi-timeframe candle data.

        Args:
            candles_by_tf: Dict mapping timeframe -> DataFrame with OHLCV columns
                           e.g. {"M5": df_m5, "M15": df_m15, "H1": df_h1}
            symbol: Trading symbol (for session-aware features)

        Returns:
            DataFrame with all features for the entry timeframe (M5),
            enriched with higher-TF context. Returns None if insufficient data.
        """
        entry_tf = config.TRADING_TIMEFRAME

        if entry_tf not in candles_by_tf or candles_by_tf[entry_tf].empty:
            return None

        df = candles_by_tf[entry_tf].copy()

        if len(df) < 100:
            return None

        # ── Core features on entry timeframe ────────────────
        df = cls._add_trend_features(df)
        df = cls._add_momentum_features(df)
        df = cls._add_volatility_features(df)
        df = cls._add_price_action_features(df)
        df = cls._add_volume_features(df)
        df = cls._add_structural_features(df)
        df = cls._add_session_features(df, symbol)
        df = cls._add_microstructure_features(df)

        # ── Higher timeframe context ────────────────────────
        for tf_name, tf_df in candles_by_tf.items():
            if tf_name == entry_tf or tf_df.empty or len(tf_df) < 50:
                continue
            df = cls._add_htf_context(df, tf_df, tf_name)

        # ── Clean up ────────────────────────────────────────
        # Identify feature columns (everything except metadata)
        meta_cols = ["time", "open", "high", "low", "close",
                     "tick_volume", "real_volume", "spread", "label"]
        cls.FEATURE_COLUMNS = [c for c in df.columns if c not in meta_cols]

        # Drop rows with NaN (from rolling calculations)
        df = df.dropna(subset=cls.FEATURE_COLUMNS)

        return df

    @classmethod
    def get_feature_columns(cls) -> List[str]:
        """Get the list of feature column names."""
        return cls.FEATURE_COLUMNS or []

    # ─── Trend Features ─────────────────────────────────────

    @staticmethod
    def _add_trend_features(df: pd.DataFrame) -> pd.DataFrame:
        """Moving averages, MACD, ADX, trend strength."""
        close = df["close"]

        # EMAs
        for period in [8, 13, 21, 50]:
            ema = EMAIndicator(close=close, window=period).ema_indicator()
            df[f"ema_{period}"] = ema
            df[f"close_vs_ema_{period}"] = (close - ema) / ema

        # SMA 200 (long-term trend context)
        if len(df) >= 200:
            sma200 = SMAIndicator(close=close, window=200).sma_indicator()
            df["sma_200"] = sma200
            df["close_vs_sma_200"] = (close - sma200) / sma200
        else:
            df["sma_200"] = np.nan
            df["close_vs_sma_200"] = np.nan

        # EMA crossover signals
        df["ema_8_13_cross"] = (df["ema_8"] - df["ema_13"]) / close
        df["ema_13_21_cross"] = (df["ema_13"] - df["ema_21"]) / close
        df["ema_21_50_cross"] = (df["ema_21"] - df["ema_50"]) / close

        # EMA alignment score (-1 to 1): fully bearish to fully bullish
        df["ema_alignment"] = (
            np.sign(df["ema_8"] - df["ema_13"]) +
            np.sign(df["ema_13"] - df["ema_21"]) +
            np.sign(df["ema_21"] - df["ema_50"])
        ) / 3

        # MACD
        macd = MACD(close=close)
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_hist"] = macd.macd_diff()
        df["macd_hist_change"] = df["macd_hist"].diff()  # Acceleration

        # ADX — trend strength
        try:
            adx = ADXIndicator(high=df["high"], low=df["low"], close=close, window=14)
            df["adx"] = adx.adx()
            df["di_plus"] = adx.adx_pos()
            df["di_minus"] = adx.adx_neg()
            df["di_diff"] = df["di_plus"] - df["di_minus"]
        except Exception:
            df["adx"] = 25
            df["di_plus"] = 25
            df["di_minus"] = 25
            df["di_diff"] = 0

        return df

    # ─── Momentum Features ──────────────────────────────────

    @staticmethod
    def _add_momentum_features(df: pd.DataFrame) -> pd.DataFrame:
        """RSI, Stochastic, momentum quality indicators."""
        close = df["close"]

        # RSI
        rsi = RSIIndicator(close=close, window=14).rsi()
        df["rsi"] = rsi
        df["rsi_slope"] = rsi.diff(3)  # RSI direction over 3 bars

        # RSI zones (normalized: 0 = oversold, 1 = overbought)
        df["rsi_zone"] = (rsi - 30) / 40  # Maps 30-70 to 0-1

        # Stochastic
        stoch = StochasticOscillator(
            high=df["high"], low=df["low"], close=close, window=14
        )
        df["stoch_k"] = stoch.stoch()
        df["stoch_d"] = stoch.stoch_signal()
        df["stoch_cross"] = df["stoch_k"] - df["stoch_d"]

        # Rate of change
        for period in [3, 5, 10]:
            df[f"roc_{period}"] = close.pct_change(period)

        # Momentum quality: is momentum increasing or fading?
        df["momentum_quality"] = (
            df["roc_3"].rolling(3).mean() - df["roc_3"].rolling(10).mean()
        )

        return df

    # ─── Volatility Features ────────────────────────────────

    @staticmethod
    def _add_volatility_features(df: pd.DataFrame) -> pd.DataFrame:
        """ATR, Bollinger Bands, volatility regime classification."""
        close = df["close"]
        high = df["high"]
        low = df["low"]

        # ATR
        atr = AverageTrueRange(high=high, low=low, close=close, window=14)
        df["atr"] = atr.average_true_range()
        df["atr_percent"] = df["atr"] / close  # Normalized ATR

        # ATR percentile (is current vol high or low relative to recent history?)
        df["atr_percentile"] = df["atr"].rolling(100).rank(pct=True)

        # Bollinger Bands
        bb = BollingerBands(close=close, window=20, window_dev=2)
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_lower"] = bb.bollinger_lband()
        df["bb_mid"] = bb.bollinger_mavg()
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]
        df["bb_position"] = (close - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])

        # BB squeeze detection (volatility contraction)
        bb_width_sma = df["bb_width"].rolling(50).mean()
        df["bb_squeeze"] = (df["bb_width"] < bb_width_sma * 0.75).astype(int)

        # High-Low range normalized
        df["hl_range"] = (high - low) / close

        # Range expansion (current range vs average)
        df["range_expansion"] = df["hl_range"] / df["hl_range"].rolling(20).mean()

        return df

    # ─── Price Action Features ──────────────────────────────

    @staticmethod
    def _add_price_action_features(df: pd.DataFrame) -> pd.DataFrame:
        """Candlestick patterns, engulfing, pin bars, inside bars."""
        o, h, l, c = df["open"], df["high"], df["low"], df["close"]

        body = (c - o).abs()
        full_range = h - l
        upper_wick = h - pd.concat([c, o], axis=1).max(axis=1)
        lower_wick = pd.concat([c, o], axis=1).min(axis=1) - l

        # Body ratio (body / total range)
        df["body_ratio"] = body / full_range.replace(0, np.nan)

        # Upper/Lower wick ratios
        df["upper_wick_ratio"] = upper_wick / full_range.replace(0, np.nan)
        df["lower_wick_ratio"] = lower_wick / full_range.replace(0, np.nan)

        # Bullish/Bearish candle (1 = bullish, -1 = bearish)
        df["candle_direction"] = np.sign(c - o)

        # Consecutive same-direction candles
        direction = np.sign(c - o)
        groups = (direction != direction.shift()).cumsum()
        df["consecutive_candles"] = direction.groupby(groups).cumcount() + 1
        df["consecutive_candles"] *= direction  # Negative for bearish streaks

        # Close position in range (0 = closed at low, 1 = closed at high)
        df["close_position"] = (c - l) / full_range.replace(0, np.nan)

        # Engulfing pattern (simplified)
        prev_body = body.shift(1)
        df["bullish_engulfing"] = (
            (direction.shift(1) == -1) & (direction == 1) &
            (body > prev_body * 1.1)
        ).astype(int)
        df["bearish_engulfing"] = (
            (direction.shift(1) == 1) & (direction == -1) &
            (body > prev_body * 1.1)
        ).astype(int)

        # Pin bar detection
        df["bullish_pin"] = (
            (lower_wick > body * 2) & (upper_wick < body * 0.5)
        ).astype(int)
        df["bearish_pin"] = (
            (upper_wick > body * 2) & (lower_wick < body * 0.5)
        ).astype(int)

        # Inside bar
        df["inside_bar"] = (
            (h < h.shift(1)) & (l > l.shift(1))
        ).astype(int)

        return df

    # ─── Volume Features ────────────────────────────────────

    @staticmethod
    def _add_volume_features(df: pd.DataFrame) -> pd.DataFrame:
        """Volume analysis: relative volume, volume-price correlation."""
        vol_col = "tick_volume" if "tick_volume" in df.columns else "volume"

        if vol_col not in df.columns:
            df["volume_ratio"] = 1.0
            df["volume_sma_ratio"] = 1.0
            df["volume_trend"] = 0.0
            return df

        vol = df[vol_col].astype(float)

        # Relative volume (current vs 20-period average)
        vol_sma = vol.rolling(20).mean()
        df["volume_ratio"] = vol / vol_sma.replace(0, np.nan)

        # Volume trend (is volume increasing or decreasing?)
        df["volume_trend"] = vol.rolling(5).mean() / vol.rolling(20).mean()

        # Volume-price divergence (high volume + small move = absorption)
        df["vol_price_divergence"] = df["volume_ratio"] / (
            df["hl_range"].rolling(5).mean() / df["hl_range"].rolling(20).mean()
        ).replace(0, np.nan)

        return df

    # ─── Structural Features ────────────────────────────────

    @staticmethod
    def _add_structural_features(df: pd.DataFrame) -> pd.DataFrame:
        """Support/Resistance, swing highs/lows, pivot points."""
        h, l, c = df["high"], df["low"], df["close"]

        # Rolling support and resistance
        df["resistance_20"] = h.rolling(20).max()
        df["support_20"] = l.rolling(20).min()
        df["dist_to_resistance"] = (df["resistance_20"] - c) / c
        df["dist_to_support"] = (c - df["support_20"]) / c

        # Position in range (0 = at support, 1 = at resistance)
        sr_range = df["resistance_20"] - df["support_20"]
        df["position_in_range"] = (c - df["support_20"]) / sr_range.replace(0, np.nan)

        # Pivot points (classic)
        pp = (h.shift(1) + l.shift(1) + c.shift(1)) / 3
        df["pivot"] = pp
        df["r1"] = 2 * pp - l.shift(1)
        df["s1"] = 2 * pp - h.shift(1)
        df["dist_to_pivot"] = (c - pp) / c

        # Higher-high, lower-low detection (market structure)
        swing_high = h.rolling(10).max()
        swing_low = l.rolling(10).min()
        df["making_higher_highs"] = (swing_high > swing_high.shift(10)).astype(int)
        df["making_lower_lows"] = (swing_low < swing_low.shift(10)).astype(int)

        # Market structure score
        df["structure_score"] = df["making_higher_highs"] - df["making_lower_lows"]

        return df

    # ─── Session-Aware Features ─────────────────────────────

    @staticmethod
    def _add_session_features(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Time-of-day and session features."""
        if "time" not in df.columns:
            # Add placeholder session features
            df["hour_sin"] = 0
            df["hour_cos"] = 0
            df["day_of_week"] = 0
            df["is_session_active"] = 1
            df["time_in_session"] = 0.5
            return df

        times = pd.to_datetime(df["time"])

        # Cyclical time encoding (so 23:00 is close to 00:00)
        hour = times.dt.hour + times.dt.minute / 60
        df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
        df["hour_cos"] = np.cos(2 * np.pi * hour / 24)

        # Day of week (0 = Monday)
        df["day_of_week"] = times.dt.dayofweek / 6  # Normalized 0-1

        # Is within trading session?
        session_windows = config.get_session_windows(symbol)
        df["is_session_active"] = 0
        for start_hour, end_hour in session_windows:
            mask = (times.dt.hour >= start_hour) & (times.dt.hour < end_hour)
            df.loc[mask, "is_session_active"] = 1

        # Time within session (0 = session start, 1 = session end)
        if session_windows:
            start, end = session_windows[0]
            session_length = end - start
            df["time_in_session"] = np.clip(
                (times.dt.hour - start) / max(session_length, 1), 0, 1
            )
        else:
            df["time_in_session"] = 0.5

        return df

    # ─── Microstructure Features ────────────────────────────

    @staticmethod
    def _add_microstructure_features(df: pd.DataFrame) -> pd.DataFrame:
        """Market microstructure: spread, tick patterns."""
        # Spread (if available)
        if "spread" in df.columns:
            spread = df["spread"].astype(float)
            df["spread_percentile"] = spread.rolling(100).rank(pct=True)
            df["spread_vs_avg"] = spread / spread.rolling(50).mean().replace(0, np.nan)
        else:
            df["spread_percentile"] = 0.5
            df["spread_vs_avg"] = 1.0

        # Price change acceleration
        price_change = df["close"].pct_change()
        df["price_acceleration"] = price_change.diff()

        # Choppy vs smooth price action (efficiency ratio)
        net_change = abs(df["close"] - df["close"].shift(10))
        sum_changes = df["close"].diff().abs().rolling(10).sum()
        df["efficiency_ratio"] = net_change / sum_changes.replace(0, np.nan)

        return df

    # ─── Higher Timeframe Context ───────────────────────────

    @staticmethod
    def _add_htf_context(df: pd.DataFrame, htf_df: pd.DataFrame,
                         tf_name: str) -> pd.DataFrame:
        """Add higher-timeframe trend/momentum context as features."""
        prefix = f"htf_{tf_name.lower()}"
        htf = htf_df.copy()

        if len(htf) < 50:
            return df

        close = htf["close"]

        # HTF trend direction (EMA 21 slope)
        ema21 = EMAIndicator(close=close, window=21).ema_indicator()
        htf[f"{prefix}_trend"] = (close - ema21) / ema21

        # HTF RSI
        htf[f"{prefix}_rsi"] = RSIIndicator(close=close, window=14).rsi()

        # HTF ADX
        try:
            adx = ADXIndicator(high=htf["high"], low=htf["low"],
                               close=close, window=14)
            htf[f"{prefix}_adx"] = adx.adx()
        except Exception:
            htf[f"{prefix}_adx"] = 25

        # HTF candle direction
        htf[f"{prefix}_direction"] = np.sign(close - htf["open"])

        # Select only the context columns
        context_cols = [c for c in htf.columns if c.startswith(prefix)]

        if "time" in htf.columns:
            htf_context = htf[["time"] + context_cols].copy()
            htf_context["time"] = pd.to_datetime(htf_context["time"])

            # Forward-fill HTF values onto the entry-TF dataframe
            if "time" in df.columns:
                df["time"] = pd.to_datetime(df["time"])
                df = pd.merge_asof(
                    df.sort_values("time"),
                    htf_context.sort_values("time"),
                    on="time",
                    direction="backward"
                )
        else:
            # Fallback: just use the last HTF values as constants
            for col in context_cols:
                last_val = htf[col].dropna().iloc[-1] if not htf[col].dropna().empty else 0
                df[col] = last_val

        return df

    # ─── Label Creation (Triple-Barrier Method) ──────────────

    @staticmethod
    def create_labels(df: pd.DataFrame, forward_periods: int = 15,
                      threshold: float = 0.0003) -> pd.DataFrame:
        """
        Triple-Barrier Labeling Method:
        Simulates Stop-Loss, Take-Profit, and Time-decay barriers for each candle.
        1 = BUY wins (TP hit before SL)
        -1 = SELL wins (SL hit or downward move)
        0 = HOLD (neither barrier reached within horizon)
        """
        df = df.copy()
        n = len(df)
        if n <= forward_periods:
            return df

        labels = np.zeros(n, dtype=int)
        closes = df["close"].values
        highs = df["high"].values if "high" in df.columns else closes
        lows = df["low"].values if "low" in df.columns else closes
        atrs = df["atr"].values if "atr" in df.columns else closes * 0.001

        for i in range(n - forward_periods):
            entry = closes[i]
            atr = atrs[i] if not np.isnan(atrs[i]) and atrs[i] > 0 else entry * 0.001

            # Training labels: use realistic barriers for M5 timeframe
            # Live 1:2 R:R is enforced in smart_executor, not here
            tp_distance = atr * 2.5   # Achievable TP on M5 in 15 forward periods
            sl_distance = atr * 2.0   # Standard SL barrier

            upper_barrier = entry + tp_distance
            lower_barrier = entry - sl_distance

            outcome = 0
            for j in range(1, forward_periods + 1):
                idx = i + j
                h = highs[idx]
                l = lows[idx]

                hit_upper = h >= upper_barrier
                hit_lower = l <= lower_barrier

                if hit_upper and not hit_lower:
                    outcome = 1   # Bullish TP hit first
                    break
                elif hit_lower and not hit_upper:
                    outcome = -1  # Bearish SL hit first
                    break
                elif hit_upper and hit_lower:
                    outcome = 0   # Volatile spike in both directions
                    break

            if outcome == 0:
                # Vertical barrier (time expiration): check net return at horizon end
                future_ret = (closes[i + forward_periods] - entry) / entry
                if future_ret > threshold:
                    outcome = 1
                elif future_ret < -threshold:
                    outcome = -1

            labels[i] = outcome

        df["label"] = labels
        # Trim unlabelled tail
        df = df.iloc[:-forward_periods].copy()
        return df


    @staticmethod
    def get_label_threshold(symbol: str) -> float:
        """Get appropriate label threshold for a symbol."""
        # Gold has larger moves, needs higher threshold
        if "XAU" in symbol or "GOLD" in symbol:
            return 0.0005  # 5 pips on gold ~= $0.50 move
        elif "JPY" in symbol:
            return 0.0003
        else:
            return 0.0002  # Standard forex
