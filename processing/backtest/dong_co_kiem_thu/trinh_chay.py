"""
Backtest Runner: Reads config.json, selects data loader,
loads strategy (signal_engine) and activates the simulation engine.

Supports:
  - source="auto": Automatically routes symbols to the appropriate loader based on format.
  - interval: Candle timeframe (1m/5m/15m/30m/1H/4H/1D).
  - engine: Select engine type (daily/options).

Usage: ``python -m backtest.runner <run_dir>``
"""

import importlib.util
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List

# Load config from central system
try:
    from utils.config import cfg
except ImportError:
    pass


# Add project root to PYTHONPATH for internal module resolution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

try:
    from data.loaders.OHLCV.dang_ky_he_thong import (
        LOADER_REGISTRY,
        get_loader_cls_with_fallback,
        resolve_loader,
    )
    from data.loaders.OHLCV.co_so import NoAvailableSourceError
except ImportError as e:
    logger.error(f"System module import error: {e}")
    sys.exit(1)

from utils.helpers import logger

def _load_module_from_file(file_path: Path, module_name: str):
    """Dynamically load a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# --- Market detection (based on symbol format) ---

_MARKET_PATTERNS = [
    # Vietnamese equities: 3 uppercase letters (e.g. FPT, VNM, SSI)
    (re.compile(r"^[A-Z]{3}$", re.I), "vn_equity"),
    # US equities: AAPL.US, TSLA.US
    (re.compile(r"^[A-Z]+\.US$", re.I), "us_equity"),
    # Hong Kong equities: 00700.HK, 9988.HK
    (re.compile(r"^\d{3,5}\.HK$", re.I), "hk_equity"),
    # Crypto: BTC-USDT, ETH-USDT or BTC/USDT
    (re.compile(r"^[A-Z0-9]+[-/]USDT$", re.I), "crypto"),
    # Forex: EUR/USD or EURUSD.FX
    (re.compile(r"^[A-Z]{3}/[A-Z]{3}$"), "forex"),
    (re.compile(r"^[A-Z]{6}\.FX$"), "forex"),
    # Global futures
    (re.compile(r"^[A-Z]{2,4}[FGHJKMNQUVXZ]\d{1,2}$", re.I), "futures"),
]

# Market → default data source mapping
_MARKET_TO_SOURCE = {
    "vn_equity": "vnstock",
    "us_equity": "yfinance",
    "hk_equity": "yfinance",
    "crypto": "okx",
    "forex": "yfinance",
}

def _detect_market(code: str) -> str:
    """Infer market type from symbol format."""
    for pattern, market in _MARKET_PATTERNS:
        if pattern.match(code):
            return market
    return "vn_equity"  # Default to Vietnam if no match

def _detect_primary_source(codes: List[str], source: str) -> str:
    """Determine the primary data source for annualization metrics."""
    if source != "auto":
        return source
    if not codes:
        return "vnstock"

    # Count which source appears most in the symbol list
    counts = {}
    for c in codes:
        src = _MARKET_TO_SOURCE.get(_detect_market(c), "vnstock")
        counts[src] = counts.get(src, 0) + 1
    return max(counts, key=counts.get)

# --- Main controller ---

def _resolve_run_dir(run_dir: Path) -> Path:
    """Resolve run_dir: if short run_id → map to a11 backtest_runs."""
    if run_dir.is_absolute() and run_dir.exists():
        return run_dir
    # Try to resolve to data.store/backtest_runs/
    try:
        from data.store import A11
        resolved = A11.backtest_run(run_dir.name)
        return resolved
    except ImportError:
        pass
    return run_dir


def main(run_dir: Path) -> None:
    """Load config, fetch data, and launch the appropriate backtest engine.

    Output (metrics.json, equity.csv, trades.csv) is saved at run_dir.
    If run_dir is just a run_id, auto-resolves to:
        data.store/backtest_runs/<run_id>/
    """
    run_dir = _resolve_run_dir(run_dir)
    config_path = run_dir / "config.json"
    if not config_path.exists():
        logger.error(json.dumps({"error": "config.json not found"}))
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    source = config.get("source", "vnstock")
    codes = config.get("codes", [])
    interval = config.get("interval", "1D")

    # 1. Load user strategy module (Signal Engine)
    signal_path = run_dir / "code" / "signal_engine.py"
    if not signal_path.exists():
        logger.error(json.dumps({"error": "Strategy not found at code/signal_engine.py"}))
        sys.exit(1)

    signal_module = _load_module_from_file(signal_path, "signal_engine")
    engine_cls = getattr(signal_module, "SignalEngine", None)
    if engine_cls is None:
        logger.error(json.dumps({"error": "Class 'SignalEngine' not found in strategy file"}))
        sys.exit(1)

    # 2. Load data (auto or single source)
    if source == "auto":
        data_map = _fetch_auto(codes, config, interval)
    else:
        # Normalize symbols (e.g. crypto needs dashes)
        if source in ("okx", "ccxt"):
            codes = [c.replace("/", "-").upper() for c in codes]

        LoaderCls = get_loader_cls_with_fallback(source)
        loader = LoaderCls()
        data_map = loader.fetch(
            codes,
            config.get("start_date", ""),
            config.get("end_date", ""),
            interval=interval,
        )

    if not data_map:
        logger.error(json.dumps({"error": "No data loaded. Check symbol or connection."}))
        sys.exit(1)

    # 3. Initialize engine and strategy
    signal_engine = engine_cls()
    effective_source = _detect_primary_source(codes, source)

    # Calculate bars per year for Sharpe/Annual Return
    from processing.backtest.dong_co_kiem_thu.chi_so_do_luong import calc_bars_per_year
    bars_per_year = calc_bars_per_year(interval, effective_source)

    # For auto mode, wrap pre-loaded data in a dummy loader
    if source == "auto":
        loader = _AutoLoader(data_map)

    market_engine = _create_market_engine(effective_source, config, codes)

    logger.success(f"[START] Backtest: {effective_source.upper()} | Interval: {interval}")
    market_engine.run_backtest(config, loader, signal_engine, run_dir, bars_per_year=bars_per_year)


def _create_market_engine(source: str, config: dict, codes: List[str]):
    """Instantiate the engine appropriate for the target market."""
    markets = {_detect_market(c) for c in codes} if codes else {"vn_equity"}

    if "vn_equity" in markets:
        from processing.backtest.dong_co_kiem_thu.bo_xu_ly.co_phieu_viet_nam import VietnamEquityEngine
        return VietnamEquityEngine(config)

    if "crypto" in markets:
        from processing.backtest.dong_co_kiem_thu.bo_xu_ly.tien_dien_tu import CryptoEngine
        return CryptoEngine(config)

    if "forex" in markets:
        from processing.backtest.dong_co_kiem_thu.bo_xu_ly.ngoai_hoi import ForexEngine
        return ForexEngine(config)

    if "us_equity" in markets or "hk_equity" in markets:
        from processing.backtest.dong_co_kiem_thu.bo_xu_ly.co_phieu_toan_cau import GlobalEquityEngine
        submarket = "hk" if any(c.upper().endswith(".HK") for c in codes) else "us"
        return GlobalEquityEngine(config, market=submarket)

    # Default fallback
    from processing.backtest.dong_co_kiem_thu.bo_xu_ly.co_phieu_viet_nam import VietnamEquityEngine
    return VietnamEquityEngine(config)


def _fetch_auto(codes: List[str], config: dict, interval: str = "1D") -> dict:
    """Auto mode: group symbols by market and call the matching loader."""
    merged = {}
    groups: Dict[str, List[str]] = {}

    for c in codes:
        m = _detect_market(c)
        groups.setdefault(m, []).append(c)

    for market, market_codes in groups.items():
        try:
            loader = resolve_loader(market)
            res = loader.fetch(
                market_codes,
                config.get("start_date", ""),
                config.get("end_date", ""),
                interval=interval,
            )
            merged.update(res)
        except Exception as e:
            logger.error(f"Auto-fetch error for market group '{market}': {e}")

    return merged


class _AutoLoader:
    """Dummy loader that returns pre-fetched Polars data."""
    def __init__(self, data_map: dict):
        self._data = data_map

    def fetch(self, codes, *args, **kwargs):
        return {c: df for c, df in self._data.items() if c in codes}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.info("Usage: python -m backtest.runner <run_dir>")
        sys.exit(1)
    main(Path(sys.argv[1]))