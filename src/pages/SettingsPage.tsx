import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Settings, Plus, X, Save } from "lucide-react";
import { setBaseUrl, getBaseUrl } from "@/services/mt5Api";
import { toast } from "sonner";

const DEFAULT_PAIRS = [
  "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
  "EURGBP", "EURJPY", "GBPJPY", "XAUUSD", "BTCUSD",
];

export default function SettingsPage() {
  const [apiUrl, setApiUrl] = useState(getBaseUrl());
  const [pairs, setPairs] = useState<string[]>(() => {
    return JSON.parse(localStorage.getItem("watched_pairs") || "null") || DEFAULT_PAIRS;
  });
  const [newPair, setNewPair] = useState("");
  const [autoTrade, setAutoTrade] = useState(() => localStorage.getItem("auto_trade") === "true");
  const [confluenceThreshold, setConfluenceThreshold] = useState(() =>
    parseInt(localStorage.getItem("confluence_threshold") || "3")
  );

  const save = () => {
    setBaseUrl(apiUrl);
    localStorage.setItem("watched_pairs", JSON.stringify(pairs));
    localStorage.setItem("auto_trade", String(autoTrade));
    localStorage.setItem("confluence_threshold", String(confluenceThreshold));
    toast.success("Settings saved");
  };

  const addPair = () => {
    const p = newPair.trim().toUpperCase();
    if (p && !pairs.includes(p)) {
      setPairs([...pairs, p]);
      setNewPair("");
    }
  };

  const removePair = (p: string) => setPairs(pairs.filter((x) => x !== p));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-sm text-muted-foreground">Configure bot behavior</p>
        </div>
        <Button onClick={save} className="gap-2">
          <Save className="h-4 w-4" /> Save
        </Button>
      </div>

      {/* Connection */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Connection</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1.5">
            <Label className="text-xs">MT5 REST API URL</Label>
            <Input
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              placeholder="http://localhost:6542"
              className="font-mono"
            />
          </div>
        </CardContent>
      </Card>

      {/* Auto Trading */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Auto Trading</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Enable Auto-Execution</p>
              <p className="text-xs text-muted-foreground">
                Automatically execute trades when signals meet confluence threshold
              </p>
            </div>
            <Switch checked={autoTrade} onCheckedChange={setAutoTrade} />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Min Confluence Score (1–4)</Label>
            <Input
              type="number"
              min={1}
              max={4}
              value={confluenceThreshold}
              onChange={(e) => setConfluenceThreshold(parseInt(e.target.value) || 3)}
              className="font-mono w-24"
            />
          </div>
        </CardContent>
      </Card>

      {/* Watched Pairs */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Watched Pairs</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {pairs.map((p) => (
              <Badge key={p} variant="secondary" className="gap-1 font-mono text-xs">
                {p}
                <button onClick={() => removePair(p)} className="ml-1 hover:text-loss">
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              value={newPair}
              onChange={(e) => setNewPair(e.target.value)}
              placeholder="NZDUSD"
              className="font-mono max-w-[200px]"
              onKeyDown={(e) => e.key === "Enter" && addPair()}
            />
            <Button variant="outline" size="icon" onClick={addPair}>
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
