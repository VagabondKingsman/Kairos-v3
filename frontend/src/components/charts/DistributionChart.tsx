import { useMemo } from "react";
import { clsx } from "clsx";
import type { Trade } from "@/lib/api";

interface Props {
  type: "day" | "hour";
  trades: Trade[];
  selectedIndex: number | null;
  onBarClick: (index: number) => void;
}

const DAY_LABELS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];
const HOUR_LABELS = Array.from({ length: 24 }, (_, i) => `${i}h`);

export function DistributionChart({ type, trades, selectedIndex, onBarClick }: Props) {
  const count = type === "day" ? 7 : 24;
  const labels = type === "day" ? DAY_LABELS : HOUR_LABELS;

  // Aggregate PnL per day/hour
  const data = useMemo(() => {
    const arr = new Array<number>(count).fill(0);
    for (const t of trades) {
      const idx = type === "day"
        ? ((t.filter_weekday ?? 1) - 1)   // 1=Mon=0..7=Sun=6
        : (t.filter_hour ?? 0);
      if (idx >= 0 && idx < count) arr[idx] += t.pnl_usd;
    }
    return arr;
  }, [trades, type, count]);

  const maxAbs = Math.max(...data.map(Math.abs), 1);

  return (
    <div className="w-full h-full flex flex-col">
      {/* Bars */}
      <div className="flex-1 flex items-end gap-0.5 overflow-hidden relative">
        {/* Zero line */}
        <div className="absolute inset-x-0 top-1/2 border-t border-border/40 border-dashed pointer-events-none" />

        {data.map((val, i) => {
          const isSelected = selectedIndex === i;
          const isDimmed = selectedIndex !== null && !isSelected;
          const isWin = val >= 0;
          const barH = (Math.abs(val) / maxAbs) * 42;

          return (
            <div
              key={i}
              className="flex-1 flex flex-col items-center cursor-pointer"
              onClick={() => onBarClick(i)}
              title={`${labels[i]}: ${val >= 0 ? "+" : ""}${val.toFixed(0)}$`}
            >
              {/* Top (positive) */}
              <div className="flex-1 w-full flex items-end">
                {isWin && (
                  <div
                    className={clsx(
                      "w-full rounded-t-sm transition-all",
                      isSelected ? "bg-success ring-1 ring-success" : "bg-success",
                      isDimmed ? "opacity-25" : "opacity-80 hover:opacity-100"
                    )}
                    style={{ height: `${barH}%` }}
                  />
                )}
              </div>

              {/* Bottom (negative) */}
              <div className="flex-1 w-full flex items-start">
                {!isWin && (
                  <div
                    className={clsx(
                      "w-full rounded-b-sm transition-all",
                      isSelected ? "bg-danger ring-1 ring-danger" : "bg-danger",
                      isDimmed ? "opacity-25" : "opacity-80 hover:opacity-100"
                    )}
                    style={{ height: `${barH}%` }}
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Labels */}
      <div className="flex gap-0.5 mt-1">
        {labels.map((lbl, i) => {
          const isSelected = selectedIndex === i;
          const show = type === "day" || i % 3 === 0;
          return (
            <div
              key={i}
              className={clsx(
                "flex-1 text-center text-[9px] truncate transition-colors cursor-pointer",
                isSelected ? "text-primary font-bold" : "text-muted-foreground"
              )}
              onClick={() => onBarClick(i)}
            >
              {show ? lbl : ""}
            </div>
          );
        })}
      </div>
    </div>
  );
}
