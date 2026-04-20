import { useMemo } from "react";
import { clsx } from "clsx";
import type { Trade } from "@/lib/api";

interface Props {
  trades: Trade[];
  year: number;
  month: number;
  selectedDate: string | null;
  onDateClick: (date: string) => void;
  onPrevMonth: () => void;
  onNextMonth: () => void;
}

const DAYS = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];

function isoDate(y: number, m: number, d: number) {
  return `${y}-${String(m).padStart(2,"0")}-${String(d).padStart(2,"0")}`;
}

export function PnLCalendar({ trades, year, month, selectedDate, onDateClick, onPrevMonth, onNextMonth }: Props) {
  const pnlMap = useMemo(() => {
    const map = new Map<string, number>();
    for (const t of trades) {
      const d = t.filter_date ?? t.time_close.slice(0, 10);
      map.set(d, (map.get(d) ?? 0) + t.pnl_usd);
    }
    return map;
  }, [trades]);

  const daysInMonth = new Date(year, month, 0).getDate();
  const firstDow = new Date(year, month - 1, 1).getDay();
  const cells: (number | null)[] = [];
  for (let i = 0; i < firstDow; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);

  const maxPnl = Math.max(...Array.from(pnlMap.values()).map(Math.abs), 1);
  const today = isoDate(new Date().getFullYear(), new Date().getMonth() + 1, new Date().getDate());

  const color = (pnl: number) => {
    const a = (0.15 + Math.min(Math.abs(pnl) / maxPnl, 1) * 0.65).toFixed(2);
    return pnl >= 0 ? `rgba(76,175,80,${a})` : `rgba(229,57,53,${a})`;
  };

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-2">
        <button onClick={onPrevMonth} className="px-2 py-0.5 rounded hover:bg-muted text-muted-foreground text-sm">‹</button>
        <span className="text-[11px] font-semibold text-muted-foreground">Tháng {String(month).padStart(2,"0")} / {year}</span>
        <button onClick={onNextMonth} className="px-2 py-0.5 rounded hover:bg-muted text-muted-foreground text-sm">›</button>
      </div>
      <div className="grid grid-cols-7 mb-1">
        {DAYS.map(d => <div key={d} className="text-center text-[9px] text-muted-foreground">{d}</div>)}
      </div>
      <div className="grid grid-cols-7 gap-0.5">
        {cells.map((day, i) => {
          if (!day) return <div key={`e${i}`} />;
          const ds = isoDate(year, month, day);
          const pnl = pnlMap.get(ds);
          return (
            <div key={ds} onClick={() => pnl !== undefined && onDateClick(ds)}
              className={clsx("rounded-sm py-1 text-center transition-all",
                pnl !== undefined ? "cursor-pointer" : "",
                selectedDate === ds ? "ring-1 ring-primary" : "",
                ds === today ? "ring-1 ring-primary/40" : "")}
              style={{ background: pnl !== undefined ? color(pnl) : undefined }}
              title={pnl !== undefined ? `${ds}: ${pnl >= 0 ? "+" : ""}${pnl.toFixed(0)}$` : undefined}>
              <div className={clsx("text-[10px] font-semibold", ds === today ? "text-primary" : pnl !== undefined ? "text-foreground" : "text-muted-foreground/40")}>{day}</div>
              {pnl !== undefined && (
                <div className={clsx("text-[8px] font-mono", pnl >= 0 ? "text-success" : "text-danger")}>
                  {pnl >= 0 ? "+" : ""}{Math.abs(pnl) >= 1000 ? `${(pnl/1000).toFixed(1)}K` : pnl.toFixed(0)}
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className="flex gap-3 justify-end mt-1.5">
        <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-sm bg-success/70"/><span className="text-[9px] text-muted-foreground">Lãi</span></div>
        <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-sm bg-danger/70"/><span className="text-[9px] text-muted-foreground">Lỗ</span></div>
      </div>
    </div>
  );
}
