---
name: chien_luoc_machine_learning
description: Tích hợp 6 module Machine Learning từ a07_trung_tam_hoc_may vào chiến lược giao dịch — Phân loại chế độ thị trường (Regime), chấm điểm tín hiệu (Signal Scoring), dự báo giá (LSTM), phát hiện bất thường (Anomaly Detection), nhận diện nến (Candlestick CNN), và tối ưu danh mục (Portfolio Optimization).
category: strategy
---

# Chiến lược Tích hợp Machine Learning (ML Integration)

## Kiến trúc Hệ thống ML trong KAIROS

```text
a07_trung_tam_hoc_may/
├── trang_thai_thi_truong_ml/  → Module 1: MLP — Phân loại Chế độ Thị trường (Regime 0-7)
├── du_bao_gia_lstm/           → Module 2: LSTM — Dự báo hướng giá ngắn hạn
├── phat_hien_bat_thuong/      → Module 3: Isolation Forest — Phát hiện Pump/Dump/Black Swan
├── cho_diem_tin_hieu/         → Module 4: XGBoost — Chấm điểm chất lượng tín hiệu
├── phan_loai_nen/             → Module 5: CNN 1D — Nhận diện mô hình nến đặc biệt
└── toi_uu_danh_muc/           → Module 6: Markowitz/RL — Tối ưu phân bổ danh mục
```

---

## Module 1: Phân Loại Chế Độ Thị Trường (Regime Classification)

Nhận diện 8 trạng thái thị trường để áp dụng chiến lược phù hợp:

| ID | Tên Trạng Thái | Chiến Lược Phù Hợp |
|----|------|--------|
| 0 | `DONG_BANG` | Đứng ngoài tuyệt đối |
| 1 | `NEN_CHAT` | Canh Breakout (Phá vỡ vùng nén) |
| 2 | `DAU_XU_HUONG` | Vào lệnh sớm theo xu hướng mới |
| 3 | `XU_HUONG_MANH` | Follow Trend mạnh (EMA / Ichimoku) |
| 4 | `CAO_TRAO` | Scale out / Chốt lời một phần |
| 5 | `HOI_QUY` | Counter-trend / Mean Reversion |
| 6 | `NHIEU_DONG` | Đánh Range hoặc đứng ngoài |
| 7 | `DAO_CHIEU` | Canh đảo chiều (Cần xác nhận cấu trúc) |

### Code Tích Hợp Module 1 vào SignalEngine

```python
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pandas as pd
from typing import Dict
from a04_kho_chien_luoc_va_kiem_thu.nen_htf import XayDungNenHTF
from a07_trung_tam_hoc_may.trang_thai_thi_truong_ml import (
    du_doan_trang_thai_ml_vector,
    STATE_MAP
)

class SignalEngine:
    """
    Chiến lược kết hợp ML Regime + nen_htf đa khung thời gian.
    Dữ liệu base TF = 1H. ML nhận diện regime từ 4 khung (5M/15M/1H/4H).
    """
    def __init__(self):
        self._htf = XayDungNenHTF()

    def generate(self, data_map: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
        signals = {}
        for code, df in data_map.items():
            try:
                signals[code] = self._compute(df)
            except Exception:
                signals[code] = pd.Series(0.0, index=df.index)
        return signals

    def _compute(self, df: pd.DataFrame) -> pd.Series:
        # 1. Nhận diện Chế độ Thị Trường bằng ML (vectorized — không lookahead)
        import polars as pl
        df_pl = pl.from_pandas(df.reset_index().rename(columns={"index": "timestamp"}))
        df_regime = du_doan_trang_thai_ml_vector(df_pl)

        # 2. Map kết quả về Pandas Series
        regime_series = df_regime["regime"].to_pandas()
        regime_series.index = df.index[:len(regime_series)]

        sig = pd.Series(0.0, index=df.index)

        # 3. Quy tắc giao dịch theo từng Regime
        ema_fast = df["close"].ewm(span=12).mean()
        ema_slow = df["close"].ewm(span=26).mean()
        trend_up = ema_fast > ema_slow
        trend_dn = ema_fast < ema_slow

        # Regime 1 — NEN_CHAT: Canh Breakout
        r1 = regime_series == 1
        sig[r1 & trend_up] = 1.0
        sig[r1 & trend_dn] = -1.0

        # Regime 2,3 — DAU_XU_HUONG / XU_HUONG_MANH: Follow trend
        r23 = regime_series.isin([2, 3])
        sig[r23 & trend_up] = 1.0
        sig[r23 & trend_dn] = -1.0

        # Regime 4 — CAO_TRAO: Giảm vị thế (tín hiệu yếu)
        sig[regime_series == 4] = 0.0

        # Regime 0, 6, 7 — DONG_BANG / NHIEU_DONG / DAO_CHIEU: Đứng ngoài
        sig[regime_series.isin([0, 6, 7])] = 0.0

        return sig.fillna(0)
```

---

## Module 4: Chấm Điểm Tín Hiệu (Signal Scoring — XGBoost)

Dùng để **lọc bỏ các tín hiệu chất lượng thấp** trước khi vào lệnh. Bất kỳ chiến lược nào cũng có thể dùng bộ chấm điểm này.

```python
from a07_trung_tam_hoc_may.cho_diem_tin_hieu import SignalScorerEngine

scorer = SignalScorerEngine()

# Mỗi lần chuẩn bị vào lệnh, gọi chấm điểm:
score = scorer.predict(signal_features_dict)
# score = 0.0 → 1.0 (≥ 0.65: Tín hiệu tốt; < 0.65: Bỏ qua)

if score >= 0.65:
    # Vào lệnh
    sig[i] = 1.0
```

