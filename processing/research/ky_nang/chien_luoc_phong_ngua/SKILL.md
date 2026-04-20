---
name: chien_luoc_phong_ngua
description: Thiết kế Chiến lược Phòng vệ rủi ro (Hedging) bao gồm Beta Hedge, Phòng vệ bằng Quyền chọn (Options), Rủi ro Đuôi (Tail Risk), và Phòng vệ chéo tài sản. Tính toán tỷ lệ Hedge và đánh giá chi phí.
category: asset-class
---

# Thiết kế Chiến lược Phòng vệ (Hedging Strategy)

## Tổng quan

Thiết kế các kế hoạch phòng vệ có hệ thống cho các vị thế đang mở, bao gồm Phòng vệ tuyến tính (Hợp đồng Tương lai / ETF Bán khống) và Phòng vệ phi tuyến tính (Quyền chọn). Khẩu quyết cốt lõi: **Phòng vệ không làm biến mất rủi ro; nó chỉ đổi những khoản lỗ không xác định thành một khoản chi phí xác định.**

## Các Khái niệm Cốt lõi

### 1. Phòng vệ Beta (Dùng Hợp đồng Tương lai / ETF)

**Nguyên lý:** Triệt tiêu rủi ro hệ thống (Beta) của thị trường chung bằng cách bán khống Chỉ số, trong khi vẫn giữ lại phần lợi nhuận vượt trội (Alpha) của danh mục cổ phiếu/tài sản bạn chọn.

**Tính toán Tỷ lệ Phòng vệ (Hedge Ratio):**

```python
# Tỷ lệ phòng vệ tối thiểu hóa phương sai (Minimum-variance)
hedge_ratio = beta_portfolio * (portfolio_value / futures_value)

# Ví dụ: Nắm giữ danh mục Cổ phiếu Mỹ trị giá 10 triệu USD, Beta = 1.2
# Giá hợp đồng Tương lai E-mini S&P 500 (ES) = 5000, Giá trị 1 HĐ = 5000 × $50 = $250,000
# Số lượng Hợp đồng cần Bán khống (Short) = 1.2 × (10,000,000 / 250,000) = 48 Hợp đồng

# Cách ước tính Beta bằng Python:
import numpy as np
# Hồi quy OLS: Lợi nhuận danh mục = alpha + beta * Lợi nhuận chỉ số + epsilon
beta = np.cov(portfolio_returns, index_returns)[0][1] / np.var(index_returns)
```

**Lưu ý:** Hợp đồng tương lai luôn có Chênh lệch giá (Basis - Contango/Backwardation). Nếu bạn Short lúc thị trường Contango, bạn sẽ mất thêm chi phí Roll (Cuộn) hợp đồng.

### 2. Phòng vệ bằng Quyền chọn (Options Hedging)

#### Protective Put (Mua Bảo hiểm Rớt giá)

```text
Cầm Tài sản cơ sở + Mua Quyền chọn Bán (Put Option)
```
- **Chi phí:** Phí mua quyền chọn (Premium) (Khoảng 1-3% giá trị tài sản mỗi tháng).
- **Phạm vi bảo vệ:** Bảo vệ 100% nếu giá rơi thủng mức giá thực thi (Strike price).
- **Kịch bản dùng:** Sợ thị trường sập nhưng không muốn chốt lời cổ phiếu vì sợ mất vị thế.

**Ví dụ với Bitcoin:**
- Hold 10 BTC giá $65,000.
- Mua 10 Hợp đồng BTC Put Option Strike $60,000 đáo hạn cuối tháng.
- Nếu BTC sập về $40,000, bạn vẫn có quyền bán 10 BTC đó với giá $60,000. Lỗ tối đa bị khóa cứng.

#### Collar (Đeo Vòng Cổ)

```text
Cầm Tài sản cơ sở + Mua Put OTM (Bảo hiểm rớt giá) + Bán Call OTM (Bán quyền chốt lời)
```
- **Chi phí:** Gần như Miễn phí (Tiền bán Call đắp vào tiền mua Put).
- **Đánh đổi:** Bị cắt mất phần lợi nhuận nếu giá tăng vượt mức Call.
- **Kịch bản dùng:** Sẵn sàng hi sinh lợi nhuận đột biến để đổi lấy bảo hiểm miễn phí.

