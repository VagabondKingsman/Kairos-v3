---
name: tao_bao_cao
description: Trình tạo Báo cáo Nghiên cứu Tài chính chuyên nghiệp — Cấu trúc tiêu chuẩn (Tóm tắt / Quan điểm / Phân tích / Rủi ro / Khuyến nghị), Quy chuẩn Markdown, Hệ thống Xếp hạng và Từ vựng chuyên ngành.
category: tool
---

# Viết Báo cáo Nghiên cứu Chuyên nghiệp (Report Generation)

## Tổng quan

Kỹ năng này giúp chuẩn hóa toàn bộ đầu ra (Output) của AI thành định dạng của một Báo cáo Nghiên cứu Tài chính Chuyên nghiệp (tương đương chuẩn của Morgan Stanley, Goldman Sachs). Toàn bộ Markdown xuất ra có thể dùng ngay để thuyết trình hoặc đưa ra quyết định đầu tư.

## Phân loại và Cấu trúc Báo cáo

### Các Phân loại

| Loại Báo cáo | Độ dài | Nội dung Cốt lõi | Kích hoạt khi User hỏi |
|------|------|---------|---------|
| Báo cáo Chuyên sâu (Deep-dive) | Dài | Phân tích tài sản + Định giá + Khuyến nghị Mua/Bán | "Phân tích mã BTC / SPY" |
| Báo cáo Ngành (Industry) | Vừa | Cấu trúc ngành + Xu hướng + Top mã Leader | "Nhận định mảng AI / RWA?" |
| Báo cáo Vĩ mô / Chiến lược | Vừa | Vĩ mô + Phân bổ dòng tiền | "Thị trường sắp tới thế nào?" |
| Báo cáo Backtest (Định lượng)| Ngắn | Hiệu suất + Phân tích Rủi ro + Cải tiến | (Sau khi chạy xong Backtest) |
| Bình luận Nhanh (Flash note) | Ngắn | Đánh giá Sự kiện + Tác động + Hành động | "Tin FED ra có ý nghĩa gì?" |

### Template Cấu trúc Chuẩn (Markdown)

```markdown
# [Tên Báo Cáo]

> **Xếp hạng**: MUA | **Vùng giá Mục tiêu**: $XX | **Giá hiện tại**: $XX
> **Nguồn**: KAIROS Quant System | **Ngày**: 2026-04-17

## Tóm tắt Điều hành (Executive Summary)

3-5 gạch đầu dòng, mỗi gạch 1-2 câu tóm gọn kết luận.
Sử dụng ngôn từ sắc bén, rõ ràng (Bullish / Bearish). KHÔNG nói nước đôi "có thể lên hoặc xuống".

## Luận điểm Đầu tư (Core Views)

### Luận điểm 1: [Tiêu đề 1 dòng đập vào mắt]
2-3 đoạn văn phân tích, bắt buộc có data chứng minh.

### Luận điểm 2: [Tiêu đề 1 dòng]
...

## Phân tích Chi tiết (Main Analysis)

### [Mục 1: Cấu trúc thị trường / Động lực Tăng trưởng / Dữ liệu On-chain]
Phân tích sâu...

### [Mục 2: Định giá / Kết quả Backtest]
Phân tích sâu...

## Cảnh báo Rủi ro (Risk Warnings)

1. [Rủi ro 1]: Miêu tả + Tác động + Xác suất xảy ra.
2. [Rủi ro 2]: ...

## Khuyến nghị Hành động (Actionable Recommendation)

Đề xuất lệnh rõ ràng: Chiều (Long/Short), Tỷ trọng vốn (Position size), và Thời gian nắm giữ (Horizon).

---
*Disclaimer: Báo cáo được tự động tạo bởi KAIROS AI. Chỉ dùng cho mục đích nghiên cứu, không phải là lời khuyên tài chính.*
```

## Hệ thống Xếp hạng (Rating System)

### Xếp hạng Tài sản (Equities/Crypto)

| Xếp hạng | Định nghĩa | Kỳ vọng Lợi nhuận (12 Tháng) | Hoàn cảnh sử dụng |
|------|------|-----------------|---------|
| MUA MẠNH (Strong Buy) | Cực kỳ Bullish, Độ tin cậy cao | > 30% | Rất rẻ + Cú hích (Catalyst) mạnh + Trend đang lên. |
| MUA (Buy) | Bullish | 15% - 30% | Cơ bản tốt + Định giá hợp lý. |
| TRUNG LẬP (Neutral) | Đi ngang / Không rõ biên | -5% ~ 15% | Định giá đúng, không có cú hích. |
| BÁN (Avoid/Sell) | Bearish | < -5% | Quá đắt / Dữ liệu vĩ mô hoặc On-chain xấu đi. |

