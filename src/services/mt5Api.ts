// MT5 REST API Service — connects to mt5-rest EA running on localhost
// GitHub: https://github.com/nicholishen/mt5-rest (or mikha-dev/mt5-rest)

const DEFAULT_BASE_URL = "http://localhost:6542";

let baseUrl = localStorage.getItem("mt5_base_url") || DEFAULT_BASE_URL;

export function setBaseUrl(url: string) {
  baseUrl = url;
  localStorage.setItem("mt5_base_url", url);
}

export function getBaseUrl() {
  return baseUrl;
}

async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${baseUrl}${endpoint}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`MT5 API error ${res.status}: ${text}`);
  }
  return res.json();
}

// ─── Account ───────────────────────────────────────────
export interface AccountInfo {
  login: number;
  server: string;
  balance: number;
  equity: number;
  margin: number;
  free_margin: number;
  margin_level: number;
  profit: number;
  currency: string;
  leverage: number;
  name: string;
  company: string;
}

export async function getAccountInfo(): Promise<AccountInfo> {
  return apiFetch<AccountInfo>("/account");
}

// ─── Positions ─────────────────────────────────────────
export interface Position {
  ticket: number;
  symbol: string;
  type: number; // 0 = BUY, 1 = SELL
  volume: number;
  price_open: number;
  price_current: number;
  sl: number;
  tp: number;
  profit: number;
  swap: number;
  time: string;
  comment: string;
  magic: number;
}

export async function getPositions(): Promise<Position[]> {
  return apiFetch<Position[]>("/positions");
}

export async function closePosition(ticket: number): Promise<any> {
  return apiFetch(`/trade/close`, {
    method: "POST",
    body: JSON.stringify({ ticket }),
  });
}

export async function closeAllPositions(): Promise<any> {
  return apiFetch(`/trade/closeall`, { method: "POST" });
}

// ─── Orders ────────────────────────────────────────────
export interface TradeRequest {
  symbol: string;
  type: "BUY" | "SELL";
  volume: number;
  sl?: number;
  tp?: number;
  comment?: string;
  magic?: number;
}

export async function placeTrade(trade: TradeRequest): Promise<any> {
  return apiFetch("/trade/open", {
    method: "POST",
    body: JSON.stringify({
      symbol: trade.symbol,
      type: trade.type === "BUY" ? 0 : 1,
      volume: trade.volume,
      sl: trade.sl || 0,
      tp: trade.tp || 0,
      comment: trade.comment || "LovableBot",
      magic: trade.magic || 123456,
    }),
  });
}

export async function modifyPosition(
  ticket: number,
  sl: number,
  tp: number
): Promise<any> {
  return apiFetch("/trade/modify", {
    method: "POST",
    body: JSON.stringify({ ticket, sl, tp }),
  });
}

// ─── Market Data ───────────────────────────────────────
export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TickData {
  symbol: string;
  bid: number;
  ask: number;
  last: number;
  time: string;
}

export async function getCandles(
  symbol: string,
  timeframe: string = "M5",
  count: number = 100
): Promise<Candle[]> {
  return apiFetch<Candle[]>(
    `/candles?symbol=${symbol}&timeframe=${timeframe}&count=${count}`
  );
}

export async function getTick(symbol: string): Promise<TickData> {
  return apiFetch<TickData>(`/tick?symbol=${symbol}`);
}

export async function getSymbols(): Promise<string[]> {
  return apiFetch<string[]>("/symbols");
}

// ─── History ───────────────────────────────────────────
export interface HistoryDeal {
  ticket: number;
  symbol: string;
  type: number;
  volume: number;
  price: number;
  profit: number;
  swap: number;
  commission: number;
  time: string;
  comment: string;
  magic: number;
}

export async function getHistory(days: number = 30): Promise<HistoryDeal[]> {
  return apiFetch<HistoryDeal[]>(`/history?days=${days}`);
}

// ─── Connection Test ───────────────────────────────────
export async function testConnection(): Promise<{
  connected: boolean;
  account?: AccountInfo;
  error?: string;
}> {
  try {
    const account = await getAccountInfo();
    return { connected: true, account };
  } catch (err: any) {
    return { connected: false, error: err.message };
  }
}
