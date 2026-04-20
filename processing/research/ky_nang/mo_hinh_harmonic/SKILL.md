---
name: mo_hinh_harmonic
description: Động cơ Tín hiệu Mô hình Harmonic (Hài hòa). Nhận diện các cấu trúc 5 điểm XABCD như Gartley/Bat/Butterfly/Crab dựa trên tỷ lệ hình học Fibonacci, và tạo tín hiệu giao dịch tại vùng PRZ (Vùng Đảo chiều Tiềm năng).
category: strategy
---

# Mô hình Harmonic (Harmonic Patterns)

## Mục đích

Trường phái hình học Fibonacci sử dụng các tỷ lệ chính xác để nhận diện các mô hình giá có xác suất đảo chiều cao:

| Mô hình | Mức thoái lui (Retracement) Điểm B | Mức thoái lui Điểm D | Hướng giao dịch |
|------|---------|---------|------|
| Gartley | 0.618 XA | 0.786 XA | Đảo chiều |
| Bat (Dơi) | 0.382-0.5 XA | 0.886 XA | Đảo chiều |
| Butterfly (Bướm) | 0.786 XA | 1.27 XA | Đảo chiều |
| Crab (Cua) | 0.382-0.618 XA | 1.618 XA | Đảo chiều |

## Các Khái niệm Cốt lõi

- **Cấu trúc 5 điểm XABCD**: Một hình thái giá được định nghĩa bởi các tỷ lệ Fibonacci cực kỳ nghiêm ngặt.
- **PRZ (Potential Reversal Zone)**: Vùng hội tụ xung quanh điểm D, nơi xác suất giá quay đầu là lớn nhất.
- Mô hình Bullish (Điểm D cắm xuống dưới đáy) → Tín hiệu Mua (Long).
- Mô hình Bearish (Điểm D đâm lên trên đỉnh) → Tín hiệu Bán (Short).

## Dependencies

```bash
pip install pyharmonics pandas numpy requests
```

## Tham số (Parameters)

| Tham số | Mặc định | Mô tả |
|------|--------|------|
| is_stock | False | Tài sản có phải là cổ phiếu không (Ảnh hưởng đến tham số phân tích độ nhiễu) |

## Quy ước Tín hiệu

- `1` = Long (Mua)
- `-1` = Short (Bán khống)
- `0` = Đứng ngoài quan sát
