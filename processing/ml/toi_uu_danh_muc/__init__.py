"""
toi_uu_danh_muc — Tối Ưu Hóa Danh Mục Đầu Tư (KAIROS v3.0)

Chiến lược tối ưu:
    1. Markowitz       — Max Sharpe (Monte Carlo, 10k simulations)
    2. Risk Parity     — Equal Risk Contribution (ERC, không cần scipy)
    3. Min Variance    — Danh mục biến động thấp nhất
    4. Kelly Portfolio — Markowitz × Kelly(confidence) → scale theo tín hiệu
    5. Regime-aware    — Điều chỉnh phân bổ theo trạng thái thị trường (STATE_MAP)
    6. PPO (RL)        — Học tối ưu động, cần train qua PortfolioEnv

Quản lý rủi ro:
    - DrawdownTracker     — Scale-down real-time khi vượt ngưỡng DD
    - Correlation Filter  — Loại tài sản tương quan cao (threshold 0.85)
    - Risk Report         — VaR, CVaR, Sharpe, Sortino, Calmar, Max DD

Cách dùng:
    from processing.ml.toi_uu_danh_muc import PortfolioOptimizer

    opt = PortfolioOptimizer()
    weights = opt.markowitz(returns_df)
    weights = opt.risk_parity(returns_df)
    weights = opt.regime_aware(returns_df, regime_id=3, scores={"BTC": 0.72})
    size    = opt.kelly_position_size(capital=10000, score=0.72)
    report  = opt.bao_cao_danh_muc(returns_df, weights)
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import polars as pl

from processing.ml.toi_uu_danh_muc.risk import (
    tinh_risk_contribution,
    tinh_ma_tran_tuong_quan,
    loc_tai_san_tuong_quan,
    bao_cao_rui_ro,
    DrawdownTracker,
)

try:
    from data.store import A11
    DATA_DIR = A11.ml_model("toi_uu_danh_muc")
except ImportError:
    DATA_DIR = Path(__file__).parent / "du_lieu"
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# REGIME → ALLOCATION MULTIPLIER (STATE_MAP từ trang_thai_thi_truong_ml)
# ─────────────────────────────────────────────────────────────────────────────
_REGIME_MULTIPLIER = {
    0: 0.0,   # DONG_BANG    — Dừng hoàn toàn, volume cạn kiệt
    1: 0.6,   # NEN_CHAT     — Chờ breakout, giảm size 40%
    2: 0.8,   # DAU_XU_HUONG — Bắt đầu trend, full 80%
    3: 1.0,   # XU_HUONG_MANH — Follow trend, full size
    4: 0.4,   # CAO_TRAO     — Scale out, giảm mạnh
    5: 0.5,   # HOI_QUY      — Counter-trend, thận trọng
    6: 0.3,   # NHIEU_DONG   — Range chop, giảm tối đa
    7: 0.5,   # DAO_CHIEU    — Chờ xác nhận, nửa size
}


class PortfolioOptimizer:
    """Tối ưu hóa danh mục toàn diện: 6 chiến lược + quản lý rủi ro."""

    MAX_KELLY_FRACTION = 0.25   # Half-Kelly cap
    MAX_PORTFOLIO_RISK = 0.02   # 2% vốn rủi ro tối đa mỗi lệnh

    def __init__(self):
        self._rl_model = None
        self._dd_tracker = DrawdownTracker(max_dd_limit=0.15)
        self._try_load_rl()

    def _try_load_rl(self):
        model_path = DATA_DIR / "ppo_model.zip"
        if model_path.exists():
            try:
                from stable_baselines3 import PPO
                self._rl_model = PPO.load(str(model_path))
            except Exception as e:
                print(f"⚠️ PortfolioOptimizer PPO: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # UTILS nội bộ
    # ─────────────────────────────────────────────────────────────────────────

    def _to_numpy(self, returns_df) -> tuple[list[str], np.ndarray]:
        """Chuẩn hóa đầu vào về (symbols, R_numpy)."""
        if isinstance(returns_df, pl.DataFrame):
            return returns_df.columns, returns_df.to_numpy().astype(np.float64)
        cols = list(returns_df.columns)
        return cols, returns_df.values.astype(np.float64)

    def _polars_cov(self, returns_df) -> np.ndarray:
        """Ma trận hiệp phương sai nhanh bằng Polars (O(n²T) bằng dot product)."""
        symbols, R = self._to_numpy(returns_df)
        means = R.mean(axis=0, keepdims=True)
        Rc = R - means
        n = len(R)
        return (Rc.T @ Rc) / (n - 1)

    def _normalize(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Chuẩn hóa weights tổng = 1.0."""
        total = sum(weights.values())
        if total <= 0:
            n = len(weights)
            return {s: round(1 / n, 4) for s in weights}
        return {s: round(v / total, 4) for s, v in weights.items()}

    # ─────────────────────────────────────────────────────────────────────────
    # 1. MARKOWITZ — MAX SHARPE (MONTE CARLO)
    # ─────────────────────────────────────────────────────────────────────────

    def markowitz(self, returns_df, n_sim: int = 10_000) -> Dict[str, float]:
        """Max Sharpe bằng Monte Carlo simulation."""
        try:
            symbols, R = self._to_numpy(returns_df)
            n = len(symbols)
            mu  = R.mean(axis=0) * 252
            cov = self._polars_cov(returns_df) * 252

            best_sharpe, best_w = -999.0, np.ones(n) / n
            rng = np.random.default_rng(42)

            for _ in range(n_sim):
                w = rng.random(n)
                w /= w.sum()
                ret = float(w @ mu)
                vol = float(np.sqrt(w @ cov @ w))
                s   = ret / (vol + 1e-10)
                if s > best_sharpe:
                    best_sharpe, best_w = s, w.copy()

            return {s: round(float(w), 4) for s, w in zip(symbols, best_w)}
        except Exception as e:
            print(f"⚠️ Markowitz lỗi: {e}")
            symbols, _ = self._to_numpy(returns_df)
            n = len(symbols)
            return {s: round(1 / n, 4) for s in symbols}

    # ─────────────────────────────────────────────────────────────────────────
    # 2. RISK PARITY — EQUAL RISK CONTRIBUTION (ERC)
    # ─────────────────────────────────────────────────────────────────────────

    def risk_parity(self, returns_df, max_iter: int = 1000, tol: float = 1e-8) -> Dict[str, float]:
        """Equal Risk Contribution — mỗi tài sản đóng góp rủi ro bằng nhau.

        Thuật toán: Gradient descent trên Risk Contribution loss.
        Không cần scipy — thuần numpy.
        """
        try:
            symbols, _ = self._to_numpy(returns_df)
            n   = len(symbols)
            cov = self._polars_cov(returns_df)
            target = np.ones(n) / n   # ERC target = 1/n mỗi tài sản

            # Khởi tạo bằng inverse volatility
            vols = np.sqrt(np.diag(cov))
            w = (1.0 / (vols + 1e-10))
            w /= w.sum()

            lr = 0.01
            for _ in range(max_iter):
                rc = tinh_risk_contribution(w, cov)
                grad = 2 * (rc - target)

                # Gradient step + project về simplex
                w_new = w - lr * grad
                w_new = np.maximum(w_new, 1e-6)
                w_new /= w_new.sum()

                if np.linalg.norm(w_new - w) < tol:
                    w = w_new
                    break
                w = w_new

            return {s: round(float(wi), 4) for s, wi in zip(symbols, w)}
        except Exception as e:
            print(f"⚠️ Risk Parity lỗi: {e}")
            symbols, _ = self._to_numpy(returns_df)
            n = len(symbols)
            return {s: round(1 / n, 4) for s in symbols}

    # ─────────────────────────────────────────────────────────────────────────
    # 3. MIN VARIANCE
    # ─────────────────────────────────────────────────────────────────────────

    def min_variance(self, returns_df, n_sim: int = 10_000) -> Dict[str, float]:
        """Danh mục biến động thấp nhất (Monte Carlo)."""
        try:
            symbols, _ = self._to_numpy(returns_df)
            n   = len(symbols)
            cov = self._polars_cov(returns_df) * 252

            best_vol, best_w = 999.0, np.ones(n) / n
            rng = np.random.default_rng(0)

            for _ in range(n_sim):
                w = rng.random(n)
                w /= w.sum()
                vol = float(np.sqrt(w @ cov @ w))
                if vol < best_vol:
                    best_vol, best_w = vol, w.copy()

            return {s: round(float(w), 4) for s, w in zip(symbols, best_w)}
        except Exception as e:
            print(f"⚠️ Min Variance lỗi: {e}")
            symbols, _ = self._to_numpy(returns_df)
            n = len(symbols)
            return {s: round(1 / n, 4) for s in symbols}

    # ─────────────────────────────────────────────────────────────────────────
    # 4. KELLY CRITERION
    # ─────────────────────────────────────────────────────────────────────────

    def kelly_fraction(
        self,
        win_rate:   float,
        win_ratio:  float = 1.5,
        confidence: float = 1.0,
    ) -> float:
        """Kelly Fraction scale theo Confidence Score.

        Formula: f* = (p*(b+1) - 1) / b, rồi × confidence, cap tại 0.25.
        """
        b      = max(win_ratio, 0.1)
        f_star = max(0.0, (win_rate * (b + 1) - 1) / b)
        return round(min(f_star * confidence, self.MAX_KELLY_FRACTION), 4)

    def kelly_position_size(
        self,
        capital:   float,
        score:     float,
        win_rate:  float = 0.55,
        win_ratio: float = 1.5,
        max_dd:    float = 0.05,
    ) -> dict:
        """Size lệnh (USD) = Kelly × Confidence, bị giới hạn bởi Max Drawdown.

        Returns:
            {"position_usd": float, "kelly_f": float, "risk_limited": bool}
        """
        kelly_f    = self.kelly_fraction(win_rate, win_ratio, confidence=score)
        kelly_usd  = capital * kelly_f
        dd_limit   = capital * max_dd
        risk_limited = kelly_usd > dd_limit
        position_usd = min(kelly_usd, dd_limit)

        # Thêm hệ số giảm nếu đang trong drawdown
        dd_scale = self._dd_tracker.he_so_giam_size()
        position_usd *= dd_scale

        return {
            "position_usd": round(position_usd, 2),
            "kelly_f":       kelly_f,
            "risk_limited":  risk_limited,
            "dd_scale":      round(dd_scale, 4),
        }

    def kelly_portfolio(
        self,
        returns_df,
        scores:    Dict[str, float],
        win_rate:  float = 0.55,
        win_ratio: float = 1.5,
    ) -> Dict[str, float]:
        """Markowitz weights × Kelly(confidence) → chuẩn hóa về 1.0."""
        markowitz_w = self.markowitz(returns_df)
        combined = {
            s: markowitz_w[s] * self.kelly_fraction(win_rate, win_ratio, scores.get(s, 0.5))
            for s in markowitz_w
        }
        return self._normalize(combined)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. REGIME-AWARE ALLOCATION
    # ─────────────────────────────────────────────────────────────────────────

    def regime_aware(
        self,
        returns_df,
        regime_id:  int,
        scores:     Optional[Dict[str, float]] = None,
        base:       str = "markowitz",     # "markowitz" | "risk_parity" | "equal"
    ) -> Dict[str, float]:
        """Điều chỉnh phân bổ theo trạng thái thị trường (STATE_MAP).

        Quy trình:
            1. Tính base weights (Markowitz / Risk Parity / Equal)
            2. Scale toàn bộ theo regime multiplier
            3. Nếu có scores → nhân thêm Kelly confidence
            4. Chuẩn hóa

        Args:
            regime_id: 0-7 từ trang_thai_thi_truong_ml.STATE_MAP
            scores:    {symbol: confidence_score} từ SignalScorerEngine
            base:      Chiến lược base weights
        """
        multiplier = _REGIME_MULTIPLIER.get(regime_id, 0.5)

        # Regime 0 (DONG_BANG) → dừng hoàn toàn
        if multiplier == 0.0:
            symbols, _ = self._to_numpy(returns_df)
            return {s: 0.0 for s in symbols}

        # Base weights
        if base == "risk_parity":
            w = self.risk_parity(returns_df)
        elif base == "equal":
            symbols, _ = self._to_numpy(returns_df)
            w = self.equal_weight(symbols)
        else:
            w = self.markowitz(returns_df)

        # Scale theo confidence scores nếu có
        if scores:
            w = {s: w[s] * scores.get(s, 0.5) for s in w}

        # Scale theo regime multiplier
        w = {s: v * multiplier for s, v in w.items()}

        return self._normalize(w)

    # ─────────────────────────────────────────────────────────────────────────
    # 6. CORRELATION FILTER
    # ─────────────────────────────────────────────────────────────────────────

    def loc_tuong_quan(
        self,
        returns_df,
        threshold: float = 0.85,
    ) -> Dict[str, float]:
        """Lọc bỏ tài sản có tương quan cao, trả về equal-weight trên nhóm còn lại.

        Dùng trước khi tối ưu để tránh danh mục tập trung vào tài sản đồng biến.
        """
        if isinstance(returns_df, pl.DataFrame):
            symbols = list(returns_df.columns)
        else:
            symbols = list(returns_df.columns)

        corr = tinh_ma_tran_tuong_quan(
            returns_df if isinstance(returns_df, pl.DataFrame)
            else pl.DataFrame(returns_df.to_dict())
        )
        filtered = loc_tai_san_tuong_quan(symbols, corr, threshold)
        w = round(1 / len(filtered), 4) if filtered else 0.0
        return {s: (w if s in filtered else 0.0) for s in symbols}

    def kiem_tra_tuong_quan(self, returns_df, threshold: float = 0.85) -> dict:
        """Báo cáo các cặp tài sản có tương quan cao."""
        if isinstance(returns_df, pl.DataFrame):
            symbols = list(returns_df.columns)
        else:
            symbols = list(returns_df.columns)

        corr = tinh_ma_tran_tuong_quan(
            returns_df if isinstance(returns_df, pl.DataFrame)
            else pl.DataFrame({s: returns_df[s].tolist() for s in symbols})
        )

        high_corr_pairs = []
        n = len(symbols)
        for i in range(n):
            for j in range(i + 1, n):
                if abs(corr[i, j]) > threshold:
                    high_corr_pairs.append({
                        "asset_1":    symbols[i],
                        "asset_2":    symbols[j],
                        "correlation": round(float(corr[i, j]), 4),
                    })

        return {
            "n_pairs_high_corr": len(high_corr_pairs),
            "threshold":          threshold,
            "pairs":              high_corr_pairs,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 7. DRAWDOWN MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────

    def cap_nhat_equity(self, equity: float) -> dict:
        """Cập nhật equity thực tế để DrawdownTracker tính scale factor.

        Gọi hàm này sau mỗi nến đóng cửa.

        Returns:
            Trạng thái drawdown hiện tại.
        """
        self._dd_tracker.cap_nhat(equity)
        return self._dd_tracker.trang_thai

    def nen_dung_giao_dich(self) -> bool:
        """True nếu drawdown vượt giới hạn → dừng toàn bộ bot."""
        return self._dd_tracker.dung_giao_dich()

    def thiet_lap_drawdown_limit(self, max_dd: float = 0.15) -> None:
        """Thiết lập lại ngưỡng Max Drawdown."""
        self._dd_tracker = DrawdownTracker(max_dd_limit=max_dd)

    # ─────────────────────────────────────────────────────────────────────────
    # 8. PORTFOLIO ANALYTICS
    # ─────────────────────────────────────────────────────────────────────────

    def bao_cao_danh_muc(
        self,
        returns_df,
        weights:    Dict[str, float],
        rf:         float = 0.0,
        periods:    int   = 252,
    ) -> dict:
        """Báo cáo đầy đủ rủi ro danh mục (VaR, CVaR, Sharpe, Sortino, MDD...).

        Args:
            returns_df: DataFrame lịch sử returns
            weights:    {symbol: weight} đã tính từ markowitz/risk_parity/etc.

        Returns:
            Dict với đầy đủ chỉ số rủi ro.
        """
        return bao_cao_rui_ro(returns_df, weights, rf=rf, periods=periods)

    def so_sanh_chien_luoc(self, returns_df, scores: Optional[Dict[str, float]] = None) -> dict:
        """So sánh tất cả chiến lược phân bổ trên cùng một bộ dữ liệu.

        Returns:
            Dict {"markowitz": metrics, "risk_parity": metrics, "min_variance": metrics, ...}
        """
        strategies = {
            "equal_weight": self.equal_weight(
                returns_df.columns if isinstance(returns_df, pl.DataFrame) else list(returns_df.columns)
            ),
            "markowitz":    self.markowitz(returns_df),
            "risk_parity":  self.risk_parity(returns_df),
            "min_variance": self.min_variance(returns_df),
        }
        if scores:
            strategies["kelly_portfolio"] = self.kelly_portfolio(returns_df, scores)

        return {
            name: self.bao_cao_danh_muc(returns_df, w)
            for name, w in strategies.items()
        }

    def polars_cov_matrix(self, returns_df) -> dict:
        """Covariance matrix + annual volatilities."""
        symbols, _ = self._to_numpy(returns_df)
        cov        = self._polars_cov(returns_df)
        annual_vol = {s: round(float(np.sqrt(cov[i, i] * 252)), 4) for i, s in enumerate(symbols)}
        return {"cov_matrix": cov, "symbols": symbols, "annual_vol": annual_vol}

    # ─────────────────────────────────────────────────────────────────────────
    # 9. PPO RL OPTIMIZATION
    # ─────────────────────────────────────────────────────────────────────────

    def rl_optimize(self, returns_df, regime_arr: Optional[np.ndarray] = None) -> Dict[str, float]:
        """Tối ưu bằng PPO (RL). Fallback về Markowitz nếu chưa train."""
        symbols, _ = self._to_numpy(returns_df)
        if self._rl_model is None:
            print("⚠️ PPO chưa train. Dùng Markowitz thay thế.")
            return self.markowitz(returns_df)

        try:
            from processing.ml.toi_uu_danh_muc.rl_env import PortfolioEnv
            env = PortfolioEnv(returns_df, regime_arr=regime_arr)
            obs, _ = env.reset()
            action, _ = self._rl_model.predict(obs, deterministic=True)
            w = _softmax_np(action)
            return {s: round(float(wi), 4) for s, wi in zip(symbols, w)}
        except Exception as e:
            print(f"⚠️ PPO inference lỗi: {e}")
            return self.markowitz(returns_df)

    def train_rl(
        self,
        returns_df,
        regime_arr:  Optional[np.ndarray] = None,
        timesteps:   int   = 500_000,
        window:      int   = 60,
        tc_bps:      float = 5.0,
    ) -> None:
        """Huấn luyện PPO agent từ dữ liệu lịch sử.

        Args:
            returns_df:  DataFrame lịch sử daily returns
            regime_arr:  Mảng regime_id từ trang_thai_thi_truong_ml
            timesteps:   Số bước train (mặc định 500k)
        """
        try:
            from stable_baselines3 import PPO
            from stable_baselines3.common.env_checker import check_env
        except ImportError:
            raise ImportError("Cần cài: pip install stable-baselines3")

        from processing.ml.toi_uu_danh_muc.rl_env import PortfolioEnv

        env = PortfolioEnv(returns_df, regime_arr=regime_arr, window=window, tc_bps=tc_bps)
        model = PPO(
            "MlpPolicy", env,
            learning_rate=3e-4,
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            gamma=0.99,
            verbose=1,
        )
        model.learn(total_timesteps=timesteps)
        model.save(str(DATA_DIR / "ppo_model.zip"))
        self._rl_model = model
        print(f"✅ PPO train xong! Đã lưu → {DATA_DIR / 'ppo_model.zip'}")

    # ─────────────────────────────────────────────────────────────────────────
    # 10. HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def equal_weight(self, symbols: List[str]) -> Dict[str, float]:
        w = round(1 / len(symbols), 4)
        return {s: w for s in symbols}


def _softmax_np(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


__all__ = ["PortfolioOptimizer", "DATA_DIR", "DrawdownTracker"]
