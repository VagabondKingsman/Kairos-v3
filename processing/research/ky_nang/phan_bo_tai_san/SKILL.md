---
name: phan_bo_tai_san
description: Lý thuyết và hướng dẫn phân bổ tài sản — MPT / Black-Litterman / Risk Budgeting (Ngân sách rủi ro) / Chiến lược All-Weather (Bốn mùa), bao gồm hướng dẫn cho 4 trình tối ưu hóa (optimizer) và các quy tắc tái cân bằng (rebalancing).
category: asset-class
---

# Phân bổ Tài sản và Tối ưu hóa Danh mục

## Tổng quan

Từ lý thuyết phân bổ tài sản đến triển khai thực tế, kỹ năng này bao gồm các framework kinh điển (MPT, Black-Litterman, Risk Budgeting, All-Weather) và cách sử dụng 4 bộ tối ưu hóa (optimizer) được tích hợp sẵn trong hệ thống. Đầu ra có thể được viết trực tiếp vào file `config.json`.

## Lý thuyết Phân bổ Tài sản

### 1. Lý thuyết Danh mục Đầu tư Hiện đại (MPT, Markowitz)

**Ý tưởng cốt lõi**: Tối đa hóa lợi nhuận kỳ vọng với một mức rủi ro cho trước (Đường cong hiệu quả - Efficient frontier).

```text
Bài toán tối ưu hóa:
Min  w'Σw              (Tối thiểu hóa phương sai danh mục)
Điều kiện:
     w'μ = target_return (Lợi nhuận mục tiêu)
     Σw = 1              (Tổng tỷ trọng = 100%)
     w ≥ 0               (Không bán khống)
```

| Ưu điểm | Nhược điểm |
|------|------|
| Nền tảng toán học chặt chẽ | Cực kỳ nhạy cảm với dữ liệu đầu vào (Garbage in, garbage out) |
| Trực quan hóa được Đường cong hiệu quả | Dễ bị tập trung tỷ trọng vào một vài tài sản (extreme weights) |
| Là nền tảng cho các mô hình sau này | Giả định phân phối chuẩn, bỏ qua đuôi mập (fat tails) |

**Lời khuyên thực tế**: Không nên dùng MPT thuần túy. Hãy thêm các ràng buộc (giới hạn tỷ trọng trên/dưới, giới hạn nhóm ngành) hoặc sử dụng các phiên bản đã được điều chuẩn (regularized).

### 2. Mô hình Black-Litterman (BL)

**Ý tưởng cốt lõi**: Bắt đầu từ trạng thái cân bằng của thị trường, sau đó kết hợp với quan điểm chủ quan của nhà đầu tư.

```text
Các bước:
1. Suy ngược lợi nhuận cân bằng thị trường: π = δΣw_mkt
2. Xây dựng ma trận quan điểm: P (ma trận chọn), Q (lợi nhuận kỳ vọng), Ω (độ bất định của quan điểm)
3. Pha trộn ra lợi nhuận hậu nghiệm: μ_BL = [(τΣ)^-1 + P'Ω^-1 P]^-1 [(τΣ)^-1 π + P'Ω^-1 Q]
4. Chạy tối ưu hóa Markowitz bằng μ_BL
```

**Ví dụ về quan điểm (views)**:
- Quan điểm tuyệt đối: "Chứng khoán Mỹ sẽ tăng 10% trong năm tới" → `P=[1,0,0], Q=[0.10]`
- Quan điểm tương đối: "Chứng khoán Mỹ sẽ vượt trội hơn Trái phiếu 5%" → `P=[1,-1,0], Q=[0.05]`

### 3. Ngân sách Rủi ro (Risk Budgeting)

**Ý tưởng cốt lõi**: Phân bổ dựa trên mức độ đóng góp rủi ro thay vì số vốn.

```text
Đóng góp rủi ro: RC_i = w_i × (Σw)_i / σ_p
Mục tiêu: RC_i / σ_p = budget_i (cho mọi tài sản i)
```

| Chiến lược | Ngân sách rủi ro | Dùng khi nào |
|------|---------|---------|
| Đóng góp rủi ro ngang bằng (Risk Parity) | Mỗi tài sản 1/N rủi ro | Khi bạn không biết tài sản nào sẽ tăng trưởng tốt nhất |
| Thiên vị cổ phiếu | Cổ phiếu 60%, Trái phiếu 30%, Hàng hóa 10% | Khi muốn cổ phiếu gánh nhiều rủi ro hơn |
| Linh hoạt (Dynamic) | Điều chỉnh theo tín hiệu | Khi bạn có khả năng định thời điểm thị trường |

