import os
import sys
import pandas as pd
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mt5_connector import MT5Connector
from ai_engine.data_loader import DataLoader, DATA_DIR

DEFAULT_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD", "BTCUSD"]

def download_all_training_datasets(symbols: List[str] = DEFAULT_PAIRS):
    """
    Download and cache multi-year historical datasets for all trading pairs.
    Saves datasets in trading_bot/data/ as .parquet and .csv files for fast ML training.
    """
    DataLoader.ensure_data_dir()
    print(f"\n{'='*70}")
    print(f"   DOWNLOADING MULTI-YEAR HISTORICAL DATASETS FOR AI TRAINING")
    print(f"   Pairs: {', '.join(symbols)}")
    print(f"   Destination: {DATA_DIR}")
    print(f"{'='*70}\n")

    mt5 = MT5Connector()
    mt5_connected = mt5.connect()
    if mt5_connected:
        print("  [OK] Connected to MetaTrader 5 terminal for direct broker history download.")

    download_summary = []

    for sym in symbols:
        print(f"\n------------------------------------------------------------")
        print(f"  Processing dataset for: {sym}")
        print(f"------------------------------------------------------------")

        df = None

        # Source 1: Fetch maximum history from MT5
        if mt5_connected:
            real_symbol = mt5.resolve_symbol(sym)
            print(f"  [Source 1: MT5] Requesting historical candles for {real_symbol}...")
            for tf in ["H1", "M5"]:
                for count in [100000, 70000, 50000, 30000]:
                    raw_df = mt5.get_candles(real_symbol, tf, count=count)
                    if not raw_df.empty and len(raw_df) >= 1000:
                        df = raw_df
                        df["symbol"] = sym
                        print(f"    -> MT5 returned {len(df)} {tf} candles (From {df['time'].iloc[0]} to {df['time'].iloc[-1]})")
                        break
                if df is not None and not df.empty:
                    break

        # Source 2: Fallback / Complement with Yahoo Finance multi-year dataset
        if df is None or len(df) < 5000:
            print(f"  [Source 2: Yahoo Finance] Downloading multi-year history for {sym}...")
            yf_df = DataLoader.fetch_yfinance_data(sym, period="2y", interval="1h")
            if yf_df is not None and not yf_df.empty:
                if df is None or len(yf_df) > len(df):
                    df = yf_df

        if df is not None and not df.empty:
            # Save to CSV and Parquet in trading_bot/data/
            csv_path = os.path.join(DATA_DIR, f"{sym}_history.csv")
            df.to_csv(csv_path, index=False)

            try:
                parquet_path = os.path.join(DATA_DIR, f"{sym}_history.parquet")
                df.to_parquet(parquet_path, index=False)
            except Exception:
                pass

            size_mb = os.path.getsize(csv_path) / (1024 * 1024)
            start_date = str(df["time"].iloc[0]).split(" ")[0]
            end_date = str(df["time"].iloc[-1]).split(" ")[0]

            print(f"  [SAVED] {sym}_history.csv")
            print(f"          Rows: {len(df):,} candles | Period: {start_date} to {end_date} | Size: {size_mb:.2f} MB")


            download_summary.append({
                "symbol": sym,
                "status": "SUCCESS",
                "rows": len(df),
                "start": start_date,
                "end": end_date,
                "size_mb": round(size_mb, 2),
            })
        else:
            print(f"  [FAIL] Failed to download dataset for {sym}")
            download_summary.append({
                "symbol": sym,
                "status": "FAILED",
                "rows": 0,
            })

    print(f"\n============================================================")
    print(f"   DATASET DOWNLOAD SUMMARY ({len(download_summary)} PAIRS)")
    print(f"============================================================")
    for s in download_summary:
        if s["status"] == "SUCCESS":
            print(f"   [OK] {s['symbol']}: {s['rows']:,} rows ({s['start']} -> {s['end']}) | {s['size_mb']} MB")
        else:
            print(f"   [FAIL] {s['symbol']}: Download failed")
    print(f"============================================================\n")

    return download_summary

if __name__ == "__main__":
    download_all_training_datasets()
