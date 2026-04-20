import pandas as pd
from utils.helpers.bo_chuyen_doi_du_lieu import pandas_to_polars, polars_to_pandas
from utils.helpers.bo_ghi_log_he_thong import logger


def run_legacy_strategy(strategy_class, df_pandas: pd.DataFrame, *args, **kwargs) -> pd.Series:
    """Run a legacy v2.0 Pandas-based strategy within the Polars architecture.

    Converts input to Polars, runs the strategy, then converts result back to Pandas.
    """
    logger.debug(f"Wrapping legacy strategy: {strategy_class.__name__}")

    df_pl = pandas_to_polars(df_pandas)

    strategy = strategy_class()

    if hasattr(strategy, 'run'):
        result_pl = strategy.run(df_pl, *args, **kwargs)
    elif hasattr(strategy, 'chay'):
        result_pl = strategy.chay(df_pl, *args, **kwargs)
    else:
        raise NotImplementedError("Legacy strategy must implement .run() or .chay()")

    return polars_to_pandas(result_pl)


# Backward-compatible alias
chay_chien_luoc_cu = run_legacy_strategy
