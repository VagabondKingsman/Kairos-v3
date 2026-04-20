---
name: loi_nhuan_quyen_chon
description: "Phương pháp luận Phân tích P&L của Quyền chọn: Vẽ biểu đồ Payoff, tính toán Điểm hòa vốn, mô phỏng các chiến lược Đa chân (Multi-leg), và định giá kịch bản bằng hệ số Greeks thông qua mô hình Black-Scholes."
category: asset-class
---

# Biểu đồ Payoff Quyền Chọn (Options Payoff & Pricing)

## Tổng quan

Kỹ năng này sinh ra để làm trái tim cho các phân tích chiến lược Quyền chọn (Options) thuộc Hệ thống KAIROS, đảm nhiệm việc:
- Tạo đường cong Lời/Lỗ (P&L) cho các danh mục từ Cơ bản đến Phức tạp (Đa chân - Multi-leg).
- Định giá mô hình Black-Scholes và trích xuất 5 hệ số Greeks.
- Tìm ngược Biến động Hàm ý (Implied Volatility - IV).
- Định hướng lựa chọn Chiến lược tối ưu.

**Cảnh báo**: Chỉ dùng cho mục đích Nghiên cứu và Backtest. KHÔNG xuất ra tín hiệu thực thi giao dịch tự động.

---

## 1. Từ điển Chiến lược Hỗ trợ (Strategy Dictionary)

### 1.1 Chiến lược Đơn chân (Single-Leg)

| Chiến lược | Quan điểm Thị trường | Tiền phí | Lời Tối đa | Lỗ Tối đa |
|------|------|--------|----------|----------|
| Mua Call (Long Call) | Rất Bullish | Phải trả | Không giới hạn | Bằng tiền phí đã mua |
| Mua Put (Long Put) | Rất Bearish | Phải trả | Strike - Phí | Bằng tiền phí đã mua |
| Bán Call (Short Call)| Đi ngang hoặc Bearish nhẹ | Được nhận | Bằng tiền phí | Không giới hạn (Cực kỳ nguy hiểm) |
| Bán Put (Short Put) | Đi ngang hoặc Bullish nhẹ | Được nhận | Bằng tiền phí | Strike - Phí |

### 1.2 Chênh lệch Dọc (Vertical Spreads) - Khóa Rủi ro

| Chiến lược | Cấu trúc Lệnh | Quan điểm | Dòng tiền (Premium) |
|------|------|----------|----------|
| Bull Call Spread | Mua Call (K thấp) + Bán Call (K cao) | Bullish Tầm trung | Phải trả (Net debit) |
| Bear Put Spread | Mua Put (K cao) + Bán Put (K thấp) | Bearish Tầm trung | Phải trả (Net debit) |
| Bull Put Spread | Bán Put (K cao) + Mua Put (K thấp) | Bullish Tầm trung | Nhét túi (Net credit) |
| Bear Call Spread | Bán Call (K thấp) + Mua Call (K cao)| Bearish Tầm trung | Nhét túi (Net credit) |

### 1.3 Chiến lược Bắt Biến động (Straddles / Strangles)

| Chiến lược | Cấu trúc Lệnh | Khi nào dùng? |
|------|------|----------|
| Mua Straddle | Mua Call (ATM) + Mua Put (ATM) | Đánh cược thị trường sắp có bão lớn (Biến động siêu mạnh) nhưng không rõ hướng. |
| Bán Straddle | Bán Call (ATM) + Bán Put (ATM) | Đánh cược thị trường ngủ đông (Đi ngang hẹp), thu trọn tiền phí 2 đầu. |
| Mua Strangle | Mua Call (OTM) + Mua Put (OTM) | Giống Long Straddle nhưng mua ngoài vùng giá (Rẻ hơn, bù lại bão phải cực to mới có lời). |
| Bán Strangle | Bán Call (OTM) + Bán Put (OTM) | Bán bảo hiểm 2 đầu cách xa giá hiện tại. Dễ thắng, nhưng nổ bão là vỡ nợ. |

