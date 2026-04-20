import json
import numpy as np
from pathlib import Path

from processing.ml.cho_diem_tin_hieu.model import (
    DATA_DIR, MODEL_PATH, INFO_PATH, SCORE_THRESHOLD,
)
from processing.ml.cho_diem_tin_hieu.features import xay_meta_vector
from utils.helpers import logger

_xgb_model = None


def _load():
    global _xgb_model
    if MODEL_PATH.exists():
        try:
            import xgboost as xgb
            m = xgb.XGBClassifier()
            m.load_model(str(MODEL_PATH))
            _xgb_model = m
        except Exception as e:
            logger.warning(f"cho_diem_tin_hieu XGB load lỗi: {e}")


_load()


def cho_diem_tin_hieu(
    regime_id:     int,
    signal_type:   int,        # 0=LONG, 1=SHORT
    anomaly_score: float,
    pattern_id:    int,
    prob_up:       float,
    tech_snapshot: dict,
) -> dict:
    """Chấm điểm chất lượng tín hiệu (meta-labeling).

    Returns:
        {"score": float 0-1, "is_high_quality": bool, "kelly_fraction": float}
    """
    if _xgb_model is None:
        return {"score": 0.5, "is_high_quality": False, "kelly_fraction": 0.0}

    vec = xay_meta_vector(regime_id, signal_type, anomaly_score, pattern_id, prob_up, tech_snapshot)
    X = vec.reshape(1, -1)

    try:
        prob = float(_xgb_model.predict_proba(X)[0][1])
    except Exception:
        prob = 0.5

    # Kelly Fraction: f* = (p*(b+1) - 1) / b
    # Giả sử win_rate=prob, win/loss ratio=1.5 (configurable)
    b = 1.5
    kelly = max(0.0, (prob * (b + 1) - 1) / b)
    kelly = min(kelly, 0.25)   # Tối đa 25% vốn một lệnh (Half-Kelly + cap)

    return {
        "score":           round(prob, 4),
        "is_high_quality": prob >= SCORE_THRESHOLD,
        "kelly_fraction":  round(kelly, 4),
    }


def cho_diem_batch(records: list[dict]) -> list[float]:
    """Chấm điểm hàng loạt tín hiệu. Trả về list scores."""
    if _xgb_model is None:
        return [0.5] * len(records)

    X_list = []
    for r in records:
        vec = xay_meta_vector(
            r.get("regime_id", 0),
            r.get("signal_type", 0),
            r.get("anomaly_score", 50.0),
            r.get("pattern_id", 0),
            r.get("prob_up", 0.5),
            r.get("tech_snapshot", {}),
        )
        X_list.append(vec)

    X = np.array(X_list, dtype=np.float32)
    try:
        probs = _xgb_model.predict_proba(X)[:, 1].tolist()
    except Exception:
        probs = [0.5] * len(records)

    return probs
