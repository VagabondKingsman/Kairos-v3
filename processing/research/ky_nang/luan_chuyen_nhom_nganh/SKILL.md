---
name: luan_chuyen_nhom_nganh
description: Phân tích Luân chuyển Dòng tiền (Sector rotation) — Mô hình chấm điểm vĩ mô, xếp hạng động lượng (Momentum) nhóm ngành, phân tích chuỗi cung ứng và dòng tiền trên thị trường Chứng khoán Mỹ / Crypto.
category: asset-class
---

# Luân chuyển Dòng tiền (Sector Rotation)

## Tổng quan

Dòng tiền trên thị trường không bao giờ nằm im. Nó liên tục chảy từ nhóm ngành được định giá cao sang nhóm ngành đang bị định giá thấp, hoặc từ nhóm Rủi ro (Risk-on) sang nhóm Phòng thủ (Risk-off) tùy thuộc vào chu kỳ Kinh tế.

Chiến lược này sử dụng mô hình chấm điểm Động lượng (Momentum), định giá, và phân tích Vĩ mô để xác định Đâu là nhóm ngành đang hút tiền, từ đó đưa ra quyết định Tăng/Giảm tỷ trọng (Overweight/Underweight).

## Phân loại Nhóm Ngành (Sector Classification)

### 1. Thị trường Chứng khoán Mỹ (GICS Sectors)

| Nhóm Ngành | Tính chất Chu kỳ | ETF Đại diện | Động lực Tăng trưởng chính |
|------|------|---------|---------|
| Công nghệ (Tech) | Tăng trưởng (Growth) | XLK | Lãi suất giảm, Chu kỳ nâng cấp phần cứng (AI) |
| Tiêu dùng Tùy ý (Consumer Discretionary) | Biến động theo Kinh tế | XLY | Sức mua người dân, Tỷ lệ việc làm |
| Y tế (Healthcare) | Phòng thủ (Defensive) | XLV | Dân số già hóa, Đổi mới Dược phẩm |
| Tài chính (Financials) | Chu kỳ (Cyclical) | XLF | Đường cong Lợi suất (Yield Curve) dốc lên |
| Năng lượng (Energy) | Biến động cực mạnh | XLE | Giá dầu tháo chạy, Địa chính trị |
| Tiện ích (Utilities) | Phòng thủ tuyệt đối | XLU | Lãi suất trái phiếu giảm (Chơi lấy Cổ tức) |

### 2. Thị trường Crypto (Mảng / Narrative)

| Mảng (Sector) | Đại diện | Tính chất Dòng tiền |
|------|------|---------|
| Layer 1 / Smart Contracts | ETH, SOL, AVAX | Chỉ số nền tảng, Dòng tiền vào đầu tiên |
| DeFi | UNI, AAVE, MKR | Dòng tiền đổ vào khi cần Yield / Vay mượn Margin |
| AI / DePIN | RNDR, TAO, FET | Dòng tiền đầu cơ cực mạnh, bám theo trend AI toàn cầu |
| Memecoin | DOGE, PEPE, WIF | Cờ bạc, Thanh khoản rác. Dấu hiệu đỉnh chu kỳ |
| RWA (Tài sản Đời thực)| ONDO, LINK | Kết nối TradFi và Crypto |

## Khung Xếp hạng Động lượng (Momentum Ranking)

Dòng tiền có tính quán tính. Ngành nào đang tăng sẽ có xu hướng tiếp tục tăng trong ngắn hạn (Hiệu ứng Momentum).

### Động lượng Giá (Price Momentum)

```python
def sector_momentum(sector_returns: pd.DataFrame, lookback: int = 60, skip: int = 5) -> pd.Series:
    """
    Xếp hạng các nhóm ngành dựa trên lợi nhuận tích lũy.
    Args:
        sector_returns: Lợi nhuận hàng ngày của các Sector ETF
        lookback: Cửa sổ nhìn lại (Ví dụ: 60 ngày)
        skip: Bỏ qua 5 ngày gần nhất (Để tránh bị dính hiện tượng Đảo chiều Ngắn hạn - Short-term Reversal)
    Returns:
        Xếp hạng Động lượng (Rank)
    """
    cum_return = (1 + sector_returns).rolling(lookback).apply(lambda x: x[:-skip].prod() - 1)
    return cum_return.iloc[-1].rank(ascending=False)
```

## Khung So sánh và Lọc (Screening Framework)

Dùng kết hợp 3 lăng kính để tìm ra Sector chiến thắng.

