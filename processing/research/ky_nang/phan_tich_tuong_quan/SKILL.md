---
name: phan_tich_tuong_quan
description: Phân tích Tương quan và Đồng liên kết — Tìm kiếm sự đồng pha, Phân tích chuyên sâu tương quan lợi nhuận, Phân cụm ngành, Tương quan thực tế (Realized correlation), Đồng liên kết Engle-Granger/Johansen, Chu kỳ bán rã (Half-life), Tỷ lệ phòng ứng bằng Kalman, và Chiến lược Giao dịch Cặp (Pairs trading).
category: analysis
---

# Phân tích Tương quan và Đồng liên kết (Correlation and Cointegration)

## Tổng quan

Phân tích tương quan là công cụ nền tảng cho chiến lược Giao dịch cặp (Pairs Trading), xây dựng danh mục, và quản trị rủi ro. Kỹ năng này trải dài từ việc tìm kiếm cặp tài sản, đo lường hệ số, cho đến kiểm định Đồng liên kết (Cointegration) và tự động tạo tín hiệu vào lệnh.

---

## Chế độ 1: Khám phá Đồng pha (Co-Movement Discovery)

**Sử dụng khi**: Đã có 1 tài sản mục tiêu, muốn quét toàn thị trường để tìm ra các tài sản giống hệt nó nhằm mục đích đánh cặp (Pairs trading) hoặc tìm hàng thay thế.

```python
# Quy tắc chọn lọc:
# > 0.8: Cực kỳ đồng pha (Đưa ngay vào kiểm định Đồng liên kết).
# 0.6 - 0.8: Tương quan vừa phải (Cần xem xét có cùng chung nhóm ngành/đặc tính không).
# < 0.6: Tương quan yếu (Bỏ qua).
# < -0.6: Tương quan nghịch cực mạnh (Dùng để Hedge rủi ro).
```

---

## Chế độ 2: Phân tích Tương quan Lợi nhuận Chuyên sâu

**Sử dụng khi**: Phân tích chi tiết 2 tài sản. Chạy các hệ số Pearson, Spearman, Beta (Hồi quy tuyến tính), Z-Score.

### Cẩm nang Chọn Hệ số Tương quan

| Hệ số | Giả định | Dùng khi nào | Không nên dùng khi |
|------|------|---------|--------|
| **Pearson** | Tuyến tính, phân phối xấp xỉ Chuẩn | Chuỗi lợi nhuận thông thường | Dữ liệu có đuôi mập (fat tails) hoặc quá nhiều giá trị dị biệt (outliers) |
| **Spearman** | Mối quan hệ đơn điệu | Phân tích xếp hạng / Lọc nhiễu outliers | Khi biên độ/độ lớn (magnitude) của giá có ý nghĩa quan trọng |
| **Kendall** | Tính nhất quán về thứ tự | Mẫu dữ liệu nhỏ | Mẫu dữ liệu quá lớn (tính toán chậm) |

**Nguyên tắc thực chiến**: Luôn báo cáo cả 3. Nếu Pearson và Spearman lệch nhau quá 0.1, chứng tỏ quan hệ giữa 2 tài sản bị cong (phi tuyến tính) hoặc bị phá vỡ bởi các cú sốc thiên nga đen. Khi đó hãy tin vào Spearman.

---

## Chế độ 3: Phân cụm Ngành (Sector Clustering)

**Sử dụng khi**: Đưa vào một mảng 100 tài sản, hệ thống sẽ tự động dùng thuật toán Học máy (Hierarchical clustering) để nhóm chúng thành các cụm (clusters). 

| Phương pháp Nối (Linkage) | Đặc điểm |
|------|------|
| **Ward** (Mặc định) | Tối thiểu hóa phương sai nội bộ cụm. Cụm sinh ra rất gọn gàng. Phù hợp nhất cho Tài chính. |
| **Complete** | Dùng khoảng cách tối đa. Các cụm sẽ rời rạc và dài. Dùng khi cần kiểm soát độ rủi ro tương quan cực đoan. |
| **Average** | Phương pháp thỏa hiệp. Nhạy cảm với nhiễu. |

---

## Chế độ 4: Kiểm định Đồng liên kết (Cointegration)

**SỰ KHÁC BIỆT CỐT LÕI**: Tương quan (Correlation) chỉ đo lường việc 2 tài sản có chạy cùng hướng hay không. Đồng liên kết (Cointegration) đo lường xem chúng có bị trói buộc với nhau bằng một **Trạng thái Cân bằng Dài hạn (Long-run equilibrium)** hay không.
* Hai tài sản có thể Tương quan cao nhưng KHÔNG Đồng liên kết (Ví dụ: Một tài sản tăng 5%, tài sản kia tăng 10% mãi mãi -> Cặp này sẽ banh xác nếu trade Pairs).*

