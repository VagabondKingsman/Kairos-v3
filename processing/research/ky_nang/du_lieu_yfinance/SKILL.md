---
name: du_lieu_yfinance
description: Giao diện dữ liệu Thị trường Toàn cầu yfinance — Tải dữ liệu Nến (OHLCV), Báo cáo Tài chính, Giao dịch Nội bộ, và Hành vi của Tổ chức cho Chứng khoán Mỹ, Hong Kong, ETF và Chỉ số (Indices) thông qua Yahoo Finance. Hoàn toàn Miễn phí, không cần API Key.
category: data-source
---

# Nguồn Dữ liệu yfinance (Yahoo Finance)

## Tổng quan

`yfinance` là thư viện mã nguồn mở khét tiếng bằng Python giúp "bòn rút" dữ liệu tài chính toàn cầu từ Yahoo Finance.
**Ưu điểm tuyệt đối**: HOÀN TOÀN MIỄN PHÍ. Không cần đăng ký, không cần API Key, không giới hạn phi lý.
Hệ thống KAIROS đã tích hợp sẵn DataLoader cho yfinance (`backtest/loaders/yfinance_loader.py`). Khi chạy backtest, chỉ cần set `source: "yfinance"` hoặc `source: "auto"` trong file `config.json`.

## Hướng dẫn Khởi động Nhanh

```bash
pip install yfinance pandas
```

```python
import yfinance as yf

# Lấy dữ liệu nến Ngày (Daily) của Apple trong năm qua
df = yf.download("AAPL", start="2025-01-01", end="2026-01-01", progress=False)
print(df.head())

# Lấy dữ liệu Cổ phiếu Hong Kong (Tencent)
df = yf.download("0700.HK", start="2025-01-01", end="2026-01-01", progress=False)
print(df.head())
```

## Chuẩn hóa Định dạng Mã Giao dịch (Ticker)

Hệ thống KAIROS dùng một định dạng ticker thống nhất. Khi dùng `yfinance_loader`, nó sẽ tự động dịch sang định dạng mà Yahoo Finance hiểu:

| Định dạng KAIROS | Định dạng yfinance | Thị trường |
|---------------|----------------|--------|
| `AAPL.US` | `AAPL` | Chứng khoán Mỹ |
| `MSFT.US` | `MSFT` | Chứng khoán Mỹ |
| `700.HK` | `0700.HK` | Chứng khoán Hong Kong |
| `9988.HK` | `9988.HK` | Chứng khoán Hong Kong |
| `SPY.US` | `SPY` | ETF Mỹ |

**Quy tắc ngầm:**
- **Cổ phiếu Mỹ**: Cắt bỏ đuôi `.US` -> Đưa về mã gốc.
- **Cổ phiếu HK**: Giữ nguyên đuôi `.HK`, nhưng phải thêm số 0 vào đầu cho đủ 4 chữ số (Ví dụ `700` phải biến thành `0700`).

## Các Phân hệ Dữ liệu được Hỗ trợ

### 1. Dữ liệu Giá Quá khứ (Historical OHLCV)

```python
# Cụ thể Khung thời gian (Interval)
# 1m/5m/15m/30m/1h/1d/1wk/1mo
df = yf.download("AAPL", start="2026-03-01", end="2026-03-30",
                 interval="1h", progress=False)  
```

**Giới hạn chết người của dữ liệu Nến Phút (Minute Data):**
- Nến `1m` (1 Phút): Chỉ cho phép tải tối đa **7 ngày** gần nhất.
- Nến `2m/5m/15m/30m/60m/90m`: Chỉ cho phép tải **60 ngày** gần nhất.
- Nến `1h` (1 Giờ): Tối đa **730 ngày** (2 năm).
- Nến `1d` (Ngày) trở lên: Vô hạn. Lấy từ lúc công ty lên sàn cũng được.

### 2. Thông tin Công ty (Company Info)

```python
ticker = yf.Ticker("AAPL")
info = ticker.info

print(f"Tên: {info.get('longName')}")
print(f"Vốn hóa: {info.get('marketCap')}")
print(f"Chỉ số P/E: {info.get('trailingPE')}")
print(f"Tỷ suất Cổ tức: {info.get('dividendYield')}")
```

### 3. Báo cáo Tài chính (Financial Statements)

```python
ticker = yf.Ticker("AAPL")

# Báo cáo Kết quả Kinh doanh (Theo Năm / Quý)
income = ticker.financials
income_q = ticker.quarterly_financials

# Bảng Cân đối Kế toán
balance = ticker.balance_sheet

# Báo cáo Lưu chuyển Tiền tệ
cashflow = ticker.cashflow
```

### 4. Dấu chân Tổ chức & Nội bộ (Holders & Insiders)

```python
ticker = yf.Ticker("AAPL")

# Các Quỹ đang nắm giữ (Institutional holders)
holders = ticker.institutional_holders

# Giao dịch của Cổ đông Nội bộ (CEO, CFO xả hàng)
insider = ticker.insider_transactions
```

