import { useEffect, useRef } from "react";
import * as echarts from "echarts";

interface Props {
  data: Array<{ time: string; equity: number }>;
  initialCash: number;
  height?: number;
}

export function EquityCurveChart({ data, initialCash, height = 260 }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || data.length === 0) return;
    const chart = echarts.init(ref.current, "dark");

    const times = data.map(d => d.time);
    const equities = data.map(d => d.equity);
    const isProfit = equities[equities.length - 1] >= initialCash;

    const color = isProfit ? "#4CAF50" : "#E53935";
    const colorFade = isProfit ? "rgba(76,175,80,0.08)" : "rgba(229,57,53,0.08)";

    // Drawdown series
    const drawdowns = equities.map((eq, i) => {
      const peak = Math.max(...equities.slice(0, i + 1));
      return parseFloat(((eq - peak) / peak * 100).toFixed(2));
    });

    chart.setOption({
      backgroundColor: "transparent",
      tooltip: {
        trigger: "axis",
        backgroundColor: "#1a1d26",
        borderColor: "#2a2d3a",
        textStyle: { color: "#e0e0e0", fontSize: 12 },
        formatter: (params: echarts.TooltipComponentFormatterCallbackParams) => {
          const p = params as { name: string; value: number; seriesName: string }[];
          if (!Array.isArray(p)) return "";
          const eq = p.find(x => x.seriesName === "Vốn");
          const dd = p.find(x => x.seriesName === "Drawdown");
          return `<div style="padding:4px 8px">
            <div style="color:#999;font-size:11px">${p[0]?.name}</div>
            ${eq ? `<div>Vốn: <b style="color:${color}">${eq.value.toLocaleString("vi-VN")}$</b></div>` : ""}
            ${dd ? `<div>DD: <b style="color:#E53935">${dd.value}%</b></div>` : ""}
          </div>`;
        },
      },
      legend: {
        top: 0, right: 8,
        textStyle: { color: "#888", fontSize: 11 },
      },
      grid: [
        { top: 28, left: 72, right: 16, height: "56%" },
        { top: "72%", left: 72, right: 16, bottom: 24 },
      ],
      xAxis: [
        { type: "category", data: times, gridIndex: 0, show: false, boundaryGap: false },
        { type: "category", data: times, gridIndex: 1, axisLabel: { color: "#666", fontSize: 10 }, boundaryGap: false },
      ],
      yAxis: [
        {
          gridIndex: 0, scale: true, splitLine: { lineStyle: { color: "#1e2130" } },
          axisLabel: { color: "#666", fontSize: 10, formatter: (v: number) => `${(v / 1000).toFixed(0)}K` },
        },
        {
          gridIndex: 1, scale: true, splitLine: { lineStyle: { color: "#1e2130" } },
          axisLabel: { color: "#666", fontSize: 10, formatter: (v: number) => `${v}%` },
        },
      ],
      series: [
        {
          name: "Vốn", type: "line", xAxisIndex: 0, yAxisIndex: 0,
          data: equities, symbol: "none", lineStyle: { color, width: 2 },
          areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color }, { offset: 1, color: colorFade }] } },
          markLine: {
            silent: true, symbol: "none",
            data: [{ yAxis: initialCash, lineStyle: { color: "#444", type: "dashed" }, label: { show: true, formatter: "Vốn ban đầu", color: "#666" } }],
          },
        },
        {
          name: "Drawdown", type: "line", xAxisIndex: 1, yAxisIndex: 1,
          data: drawdowns, symbol: "none", lineStyle: { color: "#E53935", width: 1.5 },
          areaStyle: { color: "rgba(229,57,53,0.12)" },
        },
      ],
    });

    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(ref.current);
    return () => { ro.disconnect(); chart.dispose(); };
  }, [data, initialCash]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}
