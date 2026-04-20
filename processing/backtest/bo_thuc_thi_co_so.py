from abc import ABC, abstractmethod
from typing import Any
import polars as pl
from utils.helpers.bo_chuyen_doi_du_lieu import polars_to_pandas


class BaseExecutor(ABC):
    """Common interface for all research executors (backtest, paper, live)."""

    def __init__(self, config: dict = None):
        self.config = config or {}

    @abstractmethod
    def load_data(self, *args, **kwargs) -> pl.DataFrame:
        """Load OHLCV data for the execution run."""
        pass

    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        """Main entry point to start the execution."""
        pass

    def to_pandas(self, df: pl.DataFrame) -> "pd.DataFrame":
        """Convert Polars DataFrame to Pandas (for legacy integrations)."""
        return polars_to_pandas(df)


# Backward-compatible alias
BoThucThiCoSo = BaseExecutor
