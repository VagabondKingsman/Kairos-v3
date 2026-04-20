---
name: phai_sinh_crypto
description: Chiến lược Phái sinh Tiền mã hóa (Crypto-derivatives) — Kinh doanh chênh lệch Funding Rate (Phí tài trợ), Giao dịch Cấu trúc kỳ hạn (Contango/Backwardation), và Phân tích Quyền chọn (Volatility smile / Greeks).
category: crypto
---

# Chiến lược Phái sinh Tiền mã hóa (Crypto-Derivatives)

## Tổng quan

Bao gồm 3 hướng chiến lược phái sinh chính trong thị trường Crypto: Chênh lệch Funding Rate của Hợp đồng Tương lai Không kỳ hạn (Perpetual), Giao dịch Cấu trúc kỳ hạn (Term structure), và Chiến lược Quyền chọn (Volatility trading). Sàn giao dịch chính là OKX và Deribit.

## Kinh doanh Chênh lệch Funding Rate (Perpetual Funding-Rate Arbitrage)

### Cơ chế Funding Rate

```text
Hợp đồng Perpetual không có ngày đáo hạn, nó dùng Funding Rate để neo giá sát với giá Spot (Giao ngay):

Funding rate > 0: Phe Long trả tiền cho phe Short (Tâm lý cực kỳ Bullish).
Funding rate < 0: Phe Short trả tiền cho phe Long (Tâm lý cực kỳ Bearish).

Tần suất thanh toán: OKX thanh toán mỗi 8 tiếng (00:00 / 08:00 / 16:00 giờ UTC).
Lợi suất thường niên (Annualized) = Funding rate × 3 × 365.
```

### Chiến lược Kinh doanh Chênh lệch (Arbitrage)

```text
Arbitrage thu Funding (Khi Funding rate > 0):
  Mua Spot + Short Perpetual = Đưa vị thế Delta về 0 (Không quan tâm giá lên hay xuống).
  Nguồn lợi nhuận: Nhận tiền Funding đều đặn mỗi 8 tiếng.

Arbitrage ngược (Khi Funding rate < 0, hiếm gặp hơn):
  Bán khống Spot (Vay coin bán) + Long Perpetual.
  Nguồn lợi nhuận: Nhận tiền Funding mỗi 8 tiếng.
```

### Tín hiệu Funding Rate (Mỗi 8H)

| Funding Rate | Thường niên | Tâm lý thị trường | Tín hiệu Chiến lược |
|-------------|------|---------|---------|
| > 0.1% | > 109% | Cực kỳ Tham lam | Bán khống (Lãi suất này không thể duy trì) |
| 0.03-0.1% | 33-109% | Thiên hướng Bullish | Mở vị thế Arbitrage thu Funding |
| 0.01-0.03% | 11-33% | Bình thường | Có thể mở Arbitrage |
| -0.01~0.01% | -11~11% | Trung lập | Không có cơ hội Arbitrage |
| < -0.01% | < -11% | Thiên hướng Bearish | Mở Arbitrage ngược hoặc Cắt lỗ Long |
| < -0.1% | < -109% | Cực kỳ Hoảng loạn | Mua bắt đáy (Lãi suất này không thể duy trì) |

### Kiểm soát Rủi ro Arbitrage

1. **Cháy tài khoản (Liquidation)**: Đầu Short Perpetual yêu cầu ký quỹ, nếu giá tăng sốc (x2, x3) có thể làm cháy tài khoản phái sinh trước khi bạn kịp nạp thêm tiền.
2. **Funding đảo chiều**: Rate dương đột ngột chuyển sang âm, khiến bạn phải trả tiền ngược lại.
3. **Biến động Basis**: Sự chênh lệch giữa giá Spot và giá Perpetual có thể gây lỗ trạng thái.
4. **Rủi ro sàn**: Sàn sập, cấm rút tiền, hoặc cắm râu thanh lý.

**Tham số Quản trị:**
- Đòn bẩy (Leverage): Không quá 3x.
- Tỷ lệ ký quỹ: Giữ > 50% (Cách xa giá thanh lý).
- Tỷ trọng một đồng coin: < 30%.
- Cắt lỗ: Đóng lệnh khi lỗ trạng thái (Floating loss) vượt quá lợi nhuận Funding dự kiến trong 3 tháng.

## Giao dịch Cấu trúc Kỳ hạn (Term-Structure Trading)

### Khái niệm Cơ bản

