import { BrainCircuit, CheckCircle, XCircle, RefreshCw, Loader2 } from "lucide-react";
import { clsx } from "clsx";
import { useState } from "react";

const MODULES = [
  { key: "trang_thai",    label: "Chế Độ Thị Trường", desc: "MLP ResBlock — Phân loại Regime 0–7", trained: true,  accuracy: 0.84, f1: 0.81, samples: 12400 },
  { key: "du_bao_gia",    label: "Dự Báo Giá",         desc: "LSTM — Xác suất tăng/giảm n nến tới", trained: false, accuracy: null, f1: null, samples: 0 },
  { key: "bat_thuong",    label: "Phát Hiện Bất Thường",desc: "Isolation Forest + Autoencoder",       trained: true,  accuracy: 0.91, f1: 0.88, samples: 8700 },
  { key: "cho_diem",      label: "Chấm Điểm Tín Hiệu", desc: "XGBoost — Signal Quality Score 0→1",  trained: false, accuracy: null, f1: null, samples: 0 },
  { key: "phan_loai_nen", label: "Phân Loại Nến",       desc: "CNN 1D — Pinbar, Engulfing, Doji...", trained: false, accuracy: null, f1: null, samples: 0 },
  { key: "danh_muc",      label: "Tối Ưu Danh Mục",    desc: "Markowitz + PPO — Portfolio weights",  trained: true,  accuracy: null, f1: null, samples: 5200 },
];

export function MLCenter() {
  const [training, setTraining] = useState<string | null>(null);

  const handleTrain = (key: string) => {
    setTraining(key);
    setTimeout(() => setTraining(null), 3000); // Mock
  };

  return (
    <div className="flex-1 overflow-auto">
      <div className="p-5 max-w-[1200px] mx-auto">
        <div className="flex items-center gap-2 mb-2">
          <BrainCircuit className="h-5 w-5 text-primary" />
          <h2 className="text-base font-semibold">Trung Tâm Học Máy (a07)</h2>
        </div>
        <p className="text-xs text-muted-foreground mb-5">
          6 module ML độc lập. Mỗi module có thể tích hợp vào chiến lược qua{" "}
          <code className="font-mono text-primary">a07_trung_tam_hoc_may</code>
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {MODULES.map((m, idx) => {
            const isTraining = training === m.key;
            return (
              <div key={m.key} className={clsx(
                "card-kairos p-4 transition-all",
                m.trained ? "border-success/20 hover:border-success/40" : "hover:border-primary/20"
              )}>
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-[10px] font-mono text-muted-foreground">#{idx + 1}</span>
                      <span className="text-sm font-semibold">{m.label}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">{m.desc}</p>
                  </div>
                  {m.trained
                    ? <CheckCircle className="h-5 w-5 text-success shrink-0" />
                    : <XCircle className="h-5 w-5 text-muted-foreground/40 shrink-0" />}
                </div>

                {/* Metrics */}
                <div className="flex gap-4 mb-3">
                  <div>
                    <div className="text-[9px] text-muted-foreground">Trạng thái</div>
                    <div className={clsx("text-xs font-semibold", m.trained ? "text-success" : "text-muted-foreground")}>
                      {m.trained ? "Đã Train" : "Chưa Train"}
                    </div>
                  </div>
                  {m.accuracy && (
                    <div>
                      <div className="text-[9px] text-muted-foreground">Accuracy</div>
                      <div className="text-xs font-semibold font-mono">{(m.accuracy * 100).toFixed(0)}%</div>
                    </div>
                  )}
                  {m.f1 && (
                    <div>
                      <div className="text-[9px] text-muted-foreground">F1 Score</div>
                      <div className="text-xs font-semibold font-mono">{m.f1.toFixed(2)}</div>
                    </div>
                  )}
                  {m.samples > 0 && (
                    <div>
                      <div className="text-[9px] text-muted-foreground">Mẫu train</div>
                      <div className="text-xs font-semibold font-mono">{m.samples.toLocaleString()}</div>
                    </div>
                  )}
                </div>

                {/* Progress bar (accuracy) */}
                {m.accuracy && (
                  <div className="h-1 rounded-full bg-muted mb-3 overflow-hidden">
                    <div className="h-full bg-success rounded-full" style={{ width: `${m.accuracy * 100}%` }} />
                  </div>
                )}

                {/* Import snippet */}
                <div className="bg-muted/50 rounded px-2.5 py-1.5 font-mono text-[10px] text-muted-foreground mb-3 overflow-x-auto">
                  from a07_trung_tam_hoc_may.{m.key} import *
                </div>

                {/* Action button */}
                <button
                  onClick={() => handleTrain(m.key)}
                  disabled={isTraining}
                  className={clsx(
                    "w-full flex items-center justify-center gap-2 py-1.5 rounded-md text-xs font-medium transition-colors",
                    m.trained
                      ? "border border-border text-muted-foreground hover:text-foreground hover:bg-muted"
                      : "bg-primary/10 text-primary hover:bg-primary/20",
                    isTraining && "opacity-70 cursor-not-allowed"
                  )}
                >
                  {isTraining
                    ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Đang huấn luyện...</>
                    : <><RefreshCw className="h-3.5 w-3.5" /> {m.trained ? "Tái Huấn Luyện" : "Bắt Đầu Train"}</>}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
