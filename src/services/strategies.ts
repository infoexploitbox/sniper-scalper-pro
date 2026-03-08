// Strategy Engine — runs client-side on candle data from MT5
import type { Candle } from "./mt5Api";

export interface Signal {
  id: string;
  symbol: string;
  direction: "BUY" | "SELL";
  strategies: string[];
  confluenceScore: number; // 1-5
  entryPrice: number;
  sl: number;
  tp: number;
  riskReward: number;
  timestamp: Date;
  timeframe: string;
}

// ─── Indicators ────────────────────────────────────────

function ema(closes: number[], period: number): number[] {
  const k = 2 / (period + 1);
  const result: number[] = [closes[0]];
  for (let i = 1; i < closes.length; i++) {
    result.push(closes[i] * k + result[i - 1] * (1 - k));
  }
  return result;
}

function rsi(closes: number[], period: number = 14): number[] {
  const result: number[] = [];
  let gains = 0, losses = 0;

  for (let i = 1; i <= period; i++) {
    const diff = closes[i] - closes[i - 1];
    if (diff > 0) gains += diff;
    else losses -= diff;
  }

  let avgGain = gains / period;
  let avgLoss = losses / period;
  result.length = period;
  result[period] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);

  for (let i = period + 1; i < closes.length; i++) {
    const diff = closes[i] - closes[i - 1];
    avgGain = (avgGain * (period - 1) + (diff > 0 ? diff : 0)) / period;
    avgLoss = (avgLoss * (period - 1) + (diff < 0 ? -diff : 0)) / period;
    result[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  }

  return result;
}

function findSwingHighs(candles: Candle[], lookback: number = 5): number[] {
  const highs: number[] = [];
  for (let i = lookback; i < candles.length - lookback; i++) {
    let isHigh = true;
    for (let j = i - lookback; j <= i + lookback; j++) {
      if (j !== i && candles[j].high >= candles[i].high) {
        isHigh = false;
        break;
      }
    }
    if (isHigh) highs.push(candles[i].high);
  }
  return highs;
}

function findSwingLows(candles: Candle[], lookback: number = 5): number[] {
  const lows: number[] = [];
  for (let i = lookback; i < candles.length - lookback; i++) {
    let isLow = true;
    for (let j = i - lookback; j <= i + lookback; j++) {
      if (j !== i && candles[j].low <= candles[i].low) {
        isLow = false;
        break;
      }
    }
    if (isLow) lows.push(candles[i].low);
  }
  return lows;
}

// ─── Strategy 1: EMA Crossover (9/21) ─────────────────

function emaStrategy(candles: Candle[]): { direction: "BUY" | "SELL" | null } {
  const closes = candles.map((c) => c.close);
  const ema9 = ema(closes, 9);
  const ema21 = ema(closes, 21);
  const last = closes.length - 1;
  const prev = last - 1;

  if (ema9[prev] <= ema21[prev] && ema9[last] > ema21[last]) {
    return { direction: "BUY" };
  }
  if (ema9[prev] >= ema21[prev] && ema9[last] < ema21[last]) {
    return { direction: "SELL" };
  }
  return { direction: null };
}

// ─── Strategy 2: RSI at Support/Resistance ─────────────

function rsiSRStrategy(candles: Candle[]): { direction: "BUY" | "SELL" | null } {
  const closes = candles.map((c) => c.close);
  const rsiValues = rsi(closes, 14);
  const lastRsi = rsiValues[rsiValues.length - 1];
  const swingLows = findSwingLows(candles);
  const swingHighs = findSwingHighs(candles);
  const currentPrice = closes[closes.length - 1];
  const pipRange = currentPrice * 0.002;

  const nearSupport = swingLows.some((l) => Math.abs(currentPrice - l) < pipRange);
  const nearResistance = swingHighs.some((h) => Math.abs(currentPrice - h) < pipRange);

  if (lastRsi < 35 && nearSupport) return { direction: "BUY" };
  if (lastRsi > 65 && nearResistance) return { direction: "SELL" };
  return { direction: null };
}

// ─── Strategy 3: Smart Money Concepts (FVG + BOS) ──────

function smcStrategy(candles: Candle[]): { direction: "BUY" | "SELL" | null } {
  const len = candles.length;
  if (len < 10) return { direction: null };

  // Break of Structure
  const recentHighs = candles.slice(-10).map((c) => c.high);
  const recentLows = candles.slice(-10).map((c) => c.low);
  const prevHigh = Math.max(...recentHighs.slice(0, -1));
  const prevLow = Math.min(...recentLows.slice(0, -1));
  const lastCandle = candles[len - 1];

  // Fair Value Gap detection (3-candle pattern)
  const c1 = candles[len - 3];
  const c3 = candles[len - 1];
  const bullishFVG = c3.low > c1.high; // gap up
  const bearishFVG = c3.high < c1.low; // gap down

  if (lastCandle.close > prevHigh && bullishFVG) return { direction: "BUY" };
  if (lastCandle.close < prevLow && bearishFVG) return { direction: "SELL" };
  return { direction: null };
}

