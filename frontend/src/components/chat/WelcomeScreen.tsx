import { FlaskConical, TrendingUp, Bitcoin, Globe, Sparkles, Users } from "lucide-react";
import { useI18n } from "@/lib/i18n";

interface Example {
  title: string;
  desc: string;
  prompt: string;
}

interface Category {
  label: string;
  icon: React.ReactNode;
  color: string;
  examples: Example[];
}

const CATEGORIES: Category[] = [
  {
    label: "Backtest Đa Thị Trường",
    icon: <TrendingUp className="h-4 w-4" />,
    color: "text-red-400 border-red-500/30 hover:border-red-500/60 hover:bg-red-500/5",
    examples: [
      {
        title: "Chiến lược MA Chéo Đôi VN",
        desc: "VCB.VN + HPG.VN với MA 5/20, backtest 2024",
        prompt: "Tạo chiến lược MA chéo đôi (5/20 ngày) cho VCB.VN và HPG.VN, backtest toàn năm 2024, so sánh với buy-and-hold",
      },
      {
        title: "Bollinger Band BTC 1H",
        desc: "Mean-reversion trên BTC-USDT khung 1 giờ",
        prompt: "Backtest chiến lược Bollinger Band mean-reversion cho BTC-USDT khung 1H, 30 ngày gần nhất, với stop-loss 2%",
      },
      {
        title: "Danh Mục Tối Ưu KAIROS",
        desc: "Phân bổ vốn tối ưu cho 5 cổ phiếu VN",
        prompt: "Backtest danh mục gồm VCB, HPG, SSI, MWG, FPT với tối ưu hoá tỉ lệ Sharpe, toàn năm 2023-2024",
      },
    ],
  },
  {
    label: "Nghiên Cứu & Phân Tích",
    icon: <Sparkles className="h-4 w-4" />,
    color: "text-amber-400 border-amber-500/30 hover:border-amber-500/60 hover:bg-amber-500/5",
    examples: [
      {
        title: "Mô Hình Alpha Đa Nhân Tố",
        desc: "Tổng hợp nhân tố Momentum, Value, Quality",
        prompt: "Xây dựng mô hình alpha đa nhân tố (momentum, value, quality) cho 30 cổ phiếu VN-Index, backtest 2022-2024 với IC-weighted synthesis",
      },
      {
        title: "Phân Tích Greeks Quyền Chọn",
        desc: "Black-Scholes: Delta/Gamma/Theta/Vega",
        prompt: "Tính toán Greeks cho quyền chọn VN30: spot=1250, strike=1280, lãi suất=4.5%, vol=22%, đáo hạn=90 ngày",
      },
    ],
  },
  {
    label: "Hội Đồng AI (Swarm)",
    icon: <Users className="h-4 w-4" />,
    color: "text-violet-400 border-violet-500/30 hover:border-violet-500/60 hover:bg-violet-500/5",
    examples: [
      {
        title: "Ủy Ban Rủi Ro KAIROS",
        desc: "Tranh luận AI: long vs short, phân tích rủi ro, quyết định PM",
        prompt: "[Swarm Team Mode] Dùng preset investment_committee để đánh giá nên long hay short HPG.VN trong bối cảnh thị trường hiện tại",
      },
      {
        title: "Ban Nghiên Cứu Chiến Lược",
        desc: "Sàng lọc → nghiên cứu nhân tố → backtest → kiểm toán rủi ro",
        prompt: "[Swarm Team Mode] Dùng preset quant_strategy_desk để tìm và backtest chiến lược momentum tốt nhất trên VN30",
      },
    ],
  },
  {
    label: "Nghiên Cứu Tài Liệu & Web",
    icon: <Globe className="h-4 w-4" />,
    color: "text-blue-400 border-blue-500/30 hover:border-blue-500/60 hover:bg-blue-500/5",
    examples: [
      {
        title: "Phân Tích Báo Cáo Tài Chính",
        desc: "Upload PDF và đặt câu hỏi về tài chính",
        prompt: "Tóm tắt các chỉ số tài chính chính, rủi ro và triển vọng từ báo cáo tài chính đã upload",
      },
      {
        title: "Nghiên Cứu Vĩ Mô",
        desc: "Đọc nguồn web trực tiếp để phân tích macro",
        prompt: "Phân tích tác động của chính sách lãi suất Fed gần nhất đến thị trường chứng khoán và crypto Việt Nam",
      },
    ],
  },
];

const CAPABILITY_CHIPS = [
  "Hội Đồng AI 6 Thành Viên",
  "Module ML PyTorch",
  "19 Công Cụ AI",
  "3 Thị Trường: VN · Crypto · US/HK",
  "Khung Thời Gian 1P - 1D",
  "4 Bộ Tối Ưu Danh Mục",
  "15+ Chỉ Số Rủi Ro",
  "Kiểm Chứng Monte Carlo",
  "PDF & Web Research",
  "Bootstrap Sharpe CI",
];

interface Props {
  onExample: (s: string) => void;
}

export function WelcomeScreen({ onExample }: Props) {
  const { t } = useI18n();

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-8 text-center">
      <div className="space-y-3">
        <div className="h-16 w-16 mx-auto rounded-2xl bg-gradient-to-br from-[#1a1a2e] to-[#f5a623] flex items-center justify-center shadow-lg">
          <FlaskConical className="h-8 w-8 text-white" />
        </div>
        <div>
          <h2 className="text-2xl font-bold tracking-tight">KAIROS Quant System v3.0</h2>
          <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto leading-relaxed">
            Hệ thống nghiên cứu chiến lược định lượng AI hàng đầu
          </p>
          <p className="text-sm text-muted-foreground mt-2 max-w-md leading-relaxed mx-auto">
            {t.describeStrategy}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap justify-center gap-2 max-w-lg">
        {CAPABILITY_CHIPS.map((chip) => (
          <span
            key={chip}
            className="px-2.5 py-1 text-xs rounded-full border border-border/60 text-muted-foreground bg-muted/30"
          >
            {chip}
          </span>
        ))}
      </div>

      <div className="w-full max-w-2xl text-left space-y-4">
        <p className="text-xs text-muted-foreground px-1">{t.examples}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {CATEGORIES.map((cat) => (
            <div key={cat.label} className="space-y-2">
              <div className={`flex items-center gap-1.5 text-xs font-medium px-1 ${cat.color.split(" ").filter(c => c.startsWith("text-")).join(" ")}`}>
                {cat.icon}
                <span>{cat.label}</span>
              </div>
              <div className="space-y-1.5">
                {cat.examples.map((ex) => (
                  <button
                    key={ex.title}
                    onClick={() => onExample(ex.prompt)}
                    className={`block w-full text-left px-3 py-2.5 rounded-xl border transition-colors ${cat.color}`}
                  >
                    <span className="text-sm font-medium text-foreground leading-snug">
                      {ex.title}
                    </span>
                    <span className="block text-xs text-muted-foreground mt-0.5 leading-snug">
                      {ex.desc}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
