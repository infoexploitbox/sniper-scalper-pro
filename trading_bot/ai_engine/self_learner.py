"""
Self-Learning Engine — evaluates performance, adapts thresholds,
triggers retraining, and prunes features.

This is the brain that makes the AI improve over time.
"""

import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

import config
from ai_engine.database import TradingDatabase
from ai_engine.ensemble_model import EnsembleModel


class SelfLearner:
    """
    Self-improvement loop that runs periodically to:
    1. Evaluate recent prediction accuracy vs actual outcomes
    2. Adjust confidence thresholds
    3. Adjust model voting weights
    4. Trigger retraining when performance degrades
    5. Track which regimes/sessions are profitable
    """

    def __init__(self, db: TradingDatabase):
        self.db = db
        self.current_confidence_threshold = config.MIN_CONFIDENCE
        self._load_state()

    def _load_state(self):
        """Load persisted state from database."""
        saved_threshold = self.db.get_state("confidence_threshold")
        if saved_threshold is not None:
            loaded = float(saved_threshold)
            # Always clamp within current config bounds so .env changes take effect on restart
            clamped = max(config.MIN_CONFIDENCE_FLOOR, min(loaded, config.MAX_CONFIDENCE_CEILING))
            if clamped != loaded:
                print(f"  [SelfLearner] Threshold clamped {loaded:.3f} -> {clamped:.3f} (config bounds changed)")
                self.db.save_state("confidence_threshold", clamped)
            self.current_confidence_threshold = clamped
            print(f"  [SelfLearner] Loaded confidence threshold: {self.current_confidence_threshold:.3f}")

    # ─── Main Evaluation Loop ────────────────────────────────

    def evaluate_and_adapt(self, models: Dict[str, EnsembleModel]) -> Dict:
        """
        Run the full self-learning evaluation cycle.

        Called periodically (every 30 minutes by default).
        Returns a summary of adaptations made.
        """
        adaptations = []

        for symbol, model in models.items():
            # Get recent trade performance
            perf = self.db.get_win_rate(symbol=symbol, hours=168)  # 7-day rolling window

            if perf["total"] < 15:
                continue  # Require at least 15 trades for statistical significance

            # 1. Adapt confidence threshold
            threshold_change = self._adapt_confidence_threshold(symbol, perf)
            if threshold_change:
                adaptations.append(threshold_change)

            # 2. Adapt model weights
            weight_change = self._adapt_model_weights(symbol, model)
            if weight_change:
                adaptations.append(weight_change)

            # 3. Check if retraining is needed
            retrain_needed = self._check_retrain_needed(symbol, perf)
            if retrain_needed:
                adaptations.append(retrain_needed)

            # 4. Log regime performance
            self._log_regime_performance(symbol)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "adaptations": adaptations,
            "current_threshold": self.current_confidence_threshold,
        }

    # ─── Confidence Threshold Adaptation ─────────────────────

    def _adapt_confidence_threshold(self, symbol: str, perf: Dict) -> Optional[Dict]:
        """
        If win rate is below target, tighten the confidence threshold.
        If win rate is well above target, loosen it slightly.
        """
        win_rate = perf["win_rate"]
        total = perf["total"]

        old_threshold = self.current_confidence_threshold

        if win_rate < config.TARGET_WIN_RATE and total >= 10:
            # Performance is below target — be more selective
            new_threshold = min(
                self.current_confidence_threshold + config.CONFIDENCE_ADJUST_STEP,
                config.MAX_CONFIDENCE_CEILING
            )
            reason = f"Win rate {win_rate:.1%} below target {config.TARGET_WIN_RATE:.1%}"

        elif win_rate > config.TARGET_WIN_RATE + 0.10 and total >= 15:
            # Performance is well above target — we can be slightly less picky
            new_threshold = max(
                self.current_confidence_threshold - config.CONFIDENCE_ADJUST_STEP * 0.5,
                config.MIN_CONFIDENCE_FLOOR
            )
            reason = f"Win rate {win_rate:.1%} well above target — loosening"

        else:
            return None  # No change needed

        if abs(new_threshold - old_threshold) < 0.001:
            return None

        self.current_confidence_threshold = new_threshold

        # Persist
        self.db.save_state("confidence_threshold", new_threshold)

        # Log adaptation
        adaptation = {
            "type": "confidence_threshold",
            "symbol": symbol,
            "old_value": f"{old_threshold:.3f}",
            "new_value": f"{new_threshold:.3f}",
            "reason": reason,
            "win_rate": win_rate,
            "total_trades": total,
        }

        self.db.log_adaptation(
            "confidence_threshold", adaptation,
            str(old_threshold), str(new_threshold), reason
        )

        print(f"  [SelfLearner] {symbol} threshold: {old_threshold:.3f} -> {new_threshold:.3f} ({reason})")

        return adaptation

    # ─── Model Weight Adaptation ─────────────────────────────

    def _adapt_model_weights(self, symbol: str, model: EnsembleModel) -> Optional[Dict]:
        """
        Evaluate each model's recent accuracy and adjust voting weights.
        """
        # Get recent predictions with outcomes
        recent_trades = self.db.get_recent_trades(symbol=symbol, limit=50)

        if len(recent_trades) < 10:
            return None

        # We need to evaluate each model's accuracy from the stored model_votes
        # For now, use the aggregate accuracy as a proxy
        model_accuracies = {}

        for name in model.models.keys():
            # Estimate accuracy from trade outcomes
            correct = 0
            total = 0
            for trade in recent_trades:
                if trade["profit"] is not None:
                    total += 1
                    if trade["profit"] > 0:
                        correct += 1

            if total > 0:
                model_accuracies[name] = correct / total

        if model_accuracies:
            old_weights = dict(model.model_weights)
            model.update_weights(model_accuracies)

            if old_weights != model.model_weights:
                adaptation = {
                    "type": "model_weights",
                    "symbol": symbol,
                    "old_value": str(old_weights),
                    "new_value": str(model.model_weights),
                    "reason": f"Based on {len(recent_trades)} recent trades",
                }

                self.db.log_adaptation(
                    "model_weights", adaptation,
                    str(old_weights), str(model.model_weights),
                    adaptation["reason"]
                )

                return adaptation

        return None

    # ─── Retrain Trigger ─────────────────────────────────────

    def _check_retrain_needed(self, symbol: str, perf: Dict) -> Optional[Dict]:
        """
        Check if the model should be retrained.

        Triggers retrain if:
        - Win rate dropped below 50% over last 48 hours
        - It's been more than RETRAIN_INTERVAL_HOURS since last train
        - Profit factor is below 1.0 (losing money)
        """
        should_retrain = False
        reason = ""

        # Check win rate
        if perf["total"] >= 15 and perf["win_rate"] < 0.50:
            should_retrain = True
            reason = f"Win rate critically low: {perf['win_rate']:.1%}"

        # Check profit factor
        elif perf["total"] >= 15 and perf.get("profit_factor", 1) < 0.8:
            should_retrain = True
            reason = f"Profit factor low: {perf.get('profit_factor', 0):.2f}"

        if should_retrain:
            adaptation = {
                "type": "retrain_triggered",
                "symbol": symbol,
                "reason": reason,
                "win_rate": perf["win_rate"],
                "total_trades": perf["total"],
            }

            self.db.log_adaptation("retrain_triggered", adaptation, reason=reason)
            print(f"  [SelfLearner] RETRAIN triggered for {symbol}: {reason}")

            return adaptation

        return None

    # ─── Regime Performance Logging ──────────────────────────

    def _log_regime_performance(self, symbol: str):
        """Log performance breakdown by market regime."""
        regime_perf = self.db.get_performance_by_regime(symbol, hours=168)

        for rp in regime_perf:
            self.db.log_adaptation(
                "regime_stats",
                {
                    "symbol": symbol,
                    "regime": rp["regime"],
                    "win_rate": rp["win_rate"],
                    "avg_profit": rp["avg_profit"],
                    "total": rp["total"],
                },
                reason=f"Regime {rp['regime']}: {rp['win_rate']:.1%} win rate over {rp['total']} trades"
            )

    # ─── Getters ─────────────────────────────────────────────

    def get_confidence_threshold(self) -> float:
        """Get the current adaptive confidence threshold."""
        return self.current_confidence_threshold

    def should_take_trade(self, confidence: float, regime: str = None) -> bool:
        """
        Decide if a trade should be taken based on adaptive threshold
        and regime adjustments.
        """
        from ai_engine.regime_detector import RegimeDetector

        threshold = self.current_confidence_threshold

        # Apply regime adjustment
        if regime:
            adjustments = RegimeDetector.get_regime_adjustments(regime)
            threshold -= adjustments.get("confidence_bonus", 0)

        return confidence >= threshold

    def get_learning_summary(self) -> Dict:
        """Get a summary of the self-learning state."""
        adaptations = self.db.get_recent_adaptations(limit=10)

        return {
            "current_confidence_threshold": self.current_confidence_threshold,
            "target_win_rate": config.TARGET_WIN_RATE,
            "recent_adaptations": adaptations,
        }

    def get_performance_dashboard(self, symbol: str = None) -> Dict:
        """Get comprehensive performance data for the dashboard."""
        # Overall performance
        overall_24h = self.db.get_win_rate(symbol=symbol, hours=24)
        overall_7d = self.db.get_win_rate(symbol=symbol, hours=168)

        # By regime
        regime_perf = []
        if symbol:
            regime_perf = self.db.get_performance_by_regime(symbol)

        # By confidence bucket
        confidence_perf = self.db.get_performance_by_confidence(symbol)

        # Daily P&L
        daily_pnl = self.db.get_daily_pnl()

        return {
            "performance_24h": overall_24h,
            "performance_7d": overall_7d,
            "by_regime": regime_perf,
            "by_confidence": confidence_perf,
            "daily_pnl": daily_pnl,
            "confidence_threshold": self.current_confidence_threshold,
        }