### 4. Chiến lược All-Weather (Bốn Mùa)

**Framework của Bridgewater**: Chia đều rủi ro cho các môi trường kinh tế khác nhau.

```text
Môi trường kinh tế       Tài sản phù hợp
─────────              ─────────
Tăng trưởng mạnh         Cổ phiếu + Hàng hóa + Trái phiếu doanh nghiệp
Tăng trưởng chậm         Trái phiếu chính phủ + Trái phiếu chống lạm phát
Lạm phát tăng            Hàng hóa + Trái phiếu chống lạm phát
Lạm phát giảm            Cổ phiếu + Trái phiếu chính phủ
```

## Hướng dẫn 4 Trình Tối Ưu Hóa (Optimizers)

Cấu hình trong `config.json` thông qua `optimizer` và `optimizer_params`:

| optimizer | Tên hiển thị | Ý tưởng | Dùng khi nào |
|-----------|--------|---------|---------|
| `equal_volatility` | Nghịch đảo biến động | Chia tỷ trọng theo nghịch đảo độ biến động | Đơn giản, làm baseline tốt |
| `risk_parity` | Risk Parity | Cân bằng đóng góp rủi ro, có xét tương quan | Danh mục đầu tư dài hạn |
| `mean_variance` | Mean-Variance | Tối đa hóa Sharpe hoặc tối thiểu phương sai | Khi có dự phóng lợi nhuận |
| `max_diversification` | Đa dạng hóa tối đa | Tối đa hóa tỷ lệ đa dạng hóa (DR) | Khi muốn danh mục có độ tương quan thấp |

### 1. `equal_volatility`

```json
{
  "optimizer": "equal_volatility",
  "optimizer_params": { "lookback": 60 }
}
```

**Ưu điểm**: Đơn giản, nhanh, không cần ma trận tương quan.
**Nhược điểm**: Bỏ qua tương quan chéo giữa các tài sản.

### 2. `risk_parity`

```json
{
  "optimizer": "risk_parity",
  "optimizer_params": { "lookback": 60 }
}
```

**Ưu điểm**: Tính toán cả tương quan, phân tán rủi ro đều hơn, cực kỳ bền bỉ trong dài hạn. (Khuyên dùng)
**Nhược điểm**: Cần giải thuật lặp, nhạy cảm với ma trận hiệp phương sai.

### 3. `mean_variance`

```json
{
  "optimizer": "mean_variance",
  "optimizer_params": { "lookback": 60, "risk_free": 0.0 }
}
```

**Lời khuyên**: Đừng để `lookback` quá ngắn (`<30` rất dễ bị quá khớp - overfit), và nên thêm các giới hạn tỷ trọng.

### 4. `max_diversification`

```json
{
  "optimizer": "max_diversification",
  "optimizer_params": { "lookback": 60 }
}
```

### Cây quyết định chọn Optimizer

```text
Bạn có dự phóng lợi nhuận không?
├── Có → mean_variance (nhớ thêm ràng buộc)
└── Không → Bạn có cần xét tương quan không?
    ├── Có → risk_parity (Khuyên dùng)
    └── Không → Độ chênh lệch biến động giữa các tài sản có lớn không?
        ├── Có → equal_volatility
        └── Không → max_diversification
```

## Chiến lược Tái cân bằng (Rebalancing)

| Phương pháp | Điều kiện kích hoạt | Ưu điểm | Nhược điểm |
|------|---------|------|------|
| Định kỳ | Cố định hàng tháng/quý | Đơn giản, dễ tính chi phí | Có thể trễ nhịp thị trường |
| Ngưỡng | Lệch khỏi mục tiêu > X% | Chỉ giao dịch khi cần | Giao dịch nhiều khi thị trường giật mạnh |
| Biến động | VIX vượt ngưỡng | Thích ứng với thị trường | Khó chọn tham số |

**Tần suất gợi ý**:
- Cổ phiếu: Hàng tháng (±5%)
- Cổ phiếu + Trái phiếu: Hàng quý (±10%)
- Crypto: Hàng tuần/2 tuần (±15%)

Viết logic tái cân bằng trong `signal_engine.py`:
```python
if bar_count % rebalance_freq == 0:
    new_weights = calculate_target_weights(data_map)
    for code, weight in new_weights.items():
        signals[code].iloc[i] = weight
```
