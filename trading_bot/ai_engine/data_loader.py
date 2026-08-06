import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Union

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

class DataLoader:
    """
    Multi-source historical dataset loader & preprocessor.
    Supports importing CSV/Parquet files from Dukascopy, MetaTrader, Tickstory,
    and automatic historical downloading via yfinance/MT5.
    """

    @staticmethod
    def ensure_data_dir() -> str:
        """Ensure data directory exists."""
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)
        return DATA_DIR

    @staticmethod
    def load_csv(filepath: str, symbol: str) -> Optional[pd.DataFrame]:
        """
        Load historical OHLCV data from a CSV file.
        Supports Dukascopy, MT5 export, and MetaTrader formats.
        """
        if not os.path.exists(filepath):
            print(f"[DataLoader] File not found: {filepath}")
            return None

        try:
            df = pd.read_csv(filepath)
            df.columns = [c.strip().lower() for c in df.columns]

            # Column mapping aliases
            col_map = {
                "date": "time", "datetime": "time", "gmt time": "time", "timestamp": "time",
                "open": "open", "high": "high", "low": "low", "close": "close",
                "vol": "tick_volume", "volume": "tick_volume", "vol(ticks)": "tick_volume"
            }

            df = df.rename(columns=col_map)

            if "time" not in df.columns or "close" not in df.columns:
                print(f"[DataLoader] CSV missing required columns (time, close). Found: {list(df.columns)}")
                return None

            df["time"] = pd.to_datetime(df["time"])
            df = df.sort_values("time").reset_index(drop=True)

            for col in ["open", "high", "low", "close"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            if "tick_volume" not in df.columns:
                df["tick_volume"] = 1000

            df["symbol"] = symbol
            df = df.dropna(subset=["open", "high", "low", "close"])

            print(f"[DataLoader] Successfully loaded {len(df)} candles from {os.path.basename(filepath)}")
            return df
        except Exception as e:
            print(f"[DataLoader] Error reading CSV {filepath}: {e}")
            return None

    @staticmethod
    def fetch_yfinance_data(symbol: str, period: str = "2y", interval: str = "1h") -> Optional[pd.DataFrame]:
        """
        Download historical candles from Yahoo Finance as a quick fallback.
        """
        try:
            import yfinance as yf

            # Map forex/gold/crypto symbols to Yahoo tickers
            ticker_map = {
                "EURUSD": "EURUSD=X",
                "GBPUSD": "GBPUSD=X",
                "USDJPY": "JPY=X",
                "AUDUSD": "AUDUSD=X",
                "USDCAD": "CAD=X",
                "XAUUSD": "GC=F",
                "BTCUSD": "BTC-USD",
            }

            ticker = ticker_map.get(symbol, f"{symbol}=X")
            print(f"[DataLoader] Fetching historical data for {symbol} ({ticker}) via yfinance...")

            df = yf.download(ticker, period=period, interval=interval, progress=False)

            if df.empty:
                print(f"[DataLoader] No data returned from yfinance for {ticker}")
                return None

            # Reset multi-index if returned by yfinance
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df = df.reset_index()
            df.columns = [c.lower() for c in df.columns]

            col_map = {"date": "time", "datetime": "time", "volume": "tick_volume"}
            df = df.rename(columns=col_map)

            df["symbol"] = symbol
            df["time"] = pd.to_datetime(df["time"])
            df = df.sort_values("time").reset_index(drop=True)

            print(f"[DataLoader] Loaded {len(df)} candles for {symbol} from Yahoo Finance")
            return df
        except Exception as e:
            print(f"[DataLoader] yfinance fetch failed: {e}")
            return None

    @staticmethod
    def resample_candles(df: pd.DataFrame, timeframe: str = "5T") -> pd.DataFrame:
        """
        Resample lower timeframe candles (e.g. M1) to target timeframe (e.g. M5, H1).
        """
        if df is None or df.empty:
            return pd.DataFrame()

        df = df.set_index("time")
        resampled = df.resample(timeframe).agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "tick_volume": "sum",
        }).dropna().reset_index()

        return resampled

    @staticmethod
    def save_dataset(df: pd.DataFrame, symbol: str, timeframe: str) -> str:
        """Save processed dataframe to Parquet for fast loading."""
        DataLoader.ensure_data_dir()
        filename = os.path.join(DATA_DIR, f"{symbol}_{timeframe}.parquet")
        df.to_parquet(filename, index=False)
        print(f"[DataLoader] Saved dataset to {filename} ({len(df)} rows)")
        return filename

    @staticmethod
    def load_dataset(symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Load pre-saved Parquet dataset."""
        filename = os.path.join(DATA_DIR, f"{symbol}_{timeframe}.parquet")
        if os.path.exists(filename):
            print(f"[DataLoader] Loading pre-saved dataset {filename}...")
            return pd.read_parquet(filename)
        return None
