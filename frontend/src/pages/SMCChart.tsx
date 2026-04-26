import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  createSeriesMarkers,
  type IChartApi,
  type ISeriesApi,
  type IPriceLine,
  type ISeriesMarkersPluginApi,
  type Time,
} from "lightweight-charts";
import { FVGPrimitive } from "./fvgPrimitive";
import { GannPrimitive, FibCirclesPrimitive, type GannFanData, type FibCirclesData } from "./gannFibPrimitives";
import { OrderBlockPrimitive } from "./orderBlockPrimitive";
import clsx from "clsx";
import axios from "axios";
import {
  ArrowLeft,
  RefreshCw,
  Search,
  Eye,
  EyeOff,
  AlertTriangle,
} from "lucide-react";

const API = import.meta.env.PROD ? "http://34.126.141.16:8001" : "";

type Period = "1mo" | "3mo" | "6mo" | "1y" | "2y";

interface SMCFvg {
  type: "bullish" | "bearish";
  top: number; bottom: number;
  start_time: string; end_time: string;
  mitigated?: boolean;
}
interface SMCOrderBlock {
  type: "bullish" | "bearish";
  top: number; bottom: number;
  start_time: string; end_time: string;
  status: "fresh" | "tested" | "mitigated";
}
interface StructureEvent {
  type: string; price: number; from_price: number;
  time: string; from_time: string;
}
interface KeyLevel {
  label: string; price: number; color: string;
  purpose: "resistance" | "support" | "breakout_long" | "breakout_short";
}
interface AnalysisData {
  bias: string; confidence: string;
  action: string; action_color: string;
  summary: string; reasons: string[];
  entry: number | null; entry_label: string | null;
  stop_loss: number | null;
  target1: number | null; target2: number | null;
  risk_reward: number | null;
  triggers: { icon: string; text: string }[];
}
interface AccumulationData {
  phase: "ACCUMULATION" | "DISTRIBUTION" | "CONSOLIDATION";
  bias: "bullish" | "bearish" | "neutral";
  confidence: "LOW" | "MEDIUM" | "HIGH";
  range_high: number;
  range_low: number;
  range_pct: number;
  target_up: number | null;
  target_down: number | null;
  volume_ratio: number;
  support_tests: number;
  resistance_tests: number;
  bars_inside: number;
  lookback: number;
  pre_trend_pct: number;
  summary: string;
}

interface ChartData {
  symbol: string;
  current_price: number;
  candles: { time: string; open: number; high: number; low: number; close: number }[];
  volumes: { time: string; value: number; color: string }[];
  fvgs: SMCFvg[];
  structure: StructureEvent[];
  order_blocks: SMCOrderBlock[];
  key_levels: KeyLevel[];
  fibonacci: { levels: { label: string; price: number }[] } | null;
  pivots: Record<string, number> | null;
  moving_averages: Record<string, { time: string; value: number }[]>;
  gann_fan: GannFanData | null;
  fib_circles: FibCirclesData | null;
  analysis: AnalysisData;
  accumulation?: AccumulationData | null;
}

interface Toggles {
  fvg: boolean; ob: boolean; bos: boolean; levels: boolean;
  fib: boolean; fibCircles: boolean; gann: boolean;
  pivots: boolean; ma20: boolean; ma50: boolean; ma200: boolean;
}

const DEFAULT_TOGGLES: Toggles = {
  fvg: true, ob: true, bos: true, levels: true,
  fib: false, fibCircles: false, gann: false,
  pivots: false, ma20: false, ma50: false, ma200: false,
};

const STORAGE_KEY = "nasdaq-smc-toggles-v1";
const CHART_HEIGHT = 600;

function loadToggles(): Toggles {
  if (typeof window === "undefined") return DEFAULT_TOGGLES;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? { ...DEFAULT_TOGGLES, ...JSON.parse(raw) } : DEFAULT_TOGGLES;
  } catch { return DEFAULT_TOGGLES; }
}

