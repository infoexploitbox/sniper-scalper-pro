"""
Ensemble Model — XGBoost + LightGBM + Random Forest with weighted voting.

Each model votes on BUY/HOLD/SELL and provides a confidence score.
Votes are weighted based on each model's recent performance (adaptive weights).
"""

import os
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone
import warnings

# Suppress sklearn/joblib UserWarnings that spam the console
warnings.filterwarnings('ignore', category=UserWarning)

from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb
import lightgbm as lgb
import joblib

import config


class EnsembleModel:
    """
    3-model ensemble: XGBoost + LightGBM + Random Forest.

    Uses weighted voting where weights adapt based on recent performance.
    Each model outputs probabilities for 3 classes: SELL(-1), HOLD(0), BUY(1).
    """

    CLASS_MAP = {0: -1, 1: 0, 2: 1}  # Internal class → signal
    SIGNAL_MAP = {-1: "SELL", 0: "HOLD", 1: "BUY"}
    REVERSE_CLASS_MAP = {-1: 0, 0: 1, 1: 2}  # signal → internal class

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.model_dir = config.get_model_dir(symbol)
        os.makedirs(self.model_dir, exist_ok=True)

        # Models
        self.models: Dict[str, any] = {}
        self.scaler = StandardScaler()
        self.feature_columns: List[str] = []

        # Adaptive weights (start with config defaults)
        self.model_weights = dict(config.INITIAL_MODEL_WEIGHTS)

        # Feature importance
        self.feature_importance: Dict[str, float] = {}

        # Training metadata
        self.last_trained: Optional[str] = None
        self.training_samples: int = 0
        self.is_trained: bool = False

    # ─── Model Building ─────────────────────────────────────

    def _build_xgboost(self, n_features: int) -> xgb.XGBClassifier:
        """Build XGBoost classifier tuned for financial data."""
        return xgb.XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=5,
            gamma=0.1,
            reg_alpha=0.1,  # L1 regularization
            reg_lambda=1.0,  # L2 regularization
            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
            use_label_encoder=False,
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )

    def _build_lightgbm(self, n_features: int) -> lgb.LGBMClassifier:
        """Build LightGBM classifier."""
        return lgb.LGBMClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_samples=20,
            reg_alpha=0.1,
            reg_lambda=1.0,
            objective="multiclass",
            num_class=3,
            metric="multi_logloss",
            random_state=42,
            n_jobs=1,   # Fix: access violation on Windows Server with multi-thread
            verbose=-1,
        )

    def _build_random_forest(self, n_features: int) -> RandomForestClassifier:
        """Build Random Forest classifier."""
        return RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_split=10,
            min_samples_leaf=5,
            max_features="sqrt",
            random_state=42,
            n_jobs=-1,
        )

    # ─── Training ────────────────────────────────────────────

    def train(self, df: pd.DataFrame, feature_columns: List[str]) -> Dict:
        """
        Train the ensemble on labeled data.

        Uses TimeSeriesSplit for proper financial data validation
        (no future leakage).
        """
        self.feature_columns = feature_columns

        # Prepare data
        X = df[feature_columns].values
        y = df["label"].values
        y_classes = np.array([self.REVERSE_CLASS_MAP[v] for v in y])  # -1,0,1 → 0,1,2

        if len(X) < config.MIN_SAMPLES_FOR_TRAINING:
            print(f"[{self.symbol}] Not enough data: {len(X)} < {config.MIN_SAMPLES_FOR_TRAINING}")
            return {"error": "insufficient_data"}

        # Time series split (no shuffling — respect temporal order)
        tscv = TimeSeriesSplit(n_splits=3)
        splits = list(tscv.split(X))
        train_idx, test_idx = splits[-1]  # Use last split for final eval

        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y_classes[train_idx], y_classes[test_idx]

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train each model
        metrics = {}
        builders = {
            "xgboost": self._build_xgboost,
            "lightgbm": self._build_lightgbm,
            "random_forest": self._build_random_forest,
        }

        for name in config.ENSEMBLE_MODELS:
            if name not in builders:
                continue

            print(f"  [{self.symbol}] Training {name}...")
            model = builders[name](X_train_scaled.shape[1])

            try:
                if isinstance(model, (xgb.XGBClassifier, lgb.LGBMClassifier)):
                    model.fit(
                        X_train_scaled, y_train,
                        eval_set=[(X_test_scaled, y_test)],
                    )
                else:
                    model.fit(X_train_scaled, y_train)

                self.models[name] = model

                # Evaluate
                y_pred = model.predict(X_test_scaled)
                metrics[name] = {
                    "accuracy": float(accuracy_score(y_test, y_pred)),
                    "precision": float(precision_score(y_test, y_pred, average="weighted", zero_division=0)),
                    "recall": float(recall_score(y_test, y_pred, average="weighted", zero_division=0)),
                    "f1": float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
                }
                print(f"    {name} accuracy: {metrics[name]['accuracy']:.4f}")

            except Exception as e:
                print(f"    {name} training failed: {e}")
                metrics[name] = {"error": str(e)}

        # Calculate feature importance (averaged across models)
        self._calculate_feature_importance()

        # Save everything
        self.last_trained = datetime.now(timezone.utc).isoformat()
        self.training_samples = len(X)
        self.is_trained = True
        self.save()

        print(f"  [{self.symbol}] Ensemble training complete. Models: {list(self.models.keys())}")

        return {
            "symbol": self.symbol,
            "models": metrics,
            "training_samples": len(X),
            "test_samples": len(X_test),
            "feature_count": len(feature_columns),
            "timestamp": self.last_trained,
        }

    # ─── Prediction ──────────────────────────────────────────

    def predict(self, features: pd.DataFrame) -> Tuple[str, float, Dict]:
        """
        Make a prediction using the weighted ensemble.

        Returns:
            (signal: "BUY"/"SELL"/"HOLD", confidence: float, model_votes: dict)
        """
        if not self.is_trained or not self.models:
            return "HOLD", 0.0, {}

        # Prepare features
        X = features[self.feature_columns].values
        X_scaled = self.scaler.transform(X)

        # Get predictions from each model
        model_votes = {}
        weighted_probs = np.zeros(3)  # SELL, HOLD, BUY probabilities
        total_weight = 0

        for name, model in self.models.items():
            try:
                probs = model.predict_proba(X_scaled)[0]  # [P(SELL), P(HOLD), P(BUY)]
                weight = self.model_weights.get(name, 0.33)

                weighted_probs += probs * weight
                total_weight += weight

                pred_class = np.argmax(probs)
                model_votes[name] = {
                    "signal": self.SIGNAL_MAP[self.CLASS_MAP[pred_class]],
                    "confidence": float(np.max(probs)),
                    "probabilities": {
                        "SELL": float(probs[0]),
                        "HOLD": float(probs[1]),
                        "BUY": float(probs[2]),
                    },
                    "weight": weight,
                }
            except Exception as e:
                print(f"  [{self.symbol}] {name} prediction failed: {e}")

        if total_weight == 0:
            return "HOLD", 0.0, {}

        # Normalize weighted probabilities
        weighted_probs /= total_weight

        # Final prediction
        pred_class = np.argmax(weighted_probs)
        signal = self.SIGNAL_MAP[self.CLASS_MAP[pred_class]]
        confidence = float(weighted_probs[pred_class])

        return signal, confidence, model_votes

    # ─── Feature Importance ──────────────────────────────────

    def _calculate_feature_importance(self):
        """Calculate averaged feature importance across all models."""
        if not self.feature_columns:
            return

        importance_sum = np.zeros(len(self.feature_columns))
        count = 0

        for name, model in self.models.items():
            try:
                if hasattr(model, "feature_importances_"):
                    imp = model.feature_importances_
                    if len(imp) == len(self.feature_columns):
                        importance_sum += imp
                        count += 1
            except Exception:
                pass

        if count > 0:
            avg_importance = importance_sum / count
            self.feature_importance = dict(
                zip(self.feature_columns, avg_importance.tolist())
            )

    def get_top_features(self, n: int = 20) -> List[Tuple[str, float]]:
        """Get the top N most important features."""
        sorted_features = sorted(
            self.feature_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_features[:n]

    # ─── Weight Adaptation ───────────────────────────────────

    def update_weights(self, model_accuracies: Dict[str, float]):
        """
        Update model voting weights based on recent accuracy.

        Models that performed better recently get higher weight.
        """
        if not model_accuracies:
            return

        # Softmax-style weighting based on accuracy
        accs = {k: v for k, v in model_accuracies.items() if k in self.models}
        if not accs:
            return

        # Scale accuracies to prevent extreme weights
        values = list(accs.values())
        exp_vals = {k: np.exp(v * 5) for k, v in accs.items()}  # Temperature = 5
        total = sum(exp_vals.values())

        for name in accs:
            self.model_weights[name] = exp_vals[name] / total

        print(f"  [{self.symbol}] Updated model weights: {self.model_weights}")

    # ─── Persistence ─────────────────────────────────────────

    def save(self):
        """Save all models, scaler, and metadata."""
        os.makedirs(self.model_dir, exist_ok=True)

        # Save each model
        for name, model in self.models.items():
            path = os.path.join(self.model_dir, f"{name}_model.pkl")
            joblib.dump(model, path)

        # Save scaler
        joblib.dump(self.scaler, os.path.join(self.model_dir, "scaler.pkl"))

        # Save metadata
        metadata = {
            "symbol": self.symbol,
            "feature_columns": self.feature_columns,
            "model_weights": self.model_weights,
            "feature_importance": self.feature_importance,
            "last_trained": self.last_trained,
            "training_samples": self.training_samples,
            "is_trained": self.is_trained,
            "models_saved": list(self.models.keys()),
        }
        with open(os.path.join(self.model_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"  [{self.symbol}] Models saved to {self.model_dir}")

    def load(self) -> bool:
        """Load saved models, scaler, and metadata."""
        metadata_path = os.path.join(self.model_dir, "metadata.json")

        if not os.path.exists(metadata_path):
            return False

        try:
            # Load metadata
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            self.feature_columns = metadata["feature_columns"]
            self.model_weights = metadata["model_weights"]
            self.feature_importance = metadata.get("feature_importance", {})
            self.last_trained = metadata["last_trained"]
            self.training_samples = metadata["training_samples"]

            # Load scaler
            scaler_path = os.path.join(self.model_dir, "scaler.pkl")
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)

            # Load models
            for name in metadata.get("models_saved", []):
                model_path = os.path.join(self.model_dir, f"{name}_model.pkl")
                if os.path.exists(model_path):
                    self.models[name] = joblib.load(model_path)

            self.is_trained = bool(self.models)
            print(f"  [{self.symbol}] Loaded {len(self.models)} models from {self.model_dir}")
            return True

        except Exception as e:
            print(f"  [{self.symbol}] Failed to load models: {e}")
            return False

    def get_status(self) -> Dict:
        """Get model status summary."""
        return {
            "symbol": self.symbol,
            "is_trained": self.is_trained,
            "models": list(self.models.keys()),
            "model_weights": self.model_weights,
            "feature_count": len(self.feature_columns),
            "training_samples": self.training_samples,
            "last_trained": self.last_trained,
            "top_features": self.get_top_features(10),
        }
