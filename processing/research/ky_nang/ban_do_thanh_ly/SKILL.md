---
name: ban_do_thanh_ly
description: Phân tích các Mốc Thanh lý (Liquidation level) và Bản đồ Nhiệt (Heatmap) — xác định vùng tập trung đòn bẩy, chuỗi thanh lý dây chuyền, vùng Săn Stop-loss (Stop-hunt), và sử dụng dữ liệu thanh lý như các tín hiệu Hỗ trợ / Kháng cự.
category: crypto
---

# Bản đồ Nhiệt và Phân tích Mốc Thanh lý (Liquidation Heatmap)

## Tổng quan

Phân tích sự phân bổ của các vị thế đòn bẩy và các mức giá sẽ khiến chúng bị thanh lý (cháy tài khoản). Các cụm thanh lý đóng vai trò như những "Cục Nam châm" — giá thường bị hút về phía các cụm thanh lý lớn vì Market Maker (Nhà tạo lập) và Cá voi (Whales) cần quét những lệnh này để lấy thanh khoản (Liquidity) lấp đầy các vị thế khổng lồ của họ.

## Các Khái niệm Cốt lõi

### 1. Cơ chế Thanh lý

**Cách thức hoạt động:**
```python
# Điểm thanh lý của lệnh Long
long_liquidation_price = entry_price * (1 - 1/leverage + maintenance_margin)

# Điểm thanh lý của lệnh Short
short_liquidation_price = entry_price * (1 + 1/leverage - maintenance_margin)

# Ví dụ: Long BTC ở $65,000, Đòn bẩy 10x, Ký quỹ duy trì 0.5%
# Cháy tài khoản: $65,000 * (1 - 1/10 + 0.005) = $58,825
# Giá rớt 9.5% là lệnh Long này sẽ bị sàn ép bán (Force sell).
```

**Đòn bẩy và Khoảng cách Cháy:**
| Đòn bẩy | Điểm Cháy (Long) | Điểm Cháy (Short) |
|----------|----------------------------|------------------------------|
| 2x | Rớt ~50% | Tăng ~50% |
| 5x | Rớt ~20% | Tăng ~20% |
| 10x | Rớt ~10% | Tăng ~10% |
| 50x | Rớt ~2% | Tăng ~2% |
| 100x | Rớt ~1% | Tăng ~1% |

### 2. Cách đọc Bản đồ Nhiệt Thanh lý (Heatmap)

Bản đồ nhiệt hiển thị nơi các lệnh thanh lý đang tụ tập đông nhất, thường dùng màu sắc để đo độ đậm đặc.

```text
Mức giá     Thanh lý Long        Thanh lý Short       Đọc hiểu
$70,000        ░░░░                 ████████████████     Cụm Short khổng lồ (Mục tiêu của giá lên)
$68,000        ░░                   ██████               Vùng Short trung bình
$66,000        ███                  ███                  Cân bằng (Vùng giá hiện tại)
$62,000        ████████████████     ░░░                  Cụm Long khổng lồ (Mục tiêu của giá xuống)
```

**Nguyên lý săn mồi:**
1. **Thanh lý là Nam châm**: Các lệnh bị ép bán/ép mua tự động sẽ tạo ra thanh khoản khổng lồ. Cá voi luôn đẩy giá về đó để xả hàng.
2. **Hiệu ứng Dây chuyền (Cascade)**: Khi cụm 1 bị cháy, lệnh ép bán sẽ đẩy giá rớt tiếp, cắn luôn vào cụm 2, cụm 3... tạo ra một cú sập hầm chớp nhoáng (Flash Crash).
3. **Hỗ trợ / Kháng cự mới**: Sau khi một cụm đòn bẩy khổng lồ bị quét sạch, mức giá đó lập tức trở thành Hỗ trợ / Kháng cự cực mạnh vì bọn "đánh bạc" đã bị loại khỏi cuộc chơi.

### 3. Các Tín hiệu Giao dịch từ Thanh lý

**Tín hiệu 1: Nam châm Hút giá (Liquidation Magnet)**
```python
def liquidation_magnet_signal(current_price, clusters):
    """
    So sánh độ lớn của Cụm thanh lý bên trên và bên dưới. Giá sẽ bị hút về phía cụm to hơn.
    """
    # Nếu Cụm Short bên trên to gấp đôi Cụm Long bên dưới -> Hướng lên (Upward Magnet).
    # Nếu Cụm Long bên dưới to gấp đôi -> Hướng xuống (Downward Magnet).
```

**Tín hiệu 2: Rủi ro Thanh lý Dây chuyền (Cascade Risk)**
```python
def cascade_risk(current_price, clusters, direction="down"):
    """
    Kiểm tra xem các cụm thanh lý có xếp sát nhau không (VD: cách nhau < 2%).
    Nếu chúng xếp lớp như hiệu ứng domino -> Nguy cơ sập dây chuyền cực cao.
    """
```

