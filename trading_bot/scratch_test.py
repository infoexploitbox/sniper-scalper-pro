import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'trading_bot'))

from mt5_connector import MT5Connector
from smart_executor import SmartExecutor
from ai_engine.database import TradingDatabase

def main():
    mt5 = MT5Connector()
    if not mt5.connect():
        print("Failed to connect to MT5")
        return
    db = TradingDatabase()
    executor = SmartExecutor(mt5, db)
    
    symbols = ["BTCUSDm", "US30m", "USDJPYm", "GBPJPYm"]
    for sym in symbols:
        spread_ok, msg = executor._check_spread(sym)
        print(f"[{sym}] Spread check: {spread_ok} | Msg: {msg}")
        
        tick = mt5.get_tick(sym)
        if tick:
            spread = tick["ask"] - tick["bid"]
            print(f"[{sym}] Actual Spread: {spread}")
            
        can_trade, reason = executor.can_open_trade(sym, "TRENDING_UP", "BUY")
        print(f"[{sym}] can_open_trade: {can_trade} | Reason: {reason}")
        
if __name__ == "__main__":
    main()
