"""
SQLite persistence layer for the AI trading engine.

Stores: predictions, trade outcomes, model performance, feature importance,
regime statistics, and self-learning adaptation history.
"""

import sqlite3
import json
import os
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any
from contextlib import contextmanager

import config


class TradingDatabase:
    """SQLite database for trade logging, performance tracking, and self-learning."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_conn(self):
        """Context manager for database connections with WAL mode for crash safety."""
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")  # Crash-safe even on power loss
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Create tables if they don't exist."""
        with self._get_conn() as conn:
            conn.executescript("""
                -- Every prediction the AI makes (whether acted on or not)
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    regime TEXT,
                    features_json TEXT,
                    model_votes_json TEXT,
                    acted_on INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                -- Every trade opened by the bot
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_id INTEGER,
                    ticket INTEGER,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    volume REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    sl REAL,
                    tp REAL,
                    open_time TEXT NOT NULL,
                    close_time TEXT,
                    close_price REAL,
                    profit REAL,
                    pips REAL,
                    close_reason TEXT,
                    confidence REAL,
                    regime TEXT,
                    session TEXT,
                    features_json TEXT,
                    status TEXT DEFAULT 'OPEN',
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (prediction_id) REFERENCES predictions(id)
                );

                -- Model performance snapshots
                CREATE TABLE IF NOT EXISTS model_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    accuracy REAL,
                    precision_score REAL,
                    recall REAL,
                    f1_score REAL,
                    win_rate REAL,
                    profit_factor REAL,
                    total_trades INTEGER,
                    feature_importance_json TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                -- Self-learning adaptation log
                CREATE TABLE IF NOT EXISTS adaptations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    adaptation_type TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    reason TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                -- Regime statistics
                CREATE TABLE IF NOT EXISTS regime_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    regime TEXT NOT NULL,
                    win_rate REAL,
                    avg_profit REAL,
                    trade_count INTEGER,
                    avg_confidence REAL,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                -- Bot state (for crash recovery)
                CREATE TABLE IF NOT EXISTS bot_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT DEFAULT (datetime('now'))
                );

                -- Backtest History
                CREATE TABLE IF NOT EXISTS backtests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    initial_balance REAL NOT NULL,
                    final_balance REAL NOT NULL,
                    total_profit REAL NOT NULL,
                    win_rate REAL NOT NULL,
                    total_trades INTEGER NOT NULL,
                    results_json TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                -- Create indexes for fast queries
                CREATE INDEX IF NOT EXISTS idx_predictions_symbol_time
                    ON predictions(symbol, timestamp);
                CREATE INDEX IF NOT EXISTS idx_trades_symbol_status
                    ON trades(symbol, status);
                CREATE INDEX IF NOT EXISTS idx_trades_open_time
                    ON trades(open_time);
                CREATE INDEX IF NOT EXISTS idx_model_perf_symbol
                    ON model_performance(symbol, timestamp);
            """)

    # ─── Predictions ────────────────────────────────────────

    def log_prediction(self, symbol: str, timeframe: str, signal: str,
                       confidence: float, regime: str = None,
                       features: dict = None, model_votes: dict = None) -> int:
        """Log an AI prediction. Returns the prediction ID."""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO predictions (timestamp, symbol, timeframe, signal,
                    confidence, regime, features_json, model_votes_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                symbol, timeframe, signal, confidence, regime,
                json.dumps(features) if features else None,
                json.dumps(model_votes) if model_votes else None,
            ))
            return cursor.lastrowid

    def mark_prediction_acted(self, prediction_id: int):
        """Mark a prediction as acted upon (trade was placed)."""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE predictions SET acted_on = 1 WHERE id = ?",
                (prediction_id,)
            )

    # ─── Trades ─────────────────────────────────────────────

    def log_trade_open(self, prediction_id: int, ticket: int, symbol: str,
                       direction: str, volume: float, entry_price: float,
                       sl: float, tp: float, confidence: float,
                       regime: str = None, session: str = None,
                       features: dict = None) -> int:
        """Log a trade being opened. Returns the trade ID."""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO trades (prediction_id, ticket, symbol, direction,
                    volume, entry_price, sl, tp, open_time, confidence,
                    regime, session, features_json, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
            """, (
                prediction_id, ticket, symbol, direction, volume,
                entry_price, sl, tp, datetime.now(timezone.utc).isoformat(),
                confidence, regime, session,
                json.dumps(features) if features else None,
            ))
            return cursor.lastrowid

    def log_trade_close(self, ticket: int, close_price: float,
                        profit: float, pips: float, close_reason: str):
        """Log a trade being closed."""
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE trades
                SET close_time = ?, close_price = ?, profit = ?,
                    pips = ?, close_reason = ?, status = 'CLOSED'
                WHERE ticket = ? AND status = 'OPEN'
            """, (
                datetime.now(timezone.utc).isoformat(),
                close_price, profit, pips, close_reason, ticket,
            ))

    def get_open_trades(self, symbol: str = None) -> List[Dict]:
        """Get all open trades, optionally filtered by symbol."""
        with self._get_conn() as conn:
            if symbol:
                rows = conn.execute(
                    "SELECT * FROM trades WHERE status = 'OPEN' AND symbol = ?",
                    (symbol,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM trades WHERE status = 'OPEN'"
                ).fetchall()
            return [dict(r) for r in rows]

    def get_recent_trades(self, symbol: str = None, limit: int = 100) -> List[Dict]:
        """Get recent closed trades."""
        with self._get_conn() as conn:
            if symbol:
                rows = conn.execute("""
                    SELECT * FROM trades WHERE status = 'CLOSED' AND symbol = ?
                    ORDER BY close_time DESC LIMIT ?
                """, (symbol, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM trades WHERE status = 'CLOSED'
                    ORDER BY close_time DESC LIMIT ?
                """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_trade_by_ticket(self, ticket: int) -> Optional[Dict]:
        """Get a trade by its MT5 ticket number."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM trades WHERE ticket = ?", (ticket,)
            ).fetchone()
            return dict(row) if row else None

    # ─── Performance Queries ────────────────────────────────

    def get_win_rate(self, symbol: str = None, hours: int = 24,
                     regime: str = None, session: str = None) -> Dict:
        """Get win rate stats for recent trades with optional filters."""
        with self._get_conn() as conn:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

            query = """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN profit = 0 THEN 1 ELSE 0 END) as breakeven,
                    AVG(profit) as avg_profit,
                    SUM(profit) as total_profit,
                    AVG(confidence) as avg_confidence,
                    AVG(CASE WHEN profit > 0 THEN profit ELSE NULL END) as avg_win,
                    AVG(CASE WHEN profit < 0 THEN profit ELSE NULL END) as avg_loss
                FROM trades
                WHERE status = 'CLOSED' AND close_time > ?
            """
            params = [cutoff]

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            if regime:
                query += " AND regime = ?"
                params.append(regime)
            if session:
                query += " AND session = ?"
                params.append(session)

            row = conn.execute(query, params).fetchone()
            result = dict(row)

            total = result["total"] or 0
            wins = result["wins"] or 0
            result["win_rate"] = wins / total if total > 0 else 0
            avg_win = abs(result["avg_win"] or 0)
            avg_loss = abs(result["avg_loss"] or 1)
            result["profit_factor"] = avg_win / avg_loss if avg_loss > 0 else 0

            return result

    def get_performance_by_regime(self, symbol: str, hours: int = 168) -> List[Dict]:
        """Get win rate broken down by market regime."""
        with self._get_conn() as conn:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
            rows = conn.execute("""
                SELECT
                    regime,
                    COUNT(*) as total,
                    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as wins,
                    AVG(profit) as avg_profit,
                    AVG(confidence) as avg_confidence
                FROM trades
                WHERE status = 'CLOSED' AND symbol = ? AND close_time > ?
                GROUP BY regime
            """, (symbol, cutoff)).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["win_rate"] = d["wins"] / d["total"] if d["total"] > 0 else 0
                results.append(d)
            return results

    def get_performance_by_confidence(self, symbol: str = None,
                                       hours: int = 168) -> List[Dict]:
        """Get win rate by confidence bucket (e.g., 0.6-0.65, 0.65-0.7, etc.)."""
        with self._get_conn() as conn:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
            query = """
                SELECT
                    CAST(confidence * 20 AS INTEGER) / 20.0 as conf_bucket,
                    COUNT(*) as total,
                    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as wins,
                    AVG(profit) as avg_profit
                FROM trades
                WHERE status = 'CLOSED' AND close_time > ?
            """
            params = [cutoff]
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            query += " GROUP BY conf_bucket ORDER BY conf_bucket"

            rows = conn.execute(query, params).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["win_rate"] = d["wins"] / d["total"] if d["total"] > 0 else 0
                results.append(d)
            return results

    # ─── Model Performance ──────────────────────────────────

    def log_model_performance(self, symbol: str, model_name: str,
                              metrics: Dict, feature_importance: Dict = None):
        """Log model performance metrics after training/evaluation."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO model_performance (timestamp, symbol, model_name,
                    accuracy, precision_score, recall, f1_score, win_rate,
                    profit_factor, total_trades, feature_importance_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(), symbol, model_name,
                metrics.get("accuracy"), metrics.get("precision"),
                metrics.get("recall"), metrics.get("f1"),
                metrics.get("win_rate"), metrics.get("profit_factor"),
                metrics.get("total_trades"),
                json.dumps(feature_importance) if feature_importance else None,
            ))

    def get_latest_model_performance(self, symbol: str) -> List[Dict]:
        """Get latest performance for each model for a symbol."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM model_performance
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT 10
            """, (symbol,)).fetchall()
            return [dict(r) for r in rows]

    # ─── Adaptations ────────────────────────────────────────

    def log_adaptation(self, adaptation_type: str, details: Dict,
                       old_value: str = None, new_value: str = None,
                       reason: str = None):
        """Log a self-learning adaptation event."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO adaptations (timestamp, adaptation_type,
                    details_json, old_value, new_value, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(), adaptation_type,
                json.dumps(details), old_value, new_value, reason,
            ))

    def get_recent_adaptations(self, limit: int = 20) -> List[Dict]:
        """Get recent adaptation events."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM adaptations
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    # ─── Bot State (crash recovery) ─────────────────────────

    def save_state(self, key: str, value: Any):
        """Save a bot state value (for crash recovery)."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO bot_state (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, json.dumps(value), datetime.now(timezone.utc).isoformat()))

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get a bot state value."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT value FROM bot_state WHERE key = ?", (key,)
            ).fetchone()
            if row:
                return json.loads(row["value"])
            return default

    def get_daily_pnl(self) -> float:
        """Get today's total P&L for drawdown checks."""
        with self._get_conn() as conn:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            row = conn.execute("""
                SELECT COALESCE(SUM(profit), 0) as daily_pnl
                FROM trades
                WHERE status = 'CLOSED' AND close_time LIKE ?
            """, (f"{today}%",)).fetchone()
            return row["daily_pnl"]

    # ─── Cleanup ────────────────────────────────────────────

    def cleanup_old_predictions(self, days: int = 30):
        """Remove old predictions that weren't acted on to save space."""
        with self._get_conn() as conn:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            conn.execute("""
                DELETE FROM predictions
                WHERE acted_on = 0 AND timestamp < ?
            """, (cutoff,))

    # ─── Backtests ──────────────────────────────────────────

    def log_backtest(self, symbol: str, timeframe: str, initial_balance: float,
                     final_balance: float, total_profit: float, win_rate: float,
                     total_trades: int, results_json: dict) -> int:
        class NpEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                if isinstance(obj, np.floating):
                    return float(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                import pandas as pd
                if isinstance(obj, (pd.Timestamp, datetime)):
                    return obj.isoformat()
                return super(NpEncoder, self).default(obj)

        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO backtests (timestamp, symbol, timeframe, initial_balance,
                    final_balance, total_profit, win_rate, total_trades, results_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(), symbol, timeframe, initial_balance,
                float(final_balance), float(total_profit), float(win_rate), int(total_trades),
                json.dumps(results_json, cls=NpEncoder),
            ))
            return cursor.lastrowid

    def get_backtests(self, limit: int = 50) -> List[Dict]:
        """Get historical backtest runs."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM backtests
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,)).fetchall()
            
            results = []
            for r in rows:
                d = dict(r)
                if "results_json" in d and d["results_json"]:
                    d["results"] = json.loads(d["results_json"])
                    del d["results_json"]
                results.append(d)
            return results
