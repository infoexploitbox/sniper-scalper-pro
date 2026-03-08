import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ShieldCheck, AlertTriangle, Ban, CheckCircle } from "lucide-react";

interface RiskSettings {
  maxDailyLossPercent: number;
  maxPositions: number;
  maxRiskPerTrade: number;
  autoStopEnabled: boolean;
  trailingStopEnabled: boolean;
}

const defaultSettings: RiskSettings = {
  maxDailyLossPercent: 3,
  maxPositions: 5,
  maxRiskPerTrade: 1,
  autoStopEnabled: true,
  trailingStopEnabled: false,
};

export default function RiskManager() {
  const [settings, setSettings] = useState<RiskSettings>(() => {
    const saved = localStorage.getItem("risk_settings");
    return saved ? JSON.parse(saved) : defaultSettings;
  });

  // Mock daily stats (will be live when connected)
  const dailyLoss = 0;
  const openPositionCount = 0;

  useEffect(() => {
    localStorage.setItem("risk_settings", JSON.stringify(settings));
  }, [settings]);

  const update = (key: keyof RiskSettings, value: any) =>
    setSettings((s) => ({ ...s, [key]: value }));

  const dailyLossPercent = settings.maxDailyLossPercent > 0
    ? (Math.abs(dailyLoss) / settings.maxDailyLossPercent) * 100
    : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Risk Manager</h1>
        <p className="text-sm text-muted-foreground">Automated drawdown & position controls</p>
      </div>

      {/* Status */}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatusCard
          label="Daily Loss"
          value={`$${dailyLoss.toFixed(2)}`}
          max={`${settings.maxDailyLossPercent}% limit`}
          ok={Math.abs(dailyLoss) < settings.maxDailyLossPercent}
        />
        <StatusCard
          label="Open Positions"
          value={openPositionCount.toString()}
          max={`${settings.maxPositions} max`}
          ok={openPositionCount < settings.maxPositions}
        />
        <StatusCard
          label="Risk/Trade"
          value={`${settings.maxRiskPerTrade}%`}
          max="of balance"
          ok={settings.maxRiskPerTrade <= 2}
        />
      </div>

      {/* Daily loss progress */}
      <Card>
        <CardContent className="py-5">
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Daily Drawdown Usage</span>
            <span className="font-mono">{dailyLossPercent.toFixed(0)}%</span>
          </div>
          <Progress value={dailyLossPercent} className="h-2" />
        </CardContent>
      </Card>

      {/* Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <ShieldCheck className="h-5 w-5" /> Risk Rules
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-6 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label className="text-xs">Max Daily Loss (%)</Label>
              <Input
                type="number"
                step={0.5}
                value={settings.maxDailyLossPercent}
                onChange={(e) => update("maxDailyLossPercent", parseFloat(e.target.value) || 0)}
                className="font-mono"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Max Open Positions</Label>
              <Input
                type="number"
                value={settings.maxPositions}
                onChange={(e) => update("maxPositions", parseInt(e.target.value) || 1)}
                className="font-mono"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Max Risk Per Trade (%)</Label>
              <Input
                type="number"
                step={0.1}
                value={settings.maxRiskPerTrade}
                onChange={(e) => update("maxRiskPerTrade", parseFloat(e.target.value) || 0)}
                className="font-mono"
              />
            </div>
          </div>

          <div className="space-y-4 border-t border-border pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Auto-Stop Trading</p>
                <p className="text-xs text-muted-foreground">
                  Stop all trading when daily loss limit is hit
                </p>
              </div>
              <Switch
                checked={settings.autoStopEnabled}
                onCheckedChange={(v) => update("autoStopEnabled", v)}
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Trailing Stop</p>
                <p className="text-xs text-muted-foreground">
                  Move SL to breakeven when trade is in profit
                </p>
              </div>
              <Switch
                checked={settings.trailingStopEnabled}
                onCheckedChange={(v) => update("trailingStopEnabled", v)}
              />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function StatusCard({
  label,
  value,
  max,
  ok,
}: {
  label: string;
  value: string;
  max: string;
  ok: boolean;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 py-4">
        {ok ? (
          <CheckCircle className="h-5 w-5 text-profit" />
        ) : (
          <AlertTriangle className="h-5 w-5 text-loss" />
        )}
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="font-mono text-lg font-bold">{value}</p>
          <p className="text-[10px] text-muted-foreground">{max}</p>
        </div>
      </CardContent>
    </Card>
  );
}
