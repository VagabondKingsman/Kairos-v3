"""Bộ tối ưu hóa Trung bình - Phương sai (Tối đa hóa Sharpe / Mean-Variance).

Giải bài toán Markowitz: Tìm tỷ trọng w sao cho Tỷ lệ Sharpe là lớn nhất.
Công thức: max (w'mu - r_f) / sqrt(w'Sigma w)
Ràng buộc: w >= 0 (Chỉ mua/Long-only), tổng(w) = 1 (Phân bổ 100% vốn).
"""

from typing import Any, Dict, List, Union

import numpy as np
import polars as pl

from processing.backtest.dong_co_kiem_thu.bo_toi_uu.co_so import BaseOptimizer

# Hình phạt lớn dùng để ngăn SLSQP hội tụ về nghiệm suy biến (vol≈0)
_PENALTY = 1e6


class MeanVarianceOptimizer(BaseOptimizer):
    """Tối đa hóa tỷ lệ Sharpe với ràng buộc chỉ mua (long-only) và tổng tỷ trọng bằng 1."""

    def __init__(self, lookback: int = 60, risk_free: float = 0.0, **kwargs: Any) -> None:
        """
        Args:
            lookback: Số nến nhìn lại trong quá khứ để tính toán biến động.
            risk_free: Mức lãi suất phi rủi ro (Ví dụ: Lãi suất trái phiếu chính phủ).
        """
        super().__init__(lookback=lookback, **kwargs)
        self.risk_free = risk_free

    def _build_context(
        self, window: pl.DataFrame, active: List[str]
    ) -> Union[Dict[str, Any], None]:
        """Tính toán vector kỳ vọng (mean) và ma trận hiệp phương sai (covariance matrix)."""
        arr = window.to_numpy()

        # 1. Tính vector lợi nhuận trung bình (Kỳ vọng - mu)
        mu = np.mean(arr, axis=0)

        # 2. Tính ma trận hiệp phương sai (Covariance - Sigma)
        if arr.shape[1] == 1:
            # Xử lý trường hợp danh mục chỉ có 1 tài sản
            cov = np.array([[np.var(arr[:, 0], ddof=1)]])
        else:
            # rowvar=False: mỗi cột là 1 biến số (tài sản)
            cov = np.cov(arr, rowvar=False)

        # Kiểm tra lỗi dữ liệu rỗng hoặc không hợp lệ (NaN)
        if np.isnan(cov).any() or np.isnan(mu).any():
            return None

        return {"cov": cov, "mu": mu}

    def _calc_weights(self, ctx: Dict[str, Any]) -> np.ndarray:
        """Sử dụng thuật toán SLSQP của SciPy để tìm tỷ trọng tối ưu hóa tỷ lệ Sharpe."""
        from scipy.optimize import minimize

        mu, cov = ctx["mu"], ctx["cov"]
        n = len(mu)
        if n == 0:
            return self._equal_weight(0)

        rf = self.risk_free

        def neg_sharpe(w: np.ndarray) -> float:
            """Tính Tỷ lệ Sharpe ÂM (SLSQP minimize -> ta đi tìm min của âm Sharpe).

            ──────────────────────────────────────────────────────────────────
            FIX BUG 2 (nghiệm suy biến khi vol≈0):
              Trước đây: trả 0.0 khi port_vol < 1e-12.
              Vấn đề: SLSQP tìm MIN; 0.0 < mọi neg_sharpe dương (chiến lược xấu)
              => optimizer BỊ HÚT về nghiệm port_vol≈0 thay vì tìm điểm tối ưu thực.
              Đúng: trả _PENALTY (+1e6) để phạt nặng, buộc optimizer tránh vùng này.
            ──────────────────────────────────────────────────────────────────
            """
            port_vol = np.sqrt(w @ cov @ w)

            if port_vol < 1e-12:
                return _PENALTY   # [FIX] Hình phạt lớn thay vì 0.0

            # Sharpe = (Lợi nhuận kỳ vọng - Lãi suất phi rủi ro) / Biến động
            return -(w @ mu - rf) / port_vol

        # Chạy bộ giải thuật SLSQP (Sequential Least SQuares Programming)
        result = minimize(
            fun=neg_sharpe,
            x0=self._equal_weight(n),
            method="SLSQP",
            bounds=[(0.0, 1.0)] * n,
            constraints={"type": "eq", "fun": lambda w: w.sum() - 1.0},
            options={"maxiter": 200, "ftol": 1e-10},
        )

        # Nếu tìm được điểm tối ưu, chuẩn hóa và trả về tỷ trọng
        if result.success:
            return self._normalize(result.x)

        # Nếu bộ giải thuật thất bại (do dữ liệu xấu), an toàn trở về chia đều tiền
        return self._equal_weight(n)


def optimize(
    ret: pl.DataFrame,
    pos: pl.DataFrame,
    dates: Union[list, pl.Series],
    lookback: int = 60,
    risk_free: float = 0.0,
) -> pl.DataFrame:
    """Hàm gọi cấp module: Tái cân bằng danh mục theo phương pháp Tối đa hóa Sharpe.

    Args:
        ret: Bảng dữ liệu lợi nhuận lịch sử (Polars DataFrame).
        pos: Bảng tín hiệu vị thế ban đầu (Polars DataFrame).
        dates: Các mốc thời gian cần chạy tối ưu.
        lookback: Số nến nhìn lại quá khứ để lấy mẫu (mặc định 60).
        risk_free: Lãi suất phi rủi ro (mặc định 0%).

    Returns:
        Bảng tỷ trọng phân bổ vốn đã được tối ưu (Polars DataFrame).
    """
    return MeanVarianceOptimizer(
        lookback=lookback, risk_free=risk_free
    ).optimize(ret, pos, dates)