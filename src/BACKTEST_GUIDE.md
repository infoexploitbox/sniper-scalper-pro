# 🎯 Backtest Feature - Complete Guide

## Overview

You can now run backtests directly from your dashboard! Test the AI trading strategy on historical data with any symbol, timeframe, and starting balance.

## How to Access

1. **Open Dashboard**: http://localhost:8080
2. **Navigate to**: Backtest page (Target icon in sidebar)
3. **Configure and Run**: Set parameters and click "Run Backtest"

## Features

### Configuration Options

- **Symbol**: Choose which pair to test (EURUSD, XAUUSDm/Gold, GBPUSD, USDJPY)
- **Initial Balance**: Starting capital ($1 - $10,000+)
- **Period**: How many months of history (1-12 months)
- **Timeframe**: M5, M15, M30, H1, H4, D1

### What It Does

1. **Fetches Historical Data**: Downloads price data from MT5
2. **Trains AI Model**: Uses 70% of data to train neural network
3. **Tests Strategy**: Simulates trading on remaining 30%
4. **Shows Results**: Complete performance analysis

### Results Displayed

**Summary Cards:**
- Final Balance
- Total Profit/Loss
- Return Percentage
- Win Rate

**Detailed Stats:**
- Initial vs Final Balance
- Total Trades
- Winning Trades
- Losing Trades

**Trade History Table:**
- Entry/Exit prices
- Trade type (BUY/SELL)
- Volume
- Profit/Loss
- AI Confidence level
- Close reason (TP Hit, SL Hit, Signal Reversal)

## Example Usage

### Test Gold with $10

```
Symbol: XAUUSDm
Initial Balance: $10
Period: 3 months
Timeframe: H1
```

Click "Run Backtest" and wait 5-10 minutes.

### Expected Results

The backtest will show:
- How the AI would have performed
- Win rate and profitability
- Every trade executed
- Model accuracy

## How It Works

### Training Phase (70% of data)
1. Calculates 20+ technical indicators
2. Trains neural network on patterns
3. Learns to predict BUY/SELL/HOLD

### Testing Phase (30% of data)
1. AI makes predictions on unseen data
2. Executes trades when confidence > 60%
3. Manages positions with SL/TP
4. Tracks all trades and P&L

### Risk Management
- Max 2% risk per trade
- Position sizing based on ATR
- Stop loss always set
- Max 2 positions per symbol

## Tips for Best Results

1. **Use H1 or H4 timeframe**: More reliable data availability
2. **Test 3+ months**: More data = better training
3. **Start with $10**: Realistic for small accounts
4. **Compare symbols**: See which performs best
5. **Check win rate**: Aim for >55%

## Understanding Results

### Good Performance
- Win rate: >55%
- Return: >10% per month
- Profit factor: >1.5
- Max drawdown: <20%

### Needs Improvement
- Win rate: <50%
- Return: <5% per month
- Profit factor: <1.0
- Max drawdown: >30%

## Limitations

- **Historical data only**: Past performance ≠ future results
- **Market conditions change**: Model trained on specific period
- **Slippage not included**: Real trading has execution delays
- **Spread simplified**: Actual spreads may vary

## After Backtesting

### If Results Are Good
1. Model is automatically saved
2. Bot can use it for live trading
3. Start with small lot sizes
4. Monitor performance

### If Results Are Poor
1. Try different timeframe
2. Test different period
3. Check if enough data available
4. Consider different symbol

## Technical Details

### Model Training
- Neural network with 3 hidden layers
- 128, 64, 32 neurons
- Dropout for regularization
- Early stopping to prevent overfitting

### Features Used
- Moving averages (SMA, EMA)
- MACD and signal
- RSI and Stochastic
- Bollinger Bands
- ATR for volatility
- Support/Resistance levels
- Volume analysis
- Trend strength

### Trade Execution
- Only trades when confidence > 60%
- SL = 2 × ATR
- TP = 3 × ATR
- Position size based on risk %

## Troubleshooting

### "Backtest failed - no trades generated"
- Not enough historical data
- Try different timeframe (H1 or H4)
- Check if symbol is available

### Takes too long
- Normal for first run (training model)
- Reduce period (try 1-2 months)
- Use larger timeframe (H4 or D1)

### Connection error
- Make sure API server is running
- Check MT5 is connected
- Verify symbol name is correct

## Command Line Alternative

You can also run backtests from command line:

```bash
cd trading_bot
python backtest.py
```

Edit `backtest.py` to change symbol/parameters.

---

**Ready to test your strategy?** Open the dashboard and navigate to the Backtest page! 🚀
