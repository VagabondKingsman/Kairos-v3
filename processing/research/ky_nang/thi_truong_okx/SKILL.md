---
name: thi_truong_okx
description: "Cổng kết nối dữ liệu thị trường OKX (Cryptocurrency). Sử dụng REST API V5 để kéo toàn bộ dữ liệu Spot, Phái sinh, Options, Funding Rate, và Open Interest. Hoàn toàn miễn phí, không cần đăng nhập/API Key."
category: data-source
---

# Kéo Dữ liệu Thị trường Crypto từ OKX (OKX Market Data)

## Tổng quan

OKX V5 REST API cung cấp kho dữ liệu thị trường Crypto khổng lồ, bao gồm Giao ngay (Spot), Hợp đồng Tương lai Vĩnh cửu (Perpetual Swap), Tương lai Có kỳ hạn (Futures), và Quyền chọn (Options).
Mọi Endpoint về thị trường (Market-data) đều là **Công cộng (Public)**, gọi trực tiếp không cần API Key. Dữ liệu từ OKX - sàn giao dịch top 2 thế giới, đủ độ sâu và thanh khoản để đại diện cho toàn bộ thị trường.

## Bắt đầu Nhanh

- Yêu cầu Python 3.9+ và thư viện `requests`, `pandas`.

```bash
pip install requests pandas
```

**Ví dụ Kéo giá Spot mới nhất của Bitcoin:**

```python
import requests

BASE_URL = "https://www.okx.com/api/v5"

# Kéo giá BTC-USDT
resp = requests.get(f"{BASE_URL}/market/ticker", params={"instId": "BTC-USDT"})
data = resp.json()["data"][0]
print(f"Giá BTC mới nhất: {data['last']} USD")
print(f"Thay đổi 24h: {float(data['last']) / float(data['open24h']) * 100 - 100:.2f}%")
```

## Cấu trúc Tham số Cốt lõi (Parameters Format)

- **Định dạng Mã giao dịch (`instId`)**:
  - Giao ngay (Spot): `BTC-USDT`, `ETH-USDT`
  - Vĩnh cửu (Perpetual Swap): `BTC-USDT-SWAP`, `ETH-USDT-SWAP`
  - Tương lai (Delivery): `BTC-USDT-250328` (Đáo hạn vào Ngày 28 Tháng 03 Năm 25)
  - Quyền chọn (Options): `BTC-USD-250328-95000-C` (Đáo hạn - Strike - Call/Put)
- **Khung thời gian Nến (`bar`)**: `1m`, `3m`, `5m`, `15m`, `30m`, `1H`, `2H`, `4H`, `6H`, `12H`, `1D`, `1W`, `1M`
- **Loại tài sản (`instType`)**: `SPOT` (Giao ngay), `SWAP` (Vĩnh cửu), `FUTURES` (Tương lai), `OPTION` (Quyền chọn)
- **Định dạng Trả về**: Mặc định là JSON. Nếu `code="0"` nghĩa là thành công, kết quả nằm trong mảng `data`. Timezone luôn là UTC, định dạng Unix timestamp (milliseconds).

## Danh sách các Endpoint Quan trọng

| Số | Đường dẫn API | Chức năng (Danh mục) | Ý nghĩa Ứng dụng |
| ---: | :--- | :--- | :--- |
| 1 | `/market/ticker` | Lấy giá 1 mã | Lấy giá Last, Cầu/Cung tốt nhất, Khối lượng 24h. |
| 2 | `/market/tickers` | Lấy giá hàng loạt | Cực kỳ hữu dụng để scan toàn bộ 400+ coin trên sàn xem con nào đang tăng mạnh nhất. Dùng tham số `instType=SPOT`. |
| 3 | `/market/candles` | Nến OHLCV | Đầu vào bắt buộc cho mọi chiến lược Backtest Kỹ thuật. |
| 4 | `/market/books` | Sổ lệnh (Order Book)| Lấy Độ sâu thị trường để tính toán trượt giá (Slippage) hoặc đo lường Bất đối xứng Mua/Bán (Microstructure). |
| 5 | `/public/funding-rate` | Phí Funding | Kéo phí Funding Rate hiện tại (Nếu phí dương -> Phe Long phải trả tiền cho Short). |
| 6 | `/public/open-interest` | Hợp đồng Mở (OI) | OI tăng + Giá tăng = Trend cực kỳ khỏe. |
| 7 | `/market/trades` | Các lệnh khớp gần nhất | Phân tích dòng lệnh (Tape reading) xem Cá voi đang mua hay bán lệnh lớn. |

## Các lỗi thường gặp
1. Lỗi `instId` sai định dạng: Rất nhiều người quen gõ `BTCUSDT` theo kiểu Binance. Ở OKX, bắt buộc phải có dấu gạch ngang: `BTC-USDT`.
2. Quá giới hạn tần suất (Rate limit): Các endpoint công cộng của OKX cho phép gọi trung bình 20 lần / 2 giây. Nếu code vòng lặp quá nhanh sẽ bị ban IP. Hãy dùng `time.sleep()`.
