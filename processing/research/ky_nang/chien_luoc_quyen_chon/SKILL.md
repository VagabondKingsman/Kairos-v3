---
name: chien_luoc_quyen_chon
description: Khung chiến lược Quyền chọn (Options strategy framework) hỗ trợ định giá Black-Scholes, phân tích Greeks và backtest danh mục nhiều chân (Multi-leg). Hoàn hảo cho Quyền chọn Crypto và Chứng khoán Mỹ.
category: asset-class
---

# Khung Chiến lược Quyền Chọn (Options Strategy Framework)

## Mục đích

Backtest các chiến lược kết hợp nhiều quyền chọn (Option portfolio). Bắt đầu từ giá tài sản cơ sở (Underlying), hệ thống sẽ tổng hợp giá quyền chọn lý thuyết qua mô hình Black-Scholes, sau đó mô phỏng PnL, độ rủi ro hệ số Greeks và quá trình thực thi khi đáo hạn (Expiration) cho các danh mục Đa chân (Multi-leg).

**Kịch bản Ứng dụng:**
- Chiến lược phòng vệ rủi ro (`Covered Call`, `Protective Put`).
- Chiến lược đánh biến động (`Straddle`, `Strangle`).
- Chiến lược chênh lệch (`Iron Condor`, `Butterfly`, `Calendar Spread`).
- Phân tích định giá và độ nhạy Greeks.

## Các loại Chiến lược Hỗ trợ

| Chiến lược | Cấu trúc lệnh | Phù hợp khi nào? |
|------|------|----------|
| Covered Call | Hold tài sản + Bán Call | Bullish nhẹ, muốn kiếm thêm lãi suất. |
| Protective Put | Hold tài sản + Mua Put | Bullish nhưng sợ rủi ro thị trường sập. |
| Straddle | Mua Call + Put cùng mức giá | Đoán sắp có bão lớn, không quan tâm hướng. |
| Strangle | Mua Call + Put khác mức giá | Giống Straddle nhưng rẻ hơn, bão phải to hơn. |
| Iron Condor | Bán Put Spread + Bán Call Spread | Đoán thị trường đi ngang, thu tiền bảo hiểm. |
| Butterfly | Mua Call Thấp + Bán 2 Call Giữa + Mua Call Cao | Đoán giá nằm im tại 1 điểm. |
| Calendar Spread| Bán tháng Gần + Mua tháng Xa | Ăn chênh lệch tốc độ tàn lụi thời gian (Theta). |

## Giao diện `OptionsSignalEngine`

Viết chiến lược trong `code/signal_engine.py`, tên class là `SignalEngine`, triển khai hàm `generate`:

```python
class SignalEngine:
    """Động cơ sinh tín hiệu Quyền chọn."""

    def generate(self, data_map: dict) -> list:
        """Sinh ra danh sách các lệnh Quyền chọn.

        Args:
            data_map: map code -> DataFrame (chứa open, high, low, close, volume)

        Returns:
            List các lệnh giao dịch. Định dạng mỗi lệnh:
            {
                "date": "2024-01-15",        # Ngày giao dịch
                "action": "open" / "close",  # Mở hoặc Đóng vị thế
                "underlying": "BTC-USDT",    # Mã tài sản cơ sở
                "legs": [                    # Danh sách các "Chân" quyền chọn
                    {
                        "type": "call" / "put",  # Loại quyền chọn
                        "strike": 50000,          # Mức giá thực thi (Strike)
                        "expiry": "2024-02-15",   # Ngày đáo hạn
                        "qty": 1                  # Số lượng (Dương = Mua, Âm = Bán)
                    }
                ]
            }
        """
```

### Ví dụ Lệnh Tổ hợp Đa chân (Multi-Leg)

Lệnh mở vị thế Iron Condor (Thần Ưng Sắt):

```python
{
    "date": "2024-01-15",
    "action": "open",
    "underlying": "BTC-USDT",
    "legs": [
        {"type": "put",  "strike": 38000, "expiry": "2024-02-15", "qty": -1},  # Bán Put
        {"type": "put",  "strike": 37000, "expiry": "2024-02-15", "qty":  1},  # Mua Put bảo vệ
        {"type": "call", "strike": 42000, "expiry": "2024-02-15", "qty": -1},  # Bán Call
        {"type": "call", "strike": 43000, "expiry": "2024-02-15", "qty":  1},  # Mua Call bảo vệ
    ]
}
```

## Định dạng file `config.json`

