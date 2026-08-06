import os
from dotenv import load_dotenv

# Load .env file from script directory or workspace root
_dir = os.path.dirname(os.path.abspath(__file__))
_env_local = os.path.join(_dir, ".env")
_env_root = os.path.join(_dir, "..", ".env")

if os.path.exists(_env_local):
    load_dotenv(_env_local)
elif os.path.exists(_env_root):
    load_dotenv(_env_root)
else:
    load_dotenv()

# ─── MT5 Connection ─────────────────────────────────────
MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")

# ─── Trading Symbols ────────────────────────────────────
SYMBOLS = os.getenv(
    "SYMBOLS",
    "EURUSDm,GBPUSDm,USDJPYm,AUDUSDm,USDCADm,NZDUSDm,USDCHFm,EURGBPm,EURJPYm,GBPJPYm,XAUUSDm,BTCUSDm,US30m,NAS100m"
).split(",")
TRADING_TIMEFRAME = os.getenv("TRADING_TIMEFRAME", os.getenv("TIMEFRAME", "M5"))  # Entry timeframe

# ─── Multi-Timeframe Analysis ───────────────────────────
# Higher timeframes used for trend direction and context
MTF_TIMEFRAMES = ["M1", "M5", "M15", "H1"]

# ─── Risk Management ────────────────────────────────────
LOT_SIZE = float(os.getenv("LOT_SIZE", "0.01"))
MAX_RISK_PERCENT = float(os.getenv("MAX_RISK_PERCENT", "5.5"))
MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "10"))
MAX_POSITIONS_PER_SYMBOL = int(os.getenv("MAX_POSITIONS_PER_SYMBOL", "2"))
MAX_DAILY_DRAWDOWN_PERCENT = float(os.getenv("MAX_DAILY_DRAWDOWN_PERCENT", "15.0"))
AUTO_REDUCE_RISK_ON_DRAWDOWN = True  # Halve risk if daily drawdown > 50% of max

# ─── Smart Execution & Trailing Exits ───────────────────
PARTIAL_TP_ENABLED = True
PARTIAL_TP_PERCENT = 0.40      # Close 40% at first target (let more run)
PARTIAL_TP_RR = 1.0            # First target at 1:1 R:R
FULL_TP_RR = 2.0               # Full target at 2:1 R:R (minimum)
BREAKEVEN_ENABLED = True
BREAKEVEN_TRIGGER_RR = 1.0     # Move SL to breakeven after 1:1 reached
BREAKEVEN_BUFFER_PIPS = 2.0    # Breakeven + 2 pip buffer
TRAILING_STOP_ENABLED = True
TRAILING_STOP_TRIGGER_RR = 1.5 # Enable trailing stop at 1.5:1 R:R
TRAILING_STOP_ATR_MULT = 1.2   # Trail SL 1.2x ATR behind price peak (tighter)
MAX_TRADE_DURATION_CANDLES = 30  # Auto-close after N candles (M5 = ~2.5 hours)
SPREAD_FILTER_PERCENTILE = 85   # Skip trade if spread > 85th percentile (stricter)


# ─── Session Windows (UTC hours) ────────────────────────
# Bot will only trade during these windows per symbol type
SESSION_WINDOWS = {
    "forex": [  # 24/7 trading as requested
        (0, 24),
    ],
    "gold": [  # 24/7 trading as requested
        (0, 24),
    ],
    "indices": [ # 24/7 trading as requested
        (0, 24),
    ],
    "crypto": [  # 24/7 including weekends
        (0, 24),
    ],
    "default": [
        (0, 24),   # 24h if no specific session defined
    ],
}

