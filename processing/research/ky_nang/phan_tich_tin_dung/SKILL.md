---
name: phan_tich_tin_dung
description: "Phân tích Tín dụng và Thu nhập cố định (Fixed Income): Xếp hạng tín nhiệm, Phân tích Spread (Phần bù rủi ro), Ước tính xác suất vỡ nợ (Altman Z-Score, Merton), Phân tích Trái phiếu rác / LGFV, và Quản trị Rủi ro Lãi suất (Duration/Convexity)."
category: analysis
---

# Phân tích Tín dụng (Credit Analysis)

## Tổng quan

Sử dụng kỹ năng này khi cần giải quyết các bài toán về:
- Định giá Trái phiếu, tính Lợi suất đáo hạn (YTM), Duration (Thời lượng) / Convexity (Độ lồi).
- Chấm điểm tín dụng doanh nghiệp, dự báo xác suất phá sản (Mô hình Altman, Merton).
- Kinh doanh chênh lệch lãi suất (Credit Spread Trading).
- Quản trị rủi ro lãi suất (DV01, Key Rate Duration).

---

## 1. Khung Phân tích Tín dụng

### 1.1 Hệ thống Xếp hạng Tín nhiệm (Credit Rating)

| S&P | Moody's | Ý nghĩa |
|-----|---------|------|
| AAA | Aaa | Chất lượng tuyệt đối, cực kỳ an toàn. |
| AA+, AA, AA- | Aa1, Aa2, Aa3 | Chất lượng cao, rủi ro vỡ nợ rất thấp. |
| A+, A, A- | A1, A2, A3 | Rủi ro thấp nhưng nhạy cảm với kinh tế vĩ mô. |
| BBB+, BBB, BBB- | Baa1, Baa2, Baa3 | Đầu tư cấp thấp nhất (Investment Grade - IG). |
| BB+, BB, B... | Ba1, Ba2, B... | Trái phiếu Đầu cơ / Rác (High Yield / Junk Bonds). |
| D | D | Đã vỡ nợ (Default). |

### 1.2 Mô hình Điểm Z Altman (Altman Z-Score)

Dùng để chẩn đoán tình trạng kiệt quệ tài chính (Phá sản). Phiên bản gốc áp dụng cho khối sản xuất niêm yết:

```text
Z = 1.2×X1 + 1.4×X2 + 3.3×X3 + 0.6×X4 + 1.0×X5
```

| Biến | Trọng số đo lường |
|------|------|
| X1 | Thanh khoản (Vốn lưu động / Tổng tài sản) |
| X2 | Tích lũy (Lợi nhuận giữ lại / Tổng tài sản) |
| X3 | Sức kiếm tiền (EBIT / Tổng tài sản) |
| X4 | Đòn bẩy (Vốn hóa / Tổng nợ) |
| X5 | Hiệu suất (Doanh thu / Tổng tài sản) |

**Ngưỡng phán quyết**:
- `Z > 2.99`: Vùng An toàn (An tâm ngủ ngon).
- `1.81 < Z < 2.99`: Vùng Xám (Có rủi ro, cần soi kỹ báo cáo dòng tiền).
- `Z < 1.81`: Vùng Đỏ (Báo động vỡ nợ).

### 1.3 Mô hình Cấu trúc Merton

Sử dụng toán học quyền chọn (Black-Scholes) để đo xác suất phá sản.
*Logic cốt lõi*: Vốn chủ sở hữu của 1 công ty thực chất là 1 Quyền chọn Mua (Call Option) đối với tổng tài sản của nó, với mức giá thực hiện (Strike price) chính là Tổng nợ.
- Nếu Tài sản > Nợ: Cổ đông trả nợ và giữ lại phần dư.
- Nếu Tài sản < Nợ: Cổ đông không thực hiện quyền chọn, công ty giao lại cho chủ nợ (Phá sản).

**Khoảng cách đến Vỡ nợ (Distance to Default - DD)**: 
Chỉ số DD càng lớn, xác suất vỡ nợ càng bằng 0. Khi DD tiến về 0 hoặc âm, rủi ro vỡ nợ là cực kỳ cao.

---

