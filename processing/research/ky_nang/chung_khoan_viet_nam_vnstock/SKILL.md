---
name: chung_khoan_viet_nam_vnstock
description: Nguồn Dữ liệu Chứng khoán Việt Nam — Tải dữ liệu Nến (OHLCV), Báo cáo Tài chính, Giao dịch Khối ngoại và Tự doanh của thị trường chứng khoán Việt Nam (HSX, HNX, UPCOM) thông qua thư viện vnstock.
category: data-source
---

# Nguồn Dữ liệu Chứng khoán Việt Nam (vnstock)

## Tổng quan

Để lấy dữ liệu chứng khoán Việt Nam một cách miễn phí và chính xác nhất, hệ thống sử dụng thư viện mã nguồn mở **`vnstock`** (phát triển bởi Thinh Vu). Thư viện này trích xuất dữ liệu trực tiếp từ các công ty chứng khoán lớn như TCBS, SSI, VNDirect mà không cần API Key phức tạp.

## Cài đặt (Installation)

```bash
pip install vnstock
```

## Hướng dẫn Khởi động Nhanh (Code Mẫu)

### 1. Lấy dữ liệu Giá Lịch sử (OHLCV)
Dữ liệu trả về mặc định đã được **điều chỉnh cổ tức/phát hành thêm** (Adjusted Prices).

```python
from vnstock import stock_historical_data
import pandas as pd

# Lấy dữ liệu nến Ngày (1D) của SSI
# Tham số: symbol, start_date, end_date, resolution, type
df = stock_historical_data(symbol='SSI', 
                            start_date='2023-01-01', 
                            end_date='2024-01-01', 
                            resolution='1D', 
                            type='stock')

print(df.head())
# Dữ liệu trả về gồm: time, open, high, low, close, volume, ticker
```

**Các khung thời gian (resolution) hỗ trợ:**
- Trong ngày (Intraday): `1`, `5`, `15`, `30`, `1H` (Thường chỉ lấy được lịch sử ngắn).
- Dài hạn: `1D` (Ngày), `1W` (Tuần), `1M` (Tháng).

### 2. Danh sách Mã Chứng khoán (Tickers List)
```python
from vnstock import listing_companies

# Lấy toàn bộ danh sách các mã đang niêm yết trên cả 3 sàn (HOSE, HNX, UPCOM)
df_listing = listing_companies()
print(df_listing.head())
```

### 3. Lấy Báo cáo Tài chính (Financial Reports)
```python
from vnstock import financial_report

# Lấy Bảng Cân đối kế toán (Balance Sheet) theo Năm
balance_sheet = financial_report(symbol='TCB', report_type='BalanceSheet', frequency='Yearly')

# Lấy Báo cáo Kết quả Kinh doanh (Income Statement) theo Quý
income_statement = financial_report(symbol='TCB', report_type='IncomeStatement', frequency='Quarterly')

# Lấy Báo cáo Lưu chuyển tiền tệ (Cash Flow)
cash_flow = financial_report(symbol='TCB', report_type='CashFlow', frequency='Quarterly')
```

### 4. Giao dịch Khối Ngoại & Tự Doanh (Institutions & Foreigners)
Đây là dữ liệu cực kỳ quan trọng để đánh giá Dòng tiền Thông minh (Smart Money) tại thị trường Việt Nam.

```python
from vnstock import stock_evaluation, fr_trade_historical

# Giao dịch Khối ngoại (Foreign Trade) theo ngày
foreign_flow = fr_trade_historical(symbol='VND', start_date='2023-01-01', end_date='2023-12-31')
# Trả về: Mua ròng, Bán ròng, Khối lượng...

# Chỉ số định giá cơ bản (P/E, P/B)
valuation = stock_evaluation(symbol='VND')
```

## Chuẩn hóa Định dạng Mã Giao dịch (Ticker) trong KAIROS

Khi tích hợp `vnstock` vào hệ thống KAIROS (qua file `config.json`), chúng ta quy ước thêm hậu tố `.VN` cho chứng khoán Việt Nam để tránh trùng lặp với các thị trường khác.

| Định dạng KAIROS | Định dạng vnstock | Ý nghĩa |
|---------------|----------------|---------|
| `SSI.VN` | `SSI` | Cổ phiếu SSI |
| `TCB.VN` | `TCB` | Ngân hàng Techcombank |
| `VNINDEX.VN` | `VNINDEX` | Chỉ số VN-Index |

Khi viết DataLoader, cần cắt bỏ đuôi `.VN` trước khi truyền vào hàm của `vnstock`.

## Cấu hình Chạy Backtest (`config.json`)

```json
{
  "source": "vnstock",
  "codes": ["SSI.VN", "VND.VN", "HCM.VN"],
  "start_date": "2020-01-01",
  "end_date": "2024-01-01",
  "interval": "1D",
  "initial_cash": 1000000000,
  "commission": 0.0015
}
```

## Cạm bẫy Tuyệt đối Phải Nhớ (Pitfalls)

1. **Giới hạn Rate Limit**: Các API ẩn của TCBS/SSI đằng sau `vnstock` có thể chặn IP của bạn (HTTP 403/429) nếu bạn tải dữ liệu quá nhanh (ví dụ: dùng vòng lặp For tải 500 mã liên tục không nghỉ). Luôn thêm `time.sleep(1)` giữa các vòng lặp tải mã mới.
2. **Nến Phút (Intraday Data)**: Dữ liệu nến phút (`1m`, `5m`) của Việt Nam rất nặng và thường chỉ truy xuất được lịch sử trong vòng vài tháng gần nhất do giới hạn từ máy chủ công ty chứng khoán. Đánh Backtest dài hạn bắt buộc phải dùng nến Ngày (`1D`).
3. **Giá Trần / Sàn**: Khác với Crypto/US, thị trường VN có biên độ giao dịch (HOSE 7%, HNX 10%, UPCOM 15%). Trong lúc Backtest, nếu mô hình của bạn khớp lệnh mua ở mức giá vượt quá giá Trần (Ceiling), lệnh đó trên thực tế sẽ không bao giờ khớp được. (Cần chú ý Slippage).
4. **T+2.5**: Chu kỳ thanh toán chứng khoán VN hiện tại là T+2.5 (Mua chiều thứ 2 thì chiều thứ 4 cổ phiếu mới về tài khoản để bán). Các mô hình Backtest thông thường hay bỏ qua việc "Giam hàng" này, dẫn đến lợi nhuận ảo (Day-trade trong ngày). Phải code thêm bộ đệm `lock_period` nếu chạy chiến lược ngắn hạn.
