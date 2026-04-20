---
name: dieu_huong_du_lieu
category: data-source
description: Cây quyết định chọn nguồn dữ liệu. Hãy tải kỹ năng này TRƯỚC KHI thực hiện bất kỳ lệnh backtest hay tải dữ liệu nào để chọn nguồn dữ liệu tốt nhất.
---

## Tổng quan Nguồn Dữ liệu

| Nguồn | Thị trường | Yêu cầu API Key | Mạng lưới | Kỹ năng |
|--------|---------|---------------|---------|-------|
| yfinance | Chứng khoán Mỹ, Chứng khoán HK, ETFs, Forex | Không | Cần truy cập Yahoo Finance | yfinance |
| okx | Crypto (Sàn OKX) | Không | Cần truy cập okx.com | okx-market |
| ccxt | Crypto (Hơn 100 sàn) | Không | Cần truy cập API của sàn | ccxt |

## Cây Quyết Định (Decision Tree)

### Kịch bản Backtest (khi viết config.json)

Sử dụng `source: "auto"` — hệ thống chạy backtest sẽ tự động điều hướng (route) dựa trên định dạng mã giao dịch và tự động chuyển sang nguồn dự phòng nếu nguồn chính bị lỗi mạng.

Bạn KHÔNG CẦN chỉ định một nguồn dữ liệu cụ thể trong `config.json` trừ khi người dùng yêu cầu đích danh.

### Kịch bản Nghiên cứu / Phân tích (khi viết script Python)

1. Xác định loại thị trường từ yêu cầu của người dùng.
2. Chọn nguồn dữ liệu theo mức độ ưu tiên:

**Chứng khoán Mỹ**: yfinance
**Chứng khoán HK**: yfinance
**Crypto**: okx (một sàn) > ccxt (đa sàn)
**Forex**: yfinance

3. Tải kỹ năng tương ứng để xem chi tiết API: ví dụ `load_skill("yfinance")`

### Kiểm tra Tính khả dụng

- **yfinance / okx / ccxt**: Hoàn toàn miễn phí nhưng có thể bị hạn chế do mạng.
- Nếu người dùng báo lỗi "connection timeout" (hết hạn kết nối) hoặc "cannot access" (không thể truy cập), hãy linh hoạt chuyển đổi nguồn dữ liệu.

## Bảng Định dạng Mã giao dịch (Symbol Format)

| Thị trường | Định dạng | Ví dụ |
|--------|--------|---------|
| Chứng khoán Mỹ | `TICKER.US` | AAPL.US, MSFT.US |
| Chứng khoán HK | `NNN(N).HK` | 700.HK, 9988.HK |
| Crypto | `SYMBOL-USDT` | BTC-USDT, ETH-USDT |
| Forex | `XXX/YYY` | EUR/USD |

## Chuỗi Dự phòng (Fallback Chain) ở tầng Runner

Bộ chạy backtest đã được tích hợp sẵn cơ chế dự phòng tự động ở cấp độ thị trường:

```text
Người dùng yêu cầu AAPL.US (Chứng khoán Mỹ)
  -> phát hiện thị trường: us_equity
  -> thử kết nối yfinance: khả dụng -> dùng yfinance
  -> thành công (không cần cấu hình phức tạp)
```

Quá trình này hoàn toàn trong suốt với người dùng — họ chỉ việc xem kết quả.
