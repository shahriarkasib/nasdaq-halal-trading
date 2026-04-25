import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  type Time,
} from 'lightweight-charts';
import axios from 'axios';
import { ArrowLeft, RefreshCw } from 'lucide-react';

interface FVG {
  type: 'bullish' | 'bearish';
  top: number;
  bottom: number;
  start_time: string;
  end_time: string;
}

interface StructureEvent {
  type: 'bullish_BOS' | 'bearish_BOS' | 'bullish_ChoCh' | 'bearish_ChoCh';
  price: number;
  from_price: number;
  time: string;
  from_time: string;
}

interface ChartData {
  symbol: string;
  current_price: number;
  candles: Array<{ time: string; open: number; high: number; low: number; close: number }>;
  volumes: Array<{ time: string; value: number; color: string }>;
  fvgs: FVG[];
  structure: StructureEvent[];
}

const API = import.meta.env.PROD ? 'http://34.126.141.16:8001' : '';

export default function Chart() {
  const { symbol = 'ABT' } = useParams();
  const nav = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const [data, setData] = useState<ChartData | null>(null);
  const [period, setPeriod] = useState<'1mo' | '3mo' | '6mo' | '1y'>('6mo');
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState(symbol);

  async function fetchData() {
    setLoading(true);
    try {
      const res = await axios.get<ChartData>(`${API}/api/v1/nasdaq/chart/${symbol}?period=${period}`);
      setData(res.data);
    } catch (err) {
      console.error(err);
      setData(null);
    }
    setLoading(false);
  }

  useEffect(() => { fetchData(); }, [symbol, period]);

  useEffect(() => {
    if (!data || !containerRef.current) return;

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 600,
      layout: { background: { color: '#0a0e17' }, textColor: '#d1d5db' },
      grid: { vertLines: { color: '#1f2937' }, horzLines: { color: '#1f2937' } },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: '#374151' },
      timeScale: { borderColor: '#374151', timeVisible: true },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });
    candleSeries.setData(data.candles.map(c => ({ ...c, time: c.time as Time })));

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    });
    volumeSeries.setData(data.volumes.map(v => ({ ...v, time: v.time as Time })));

    // FVG zones (drawn as series-based price lines on the candle series + overlay rectangles via primitives)
    // lightweight-charts v5 lets us add price lines per series for visual zones
    data.fvgs.forEach(fvg => {
      // Simplified: draw top + bottom as price lines (visual marker)
      const color = fvg.type === 'bullish' ? 'rgba(38, 166, 154, 0.25)' : 'rgba(239, 83, 80, 0.25)';
      candleSeries.createPriceLine({
        price: fvg.top,
        color: color,
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: false,
        title: fvg.type === 'bullish' ? 'FVG↑' : 'FVG↓',
      });
      candleSeries.createPriceLine({
        price: fvg.bottom,
        color: color,
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: false,
        title: '',
      });
    });

    // Structure events (BOS / ChoCh) - draw as price lines with labels
    data.structure.forEach(ev => {
      const isBullish = ev.type.startsWith('bullish');
      const isBOS = ev.type.includes('BOS');
      const label = isBOS ? 'BOS' : 'ChoCh';
      candleSeries.createPriceLine({
        price: ev.from_price,
        color: isBullish ? '#26a69a' : '#ef5350',
        lineWidth: 2,
        lineStyle: 0,
        axisLabelVisible: true,
        title: `${label} ${isBullish ? '↑' : '↓'}`,
      });
    });

    // Markers for BOS/ChoCh on the candles (v5: use custom markers via setMarkers)
    const markers = data.structure.map(ev => ({
      time: ev.time as Time,
      position: ev.type.startsWith('bullish') ? ('belowBar' as const) : ('aboveBar' as const),
      color: ev.type.startsWith('bullish') ? '#26a69a' : '#ef5350',
      shape: 'arrowUp' as const,
      text: ev.type.includes('BOS') ? 'BOS' : 'ChoCh',
    }));
    // setMarkers may exist in v5 via `createSeriesMarkers` — we'll attempt it
    try {
      // @ts-expect-error createSeriesMarkers may be available
      if (chart.createSeriesMarkers) {
        // @ts-expect-error
        chart.createSeriesMarkers(candleSeries, markers);
      }
    } catch {}

    candleSeriesRef.current = candleSeries;
    chartRef.current = chart;
    chart.timeScale().fitContent();

    const ro = new ResizeObserver(() => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [data]);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (search.trim()) nav(`/chart/${search.trim().toUpperCase()}`);
  }

  return (
    <div className="min-h-screen bg-[#0a0e17] text-gray-200 p-4 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <button onClick={() => nav('/')} className="p-2 rounded bg-gray-800 hover:bg-gray-700">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-white">{data?.symbol || symbol}</h1>
            {data && (
              <span className="text-emerald-400 text-lg font-mono">${data.current_price.toFixed(2)}</span>
            )}
          </div>
        </div>

        <form onSubmit={handleSearch} className="flex items-center gap-2">
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value.toUpperCase())}
            placeholder="Symbol..."
            className="px-3 py-1.5 bg-gray-800 rounded text-sm w-32 border border-gray-700 focus:border-emerald-500 outline-none"
          />
          <button type="submit" className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded text-sm">
            Load
          </button>
        </form>

        <div className="flex items-center gap-1 bg-gray-800/50 rounded p-1">
          {(['1mo', '3mo', '6mo', '1y'] as const).map(p => (
            <button key={p} onClick={() => setPeriod(p)}
              className={`px-3 py-1 rounded text-xs ${period === p ? 'bg-emerald-500/20 text-emerald-400' : 'text-gray-400'}`}>
              {p}
            </button>
          ))}
          <button onClick={fetchData} className="p-1 rounded hover:bg-gray-700">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="bg-gray-900/30 rounded-lg border border-gray-700/50 p-2">
        <div ref={containerRef} className="w-full" />
        {loading && (
          <div className="text-center py-20 text-gray-500">Loading chart...</div>
        )}
        {!loading && !data && (
          <div className="text-center py-20 text-red-400">No data found for {symbol}</div>
        )}
      </div>

      {data && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          <div className="bg-gray-800/30 rounded-lg p-4 border border-gray-700/50">
            <h3 className="text-sm font-bold text-emerald-400 mb-2">FVG Zones ({data.fvgs.length})</h3>
            <div className="space-y-1 max-h-60 overflow-y-auto">
              {data.fvgs.slice(0, 10).map((f, i) => (
                <div key={i} className="text-xs flex items-center justify-between border-b border-gray-700/30 py-1">
                  <span className={f.type === 'bullish' ? 'text-emerald-400' : 'text-red-400'}>
                    {f.type === 'bullish' ? '↑' : '↓'} {f.type.toUpperCase()}
                  </span>
                  <span className="font-mono text-gray-400">
                    ${f.bottom.toFixed(2)} – ${f.top.toFixed(2)}
                  </span>
                  <span className="text-gray-500">{f.start_time}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-gray-800/30 rounded-lg p-4 border border-gray-700/50">
            <h3 className="text-sm font-bold text-yellow-400 mb-2">Structure Events ({data.structure.length})</h3>
            <div className="space-y-1 max-h-60 overflow-y-auto">
              {data.structure.slice(0, 10).map((s, i) => {
                const isBullish = s.type.startsWith('bullish');
                const isBOS = s.type.includes('BOS');
                return (
                  <div key={i} className="text-xs flex items-center justify-between border-b border-gray-700/30 py-1">
                    <span className={isBullish ? 'text-emerald-400' : 'text-red-400'}>
                      {isBullish ? '↑' : '↓'} {isBOS ? 'BOS' : 'ChoCh'}
                    </span>
                    <span className="font-mono text-gray-400">${s.price.toFixed(2)}</span>
                    <span className="text-gray-500">{s.time}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      <div className="mt-4 text-xs text-gray-600 text-center">
        FVG = Fair Value Gap (3-candle imbalance) | BOS = Break of Structure | ChoCh = Change of Character
      </div>
    </div>
  );
}