### Phương pháp Engle-Granger 2 bước

Dùng cho việc phân tích đúng 1 Cặp (2 tài sản). Nhanh và hiệu quả.

```python
# Bước 1: Chạy Hồi quy OLS (y = βx + α) để tính Tỷ lệ phòng ứng (Hedge Ratio = β).
# Bước 2: Lấy phần dư (Residuals/Spread) chạy kiểm định rễ đơn ADF. 
# Nếu p-value của ADF < 0.05 -> Cặp tài sản này Đồng liên kết -> TRADE ĐƯỢC!
```

### Chu kỳ Bán rã (Half-Life)

Đo lường việc nếu Spread lệch khỏi mức cân bằng (Mean), thì mất bao lâu để nó co trở lại. Nó đóng vai trò là "Kỳ vọng Thời gian Nắm giữ" của một lệnh Pairs Trading.

| Half-Life | Ý nghĩa | Lời khuyên Giao dịch |
|-------|------|---------|
| < 5 ngày | Hội tụ cực nhanh | Đánh Intraday. Cẩn thận chi phí giao dịch (phí sàn/trượt giá) cắn hết biên lợi nhuận. |
| 5 - 20 ngày | Tốc độ lý tưởng | Vùng Vàng (Sweet spot) cho Pairs Trading. |
| 20 - 60 ngày | Hội tụ chậm | Đánh Swing, giữ lệnh trung hạn. Cần kiên nhẫn. |
| > 180 ngày | Gần như đi bộ ngẫu nhiên (Random walk) | Nguy hiểm. Đừng đánh Pairs với cặp này. |

### Bộ lọc Kalman (Kalman Filter) để tính Tỷ lệ Phòng ứng Động

Tỷ lệ Hedge Ratio tĩnh (OLS) thường bị lỗi thời khi thị trường thay đổi cấu trúc. Bộ lọc Kalman giúp Hedge Ratio tự động uốn lượn và cập nhật theo thời gian thực mỗi khi có cây nến mới. 

---

## Chế độ 5: Tương quan Liên thị trường (Cross-Market)

```text
| Cặp thị trường | Tương quan trung bình | Hướng dẫn dắt | Độ trễ |
|-------|---------|---------|------|
| Cổ phiếu Mỹ ↔ BTC | 0.1 - 0.4 | Mỹ dẫn dắt dòng tiền | < 1 ngày |
| BTC ↔ ETH | 0.7 - 0.9 | Đồng bộ cao | < 1 giờ |
| Vàng ↔ SP500 | -0.2 - 0.2 | Trú ẩn an toàn khi SP500 rớt | 0 |
```

### Sự sụp đổ Tương quan trong Khủng hoảng (Correlation Breakdown)

Trong điều kiện bình thường, Cổ phiếu và Trái phiếu ngược chiều nhau, giúp đa dạng hóa rủi ro. Tuy nhiên, khi xảy ra Khủng hoảng (Sụp đổ thanh khoản / Thiên nga đen), **Tất cả các hệ số tương quan sẽ tiến về 1**. Đám đông sẽ bán tháo mọi tài sản để lấy Tiền mặt. Đa dạng hóa danh mục sẽ hoàn toàn vô dụng.

---

## Quy trình tạo Tín hiệu Giao dịch Cặp (Pairs Trading)

```text
Bước 1: Sàng lọc
- Chạy hệ số Pearson > 0.6.
- Chạy Đồng liên kết Engle-Granger (p-value < 0.05).

Bước 2: Đánh giá Chất lượng Spread
- Tính Half-life: Lọc các cặp có thời gian từ 5 - 60 ngày.
- Kiểm tra tính dừng (Stationarity) bằng ADF.

Bước 3: Lập Tỷ lệ Hedge
- Cặp ổn định: Dùng OLS (Ví dụ: Mua 1 Cổ A, Bán khống 1.5 Cổ B).
- Cặp biến động cấu trúc: Dùng Kalman Filter.

Bước 4: Sinh Tín hiệu
- Tính Z-Score = (Spread hiện tại - Spread trung bình) / Độ lệch chuẩn của Spread.
- Z-Score > 2.0: Bán khống Cặp (Short Spread = Bán A, Mua B).
- Z-Score < -2.0: Mua Cặp (Long Spread = Mua A, Bán B).
- Z-Score về 0: Chốt lời (Take Profit).

Bước 5: Quản lý Rủi ro
- Nút thắt Stop-loss: Nếu Z-Score chạy ngược lên quá 4.0 -> Cắt lỗ.
- Half-life bất ngờ tăng gấp đôi -> Cấu trúc đồng liên kết đã gãy, thanh lý lệnh ngay.
```
