---
name: phan_tich_etf
description: "Phân tích ETF: Sàng lọc sản phẩm, so sánh mức phí, sai số mô phỏng (tracking error), đánh giá thanh khoản, ứng dụng chiến lược và khung cấu hình ETF định lượng."
category: asset-class
---

# Phân tích ETF (Exchange Traded Fund)

## Định vị

ETF (Quỹ hoán đổi danh mục) là công cụ cốt lõi cho đầu tư thụ động và phân bổ tài sản. Kỹ năng này bao gồm phương pháp lựa chọn ETF, phân tích sai số mô phỏng, và xây dựng các chiến lược luân chuyển (rotation) dựa trên dữ liệu.

---

## 1. Phân loại Sản phẩm ETF

### 1.1 Theo Tài sản Cơ sở

| Loại | Ví dụ | Đặc điểm |
|------|---------|------|
| **ETF Thị trường (Broad Market)** | SPY (S&P 500), QQQ (Nasdaq 100), DIA (Dow Jones) | Thanh khoản tốt nhất, chi phí rẻ nhất, phù hợp làm tỷ trọng cốt lõi (Core). |
| **ETF Ngành (Sector)** | XLF (Tài chính), XLV (Y tế), SMH (Bán dẫn) | Công cụ để đánh sóng ngành (Sector rotation). |
| **ETF Chủ đề (Thematic)** | ARKK (Công nghệ đột phá), URA (Uranium) | Tính đầu cơ cao, rủi ro lớn, chu kỳ sống ngắn. |
| **ETF Chiến lược / Smart Beta**| VIG (Cổ tức tăng trưởng), MTUM (Động lượng) | Dựa trên các nhân tố cụ thể (Factor), phí thường đắt hơn ETF thị trường. |
| **ETF Hàng hóa** | GLD (Vàng), USO (Dầu mỏ) | Được bảo chứng bằng hiện vật hoặc hợp đồng tương lai. Chú ý chi phí đảo hạn (Roll yield). |
| **ETF Trái phiếu** | TLT (Trái phiếu Mỹ 20+ năm), HYG (Trái phiếu Rác) | Nhạy cảm với lãi suất, dùng để quản trị rủi ro danh mục. |
| **ETF Đòn bẩy/Đảo chiều** | TQQQ (Nasdaq 3x), SQQQ (Nasdaq -3x) | Chỉ dùng đánh T+, CẤM ôm dài hạn vì hiệu ứng bào mòn (Volatility Decay). |

---

## 2. Các Chỉ số Cốt lõi của ETF

### 2.1 Sai số Mô phỏng (Tracking Error - TE)

Là chỉ số quan trọng nhất để đánh giá khả năng copy lại chỉ số gốc của một quỹ ETF.

```text
Sai số mô phỏng ngày = std(Lợi suất ngày của ETF - Lợi suất ngày của Chỉ số gốc)
Sai số mô phỏng năm = Sai số ngày × √252
```

**Nguyên nhân gây ra Sai số:**
1. Phí quản lý quỹ (Bị trừ rỉ rả mỗi ngày).
2. Xử lý cổ tức bị chậm trễ.
3. Chi phí trượt giá khi mua/bán cổ phiếu trong kỳ tái cơ cấu chỉ số.
4. Lượng tiền mặt nằm im trong quỹ (Cash drag).

### 2.2 Tỷ lệ Chi phí (Expense Ratio)

Chi phí là kẻ thù của lợi nhuận dài hạn. Một ETF S&P 500 như VOO chỉ có phí 0.03%/năm, trong khi các quỹ chủ động có thể thu 0.75%-1.0%.

```text
Lỗ hổng kép từ Chi phí = (1 - Phí_Năm)^Số_Năm
Ví dụ: Phí 0.5% so với phí 0.1%. Sau 20 năm chênh lệch lợi nhuận có thể lên tới 8-10%.
```

### 2.3 Chênh lệch Giá và Thanh khoản (Spread & Liquidity)

| Chỉ số | Ý nghĩa | Thế nào là Tốt? |
|------|------|--------|
| Khối lượng giao dịch ngày (ADV) | Khả năng thoát hàng dễ dàng | > 10 Triệu USD |
| Chênh lệch Mua/Bán (Bid-Ask Spread) | Chi phí giao dịch ẩn | < 0.05% |
| Tổng tài sản quản lý (AUM) | Rủi ro bị đóng quỹ (Liquidated) | > 500 Triệu USD |

