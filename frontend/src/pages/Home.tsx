import { Link } from "react-router-dom";
import {
  FlaskConical, BrainCircuit, BarChart3, MessageSquare,
  TrendingUp, ShieldCheck, ArrowRight
} from "lucide-react";

const FEATURES = [
  {
    icon: MessageSquare,
    title: "AI Trợ Lý Nghiên Cứu",
    desc: "Đặt câu hỏi bằng tiếng Việt, AI sẽ tự thiết kế chiến lược, backtest và phân tích kết quả.",
    color: "text-info",
  },
  {
    icon: BarChart3,
    title: "Backtest Định Lượng",
    desc: "Kiểm tra chiến lược trên dữ liệu lịch sử với đầy đủ biểu đồ Equity Curve, PnL Calendar và phân phối lệnh.",
    color: "text-primary",
  },
  {
    icon: BrainCircuit,
    title: "6 Module Machine Learning",
    desc: "Phân loại chế độ thị trường, dự báo giá, phát hiện bất thường, chấm điểm tín hiệu và tối ưu danh mục.",
    color: "text-warning",
  },
  {
    icon: TrendingUp,
    title: "Đa Thị Trường",
    desc: "Hỗ trợ Crypto (OKX/CCXT), Chứng khoán Mỹ (yfinance), Chứng khoán Việt Nam (vnstock).",
    color: "text-success",
  },
  {
    icon: ShieldCheck,
    title: "Không Lookahead Bias",
    desc: "Mọi backtest đều được thiết kế với chuẩn nen_htf đa khung thời gian, tuyệt đối không nhìn trước tương lai.",
    color: "text-primary",
  },
  {
    icon: FlaskConical,
    title: "64+ Kỹ Năng Phân Tích",
    desc: "Thư viện kỹ năng từ SMC, Ichimoku, Elliott Wave đến Phân tích Vĩ mô và Dòng tiền ETF.",
    color: "text-info",
  },
];

export function Home() {
  return (
    <div className="flex-1 overflow-auto">
      <div className="flex flex-col items-center justify-center min-h-full p-8">
        {/* Hero */}
        <div className="max-w-2xl text-center space-y-5 mt-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-primary/30 bg-primary/10 text-primary text-xs font-medium">
            <FlaskConical className="h-3 w-3" />
            Hệ Thống Giao Dịch Định Lượng AI
          </div>

          <h1 className="text-5xl font-bold tracking-tight">
            <span className="text-primary">KAIROS</span>{" "}
            <span className="text-foreground">Quant System</span>
          </h1>

          <p className="text-lg text-muted-foreground leading-relaxed">
            Nền tảng nghiên cứu và giao dịch định lượng toàn diện — kết hợp AI,
            Machine Learning và 64+ kỹ năng phân tích tài chính chuyên sâu.
          </p>

          <div className="flex items-center justify-center gap-3 pt-2">
            <Link
              to="/agent"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-primary text-primary-foreground font-semibold hover:opacity-90 transition-opacity"
            >
              Bắt đầu Phân tích <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-border text-muted-foreground font-medium hover:text-foreground hover:bg-muted transition-colors"
            >
              Xem Dashboard
            </Link>
          </div>
        </div>

        {/* Feature Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-16 max-w-5xl w-full pb-12">
          {FEATURES.map(({ icon: Icon, title, desc, color }) => (
            <div
              key={title}
              className="card-kairos p-5 space-y-3 hover:border-primary/30 transition-colors"
            >
              <Icon className={`h-7 w-7 ${color}`} />
              <h3 className="font-semibold text-sm">{title}</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
