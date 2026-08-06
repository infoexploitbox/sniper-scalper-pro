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
        <h1 className="text-2xl font-bold">Python AI Bot Setup</h1>
        <p className="text-sm text-muted-foreground">
          Connect your MetaTrader 5 to the AI trading bot in 3 easy steps
        </p>
      </div>

      {/* Steps */}
      <Step
        number={1}
        title="Install Python Dependencies"
        icon={Download}
        description="Make sure Python is installed and dependencies are ready."
      >
        <div className="rounded-lg bg-secondary p-4 font-mono text-xs leading-relaxed">
          <p className="text-muted-foreground">Run in your project folder:</p>
          <p className="mt-1 text-foreground">cd trading_bot</p>
          <p className="mt-1 text-foreground">pip install -r requirements.txt</p>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          ✅ Already done if you ran the setup! The bot includes MetaTrader5, TensorFlow, and all ML libraries.
        </p>
      </Step>

      <Step
        number={2}
        title="Configure MT5 Credentials"
        icon={Settings}
        description="Edit the .env file with your MT5 account details."
      >
        <div className="rounded-lg bg-secondary p-4 font-mono text-xs leading-relaxed">
          <p className="text-muted-foreground">File: trading_bot/.env</p>
          <p className="mt-2 text-foreground">MT5_LOGIN=your_account_number</p>
          <p className="text-foreground">MT5_PASSWORD=your_password</p>
          <p className="text-foreground">MT5_SERVER=your_broker_server</p>
          <p className="mt-2 text-foreground">SYMBOLS=EURUSD,XAUUSD</p>
          <p className="text-foreground">MAX_POSITIONS=5</p>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          ✅ Already configured! The bot will trade EURUSD and Gold (XAUUSD).
        </p>
      </Step>

      <Step
        number={3}
        title="Start the Bot"
        icon={Play}
        description="Double-click START_BOTH.bat to launch the bot and API server."
      >
        <div className="space-y-3">
          <div className="rounded-lg border bg-background p-3">
            <p className="text-sm font-medium">START_BOTH.bat</p>
            <p className="text-xs text-muted-foreground">Runs both API server and auto-trading bot</p>
          </div>
          <div className="rounded-lg border bg-background p-3">
            <p className="text-sm font-medium">START_TRADING_BOT.bat</p>
            <p className="text-xs text-muted-foreground">Only auto-trading (no API)</p>
          </div>
          <div className="rounded-lg border bg-background p-3">
            <p className="text-sm font-medium">START_API_SERVER.bat</p>
            <p className="text-xs text-muted-foreground">Only API server (manual control)</p>
          </div>
        </div>
        <p className="mt-3 text-xs text-muted-foreground">
          The bot will connect to MT5, train AI models for each symbol, and start trading automatically!
        </p>
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
              className={`rounded-lg border p-4 ${result.connected
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
