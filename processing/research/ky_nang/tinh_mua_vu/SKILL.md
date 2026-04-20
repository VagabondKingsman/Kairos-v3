---
name: tinh_mua_vu
description: Chiến lược Tính Mùa vụ / Hiệu ứng Lịch (Seasonal / Calendar effect). Sinh tín hiệu giao dịch dựa trên các quy luật về thời gian như Hiệu ứng Tháng, Hiệu ứng Ngày trong tuần.
category: strategy
---

# Chiến lược Tính Mùa vụ & Hiệu ứng Lịch (Seasonal Effects)

## Mục đích

Lợi dụng các quy luật lặp đi lặp lại có tính thống kê về mặt thời gian trên thị trường tài chính để sinh tín hiệu. Ví dụ kinh điển: Hiệu ứng "Sell in May and Go Away" (Bán vào tháng 5), Hiện tượng "Santa Claus Rally" (Tăng giá Giáng sinh vào tháng 12).

## Logic Tạo Tín hiệu

### Hiệu ứng Tháng (Mặc định)

- Rơi vào các Tháng được cấu hình Tăng (Bullish months) → Sinh tín hiệu Mua (Long).
- Rơi vào các Tháng được cấu hình Giảm (Bearish months) → Sinh tín hiệu Bán khống (Short) hoặc Đứng ngoài.
- Rơi vào các Tháng trung lập → Báo tín hiệu `0` (Đóng vị thế / Đứng ngoài).

### Hiệu ứng Ngày trong Tuần (Weekday - Tùy chọn)

- Hiện tượng Thứ Hai (Monday effect) / Thứ Sáu (Friday effect).
- Hiện tượng Đầu tháng / Cuối tháng.

### Chế độ Kết hợp

Giao cắt giữa Tháng và Ngày: Tín hiệu = Tín hiệu Tháng × Tín hiệu Ngày. (Chỉ vô lệnh khi cả 2 điều kiện thời gian cùng đồng thuận).

## Bảng Tham chiếu Các Hiệu ứng Lịch Điển hình

| Tên Hiệu ứng | Mô tả | Cấu hình Tham khảo |
|------|------|---------|
| Santa Claus Rally | Tăng điểm mạnh vào cuối tháng 12 nhờ chốt sổ cuối năm của các Quỹ. | `bullish_months=[12]` |
| Sell in May | Hiệu suất thị trường Mỹ và Toàn cầu thường ảm đạm từ tháng 5 đến tháng 10. | `bearish_months=[5,6,7,8,9,10]` |
| Hiệu ứng Thứ Hai | Thứ Hai thường hay đỏ lửa vì tiêu hóa tin tức xấu cuối tuần. | `bearish_weekdays=[0]` |
| Hiệu ứng Thứ Sáu | Thứ Sáu thường hay xanh rờn. | `bullish_weekdays=[4]` |

## Tham số Cấu hình (Parameters)

| Tham số | Mặc định | Mô tả |
|------|--------|------|
| `bullish_months` | `[1, 2, 3, 11, 12]` | Danh sách các tháng ưu tiên Đánh Lên (Long). |
| `bearish_months` | `[5, 6, 7, 8, 9]` | Danh sách các tháng ưu tiên Đánh Xuống (Short). |
| `use_weekday` | `False` | Có bật bộ lọc Ngày trong Tuần hay không. |
| `bullish_weekdays`| `[4]` | Ngày Tốt trong tuần (`0` = Thứ Hai, `4` = Thứ Sáu). |
| `bearish_weekdays`| `[0]` | Ngày Xấu trong tuần. |

## Cạm bẫy Cần tránh (Pitfalls)

- Hàm `pd.DatetimeIndex.month` của Pandas tính tháng bắt đầu từ `1` (1 = Tháng 1).
- Hàm `pd.DatetimeIndex.weekday` của Pandas tính ngày bắt đầu từ `0` (0 = Thứ 2, 4 = Thứ 6, 6 = Chủ Nhật).
- **Chú ý Kích thước Mẫu**: Chiến lược mùa vụ mang nặng tính "Quy luật Thống kê" (Heuristics) chứ không phải tín hiệu Kỹ thuật chính xác. Nếu Backtest dữ liệu quá ngắn (ví dụ 2 năm), bạn sẽ chỉ có đúng 2 mẫu quan sát cho tháng 5 -> Kết quả vô nghĩa. Backtest mùa vụ phải chạy ít nhất 10 năm.
- Các tháng trung lập (Không nằm trong mảng Tốt hay Xấu) bắt buộc phải đẩy ra tín hiệu `0` (Clear position).

## Quy ước Tín hiệu Đầu ra

- `1` = Mua (Long) do nằm trong cửa sổ thời gian Tốt.
- `-1` = Bán khống (Short) do nằm trong cửa sổ thời gian Xấu.
- `0` = Đứng im chờ đợi.