## 2. Định giá Thu nhập Cố định (Fixed Income)

### 2.1 Các Tham số Cốt lõi của Trái phiếu

- **Lãi suất Cuống phiếu (Coupon Rate)**: Lãi suất cố định trả hàng năm dựa trên Mệnh giá.
- **Lợi suất Đáo hạn (YTM - Yield to Maturity)**: Lợi suất nội bộ (IRR) nếu nhà đầu tư mua trái phiếu ở giá thị trường hiện tại và giữ nó cho đến lúc chết (đáo hạn). YTM là thước đo chuẩn xác nhất về độ đắt/rẻ của trái phiếu.
- **Luật bất thành văn**: Giá trái phiếu và YTM chạy ngược chiều. YTM tăng (Thị trường bán tháo) -> Giá trái phiếu giảm.

### 2.2 Quản trị Rủi ro Lãi suất

**Thời lượng Sửa đổi (Modified Duration - MD)**:
- Công cụ đo lường rủi ro quan trọng nhất.
- Ý nghĩa: Nếu Ngân hàng trung ương tăng lãi suất lên 1%, giá trái phiếu sẽ RỚT đúng bằng X% (Trong đó X là Duration).
- Trái phiếu kỳ hạn càng dài, Duration càng lớn, rủi ro biến động giá càng khốc liệt.

**Độ lồi (Convexity - CX)**:
- Duration chỉ là đường thẳng tuyến tính, nhưng thực tế biểu đồ giá trái phiếu bị cong (Độ lồi).
- Trái phiếu có Convexity cao luôn được săn đón, vì "Khi lãi suất giảm thì giá tăng cực mạnh, mà khi lãi suất tăng thì giá rớt ít hơn".

**DV01 (Dollar Value of 1 Basis Point)**:
- Nếu lãi suất nhích nhẹ 1 điểm cơ bản (0.01%), danh mục của bạn mất đi hoặc ăn được bao nhiêu USD? Đây là chỉ số Hedge (Phòng vệ) bắt buộc cho các Quỹ.

---

## 3. Phân tích Phần bù Rủi ro (Credit Spread)

```text
Lợi suất Trái phiếu Doanh nghiệp = Lợi suất Phi rủi ro (Trái phiếu CP) + Phần bù Tín dụng (Credit Spread)
```

Phần bù tín dụng = Tiền chuộc rủi ro vỡ nợ + Tiền bù thanh khoản kém.

**Tín hiệu Vĩ mô từ Credit Spread**:
- **Spread thu hẹp**: Kinh tế hưng thịnh, tiền rẻ bơm ra, ai cũng dám chơi hàng rủi ro. Tín hiệu múc Cổ phiếu.
- **Spread phình to**: Nỗi sợ hãi bao trùm, vỡ nợ dây chuyền, dòng tiền tháo chạy về Trái phiếu chính phủ (Flight to quality). Tín hiệu Bán tháo Cổ phiếu.

**Chiến lược Giao dịch Spread**:
- *Nhận định kinh tế phục hồi*: Mua Trái phiếu rác (Rủi ro cao) + Bán khống Trái phiếu Chính phủ. (Ăn tiền khi Spread thu hẹp).
- *Nhận định kinh tế suy thoái*: Bán khống Trái phiếu Doanh nghiệp (Hoặc mua CDS) + Mua Trái phiếu Chính phủ. (Ăn tiền khi Spread phình to).

---

## 4. Các Chiến lược Phòng vệ (Immunization)

**Miễn dịch Thời lượng (Duration Matching)**:
- Làm sao để quỹ hưu trí không bị phá sản khi lãi suất thay đổi? Cấu trúc sao cho Duration của Tổng Tài sản = Duration của Tổng Nợ. Khi đó lãi suất chạy lên hay xuống, tổng tài sản ròng (NAV) vẫn không xi nhê.

**Khớp dòng tiền (Cash Flow Matching)**:
- Ghép nối từng đồng tiền thu được từ coupon để trả gốc+lãi cho nợ đúng ngày đúng tháng. Không có rủi ro tái đầu tư nhưng chi phí thiết lập cực kỳ cao và cứng nhắc.