### 5. Lấy Chỉ số Vĩ mô & Tiền tệ (Indices & FX)

```python
# Các Chỉ số lớn (Phải có dấu ^ ở đầu)
sp500 = yf.download("^GSPC", start="2025-01-01", end="2026-01-01", progress=False)  # S&P 500
nasdaq = yf.download("^IXIC", start="2025-01-01", end="2026-01-01", progress=False)  # NASDAQ

# Tỷ giá Ngoại tệ
usdcny = yf.download("CNY=X", start="2025-01-01", end="2026-01-01", progress=False)  # USD/CNY
eurusd = yf.download("EURUSD=X", start="2025-01-01", end="2026-01-01", progress=False) # EUR/USD
```

## Danh mục Mã Phổ biến (Ticker Cheat Sheet)

### Chứng khoán Mỹ (US Stocks)

| Mã | Công ty |
|--------|---------|
| AAPL | Apple |
| MSFT | Microsoft |
| GOOGL | Alphabet (Google) |
| NVDA | NVIDIA (Ông vua AI) |
| TSLA | Tesla |

### Cổ phiếu Hong Kong (HK Stocks)

| Mã KAIROS | Mã yfinance | Công ty |
|---------------|----------------|---------|
| 700.HK | 0700.HK | Tencent (Game/Wechat) |
| 9988.HK | 9988.HK | Alibaba (Thương mại điện tử) |
| 3690.HK | 3690.HK | Meituan (Giao đồ ăn) |
| 1810.HK | 1810.HK | Xiaomi (Điện thoại/EV) |

### Chỉ số & ETF Vĩ mô

| Mã | Tài sản |
|--------|-------|
| ^GSPC | Chỉ số S&P 500 |
| ^IXIC | Chỉ số NASDAQ Composite |
| ^HSI | Chỉ số Hang Seng (Hong Kong) |
| SPY | ETF đại diện S&P 500 |
| QQQ | ETF đại diện Công nghệ NASDAQ 100 |
| TLT | ETF Trái phiếu Mỹ 20 Năm+ |

## Cấu hình Chạy Backtest (Usage in `config.json`)

### Khai báo Cứng yfinance

```json
{
  "source": "yfinance",
  "codes": ["AAPL.US", "MSFT.US", "SPY.US"],
  "start_date": "2020-01-01",
  "end_date": "2026-03-30",
  "initial_cash": 1000000,
  "commission": 0.001
}
```

### Chế độ Tự Động Xuyên Thị trường (Cross-Market Auto)

```json
{
  "source": "auto",
  "codes": ["AAPL.US", "700.HK", "BTC-USDT", "ETH-USDT"],
  "start_date": "2024-01-01",
  "end_date": "2026-03-30",
  "interval": "1d",
  "initial_cash": 1000000,
  "commission": 0.001
}
```
**Quyền năng của chữ `"auto"`**: Hệ thống KAIROS sẽ tự động mổ xẻ mã giao dịch: Thấy `.US` hoặc `.HK` thì chui vào `yfinance` để lấy dữ liệu. Thấy có chữ `-USDT` thì chui qua sàn `OKX` để lấy dữ liệu Crypto.

## Cạm bẫy Tuyệt đối Phải Nhớ (Pitfalls)

1. **Bị Cấm IP (Rate Limits)**: Yahoo Finance không có API Key, nhưng nếu bạn gọi tải dữ liệu cả ngàn mã cùng một lúc liên tục, IP của bạn sẽ bị "Ban" (Cấm) vài giờ. Hãy tải hàng loạt (Batch Download) thay vì gọi vòng lặp `for` từng mã.
2. **Giá Điều chỉnh (Auto-adjust)**: Mặc định `yf.download(auto_adjust=True)` sẽ trả về giá Đã chia cổ tức/chốt quyền (Forward-adjusted). Tuy nhiên, Bộ Loader của KAIROS yêu cầu sử dụng `auto_adjust=False` để giữ nguyên giá trị thật trên đồ thị, sau đó tự tính toán bằng thuật toán nội bộ.
3. **Lệch Múi giờ (Timezone)**: Dữ liệu yfinance tải về thường có múi giờ Mỹ (EST). KAIROS Loader sẽ tự động tước bỏ (Strip) múi giờ này để đồng bộ với các sàn khác thành giờ UTC.
4. **Không hỗ trợ `extra_fields`**: Trong Backtest, Loader của yfinance chỉ trả về 5 cột OHLCV. Nếu bạn muốn lấy P/E, P/B trong quá khứ để chạy chiến lược Định giá, bạn **KHÔNG THỂ** lấy được. Muốn lấy P/E, phải gọi hàm `yf.Ticker().info` theo thời gian thực (Chỉ có giá trị hiện tại).
