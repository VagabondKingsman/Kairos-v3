---
name: loc_co_ban
description: Bộ lọc Yếu tố Cơ bản — Sàng lọc cổ phiếu dựa trên PE/PB/ROE và các chỉ số tài chính khác để xác định cổ phiếu Giá trị (Value) hoặc Tăng trưởng (Growth). Tương thích với thị trường Mỹ, Quốc tế thông qua yfinance API.
category: flow
---

# Bộ lọc Cơ bản (Fundamental Factor Screening)

## Mục đích

Lọc các cổ phiếu bằng dữ liệu báo cáo tài chính (PE, PB, ROE, Vốn hóa, v.v.) để xây dựng một rổ (Universe) cổ phiếu Giá trị hoặc Tăng trưởng, làm nền tảng cho việc Backtest các chiến lược giao dịch tiếp theo.

## Nguồn Dữ liệu và Hỗ trợ

| Thị trường | Nguồn Dữ liệu | Phương thức | Chỉ số Hỗ trợ |
|--------|-----------|--------|------------------|
| Cổ phiếu Mỹ (US) | yfinance `Ticker.info` | Gọi API Trực tiếp | trailingPE, forwardPE, priceToBook, returnOnEquity, marketCap, dividendYield |
| Tiền mã hóa | yfinance / Các API On-chain | Custom | Vốn hóa (Market Cap), TVL (Dành cho DeFi) |

*(Lưu ý: Hệ thống đã loại bỏ sự phụ thuộc vào các nguồn dữ liệu nội địa Trung Quốc. Toàn bộ kiến trúc sử dụng API chuẩn toàn cầu như yfinance).*

## Logic Lọc Tín hiệu (Signal Logic)

### Bộ lọc Giá trị (Value Filter)

Nhắm vào các doanh nghiệp làm ăn có lãi, định giá rẻ nhưng chất lượng tài sản tốt.
1. `0 < PE < pe_max`: Định giá rẻ, loại bỏ các công ty đang thua lỗ (PE âm).
2. `PB < pb_max`: Giá thị trường không quá cao so với giá trị sổ sách.
3. `ROE > roe_min`: Doanh nghiệp phải đẻ ra tiền, có khả năng sinh lời hiệu quả.
4. NẾU thỏa mãn toàn bộ -> Mua (1), Nếu KHÔNG -> Đứng ngoài (0).

### Bộ lọc Tăng trưởng (Growth Filter)

Nhắm vào các công ty có tốc độ phát triển mạnh mẽ.
1. `PE_TTM < pe_ttm_max` (Chấp nhận PE cao hơn bộ lọc Giá trị).
2. `ROE > roe_min` (Sàn lợi nhuận tối thiểu).
3. `Market Cap > mcap_min` (Vốn hóa lớn hơn mức tối thiểu, loại bỏ các cổ phiếu rác/cổ phiếu siêu nhỏ rủi ro cao).

## Triển khai với `yfinance` cho Cổ phiếu Mỹ/Quốc tế

Dữ liệu cơ bản từ `yfinance Ticker.info` là dữ liệu theo thời gian thực (Point-in-time snapshot), không phải là dữ liệu chuỗi thời gian (Time-series) trong quá khứ. Do đó, kỹ năng này dùng để lọc danh mục "Tại thời điểm hiện tại" để chuẩn bị cho giao dịch thực, hoặc lấy danh sách đầu vào cho Backtest.

```python
import yfinance as yf

def screen_us_stocks(tickers, criteria):
    """Lọc cổ phiếu Mỹ dựa trên các bộ tiêu chí cơ bản."""
    passed = []
    for symbol in tickers:
        try:
            info = yf.Ticker(symbol).info
            pe = info.get("trailingPE")
            pb = info.get("priceToBook")
            roe = info.get("returnOnEquity")  # Số thập phân (VD: 0.25 = 25%)
            mcap = info.get("marketCap")

            # Bỏ qua nếu thiếu dữ liệu (Cổ phiếu mới IPO, bị hủy niêm yết)
            if pe is None or pb is None or roe is None:
                continue

            # Điều kiện Lọc
            if (0 < pe < criteria["pe_max"]
                and pb < criteria["pb_max"]
                and roe > criteria["roe_min"]
                and (mcap or 0) > criteria.get("mcap_min", 0)):
                
                passed.append({
                    "symbol": symbol,
                    "pe": round(pe, 2),
                    "pb": round(pb, 2),
                    "roe": round(roe * 100, 1),  # Quy đổi sang Phần trăm (%)
                    "mcap": mcap,
                })
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")

    return passed

# Ví dụ thực chiến: Lọc các cổ phiếu vốn hóa tỷ đô trong S&P 500
criteria = {
    "pe_max": 20, 
    "pb_max": 3.0, 
    "roe_min": 0.15, # Sinh lời > 15%
    "mcap_min": 10_000_000_000 # Vốn hóa > 10 Tỷ USD
}
universe = ["AAPL", "MSFT", "JNJ", "JPM", "XOM", "INTC", "AMD"]
results = screen_us_stocks(universe, criteria)
```

## Tham số Định tuyến (Parameters)

| Tham số | Mặc định | Mô tả |
|-----------|---------|-------------|
| `pe_max` | 20.0 | Trần của P/E (Loại bỏ bọn ngáo giá). |
| `pb_max` | 3.0 | Trần của P/B (Không mua tài sản bị bơm thổi quá mức). |
| `roe_min` | 15.0 | Sàn của ROE tính bằng % (Sàng lọc công ty in tiền tốt). |
| `pe_min` | 0.0 | Đáy của P/E (Loại bỏ ngay lập tức công ty Thua Lỗ). |
| `mcap_min`| 2T USD| Vốn hóa tối thiểu bằng USD. |

## Các Cạm bẫy Thường gặp (Pitfalls)

- **PE Âm**: Khi công ty làm ăn thua lỗ, EPS bị âm dẫn đến PE âm. Nhiều thuật toán sắp xếp PE từ thấp đến cao sẽ vô tình múc toàn cổ phiếu đang phá sản vì PE của chúng bị âm rất lớn. Luôn phải gài điều kiện `PE > 0`.
- **Đơn vị ROE**: Thư viện `yfinance` trả về ROE dạng thập phân (`0.15`), nhưng con người thường đọc là tỷ lệ phần trăm (`15%`). Hãy cẩn thận khi so sánh.
- **Dữ liệu Rác (NaN)**: Cổ phiếu mới lên sàn (IPO) sẽ không có PE quá khứ, hãy dùng hàm `dropna()` hoặc bỏ qua (như code ở trên) để tránh lỗi gián đoạn hệ thống.
- **Trọng số Danh mục**: Nếu có 20 cổ phiếu lọt qua bộ lọc, hãy chia đều tiền để mua cả 20 cổ phiếu đó, tỷ trọng `1/N`. Đừng All-in vào 1 mã duy nhất để tránh rủi ro phá sản cục bộ.

## Dependencies

```bash
pip install pandas numpy yfinance
```
