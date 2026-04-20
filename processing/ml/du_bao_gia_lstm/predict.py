import json
import numpy as np
import torch
import polars as pl

from processing.ml.du_bao_gia_lstm.model import (
    LSTMNet, DATA_DIR, device, N_FEATURES, HIDDEN, LAYERS, SEQ_LEN,
    MODEL_PATH, INFO_PATH,
)
from processing.ml.du_bao_gia_lstm.features import (
    build_lstm_features, build_lstm_sequences,
)
tao_feature_lstm  = build_lstm_features
xay_trinh_tu_lstm = build_lstm_sequences
from utils.helpers import logger

THRESHOLD_UP = 0.55
THRESHOLD_DN = 0.45

_lstm: LSTMNet | None = None


def _load():
    global _lstm
    if MODEL_PATH.exists():
        try:
            info = json.loads(INFO_PATH.read_text()) if INFO_PATH.exists() else {}
            m = LSTMNet(
                info.get("n_features", N_FEATURES),
                info.get("hidden", HIDDEN),
                info.get("n_layers", LAYERS),
            ).to(device)
            m.load_state_dict(torch.load(MODEL_PATH, map_location=device, weights_only=True))
            m.eval()
            _lstm = m
        except Exception as e:
            logger.warning(f"du_bao_gia_lstm load lỗi: {e}")


_load()


def predict_price_live(
    df_1m: pl.DataFrame,
    regime_id:    int   = 0,
    anomaly_score: float = 50.0,
    pattern_id:   int   = 0,
) -> dict:
    """Dự báo xác suất tăng giá cho nến kế tiếp (live)."""
    if _lstm is None:
        return {"prob_up": 0.5, "signal": "NEUTRAL", "confidence": 0.0}

    if len(df_1m) < SEQ_LEN + 20:
        return {"prob_up": 0.5, "signal": "NEUTRAL", "confidence": 0.0}

    df_feat = tao_feature_lstm(df_1m.tail(SEQ_LEN + 20))
    n = len(df_feat)
    regime_arr  = np.full(n, regime_id,     dtype=np.int32)
    anomaly_arr = np.full(n, anomaly_score, dtype=np.float32)
    pattern_arr = np.full(n, pattern_id,    dtype=np.int32)

    X, _ = xay_trinh_tu_lstm(df_feat, regime_arr, anomaly_arr, pattern_arr, n_future=1)
    if len(X) == 0:
        return {"prob_up": 0.5, "signal": "NEUTRAL", "confidence": 0.0}

    x_t = torch.tensor(X[-1:], dtype=torch.float32).to(device)
    with torch.no_grad():
        prob = float(_lstm(x_t).item())

    if prob > THRESHOLD_UP:
        signal = "LONG"
    elif prob < THRESHOLD_DN:
        signal = "SHORT"
    else:
        signal = "NEUTRAL"

    confidence = abs(prob - 0.5) * 2   # Chuẩn hóa về 0-1

    return {
        "prob_up": round(prob, 4),
        "signal": signal,
        "confidence": round(confidence, 4),
    }


def du_bao_gia_vector(
    df_1m: pl.DataFrame,
    regime_arr:  np.ndarray | None = None,
    anomaly_arr: np.ndarray | None = None,
    pattern_arr: np.ndarray | None = None,
) -> pl.DataFrame:
    """Dự báo xác suất tăng giá toàn bộ lịch sử (vectorized)."""
    _default = df_1m.with_columns([
        pl.lit(0.5).alias("prob_up"),
        pl.lit(0.0).alias("lstm_conf"),
    ])

    if _lstm is None:
        return _default

    df_feat = tao_feature_lstm(df_1m)
    n = len(df_feat)

    if regime_arr is None:  regime_arr  = np.zeros(n, dtype=np.int32)
    if anomaly_arr is None: anomaly_arr = np.full(n, 50.0, dtype=np.float32)
    if pattern_arr is None: pattern_arr = np.zeros(n, dtype=np.int32)

    X, _ = xay_trinh_tu_lstm(df_feat, regime_arr[:n], anomaly_arr[:n], pattern_arr[:n], n_future=1)
    if len(X) == 0:
        return _default

    _lstm.eval()
    X_tensor = torch.tensor(X, dtype=torch.float32)
    probs = []
    with torch.no_grad():
        for i in range(0, len(X_tensor), 512):
            batch = X_tensor[i: i + 512].to(device)
            p = _lstm(batch).cpu().numpy()
            probs.extend(p.tolist())

    probs_np = np.array(probs, dtype=np.float64)
    confs_np = np.abs(probs_np - 0.5) * 2

    pad = SEQ_LEN  # xay_trinh_tu_lstm cắt seq_len + n_future đầu
    ts = df_feat["timestamp"]
    full_p = np.concatenate([np.full(pad, 0.5), probs_np])[:len(ts)]
    full_c = np.concatenate([np.zeros(pad),      confs_np])[:len(ts)]

    df_res = pl.DataFrame({
        "timestamp": ts,
        "prob_up":   full_p,
        "lstm_conf": full_c,
    })

    return df_1m.join(df_res, on="timestamp", how="left").with_columns([
        pl.col("prob_up").fill_null(0.5),
        pl.col("lstm_conf").fill_null(0.0),
    ])