```json
{
    "codes": ["BTC-USDT"],
    "start_date": "2022-01-01",
    "end_date": "2024-12-31",
    "source": "okx",
    "engine": "options",
    "initial_cash": 1000000,
    "commission": 0.001,
    "options_config": {
        "risk_free_rate": 0.05,
        "iv_source": "historical",
        "contract_multiplier": 1.0
    }
}
```

**Các trường quan trọng**:
- `engine`: Bắt buộc là `"options"` để hệ thống kích hoạt engine backtest quyền chọn.
- `options_config.risk_free_rate`: Lãi suất phi rủi ro (Mặc định `0.05` tức 5%).
- `options_config.iv_source`: Nguồn tính Biến động (Hiện tại chỉ hỗ trợ `"historical"` - tính dựa trên dao động lịch sử 30 ngày của tài sản cơ sở).
- `options_config.contract_multiplier`: Hệ số nhân hợp đồng (Crypto thường là 1, Chứng khoán Mỹ là 100).

## Cơ chế Hoạt động của Mô hình BS

Bởi vì Engine này chạy theo mô hình **Dữ liệu Giả lập (Synthetic-data)**, nó không cần bạn kéo giá thật của Quyền chọn từ sàn về.
Thay vào đó, từ giá đóng cửa hàng ngày của BTC, engine sẽ tính ra Độ biến động (Historical Volatility), lắp vào công thức Black-Scholes để tính ra giá Quyền chọn lý thuyết tương ứng với ngày hôm đó.

## Ý nghĩa các hệ số Greeks

| Hệ số (Greek) | Ý nghĩa | Ứng dụng |
|-------|------|------|
| **Delta** | Giá thay đổi bao nhiêu khi tài sản tăng 1 USD. | Quản trị rủi ro định hướng, tính tỷ lệ phòng vệ (Hedge ratio). |
| **Gamma** | Gia tốc của Delta (Delta thay đổi bao nhiêu). | Đo lường độ ổn định. Gamma cao = Phải cắt lỗ/chốt lời liên tục. |
| **Theta** | Rò rỉ thời gian (Giá quyền chọn trừ đi bao nhiêu mỗi ngày). | Nguồn sống của hội "Bán quyền chọn". |
| **Vega** | Giá thay đổi bao nhiêu khi Biến động (IV) tăng 1%. | Thước đo bắt buộc khi giao dịch Straddle / Strangle. |

*Lưu ý: Engine sẽ tự động tính tổng Greeks của toàn bộ danh mục mỗi ngày và xuất ra file `greeks.csv`.*

## Cạm bẫy Thường gặp (Pitfalls)

1. **Nụ cười Biến động (Volatility Smile)**: Mô hình BS giả định IV là hằng số cho mọi mức giá (Strike). Thực tế ở OTM (Ngoài vùng giá), IV bị thổi phồng rất cao. Do đó, engine giả lập này có thể định giá hơi thấp cho các quyền chọn quá xa (Deep OTM). Đừng thiết kế chiến lược ăn chênh lệch li ti ở vùng Deep OTM.
2. **Rò rỉ Theta không tuyến tính**: Thời gian rớt giá mạnh nhất là vào 30 ngày cuối cùng. Bán quyền chọn thì ăn dày, nhưng rủi ro Gamma lúc này cũng cao như một quả bom.
3. **Thanh khoản và Trượt giá (Slippage)**: Dữ liệu giả lập không có Bid-Ask spread. Trong thực tế, quyền chọn OTM thanh khoản cực kỳ thê thảm, spread có thể ăn mất 20-30% lợi nhuận. Đừng quá ảo tưởng vào backtest.
4. **Quyền chọn Kiểu Mỹ**: KAIROS Engine hiện chỉ hỗ trợ Quyền chọn Kiểu Âu (Chỉ thực thi vào đúng ngày đáo hạn). Không hỗ trợ Early Exercise.

## Các File Dữ liệu Xuất ra (Artifacts)

| File | Nội dung |
|------|------|
| `equity.csv` | NAV hàng ngày, tiền mặt, giá trị danh mục. |
| `metrics.csv` | Lợi nhuận, Sharpe ratio, Max Drawdown. |
| `trades.csv` | Lịch sử lệnh (Mở / Đóng / Thực thi quyền). |
| `greeks.csv` | Tổng hợp Greeks danh mục hàng ngày (`delta/gamma/theta/vega`). |
| `ohlcv_{code}.csv` | Nến lịch sử của tài sản cơ sở. |
