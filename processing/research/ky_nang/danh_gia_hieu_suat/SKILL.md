---
name: danh_gia_hieu_suat
description: Phân tích Quy trách nhiệm Hiệu suất (Performance attribution) — Mô hình Brinson (Bóc tách Ngành/Chọn Cổ phiếu), Tách lớp Alpha/Beta Đa nhân tố (Factor models), Đánh giá Kỹ năng Chọn thời điểm (Market timing) và Hệ quy chiếu Benchmark.
category: analysis
---

# Quy Trách nhiệm Hiệu suất (Performance Attribution)

## Tổng quan

Bóc tách lợi nhuận vượt trội (Excess Return) của danh mục thành các nguồn gốc có thể giải thích được: Nhờ việc phân bổ đúng ngành, chọn đúng cổ phiếu, phơi nhiễm vào các yếu tố (Factor), hay nhờ tài năng né bão (Market timing).
Kỹ năng này trả lời câu hỏi: **Tại sao** chiến lược lại kiếm được tiền? Thay vì chỉ nhìn vào con số **Kiếm được bao nhiêu**.

## Mô hình Bóc tách Brinson (Brinson Attribution)

### Mô hình Brinson-Fachler Đơn kỳ

```text
Tổng lợi nhuận Vượt trội = Lợi nhuận Danh mục - Lợi nhuận Benchmark

Bóc tách thành 3 phần:
1. Hiệu ứng Phân bổ (Allocation): Do đặt cược tỷ trọng ngành khác với Benchmark.
2. Hiệu ứng Lựa chọn (Selection): Do chọn được con mã tốt hơn trung bình của ngành đó.
3. Hiệu ứng Tương tác (Interaction): Phần dư sinh ra do tương tác chéo giữa 2 hiệu ứng trên.
```

**Công thức Toán học:**

```text
Gọi w_p,i = Tỷ trọng ngành i trong Danh mục
    w_b,i = Tỷ trọng ngành i trong Benchmark
    r_p,i = Lợi nhuận ngành i trong Danh mục
    r_b,i = Lợi nhuận ngành i trong Benchmark
    R_b   = Tổng Lợi nhuận Benchmark

Allocation_i = (w_p,i - w_b,i) × (r_b,i - R_b)
Selection_i  = w_b,i × (r_p,i - r_b,i)
Interaction_i = (w_p,i - w_b,i) × (r_p,i - r_b,i)

Tổng Vượt trội = Σ(Allocation_i) + Σ(Selection_i) + Σ(Interaction_i)
```

## Bóc tách Đa nhân tố (Factor Attribution)

### Tách lớp Alpha-Beta Sơ cấp

```text
R_p = α + β × R_m + ε

α (Alpha): Lợi nhuận siêu ngạch, Đại diện cho kỹ năng của Quản lý quỹ / Bot giao dịch.
β (Beta): Phơi nhiễm rủi ro hệ thống (Thị trường lên thì nó lên).
ε (Epsilon): Rủi ro cá biệt (Nhiễu).
```

#### Mô hình Đa nhân tố (Kế thừa Fama-French)

Đánh giá xem việc bạn kiếm được tiền có thực sự là nhờ "Kỹ năng (Alpha)" hay chỉ là do "Ăn may" vì mua trúng nhóm Cổ phiếu Vốn hóa nhỏ (SMB) hoặc nhóm Cổ phiếu Giá trị (HML).

```text
R_p - R_f = α + β_mkt × (R_m - R_f) + β_smb × SMB + β_hml × HML + β_mom × MOM + ε

| Nhân tố | Ý nghĩa | Định nghĩa thường dùng |
|------|------|--------|
| MKT | Yếu tố Thị trường | Lợi nhuận S&P 500 (Hoặc BTC nếu là Crypto) |
| SMB | Phần bù Vốn hóa nhỏ | Rút gọn: Russell 2000 trừ đi S&P 500 |
| HML | Phần bù Giá trị | Rút gọn: Nhóm P/E thấp trừ Nhóm P/E cao |
| MOM | Quán tính (Momentum)| Rút gọn: Nhóm tăng mạnh nhất 12T trừ Nhóm yếu nhất |
```

