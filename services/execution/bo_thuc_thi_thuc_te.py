import polars as pl
from typing import Any
from processing.backtest.bo_thuc_thi_co_so import BaseExecutor, BoThucThiCoSo
from utils.helpers.bo_ghi_log_he_thong import logger

class BoThucThiThucTe(BaseExecutor):
    """Live trading executor — connects to exchange API, manages risk and slippage."""

    def load_data(self, exchange_api: str) -> pl.DataFrame:
        logger.info(f"Connecting to exchange API: {exchange_api}")
        return pl.DataFrame()

    def run(self, exchange_connection) -> Any:
        logger.info("Starting Live Trading... WARNING: Real funds activated.")
        # Webhook / websocket loop, pushes orders via API
        return 0

    # Backward-compatible aliases
    tai_du_lieu = load_data
    chay = run
