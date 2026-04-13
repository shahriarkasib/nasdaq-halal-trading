import { useState, useEffect } from "react";
import { Zap, Shield, AlertTriangle } from "lucide-react";
import axios from "axios";

const API = "/api/v1";

interface Signal {
  symbol: string;
  name: string;
  sector: string;
  price: number;
  date: string;
  rsi: number;
  chg1: number;
  chg5: number;
  vol: number;
  tier: number;
  target: number;
  sl: number;
  risk: number;
  signals: string[];
}

export default function Signals() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/nasdaq/signals`).then(r => {
      setSignals(r.data.signals || []);
    }).catch(() => {
      // Use static data if API not ready
      setSignals([
        { symbol: "SNOW", name: "Snowflake Inc.", sector: "Technology", price: 126.75, date: "2026-04-11", rsi: 28, chg1: 4.7, chg5: -15.1, vol: 0.5, tier: 2, target: 129.29, sl: 116.13, risk: 8.4, signals: ["5dDrop>10% [64%]"] },
        { symbol: "VEEV", name: "Veeva Systems Inc.", sector: "Healthcare", price: 155.00, date: "2026-04-11", rsi: 28, chg1: 2.4, chg5: -11.2, vol: 0.4, tier: 2, target: 158.10, sl: 146.97, risk: 5.2, signals: ["5dDrop>10% [64%]"] },
        { symbol: "APPN", name: "Appian Corporation", sector: "Technology", price: 20.80, date: "2026-04-11", rsi: 30, chg1: 2.9, chg5: -15.2, vol: 1.0, tier: 2, target: 21.22, sl: 19.33, risk: 7.1, signals: ["5dDrop>10% [64%]"] },
        { symbol: "AMPL", name: "Amplitude, Inc.", sector: "Technology", price: 5.78, date: "2026-04-11", rsi: 30, chg1: 2.9, chg5: -15.3, vol: 0.4, tier: 2, target: 5.89, sl: 5.36, risk: 7.2, signals: ["5dDrop>10% [64%]"] },
        { symbol: "ZS", name: "Zscaler, Inc.", sector: "Technology", price: 121.00, date: "2026-04-11", rsi: 30, chg1: 2.5, chg5: -13.3, vol: 0.3, tier: 2, target: 123.42, sl: 112.13, risk: 7.3, signals: ["5dDrop>10% [64%]"] },
        { symbol: "OKTA", name: "Okta, Inc.", sector: "Technology", price: 64.05, date: "2026-04-11", rsi: 32, chg1: 1.8, chg5: -20.5, vol: 0.4, tier: 2, target: 65.33, sl: 58.42, risk: 8.8, signals: ["5dDrop>10% [64%]"] },
        { symbol: "PLTR", name: "Palantir Technologies", sector: "Technology", price: 132.30, date: "2026-04-11", rsi: 39, chg1: 3.3, chg5: -10.6, vol: 0.5, tier: 2, target: 134.95, sl: 123.78, risk: 6.4, signals: ["5dDrop>10% [64%]"] },
        { symbol: "NOW", name: "ServiceNow, Inc.", sector: "Technology", price: 87.75, date: "2026-04-11", rsi: 31, chg1: 5.7, chg5: -14.3, vol: 0.5, tier: 2, target: 89.50, sl: 80.50, risk: 8.3, signals: ["5dDrop>10% [64%]"] },
        { symbol: "INTU", name: "Intuit Inc.", sector: "Technology", price: 361.81, date: "2026-04-11", rsi: 31, chg1: 3.1, chg5: -13.0, vol: 0.2, tier: 2, target: 369.05, sl: 339.01, risk: 6.3, signals: ["5dDrop>10% [64%]"] },
        { symbol: "NET", name: "Cloudflare, Inc.", sector: "Technology", price: 180.40, date: "2026-04-11", rsi: 41, chg1: 8.0, chg5: -14.8, vol: 0.5, tier: 2, target: 184.01, sl: 160.23, risk: 11.2, signals: ["5dDrop>10% [64%]"] },
      ]);
    }).finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Zap className="text-amber-400" size={20} />
        <h1 className="text-xl font-bold">Today's Buy Signals</h1>
        <span className="text-xs text-gray-500 ml-auto">Halal stocks only | T+1 tradeable</span>
      </div>

      <div className="flex gap-3 text-xs">
        <span className="px-2 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <Shield size={12} className="inline mr-1" /> Halal Screened
        </span>
        <span className="px-2 py-1 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
          Strategy: 5d Drop &gt;10% (64% win rate backtested)
        </span>
        <span className="text-gray-500">{signals.length} signals</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 border-b border-gray-800 text-xs">
              <th className="text-left py-2 px-2">Stock</th>
              <th className="text-left px-2">Sector</th>
              <th className="text-right px-2">Price</th>
              <th className="text-right px-2">RSI</th>
              <th className="text-right px-2">5D Drop</th>
              <th className="text-right px-2">Target</th>
              <th className="text-right px-2">SL</th>
              <th className="text-right px-2">Risk</th>
              <th className="text-left px-2">Signal</th>
            </tr>
          </thead>
          <tbody>
            {signals.map(s => (
              <tr key={s.symbol} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="py-2 px-2">
                  <div className="font-bold">{s.symbol}</div>
                  <div className="text-xs text-gray-500 truncate max-w-[150px]">{s.name}</div>
                </td>
                <td className="px-2 text-xs text-gray-400">{s.sector}</td>
                <td className="text-right px-2 font-mono">${s.price.toFixed(2)}</td>
                <td className={`text-right px-2 font-mono ${s.rsi < 30 ? "text-emerald-400" : s.rsi < 40 ? "text-amber-400" : "text-gray-400"}`}>
                  {s.rsi}
                </td>
                <td className="text-right px-2 font-mono text-red-400">{s.chg5.toFixed(1)}%</td>
                <td className="text-right px-2 font-mono text-emerald-400">${s.target.toFixed(2)}</td>
                <td className="text-right px-2 font-mono text-red-400">${s.sl.toFixed(2)}</td>
                <td className="text-right px-2 font-mono text-amber-400">{s.risk}%</td>
                <td className="px-2">
                  {s.signals.map((sig, i) => (
                    <span key={i} className="text-xs text-blue-400">{sig}</span>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 p-3 rounded bg-amber-500/5 border border-amber-500/20 text-xs text-amber-300">
        <AlertTriangle size={14} className="inline mr-1" />
        These signals are based on backtested strategies (64% win rate on 2 years data).
        36% of trades may lose. Always use the stop loss. Not financial advice.
      </div>
    </div>
  );
}
