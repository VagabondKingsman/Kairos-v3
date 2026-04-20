---
name: trai_phieu_chuyen_doi
description: Phân tích Trái phiếu Chuyển đổi (Convertible Bond) — Định giá 3 chiều (Cổ phiếu/Trái phiếu thuần/Quyền chọn), Chiến lược chênh lệch giá, Phân tích điều khoản (Mua lại, Bán lại, Hạ giá chuyển đổi), và Chiến lược Đầu tư "Hai đáy" (Dual-low strategy).
category: asset-class
---

# Phân tích Trái phiếu Chuyển đổi (Convertible Bond)

## Tổng quan

Trái phiếu chuyển đổi (TPCĐ) là một công cụ lai mang đặc điểm "Đáy bảo vệ của Trái phiếu + Quyền chọn Mua cổ phiếu". Kỹ năng này bao gồm hệ thống định giá 3 chiều, phân tích cuộc chơi tâm lý giữa các điều khoản, chiến lược "Hai đáy" (Dual-low) và framework chọn TPCĐ luân phiên.

## Các khái niệm cơ bản về TPCĐ

### Yếu tố cốt lõi

| Yếu tố | Mô tả | Ví dụ |
|------|------|------|
| Mệnh giá | Giá trị gốc | 100 USD / 100 RMB |
| Lãi suất cuống phiếu (Coupon) | Thường tăng dần qua các năm | Năm 1: 0.4%... Năm 6: 2.0% |
| Giá chuyển đổi (Strike Price) | Giá để đổi từ trái phiếu sang cổ phiếu | 15.00 |
| Kỳ hạn | Thường là 6 năm | 2024-2030 |
| Giá mua lại khi đáo hạn | Mệnh giá + Lãi năm cuối + Phần bù | 110-115 |
| Điều khoản Bán lại (Put) | Nếu giá cổ phiếu rớt thê thảm < 70% giá chuyển đổi liên tục 30 ngày | NĐT có quyền ép công ty mua lại |
| Điều khoản Chuộc lại (Call) | Nếu giá cổ phiếu tăng vọt > 130% giá chuyển đổi liên tục 15/30 ngày | Công ty có quyền ép NĐT chuyển đổi ngay lập tức |
| Điều khoản Hạ giá chuyển đổi | Công ty có quyền hạ giá chuyển đổi nếu cổ phiếu rớt sâu | Liên tục 15/30 ngày giá < 85% |

### Các chỉ số quan trọng

```text
Giá trị Chuyển đổi (Parity) = (Mệnh giá / Giá chuyển đổi) × Giá cổ phiếu hiện tại
VD: 100 / 15.00 × 18.00 = 120.00

Tỷ lệ Phần bù Chuyển đổi (Conversion Premium) = (Giá TPCĐ - Giá trị Chuyển đổi) / Giá trị Chuyển đổi × 100%
VD: (125 - 120) / 120 × 100% = 4.17%

Giá trị Trái phiếu thuần (Bond Floor) = Σ(Coupon / (1+r)^t) + Giá chuộc lại / (1+r)^n
Thường dao động từ 85-95 (tùy kỳ hạn và lãi suất chiết khấu)

Phần bù Trái phiếu thuần (Bond Premium) = (Giá TPCĐ - Giá trị Trái phiếu thuần) / Giá trị Trái phiếu thuần × 100%
```

## Hệ thống Định giá 3 Chiều

### 1. Giá trị Trái phiếu thuần (Đáy Trái phiếu)

```python
def bond_floor(coupon_rates: list, years_remaining: float,
               redemption_price: float = 110, yield_rate: float = 0.03) -> float:
    """
    Tính giá trị trái phiếu thuần (Bond Floor).
    Yield rate là lãi suất của trái phiếu doanh nghiệp cùng hạng tín nhiệm (VD: 2.5-4%).
    """
    pv = sum(c * 100 / (1 + yield_rate)**i for i, c in enumerate(coupon_rates, 1))
    pv += redemption_price / (1 + yield_rate)**len(coupon_rates)
    return pv
```

**Ý nghĩa**:
- Giá trị trái phiếu thuần càng cao → Lớp đệm bảo vệ càng chắc → Khó rớt giá sâu hơn nữa.
- Khi giá TPCĐ rớt về bằng Bond Floor, nó trở thành "Trái phiếu thuần", rất an toàn nhưng mất đi sức bật của cổ phiếu.

### 2. Giá trị Chuyển đổi (Tính Cổ phiếu)

Giá trị chuyển đổi hoàn toàn biến động theo giá cổ phiếu. Nếu công ty sử dụng quyền "Hạ giá chuyển đổi", Giá trị chuyển đổi sẽ tự động bật tăng lên.

### 3. Giá trị Quyền chọn (Option Value)

```text
Giá trị Quyền chọn = Giá TPCĐ - max(Giá trị Trái phiếu thuần, Giá trị Chuyển đổi)
```

Giá trị Quyền chọn cao có nghĩa là thị trường đang cực kỳ kỳ vọng giá cổ phiếu sẽ tăng mạnh, hoặc kỳ vọng công ty sắp Hạ giá chuyển đổi.

### Ma trận Quyết định 3 Chiều

