import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  getAccountInfo,
  getPositions,
  closePosition,
  testConnection,
  type AccountInfo,
  type Position,
} from "@/services/mt5Api";
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Activity,
  X,
  RefreshCw,
  Wifi,
  WifiOff,
} from "lucide-react";
import { toast } from "sonner";

export default function Dashboard() {
  const [connected, setConnected] = useState(false);
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setLoading(true);
    const result = await testConnection();
    setConnected(result.connected);
    if (result.connected && result.account) {
      setAccount(result.account);
      try {
        const pos = await getPositions();
        setPositions(pos);
      } catch { /* empty */ }
    }
    setLoading(false);
  };

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleClose = async (ticket: number) => {
    try {
      await closePosition(ticket);
      toast.success(`Position #${ticket} closed`);
      refresh();
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const totalProfit = positions.reduce((sum, p) => sum + p.profit, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-sm text-muted-foreground font-mono">
            {connected ? account?.server || "Connected" : "Disconnected"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge
            variant={connected ? "default" : "destructive"}
            className="gap-1.5 font-mono text-xs"
          >
            {connected ? (
              <Wifi className="h-3 w-3" />
            ) : (
              <WifiOff className="h-3 w-3" />
            )}
            {connected ? "LIVE" : "OFFLINE"}
          </Badge>
          <Button variant="outline" size="icon" onClick={refresh} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {!connected && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="flex items-center gap-3 py-4">
            <WifiOff className="h-5 w-5 text-destructive" />
            <div>
              <p className="text-sm font-medium">MT5 not connected</p>
              <p className="text-xs text-muted-foreground">
                Make sure MT5 is running with the mt5-rest EA. Go to{" "}
                <a href="/setup" className="text-primary underline">MT5 Setup</a> for instructions.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Balance"
          value={account ? `$${account.balance.toLocaleString()}` : "—"}
          icon={DollarSign}
        />
        <StatCard
          title="Equity"
          value={account ? `$${account.equity.toLocaleString()}` : "—"}
          icon={Activity}
        />
        <StatCard
          title="Open P&L"
          value={`$${totalProfit.toFixed(2)}`}
          icon={totalProfit >= 0 ? TrendingUp : TrendingDown}
          valueClass={totalProfit >= 0 ? "text-profit" : "text-loss"}
        />
        <StatCard
          title="Positions"
          value={positions.length.toString()}
          icon={Activity}
        />
      </div>

      {/* Account details */}
      {account && (
        <div className="grid gap-4 sm:grid-cols-3">
          <MiniStat label="Leverage" value={`1:${account.leverage}`} />
          <MiniStat label="Free Margin" value={`$${account.free_margin.toLocaleString()}`} />
          <MiniStat label="Margin Level" value={`${account.margin_level?.toFixed(1) || 0}%`} />
        </div>
      )}

      {/* Open Positions */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Open Positions</CardTitle>
        </CardHeader>
        <CardContent>
          {positions.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No open positions
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs text-muted-foreground">
                    <th className="pb-2 pr-4">Symbol</th>
                    <th className="pb-2 pr-4">Type</th>
                    <th className="pb-2 pr-4">Volume</th>
                    <th className="pb-2 pr-4">Open</th>
                    <th className="pb-2 pr-4">Current</th>
                    <th className="pb-2 pr-4">SL</th>
                    <th className="pb-2 pr-4">TP</th>
                    <th className="pb-2 pr-4">P&L</th>
                    <th className="pb-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((pos) => (
                    <tr key={pos.ticket} className="border-b border-border/50">
                      <td className="py-3 pr-4 font-mono font-medium">{pos.symbol}</td>
                      <td className="py-3 pr-4">
                        <Badge
                          variant="outline"
                          className={
                            pos.type === 0
                              ? "border-profit/30 text-profit"
                              : "border-loss/30 text-loss"
                          }
                        >
                          {pos.type === 0 ? "BUY" : "SELL"}
                        </Badge>
                      </td>
                      <td className="py-3 pr-4 font-mono">{pos.volume}</td>
                      <td className="py-3 pr-4 font-mono">{pos.price_open}</td>
                      <td className="py-3 pr-4 font-mono">{pos.price_current}</td>
                      <td className="py-3 pr-4 font-mono text-muted-foreground">{pos.sl || "—"}</td>
                      <td className="py-3 pr-4 font-mono text-muted-foreground">{pos.tp || "—"}</td>
                      <td
                        className={`py-3 pr-4 font-mono font-medium ${
                          pos.profit >= 0 ? "text-profit" : "text-loss"
                        }`}
                      >
                        ${pos.profit.toFixed(2)}
                      </td>
                      <td className="py-3">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-muted-foreground hover:text-loss"
                          onClick={() => handleClose(pos.ticket)}
                        >
                          <X className="h-3.5 w-3.5" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon: Icon,
  valueClass,
}: {
  title: string;
  value: string;
  icon: any;
  valueClass?: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 py-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary">
          <Icon className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{title}</p>
          <p className={`text-xl font-bold font-mono ${valueClass || ""}`}>{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card px-4 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-mono text-sm font-medium">{value}</p>
    </div>
  );
}
