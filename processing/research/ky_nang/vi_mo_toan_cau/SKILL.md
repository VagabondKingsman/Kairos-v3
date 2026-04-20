---
name: vi_mo_toan_cau
description: Khung phân tích Vĩ mô Toàn cầu (Chính sách Ngân hàng Trung ương / Dự báo Tỷ giá / Rủi ro Địa chính trị / Dòng chảy Vốn), dùng để xây dựng các Tín hiệu Nhân tố Vĩ mô định hướng việc phân bổ tài sản chéo.
category: analysis
---

# Phân tích Vĩ mô Toàn cầu (Global Macro Analysis)

## Tổng quan

Xây dựng một lăng kính Vĩ mô từ 3 chiều không gian: Chính sách của Ngân hàng Trung ương (NHTW), Chế độ Tỷ giá Hối đoái, và Sự luân chuyển Dòng vốn Toàn cầu (Capital Flows). Hệ thống sẽ xuất ra các tín hiệu "Điểm số Vĩ mô" để ra quyết định nên Phân bổ vào đâu (Asset Allocation). 

**Nguyên lý cốt lõi:** Các Chu kỳ vĩ mô quyết định "Đại Xu Hướng" (Sóng lớn) của tài sản, còn việc "Vào Lệnh Ở Đâu" (Timing) thì giao phó cho các Kỹ năng Phân tích Kỹ thuật (Technical Analysis).

## Các Khái niệm Cốt lõi

### 1. Chuỗi Truyền dẫn Chính sách của Ngân hàng Trung ương (Central Bank Transmission)

```text
Thay đổi Lãi suất Điều hành → Đường cong Lợi suất Trái phiếu Chính phủ → Chênh lệch Tín dụng (Credit Spread) → Chi phí vay vốn của nền kinh tế thực → Lợi nhuận của Tập đoàn → Định giá Cổ phiếu (P/E).
```

**Khung giám sát 3 Bố già NHTW lớn nhất:**

| Ngân hàng Trung ương | Chỉ số Cốt lõi cần soi | Tín hiệu Chặn đầu (Forward) | Xác nhận Chạy theo (Lagging) |
|------|---------|---------|---------|
| FED (Mỹ) | Fed Funds Rate (FFR), Biểu đồ Dot-plot | Cục đo lường xác suất CME FedWatch | Bảng lương Phi nông nghiệp (NFP) / CPI / PCE |
| ECB (Châu Âu) | Main refinancing rate | PMI Eurozone, HICP | Tăng trưởng Tín dụng |
| BOJ (Nhật Bản) | Giới hạn YCC, Lãi suất âm/dương | Tỷ giá JPY/USD, Lợi suất Trái phiếu JGB | Core CPI Nhật Bản |

### 2. Khung Dự báo Tỷ giá (Exchange Rate Framework)

**Mô hình 3 tầng:**

| Mô hình | Tầm nhìn | Biến số Cốt lõi | Độ chính xác |
|------|---------|---------|------|
| Cân bằng Sức mua (PPP) | 3-5 năm | Chênh lệch CPI giữa 2 quốc gia | Mỏ neo dài hạn |
| Ngang giá Lãi suất (UIP/CIP)| 3-12 tháng | Chênh lệch Lãi suất + Hợp đồng kỳ hạn | Định hướng Trung hạn |
| Mô hình BEER | 1-3 năm | Dòng vốn ròng FDI/FII + Năng suất | Ước tính Cân bằng |

### 3. Theo dõi Dòng Vốn Toàn cầu (Global Capital Flows)

Bám theo "Dấu chân của Tiền Thông Minh" (Smart Money).

**Nguồn dữ liệu bám đuôi:**
- **Dữ liệu EPFR**: Dòng tiền ròng chảy vào các Quỹ Cổ phiếu/Trái phiếu toàn cầu hàng tuần. (Nước chảy chỗ trũng, nơi nào rút ròng liên tục là sắp nát).
- **Trái phiếu Kho bạc Mỹ (TIC Data)**: Cập nhật hàng tháng, cho biết nước nào đang tích lũy hay bán tháo Trái phiếu Mỹ.
- **Thay đổi Dự trữ Ngoại hối**: Cập nhật hàng quý, định hướng xem các NHTW thế giới đang tích trữ Vàng hay Đô la.

### 4. Chu kỳ Đồng Đô la và Các Thị trường Mới nổi (Emerging Markets - EM)

Đồng Đô la (DXY) là kẻ thù truyền kiếp của các loại tài sản rủi ro (Cổ phiếu, Crypto, Hàng hóa) và Thị trường Mới nổi (Châu Á, Mỹ Latin).

**Mô hình Chu kỳ Đô la 4 Giai đoạn:**

