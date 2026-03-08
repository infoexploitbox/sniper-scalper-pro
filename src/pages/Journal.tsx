import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getHistory, type HistoryDeal } from "@/services/mt5Api";
import { BookOpen, RefreshCw, TrendingUp, TrendingDown } from "lucide-react";
import { toast } from "sonner";

export default function Journal() {
  const [deals, setDeals] = useState<HistoryDeal[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const data = await getHistory(30);
      setDeals(data);
    } catch {
      toast.error("Could not fetch trade history. Is MT5 connected?");
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const totalProfit = deals.reduce((s, d) => s + d.profit, 0);
  const winners = deals.filter((d) => d.profit > 0).length;
  const losers = deals.filter((d) => d.profit < 0).length;
  const winRate = deals.length > 0 ? (winners / deals.length) * 100 : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Trade Journal</h1>
          <p className="text-sm text-muted-foreground">Last 30 days history</p>
        </div>
        <Button variant="outline" size="icon" onClick={fetchHistory} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-4">
        <MiniStat label="Total P&L" value={`$${totalProfit.toFixed(2)}`} color={totalProfit >= 0 ? "text-profit" : "text-loss"} />
        <MiniStat label="Win Rate" value={`${winRate.toFixed(1)}%`} color={winRate >= 50 ? "text-profit" : "text-loss"} />
        <MiniStat label="Winners" value={winners.toString()} color="text-profit" />
        <MiniStat label="Losers" value={losers.toString()} color="text-loss" />
      </div>

      {/* Trades */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <BookOpen className="h-5 w-5" /> Trade History
          </CardTitle>
        </CardHeader>
        <CardContent>
          {deals.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No trade history. Connect MT5 and start trading.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs text-muted-foreground">
                    <th className="pb-2 pr-4">Ticket</th>
                    <th className="pb-2 pr-4">Symbol</th>
                    <th className="pb-2 pr-4">Type</th>
                    <th className="pb-2 pr-4">Volume</th>
                    <th className="pb-2 pr-4">Price</th>
                    <th className="pb-2 pr-4">Profit</th>
                    <th className="pb-2 pr-4">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {deals.map((deal) => (
                    <tr key={deal.ticket} className="border-b border-border/50">
                      <td className="py-2.5 pr-4 font-mono text-xs text-muted-foreground">
                        #{deal.ticket}
                      </td>
                      <td className="py-2.5 pr-4 font-mono font-medium">{deal.symbol}</td>
                      <td className="py-2.5 pr-4">
                        <Badge variant="outline" className="text-xs">
                          {deal.type === 0 ? "BUY" : "SELL"}
                        </Badge>
                      </td>
                      <td className="py-2.5 pr-4 font-mono">{deal.volume}</td>
                      <td className="py-2.5 pr-4 font-mono">{deal.price}</td>
                      <td className={`py-2.5 pr-4 font-mono font-medium ${deal.profit >= 0 ? "text-profit" : "text-loss"}`}>
                        ${deal.profit.toFixed(2)}
                      </td>
                      <td className="py-2.5 pr-4 text-xs text-muted-foreground">
                        {new Date(deal.time).toLocaleDateString()}
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

function MiniStat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <Card>
      <CardContent className="py-4">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className={`text-xl font-bold font-mono ${color}`}>{value}</p>
      </CardContent>
    </Card>
  );
}
