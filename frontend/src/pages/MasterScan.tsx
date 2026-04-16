import { useState, useEffect } from 'react';
import axios from 'axios';
import clsx from 'clsx';
import { RefreshCw, TrendingUp, Eye, Target, AlertTriangle, Zap, Clock } from 'lucide-react';

interface Stock {
  sym: string;
  name: string;
  price: number;
  rsi: number;
  chg1: number;
  chg5: number;
  mcap: number;
  sector: string;
  green: boolean;
  note?: string;
  ibs?: number;
  gap?: number;
  z?: number;
  reason?: string;
}

interface PriorityStock extends Stock {
  strat_count: number;
  strategies: string[];
}

interface Strategy {
  key: string;
  name: string;
  wr: number;
  avg_ret: number;
}

interface ScanData {
  scanned_at: string | null;
  active: Record<string, Stock[]>;
  watchlist: Record<string, Stock[]>;
  priority_buys: PriorityStock[];
  watch_priority: PriorityStock[];
  strategy_list: Strategy[];
}

const API = import.meta.env.PROD
  ? 'http://34.126.141.16:8001'
  : '';

export default function MasterScan() {
  const [data, setData] = useState<ScanData | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'priority' | 'strategies' | 'watchlist'>('priority');
  const [expandedStrat, setExpandedStrat] = useState<string | null>(null);

  useEffect(() => { fetchData(); }, []);

  async function fetchData() {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/api/v1/nasdaq/scan`);
      setData(res.data);
    } catch {
      // Fallback — show empty state
      setData(null);
    }
    setLoading(false);
  }

  function wrColor(wr: number) {
    if (wr >= 80) return 'text-emerald-400';
    if (wr >= 70) return 'text-green-400';
    if (wr >= 65) return 'text-yellow-400';
    return 'text-gray-400';
  }

  function rsiColor(rsi: number) {
    if (rsi < 30) return 'text-red-400 font-bold';
    if (rsi < 40) return 'text-amber-400';
    return 'text-gray-300';
  }

  function chgColor(chg: number) {
    if (chg > 0) return 'text-emerald-400';
    if (chg < -5) return 'text-red-400';
    if (chg < 0) return 'text-red-300';
    return 'text-gray-400';
  }

  const totalActive = data ? Object.values(data.active).reduce((s, a) => s + a.length, 0) : 0;
  const totalWatch = data ? Object.values(data.watchlist).reduce((s, a) => s + a.length, 0) : 0;

  return (
    <div className="min-h-screen bg-[#0a0e17] text-gray-200 p-4 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Zap className="w-6 h-6 text-yellow-400" />
            Master Scanner
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            14 proven strategies | Backtested on 1,575 halal stocks
          </p>
        </div>
        <div className="flex items-center gap-3">
          {data?.scanned_at && (
            <span className="text-xs text-gray-500 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {new Date(data.scanned_at).toLocaleString()}
            </span>
          )}
          <button onClick={fetchData} className="p-2 rounded bg-gray-800 hover:bg-gray-700">
            <RefreshCw className={clsx("w-4 h-4", loading && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/50">
          <div className="text-xs text-gray-500">Active Signals</div>
          <div className="text-xl font-bold text-emerald-400">{totalActive}</div>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/50">
          <div className="text-xs text-gray-500">Priority Buys</div>
          <div className="text-xl font-bold text-yellow-400">{data?.priority_buys?.length || 0}</div>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/50">
          <div className="text-xs text-gray-500">Watchlist</div>
          <div className="text-xl font-bold text-blue-400">{totalWatch}</div>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/50">
          <div className="text-xs text-gray-500">Best Strategy</div>
          <div className="text-xl font-bold text-emerald-400">83%</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 bg-gray-800/30 rounded-lg p-1">
        {[
          { key: 'priority' as const, label: 'Priority Buys', icon: Target },
          { key: 'strategies' as const, label: 'All Strategies', icon: TrendingUp },
          { key: 'watchlist' as const, label: 'Watchlist', icon: Eye },
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={clsx("flex-1 py-2 px-3 rounded-md text-sm font-medium flex items-center justify-center gap-1.5 transition",
              tab === t.key ? "bg-gray-700 text-white" : "text-gray-400 hover:text-gray-200")}>
            <t.icon className="w-4 h-4" /> {t.label}
          </button>
        ))}
      </div>

      {loading && (
        <div className="text-center py-20 text-gray-500">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2" />
          Loading scan results...
        </div>
      )}

      {!loading && !data && (
        <div className="text-center py-20">
          <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-3" />
          <p className="text-gray-400">No scan data available. Run scan_master.py on the server first.</p>
        </div>
      )}

      {/* Priority Buys Tab */}
      {!loading && data && tab === 'priority' && (
        <div>
          <div className="bg-gray-800/30 rounded-lg border border-gray-700/50 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-700/50 flex items-center gap-2">
              <Target className="w-4 h-4 text-yellow-400" />
              <span className="font-medium">Multi-Strategy Buys</span>
              <span className="text-xs text-gray-500 ml-2">Stocks with 2+ active strategies</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-500 text-xs border-b border-gray-700/30">
                    <th className="text-left px-4 py-2">Symbol</th>
                    <th className="text-left px-2 py-2">Name</th>
                    <th className="text-right px-2 py-2">Price</th>
                    <th className="text-right px-2 py-2">RSI</th>
                    <th className="text-right px-2 py-2">5D</th>
                    <th className="text-center px-2 py-2">Signals</th>
                    <th className="text-left px-2 py-2">Strategies</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.priority_buys || []).map((s, i) => (
                    <tr key={s.sym} className={clsx("border-b border-gray-800/50 hover:bg-gray-800/30",
                      i === 0 && "bg-yellow-900/10")}>
                      <td className="px-4 py-2.5 font-mono font-bold text-white">{s.sym}</td>
                      <td className="px-2 py-2.5 text-gray-400 truncate max-w-[180px]">{s.name}</td>
                      <td className="px-2 py-2.5 text-right font-mono">${s.price?.toFixed(2)}</td>
                      <td className={clsx("px-2 py-2.5 text-right font-mono", rsiColor(s.rsi))}>{s.rsi?.toFixed(1)}</td>
                      <td className={clsx("px-2 py-2.5 text-right font-mono", chgColor(s.chg5))}>
                        {s.chg5 > 0 ? '+' : ''}{s.chg5?.toFixed(1)}%
                      </td>
                      <td className="px-2 py-2.5 text-center">
                        <span className={clsx("inline-block px-2 py-0.5 rounded-full text-xs font-bold",
                          s.strat_count >= 4 ? "bg-emerald-900/50 text-emerald-300" :
                          s.strat_count >= 3 ? "bg-yellow-900/50 text-yellow-300" :
                          "bg-gray-700 text-gray-300"
                        )}>
                          {s.strat_count}x
                        </span>
                      </td>
                      <td className="px-2 py-2.5 text-xs text-gray-400 truncate max-w-[300px]">
                        {(s.strategies || []).slice(0, 3).join(' + ')}
                        {(s.strategies || []).length > 3 && ` +${s.strategies.length - 3}`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Watch Priority */}
          {data.watch_priority && data.watch_priority.length > 0 && (
            <div className="mt-6 bg-gray-800/30 rounded-lg border border-blue-900/30 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-700/50 flex items-center gap-2">
                <Eye className="w-4 h-4 text-blue-400" />
                <span className="font-medium">Watch Priority</span>
                <span className="text-xs text-gray-500 ml-2">Close to triggering multiple strategies</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-gray-500 text-xs border-b border-gray-700/30">
                      <th className="text-left px-4 py-2">Symbol</th>
                      <th className="text-left px-2 py-2">Name</th>
                      <th className="text-right px-2 py-2">Price</th>
                      <th className="text-right px-2 py-2">RSI</th>
                      <th className="text-right px-2 py-2">5D</th>
                      <th className="text-center px-2 py-2">Near</th>
                      <th className="text-left px-2 py-2">Approaching</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.watch_priority.slice(0, 15).map(s => (
                      <tr key={s.sym} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                        <td className="px-4 py-2 font-mono font-bold text-blue-300">{s.sym}</td>
                        <td className="px-2 py-2 text-gray-400 truncate max-w-[180px]">{s.name}</td>
                        <td className="px-2 py-2 text-right font-mono">${s.price?.toFixed(2)}</td>
                        <td className={clsx("px-2 py-2 text-right font-mono", rsiColor(s.rsi))}>{s.rsi?.toFixed(1)}</td>
                        <td className={clsx("px-2 py-2 text-right font-mono", chgColor(s.chg5))}>
                          {s.chg5 > 0 ? '+' : ''}{s.chg5?.toFixed(1)}%
                        </td>
                        <td className="px-2 py-2 text-center text-blue-400 font-bold">{s.strat_count}x</td>
                        <td className="px-2 py-2 text-xs text-gray-500 truncate max-w-[280px]">
                          {(s.strategies || []).slice(0, 3).join(' + ')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* All Strategies Tab */}
      {!loading && data && tab === 'strategies' && (
        <div className="space-y-3">
          {(data.strategy_list || []).map(strat => {
            const stratKey = Object.keys(data.active).find(k => k.includes(strat.name.split(' ')[0]) || k.includes(`(${strat.wr}%)`));
            const stocks = stratKey ? data.active[stratKey] || [] : [];
            const isExpanded = expandedStrat === strat.key;

            return (
              <div key={strat.key} className="bg-gray-800/30 rounded-lg border border-gray-700/50 overflow-hidden">
                <button onClick={() => setExpandedStrat(isExpanded ? null : strat.key)}
                  className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-800/50 transition">
                  <div className="flex items-center gap-3">
                    <span className={clsx("text-lg font-bold", wrColor(strat.wr))}>{strat.wr}%</span>
                    <span className="font-medium text-white">{strat.name}</span>
                    <span className="text-xs text-gray-500">avg +{strat.avg_ret}%</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {stocks.length > 0 && (
                      <span className="bg-emerald-900/50 text-emerald-300 text-xs px-2 py-0.5 rounded-full font-bold">
                        {stocks.length} active
                      </span>
                    )}
                    <span className="text-gray-500 text-xs">{isExpanded ? '▲' : '▼'}</span>
                  </div>
                </button>
                {isExpanded && stocks.length > 0 && (
                  <div className="border-t border-gray-700/30 px-4 py-2">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-gray-500 text-xs">
                          <th className="text-left py-1">Symbol</th>
                          <th className="text-left py-1">Name</th>
                          <th className="text-right py-1">Price</th>
                          <th className="text-right py-1">RSI</th>
                          <th className="text-right py-1">1D</th>
                          <th className="text-right py-1">5D</th>
                          <th className="text-left py-1">Note</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stocks.slice(0, 15).map(s => (
                          <tr key={s.sym} className="border-t border-gray-800/30 hover:bg-gray-800/20">
                            <td className="py-1.5 font-mono font-bold text-white">{s.sym}</td>
                            <td className="py-1.5 text-gray-400 truncate max-w-[160px]">{s.name}</td>
                            <td className="py-1.5 text-right font-mono">${s.price?.toFixed(2)}</td>
                            <td className={clsx("py-1.5 text-right font-mono", rsiColor(s.rsi))}>{s.rsi?.toFixed(1)}</td>
                            <td className={clsx("py-1.5 text-right font-mono", chgColor(s.chg1))}>
                              {s.chg1 > 0 ? '+' : ''}{s.chg1?.toFixed(1)}%
                            </td>
                            <td className={clsx("py-1.5 text-right font-mono", chgColor(s.chg5))}>
                              {s.chg5 > 0 ? '+' : ''}{s.chg5?.toFixed(1)}%
                            </td>
                            <td className="py-1.5 text-xs text-gray-500">{s.note || ''}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {stocks.length > 15 && <p className="text-xs text-gray-500 py-1">+{stocks.length - 15} more</p>}
                  </div>
                )}
                {isExpanded && stocks.length === 0 && (
                  <div className="border-t border-gray-700/30 px-4 py-4 text-gray-500 text-sm">
                    No active signals for this strategy today.
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Watchlist Tab */}
      {!loading && data && tab === 'watchlist' && (
        <div className="space-y-3">
          {Object.entries(data.watchlist || {}).filter(([, stocks]) => stocks.length > 0).map(([strat, stocks]) => (
            <div key={strat} className="bg-gray-800/30 rounded-lg border border-blue-900/20 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-700/30 flex items-center justify-between">
                <span className="font-medium text-blue-300">{strat}</span>
                <span className="text-xs text-gray-500">{stocks.length} stocks watching</span>
              </div>
              <div className="px-4 py-2">
                <table className="w-full text-sm">
                  <tbody>
                    {stocks.slice(0, 10).map(s => (
                      <tr key={s.sym} className="border-t border-gray-800/30 hover:bg-gray-800/20">
                        <td className="py-1.5 font-mono font-bold text-blue-300 w-20">{s.sym}</td>
                        <td className="py-1.5 text-gray-400 truncate max-w-[160px]">{s.name}</td>
                        <td className="py-1.5 text-right font-mono w-24">${s.price?.toFixed(2)}</td>
                        <td className={clsx("py-1.5 text-right font-mono w-16", rsiColor(s.rsi))}>{s.rsi?.toFixed(1)}</td>
                        <td className="py-1.5 text-xs text-gray-500 pl-3">{s.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="mt-8 text-center text-xs text-gray-600 border-t border-gray-800 pt-4">
        <p>Exit Rule: Sell when close {'>'} 5-day SMA | Avg hold: 3-4 days | Halal-only stocks</p>
        <p className="mt-1">Win rates backtested on 1,575 NASDAQ halal stocks, 2 years of data</p>
      </div>
    </div>
  );
}
