import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface CandleBar {
  time: string;  // "2024-01-02"
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
  entry?: boolean;   // điểm vào lệnh
  exit?: boolean;    // điểm thoát lệnh
  signal?: "BUY" | "SELL";
}

interface Props {
  data: CandleBar[];
  timeframe?: string;
  height?: number;
}

function genCandleData(n = 120, base = 45000): CandleBar[] {
  const result: CandleBar[] = [];
  let price = base;
  const start = new Date("2024-06-01");

  for (let i = 0; i < n; i++) {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    const change = (Math.random() - 0.49) * price * 0.022;
    const open = price;
    const close = price + change;
    const high = Math.max(open, close) + Math.random() * price * 0.008;
    const low = Math.min(open, close) - Math.random() * price * 0.008;
    const volume = 100 + Math.random() * 500;

    // Tạo điểm vào/thoát ngẫu nhiên
    const isEntry = i > 5 && i % 22 === 0;
    const isExit = i > 5 && (i - 11) % 22 === 0;

    result.push({
      time: d.toISOString().slice(0, 10),
      open: parseFloat(open.toFixed(2)),
      high: parseFloat(high.toFixed(2)),
      low: parseFloat(low.toFixed(2)),
      close: parseFloat(close.toFixed(2)),
      volume: parseFloat(volume.toFixed(2)),
      entry: isEntry,
      exit: isExit,
      signal: isEntry ? (change > 0 ? "BUY" : "SELL") : undefined,
    });

    price = close;
  }
  return result;
}

export function MultiTimeframeCandleChart({ data, timeframe = "1H", height = 360 }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;

    const candles = data.length > 0 ? data : genCandleData();
    const times = candles.map(d => d.time);
    const ohlc = candles.map(d => [d.open, d.close, d.low, d.high]);
    const volumes = candles.map(d => d.volume ?? 0);
    const volumeColors = candles.map(d => d.close >= d.open ? "rgba(16,185,129,0.5)" : "rgba(239,68,68,0.5)");

    // Điểm vào lệnh
    const entryPoints = candles
      .filter(d => d.entry)
      .map(d => ({
        name: d.signal === "BUY" ? "Vào Mua" : "Vào Bán",
        coord: [d.time, d.low * 0.997],
        value: d.signal,
        itemStyle: { color: d.signal === "BUY" ? "#10b981" : "#ef4444" },
        symbol: d.signal === "BUY" ? "arrow" : "arrow",
        symbolRotate: d.signal === "BUY" ? 0 : 180,
        symbolSize: 12,
        label: {
          show: true,
          formatter: d.signal === "BUY" ? "▲ BUY" : "▼ SELL",
          color: d.signal === "BUY" ? "#10b981" : "#ef4444",
          fontSize: 10,
          position: d.signal === "BUY" ? "bottom" : "top",
        }
      }));

    // Điểm thoát lệnh
    const exitPoints = candles
      .filter(d => d.exit)
      .map(d => ({
        name: "Thoát Lệnh",
        coord: [d.time, d.high * 1.003],
        itemStyle: { color: "#f59e0b" },
        symbol: "diamond",
        symbolSize: 10,
        label: {
          show: true,
          formatter: "✕ Exit",
          color: "#f59e0b",
          fontSize: 10,
          position: "top",
        }
      }));

    const chart = echarts.init(ref.current, "dark");

    chart.setOption({
      backgroundColor: "transparent",
      animation: false,
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "cross" },
        backgroundColor: "#0f1117",
        borderColor: "#2a2d3a",
        textStyle: { color: "#e0e0e0", fontSize: 11 },
        formatter: (params: any) => {
          const c = params.find((p: any) => p.seriesName === "Giá");
          if (!c) return "";
          const [o, cl, lo, hi] = c.value;
          const diff = cl - o;
          const color = diff >= 0 ? "#10b981" : "#ef4444";
          return `<div style="padding:4px 8px;min-width:160px">
            <div style="color:#666;font-size:10px;margin-bottom:4px">${c.name} · ${timeframe}</div>
            <div>O: <b style="color:${color}">${o?.toLocaleString()}</b></div>
            <div>H: <b style="color:#10b981">${hi?.toLocaleString()}</b></div>
            <div>L: <b style="color:#ef4444">${lo?.toLocaleString()}</b></div>
            <div>C: <b style="color:${color}">${cl?.toLocaleString()}</b></div>
            <div style="color:${color};font-weight:bold">${diff >= 0 ? "+" : ""}${diff?.toFixed(2)} (${((diff / o) * 100)?.toFixed(2)}%)</div>
          </div>`;
        }
      },
      axisPointer: { link: [{ xAxisIndex: "all" }] },
      dataZoom: [
        { type: "inside", xAxisIndex: [0, 1], start: 60, end: 100 },
        { type: "slider", xAxisIndex: [0, 1], bottom: 0, height: 20, start: 60, end: 100, fillerColor: "rgba(99,102,241,0.1)", borderColor: "#2a2d3a", handleStyle: { color: "#6366f1" }, textStyle: { color: "#666" } }
      ],
      grid: [
        { left: 70, right: 16, top: 16, height: "62%" },
        { left: 70, right: 16, top: "76%", height: "14%" },
      ],
      xAxis: [
        { type: "category", data: times, gridIndex: 0, show: false, boundaryGap: false },
        { type: "category", data: times, gridIndex: 1, boundaryGap: false, axisLabel: { color: "#555", fontSize: 10 }, axisLine: { lineStyle: { color: "#2a2d3a" } }, splitLine: { show: false } },
      ],
      yAxis: [
        {
          scale: true, gridIndex: 0,
          splitLine: { lineStyle: { color: "#1a1d26" } },
          axisLabel: { color: "#555", fontSize: 10, formatter: (v: number) => v.toLocaleString("en", { notation: "compact", maximumFractionDigits: 1 }) },
          axisLine: { lineStyle: { color: "#2a2d3a" } },
        },
        {
          scale: true, gridIndex: 1,
          splitLine: { show: false },
          axisLabel: { color: "#555", fontSize: 9, formatter: (v: number) => `${(v / 1000).toFixed(0)}K` },
          axisLine: { lineStyle: { color: "#2a2d3a" } },
        }
      ],
      series: [
        {
          name: "Giá",
          type: "candlestick",
          xAxisIndex: 0, yAxisIndex: 0,
          data: ohlc,
          itemStyle: {
            color: "#10b981",
            color0: "#ef4444",
            borderColor: "#10b981",
            borderColor0: "#ef4444",
          },
          markPoint: {
            symbol: "pin",
            data: [...entryPoints, ...exitPoints],
          },
        },
        {
          name: "Volume",
          type: "bar",
          xAxisIndex: 1, yAxisIndex: 1,
          data: volumes,
          itemStyle: {
            color: (params: any) => volumeColors[params.dataIndex] ?? "rgba(99,102,241,0.4)",
          },
          barMaxWidth: 6,
        },
      ],
    });

    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(ref.current!);
    return () => { ro.disconnect(); chart.dispose(); };
  }, [data, timeframe]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}
