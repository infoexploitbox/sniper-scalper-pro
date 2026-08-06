# 🚀 Sniper Scalper Pro - Quick Start Guide

An AI-powered trading platform with React dashboard and Python machine learning bot.

## What You Have

1. **React Dashboard** - Beautiful web interface to monitor trades
2. **Python AI Bot** - Neural network that trades EURUSD and Gold automatically
3. **Direct MT5 Connection** - No EA needed, connects via Python

## 🎯 Quick Start (3 Steps)

### Step 1: Start MT5
- Open MetaTrader 5
- Login to your account (already configured: Exness-MT5Trial9)

### Step 2: Start the Trading Bot
Double-click: **START_BOTH.bat**

This will:
- Start the API server (port 6542)
- Start the auto-trading bot
- Connect to MT5
- Train AI models for EURUSD and XAUUSD
- Begin trading automatically

### Step 3: Open the Dashboard
In a new terminal:
```bash
npm run dev
```

Then open: http://localhost:8080

## 📊 What the Bot Does

### Symbols Trading
- **EURUSD** (Euro/US Dollar)
- **XAUUSD** (Gold/US Dollar)

### AI Features
- Analyzes 20+ technical indicators (RSI, MACD, Bollinger Bands, ATR, etc.)
- Neural network predicts: BUY, SELL, or HOLD
- Only trades when confidence > 60%
- Separate AI model for each symbol

### Risk Management
- Max 2% risk per trade
- Max 5 total positions
- Max 2 positions per symbol
- Automatic stop loss and take profit
- Position sizing based on account balance

### Learning & Improvement
- Retrains every 24 hours
- Adapts to market conditions
- Tracks performance metrics
- Improves accuracy over time

## 🎮 Dashboard Features

### Pages

1. **Dashboard** - Account overview, open positions, bot status
2. **AI Signals** - Real-time AI predictions for all symbols
3. **Calculator** - Position size calculator
4. **Risk Manager** - Risk analysis tools
5. **Journal** - Trade history and notes
6. **Settings** - Bot configuration

### Real-Time Data
- Account balance and equity
- Open positions with P&L
- AI confidence levels
- Model accuracy metrics
- Live signals for each symbol

## ⚙️ Configuration

Edit `trading_bot/.env` to customize:

```env
# Symbols to trade (comma-separated)
SYMBOLS=EURUSD,XAUUSD

# Add more symbols
SYMBOLS=EURUSD,XAUUSD,GBPUSD,USDJPY

# Risk settings
MAX_RISK_PERCENT=2.0
MAX_POSITIONS=5
MAX_POSITIONS_PER_SYMBOL=2

# Timeframe
TIMEFRAME=M5
```

## 📁 Project Structure

```
sniper-scalper-pro/
├── src/                    # React dashboard
│   ├── pages/             # Dashboard pages
│   ├── components/        # UI components
│   └── services/          # API services
├── trading_bot/           # Python AI bot
│   ├── bot_runner.py     # Main bot
│   ├── api_server.py     # REST API
│   ├── ml_model.py       # Neural network
│   ├── mt5_connector.py  # MT5 connection
│   └── .env              # Configuration
├── START_BOTH.bat        # Start everything
├── START_TRADING_BOT.bat # Bot only
└── START_API_SERVER.bat  # API only
```

## 🔧 Troubleshooting

### Bot won't connect to MT5
- Make sure MT5 is running and logged in
- Check credentials in `trading_bot/.env`
- Restart the bot

### Dashboard shows "Not Connected"
- Make sure you ran `START_BOTH.bat` or `START_API_SERVER.bat`
- Check if port 6542 is available
- Refresh the dashboard

### Model training takes long
- First time training takes 2-3 minutes per symbol
- Needs at least 100 candles of historical data
- Be patient, it only happens once!

### No trades being executed
- Check if confidence is above 60%
- Verify max positions not reached
- Look at bot console for messages
- Market might be in HOLD state

## 🎓 How It Works

1. **Data Collection**: Bot fetches historical price data from MT5
2. **Feature Engineering**: Calculates 20+ technical indicators
3. **AI Prediction**: Neural network analyzes patterns and predicts direction
4. **Risk Calculation**: Determines position size based on account risk
5. **Trade Execution**: Places trade if confidence > 60%
6. **Position Management**: Monitors and manages open positions
7. **Continuous Learning**: Retrains model every 24 hours

## 📈 Performance Monitoring

The dashboard shows:
- **Model Accuracy**: How well the AI predicts (aim for >60%)
- **Confidence Levels**: AI certainty for each prediction
- **Win Rate**: Percentage of profitable trades
- **Total Trades**: Number of trades executed
- **P&L**: Real-time profit/loss

## ⚠️ Important Notes

- **Start with Demo**: Always test on demo account first
- **Monitor Regularly**: Check the bot daily
- **Small Positions**: Start with 0.01 lots
- **Risk Management**: Never risk more than you can afford to lose
- **Market Hours**: Bot trades 24/5 (Forex hours)

## 🚀 Next Steps

1. **Monitor for 24 hours** - Watch how the bot trades
2. **Check AI accuracy** - Should improve after first retrain
3. **Adjust risk** - Increase lot size gradually if profitable
4. **Add symbols** - Edit SYMBOLS in .env to trade more pairs
5. **Optimize** - Adjust MAX_RISK_PERCENT based on results

## 📞 Support

- Check bot console for detailed logs
- Dashboard shows real-time status
- Review `trading_bot/README.md` for advanced config

---

**Happy Trading! 🎯📈**

Remember: Past performance doesn't guarantee future results. Trade responsibly!
