# 📊 Dashboard Features - Connected to Python AI Bot

## Overview

Your React dashboard is now fully integrated with the Python AI trading bot. All data is real-time from your MT5 account via the bot's API.

## 🎯 Key Features

### 1. Dashboard Page (/)
**Real-Time Account Monitoring**
- Live balance, equity, and P&L
- Open positions table with close buttons
- Bot status card showing:
  - Trading symbols (EURUSD, XAUUSD)
  - Timeframe and risk settings
  - Model accuracy percentage
  - Total trades executed
  - Average confidence level
- Connection status indicator
- Auto-refresh every 5 seconds

### 2. AI Signals Page (/signals)
**Neural Network Predictions**
- Real-time AI signals for all configured symbols
- Confidence levels (0-100%)
- Signal direction: BUY, SELL, or HOLD
- Entry price, stop loss, and take profit levels
- ATR (Average True Range) for volatility
- Color-coded confidence:
  - 🎯 VERY HIGH (80%+) - Green
  - 🔥 HIGH (60-80%) - Yellow
  - ⚡ MEDIUM (40-60%) - Gray
  - 📊 LOW (<40%) - Muted
- Auto-refresh every minute
- Manual refresh button

### 3. Calculator Page (/calculator)
**Position Size Calculator**
- Calculate lot size based on risk
- Account balance integration
- Stop loss distance calculator
- Risk/reward ratio calculator

### 4. Risk Manager Page (/risk)
**Risk Analysis Tools**
- Portfolio risk overview
- Position correlation analysis
- Drawdown calculator
- Risk per symbol breakdown

### 5. Journal Page (/journal)
**Trade History & Notes**
- View past trades
- Add notes and tags
- Performance analytics
- Win/loss statistics

### 6. Settings Page (/settings)
**Bot Configuration**
- API endpoint configuration
- Symbol watchlist
- Notification preferences
- Theme settings

## 🔌 API Integration

### Endpoints Used

```typescript
// Account & Positions
GET /account          // Account info
GET /positions        // Open positions
POST /trade/close     // Close position

// AI Bot Specific
GET /analyze?symbol=EURUSD  // Get AI signal for symbol
GET /bot/status             // Bot status and metrics
GET /candles?symbol=...     // Historical data
GET /tick?symbol=...        // Current price
```

### Data Flow

```
MT5 Terminal
    ↓
Python Bot (localhost:6542)
    ↓
React Dashboard (localhost:8080)
```

## 🎨 UI Components

### Bot Status Card
Shows when bot is connected:
- Active symbols being traded
- Current timeframe
- Risk settings
- Model performance metrics
- Training status

### Signal Cards
For each symbol:
- Symbol name (EURUSD, XAUUSD, etc.)
- Signal direction badge (BUY/SELL/HOLD)
- Confidence bar with percentage
- Entry, SL, TP prices
- ATR value
- Timestamp

### Position Table
- Symbol
- Type (BUY/SELL)
- Volume
- Open price
- Current price
- Stop loss
- Take profit
- Profit/Loss
- Close button

## 🔄 Real-Time Updates

### Auto-Refresh Intervals
- Dashboard: Every 5 seconds
- AI Signals: Every 60 seconds (when auto-refresh enabled)
- Manual refresh available on all pages

### Live Data
- Account balance and equity
- Position P&L
- AI confidence levels
- Model accuracy
- Trade count

## 🎯 Usage Tips

### Monitoring the Bot
1. Check Dashboard for bot status
2. Verify model accuracy (should be >60%)
3. Monitor open positions
4. Watch confidence levels on signals

### Understanding Signals
- **HOLD**: No clear direction, bot won't trade
- **BUY/SELL with <60% confidence**: Bot won't execute
- **BUY/SELL with >60% confidence**: Bot will trade
- **>80% confidence**: Very strong signal

### Risk Management
- Dashboard shows total positions
- Max 5 positions total
- Max 2 per symbol
- Each trade risks 2% of balance

## 🚀 Advanced Features

### Multi-Symbol Support
- Each symbol has its own AI model
- Independent predictions
- Separate risk management
- Parallel analysis

### Model Performance Tracking
- Accuracy percentage
- Training count
- Last trained timestamp
- Total trades executed
- Average confidence

### Connection Monitoring
- Live/Offline badge
- Connection test button
- Error messages
- Reconnection handling

## 📱 Responsive Design

- Works on desktop, tablet, and mobile
- Adaptive layouts
- Touch-friendly buttons
- Optimized for all screen sizes

## 🎨 Theme Support

- Light and dark modes
- Consistent color scheme
- Profit/Loss color coding:
  - Green for profit/buy
  - Red for loss/sell
  - Gray for neutral/hold

## 🔔 Notifications

- Toast notifications for:
  - Trade executions
  - Position closes
  - Connection status
  - Signal updates
  - Errors and warnings

## 📊 Data Visualization

- Real-time P&L charts
- Confidence level bars
- Performance metrics
- Account statistics

---

**Your dashboard is now a complete trading command center!** 🎯

Monitor your AI bot, view real-time signals, manage positions, and track performance all in one place.
