import { useState, useEffect } from "react";
import { Target, CheckCircle, XCircle, Clock } from "lucide-react";
import axios from "axios";

interface Prediction {
  id: number;
  symbol: string;
  signal_date: string;
  signal_type: string;
  win_rate: number;
  entry_price: number;
  target_price: number;
  stop_loss: number;
  rsi_at_signal: number;
  current_price: number | null;
  max_gain_pct: number | null;
  max_loss_pct: number | null;
  days_tracked: number;
  hit_target: boolean;
  hit_stoploss: boolean;
  outcome: string;
  reasoning: string;
}

export default function Tracker() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [, setLoading] = useState(true);
  const [stats, setStats] = useState({ wins: 0, losses: 0, pending: 0, total: 0, winRate: 0 });

  useEffect(() => {
    axios.get("/api/v1/nasdaq/predictions").then(r => {
      setPredictions(r.data.predictions || []);
      setStats(r.data.stats || { wins: 0, losses: 0, pending: 0, total: 0, winRate: 0 });
    }).catch(() => {
      // Static data
      setPredictions([
        { id: 1, symbol: "SNOW", signal_date: "2026-04-11", signal_type: "5dDrop>10%", win_rate: 64.1, entry_price: 126.75, target_price: 129.29, stop_loss: 116.13, rsi_at_signal: 28, current_price: null, max_gain_pct: null, max_loss_pct: null, days_tracked: 0, hit_target: false, hit_stoploss: false, outcome: "PENDING", reasoning: "RSI 28, dropped 15% in 5d" },
        { id: 2, symbol: "VEEV", signal_date: "2026-04-11", signal_type: "5dDrop>10%", win_rate: 64.1, entry_price: 155.00, target_price: 158.10, stop_loss: 146.97, rsi_at_signal: 28, current_price: null, max_gain_pct: null, max_loss_pct: null, days_tracked: 0, hit_target: false, hit_stoploss: false, outcome: "PENDING", reasoning: "RSI 28, dropped 11% in 5d" },
        { id: 3, symbol: "APPN", signal_date: "2026-04-11", signal_type: "5dDrop>10%", win_rate: 64.1, entry_price: 20.80, target_price: 21.22, stop_loss: 19.33, rsi_at_signal: 30, current_price: null, max_gain_pct: null, max_loss_pct: null, days_tracked: 0, hit_target: false, hit_stoploss: false, outcome: "PENDING", reasoning: "RSI 30, dropped 15% in 5d" },
        { id: 4, symbol: "ZS", signal_date: "2026-04-11", signal_type: "5dDrop>10%", win_rate: 64.1, entry_price: 121.00, target_price: 123.42, stop_loss: 112.13, rsi_at_signal: 30, current_price: null, max_gain_pct: null, max_loss_pct: null, days_tracked: 0, hit_target: false, hit_stoploss: false, outcome: "PENDING", reasoning: "RSI 30, dropped 13% in 5d" },
        { id: 5, symbol: "OKTA", signal_date: "2026-04-11", signal_type: "5dDrop>10%", win_rate: 64.1, entry_price: 64.05, target_price: 65.33, stop_loss: 58.42, rsi_at_signal: 32, current_price: null, max_gain_pct: null, max_loss_pct: null, days_tracked: 0, hit_target: false, hit_stoploss: false, outcome: "PENDING", reasoning: "RSI 32, dropped 20% in 5d" },
      ]);
      setStats({ wins: 0, losses: 0, pending: 5, total: 5, winRate: 0 });
    }).finally(() => setLoading(false));
  }, []);

  const outcomeIcon = (outcome: string) => {
    if (outcome === "WIN") return <CheckCircle size={14} className="text-emerald-400" />;
    if (outcome === "LOSS") return <XCircle size={14} className="text-red-400" />;
    return <Clock size={14} className="text-amber-400" />;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Target className="text-blue-400" size={20} />
        <h1 className="text-xl font-bold">Prediction Tracker</h1>
      </div>

      {/* Stats bar */}
      <div className="flex gap-4 text-sm">
        <div className="px-3 py-2 rounded bg-gray-800 border border-gray-700">
          Total: <span className="font-bold">{stats.total}</span>
        </div>
        <div className="px-3 py-2 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
          Wins: <span className="font-bold">{stats.wins}</span>
        </div>
        <div className="px-3 py-2 rounded bg-red-500/10 border border-red-500/20 text-red-400">
          Losses: <span className="font-bold">{stats.losses}</span>
        </div>
        <div className="px-3 py-2 rounded bg-amber-500/10 border border-amber-500/20 text-amber-400">
          Pending: <span className="font-bold">{stats.pending}</span>
        </div>
        {stats.wins + stats.losses > 0 && (
          <div className="px-3 py-2 rounded bg-blue-500/10 border border-blue-500/20 text-blue-400">
            Win Rate: <span className="font-bold">{(stats.wins / (stats.wins + stats.losses) * 100).toFixed(0)}%</span>
            <span className="text-gray-500 ml-1">(expected: 64%)</span>
          </div>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 border-b border-gray-800 text-xs">
              <th className="text-left py-2 px-2">Status</th>
              <th className="text-left px-2">Stock</th>
              <th className="text-left px-2">Signal Date</th>
              <th className="text-right px-2">Entry</th>
              <th className="text-right px-2">Current</th>
              <th className="text-right px-2">Change</th>
              <th className="text-right px-2">Max Gain</th>
              <th className="text-right px-2">Max Loss</th>
              <th className="text-right px-2">Target</th>
              <th className="text-right px-2">SL</th>
              <th className="text-right px-2">Days</th>
              <th className="text-left px-2">Reason</th>
            </tr>
          </thead>
          <tbody>
            {predictions.map(p => {
              const chg = p.current_price ? ((p.current_price - p.entry_price) / p.entry_price * 100) : null;
              return (
                <tr key={p.id} className={`border-b border-gray-800/50 ${
                  p.outcome === "WIN" ? "bg-emerald-500/5" : p.outcome === "LOSS" ? "bg-red-500/5" : ""
                }`}>
                  <td className="py-2 px-2">{outcomeIcon(p.outcome)}</td>
                  <td className="px-2 font-bold">{p.symbol}</td>
                  <td className="px-2 text-gray-400 text-xs">{p.signal_date}</td>
                  <td className="text-right px-2 font-mono">${p.entry_price.toFixed(2)}</td>
                  <td className="text-right px-2 font-mono">
                    {p.current_price ? `$${p.current_price.toFixed(2)}` : "—"}
                  </td>
                  <td className={`text-right px-2 font-mono ${chg && chg > 0 ? "text-emerald-400" : chg && chg < 0 ? "text-red-400" : ""}`}>
                    {chg ? `${chg > 0 ? "+" : ""}${chg.toFixed(1)}%` : "—"}
                  </td>
                  <td className="text-right px-2 font-mono text-emerald-400">
                    {p.max_gain_pct != null ? `+${p.max_gain_pct.toFixed(1)}%` : "—"}
                  </td>
                  <td className="text-right px-2 font-mono text-red-400">
                    {p.max_loss_pct != null ? `${p.max_loss_pct.toFixed(1)}%` : "—"}
                  </td>
                  <td className="text-right px-2 font-mono text-emerald-400/60">${p.target_price.toFixed(2)}</td>
                  <td className="text-right px-2 font-mono text-red-400/60">${p.stop_loss.toFixed(2)}</td>
                  <td className="text-right px-2">{p.days_tracked}</td>
                  <td className="px-2 text-xs text-gray-500 truncate max-w-[200px]">{p.reasoning}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-gray-500 mt-4">
        Updated daily after market close. Each prediction tracked for 5 trading days.
        Win = hit target (+2%). Loss = hit stop loss. Backtested expected: 64% win rate.
      </p>
    </div>
  );
}
