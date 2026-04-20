---
name: giao_dich_theo_cap
description: Chiến lược Giao dịch Cặp (Pair trading). Giao dịch đảo chiều về giá trị trung bình (Mean reversion) dựa trên Tỷ lệ (Ratio) hoặc Độ lệch (Spread) Z-score của hai tài sản có độ tương quan cao.
category: strategy
---
# Chiến lược Giao dịch Cặp (Pair Trading)

## Mục đích

Chọn ra đúng 2 tài sản có sự tương đồng mạnh mẽ (Ví dụ: BTC và ETH, hoặc Coca-Cola và Pepsi). Giám sát xem Tỷ lệ giá (Price ratio) của chúng chênh lệch bao xa so với đường trung bình lịch sử. Khi sự chênh lệch đạt tới mức cực đoan vô lý, tiến hành Bán khống tài sản bị định giá cao và Mua tài sản bị định giá thấp, chờ đợi chúng hội tụ trở lại (Mean reversion).

## Logic Tạo Tín hiệu

1. **Tính Tỷ lệ Giá (Ratio)**: `ratio = giá_A / giá_B`
2. **Đường Trung bình và Độ lệch chuẩn (Rolling)**: `mean = ratio.rolling(lookback).mean()`, `std = ratio.rolling(lookback).std()`
3. **Chỉ số Z-score**: `z = (ratio - mean) / std` (Đo lường xem sự chênh lệch này cách bao nhiêu độ lệch chuẩn).
4. **Luật vào lệnh**:
   - `Z < -entry_z` (Tỷ lệ quá thấp): Mua A, Bán khống B (Kỳ vọng tỷ lệ sẽ tăng lại).
   - `Z > +entry_z` (Tỷ lệ quá cao): Bán khống A, Mua B (Kỳ vọng tỷ lệ sẽ giảm).
   - `|Z| < exit_z`: Đóng toàn bộ vị thế (Chốt lời khi cặp tài sản hội tụ về mức trung bình).

## Lưu ý Triển khai

- Giao dịch cặp yêu cầu **CHÍNH XÁC 2 mã tài sản** (Độ dài mảng `codes` = 2).
- Mã đầu tiên là A (`leg1`), mã thứ hai là B (`leg2`).
- Tín hiệu của A và B luôn ngược chiều nhau: A mua thì B bán khống, và ngược lại.
- **Tỷ trọng vốn (Equal-weight)**: KAIROS cấp vốn 50% cho A và 50% cho B (Mô hình tỷ trọng tĩnh, chưa tính toán tỷ lệ phòng vệ Beta linh hoạt).

## Tham số Cấu hình (Parameters)

| Tham số | Mặc định | Mô tả |
|------|--------|------|
| `lookback` | 60 | Cửa sổ thời gian để tính đường trung bình (Ví dụ: 60 nến). |
| `entry_z` | 2.0 | Ngưỡng Z-score để vào lệnh (Khuyến nghị 2.0 tức là sự chênh lệch vượt quá 2 độ lệch chuẩn - Mức cực đoan 5%). |
| `exit_z` | 0.5 | Ngưỡng Z-score để chốt lời (Chờ nó hội tụ về sát 0). |

## Định dạng `config.json`

Ví dụ Chứng khoán Mỹ (yfinance):
```json
{
  "source": "yfinance",
  "codes": ["KO", "PEP"],
  "start_date": "2020-01-01",
  "end_date": "2024-12-31",
  "initial_cash": 1000000,
  "commission": 0.001
}
```

Ví dụ Crypto (OKX):
```json
{
  "source": "okx",
  "codes": ["BTC-USDT", "ETH-USDT"],
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_cash": 1000000,
  "commission": 0.001
}
```

## Cạm bẫy Cần tránh (Pitfalls)

- Danh sách `codes` chỉ được phép có 2 mã. Thừa hoặc thiếu sẽ gây lỗi.
- Trục thời gian (Index) của 2 tài sản phải khớp nhau hoàn toàn. Phải dùng phép Inner Join để cắt bỏ những ngày tài sản A giao dịch nhưng tài sản B nghỉ lễ, nếu không tỷ lệ (Ratio) sẽ bị tính sai.
- Trong giai đoạn đầu tiên (60 ngày `lookback`), Z-score sẽ là `NaN`. Bắt buộc phải `fillna(0)` để tránh lỗi tín hiệu.
- Đừng bao giờ tạo ra tín hiệu cùng chiều (Cùng Mua hoặc Cùng Bán) cho cả A và B. Giao dịch cặp là nghiệp vụ Long-Short Hedging (Phòng vệ 2 chiều).

## Quy ước Tín hiệu Đầu ra

- Tài sản A: `0.5` = Mua 50% vốn, `-0.5` = Bán khống 50% vốn, `0` = Đóng lệnh.
- Tài sản B: Tín hiệu luôn đảo dấu so với Tài sản A.
