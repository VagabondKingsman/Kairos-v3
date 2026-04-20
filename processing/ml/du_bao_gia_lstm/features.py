"""
Xây dựng chuỗi đặc trưng (seq_len × n_features) cho LSTM.

Đầu vào: df_1m gốc + các cột bổ sung từ các module khác:
    - regime (int 0-7) từ trang_thai_thi_truong_ml
    - anomaly_score (float) từ phat_hien_bat_thuong
    - pattern_id (int 0-9) từ phan_loai_nen

Đầu ra: ma trận (N, SEQ_LEN, N_FEATURES) + nhãn Returns tương lai
"""
import numpy as np
import polars as pl

SEQ_LEN  = 60    # Chuỗi 60 nến 1m
N_REGIME = 8
N_PATTERN = 10

# Per-bar features: 6 kỹ thuật + 8 regime one-hot + 10 pattern one-hot + 1 anomaly = 25
N_FEATURES = 6 + N_REGIME + N_PATTERN + 1


def build_lstm_features(df: pl.DataFrame) -> pl.DataFrame:
    """Tính 6 đặc trưng kỹ thuật cơ bản per-bar (Polars vectorized)."""
    if "volume" not in df.columns:
        df = df.with_columns(pl.lit(1.0).alias("volume"))

    df = df.with_columns([
        (pl.col("high") - pl.col("low")).alias("_rng"),
    ]).with_columns([
        # Log return
        (pl.col("close").log() - pl.col("close").shift(1).log()).fill_nan(0.0).alias("ret"),
        # ATR normalized
        (pl.col("_rng").rolling_mean(14) / (pl.col("close") + 1e-9)).alias("atr_n"),
        # RSI (Cutler) 14
        pl.when(pl.col("close").diff() > 0).then(pl.col("close").diff()).otherwise(0)
         .rolling_mean(14).alias("_gain"),
        pl.when(pl.col("close").diff() < 0).then(pl.col("close").diff().abs()).otherwise(0)
         .rolling_mean(14).alias("_loss"),
        # Volume Z-score
        ((pl.col("volume") - pl.col("volume").rolling_mean(20)) /
         (pl.col("volume").rolling_std(20) + 1e-9)).alias("vol_z"),
        # Body proportion
        (
            (pl.max_horizontal("open", "close") - pl.min_horizontal("open", "close")) /
            (pl.col("_rng") + 1e-9)
        ).alias("body_prop"),
    ]).with_columns([
        (100 - 100 / (1 + pl.col("_gain") / (pl.col("_loss") + 1e-9))).alias("rsi"),
    ])

    df_out = df.select([
        "timestamp", "ret", "atr_n", "rsi", "vol_z", "body_prop",
        ((pl.col("close") - pl.col("close").rolling_mean(20)) /
         (pl.col("close").rolling_mean(20) + 1e-9)).alias("price_dev"),
    ])

    for c in ["ret", "atr_n", "rsi", "vol_z", "body_prop", "price_dev"]:
        df_out = df_out.with_columns(
            pl.when(pl.col(c).is_infinite() | pl.col(c).is_nan())
            .then(0.0).otherwise(pl.col(c)).alias(c)
        )
    return df_out


def build_lstm_sequences(
    df_feat: pl.DataFrame,
    regime_arr:  np.ndarray,
    anomaly_arr: np.ndarray,
    pattern_arr: np.ndarray,
    seq_len: int = SEQ_LEN,
    n_future: int = 5,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Ghép features + one-hot encode regime/pattern + anomaly thành ma trận chuỗi.

    Returns:
        X: (N, seq_len, N_FEATURES) float32
        y: (N,) float32  — log return tích lũy n_future nến tới (label)
    """
    base_cols = ["ret", "atr_n", "rsi", "vol_z", "body_prop", "price_dev"]
    X_base = df_feat.select(base_cols).fill_nan(0.0).fill_null(0.0).to_numpy().astype(np.float32)
    n = len(X_base)

    # One-hot regime (8) và pattern (10)
    regime_oh  = np.eye(N_REGIME,  dtype=np.float32)[np.clip(regime_arr.astype(int),  0, N_REGIME-1)]
    pattern_oh = np.eye(N_PATTERN, dtype=np.float32)[np.clip(pattern_arr.astype(int), 0, N_PATTERN-1)]
    anom_col   = (anomaly_arr / 100.0).astype(np.float32).reshape(-1, 1)

    X_all = np.concatenate([X_base, regime_oh, pattern_oh, anom_col], axis=1)  # (n, 25)

    # Close prices để tính label
    close = df_feat["ret"].to_numpy().astype(np.float32)  # ret là log return

    sequences, labels = [], []
    for i in range(seq_len - 1, n - n_future):
        seq = X_all[i - seq_len + 1: i + 1]
        # Label: log return tích lũy n_future nến kế tiếp
        future_ret = close[i + 1: i + 1 + n_future].sum()
        sequences.append(seq)
        labels.append(future_ret)

    if not sequences:
        return np.empty((0, seq_len, N_FEATURES), dtype=np.float32), np.empty(0, dtype=np.float32)

    return np.array(sequences, dtype=np.float32), np.array(labels, dtype=np.float32)
