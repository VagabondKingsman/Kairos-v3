---
name: phan_tich_ky_thuat_co_ban
description: Các chiến lược phân tích kỹ thuật kinh điển (EMA cắt nhau, RSI, MACD, Bollinger Bands) tích hợp bộ lọc xu hướng đa khung thời gian (HTF) qua nen_htf.
category: strategy
---

# Chiến lược Kỹ thuật Cơ bản (Technical Basic)

## Các chỉ báo được sử dụng

| Chỉ báo | Mục đích |
|-----------|---------|
| EMA Crossover | Hướng xu hướng + Điểm vào lệnh |
| RSI | Bộ lọc Quá mua / Quá bán |
| MACD | Xác nhận động lượng (Momentum) |
| Bollinger Bands | Độ biến động + Giao dịch đảo chiều (Mean reversion) |
| ATR | Tính toán khối lượng và mức cắt lỗ |

## Khung logic Đa Thời Gian (Multi-Timeframe)

```text
Xu hướng EMA D1  → Hướng chính của thị trường (chỉ mua / chỉ bán / cả hai)
RSI H4           → Bộ lọc động lượng trung hạn
EMA/MACD H1/M15  → Tín hiệu vào lệnh chính xác
```

## Triển khai (Implementation)

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
                # Đính kèm bối cảnh khung H4 và D1
                df = self._htf.them_vao_df(df, "4h", prefix="h4")
                df = self._htf.them_vao_df(df, "1D", prefix="d1")
                signals[code] = self._compute(df)
            except Exception:
                signals[code] = pd.Series(0.0, index=df.index)
        return signals

    def _compute(self, df: pd.DataFrame) -> pd.Series:
        # Tín hiệu Khung thời gian nhỏ (LTF)
        ema_fast = df["close"].ewm(span=12, adjust=False).mean()
        ema_slow = df["close"].ewm(span=26, adjust=False).mean()
        rsi = self._rsi(df["close"], 14)

        # Bộ lọc xu hướng Khung thời gian lớn (D1)
        d1_bull = df["d1_close"] > df["d1_close"].ewm(span=50, adjust=False).mean()
        d1_bear = df["d1_close"] < df["d1_close"].ewm(span=50, adjust=False).mean()

        # Bộ lọc động lượng Khung thời gian lớn (RSI H4)
        h4_rsi = self._rsi(df["h4_close"], 14)

        sig = pd.Series(0.0, index=df.index)
        
        # Mua (Long): Xu hướng D1 Tăng + RSI H4 chưa quá mua + EMA LTF cắt lên
        long_cond = d1_bull & (h4_rsi < 70) & (ema_fast > ema_slow) & (rsi > 45) & (rsi < 75)
        
        # Bán khống (Short): Xu hướng D1 Giảm + RSI H4 chưa quá bán + EMA LTF cắt xuống
        short_cond = d1_bear & (h4_rsi > 30) & (ema_fast < ema_slow) & (rsi < 55) & (rsi > 25)

        sig[long_cond]  =  1.0
        sig[short_cond] = -1.0
        return sig.fillna(0)

    @staticmethod
    def _rsi(series: pd.Series, n: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0).rolling(n).mean()
        loss = (-delta.clip(upper=0)).rolling(n).mean()
        rs = gain / (loss + 1e-9)
        return 100 - 100 / (1 + rs)
```

## `config.json`

```json
{
  "source": "auto",
  "codes": ["BTC-USDT"],
  "start_date": "2023-01-01",
  "end_date": "2026-01-01",
  "interval": "1H",
  "initial_cash": 1000000,
  "commission": 0.001,
  "extra_fields": null,
  "engine": "crypto"
}
```
