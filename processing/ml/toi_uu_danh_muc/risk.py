"""
risk.py — Bộ chỉ số rủi ro danh mục (Portfolio Risk Metrics)

Tất cả hàm đều nhận numpy array hoặc polars Series/DataFrame.
Không cần scipy — dùng numpy thuần để đảm bảo tốc độ.
"""
from __future__ import annotations
import numpy as np
import polars as pl
from typing import Dict


# ─────────────────────────────────────────────────────────────────────────────
# 1. SINGLE-ASSET METRICS
# ─────────────────────────────────────────────────────────────────────────────

def tinh_sharpe(returns: np.ndarray, rf: float = 0.0, periods: int = 252) -> float:
    """Sharpe Ratio (annualized)."""
    r = np.asarray(returns, dtype=np.float64)
    excess = r - rf / periods
    std = r.std()
    if std < 1e-10:
        return 0.0
    return float((excess.mean() / std) * np.sqrt(periods))


def tinh_sortino(returns: np.ndarray, rf: float = 0.0, periods: int = 252) -> float:
    """Sortino Ratio — chỉ phạt downside volatility."""
    r = np.asarray(returns, dtype=np.float64)
    excess = r.mean() - rf / periods
    down = r[r < 0]
    down_std = down.std() if len(down) > 1 else 1e-10
    return float((excess / (down_std + 1e-10)) * np.sqrt(periods))


def tinh_max_drawdown(equity_curve: np.ndarray) -> float:
    """Max Drawdown (0 → 1) từ equity curve (không phải returns)."""
    eq = np.asarray(equity_curve, dtype=np.float64)
    running_max = np.maximum.accumulate(eq)
    dd = (eq - running_max) / (running_max + 1e-10)
    return float(dd.min())    # Giá trị âm, VD: -0.25 = -25%


def tinh_calmar(returns: np.ndarray, periods: int = 252) -> float:
    """Calmar Ratio = Annual Return / |Max Drawdown|."""
    r = np.asarray(returns, dtype=np.float64)
    annual_ret = r.mean() * periods
    equity = np.cumprod(1 + r)
    mdd = abs(tinh_max_drawdown(equity))
    return float(annual_ret / (mdd + 1e-10))


def tinh_var(returns: np.ndarray, confidence: float = 0.95) -> float:
    """Value at Risk (VaR) — mức lỗ tối đa tại confidence level (dương = lỗ)."""
    r = np.asarray(returns, dtype=np.float64)
    return float(-np.percentile(r, (1 - confidence) * 100))


def tinh_cvar(returns: np.ndarray, confidence: float = 0.95) -> float:
    """Conditional VaR (Expected Shortfall) — lỗ trung bình vượt VaR."""
    r = np.asarray(returns, dtype=np.float64)
    var = tinh_var(r, confidence)
    tail = r[r <= -var]
    return float(-tail.mean()) if len(tail) > 0 else var


