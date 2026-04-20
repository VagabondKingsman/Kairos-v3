---
name: thong_ke_dinh_luong
description: "Các phương pháp Thống kê Định lượng (Quant statistics): Kiểm định ADF (Tính dừng), Cointegration (Đồng liên kết), Mô hình Biến động GARCH, Chẩn đoán Hồi quy, Bootstrap, và Kiểm định Giả thuyết."
category: analysis
---

# Các Phương pháp Thống kê Định lượng (Quant Statistics)

## Tổng quan

Đây là xương sống toán học của hệ thống KAIROS, bao gồm các phương pháp kiểm định chuỗi thời gian, mô hình hóa độ biến động, chẩn đoán lỗi của mô hình hồi quy và suy luận thống kê. Nó bảo vệ bạn khỏi việc tìm ra những quy luật "ảo" (Spurious regression) hoặc "ăn may" trong dữ liệu.

## Kiểm định Chuỗi Thời gian (Time-Series Tests)

### 1. Kiểm định ADF (Kiểm tra Tính Dừng - Stationarity)

**Tại sao lại quan trọng**: Đem một chuỗi dữ liệu "Không Dừng" (như Giá cổ phiếu) đi chạy Hồi quy (Regression) sẽ sinh ra những kết quả có R² cực cao nhưng hoàn toàn vô nghĩa (Spurious regression).

```python
from statsmodels.tsa.stattools import adfuller

def adf_test(series: pd.Series, significance: float = 0.05) -> dict:
    """
    Kiểm định ADF: H0 = Có nghiệm đơn vị (Không dừng), H1 = Chuỗi Dừng (Stationary)
    """
    result = adfuller(series.dropna(), autolag='AIC')
    return {
        'adf_statistic': result[0],
        'p_value': result[1],
        'is_stationary': result[1] < significance,
    }
```

**Bảng Chẩn đoán Tính Dừng:**
| Loại Dữ liệu | Trạng thái Thường gặp | Cách Xử lý (Treatment) |
|------|---------|---------|
| Giá (Price) | KHÔNG DỪNG (Non-stationary) | Tuyệt đối không dùng trực tiếp. Phải chuyển sang Tỷ suất sinh lời Log (Log returns). |
| Log Returns | DỪNG (Stationary) | Xài trực tiếp vô tư. |
| P/E, P/B | Thường Không Dừng | Tính mức thay đổi (Delta) hoặc lấy Log. |
| Độ biến động (Vol) | Thường Dừng | Xài trực tiếp. |

### 2. Kiểm định Đồng liên kết (Cointegration Test)

**Mục đích**: Tìm xem 2 tài sản Không Dừng có một mối quan hệ cân bằng trong dài hạn hay không (Đây là Chén Thánh của chiến lược Pair Trading).

```python
from statsmodels.tsa.stattools import coint

def cointegration_test(y: pd.Series, x: pd.Series) -> dict:
    """
    Kiểm định Engle-Granger 2 bước. H0: Không có Đồng liên kết.
    """
    score, p_value, critical = coint(y, x)
    return {
        'test_statistic': score,
        'p_value': p_value,
        'is_cointegrated': p_value < 0.05,
    }
```

### 3. Kiểm định Nhân quả Granger (Granger Causality)

Kiểm tra xem dữ liệu lịch sử của biến X có giúp dự báo biến Y tốt hơn không. (Lưu ý: Đây là nhân quả về mặt "dự báo", không phải nhân quả "vật lý").

## Mô hình Hóa Biến động GARCH

### Mô hình GARCH(1,1) Tiêu chuẩn

Dùng để mô phỏng và dự báo rủi ro bùng nổ của thị trường.
```text
Lợi nhuận: r_t = μ + ε_t
Biến động (Phương sai): σ²_t = ω + α×ε²_{t-1} + β×σ²_{t-1}

Ý nghĩa Tham số:
- ω (omega): Mức nền biến động dài hạn.
- α (alpha): Độ sốc (Cú sập hôm qua ảnh hưởng bao nhiêu tới hôm nay).
- β (beta): Quán tính (Biến động của hôm qua còn lưu đọng lại bao nhiêu cho hôm nay).
- α + β: Độ lỳ của bão (Volatility persistence). Càng sát 1, bão càng lâu tan.
```