| Giá trị Chuyển đổi | Giá trị Trái phiếu thuần | Phân loại | Chiến lược |
|---------|---------|---------|------|
| > 120 | Không quan trọng | Thiên về Cổ phiếu (Equity-like) | Đánh theo cổ phiếu, coi chừng bị ép chuộc lại (Call) |
| 100 - 120 | Không quan trọng | Cân bằng (Balanced) | Tấn công tốt, phòng thủ tốt (Vùng ngon nhất) |
| < 100 | > 90 | Thiên về Trái phiếu (Bond-like) | Ôm lấy lãi, chờ công ty hạ giá chuyển đổi hoặc cổ phiếu phục hồi |
| < 80 | < 85 | Kiệt quệ (Distressed) | Rủi ro vỡ nợ, tránh xa |

## Phân tích Cuộc chơi Tâm lý (Game Theory)

### Trò chơi Hạ giá Chuyển đổi (Downward Revision Game)

**Điều kiện kích hoạt**: Giá cổ phiếu liên tục nằm dưới 85% giá chuyển đổi.
Động lực của công ty:
- Nếu quỹ đạo giá đang thỏa mãn điều kiện Bán lại (Put), công ty buộc phải Hạ giá chuyển đổi để tránh bị NĐT ép trả lại tiền (vì công ty thường không có tiền mặt).
- Nếu cổ đông lớn đang cầm nhiều TPCĐ, họ có động lực ép công ty Hạ giá chuyển đổi để ăn chênh lệch.
- Việc hạ giá chuyển đổi sẽ gây pha loãng cổ phiếu, nên các công ty xịn thường không thích làm điều này.

### Trò chơi Ép Chuộc lại (Forced Redemption / Call Game)

**Điều kiện kích hoạt**: Giá cổ phiếu tăng vọt lên > 130% giá chuyển đổi trong 15/30 ngày.
- Lúc này công ty sẽ ra thông báo Ép Chuộc lại với giá 100.xx.
- Đang có giá thị trường 160 mà bị ép bán với giá 100 thì NĐT sẽ lỗ nặng. BẮT BUỘC NĐT phải làm lệnh Chuyển đổi ra cổ phiếu hoặc Bán ngay trên sàn trước hạn chót.

## Chiến lược "Hai đáy" (Dual-Low Strategy)

Đây là chiến lược kinh điển an toàn nhất:

```text
Chỉ số Hai Đáy (Dual-Low Score) = Giá TPCĐ + Tỷ lệ Phần bù Chuyển đổi × 100

Chỉ số càng thấp → Giá TPCĐ đang rẻ + Phần bù thấp → Món hời.

Bộ lọc tiêu chuẩn:
1. Chỉ số Hai Đáy < 130 (Khắt khe) hoặc < 150 (Nới lỏng).
2. Giá TPCĐ < 115 (An toàn vốn).
3. Tỷ lệ phần bù chuyển đổi < 30% (Độ đàn hồi tốt).
4. Kỳ hạn còn lại > 1 năm.
5. Hạng tín nhiệm ≥ AA- (Né rủi ro vỡ nợ).
```

### Backtest Chiến lược

- Mua Top N trái phiếu có Dual-Low Score thấp nhất.
- Nắm giữ bằng trọng số (Equal-weight).
- Rebalance hàng tháng.
- Return kỳ vọng (Thị trường Trung Quốc): 10-15%/năm, Max Drawdown: 8-15%, Sharpe: 1.0-1.5.

## Định dạng Đầu ra (Output)

```markdown
## Phân tích Trái phiếu Chuyển đổi: [Tên Mã]

### Thông tin cơ bản
| Chỉ báo | Giá trị |
|------|-----|
| Giá hiện tại | 112.50 |
| Giá trị Chuyển đổi | 98.30 |
| Giá trị Trái phiếu | 92.15 |
| Phần bù Chuyển đổi | 14.4% |
| Điểm Dual-Low | 126.9 |
| Hạng Tín nhiệm | AA |

### Định giá 3 Chiều
- **Đáy bảo vệ**: Giá trị trái phiếu thuần 92.15, Rủi ro sụt giảm tối đa khoảng 18%.
- **Sức bật Cổ phiếu**: Phần bù 14.4% là khá thấp. Nếu cổ phiếu tăng 10%, TPCĐ dự kiến tăng 8%.

### Phân tích Trò chơi
- **Xác suất Hạ giá chuyển đổi**: Trung bình (Giá cổ phiếu còn cách mức kích hoạt 12%).
- **Rủi ro Ép chuộc lại**: Thấp (Cách vạch tử thần 35%).

### Khuyến nghị Đầu tư
Điểm Dual-Low đạt 126.9, nằm trong vùng an toàn và đáng mua. Phân bổ tối đa 5% danh mục...
```

## Lưu ý Quan trọng

1. **Rủi ro tín dụng là lớn nhất**: Mặc dù gọi là "trái phiếu", vẫn có những công ty vỡ nợ hoàn toàn. Bắt buộc phải né các mã có hạng tín nhiệm dưới A+.
2. **Quên lệnh Ép Chuộc lại là mất trắng**: Bắt buộc phải cài cảnh báo tự động khi công ty ra thông báo Call.
3. **Thanh khoản**: TPCĐ quy mô nhỏ thanh khoản rất giật cục.
4. **Không chuyển đổi khi đáo hạn**: Nếu ôm đến ngày đáo hạn mà giá không lên, NĐT chỉ nhận lại được Mệnh giá + Lãi (tầm 110). Nếu đu đỉnh giá 130 thì ôm đến ngày cuối cùng vẫn lỗ.
