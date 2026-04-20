---
name: do_bien_dong
description: Chiến lược Biến động (Volatility strategy). Giao dịch đảo chiều dựa trên Xếp hạng Phân vị (Percentile) của Biến động Lịch sử (HV). Phù hợp với mọi dữ liệu OHLCV. Đã được hỗ trợ bởi hệ thống nen_htf.
category: strategy
---

# Chiến lược Giao dịch Dựa trên Độ Biến Động (Volatility Strategy)

## Mục đích

Thị trường không di chuyển theo đường thẳng, mà nó luôn nén và bung. Chiến lược này tìm kiếm lợi nhuận từ tính chất Trở về giá trị trung bình (Mean Reversion) của độ biến động:
- Tích lũy vị thế (Gom hàng) ở những khu vực "Nén" (Độ biến động cực thấp), chờ đợi một cú bung nổ (Breakout).
- Chốt lời hoặc Bán khống (Short) ở những khu vực "Bung" (Độ biến động cực cao), chờ đợi sự tĩnh lặng quay lại.

## Logic Tín hiệu

1. **Tính toán Độ Biến động Lịch sử (HV)**: Độ lệch chuẩn của Tỷ suất sinh lời trong `hv_window` ngày qua, sau đó Thường niên hóa (Annualized).
2. **Xếp hạng Phân vị (Percentile Ranking)**: Xem mức độ Biến động hiện tại đứng thứ mấy trong lịch sử `lookback` ngày qua (Từ 0 đến 100 điểm).
3. **Phát tín hiệu**:
   - Phân vị < `low_pct` → MUA (Long). (Thị trường đang đi ngang tắt thanh khoản, bão sắp đến, biến động sẽ mở rộng).
   - Phân vị > `high_pct` → ĐÓNG LỆNH / BÁN KHỐNG (Short). (Thị trường đang dao động biên độ khổng lồ, đám đông đang cuồng loạn, rủi ro cao, biến động sẽ thu hẹp lại).
   - Nằm ở khoảng giữa → Giữ nguyên vị thế cũ (Hold).

## Chi tiết Thuật toán (Implementation)

- Tính HV = `returns.rolling(hv_window).std() * sqrt(annualize)` (annualize = 252 đối với Chứng khoán, 365 đối với Crypto).
- Tính Phân vị = `hv.rolling(lookback).rank(pct=True) * 100`

## Các Tham số `config.json`

| Tham số | Mặc định | Ý nghĩa |
|------|--------|------|
| `hv_window` | 20 | Cửa sổ tính toán Biến động (Dùng 20 ngày gần nhất) |
| `lookback` | 120 | Cửa sổ nhìn lại để Xếp hạng Phân vị (So sánh với 120 ngày qua) |
| `low_pct` | 20.0 | Ngưỡng Biến động Thấp (Nén chặt) - Tín hiệu Long |
| `high_pct` | 80.0 | Ngưỡng Biến động Cao (Giãn nở tột độ) - Tín hiệu Short |
| `annualize` | 252 | Hệ số thường niên hóa (Cổ phiếu Mỹ = 252, Crypto = 365) |

## Các Cạm bẫy Phải Lưu ý (Pitfalls)

1. **Dữ liệu Rỗng ban đầu**: Trước khi lấp đầy cửa sổ `lookback` (Ví dụ 120 ngày đầu tiên), hệ thống sẽ không có đủ dữ liệu để tính Phân vị. Phải dùng `fillna(0)` để đánh dấu là "Đứng ngoài thị trường" trong giai đoạn khởi động này.
2. **Độ Biến Động KHÔNG phải là Xu hướng**: Hệ thống phát lệnh MUA khi thị trường biến động thấp, điều này chỉ nói lên rằng **Biến động sắp bùng nổ**, chứ nó KHÔNG đảm bảo là giá sẽ tăng. (Giá hoàn toàn có thể bùng nổ cắm mỏ đi xuống). Do đó, chiến lược này thường được kết hợp với một Hệ thống Nhận diện Xu hướng (VD: Đường EMA, hoặc khung HTF D1).
3. **Thị trường Crypto không có ngày nghỉ**: Cấm dùng hệ số 252. Phải sửa thành 365.

## Quy ước Tín hiệu trong SignalEngine

- `1.0` = Long (Nén thanh khoản, mua chờ bung).
- `-1.0` = Short (Biến động cực độ, bán khống chờ tĩnh lặng).
- `0.0` = Flat (Đứng ngoài).