---

## Module 3: Phát Hiện Bất Thường (Anomaly Detection)

Dùng để **tắt chiến lược** trong những giai đoạn thị trường bất thường (Pump/Dump, Flash Crash, Tin tức kinh tế cực lớn).

```python
from a07_trung_tam_hoc_may.phat_hien_bat_thuong import AnomalyEngine

anomaly_detector = AnomalyEngine()

# Tính điểm bất thường cho DataFrame
anomaly_score = anomaly_detector.predict(df)   # 0 → 100
# Score > 80: Thị trường bất thường — không vào lệnh mới
sig[anomaly_score > 80] = 0.0
```

---

## Mẫu SignalEngine Tích Hợp Đầy Đủ (3 Module ML)

Mẫu "Vàng" kết hợp: **Regime Filter + Signal Scorer + Anomaly Guard**

```python
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pandas as pd
import polars as pl
from typing import Dict
from a04_kho_chien_luoc_va_kiem_thu.nen_htf import XayDungNenHTF
from a07_trung_tam_hoc_may.trang_thai_thi_truong_ml import du_doan_trang_thai_ml_vector

class SignalEngine:
    def __init__(self):
        self._htf = XayDungNenHTF()

    def generate(self, data_map: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
        signals = {}
        for code, df in data_map.items():
            try:
                # 1. Thêm ngữ cảnh HTF (không lookahead)
                df_mtf = self._htf.them_vao_df(df, "4h", prefix="h4")
                df_mtf = self._htf.them_vao_df(df_mtf, "1D", prefix="d1")

                # 2. Nhận diện regime bằng ML
                df_pl = pl.from_pandas(df.reset_index().rename(columns={"index": "timestamp"}))
                df_regime = du_doan_trang_thai_ml_vector(df_pl)
                regime = df_regime["regime"].to_pandas()
                regime.index = df.index[:len(regime)]

                # 3. Tín hiệu kỹ thuật cơ bản
                ema_fast = df_mtf["close"].ewm(span=12).mean()
                ema_slow = df_mtf["close"].ewm(span=26).mean()

                sig = pd.Series(0.0, index=df_mtf.index)
                # Chỉ Long khi: xu hướng cơ bản tốt AND regime phù hợp AND d1 tăng
                d1_bull = df_mtf["d1_close"] > df_mtf["d1_open"]
                trade_regime = regime.isin([1, 2, 3])
                sig[d1_bull & trade_regime & (ema_fast > ema_slow)] = 1.0
                sig[~d1_bull & trade_regime & (ema_fast < ema_slow)] = -1.0

                # Tắt tín hiệu khi regime nguy hiểm
                sig[regime.isin([0, 4, 7])] = 0.0

                signals[code] = sig.fillna(0)
            except Exception:
                signals[code] = pd.Series(0.0, index=df.index)
        return signals
```

---

## Quy Trình Tích Hợp ML Từng Bước

```text
Bước 1: Kiểm tra model đã train chưa
    → Xem file trang_thai_thi_truong_ml/du_lieu_ml/model_pytorch.pth có tồn tại không

Bước 2: Nếu chưa có model → Khởi tạo "Bộ não trắng"
    from a07_trung_tam_hoc_may.trang_thai_thi_truong_ml import huan_luyen_model
    huan_luyen_model(df_5m, df_15m, df_1h, df_4h)

Bước 3: Viết SignalEngine theo mẫu Tích hợp ML ở trên

Bước 4: Chạy Backtest với config.json có interval="1H"

Bước 5: Sau khi thu thập log thực tế → Tái huấn luyện
    from a07_trung_tam_hoc_may.trang_thai_thi_truong_ml import tu_dong_hoc_tu_log
    tu_dong_hoc_tu_log()
```

---

## `config.json` Mẫu Cho Chiến Lược ML

```json
{
  "source": "okx",
  "codes": ["BTC-USDT", "ETH-USDT"],
  "start_date": "2023-01-01",
  "end_date": "2026-01-01",
  "interval": "1H",
  "initial_cash": 1000000,
  "commission": 0.001,
  "engine": "crypto",
  "validation": {
    "walk_forward": {"n_windows": 5}
  }
}
```

> [!IMPORTANT]
> **Cấm Lookahead trong ML**: Module `du_doan_trang_thai_ml_vector()` đã được thiết kế để chạy trên toàn bộ DataFrame lịch sử mà KHÔNG bị lỗi nhìn trước tương lai. Mỗi dự đoán tại nến `t` chỉ sử dụng dữ liệu từ nến `t-1` trở về trước (Vectorized Inference).

## Cạm bẫy (Pitfalls)

1. **Gọi ML bên trong vòng lặp từng nến** (`bar-by-bar`) sẽ RẤT CHẬM và dễ gây lỗi lookahead. Luôn dùng hàm `*_vector()` để xử lý toàn bộ DataFrame một lần.
2. **Model chưa được train** → Tất cả dự đoán đều trả về regime 0 (DONG_BANG). Chiến lược sẽ không ra tín hiệu. Phải khởi tạo "Bộ não trắng" trước khi backtest.
3. **Lệch feature**: Nếu thêm/bớt feature trong `tao_feature.py` sau khi đã train, model cũ sẽ bị lỗi. Phải train lại hoàn toàn sau mỗi lần thay đổi feature.
