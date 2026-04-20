"""Foundation backtest engine with bar-by-bar execution loop.

All market engines inherit from BaseEngine and override market rule methods.
run_backtest() handles the full pipeline: load data → generate signals →
pre-compute target weights (with optimizer) → execute bar-by-bar with
market rule checks → compute metrics → write artifacts.
"""

from __future__ import annotations

import importlib
import json
import sys
from abc import ABC, abstractmethod
from utils.helpers import logger
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timedelta

import numpy as np
import polars as pl

from processing.backtest.dong_co_kiem_thu.chi_so_do_luong import (
    by_exit_reason_stats,
    by_symbol_stats,
    calc_metrics,
)
from processing.backtest.dong_co_kiem_thu.mo_hinh import EquitySnapshot, Position, TradeRecord


# ─── Căn chỉnh tín hiệu (tái sử dụng từ logic daily_portfolio) ───


def _align(
    data_map: Dict[str, pl.DataFrame],
    signal_map: Dict[str, pl.Series],
    codes: List[str],
    optimizer: Optional[Callable] = None,
) -> tuple:
    """Build aligned date index, close price matrix, target position matrix, and returns matrix.

    Signals are shifted by 1 bar (next-bar-open semantics) then normalized
    so ``sum(abs(weights)) <= 1.0``.

    Args:
        data_map: symbol → OHLCV DataFrame.
        signal_map: symbol → signal Series.
        codes: List of valid instrument codes.
        optimizer: Optional weight optimizer ``(ret, pos, dates) -> pos``.

    Returns:
        (dates, close_df, positions_df, returns_df) — all as Polars DataFrames/Series.
    """
    # Collect all dates from every symbol
    all_dates: set = set()
    for c in codes:
        all_dates.update(data_map[c]["timestamp"].to_list())
    dates = sorted(all_dates)

    # Sync dtype to avoid "datatypes of join keys don't match" (us vs ms)
    ts_dtype = data_map[codes[0]]["timestamp"].dtype
    dates_df = pl.Series("timestamp", dates, dtype=ts_dtype).to_frame()

    close_df = pl.DataFrame({
        "timestamp": dates,
        **{c: dates_df
             .join(data_map[c].select(["timestamp", "close"]).rename({"close": c}),
                   on="timestamp", how="left")[c]
             .fill_null(strategy="forward")
             .fill_null(strategy="backward")
           for c in codes},
    })

    # Build position matrix — shift signals by 1 bar
    pos_data_series = {"timestamp": dates_df["timestamp"]}
    for c in codes:
        # signal_map[c] is a pl.Series with same length as data_map[c]
        sig_map_df = pl.DataFrame({
            "timestamp": data_map[c]["timestamp"],
            c: signal_map[c]
        }).with_columns(pl.col("timestamp").cast(ts_dtype))
        
        sig_df = dates_df.join(sig_map_df, on="timestamp", how="left")
        raw = (
            sig_df[c]
            .fill_null(0.0)
            .clip(-1.0, 1.0)
        )
        # Shift by 1 step (next-bar semantics)
        shifted = raw.shift(1).fill_null(0.0)
        pos_data_series[c] = shifted

    pos_df = pl.DataFrame(pos_data_series)

    # Compute percent returns from close prices
    ret_data: Dict[str, List[float]] = {"timestamp": dates}
    for c in codes:
        close_col = close_df[c].to_list()
        pct = [0.0] + [
            (close_col[i] - close_col[i - 1]) / close_col[i - 1]
            if close_col[i - 1] != 0 else 0.0
            for i in range(1, len(close_col))
        ]
        ret_data[c] = pct

    ret_df = pl.DataFrame(ret_data)

    # Apply optimizer if provided
    if optimizer is not None:
        pos_df = optimizer(ret_df, pos_df, dates)

    code_cols = [c for c in codes]

    # 1. Sum absolute weights per row
    abs_sum_expr = pl.sum_horizontal([pl.col(c).abs() for c in code_cols])

    # 2. Scale factor: ensure total weight sums to at most 1.0
    scale_expr = pl.max_horizontal(abs_sum_expr, pl.lit(1.0))

    # 3. Normalize weights by scale factor
    pos_df = pos_df.with_columns([
        (pl.col(c) / scale_expr).alias(c) for c in code_cols
    ])
    
    return dates, close_df, pos_df, ret_df


