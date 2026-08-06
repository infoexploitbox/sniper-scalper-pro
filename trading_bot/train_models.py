import os
import sys
import time
import pandas as pd
from typing import Dict, List, Optional

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mt5_connector import MT5Connector
from ai_engine.feature_engine import FeatureEngine
from ai_engine.ensemble_model import EnsembleModel
from ai_engine.data_loader import DataLoader
import config

DEFAULT_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD", "BTCUSD"]

def train_ensemble_for_symbol(symbol: str, timeframe: str = "H1", csv_path: Optional[str] = None) -> Dict:
    """
    Train AI Ensemble (XGBoost + LightGBM + Random Forest) for a single symbol
    using multi-year historical data.
    """
    print(f"\n{'='*70}")
    print(f"   STARTING MULTI-YEAR AI TRAINING — {symbol} ({timeframe})")
    print(f"{'='*70}\n")

    candles_by_tf = {}
    df = None

    # 1. Load custom CSV if provided
    if csv_path and os.path.exists(csv_path):
        print(f"[1/4] Loading custom historical dataset from CSV: {csv_path}")
        df = DataLoader.load_csv(csv_path, symbol)

    # 2. Try fetching maximum history from MT5
    if df is None or df.empty:
        print(f"[1/4] Fetching historical candle data from MT5 for {symbol}...")
        mt5 = MT5Connector()
        if mt5.connect():
            for count in [100000, 70000, 50000, 30000, 10000]:
                raw_df = mt5.get_candles(symbol, timeframe, count=count)
                if not raw_df.empty and len(raw_df) >= 500:
                    df = raw_df
                    print(f"  [OK] Fetched {len(df)} candles from MT5 (From {df['time'].iloc[0]} to {df['time'].iloc[-1]})")
                    break

    # 3. Fallback to Yahoo Finance if MT5 history is short
    if df is None or df.empty:
        print(f"[1/4] Falling back to Yahoo Finance 2-year history for {symbol}...")
        df = DataLoader.fetch_yfinance_data(symbol, period="2y", interval="1h")

    if df is None or df.empty:
        print(f"[FAIL] Unable to acquire historical data for {symbol}")
        return {"symbol": symbol, "status": "failed", "reason": "No data"}

    candles_by_tf[timeframe] = df
    original_tf = config.TRADING_TIMEFRAME
    config.TRADING_TIMEFRAME = timeframe

    # Fetch higher timeframe data if MT5 is available
    mt5 = MT5Connector()
    if mt5.connect():
        htf = "H4" if timeframe == "H1" else "H1"
        htf_df = mt5.get_candles(symbol, htf, count=5000)
        if not htf_df.empty:
            candles_by_tf[htf] = htf_df

    # 2. Feature Engineering
    print(f"\n[2/4] Building 70+ technical & price action features...")
    featured_df = FeatureEngine.build_features(candles_by_tf, symbol)
    config.TRADING_TIMEFRAME = original_tf


    if featured_df is None or featured_df.empty:
        print(f"[FAIL] Feature engineering returned empty dataframe for {symbol}")
        return {"symbol": symbol, "status": "failed", "reason": "Feature engineering failed"}

    # 3. Triple-Barrier Method Labeling
    print(f"[3/4] Creating Triple-Barrier labels (ATR Stop Loss, Take Profit & Expiration)...")
    threshold = FeatureEngine.get_label_threshold(symbol)
    featured_df = FeatureEngine.create_labels(featured_df, forward_periods=15, threshold=threshold)

    feature_cols = FeatureEngine.get_feature_columns()
    available_cols = [c for c in feature_cols if c in featured_df.columns]
    featured_df = featured_df.dropna(subset=available_cols + ["label"])

    print(f"  [OK] Clean dataset size: {len(featured_df)} samples with {len(available_cols)} features")

    # Split 70% Train, 30% Validation
    split_idx = int(len(featured_df) * 0.7)
    train_df = featured_df.iloc[:split_idx].copy()
    val_df = featured_df.iloc[split_idx:].copy()

    print(f"  Train Set: {len(train_df)} samples | Validation Set: {len(val_df)} samples")

    # 4. Train AI Ensemble
    print(f"\n[4/4] Training Ensemble (XGBoost + LightGBM + Random Forest)...")
    model = EnsembleModel(symbol)
    metrics = model.train(train_df, available_cols)

    if "error" in metrics:
        print(f"[FAIL] Ensemble training failed: {metrics['error']}")
        return {"symbol": symbol, "status": "failed", "reason": metrics["error"]}

    print(f"\n{'='*60}")
    print(f"   TRAINING RESULTS — {symbol}")
    print(f"{'='*60}")
    for m_name, m_stats in metrics.get("models", {}).items():
        if "accuracy" in m_stats:
            print(f"   - {m_name}: Accuracy = {m_stats['accuracy']*100:.2f}% | Precision = {m_stats.get('precision',0)*100:.2f}%")

    top_feats = model.get_top_features(8)
    print(f"\n   Top Feature Importances:")
    for feat, imp in top_feats:
        print(f"     * {feat}: {imp:.4f}")

    print(f"\n  [SUCCESS] Ensemble model trained & saved to trading_bot/models/{symbol}/\n")

    return {
        "symbol": symbol,
        "status": "success",
        "samples": len(featured_df),
        "features_count": len(available_cols),
        "metrics": metrics,
        "top_features": top_feats,
    }

def train_all_symbols(symbols: Optional[List[str]] = None, timeframe: str = "H1"):
    """Train AI models across all 7 portfolio pairs."""
    symbols = symbols or DEFAULT_PAIRS
    results = {}

    print(f"\n============================================================")
    print(f"   AI ENSEMBLE MULTI-PAIR PORTFOLIO TRAINING (7 PAIRS)")
    print(f"   Pairs: {', '.join(symbols)}")
    print(f"============================================================\n")

    start_time = time.time()
    for sym in symbols:
        try:
            res = train_ensemble_for_symbol(sym, timeframe=timeframe)
            results[sym] = res
        except Exception as e:
            print(f"  [ERROR] Failed to train {sym}: {e}")
            results[sym] = {"symbol": sym, "status": "error", "reason": str(e)}

    elapsed = time.time() - start_time
    print(f"\n============================================================")
    print(f"   PORTFOLIO TRAINING COMPLETED IN {elapsed/60:.2f} MINUTES")
    print(f"============================================================")
    for sym, res in results.items():
        st = res.get("status", "unknown").upper()
        samples = res.get("samples", 0)
        print(f"   [{st}] {sym}: {samples} training samples processed")

    return results

if __name__ == "__main__":
    train_all_symbols()
