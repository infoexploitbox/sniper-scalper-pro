import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { calculateLotSize } from "@/services/strategies";
import { Calculator as CalcIcon, DollarSign, AlertTriangle } from "lucide-react";

export default function Calculator() {
  const [balance, setBalance] = useState(1000);
  const [riskPercent, setRiskPercent] = useState(1);
  const [entry, setEntry] = useState(1.1);
  const [sl, setSl] = useState(1.098);
  const [pipValue, setPipValue] = useState(10);

  const lotSize = calculateLotSize(balance, riskPercent, entry, sl, pipValue);
  const riskAmount = balance * (riskPercent / 100);
  const slPips = Math.abs(entry - sl) * 10000;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Position Calculator</h1>
        <p className="text-sm text-muted-foreground">Auto lot sizing • $10 to $100M accounts</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <CalcIcon className="h-5 w-5" /> Input
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Field label="Account Balance ($)" value={balance} onChange={setBalance} />
            <Field label="Risk %" value={riskPercent} onChange={setRiskPercent} step={0.1} />
            <Field label="Entry Price" value={entry} onChange={setEntry} step={0.00001} />
            <Field label="Stop Loss Price" value={sl} onChange={setSl} step={0.00001} />
            <Field label="Pip Value ($/pip/lot)" value={pipValue} onChange={setPipValue} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <DollarSign className="h-5 w-5" /> Result
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="rounded-xl bg-secondary p-6 text-center">
              <p className="text-sm text-muted-foreground">Recommended Lot Size</p>
              <p className="text-5xl font-bold font-mono text-primary">{lotSize.toFixed(2)}</p>
              <p className="mt-1 text-xs text-muted-foreground">lots</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <ResultItem label="Risk Amount" value={`$${riskAmount.toFixed(2)}`} />
              <ResultItem label="SL Distance" value={`${slPips.toFixed(1)} pips`} />
              <ResultItem label="Risk %" value={`${riskPercent}%`} />
              <ResultItem label="Balance" value={`$${balance.toLocaleString()}`} />
            </div>
            {riskPercent > 2 && (
              <div className="flex items-center gap-2 rounded-lg border border-warning/30 bg-warning/5 px-4 py-3 text-xs text-warning">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                Risk above 2% is aggressive. Consider reducing.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  step = 1,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs">{label}</Label>
      <Input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        className="font-mono"
      />
    </div>
  );
}

function ResultItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border px-3 py-2">
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p className="font-mono text-sm font-medium">{value}</p>
    </div>
  );
}
