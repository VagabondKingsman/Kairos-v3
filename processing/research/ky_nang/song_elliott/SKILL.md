---
name: song_elliott
description: Elliott Wave cycle identification — W1/D1 wave count filter + H4 impulse/corrective entry via nen_htf.
category: strategy
---

# Elliott Wave Strategy

## Wave Theory Basics

Elliott Wave operates on **fractals**: the same 5-3 pattern repeats at every timeframe.

```
Impulse (5 waves):    1↑ 2↓ 3↑ 4↓ 5↑   → trend direction
Correction (3 waves): A↓ B↑ C↓           → counter-trend
```

**Fibonacci ratios** determine wave targets:
- Wave 3: 1.618 × Wave 1
- Wave 5: 1.0–1.618 × Wave 1
- Wave 2 retracement: 38.2%–61.8% of Wave 1
- Wave 4 retracement: 23.6%–38.2% of Wave 1 (should not overlap Wave 1)

## Multi-Timeframe Framework

```
W1 / D1  → Major wave count (which impulse wave are we in?)
H4       → Minor wave entry (Wave 3 or Wave C completion?)
H1       → Precise entry point
```

## Implementation

```python
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pandas as pd
import numpy as np
from typing import Dict
from a04_kho_chien_luoc_va_kiem_thu.nen_htf import XayDungNenHTF

class SignalEngine:
    """
    Simplified Elliott Wave proxy:
    - Uses swing pivots to count impulse legs
    - W1 trend defines primary direction
    - Enters after completion of corrective retracement (Wave 2/4 or A-B-C)
    """
    def __init__(self, swing_window: int = 10, fib_tolerance: float = 0.05):
        self._htf = XayDungNenHTF()
        self._swing = swing_window
        self._fib_tol = fib_tolerance

    def generate(self, data_map: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
        signals = {}
        for code, df in data_map.items():
            try:
                # W1 and D1 context
                df = self._htf.them_vao_df(df, "1W", prefix="w1")
                df = self._htf.them_vao_df(df, "1D", prefix="d1")
                signals[code] = self._compute(df)
            except Exception:
                signals[code] = pd.Series(0.0, index=df.index)
        return signals

    def _compute(self, df: pd.DataFrame) -> pd.Series:
        sig = pd.Series(0.0, index=df.index)
        w = self._swing

        # W1 trend: weekly close above 50-week MA = primary bull
        w1_ema50 = df["w1_close"].ewm(span=50, adjust=False).mean()
        w1_bull = df["w1_close"] > w1_ema50
        w1_bear = df["w1_close"] < w1_ema50

        # Swing highs/lows on base TF (simple pivot detection)
        roll_high = df["high"].rolling(w * 2 + 1, center=True).max()
        roll_low  = df["low"].rolling(w * 2 + 1, center=True).min()
        swing_high = (df["high"] == roll_high)
        swing_low  = (df["low"]  == roll_low)

        # Detect last swing high and low
        last_sh = df["high"][swing_high].reindex(df.index).ffill()
        last_sl = df["low"][swing_low].reindex(df.index).ffill()

        # Price retracement from last swing
        retrace = (df["close"] - last_sl) / (last_sh - last_sl + 1e-9)

        # Long: W1 bull + price retraced to golden zone (38.2%-61.8%) = Wave 2/4 completion
        golden_zone = (retrace >= 0.382) & (retrace <= 0.618)
        sig[w1_bull & golden_zone & swing_low] = 1.0

        # Short: W1 bear + price bounced to 38.2%-61.8% = corrective B wave done
        sig[w1_bear & golden_zone & swing_high] = -1.0

        return sig.fillna(0)
```

## config.json

```json
{
  "source": "okx",
  "codes": ["BTC-USDT"],
  "start_date": "2021-01-01",
  "end_date": "2026-01-01",
  "interval": "4H",
  "initial_cash": 1000000,
  "commission": 0.001,
  "engine": "crypto"
}
```

## Key Rules

- Elliott Wave **requires more history** than other strategies — use at least 2–3 years
- Wave 3 **cannot be the shortest** impulse wave
- Wave 4 **must not overlap** Wave 1 territory (invalidation rule)
- In Kairos: use `interval: "4H"` as base TF with W1 + D1 context from `nen_htf`
- The Fibonacci golden zone (38.2%–61.8%) is the primary entry region
