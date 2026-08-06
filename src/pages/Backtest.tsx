import { useState, useEffect, useMemo, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  runBacktest,
  getSymbols,
  getBacktestHistory,
  getBacktestLogs,
  type BacktestResult,
} from "@/services/mt5Api";
import {
  Play,
  Loader2,
  TrendingUp,
  TrendingDown,
  Target,
  DollarSign,
  Activity,
  History,
  BarChart2,
  PieChart as PieIcon,
  Filter,
  CheckCircle2,
  Zap,
  ShieldAlert,
  Terminal as TerminalIcon,
  Maximize2,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  Cell,
} from "recharts";

const DEFAULT_PAIRS = [
  "EURUSD",
  "GBPUSD",
  "USDJPY",
  "AUDUSD",
  "USDCAD",
  "XAUUSD",
  "BTCUSD",
];

export default function Backtest() {
  const [symbol, setSymbol] = useState(() => sessionStorage.getItem("bt_symbol") || "XAUUSD");
  const [availableSymbols, setAvailableSymbols] = useState<string[]>(DEFAULT_PAIRS);
  const [initialBalance, setInitialBalance] = useState(() => Number(sessionStorage.getItem("bt_balance")) || 1000);
  const [months, setMonths] = useState(() => Number(sessionStorage.getItem("bt_months")) || 12);
  const [timeframe, setTimeframe] = useState(() => sessionStorage.getItem("bt_timeframe") || "H1");
  const [riskPercent, setRiskPercent] = useState(() => Number(sessionStorage.getItem("bt_risk")) || 5);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(() => {
    const saved = sessionStorage.getItem("backtestResult");
    return saved ? JSON.parse(saved) : null;
  });

  const [history, setHistory] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Live Backtest Terminal Logs State
  const [liveLogs, setLiveLogs] = useState<string[]>([]);
  const [logStatusMessage, setLogStatusMessage] = useState("");
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Filters for trade log
  const [tradeFilter, setTradeFilter] = useState<"ALL" | "WIN" | "LOSS" | "BUY" | "SELL">("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    sessionStorage.setItem("bt_symbol", symbol);
    sessionStorage.setItem("bt_balance", String(initialBalance));
    sessionStorage.setItem("bt_months", String(months));
    sessionStorage.setItem("bt_timeframe", timeframe);
    sessionStorage.setItem("bt_risk", String(riskPercent));
    if (result) {
      sessionStorage.setItem("backtestResult", JSON.stringify(result));
    } else {
      sessionStorage.removeItem("backtestResult");
    }
  }, [symbol, initialBalance, months, timeframe, riskPercent, result]);

  useEffect(() => {
    getSymbols()
      .then((symbols) => {
        if (symbols && symbols.length > 0) {
          const merged = Array.from(new Set([...DEFAULT_PAIRS, ...symbols]));
          setAvailableSymbols(merged);
        }
      })
      .catch((err) => console.error("Failed to load symbols", err));
  }, []);

  // Poll live logs while running
  useEffect(() => {
    let intervalId: any;
    if (running) {
      intervalId = setInterval(async () => {
        const data = await getBacktestLogs();
        if (data.logs && data.logs.length > 0) {
          setLiveLogs(data.logs);
        }
        if (data.status?.message) {
          setLogStatusMessage(data.status.message);
        }
      }, 1000);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [running]);

  // Auto-scroll terminal log
  useEffect(() => {
    if (running && terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [liveLogs, running]);

  const fetchHistory = async () => {
    setLoadingHistory(true);
    try {
      const data = await getBacktestHistory(50);
      setHistory(data);
    } catch (err) {
      toast.error("Failed to fetch backtest history");
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleRun = async () => {
    setRunning(true);
    setResult(null);
    setLiveLogs([`[INITIALIZING] Starting AI Ensemble Walk-Forward Backtest for ${symbol}...`]);
    setLogStatusMessage(`Running backtest for ${symbol}...`);

    try {
      toast.info(`Starting 1-Year AI Backtest for ${symbol}...`);
      const res = await runBacktest({
        symbol,
        initial_balance: initialBalance,
        months,
        timeframe,
        risk_percent: riskPercent,
      });

      setResult(res);
      toast.success("Backtest completed successfully!");
      // Fetch final logs once done
      const finalLogData = await getBacktestLogs();
      if (finalLogData.logs) setLiveLogs(finalLogData.logs);
    } catch (err: any) {
      toast.error(err.message || "Backtest failed");
    } finally {
      setRunning(false);
    }
  };

  // Filtered trades list
  const filteredTrades = useMemo(() => {
    if (!result || !result.trades) return [];
    return result.trades.filter((t) => {
      if (tradeFilter === "WIN" && t.profit <= 0) return false;
      if (tradeFilter === "LOSS" && t.profit >= 0) return false;
      if (tradeFilter === "BUY" && t.type !== "BUY") return false;
      if (tradeFilter === "SELL" && t.type !== "SELL") return false;

      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchesReason = t.reason?.toLowerCase().includes(q);
        const matchesRegime = t.regime?.toLowerCase().includes(q);
        const matchesType = t.type?.toLowerCase().includes(q);
        if (!matchesReason && !matchesRegime && !matchesType) return false;
      }
      return true;
    });
  }, [result, tradeFilter, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Target className="h-6 w-6 text-primary" />
            AI Strategy Walk-Forward Backtester
          </h1>
          <p className="text-sm text-muted-foreground">
            Test multi-pair ensemble models with Triple-Barrier labeling & regime detection
          </p>
        </div>

        <Badge variant="outline" className="w-fit gap-1.5 py-1 px-3 border-primary/30 text-primary">
          <Zap className="h-3.5 w-3.5" />
          Ensemble V2 Engine Active
        </Badge>
      </div>

      <Tabs defaultValue="run" className="w-full">
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="run">Run Backtest</TabsTrigger>
          <TabsTrigger value="history" onClick={fetchHistory}>
            <History className="mr-2 h-4 w-4" />
            Backtest History
          </TabsTrigger>
        </TabsList>

        <TabsContent value="run" className="space-y-6 mt-6">
          {/* Configuration Card */}
          <Card className="border-border/60 shadow-sm">
            <CardHeader className="pb-4">
              <CardTitle className="text-lg flex items-center gap-2">
                <Filter className="h-5 w-5 text-primary" />
                Backtest Configuration
              </CardTitle>
              <CardDescription>
                Configure parameters for 1-year historical walk-forward evaluation
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-5">
                <div className="space-y-2">
                  <Label htmlFor="symbol">Symbol / Pair</Label>
                  <select
                    id="symbol"
                    value={symbol}
                    onChange={(e) => setSymbol(e.target.value)}
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    disabled={running}
                  >
                    {availableSymbols.map((sym) => (
                      <option key={sym} value={sym}>
                        {sym}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="balance">Initial Balance ($)</Label>
                  <Input
                    id="balance"
                    type="number"
                    value={initialBalance}
                    onChange={(e) => setInitialBalance(Number(e.target.value))}
                    min={100}
                    step={100}
                    disabled={running}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="months">Duration (Months)</Label>
                  <Input
                    id="months"
                    type="number"
                    value={months}
                    onChange={(e) => setMonths(Number(e.target.value))}
                    min={1}
                    max={12}
                    disabled={running}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="timeframe">Entry Timeframe</Label>
                  <select
                    id="timeframe"
                    value={timeframe}
                    onChange={(e) => setTimeframe(e.target.value)}
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    disabled={running}
                  >
                    <option value="M5">M5 (5 Minutes)</option>
                    <option value="M15">M15 (15 Minutes)</option>
                    <option value="M30">M30 (30 Minutes)</option>
                    <option value="H1">H1 (1 Hour)</option>
                    <option value="H4">H4 (4 Hours)</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="risk">Risk per Trade (%)</Label>
                  <Input
                    id="risk"
                    type="number"
                    value={riskPercent}
                    onChange={(e) => setRiskPercent(Number(e.target.value))}
                    min={1}
                    max={20}
                    step={0.5}
                    disabled={running}
                  />
                </div>
              </div>

              <Button
                onClick={handleRun}
                disabled={running}
                className="w-full gap-2 text-base font-semibold py-6 shadow-md transition-all hover:brightness-110"
              >
                {running ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Running 1-Year AI Backtest...
                  </>
                ) : (
                  <>
                    <Play className="h-5 w-5 fill-current" />
                    Run 1-Year Backtest ({symbol})
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Live Backtest Terminal & Console Component */}
          {(running || liveLogs.length > 0) && (
            <Card className="border-border/80 bg-zinc-950 text-zinc-100 shadow-xl overflow-hidden">
              <CardHeader className="py-3 px-4 bg-zinc-900/90 border-b border-zinc-800 flex flex-row items-center justify-between">
                <div className="flex items-center gap-2">
                  <TerminalIcon className="h-4 w-4 text-emerald-400" />
                  <span className="font-mono text-xs font-semibold text-zinc-200">
                    Live Execution Console — {symbol}
                  </span>
                  {running && (
                    <Badge variant="outline" className="text-[10px] py-0 px-2 border-emerald-500/50 text-emerald-400 animate-pulse">
                      PROCESSING
                    </Badge>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setLiveLogs([])}
                    title="Clear console"
                    className="p-1 text-zinc-400 hover:text-zinc-200 transition-colors"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </CardHeader>

              <CardContent className="p-4 font-mono text-xs space-y-2">
                {/* Pipeline Step Indicators */}
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 mb-3 pb-3 border-b border-zinc-800 text-[11px]">
                  <div className="flex items-center gap-2 text-zinc-300">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                    <span>1. Fetching MT5 Data</span>
                  </div>
                  <div className="flex items-center gap-2 text-zinc-300">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                    <span>2. Building 70+ Features</span>
                  </div>
                  <div className="flex items-center gap-2 text-zinc-300">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                    <span>3. Triple-Barrier Labeling</span>
                  </div>
                  <div className="flex items-center gap-2 text-zinc-300">
                    {running ? (
                      <Loader2 className="h-3.5 w-3.5 text-amber-400 animate-spin" />
                    ) : (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                    )}
                    <span>4. Ensemble Model Sim</span>
                  </div>
                </div>

                {/* Terminal Log Stream Area */}
                <div className="max-h-64 overflow-y-auto space-y-1.5 text-zinc-300 pr-2 leading-relaxed scrollbar-thin">
                  {liveLogs.map((logLine, idx) => {
                    const isError = logLine.includes("[FAIL]") || logLine.includes("Error");
                    const isSuccess = logLine.includes("[OK]") || logLine.includes("WIN");
                    const isHeader = logLine.includes("===") || logLine.includes("TRAINING") || logLine.includes("RESULTS");
                    const isTrade = logLine.includes("CLOSE") || logLine.includes("BUY") || logLine.includes("SELL");

                    return (
                      <div
                        key={idx}
                        className={`${
                          isHeader
                            ? "text-amber-400 font-bold"
                            : isError
                            ? "text-rose-400 font-semibold"
                            : isSuccess
                            ? "text-emerald-400"
                            : isTrade
                            ? "text-cyan-300"
                            : "text-zinc-400"
                        }`}
                      >
                        {logLine}
                      </div>
                    );
                  })}
                  <div ref={terminalEndRef} />
                </div>
              </CardContent>
            </Card>
          )}

          {/* Results Overview */}
          {result && (
            <>
              {/* Primary Stat Cards */}
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <MetricCard
                  title="Final Balance"
                  value={`$${result.final_balance?.toFixed(2)}`}
                  subtext={`Initial: $${result.initial_balance?.toFixed(2)}`}
                  icon={DollarSign}
                  trend={result.total_profit >= 0 ? "up" : "down"}
                />
                <MetricCard
                  title="Total Net Profit"
                  value={`$${result.total_profit?.toFixed(2)}`}
                  subtext={`${result.return_percent >= 0 ? "+" : ""}${result.return_percent?.toFixed(2)}% Return`}
                  icon={result.total_profit >= 0 ? TrendingUp : TrendingDown}
                  trend={result.total_profit >= 0 ? "up" : "down"}
                />
                <MetricCard
                  title="Win Rate"
                  value={`${result.win_rate?.toFixed(1)}%`}
                  subtext={`${result.winning_trades} Wins / ${result.losing_trades} Losses`}
                  icon={Activity}
                  trend={result.win_rate >= 55 ? "up" : "down"}
                />
                <MetricCard
                  title="Max Drawdown"
                  value={`${result.max_drawdown_percent?.toFixed(2)}%`}
                  subtext={`Profit Factor: ${result.profit_factor?.toFixed(2)}`}
                  icon={ShieldAlert}
                  trend={result.max_drawdown_percent <= 15 ? "up" : "down"}
                />
              </div>

              {/* Detailed Performance Metrics Grid */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <BarChart2 className="h-5 w-5 text-primary" />
                    Advanced Performance Statistics
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
                    <DetailStat
                      label="Profit Factor"
                      value={result.profit_factor?.toFixed(2) || "0.00"}
                      highlight={result.profit_factor >= 1.5}
                    />
                    <DetailStat
                      label="Average Win"
                      value={`+$${result.avg_win?.toFixed(2) || "0.00"}`}
                      className="text-emerald-500 font-medium"
                    />
                    <DetailStat
                      label="Average Loss"
                      value={`-$${result.avg_loss?.toFixed(2) || "0.00"}`}
                      className="text-rose-500 font-medium"
                    />
                    <DetailStat
                      label="Best Trade"
                      value={`+$${result.best_trade?.toFixed(2) || "0.00"}`}
                      className="text-emerald-500 font-medium"
                    />
                    <DetailStat
                      label="Worst Trade"
                      value={`-$${Math.abs(result.worst_trade || 0).toFixed(2)}`}
                      className="text-rose-500 font-medium"
                    />
                    <DetailStat
                      label="Total Trades"
                      value={result.total_trades?.toString() || "0"}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Equity Curve Chart */}
              {result.equity_curve && result.equity_curve.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <TrendingUp className="h-5 w-5 text-primary" />
                      Account Equity & Balance Growth Curve
                    </CardTitle>
                    <CardDescription>
                      Visualizing capital trajectory over the backtest period
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[320px] w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart
                          data={result.equity_curve}
                          margin={{ top: 10, right: 30, left: 10, bottom: 0 }}
                        >
                          <defs>
                            <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                              <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                          <XAxis
                            dataKey="time"
                            tick={{ fontSize: 11 }}
                            tickFormatter={(val) =>
                              typeof val === "string" ? val.split("T")[0] || val : String(val)
                            }
                          />
                          <YAxis
                            tick={{ fontSize: 11 }}
                            domain={["auto", "auto"]}
                            tickFormatter={(val) => `$${val}`}
                          />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: "hsl(var(--background))",
                              borderColor: "hsl(var(--border))",
                              borderRadius: "8px",
                              fontSize: "12px",
                            }}
                            formatter={(value: any) => [`$${Number(value).toFixed(2)}`, "Equity"]}
                          />
                          <Area
                            type="monotone"
                            dataKey="equity"
                            stroke="#10b981"
                            strokeWidth={2}
                            fillOpacity={1}
                            fill="url(#equityGrad)"
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Market Regime & Exit Reason Breakdown */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Regime Breakdown */}
                {result.regime_stats && result.regime_stats.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <PieIcon className="h-5 w-5 text-primary" />
                        Performance by Market Regime
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="h-[200px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={result.regime_stats}>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                            <XAxis dataKey="regime" tick={{ fontSize: 10 }} />
                            <YAxis tick={{ fontSize: 10 }} unit="%" />
                            <Tooltip
                              formatter={(val: any) => [`${Number(val).toFixed(1)}%`, "Win Rate"]}
                              contentStyle={{
                                backgroundColor: "hsl(var(--background))",
                                borderColor: "hsl(var(--border))",
                                borderRadius: "8px",
                              }}
                            />
                            <Bar dataKey="win_rate" radius={[4, 4, 0, 0]}>
                              {result.regime_stats.map((entry, index) => (
                                <Cell
                                  key={`cell-${index}`}
                                  fill={
                                    entry.win_rate >= 55
                                      ? "#10b981"
                                      : entry.win_rate >= 45
                                      ? "#f59e0b"
                                      : "#ef4444"
                                  }
                                />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-xs">
                        {result.regime_stats.map((reg) => (
                          <div
                            key={reg.regime}
                            className="flex items-center justify-between p-2 rounded-md border bg-secondary/30"
                          >
                            <span className="font-semibold">{reg.regime}</span>
                            <span className="font-mono text-muted-foreground">
                              {reg.wins}/{reg.total} ({reg.win_rate?.toFixed(0)}%)
                            </span>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Exit Reason Breakdown */}
                {result.reason_stats && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Target className="h-5 w-5 text-primary" />
                        Trade Exit Distribution
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-2 gap-3">
                        {Object.entries(result.reason_stats).map(([reason, count]) => {
                          const pct = ((count / result.total_trades) * 100).toFixed(1);
                          return (
                            <div
                              key={reason}
                              className="flex flex-col justify-between p-3 rounded-lg border bg-background"
                            >
                              <div className="flex items-center justify-between text-xs text-muted-foreground">
                                <span className="font-medium">{reason}</span>
                                <span>{pct}%</span>
                              </div>
                              <div className="mt-2 flex items-baseline justify-between">
                                <span className="text-xl font-bold font-mono">{count}</span>
                                <Badge
                                  variant="outline"
                                  className={
                                    reason.includes("TP")
                                      ? "text-emerald-500 border-emerald-500/30"
                                      : reason.includes("SL")
                                      ? "text-rose-500 border-rose-500/30"
                                      : "text-amber-500 border-amber-500/30"
                                  }
                                >
                                  {reason}
                                </Badge>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>

              {/* Trade Log Table */}
              <Card>
                <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                  <div>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <History className="h-5 w-5 text-primary" />
                      Detailed Trade Log ({filteredTrades.length} Trades)
                    </CardTitle>
                  </div>

                  <div className="flex items-center gap-2">
                    <Input
                      placeholder="Search regime or reason..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-48 text-xs h-8"
                    />

                    <div className="flex rounded-md border p-1 bg-secondary/50">
                      {(["ALL", "WIN", "LOSS", "BUY", "SELL"] as const).map((f) => (
                        <button
                          key={f}
                          onClick={() => setTradeFilter(f)}
                          className={`px-2.5 py-0.5 text-xs rounded-sm transition-all font-medium ${
                            tradeFilter === f
                              ? "bg-background text-foreground shadow-sm"
                              : "text-muted-foreground hover:text-foreground"
                          }`}
                        >
                          {f}
                        </button>
                      ))}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto max-h-[450px]">
                    <table className="w-full text-sm">
                      <thead className="sticky top-0 bg-background border-b z-10">
                        <tr className="text-left text-xs text-muted-foreground">
                          <th className="pb-2 pr-4">Type</th>
                          <th className="pb-2 pr-4">Entry</th>
                          <th className="pb-2 pr-4">Exit</th>
                          <th className="pb-2 pr-4">Lots</th>
                          <th className="pb-2 pr-4">P&L ($)</th>
                          <th className="pb-2 pr-4">Confidence</th>
                          <th className="pb-2 pr-4">Regime</th>
                          <th className="pb-2 pr-4">Reason</th>
                          <th className="pb-2 pr-4">Time</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredTrades.map((trade, idx) => (
                          <tr
                            key={idx}
                            className="border-b border-border/40 hover:bg-secondary/20 transition-colors text-xs font-mono"
                          >
                            <td className="py-2.5 pr-4">
                              <Badge
                                variant="outline"
                                className={
                                  trade.type === "BUY"
                                    ? "border-emerald-500/30 text-emerald-500"
                                    : "border-rose-500/30 text-rose-500"
                                }
                              >
                                {trade.type}
                              </Badge>
                            </td>
                            <td className="py-2.5 pr-4">{trade.entry?.toFixed(2)}</td>
                            <td className="py-2.5 pr-4">{trade.exit?.toFixed(2)}</td>
                            <td className="py-2.5 pr-4">{trade.volume}</td>
                            <td
                              className={`py-2.5 pr-4 font-bold ${
                                trade.profit >= 0 ? "text-emerald-500" : "text-rose-500"
                              }`}
                            >
                              ${trade.profit?.toFixed(2)}
                            </td>
                            <td className="py-2.5 pr-4">
                              {(trade.confidence * 100).toFixed(0)}%
                            </td>
                            <td className="py-2.5 pr-4 font-sans text-muted-foreground">
                              {trade.regime || "-"}
                            </td>
                            <td className="py-2.5 pr-4 font-sans">
                              <Badge variant="secondary" className="text-[10px]">
                                {trade.reason}
                              </Badge>
                            </td>
                            <td className="py-2.5 pr-4 text-muted-foreground font-sans text-[11px]">
                              {trade.open_time
                                ? String(trade.open_time).replace("T", " ").slice(0, 16)
                                : "-"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Past Backtest Runs</CardTitle>
            </CardHeader>
            <CardContent>
              {loadingHistory ? (
                <div className="flex justify-center p-8">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              ) : history.length === 0 ? (
                <div className="text-center p-8 text-muted-foreground">
                  No backtest history found. Run a backtest to see results here!
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-xs text-muted-foreground">
                        <th className="pb-2 pr-4">Date</th>
                        <th className="pb-2 pr-4">Symbol</th>
                        <th className="pb-2 pr-4">Timeframe</th>
                        <th className="pb-2 pr-4">Initial</th>
                        <th className="pb-2 pr-4">Final</th>
                        <th className="pb-2 pr-4">Profit</th>
                        <th className="pb-2 pr-4">Win Rate</th>
                        <th className="pb-2 pr-4">Trades</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((run, idx) => {
                        const d = new Date(run.timestamp);
                        return (
                          <tr key={idx} className="border-b border-border/50">
                            <td className="py-3 pr-4 text-xs">
                              {d.toLocaleDateString()} {d.toLocaleTimeString()}
                            </td>
                            <td className="py-3 pr-4 font-medium">{run.symbol}</td>
                            <td className="py-3 pr-4">{run.timeframe}</td>
                            <td className="py-3 pr-4 font-mono">
                              ${run.initial_balance?.toFixed(2)}
                            </td>
                            <td className="py-3 pr-4 font-mono">
                              ${run.final_balance?.toFixed(2)}
                            </td>
                            <td
                              className={`py-3 pr-4 font-mono font-medium ${
                                run.total_profit >= 0 ? "text-emerald-500" : "text-rose-500"
                              }`}
                            >
                              ${run.total_profit?.toFixed(2)}
                            </td>
                            <td className="py-3 pr-4 font-mono">
                              {run.win_rate?.toFixed(1)}%
                            </td>
                            <td className="py-3 pr-4 font-mono">{run.total_trades}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function MetricCard({
  title,
  value,
  subtext,
  icon: Icon,
  trend,
}: {
  title: string;
  value: string;
  subtext: string;
  icon: any;
  trend: "up" | "down";
}) {
  return (
    <Card className="border-border/60">
      <CardContent className="flex items-center justify-between p-5">
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground font-medium">{title}</p>
          <p
            className={`text-2xl font-bold font-mono ${
              trend === "up" ? "text-emerald-500" : "text-rose-500"
            }`}
          >
            {value}
          </p>
          <p className="text-[11px] text-muted-foreground">{subtext}</p>
        </div>
        <div
          className={`flex h-11 w-11 items-center justify-center rounded-xl ${
            trend === "up" ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"
          }`}
        >
          <Icon className="h-5 w-5" />
        </div>
      </CardContent>
    </Card>
  );
}

function DetailStat({
  label,
  value,
  className,
  highlight,
}: {
  label: string;
  value: string;
  className?: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border p-3 bg-background/50 ${
        highlight ? "border-emerald-500/40 bg-emerald-500/5" : ""
      }`}
    >
      <p className="text-[11px] text-muted-foreground font-medium">{label}</p>
      <p className={`font-mono text-base font-bold mt-0.5 ${className || ""}`}>{value}</p>
    </div>
  );
}
