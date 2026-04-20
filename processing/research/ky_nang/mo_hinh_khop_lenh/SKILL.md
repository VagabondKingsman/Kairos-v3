---
name: mo_hinh_khop_lenh
description: Mô hình hóa Khớp lệnh (Dành cho Backtest) — Các công thức Trượt giá (Slippage), Logic chia lệnh VWAP/TWAP, Ước tính chi phí tác động thị trường (Market Impact), và cấu hình các giả định khớp lệnh.
category: strategy
---

# Mô hình hóa Khớp lệnh (Trade Execution Modeling)

## Tổng quan

Cung cấp các giả định khớp lệnh thực tế và khắc nghiệt hơn cho hệ thống Backtest, bao gồm các mô hình Trượt giá, Tác động thị trường và thuật toán Khớp lệnh. Lưu ý: Kỹ năng này chỉ dùng để mô phỏng Backtest cho sát với thực tế, không dùng để đẩy lệnh lên sàn (Live Execution).

## Các Mô hình Trượt giá (Slippage Models)

### Tại sao Cần Mô hình Trượt giá?

```text
Backtest trong mơ: Mua/bán khớp ngay lập tức ở giá đóng cửa, không tốn một đồng trượt giá nào.
Thế giới thực:
1. Sổ lệnh luôn có khoảng cách Mua/Bán (Bid-ask spread).
2. Khi bạn quăng lệnh lớn vào, nó sẽ ăn mòn thanh khoản và làm giá bị đẩy lên/đạp xuống (Market impact).
3. Độ trễ (Latency): Từ lúc có tín hiệu đến lúc sàn khớp lệnh mất vài giây, giá đã chạy mất.

Backtest không có trượt giá -> Bức tranh lợi nhuận ảo tưởng -> Cháy tài khoản khi đem ra trade thật.
```

### 1. Mô hình Trượt giá Cố định (Fixed Slippage)

```python
def fixed_slippage(price: float, direction: int, bps: float = 5.0) -> float:
    """
    direction: 1=Mua, -1=Bán
    bps: Trượt giá tính bằng điểm cơ bản (1 bp = 0.01%), mặc định 5 bps.
    """
    slippage = price * bps / 10000
    return price + direction * slippage
```

**Bảng tham chiếu Trượt giá Cố định:**

| Thị trường / Tài sản | Trượt giá Đề xuất (bps) | Ghi chú |
|------|-------------|------|
| Cổ phiếu vốn hóa Lớn (SP500) | 1 - 3 | Thanh khoản hoàn hảo |
| Cổ phiếu vốn hóa Vừa/Nhỏ | 5 - 15 | Thanh khoản trung bình |
| Tiền mã hóa BTC/ETH Spot | 2 - 5 | Thanh khoản tốt trên Binance/OKX |
| Altcoins (Crypto nhỏ) | 10 - 50 | Spread lớn, rất rủi ro |

### 2. Mô hình Tác động Tuyến tính (Linear Impact)

```python
def linear_impact(price: float, direction: int,
                  volume_traded: float, adv: float,
                  impact_coeff: float = 0.1) -> float:
    """
    Tác động thị trường tỷ lệ thuận với: Khối lượng Lệnh của bạn / Khối lượng Giao dịch Trung bình Ngày (ADV).
    
    volume_traded: Khối lượng bạn muốn đánh.
    adv: Trung bình thanh khoản ngày của tài sản.
    impact_coeff: Hệ số tác động (Thường từ 0.05 - 0.2).
    """
    participation_rate = volume_traded / adv
    impact = impact_coeff * participation_rate
    return price * (1 + direction * impact)
```

### 3. Mô hình Tác động Căn bậc hai (Square-Root Impact - Almgren-Chriss)

Mô hình chuẩn mực nhất trong giới học thuật và quỹ định lượng. Nó dựa trên nguyên lý: Lệnh càng lớn thì tác động càng mạnh, nhưng sức mạnh sẽ giảm dần (không tuyến tính).

```python
import numpy as np

def sqrt_impact(price: float, direction: int,
                volume_traded: float, adv: float,
                volatility: float, eta: float = 0.5) -> float:
    """
    impact = η × σ × sqrt(Lệnh_của_bạn / ADV)
    
    volatility: Độ biến động hàng ngày của tài sản (Độ lệch chuẩn).
    eta: Hệ số độ co giãn, thường từ 0.3 - 0.8.
    """
    participation = volume_traded / adv
    impact = eta * volatility * np. np.sqrt(participation)
    return price * (1 + direction * impact)
```