def tinh_win_stats(returns: np.ndarray) -> Dict[str, float]:
    """Win rate, avg win, avg loss, profit factor từ mảng returns."""
    r = np.asarray(returns, dtype=np.float64)
    wins  = r[r > 0]
    losses = r[r < 0]
    win_rate    = len(wins) / (len(r) + 1e-10)
    avg_win     = float(wins.mean())  if len(wins)   > 0 else 0.0
    avg_loss    = float(losses.mean()) if len(losses) > 0 else 0.0
    profit_factor = (wins.sum() / (-losses.sum() + 1e-10)) if len(losses) > 0 else float("inf")
    win_loss_ratio = abs(avg_win / (avg_loss + 1e-10)) if avg_loss != 0 else float("inf")
    return {
        "win_rate":        round(win_rate, 4),
        "avg_win":         round(avg_win, 6),
        "avg_loss":        round(avg_loss, 6),
        "win_loss_ratio":  round(win_loss_ratio, 4),
        "profit_factor":   round(profit_factor, 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. PORTFOLIO-LEVEL METRICS
# ─────────────────────────────────────────────────────────────────────────────

def tinh_portfolio_returns(
    returns_df: pl.DataFrame | np.ndarray,
    weights: Dict[str, float] | np.ndarray,
) -> np.ndarray:
    """Tính chuỗi returns danh mục từ weights."""
    if isinstance(returns_df, pl.DataFrame):
        symbols = returns_df.columns
        w = np.array([weights.get(s, 0.0) for s in symbols], dtype=np.float64)
        R = returns_df.to_numpy()
    else:
        R = returns_df
        w = np.asarray(weights, dtype=np.float64)

    w = w / (w.sum() + 1e-10)
    return R @ w


def bao_cao_rui_ro(
    returns_df: pl.DataFrame | np.ndarray,
    weights: Dict[str, float] | np.ndarray,
    rf: float = 0.0,
    periods: int = 252,
    confidence: float = 0.95,
) -> Dict[str, float]:
    """Báo cáo đầy đủ rủi ro danh mục."""
    port_ret = tinh_portfolio_returns(returns_df, weights)
    equity   = np.cumprod(1 + port_ret)
    stats    = tinh_win_stats(port_ret)

    return {
        "annual_return":  round(float(port_ret.mean() * periods), 4),
        "annual_vol":     round(float(port_ret.std() * np.sqrt(periods)), 4),
        "sharpe":         round(tinh_sharpe(port_ret, rf, periods), 4),
        "sortino":        round(tinh_sortino(port_ret, rf, periods), 4),
        "max_drawdown":   round(tinh_max_drawdown(equity), 4),
        "calmar":         round(tinh_calmar(port_ret, periods), 4),
        "var_95":         round(tinh_var(port_ret, confidence), 4),
        "cvar_95":        round(tinh_cvar(port_ret, confidence), 4),
        **stats,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. RISK CONTRIBUTION & CORRELATION
# ─────────────────────────────────────────────────────────────────────────────

def tinh_risk_contribution(
    weights: np.ndarray,
    cov: np.ndarray,
) -> np.ndarray:
    """Tính % đóng góp rủi ro của từng tài sản (Risk Contribution)."""
    w = np.asarray(weights, dtype=np.float64)
    port_var = float(w @ cov @ w)
    if port_var < 1e-12:
        return np.ones(len(w)) / len(w)
    marginal = cov @ w
    contrib = w * marginal / (np.sqrt(port_var) + 1e-10)
    total = contrib.sum()
    return contrib / (total + 1e-10)


def tinh_ma_tran_tuong_quan(returns_df: pl.DataFrame) -> np.ndarray:
    """Tính ma trận tương quan nhanh bằng Polars."""
    symbols = returns_df.columns
    n = len(symbols)
    data = np.array([returns_df[s].to_numpy() for s in symbols], dtype=np.float64)  # (n, T)
    # Chuẩn hóa
    means = data.mean(axis=1, keepdims=True)
    stds  = data.std(axis=1, keepdims=True) + 1e-10
    data_n = (data - means) / stds
    corr = (data_n @ data_n.T) / data.shape[1]
    return corr


def loc_tai_san_tuong_quan(
    symbols: list[str],
    corr: np.ndarray,
    threshold: float = 0.85,
) -> list[str]:
    """Loại bỏ tài sản có tương quan cao (> threshold).

    Giữ tài sản đầu tiên trong cặp, loại tài sản thứ hai.
    Returns: Danh sách symbols sau khi lọc.
    """
    n = len(symbols)
    keep = list(range(n))
    remove = set()

    for i in range(n):
        for j in range(i + 1, n):
            if j in remove:
                continue
            if abs(corr[i, j]) > threshold:
                remove.add(j)

    return [symbols[i] for i in keep if i not in remove]


# ─────────────────────────────────────────────────────────────────────────────
# 4. DRAWDOWN TRACKING
# ─────────────────────────────────────────────────────────────────────────────

class DrawdownTracker:
    """Theo dõi drawdown real-time và tính hệ số scale-down vị thế."""

    def __init__(self, max_dd_limit: float = 0.15):
        """
        Args:
            max_dd_limit: Ngưỡng drawdown tối đa cho phép (VD: 0.15 = -15%).
                          Khi vượt ngưỡng, hệ thống giảm toàn bộ size về 0.
        """
        self.max_dd_limit = max_dd_limit
        self.peak_equity  = None
        self.current_dd   = 0.0

    def cap_nhat(self, equity: float) -> None:
        """Cập nhật equity mỗi nến."""
        if self.peak_equity is None or equity > self.peak_equity:
            self.peak_equity = equity
        self.current_dd = (equity - self.peak_equity) / (self.peak_equity + 1e-10)

    def he_so_giam_size(self) -> float:
        """Trả về hệ số scale-down (0-1) dựa trên drawdown hiện tại.

        Logic tuyến tính:
            0%  DD → scale = 1.0  (full size)
            50% max_dd → scale = 0.5
            100% max_dd → scale = 0.0 (dừng giao dịch)
        """
        if self.current_dd >= 0:
            return 1.0
        dd_ratio = abs(self.current_dd) / (self.max_dd_limit + 1e-10)
        return float(max(0.0, 1.0 - dd_ratio))

    def dung_giao_dich(self) -> bool:
        """True nếu drawdown vượt ngưỡng tối đa → dừng toàn bộ giao dịch."""
        return abs(self.current_dd) >= self.max_dd_limit

    @property
    def trang_thai(self) -> dict:
        return {
            "current_dd":    round(self.current_dd, 4),
            "peak_equity":   self.peak_equity,
            "scale_factor":  round(self.he_so_giam_size(), 4),
            "dung_giao_dich": self.dung_giao_dich(),
        }