### 1.4 Bướm & Chim ưng (Butterflies / Condors)

| Chiến lược | Cấu trúc Lệnh | Đặc điểm |
|------|------|------|
| Bướm Mua (Long Butterfly) | Mua 1 Call (K1) + Bán 2 Call (K2) + Mua 1 Call (K3) | Chi phí cực rẻ. Cược rằng ngày đáo hạn giá sẽ nằm im chính xác tại mốc K2. |
| Bướm Sắt (Iron Butterfly) | Bán Call (K2) + Bán Put (K2) + Mua Call (K3) + Mua Put (K1)| Tương tự Bướm, nhưng là lệnh nhét túi tiền phí. |
| Thần ưng Sắt (Iron Condor)| Bán Put (K2) + Mua Put (K1) + Bán Call (K3) + Mua Call (K4)| Chiến lược ruột của dân đánh Neutral (Đi ngang). Ăn tiền phí, chặn lỗ an toàn cả 2 đầu. |

---

## 2. Mô hình Định giá Black-Scholes

### 2.1 Các Giả định Cốt lõi

- Giá tài sản đi theo Phân phối chuẩn Logarit (Brownian motion).
- Lãi suất phi rủi ro `r` là một hằng số.
- Biến động `σ` là một hằng số.
- Là Quyền chọn Kiểu Âu (Chỉ được thực thi vào chính xác ngày đáo hạn).

### 2.2 Động cơ Tính toán 5 hệ số Greeks

*Công thức đầy đủ có sẵn trong code Python mẫu phía dưới.*

1. **Delta (Tốc độ)**: Giao động từ `[0, 1]` cho Call và `[-1, 0]` cho Put.
2. **Gamma (Gia tốc)**: Điểm cao nhất luôn nằm ở ATM (Tại giá hiện tại).
3. **Theta (Thời gian - Bị trừ tiền mỗi ngày)**: Thường mang dấu Âm cho người Mua. Mức độ trừ tiền khốc liệt nhất diễn ra vào những ngày cận đáo hạn.
4. **Vega (Biến động)**: Tính bằng việc giá trị Quyền chọn thay đổi bao nhiêu khi IV tăng 1%.
5. **Rho (Lãi suất)**: Ít quan trọng với Quyền chọn Crypto hoặc Chứng khoán ngắn hạn.

---

## 3. Phân tích Biểu đồ Payoff (Đường Lời/Lỗ)

### 3.1 Đường P&L vào Ngày Đáo hạn (Expiry Curve)

Đây là đường cứng (Gãy khúc).
- Đối với mỗi cái chân (Leg): Tính toán giá trị thanh lý nội tại (Intrinsic value) dựa vào giá đáo hạn giả định.
- Trừ đi phí Mua (Hoặc cộng thêm phí Bán) ban đầu.
- Tổng hợp toàn bộ các chân sẽ ra một đường P&L cuối cùng.

### 3.2 Đường Giá trị Lý thuyết Hiện tại (Theo Black-Scholes)

Đây là đường cong mềm mại mượt mà.
Sử dụng công thức Black-Scholes để tính giá quyền chọn TẠI THỜI ĐIỂM HIỆN TẠI (với T = thời gian còn lại). Khoảng cách từ đường cong mượt này đập xuống đường cứng Gãy khúc chính là **Giá trị Thời gian (Time Value)**.

### 3.3 Điểm Hòa vốn (Break-Even Points - BEP)

Giải phương trình `Payoff(Giá) = 0`.
- Single-leg: Rất dễ tính (Ví dụ Long Call = Strike + Phí trả).
- Multi-leg (Ví dụ Iron Condor): Có tới 2 điểm hòa vốn. Cần dùng thuật toán nội suy (`scipy.optimize.brentq`) để dò nghiệm.

