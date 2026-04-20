import pickle
import numpy as np
import torch
import polars as pl

from processing.ml.phat_hien_bat_thuong.model import (
    AnomalyAutoencoder, DATA_DIR, device, N_FEAT, AE_SEQ_LEN,
    ISO_PATH, AE_PATH, SCALER_PATH,
)
from processing.ml.phat_hien_bat_thuong.features import (
    tao_feature_bat_thuong, xay_trinh_tu_ae,
)
from utils.helpers import logger

ANOMALY_THRESHOLD = 80.0  # Score > 80: Bất thường nghiêm trọng

_iso   = None
_ae    = None
_scaler = None


def _load():
    global _iso, _ae, _scaler
    if ISO_PATH.exists():
        with open(ISO_PATH, "rb") as f:
            _iso = pickle.load(f)
    if AE_PATH.exists():
        try:
            m = AnomalyAutoencoder(N_FEAT, 64, AE_SEQ_LEN).to(device)
            m.load_state_dict(torch.load(AE_PATH, map_location=device, weights_only=True))
            m.eval()
            _ae = m
        except Exception as e:
            logger.warning(f"phat_hien_bat_thuong AE load lỗi: {e}")
    if SCALER_PATH.exists():
        with open(SCALER_PATH, "rb") as f:
            _scaler = pickle.load(f)


_load()


def _iso_score(X_scaled: np.ndarray) -> np.ndarray:
    """Isolation Forest → score 0-100 (cao = bất thường hơn)."""
    if _iso is None:
        return np.full(len(X_scaled), 50.0)
    raw = _iso.decision_function(X_scaled)  # Positive = normal, negative = anomaly
    # Chuẩn hóa về 0-100: score cao = bất thường nhiều
    norm = (-raw - raw.min()) / (raw.max() - raw.min() + 1e-9)
    return (norm * 100).clip(0, 100)


def _ae_score(X_seq: np.ndarray) -> np.ndarray:
    """Autoencoder reconstruction error → score 0-100."""
    if _ae is None or len(X_seq) == 0:
        return np.full(len(X_seq), 50.0)

    X_tensor = torch.tensor(X_seq, dtype=torch.float32)
    errors = []
    with torch.no_grad():
        for i in range(0, len(X_tensor), 512):
            batch = X_tensor[i: i + 512].to(device)
            recon = _ae(batch)
            err = ((batch - recon) ** 2).mean(dim=(1, 2)).cpu().numpy()
            errors.extend(err.tolist())

    errors = np.array(errors)
    # Chuẩn hóa về 0-100
    norm = (errors - errors.min()) / (errors.max() - errors.min() + 1e-9)
    return (norm * 100).clip(0, 100)


def phat_hien_bat_thuong_live(df: pl.DataFrame) -> dict:
    """Tính anomaly score cho cây nến vừa đóng (live)."""
    if len(df) < AE_SEQ_LEN + 20:
        return {"anomaly_score": 50.0, "is_anomaly": False, "iso_score": 50.0, "ae_score": 50.0}

    df_feat = tao_feature_bat_thuong(df.tail(AE_SEQ_LEN + 20))
    feat_cols = ["ret_1", "ret_5", "spread_atr", "vol_z", "body_prop", "wick_extreme"]
    X_tab = df_feat.select(feat_cols).to_numpy().astype(np.float32)

    if _scaler is not None:
        X_scaled = _scaler.transform(X_tab)
    else:
        X_scaled = X_tab

    iso_s = float(_iso_score(X_scaled[-1:]).item())

    ae_s = 50.0
    X_seq = xay_trinh_tu_ae(df_feat, AE_SEQ_LEN)
    if len(X_seq) > 0:
        ae_s = float(_ae_score(X_seq[-1:]).item())

    # Ensemble: trọng số 60% IsoForest + 40% Autoencoder
    score = 0.6 * iso_s + 0.4 * ae_s

    return {
        "anomaly_score": round(score, 2),
        "is_anomaly": score > ANOMALY_THRESHOLD,
        "iso_score": round(iso_s, 2),
        "ae_score": round(ae_s, 2),
    }


def phat_hien_bat_thuong_vector(df_1m: pl.DataFrame) -> pl.DataFrame:
    """Tính anomaly score toàn bộ lịch sử (vectorized)."""
    df_feat = tao_feature_bat_thuong(df_1m)
    feat_cols = ["ret_1", "ret_5", "spread_atr", "vol_z", "body_prop", "wick_extreme"]
    ts = df_feat["timestamp"]
    n = len(ts)

    _default = df_1m.with_columns([
        pl.lit(50.0).alias("anomaly_score"),
        pl.lit(False).alias("is_anomaly"),
    ])

    X_tab = df_feat.select(feat_cols).to_numpy().astype(np.float32)
    if len(X_tab) == 0:
        return _default

    X_scaled = _scaler.transform(X_tab) if _scaler is not None else X_tab

    iso_scores = _iso_score(X_scaled)

    # Autoencoder scores với padding
    X_seq = xay_trinh_tu_ae(df_feat, AE_SEQ_LEN)
    pad = AE_SEQ_LEN - 1
    if len(X_seq) > 0:
        ae_raw = _ae_score(X_seq)
        ae_scores = np.concatenate([np.full(pad, 50.0), ae_raw])[:n]
    else:
        ae_scores = np.full(n, 50.0)

    scores = (0.6 * iso_scores + 0.4 * ae_scores).clip(0, 100)
    is_anom = scores > ANOMALY_THRESHOLD

    df_res = pl.DataFrame({
        "timestamp":     ts,
        "anomaly_score": scores.astype(np.float64),
        "is_anomaly":    is_anom,
    })

    return df_1m.join(df_res, on="timestamp", how="left").with_columns([
        pl.col("anomaly_score").fill_null(50.0),
        pl.col("is_anomaly").fill_null(False),
    ])
