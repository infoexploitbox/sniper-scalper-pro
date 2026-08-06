"""
Smart Executor — handles trade entry/exit with session filtering,
spread filtering, partial take-profit, breakeven stops, and time-limited exits.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List

import config
from mt5_connector import MT5Connector
from ai_engine.database import TradingDatabase
from ai_engine.regime_detector import RegimeDetector


class SmartExecutor:
    """
    Intelligent trade execution with risk management.

    Entry filters: session, spread, drawdown, position limits
    Exit management: partial TP, breakeven stops, time-based exits
    """

    def __init__(self, mt5: MT5Connector, db: TradingDatabase):
        self.mt5 = mt5
        self.db = db

    # ─── Entry Filters ───────────────────────────────────────

    def can_open_trade(self, symbol: str, regime: str, direction: str = None) -> tuple:
        """
        Check all entry filters. Returns (can_trade: bool, reason: str).
        """
        # 1. Check session
        if not self._is_session_active(symbol):
            return False, "Outside trading session"

        # 2. Check regime
        if not RegimeDetector.should_trade(regime):
            return False, f"Regime {regime} — not trading"

        # 3. Check total position limit
        positions = self.mt5.get_positions()
        if len(positions) >= config.MAX_POSITIONS:
            return False, f"Max positions ({config.MAX_POSITIONS}) reached"

        # 4. Check per-symbol position limit
        symbol_positions = [p for p in positions if p["symbol"] == symbol]
        if len(symbol_positions) >= config.MAX_POSITIONS_PER_SYMBOL:
            return False, f"Max {symbol} positions ({config.MAX_POSITIONS_PER_SYMBOL}) reached"

        # Prevent Hedging (Opposite positions)
        if direction and symbol_positions:
            target_type = 0 if direction == "BUY" else 1
            for p in symbol_positions:
                if p["type"] != target_type:
                    return False, f"Opposite position already open for {symbol}"

        # 5. Check daily drawdown
        if not self._check_drawdown():
            return False, "Daily drawdown limit reached"

        # 6. Check spread
        spread_ok, spread_msg = self._check_spread(symbol)
        if not spread_ok:
            return False, spread_msg

        return True, "All filters passed"

    def _is_session_active(self, symbol: str) -> bool:
        """Check if current time is within the trading session for this symbol."""
        now_utc = datetime.now(timezone.utc)
        hour = now_utc.hour

        # Don't trade on weekends, unless it's crypto
        is_crypto = any(c in symbol.upper() for c in ["BTC", "ETH", "CRYPTO"])
        if now_utc.weekday() >= 5 and not is_crypto:  # Saturday = 5, Sunday = 6
            return False

        windows = config.get_session_windows(symbol)
        for start, end in windows:
            if start <= hour < end:
                return True
        return False

    def _check_drawdown(self) -> bool:
        """Check if daily drawdown is within limits."""
        account = self.mt5.get_account_info()
        if not account:
            return True  # Can't check, allow trade

        balance = account["balance"]
        daily_pnl = self.db.get_daily_pnl()

        max_daily_loss = balance * (config.MAX_DAILY_DRAWDOWN_PERCENT / 100)
        if daily_pnl < -max_daily_loss:
            print(f"  [Executor] Daily drawdown limit hit: ${daily_pnl:.2f} / -${max_daily_loss:.2f}")
            return False
        return True

    def _check_spread(self, symbol: str) -> tuple:
        """Check if current spread is acceptable."""
        tick = self.mt5.get_tick(symbol)
        if not tick:
            return True, ""  # Can't check, allow

        spread = tick["ask"] - tick["bid"]

        # Simple heuristic: spread should be less than 10% of typical ATR
        # We'll refine this with historical data once we have enough
        symbol_upper = symbol.upper()
        if "XAU" in symbol_upper or "GOLD" in symbol_upper:
            max_spread = 1.00  # $1.00 for gold
        elif "BTC" in symbol_upper:
            max_spread = 50.0  # $50 for Bitcoin
        elif "ETH" in symbol_upper:
            max_spread = 5.0   # $5 for Ethereum
        elif "US30" in symbol_upper or "NAS100" in symbol_upper:
            max_spread = 10.0  # 10 points for indices
        elif "SPX" in symbol_upper:
            max_spread = 2.0   # 2 points for SPX500
        elif "JPY" in symbol_upper:
            max_spread = 0.03  # 3 pips for JPY pairs
        else:
            max_spread = 0.0003  # 3 pips for standard forex pairs

        if spread > max_spread:
            return False, f"Spread too wide: {spread:.5f} > {max_spread:.5f}"

        return True, ""

    def get_current_session(self, symbol: str) -> str:
        """Get the current active session name."""
        hour = datetime.now(timezone.utc).hour

        if 0 <= hour < 7:
            return "ASIAN"
        elif 7 <= hour < 13:
            return "LONDON"
        elif 13 <= hour < 17:
            return "NY_OVERLAP"
        elif 17 <= hour < 21:
            return "NY"
        else:
            return "AFTER_HOURS"

    # ─── Position Sizing ─────────────────────────────────────

    def calculate_position_size(self, symbol: str, sl_distance: float,
                                confidence: float) -> float:
        """
        Dynamic position sizing based on risk, confidence, and recent performance.
        """
        account = self.mt5.get_account_info()
        if not account:
            return config.LOT_SIZE

        balance = account["balance"]

        # Base risk from config
        risk_percent = config.MAX_RISK_PERCENT

        # Auto-reduce risk if in drawdown
        if config.AUTO_REDUCE_RISK_ON_DRAWDOWN:
            daily_pnl = self.db.get_daily_pnl()
            max_daily_loss = balance * (config.MAX_DAILY_DRAWDOWN_PERCENT / 100)
            if daily_pnl < -max_daily_loss * 0.5:
                risk_percent *= 0.5  # Halve risk
                print(f"  [Executor] Risk reduced to {risk_percent:.1f}% due to drawdown")

        # Scale by confidence (higher confidence = can risk more)
        confidence_scaler = 0.7 + (confidence * 0.3)  # 0.7x at 0% conf, 1.0x at 100%
        risk_percent *= confidence_scaler

        risk_amount = balance * (risk_percent / 100)

        if sl_distance <= 0:
            return config.LOT_SIZE

        # Calculate lot size based on symbol type
        symbol_upper = symbol.upper()
        if "XAU" in symbol_upper or "GOLD" in symbol_upper:
            # Gold: 1 lot = 100 oz
            position_size = risk_amount / (sl_distance * 100)
        elif "BTC" in symbol_upper or "ETH" in symbol_upper:
            # Crypto: 1 lot = 1 coin
            position_size = risk_amount / (sl_distance * 1)
        elif "US30" in symbol_upper or "NAS100" in symbol_upper or "SPX" in symbol_upper:
            # Indices: usually 1 lot = 1 unit or 10 units (using 1 as safe default)
            position_size = risk_amount / (sl_distance * 1)
        elif "JPY" in symbol_upper:
            # JPY pairs: different pip value
            position_size = risk_amount / (sl_distance * 1000)
        else:
            # Standard forex
            position_size = risk_amount / (sl_distance * 100000)

        # Round and clamp
        position_size = max(0.01, round(position_size, 2))
        # Use a more reasonable safety cap (e.g., 50 lots) instead of LOT_SIZE * 20 (which was 0.2)
        position_size = min(position_size, 50.0)  # Safety cap

        return position_size

    # ─── Trade Execution ─────────────────────────────────────

    def execute_trade(self, signal: Dict, prediction_id: int) -> Optional[Dict]:
        """
        Execute a trade with proper position sizing and risk management.
        Returns trade details or None if trade was rejected.
        """
        symbol = signal["symbol"]
        direction = signal["signal"]
        confidence = signal["confidence"]
        regime = signal.get("regime", "RANGING")

        if direction == "HOLD":
            return None

        # Calculate SL/TP based on ATR and regime
        atr = signal.get("atr", 0)
        current_price = signal["current_price"]

        regime_adj = RegimeDetector.get_regime_adjustments(regime)
        sl_mult = regime_adj["sl_multiplier"]
        tp_mult = regime_adj["tp_multiplier"]

        sl_distance = atr * 1.5 * sl_mult     # Tighter SL for better R:R
        tp_distance = atr * 3.0 * tp_mult     # Minimum 1:2 R:R (sl * 2)

        if direction == "BUY":
            sl = current_price - sl_distance
            tp = current_price + tp_distance
        else:
            sl = current_price + sl_distance
            tp = current_price - tp_distance

        # Calculate position size
        volume = self.calculate_position_size(symbol, sl_distance, confidence)

        # Place order
        result = self.mt5.place_order(
            symbol=symbol,
            order_type=direction,
            volume=volume,
            sl=sl,
            tp=tp,
            comment=f"AI {confidence:.0%} {regime[:3]}"
        )

        if result:
            # Log to database
            session = self.get_current_session(symbol)
            trade_id = self.db.log_trade_open(
                prediction_id=prediction_id,
                ticket=result["ticket"],
                symbol=symbol,
                direction=direction,
                volume=volume,
                entry_price=result["price"],
                sl=sl,
                tp=tp,
                confidence=confidence,
                regime=regime,
                session=session,
            )

            self.db.mark_prediction_acted(prediction_id)

            print(f"  [Executor] [OK] {direction} {volume} {symbol} @ {result['price']:.5f} "
                  f"| SL: {sl:.5f} | TP: {tp:.5f} | Conf: {confidence:.0%}")

            return {
                **result,
                "trade_id": trade_id,
                "direction": direction,
                "volume": volume,
                "sl": sl,
                "tp": tp,
                "confidence": confidence,
                "regime": regime,
                "session": session,
            }

        return None

    # ─── Position Management ─────────────────────────────────

    def manage_open_positions(self, models: Dict = None):
        """
        Manage all open positions: breakeven stops, time-based exits,
        and signal-reversal exits.
        """
        positions = self.mt5.get_positions()

        for pos in positions:
            # Only manage our bot's positions
            if "AI" not in pos.get("comment", ""):
                continue

            # Check for time-limited exit
            self._check_time_exit(pos)

            # Check for breakeven stop
            if config.BREAKEVEN_ENABLED:
                self._check_breakeven(pos)

            # Check for ATR trailing stop
            if getattr(config, "TRAILING_STOP_ENABLED", True):
                self._check_trailing_stop(pos)


    def _check_time_exit(self, pos: Dict):
        """Close position if it's been open too long (scalping time limit)."""
        try:
            open_time = datetime.fromisoformat(pos["time"])
            # Make timezone-aware if naive (fixes offset-naive vs offset-aware error)
            if open_time.tzinfo is None:
                open_time = open_time.replace(tzinfo=timezone.utc)
            elapsed = datetime.now(timezone.utc) - open_time

            # Convert max candle duration to minutes based on timeframe
            tf = config.TRADING_TIMEFRAME
            candle_minutes = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60}.get(tf, 5)
            max_minutes = config.MAX_TRADE_DURATION_CANDLES * candle_minutes

            if elapsed > timedelta(minutes=max_minutes):
                print(f"  [Executor] Time exit: #{pos['ticket']} open for {elapsed}")

                # Close position
                success = self.mt5.close_position(pos["ticket"])
                if success:
                    profit = pos.get("profit", 0)
                    self.db.log_trade_close(
                        ticket=pos["ticket"],
                        close_price=pos["price_current"],
                        profit=profit,
                        pips=0,  # Will be calculated
                        close_reason="TIME_EXIT"
                    )
        except Exception as e:
            print(f"  [Executor] Time exit check failed: {e}")

    def _check_breakeven(self, pos: Dict):
        """Move SL to breakeven + buffer if position is in 1:1 R:R profit."""
        try:
            entry = pos["price_open"]
            current = pos["price_current"]
            sl = pos["sl"]
            is_buy = pos["type"] == 0
            symbol = pos["symbol"]

            # Calculate pip multiplier
            pip_unit = 0.1 if ("XAU" in symbol or "GOLD" in symbol) else (0.01 if "JPY" in symbol else 0.0001)

            if is_buy:
                favorable_move = current - entry
                risk = entry - sl if sl > 0 else 0
            else:
                favorable_move = entry - current
                risk = sl - entry if sl > 0 else 0

            if risk <= 0:
                return

            rr_achieved = favorable_move / risk if risk > 0 else 0

            if rr_achieved >= config.BREAKEVEN_TRIGGER_RR:
                if is_buy:
                    new_sl = entry + (config.BREAKEVEN_BUFFER_PIPS * pip_unit)
                    if sl < new_sl:
                        if self.mt5.modify_position(pos["ticket"], sl=new_sl):
                            print(f"  [Executor] Breakeven hit! Moved BUY SL for #{pos['ticket']} to {new_sl:.5f}")
                else:
                    new_sl = entry - (config.BREAKEVEN_BUFFER_PIPS * pip_unit)
                    if sl > new_sl or sl == 0:
                        if self.mt5.modify_position(pos["ticket"], sl=new_sl):
                            print(f"  [Executor] Breakeven hit! Moved SELL SL for #{pos['ticket']} to {new_sl:.5f}")
        except Exception as e:
            print(f"  [Executor] Breakeven check failed: {e}")

    def _check_trailing_stop(self, pos: Dict):
        """Dynamically trail Stop Loss using ATR / price distance to lock in profits."""
        try:
            entry = pos["price_open"]
            current = pos["price_current"]
            sl = pos["sl"]
            is_buy = pos["type"] == 0
            symbol = pos["symbol"]

            pip_unit = 0.1 if ("XAU" in symbol or "GOLD" in symbol) else (0.01 if "JPY" in symbol else 0.0001)
            atr_approx = abs(entry - sl) / 2.0 if sl > 0 else 10 * pip_unit

            if is_buy:
                favorable_move = current - entry
                risk = entry - sl if sl > 0 else 0
            else:
                favorable_move = entry - current
                risk = sl - entry if sl > 0 else 0

            if risk <= 0:
                return

            rr_achieved = favorable_move / risk

            if rr_achieved >= getattr(config, "TRAILING_STOP_TRIGGER_RR", 1.0):
                mult = getattr(config, "TRAILING_STOP_ATR_MULT", 1.5)
                trail_distance = atr_approx * mult

                if is_buy:
                    trailing_sl = current - trail_distance
                    if trailing_sl > sl and trailing_sl > entry:
                        if self.mt5.modify_position(pos["ticket"], sl=trailing_sl):
                            print(f"  [Executor] Trailing SL updated for BUY #{pos['ticket']} -> {trailing_sl:.5f}")
                else:
                    trailing_sl = current + trail_distance
                    if (sl == 0 or trailing_sl < sl) and trailing_sl < entry:
                        if self.mt5.modify_position(pos["ticket"], sl=trailing_sl):
                            print(f"  [Executor] Trailing SL updated for SELL #{pos['ticket']} -> {trailing_sl:.5f}")
        except Exception as e:
            print(f"  [Executor] Trailing stop check failed: {e}")


    def reconcile_positions(self):
        """
        Reconcile MT5 positions with database after a restart/crash.
        Finds positions opened by bot that aren't in DB and vice versa.
        """
        mt5_positions = self.mt5.get_positions()
        db_open_trades = self.db.get_open_trades()

        bot_positions = [p for p in mt5_positions if "AI" in p.get("comment", "")]
        db_tickets = {t["ticket"] for t in db_open_trades}
        mt5_tickets = {p["ticket"] for p in bot_positions}

        # Positions in DB but not in MT5 → they were closed while bot was offline
        closed_offline = db_tickets - mt5_tickets
        for ticket in closed_offline:
            print(f"  [Executor] Position #{ticket} was closed while offline")
            # Mark as closed with unknown details
            self.db.log_trade_close(
                ticket=ticket,
                close_price=0,  # Unknown
                profit=0,  # Unknown
                pips=0,
                close_reason="CLOSED_WHILE_OFFLINE"
            )

        # Positions in MT5 but not in DB → opened before we had tracking
        new_positions = mt5_tickets - db_tickets
        for ticket in new_positions:
            pos = next(p for p in bot_positions if p["ticket"] == ticket)
            print(f"  [Executor] Found untracked position #{ticket} — adding to DB")
            self.db.log_trade_open(
                prediction_id=0,
                ticket=ticket,
                symbol=pos["symbol"],
                direction="BUY" if pos["type"] == 0 else "SELL",
                volume=pos["volume"],
                entry_price=pos["price_open"],
                sl=pos["sl"],
                tp=pos["tp"],
                confidence=0,
                regime="UNKNOWN",
                session="UNKNOWN",
            )

        if closed_offline or new_positions:
            print(f"  [Executor] Reconciliation: {len(closed_offline)} closed offline, "
                  f"{len(new_positions)} new untracked")