**Tín hiệu 3: Thiết lập Hỗ trợ/Kháng cự sau Thanh lý**
```text
Nếu vừa có một cú quét > $100 Triệu USD lệnh Long ở mốc $60,000. 
-> Mốc $60,000 chính thức trở thành Hỗ trợ thép (Hard Support).
```

### 4. Đọc vị Dữ liệu Thanh lý Hàng ngày

| Khối lượng Cháy (24h) | Trạng thái Thị trường | Ý nghĩa |
|-----------------|-------------|-------------|
| > 1 Tỷ USD | Cực đoan (Extreme) | Bọn đòn bẩy đã bị giết sạch, sẵn sàng cho cú Đảo chiều chữ V. |
| 500M - 1 Tỷ USD | Biến động cao | Định hình lại cấu trúc vị thế. |
| 50M - 200M USD | Bình thường | Nhiễu hàng ngày. |
| < 50M USD | Lặng sóng | Đòn bẩy đang được tích tụ rình rập. |

**Tỷ lệ Long/Short bị cháy:**
- Nếu Long bị cháy gấp 3 lần Short -> Phe Long vừa bị vắt kiệt (Long Squeeze).

### 5. Giải phẫu một Cú Sập Dây chuyền (Cascade Anatomy)

```text
1. Phát súng đầu tiên (Tin xấu vĩ mô, Cá voi xả hàng).
   ↓
2. Giá rớt chạm vào Cụm Long đầu tiên ($65,000).
   → Sàn kích hoạt ép bán (Market Sell) 200 Triệu USD lệnh Long.
   ↓
3. Lệnh ép bán làm giá rớt thảm hơn, cắn vào Cụm Long thứ hai ($63,000).
   → Ép bán thêm 300 Triệu USD nữa.
   ↓
4. Cháy lan (Cascade) → Nhóm đòn bẩy cao chết la liệt.
   ↓
5. Kết cục: Hợp đồng mở (Open Interest - OI) tụt giảm 30%, Funding rate âm nặng.
   → Đòn bẩy đã được "Gội sạch" (Washed out) → Tạo ĐÁY cứng.
   ↓
6. Bắt đầu hồi phục vì thị trường không còn ai bị ép bán nữa.
```

**Hành động trong cơn bão:**
- **Trước cơn bão**: Không đặt lệnh Long bằng đòn bẩy lớn ngay trên đầu một Cụm thanh lý Long khổng lồ. (Bạn sẽ bị dìm chết cùng với chúng).
- **Trong cơn bão**: KHÔNG bắt dao rơi. Đợi Hợp đồng mở (OI) ổn định lại.
- **Sau cơn bão**: Khi Funding rate âm chót vót và OI đã tụt >20%, múc Long ngược đám đông với mức rủi ro kiểm soát.

## Nguồn Dữ liệu On-chain / API

| Nguồn | Truy cập | Dữ liệu cung cấp |
|--------|--------|---------------|
| CoinGlass | Miễn phí | Heatmap Thanh lý, Khối lượng cháy 24h, OI. |
| Laevitas | Có phí | Mức thanh lý của Options + Futures. |
| Hyblock Capital | Có phí | Heatmap chuyên nghiệp của tay to. |
| OKX / Binance API | Miễn phí | Dữ liệu lịch sử lệnh thanh lý (Cần tự build tool). |
| DeFi Llama | Miễn phí | Các mốc thanh lý trên giao thức DeFi (On-chain, hoàn toàn minh bạch). |

## Định dạng Đầu ra (Output Format)

```markdown
## Phân tích Thanh lý (Liquidation) — [Tài sản]

### Tổng quan 24h
- **Tổng thiệt hại**: $XXX Triệu USD
- **Phe Long bị cháy**: $XXX Triệu USD (XX%)
- **Phe Short bị cháy**: $XXX Triệu USD (XX%)
- **Lệnh cháy lớn nhất**: $XX Triệu USD trên sàn [Binance/OKX]

### Các Mốc Hút Máu (Magnet Levels)
| Mức Giá | Loại | Khối lượng Ước tính | Cách Hiện tại | Mức độ |
|------------|------|-------------|----------------------|----------|
| $XX,XXX | Cụm Short | $XXX M | +X.X% | Cao |
| $XX,XXX | Cụm Long | $XXX M | -X.X% | Cao |

### Rủi ro Cháy Dây chuyền (Cascade)
- **Rủi ro Dây chuyền Long (Downside)**: [Cao / Trung bình / Thấp] (Có 3 cụm bám sát nhau dưới mức giá hiện tại).

### Hành động Giao dịch
- **Khuynh hướng**: Mảnh đất Short phía trên màu mỡ hơn -> Giá dễ bật lên (Mild Bullish).
- **Hỗ trợ mới**: Lệnh Long vừa bị dọn sạch ở $XX,XXX tạo thành đáy cứng.
```
