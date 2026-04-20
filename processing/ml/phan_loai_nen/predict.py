import pickle
import numpy as np
import torch
import polars as pl

from processing.ml.phan_loai_nen.model import (
    CandleCNN, DATA_DIR, device, SEQ_LEN, N_FEATURES, N_PATTERNS,
    MODEL_PATH, KMEANS_PATH, SCALER_PATH,
)
from processing.ml.phan_loai_nen.features import tao_feature_nen, xay_trinh_tu
from utils.helpers import logger

PATTERN_NAMES = {
    0: "Không_có_mẫu", 1: "Pinbar_Tăng",    2: "Pinbar_Giảm",
    3: "Engulfing_Tăng", 4: "Engulfing_Giảm", 5: "Inside_Bar",
    6: "Morning_Star",   7: "Evening_Star",    8: "Doji", 9: "Spike",
}

_cnn: CandleCNN | None = None
_kmeans = None
_scaler = None


def _load():
    global _cnn, _kmeans, _scaler
    if MODEL_PATH.exists():
        try:
            m = CandleCNN().to(device)
            m.load_state_dict(torch.load(MODEL_PATH, map_location=device, weights_only=True))
            m.eval()
            _cnn = m
        except Exception as e:
            logger.warning(f"phan_loai_nen CNN load lỗi: {e}")
    if KMEANS_PATH.exists():
        with open(KMEANS_PATH, "rb") as f:
            _kmeans = pickle.load(f)
    if SCALER_PATH.exists():
        with open(SCALER_PATH, "rb") as f:
            _scaler = pickle.load(f)


_load()


def phan_loai_nen_live(df: pl.DataFrame) -> dict:
    """Dự đoán mẫu nến từ ~20 nến cuối (live bar-by-bar)."""
    if len(df) < SEQ_LEN:
        return {"pattern_id": 0, "pattern_name": PATTERN_NAMES[0], "confidence": 0.0, "cluster_id": -1}

    df_feat = tao_feature_nen(df.tail(SEQ_LEN + 25))
    seq = xay_trinh_tu(df_feat, SEQ_LEN)
    if len(seq) == 0:
        return {"pattern_id": 0, "pattern_name": PATTERN_NAMES[0], "confidence": 0.0, "cluster_id": -1}

    last = seq[-1:]

    pattern_id, confidence = 0, 0.0
    if _cnn is not None:
        x = torch.tensor(last, dtype=torch.float32).to(device)
        with torch.no_grad():
            probs = torch.softmax(_cnn(x), dim=1)[0]
            conf, pred = torch.max(probs, 0)
        pattern_id = int(pred.item())
        confidence = float(conf.item())

    cluster_id = -1
    if _kmeans is not None and _scaler is not None:
        flat_s = _scaler.transform(last.reshape(1, -1))
        cluster_id = int(_kmeans.predict(flat_s)[0])

    return {
        "pattern_id": pattern_id,
        "pattern_name": PATTERN_NAMES.get(pattern_id, "Unknown"),
        "confidence": round(confidence, 4),
        "cluster_id": cluster_id,
    }


def phan_loai_nen_vector(df_1m: pl.DataFrame) -> pl.DataFrame:
    """Phân loại mẫu nến toàn bộ lịch sử (vectorized inference)."""
    df_feat = tao_feature_nen(df_1m)
    ts = df_feat["timestamp"]

    _default = df_1m.with_columns([
        pl.lit(0).cast(pl.Int32).alias("pattern_id"),
        pl.lit(0.0).alias("pattern_conf"),
        pl.lit(-1).cast(pl.Int32).alias("cluster_id"),
    ])

    X_seq = xay_trinh_tu(df_feat, SEQ_LEN)
    if len(X_seq) == 0 or _cnn is None:
        return _default

    _cnn.eval()
    X_tensor = torch.tensor(X_seq, dtype=torch.float32)
    preds, confs = [], []

    with torch.no_grad():
        for i in range(0, len(X_tensor), 1024):
            batch = X_tensor[i: i + 1024].to(device)
            probs = torch.softmax(_cnn(batch), dim=1)
            c, p = torch.max(probs, dim=1)
            preds.extend(p.cpu().numpy().tolist())
            confs.extend(c.cpu().numpy().tolist())

    preds_np = np.array(preds, dtype=np.int32)
    confs_np = np.array(confs, dtype=np.float64)

    # KMeans clusters (batch)
    if _kmeans is not None and _scaler is not None:
        X_flat = X_seq.reshape(len(X_seq), -1)
        X_flat_s = _scaler.transform(X_flat)
        clusters = _kmeans.predict(X_flat_s).astype(np.int32)
    else:
        clusters = np.full(len(X_seq), -1, dtype=np.int32)

    pad = SEQ_LEN - 1
    n = len(ts)
    full_p = np.concatenate([np.zeros(pad, np.int32),   preds_np])[:n]
    full_c = np.concatenate([np.zeros(pad),              confs_np])[:n]
    full_k = np.concatenate([np.full(pad, -1, np.int32), clusters])[:n]

    df_res = pl.DataFrame({
        "timestamp":   ts,
        "pattern_id":  full_p,
        "pattern_conf": full_c,
        "cluster_id":  full_k,
    })

    return df_1m.join(df_res, on="timestamp", how="left").with_columns([
        pl.col("pattern_id").fill_null(0).cast(pl.Int32),
        pl.col("pattern_conf").fill_null(0.0),
        pl.col("cluster_id").fill_null(-1).cast(pl.Int32),
    ])