### 1. Định giá (Valuation)
Đừng bao giờ đua lệnh vào một Sector có P/E lịch sử nằm ở phân vị 99%.
- **Chứng khoán**: Xem P/E TTM, P/B so với mốc lịch sử 5 năm.
- **Crypto**: Xem Tỷ lệ Lạm phát Token, Mở khóa Token (Unlock schedule), FDV/TVL.

### 2. Dòng tiền (Flows)
- **Chứng khoán**: Dòng tiền mua ròng vào các quỹ ETF (Ví dụ dòng tiền chảy cuồn cuộn vào XLK).
- **Crypto**: Stablecoin Flow rẽ vào hệ sinh thái nào (Ví dụ: USDC được in ồ ạt trên mạng Solana -> Dòng tiền đang chuẩn bị đánh lên SOL).

### 3. Vĩ mô / Chính sách (Macro Catalysts)
- Lãi suất hạ -> Mua Công nghệ, Bán Ngân hàng.
- Lạm phát tăng lại -> Mua Hàng hóa, Năng lượng.

## Băng chuyền Truyền dẫn Chuỗi cung ứng (Supply Chain)

Tiền sẽ chảy từ Thượng nguồn xuống Hạ nguồn, hoặc ngược lại tùy thuộc vào chu kỳ hàng hóa.

```text
Ví dụ: Chuỗi cung ứng Bán dẫn (Semiconductor) AI
- Thượng nguồn (Sản xuất chip): NVDA, TSM -> Hưởng lợi đầu tiên, rõ ràng nhất.
- Trung nguồn (Máy chủ, Làm mát): SMCI -> Nhận đơn hàng sau khi Thượng nguồn nghẽn.
- Hạ nguồn (Ứng dụng Phần mềm AI): MSFT, GOOGL -> Khó đoán nhất vì chưa biết AI có mang lại tiền từ user thật không.
```

*Quy tắc*: Đánh sóng theo nhu cầu (Demand) thì mua con Hạ nguồn trước. Đánh sóng khan hiếm chi phí (Cost/Supply) thì mua con Thượng nguồn.

## Định dạng Đầu ra

```markdown
## Báo cáo Luân chuyển Dòng tiền (Sector Rotation)

### 1. Bảng Xếp hạng Động lượng Top 3 (Lookback 60 Ngày)
| Hạng | Ngành / Mảng | Chỉ số Động lượng | Trạng thái Dòng tiền |
|------|------|--------|---------|
| 1 | AI (Crypto) | +45.2% | Cực nóng (Overheated) |
| 2 | Layer 1 (SOL) | +22.1% | Đang hút Stablecoin mạnh |
| 3 | DeFi | +8.5% | Dòng tiền bắt đầu nhen nhóm |

### 2. Khuyến nghị Phân bổ (Allocation)
- **Tăng Tỷ trọng (Overweight)**: DeFi. Do định giá TVL/FDV đang ở mức thấp nhất 2 năm, kết hợp với việc dòng tiền trên Layer 1 đang chốt lời và có dấu hiệu luân chuyển sang.
- **Hạ Tỷ trọng (Underweight)**: Memecoin. Khối lượng giao dịch sụt giảm, dòng tiền tháo chạy.

### 3. Cảnh báo Chu kỳ
- Nhóm phòng thủ đang hút dòng tiền (Báo hiệu rủi ro Vĩ mô). Khuyến nghị chuẩn bị phương án Hedging.
```

## Chú ý (Pitfalls)

1. **Bẫy Giá trị (Value Trap)**: Các nhóm ngành mang tính chu kỳ (Tài chính, Hóa chất, Dầu mỏ) có mức P/E cực kỳ thấp ở đúng **ĐỈNH** của chu kỳ lợi nhuận. Đừng bao giờ mua Cổ phiếu Chu kỳ chỉ vì P/E thấp. Hãy dùng P/B.
2. **Nhiễu từ Cổ phiếu Vốn hóa Siêu Lớn**: Nhóm Tiêu dùng Tùy ý (XLY) thường bị bóp méo hoàn toàn bởi Amazon và Tesla. Khi phân tích Sector, phải nhìn vào Cổ phiếu Trọng số Bằng nhau (Equal-weight) để xem tiền có thực sự chảy vào ngành đó không, hay chỉ do 1 con siêu to kéo.
3. **Chu kỳ Luân chuyển Crypto rất nhanh**: Ở thị trường truyền thống, dòng tiền luân chuyển tính bằng Tháng. Ở Crypto, nó có thể nhảy từ Layer 1 sang Memecoin chỉ trong 3 Ngày.
