import { useState, useEffect, useRef, useCallback } from "react";
import {
  Play, Square, Activity, Cpu, Terminal as TerminalIcon,
  TrendingUp, TrendingDown, Zap, RefreshCw,
  DollarSign, BarChart2, Clock
} from "lucide-react";
import { clsx } from "clsx";

const API = "";

interface EngineStatus {
  is_running: boolean;
  mode: string;
  exchange: string;
  start_time: number | null;
  uptime_s: number;
  strategy_ids: string[];
  open_positions: number;
  total_trades: number;
  equity: number;
  initial_equity: number;
  total_pnl_usd: number;
  total_pnl_pct: number;
  unrealized_pnl: number;
}

interface Position {
  id: string;
  symbol: string;
  strategy_id: string;
  strategy_name: string;
  side: "LONG" | "SHORT";
  entry_price: number;
  current_price?: number;
  qty: number;
  size_usd: number;
  sl_price: number;
  tp_price: number;
  open_time: string;
  unrealized_pnl: number;
}

interface ClosedTrade extends Position {
  exit_price: number;
  pnl_usd: number;
  pnl_pct: number;
  close_time: string;
  status: string;
}

interface LogEntry {
  id: string;
  time: string;
  ts: number;
  level: "INFO" | "WARNING" | "ERROR" | "SUCCESS";
  message: string;
}

