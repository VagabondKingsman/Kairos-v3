---
name: phan_tich_nen_phut
description: Phân tích và Backtest bằng dữ liệu nến Phút (Minute-level). Kéo dữ liệu nến phút qua API OKX/yfinance, dùng để tính toán các chỉ báo trong ngày (Intraday) hoặc làm đầu vào cho Engine Backtest.
category: strategy
---

# Phân tích và Backtest Dữ liệu Nến Phút (Minute-Level Analysis)

## Mục đích

Lấy dữ liệu nến ở khung thời gian cực nhỏ (Phút) thông qua các API, phục vụ cho việc tính toán các chỉ báo trong ngày (VWAP, TWAP, Phân phối dòng tiền) và Backtest các chiến lược giao dịch cao tần (Intraday).

Để chạy Backtest nến phút, chỉ cần cài đặt `"interval": "5m"` trong file `config.json` và hệ thống sẽ tự động điều hướng.

## Cấu hình Backtest Nến Phút

Thêm trường `interval` vào `config.json`:

```json
{
  "source": "okx",
  "codes": ["BTC-USDT"],
  "start_date": "2026-03-01",
  "end_date": "2026-03-15",
  "interval": "5m",
  "initial_cash": 1000000,
  "commission": 0.0005
}
```

- Hệ số thường niên hóa (Annualization factor) sẽ được tự động suy luận từ `source + interval` (Ví dụ: `OKX 5m = 365 ngày x 288 nến/ngày = 105120`).
- **Khuyến cáo kích thước dữ liệu**: Nến phút rất nặng. Nên giới hạn: `1m` không quá 7 ngày, `5m` không quá 30 ngày, và `1H` không quá 1 năm để tránh sập RAM.

## Nguồn dữ liệu hỗ trợ

| Nguồn Dữ liệu | Khung thời gian | Đặc điểm |
|--------|---------|------|
| **OKX** | 1m/5m/15m/30m/1H/4H | Thị trường Crypto, giao dịch 24/7, cực kỳ chi tiết. |
| **yfinance** | 1m/5m/15m/30m/1H | Chứng khoán Mỹ / Quốc tế (Miễn phí API, giới hạn 1m trong vòng 7 ngày gần nhất). |

*(Lưu ý: Hệ thống đã loại bỏ hoàn toàn việc sử dụng dữ liệu Tushare của chứng khoán nội địa Trung Quốc).*

## Kéo dữ liệu nến Phút từ OKX

```python
import requests
import pandas as pd

resp = requests.get("https://www.okx.com/api/v5/market/candles", params={
    "instId": "BTC-USDT",
    "bar": "1m",       # 1m/5m/15m/30m/1H/4H
    "limit": "300",    # Tối đa 300 nến mỗi lần gọi
})
data = resp.json()["data"]
columns = ["ts", "open", "high", "low", "close", "vol", "volCcy", "volCcyQuote", "confirm"]
df = pd.DataFrame(reversed(data), columns=columns)
df["ts"] = pd.to_datetime(df["ts"].astype("int64"), unit="ms")
for col in ["open", "high", "low", "close", "vol"]:
    df[col] = df[col].astype(float)
```

## Các Mẫu Tính toán Chỉ báo Intraday

### VWAP (Trung bình Giá Gia quyền theo Khối lượng)

Chỉ báo yêu thích của dòng tiền tổ chức để đánh giá xem họ đang mua đắt hay mua rẻ so với giá trị thực trong ngày.
```python
typical_price = (df["high"] + df["low"] + df["close"]) / 3
df["vwap"] = (typical_price * df["vol"]).cumsum() / df["vol"].cumsum()
```

### TWAP (Trung bình Giá Gia quyền theo Thời gian)

Được dùng để chẻ nhỏ lệnh lớn (Iceberg order) và khớp rải rác đều đặn qua từng phút.
```python
df["twap"] = df["close"].expanding().mean()
```

### Phân phối Khối lượng (Volume Distribution)

```python
df["vol_pct"] = df["vol"] / df["vol"].sum() * 100
hourly_vol = df.set_index("ts").resample("1h")["vol"].sum()
```

## Các Cạm bẫy Thường gặp (Pitfalls)

- OKX chỉ trả về 300 dòng mỗi lần gọi API. Trình tải dữ liệu (Loader) của KAIROS đã xử lý tự động phân trang (Pagination), nhưng nếu bạn kéo nến `1m` cho 1 năm, nó sẽ mất rất nhiều thời gian.
- **Phí giao dịch (Commission)**: Hãy set phí giao dịch cho nến phút cực thấp (ví dụ `0.0002` hoặc `0.0005`). Giao dịch nến phút đánh rất nhiều lệnh, nếu set phí `0.001` (0.1%), backtest của bạn sẽ luôn luôn lỗ sấp mặt.
- Timezone: Timestamp trả về thường là giờ UTC. Hãy cẩn thận khi đối chiếu với giờ mở cửa/đóng cửa của các phiên giao dịch (Ví dụ phiên Mỹ mở lúc 9:30 AM EST).
