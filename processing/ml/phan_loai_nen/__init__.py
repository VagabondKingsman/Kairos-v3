"""
phan_loai_nen — Phân Loại Mẫu Nến (CNN 1D + KMeans)

Model: CNN 1D (PyTorch) + KMeans unsupervised (scikit-learn)
Input: Chuỗi 20 nến OHLCV
Output: Loại mẫu nến (0-9) + Confidence + Cluster ID

Cách dùng:
    from processing.ml.phan_loai_nen import CandleClassifier

    clf = CandleClassifier()
    result = clf.predict_live(df)          # {"pattern_id": 1, "pattern_name": "Pinbar_Tăng", ...}
    df_out = clf.predict_vector(df_1m)     # DataFrame với cột pattern_id, pattern_conf, cluster_id
    clf.train(df_1m)                       # Huấn luyện từ dữ liệu lịch sử
"""
from __future__ import annotations
from pathlib import Path
import polars as pl

from processing.ml.phan_loai_nen.predict import (
    phan_loai_nen_live,
    phan_loai_nen_vector,
    PATTERN_NAMES,
    _load,
)
from processing.ml.phan_loai_nen.model import huan_luyen, DATA_DIR

try:
    from data.store import A11
    DATA_DIR = A11.ml_model("phan_loai_nen")
except ImportError:
    DATA_DIR = Path(__file__).parent / "du_lieu"
    DATA_DIR.mkdir(parents=True, exist_ok=True)


class CandleClassifier:
    """Phân loại mẫu nến bằng CNN 1D + KMeans."""

    SEQ_LEN = 20

    def __init__(self):
        _load()

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict_live(self, df: pl.DataFrame) -> dict:
        """Dự đoán mẫu nến từ ~20 nến cuối (live).

        Returns:
            {"pattern_id": int, "pattern_name": str, "confidence": float, "cluster_id": int}
        """
        return phan_loai_nen_live(df)

    def predict(self, df: pl.DataFrame) -> int:
        """Trả về pattern_id (0-9). 0 = không có mẫu."""
        return phan_loai_nen_live(df)["pattern_id"]

    def predict_label(self, df: pl.DataFrame) -> str:
        """Trả về tên mẫu nến."""
        return phan_loai_nen_live(df)["pattern_name"]

    def predict_vector(self, df_1m: pl.DataFrame) -> pl.DataFrame:
        """Phân loại toàn bộ lịch sử (vectorized).

        Returns:
            df_1m với thêm cột: pattern_id, pattern_conf, cluster_id
        """
        return phan_loai_nen_vector(df_1m)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def is_bullish(self, df: pl.DataFrame) -> bool:
        return self.predict(df) in [1, 3, 6]

    def is_bearish(self, df: pl.DataFrame) -> bool:
        return self.predict(df) in [2, 4, 7]

    # ── Training ──────────────────────────────────────────────────────────────

    def train(self, df_1m: pl.DataFrame, epochs: int = 30) -> None:
        """Huấn luyện CandleCNN + KMeans từ dữ liệu OHLCV 1m lịch sử."""
        huan_luyen(df_1m, epochs=epochs)
        _load()  # Reload model sau khi train


__all__ = ["CandleClassifier", "PATTERN_NAMES", "DATA_DIR"]
