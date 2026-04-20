---
name: tao_chien_luoc
description: Tạo, chỉnh sửa và tối ưu hóa các chiến lược giao dịch định lượng với hỗ trợ đa khung thời gian (HTF) qua nen_htf, sau đó backtest và đánh giá.
category: strategy
---

## Quy trình làm việc (Workflow)

1. **Phân tích yêu cầu**: Hiểu ý định của người dùng, trích xuất mã giao dịch, khoảng thời gian, logic chiến lược → viết `config.json`
2. **Thiết kế chiến lược**: Trả lời 5 câu hỏi (dữ liệu / tín hiệu / bối cảnh HTF / quản lý vốn / kiểm định)
3. **Lập trình chiến lược**: Viết code vào `code/signal_engine.py` tuân thủ chuẩn `SignalEngine`
4. **Kiểm tra cú pháp**: Dùng `bash("python -c \"import ast; ast.parse(open('code/signal_engine.py').read()); print('OK')\"")`
5. **Chạy Backtest**: Gọi công cụ `backtest` (đã được tích hợp sẵn; KHÔNG viết file `run_backtest.py`)
6. **Đánh giá kết quả**: Đọc file `artifacts/metrics.csv`, đánh giá dựa trên tiêu chí kiểm duyệt
7. **Sửa lỗi lặp lại**: Nếu kết quả tệ → `edit_file` → `backtest` → đánh giá lại

**Bạn CHỈ CẦN viết `signal_engine.py` và `config.json`.**

---

## Đa khung thời gian (HTF) — BẮT BUỘC cho mọi chiến lược

Kairos sử dụng `XayDungNenHTF` từ thư mục `a04_kho_chien_luoc_va_kiem_thu.nen_htf` để xây dựng nến khung thời gian lớn **tuyệt đối không bị lỗi nhìn trước tương lai (lookahead bias)**.

### Mẫu Import chuẩn (luôn dùng mẫu này trong signal_engine.py)

```python
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pandas as pd
from a04_kho_chien_luoc_va_kiem_thu.nen_htf import XayDungNenHTF

class SignalEngine:
    def __init__(self):
        self._htf = XayDungNenHTF()

    def generate(self, data_map):
        signals = {}
        for code, df in data_map.items():
            # Thêm cột khung H4: h4_open, h4_high, h4_low, h4_close, h4_volume
            df_mtf = self._htf.them_vao_df(df, "4h", prefix="h4")
            # Thêm chiều xu hướng khung Ngày (D1)
            df_mtf = self._htf.them_vao_df(df_mtf, "1D", prefix="d1")
            signals[code] = self._compute(df_mtf)
        return signals

    def _compute(self, df):
        # Bộ lọc xu hướng HTF: Chỉ đánh Long khi nến D1 xanh (close > open)
        d1_bullish = df["d1_close"] > df["d1_open"]
        # Tín hiệu vào lệnh LTF: EMA cắt nhau trên khung thời gian cơ sở
        ema_fast = df["close"].ewm(span=12).mean()
        ema_slow = df["close"].ewm(span=26).mean()
        signal = pd.Series(0.0, index=df.index)
        signal[d1_bullish & (ema_fast > ema_slow)] = 1.0
        signal[~d1_bullish & (ema_fast < ema_slow)] = -1.0
        return signal.fillna(0)
```

### Các khung thời gian HTF được hỗ trợ

| Mã chuỗi | Ý nghĩa |
|--------|---------|
| `"15m"` | 15 Phút |
| `"1h"` | 1 Giờ |
| `"4h"` | 4 Giờ |
| `"1D"` | Ngày (Daily) |
| `"1W"` | Tuần (Weekly) |

### API của XayDungNenHTF

```python
# Ghép các cột HTF vào df gốc (với tiền tố h4_open/high/low/close/volume)
df = htf.them_vao_df(df, "4h", prefix="h4")

# Tạo riêng một DataFrame HTF độc lập
df_h4 = htf.build(df, "4h")

# Tạo nhiều khung thời gian cùng lúc
mtf = htf.build_multi(df, ["1h", "4h", "1D"])
# → {"1h": df_1h, "4h": df_4h, "1D": df_1D}
```

---

## Kỹ năng Chiến lược có sẵn (trong a04/ky_nang_chien_luoc/)

Thay vì viết lại từ đầu, hãy sử dụng các chiến lược đã được tích hợp sẵn:

