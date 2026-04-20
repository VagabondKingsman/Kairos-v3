---
name: du_bao_loi_nhuan
description: Dự phóng lợi nhuận và Phân tích Đồng thuận (Phương pháp Top-Down / Bottom-Up / Lợi nhuận bất ngờ SUE / Độ trễ giá PEAD / Động lượng thay đổi dự phóng), giúp bắt bắt các cơ hội giao dịch nhờ vào sự "vượt kỳ vọng".
category: analysis
---
# Dự phóng Lợi nhuận và Phân tích Đồng thuận (Earnings Forecast & Consensus)

## Tổng quan

Xây dựng tín hiệu giao dịch xoay quanh việc Dự phóng lợi nhuận doanh nghiệp và Sự sai lệch so với Dự báo Đồng thuận của thị trường (Market Consensus). 
**Logic Cốt lõi**: Giá cổ phiếu trong ngắn hạn được thúc đẩy bởi "Sự chênh lệch kỳ vọng". Việc bắt được sự chênh lệch này (Lãi thật lớn hơn Lãi dự đoán) mang lại giá trị to lớn hơn nhiều so với việc chỉ đoán ra đúng con số lợi nhuận tuyệt đối.

2 hướng chính: 
① Tự tính toán dự phóng và đem so sánh với kỳ vọng của thị trường.
② Theo dõi Động lượng của việc các Chuyên gia Phân tích (Analyst) cập nhật/điều chỉnh dự phóng.

## Các Khái niệm Cốt lõi

### 1. Phương pháp Dự phóng Từ Trên Xuống (Top-Down)

**Chuỗi dự phóng:**
```text
Dự báo Tốc độ tăng trưởng GDP → Tốc độ tăng trưởng Ngành → Tốc độ tăng doanh thu Ngành → Tốc độ tăng doanh thu Công ty Đầu ngành → Giả định Biên lợi nhuận → Dự phóng EPS (Lợi nhuận trên mỗi cổ phiếu).
```

**Áp dụng thực chiến (Ví dụ ngành Bán lẻ):**
| Cấp độ | Chỉ số | Logic Dự phóng |
|------|------|---------|
| Vĩ mô | GDP +5.0% | Tiêu dùng chiếm 60% GDP, dự kiến Tiêu dùng tăng +6%. |
| Ngành | Bán lẻ +8% | Xu hướng chuyển dịch sang hàng cao cấp. |
| Công ty | Vinamilk (VNM) | Tăng giá bán +5%, Sản lượng +3% -> Doanh thu ~+8%. |
| Lợi nhuận | Biên lợi nhuận 20% | Giá nguyên liệu đầu vào sữa bột giảm, chi phí bán hàng giữ nguyên. |
| EPS | Khoảng 4,500 VND | Lợi nhuận ròng / Tổng số cổ phiếu. |

**Dùng khi nào:** Định vị chu kỳ lợi nhuận của toàn thị trường, chọn sóng Ngành (Beta).

### 2. Phương pháp Dự phóng Từ Dưới Lên (Bottom-Up)

**3 Công thức chia nhỏ Doanh thu:**

```python
# Cách 1: Tách Lượng - Giá
revenue = volume * price
# Ví dụ Cổ phiếu Thép: Doanh thu = Khối lượng bán (Tấn) × Giá thép (VND/Tấn)

# Cách 2: Tách Dòng sản phẩm
revenue = sum(segment_revenue for segment in business_lines)
# Ví dụ Tập đoàn FPT: Doanh thu = Khối Viễn thông + Khối Phần mềm + Khối Giáo dục

# Cách 3: Tách Cửa hàng / Người dùng
revenue = stores * revenue_per_store  # Hoặc: users * ARPU
# Ví dụ MWG: Doanh thu = Số lượng siêu thị BHX × Doanh thu/siêu thị/tháng
```

**Các điểm mù về Lợi nhuận cần chú ý:**
- Biên lợi nhuận gộp: Biến động giá nguyên liệu đầu vào.
- Tỷ lệ Chi phí: Hiệu ứng quy mô kinh tế (Khi doanh thu bùng nổ, chi phí cố định giảm làm Lợi nhuận bung mạnh).
- Thuế suất: Doanh nghiệp hết hạn ưu đãi miễn thuế.

### 3. Lợi nhuận Bất ngờ Chuẩn hóa (SUE - Standardized Unexpected Earnings)

