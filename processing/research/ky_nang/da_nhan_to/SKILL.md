---
name: da_nhan_to
description: Xếp hạng cổ phiếu đa nhân tố (Multi-factor) theo mặt cắt ngang (Cross-sectional). Tính chuẩn hóa Z-score các nhân tố, chấm điểm tổng hợp và xây dựng danh mục Top N. Dành cho chiến lược phân bổ nhiều mã cùng lúc.
category: strategy
---

# Xếp hạng Đa Nhân Tố (Multi-Factor Cross-Sectional Ranking)

## Mục đích

Cùng tại một thời điểm (Mặt cắt ngang), tính toán nhiều tiêu chí (Nhân tố / Factor) khác nhau cho hàng loạt cổ phiếu/coin. Sau đó chuẩn hóa các điểm số này, cộng gộp lại thành Điểm Tổng Hợp, và chọn ra Top N tài sản đứng đầu để Mua.

## Logic Tạo Tín hiệu

1. **Tính toán Nhân tố**: Tính N chỉ số cho từng mã (ví dụ: Quán tính/Momentum, Giá trị/Value, Chất lượng/Quality, Thanh khoản).
2. **Chuẩn hóa Mặt cắt ngang (Cross-sectional)**: Tại ngày T, dùng Z-score để chuẩn hóa điểm của tất cả các mã (Trừ đi giá trị trung bình, chia cho Độ lệch chuẩn) để các nhân tố có thể cộng được với nhau.
3. **Chấm điểm Tổng hợp**: Cộng các Z-score lại (với trọng số bằng nhau hoặc tự định nghĩa) để ra `Composite Score`.
4. **Xếp hạng & Lọc**: Mua (Long) Top N mã điểm cao nhất. Trọng số mỗi mã = `1/N`.

## Các Nhân tố Tích hợp (Built-in Factors)

| Tên Nhân tố | Cách tính | Hướng tối ưu |
|--------|---------|------|
| `momentum` (Quán tính) | Lợi nhuận tích lũy N ngày qua | Dương (Càng cao càng tốt) |
| `reversal` (Đảo chiều) | Lợi nhuận 5 ngày gần nhất | Âm (Càng thấp càng tốt, vì dễ bị chốt lời) |
| `volatility` (Biến động)| Độ lệch chuẩn của nến ngày | Âm (Càng thấp càng tốt, ưu tiên an toàn) |
| `volume_ratio` (Đột biến KL)| Volume hôm nay / Trung bình Volume N ngày | Dương (Càng to càng tốt) |

Nếu kết hợp với API báo cáo tài chính (`yfinance`), bạn có thể thêm:
- `pe_factor`: 1 / PE (Càng to tức là định giá càng rẻ).
- `roe_factor`: ROE (Khả năng sinh lời, càng cao càng tốt).

## Tham số Cấu hình (Parameters)

| Tham số | Mặc định | Mô tả |
|------|--------|------|
| `momentum_window` | 20 | Số ngày tính Quán tính (Khoảng 1 tháng). |
| `vol_window` | 20 | Số ngày tính Độ biến động. |
| `top_n` | 3 | Số lượng mã được chọn mua. |
| `rebalance_freq` | 20 | Tần suất chốt lời/cắt lỗ và Đảo danh mục (Số nến). |

## Cạm bẫy Cần tránh (Pitfalls)

- **Số lượng mã tối thiểu**: Chuẩn hóa chéo (Z-score) bắt buộc danh mục (Universe) phải có ít nhất 3 mã. Nếu chỉ trade 1 mã duy nhất, kỹ năng này trở nên vô nghĩa.
- **Sự đảo ngược hướng**: Momentum thì số to là Tốt, nhưng Biến động thì số to là Xấu. Bắt buộc phải nhân với `-1` cho các nhân tố ngược chiều TRƯỚC KHI đem chuẩn hóa Z-score.
- **Tránh xáo trộn hàng ngày**: Chỉ Đảo danh mục (Rebalance) vào đúng ngày định trước (ví dụ 1 tháng 1 lần). Nếu ngày nào cũng tính lại và đảo danh mục, tiền phí giao dịch (Commission) sẽ ăn mòn hết lợi nhuận.
- **Trọng số Tín hiệu**: Chỉ gán mức 1/N cho các mã lọt Top, các mã còn lại ép về `0`.

## Quy ước Tín hiệu

- Tín hiệu `1/N` = Lọt vào Top N (Tiến hành Mua chia đều tiền).
- Tín hiệu `0` = Rớt khỏi Top N (Không mua / Bán bỏ nếu đang cầm).
