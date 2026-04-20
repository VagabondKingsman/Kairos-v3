---
name: may_ichimoku
description: Chiến lược Mây Ichimoku đa khung thời gian — Lọc xu hướng trên khung Ngày (D1) bằng Kumo + Điểm vào lệnh giao cắt TK trên khung H4 (Sử dụng hệ thống nen_htf).
category: strategy
---

# Mây Ichimoku Đa Khung Thời Gian (Multi-Timeframe Ichimoku)

## Các thành phần của Ichimoku

| Đường (Line) | Tiếng Nhật | Chu kỳ | Mục đích |
|------|---------|--------|---------|
| Tenkan-sen | 転換線 | 9 | Đường Chuyển đổi (Tín hiệu nhanh) |
| Kijun-sen | 基準線 | 26 | Đường Tiêu chuẩn (Tín hiệu chậm) |
| Senkou Span A | 先行スパンA | (T+K)/2, dịch +26 | Biên trên/dưới của Mây Kumo |
| Senkou Span B | 先行スパンB | 52, dịch +26 | Biên trên/dưới của Mây Kumo |
| Chikou Span | 遅行スパン | Giá Đóng cửa, dịch -26| Đường Trễ (Dùng để xác nhận xu hướng) |

## Cấu trúc Đa Khung Thời Gian (Multi-Timeframe)

Bí quyết đánh Ichimoku là không bao giờ đánh 1 khung.

```text
Mây Kumo D1 (Khung Ngày)  → Xác định xu hướng chính (Trên Mây = Chỉ Mua, Dưới Mây = Chỉ Bán)
Giao cắt T-K H4 (Khung 4H) → Tìm tín hiệu kích hoạt (Trigger)
H1/M15                    → Chọn thời điểm bóp cò.
```

## Cách Triển khai Thực tế (Implementation)

Dùng thư viện `nen_htf` để nhúng khung Ngày (D1) vào khung Nhỏ mà không bị lỗi Nhìn trước tương lai (Lookahead bias).

```python
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pandas as pd
import numpy as np
from typing import Dict
from a04_kho_chien_luoc_va_kiem_thu.nen_htf import XayDungNenHTF

class SignalEngine:
    def __init__(self):
        self._htf = XayDungNenHTF()

    def generate(self, data_map: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
        signals = {}
        for code, df in data_map.items():
            try:
                # Đính kèm bối cảnh khung Ngày (D1) vào dữ liệu
                df = self._htf.them_vao_df(df, "1D", prefix="d1")
                signals[code] = self._compute(df)
            except Exception:
                signals[code] = pd.Series(0.0, index=df.index)
        return signals

    def _ichimoku(self, high, low, close, t=9, k=26, s=52):
        tenkan = (high.rolling(t).max() + low.rolling(t).min()) / 2
        kijun  = (high.rolling(k).max() + low.rolling(k).min()) / 2
        span_a = ((tenkan + kijun) / 2).shift(k)
        span_b = ((high.rolling(s).max() + low.rolling(s).min()) / 2).shift(k)
        chikou = close.shift(-k)
        return tenkan, kijun, span_a, span_b, chikou

    def _compute(self, df: pd.DataFrame) -> pd.Series:
        # Tính Ichimoku cho Khung Thời Gian Nhỏ (Base TF - Ví dụ H4)
        T, K, A, B, C = self._ichimoku(df["high"], df["low"], df["close"])

        # Lọc Xu hướng bằng Mây Kumo Khung Ngày (D1)
        d1_T, d1_K, d1_A, d1_B, _ = self._ichimoku(
            df["d1_high"], df["d1_low"], df["d1_close"]
        )
        # Nằm trên Mây
        d1_above_cloud = df["d1_close"] > d1_A.combine(d1_B, max)
        # Nằm dưới Mây
        d1_below_cloud = df["d1_close"] < d1_A.combine(d1_B, min)

        # Tín hiệu Khung Nhỏ (Giao cắt Tenkan & Kijun)
        tk_bull = (T > K) & (T.shift(1) <= K.shift(1))  # T cắt lên K
        tk_bear = (T < K) & (T.shift(1) >= K.shift(1))  # T cắt xuống K
        
        # Giá khung nhỏ cũng phải nằm trên/dưới Mây
        price_above_cloud = df["close"] > A.combine(B, max)
        price_below_cloud = df["close"] < A.combine(B, min)

        sig = pd.Series(0.0, index=df.index)
        # Lệnh Mua (Long)
        sig[d1_above_cloud & tk_bull & price_above_cloud] =  1.0
        # Lệnh Bán khống (Short)
        sig[d1_below_cloud & tk_bear & price_below_cloud] = -1.0
        
        return sig.fillna(0)
```

## `config.json` Mẫu

```json
{
  "source": "auto",
  "codes": ["BTC-USDT"],
  "start_date": "2023-01-01",
  "end_date": "2026-01-01",
  "interval": "4H", 
  "initial_cash": 1000000,
  "commission": 0.001,
  "engine": "crypto"
}
```

## Các Quy tắc Sống còn (Key Rules)

1. **Xoắn Mây (Kumo Twist)**: Khi Span A cắt Span B (Đổi màu mây). Đây là tín hiệu cực mạnh cảnh báo Đổi Xu Hướng. Cần cân nhắc chốt lời vị thế hiện tại.
2. **Tín hiệu Tuyệt đối (Strong Signal)**: Chỉ bóp cò khi 6 điều kiện đồng thuận (Mây D1 xanh, Mây H4 xanh, T cắt K, Chikou Span nằm trên mây, Chikou nằm trên đường giá, và Giá nằm trên Kijun). Tần suất vào lệnh sẽ rất thấp nhưng tỷ lệ thắng cực cao.
3. **Đường Trễ Chikou (Chikou Span)**: Đường này lùi lại 26 chu kỳ. Rất nguy hiểm nếu code nhầm vì nó chứa dữ liệu tương lai. Trong hệ thống backtest, không dùng Chikou để làm tín hiệu Trigger, chỉ dùng để check bằng mắt thường khi Trade tay.
4. **Không Trade ở Timeframe nhỏ**: Ichimoku cần nhiều dữ liệu nến (Tối thiểu 52 nến). Đừng chạy Ichimoku ở khung 1 Phút. Khuyến nghị `interval: "4H"` hoặc `"1D"`.
