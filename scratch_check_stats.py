import sqlite3
import pandas as pd
import sys

try:
    conn = sqlite3.connect('trading_bot/data/trading_bot.db')
    
    # Check what tables exist
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables in DB: {tables}")
    
    if ('trades',) in tables:
        df = pd.read_sql('SELECT * FROM trades', conn)
        print(f"Total Trades Logged: {len(df)}")
        
        if len(df) > 0:
            if 'profit' in df.columns:
                win_rate = (df['profit'] > 0).mean() * 100
                total_pnl = df['profit'].sum()
                print(f"Win Rate: {win_rate:.2f}%")
                print(f"Total PnL: ${total_pnl:.2f}")
                
                print("\nPnL by Symbol:")
                print(df.groupby('symbol')['profit'].sum())
                
                if 'close_reason' in df.columns:
                    print("\nTrades by Close Reason:")
                    print(df.groupby('close_reason').size())
            else:
                print("No 'profit' column found in trades table.")
                print(df.head())
    else:
        print("No 'trades' table found.")
        
except Exception as e:
    print(f"Error: {e}")