## Đánh giá Kỹ năng Chọn Thời điểm (Market-Timing Evaluation)

Đo lường xem hệ thống/người quản lý quỹ có khả năng né bão khi sập và bơm Margin khi uptrend hay không.

### Mô hình Treynor-Mazuy

```text
R_p - R_f = α + β × (R_m - R_f) + γ × (R_m - R_f)² + ε

γ (Gamma) > 0 và có ý nghĩa thống kê → Có tài năng Timing (Danh mục tự tăng beta khi Uptrend và tự hạ rủi ro khi Downtrend).
```

### Các Thước đo Timing Thực chiến (Nên dùng)

| Thước đo | Cách tính | Ý nghĩa |
|------|------|------|
| Tỷ lệ Hấp thụ Bull (Bull capture) | Lợi nhuận Danh mục khi thị trường tăng / Lợi nhuận Benchmark | > 100% = Tấn công giỏi hơn Benchmark |
| Tỷ lệ Hấp thụ Bear (Bear capture) | Lợi nhuận Danh mục khi thị trường sập / Lợi nhuận Benchmark | < 100% = Phòng thủ vững chắc hơn |
| Tỷ lệ Đoán đúng (Hit rate) | Số tháng đoán đúng hướng thị trường | > 55% = Có kỹ năng dự báo |

## Khung Chọn Benchmark (Benchmark Selection)

Benchmark sai = Toàn bộ số liệu Alpha trở thành Lừa đảo.

| Loại Chiến lược | Benchmark Đề xuất | Mã Ticker tiêu biểu |
|---------|---------|---------|
| Chứng khoán Mỹ (Large Cap) | S&P 500 | SPY |
| Chứng khoán Mỹ (Công nghệ) | NASDAQ 100 | QQQ |
| Chứng khoán Mỹ (Small Cap) | Russell 2000 | IWM |
| Crypto (Tổng hợp) | Bitcoin | BTC-USDT |
| Đa tài sản (Multi-asset) | Danh mục Tĩnh 60/40 | Tự thiết lập 60% SPY / 40% TLT |

## Chỉ số Rủi ro (Risk-Adjusted Metrics)

| Chỉ số | Công thức | Xuất sắc | Khá Tốt | Trung Bình |
|------|------|------|------|------|
| Sharpe | `(R_p - R_f) / σ_p` | > 1.5 | 1.0 - 1.5 | 0.5 - 1.0 |
| Sortino | `(R_p - R_f) / σ_down` | > 2.0 | 1.5 - 2.0 | 1.0 - 1.5 |
| Calmar | `R_p / MaxDD` | > 1.0 | 0.5 - 1.0 | 0.2 - 0.5 |
| Information Ratio | `(R_p - R_b) / TE` | > 1.0 | 0.5 - 1.0 | 0.2 - 0.5 |

## Cạm bẫy Sống còn

1. **Attribution không phải Quả cầu pha lê**: Nó chỉ giải thích quá khứ. Việc có Alpha trong quá khứ không cam kết có Alpha trong tương lai.
2. **Ảo tưởng Benchmark**: Thay đổi Benchmark (Dùng chỉ số yếu hơn) thì Alpha sẽ tự nhiên xuất hiện. Đây là mánh khóe bán hàng rẻ tiền của các Quỹ mở.
3. **Thiên kiến Kẻ Sống Sót (Survivorship Bias)**: Việc Backtest mà chỉ dùng các mã "hiện tại đang sống sót", bỏ qua các công ty đã phá sản sẽ tạo ra lợi nhuận Alpha ảo siêu khổng lồ.
4. **Kiểm định Chéo (Multiple-testing)**: Nếu bạn chạy thử 100 chiến lược ngẫu nhiên, kiểu gì cũng có 5 chiến lược vô tình sinh ra lời khổng lồ (P-value = 0.05). Phải dùng dữ liệu Out-of-Sample để kiểm chứng.
