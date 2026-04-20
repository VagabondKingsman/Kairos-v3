import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  BarChart3, TrendingUp, TrendingDown, Trash2,
  BotMessageSquare, X, Send, Loader2, Plus, ChevronRight,
  Sparkles, Eye, Code2, Settings2, Info, Rocket
} from "lucide-react";
import { clsx } from "clsx";

const API = "";

interface Strategy {
  id: string; name: string; description: string; htf: string;
  codes: string[]; last_return: number; sharpe: number; max_drawdown: number; win_rate: number;
  tags: string[]; mode: string; exchange: string;
  params: Record<string, any>;
  description_detail: string;
  backtest_mode: string;
  created_at: string;
}

interface Message { role: "user" | "ai"; text: string; }

// ─── Strategy Detail Modal ─────────────────────────────────────────────────
function StrategyDetailModal({ strategy, onClose }: { strategy: Strategy; onClose: () => void }) {
  const [tab, setTab] = useState<"info" | "params" | "code">("info");
  const [pythonCode, setPythonCode] = useState<string | null>(null);
  const [loadingCode, setLoadingCode] = useState(false);

  const fetchCode = async () => {
    if (pythonCode !== null) return; // đã load rồi
    setLoadingCode(true);
    try {
      const res = await fetch(`/api/strategies/${strategy.id}/code`);
      if (res.ok) {
        const data = await res.json();
        setPythonCode(data.code || "# Không có mã nguồn Python cho chiến lược này.");
      } else {
        setPythonCode("# Chiến lược này chưa có file code Python.\n# Hãy tạo chiến lược mới từ AI để có mã nguồn tự động.");
      }
    } catch {
      setPythonCode("# Không thể tải mã nguồn. Vui lòng kiểm tra kết nối Backend.");
    } finally {
      setLoadingCode(false);
    }
  };

  const modeInfo = {
    B2B: {
      label: "Backtest Bar-to-Bar (B2B)",
      color: "text-blue-400",
      bg: "bg-blue-500/10 border-blue-500/30",
      desc: "Mô phỏng giao dịch trên dữ liệu lịch sử bằng cách duyệt từng nến (bar) một theo thứ tự thời gian. Chiến lược chỉ \"thấy\" dữ liệu của nến hiện tại và những nến trước đó — giống hệt như khi chạy thật.",
      steps: [
        "Tải OHLCV lịch sử từ A01 (OKX/VNStock/...)",
        "Vòng lặp for qua từng nến: bar₀ → bar₁ → ... → barₙ",
        "Tại mỗi nến: chạy hàm chiến lược → sinh tín hiệu BUY/SELL/HOLD",
        "Bộ lọc A03 bị BỎ QUA để đo sức mạnh thô của logic",
        "Executor ảo ghi nhận lệnh, tính PnL, cập nhật equity curve",
        "Xuất kết quả: Sharpe, Drawdown, Win Rate, Trade log",
      ]
    },
    DEMO: {
      label: "Demo (Paper Trading)",
      color: "text-emerald-400",
      bg: "bg-emerald-500/10 border-emerald-500/30",
      desc: "Kết nối với sàn thật qua A13, nhận dữ liệu giá thời gian thực, nhưng đặt lệnh trên tài khoản Demo/Paper — không dùng tiền thật. Bộ lọc A03 BẮT BUỘC hoạt động.",
      steps: [
        "A01 lấy giá real-time từ sàn (OKX/CCXT...)",
        "Chiến lược chạy trên nến mới đóng (bar close)",
        "Tín hiệu đi qua A03: nếu thị trường BAD STATE → BLOCK",
        "A13 gửi lệnh tới tài khoản Paper của sàn",
        "Theo dõi vị thế, PnL trong Execution Terminal",
      ]
    },
    LIVE: {
      label: "Live (Real Money)",
      color: "text-red-400",
      bg: "bg-red-500/10 border-red-500/30",
      desc: "Giao dịch TIỀN THẬT. Mọi lệnh đều ảnh hưởng tài khoản thực. A03 hoạt động nâng cao: điều chỉnh động khối lượng và stoploss dựa trên trạng thái thị trường.",
      steps: [
        "Yêu cầu API Key thật với quyền TRADE",
        "A03 phân tích regime → tính Dynamic Volume & SL",
        "A12 kiểm tra: Max DD limit, Max Open Positions",
        "A13 đặt lệnh thị trường/giới hạn lên sàn thật",
        "Giám sát liên tục, cắt lệnh khẩn nếu vượt rủi ro",
      ]
    }
  };

  const modeMeta = modeInfo[strategy.backtest_mode as keyof typeof modeInfo] ?? modeInfo.B2B;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-card border border-border rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-border/50">
          <div>
            <h2 className="font-bold text-base">{strategy.name}</h2>
            <p className="text-xs text-muted-foreground mt-0.5">{strategy.description}</p>
            <p className="text-[10px] text-primary/80 mt-1">{modeMeta.label}</p>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-muted rounded-lg transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border/50">
          {[
            { key: "info", label: "Tổng quan", icon: Info },
            { key: "params", label: "Thông số", icon: Settings2 },
            { key: "code", label: "Code Python", icon: Code2 },
          ].map(({ key, label, icon: Icon }) => (
            <button key={key} onClick={() => { setTab(key as any); if (key === "code") fetchCode(); }}
              className={clsx("flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors",
                tab === key ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"
              )}>
              <Icon className="h-3.5 w-3.5" />{label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5">
          {tab === "info" && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground leading-relaxed">{strategy.description_detail}</p>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: "Khung thời gian", value: strategy.htf },
                  { label: "Sàn giao dịch", value: strategy.exchange },
                  { label: "Chế độ mặc định", value: strategy.mode },
                  { label: "Ngày tạo", value: strategy.created_at?.slice(0, 10) },
                ].map(row => (
                  <div key={row.label} className="bg-muted/30 rounded-lg p-3">
                    <div className="text-[10px] text-muted-foreground mb-1">{row.label}</div>
                    <div className="text-sm font-semibold">{row.value}</div>
                  </div>
                ))}
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-2">Cặp giao dịch</div>
                <div className="flex flex-wrap gap-1.5">
                  {(strategy.codes || []).map(c => (
                    <span key={c} className="px-2.5 py-1 rounded-full bg-primary/10 text-primary text-xs font-mono">{c}</span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {tab === "params" && (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground mb-3">Thông số kỹ thuật hiện tại của chiến lược (có thể chỉnh trong Cài đặt).</p>
              {Object.entries(strategy.params ?? {}).map(([key, val]) => (
                <div key={key} className="flex items-center justify-between py-2 border-b border-border/30">
                  <span className="text-xs font-mono text-muted-foreground">{key}</span>
                  <span className="text-sm font-semibold font-mono">{String(val)}</span>
                </div>
              ))}
            </div>
          )}

          {tab === "code" && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground">Mã nguồn Python được AI sinh ra và lưu tại <code className="text-primary">a04_kho_chien_luoc_va_kiem_thu/ky_nang_chien_luoc/{strategy.id}.py</code></p>
              </div>
              {loadingCode ? (
                <div className="flex items-center gap-2 py-8 justify-center text-muted-foreground text-sm">
                  <Loader2 className="h-4 w-4 animate-spin" /> Đang tải code...
                </div>
              ) : (
                <div className="relative group">
                  <pre className="bg-[#0D1117] border border-[#30363D] rounded-xl p-4 overflow-x-auto overflow-y-auto max-h-[50vh] text-[12px] font-mono text-[#e6edf3] leading-relaxed whitespace-pre">
                    <code>{pythonCode}</code>
                  </pre>
                  <button
                    onClick={() => navigator.clipboard.writeText(pythonCode ?? "")}
                    className="absolute top-2.5 right-2.5 opacity-0 group-hover:opacity-100 transition-opacity px-2.5 py-1 rounded-md bg-[#21262d] border border-[#30363D] text-[11px] text-[#8b949e] hover:text-white hover:bg-[#30363d] transition-colors"
                  >
                    Copy
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border/50 flex gap-2 justify-end">
          <Link to={`/backtest/${strategy.id}`} onClick={onClose}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm hover:bg-primary/90 transition-colors">
            <BarChart3 className="h-4 w-4" /> Xem Kết Quả Backtest
          </Link>
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────────────
export function Strategies() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [detailStrategy, setDetailStrategy] = useState<Strategy | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deployingId, setDeployingId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    { role: "ai", text: "Xin chào! Tôi là KAIROS AI. Hãy mô tả chiến lược bạn muốn tạo — ví dụ: *'EMA 20/50 trên BTC khung 1H, stoploss 1.5%'*" }
  ]);
  const [input, setInput] = useState("");
  const [aiLoading, setAiLoading] = useState(false);

  // Load từ API, fallback localStorage
  const fetchStrategies = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/strategies`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      setStrategies(data);
      localStorage.setItem("kairos_strategies", JSON.stringify(data));
      setApiError(false);
    } catch {
      setApiError(true);
      const cached = localStorage.getItem("kairos_strategies");
      if (cached) setStrategies(JSON.parse(cached));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchStrategies(); }, [fetchStrategies]);

  const handleDelete = async (id: string) => {
    setDeleteId(null); // đóng modal ngay
    try {
      const res = await fetch(`${API}/api/strategies/${id}`, { method: "DELETE" });
      if (res.ok) {
        // Thành công: cập nhật UI ngay lập tức
        const updated = strategies.filter(s => s.id !== id);
        setStrategies(updated);
        localStorage.setItem("kairos_strategies", JSON.stringify(updated));
        // Đồng bộ lại từ server để chắc chắn
        setTimeout(() => fetchStrategies(), 300);
      } else {
        // Server trả lỗi - thử xóa trong localStorage
        const updated = strategies.filter(s => s.id !== id);
        setStrategies(updated);
        localStorage.setItem("kairos_strategies", JSON.stringify(updated));
        alert(`Không thể xóa trên server (lỗi ${res.status}). Đã xóa cục bộ.`);
      }
    } catch {
      // Offline: chỉ xóa trong local state
      const updated = strategies.filter(s => s.id !== id);
      setStrategies(updated);
      localStorage.setItem("kairos_strategies", JSON.stringify(updated));
    }
  };

  const handleDeploy = async (id: string) => {
    setDeployingId(id);
    try {
      const res = await fetch(`${API}/api/engine/deploy/${id}`, { method: "POST" });
      if (res.ok) {
        // Toast-like notification via title
        const btn = document.getElementById(`deploy-btn-${id}`);
        if (btn) { btn.textContent = "✓ Đã Deploy!"; setTimeout(() => { if (btn) btn.textContent = "Deploy"; }, 2000); }
      }
    } catch {}
    finally { setDeployingId(null); }
  };

  const handleSendMessage = async () => {
    if (!input.trim() || aiLoading) return;
    const userMsg = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", text: userMsg }]);
    setAiLoading(true);
    setTimeout(() => {
      setMessages(prev => [...prev, {
        role: "ai",
        text: `Tôi đã phân tích yêu cầu của bạn:\n\n**Tên đề xuất:** ${userMsg.slice(0, 40)}...\n**Tín hiệu:** Dựa theo yêu cầu\n**Rủi ro:** 1–2% mỗi lệnh\n**Chế độ:** Demo trước khi Live\n\nBạn có muốn tôi sinh file code chiến lược vào kho A04 không?`
      }]);
      setAiLoading(false);
    }, 1500);
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin mr-2" /> Đang tải chiến lược...
      </div>
    );
  }

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* ── Strategy List ── */}
      <div className={clsx("flex flex-col transition-all duration-300", showChat ? "w-[55%] border-r border-border/50" : "w-full")}>
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-border/40 bg-card/30 shrink-0">
          <div>
            <h1 className="text-base font-bold">Kho Chiến Lược</h1>
            <p className="text-xs text-muted-foreground">
              {strategies.length} chiến lược
              {apiError && <span className="ml-2 text-yellow-500">· Offline (localStorage)</span>}
            </p>
          </div>
          <button onClick={() => setShowChat(v => !v)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-all">
            <Sparkles className="h-3.5 w-3.5" />
            {showChat ? "Đóng AI" : "Tạo chiến lược (AI)"}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {strategies.map(s => {
            const isPos = s.last_return >= 0;
            return (
              <div key={s.id} className="group border border-border/50 rounded-xl p-4 bg-card hover:border-primary/30 transition-all">
                <div className="flex items-start gap-3">
                  <div className={clsx("w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5",
                    isPos ? "bg-emerald-500/10" : "bg-red-500/10")}>
                    {isPos ? <TrendingUp className="h-5 w-5 text-emerald-500" /> : <TrendingDown className="h-5 w-5 text-red-500" />}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="font-semibold text-sm">{s.name}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground font-mono">{s.htf || "1D"}</span>
                      <span className={clsx("text-[9px] px-1.5 py-0.5 rounded border font-mono",
                        s.mode === "LIVE" ? "border-red-500/50 text-red-400" :
                        s.mode === "DEMO" ? "border-emerald-500/50 text-emerald-400" :
                        "border-blue-500/50 text-blue-400"
                      )}>{s.mode || s.backtest_mode || "B2B"}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mb-2">{s.description}</p>
                    <div className="flex flex-wrap gap-1 mb-2.5">
                      {(s.codes || []).map(c => <span key={c} className="text-[10px] px-2 py-0.5 rounded-full border border-border text-muted-foreground">{c}</span>)}
                      {(s.tags || []).map(t => <span key={t} className="text-[10px] px-2 py-0.5 rounded-full bg-primary/10 text-primary">{t}</span>)}
                    </div>
                    <div className="grid grid-cols-4 gap-2">
                      {[
                        { l: "Lợi nhuận", v: `${isPos ? "+" : ""}${s.last_return ?? 0}%`, c: isPos ? "text-emerald-500" : "text-red-500" },
                        { l: "Sharpe", v: (s.sharpe ?? 0).toString(), c: (s.sharpe ?? 0) > 1 ? "text-emerald-500" : "text-yellow-500" },
                        { l: "Max DD", v: `${s.max_drawdown ?? 0}%`, c: "text-red-500" },
                        { l: "Win Rate", v: `${s.win_rate ?? 0}%`, c: (s.win_rate ?? 0) > 50 ? "text-emerald-500" : "text-red-500" },
                      ].map(m => (
                        <div key={m.l} className="bg-muted/40 rounded-lg p-2 text-center">
                          <div className="text-[10px] text-muted-foreground mb-0.5">{m.l}</div>
                          <div className={clsx("text-sm font-bold font-mono", m.c)}>{m.v}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="shrink-0 flex flex-col gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onClick={() => setDetailStrategy(s)}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border border-border text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
                      <Eye className="h-3.5 w-3.5" /> Chi tiết
                    </button>
                    <Link to={`/backtest/${s.id}`}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-primary/10 text-primary text-xs hover:bg-primary/20 transition-colors">
                      <BarChart3 className="h-3.5 w-3.5" /> Backtest
                    </Link>
                    <button id={`deploy-btn-${s.id}`} onClick={() => handleDeploy(s.id)}
                      disabled={deployingId === s.id}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-emerald-500/10 text-emerald-500 text-xs hover:bg-emerald-500/20 transition-colors disabled:opacity-50">
                      <Rocket className="h-3.5 w-3.5" /> Deploy
                    </button>
                    <button onClick={() => setDeleteId(s.id)}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-red-500/10 text-red-500 text-xs hover:bg-red-500/20 transition-colors">
                      <Trash2 className="h-3.5 w-3.5" /> Xóa
                    </button>
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0 mt-1" onClick={() => setDetailStrategy(s)} />
                </div>
              </div>
            );
          })}

          {strategies.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <Plus className="h-10 w-10 mb-3 text-muted-foreground/30" />
              <p className="text-sm text-muted-foreground">Chưa có chiến lược nào.</p>
              <button onClick={() => setShowChat(true)} className="mt-2 text-xs text-primary hover:underline">
                Tạo chiến lược bằng AI →
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── AI Chat Panel ── */}
      {showChat && (
        <div className="flex-1 flex flex-col bg-background">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border/40 bg-card/30 shrink-0">
            <div className="flex items-center gap-2">
              <BotMessageSquare className="h-5 w-5 text-primary" />
              <div>
                <div className="text-sm font-semibold">KAIROS Strategy Builder AI</div>
                <div className="text-xs text-muted-foreground">Kết nối A03 — Hội Đồng Đầu Tư</div>
              </div>
            </div>
            <button onClick={() => setShowChat(false)} className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors">
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((msg, i) => (
              <div key={i} className={clsx("flex", msg.role === "user" ? "justify-end" : "justify-start")}>
                {msg.role === "ai" && (
                  <div className="w-7 h-7 rounded-full bg-primary/20 flex items-center justify-center mr-2 shrink-0 mt-0.5">
                    <Sparkles className="h-3.5 w-3.5 text-primary" />
                  </div>
                )}
                <div className={clsx(
                  "max-w-[80%] px-3 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap",
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground rounded-br-sm"
                    : "bg-card border border-border/50 rounded-bl-sm"
                )}>{msg.text}</div>
              </div>
            ))}
            {aiLoading && (
              <div className="flex justify-start">
                <div className="w-7 h-7 rounded-full bg-primary/20 flex items-center justify-center mr-2 shrink-0">
                  <Sparkles className="h-3.5 w-3.5 text-primary" />
                </div>
                <div className="px-3 py-2.5 bg-card border border-border/50 rounded-2xl rounded-bl-sm">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              </div>
            )}
          </div>

          <div className="p-3 border-t border-border/40 bg-card/20">
            <div className="flex gap-2">
              <textarea value={input} onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSendMessage(); } }}
                placeholder="Mô tả chiến lược... (Enter để gửi)"
                rows={2}
                className="flex-1 bg-background border border-border rounded-xl px-3 py-2 text-sm resize-none outline-none focus:border-primary transition-colors placeholder:text-muted-foreground"
              />
              <button onClick={handleSendMessage} disabled={!input.trim() || aiLoading}
                className="px-3 bg-primary text-primary-foreground rounded-xl hover:bg-primary/90 transition-colors disabled:opacity-50">
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Strategy Detail Modal ── */}
      {detailStrategy && (
        <StrategyDetailModal strategy={detailStrategy} onClose={() => setDetailStrategy(null)} />
      )}

      {/* ── Delete Confirm ── */}
      {deleteId && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-2xl p-6 max-w-sm w-full mx-4 shadow-2xl">
            <h3 className="font-semibold mb-2">Xác nhận xóa chiến lược</h3>
            <p className="text-sm text-muted-foreground mb-5">
              Bạn có chắc muốn xóa <strong>"{strategies.find(s => s.id === deleteId)?.name}"</strong>?
            </p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setDeleteId(null)} className="px-4 py-2 rounded-lg border border-border text-sm hover:bg-muted transition-colors">Hủy</button>
              <button onClick={() => handleDelete(deleteId)} className="px-4 py-2 rounded-lg bg-red-500 text-white text-sm hover:bg-red-600 transition-colors">Xóa</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
