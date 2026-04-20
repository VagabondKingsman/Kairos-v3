import { useState, useMemo } from "react";
import type { Trade } from "@/lib/api";
import { clsx } from "clsx";

interface Props {
  trades: Trade[];
  selectedDate: string | null;
  onDateClick: (date: string) => void;
}

interface DayStat {
  date: string;
  totalPnl: number;
  longPnl: number;
  shortPnl: number;
  count: number;
}

export function DailyPnLChart({ trades, selectedDate, onDateClick }: Props) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [intradayDate, setIntradayDate] = useState<string | null>(null);

  // Aggregate daily stats
  const dailyStats = useMemo<DayStat[]>(() => {
    const map = new Map<string, DayStat>();
    for (const t of trades) {
      const d = t.filter_date ?? t.time_close.slice(0, 10);
      if (!map.has(d)) map.set(d, { date: d, totalPnl: 0, longPnl: 0, shortPnl: 0, count: 0 });
      const s = map.get(d)!;
      s.totalPnl += t.pnl_usd;
      s.count++;
      if (t.filter_side === "long") s.longPnl += t.pnl_usd;
      else s.shortPnl += t.pnl_usd;
    }
    return Array.from(map.values())
      .sort((a, b) => a.date.localeCompare(b.date))
      .slice(-60); // last 60 days
  }, [trades]);

  // Intraday breakdown for selected day
  const intradayTrades = useMemo(() => {
    if (!intradayDate) return [];
    return trades
      .filter(t => (t.filter_date ?? t.time_close.slice(0, 10)) === intradayDate)
      .sort((a, b) => a.time_close.localeCompare(b.time_close));
  }, [trades, intradayDate]);

  const maxAbs = useMemo(() =>
    Math.max(...dailyStats.map(d => Math.abs(d.totalPnl)), 1),
    [dailyStats]
  );

  const totalPnl = useMemo(() => trades.reduce((s, t) => s + t.pnl_usd, 0), [trades]);

  const handleBarClick = (date: string) => {
    if (intradayDate === date) {
      setIntradayDate(null);
    } else {
      setIntradayDate(date);
      onDateClick(date);
    }
  };

  return (
    <div className="w-full h-full flex flex-col">
      {/* Total PnL header */}
      <div className="flex items-center justify-between mb-2">
        <span className={clsx("text-xl font-bold font-mono", totalPnl >= 0 ? "text-success" : "text-danger")}>
          {totalPnl >= 0 ? "+" : ""}{totalPnl.toLocaleString("vi-VN", { maximumFractionDigits: 0 })}$
        </span>
        {intradayDate && (
          <button
            onClick={() => { setIntradayDate(null); onDateClick(intradayDate); }}
            className="text-xs text-primary hover:underline"
          >
            ← Quay lại tổng quan
          </button>
        )}
      </div>

      {/* Chart area */}
      {!intradayDate ? (
        /* Daily bars */
        <div className="flex-1 flex items-end gap-px overflow-hidden relative">
          {/* Zero line */}
          <div className="absolute inset-x-0 top-1/2 border-t border-border/50 border-dashed pointer-events-none" />

          {dailyStats.map((d, i) => {
            const isSelected = selectedDate === d.date;
            const isHovered = hoveredIndex === i;
            const barH = (Math.abs(d.totalPnl) / maxAbs) * 44; // max 44% height
            const isWin = d.totalPnl >= 0;

            return (
              <div
                key={d.date}
                className="flex-1 flex flex-col items-center cursor-pointer group"
                style={{ minWidth: 4 }}
                onClick={() => handleBarClick(d.date)}
                onMouseEnter={() => setHoveredIndex(i)}
                onMouseLeave={() => setHoveredIndex(null)}
                title={`${d.date}: ${d.totalPnl >= 0 ? "+" : ""}${d.totalPnl.toFixed(0)}$ (${d.count} lệnh)`}
              >
                {/* Top half (wins) */}
                <div className="flex-1 flex items-end justify-center w-full">
                  <div
                    className={clsx(
                      "w-full transition-opacity rounded-t-sm",
                      isWin ? "bg-success" : "opacity-0",
                      (isSelected || isHovered) ? "opacity-100" : "opacity-75"
                    )}
                    style={{ height: isWin ? `${barH}%` : "0%" }}
                  />
                </div>

                {/* Bottom half (losses) */}
                <div className="flex-1 flex items-start justify-center w-full">
                  <div
                    className={clsx(
                      "w-full transition-opacity rounded-b-sm",
                      !isWin ? "bg-danger" : "opacity-0",
                      (isSelected || isHovered) ? "opacity-100" : "opacity-75"
                    )}
                    style={{ height: !isWin ? `${barH}%` : "0%" }}
                  />
                </div>

                {/* Selected highlight ring */}
                {isSelected && (
                  <div className="absolute inset-x-0 inset-y-0 ring-1 ring-primary rounded pointer-events-none" />
                )}
              </div>
            );
          })}
        </div>
      ) : (
        /* Intraday line chart */
        <IntradayLine trades={intradayTrades} date={intradayDate} />
      )}
    </div>
  );
}

function IntradayLine({ trades, date }: { trades: Trade[]; date: string }) {
  const points = useMemo(() => {
    let cum = 0;
    const pts = [0, ...trades.map(t => { cum += t.pnl_usd; return cum; })];
    return pts;
  }, [trades]);

  const maxV = Math.max(...points.map(Math.abs), 1);
  const svgH = 100;
  const svgW = 400;

  const pathD = points.map((v, i) => {
    const x = (i / (points.length - 1)) * svgW;
    const y = svgH / 2 - (v / maxV) * (svgH / 2.2);
    return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");

  const lastY = svgH / 2 - (points[points.length - 1] / maxV) * (svgH / 2.2);
  const isProfit = points[points.length - 1] >= 0;

  return (
    <div className="flex-1 flex flex-col">
      <div className="text-xs text-primary mb-1">
        Chi tiết {date} — {trades.length} lệnh
      </div>
      <div className="flex-1 relative">
        <svg viewBox={`0 0 ${svgW} ${svgH}`} className="w-full h-full" preserveAspectRatio="none">
          {/* Zero line */}
          <line x1="0" y1={svgH / 2} x2={svgW} y2={svgH / 2} stroke="#333" strokeDasharray="4 4" strokeWidth="0.5" />
          {/* Fill */}
          <path
            d={`${pathD} L${svgW},${svgH / 2} L0,${svgH / 2} Z`}
            fill={isProfit ? "rgba(76,175,80,0.1)" : "rgba(229,57,53,0.1)"}
          />
          {/* Line */}
          <path d={pathD} fill="none" stroke={isProfit ? "#4CAF50" : "#E53935"} strokeWidth="1.5" />
          {/* End dot */}
          <circle cx={svgW} cy={lastY} r="3" fill={isProfit ? "#4CAF50" : "#E53935"} />
        </svg>
      </div>
    </div>
  );
}
