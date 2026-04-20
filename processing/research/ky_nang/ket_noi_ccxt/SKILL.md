---
name: ket_noi_ccxt
category: data-source
description: Thư viện CCXT lấy dữ liệu Crypto từ hơn 100+ sàn giao dịch. Lấy dữ liệu miễn phí, dùng làm nguồn dự phòng khi sàn OKX bị lỗi.
---

## Tổng quan

CCXT là một thư viện chuẩn hóa dữ liệu giao dịch tiền điện tử, hỗ trợ hơn 100 sàn bao gồm Binance, Bybit, OKX, Coinbase, Kraken, v.v. Việc lấy dữ liệu thị trường công khai (Nến OHLCV, Tickers, Order books) **KHÔNG cần API Key**.

- GitHub: https://github.com/ccxt/ccxt (Hơn 35k sao)
- Cài đặt: `pip install ccxt`

## Hướng dẫn Nhanh

```python
import ccxt

exchange = ccxt.binance({"enableRateLimit": True})

# Lấy nến OHLCV (Khung ngày)
ohlcv = exchange.fetch_ohlcv("BTC/USDT", "1d", limit=100)
# Trả về dạng mảng: [[timestamp, open, high, low, close, volume], ...]

# Lấy giá Ticker
ticker = exchange.fetch_ticker("ETH/USDT")
print(f"Giá ETH hiện tại: {ticker['last']}")
```

## Các Hàm quan trọng

| Hàm | Chức năng | Dữ liệu trả về |
|--------|-------------|---------|
| `fetch_ohlcv(symbol, timeframe, since, limit)` | Lấy nến lịch sử | `[[ts, o, h, l, c, v], ...]` |
| `fetch_ticker(symbol)` | Lấy giá hiện tại | `{last, bid, ask, volume, ...}` |
| `fetch_tickers(symbols)` | Lấy giá nhiều mã cùng lúc | `{symbol: ticker}` |
| `fetch_order_book(symbol, limit)` | Lấy sổ lệnh | `{bids, asks, timestamp}` |
| `fetch_trades(symbol, since, limit)` | Lịch sử khớp lệnh gần nhất | `[{price, amount, side, timestamp}, ...]` |

## Khung thời gian (Timeframes)

`1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `12h`, `1d`, `1w`, `1M`

**Lưu ý**: Không phải sàn nào cũng hỗ trợ tất cả các khung thời gian này. Sử dụng biến `exchange.timeframes` để kiểm tra các khung được sàn hỗ trợ.

## Định dạng Mã giao dịch (Symbol Format)

CCXT sử dụng dấu gạch chéo (slash): `BTC/USDT`, `ETH/BTC`, `SOL/USDT`.

Hệ thống tải dữ liệu (DataLoader) của dự án sẽ tự động chuyển đổi từ dạng gạch ngang `BTC-USDT` sang dạng gạch chéo `BTC/USDT` để tương thích.

## Lựa chọn Sàn giao dịch

Được cấu hình thông qua biến môi trường: `CCXT_EXCHANGE=binance` (Mặc định).

Các sàn phổ biến: `binance`, `bybit`, `okx`, `coinbase`, `kraken`, `bitget`, `gate`.

## Loader tích hợp sẵn

Dự án đã có sẵn một file DataLoader cho CCXT tại đường dẫn `backtest/loaders/ccxt_loader.py`. Nó đóng vai trò là nguồn dữ liệu dự phòng khi loader của OKX bị lỗi hoặc không có dữ liệu.

## Phân trang (Pagination)

Để lấy dữ liệu lịch sử quá dài, CCXT sử dụng phân trang thông qua tham số `since` (mốc thời gian tính bằng mili-giây). Bộ loader tích hợp sẵn của dự án đã tự động xử lý vòng lặp này (hỗ trợ kéo tối đa 200 trang).