function formatUptime(seconds: number): string {
  if (!seconds) return "—";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

export function Execution() {
  const [status, setStatus] = useState<EngineStatus>({
    is_running: false, mode: "DEMO", exchange: "OKX",
    start_time: null, uptime_s: 0, strategy_ids: [],
    open_positions: 0, total_trades: 0, equity: 10000,
    initial_equity: 10000, total_pnl_usd: 0, total_pnl_pct: 0, unrealized_pnl: 0,
  });
  const [positions, setPositions] = useState<Position[]>([]);
  const [closedTrades, setClosedTrades] = useState<ClosedTrade[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<"positions" | "history">("positions");
  const [mode, setMode] = useState("DEMO");
  const [exchange, setExchange] = useState("OKX");
  const logRef = useRef<HTMLDivElement>(null);
  const lastLogTs = useRef<number>(0);

  const fetchAll = useCallback(async () => {
    try {
      const [statusRes, posRes, logRes] = await Promise.all([
        fetch(`${API}/api/engine/status`),
        fetch(`${API}/api/engine/positions`),
        fetch(`${API}/api/engine/logs?limit=150`),
      ]);
      if (statusRes.ok) setStatus(await statusRes.json());
      if (posRes.ok) {
        const d = await posRes.json();
        setPositions(d.positions || []);
        setClosedTrades(d.closed_trades || []);
      }
      if (logRes.ok) {
        const d = await logRes.json();
        const newLogs: LogEntry[] = (d.logs || []).filter((l: LogEntry) => l.ts > lastLogTs.current);
        if (newLogs.length > 0) {
          lastLogTs.current = newLogs[newLogs.length - 1].ts;
          setLogs(prev => [...prev, ...newLogs].slice(-200));
        }
      }
    } catch (e) {
      console.error("Engine fetch error:", e);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const iv = setInterval(fetchAll, 5000);
    return () => clearInterval(iv);
  }, [fetchAll]);

  // Auto-scroll terminal
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);

  const handleStart = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/engine/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode, exchange }),
      });
      if (res.ok) await fetchAll();
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await fetch(`${API}/api/engine/stop`, { method: "POST" });
      await fetchAll();
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const equityPct = ((status.equity - status.initial_equity) / status.initial_equity) * 100;

  return (
    <div className="flex flex-col h-full bg-background overflow-hidden">
      {/* ── Header ── */}
      <div className="border-b border-border/40 px-5 py-3 shrink-0 flex justify-between items-center bg-card">
        <div className="flex items-center gap-3">
          <div className={clsx(
            "w-2.5 h-2.5 rounded-full",
            status.is_running ? "bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.6)]" : "bg-zinc-600"
          )} />
          <div>
            <h1 className="text-base font-bold flex items-center gap-2">
              <Cpu className="h-4 w-4 text-primary" /> Động Cơ Thực Thi (A10)
              <span className={clsx("text-[11px] px-2 py-0.5 rounded-full font-mono border",
                status.is_running
                  ? "border-emerald-500/40 text-emerald-400 bg-emerald-500/10"
                  : "border-zinc-600/40 text-zinc-500 bg-zinc-800/20"
              )}>
                {status.is_running ? `● RUNNING · ${status.mode}` : "○ STOPPED"}
              </span>
            </h1>
            <p className="text-xs text-muted-foreground">
              {status.is_running
                ? `Uptime: ${formatUptime(status.uptime_s)} · ${status.strategy_ids.length} chiến lược · ${status.open_positions} vị thế`
                : "Cấu hình và bật engine để bắt đầu paper trading"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={fetchAll} className="p-2 rounded-lg border border-border hover:bg-muted transition-colors">
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
          {!status.is_running ? (
            <button onClick={handleStart} disabled={loading}
              className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50">
              <Play className="h-4 w-4" /> BẮT ĐẦU
            </button>
          ) : (
            <button onClick={handleStop} disabled={loading}
              className="flex items-center gap-2 bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50">
              <Square className="h-4 w-4" /> DỪNG
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* ── Left Sidebar ── */}
        <div className="w-72 shrink-0 border-r border-border/40 bg-card/30 flex flex-col gap-0 overflow-y-auto">

          {/* Config */}
          <div className="p-4 border-b border-border/40 space-y-3">
            <h2 className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5" /> Cấu hình Engine
            </h2>
            <div>
              <label className="text-xs text-muted-foreground mb-1.5 block">Chế Độ Thực Thi</label>
              <select disabled={status.is_running} value={mode} onChange={e => setMode(e.target.value)}
                className="w-full bg-background border border-border rounded-md p-2 text-sm outline-none focus:border-primary disabled:opacity-50">
                <option value="DEMO">🧪 Demo (Paper Trading)</option>
                <option value="LIVE">⚡ Live (Real Money)</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1.5 block">Adapter A13 (Sàn)</label>
              <select disabled={status.is_running} value={exchange} onChange={e => setExchange(e.target.value)}
                className="w-full bg-background border border-border rounded-md p-2 text-sm outline-none focus:border-primary disabled:opacity-50">
                <option value="OKX">OKX (Crypto)</option>
                <option value="CCXT">CCXT Đa Sàn</option>
                <option value="VNSTOCK">Chứng Khoán VN</option>
                <option value="YFINANCE">Global Stocks</option>
              </select>
            </div>
          </div>

          {/* Portfolio Stats */}
          <div className="p-4 border-b border-border/40 space-y-3">
            <h2 className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <DollarSign className="h-3.5 w-3.5" /> Portfolio (Paper)
            </h2>
            <div className="bg-background rounded-xl p-3.5 border border-border/60">
              <div className="text-[11px] text-muted-foreground mb-1">Tổng Equity</div>
              <div className="text-2xl font-mono font-bold">${status.equity.toLocaleString("en", {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
              <div className={clsx("text-xs mt-1 flex items-center gap-1", equityPct >= 0 ? "text-emerald-500" : "text-red-500")}>
                {equityPct >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                {equityPct >= 0 ? "+" : ""}{equityPct.toFixed(2)}% tổng
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              {[
                { label: "PnL Thực", value: `${status.total_pnl_usd >= 0 ? "+" : ""}$${status.total_pnl_usd.toFixed(0)}`, color: status.total_pnl_usd >= 0 ? "text-emerald-500" : "text-red-500" },
                { label: "Chưa chốt", value: `${status.unrealized_pnl >= 0 ? "+" : ""}$${status.unrealized_pnl.toFixed(0)}`, color: status.unrealized_pnl >= 0 ? "text-blue-400" : "text-orange-400" },
                { label: "Vị thế mở", value: status.open_positions.toString(), color: "text-foreground" },
                { label: "Tổng lệnh", value: status.total_trades.toString(), color: "text-foreground" },
              ].map(item => (
                <div key={item.label} className="bg-muted/30 rounded-lg p-2.5 border border-border/40">
                  <div className="text-[10px] text-muted-foreground mb-0.5">{item.label}</div>
                  <div className={clsx("text-sm font-bold font-mono", item.color)}>{item.value}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Active Strategies */}
          <div className="p-4 space-y-2">
            <h2 className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Zap className="h-3.5 w-3.5" /> Chiến lược đang chạy
            </h2>
            {status.strategy_ids.length === 0 ? (
              <p className="text-xs text-muted-foreground italic">Chưa có chiến lược nào.</p>
            ) : (
              status.strategy_ids.map(id => (
                <div key={id} className="flex items-center gap-2 py-1.5 px-2.5 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                  <span className="text-xs font-mono text-emerald-400 truncate">{id}</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* ── Main Content ── */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Tabs */}
          <div className="border-b border-border/40 px-4 shrink-0 flex gap-0 bg-card/20">
            {(["positions", "history"] as const).map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={clsx("px-4 py-2.5 text-xs font-medium border-b-2 transition-colors",
                  tab === t ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"
                )}>
                {t === "positions" ? `📊 Vị Thế Mở (${positions.length})` : `📋 Lịch Sử (${closedTrades.length})`}
              </button>
            ))}
          </div>

          {/* Positions / History Table */}
          <div className="flex-[2] overflow-y-auto border-b border-border/40">
            {tab === "positions" ? (
              positions.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
                  <BarChart2 className="h-8 w-8 opacity-20" />
                  <p className="text-sm">{status.is_running ? "Đang quét tín hiệu... Chưa có vị thế nào." : "Engine chưa chạy."}</p>
                </div>
              ) : (
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-card border-b border-border/40">
                    <tr>
                      {["Symbol", "Strategy", "Side", "Entry", "Current", "Size", "TP / SL", "Unrealized PnL", "Mở lúc"].map(h => (
                        <th key={h} className="px-3 py-2.5 text-left text-muted-foreground font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map(p => {
                      const pnlPos = p.unrealized_pnl >= 0;
                      return (
                        <tr key={p.id} className="border-b border-border/20 hover:bg-muted/20 transition-colors">
                          <td className="px-3 py-2.5 font-mono font-bold text-foreground">{p.symbol}</td>
                          <td className="px-3 py-2.5 text-muted-foreground max-w-[120px] truncate">{p.strategy_name}</td>
                          <td className="px-3 py-2.5">
                            <span className={clsx("px-1.5 py-0.5 rounded text-[10px] font-bold",
                              p.side === "LONG" ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400"
                            )}>{p.side}</span>
                          </td>
                          <td className="px-3 py-2.5 font-mono">${p.entry_price.toLocaleString()}</td>
                          <td className="px-3 py-2.5 font-mono">${(p.current_price ?? p.entry_price).toLocaleString()}</td>
                          <td className="px-3 py-2.5 font-mono">${p.size_usd.toFixed(0)}</td>
                          <td className="px-3 py-2.5 font-mono text-[11px]">
                            <span className="text-emerald-400">${p.tp_price.toFixed(0)}</span>
                            <span className="text-muted-foreground"> / </span>
                            <span className="text-red-400">${p.sl_price.toFixed(0)}</span>
                          </td>
                          <td className={clsx("px-3 py-2.5 font-mono font-bold", pnlPos ? "text-emerald-400" : "text-red-400")}>
                            {pnlPos ? "+" : ""}{p.unrealized_pnl.toFixed(2)}$
                          </td>
                          <td className="px-3 py-2.5 text-muted-foreground">{p.open_time.split("T")[1]}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )
            ) : (
              closedTrades.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
                  <Clock className="h-8 w-8 opacity-20" />
                  <p className="text-sm">Chưa có lệnh nào được đóng.</p>
                </div>
              ) : (
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-card border-b border-border/40">
                    <tr>
                      {["Symbol", "Strategy", "Entry", "Exit", "PnL (USD)", "PnL (%)", "Đóng lúc"].map(h => (
                        <th key={h} className="px-3 py-2.5 text-left text-muted-foreground font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[...closedTrades].reverse().map(t => {
                      const pnlPos = t.pnl_usd >= 0;
                      return (
                        <tr key={t.id} className="border-b border-border/20 hover:bg-muted/20 transition-colors">
                          <td className="px-3 py-2.5 font-mono font-bold">{t.symbol}</td>
                          <td className="px-3 py-2.5 text-muted-foreground max-w-[120px] truncate">{t.strategy_name}</td>
                          <td className="px-3 py-2.5 font-mono">${t.entry_price.toLocaleString()}</td>
                          <td className="px-3 py-2.5 font-mono">${t.exit_price?.toLocaleString()}</td>
                          <td className={clsx("px-3 py-2.5 font-mono font-bold", pnlPos ? "text-emerald-400" : "text-red-400")}>
                            {pnlPos ? "+" : ""}{t.pnl_usd?.toFixed(2)}$
                          </td>
                          <td className={clsx("px-3 py-2.5 font-mono", pnlPos ? "text-emerald-400" : "text-red-400")}>
                            {pnlPos ? "+" : ""}{t.pnl_pct?.toFixed(2)}%
                          </td>
                          <td className="px-3 py-2.5 text-muted-foreground">{t.close_time?.split("T")[1]}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )
            )}
          </div>

          {/* ── Terminal Log ── */}
          <div className="flex-1 bg-[#0D1117] flex flex-col min-h-[180px]">
            <div className="h-8 shrink-0 bg-[#161B22] border-b border-[#30363D] flex items-center px-4 gap-2">
              <TerminalIcon className="h-3.5 w-3.5 text-gray-500" />
              <span className="text-[11px] font-mono text-gray-500">kairos-engine.log</span>
              <span className="ml-auto text-[10px] text-gray-600">{logs.length} entries</span>
            </div>
            <div ref={logRef} className="flex-1 p-3 overflow-y-auto font-mono text-[12px] space-y-0.5">
              {logs.length === 0 ? (
                <span className="text-gray-600 italic">Chưa có log. Bật Engine để bắt đầu...</span>
              ) : logs.map(log => {
                const colors: Record<string, string> = {
                  SUCCESS: "text-emerald-400", WARNING: "text-yellow-400",
                  ERROR: "text-red-400", INFO: "text-gray-300"
                };
                const icons: Record<string, string> = {
                  SUCCESS: "✓", WARNING: "⚠", ERROR: "✗", INFO: "·"
                };
                return (
                  <div key={log.id} className="flex gap-2.5 hover:bg-white/[0.03] px-1 py-0.5 rounded">
                    <span className="text-gray-600 shrink-0">[{log.time}]</span>
                    <span className={clsx("shrink-0", colors[log.level])}>{icons[log.level]}</span>
                    <span className={colors[log.level]}>{log.message}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
