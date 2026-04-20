---
name: phan_tich_rui_ro
description: Đo lường Rủi ro và Kiểm tra Sức chịu đựng (Stress testing) — Tính toán VaR/CVaR, Sụt giảm tối đa (Max Drawdown), Mô phỏng Monte Carlo, phân tích Rủi ro đuôi (Tail-risk), và thiết lập kịch bản sập hầm lịch sử.
category: analysis
---

# Đo lường Rủi ro & Kiểm tra Sức chịu đựng (Risk Analysis)

## Tổng quan

Đo lường Rủi ro (Risk Measurement) giúp chúng ta trả lời câu hỏi: *"Trong kịch bản tồi tệ nhất, tôi có thể mất bao nhiêu tiền và liệu tôi có sống sót qua được cú sập đó không?"*
Kỹ năng này bao gồm việc tính VaR/CVaR, thiết lập các bài Test chịu tải (Stress testing) đâm thẳng danh mục vào các cuộc khủng hoảng lịch sử, và phát hiện các rủi ro Thiên nga đen (Tail-risk).

## Các Phương pháp Đo lường Rủi ro

### 1. VaR (Value at Risk - Giá trị Chịu Rủi ro)

**Định nghĩa**: Mức lỗ tối đa mà danh mục có thể gánh chịu trong một khoảng thời gian nhất định, với độ tin cậy X%.
*(Ví dụ: VaR 95% 1 ngày là -2% -> Nghĩa là có 95% xác suất ngày mai bạn sẽ không lỗ vượt quá 2%).*

#### 3 Cách Tính VaR

| Phương pháp | Thuật toán | Ưu điểm | Nhược điểm |
|------|----------|------|------|
| Lịch sử (Historical) | Xếp hạng chuỗi lợi nhuận quá khứ, lấy mốc phân vị (Quantile). | Không cần ép dữ liệu phải theo phân phối chuẩn. | Quá khứ chưa chắc lặp lại. |
| Tham số (Parametric) | `VaR = μ - z_α × σ` | Tính cực nhanh. | Mù quáng tin rằng thị trường tuân theo Phân phối chuẩn. |
| Monte Carlo | Mô phỏng 10,000 nhánh vũ trụ song song, lấy phân vị. | Rất mạnh, tùy biến cao. | Đốt CPU máy tính. |

### 2. CVaR / ES (Conditional VaR / Expected Shortfall)

**Định nghĩa**: Nếu xui xẻo rơi vào 5% trường hợp vỡ trận (Vượt mốc VaR), thì trung bình lúc đó tôi sẽ lỗ bao nhiêu?
CVaR luôn bảo thủ và khốc liệt hơn VaR. Tiêu chuẩn quản trị rủi ro của giới ngân hàng (Basel III) hiện đã chuyển sang dùng CVaR.

```python
def historical_cvar(returns: pd.Series, confidence: float = 0.95) -> float:
    """CVaR = Trung bình cộng của tất cả những khoản lỗ vượt quá VaR."""
    var = historical_var(returns, confidence)
    tail_losses = returns[returns < -var]
    return -tail_losses.mean() if len(tail_losses) > 0 else var
```

### 3. Sụt giảm Tối đa (Maximum Drawdown - MaxDD)

Chỉ số ám ảnh nhất của giới đầu tư. MaxDD đo lường mức giảm từ Đỉnh Lịch sử (Peak) xuống Đáy sâu nhất (Trough).
*Lưu ý: Một hệ thống có MaxDD > 30% thì rất khó để tâm lý con người gồng được trong thực tế.*

## Khung Kiểm tra Sức chịu đựng (Stress-Testing)

Mang danh mục của bạn ném vào các cuộc khủng hoảng để xem nó bị bào mòn bao nhiêu %.

### 1. Kịch bản Khủng hoảng Lịch sử (Historical Scenarios)

| Sự kiện / Kịch bản | Giai đoạn | Chứng khoán Mỹ rớt | Crypto rớt (BTC) | Trái phiếu CP 10 Năm |
|------|--------|---------|---------|---------|
| Khủng hoảng 2008 | 01/2008 - 10/2008 | -50% | N/A | Lợi suất giảm (Giá tăng) |
| Cú sốc FED tăng lãi suất | Cả năm 2022 | -25% | -65% | Lợi suất tăng sốc (Giá sập) |
| Thiên nga đen COVID-19 | 02/2020 - 03/2020 | -35% | -50% (Sập trong 2 ngày) | Lợi suất giảm kỷ lục |
| Chiến tranh Thương mại | Cả năm 2018 | -20% | -80% (Mùa đông Crypto) | Lợi suất giảm |