**Công thức:**
```python
SUE = (actual_EPS - consensus_EPS) / std(actual_EPS - consensus_EPS)
# consensus_EPS: Dự báo EPS đồng thuận của các Chuyên gia (Median).
# std: Độ lệch chuẩn của sai số dự báo trong 8 quý gần nhất.
```

**Ngưỡng tín hiệu (Thực chiến):**
| Vùng SUE | Ý nghĩa | Hành động |
|---------|------|---------|
| SUE > +2.0 | Vượt xa mọi kỳ vọng | MUA MẠNH |
| SUE +1.0 ~ +2.0 | Tích cực hơn kỳ vọng | MUA |
| SUE -1.0 ~ +1.0 | Đúng như kỳ vọng | Không có tín hiệu |
| SUE -2.0 ~ -1.0 | Kém hơn kỳ vọng | BÁN |
| SUE < -2.0 | Tệ hại | BÁN KHỐNG / THOÁT HÀNG MẠNH |

### 4. Hiện tượng Trôi giá Sau Báo cáo (PEAD - Post-Earnings Announcement Drift)

**Hiện tượng**: Sau khi ra báo cáo tài chính vượt kỳ vọng, giá cổ phiếu không tăng một mạch đến giá trị thực ngay lập tức, mà nó sẽ "tịnh tiến (drift)" liên tục trong 30-60 ngày tiếp theo do sự chậm chạp của các quỹ lớn.

**Triển khai Chiến lược PEAD:**
```python
# 1. Quét dữ liệu ngay Ngày ra Báo cáo tài chính.
# 2. Tính chỉ số SUE.
# 3. Lọc cổ phiếu có SUE > +1.5 -> Mua và nhắm mắt nắm giữ đúng 40 ngày giao dịch.
# 4. Lọc cổ phiếu có SUE < -1.5 -> Bán / Short.
```

### 5. Động lượng Cập nhật Dự báo của Chuyên gia

Khi một chuyên gia sửa lại (nâng/hạ) dự báo của họ, các chuyên gia khác thường làm theo (Hiệu ứng bầy đàn). 

**3 Chỉ số theo dõi:**
```python
# 1. Tỷ lệ Cập nhật (ERM - Expected Revision Momentum)
ERM = (Số chuyên gia Nâng dự báo - Số chuyên gia Hạ dự báo) / Tổng số chuyên gia
# ERM > 0.3 = Động lượng tốt, ERM < -0.3 = Động lượng xấu.

# 2. Mức độ thay đổi
eps_change_pct = (new_consensus - old_consensus_30d_ago) / abs(old_consensus_30d_ago)
# > +5% = Đáng chú ý.

# 3. Mức độ phân tán (Đồng thuận hay Tranh cãi?)
dispersion = std(all_analyst_EPS) / mean(all_analyst_EPS)
# > 0.3 = Các chuyên gia tranh cãi kịch liệt, rủi ro cao.
# < 0.1 = Rất đồng thuận, xác suất đúng cao.
```

## Định dạng Đầu ra (Output)

```markdown
## Phân tích Dự phóng Lợi nhuận — [Mã CP]

### Dự phóng Nội bộ (Tự làm)
- Phương pháp: [Top-Down / Bottom-Up]
- EPS Dự phóng: [X VND]
- Căn cứ: [Doanh thu tăng X%, Biên lợi nhuận Y%]

### Đối chiếu với Kỳ vọng Đồng thuận
- EPS Đồng thuận: [Y VND] (Từ X chuyên gia)
- Lệch so với Đồng thuận: [+X% / -X%]
- Chỉ số SUE: [+X.X]
- Mức độ tranh cãi (Dispersion): [Cao / Thấp]

### Động lượng Chuyên gia
- ERM: [+X.X] (Có N ông nâng dự báo, M ông hạ dự báo)
- Sự thay đổi trung bình 30 ngày: [+X%]

### Tín hiệu Khuyến nghị
- Tín hiệu SUE: [MUA MẠNH / BÁN MẠNH]
- Giao dịch theo PEAD: [Có / Không] (Giữ lệnh trong 40 ngày).
```

## Lưu ý
- Dữ liệu Đồng thuận EPS thường nằm ở các terminal trả phí (Bloomberg, FiinPro, WiChart). Các trang web miễn phí lấy dữ liệu có thể bị chậm.
- Báo cáo ước tính kết quả kinh doanh (trước khi ra báo cáo chính thức 15 ngày) thường là điểm "nổ" tín hiệu đầu tiên và quan trọng nhất.
- Đừng dùng PEAD cho các cổ phiếu Mid/Small Cap vô danh không có chuyên gia nào theo dõi (Số lượng Analyst < 3).