---

## 4. Code Mẫu Định Giá (Python Core)

```python
import numpy as np
from scipy.stats import norm

def bs_price(S, K, T, r, sigma, option_type, q=0.0):
    """
    S: Giá tài sản hiện tại
    K: Giá thực thi (Strike)
    T: Thời gian còn lại (Năm, VD: 0.25 là 3 tháng)
    r: Lãi suất phi rủi ro
    sigma: Biến động Hàm ý (IV)
    q: Tỷ suất cổ tức liên tục
    """
    if T <= 0:
        if option_type == "call":
            return max(0.0, S - K)
        return max(0.0, K - S)

    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == "call":
        price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)

    return float(price)

# Đoạn code tính Greeks và vẽ biểu đồ Plotly / Matplotlib 
# đã được trừu tượng hóa. Dùng tương tự như các file chuẩn.
```

---

## 5. Cẩm nang Giao dịch Thực chiến (Decision Tree)

### 5.1 Chọn Chiến lược theo Quan điểm Thị trường

```text
Quan điểm của bạn
├── Bullish Mạnh (Chắc chắn tăng thốc)
│   ├── Sẵn tiền trả phí mạo hiểm → Mua Call (Long Call)
│   └── Muốn tiết kiệm phí bù lại cắt lãi đỉnh → Bull Call Spread
├── Bullish Nhẹ nhàng / Đi ngang
│   ├── Đang ôm sẵn Cổ phiếu/Coin trong ví → Covered Call (Bán Call lấy lãi suất)
│   └── Đánh tay không bắt giặc → Bull Put Spread (Nhét túi tiền phí rủi ro thấp)
├── Bearish Mạnh (Chắc chắn sập hầm)
│   ├── Sẵn tiền trả phí mạo hiểm → Mua Put (Long Put)
│   └── Muốn tiết kiệm phí → Bear Put Spread
├── Đứng im (Thị trường nhàm chán / Lưỡng lự)
│   ├── Dự đoán đi ngang hẹp → Iron Condor (Ăn tiền tàn lụi 2 đầu)
│   └── Tin rằng sắp có bão nhưng không biết hướng → Long Straddle
```

### 5.2 Môi trường Biến động (IV Regime)

| Trạng thái IV | Phần trăm Lịch sử (IV Rank) | Vũ khí Phù hợp | Tránh xa |
|---------|----------|----------|----------|
| IV Thấp Đáy (< 20%) | Dưới 20 | Mua Straddle, Mua Quyền chọn Đơn. Đồ đang rất rẻ. | Bán quyền chọn (Vì bán được quá ít tiền lẻ). |
| IV Bình thường (20-80%)| 20 đến 80 | Chênh lệch dọc (Spreads), Calendar Spread | Đánh bạc bằng quyền chọn đơn (Hên xui). |
| IV Cao Ngút trời (> 80%)| Trên 80 | Bán Straddle, Iron Condor, Covered Call. Đồ đang cực kỳ đắt. | Mua Quyền chọn (Vào mua là dính Đu đỉnh IV). |

### 5.3 Khi nào Cần Lăn chốt (Rolling) hoặc Sửa sai?

**Kỹ thuật Cuộn lệnh (Rolling):**
- **Đóng cũ mở mới**: Đóng cái quyền chọn sắp sửa lỗ lòi mắt lại, mở một cái mới ở mức giá xa hơn (Rolling Up/Down) hoặc tháng xa hơn (Rolling Out) để gồng lỗ lấy thêm thời gian thở.
- **Tiêu chuẩn Stop-Loss (Cắt máu)**: Trong các lệnh Iron Condor hoặc Short Spread, luật bất thành văn là: Khi mức Lỗ hiện tại = 2 lần Mức Phí thu được ban đầu -> CẮT LỖ NGAY LẬP TỨC. Đừng để dính rủi ro đuôi (Tail Risk) cháy tài khoản.