| Tham số | Xông xáo (Aggressive) | Cân bằng (Balanced) | Thận trọng (Conservative) |
|------|--------|--------|--------|
| Mua Put | ATM - 5% | ATM - 8% | ATM - 10% |
| Bán Call| ATM + 8% | ATM + 5% | ATM + 3% |
| Mức Lỗ Tối đa | -5% | -8% | -10% |
| Lợi nhuận Tối đa | +8% | +5% | +3% |

### 3. Phòng vệ Rủi ro Đuôi (Tail-Risk Hedging)

Đề phòng Thiên nga đen (Thị trường sập > 20% trong vài ngày).

**Chiến lược Mua Put siêu xa (Far OTM Put):**
```python
# Mua các quyền chọn Put nằm rất xa giá hiện tại (Delta ≈ -0.05 đến -0.10)
# Đặc điểm: 95% thời gian sẽ đáo hạn vô giá trị (Mất tiền), nhưng nếu Sập sẽ ăn x10, x20 lần.

# Quản lý chi phí: Tốn khoảng 3-4% danh mục mỗi năm. 
# Phong cách Nassim Taleb: Chịu những khoản lỗ nhỏ liên tục, để ăn một cú vỡ nợ khổng lồ của thị trường.
```

### 4. Phòng vệ Chéo Tài sản (Cross-Asset Hedging)

**Cổ phiếu - Trái phiếu (Stock-bond hedge):**
Cấu trúc 60/40 kinh điển (60% Cổ phiếu Mỹ / 40% Trái phiếu kho bạc Mỹ).
*Lưu ý: Năm 2022, khi Lạm phát tăng cao, cả Cổ phiếu và Trái phiếu cùng sập hầm, cấu trúc 60/40 thất bại nặng nề.*

**Cổ phiếu - Hàng hóa (Bảo vệ Lạm phát):**
Khi lạm phát tăng, Cổ phiếu rớt giá nhưng Hàng hóa (Dầu, Đồng) tăng giá -> Hàng hóa bảo vệ danh mục khỏi rủi ro lạm phát. Vàng (GLD) là công cụ tuyệt vời để chống rủi ro địa chính trị.

### 5. Các Phương pháp Tính Tỷ lệ Phòng vệ

```python
import numpy as np
from scipy import stats

# Cách 1: Hồi quy OLS (Đơn giản nhất, tĩnh)
slope, intercept, r, p, se = stats.linregress(hedge_returns, portfolio_returns)
hedge_ratio_ols = slope

# Cách 2: Phương sai Tối thiểu (Minimum variance)
covariance = np.cov(portfolio_returns, hedge_returns)[0][1]
variance_hedge = np.var(hedge_returns)
hedge_ratio_mv = covariance / variance_hedge

# Hướng dẫn chọn:
# Tái cân bằng theo tháng -> Dùng OLS
# Cần phòng vệ danh mục biến động cực mạnh -> Dùng Phương sai Tối thiểu.
```

## Các Cạm bẫy Sống còn

1. **Thanh khoản Quyền chọn**: Các quyền chọn quá xa (Deep OTM) thường có Spread rất rộng, chi phí trượt giá khi mua bảo hiểm là rất cao.
2. **Beta là một đồ thị ảo ảnh**: Beta thường thấp trong uptrend và giật rất cao trong downtrend (Nghĩa là khi bạn cần phòng vệ nhất, thì lượng Hợp đồng tương lai bạn Short thường không đủ để bảo vệ bạn).
3. **Collar bóp nghẹt lợi nhuận**: Chiến lược Collar khóa lợi nhuận phía trên, nếu tài sản vào siêu sóng (Super Bull Run), danh mục của bạn sẽ đứng im nhìn thiên hạ kiếm tiền.
4. **Phòng vệ Rủi ro Đuôi (Tail Hedging) đòi hỏi kỷ luật sắt**: Vì 95% thời gian bạn sẽ bị trừ tiền bảo hiểm hằng tháng. Rất nhiều quỹ bỏ cuộc giữa chừng vì "thấy phí tiền quá", và ngay tháng sau đó Thiên nga đen xuất hiện.
