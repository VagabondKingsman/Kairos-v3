import pandas as pd
import polars as pl
from utils.helpers.bo_ghi_log_he_thong import logger


def pandas_to_polars(df_pandas: pd.DataFrame) -> pl.DataFrame:
    """Safely convert a Pandas DataFrame to Polars."""
    try:
        if isinstance(df_pandas, pl.DataFrame):
            return df_pandas
        # Reset index if DatetimeIndex to avoid losing the timestamp column
        if isinstance(df_pandas.index, pd.DatetimeIndex):
            df_pandas = df_pandas.reset_index()
        return pl.from_pandas(df_pandas)
    except Exception as e:
        logger.error(f"Error converting Pandas -> Polars: {e}")
        raise


def polars_to_pandas(df_polars: pl.DataFrame) -> pd.DataFrame:
    """Safely convert a Polars DataFrame to Pandas."""
    try:
        if isinstance(df_polars, pd.DataFrame):
            return df_polars
        return df_polars.to_pandas()
    except Exception as e:
        logger.error(f"Error converting Polars -> Pandas: {e}")
        raise


# Backward-compatible aliases (kept for legacy callers)
pandas_sang_polars = pandas_to_polars
polars_sang_pandas = polars_to_pandas