def _load_optimizer(config: Dict[str, Any]) -> Optional[Callable]:
    """Dynamically load weight optimizer from config.

    Args:
        config: Backtest configuration dict.

    Returns:
        Optimizer callable, or None if not configured or load fails.
    """
    opt_name = config.get("bo_toi_uu")
    if not opt_name:
        return None
    opt_params = config.get("bo_toi_uu_params") or {}
    try:
        mod = importlib.import_module(f"dong_co_kiem_thu.bo_toi_uu.{opt_name}")
        return lambda ret, pos, dates: mod.optimize(ret, pos, dates, **opt_params)
    except (ImportError, AttributeError) as e:
        logger.warning(f"Could not load optimizer '{opt_name}': {e}, using equal weight")
        return None


# ─── Engine Nền Tảng ───


class BaseEngine(ABC):
    """Abstract base for all market engines.

    Subclasses override market rule methods:
      - can_execute: check if a trade is allowed under market rules
      - round_size: round lot size to market conventions
      - calc_commission: commission fee structure
      - apply_slippage: slippage model
      - on_bar: per-bar hook (funding fees, liquidation checks, etc.)
    """

    def __init__(self, config: dict):
        self.config = config
        self.initial_capital: float = config.get("initial_cash", 1_000_000)  # Starting capital
        self.default_leverage: float = config.get("leverage", 1.0)            # Default leverage
        self.capital: float = self.initial_capital                             # Free cash
        self.positions: Dict[str, Position] = {}                               # Open positions
        self.trades: List[TradeRecord] = []                                    # Closed trade history
        self.equity_snapshots: List[EquitySnapshot] = []                       # Total equity history
        self._bar_idx: int = 0                                                 # Current bar index
        self._active_symbol: str = ""  # Symbol being processed (used by subclasses)

    # ── Market rule interface (subclasses must implement) ──

    @abstractmethod
    def can_execute(self, symbol: str, direction: int, bar: dict) -> bool:
        """Check whether market rules allow this trade.

        Args:
            symbol: Instrument code.
            direction: 1 (buy/long), -1 (sell/short), 0 (close position).
            bar: Current bar data (OHLCV + extras).

        Returns:
            True if execution is permitted.
        """

    @abstractmethod
    def round_size(self, raw_size: float, price: float) -> float:
        """Round position size to market lot conventions.

        Args:
            raw_size: Desired size (unrounded).
            price: Current price.

        Returns:
            Rounded size.
        """

    @abstractmethod
    def calc_commission(self, size: float, price: float, direction: int, is_open: bool) -> float:
        """Calculate commission for a trade.

        Args:
            size: Trade volume.
            price: Execution price.
            direction: 1 or -1.
            is_open: True when opening, False when closing.

        Returns:
            Commission amount.
        """

    @abstractmethod
    def apply_slippage(self, price: float, direction: int) -> float:
        """Apply slippage to execution price.

        Args:
            price: Original price before slippage.
            direction: 1 (buy / cover short) or -1 (sell / short).

        Returns:
            Price after slippage.
        """

    def on_bar(self, symbol: str, bar: dict, timestamp: Any) -> None:
        """Per-bar market rule hook (funding fees, liquidation checks, etc.).

        Default: no-op. Override in subclass if needed.
        """

    # ── PnL / margin hooks ──
    # Override in FuturesBaseEngine to incorporate contract multiplier.

    def _calc_pnl(
        self, symbol: str, direction: int, size: float,
        entry_price: float, exit_price: float,
    ) -> float:
        """Calculate realized PnL when closing a position."""
        return direction * size * (exit_price - entry_price)

    def _calc_margin(
        self, symbol: str, size: float, price: float, leverage: float,
    ) -> float:
        """Calculate margin (collateral) required for a position."""
        return size * price / leverage

    def _calc_raw_size(
        self, symbol: str, target_notional: float, price: float,
    ) -> float:
        """Convert target notional value to number of units/contracts."""
        return target_notional / price

    # ── Main entry point ──

    def run_backtest(
        self,
        config: Dict[str, Any],
        loader: Any,
        signal_engine: Any,
        run_dir: Path,
        bars_per_year: int = 252,
    ) -> Dict[str, Any]:
        """Full backtest pipeline with warm-up period support."""
        codes = config.get("codes", [])
        interval = config.get("interval", "1D")
        extra_fields = config.get("extra_fields") or None

        start_date = config.get("start_date", "")
        end_date = config.get("end_date", "")

        # ---------------------------------------------------------
        # STEP 1: ROLL BACK START DATE TO LOAD WARM-UP DATA
        # ---------------------------------------------------------
        # Default: fetch 30 extra days before start_date for RSI, MACD, SMA, etc.
        lookback_days = config.get("lookback_days", 30)
        fetch_start_date = start_date

        if start_date:
            try:
                dt_obj = datetime.strptime(start_date, "%Y-%m-%d")
                dt_obj -= timedelta(days=lookback_days)
                fetch_start_date = dt_obj.strftime("%Y-%m-%d")
            except Exception as e:
                logger.warning(f"Failed to parse start_date: {e}")

        # 1. Load market data (using the rolled-back fetch_start_date)
        data_map = loader.fetch(
            codes,
            fetch_start_date,  # <-- load from earlier date for warm-up
            end_date,
            fields=extra_fields,
            interval=interval,
        )
        if not data_map:
            logger.error(json.dumps({"error": "No data loaded"}))
            sys.exit(1)

        # 2. Generate trading signals (computed on the full warm-up dataset)
        signal_map = signal_engine.generate(data_map)
        valid_codes = sorted(c for c in signal_map if c in data_map)
        if not valid_codes:
            logger.error(json.dumps({"error": "No valid signals generated"}))
            sys.exit(1)

        # 3. Pre-compute target weights
        opt_fn = _load_optimizer(config)
        dates, close_df, target_pos, ret_df = _align(
            data_map, signal_map, valid_codes, optimizer=opt_fn,
        )

        # ---------------------------------------------------------
        # STEP 2: TRIM WARM-UP DATA — ONLY TRADE FROM START_DATE
        # ---------------------------------------------------------
        if start_date:
            start_idx = 0
            for i, d in enumerate(dates):
                # Safe cast to yyyy-mm-dd string for comparison
                d_str = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
                if d_str >= start_date:
                    start_idx = i
                    break

            # Slice date list and Polars DataFrames (very fast)
            if start_idx > 0 and start_idx < len(dates):
                dates = dates[start_idx:]
                close_df = close_df.slice(start_idx)
                target_pos = target_pos.slice(start_idx)
                ret_df = ret_df.slice(start_idx)

        # 4. Execute bar-by-bar
        self._execute_bars(dates, data_map, close_df, target_pos, valid_codes)

        # ---------------------------------------------------------
        # 5. Build output equity curve (Loại bỏ hoàn toàn Pandas)
        # ---------------------------------------------------------
        equity_vals = [s.equity for s in self.equity_snapshots]

        # Benchmark return: average return across all symbols
        if len(valid_codes) > 0:
            ret_matrix = [ret_df[c].to_list() for c in valid_codes]
            bench_ret_list = [sum(row) / len(row) for row in zip(*ret_matrix)]
        else:
            bench_ret_list = [0.0] * len(dates)

        cum = 1.0
        bench_equity_list = []
        for r in bench_ret_list:
            cum *= (1 + r)
            bench_equity_list.append(self.initial_capital * cum)

        # ---------------------------------------------------------
        # 6. Compute performance metrics (Dùng Numpy thuần túy)
        # ---------------------------------------------------------
        m = calc_metrics(
            equity_curve=np.array(equity_vals), 
            trades=self.trades, 
            initial_cash=self.initial_capital, 
            bars_per_year=bars_per_year, 
            bench_ret=np.array(bench_ret_list)
        )
        m["by_symbol"] = by_symbol_stats(self.trades)
        m["by_exit_reason"] = by_exit_reason_stats(self.trades)

        # 7. Validation (optional)
        if config.get("validation"):
            from ..kiem_chung import run_validation
            # Tạm thời ép thành pl.Series để kiem_chung.py xử lý trơn tru
            v_results = run_validation(
                config, pl.Series("equity", equity_vals), self.trades, self.initial_capital, bars_per_year,
            )
            m["validation"] = v_results
            v_path = run_dir / "artifacts" / "validation.json"
            v_path.write_text(json.dumps(v_results, indent=2, ensure_ascii=False), encoding="utf-8")

        # 8. Write artifacts (Truyền List thẳng vào, không dùng Pandas)
        self._write_artifacts(
            run_dir, data_map, dates, equity_vals, bench_equity_list, bench_ret_list,
            target_pos, m, valid_codes,
        )
        with open(run_dir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, indent=4)

        logger.info(json.dumps({k: v for k, v in m.items() if not isinstance(v, dict)}, indent=2))
        return m

    # ── Execution loop ──

    def _execute_bars(
        self,
        dates: List[Any],
        data_map: Dict[str, pl.DataFrame],
        close_df: pl.DataFrame,
        target_pos: pl.DataFrame,
        codes: List[str],
    ) -> None:
        """Bar-by-bar execution loop with market rule checks."""
        # Fast lookup: symbol → set of timestamps with data
        date_sets: Dict[str, set] = {
            c: set(data_map[c]["timestamp"].to_list()) for c in codes
        }
        # close_df → lookup dict: (timestamp, symbol) → price
        close_lookup: Dict[tuple, float] = {}
        for c in codes:
            for ts, price in zip(close_df["timestamp"].to_list(), close_df[c].to_list()):
                if price is not None:
                    close_lookup[(ts, c)] = float(price)

        # Bar data lookup: (symbol, timestamp) → row dict
        bar_lookup: Dict[tuple, dict] = {}
        for c in codes:
            df_c = data_map[c]
            for row in df_c.iter_rows(named=True):
                bar_lookup[(c, row["timestamp"])] = row

        # Target weight lookup: (timestamp, symbol) → float
        target_lookup: Dict[tuple, float] = {}
        ts_list = target_pos["timestamp"].to_list()
        for c in codes:
            col = target_pos[c].to_list()
            for ts, w in zip(ts_list, col):
                target_lookup[(ts, c)] = float(w) if w is not None else 0.0

        for i, ts in enumerate(dates):
            self._bar_idx = i

            # a. Per-bar hook (funding fees, liquidation checks)
            for c in codes:
                if ts in date_sets[c]:
                    bar = bar_lookup.get((c, ts), {})
                    self.on_bar(c, bar, ts)

            # b. Rebalance each symbol toward its target weight
            equity = self._calc_equity(close_lookup, ts)
            for c in codes:
                target_w = target_lookup.get((ts, c), 0.0)
                self._rebalance(c, target_w, data_map.get(c), bar_lookup, ts, equity)

            # c. Record equity snapshot
            snap_equity = self._calc_equity(close_lookup, ts)
            total_unrealized = 0.0
            for p in self.positions.values():
                cp = close_lookup.get((ts, p.symbol), p.entry_price)
                total_unrealized += self._calc_pnl(
                    p.symbol, p.direction, p.size, p.entry_price, cp,
                )
            self.equity_snapshots.append(EquitySnapshot(
                timestamp=ts,
                capital=self.capital,
                unrealized=total_unrealized,
                equity=snap_equity,
                positions=len(self.positions),
            ))

        # d. Force-close all open positions at end of backtest
        if len(dates) > 0:
            last_ts = dates[-1]
            for c in list(self.positions.keys()):
                price = close_lookup.get((last_ts, c), self.positions[c].entry_price)
                self._close_position(c, price, last_ts, "end_of_backtest")

    def _calc_equity(
        self,
        close_lookup: Dict[tuple, float],
        ts: Any,
    ) -> float:
        """Total equity = free cash + sum(margin + unrealized PnL) for each open position."""
        equity = self.capital
        for sym, pos in self.positions.items():
            cp = close_lookup.get((ts, sym), pos.entry_price)
            margin = self._calc_margin(sym, pos.size, pos.entry_price, pos.leverage)
            unrealized = self._calc_pnl(sym, pos.direction, pos.size, pos.entry_price, cp)
            equity += margin + unrealized
        return equity

    def _rebalance(
        self,
        symbol: str,
        target_weight: float,
        df: Optional[pl.DataFrame],
        bar_lookup: Dict[tuple, dict],
        ts: Any,
        equity: float,
    ) -> None:
        """Adjust *symbol* position toward *target_weight*."""
        self._active_symbol = symbol
        target_dir = 1 if target_weight > 1e-9 else (-1 if target_weight < -1e-9 else 0)
        current_pos = self.positions.get(symbol)

        # Nothing to do
        if current_pos is None and target_dir == 0:
            return
        if df is None:
            return

        bar = bar_lookup.get((symbol, ts))
        if bar is None:
            return

        # Close position if target is flat or direction reversed
        if current_pos is not None:
            need_close = target_dir == 0 or target_dir != current_pos.direction
            if need_close:
                if self.can_execute(symbol, 0, bar):
                    open_price = float(bar.get("open", bar.get("close", 0)))
                    price = self.apply_slippage(open_price, -current_pos.direction)
                    self._close_position(symbol, price, ts, "signal")
                else:
                    return  # Blocked (e.g. stock at floor price, cannot sell)

        # Open new position if target is non-zero and no position exists
        if target_dir != 0 and symbol not in self.positions:
            if not self.can_execute(symbol, target_dir, bar):
                return  # Blocked (e.g. stock not shortable)

            open_price = float(bar.get("open", bar.get("close", 0)))
            if open_price <= 0:
                return

            slipped = self.apply_slippage(open_price, target_dir)
            leverage = self.default_leverage
            target_notional = abs(target_weight) * equity * leverage
            raw_size = self._calc_raw_size(symbol, target_notional, slipped)
            size = self.round_size(raw_size, slipped)
            if size <= 0:
                return

            margin = self._calc_margin(symbol, size, slipped, leverage)
            comm = self.calc_commission(size, slipped, target_dir, is_open=True)

            # Insufficient capital — scale down size
            if margin + comm > self.capital:
                available = self.capital - comm
                if available <= 0:
                    return
                size = self.round_size(
                    self._calc_raw_size(symbol, available * leverage, slipped), slipped,
                )
                if size <= 0:
                    return
                margin = self._calc_margin(symbol, size, slipped, leverage)
                comm = self.calc_commission(size, slipped, target_dir, is_open=True)

            # Deduct margin + commission from cash
            self.capital -= (margin + comm)
            self.positions[symbol] = Position(
                symbol=symbol,
                direction=target_dir,
                entry_price=slipped,
                entry_time=ts,
                size=size,
                leverage=leverage,
                entry_bar_idx=self._bar_idx,
                entry_commission=comm,
            )

    def _close_position(
        self,
        symbol: str,
        exit_price: float,
        exit_time: Any,
        reason: str,
    ) -> None:
        """Close position, record trade history, and return capital."""
        self._active_symbol = symbol
        pos = self.positions.pop(symbol, None)
        if pos is None:
            return

        pnl = self._calc_pnl(symbol, pos.direction, pos.size, pos.entry_price, exit_price)
        margin = self._calc_margin(symbol, pos.size, pos.entry_price, pos.leverage)
        pnl_pct = pnl / margin * 100 if margin > 1e-9 else 0.0
        exit_comm = self.calc_commission(pos.size, exit_price, pos.direction, is_open=False)

        # Return margin + PnL to cash, deduct exit commission
        self.capital += margin + pnl - exit_comm

        holding_bars = max(self._bar_idx - pos.entry_bar_idx, 0)

        self.trades.append(TradeRecord(
            symbol=symbol,
            direction=pos.direction,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            entry_time=pos.entry_time,
            exit_time=exit_time,
            size=pos.size,
            leverage=pos.leverage,
            pnl=pnl,
            pnl_pct=pnl_pct,
            exit_reason=reason,
            holding_bars=holding_bars,
            commission=pos.entry_commission + exit_comm,
        ))

    # ── Write Artifacts ──

    def _write_artifacts(
        self,
        run_dir: Path,
        data_map: Dict[str, pl.DataFrame],
        dates: List[Any],
        equity_vals: List[float],       # <-- SỬA: Nhận thẳng List
        bench_equity_list: List[float], # <-- SỬA: Nhận thẳng List
        bench_ret_list: List[float],    # <-- SỬA: Nhận thẳng List
        target_pos: pl.DataFrame,
        metrics: dict,
        codes: List[str],
    ) -> None:
        """Write CSV artifacts compatible with the daily_portfolio format."""
        out = run_dir / "artifacts"
        out.mkdir(parents=True, exist_ok=True)

        # Per-symbol OHLCV
        for code, df in data_map.items():
            df.write_csv(str(out / f"ohlcv_{code}.csv"))

        # Equity curve (Không cần trích xuất .values.tolist() từ Pandas nữa)
        port_ret = [0.0] + [
            (equity_vals[i] - equity_vals[i - 1]) / equity_vals[i - 1]
            if equity_vals[i - 1] != 0 else 0.0
            for i in range(1, len(equity_vals))
        ]
        
        # Drawdown: (equity - peak) / peak
        peak = equity_vals[0] if equity_vals else 1.0
        drawdowns = []
        for v in equity_vals:
            if v > peak:
                peak = v
            drawdowns.append((v - peak) / peak if peak != 0 else 0.0)

        # Tính active_return (Đã có sẵn dạng List cùng độ dài)
        active_ret = [pr - br for pr, br in zip(port_ret, bench_ret_list)]

        eq_df = pl.DataFrame({
            "timestamp": [str(d) for d in dates],
            "ret": port_ret,
            "equity": equity_vals,
            "drawdown": drawdowns,
            "benchmark_equity": bench_equity_list,
            "active_ret": active_ret,
        })
        eq_df.write_csv(str(out / "equity.csv"))
        
        # Performance metrics (scalar values only, nested dicts excluded)
        flat_metrics = {k: v for k, v in metrics.items() if not isinstance(v, dict)}
        pl.DataFrame([flat_metrics]).write_csv(str(out / "metrics.csv"))

    # ── Utilities ──

    @staticmethod
    def _safe_price(
        close_lookup: Dict[tuple, float],
        ts: Any,
        symbol: str,
        fallback: float,
    ) -> float:
        """Return close price from lookup table, or fallback if missing."""
        val = close_lookup.get((ts, symbol))
        return float(val) if val is not None else fallback