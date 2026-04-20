import numpy as np
import polars as pl

AE_SEQ_LEN = 30   # Autoencoder dùng chuỗi 30 nến


def build_anomaly_features(df: pl.DataFrame) -> pl.DataFrame:
    """7 đặc trưng phát hiện bất thường từ OHLCV (Polars vectorized)."""
    if "volume" not in df.columns:
        df = df.with_columns(pl.lit(1.0).alias("volume"))

    df = df.with_columns([
        (pl.col("high") - pl.col("low")).alias("_rng"),
        (pl.col("close").log() - pl.col("close").shift(1).log()).alias("ret_1"),
    ]).with_columns([
        (pl.col("close").log() - pl.col("close").shift(5).log()).fill_nan(0.0).alias("ret_5"),
        # ATR 14
        pl.col("_rng").rolling_mean(14).alias("atr14"),
        # Volume Z-score
        pl.col("volume").rolling_mean(20).alias("vol_ma"),
        pl.col("volume").rolling_std(20).alias("vol_std"),
        # Body proportion
        (
            (pl.max_horizontal("open", "close") - pl.min_horizontal("open", "close")) /
            (pl.col("_rng") + 1e-9)
        ).alias("body_prop"),
    ]).with_columns([
        # Spread / ATR — spike khi spread to bất thường
        (pl.col("_rng") / (pl.col("atr14") + 1e-9)).alias("spread_atr"),
        # Volume Z-score
        ((pl.col("volume") - pl.col("vol_ma")) / (pl.col("vol_std") + 1e-9)).alias("vol_z"),
        # Wick extreme (bóng lớn nhất / range)
        (
            pl.max_horizontal(
                (pl.col("high") - pl.max_horizontal("open", "close")) / (pl.col("_rng") + 1e-9),
                (pl.min_horizontal("open", "close") - pl.col("low")) / (pl.col("_rng") + 1e-9),
            )
        ).alias("wick_extreme"),
    ])

    feat_cols = ["timestamp", "ret_1", "ret_5", "spread_atr", "vol_z", "body_prop", "wick_extreme"]
    df_out = df.select(feat_cols)

    # Khử infinity và NaN
    for c in feat_cols[1:]:
        df_out = df_out.with_columns(
            pl.when(pl.col(c).is_infinite() | pl.col(c).is_nan())
            .then(0.0)
            .otherwise(pl.col(c))
            .alias(c)
        )

    return df_out


def build_ae_sequences(df_feat: pl.DataFrame, seq_len: int = AE_SEQ_LEN) -> np.ndarray:
    """Xây ma trận (N, seq_len, n_feat) để feed Autoencoder."""
    feat_cols = ["ret_1", "ret_5", "spread_atr", "vol_z", "body_prop", "wick_extreme"]
    X = df_feat.select(feat_cols).fill_nan(0.0).fill_null(0.0).to_numpy().astype(np.float32)
    N = len(X)
    n_feat = X.shape[1]
    if N < seq_len:
        return np.empty((0, seq_len, n_feat), dtype=np.float32)
    return np.lib.stride_tricks.sliding_window_view(X, (seq_len, n_feat)).reshape(-1, seq_len, n_feat).copy()