// ─── Strategy 4: Price Action (Engulfing + Pin Bar) ────

function priceActionStrategy(candles: Candle[]): { direction: "BUY" | "SELL" | null } {
  const len = candles.length;
  if (len < 3) return { direction: null };

  const prev = candles[len - 2];
  const curr = candles[len - 1];
  const body = Math.abs(curr.close - curr.open);
  const upperWick = curr.high - Math.max(curr.close, curr.open);
  const lowerWick = Math.min(curr.close, curr.open) - curr.low;

  // Bullish engulfing
  if (
    prev.close < prev.open &&
    curr.close > curr.open &&
    curr.close > prev.open &&
    curr.open < prev.close
  ) {
    return { direction: "BUY" };
  }

  // Bearish engulfing
  if (
    prev.close > prev.open &&
    curr.close < curr.open &&
    curr.close < prev.open &&
    curr.open > prev.close
  ) {
    return { direction: "SELL" };
  }

  // Bullish pin bar (long lower wick)
  if (lowerWick > body * 2 && upperWick < body * 0.5) {
    return { direction: "BUY" };
  }

  // Bearish pin bar (long upper wick)
  if (upperWick > body * 2 && lowerWick < body * 0.5) {
    return { direction: "SELL" };
  }

  return { direction: null };
}

// ─── Confluence Scanner ────────────────────────────────

export function analyzeSymbol(
  symbol: string,
  candles: Candle[],
  timeframe: string
): Signal | null {
  if (candles.length < 30) return null;

  const strategies: { name: string; result: { direction: "BUY" | "SELL" | null } }[] = [
    { name: "EMA 9/21", result: emaStrategy(candles) },
    { name: "RSI + S/R", result: rsiSRStrategy(candles) },
    { name: "SMC (FVG+BOS)", result: smcStrategy(candles) },
    { name: "Price Action", result: priceActionStrategy(candles) },
  ];

  // Count agreements
  const buyStrategies = strategies.filter((s) => s.result.direction === "BUY");
  const sellStrategies = strategies.filter((s) => s.result.direction === "SELL");

  let direction: "BUY" | "SELL";
  let agreeing: typeof strategies;

  if (buyStrategies.length >= sellStrategies.length && buyStrategies.length >= 1) {
    direction = "BUY";
    agreeing = buyStrategies;
  } else if (sellStrategies.length >= 1) {
    direction = "SELL";
    agreeing = sellStrategies;
  } else {
    return null;
  }

  const confluenceScore = agreeing.length;
  const currentPrice = candles[candles.length - 1].close;
  const swingLows = findSwingLows(candles);
  const swingHighs = findSwingHighs(candles);
  const atr = calculateATR(candles, 14);

  let sl: number, tp: number;

  if (direction === "BUY") {
    sl = swingLows.length > 0
      ? Math.min(...swingLows.slice(-3))
      : currentPrice - atr * 1.5;
    const risk = currentPrice - sl;
    tp = currentPrice + risk * 2;
  } else {
    sl = swingHighs.length > 0
      ? Math.max(...swingHighs.slice(-3))
      : currentPrice + atr * 1.5;
    const risk = sl - currentPrice;
    tp = currentPrice - risk * 2;
  }

  const risk = Math.abs(currentPrice - sl);
  const reward = Math.abs(tp - currentPrice);
  const riskReward = risk > 0 ? reward / risk : 0;

  return {
    id: `${symbol}-${timeframe}-${Date.now()}`,
    symbol,
    direction,
    strategies: agreeing.map((s) => s.name),
    confluenceScore,
    entryPrice: currentPrice,
    sl,
    tp,
    riskReward,
    timestamp: new Date(),
    timeframe,
  };
}

function calculateATR(candles: Candle[], period: number = 14): number {
  const trs: number[] = [];
  for (let i = 1; i < candles.length; i++) {
    const tr = Math.max(
      candles[i].high - candles[i].low,
      Math.abs(candles[i].high - candles[i - 1].close),
      Math.abs(candles[i].low - candles[i - 1].close)
    );
    trs.push(tr);
  }
  const recent = trs.slice(-period);
  return recent.reduce((a, b) => a + b, 0) / recent.length;
}

// ─── Position Sizing ───────────────────────────────────

export function calculateLotSize(
  accountBalance: number,
  riskPercent: number,
  entryPrice: number,
  slPrice: number,
  pipValue: number = 10 // standard lot pip value in USD for most pairs
): number {
  const riskAmount = accountBalance * (riskPercent / 100);
  const slPips = Math.abs(entryPrice - slPrice) * 10000; // for 4-digit pairs
  if (slPips === 0) return 0.01;
  const lotSize = riskAmount / (slPips * pipValue);
  return Math.max(0.01, Math.round(lotSize * 100) / 100);
}
