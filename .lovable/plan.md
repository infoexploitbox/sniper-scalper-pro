

# Free MT5 Connection — Local REST API Bridge

## The Problem
MetaAPI.cloud is a paid service. You have MT5 installed locally, so we can skip it entirely.

## The Solution: Local REST API via MT5 Expert Advisor

There's an open-source project called **mt5-rest** (github.com/mikha-dev/mt5-rest) — it's a free MQL5 Expert Advisor that you install directly into your MT5 terminal. Once running, it turns your MT5 into a REST API server on your PC (e.g., `http://localhost:6542`).

Since our React app runs **in your browser on the same PC**, it can call `localhost` directly — no cloud service needed, no paid API, no middleman.

```text
┌─────────────────────┐         ┌──────────────────┐
│  React Dashboard    │──HTTP──▶│  MT5 Terminal     │
│  (in your browser)  │localhost│  + mt5-rest EA    │
│                     │◀──JSON──│  (port 6542)      │
└─────────────────────┘         └──────────────────┘
        Same PC — no cloud needed
```

## What We'll Build

### Setup Guide Page
- Step-by-step instructions to install the mt5-rest EA into MT5
- Connection test button to verify the bridge is working

### MT5 Service Layer
- TypeScript service that calls the local REST API (`localhost:6542`)
- Functions: get account info, get positions, place orders, get market data, close positions

### Dashboard Pages (same as before)
1. **Dashboard** — Account balance, equity, open positions, one-click close
2. **Signal Engine** — Multi-strategy analysis (EMA crossover, RSI+S/R, Smart Money, Price Action) with confluence scoring
3. **Auto-Trade** — When signals meet confluence threshold, execute trades via the local API
4. **Position Calculator** — Auto lot sizing for $10–$100M accounts
5. **Risk Manager** — Daily drawdown limits, max positions, stop-trading rules
6. **Trade Journal** — Log and analyze past trades by strategy/pair/session
7. **Settings** — Configure pairs, risk %, auto-trade on/off, localhost port

### Strategy Engine (client-side)
- Fetches candle data from MT5 via the local API
- Runs all strategy calculations in the browser
- Generates signals with confluence scores
- Auto-executes when enabled and threshold met

## Important Notes
- **Works only when MT5 is open** on your PC with the EA running
- **No Supabase needed** — everything runs locally, no secrets to store
- **No latency penalty** — localhost calls are near-instant
- **Free forever** — no API subscriptions
- CORS may need handling — we'll add a proxy configuration or use the EA's built-in settings

## Implementation Order
1. Setup guide page + MT5 service layer + connection test
2. Dashboard with live account data
3. Market data fetching + signal engine with all strategies
4. Auto-trade execution + risk manager
5. Position calculator + trade journal
6. Settings page

