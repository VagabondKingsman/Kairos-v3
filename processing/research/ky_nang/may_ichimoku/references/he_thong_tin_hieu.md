# Hệ Thống Tín Hiệu Mây Ichimoku (Ichimoku Cloud)

## Giao cắt T-K (Tín hiệu Cốt lõi)

### Giao cắt Vàng - Golden Cross (Tín hiệu Tăng giá)
Đường Chuyển đổi (Tenkan-sen) cắt lên trên Đường Tiêu chuẩn (Kijun-sen):
- **Tín hiệu Mạnh**: Điểm cắt nằm ở PHÍA TRÊN đám mây Kumo.
- **Tín hiệu Trung bình**: Điểm cắt nằm BÊN TRONG đám mây Kumo.
- **Tín hiệu Yếu**: Điểm cắt nằm ở PHÍA DƯỚI đám mây Kumo.

### Giao cắt Tử thần - Death Cross (Tín hiệu Giảm giá)
Đường Chuyển đổi (Tenkan-sen) cắt xuống dưới Đường Tiêu chuẩn (Kijun-sen):
- **Tín hiệu Mạnh**: Điểm cắt nằm ở PHÍA DƯỚI đám mây Kumo.
- **Tín hiệu Trung bình**: Điểm cắt nằm BÊN TRONG đám mây Kumo.
- **Tín hiệu Yếu**: Điểm cắt nằm ở PHÍA TRÊN đám mây Kumo.

## Bộ Lọc Ba Lớp (Triple Filter)

Engine này sử dụng hệ thống lọc 3 lớp để đảm bảo chất lượng tín hiệu tốt nhất:
1. **Giao cắt T-K**: Điều kiện kích hoạt (Trigger).
2. **Vị thế của Giá so với Mây**: Giá nằm trên mây thì chỉ Mua, giá nằm dưới mây thì chỉ Bán.
3. **Màu sắc của Mây (Hướng của Mây)**: Mây tương lai (Senkou Span A > B) màu Xanh là mây Tăng, ngược lại là mây Giảm.

Tín hiệu giao dịch CHỈ được phát ra khi cả 3 điều kiện trên đồng thuận tuyệt đối.

## Yêu cầu Về Dữ liệu (Khởi động)

Hệ thống cần tối thiểu 78 cây nến (52 nến để tính mây + 26 nến dịch chuyển mây về phía trước) để có thể bắt đầu phát ra các tín hiệu hợp lệ đầu tiên.
