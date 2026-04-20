"""
phat_hien_bat_thuong — Phát Hiện Bất Thường Thị Trường

Model: Isolation Forest + LSTM Autoencoder (PyTorch)
Input: OHLCV → 6 đặc trưng bất thường
Output: Anomaly Score (0 → 100). Score > 80 = Cảnh báo đỏ, tạm dừng giao dịch

Cách dùng:
    from processing.ml.phat_hien_bat_thuong import AnomalyEngine

    engine = AnomalyEngine()
    result = engine.predict_live(df)     # {"anomaly_score": 23.5, "is_anomaly": False, ...}
    df_out = engine.predict_vector(df_1m) # DataFrame với cột anomaly_score, is_anomaly
    engine.train(df_1m)                  # Huấn luyện từ dữ liệu lịch sử
"""
from __future__ import annotations
from pathlib import Path
import polars as pl

from processing.ml.phat_hien_bat_thuong.predict import (
    phat_hien_bat_thuong_live,
    phat_hien_bat_thuong_vector,
    ANOMALY_THRESHOLD,
    _load,
)
from processing.ml.phat_hien_bat_thuong.model import huan_luyen, DATA_DIR

try:
    from data.store import A11
    DATA_DIR = A11.ml_model("phat_hien_bat_thuong")
except ImportError:
    DATA_DIR = Path(__file__).parent / "du_lieu"
    DATA_DIR.mkdir(parents=True, exist_ok=True)


class AnomalyEngine:
    """Phát hiện bất thường bằng Isolation Forest + LSTM Autoencoder."""

    def __init__(self):
        _load()

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict_live(self, df: pl.DataFrame) -> dict:
        """Tính anomaly score cho cây nến cuối (live).

        Returns:
            {"anomaly_score": float, "is_anomaly": bool, "iso_score": float, "ae_score": float}
        """
        return phat_hien_bat_thuong_live(df)

    def predict(self, df: pl.DataFrame) -> float:
        """Trả về anomaly score 0-100. (50 = trung tính nếu chưa train)"""
        return phat_hien_bat_thuong_live(df)["anomaly_score"]

    def predict_vector(self, df_1m: pl.DataFrame) -> pl.DataFrame:
        """Tính anomaly score toàn bộ lịch sử (vectorized).

        Returns:
            df_1m với thêm cột: anomaly_score, is_anomaly
        """
        return phat_hien_bat_thuong_vector(df_1m)

    def is_anomaly(self, df: pl.DataFrame) -> bool:
        """True nếu thị trường đang bất thường (Pump/Dump/Flash Crash)."""
        return self.predict(df) > ANOMALY_THRESHOLD

    # ── Training ──────────────────────────────────────────────────────────────

    def train(self, df_1m: pl.DataFrame, epochs: int = 20,
              iso_contamination: float = 0.02) -> None:
        """Huấn luyện Isolation Forest + LSTM Autoencoder từ dữ liệu lịch sử."""
        huan_luyen(df_1m, epochs=epochs, iso_contamination=iso_contamination)
        _load()


__all__ = ["AnomalyEngine", "DATA_DIR", "ANOMALY_THRESHOLD"]