```text
Giai đoạn Đô la Mạnh (DXY leo dốc):
Tiền bị hút khỏi Thị trường Mới nổi (EM) chạy về Mỹ → Tỷ giá EM sụp đổ → Cả Cổ phiếu và Trái phiếu EM bị bán tháo đẫm máu. Lãi suất FED cao hút cạn thanh khoản của Crypto.

Giai đoạn Đô la Yếu (DXY lao dốc):
Tiền ồ ạt rời Mỹ để đi tìm lợi nhuận rủi ro cao ở EM và Crypto → Tiền EM lên giá → Tài sản rủi ro Outperform (Vượt trội) so với Mỹ.
```

**Ứng dụng Thực chiến (Mapping):**
- `DXY > 105` và đang trong xu hướng Tăng: Đứng ngoài Crypto và Thị trường EM. Ôm chặt tài sản tính bằng USD và Trái phiếu ngắn hạn.
- `DXY < 100` và đang Gãy xu hướng: Full Margin vào tài sản rủi ro (Chứng khoán, Crypto), giảm tỷ trọng Tiền mặt USD.

## Khung Phân tích (Analysis Framework)

### Các Bước Xây dựng Bảng Điều khiển Vĩ mô (Macro Dashboard)

1. **Thu thập Dữ liệu**: Lãi suất (US 10Y), Tỷ giá (DXY), Hàng hóa (Vàng / Dầu mỏ / Đồng), Dòng chảy vốn.
2. **Định vị Chu kỳ**: Chúng ta đang ở đâu trong bàn cờ? (Đang Tăng lãi suất / Dừng lại / Hay bắt đầu Cắt giảm?). Đô la đang mạnh hay yếu?
3. **Chấm điểm Nhân tố (Factor Scoring)**: Cho điểm từng biến số vĩ mô từ `-2` đến `+2` (-2 = Cực kỳ Bearish đánh xuống, +2 = Cực kỳ Bullish múc mạnh).
4. **Áp dụng Phân bổ**: Tổng điểm Vĩ mô sẽ tự động điều chỉnh Trọng số danh mục cho các tài sản.

### Ví dụ Về Chấm điểm Nhân tố Vĩ mô

```python
macro_factors = {
    "fed_policy": +1,      # FED ngừng tăng lãi suất, thiên hướng bồ câu (Dovish).
    "dxy_cycle": +1,       # Chu kỳ Đô la suy yếu.
    "geopolitical": -1,    # Xung đột vũ trang ở Trung Đông.
    "global_flow": 0,      # Dòng vốn chưa có dấu hiệu dịch chuyển mạnh.
}
# Tổng điểm = (+1 + 1 - 1 + 0) / 4 = +0.25 → Hơi Bullish, ưu tiên cầm Tài sản Rủi ro thay vì tiền mặt.
```

## Định dạng Đầu ra (Output Format)

```markdown
## Báo cáo Phân tích Vĩ mô Toàn cầu

### Định vị Chu kỳ
- Chính sách FED: [Cuối chu kỳ tăng / Đang Tạm dừng / Bắt đầu Cắt giảm]
- Chu kỳ Đồng USD (DXY): [Mạnh / Sideway / Đang lao dốc]

### Bảng Điểm Nhân tố (-2 đến +2)
| Nhân tố | Điểm | Lập luận |
|------|------|------|
| Chính sách NHTW | +1 | FED dừng tăng lãi suất, thị trường đặt cược 70% sẽ cắt giảm vào Quý 3. |
| Dòng chảy Vốn | +2 | Dòng tiền ồ ạt chảy vào các ETF Bitcoin và Chứng khoán Công nghệ. |
| Địa chính trị | -1 | Tắt nghẽn Biển Đỏ đẩy giá cước vận tải lên cao. |

### Lời khuyên Phân bổ Tài sản (Asset Allocation)
- Tiền mã hóa (Crypto): [Tăng tỷ trọng / Giữ nguyên / Giảm tỷ trọng] — Lý do.
- Cổ phiếu Mỹ (S&P 500): [Tăng tỷ trọng / Giữ nguyên / Giảm tỷ trọng] — Lý do.
- Vàng (Gold): [Tăng tỷ trọng / Giữ nguyên / Giảm tỷ trọng] — Lý do.
- Trái phiếu Mỹ: [Tăng tỷ trọng / Giữ nguyên / Giảm tỷ trọng] — Lý do.
```

## Lưu ý Sống còn

- Vĩ mô chỉ cho bạn **Hướng đi (Direction)**, không cho bạn **Điểm vào lệnh (Precise Timing)**. Điểm vào lệnh hãy dùng Kỹ năng `technical-basic` hoặc `volatility`.
- Đánh giá chính sách NHTW phải dựa trên Biên bản cuộc họp (Meeting minutes) và Dữ liệu lạm phát (CPI/PCE). Đừng nghe tin đồn nhảm trên mạng xã hội.
- Các cú sốc Địa chính trị thường chết yểu rất nhanh (1-4 tuần) và sẽ quay đầu, TRỪ KHI nó làm đứt gãy NGUỒN CUNG vật lý trong dài hạn (Như Cấm vận năng lượng Nga).
- Đây là khung tư duy Vĩ mô, Cấm áp dụng một cách cứng nhắc mà phải linh hoạt theo phản ứng của Ngài Thị trường.