**Cây Quyết định Chọn Mô hình Trượt giá:**
```text
So sánh Quy mô vốn của bạn với Thanh khoản của tài sản (ADV):
├── Vốn < 0.5% ADV -> Chỉ cần dùng Trượt giá cố định (5 bps).
├── Vốn từ 0.5% - 5% ADV -> Dùng Tác động Tuyến tính.
└── Vốn > 5% ADV -> BẮT BUỘC dùng Tác động Căn bậc hai. (Trở thành cá mập làm giá).
```

## Các Thuật toán Khớp lệnh

### VWAP (Khớp lệnh theo Giá Trung bình Gia quyền Khối lượng)

```text
Mục tiêu: Rải lệnh đều đặn sao cho giá khớp trung bình của bạn đúng bằng giá VWAP của cả ngày.

Logic thực thi:
1. Dự báo hồ sơ thanh khoản trong ngày (Thường có hình chữ U: Sôi động ở đầu phiên và cuối phiên).
2. Chia nhỏ Lệnh Lớn thành các Lệnh Nhỏ tương ứng với hồ sơ thanh khoản đó.
3. Đặt lệnh rải rác.

Trong Backtest:
Nếu bạn đánh nến Ngày (1D), hãy dùng thẳng cột giá VWAP làm giá Khớp lệnh thay vì dùng giá Đóng cửa (Close).
```

### TWAP (Khớp lệnh theo Giá Trung bình Gia quyền Thời gian)

```text
Mục tiêu: Khớp lệnh đều đặn bằng cách xẻ nhỏ lệnh theo các khoảng thời gian bằng nhau.
Ví dụ: Lệnh 100,000 USD. TWAP 10 tiếng. Mỗi tiếng đều đặn quăng 10,000 USD vào thị trường.

Ưu điểm: Đơn giản, mù tịt, không cần quan tâm thanh khoản cao hay thấp.
Nhược điểm: Rất dễ bị "Quét" (Front-run) bởi các Bot HFT vì hành vi quá dễ đoán.
```

## Mô hình Tổng Chi phí Giao dịch (TCA - Transaction Cost Analysis)

```text
Tổng chi phí = Chi phí Nổi (Explicit) + Chi phí Chìm (Implicit)

Chi phí Nổi:
- Phí giao dịch (Commission): Khoảng 0.02% - 0.1% tùy sàn.
- Thuế (Nếu có).

Chi phí Chìm:
- Chênh lệch Mua/Bán (Spread).
- Trượt giá (Slippage) / Tác động thị trường (Market Impact).
```

**Khuyến nghị Đặt Tham số trong Backtest:**
Thay vì cấu hình từng loại phí phức tạp, hệ thống gom chung tất cả lại thành tham số `commission` trong `config.json`.
- Nên đặt `commission = 0.001` (Tức 0.1%). Đây là một con số thận trọng, đủ bao trùm cả phí sàn, thuế, spread và trượt giá nhẹ.

## Tích hợp Độ trễ (Execution Delay) vào Backtest

Tránh việc thuật toán "thấy tín hiệu là khớp ngay".

```python
class SignalEngine:
    def __init__(self):
        # Thông số cấu hình khớp lệnh khắc nghiệt
        self.execution_delay = 1       # Trễ 1 cây nến (Tín hiệu hnay, ngày mai mới mua)
        self.slippage_bps = 5          # Trượt 5 bps mỗi lệnh
        self.max_participation = 0.05  # Quy mô vốn không được vượt quá 5% volumn ngày

    def generate(self, data_map):
        for code, df in data_map.items():
            raw_signal = self._compute_signal(df)
            
            # Đẩy tín hiệu trễ đi 1 cây nến
            delayed_signal = raw_signal.shift(self.execution_delay)
            
            # Bộ lọc Thanh khoản (Volume filter)
            # Khối lượng ngày hôm đó phải lớn hơn 30% trung bình 20 ngày mới cho phép trade
            volume_ok = df['volume'] > df['volume'].rolling(20).mean() * 0.3
            delayed_signal[~volume_ok] = 0
            
            signals[code] = delayed_signal
```

## Đánh giá Tác động của Chi phí

Nếu hệ thống của bạn có Vòng quay vốn (Turnover) quá cao, chi phí sẽ ăn mòn mọi lợi nhuận.

```text
Bước 1: Tính Vòng quay vốn hằng năm
  Turnover = Số lệnh × 2 (Mở+Đóng) / Tổng số tài sản đang giữ.
  
Bước 2: Tính Mất mát do chi phí
  Lỗ chi phí = Turnover × Tổng phí 1 chiều (Ví dụ 0.1%)

Ví dụ: Bạn rebalance danh mục hằng tháng -> Turnover = 12 vòng.
  Lỗ chi phí = 12 × 0.1% = 1.2% / năm.
  Nếu thuật toán của bạn chỉ sinh ra Lợi nhuận gộp 5%/năm, thì tiền phí đã xén mất 25% công sức của bạn!
```
