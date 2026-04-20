"""Statistical validation for backtest results.

Includes three independent tools:
  - Monte Carlo permutation test: Is the strategy genuinely better than random?
  - Bootstrap Sharpe CI: How stable is the Sharpe ratio?
  - Walk-forward analysis: Is performance consistent across time periods?
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Union

import numpy as np
import polars as pl

from processing.backtest.dong_co_kiem_thu.mo_hinh import TradeRecord
from utils.helpers import logger


# ─── Monte Carlo Permutation Test ───

def monte_carlo_test(
    trades: List[TradeRecord],
    initial_capital: float,
    n_simulations: int = 1000,
    seed: int = 42,
) -> Dict[str, Any]:
    """Shuffle PnL order to test statistical significance.

    Null hypothesis: the observed Sharpe / Max Drawdown is no better
    than a random reordering of the same trades.
    """
    if len(trades) < 3:
        return {"error": "need at least 3 trades", "p_value_sharpe": 1.0}

    pnls = np.array([t.pnl for t in trades])
    actual = _path_metrics(pnls, initial_capital)

    rng = np.random.default_rng(seed)
    sharpe_count = 0
    dd_count = 0
    sim_sharpes = []

    for _ in range(n_simulations):
        shuffled = rng.permutation(pnls)
        sim = _path_metrics(shuffled, initial_capital)
        sim_sharpes.append(sim["sharpe"])
        if sim["sharpe"] >= actual["sharpe"]:
            sharpe_count += 1
        if sim["max_dd"] >= actual["max_dd"]:  # less negative = "better"
            dd_count += 1

    sim_arr = np.array(sim_sharpes)
    return {
        "actual_sharpe": round(actual["sharpe"], 4),
        "actual_max_dd": round(actual["max_dd"], 4),
        "p_value_sharpe": round(sharpe_count / n_simulations, 4),
        "p_value_max_dd": round(dd_count / n_simulations, 4),
        "simulated_sharpe_mean": round(float(sim_arr.mean()), 4),
        "simulated_sharpe_std": round(float(sim_arr.std()), 4),
        "simulated_sharpe_p5": round(float(np.percentile(sim_arr, 5)), 4),
        "simulated_sharpe_p95": round(float(np.percentile(sim_arr, 95)), 4),
        "n_simulations": n_simulations,
        "n_trades": len(trades),
    }


def _path_metrics(pnls: np.ndarray, initial_capital: float) -> Dict[str, float]:
    """Compute Sharpe and Max Drawdown from a PnL sequence."""
    equity = initial_capital + np.cumsum(pnls)
    returns = np.diff(equity) / equity[:-1] if len(equity) > 1 else np.array([0.0])
    std = returns.std()
    sharpe = float(returns.mean() / (std + 1e-10) * np.sqrt(252))
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / np.where(peak > 0, peak, 1.0)
    max_dd = float(dd.min())
    return {"sharpe": sharpe, "max_dd": max_dd}


# ─── Bootstrap Sharpe Confidence Interval ───

def bootstrap_sharpe_ci(
    equity_curve: pl.Series,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    bars_per_year: int = 252,
    seed: int = 42,
) -> Dict[str, Any]:
    """Resample returns to estimate a confidence interval for the Sharpe ratio."""
    # Compute daily returns using Polars
    returns = (equity_curve / equity_curve.shift(1) - 1).drop_nulls().to_numpy()

    if len(returns) < 5:
        return {"error": "need at least 5 return observations"}

    observed = _sharpe(returns, bars_per_year)

    rng = np.random.default_rng(seed)
    boot_sharpes = []
    for _ in range(n_bootstrap):
        sample = rng.choice(returns, size=len(returns), replace=True)
        boot_sharpes.append(_sharpe(sample, bars_per_year))

    arr = np.array(boot_sharpes)
    alpha = (1 - confidence) / 2
    lower = float(np.percentile(arr, alpha * 100))
    upper = float(np.percentile(arr, (1 - alpha) * 100))
    prob_pos = float(np.mean(arr > 0))

    return {
        "observed_sharpe": round(observed, 4),
        "ci_lower": round(lower, 4),
        "ci_upper": round(upper, 4),
        "median_sharpe": round(float(np.median(arr)), 4),
        "prob_positive": round(prob_pos, 4),
        "confidence": confidence,
        "n_bootstrap": n_bootstrap,
    }


def _sharpe(returns: np.ndarray, bars_per_year: int = 252) -> float:
    """Annualized Sharpe ratio."""
    std = returns.std()
    return float(returns.mean() / (std + 1e-10) * np.sqrt(bars_per_year))


# ─── Walk-Forward Analysis ───

def walk_forward_analysis(
    equity_curve: pl.Series,
    trades: List[TradeRecord],
    n_windows: int = 5,
    bars_per_year: int = 252,
) -> Dict[str, Any]:
    """Split the backtest into sequential windows to check performance consistency."""
    if len(equity_curve) < n_windows * 2:
        return {"error": f"need at least {n_windows * 2} bars for {n_windows} windows"}

    total_len = len(equity_curve)
    window_size = total_len // n_windows
    windows = []
    eq_values = equity_curve.to_numpy()

    for i in range(n_windows):
        start_idx = i * window_size
        end_idx = (i + 1) * window_size if i < n_windows - 1 else total_len
        win_eq = eq_values[start_idx:end_idx]

        # Basic performance stats for this window
        ret = float(win_eq[-1] / win_eq[0] - 1) if win_eq[0] > 0 else 0.0
        win_returns = np.diff(win_eq) / win_eq[:-1]
        sharpe = _sharpe(win_returns, bars_per_year) if len(win_returns) > 1 else 0.0

        peak = np.maximum.accumulate(win_eq)
        dd = (win_eq - peak) / np.where(peak > 0, peak, 1.0)
        max_dd = float(dd.min())

        windows.append({
            "window": i + 1,
            "return": round(ret, 6),
            "sharpe": round(sharpe, 4),
            "max_dd": round(max_dd, 6),
        })

    returns_list = [w["return"] for w in windows]
    sharpes_list = [w["sharpe"] for w in windows]
    profitable_windows = sum(1 for r in returns_list if r > 0)

    return {
        "n_windows": n_windows,
        "windows": windows,
        "profitable_windows": profitable_windows,
        "consistency_rate": round(profitable_windows / n_windows, 4),
        "return_mean": round(float(np.mean(returns_list)), 6),
        "sharpe_mean": round(float(np.mean(sharpes_list)), 4),
    }


# ─── Runner Integration ───

def run_validation(
    config: Dict[str, Any],
    equity_curve: pl.Series,
    trades: List[TradeRecord],
    initial_capital: float,
    bars_per_year: int = 252,
) -> Dict[str, Any]:
    """Run the validation checks configured in the config dict."""
    v_cfg = config.get("validation", {})
    results: Dict[str, Any] = {}

    if "monte_carlo" in v_cfg:
        mc_cfg = v_cfg["monte_carlo"] if isinstance(v_cfg["monte_carlo"], dict) else {}
        results["monte_carlo"] = monte_carlo_test(
            trades, initial_capital,
            n_simulations=mc_cfg.get("n_simulations", 1000),
            seed=mc_cfg.get("seed", 42),
        )

    if "bootstrap" in v_cfg:
        bs_cfg = v_cfg["bootstrap"] if isinstance(v_cfg["bootstrap"], dict) else {}
        results["bootstrap"] = bootstrap_sharpe_ci(
            equity_curve, bars_per_year=bars_per_year,
            n_bootstrap=bs_cfg.get("n_bootstrap", 1000),
            confidence=bs_cfg.get("confidence", 0.95),
            seed=bs_cfg.get("seed", 42),
        )

    if "walk_forward" in v_cfg:
        wf_cfg = v_cfg["walk_forward"] if isinstance(v_cfg["walk_forward"], dict) else {}
        results["walk_forward"] = walk_forward_analysis(
            equity_curve, trades,
            n_windows=wf_cfg.get("n_windows", 5),
            bars_per_year=bars_per_year,
        )

    return results


# ─── Data Loading Utilities (Polars) ───

def _load_equity(run_dir: Path) -> pl.Series:
    """Load equity curve from artifacts/bien_dong_von.csv."""
    path = run_dir / "artifacts" / "bien_dong_von.csv"
    if not path.exists():
        return pl.Series([], name="equity")
    df = pl.read_csv(path)
    return df["equity"]


def _load_trades(run_dir: Path) -> List[TradeRecord]:
    """Load trade history from artifacts/lich_su_giao_dich.csv."""
    path = run_dir / "artifacts" / "lich_su_giao_dich.csv"
    if not path.exists():
        return []

    df = pl.read_csv(path)
    if df.is_empty():
        return []

    # Filter closed-trade rows (pnl not null, includes breakeven)
    exit_rows = df.filter(pl.col("pnl").is_not_null())

    trades = []
    for row in exit_rows.to_dicts():
        trades.append(TradeRecord(
            symbol=str(row.get("code", "")),
            direction=1 if row.get("side") == "sell" else -1,
            entry_price=0.0,
            exit_price=float(row.get("price", 0)),
            entry_time=row.get("timestamp"),
            exit_time=row.get("timestamp"),
            size=float(row.get("qty", 0)),
            leverage=1.0,
            pnl=float(row.get("pnl", 0)),
            pnl_pct=float(row.get("return_pct", 0)),
            exit_reason=str(row.get("reason", "signal")),
            holding_bars=int(row.get("holding_days", 0)),
            commission=0.0,
        ))
    return trades


def main(run_dir: Path) -> Dict[str, Any]:
    """Run all validations against existing run artifacts."""
    import json

    config_path = run_dir / "config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = {}

    initial_capital = config.get("initial_cash", 1_000_000)
    equity = _load_equity(run_dir)
    trades = _load_trades(run_dir)

    results = {
        "monte_carlo": monte_carlo_test(trades, initial_capital),
        "bootstrap": bootstrap_sharpe_ci(equity),
        "walk_forward": walk_forward_analysis(equity, trades),
    }

    # Write results to JSON
    out = run_dir / "artifacts" / "validation.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(json.dumps(results, indent=2, ensure_ascii=False))
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        logger.info("Usage: python -m backtest.validation <run_dir>")
        sys.exit(1)
    main(Path(sys.argv[1]))