```text
Cấu trúc kỳ hạn = Đường cong giá của các Hợp đồng Tương lai (Futures) có ngày đáo hạn khác nhau.

Bù hoãn mua (Contango): Tháng xa > Tháng gần > Spot
  - Ý nghĩa: Thị trường kỳ vọng giá tương lai sẽ tăng. Rất phổ biến trong Up-trend.

Bù hoãn bán (Backwardation): Tháng xa < Tháng gần < Spot
  - Ý nghĩa: Nhu cầu gom hàng Spot ngay lập tức cực kỳ lớn. Phổ biến trong Down-trend hoặc Panic Sell.
```

### Chiến lược Giao dịch

| Chiến lược | Hành động | Môi trường áp dụng | Rủi ro |
|------|------|---------|------|
| Cash-and-Carry | Mua Spot + Short Futures (Giữ đến đáo hạn) | Contango lớn (Lãi năm > 15%) | Rủi ro sàn |
| Calendar Spread | Long Tháng gần + Short Tháng xa | Kỳ vọng Contango hội tụ | Lệch Basis |
| Reverse Calendar | Short Tháng gần + Long Tháng xa | Kỳ vọng Backwardation hội tụ | Đảo chiều Basis |

## Chiến lược Quyền chọn (Options Strategies)

### Các thông số Hy Lạp cơ bản (Greeks)

| Greek | Ý nghĩa | Đặc thù Crypto |
|-------|------|-----------|
| Delta | Giá Quyền chọn thay đổi bao nhiêu khi Giá coin thay đổi 1% | Biến động mạnh, Delta thay đổi rất nhanh |
| Gamma | Tốc độ thay đổi của Delta | Các quyền chọn ATM (At-the-money) có Gamma cao nhất |
| Theta | Tốc độ mất giá do thời gian (Hàng ngày) | Crypto trade 24/7, Theta rớt không ngừng nghỉ cả cuối tuần |
| Vega | Tác động khi Độ biến động ngầm định (IV) thay đổi 1% | IV của BTC thường ở mức 50-120%, cao hơn cực nhiều so với CK truyền thống |

### Nụ cười Biến động (Volatility Smile / Skew)

```text
1. Nụ cười (Smile): IV của quyền chọn OTM (Out-of-the-money) Put và Call đều cao hơn IV của ATM.
2. Lệch (Skew): Thông thường IV của OTM Put > OTM Call (Do nhu cầu mua Put để bảo hiểm rủi ro rớt giá).
3. Lệch ngược (Reverse Skew): Trong Up-trend cực mạnh, đám đông Fomo mua Call khiến IV của OTM Call > OTM Put.

Risk Reversal (25Δ) = IV(25Δ Call) - IV(25Δ Put)
  > 0: Lệch Bullish (Thị trường điên rồ).
  < 0: Lệch Bearish (Trạng thái bình thường).
```

### Các Chiến lược Phổ biến

**1. Bán Straddle (Short Straddle)**
- **Hành động**: Bán ATM Call + Bán ATM Put cùng lúc.
- **Nguồn lãi**: Ăn tiền phí Theta (Thời gian trôi qua).
- **Rủi ro**: Lỗ vô cực nếu giá biến động một chiều quá mạnh. Dùng khi IV > 80% và kỳ vọng giá đi ngang.

**2. Mua Put Bảo hiểm (Protective Put)**
- **Hành động**: Ôm Spot + Mua OTM Put.
- **Mục đích**: Bảo hiểm rủi ro rớt giá sâu trong Up-trend. Tốn phí mua Put (khoảng 2-5% giá trị vốn mỗi tháng).

**3. Giao dịch Độ biến động (Volatility Arbitrage)**
- Nếu IV < Biến động Lịch sử (Khoảng < 40%): Mua Biến động (Long Volatility) bằng cách Mua Straddle + Delta Hedge.
- Nếu IV > Biến động Lịch sử (Khoảng > 80%): Bán Biến động (Short Volatility) bằng cách Bán Straddle + Delta Hedge.

## Định dạng Đầu ra (Output)

```markdown
## Phân tích Phái sinh Crypto

### Bức tranh Thị trường
| Chỉ báo | BTC | ETH |
|------|-----|-----|
| Giá Spot | $95,000 | $3,200 |
| Funding (8h) | 0.035% | 0.028% |
| Tỷ suất Funding Năm | 38.3% | 30.7% |
| Lãi Arbitrage Quý | 18.5% | 15.2% |
| ATM IV (30 ngày) | 65% | 72% |

### Khuyến nghị Chiến lược
| Chiến lược | Hướng dẫn | Lợi nhuận Kỳ vọng (Năm) | Rủi ro |
|------|------|---------|---------|
| Arbitrage Funding BTC | Short Perpetual + Mua Spot | 25-35% | Trung bình |
| Bán Khống Biến động BTC | Bán OTM Call + Put | Thu phí chênh lệch | Cao |

### Cảnh báo Rủi ro
- ...
```
