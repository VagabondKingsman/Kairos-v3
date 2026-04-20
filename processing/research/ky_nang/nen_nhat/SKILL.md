---
name: nen_nhat
description: Nhận diện mẫu hình nến Nhật (Candlestick pattern), triển khai thuần túy bằng thư viện pandas cho 15 mẫu hình nến kinh điển (5 mẫu nến đơn, 5 mẫu nến đôi, 4 mẫu nến ba), tổng hợp thành tín hiệu Mua/Bán tổng hợp.
category: strategy
---
# Nhận diện Mẫu hình Nến (Candlestick Patterns)

## Mục đích

Phát hiện 15 mẫu hình nến Nhật kinh điển và tạo ra tín hiệu giao dịch:

### Mẫu hình 1 nến (5)
| Mẫu hình | Tín hiệu | Mô tả |
|------|------|------|
| Hammer (Cây búa) | Bullish (Tăng) | Bóng dưới dài, thân nến nhỏ nằm ở đỉnh |
| Inverted Hammer (Búa ngược) | Bullish (Tăng) | Bóng trên dài, thân nến nhỏ nằm ở đáy |
| Shooting Star (Sao băng) | Bearish (Giảm) | Bóng trên dài, thân nến nhỏ ở đáy (xuất hiện sau đà tăng) |
| Doji | Neutral (Trung lập) | Giá mở cửa và đóng cửa gần bằng nhau |
| Spinning Top (Con xoay) | Neutral (Trung lập) | Thân nến nhỏ, bóng trên và bóng dưới dài xấp xỉ nhau |

### Mẫu hình 2 nến (5)
| Mẫu hình | Tín hiệu |
|------|------|
| Bullish Engulfing (Nhấn chìm tăng) | Bullish (Tăng) |
| Bearish Engulfing (Nhấn chìm giảm) | Bearish (Giảm) |
| Bullish Harami (Mẹ bồng con tăng) | Bullish (Tăng) |
| Bearish Harami (Mẹ bồng con giảm) | Bearish (Giảm) |
| Piercing Line (Đường xuyên thấu) | Bullish (Tăng) |
| Dark Cloud Cover (Mây đen bao phủ) | Bearish (Giảm) |

### Mẫu hình 3 nến (4)
| Mẫu hình | Tín hiệu |
|------|------|
| Morning Star (Sao mai) | Bullish (Tăng) |
| Evening Star (Sao hôm) | Bearish (Giảm) |
| Three White Soldiers (Ba chàng lính ngự lâm) | Bullish (Tăng) |
| Three Black Crows (Ba con quạ đen) | Bearish (Giảm) |

## Logic Tín hiệu

Các mẫu hình Tăng giá (Bullish) cộng 1 điểm, mẫu hình Giảm giá (Bearish) trừ 1 điểm. 
Mua (Long) khi tổng điểm > 0.
Bán (Short) khi tổng điểm < 0.
Đứng ngoài (Flat) khi tổng điểm = 0.

## Tham số cấu hình

| Tham số | Mặc định | Ý nghĩa |
|------|--------|------|
| `body_pct` | 0.1 | Ngưỡng tỷ lệ thân nến so với toàn bộ cây nến để được coi là Doji |
| `shadow_ratio` | 2.0 | Tỷ lệ bóng nến phải dài gấp bao nhiêu lần thân nến (áp dụng cho Búa/Sao băng) |

## Quy ước Tín hiệu

- `1` = Mua (Long)
- `-1` = Bán Khống (Short)
- `0` = Đứng ngoài (Stand aside)
