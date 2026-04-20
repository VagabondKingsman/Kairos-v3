"""trang_thai_thi_truong — Market Regime Classification Module.

Model: MLP ResBlock (PyTorch) + Weighted Cross-Entropy
Input: 72 multi-timeframe features (5M/15M/1H/4H) from OHLCV
Output: Market regime (0-7) + confidence score

Usage:
    from processing.ml.trang_thai_thi_truong import RegimeEngine

    engine = RegimeEngine()
    packet  = engine.predict_live(df_5m, df_15m, df_1h, df_4h, last_state=0)
    df_out  = engine.predict_vector(df_1m)
    engine.train(df_5m, df_15m, df_1h, df_4h)
"""
from __future__ import annotations
from pathlib import Path
import polars as pl

from processing.ml.trang_thai_thi_truong.predict import (
    predict_market_state,
    predict_state_vectorized,
    evaluate_prediction,
    STATE_MAP,
)
from processing.ml.trang_thai_thi_truong.model import (
    AI_Engine,
    train_model,
    auto_learn_from_log,
    train_from_dataframe,
)

try:
    from data.store import A11
    DATA_DIR = A11.ml_model("trang_thai_thi_truong")
except ImportError:
    DATA_DIR = Path(__file__).parent / "du_lieu_ml"
    DATA_DIR.mkdir(parents=True, exist_ok=True)


class RegimeEngine:
    """Market regime classifier using MLP ResBlock."""

    def __init__(self):
        self._engine = AI_Engine()

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict_live(self, df_5m, df_15m, df_1h, df_4h, last_state: int = 0) -> dict | None:
        """Predict market regime for the current bar (live mode).

        Returns:
            {"state_id": int, "state_name": str, "confidence": float, "probs": list}
            or None if insufficient data.
        """
        return predict_market_state(df_5m, df_15m, df_1h, df_4h, last_state=last_state)

    def predict(self, df_5m, df_15m, df_1h, df_4h, last_state: int = 0) -> int:
        """Return state_id (0-7)."""
        packet = predict_market_state(df_5m, df_15m, df_1h, df_4h, last_state=last_state)
        return packet["state_id"] if packet else 0

    def predict_vector(self, df_1m: pl.DataFrame) -> pl.DataFrame:
        """Predict regime for all bars in history (vectorized batch).

        Returns:
            df_1m with added columns: regime (int 0-7), confidence (float)
        """
        return predict_state_vectorized(df_1m)

    # ── Evaluation ────────────────────────────────────────────────────────────

    def evaluate(self, packet: dict, pnl: float, dd: float, correct: int = None) -> None:
        """Log trade result for reinforcement learning."""
        evaluate_prediction(packet, pnl, dd, correct=correct)

    # ── Training ──────────────────────────────────────────────────────────────

    def train(self, df_5m, df_15m, df_1h, df_4h) -> None:
        """Train from multi-timeframe OHLCV data."""
        train_model(df_5m, df_15m, df_1h, df_4h)

    def train_from_dataframe(self, df_labeled: pl.DataFrame, epochs: int = 20) -> None:
        """Train from a pre-labeled DataFrame with regime column (vectorized)."""
        train_from_dataframe(df_labeled, epochs=epochs)

    def learn_from_log(self) -> None:
        """Self-learn from trading_memory.csv (reinforcement loop)."""
        auto_learn_from_log()


__all__ = [
    "RegimeEngine",
    "STATE_MAP",
    "DATA_DIR",
    # New English names
    "predict_market_state",
    "predict_state_vectorized",
    "evaluate_prediction",
    "AI_Engine",
    "train_model",
    "auto_learn_from_log",
    "train_from_dataframe",
    # Backward-compatible aliases
    "du_doan_trang_thai_ml",
    "du_doan_trang_thai_ml_vector",
    "danh_gia_ml",
    "huan_luyen_model",
    "tu_dong_hoc_tu_log",
    "huan_luyen_tu_dataframe",
]

# Backward-compatible aliases
du_doan_trang_thai_ml       = predict_market_state
du_doan_trang_thai_ml_vector = predict_state_vectorized
danh_gia_ml                 = evaluate_prediction
huan_luyen_model            = train_model
tu_dong_hoc_tu_log          = auto_learn_from_log
huan_luyen_tu_dataframe     = train_from_dataframe
