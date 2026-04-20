---
name: phan_tich_hang_hoa
description: Phân tích Hàng hóa (Cân bằng Cung-Cầu dầu mỏ / Mô hình định giá Vàng / Đồng như một phong vũ biểu kinh tế / Chu kỳ Hàng tồn kho / Cấu trúc bù hoãn mua-bán kỳ hạn / Tính mùa vụ), tạo ra tín hiệu định hướng cho giao dịch Hàng hóa.
category: analysis
---
# Phân tích Hàng hóa (Commodity Analysis)

## Tổng quan

Phân tích thị trường hàng hóa từ 4 góc độ — Cân bằng cung-cầu, Mô hình định giá, Chu kỳ tồn kho, và Cấu trúc hợp đồng kỳ hạn (Term structure) — để xuất ra các tín hiệu định hướng phù hợp cho backtest. Trọng tâm tập trung vào Dầu thô (Mỏ neo định giá toàn cầu), Vàng (Nơi trú ẩn an toàn + Tránh lạm phát), và Đồng (Phong vũ biểu kinh tế).

## Khái niệm Cốt lõi

### 1. Cân bằng Cung-Cầu Dầu thô

**Các biến số then chốt bên Cung:**

| Biến số | Nguồn dữ liệu | Tần suất | Chiều tác động |
|------|--------|------|---------|
| Sản lượng OPEC | Báo cáo tháng OPEC | Hàng tháng | Cắt giảm sản lượng → Giá dầu ↑ |
| Sản lượng đá phiến Mỹ | Báo cáo tuần EIA | Hàng tuần | Sản lượng tăng → Giá dầu ↓ |
| Số lượng giàn khoan (Baker Hughes) | Baker Hughes | Hàng tuần | Dẫn trước sản lượng 3-6 tháng |
| Dự trữ Dầu mỏ Chiến lược (SPR) | EIA | Hàng tuần | Xả kho SPR → Giá dầu ngắn hạn ↓ |

**Các biến số then chốt bên Cầu:**
- Dự báo nhu cầu dầu toàn cầu của IEA (Hàng quý)
- Lượng nhập khẩu dầu thô của Trung Quốc (Dữ liệu hải quan hàng tháng)
- Nhu cầu xăng của Mỹ (Báo cáo tuần EIA, nhu cầu ngụ ý)
- Chỉ số PMI Toàn cầu (Dẫn trước nhu cầu 1-2 tháng)

**Tín hiệu Cân bằng Cung-Cầu:**

```python
# Đánh giá Cung-Cầu rút gọn
if opec_compliance > 0.90 and us_rig_count_declining:
    supply_signal = "tight"  # Nguồn cung thắt chặt -> Bullish
elif opec_compliance < 0.80 and us_production_rising:
    supply_signal = "loose"  # Nguồn cung dư thừa -> Bearish

if global_pmi > 50 and china_import_yoy > 0.05:
    demand_signal = "strong"  # Nhu cầu mạnh -> Bullish
elif global_pmi < 48 and china_import_yoy < 0:
    demand_signal = "weak"    # Nhu cầu yếu -> Bearish
```

### 2. Khung Định giá Vàng

**Mô hình 4 Nhân tố:**

| Nhân tố | Trọng số | Logic | Chỉ báo |
|------|------|------|------|
| Lãi suất thực | 40% | Lãi suất thực ↓ → Chi phí cơ hội giữ vàng giảm → Vàng ↑ | Lợi suất TIPS 10 năm |
| Chỉ số USD | 25% | USD ↓ → Vàng rẻ hơn khi định giá bằng ngoại tệ khác → Vàng ↑ | DXY |
| Nhu cầu trú ẩn | 20% | Rủi ro ↑ → Mua vàng trú ẩn → Vàng ↑ | VIX + Chỉ số Rủi ro Địa chính trị |
| Lực mua của NHTW | 15% | NHTW mua vào → Lực đỡ cấu trúc cho nhu cầu | Báo cáo quý của WGC |

**Quy tắc thực chiến:**
- TIPS 10 năm < 0%: Lực đỡ cực mạnh cho vàng (Lãi suất thực âm nghĩa là giữ tiền mặt bị lỗ).
- TIPS 10 năm > 2%: Áp lực lớn lên vàng.
- Lực mua của Ngân hàng Trung ương > 1000 tấn / năm: Lực đỡ Bullish dài hạn.

### 3. Tiến sĩ Đồng (Dr. Copper) - Chỉ báo Kinh tế

**Đồng là chỉ báo dẫn dắt (Leading indicator):**
- Mức thay đổi giá Đồng YoY dẫn dắt Sản xuất Công nghiệp khoảng 2-3 tháng.
- Tỷ lệ Đồng / Vàng có tương quan thuận cực cao với Lợi suất Trái phiếu kho bạc Mỹ 10 năm (`r > 0.7`).

### 4. Phân tích Chu kỳ Tồn kho (Inventory Cycle)

**Tồn kho hiện hữu vs Tồn kho ẩn:**
- Tồn kho hiện hữu: Được công bố bởi các sàn (LME / SHFE / COMEX), minh bạch.
- Tồn kho ẩn: Nằm ở các kho hải quan / kho của trader, không minh bạch nhưng quy mô có thể lớn hơn.

**4 Giai đoạn Chu kỳ Tồn kho (Lấy Đồng làm ví dụ):**