| Chiến lược | Tên Module | HTF sử dụng | Lệnh load_skill() |
|----------|--------|-----|-------------|
| Dòng tiền thông minh (SMC) | `dong_tien_thong_minh_smc.py` | ✅ 4h | `load_skill("smc")` |
| Ichimoku Đa khung | `ichimoku_da_khung.py` | ✅ D1 | `load_skill("ichimoku")` |
| Sóng Elliott | `elliott_song.py` | ✅ W1 | `load_skill("elliott-wave")` |
| Kỹ thuật cơ bản (EMA/RSI/MACD) | `ky_thuat_co_ban.py` | ✅ 4h | `load_skill("technical-basic")` |
| Chiến lược Machine Learning | `chien_luoc_ml.py` | ✅ 4h | `load_skill("ml-strategy")` |

**Quy trình dùng chiến lược có sẵn:**
```text
1. load_skill("smc")              ← đọc phương pháp luận + mẫu SignalEngine
2. viết config.json               ← đặt interval là khung cơ sở (vd: "1H")
3. viết code/signal_engine.py     ← gọi SmcSignalEngine từ a04 HOẶC tự viết logic mới
4. backtest()
```

---

## Tích hợp Machine Learning (ML) vào Chiến lược

Khi người dùng muốn nâng cấp chiến lược bằng AI, sử dụng các module từ `a07_trung_tam_hoc_may`:

| Module ML | Lợi ích | Import |
|-----------|---------|--------|
| `trang_thai_thi_truong_ml` | Lọc bỏ tín hiệu trong chế độ xấu (DONG_BANG, NHIEU_DONG) | `from a07_trung_tam_hoc_may.trang_thai_thi_truong_ml import du_doan_trang_thai_ml_vector` |
| `cho_diem_tin_hieu` | Chấm điểm chất lượng tín hiệu (0→1), bỏ qua tín hiệu yếu | `from a07_trung_tam_hoc_may.cho_diem_tin_hieu import SignalScorerEngine` |
| `phat_hien_bat_thuong` | Tắt chiến lược khi Pump/Dump/Flash Crash | `from a07_trung_tam_hoc_may.phat_hien_bat_thuong import AnomalyEngine` |
| `phan_loai_nen` | Xác nhận tín hiệu bằng mô hình nến (Pinbar, Engulfing...) | `from a07_trung_tam_hoc_may.phan_loai_nen import CandlePatternEngine` |

**Khi người dùng yêu cầu tích hợp AI/ML vào chiến lược, luôn đọc kỹ năng `chien_luoc_machine_learning` trước.**


---

## Phân tích Yêu cầu

Trích xuất các thông tin sau từ yêu cầu của người dùng:
- **Mã giao dịch**: Chuẩn hóa theo quy tắc bên dưới.
- **Khoảng thời gian**: Nếu không chỉ định, mặc định lấy **2 năm tính từ hôm nay**.
- **Khung thời gian cơ sở** (`interval`): Khung thời gian nhỏ nhất dùng để tải dữ liệu (vd: `"1H"`).
- **Bối cảnh HTF**: Khung thời gian lớn dùng làm bộ lọc xu hướng (vd: `"4h"` hoặc `"1D"`).
- **Logic chiến lược**: Điều kiện vào lệnh / thoát lệnh, chỉ báo kỹ thuật.

**Nếu thiếu thông tin quan trọng, HÃY HỎI người dùng:**
- Không có mã giao dịch → hỏi (gợi ý BTC-USDT, AAPL.US)
- Chiến lược chung chung → đề xuất 2-3 hướng tiếp cận
- Khối lượng thị trường hỗn hợp → xác nhận lại nguồn dữ liệu

**Viết `config.json` ĐẦU TIÊN, sau đó mới viết code.**

---

## Hợp đồng (Contract) `SignalEngine`

```python
from typing import Dict
import pandas as pd

class SignalEngine:
    def generate(self, data_map: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
        """
        Tham số:
            data_map: dict map từ mã giao dịch (code) → DataFrame
                      Các cột: open, high, low, close, volume (DatetimeIndex)
        Trả về:
            code → Series tín hiệu, dải giá trị [-1.0, 1.0]
            1.0 = Mua toàn bộ (Long), 0.0 = Đứng ngoài (Flat), -1.0 = Bán khống (Short)
        """
```

**Ràng buộc cốt lõi:**
- Index của `Series` tín hiệu phải khớp CHÍNH XÁC với index của `DataFrame` đầu vào.
- Bao gồm đầy đủ các thư viện import (`numpy`, `pandas`, `typing`, `sys`, `os`).
- KHÔNG hardcode ngày tháng hoặc mã cổ phiếu trong code.
- KHÔNG sử dụng block `if __name__ == "__main__"`.
- KHÔNG import các thư viện tín hiệu bên ngoài (chỉ dùng `a04.nen_htf` cho HTF).
- In ra mã Python thuần túy, không để trong định dạng Markdown code fences.