### Xếp hạng Chiến lược Định lượng (Sau Backtest)

| Xếp hạng | Tín hiệu | Tiêu chuẩn |
|------|------|------|
| Ưu tiên Triển khai (High) | Tỷ lệ Lợi nhuận/Rủi ro xuất sắc | Sharpe > 1.5, Max Drawdown < 20% |
| Có thể Chạy (Allocatable)| Chạy được, rủi ro trong tầm kiểm soát | Sharpe > 1.0, Max Drawdown < 30% |
| Theo dõi (Watch) | Cần thu thập thêm dữ liệu Forward | Sharpe 0.5 - 1.0 |
| Vứt bỏ (Discard) | Quá sức nguy hiểm | Sharpe < 0.5 hoặc Drawdown > 40% |

## Tiêu chuẩn Trình bày Markdown

### Cấu trúc Bảng dữ liệu (Tables)

**Quy tắc lập bảng**:
- Ký hiệu tiền tệ và đơn vị phải rõ ràng ở tiêu đề cột (`Triệu USD`, `%`).
- Dữ liệu dự phóng thêm chữ `E` (`2025E`), dữ liệu thực tế thêm chữ `A` (`2024A`).
- Luôn giữ 1 chữ số thập phân cho Tỷ lệ phần trăm (`12.5%`).

### Xử lý Biểu đồ (Khi không thể vẽ Chart)

Vì Markdown text không thể render ảnh trực tiếp, hãy dùng Định dạng "Text Description + Table" thay thế:

```markdown
### Đường Cong Vốn (Equity Curve)

Tài khoản bắt đầu từ 1.00 vào 2024-01, leo lên đỉnh 1.85 vào 2024-05,
sau đó trải qua cú sụt giảm (Drawdown) -25.3% trong quý 3, và 
hiện tại đã vượt đỉnh lịch sử lên mức 2.10.

| Mốc Thời Gian | Net Value | Lãi Lũy Kế | Sự kiện Tương ứng |
|---------|------|---------|---------|
| 2024-01 | 1.00 | 0% | Khởi tạo hệ thống |
| 2024-05 | 1.85 | +85% | Đạt đỉnh chu kỳ Bull |
| 2024-09 | 1.38 | +38% | Đáy sụt giảm |
| Hiện tại | 2.10 | +110% | Vượt đỉnh Mới (ATH) |
```

## Cẩm nang Thuật ngữ Chuyên ngành (Terminology Guide)

Thể hiện đẳng cấp chuyên gia bằng cách dùng đúng từ vựng.

| Thay vì dùng từ Chợ búa | Hãy dùng từ Chuyên ngành |
|---------|---------|
| "Giá giảm / Rớt" | Điều chỉnh (Correction), Sụt giảm (Drawdown), Kéo ngược (Pullback) |
| "Giá tăng / Lên" | Phục hồi (Rebound), Bứt phá (Breakout), Củng cố xu hướng (Strengthened) |
| "Chưa biết được" | Bất ổn vĩ mô vẫn hiện hữu (Uncertainty remains), Cần theo dõi thêm (Needs monitoring) |
| "Mua đi" | Nâng tỷ trọng (Overweight), Tích lũy (Accumulate) |
| "Bán đi" | Hạ tỷ trọng (Underweight), Đứng ngoài (Stand aside) |
| "Rất rẻ" | Cung cấp Biên an toàn lớn (Margin of safety) |
| "Giá ảo / Đắt" | Phần bù rủi ro cạn kiệt (Valuation premium is elevated) |

## Lưu ý Sống còn

1. **Không dự báo giá chính xác như thầy bói**: Sử dụng Vùng giá (Ví dụ: `Mục tiêu $85,000 - $90,000` thay vì `$87,542`).
2. **Nguyên tắc "Kết luận trước, Bằng chứng sau"**: Giám đốc quỹ không có thời gian đọc lan man. Quăng kết luận ngay ở phần Tóm tắt.
3. **Mọi luận điểm đều phải gắn với Dữ liệu**: Cấm chém gió chay.
4. **Viết hai chiều**: Report Bullish vẫn phải liệt kê Cảnh báo rủi ro sập hầm. Report Bearish vẫn phải liệt kê yếu tố có thể gây Short-squeeze.
