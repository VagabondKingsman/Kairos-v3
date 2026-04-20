import { useParams, Link } from "react-router-dom";
import { useState, useMemo, useEffect } from "react";
import Papa from "papaparse";
import {
  ArrowLeft, TrendingUp, TrendingDown, Activity,
  BarChart2, Calendar, Clock, Layers, Download,
  CandlestickChart
} from "lucide-react";
import { clsx } from "clsx";
import { EquityCurveChart } from "@/components/charts/EquityCurveChart";
import { DailyPnLChart } from "@/components/charts/DailyPnLChart";
import { DistributionChart } from "@/components/charts/DistributionChart";
import { PnLCalendar } from "@/components/charts/PnLCalendar";
import { TradeTable } from "@/components/kairos/TradeTable";
import { MultiTimeframeCandleChart } from "@/components/charts/MultiTimeframeCandleChart";
import { api, type BacktestRun, type Trade } from "@/lib/api";

// ─── Helpers ─────────────────────────────────────────────────────────────────
const fmt$ = (v: number) =>
  `${v >= 0 ? "+" : ""}${v.toLocaleString("vi-VN", { maximumFractionDigits: 0 })}$`;
const fmtPct = (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;

function MetricItem({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-border/30 last:border-0">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={clsx("text-sm font-semibold font-mono", color ?? "text-foreground")}>{value}</span>
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────
export function BacktestDetail() {
  const { runId = "demo" } = useParams();
  
  // States
  const [run, setRun] = useState<BacktestRun | null>(null);
  const [equityData, setEquityData] = useState<Array<{ time: string; equity: number }>>([]);
  const [tradesData, setTradesData] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [dayFilter, setDayFilter] = useState<number | null>(null);
  const [hourFilter, setHourFilter] = useState<number | null>(null);
  const [dateFilter, setDateFilter] = useState<string | null>(null);
  const [activeTimeframe, setActiveTimeframe] = useState("1H");
  const [calMonth, setCalMonth] = useState(() => {
    const d = new Date(); return { year: d.getFullYear(), month: d.getMonth() + 1 };
  });

  useEffect(() => {
    const fetchRealData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch run metadata, equity CSV, and trades CSV in parallel
        const [runData, equityCsv, tradesCsv] = await Promise.all([
          api.getKairosRun(runId),
          api.getArtifact(runId, "equity.csv"),
          api.getArtifact(runId, "trades.csv"),
        ]);

        setRun(runData);

        // Set default timeframe from run config
        if (runData.config?.htf) setActiveTimeframe(runData.config.htf);

        // Parse equity CSV — column is "timestamp"
        Papa.parse(equityCsv, {
          header: true,
          dynamicTyping: true,
          skipEmptyLines: true,
          complete: (results) => {
            const formattedEquity = results.data.map((row: any) => ({
              time: row.timestamp ? String(row.timestamp).split('T')[0] : '',
              equity: Number(row.equity) || 0
            }));
            setEquityData(formattedEquity);
          }
        });

        // Parse trades CSV
        Papa.parse(tradesCsv, {
          header: true,
          dynamicTyping: true,
          skipEmptyLines: true,
          complete: (results) => {
            const formattedTrades: Trade[] = results.data.map((row: any) => {
              const d = new Date(row.time_close);
              return {
                id: row.id || `T${Math.random()}`,
                time_open: row.time_open,
                time_close: row.time_close,
                side: row.side,
                entry_price: Number(row.entry_price),
                exit_price: Number(row.exit_price),
                pnl_usd: Number(row.pnl_usd),
                duration_h: Number(row.duration_h),
                filter_date: row.time_close ? String(row.time_close).slice(0, 10) : "",
                filter_weekday: isNaN(d.getDay()) ? 1 : (d.getDay() === 0 ? 7 : d.getDay()),
                filter_hour: isNaN(d.getHours()) ? 0 : d.getHours(),
                filter_side: row.side as "long" | "short"
              };
            });
            setTradesData(formattedTrades);
          }
        });

      } catch (err: any) {
        console.error("Lỗi tải Backtest Detail:", err);
        setError(`⚠️ Không tải được kết quả. Hãy chắc chắn KAIROS Backend đang chạy. (Chi tiết: ${err.message})`);
      } finally {
        setLoading(false);
      }
    };

    if (runId && runId !== "demo") {
        fetchRealData();
    } else {
        setError("Vui lòng chọn một chiến lược cụ thể từ danh sách Backtest để xem báo cáo.");
        setLoading(false);
    }
  }, [runId]);

  const filteredTrades = useMemo(() => {
    let t = tradesData;
    if (dayFilter !== null) t = t.filter(x => x.filter_weekday === dayFilter + 1);
    if (hourFilter !== null) t = t.filter(x => x.filter_hour === hourFilter);
    if (dateFilter) t = t.filter(x => x.filter_date === dateFilter);
    return t;
  }, [tradesData, dayFilter, hourFilter, dateFilter]);

  if (loading) return <div className="flex h-full items-center justify-center p-8"><span className="animate-pulse text-primary">⏳ Đang đọc dữ liệu Artifacts...</span></div>;
  if (error || !run || !run.metrics) return <div className="flex h-full items-center justify-center p-8 text-red-400">❌ Lỗi: {error || "Dữ liệu bị thiếu (Metrics)"}</div>;

  const m = run.metrics;
  const initialCash = run.config?.initial_cash || 1000000;
  const currentEquity = equityData.length > 0 ? equityData[equityData.length - 1].equity : initialCash;
  const totalPnl = currentEquity - initialCash;
  const isProfit = totalPnl >= 0;
  const symbol = run.config?.codes?.[0] || "Unknown";
  const start_date = run.config?.start_date || "";
  const end_date = run.config?.end_date || "";

  const handleExport = () => {
    const rows = ["Mở,Đóng,Hướng,Vào,Ra,PnL (USD),Thời gian (h)"];
    filteredTrades.forEach(t => {
      rows.push(`${String(t.time_open).slice(0, 16)},${String(t.time_close).slice(0, 16)},${t.side},${t.entry_price.toFixed(2)},${t.exit_price.toFixed(2)},${t.pnl_usd.toFixed(2)},${t.duration_h}`);
    });
    const blob = new Blob([rows.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `kairos_backtest_${runId}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex-1 overflow-y-auto bg-background">
      {/* ── Sticky Header ── */}
      <div className="sticky top-0 z-20 bg-background/95 backdrop-blur-sm border-b border-border/40 px-5 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/strategies" className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <h1 className="text-sm font-bold">{run.strategy_name || `Chiến lược ${symbol}`}</h1>
            <div className="text-xs text-muted-foreground flex items-center gap-1.5 mt-0.5">
              <span className={clsx("inline-block w-1.5 h-1.5 rounded-full", run.status === "completed" ? "bg-emerald-500" : "bg-yellow-500")} />
              {start_date} → {end_date} · {run.config?.htf} · {symbol}
            </div>
          </div>
        </div>
        <button
          onClick={handleExport}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
        >
          <Download className="h-3.5 w-3.5" /> Xuất CSV
        </button>
      </div>

      <div className="p-4 space-y-4 max-w-[1600px] mx-auto">
        {/* ── Row 1: KPIs nhanh ── */}
        <div className="grid grid-cols-5 gap-3">
          {[
            { label: "Tổng Lợi Nhuận", value: fmt$(totalPnl), sub: fmtPct(m.total_return || 0), color: isProfit ? "text-emerald-400" : "text-red-400" },
            { label: "Sharpe Ratio", value: Number(m.sharpe_ratio || 0).toFixed(2), sub: Number(m.sharpe_ratio) > 1 ? "Tốt" : "Trung bình", color: Number(m.sharpe_ratio) > 1 ? "text-emerald-400" : "text-yellow-400" },
            { label: "Max Drawdown", value: fmtPct(m.max_drawdown || 0), sub: "Sụt giảm tối đa", color: "text-red-400" },
            { label: "Win Rate", value: `${Number(m.win_rate || 0).toFixed(1)}%`, sub: `${m.total_trades || 0} lệnh`, color: Number(m.win_rate) > 50 ? "text-emerald-400" : "text-red-400" },
            { label: "Profit Factor", value: Number(m.profit_factor || 0).toFixed(2), sub: `R:R ${Number(m.rr_ratio || 0).toFixed(2)}`, color: Number(m.profit_factor) > 1 ? "text-emerald-400" : "text-red-400" },
          ].map(kpi => (
            <div key={kpi.label} className="border border-border/50 rounded-xl p-4 bg-card">
              <div className="text-xs text-muted-foreground mb-1.5">{kpi.label}</div>
              <div className={clsx("text-xl font-bold font-mono", kpi.color)}>{kpi.value}</div>
              <div className="text-xs text-muted-foreground/60 mt-0.5">{kpi.sub}</div>
            </div>
          ))}
        </div>

        {/* ── Row 2: Biểu đồ nến đa khung + Equity ── */}
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-12 lg:col-span-7 border border-border/50 rounded-xl overflow-hidden bg-card">
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/40 bg-muted/20">
              <div className="flex items-center gap-2">
                <CandlestickChart className="h-3.5 w-3.5 text-primary" />
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Biểu đồ Nến · {symbol}
                </span>
              </div>
              <div className="flex gap-1">
                {["15m", "1H", "4H", "1D"].map(tf => (
                  <button
                    key={tf}
                    onClick={() => setActiveTimeframe(tf)}
                    className={clsx(
                      "px-2 py-0.5 rounded text-[11px] font-mono font-medium transition-colors",
                      activeTimeframe === tf ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted"
                    )}
                  >
                    {tf}
                  </button>
                ))}
              </div>
            </div>
            <div className="p-3">
              <MultiTimeframeCandleChart data={[]} timeframe={activeTimeframe} height={320} />
            </div>
          </div>

          <div className="col-span-12 lg:col-span-5 space-y-4">
            <div className="border border-border/50 rounded-xl overflow-hidden bg-card">
              <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border/40 bg-muted/20">
                <TrendingUp className="h-3.5 w-3.5 text-primary" />
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Đường Vốn (Equity Curve)</span>
              </div>
              <div className="p-3">
                <div style={{ height: 220 }}>
                  <EquityCurveChart data={equityData} initialCash={initialCash} />
                </div>
              </div>
            </div>

            <div className="border border-border/50 rounded-xl overflow-hidden bg-card">
              <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border/40 bg-muted/20">
                <Activity className="h-3.5 w-3.5 text-primary" />
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Chỉ Số Chi Tiết</span>
              </div>
              <div className="px-4 py-2">
                <MetricItem label="Kỳ vọng / lệnh" value={fmt$(Number(m.expectancy || 0))} />
                <MetricItem label="Lợi nhuận TB (thắng)" value={fmt$(Number(m.avg_win || 0))} color="text-emerald-500" />
                <MetricItem label="Thua lỗ TB" value={`-${Number(m.avg_loss || 0).toLocaleString("vi-VN", { maximumFractionDigits: 0 })}$`} color="text-red-500" />
                <MetricItem label="Profit Factor" value={Number(m.profit_factor || 0).toFixed(2)} color={Number(m.profit_factor) > 1 ? "text-emerald-500" : "text-red-500"} />
                <MetricItem label="Tổng số lệnh" value={`${m.total_trades || 0}`} />
              </div>
            </div>
          </div>
        </div>

        {/* ── Row 3: Daily PnL + Calendar ── */}
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-12 lg:col-span-8 border border-border/50 rounded-xl overflow-hidden bg-card">
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border/40 bg-muted/20">
              <BarChart2 className="h-3.5 w-3.5 text-primary" />
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">PnL Theo Ngày</span>
            </div>
            <div className="p-4" style={{ height: 200 }}>
              <DailyPnLChart trades={filteredTrades} onDateClick={(date) => setDateFilter(date === dateFilter ? null : date)} selectedDate={dateFilter} />
            </div>
          </div>

          <div className="col-span-12 lg:col-span-4 border border-border/50 rounded-xl overflow-hidden bg-card">
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border/40 bg-muted/20">
              <Calendar className="h-3.5 w-3.5 text-primary" />
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Lịch PnL</span>
            </div>
            <div className="p-4">
              <PnLCalendar trades={tradesData} year={calMonth.year} month={calMonth.month} selectedDate={dateFilter} onDateClick={(date) => setDateFilter(date === dateFilter ? null : date)} onPrevMonth={() => setCalMonth(p => { const m = p.month - 1; return m < 1 ? { year: p.year - 1, month: 12 } : { ...p, month: m }; })} onNextMonth={() => setCalMonth(p => { const m = p.month + 1; return m > 12 ? { year: p.year + 1, month: 1 } : { ...p, month: m }; })} />
            </div>
          </div>
        </div>

        {/* ── Row 4: Phân phối ── */}
        <div className="grid grid-cols-2 gap-4">
          <div className="border border-border/50 rounded-xl overflow-hidden bg-card">
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border/40 bg-muted/20">
              <Layers className="h-3.5 w-3.5 text-primary" />
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">PnL Theo Thứ</span>
            </div>
            <div className="p-4" style={{ height: 160 }}>
              <DistributionChart type="day" trades={tradesData} selectedIndex={dayFilter} onBarClick={(i) => setDayFilter(i === dayFilter ? null : i)} />
            </div>
          </div>

          <div className="border border-border/50 rounded-xl overflow-hidden bg-card">
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border/40 bg-muted/20">
              <Clock className="h-3.5 w-3.5 text-primary" />
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">PnL Theo Giờ</span>
            </div>
            <div className="p-4" style={{ height: 160 }}>
              <DistributionChart type="hour" trades={tradesData} selectedIndex={hourFilter} onBarClick={(i) => setHourFilter(i === hourFilter ? null : i)} />
            </div>
          </div>
        </div>

        {/* ── Row 5: Trade Table ── */}
        <div className="border border-border/50 rounded-xl overflow-hidden bg-card">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/40 bg-muted/20">
            <div className="flex items-center gap-2">
              <TrendingDown className="h-3.5 w-3.5 text-primary" />
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Danh Sách Lệnh ({filteredTrades.length} {filteredTrades.length < tradesData.length ? ` / ${tradesData.length} đã lọc` : ""})
              </span>
            </div>
            {(dayFilter !== null || hourFilter !== null || dateFilter) && (
              <div className="flex items-center gap-2">
                {dayFilter !== null && <span onClick={() => setDayFilter(null)} className="px-2 py-0.5 rounded bg-primary/10 text-primary text-xs cursor-pointer hover:bg-primary/20">{["T2","T3","T4","T5","T6","T7","CN"][dayFilter]} ✕</span>}
                {hourFilter !== null && <span onClick={() => setHourFilter(null)} className="px-2 py-0.5 rounded bg-primary/10 text-primary text-xs cursor-pointer hover:bg-primary/20">{hourFilter}h ✕</span>}
                {dateFilter && <span onClick={() => setDateFilter(null)} className="px-2 py-0.5 rounded bg-primary/10 text-primary text-xs cursor-pointer hover:bg-primary/20">{dateFilter} ✕</span>}
                <button onClick={() => { setDayFilter(null); setHourFilter(null); setDateFilter(null); }} className="text-xs text-muted-foreground hover:text-foreground">Xoá hết bộ lọc</button>
              </div>
            )}
          </div>
          <div className="p-4">
            <TradeTable trades={filteredTrades} />
          </div>
        </div>
      </div>
    </div>
  );
}