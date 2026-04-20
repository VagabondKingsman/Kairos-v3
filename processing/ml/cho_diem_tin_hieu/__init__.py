"""
cho_diem_tin_hieu — Chấm Điểm Chất Lượng Tín Hiệu (Meta-Labeling)

Model: XGBoost Binary Classifier (Meta-Labeler cấp 2)
Input: Regime + Pattern + Anomaly + LSTM prob + Technical snapshot
Output: Score 0.0 → 1.0 + Kelly Fraction tối ưu
        ≥ 0.65 = Tín hiệu chất lượng cao → Vào lệnh
        <  0.65 = Tín hiệu yếu → Bỏ qua

Cách dùng:
    from processing.ml.cho_diem_tin_hieu import SignalScorerEngine

    scorer = SignalScorerEngine()
    result = scorer.predict(
        regime_id=3, signal_type=0, anomaly_score=20.0,
        pattern_id=1, prob_up=0.62, tech_snapshot={"RSI": 55, "ADX": 32, ...}
    )
    if result["is_high_quality"]:
        size = capital * result["kelly_fraction"]
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any

from processing.ml.cho_diem_tin_hieu.predict import (
    cho_diem_tin_hieu,
    cho_diem_batch,
    SCORE_THRESHOLD,
    _load,
)
from processing.ml.cho_diem_tin_hieu.model import (
    huan_luyen,
    huan_luyen_tu_log,
    DATA_DIR,
)

try:
    from data.store import A11
    DATA_DIR = A11.ml_model("cho_diem_tin_hieu")
except ImportError:
    DATA_DIR = Path(__file__).parent / "du_lieu"
    DATA_DIR.mkdir(parents=True, exist_ok=True)


class SignalScorerEngine:
    """Chấm điểm chất lượng tín hiệu bằng XGBoost Meta-Labeler."""

    SCORE_THRESHOLD = SCORE_THRESHOLD

    def __init__(self):
        _load()

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict(
        self,
        regime_id:     int   = 0,
        signal_type:   int   = 0,
        anomaly_score: float = 50.0,
        pattern_id:    int   = 0,
        prob_up:       float = 0.5,
        tech_snapshot: Dict[str, Any] = None,
    ) -> dict:
        """Chấm điểm 1 tín hiệu.

        Returns:
            {"score": float, "is_high_quality": bool, "kelly_fraction": float}
        """
        return cho_diem_tin_hieu(
            regime_id, signal_type, anomaly_score,
            pattern_id, prob_up, tech_snapshot or {},
        )

    def score(self, **kwargs) -> float:
        """Trả về score 0-1 (0.5 nếu chưa train)."""
        return self.predict(**kwargs)["score"]

    def is_high_quality(self, **kwargs) -> bool:
        """True nếu tín hiệu đạt ngưỡng chất lượng."""
        return self.predict(**kwargs)["is_high_quality"]

    def kelly_fraction(self, **kwargs) -> float:
        """Fraction vốn tối ưu theo Kelly Criterion (0-0.25)."""
        return self.predict(**kwargs)["kelly_fraction"]

    def score_batch(self, records: list) -> list[float]:
        """Chấm điểm hàng loạt tín hiệu."""
        return cho_diem_batch(records)

    # ── Training ──────────────────────────────────────────────────────────────

    def train(self, records: list[dict], n_estimators: int = 300) -> None:
        """Huấn luyện từ list records (xem features.py để biết format)."""
        huan_luyen(records, n_estimators=n_estimators)
        _load()

    def train_from_log(self, log_path: str) -> None:
        """Tự động đọc trading_memory.csv và huấn luyện."""
        huan_luyen_tu_log(log_path)
        _load()


__all__ = ["SignalScorerEngine", "DATA_DIR", "SCORE_THRESHOLD"]
