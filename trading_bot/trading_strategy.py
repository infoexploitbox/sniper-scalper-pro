"""
Trading Strategy — orchestrates the AI pipeline.

Flow: Fetch data → Build features → Detect regime → Ensemble predict
     → Smart execute → Log everything
"""

import pandas as pd
from datetime import datetime, timezone
from typing import Optional, Dict

import config
from mt5_connector import MT5Connector
from ai_engine.feature_engine import FeatureEngine
from ai_engine.ensemble_model import EnsembleModel
from ai_engine.regime_detector import RegimeDetector
from ai_engine.database import TradingDatabase
from ai_engine.self_learner import SelfLearner
from smart_executor import SmartExecutor


class TradingStrategy:
    """AI-powered trading strategy with full pipeline orchestration."""

    def __init__(self, mt5: MT5Connector, model: EnsembleModel,
                 db: TradingDatabase, self_learner: SelfLearner,
                 executor: SmartExecutor):
        self.mt5 = mt5
        self.model = model
        self.db = db
        self.self_learner = self_learner
        self.executor = executor

    def analyze_market(self, symbol: str) -> Optional[Dict]:
        """
        Full market analysis pipeline:
        1. Fetch multi-timeframe data
        2. Build 70+ features
        3. Detect market regime
        4. Run ensemble prediction
        5. Return signal with context
        """
        # 1. Fetch multi-timeframe candle data
        candles_by_tf = {}
        for tf in config.MTF_TIMEFRAMES:
            df = self.mt5.get_candles(symbol, tf, count=config.FEATURE_CANDLE_COUNT)
            if not df.empty:
                candles_by_tf[tf] = df

        if config.TRADING_TIMEFRAME not in candles_by_tf:
            print(f"  [{symbol}] No data for entry timeframe {config.TRADING_TIMEFRAME}")
            return None

        # 2. Build features
        df = FeatureEngine.build_features(candles_by_tf, symbol)
        if df is None or df.empty:
            print(f"  [{symbol}] Feature engineering failed")
            return None

        # 3. Detect market regime
        entry_df = candles_by_tf[config.TRADING_TIMEFRAME]
        regime = RegimeDetector.detect(entry_df)

        # 4. Run ensemble prediction
        feature_cols = FeatureEngine.get_feature_columns()
        if not feature_cols or not self.model.is_trained:
            print(f"  [{symbol}] Model not ready (trained={self.model.is_trained})")
            return None

        # Use only feature columns that exist in the dataframe
        available_cols = [c for c in feature_cols if c in df.columns]
        if not available_cols:
            print(f"  [{symbol}] No feature columns available")
            return None

        latest = df.iloc[[-1]]
        signal, confidence, model_votes = self.model.predict(latest)

        # 5. Get current price and ATR
        tick = self.mt5.get_tick(symbol)
        if not tick:
            return None

        current_price = tick["bid"]
        atr = float(df.iloc[-1]["atr"]) if "atr" in df.columns else 0

        # 6. Build result
        result = {
            "symbol": symbol,
            "signal": signal,
            "confidence": confidence,
            "current_price": current_price,
            "atr": atr,
            "regime": regime,
            "model_votes": model_votes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session": self.executor.get_current_session(symbol),
        }

        # Add SL/TP suggestions
        regime_adj = RegimeDetector.get_regime_adjustments(regime)
        sl_distance = atr * 2 * regime_adj["sl_multiplier"]
        tp_distance = atr * 3 * regime_adj["tp_multiplier"]

        if signal == "BUY":
            result["sl"] = current_price - sl_distance
            result["tp"] = current_price + tp_distance
        elif signal == "SELL":
            result["sl"] = current_price + sl_distance
            result["tp"] = current_price - tp_distance

        # 7. Log prediction
        prediction_id = self.db.log_prediction(
            symbol=symbol,
            timeframe=config.TRADING_TIMEFRAME,
            signal=signal,
            confidence=confidence,
            regime=regime,
            model_votes=model_votes,
        )
        result["prediction_id"] = prediction_id

        return result

    def execute_signal(self, signal: Dict) -> Optional[Dict]:
        """
        Decide whether to execute a signal and do it.
        Applies all entry filters and risk checks.
        """
        if signal["signal"] == "HOLD":
            return None

        symbol = signal["symbol"]
        confidence = signal["confidence"]
        regime = signal["regime"]

        # Check adaptive confidence threshold
        if not self.self_learner.should_take_trade(confidence, regime):
            threshold = self.self_learner.get_confidence_threshold()
            print(f"  [{symbol}] Skipped: confidence {confidence:.1%} < threshold {threshold:.1%}")
            return None

        # Check entry filters (session, spread, drawdown, position limits, hedging)
        can_trade, reason = self.executor.can_open_trade(symbol, regime, direction=signal["signal"])
        if not can_trade:
            print(f"  [{symbol}] Skipped: {reason}")
            return None

        # Check regime direction alignment
        regime_adj = RegimeDetector.get_regime_adjustments(regime)
        favored = regime_adj.get("favor_direction")
        if favored and signal["signal"] != favored:
            # Counter-trend trade requires higher confidence
            min_counter_trend = self.self_learner.get_confidence_threshold() + 0.10
            if confidence < min_counter_trend:
                print(f"  [{symbol}] Skipped counter-trend {signal['signal']} in {regime}")
                return None

        # Execute
        return self.executor.execute_trade(signal, signal["prediction_id"])

    def train_model(self, symbol: str) -> Dict:
        """
        Train the ensemble model on historical data.
        Fetches data, builds features, creates labels, and trains.
        """
        print(f"\n{'='*50}")
        print(f"TRAINING AI MODEL — {symbol}")
        print(f"{'='*50}")

        # Fetch multi-timeframe data
        candles_by_tf = {}
        for tf in config.MTF_TIMEFRAMES:
            count = 5000  # Need plenty of data to survive NaN dropping from HTF indicators
            df = self.mt5.get_candles(symbol, tf, count=count)
            if not df.empty:
                candles_by_tf[tf] = df
                print(f"  Loaded {len(df)} {tf} candles")

        if config.TRADING_TIMEFRAME not in candles_by_tf:
            print(f"  Failed to load {config.TRADING_TIMEFRAME} data")
            return {"error": "no_data"}

        # Build features
        print("  Building features...")
        df = FeatureEngine.build_features(candles_by_tf, symbol)
        if df is None or df.empty:
            print("  Feature engineering failed")
            return {"error": "feature_engineering_failed"}

        # Create labels
        print("  Creating labels...")
        threshold = FeatureEngine.get_label_threshold(symbol)
        df = FeatureEngine.create_labels(df, forward_periods=5, threshold=threshold)

        feature_cols = FeatureEngine.get_feature_columns()
        available_cols = [c for c in feature_cols if c in df.columns]

        if not available_cols:
            print("  No feature columns available")
            return {"error": "no_features"}

        # Drop NaN
        df = df.dropna(subset=available_cols + ["label"])
        print(f"  Training on {len(df)} samples with {len(available_cols)} features")

        # Update model's feature columns to match available ones
        self.model.feature_columns = available_cols

        # Train
        result = self.model.train(df, available_cols)

        # Log to database
        if "error" not in result:
            for model_name, metrics in result.get("models", {}).items():
                if "error" not in metrics:
                    self.db.log_model_performance(
                        symbol=symbol,
                        model_name=model_name,
                        metrics=metrics,
                        feature_importance=self.model.feature_importance,
                    )

        print(f"  Training complete for {symbol}")
        return result
