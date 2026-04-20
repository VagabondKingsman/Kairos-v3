import json
import importlib.util
import sys
from pathlib import Path
from typing import Any, List

import polars as pl
from processing.backtest.bo_thuc_thi_co_so import BaseExecutor, BoThucThiCoSo
from utils.helpers.bo_ghi_log_he_thong import logger
from processing.backtest.dong_co_kiem_thu.trinh_chay import (
    _load_module_from_file, _resolve_run_dir, _fetch_auto, _detect_primary_source,
    _create_market_engine, _AutoLoader
)
from data.loaders.OHLCV.dang_ky_he_thong import get_loader_cls_with_fallback
from processing.backtest.dong_co_kiem_thu.chi_so_do_luong import calc_bars_per_year

class BacktestExecutor(BaseExecutor):
    """Backtest executor — programmatic API wrapper around trinh_chay.py core logic."""

    def load_data(self, source: str, codes: List[str], start_date: str, end_date: str, interval: str) -> dict:
        """Load OHLCV data for backtest. Returns dict {code: pl.DataFrame}."""
        logger.info(f"Loading backtest data from: {source}")

        if source == "auto":
            config_tmp = {"start_date": start_date, "end_date": end_date}
            data_map = _fetch_auto(codes, config_tmp, interval)
        else:
            if source in ("okx", "ccxt"):
                codes = [c.replace("/", "-").upper() for c in codes]

            LoaderCls = get_loader_cls_with_fallback(source)
            loader = LoaderCls()
            data_map = loader.fetch(codes, start_date, end_date, interval=interval)
        return data_map

    def run(self, run_dir: str) -> Any:
        """Execute backtest from a run_dir path. Equivalent to main() in trinh_chay.py."""
        logger.info("Starting BacktestExecutor...")

        run_dir_path = _resolve_run_dir(Path(run_dir))
        config_path = run_dir_path / "config.json"

        if not config_path.exists():
            logger.error(f"config.json not found at {config_path}")
            raise FileNotFoundError("config.json not found")

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        source = config.get("source", "vnstock")
        codes = config.get("codes", [])
        interval = config.get("interval", "1D")

        # 1. Load strategy module
        signal_path = run_dir_path / "code" / "signal_engine.py"
        if not signal_path.exists():
            raise FileNotFoundError(f"Strategy not found at {signal_path}")

        signal_module = _load_module_from_file(signal_path, "signal_engine")
        engine_cls = getattr(signal_module, "SignalEngine", None)
        if engine_cls is None:
            raise ValueError("Class 'SignalEngine' not found in strategy file")

        # 2. Load data
        data_map = self.load_data(
            source=source,
            codes=codes,
            start_date=config.get("start_date", ""),
            end_date=config.get("end_date", ""),
            interval=interval,
        )

        if not data_map:
            raise ValueError("No data loaded.")

        # 3. Initialize engine
        signal_engine = engine_cls()
        effective_source = _detect_primary_source(codes, source)
        bars_per_year = calc_bars_per_year(interval, effective_source)

        if source == "auto":
            loader = _AutoLoader(data_map)
        else:
            LoaderCls = get_loader_cls_with_fallback(source)
            loader = LoaderCls()

        market_engine = _create_market_engine(effective_source, config, codes)

        logger.info(f"[BacktestExecutor] Running backtest: {effective_source.upper()} | Interval: {interval}")

        result = market_engine.run_backtest(config, loader, signal_engine, run_dir_path, bars_per_year=bars_per_year)

        logger.info("Backtest complete.")
        return result


# Backward-compatible aliases
BoThucThiKiemThu = BacktestExecutor