```text
Chủ động tích trữ (Giá↑ Lượng↑) -> Bị động tích trữ (Giá↓ Lượng↑) -> Chủ động xả kho (Giá↓ Lượng↓) -> Bị động xả kho (Giá↑ Lượng↓)
       Giữa Up-trend                    Cuối Up-trend                   Giữa Down-trend                 Cuối Down-trend / Đầu Up-trend
```

**Tín hiệu giao dịch:**

| Giai đoạn | Hướng Tồn kho | Hướng Giá | Tín hiệu Giao dịch |
|------|---------|---------|---------|
| Bị động xả kho | ↓ | ↑ | Long (Điểm mua đẹp nhất) |
| Chủ động tích trữ | ↑ | ↑ | Tiếp tục giữ lệnh Long |
| Bị động tích trữ | ↑ | ↓ | Chốt lời Long (Cảnh báo đảo chiều) |
| Chủ động xả kho | ↓ | ↓ | Short hoặc Đứng ngoài |

### 5. Cấu trúc Bù hoãn mua/Bán (Contango / Backwardation)

**Contango (Giá kỳ hạn > Giá giao ngay, Thị trường bình thường):**
- Nguồn cung dư thừa, thị trường định giá bao gồm cả chi phí lưu kho (carrying costs).
- Lợi suất đảo hạn (Roll yield) bị âm (`roll yield < 0`), bất lợi cho phe cầm Long.
- Contango sâu (`Tháng xa - Tháng gần > 5%`) = Cực kỳ dư thừa.

**Backwardation (Giá kỳ hạn < Giá giao ngay, Thị trường đảo ngược):**
- Nguồn cung thắt chặt, phần bù giá giao ngay phản ánh nhu cầu ngay lập tức quá mạnh.
- Lợi suất đảo hạn dương (`roll yield > 0`), có lợi cho phe cầm Long.
- Backwardation sâu (`Tháng gần - Tháng xa > 3%`) = Squeeze (Ép hàng) hoặc thiếu hụt cực đoan.

**Tín hiệu Cấu trúc kỳ hạn:**

```python
# Tỷ lệ chênh lệch = (Tháng gần - Tháng tiếp theo) / Tháng gần
spread_ratio = (front_month - second_month) / front_month

if spread_ratio > 0.02:    # Backwardation > 2%
    signal = "strongly bullish"  # Thiếu hàng giao ngay
elif spread_ratio < -0.03: # Contango > 3%
    signal = "bearish"           # Thừa cung
else:
    signal = "neutral"
```

### 6. Tính mùa vụ (Seasonality)

**Mùa vụ Dầu mỏ:**
- Tháng 3-Tháng 5: Kết thúc bảo trì nhà máy lọc dầu + Tích trữ tồn kho mùa hè → Giá tăng (chuẩn bị cho "mùa lái xe").
- Tháng 9-Tháng 10: Mùa bão (Vịnh Mexico) → Gián đoạn nguồn cung → Biến động mạnh.
- Tháng 11-Tháng 12: Nhu cầu dầu sưởi ấm.

**Mùa vụ Vàng:**
- Tháng 1-Tháng 2: Tết Âm lịch + Mùa cưới Ấn Độ → Nhu cầu vật chất mạnh → Giá thường mạnh.
- Tháng 7-Tháng 8: Mùa thấp điểm truyền thống.

## Khung Phân tích (Analysis Framework)

1. **Cung-cầu định hướng**: Đang thặng dư hay thiếu hụt? Các biến số biên đang nghiêng về đâu?
2. **Tồn kho bắt nhịp**: Đang ở giai đoạn nào của chu kỳ tồn kho? Đã sắp đảo chiều chưa?
3. **Cấu trúc kỳ hạn xác nhận**: Đang Contango hay Backwardation? Nó có đồng thuận với Cung-Cầu không?
4. **Yếu tố Mùa vụ**: Đang là lực cản hay lực đẩy?
5. **Vĩ mô xác nhận**: Đồng USD, Lãi suất, Khẩu vị rủi ro có ủng hộ không?

## Định dạng Đầu ra (Output)

```markdown
## Báo cáo Phân tích Hàng hóa — [Tên Hàng hóa]

### Cấu trúc Cung-Cầu
- Bên cung: [Thặng dư / Cân bằng / Thiếu hụt] — [Dữ liệu cụ thể]
- Bên cầu: [Mạnh / Ổn định / Yếu] — [Dữ liệu cụ thể]

### Chu kỳ Tồn kho
- Giai đoạn hiện tại: [Bị động xả kho]
- Tồn kho hiện hữu: [LME X tấn, SHFE Y tấn, Thay đổi WoW]

### Cấu trúc Kỳ hạn
- Chênh lệch tháng gần/xa: [Backwardation X%]
- Roll yield: [Dương / Âm]

### Tín hiệu Giao dịch
- Định hướng: [Bullish / Bearish / Neutral]
- Độ tin cậy: [Cao / Trung bình / Thấp]
- Rủi ro tiềm ẩn: [Liệt kê]
```

## Lưu ý

- Các nguồn dữ liệu hàng hóa rất phân tán (EIA / OPEC / LME / SHFE). Kỹ năng này cung cấp khung phân tích, dữ liệu cần được Agent tự thu thập qua `web-reader` hoặc nhập tay.
- Giá kỳ hạn luôn bao gồm chi phí đảo hạn (roll costs).
- Tính mùa vụ chỉ là xác suất thống kê, đôi khi có thể bị bẻ gãy hoàn toàn bởi các yếu tố cơ bản đột biến trong năm đó.
- Vàng chịu ảnh hưởng của tài chính (Lãi suất/USD) mạnh hơn là yếu tố hàng hóa thực trong ngắn hạn.
