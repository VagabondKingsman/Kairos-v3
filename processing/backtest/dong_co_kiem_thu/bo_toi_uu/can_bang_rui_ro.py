"""Cân bằng rủi ro (Risk Parity): Cân bằng mức đóng góp rủi ro biên.

Thuật toán lặp tinh chỉnh để mức đóng góp rủi ro (w_i * MRC_i)
gần như bằng nhau giữa tất cả các tài sản trong danh mục.
"""

from typing import Any, Dict, Union

import numpy as np
import polars as pl

from processing.backtest.dong_co_kiem_thu.bo_toi_uu.co_so import BaseOptimizer


class RiskParityOptimizer(BaseOptimizer):
    """Khởi tạo tỷ trọng bằng nghịch đảo biến động (inverse-vol) + tinh chỉnh kiểu Newton (Spinu, 2013)."""

    def _calc_weights(self, ctx: Dict[str, Any]) -> np.ndarray:
        """Tính toán tỷ trọng sao cho mức đóng góp rủi ro (Risk Contribution) là bằng nhau."""
        cov = ctx["cov"]
        n = cov.shape[0]
        if n == 0:
            return self._equal_weight(0)

        # 1. Tính độ lệch chuẩn (biến động - volatility) của từng tài sản
        vols = np.sqrt(np.diag(cov))
        
        # Nếu có tài sản biến động gần như bằng 0 (lỗi dữ liệu hoặc quá tĩnh), chia đều tỷ trọng
        if np.any(vols < 1e-12):
            return self._equal_weight(n)

        # 2. Khởi tạo tỷ trọng ban đầu (seed) bằng nghịch đảo biến động
        inv_vol = 1.0 / vols
        w = inv_vol / inv_vol.sum()

        # 3. Lặp tối đa 5 lần để tinh chỉnh tỷ trọng (Newton-style refinement)
        for _ in range(5):
            # Tính biến động của toàn bộ danh mục (Portfolio Volatility)
            port_vol = np.sqrt(w @ cov @ w)
            if port_vol < 1e-12:
                break
            
            # Tính Rủi ro biên (Marginal Risk Contribution - MRC)
            mrc = (cov @ w) / port_vol
            
            # Tính Đóng góp rủi ro thực tế của từng tài sản (Risk Contribution - RC)
            rc = w * mrc
            
            # Mục tiêu: mỗi tài sản đóng góp 1/n tổng rủi ro của danh mục
            target = port_vol / n
            
            # Cập nhật tỷ trọng (thêm 1e-12 để tránh lỗi chia cho 0)
            w = w * (target / (rc + 1e-12))
            
            # Chuẩn hóa để tổng tỷ trọng luôn bằng 1.0 (100% vốn)
            w = w / w.sum()

        return w


def optimize(
    ret: pl.DataFrame,
    pos: pl.DataFrame,
    dates: Union[list, pl.Series],
    lookback: int = 60,
) -> pl.DataFrame:
    """Hàm gọi cấp module: Tính toán lại tỷ trọng vị thế theo phương pháp Cân bằng rủi ro.
    
    Args:
        ret: Bảng dữ liệu lợi nhuận của các tài sản (Polars DataFrame).
        pos: Bảng tỷ trọng/tín hiệu vị thế ban đầu thô (Polars DataFrame).
        dates: Danh sách hoặc Cột chứa các mốc thời gian cần tái cân bằng.
        lookback: Số lượng nến (kỳ) nhìn lại trong quá khứ để tính ma trận hiệp phương sai.
        
    Returns:
        Bảng tỷ trọng đã được tối ưu (Polars DataFrame).
    """
    return RiskParityOptimizer(lookback=lookback).optimize(ret, pos, dates)