import numpy as np
import polars as pl

SEQ_LEN = 20
N_FEATURES = 5  # body_size, upper_wick, lower_wick, direction, vol_ratio


def build_candle_features(df: pl.DataFrame) -> pl.DataFrame:
    """5 đặc trưng chuẩn hóa mỗi nến (Polars vectorized)."""
    if "volume" not in df.columns:
        df = df.with_columns(pl.lit(1.0).alias("volume"))

    df = df.with_columns([
        (pl.col("high") - pl.col("low")).alias("_rng"),
        pl.max_horizontal("open", "close").alias("_top"),
        pl.min_horizontal("open", "close").alias("_bot"),
    ]).with_columns([
        ((pl.col("_top") - pl.col("_bot")) / (pl.col("_rng") + 1e-9)).alias("body_size"),
        ((pl.col("high") - pl.col("_top")) / (pl.col("_rng") + 1e-9)).alias("upper_wick"),
        ((pl.col("_bot") - pl.col("low")) / (pl.col("_rng") + 1e-9)).alias("lower_wick"),
        pl.when(pl.col("close") > pl.col("open")).then(1.0).otherwise(-1.0).alias("direction"),
        (pl.col("volume") / (pl.col("volume").rolling_mean(20) + 1e-9)).alias("vol_ratio"),
    ])
    return df.select(["timestamp", "body_size", "upper_wick", "lower_wick", "direction", "vol_ratio"])


def label_candles_rule_based(df: pl.DataFrame) -> pl.DataFrame:
    """Gán nhãn mẫu nến bằng quy tắc truyền thống (Polars vectorized) → tạo training data."""
    if "volume" not in df.columns:
        df = df.with_columns(pl.lit(1.0).alias("volume"))

    df = df.with_columns([
        (pl.col("high") - pl.col("low")).alias("_rng"),
        pl.max_horizontal("open", "close").alias("_top"),
        pl.min_horizontal("open", "close").alias("_bot"),
    ]).with_columns([
        ((pl.col("_top") - pl.col("_bot")) / (pl.col("_rng") + 1e-9)).alias("body_prop"),
        ((pl.col("high") - pl.col("_top")) / (pl.col("_rng") + 1e-9)).alias("wick_up"),
        ((pl.col("_bot") - pl.col("low")) / (pl.col("_rng") + 1e-9)).alias("wick_dn"),
        (pl.col("_top") - pl.col("_bot")).alias("body_abs"),
        pl.when(pl.col("close") > pl.col("open")).then(1).otherwise(-1).alias("dir"),
    ])

    prev_body = (pl.col("_top").shift(1) - pl.col("_bot").shift(1)).abs()
    df = df.with_columns(prev_body.fill_null(0.0).alias("prev_body"))

    pattern = (
        pl.when((pl.col("wick_up") + pl.col("wick_dn")) > 0.85).then(9)          # Spike
        .when(
            (pl.col("dir").shift(2) == -1) &
            (pl.col("body_prop").shift(1) < 0.2) &
            (pl.col("dir") == 1) & (pl.col("body_prop") > 0.4)
        ).then(6)                                                                   # Morning Star
        .when(
            (pl.col("dir").shift(2) == 1) &
            (pl.col("body_prop").shift(1) < 0.2) &
            (pl.col("dir") == -1) & (pl.col("body_prop") > 0.4)
        ).then(7)                                                                   # Evening Star
        .when(
            (pl.col("dir") == 1) &
            (pl.col("body_abs") > pl.col("prev_body") * 1.2) &
            (pl.col("close") > pl.col("_top").shift(1)) &
            (pl.col("open") < pl.col("_bot").shift(1))
        ).then(3)                                                                   # Engulfing Bull
        .when(
            (pl.col("dir") == -1) &
            (pl.col("body_abs") > pl.col("prev_body") * 1.2) &
            (pl.col("open") > pl.col("_top").shift(1)) &
            (pl.col("close") < pl.col("_bot").shift(1))
        ).then(4)                                                                   # Engulfing Bear
        .when((pl.col("wick_dn") > 0.5) & (pl.col("wick_up") < 0.2) & (pl.col("body_prop") < 0.4)).then(1)   # Pinbar Bull
        .when((pl.col("wick_up") > 0.5) & (pl.col("wick_dn") < 0.2) & (pl.col("body_prop") < 0.4)).then(2)   # Pinbar Bear
        .when(
            (pl.col("high") < pl.col("high").shift(1)) &
            (pl.col("low") > pl.col("low").shift(1))
        ).then(5)                                                                   # Inside Bar
        .when(pl.col("body_prop") < 0.1).then(8)                                   # Doji
        .otherwise(0)
    )

    return df.with_columns(pattern.cast(pl.Int32).alias("pattern"))


def build_sequences(df_feat: pl.DataFrame, seq_len: int = SEQ_LEN) -> np.ndarray:
    """Xây dựng ma trận chuỗi (N, seq_len, N_FEATURES) cho CNN/LSTM."""
    feat_cols = ["body_size", "upper_wick", "lower_wick", "direction", "vol_ratio"]
    X = df_feat.select(feat_cols).fill_nan(0.0).fill_null(0.0).to_numpy().astype(np.float32)
    N = len(X)
    if N < seq_len:
        return np.empty((0, seq_len, N_FEATURES), dtype=np.float32)
    sequences = np.lib.stride_tricks.sliding_window_view(X, (seq_len, N_FEATURES)).reshape(-1, seq_len, N_FEATURES)
    return sequences.copy()
