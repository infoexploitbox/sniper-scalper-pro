import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { testConnection, type AccountInfo } from "@/services/mt5Api";
import {
  CheckCircle,
  XCircle,
  Loader2,
  Wifi,
  Download,
  FolderOpen,
  Play,
  Settings,
  ExternalLink,
} from "lucide-react";

export default function Setup() {
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<{
    connected: boolean;
    account?: AccountInfo;
    error?: string;
  } | null>(null);

  const handleTest = async () => {
    setTesting(true);
    setResult(null);
    const res = await testConnection();
    setResult(res);
    setTesting(false);
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">MT5 Setup Guide</h1>
        <p className="text-sm text-muted-foreground">
          Connect your MetaTrader 5 to the trading bot in 4 steps
        </p>
      </div>

      {/* Steps */}
      <Step
        number={1}
        title="Download mt5-rest EA"
        icon={Download}
        description="Download the free mt5-rest Expert Advisor from GitHub."
      >
        <a
          href="https://github.com/nicholishen/mt5-rest"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Button variant="outline" className="gap-2">
            <ExternalLink className="h-4 w-4" /> View on GitHub
          </Button>
        </a>
        <p className="mt-2 text-xs text-muted-foreground">
          Clone or download the repo, then compile the <code className="rounded bg-secondary px-1">mt5-rest.mq5</code> EA in MetaEditor,
          or copy the pre-compiled <code className="rounded bg-secondary px-1">.ex5</code> file if available.
        </p>
      </Step>

      <Step
        number={2}
        title="Install into MT5"
        icon={FolderOpen}
        description="Copy the EA file into your MetaTrader 5 Experts folder."
      >
        <div className="rounded-lg bg-secondary p-4 font-mono text-xs leading-relaxed">
          <p className="text-muted-foreground">Copy to this folder:</p>
          <p className="mt-1 text-foreground">
            C:\Users\[YourName]\AppData\Roaming\MetaQuotes\Terminal\[ID]\MQL5\Experts\
          </p>
          <p className="mt-3 text-muted-foreground">Or in MT5:</p>
          <p className="mt-1 text-foreground">File → Open Data Folder → MQL5 → Experts</p>
        </div>
      </Step>

      <Step
        number={3}
        title="Enable & Configure"
        icon={Settings}
        description="Enable the EA in MetaTrader 5 settings."
      >
        <ol className="space-y-2 text-sm text-muted-foreground">
          <li className="flex gap-2">
            <span className="font-mono text-foreground">1.</span>
            In MT5, go to <strong className="text-foreground">Tools → Options → Expert Advisors</strong>
          </li>
          <li className="flex gap-2">
            <span className="font-mono text-foreground">2.</span>
            Check <strong className="text-foreground">"Allow Algo Trading"</strong>
          </li>
          <li className="flex gap-2">
            <span className="font-mono text-foreground">3.</span>
            Check <strong className="text-foreground">"Allow WebRequest for listed URL"</strong>
          </li>
          <li className="flex gap-2">
            <span className="font-mono text-foreground">4.</span>
            Restart MT5 or right-click Navigator → Refresh
          </li>
        </ol>
      </Step>

      <Step
        number={4}
        title="Attach to Chart & Run"
        icon={Play}
        description="Drag the EA onto any chart to start the REST server."
      >
        <ol className="space-y-2 text-sm text-muted-foreground">
          <li className="flex gap-2">
            <span className="font-mono text-foreground">1.</span>
            Open any chart (e.g. EURUSD)
          </li>
          <li className="flex gap-2">
            <span className="font-mono text-foreground">2.</span>
            In Navigator panel, find <strong className="text-foreground">mt5-rest</strong> under Expert Advisors
          </li>
          <li className="flex gap-2">
            <span className="font-mono text-foreground">3.</span>
            Drag it onto the chart. Set port to <strong className="text-foreground">6542</strong> (default)
          </li>
          <li className="flex gap-2">
            <span className="font-mono text-foreground">4.</span>
            Click OK. You should see a smiley face 😊 in the top-right corner of the chart
          </li>
        </ol>
      </Step>

      {/* Connection Test */}
      <Card className="border-primary/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Wifi className="h-5 w-5" /> Test Connection
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button onClick={handleTest} disabled={testing} className="gap-2">
            {testing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Wifi className="h-4 w-4" />
            )}
            {testing ? "Testing..." : "Test MT5 Connection"}
          </Button>

          {result && (
            <div
              className={`rounded-lg border p-4 ${
                result.connected
                  ? "border-profit/30 bg-profit/5"
                  : "border-loss/30 bg-loss/5"
              }`}
            >
              <div className="flex items-center gap-2">
                {result.connected ? (
                  <CheckCircle className="h-5 w-5 text-profit" />
                ) : (
                  <XCircle className="h-5 w-5 text-loss" />
                )}
                <p className="font-medium">
                  {result.connected ? "Connected!" : "Connection Failed"}
                </p>
              </div>
              {result.connected && result.account && (
                <div className="mt-3 grid grid-cols-2 gap-2 text-sm font-mono">
                  <div>
                    <span className="text-muted-foreground">Account: </span>
                    {result.account.login}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Server: </span>
                    {result.account.server}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Balance: </span>
                    ${result.account.balance}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Leverage: </span>
                    1:{result.account.leverage}
                  </div>
                </div>
              )}
              {result.error && (
                <p className="mt-2 text-xs text-muted-foreground">{result.error}</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Step({
  number,
  title,
  icon: Icon,
  description,
  children,
}: {
  number: number;
  title: string;
  icon: any;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-3 text-lg">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground">
            {number}
          </div>
          <Icon className="h-5 w-5 text-muted-foreground" />
          {title}
        </CardTitle>
        <p className="ml-11 text-sm text-muted-foreground">{description}</p>
      </CardHeader>
      <CardContent className="ml-11">{children}</CardContent>
    </Card>
  );
}
