import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { getCandles } from "@/services/mt5Api";
import { analyzeSymbol, type Signal } from "@/services/strategies";
import { Zap, Play, Loader2, TrendingUp, TrendingDown } from "lucide-react";
import { toast } from "sonner";

const DEFAULT_PAIRS = [
  "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
  "EURGBP", "EURJPY", "GBPJPY", "XAUUSD", "BTCUSD",
];

export default function Signals() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [scanning, setScanning] = useState(false);
  const [timeframe, setTimeframe] = useState("M5");

  const pairs = JSON.parse(localStorage.getItem("watched_pairs") || "null") || DEFAULT_PAIRS;

  const scan = async () => {
    setScanning(true);
    const newSignals: Signal[] = [];

    for (const symbol of pairs) {
      try {
        const candles = await getCandles(symbol, timeframe, 100);
        const signal = analyzeSymbol(symbol, candles, timeframe);
        if (signal) newSignals.push(signal);
      } catch {
        // skip unavailable symbols
      }
    }

    setSignals(newSignals.sort((a, b) => b.confluenceScore - a.confluenceScore));
    setScanning(false);

    if (newSignals.length === 0) {
      toast.info("No signals found on current scan");
    } else {
      toast.success(`Found ${newSignals.length} signal(s)`);
    }
  };

  const confluenceColor = (score: number) => {
    if (score >= 4) return "text-profit";
    if (score >= 3) return "text-warning";
    if (score >= 2) return "text-info";
    return "text-muted-foreground";
  };

  const confluenceLabel = (score: number) => {
    if (score >= 4) return "🎯 SNIPER";
    if (score >= 3) return "🔥 STRONG";
    if (score >= 2) return "⚡ MODERATE";
    return "📊 WEAK";
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Signal Engine</h1>
          <p className="text-sm text-muted-foreground">
            Multi-strategy confluence scanner
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            className="rounded-md border border-border bg-secondary px-3 py-2 text-sm"
          >
            <option value="M1">M1</option>
            <option value="M5">M5</option>
            <option value="M15">M15</option>
            <option value="M30">M30</option>
            <option value="H1">H1</option>
            <option value="H4">H4</option>
            <option value="D1">D1</option>
          </select>
          <Button onClick={scan} disabled={scanning} className="gap-2">
            {scanning ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            Scan Now
          </Button>
        </div>
      </div>

      {/* Strategy Legend */}
      <Card>
        <CardContent className="flex flex-wrap gap-3 py-4">
          <Badge variant="outline" className="text-xs">EMA 9/21</Badge>
          <Badge variant="outline" className="text-xs">RSI + S/R</Badge>
          <Badge variant="outline" className="text-xs">SMC (FVG+BOS)</Badge>
          <Badge variant="outline" className="text-xs">Price Action</Badge>
          <span className="ml-auto text-xs text-muted-foreground">
            Confluence = strategies agreeing on direction
          </span>
        </CardContent>
      </Card>

      {/* Signals */}
      {signals.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Zap className="mb-4 h-12 w-12 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              No signals yet. Click "Scan Now" to analyze the market.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {signals.map((signal) => (
            <Card key={signal.id} className="overflow-hidden">
              <div
                className={`h-1 ${
                  signal.direction === "BUY" ? "bg-profit" : "bg-loss"
                }`}
              />
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold font-mono">
                      {signal.symbol}
                    </span>
                    <Badge
                      variant="outline"
                      className={
                        signal.direction === "BUY"
                          ? "border-profit/30 text-profit"
                          : "border-loss/30 text-loss"
                      }
                    >
                      {signal.direction === "BUY" ? (
                        <TrendingUp className="mr-1 h-3 w-3" />
                      ) : (
                        <TrendingDown className="mr-1 h-3 w-3" />
                      )}
                      {signal.direction}
                    </Badge>
                  </div>
                  <span className={`text-sm font-bold ${confluenceColor(signal.confluenceScore)}`}>
                    {confluenceLabel(signal.confluenceScore)}
                  </span>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex flex-wrap gap-1.5">
                  {signal.strategies.map((s) => (
                    <Badge key={s} variant="secondary" className="text-xs">
                      {s}
                    </Badge>
                  ))}
                </div>
                <div className="grid grid-cols-4 gap-2 rounded-lg bg-secondary p-3 text-xs font-mono">
                  <div>
                    <p className="text-muted-foreground">Entry</p>
                    <p className="font-medium">{signal.entryPrice.toFixed(5)}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">SL</p>
                    <p className="text-loss">{signal.sl.toFixed(5)}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">TP</p>
                    <p className="text-profit">{signal.tp.toFixed(5)}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">R:R</p>
                    <p className="font-medium">1:{signal.riskReward.toFixed(1)}</p>
                  </div>
                </div>
                <p className="text-[10px] text-muted-foreground font-mono">
                  {signal.timeframe} • {signal.timestamp.toLocaleTimeString()}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