---

## Danh sách Tự kiểm điểm (Quality Checklist)

Sau khi viết `signal_engine.py`:
- [ ] Đã import `from a04_kho_chien_luoc_va_kiem_thu.nen_htf import XayDungNenHTF`
- [ ] Bối cảnh HTF đã được thêm bằng `them_vao_df()` trước khi tính toán tín hiệu
- [ ] Đã import đủ các thư viện cần thiết
- [ ] Không có biến nào chưa được định nghĩa
- [ ] Dùng `fillna(0)` cho toàn bộ tín hiệu trước khi return
- [ ] Giá trị tín hiệu luôn nằm trong dải `[-1.0, 1.0]`
- [ ] Đối với danh mục đầu tư (Portfolio): Lọc ra top N mã → tỷ trọng mỗi mã = 1/N
- [ ] **Nếu dùng ML**: Import từ `a07_trung_tam_hoc_may.*` (KHÔNG dùng `from ml.*`)
- [ ] **Nếu dùng ML**: Gọi hàm `*_vector()` (vectorized) thay vì gọi từng nến (avoid lookahead)
- [ ] **Nếu dùng ML Regime**: Kiểm tra model đã train chưa (`du_lieu_ml/model_pytorch.pth`)


---

## Định dạng `config.json`

```json
{
  "source": "auto",
  "codes": ["BTC-USDT"],
  "start_date": "2024-01-01",
  "end_date": "2026-01-01",
  "interval": "1H",
  "initial_cash": 1000000,
  "commission": 0.001,
  "extra_fields": null,
  "optimizer": null,
  "optimizer_params": {},
  "engine": "crypto",
  "validation": null
}
```

| Trường (Field) | Tùy chọn | Ghi chú |
|-------|---------|------|
| `source` | `"auto"` / `"okx"` / `"yfinance"` / `"ccxt"` | Khuyên dùng `"auto"` |
| `interval` | `"1m"` `"5m"` `"15m"` `"30m"` `"1H"` `"4H"` `"1D"` | Khung thời gian tải dữ liệu (Base TF) |
| `engine` | `"crypto"` `"daily"` `"global_futures"` `"forex"` `"options"` | Tự động nhận diện nếu để trống |
| `optimizer` | `null` `"equal_volatility"` `"risk_parity"` `"mean_variance"` `"max_diversification"` | Trình tối ưu danh mục |
| `validation` | Xem bên dưới | Kiểm định thống kê (Tùy chọn) |

```json
"validation": {
  "monte_carlo": {"n_simulations": 1000},
  "bootstrap": {"n_bootstrap": 1000, "confidence": 0.95},
  "walk_forward": {"n_windows": 5}
}
```

---

## Chuẩn hóa Mã giao dịch (Instrument Code Normalization)

| Dạng thức | Thị trường | Nguồn dữ liệu (source) |
|---------|--------|--------|
| Chữ cái in hoa + `.US` | Chứng khoán Mỹ | yfinance |
| Chữ số + `.HK` | Chứng khoán HK | yfinance |
| `XXX-USDT` | Tiền điện tử (Crypto) | okx |
| `EUR/USD` v.v. | Forex | yfinance |

---

## Tiêu chí Đánh giá (Review Criteria)

### Điều kiện bắt buộc (Thất bại bất kỳ mục nào → `passed=false`)
1. File `artifacts/metrics.csv` tồn tại và không rỗng.
2. File `artifacts/equity.csv` tồn tại và không rỗng.
3. `exit_code == 0` (Code chạy không lỗi).
4. Cột `equity` không chứa giá trị `NaN`.
5. `trade_count > 0` (Có phát sinh giao dịch).

### Các loại lỗi Logic phổ biến
1. **Không có giao dịch (Zero trades)**: Điều kiện tín hiệu quá khắt khe.
2. **Vào lệnh quá trễ**: (Lệnh đầu tiên cách lúc bắt đầu quá 2 năm): Khung nhìn (lookback window) quá dài.
3. **Hiệu suất vốn < 50%**: Lỗi do quản lý vị thế, không mua hết tiền.
4. **Còn vị thế mở ở cuối kỳ**: Lỗi thiếu tín hiệu thoát lệnh (exit signal).

### Định dạng `action_items`
- `"Đổi X từ A sang B"` / `"Thêm logic X vào signal_engine.py"`
- Phải cụ thể (ghi rõ giá trị tham số, tên hàm).
- Có ít nhất 2 mục hành động.
