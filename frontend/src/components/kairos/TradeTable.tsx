import { clsx } from "clsx";
import type { Trade } from "@/lib/api";

export function TradeTable({ trades }: { trades: Trade[] }) {
  if (trades.length === 0) {
    return <div className="py-8 text-center text-sm text-muted-foreground">Không có lệnh nào</div>;
  }
  return (
    <div className="overflow-auto max-h-72">
      <table className="w-full text-xs border-collapse">
        <thead className="sticky top-0 bg-muted/80 backdrop-blur-sm">
          <tr>
            {["Mở Lệnh","Đóng Lệnh","Hướng","Vào ($)","Ra ($)","PnL (USD)","Thời gian"].map(h => (
              <th key={h} className="px-3 py-2 text-left font-semibold text-muted-foreground border-b border-border">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {trades.map((t, i) => {
            const isWin = t.pnl_usd > 0;
            return (
              <tr key={t.id ?? i} className={clsx("border-b border-border/50 transition-colors hover:bg-muted/30", i % 2 === 0 ? "" : "bg-muted/10")}>
                <td className="px-3 py-1.5 font-mono text-muted-foreground">{t.time_open.slice(0,16).replace("T"," ")}</td>
                <td className="px-3 py-1.5 font-mono text-muted-foreground">{t.time_close.slice(0,16).replace("T"," ")}</td>
                <td className="px-3 py-1.5">
                  <span className={clsx("px-1.5 py-0.5 rounded text-[10px] font-semibold", t.side === "long" ? "bg-success/15 text-success" : "bg-danger/15 text-danger")}>
                    {t.side === "long" ? "LONG" : "SHORT"}
                  </span>
                </td>
                <td className="px-3 py-1.5 font-mono">{t.entry_price.toLocaleString("vi-VN",{maximumFractionDigits:2})}</td>
                <td className="px-3 py-1.5 font-mono">{t.exit_price.toLocaleString("vi-VN",{maximumFractionDigits:2})}</td>
                <td className={clsx("px-3 py-1.5 font-mono font-semibold", isWin ? "text-success" : "text-danger")}>
                  {isWin ? "+" : ""}{t.pnl_usd.toLocaleString("vi-VN",{maximumFractionDigits:2})}$
                </td>
                <td className="px-3 py-1.5 text-muted-foreground">{t.duration_h.toFixed(1)}h</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
