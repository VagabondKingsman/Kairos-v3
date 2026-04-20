import json
import numpy as np
from pathlib import Path

from processing.ml.cho_diem_tin_hieu.features import build_meta_batch, N_META_FEATURES
xay_meta_batch = build_meta_batch   # backward-compat alias
from utils.helpers import logger

try:
    from data.store import A11
    DATA_DIR = A11.ml_model("cho_diem_tin_hieu")
except ImportError:
    DATA_DIR = Path(__file__).parent / "du_lieu"
    DATA_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = DATA_DIR / "xgb_model.json"
INFO_PATH  = DATA_DIR / "model_info.json"

SCORE_THRESHOLD = 0.65


def train_signal_scorer(records: list[dict], n_estimators: int = 300, max_depth: int = 4) -> None:
    """Huấn luyện XGBoost meta-labeler từ danh sách trading records.

    Mỗi record phải có: regime_id, signal_type, anomaly_score, pattern_id,
                        prob_up, tech_snapshot (dict), label (1=win / 0=loss)
    """
    try:
        import xgboost as xgb
    except ImportError:
        logger.error("cho_diem_tin_hieu | Cần cài xgboost: pip install xgboost")
        return

    logger.info("cho_diem_tin_hieu | Bước 1: Xây dựng meta-feature batch...")
    X, y = xay_meta_batch(records)

    if len(X) < 20:
        logger.warning("cho_diem_tin_hieu | Cần ít nhất 20 records để train.")
        return

    logger.info(f"cho_diem_tin_hieu | Train XGBoost trên {len(X)} records (Win rate: {y.mean():.2%})...")

    pos = y.sum()
    neg = len(y) - pos
    scale_pos = float(neg) / (pos + 1e-9)

    model = xgb.XGBClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos,
        eval_metric="logloss",
        use_label_encoder=False,
        random_state=42,
        n_jobs=-1,
    )

    split = int(len(X) * 0.85)
    model.fit(
        X[:split], y[:split],
        eval_set=[(X[split:], y[split:])],
        verbose=False,
    )

    model.save_model(str(MODEL_PATH))
    with open(INFO_PATH, "w") as f:
        json.dump({
            "n_features": N_META_FEATURES,
            "n_estimators": n_estimators,
            "score_threshold": SCORE_THRESHOLD,
            "win_rate": float(y.mean()),
        }, f)
    logger.success(f"cho_diem_tin_hieu | Train xong XGBoost! Win rate: {y.mean():.2%}")


def huan_luyen_tu_log(log_path: str, pnl_col: str = "pnl") -> None:
    """Tự động đọc trading_memory.csv và build records để train."""
    import csv
    import json as _json

    records = []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    pnl = float(row.get(pnl_col, 0))
                    feat = _json.loads(row.get("features_json", "{}"))
                    records.append({
                        "regime_id":     int(row.get("state", 0)),
                        "signal_type":   0,     # Không có thông tin, mặc định LONG
                        "anomaly_score": 50.0,
                        "pattern_id":    0,
                        "prob_up":       0.5,
                        "tech_snapshot": feat,
                        "label":         1 if pnl > 0 else 0,
                    })
                except Exception:
                    continue
    except Exception as e:
        logger.error(f"cho_diem_tin_hieu | Lỗi đọc log: {e}")
        return

    if records:
        huan_luyen(records)
    else:
        logger.warning("cho_diem_tin_hieu | Không tìm thấy records hợp lệ trong log.")
