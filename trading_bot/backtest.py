"""
Backtester — walk-forward testing using the new AI ensemble engine.

Tests the strategy on historical data with proper train/test split,
no future leakage, and comprehensive performance reporting.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional

import config
from mt5_connector import MT5Connector
from ai_engine.feature_engine import FeatureEngine
from ai_engine.ensemble_model import EnsembleModel
from ai_engine.regime_detector import RegimeDetector


class Backtester:
    """Walk-forward backtest using the AI ensemble engine."""

    def __init__(self, symbol: str, initial_balance: float = 10.0, log_callback=None):
        self.symbol = symbol
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity = initial_balance
        self.mt5 = MT5Connector()
        self.trades: List[Dict] = []
        self.equity_curve: List[Dict] = []
        self.log_callback = log_callback

    def log(self, msg: str):
        print(msg)
        if self.log_callback:
            try:
                self.log_callback(msg)
            except Exception:
                pass

    def run_backtest(self, months: int = 3, timeframe: str = "M5") -> Optional[List[Dict]]:
        """Run walk-forward backtest."""
        self.log(f"\n{'='*60}")
        self.log(f"  BACKTESTING {self.symbol} — AI Ensemble Engine")
        self.log(f"{'='*60}")
        self.log(f"  Initial Balance: ${self.initial_balance}")
        self.log(f"  Timeframe: {timeframe}")
        self.log(f"{'='*60}\n")

        # Connect to MT5
        if not self.mt5.connect():
            self.log("  [FAIL] Failed to connect to MT5")
            return None

        # Fetch data
        self.log("  Fetching historical candle data...")
        candles_by_tf = {}

        # Get entry timeframe data (up to 1 year of candles)
        for count in [70000, 50000, 20000, 10000, 5000]:
            df = self.mt5.get_candles(self.symbol, timeframe, count=count)
            if not df.empty and len(df) >= 500:
                candles_by_tf[timeframe] = df
                break

        if timeframe not in candles_by_tf:
            self.log("  [FAIL] Failed to fetch candle data from MT5")
            return None

        # Also fetch higher timeframes for context
        for tf in ["M15", "H1"]:
            if tf != timeframe:
                htf_df = self.mt5.get_candles(self.symbol, tf, count=2000)
                if not htf_df.empty:
                    candles_by_tf[tf] = htf_df

        df = candles_by_tf[timeframe]
        self.log(f"  [OK] Loaded {len(df)} {timeframe} candles")
        self.log(f"    From: {df['time'].iloc[0]}")
        self.log(f"    To:   {df['time'].iloc[-1]}")

        # Temporarily set trading timeframe to backtest timeframe
        original_tf = config.TRADING_TIMEFRAME
        config.TRADING_TIMEFRAME = timeframe

        # Build features
        self.log("\n  Building 70+ technical & price action features...")
        featured_df = FeatureEngine.build_features(candles_by_tf, self.symbol)

        if featured_df is None or featured_df.empty:
            self.log("  [FAIL] Feature engineering failed")
            config.TRADING_TIMEFRAME = original_tf
            return None

        # Create labels
        threshold = FeatureEngine.get_label_threshold(self.symbol)
        featured_df = FeatureEngine.create_labels(featured_df, forward_periods=15,
                                                   threshold=threshold)

        feature_cols = FeatureEngine.get_feature_columns()
        available_cols = [c for c in feature_cols if c in featured_df.columns]
        featured_df = featured_df.dropna(subset=available_cols + ["label"])

        self.log(f"  [OK] {len(featured_df)} samples ready with {len(available_cols)} features")

        # Split: 70% train, 30% test
        split_idx = int(len(featured_df) * 0.7)
        train_df = featured_df.iloc[:split_idx].copy()
        test_df = featured_df.iloc[split_idx:].copy()

        self.log(f"  Train Set: {len(train_df)} samples | Test Set: {len(test_df)} samples")

        # Train model
        self.log(f"\n{'='*60}")
        self.log(f"  TRAINING AI ENSEMBLE (XGBoost + LightGBM + Random Forest)")
        self.log(f"{'='*60}")

        model = EnsembleModel(self.symbol)
        result = model.train(train_df, available_cols)

        if "error" in result:
            self.log(f"  [FAIL] Training failed: {result['error']}")
            config.TRADING_TIMEFRAME = original_tf
            return None

        for name, metrics in result.get("models", {}).items():
            if "accuracy" in metrics:
                self.log(f"  [MODEL] {name}: accuracy={metrics['accuracy']:.4f}")

        # Show top features
        top_features = model.get_top_features(10)
        self.log(f"\n  Top 10 Feature Importances:")
        for feat, imp in top_features:
            self.log(f"    - {feat}: {imp:.4f}")

        # Run backtest on test data
        self.log(f"\n{'='*60}")
        self.log(f"  SIMULATING TRADES ON TEST DATA ({len(test_df)} bars)")
        self.log(f"{'='*60}")


        open_positions = []

        for idx in range(len(test_df)):
            if idx < 50:
                continue  # Need minimum data

            current = test_df.iloc[idx]
            current_price = current["close"]
            current_time = current.get("time", idx)
            atr = current.get("atr", current_price * 0.001)

            # Detect regime
            regime_df = test_df.iloc[max(0, idx-100):idx+1]
            regime = RegimeDetector.detect(
                pd.DataFrame({
                    "open": regime_df.get("open", regime_df["close"]) if "open" in regime_df.columns else regime_df["close"],
                    "high": regime_df.get("high", regime_df["close"]) if "high" in regime_df.columns else regime_df["close"],
                    "low": regime_df.get("low", regime_df["close"]) if "low" in regime_df.columns else regime_df["close"],
                    "close": regime_df["close"],
                }) if all(c in regime_df.columns for c in ["open", "high", "low", "close"]) else regime_df
            )

            # Predict
            try:
                latest = test_df.iloc[[idx]]
                signal, confidence, model_votes = model.predict(latest)
            except Exception:
                continue

            # Manage open positions
            for pos in open_positions[:]:
                closed = False

                if pos["type"] == "BUY":
                    if current_price >= pos["tp"]:
                        profit = (pos["tp"] - pos["entry"]) * pos["volume"] * self._get_multiplier()
                        self._close(pos, current_price, current_time, profit, "TP_HIT")
                        closed = True
                    elif current_price <= pos["sl"]:
                        profit = (pos["sl"] - pos["entry"]) * pos["volume"] * self._get_multiplier()
                        self._close(pos, current_price, current_time, profit, "SL_HIT")
                        closed = True
                    elif signal == "SELL" and confidence > 0.65:
                        profit = (current_price - pos["entry"]) * pos["volume"] * self._get_multiplier()
                        self._close(pos, current_price, current_time, profit, "REVERSAL")
                        closed = True

                elif pos["type"] == "SELL":
                    if current_price <= pos["tp"]:
                        profit = (pos["entry"] - pos["tp"]) * pos["volume"] * self._get_multiplier()
                        self._close(pos, current_price, current_time, profit, "TP_HIT")
                        closed = True
                    elif current_price >= pos["sl"]:
                        profit = (pos["entry"] - pos["sl"]) * pos["volume"] * self._get_multiplier()
                        self._close(pos, current_price, current_time, profit, "SL_HIT")
                        closed = True
                    elif signal == "BUY" and confidence > 0.65:
                        profit = (pos["entry"] - current_price) * pos["volume"] * self._get_multiplier()
                        self._close(pos, current_price, current_time, profit, "REVERSAL")
                        closed = True

                # Breakeven & Trailing Stop check
                if not closed:
                    pip_unit = 0.1 if ("XAU" in self.symbol or "GOLD" in self.symbol) else (0.01 if "JPY" in self.symbol else 0.0001)
                    entry_p = pos["entry"]
                    sl_p = pos["sl"]

                    if pos["type"] == "BUY":
                        fav_move = current_price - entry_p
                        risk_p = entry_p - sl_p if sl_p > 0 else 0
                        if risk_p > 0:
                            rr = fav_move / risk_p
                            if rr >= config.BREAKEVEN_TRIGGER_RR:
                                be_sl = entry_p + (config.BREAKEVEN_BUFFER_PIPS * pip_unit)
                                if pos["sl"] < be_sl:
                                    pos["sl"] = be_sl

                            if getattr(config, "TRAILING_STOP_ENABLED", True) and rr >= getattr(config, "TRAILING_STOP_TRIGGER_RR", 1.0):
                                trail_sl = current_price - (risk_p * 0.75)
                                if trail_sl > pos["sl"] and trail_sl > entry_p:
                                    pos["sl"] = trail_sl
                    else:
                        fav_move = entry_p - current_price
                        risk_p = sl_p - entry_p if sl_p > 0 else 0
                        if risk_p > 0:
                            rr = fav_move / risk_p
                            if rr >= config.BREAKEVEN_TRIGGER_RR:
                                be_sl = entry_p - (config.BREAKEVEN_BUFFER_PIPS * pip_unit)
                                if pos["sl"] > be_sl or pos["sl"] == 0:
                                    pos["sl"] = be_sl

                            if getattr(config, "TRAILING_STOP_ENABLED", True) and rr >= getattr(config, "TRAILING_STOP_TRIGGER_RR", 1.0):
                                trail_sl = current_price + (risk_p * 0.75)
                                if (pos["sl"] == 0 or trail_sl < pos["sl"]) and trail_sl < entry_p:
                                    pos["sl"] = trail_sl

                # Time exit
                if not closed and (idx - pos["open_idx"]) > config.MAX_TRADE_DURATION_CANDLES:
                    if pos["type"] == "BUY":
                        profit = (current_price - pos["entry"]) * pos["volume"] * self._get_multiplier()
                    else:
                        profit = (pos["entry"] - current_price) * pos["volume"] * self._get_multiplier()
                    self._close(pos, current_price, current_time, profit, "TIME_EXIT")
                    closed = True

                if closed:
                    open_positions.remove(pos)

            # Open new position
            if (len(open_positions) < config.MAX_POSITIONS_PER_SYMBOL and
                    confidence > config.MIN_CONFIDENCE and signal != "HOLD"):

                regime_adj = RegimeDetector.get_regime_adjustments(regime)
                sl_dist = atr * 2 * regime_adj["sl_multiplier"]
                tp_dist = atr * 3 * regime_adj["tp_multiplier"]

                # Skip counter-trend with low confidence
                favored = regime_adj.get("favor_direction")
                if favored and signal != favored and confidence < 0.72:
                    continue

                # Position sizing for micro-accounts ($50+) with 5.5% max risk
                risk_amount = self.balance * (config.MAX_RISK_PERCENT / 100)
                multiplier = self._get_multiplier()
                position_size = risk_amount / (sl_dist * multiplier) if sl_dist > 0 else 0.01
                position_size = max(0.01, min(5.0, round(position_size, 2)))


                if signal == "BUY":
                    pos = {
                        "type": "BUY", "entry": current_price,
                        "sl": current_price - sl_dist,
                        "tp": current_price + tp_dist,
                        "volume": position_size,
                        "open_time": current_time,
                        "open_idx": idx,
                        "confidence": confidence,
                        "regime": regime,
                    }
                    open_positions.append(pos)
                elif signal == "SELL":
                    pos = {
                        "type": "SELL", "entry": current_price,
                        "sl": current_price + sl_dist,
                        "tp": current_price - tp_dist,
                        "volume": position_size,
                        "open_time": current_time,
                        "open_idx": idx,
                        "confidence": confidence,
                        "regime": regime,
                    }
                    open_positions.append(pos)

            # Track equity
            unrealized = sum(
                (current_price - p["entry"]) * p["volume"] * self._get_multiplier()
                if p["type"] == "BUY" else
                (p["entry"] - current_price) * p["volume"] * self._get_multiplier()
                for p in open_positions
            )
            self.equity = self.balance + unrealized
            self.equity_curve.append({
                "time": current_time, "balance": self.balance, "equity": self.equity
            })

        # Close remaining positions
        if open_positions:
            final_price = test_df.iloc[-1]["close"]
            final_time = test_df.iloc[-1].get("time", len(test_df))
            for pos in open_positions:
                if pos["type"] == "BUY":
                    profit = (final_price - pos["entry"]) * pos["volume"] * self._get_multiplier()
                else:
                    profit = (pos["entry"] - final_price) * pos["volume"] * self._get_multiplier()
                self._close(pos, final_price, final_time, profit, "BACKTEST_END")

        # Restore config
        config.TRADING_TIMEFRAME = original_tf

        # Print results
        self._print_results()

        # Do not disconnect here, because api_server needs the connection
        return self.trades

    def _get_multiplier(self) -> float:
        """Get the profit multiplier for the symbol."""
        if "XAU" in self.symbol or "GOLD" in self.symbol:
            return 100  # Gold: 1 lot = 100 oz
        elif "BTC" in self.symbol or "ETH" in self.symbol:
            return 1    # Crypto: 1 lot = 1 coin
        elif "JPY" in self.symbol:
            return 1000
        else:
            return 100000  # Standard forex

    def _close(self, pos, close_price, close_time, profit, reason):
        """Close a position and record the trade."""
        balance_before = self.balance
        self.balance += profit
        
        trade = {
            "symbol": self.symbol,
            "type": pos["type"],
            "entry": pos["entry"],
            "exit": close_price,
            "volume": pos["volume"],
            "profit": profit,
            "balance_before": balance_before,
            "balance_after": self.balance,
            "open_time": pos["open_time"],
            "close_time": close_time,
            "confidence": pos["confidence"],
            "regime": pos.get("regime", ""),
            "reason": reason,
        }
        self.trades.append(trade)
        result = "WIN" if profit > 0 else "LOSS"
        self.log(f"  [{close_time}] CLOSE {pos['type']} @ {close_price:.2f} "
                 f"| P&L: ${profit:.2f} | {result} ({reason})")

    def _print_results(self):
        """Print comprehensive backtest results."""
        self.log(f"\n{'='*60}")
        self.log(f"  BACKTEST RESULTS — {self.symbol}")
        self.log(f"{'='*60}")

        if not self.trades:
            self.log("  No trades executed")
            return

        total = len(self.trades)
        wins = [t for t in self.trades if t["profit"] > 0]
        losses = [t for t in self.trades if t["profit"] < 0]
        win_rate = len(wins) / total * 100

        total_profit = sum(t["profit"] for t in self.trades)
        avg_win = sum(t["profit"] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t["profit"] for t in losses) / len(losses) if losses else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf")

        # Max drawdown
        peak = self.initial_balance
        max_dd = 0
        for p in self.equity_curve:
            if p["equity"] > peak:
                peak = p["equity"]
            dd = (peak - p["equity"]) / peak * 100
            max_dd = max(max_dd, dd)

        self.log(f"\n  Account:")
        self.log(f"    Initial:      ${self.initial_balance:.2f}")
        self.log(f"    Final:        ${self.balance:.2f}")
        self.log(f"    Total Profit: ${total_profit:.2f}")
        self.log(f"    Return:       {((self.balance - self.initial_balance) / self.initial_balance * 100):.2f}%")
        self.log(f"    Max Drawdown: {max_dd:.2f}%")

        self.log(f"\n  Trades:")
        self.log(f"    Total:    {total}")
        self.log(f"    Wins:     {len(wins)}")
        self.log(f"    Losses:   {len(losses)}")
        self.log(f"    Win Rate: {win_rate:.1f}%")

        self.log(f"\n  Profit:")
        self.log(f"    Avg Win:       ${avg_win:.2f}")
        self.log(f"    Avg Loss:      ${avg_loss:.2f}")
        self.log(f"    Profit Factor: {profit_factor:.2f}")

        # By regime
        regimes = {}
        for t in self.trades:
            r = t.get("regime", "UNKNOWN")
            if r not in regimes:
                regimes[r] = {"wins": 0, "total": 0, "profit": 0}
            regimes[r]["total"] += 1
            regimes[r]["profit"] += t["profit"]
            if t["profit"] > 0:
                regimes[r]["wins"] += 1

        self.log(f"\n  By Regime:")
        for r, stats in regimes.items():
            wr = stats["wins"] / stats["total"] * 100 if stats["total"] > 0 else 0
            self.log(f"    {r}: {stats['total']} trades, {wr:.0f}% win rate, ${stats['profit']:.2f}")

        # By close reason
        reasons = {}
        for t in self.trades:
            reasons[t["reason"]] = reasons.get(t["reason"], 0) + 1
        self.log(f"\n  Close Reasons:")
        for reason, count in sorted(reasons.items()):
            self.log(f"    {reason}: {count}")

        self.log(f"\n{'='*60}")



if __name__ == "__main__":
    symbols_to_test = config.SYMBOLS
    print(f"\n============================================================")
    print(f"  LAUNCHING MULTI-PAIR 1-YEAR PORTFOLIO BACKTEST")
    print(f"  Pairs: {', '.join(symbols_to_test)}")
    print(f"============================================================\n")

    portfolio_results = []
    total_portfolio_profit = 0.0

    for symbol in symbols_to_test:
        backtester = Backtester(symbol=symbol, initial_balance=1000.0)
        trades = backtester.run_backtest(months=12, timeframe="H1")

        if trades:
            df = pd.DataFrame(trades)
            filename = f"trading_bot/data/backtest_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            import os
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            df.to_csv(filename, index=False)

            symbol_profit = sum(t["profit"] for t in trades)
            wins = len([t for t in trades if t["profit"] > 0])
            total = len(trades)
            win_rate = (wins / total * 100) if total > 0 else 0

            portfolio_results.append({
                "symbol": symbol,
                "trades": total,
                "win_rate": win_rate,
                "profit": symbol_profit,
            })
            total_portfolio_profit += symbol_profit

    print("\n============================================================")
    print("  7-PAIR PORTFOLIO BACKTEST SUMMARY")
    print("============================================================")
    for res in portfolio_results:
        print(f"  {res['symbol']:<10} | Trades: {res['trades']:<4} | Win Rate: {res['win_rate']:.1f}% | P&L: ${res['profit']:.2f}")
    print("------------------------------------------------------------")
    print(f"  PORTFOLIO TOTAL P&L: ${total_portfolio_profit:.2f}")
    print("============================================================\n")

