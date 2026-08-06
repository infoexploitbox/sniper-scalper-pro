# AI Trading Bot for MT5

An intelligent trading bot that connects directly to MetaTrader 5, uses machine learning to make trading decisions, and continuously learns to improve its performance.

## Features

- **Direct MT5 Connection**: No EA required, connects directly via Python
- **Machine Learning**: Neural network that learns from historical data
- **Auto-Trading**: Executes trades automatically based on AI signals
- **Risk Management**: Built-in position sizing and risk controls
- **Self-Improving**: Retrains periodically to adapt to market conditions
- **REST API**: Provides API for your React dashboard
- **Technical Analysis**: 20+ technical indicators for decision making

## Quick Start

### 1. Install Dependencies

```bash
cd trading_bot
pip install -r requirements.txt
```

### 2. Configure Settings

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` with your MT5 credentials:

```
MT5_LOGIN=your_account_number
MT5_PASSWORD=your_password
MT5_SERVER=your_broker_server

SYMBOL=EURUSD
TIMEFRAME=M5
LOT_SIZE=0.01
MAX_RISK_PERCENT=2.0
MAX_POSITIONS=3
```

### 3. Run the Bot

**Option A: Auto-Trading Mode** (Bot trades independently)
```bash
python bot_runner.py
```

**Option B: API Server Mode** (Manual control via React app)
```bash
python api_server.py
```

**Option C: Both** (Run in separate terminals)
```bash
# Terminal 1
python api_server.py

# Terminal 2
python bot_runner.py
```

## How It Works

### 1. Data Collection
- Fetches historical price data from MT5
- Calculates 20+ technical indicators (RSI, MACD, Bollinger Bands, etc.)

### 2. Machine Learning
- Neural network trained on historical patterns
- Predicts: BUY, SELL, or HOLD
- Provides confidence score for each prediction

### 3. Trading Execution
- Only trades when confidence > 60%
- Calculates position size based on risk (default 2% per trade)
- Sets stop loss and take profit based on ATR
- Respects max position limit

### 4. Continuous Learning
- Retrains model every 24 hours (configurable)
- Adapts to changing market conditions
- Tracks performance metrics

## API Endpoints

The bot provides a REST API on `http://localhost:6542`:

- `GET /account` - Account information
- `GET /positions` - Open positions
- `GET /analyze?symbol=EURUSD` - Get AI trading signal
- `GET /candles?symbol=EURUSD&timeframe=M5&count=100` - Historical data
- `GET /bot/status` - Bot status and statistics
- `POST /trade/open` - Place manual trade
- `POST /trade/close` - Close position

## Configuration

### Trading Parameters

- `SYMBOLS`: Trading pairs separated by commas (default: EURUSD,XAUUSD)
  - EURUSD = Euro/US Dollar
  - XAUUSD = Gold/US Dollar
  - Add more: GBPUSD,USDJPY,BTCUSD, etc.
- `TIMEFRAME`: Chart timeframe (M1, M5, M15, M30, H1, H4, D1)
- `LOT_SIZE`: Base lot size (default: 0.01)
- `MAX_RISK_PERCENT`: Max risk per trade (default: 2%)
- `MAX_POSITIONS`: Maximum total concurrent positions (default: 5)
- `MAX_POSITIONS_PER_SYMBOL`: Max positions per symbol (default: 2)

### ML Parameters

- `RETRAIN_INTERVAL_HOURS`: How often to retrain (default: 24)
- `MIN_TRADES_FOR_TRAINING`: Minimum data points needed (default: 100)

## Safety Features

- **Risk Management**: Never risks more than configured percentage
- **Position Limits**: Won't open more than max positions
- **Confidence Threshold**: Only trades with >60% confidence
- **Stop Loss**: Always sets stop loss on every trade
- **Connection Monitoring**: Handles MT5 disconnections gracefully

## Monitoring

The bot logs all activity to console:
- Trading signals and confidence levels
- Trade executions
- Account balance and equity
- Model retraining events
- Errors and warnings

## Troubleshooting

### "MT5 initialization failed"
- Make sure MT5 terminal is running
- Check your credentials in `.env`
- Verify MT5 allows API connections (Tools > Options > Expert Advisors)

### "No data available"
- Check if symbol is correct
- Ensure you have market data in MT5
- Try a different timeframe

### "Model training failed"
- Need at least 100 candles of historical data
- Check if symbol has enough history
- Reduce `MIN_TRADES_FOR_TRAINING` in config

## Next Steps

1. **Backtest**: Test the strategy on historical data before live trading
2. **Paper Trade**: Use a demo account first
3. **Monitor**: Watch the bot for a few days before increasing lot size
4. **Optimize**: Adjust parameters based on performance
5. **Scale**: Gradually increase position sizes as confidence grows

## Warning

⚠️ **Trading involves risk. This bot is for educational purposes. Always:**
- Start with a demo account
- Use small position sizes
- Monitor the bot regularly
- Understand the risks involved
- Never trade with money you can't afford to lose

## Support

For issues or questions, check:
- MT5 connection status
- Log files for errors
- Configuration settings
- API endpoint responses