---

## 3. Khung Sàng lọc và Chấm điểm ETF

Khi có nhiều quỹ ETF cùng mô phỏng một chỉ số (Ví dụ: SPY, VOO, IVV đều mô phỏng S&P 500), hãy dùng quy trình sau:

```text
Bước 1: Sàng lọc AUM → Loại bỏ các quỹ < 100 Triệu USD.
Bước 2: So sánh Phí → Chọn quỹ có tỷ lệ chi phí (Expense Ratio) thấp nhất.
Bước 3: Sai số mô phỏng → Ưu tiên quỹ có TE thấp nhất trong 1 năm qua.
Bước 4: Thanh khoản → Kiểm tra Spread và Khối lượng giao dịch.
```

---

## 4. Ứng dụng Chiến lược ETF

### 4.1 Chiến lược Cốt lõi - Vệ tinh (Core-Satellite)

```text
Tổng danh mục = Cốt lõi (70-80%) + Vệ tinh (20-30%)

Cốt lõi (Core): Ôm cứng các ETF Thị trường (như S&P 500, Toàn cầu) để ăn Beta của thị trường, phí cực rẻ, không bao giờ bán.
Vệ tinh (Satellite): Dùng ETF Ngành hoặc Smart Beta để tìm kiếm lợi nhuận đột biến (Alpha), có thể giao dịch chủ động.
```

### 4.2 Luân chuyển Động lượng (Momentum Rotation)

```python
def etf_momentum_rotation(etf_returns: pd.DataFrame, lookback: int = 60, top_n: int = 2) -> list[str]:
    """
    Chiến lược luân chuyển ETF dựa trên Động lượng (Momentum).
    Ví dụ: Đưa vào 10 ETF ngành của Mỹ, chọn ra 2 ngành mạnh nhất trong 3 tháng qua.
    """
    # Tính tổng lợi nhuận trong khung thời gian lookback
    momentum = etf_returns.tail(lookback).sum()
    # Chọn ra Top N ETF mạnh nhất
    selected = momentum.nlargest(top_n).index.tolist()
    return selected
```

### 4.3 Cẩn thận với Hiệu ứng Bào mòn của ETF Đòn bẩy (Beta Decay)

```text
ETF đòn bẩy duy trì mức đòn bẩy N lần MỖI NGÀY. Lãi kép hằng ngày sẽ khiến lợi nhuận dài hạn KHÔNG bằng N lần lợi chỉ số gốc.

Công thức Bào mòn (xấp xỉ) = N²(N-1)/2 × Biến động_Ngày² × Số ngày nắm giữ
```

**Kết luận thực chiến**: Tuyệt đối cấm sử dụng TQQQ (Nasdaq 3x) hay SQQQ để đầu tư ôm dài hạn. Nếu thị trường đi ngang (Sideway) và giật lên giật xuống, tiền của bạn sẽ bốc hơi sạch sẽ vì Beta Decay.

---

## 5. Dữ liệu và Phân tích Bằng `yfinance`

Vì hệ thống tập trung vào dữ liệu toàn cầu, chúng ta sử dụng `yfinance` thay cho các nguồn dữ liệu nội địa.

```python
import yfinance as yf
import pandas as pd
import numpy as np

def analyze_etf_tracking(etf_ticker: str, index_ticker: str, period: str = "1y"):
    """
    Phân tích Sai số mô phỏng (Tracking Error) giữa ETF và Chỉ số gốc.
    Ví dụ: etf_ticker="VOO", index_ticker="^GSPC" (S&P 500)
    """
    etf = yf.Ticker(etf_ticker).history(period=period)['Close']
    index = yf.Ticker(index_ticker).history(period=period)['Close']
    
    # Căn chỉnh dữ liệu
    df = pd.concat([etf, index], axis=1).dropna()
    df.columns = ['ETF', 'Index']
    
    # Lợi suất hàng ngày
    etf_ret = df['ETF'].pct_change().dropna()
    idx_ret = df['Index'].pct_change().dropna()
    
    # Độ lệch hàng ngày
    daily_diff = etf_ret - idx_ret
    tracking_error = daily_diff.std() * np.sqrt(252) * 100
    
    return {
        "Tracking_Error_Annualized_%": round(tracking_error, 4),
        "Max_Daily_Deviation_%": round(daily_diff.abs().max() * 100, 4)
    }
```
