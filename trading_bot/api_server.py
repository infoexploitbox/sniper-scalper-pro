from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
from contextlib import asynccontextmanager
import uvicorn
import numpy as np
import json
import subprocess
import os
import signal

import config
from mt5_connector import MT5Connector
from ai_engine.database import TradingDatabase
from ai_engine.ensemble_model import EnsembleModel
from ai_engine.self_learner import SelfLearner
from smart_executor import SmartExecutor
from trading_strategy import TradingStrategy


# Custom JSON encoder for numpy types
class NumpyEncoder(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=self._default,
        ).encode("utf-8")

    @staticmethod
    def _default(obj):
        if isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# ─── Lifespan ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # Startup
    if not mt5.connect():
        print("Warning: MT5 connection failed")

    for symbol in config.SYMBOLS:
        model = EnsembleModel(symbol)
        model.load()
        models[symbol] = model
        strategies[symbol] = TradingStrategy(
            mt5=mt5, model=model, db=db,
            self_learner=self_learner, executor=executor,
        )

    # Reconcile positions after crash
    executor.reconcile_positions()

    yield

    # Shutdown
    mt5.disconnect()


app = FastAPI(
    title="AI Trading Bot API",
    default_response_class=NumpyEncoder,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Global Instances ────────────────────────────────────

mt5 = MT5Connector()
db = TradingDatabase()
self_learner = SelfLearner(db)
executor = SmartExecutor(mt5, db)
models: Dict[str, EnsembleModel] = {}
strategies: Dict[str, TradingStrategy] = {}
bot_process: Optional[subprocess.Popen] = None


# ─── Request Models ──────────────────────────────────────

class TradeRequest(BaseModel):
    symbol: str
    type: str
    volume: float
    sl: Optional[float] = 0
    tp: Optional[float] = 0
    comment: Optional[str] = "Manual"


# ─── Existing Endpoints ──────────────────────────────────

@app.get("/")
async def root():
    return {"status": "AI Trading Bot API", "version": "2.0.0", "engine": "ensemble"}


@app.get("/account")
async def get_account():
    """Get account information."""
    account = mt5.get_account_info()
    if not account:
        raise HTTPException(status_code=500, detail="Failed to get account info")
    return account


@app.get("/positions")
async def get_positions():
    """Get open positions."""
    return mt5.get_positions()


@app.get("/tick")
async def get_tick(symbol: str = "EURUSD"):
    """Get current tick data."""
    tick = mt5.get_tick(symbol)
    if not tick:
        raise HTTPException(status_code=404, detail=f"Tick data not found for {symbol}")
    return tick


@app.get("/candles")
async def get_candles(symbol: str = "EURUSD",
                      timeframe: str = config.TRADING_TIMEFRAME,
                      count: int = 100):
    """Get historical candles."""
    df = mt5.get_candles(symbol, timeframe, count)
    if df.empty:
        raise HTTPException(status_code=404, detail="No candle data found")
    return df.to_dict(orient="records")


@app.get("/analyze")
async def analyze_market(symbol: str = "EURUSD"):
    """Analyze market and get AI signal."""
    if symbol not in strategies:
        raise HTTPException(status_code=404, detail=f"No strategy for {symbol}")

    signal = strategies[symbol].analyze_market(symbol)
    if not signal:
        raise HTTPException(status_code=500, detail="Analysis failed")
    return signal


@app.post("/trade/open")
async def open_trade(trade: TradeRequest):
    """Place a manual trade."""
    result = mt5.place_order(
        symbol=trade.symbol,
        order_type=trade.type,
        volume=trade.volume,
        sl=trade.sl,
        tp=trade.tp,
        comment=trade.comment,
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to place order")
    return result


@app.post("/trade/close")
async def close_trade(ticket: int):
    """Close a position."""
    success = mt5.close_position(ticket)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to close position")
    return {"success": True, "ticket": ticket}


@app.get("/symbols")
async def get_symbols():
    """Get configured symbols."""
    return config.SYMBOLS


# ─── AI Performance Endpoints ────────────────────────────

@app.get("/bot/status")
async def bot_status():
    """Get bot status, model info, and performance."""
    global bot_process
    
    # Check if process is still running
    is_running = bot_process is not None and bot_process.poll() is None
    
    model_statuses = {}
    for symbol, model in models.items():
        model_statuses[symbol] = model.get_status()

    return {
        "is_running": is_running,
        "connected": mt5.connected,
        "model_loaded": all(m.is_trained for m in models.values()),
        "config": {
            "symbols": config.SYMBOLS,
            "timeframe": config.TRADING_TIMEFRAME,
            "lot_size": config.LOT_SIZE,
            "max_positions": config.MAX_POSITIONS,
            "max_risk_percent": config.MAX_RISK_PERCENT,
            "ensemble_models": config.ENSEMBLE_MODELS,
        },
        "models": model_statuses,
        "self_learning": self_learner.get_learning_summary(),
    }


@app.get("/ai/performance")
async def ai_performance(symbol: str = None):
    """Get AI performance dashboard data."""
    return self_learner.get_performance_dashboard(symbol)


@app.get("/ai/performance/{symbol}")
async def ai_performance_symbol(symbol: str):
    """Get AI performance for a specific symbol."""
    return self_learner.get_performance_dashboard(symbol)


@app.get("/ai/trades")
async def ai_trades(symbol: str = None, limit: int = 50):
    """Get recent AI trades."""
    return db.get_recent_trades(symbol=symbol, limit=limit)


@app.get("/ai/learning-history")
async def ai_learning_history():
    """Get self-learning adaptation history."""
    return db.get_recent_adaptations(limit=30)


@app.get("/ai/regime")
async def ai_regime():
    """Get current market regime for all symbols."""
    from ai_engine.regime_detector import RegimeDetector

    regimes = {}
    for symbol in config.SYMBOLS:
        df = mt5.get_candles(symbol, config.TRADING_TIMEFRAME, count=200)
        if not df.empty:
            regime = RegimeDetector.detect(df)
            adjustments = RegimeDetector.get_regime_adjustments(regime)
            regimes[symbol] = {
                "regime": regime,
                "should_trade": RegimeDetector.should_trade(regime),
                "adjustments": adjustments,
            }
    return regimes


@app.get("/ai/features/{symbol}")
async def ai_features(symbol: str):
    """Get top features for a symbol's model."""
    if symbol not in models:
        raise HTTPException(status_code=404, detail=f"No model for {symbol}")

    model = models[symbol]
    return {
        "symbol": symbol,
        "top_features": model.get_top_features(20),
        "total_features": len(model.feature_columns),
    }


@app.post("/ai/train/{symbol}")
async def ai_train(symbol: str):
    """Manually trigger model training for a symbol."""
    if symbol not in strategies:
        raise HTTPException(status_code=404, detail=f"No strategy for {symbol}")

    result = strategies[symbol].train_model(symbol)
    return result

@app.post("/bot/start")
async def start_bot():
    """Start the live trading bot runner process."""
    global bot_process
    
    # Check if already running
    if bot_process is not None and bot_process.poll() is None:
        raise HTTPException(status_code=400, detail="Bot is already running")
    
    try:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        # Using subprocess to launch bot_runner.py. Use sys.executable to ensure we use the same Python environment.
        import sys
        bot_process = subprocess.Popen(
            [sys.executable, "trading_bot/bot_runner.py"],
            cwd=root_dir,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        return {"success": True, "message": "Bot started in background"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start bot: {str(e)}")


@app.post("/bot/stop")
async def stop_bot():
    """Stop the live trading bot runner process."""
    global bot_process
    
    if bot_process is None or bot_process.poll() is not None:
        bot_process = None
        raise HTTPException(status_code=400, detail="Bot is not currently running")
    
    try:
        if os.name == 'nt':
            # Send CTRL_BREAK_EVENT or terminate
            bot_process.terminate()
        else:
            bot_process.terminate()
            
        bot_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        bot_process.kill()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop bot: {str(e)}")
    
    bot_process = None
    return {"success": True, "message": "Bot stopped successfully"}


# ─── Model Training Endpoint ───────────────────────────────────

@app.post("/model/train")
def train_model(symbol: Optional[str] = None, timeframe: str = "H1"):
    """Trigger AI ensemble training for a specific symbol or all portfolio pairs."""
    try:
        from train_models import train_ensemble_for_symbol, train_all_symbols

        if symbol:
            res = train_ensemble_for_symbol(symbol=symbol, timeframe=timeframe)
            return {"success": True, "results": {symbol: res}}
        else:
            results = train_all_symbols(timeframe=timeframe)
            return {"success": True, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model training error: {str(e)}")

# Global live backtest log memory
latest_backtest_logs: List[str] = []
backtest_status = {"running": False, "symbol": "", "message": "Idle"}

# ─── Backtest Endpoint ───────────────────────────────────


@app.get("/backtest/logs")
def get_backtest_logs():
    """Get live logs from the currently running or last completed backtest."""
    return {
        "logs": latest_backtest_logs,
        "status": backtest_status
    }

@app.post("/backtest/run")
def run_backtest(symbol: str, initial_balance: float = 1000.0,
                 months: int = 3, timeframe: str = "H1", risk_percent: float = 5.0):
    """Run backtest for a symbol with detailed metrics and live log streaming."""
    global latest_backtest_logs, backtest_status
    latest_backtest_logs.clear()
    backtest_status = {"running": True, "symbol": symbol, "message": f"Running 1-year backtest for {symbol}"}

    def append_log(msg: str):
        latest_backtest_logs.append(msg)

    try:
        from backtest import Backtester

        if not mt5.connected:
            mt5.connect()

        resolved_symbol = mt5.resolve_symbol(symbol)
        append_log(f"  Resolved trading symbol: '{symbol}' -> '{resolved_symbol}'")

        backtester = Backtester(symbol=resolved_symbol, initial_balance=initial_balance, log_callback=append_log)
        trades = backtester.run_backtest(months=months, timeframe=timeframe)


        if not trades:
            backtest_status = {"running": False, "symbol": symbol, "message": "Failed: No trade data"}
            raise HTTPException(status_code=500, detail="Backtest failed — no trade data returned")

        backtest_status = {"running": False, "symbol": symbol, "message": "Completed successfully"}


        total_trades = len(trades)
        wins = [t for t in trades if t["profit"] > 0]
        losses = [t for t in trades if t["profit"] < 0]
        winning_trades = len(wins)
        losing_trades = len(losses)

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        total_profit = sum(t["profit"] for t in trades)

        avg_win = sum(t["profit"] for t in wins) / winning_trades if winning_trades > 0 else 0
        avg_loss = abs(sum(t["profit"] for t in losses) / losing_trades) if losing_trades > 0 else 0
        profit_factor = avg_win / avg_loss if avg_loss > 0 else (99.0 if avg_win > 0 else 0.0)

        best_trade = max((t["profit"] for t in trades), default=0.0)
        worst_trade = min((t["profit"] for t in trades), default=0.0)

        # Max drawdown
        peak = initial_balance
        max_dd = 0.0
        for pt in backtester.equity_curve:
            eq = pt["equity"]
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100.0 if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        # Regime breakdown
        regimes = {}
        for t in trades:
            r = t.get("regime", "UNKNOWN")
            if r not in regimes:
                regimes[r] = {"regime": r, "total": 0, "wins": 0, "profit": 0.0}
            regimes[r]["total"] += 1
            regimes[r]["profit"] += t["profit"]
            if t["profit"] > 0:
                regimes[r]["wins"] += 1

        regime_stats = []
        for r, st in regimes.items():
            st["win_rate"] = (st["wins"] / st["total"] * 100.0) if st["total"] > 0 else 0.0
            regime_stats.append(st)

        # Reason breakdown
        reason_stats = {}
        for t in trades:
            re = t.get("reason", "UNKNOWN")
            reason_stats[re] = reason_stats.get(re, 0) + 1

        # Downsampled equity curve for smooth charting (max 200 points)
        eq_curve = backtester.equity_curve
        if len(eq_curve) > 200:
            step = len(eq_curve) // 200
            sampled_curve = eq_curve[::step]
            if eq_curve[-1] not in sampled_curve:
                sampled_curve.append(eq_curve[-1])
        else:
            sampled_curve = eq_curve

        result_dict = {
            "success": True,
            "symbol": symbol,
            "initial_balance": initial_balance,
            "final_balance": backtester.balance,
            "total_profit": total_profit,
            "return_percent": ((backtester.balance - initial_balance) / initial_balance * 100.0),
            "max_drawdown_percent": max_dd,
            "profit_factor": profit_factor,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "best_trade": best_trade,
            "worst_trade": worst_trade,
            "equity_curve": sampled_curve,
            "regime_stats": regime_stats,
            "reason_stats": reason_stats,
            "trades": trades,
        }

        # Log to database
        db.log_backtest(
            symbol=symbol,
            timeframe=timeframe,
            initial_balance=initial_balance,
            final_balance=backtester.balance,
            total_profit=total_profit,
            win_rate=win_rate,
            total_trades=total_trades,
            results_json=result_dict
        )

        return result_dict

    except Exception as e:
        import traceback
        err_msg = f"  [FAIL] Backtest Error: {str(e)}"
        latest_backtest_logs.append(err_msg)
        latest_backtest_logs.append(traceback.format_exc())
        backtest_status = {"running": False, "symbol": symbol, "message": f"Error: {str(e)}"}
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/backtests")
async def get_backtests(limit: int = 50):
    """Get historical backtests."""
    return db.get_backtests(limit)

if __name__ == "__main__":
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)
