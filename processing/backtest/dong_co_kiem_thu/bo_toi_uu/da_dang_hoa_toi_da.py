"""Tối đa hóa tỷ lệ đa dạng hóa (Maximum Diversification Ratio).

Công thức: Tìm Max của (w' sigma) / sqrt(w' Sigma w).
Trong đó:
- ``sigma`` là vector độ lệch chuẩn (biến động) của từng tài sản riêng lẻ.
- ``Sigma`` là ma trận hiệp phương sai.
Chỉ số DR (Diversification Ratio) càng cao đồng nghĩa với việc danh mục
đạt được mức độ đa dạng hóa càng lớn trên mỗi đơn vị rủi ro chịu phải.
"""

from typing import Any, Dict, Union

import numpy as np
import polars as pl

from processing.backtest.dong_co_kiem_thu.bo_toi_uu.co_so import BaseOptimizer

# Hình phạt lớn dùng để ngăn SLSQP hội tụ về nghiệm suy biến (vol≈0)
_PENALTY = 1e6


class MaxDiversificationOptimizer(BaseOptimizer):
    """Tối đa hóa Tỷ lệ Đa dạng hóa (Dựa theo mô hình của Choueifaty & Coignard)."""

    def _calc_weights(self, ctx: Dict[str, Any]) -> np.ndarray:
        """Sử dụng thuật toán SLSQP để tìm tỷ trọng tối đa hóa DR."""
        from scipy.optimize import minimize

        cov = ctx["cov"]
        n = cov.shape[0]

        if n == 0:
            return self._equal_weight(0)

        # Tính vector độ lệch chuẩn (biến động) của các tài sản
        vols = np.sqrt(np.diag(cov))

        # Nếu có tài sản biến động gần như bằng 0, chia đều tỷ trọng
        if np.any(vols < 1e-12):
            return self._equal_weight(n)

        def neg_dr(w: np.ndarray) -> float:
            """Tính Tỷ lệ Đa dạng hóa ÂM (SLSQP minimize -> tìm min âm DR = max DR).

            ──────────────────────────────────────────────────────────────────
            FIX BUG 2 (nghiệm suy biến khi vol≈0):
              Trước đây: trả 0.0 khi port_vol < 1e-12.
              Vấn đề: DR = (w' sigma)/0 -> vô cực, nhưng khi trả 0.0, SLSQP
              thấy đây là một "minimum tốt" và có thể hội tụ về đó.
              Đúng: trả _PENALTY (+1e6) để phạt nặng, buộc optimizer tránh vùng này.
            ──────────────────────────────────────────────────────────────────
            """
            port_vol = np.sqrt(w @ cov @ w)

            if port_vol < 1e-12:
                return _PENALTY   # [FIX] Hình phạt lớn thay vì 0.0

            # DR = (Trung bình trọng số của biến động riêng lẻ) / Biến động tổng danh mục
            return -(w @ vols) / port_vol

        # Chạy bộ giải thuật SLSQP
        result = minimize(
            fun=neg_dr,
            x0=self._equal_weight(n),
            method="SLSQP",
            bounds=[(0.0, 1.0)] * n,
            constraints={"type": "eq", "fun": lambda w: w.sum() - 1.0},
            options={"maxiter": 200, "ftol": 1e-10},
        )

        if result.success:
            return self._normalize(result.x)

        return self._equal_weight(n)


def optimize(
    ret: pl.DataFrame,
    pos: pl.DataFrame,
    dates: Union[list, pl.Series],
    lookback: int = 60,
) -> pl.DataFrame:
    """Hàm gọi cấp module: Tái cân bằng danh mục theo phương pháp Đa dạng hóa tối đa.

    Args:
        ret: Bảng dữ liệu lợi nhuận lịch sử (Polars DataFrame).
        pos: Bảng tín hiệu vị thế ban đầu (Polars DataFrame).
        dates: Các mốc thời gian cần chạy tối ưu.
        lookback: Số lượng nến nhìn lại quá khứ để tính ma trận.

    Returns:
        Bảng tỷ trọng phân bổ vốn đã được tối ưu (Polars DataFrame).
    """
    return MaxDiversificationOptimizer(lookback=lookback).optimize(ret, pos, dates)