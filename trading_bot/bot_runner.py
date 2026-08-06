"""
Bot Runner — main autonomous trading loop.

Handles: initialization, auto-recovery, scheduled trading,
model retraining, self-learning evaluation, and graceful shutdown.
"""

import time
import sys
import schedule
from datetime import datetime, timezone
from typing import Dict

import config
from mt5_connector import MT5Connector
from ai_engine.database import TradingDatabase
from ai_engine.ensemble_model import EnsembleModel
from ai_engine.self_learner import SelfLearner
from smart_executor import SmartExecutor
from trading_strategy import TradingStrategy


class BotRunner:
    """Main bot runner with self-learning integration and crash recovery."""

    def __init__(self):
        self.mt5 = MT5Connector()
        self.db = TradingDatabase()
        self.self_learner = SelfLearner(self.db)
        self.executor = SmartExecutor(self.mt5, self.db)

        self.models: Dict[str, EnsembleModel] = {}
        self.strategies: Dict[str, TradingStrategy] = {}

        self.is_running = False
        self.symbols = config.SYMBOLS
        self.cycle_count = 0

    def initialize(self) -> bool:
        """Initialize bot: connect MT5, load/train models, recover state."""
        print("=" * 60)
        print("  SNIPER SCALPER PRO — AI Trading Bot")
        print("=" * 60)
        print(f"  Symbols: {', '.join(self.symbols)}")
        print(f"  Timeframe: {config.TRADING_TIMEFRAME}")
        print(f"  Risk: {config.MAX_RISK_PERCENT}%")
        print(f"  Session filter: Enabled")
        print(f"  Self-learning: Enabled")
        print("=" * 60)

        # Connect to MT5
        print("\n[1/4] Connecting to MT5...")
        if not self.mt5.connect():
            print("  [FAIL] Failed to connect to MT5")
            return False
        print("  [OK] MT5 connected")

        # Initialize models and strategies for each symbol
        print("\n[2/4] Loading AI models...")
        for symbol in self.symbols:
            model = EnsembleModel(symbol)

            if model.load():
                print(f"  [OK] {symbol}: Loaded existing model ({len(model.models)} models)")
            else:
                print(f"  [INFO] {symbol}: No saved model — will train on first cycle")

            self.models[symbol] = model
            self.strategies[symbol] = TradingStrategy(
                mt5=self.mt5,
                model=model,
                db=self.db,
                self_learner=self.self_learner,
                executor=self.executor,
            )

        # Crash recovery: reconcile positions
        print("\n[3/4] Reconciling positions...")
        self.executor.reconcile_positions()
        print("  [OK] Position reconciliation complete")

        # Restore bot state
        print("\n[4/4] Restoring state...")
        last_cycle = self.db.get_state("last_cycle_time")
        if last_cycle:
            print(f"  [OK] Last cycle was at: {last_cycle}")
        else:
            print("  [INFO] Fresh start — no previous state")

        print("\n" + "=" * 60)
        print("  Bot initialization complete!")
        print("=" * 60)

        return True

    def trading_loop(self):
        """Main trading loop — runs periodically."""
        if not self.is_running:
            return

        self.cycle_count += 1
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n+- Cycle #{self.cycle_count} [{timestamp} UTC] {'-' * 30}")

        try:
            for symbol in self.symbols:
                strategy = self.strategies[symbol]
                model = self.models[symbol]

                print(f"|")
                print(f"+- {symbol}")

                # Train model if not yet trained
                if not model.is_trained:
                    print(f"|  Training model (first time)...")
                    result = strategy.train_model(symbol)
                    if "error" in result:
                        print(f"|  [FAIL] Training failed: {result['error']}")
                        continue
                    print(f"|  [OK] Model trained")

                # Analyze market
                signal = strategy.analyze_market(symbol)

                if not signal:
                    print(f"|  - No signal generated")
                    continue

                regime = signal.get("regime", "?")
                conf = signal.get("confidence", 0)
                direction = signal.get("signal", "HOLD")
                print(f"|  Signal: {direction} | Conf: {conf:.0%} | Regime: {regime}")

                # Execute if actionable
                if direction != "HOLD":
                    trade = strategy.execute_signal(signal)
                    if trade:
                        print(f"|  [OK] TRADE EXECUTED: {trade['direction']} {trade['volume']} lots")
                    else:
                        print(f"|  - Signal filtered (not executed)")

            # Manage existing positions
            print(f"|")
            print(f"+- Managing positions...")
            self.executor.manage_open_positions(self.models)

            # Check closed positions and log P&L
            self._check_closed_positions()

            # Print account status
            self._print_account_status()

            # Save state
            self.db.save_state("last_cycle_time", timestamp)
            self.db.save_state("cycle_count", self.cycle_count)

        except Exception as e:
            print(f"|  [FAIL] Error in trading loop: {e}")
            import traceback
            traceback.print_exc()

        print(f"+{'-' * 55}")

    def _check_closed_positions(self):
        """Check if any bot positions were closed (by SL/TP) and log real deal outcomes."""
        db_open = self.db.get_open_trades()
        if not db_open:
            return

        mt5_positions = self.mt5.get_positions()
        mt5_tickets = {p["ticket"] for p in mt5_positions}

        for trade in db_open:
            ticket = trade["ticket"]
            if ticket not in mt5_tickets:
                # Position was closed (by SL, TP, or manually)
                # Fetch exact deal history details from MT5
                deal_info = self.mt5.get_deal_history(ticket)
                if deal_info:
                    print(f"|  Position #{ticket} closed: P&L ${deal_info['profit']:.2f} ({deal_info['close_reason']})")
                    self.db.log_trade_close(
                        ticket=ticket,
                        close_price=deal_info["close_price"],
                        profit=deal_info["profit"],
                        pips=deal_info["pips"],
                        close_reason=deal_info["close_reason"]
                    )
                else:
                    print(f"|  Position #{ticket} closed (details unavailable)")
                    self.db.log_trade_close(
                        ticket=ticket,
                        close_price=0,
                        profit=0,
                        pips=0,
                        close_reason="CLOSED_OFFLINE"
                    )


    def _print_account_status(self):
        """Print current account status."""
        account = self.mt5.get_account_info()
        if account:
            positions = self.mt5.get_positions()
            bot_positions = [p for p in positions if "AI" in p.get("comment", "")]
            daily_pnl = self.db.get_daily_pnl()

            print(f"|")
            print(f"+- Account Status")
            print(f"|  Balance: ${account['balance']:.2f} | "
                  f"Equity: ${account['equity']:.2f} | "
                  f"Daily P&L: ${daily_pnl:.2f}")
            print(f"|  Bot positions: {len(bot_positions)} / {config.MAX_POSITIONS}")

    def self_learning_cycle(self):
        """Run the self-learning evaluation (every 30 min)."""
        if not self.is_running:
            return

        print(f"\n  [SelfLearner] Running evaluation cycle...")
        result = self.self_learner.evaluate_and_adapt(self.models)

        if result["adaptations"]:
            print(f"  [SelfLearner] {len(result['adaptations'])} adaptations made")
            for a in result["adaptations"]:
                if a["type"] == "retrain_triggered":
                    # Trigger retrain
                    symbol = a["symbol"]
                    print(f"  [SelfLearner] Retraining {symbol}...")
                    self.strategies[symbol].train_model(symbol)
        else:
            threshold = result["current_threshold"]
            print(f"  [SelfLearner] No changes needed (threshold: {threshold:.3f})")

    def scheduled_retrain(self):
        """Scheduled full model retrain (every 6 hours)."""
        print(f"\n{'='*50}")
        print(f"  SCHEDULED MODEL RETRAIN")
        print(f"{'='*50}")

        for symbol in self.symbols:
            self.strategies[symbol].train_model(symbol)

    def start(self):
        """Start the bot."""
        if not self.initialize():
            print("\nBot initialization failed. Exiting.")
            return

        self.is_running = True

        # Get timeframe interval in minutes
        tf_minutes = {
            "M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60
        }.get(config.TRADING_TIMEFRAME, 5)

        # Schedule trading loop
        schedule.every(tf_minutes).minutes.do(self.trading_loop)

        # Schedule self-learning evaluation
        schedule.every(config.PERFORMANCE_EVAL_INTERVAL_MINUTES).minutes.do(
            self.self_learning_cycle
        )

        # Schedule model retraining
        schedule.every(config.RETRAIN_INTERVAL_HOURS).hours.do(self.scheduled_retrain)

        print(f"\n  Trading loop: every {tf_minutes} minutes")
        print(f"  Self-learning: every {config.PERFORMANCE_EVAL_INTERVAL_MINUTES} minutes")
        print(f"  Retrain: every {config.RETRAIN_INTERVAL_HOURS} hours")
        print(f"\n  Bot is LIVE. Press Ctrl+C to stop.\n")

        # Run first cycle immediately
        self.trading_loop()

        # Keep running
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n  Stopping bot...")
            self.stop()

    def stop(self):
        """Graceful shutdown."""
        self.is_running = False
        self.db.save_state("shutdown_time", datetime.now(timezone.utc).isoformat())
        self.db.save_state("shutdown_reason", "graceful")

        # Save all models
        for symbol, model in self.models.items():
            if model.is_trained:
                model.save()

        self.mt5.disconnect()
        print("  Bot stopped. Models saved. Goodbye!")


if __name__ == "__main__":
    bot = BotRunner()
    bot.start()
