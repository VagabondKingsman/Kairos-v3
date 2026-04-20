"""
Bộ tính toán chỉ số hiệu suất (Metrics): Trích xuất từ hệ thống KAIROS để tái sử dụng.

Cung cấp các công cụ hỗ trợ quy đổi năm (annualisation), thống kê giao dịch 
và tính toán toàn bộ các chỉ số tài chính (Sharpe, Sortino, Drawdown...).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

import numpy as np
import polars as pl

from processing.backtest.dong_co_kiem_thu.mo_hinh import TradeRecord

# ─── Cấu hình quy đổi theo năm (Annualisation) ───

# Số ngày giao dịch mỗi năm theo từng nguồn dữ liệu
_TRADING_DAYS = {
    "vnstock": 250,   # Thị trường Việt Nam
    "yfinance": 252,  # Thị trường Mỹ/Quốc tế
    "okx": 365,       # Tiền điện tử (24/7)
    "ccxt": 365       # Tiền điện tử (24/7)
}

# Số nến trong một ngày giao dịch theo từng khung thời gian
_BARS_PER_DAY = {
    "1m":  {"vnstock": 240, "okx": 1440, "yfinance": 390, "ccxt": 1440},
    "5m":  {"vnstock": 48,  "okx": 288,  "yfinance": 78,  "ccxt": 288},
    "15m": {"vnstock": 16,  "okx": 96,   "yfinance": 26,  "ccxt": 96},
    "30m": {"vnstock": 8,   "okx": 48,   "yfinance": 13,  "ccxt": 48},
    "1H":  {"vnstock": 4,   "okx": 24,   "yfinance": 7,   "ccxt": 24},
    "4H":  {"vnstock": 1,   "okx": 6,    "yfinance": 2,   "ccxt": 6},
    "1D":  {"vnstock": 1,   "okx": 1,    "yfinance": 1,   "ccxt": 1},
}


def calc_bars_per_year(interval: str = "1D", source: str = "vnstock") -> int:
    """Tính toán tổng số nến trong một năm để quy đổi lãi suất."""
    trading_days = _TRADING_DAYS.get(source, 250)
    bars_per_day = _BARS_PER_DAY.get(interval, {}).get(source, 1)
    return trading_days * bars_per_day


def win_rate_and_stats(trades: List[TradeRecord]) -> Dict[str, float]:
    """Tính toán tỷ lệ thắng và các thống kê P&L từ lịch sử lệnh đã đóng.
    
    Giữ nguyên các keys: win_rate, profit_loss_ratio, max_consecutive_loss...
    """
    if not trades:
        return {
            "win_rate": 0.0,
            "profit_loss_ratio": 0.0,
            "max_consecutive_loss": 0,
            "avg_holding_bars": 0.0,
            "profit_factor": 0.0,
            "avg_win": 0.0, 
            "avg_loss": 0.0,
        }

    wins = [t.pnl for t in trades if t.pnl > 0]
    losses = [t.pnl for t in trades if t.pnl < 0]

    win_rate = len(wins) / len(trades)

    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = abs(float(np.mean(losses))) if losses else 1e-10
    profit_loss_ratio = avg_win / avg_loss if avg_loss > 1e-10 else 0.0

    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 1e-10
    profit_factor = gross_profit / gross_loss if gross_loss > 1e-10 else 0.0

    max_consec = 0
    cur_consec = 0
    for t in trades:
        if t.pnl < 0:
            cur_consec += 1
            max_consec = max(max_consec, cur_consec)
        else:
            cur_consec = 0

    hold_bars = [t.holding_bars for t in trades if t.holding_bars > 0]
    avg_holding = float(np.mean(hold_bars)) if hold_bars else 0.0

    return {
        "win_rate": win_rate,
        "profit_loss_ratio": round(profit_loss_ratio, 4),
        "max_consecutive_loss": max_consec,
        "avg_holding_bars": round(avg_holding, 1),
        "profit_factor": round(profit_factor, 4),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
    }


def by_symbol_stats(trades: List[TradeRecord]) -> Dict[str, Dict[str, Any]]:
    """Thống kê chi tiết hiệu suất theo từng mã tài sản (Symbol)."""
    groups: Dict[str, list] = {}
    for t in trades:
        groups.setdefault(t.symbol, []).append(t)

    result = {}
    for sym, sym_trades in groups.items():
        pnls = [t.pnl for t in sym_trades]
        wins = [p for p in pnls if p > 0]
        result[sym] = {
            "count": len(sym_trades),
            "win_rate": round(len(wins) / len(sym_trades), 4) if sym_trades else 0.0,
            "total_pnl": round(sum(pnls), 2),
            "avg_pnl": round(float(np.mean(pnls)), 2) if pnls else 0.0,
        }
    return result

def by_exit_reason_stats(trades: List[TradeRecord]) -> Dict[str, Dict[str, Any]]:
    """Per-exit-reason trade statistics.

    Args:
        trades: Completed round-trip trades.

    Returns:
        {reason: {count, total_pnl}}.
    """
    groups: Dict[str, list] = {}
    for t in trades:
        groups.setdefault(t.exit_reason, []).append(t)

    result = {}
    for reason, reason_trades in groups.items():
        pnls = [t.pnl for t in reason_trades]
        result[reason] = {
            "count": len(reason_trades),
            "total_pnl": round(sum(pnls), 2),
        }
    return result


def calc_metrics(
    equity_curve: Union[pl.Series, Any],
    trades: List[TradeRecord],
    initial_cash: float,
    bars_per_year: int = 250,
    bench_ret: Optional[pl.Series] = None,
) -> Dict[str, Any]:
    """Tính toán bộ chỉ số hiệu suất đầy đủ (Sharpe, CAGR, Drawdown...)."""
    if len(equity_curve) == 0:
        return _empty_metrics(initial_cash)

    # Chuyển đổi sang NumPy để tính toán toán học nhanh hơn
    eq_values = equity_curve.to_numpy() if isinstance(equity_curve, pl.Series) else np.array(equity_curve)
    n = len(eq_values)
    bpy = bars_per_year

    # Tính lợi nhuận từng cây nến (Returns)
    port_ret = np.diff(eq_values) / eq_values[:-1]
    port_ret = np.insert(port_ret, 0, 0.0)

    total_ret = float(eq_values[-1] / initial_cash - 1)
    ann_ret = float((1 + total_ret) ** (bpy / max(n, 1)) - 1)
    vol = float(np.std(port_ret))
    sharpe = float(np.mean(port_ret) / (vol + 1e-10) * np.sqrt(bpy))

    # Tính toán Drawdown
    peak = np.maximum.accumulate(eq_values)
    dd = (eq_values - peak) / np.where(peak > 0, peak, 1.0)
    max_dd = float(dd.min())

    calmar = ann_ret / abs(max_dd) if abs(max_dd) > 1e-10 else 0.0

    # Sortino
    downside_ret = port_ret[port_ret < 0]
    downside_std = float(np.std(downside_ret)) if len(downside_ret) > 1 else 1e-10
    sortino = float(np.mean(port_ret) / (downside_std + 1e-10) * np.sqrt(bpy))

    trade_stats = win_rate_and_stats(trades)

    # So sánh với Benchmark
    bench_return = 0.0
    excess = 0.0
    ir = 0.0
    if bench_ret is not None and len(bench_ret) > 0:
        b_ret = bench_ret.to_numpy()
        bench_return = float(np.prod(1 + b_ret) - 1)
        excess = total_ret - bench_return
        active_ret = port_ret - b_ret
        active_std = float(np.std(active_ret))
        ir = float(np.mean(active_ret) / (active_std + 1e-10) * np.sqrt(bpy))

    return {
        "final_value": float(eq_values[-1]),
        "total_return": round(total_ret * 100, 2),    # Chuyển sang %
        "annual_return": round(ann_ret * 100, 2),   # Chuyển sang %
        "max_drawdown": round(max_dd * 100, 2),     # Chuyển sang %
        "sharpe_ratio": round(sharpe, 4),           # Khớp với UI (BacktestDetail.tsx)
        "sharpe": round(sharpe, 4),                 # Giữ lại để tương thích ngược
        "calmar": round(calmar, 4),
        "sortino": round(sortino, 4),
        "win_rate": round(trade_stats["win_rate"] * 100, 2), # Chuyển sang %
        "profit_loss_ratio": trade_stats["profit_loss_ratio"],
        "rr_ratio": trade_stats["profit_loss_ratio"], # Khớp với UI
        "profit_factor": trade_stats["profit_factor"],
        "max_consecutive_loss": trade_stats["max_consecutive_loss"],
        "avg_holding_days": trade_stats["avg_holding_bars"],
        "total_trades": len(trades),                 # Khớp với UI
        "trade_count": len(trades),                  # Tương thích ngược
        "expectancy": round(float(total_ret * initial_cash / len(trades)), 2) if len(trades) > 0 else 0.0,
        "avg_win": trade_stats["avg_win"],
        "avg_loss": trade_stats["avg_loss"],
        "benchmark_return": round(bench_return * 100, 2),
        "excess_return": round(excess * 100, 2),
        "information_ratio": round(ir, 4),
    }


def _empty_metrics(initial_cash: float) -> Dict[str, Any]:
    """Trả về bộ chỉ số rỗng khi không có dữ liệu."""
    return {
        "final_value": initial_cash,
        "total_return": 0.0, "annual_return": 0.0, "max_drawdown": 0.0,
        "sharpe_ratio": 0.0, "sharpe": 0.0, "calmar": 0.0, "sortino": 0.0,
        "win_rate": 0.0, "profit_loss_ratio": 0.0, "rr_ratio": 0.0, "profit_factor": 0.0,
        "max_consecutive_loss": 0, "avg_holding_days": 0, "total_trades": 0, "trade_count": 0,
        "expectancy": 0.0, "avg_win": 0.0, "avg_loss": 0.0,
        "benchmark_return": 0.0, "excess_return": 0.0, "information_ratio": 0.0,
    }