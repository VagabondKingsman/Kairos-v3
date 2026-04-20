# Tính Toán 5 Đường Ichimoku

## Đường Chuyển đổi (Tenkan-sen)
```python
tenkan = (highest_high(9) + lowest_low(9)) / 2
```
Phản ánh mức giá trung bình của các đỉnh và đáy trong ngắn hạn (khoảng 2 tuần).

## Đường Tiêu chuẩn (Kijun-sen)
```python
kijun = (highest_high(26) + lowest_low(26)) / 2
```
Phản ánh mức giá trung bình trong trung hạn (khoảng 1 tháng). Kijun-sen được xem là "điểm cân bằng" của giá.

## Đường Dẫn trước A (Senkou Span A)
```python
span_a = (tenkan + kijun) / 2  # Dịch chuyển về phía trước 26 chu kỳ
```
Là trung bình cộng của Tenkan-sen và Kijun-sen, được vẽ tiến về phía trước 26 phiên.

## Đường Dẫn trước B (Senkou Span B)
```python
span_b = (highest_high(52) + lowest_low(52)) / 2  # Dịch chuyển về phía trước 26 chu kỳ
```
Là mức giá trung bình của đỉnh và đáy trong 52 phiên, được vẽ tiến về phía trước 26 phiên.

## Đường Trễ (Chikou Span)
```python
chikou = close  # Dịch chuyển lùi về quá khứ 26 chu kỳ
```
Mức giá đóng cửa hiện tại được vẽ lùi lại 26 phiên. Dùng để xác nhận xu hướng: Chikou nằm trên giá thì là xu hướng Tăng, nằm dưới giá là xu hướng Giảm.

## Đám Mây (Kumo)

Vùng không gian nằm giữa Span A và Span B được gọi là "Đám mây".
- Span A > Span B: Mây Tăng (Thường vẽ màu Xanh).
- Span A < Span B: Mây Giảm (Thường vẽ màu Đỏ).
- Độ dày của đám mây phản ánh sức mạnh của vùng Hỗ trợ / Kháng cự.
