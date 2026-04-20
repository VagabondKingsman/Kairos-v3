"""
Xây dựng vector đặc trưng Meta-Labeling cho SignalScorer.

Đầu vào: snapshot features của 1 tín hiệu tại thời điểm vào lệnh:
    - regime_id (0-7)
    - signal_type (0=LONG, 1=SHORT)
    - anomaly_score (0-100)
    - pattern_id (0-9)
    - prob_up (0-1) từ LSTM
    - Technical features (RSI, ADX, ATRn, BBwidth, VOLz, etc.)

Đầu ra: dict hoặc numpy array chuẩn để feed XGBoost
"""
from __future__ import annotations
import numpy as np

N_REGIME  = 8
N_PATTERN = 10
# 8 regime-OH + 10 pattern-OH + 2 signal + 1 anomaly + 1 prob_up + 8 tech = 30
N_META_FEATURES = N_REGIME + N_PATTERN + 2 + 1 + 1 + 8

TECH_FEATURES = ["RSI", "ADX", "ATRn", "BBwidth", "VOLz", "BBpctB", "ER", "SpreadATR"]


def build_meta_vector(
    regime_id:     int,
    signal_type:   int,       # 0=LONG, 1=SHORT
    anomaly_score: float,
    pattern_id:    int,
    prob_up:       float,
    tech_snapshot: dict,       # {"RSI": 55.2, "ADX": 30.1, ...}
) -> np.ndarray:
    """Tạo vector đặc trưng meta-labeling (30 chiều)."""
    # One-hot regime
    regime_oh  = np.zeros(N_REGIME,  dtype=np.float32)
    pattern_oh = np.zeros(N_PATTERN, dtype=np.float32)
    regime_oh[np.clip(regime_id,  0, N_REGIME-1)]  = 1.0
    pattern_oh[np.clip(pattern_id, 0, N_PATTERN-1)] = 1.0

    # Technical features (normalized / fallback 0)
    tech = np.array([
        float(tech_snapshot.get("RSI",       50.0)) / 100.0,
        float(tech_snapshot.get("ADX",       25.0)) / 100.0,
        float(tech_snapshot.get("ATRn",       0.0)),
        float(tech_snapshot.get("BBwidth",    0.0)),
        float(tech_snapshot.get("VOLz",       0.0)) / 5.0,
        float(tech_snapshot.get("BBpctB",     0.5)),
        float(tech_snapshot.get("ER",         0.5)),
        float(tech_snapshot.get("SpreadATR",  1.0)) / 3.0,
    ], dtype=np.float32)

    vec = np.concatenate([
        regime_oh,
        pattern_oh,
        np.array([float(signal_type), anomaly_score / 100.0], dtype=np.float32),
        np.array([prob_up], dtype=np.float32),
        tech,
    ])
    return vec  # (30,)


def build_meta_batch(records: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """
    Chuyển list records từ trading log thành (X, y) cho XGBoost.

    Mỗi record cần có:
        regime_id, signal_type, anomaly_score, pattern_id, prob_up,
        tech_snapshot (dict), label (1=win, 0=loss)
    """
    X, y = [], []
    for r in records:
        try:
            vec = build_meta_vector(
                regime_id     = r.get("regime_id", 0),
                signal_type   = r.get("signal_type", 0),
                anomaly_score = r.get("anomaly_score", 50.0),
                pattern_id    = r.get("pattern_id", 0),
                prob_up       = r.get("prob_up", 0.5),
                tech_snapshot = r.get("tech_snapshot", {}),
            )
            X.append(vec)
            y.append(int(r["label"]))   # 1=win, 0=loss
        except Exception:
            continue

    if not X:
        return np.empty((0, N_META_FEATURES), dtype=np.float32), np.empty(0, dtype=np.int32)

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32)