**Đặc điểm GARCH của Crypto (BTC/ETH):**
- `α` thường rất to (0.05-0.20): Thị trường Crypto cực kỳ nhạy cảm với tin tức FUD/FOMO. Sốc 1 phát là nổ bão ngay.
- Tính đối xứng: Khác với Chứng khoán Mỹ (Nơi giá giảm thì Volatility tăng vọt, giá tăng thì Volatility giảm), Crypto có Volatility khổng lồ ở cả hai chiều (Lên cũng sốc mà xuống cũng sốc).
- Volatility Dài hạn: Thường neo ở mức rất cao (60-80% / năm).

## Chẩn đoán Hồi quy (Regression Diagnostics)

Bất cứ khi nào bạn chạy một mô hình Tuyến tính (OLS), phải check list này:

1. **Kiểm định Phương sai Sai số thay đổi (Heteroskedasticity)**: Dữ liệu tài chính luôn bị lỗi này (Lúc bão thì sai số to, lúc êm đềm sai số nhỏ). Bắt buộc phải dùng `HAC standard errors (Newey-West)`.
2. **Kiểm định Tự tương quan (Autocorrelation - Ljung-Box test)**: Giá hôm nay có bị ảnh hưởng bởi quán tính giá hôm qua không?
3. **Đa cộng tuyến (Multicollinearity - VIF)**: Bỏ 2 chỉ báo Kỹ thuật y hệt nhau (ví dụ SMA20 và EMA20) vào cùng 1 mô hình AI -> Lỗi Đa cộng tuyến. VIF > 10 là vứt mô hình đi.

## Phương pháp Lấy Mẫu Lại (Bootstrap)

Dùng để kiểm tra xem chỉ số Sharpe Ratio của bạn có phải do "ăn may" mà có không.

```python
def bootstrap_sharpe(returns: pd.Series, n_bootstrap: int = 10000) -> dict:
    """Xáo trộn lại chuỗi lợi nhuận 10,000 lần để tính khoảng tin cậy 95% của Sharpe."""
    # Nếu Khoảng tin cậy thấp nhất (Lower bound) vẫn > 0
    # -> Chiến lược của bạn THỰC SỰ CÓ TÀI NĂNG (Alpha thật).
```

## Giải quyết Vấn đề "Nghiện Backtest" (Multiple-Testing)

Nếu bạn lấy 100 cái Chỉ báo Kỹ thuật khác nhau, cho nó chạy rà soát dữ liệu quá khứ, kiểu gì cũng có 5 cái chỉ báo ngẫu nhiên sinh ra lợi nhuận khủng khiếp (với p-value < 0.05).
Đây gọi là lỗi rà dữ liệu (Data Snooping / P-hacking).

**Cách KAIROS giải quyết:**
- Luôn phải dùng phương pháp điều chỉnh **FDR (Benjamini-Hochberg)** hoặc Out-of-sample test.

## Định dạng Đầu ra Báo cáo

```markdown
## Báo cáo Kiểm định Thống kê Định lượng

### 1. Kiểm định Tính Dừng (Stationarity)
| Chuỗi Dữ liệu | ADF Statistic | p-value | Kết luận |
|------|----------|-----|------|
| Giá BTC_Spot | -1.23 | 0.65 | KHÔNG DỪNG (Cấm xài) |
| Log Return BTC | -15.8 | 0.000 | DỪNG *** (An toàn) |

### 2. Kiểm định Cặp Giao dịch (Cointegration)
| Cặp (Pair) | Statistic | p-value | Có Đồng Liên kết? |
|------|--------|-----|------|
| BTC / ETH | -4.52 | 0.002 | Có ** |

### 3. Ước lượng Biến động GARCH
| Tham số | Giá trị | Ý nghĩa |
|------|-----|------|
| α (Sốc) | 0.15 | Thị trường đang rất nhạy cảm với tin tức |
| β (Quán tính)| 0.80 | Bão sẽ kéo dài |

### 4. Đánh giá Sharpe bằng Bootstrap
| Chỉ số | Điểm ước lượng | Khoảng tin cậy 95% | Kết luận (Có Alpha không) |
|------|--------|--------|------|
| Sharpe Ratio | 1.25 | [0.62, 1.88] | CÓ (Lower bound > 0) |
```