### 2. Thiết lập Kịch bản Giả định (Hypothetical Scenarios)

```python
STRESS_SCENARIOS = {
    'rate_shock_up_100bp': { # FED đấm 100 điểm lãi suất bất ngờ
        'equity': -0.10,    # Cổ phiếu sập 10%
        'gold': +0.05,      # Vàng bay 5%
        'btc': -0.15,       # Crypto sập 15% (bị rút thanh khoản)
    },
    'liquidity_dry_up': {    # Thanh khoản bốc hơi toàn cầu
        'equity': -0.20,
        'gold': -0.05,      # Hoảng loạn tới mức bán cả Vàng để thu tiền mặt
        'btc': -0.40,
        'cash': 0.0,
    }
}
```

## Phân tích Rủi ro Đuôi (Tail-Risk & Extreme Value)

Sử dụng định lý EVT (Extreme Value Theory) để đo lường độ tàn bạo của các cú "Thiên nga đen".

| Thước đo | Cách tính | Ý nghĩa |
|------|------|------|
| Độ nhọn (Kurtosis) | `returns.kurtosis()` | Lớn hơn 3 nghĩa là thị trường có **Đuôi béo (Fat tails)**. Khả năng xảy ra Thiên nga đen cao hơn nhiều so với lý thuyết thông thường. |
| Độ lệch (Skewness) | `returns.skew()` | Âm (<0) nghĩa là thị trường Tăng thì đi thang bộ, mà Giảm thì nhảy lầu (Đặc thù chung của tài chính). |
| Tỷ lệ Đuôi (Tail ratio)| Dưới 5% / Trên 5% | Lớn hơn 1 nghĩa là rủi ro hướng xuống nặng nề hơn hướng lên. |

## Định dạng Đầu ra Báo cáo Rủi ro

```markdown
## Báo cáo Phân tích Rủi ro Toàn diện

### 1. Số đo Rủi ro Cốt lõi
| Thước đo | Giá trị | Nhận định |
|------|-----|-----|
| Biến động Thường niên (Vol) | 29.3% | Trung bình - Cao |
| Sụt giảm Tối đa (Max Drawdown) | -32.5% | Nguy hiểm (Xảy ra vào 09/2024) |
| VaR (95%, 1 Ngày) | -2.8% | 95% số ngày không lỗ quá 2.8% |
| CVaR (95%, 1 Ngày) | -4.2% | Nếu xui xẻo sập, trung bình sẽ lỗ 4.2% / ngày |
| Độ nhọn (Kurtosis) | 5.2 | Đuôi béo cực đoan (Fat tail) |

### 2. Kết quả Stress Test
| Kịch bản Giả định | Mức độ Sát thương | Chạm Stop-loss Hệ thống? |
|------|---------|----------|
| Lặp lại COVID-19 (Tháng 3/2020) | -18.5% | Không |
| Sập thanh khoản toàn cầu | -28.7% | CÓ (Hệ thống bị Shutdown) |

### 3. Đề xuất Quản trị (Risk-Control Recommendations)
1. Danh mục đang chịu rủi ro Đuôi béo rất lớn. Khuyến nghị Phân bổ thêm 5-10% vào Vàng hoặc Tài sản phi rủi ro để hãm phanh.
2. Thiết lập Mức Cắt lỗ Tổng (Portfolio Stop-loss) cứng ở mức -15%. Nếu chạm mức này, đóng 100% vị thế ra Cash.
3. Trong các cuộc khủng hoảng, Sự Tương quan (Correlation) của mọi loại tài sản đều lao về 1 (tức là sập cùng nhau). Việc phân bổ đa dạng (Diversification) sẽ hoàn toàn vô dụng. Cần chuẩn bị sẵn công cụ phòng vệ (Hedging) bằng Options.
```

## Các Cạm bẫy Tuyệt đối Phải nhớ

1. **VaR không phải là Mức Lỗ Tối Đa**: VaR 95% = -2% chỉ lo được cho 95% ngày bình yên. Trong 5% ngày giông bão còn lại, bạn có thể mất -20%, -50% hoặc Cháy tài khoản.
2. **Ảo tưởng Phân phối Chuẩn**: Dữ liệu tài chính KHÔNG BAO GIỜ tuân theo phân phối chuẩn hình chuông. Nó là đuôi béo. Dùng Parametric VaR là đang tự ru ngủ bản thân.
3. **Mù lòa Tương quan (Correlation Breakdown)**: Lúc thị trường bò lên, các mã tăng giảm lệch pha nhau (Tương quan thấp). Khi thị trường sập hầm hoảng loạn, vạn vật đều rớt.
