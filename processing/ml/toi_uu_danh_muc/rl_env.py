"""
rl_env.py — Môi trường Gymnasium cho PPO Portfolio Optimization

Môi trường mô phỏng quản lý danh mục đầu tư:
- State:  [returns_window, current_weights, risk_metrics, regime_id]
- Action: Delta weights (thay đổi phân bổ tương đối)
- Reward: Sharpe-based risk-adjusted return có phạt drawdown

Cách dùng:
    from processing.ml.toi_uu_danh_muc.rl_env import PortfolioEnv
    from stable_baselines3 import PPO

    env = PortfolioEnv(returns_df, window=60)
    model = PPO("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=500_000)
"""
from __future__ import annotations
import numpy as np
import polars as pl
from typing import Optional, Tuple

from processing.ml.toi_uu_danh_muc.risk import (
    tinh_sharpe, tinh_max_drawdown, tinh_risk_contribution,
)


class PortfolioEnv:
    """
    Gymnasium-compatible environment cho PPO Portfolio Optimization.

    Observations (state):
        - returns_window: (window, n_assets) — cửa sổ returns lịch sử
        - current_weights: (n_assets,) — phân bổ hiện tại
        - risk_features: (4,) — [portfolio_ret, portfolio_vol, current_dd, sharpe_est]
        - regime_oh: (8,) — one-hot regime từ trang_thai_thi_truong_ml

    Actions:
        - (n_assets,) continuous — logits softmax → new weights

    Reward:
        - Sharpe-scaled step return
        - Penalty: drawdown vượt threshold, transaction cost
        - Bonus: Calmar ratio cao
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        returns_df: pl.DataFrame | np.ndarray,
        regime_arr: Optional[np.ndarray] = None,
        window:     int   = 60,
        tc_bps:     float = 5.0,    # Transaction cost (basis points)
        max_dd_pen: float = 0.10,   # Penalty khi DD vượt 10%
        risk_free:  float = 0.0,
    ):
        if isinstance(returns_df, pl.DataFrame):
            self.symbols = returns_df.columns
            self.R = returns_df.to_numpy().astype(np.float64)
        else:
            self.symbols = [f"asset_{i}" for i in range(returns_df.shape[1])]
            self.R = returns_df.astype(np.float64)

        self.n_assets = self.R.shape[1]
        self.T        = self.R.shape[0]
        self.window   = window
        self.tc_bps   = tc_bps / 10_000
        self.max_dd_pen = max_dd_pen
        self.rf       = risk_free

        self.regime_arr = regime_arr if regime_arr is not None else np.zeros(self.T, dtype=np.int32)

        # Observation & Action spaces (tương thích gymnasium)
        obs_dim = window * self.n_assets + self.n_assets + 4 + 8
        self.observation_space = _SimpleBox(-5.0, 5.0, shape=(obs_dim,))
        self.action_space      = _SimpleBox(-1.0, 1.0, shape=(self.n_assets,))

        self._t          = window
        self._weights    = np.ones(self.n_assets) / self.n_assets
        self._equity     = 1.0
        self._peak       = 1.0
        self._port_rets  = []

    # ── Gymnasium API ─────────────────────────────────────────────────────────

    def reset(self, seed: int = None) -> Tuple[np.ndarray, dict]:
        rng = np.random.default_rng(seed)
        self._t       = self.window + rng.integers(0, max(1, self.T - self.window - 252))
        self._weights = np.ones(self.n_assets) / self.n_assets
        self._equity  = 1.0
        self._peak    = 1.0
        self._port_rets = []
        return self._obs(), {}

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, dict]:
        # 1. Chuyển action → new weights (softmax)
        new_w = _softmax(action)

        # 2. Transaction cost
        tc = np.abs(new_w - self._weights).sum() * self.tc_bps

        # 3. Portfolio return tại bước t
        step_ret = float(self.R[self._t] @ new_w) - tc
        self._equity *= (1 + step_ret)
        self._peak    = max(self._peak, self._equity)
        self._port_rets.append(step_ret)
        self._weights = new_w
        self._t      += 1

        # 4. Reward
        reward = self._compute_reward(step_ret)

        # 5. Done
        terminated = self._t >= self.T - 1
        info = {
            "equity":  self._equity,
            "weights": self._weights.tolist(),
            "step_ret": step_ret,
        }
        return self._obs(), reward, terminated, False, info

    # ── Internal ──────────────────────────────────────────────────────────────

    def _obs(self) -> np.ndarray:
        t = min(self._t, self.T - 1)

        # Returns window (window × n_assets) → flatten
        start = max(0, t - self.window)
        ret_window = self.R[start: t]
        if len(ret_window) < self.window:
            pad = np.zeros((self.window - len(ret_window), self.n_assets))
            ret_window = np.vstack([pad, ret_window])
        ret_flat = ret_window.flatten()

        # Risk features
        if len(self._port_rets) >= 2:
            pr = np.array(self._port_rets[-min(60, len(self._port_rets)):])
            port_ret = pr.mean()
            port_vol = pr.std() + 1e-10
            sharpe_e = (port_ret / port_vol) * np.sqrt(252)
        else:
            port_ret, port_vol, sharpe_e = 0.0, 1e-10, 0.0

        dd = (self._equity - self._peak) / (self._peak + 1e-10)
        risk_feat = np.array([port_ret * 100, port_vol * 100, dd, sharpe_e], dtype=np.float64)

        # Regime one-hot (8)
        regime = int(self.regime_arr[t]) if t < len(self.regime_arr) else 0
        regime_oh = np.zeros(8, dtype=np.float64)
        regime_oh[np.clip(regime, 0, 7)] = 1.0

        obs = np.concatenate([ret_flat, self._weights, risk_feat, regime_oh]).astype(np.float32)
        return np.clip(obs, -5.0, 5.0)

    def _compute_reward(self, step_ret: float) -> float:
        dd = (self._equity - self._peak) / (self._peak + 1e-10)

        # Base reward: step return (annualized scaled)
        reward = step_ret * 252

        # Sharpe bonus: tính Sharpe 20 bước gần nhất
        if len(self._port_rets) >= 20:
            pr = np.array(self._port_rets[-20:])
            sharpe = (pr.mean() / (pr.std() + 1e-10)) * np.sqrt(252)
            reward += sharpe * 0.01   # Nhỏ để không override signal

        # Drawdown penalty
        if abs(dd) > self.max_dd_pen:
            excess_dd = abs(dd) - self.max_dd_pen
            reward -= excess_dd * 5.0   # Phạt nặng khi vượt ngưỡng

        # Diversification bonus: thưởng entropy phân bổ
        w = self._weights + 1e-10
        entropy = -np.sum(w * np.log(w))
        reward += entropy * 0.005

        return float(np.clip(reward, -10.0, 10.0))

    def render(self):
        pass

    def close(self):
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


class _SimpleBox:
    """Minimal Box space tương thích stable-baselines3 (không cần gymnasium cài)."""
    def __init__(self, low, high, shape):
        self.low   = np.full(shape, low,  dtype=np.float32)
        self.high  = np.full(shape, high, dtype=np.float32)
        self.shape = shape
        self.dtype = np.float32

    def sample(self) -> np.ndarray:
        return np.random.uniform(self.low, self.high).astype(np.float32)