# Map symbols to session types
SYMBOL_SESSION_MAP = {
    # Forex majors & crosses
    "EURUSD": "forex", "EURUSDm": "forex",
    "GBPUSD": "forex", "GBPUSDm": "forex",
    "USDJPY": "forex", "USDJPYm": "forex",
    "AUDUSD": "forex", "AUDUSDm": "forex",
    "USDCAD": "forex", "USDCADm": "forex",
    "NZDUSD": "forex", "NZDUSDm": "forex",
    "USDCHF": "forex", "USDCHFm": "forex",
    "EURGBP": "forex", "EURGBPm": "forex",
    "EURJPY": "forex", "EURJPYm": "forex",
    "GBPJPY": "forex", "GBPJPYm": "forex",
    # Gold
    "XAUUSD": "gold", "XAUUSDm": "gold", "GOLD": "gold",
    # Crypto
    "BTCUSD": "crypto", "BTCUSDm": "crypto",
    "ETHUSD": "crypto", "ETHUSDm": "crypto",
    # Indices
    "US30": "indices", "US30m": "indices",
    "NAS100": "indices", "NAS100m": "indices",
    "SPX500": "indices", "SPX500m": "indices",
}

# ─── AI Ensemble Config ─────────────────────────────────
ENSEMBLE_MODELS = ["xgboost", "lightgbm", "random_forest"]
INITIAL_MODEL_WEIGHTS = {
    "xgboost": 0.45,
    "lightgbm": 0.35,
    "random_forest": 0.20,
}

# Confidence thresholds
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.62"))
HIGH_CONFIDENCE = float(os.getenv("HIGH_CONFIDENCE", "0.75"))

# ─── Feature Engineering ────────────────────────────────
FEATURE_CANDLE_COUNT = 500   # Candles to fetch for feature calculation
LOOKBACK_PERIODS = [5, 10, 20, 50]  # Rolling window sizes

# ─── Self-Learning Loop ─────────────────────────────────
RETRAIN_INTERVAL_HOURS = int(os.getenv("RETRAIN_INTERVAL_HOURS", "6"))
FULL_RETRAIN_INTERVAL_HOURS = 24
MIN_SAMPLES_FOR_TRAINING = int(os.getenv("MIN_SAMPLES_FOR_TRAINING", "200"))
PERFORMANCE_EVAL_INTERVAL_MINUTES = 30
ROLLING_WINDOW_SIZE = 2000  # Candles for rolling retrain

# Adaptive confidence adjustment
CONFIDENCE_ADJUST_STEP = 0.02  # How much to tighten/loosen threshold
MIN_CONFIDENCE_FLOOR = 0.55    # Never go below this
MAX_CONFIDENCE_CEILING = 0.75  # Never go above this (was 0.85, too restrictive)
TARGET_WIN_RATE = 0.60         # Target win rate for threshold adaptation

# ─── Smart Execution ────────────────────────────────────
PARTIAL_TP_ENABLED = True
PARTIAL_TP_PERCENT = 0.50      # Close 50% at first target
PARTIAL_TP_RR = 1.0            # First target at 1:1 R:R
FULL_TP_RR = 2.0               # Full target at 2:1 R:R
BREAKEVEN_ENABLED = True
BREAKEVEN_TRIGGER_RR = 1.0     # Move SL to breakeven after 1:1 reached
BREAKEVEN_BUFFER_PIPS = 1.0    # Breakeven + 1 pip buffer
MAX_TRADE_DURATION_CANDLES = 20  # Auto-close after N candles (M5 = ~1.5 hours)
SPREAD_FILTER_PERCENTILE = 90   # Skip trade if spread > 90th percentile

# ─── API Configuration ──────────────────────────────────
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "6542"))

# ─── Paths ───────────────────────────────────────────────
MODELS_DIR = "trading_bot/models"
DATA_DIR = "trading_bot/data"
DB_PATH = "trading_bot/data/trading_bot.db"
TRADE_LOG_PATH = "trading_bot/data/trade_log.csv"


def get_model_dir(symbol: str) -> str:
    """Get model directory for a specific symbol"""
    return f"{MODELS_DIR}/{symbol}"


def get_session_type(symbol: str) -> str:
    """Get session type for a symbol"""
    # Check exact match first
    if symbol in SYMBOL_SESSION_MAP:
        return SYMBOL_SESSION_MAP[symbol]
    # Check partial match (e.g., XAUUSDm matches XAUUSD)
    for key, session_type in SYMBOL_SESSION_MAP.items():
        if key in symbol or symbol in key:
            return session_type
    return "default"


def get_session_windows(symbol: str) -> list:
    """Get trading session windows for a symbol"""
    session_type = get_session_type(symbol)
    return SESSION_WINDOWS.get(session_type, SESSION_WINDOWS["default"])
