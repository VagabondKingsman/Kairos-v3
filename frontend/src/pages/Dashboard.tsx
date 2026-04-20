import { Link } from "react-router-dom";
import { BrainCircuit, TrendingUp, TrendingDown, Activity, BarChart3, ArrowRight } from "lucide-react";
import { clsx } from "clsx";

// ── Mock regime data ──────────────────────────────────────────────────────────
const REGIME = { state_id: 3, state_name: "XU_HUONG_MANH", confidence: 0.87 };
const REGIME_META: Record<string, { label: string; color: string; action: string }> = {
  DONG_BANG:    { label: "Đóng Băng",      color: "text-muted-foreground", action: "Đứng ngoài tuyệt đối" },
  NEN_CHAT:     { label: "Nén Chặt",       color: "text-warning",           action: "Canh Breakout" },
  DAU_XU_HUONG: { label: "Đầu Xu Hướng",  color: "text-info",              action: "Vào lệnh sớm" },
  XU_HUONG_MANH:{ label: "Xu Hướng Mạnh", color: "text-success",           action: "Follow Trend" },
  CAO_TRAO:     { label: "Cao Trào",       color: "text-warning",           action: "Scale out / Chốt lời" },
  HOI_QUY:      { label: "Hồi Quy",        color: "text-info",              action: "Counter-trend" },
  NHIEU_DONG:   { label: "Nhiễu Động",     color: "text-muted-foreground",  action: "Đánh Range hoặc nghỉ" },
  DAO_CHIEU:    { label: "Đảo Chiều",      color: "text-danger",            action: "Canh đảo chiều" },
};

const PORTFOLIO = [
  { label: "Tổng vốn",    value: "1,287,450$",  delta: "+28.7%",  pos: true },
  { label: "PnL hôm nay", value: "+3,240$",      delta: "+0.25%",  pos: true },
  { label: "Win Rate",    value: "61.2%",         delta: "+2.1%",   pos: true },
  { label: "Max Drawdown",value: "-9.4%",         delta: "",        pos: false },
];

const ML_MODULES = [
  { key: "trang_thai", label: "Chế Độ TT",  trained: true,  accuracy: 0.84 },
  { key: "du_bao_gia", label: "Dự Báo Giá", trained: false, accuracy: null },
  { key: "bat_thuong", label: "Bất Thường",  trained: true,  accuracy: 0.91 },
  { key: "cho_diem",   label: "Chấm Điểm",  trained: false, accuracy: null },
  { key: "phan_loai_nen", label: "Phân Loại Nến", trained: false, accuracy: null },
  { key: "danh_muc",   label: "Tối Ưu DM",  trained: true,  accuracy: null },
];

const RECENT_RUNS = [
  { id: "bt001", name: "SMC + ML (BTC 1H)",   date: "17/04",  ret: "+14.2%", pos: true  },
  { id: "bt002", name: "Ichimoku D1 (ETH)",   date: "16/04",  ret: "+8.7%",  pos: true  },
  { id: "bt003", name: "EMA Cross (SSI.VN)",  date: "15/04",  ret: "-3.1%",  pos: false },
];

function StatCard({ label, value, delta, pos }: { label: string; value: string; delta: string; pos: boolean }) {
  return (
    <div className="card-kairos p-4">
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      <div className={clsx("text-2xl font-bold font-mono", pos ? "text-success" : "text-danger")}>{value}</div>
      {delta && <div className={clsx("text-xs mt-0.5", pos ? "text-success/70" : "text-danger/70")}>{delta}</div>}
    </div>
  );
}

export function Dashboard() {
  const regime = REGIME_META[REGIME.state_name] ?? REGIME_META["DONG_BANG"];

  return (
    <div className="flex-1 overflow-auto">
      <div className="p-5 space-y-4 max-w-[1400px] mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Bảng Điều Khiển</h2>
          <div className="text-xs text-muted-foreground">{new Date().toLocaleString("vi-VN")}</div>
        </div>

        {/* Row 1: Portfolio stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {PORTFOLIO.map(p => <StatCard key={p.label} {...p} />)}
        </div>

        {/* Row 2: Regime + ML status */}
        <div className="grid grid-cols-12 gap-4">
          {/* Regime card */}
          <div className="col-span-12 md:col-span-4 card-kairos p-4">
            <div className="flex items-center gap-2 mb-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              <BrainCircuit className="h-4 w-4 text-primary" /> Chế Độ Thị Trường (ML)
            </div>
            <div className={clsx("text-3xl font-bold mb-1", regime.color)}>{regime.label}</div>
            <div className="text-xs text-muted-foreground mb-3">Độ tự tin: <span className="text-foreground font-mono">{(REGIME.confidence * 100).toFixed(0)}%</span></div>
            <div className="flex items-center gap-2 px-3 py-2 rounded-md bg-muted/50">
              <Activity className="h-3.5 w-3.5 text-primary" />
              <span className="text-xs">{regime.action}</span>
            </div>
            {/* Confidence bar */}
            <div className="mt-3 h-1.5 rounded-full bg-muted overflow-hidden">
              <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${REGIME.confidence * 100}%` }} />
            </div>
          </div>

          {/* ML modules grid */}
          <div className="col-span-12 md:col-span-8 card-kairos p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                <BrainCircuit className="h-4 w-4 text-primary" /> 6 Module ML (a07)
              </div>
              <Link to="/ml" className="text-xs text-primary hover:underline flex items-center gap-1">
                Quản lý <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {ML_MODULES.map(m => (
                <div key={m.key} className="flex items-center gap-2 px-3 py-2 rounded-md bg-muted/40">
                  <div className={clsx("w-2 h-2 rounded-full shrink-0", m.trained ? "bg-success" : "bg-muted-foreground/40")} />
                  <div className="min-w-0">
                    <div className="text-xs font-medium truncate">{m.label}</div>
                    <div className="text-[10px] text-muted-foreground">
                      {m.trained ? (m.accuracy ? `Acc: ${(m.accuracy*100).toFixed(0)}%` : "Đã train") : "Chưa train"}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Row 3: Recent backtests */}
        <div className="card-kairos p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-primary" /> Backtest Gần Đây
            </div>
            <Link to="/strategies" className="text-xs text-primary hover:underline flex items-center gap-1">
              Tất cả <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="space-y-2">
            {RECENT_RUNS.map(r => (
              <Link key={r.id} to={`/backtest/${r.id}`}
                className="flex items-center justify-between px-3 py-2.5 rounded-md bg-muted/30 hover:bg-muted/60 transition-colors">
                <div className="flex items-center gap-3">
                  {r.pos ? <TrendingUp className="h-4 w-4 text-success shrink-0" /> : <TrendingDown className="h-4 w-4 text-danger shrink-0" />}
                  <div>
                    <div className="text-xs font-medium">{r.name}</div>
                    <div className="text-[10px] text-muted-foreground">{r.date}</div>
                  </div>
                </div>
                <span className={clsx("text-sm font-bold font-mono", r.pos ? "text-success" : "text-danger")}>{r.ret}</span>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
