"""
du_bao_gia_lstm — Dự Báo Giá Ngắn Hạn (LSTM + GRU)

Model: LSTM 2 lớp (PyTorch)
Input: Chuỗi 60 nến × 25 features (6 kỹ thuật + 8 regime one-hot + 10 pattern one-hot + 1 anomaly)
Output: prob_up (0.0 → 1.0) — xác suất giá tăng trong n nến tới

Cách dùng:
    from processing.ml.du_bao_gia_lstm import LSTMEngine

    engine = LSTMEngine()
    result = engine.predict_live(df_1m, regime_id=3, anomaly_score=20.0, pattern_id=1)
    df_out = engine.predict_vector(df_1m, regime_arr, anomaly_arr, pattern_arr)
    engine.train(df_1m, regime_arr, anomaly_arr, pattern_arr)
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import polars as pl

from processing.ml.du_bao_gia_lstm.predict import (
    du_bao_gia_live,
    du_bao_gia_vector,
    THRESHOLD_UP,
    THRESHOLD_DN,
    _load,
)
from processing.ml.du_bao_gia_lstm.model import huan_luyen, DATA_DIR

try:
    from data.store import A11
    DATA_DIR = A11.ml_model("du_bao_gia_lstm")
except ImportError:
    DATA_DIR = Path(__file__).parent / "du_lieu"
    DATA_DIR.mkdir(parents=True, exist_ok=True)


class LSTMEngine:
    """Engine dự báo giá bằng LSTM tích hợp Regime + Anomaly + Pattern."""

    SEQ_LEN      = 60
    THRESHOLD_UP = THRESHOLD_UP
    THRESHOLD_DN = THRESHOLD_DN

    def __init__(self):
        _load()

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict_live(
        self,
        df_1m: pl.DataFrame,
        regime_id:     int   = 0,
        anomaly_score: float = 50.0,
        pattern_id:    int   = 0,
    ) -> dict:
        """Dự báo cho nến kế tiếp (live).

        Returns:
            {"prob_up": float, "signal": "LONG"|"SHORT"|"NEUTRAL", "confidence": float}
        """
        return du_bao_gia_live(df_1m, regime_id, anomaly_score, pattern_id)

    def predict(self, df_1m: pl.DataFrame, **kwargs) -> float:
        """Trả về prob_up (0.0-1.0). 0.5 = trung tính."""
        return du_bao_gia_live(df_1m, **kwargs)["prob_up"]

    def predict_vector(
        self,
        df_1m:       pl.DataFrame,
        regime_arr:  np.ndarray | None = None,
        anomaly_arr: np.ndarray | None = None,
        pattern_arr: np.ndarray | None = None,
    ) -> pl.DataFrame:
        """Dự báo toàn bộ lịch sử (vectorized).

        Returns:
            df_1m với thêm cột: prob_up, lstm_conf
        """
        return du_bao_gia_vector(df_1m, regime_arr, anomaly_arr, pattern_arr)

    # ── Training ──────────────────────────────────────────────────────────────

    def train(
        self,
        df_1m:       pl.DataFrame,
        regime_arr:  np.ndarray | None = None,
        anomaly_arr: np.ndarray | None = None,
        pattern_arr: np.ndarray | None = None,
        epochs:      int = 30,
    ) -> None:
        """Huấn luyện LSTM từ dữ liệu lịch sử."""
        huan_luyen(df_1m, regime_arr, anomaly_arr, pattern_arr, epochs=epochs)
        _load()


__all__ = ["LSTMEngine", "DATA_DIR"]