function saveToggles(t: Toggles) {
  try { window.localStorage.setItem(STORAGE_KEY, JSON.stringify(t)); } catch {}
}

export default function SMCChart() {
  const { symbol = "AAPL" } = useParams();
  const nav = useNavigate();

  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const fvgPrimitiveRef = useRef<FVGPrimitive | null>(null);
  const obPrimitiveRef = useRef<OrderBlockPrimitive | null>(null);
  const gannPrimitiveRef = useRef<GannPrimitive | null>(null);
  const fibCirclesPrimitiveRef = useRef<FibCirclesPrimitive | null>(null);
  const bosSeriesRef = useRef<ISeriesApi<"Line">[]>([]);
  const bosMarkersRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  const levelsLinesRef = useRef<IPriceLine[]>([]);
  const fibLinesRef = useRef<IPriceLine[]>([]);
  const pivotLinesRef = useRef<IPriceLine[]>([]);
  const maSeriesRef = useRef<Record<string, ISeriesApi<"Line">>>({});

  const [data, setData] = useState<ChartData | null>(null);
  const [period, setPeriod] = useState<Period>("6mo");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState(symbol);
  const [toggles, setTogglesState] = useState<Toggles>(loadToggles);
  const [chartReady, setChartReady] = useState(false);

  const setToggles = useCallback((updater: (t: Toggles) => Toggles) => {
    setTogglesState((prev) => {
      const next = updater(prev);
      saveToggles(next);
      return next;
    });
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get<ChartData>(
        `${API}/api/v1/nasdaq/smc-chart/${symbol.toUpperCase()}?period=${period}`,
      );
      setData(res.data);
    } catch (err: any) {
      setError(err?.message || "Failed to load chart");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [symbol, period]);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    if (!containerRef.current) return;

    const width = containerRef.current.clientWidth ||
      containerRef.current.parentElement?.clientWidth ||
      Math.max(window.innerWidth - 64, 320);

    const chart = createChart(containerRef.current, {
      width, height: CHART_HEIGHT,
      layout: { background: { color: "#0a0e17" }, textColor: "#d1d5db" },
      grid: { vertLines: { color: "#1f2937" }, horzLines: { color: "#1f2937" } },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: "#374151" },
      timeScale: { borderColor: "#374151", timeVisible: true },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#26a69a", downColor: "#ef5350",
      borderVisible: false, wickUpColor: "#26a69a", wickDownColor: "#ef5350",
    });
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" }, priceScaleId: "volume",
    });
    volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;

    fvgPrimitiveRef.current = null;
    obPrimitiveRef.current = null;
    gannPrimitiveRef.current = null;
    fibCirclesPrimitiveRef.current = null;
    bosSeriesRef.current = [];
    bosMarkersRef.current = null;
    levelsLinesRef.current = [];
    fibLinesRef.current = [];
    pivotLinesRef.current = [];
    maSeriesRef.current = {};

    setChartReady(true);

    const ro = new ResizeObserver(() => {
      if (containerRef.current && chartRef.current) {
        const newWidth = containerRef.current.clientWidth || width;
        chartRef.current.applyOptions({ width: newWidth });
      }
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      setChartReady(false);
      if (chartRef.current) {
        try { chartRef.current.remove(); } catch {}
        chartRef.current = null;
      }
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
    };
  }, [symbol]);

  // Update series data
  useEffect(() => {
    if (!chartReady || !data) return;
    const c = candleSeriesRef.current; const v = volumeSeriesRef.current; const ch = chartRef.current;
    if (!c || !v || !ch) return;
    c.setData(data.candles.map((x) => ({ ...x, time: x.time as Time })));
    v.setData(data.volumes.map((x) => ({ ...x, time: x.time as Time })));
    ch.timeScale().fitContent();
  }, [chartReady, data]);

  // FVG
  useEffect(() => {
    if (!chartReady || !data) return;
    const cs = candleSeriesRef.current; if (!cs) return;
    if (fvgPrimitiveRef.current) {
      try { cs.detachPrimitive(fvgPrimitiveRef.current); } catch {}
      fvgPrimitiveRef.current = null;
    }
    if (!toggles.fvg || !data.fvgs?.length) return;
    try {
      const p = new FVGPrimitive(data.fvgs.slice(-30));
      cs.attachPrimitive(p);
      fvgPrimitiveRef.current = p;
    } catch {}
  }, [chartReady, data, toggles.fvg]);

  // OB
  useEffect(() => {
    if (!chartReady || !data) return;
    const cs = candleSeriesRef.current; if (!cs) return;
    if (obPrimitiveRef.current) {
      try { cs.detachPrimitive(obPrimitiveRef.current); } catch {}
      obPrimitiveRef.current = null;
    }
    if (!toggles.ob || !data.order_blocks?.length) return;
    try {
      const p = new OrderBlockPrimitive(data.order_blocks);
      cs.attachPrimitive(p);
      obPrimitiveRef.current = p;
    } catch {}
  }, [chartReady, data, toggles.ob]);

  // Gann
  useEffect(() => {
    if (!chartReady || !data) return;
    const cs = candleSeriesRef.current; if (!cs) return;
    if (gannPrimitiveRef.current) {
      try { cs.detachPrimitive(gannPrimitiveRef.current); } catch {}
      gannPrimitiveRef.current = null;
    }
    if (!toggles.gann || !data.gann_fan) return;
    try {
      const p = new GannPrimitive(data.gann_fan);
      cs.attachPrimitive(p);
      gannPrimitiveRef.current = p;
    } catch {}
  }, [chartReady, data, toggles.gann]);

  // Fib Circles
  useEffect(() => {
    if (!chartReady || !data) return;
    const cs = candleSeriesRef.current; if (!cs) return;
    if (fibCirclesPrimitiveRef.current) {
      try { cs.detachPrimitive(fibCirclesPrimitiveRef.current); } catch {}
      fibCirclesPrimitiveRef.current = null;
    }
    if (!toggles.fibCircles || !data.fib_circles) return;
    try {
      const p = new FibCirclesPrimitive(data.fib_circles);
      cs.attachPrimitive(p);
      fibCirclesPrimitiveRef.current = p;
    } catch {}
  }, [chartReady, data, toggles.fibCircles]);

  // BOS / ChoCh
  useEffect(() => {
    if (!chartReady || !data) return;
    const ch = chartRef.current; const cs = candleSeriesRef.current;
    if (!ch || !cs) return;
    bosSeriesRef.current.forEach((s) => { try { ch.removeSeries(s); } catch {} });
    bosSeriesRef.current = [];
    if (bosMarkersRef.current) { try { bosMarkersRef.current.detach(); } catch {} bosMarkersRef.current = null; }
    if (!toggles.bos) return;
    const events = data.structure.slice(-8);
    events.forEach((ev) => {
      try {
        const isBull = ev.type.startsWith("bullish");
        const line = ch.addSeries(LineSeries, {
          color: isBull ? "rgba(38,166,154,0.7)" : "rgba(239,83,80,0.7)",
          lineWidth: 1, lineStyle: 2,
          priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
        });
        line.setData([
          { time: ev.from_time as Time, value: ev.from_price },
          { time: ev.time as Time, value: ev.from_price },
        ]);
        bosSeriesRef.current.push(line);
      } catch {}
    });
    try {
      const markers = events.map((ev) => {
        const isBull = ev.type.startsWith("bullish");
        const isBOS = ev.type.includes("BOS");
        return {
          time: ev.time as Time,
          position: isBull ? ("belowBar" as const) : ("aboveBar" as const),
          color: isBull ? "#26a69a" : "#ef5350",
          shape: isBull ? ("arrowUp" as const) : ("arrowDown" as const),
          text: isBOS ? "BOS" : "ChoCh",
        };
      });
      bosMarkersRef.current = createSeriesMarkers(cs, markers);
    } catch {}
  }, [chartReady, data, toggles.bos]);

  // Key Levels
  useEffect(() => {
    if (!chartReady || !data) return;
    const cs = candleSeriesRef.current; if (!cs) return;
    levelsLinesRef.current.forEach((ln) => { try { cs.removePriceLine(ln); } catch {} });
    levelsLinesRef.current = [];
    if (!toggles.levels || !data.key_levels) return;
    data.key_levels.forEach((lvl) => {
      try {
        const isBreakout = lvl.purpose === "breakout_long" || lvl.purpose === "breakout_short";
        levelsLinesRef.current.push(cs.createPriceLine({
          price: lvl.price, color: lvl.color,
          lineWidth: isBreakout ? 2 : 1, lineStyle: isBreakout ? 0 : 2,
          axisLabelVisible: true, title: lvl.label,
        }));
      } catch {}
    });
  }, [chartReady, data, toggles.levels]);

  // Fib levels
  useEffect(() => {
    if (!chartReady || !data) return;
    const cs = candleSeriesRef.current; if (!cs) return;
    fibLinesRef.current.forEach((ln) => { try { cs.removePriceLine(ln); } catch {} });
    fibLinesRef.current = [];
    if (!toggles.fib || !data.fibonacci) return;
    const colors: Record<string, string> = {
      "0%": "#9ca3af", "23.6%": "#fbbf24", "38.2%": "#fb923c", "50%": "#a855f7",
      "61.8%": "#f472b6", "78.6%": "#60a5fa", "100%": "#9ca3af",
    };
    data.fibonacci.levels.forEach((lvl) => {
      try {
        fibLinesRef.current.push(cs.createPriceLine({
          price: lvl.price, color: colors[lvl.label] ?? "#a78bfa",
          lineWidth: 1, lineStyle: 1, axisLabelVisible: true, title: `Fib ${lvl.label}`,
        }));
      } catch {}
    });
  }, [chartReady, data, toggles.fib]);

  // Pivots
  useEffect(() => {
    if (!chartReady || !data) return;
    const cs = candleSeriesRef.current; if (!cs) return;
    pivotLinesRef.current.forEach((ln) => { try { cs.removePriceLine(ln); } catch {} });
    pivotLinesRef.current = [];
    if (!toggles.pivots || !data.pivots) return;
    const p = data.pivots;
    const lines: [string, number, string][] = [
      ["R3", p.r3, "#ef4444"], ["R2", p.r2, "#f87171"], ["R1", p.r1, "#fca5a5"],
      ["P", p.pivot, "#facc15"],
      ["S1", p.s1, "#86efac"], ["S2", p.s2, "#4ade80"], ["S3", p.s3, "#22c55e"],
    ];
    lines.forEach(([label, price, color]) => {
      try {
        pivotLinesRef.current.push(cs.createPriceLine({
          price, color, lineWidth: 1, lineStyle: 3,
          axisLabelVisible: true, title: label,
        }));
      } catch {}
    });
  }, [chartReady, data, toggles.pivots]);

  // MAs
  useEffect(() => {
    if (!chartReady || !data?.moving_averages) return;
    const ch = chartRef.current; if (!ch) return;
    const configs: [string, keyof Toggles, string][] = [
      ["ma_20", "ma20", "#facc15"], ["ma_50", "ma50", "#60a5fa"], ["ma_200", "ma200", "#f472b6"],
    ];
    configs.forEach(([key, tk, color]) => {
      const enabled = toggles[tk]; const existing = maSeriesRef.current[key];
      try {
        if (enabled && !existing) {
          const s = ch.addSeries(LineSeries, { color, lineWidth: 1,
            priceLineVisible: false, lastValueVisible: false });
          s.setData((data.moving_averages?.[key] || []).map((pt) =>
            ({ time: pt.time as Time, value: pt.value })));
          maSeriesRef.current[key] = s;
        } else if (!enabled && existing) {
          ch.removeSeries(existing);
          delete maSeriesRef.current[key];
        }
      } catch {}
    });
  }, [chartReady, data, toggles.ma20, toggles.ma50, toggles.ma200]);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (search.trim()) nav(`/smc-chart/${search.trim().toUpperCase()}`);
  }

  function toggle(key: keyof Toggles) {
    setToggles((t) => ({ ...t, [key]: !t[key] }));
  }

  const toggleButtons: { key: keyof Toggles; label: string; color: string }[] = useMemo(() => [
    { key: "fvg", label: "FVG", color: "text-emerald-400" },
    { key: "ob", label: "Order Blocks", color: "text-violet-400" },
    { key: "bos", label: "BOS/ChoCh", color: "text-yellow-400" },
    { key: "levels", label: "Key Levels", color: "text-amber-400" },
    { key: "fib", label: "Fibonacci", color: "text-purple-400" },
    { key: "fibCircles", label: "Fib Circles", color: "text-pink-400" },
    { key: "gann", label: "Gann Fan", color: "text-amber-300" },
    { key: "pivots", label: "Pivots", color: "text-orange-400" },
    { key: "ma20", label: "MA20", color: "text-yellow-300" },
    { key: "ma50", label: "MA50", color: "text-blue-400" },
    { key: "ma200", label: "MA200", color: "text-pink-300" },
  ], []);

  const a = data?.analysis;

  return (
    <div className="min-h-screen p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <button onClick={() => nav("/")} className="p-2 rounded bg-gray-800 hover:bg-gray-700">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-white">{data?.symbol || symbol}</h1>
            {data && <span className="text-emerald-400 text-lg font-mono">${data.current_price.toFixed(2)}</span>}
          </div>
        </div>
        <form onSubmit={handleSearch} className="flex items-center gap-2">
          <div className="flex items-center gap-2 bg-gray-800 rounded px-3 py-1.5 border border-gray-700">
            <Search className="w-4 h-4 text-gray-500" />
            <input value={search} onChange={(e) => setSearch(e.target.value.toUpperCase())}
              placeholder="Symbol..." className="bg-transparent w-32 outline-none text-sm" />
          </div>
          <button type="submit" className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded text-sm">
            Load
          </button>
        </form>
        <div className="flex items-center gap-1 bg-gray-800/50 rounded p-1">
          {(["1mo", "3mo", "6mo", "1y", "2y"] as const).map((p) => (
            <button key={p} onClick={() => setPeriod(p)}
              className={clsx("px-3 py-1 rounded text-xs",
                period === p ? "bg-emerald-500/20 text-emerald-400" : "text-gray-400")}>
              {p}
            </button>
          ))}
          <button onClick={fetchData} className="p-1 rounded hover:bg-gray-700">
            <RefreshCw className={clsx("w-4 h-4", loading && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Toggles */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <span className="text-xs text-gray-500">Indicators:</span>
        {toggleButtons.map((b) => {
          const on = toggles[b.key];
          return (
            <button key={b.key} onClick={() => toggle(b.key)}
              className={clsx("flex items-center gap-1 px-2.5 py-1 rounded text-xs border transition",
                on ? "bg-gray-800 border-gray-600" : "bg-transparent border-gray-800 opacity-60")}>
              {on ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
              <span className={on ? b.color : "text-gray-500"}>{b.label}</span>
            </button>
          );
        })}
      </div>

      {/* Analysis Card */}
      {a && (
        <div className="mb-4 rounded-lg border-2 overflow-hidden"
          style={{ borderColor:
            a.action_color === "green" ? "#10b981" :
            a.action_color === "yellow" ? "#f59e0b" :
            a.action_color === "orange" ? "#f97316" :
            a.action_color === "red" ? "#ef4444" : "#6b7280" }}>
          <div className="px-4 py-3 flex items-center gap-3 flex-wrap"
            style={{ background:
              a.action_color === "green" ? "rgba(16,185,129,0.12)" :
              a.action_color === "yellow" ? "rgba(245,158,11,0.12)" :
              a.action_color === "orange" ? "rgba(249,115,22,0.12)" :
              a.action_color === "red" ? "rgba(239,68,68,0.12)" : "rgba(107,114,128,0.12)" }}>
            <span className={clsx(
              "px-3 py-1 rounded-full text-xs font-bold",
              a.bias === "BULLISH" && "bg-emerald-500/25 text-emerald-300",
              a.bias === "BEARISH" && "bg-red-500/25 text-red-300",
              a.bias === "WHIPSAW" && "bg-amber-500/25 text-amber-300",
              a.bias === "NEUTRAL" && "bg-gray-500/25 text-gray-300",
            )}>BIAS: {a.bias}</span>
            <span className="text-xs text-gray-500">
              Confidence: <strong className={clsx(
                a.confidence === "HIGH" && "text-emerald-400",
                a.confidence === "MEDIUM" && "text-yellow-400",
                a.confidence === "LOW" && "text-gray-500",
              )}>{a.confidence}</strong>
            </span>
            <span className="text-base font-bold" style={{ color:
              a.action_color === "green" ? "#10b981" :
              a.action_color === "yellow" ? "#f59e0b" :
              a.action_color === "orange" ? "#f97316" :
              a.action_color === "red" ? "#ef4444" : "#9ca3af" }}>
              → {a.action}
            </span>
          </div>
          <div className="px-4 py-3 bg-gray-900/40">
            <p className="text-sm mb-3">{a.summary}</p>
            {a.reasons.length > 0 && (
              <ul className="text-xs text-gray-400 space-y-1 mb-3">
                {a.reasons.map((r, i) => <li key={i} className="flex gap-2"><span>•</span><span>{r}</span></li>)}
              </ul>
            )}
            {a.entry !== null && (
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs mb-3">
                <div className="bg-emerald-500/10 border border-emerald-500/30 rounded px-2 py-1.5">
                  <div className="text-gray-500 text-[10px]">Entry</div>
                  <div className="font-mono font-bold text-emerald-400">${a.entry}</div>
                </div>
                <div className="bg-red-500/10 border border-red-500/30 rounded px-2 py-1.5">
                  <div className="text-gray-500 text-[10px]">Stop Loss</div>
                  <div className="font-mono font-bold text-red-400">${a.stop_loss}</div>
                </div>
                <div className="bg-blue-500/10 border border-blue-500/30 rounded px-2 py-1.5">
                  <div className="text-gray-500 text-[10px]">Target 1</div>
                  <div className="font-mono font-bold text-blue-400">${a.target1}</div>
                </div>
                <div className="bg-purple-500/10 border border-purple-500/30 rounded px-2 py-1.5">
                  <div className="text-gray-500 text-[10px]">Target 2</div>
                  <div className="font-mono font-bold text-purple-400">${a.target2}</div>
                </div>
                <div className="bg-gray-500/10 border border-gray-500/30 rounded px-2 py-1.5">
                  <div className="text-gray-500 text-[10px]">R/R</div>
                  <div className="font-mono font-bold">1 : {a.risk_reward}</div>
                </div>
              </div>
            )}
            {a.entry_label && <p className="text-xs text-gray-500 italic mb-2">{a.entry_label}</p>}
            {a.triggers.length > 0 && (
              <div className="border-t border-gray-700/50 pt-2">
                <p className="text-[11px] uppercase tracking-wide text-gray-500 mb-1">
                  Tomorrow — what to watch
                </p>
                {a.triggers.map((t, i) => (
                  <div key={i} className="text-xs flex gap-2 py-0.5">
                    <span>{t.icon}</span><span>{t.text}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Accumulation / Distribution card */}
      {data?.accumulation && (
        <div
          className="mb-4 rounded-lg border-2 overflow-hidden"
          style={{
            borderColor:
              data.accumulation.bias === "bullish" ? "#14b8a6" :
              data.accumulation.bias === "bearish" ? "#ef4444" :
              "#a78bfa",
          }}
        >
          <div
            className="px-4 py-2 flex items-center gap-3 flex-wrap"
            style={{
              background:
                data.accumulation.bias === "bullish" ? "rgba(20,184,166,0.1)" :
                data.accumulation.bias === "bearish" ? "rgba(239,68,68,0.1)" :
                "rgba(167,139,250,0.1)",
            }}
          >
            <span
              className={clsx(
                "px-2 py-0.5 rounded-full text-xs font-bold tracking-wide",
                data.accumulation.phase === "ACCUMULATION" && "bg-teal-500/25 text-teal-300",
                data.accumulation.phase === "DISTRIBUTION" && "bg-red-500/25 text-red-300",
                data.accumulation.phase === "CONSOLIDATION" && "bg-violet-500/25 text-violet-300",
              )}
            >
              📊 {data.accumulation.phase}
            </span>
            <span className="text-xs text-gray-500">
              Confidence: <strong>{data.accumulation.confidence}</strong>
            </span>
            {data.accumulation.target_up !== null && (
              <span className="text-sm font-mono text-teal-400">
                Breakout target: ${data.accumulation.target_up}
              </span>
            )}
            {data.accumulation.target_down !== null && (
              <span className="text-sm font-mono text-red-400">
                Breakdown target: ${data.accumulation.target_down}
              </span>
            )}
          </div>
          <div className="px-4 py-2 bg-gray-900/40 text-xs">
            <p className="mb-2">{data.accumulation.summary}</p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
              <div>
                <span className="text-gray-500">Range:</span>{" "}
                <span className="font-mono">
                  ${data.accumulation.range_low}–{data.accumulation.range_high}
                </span>{" "}
                <span className="text-gray-500">({data.accumulation.range_pct}%)</span>
              </div>
              <div>
                <span className="text-gray-500">Volume:</span>{" "}
                <span className={clsx(
                  "font-mono",
                  data.accumulation.volume_ratio >= 1.2 ? "text-emerald-400" :
                  data.accumulation.volume_ratio >= 0.8 ? "text-yellow-400" :
                  "text-gray-500",
                )}>
                  {data.accumulation.volume_ratio}x
                </span>
              </div>
              <div>
                <span className="text-gray-500">Tests:</span>{" "}
                <span className="font-mono">
                  {data.accumulation.support_tests}↓ / {data.accumulation.resistance_tests}↑
                </span>
              </div>
              <div>
                <span className="text-gray-500">Pre-trend:</span>{" "}
                <span className={clsx(
                  "font-mono",
                  data.accumulation.pre_trend_pct < 0 ? "text-red-400" : "text-emerald-400",
                )}>
                  {data.accumulation.pre_trend_pct > 0 ? "+" : ""}{data.accumulation.pre_trend_pct}%
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Chart */}
      <div className="bg-gray-900/30 rounded-lg border border-gray-700/50 p-2 relative">
        <div ref={containerRef} className="w-full" style={{ minHeight: CHART_HEIGHT }} />
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900/70 rounded-lg pointer-events-none">
            <div className="text-center">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto text-emerald-400 mb-2" />
              <p className="text-sm text-gray-500">Loading {symbol}...</p>
            </div>
          </div>
        )}
        {!loading && error && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center max-w-md p-4">
              <AlertTriangle className="w-8 h-8 mx-auto text-red-500 mb-2" />
              <p className="text-sm text-red-400 mb-2">Couldn't load {symbol}</p>
              <p className="text-xs text-gray-500 mb-3">{error}</p>
              <button onClick={fetchData}
                className="px-3 py-1 text-xs bg-emerald-500/20 text-emerald-400 rounded hover:bg-emerald-500/30">
                Retry
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="mt-4 text-xs text-gray-600 text-center">
        FVG = Fair Value Gap • OB = Order Block • BOS = Break of Structure • ChoCh = Change of Character
      </div>
    </div>
  );
}
