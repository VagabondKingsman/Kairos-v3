"""Phân bổ vốn theo biến động tương đương (Nghịch đảo biến động / Equal-Volatility).

Mô hình này cấp tỷ trọng cao hơn cho các tài sản có biến động (rủi ro) thấp.
Mục tiêu là để mỗi tài sản trong danh mục đóng góp một mức độ biến động (volatility)
tương đương nhau vào tổng rủi ro của toàn bộ danh mục.
"""

from typing import Any, Dict, List, Union

import numpy as np
import polars as pl

from processing.backtest.dong_co_kiem_thu.bo_toi_uu.co_so import BaseOptimizer


class EqualVolatilityOptimizer(BaseOptimizer):
    """Tối ưu tỷ trọng dựa trên nghịch đảo biến động (không cần ma trận hiệp phương sai đầy đủ)."""

    def _build_context(
        self, window: pl.DataFrame, active: List[str]
    ) -> Union[Dict[str, Any], None]:
        """Tính toán độ lệch chuẩn (biến động) xoay vòng cho từng tài sản.

        Args:
            window: Bảng dữ liệu lợi nhuận trong khung thời gian nhìn lại (Polars).
            active: Danh sách mã các tài sản đang có tín hiệu giao dịch.

        Returns:
            Từ điển chứa mảng độ lệch chuẩn ``vols`` và ``valid_mask`` hoặc None nếu
            không còn tài sản nào hợp lệ sau khi lọc.
        """
        arr = window.select(active).to_numpy()

        # Tính độ lệch chuẩn mẫu (sample standard deviation, ddof=1 giống Pandas mặc định)
        vols = np.std(arr, axis=0, ddof=1)

        # Kiểm tra NaN
        if np.isnan(vols).any():
            return None

        # ──────────────────────────────────────────────────────────────────
        # FIX BUG 3 (bỏ qua toàn bar):
        #   Trước đây: nếu ANY asset vol≈0 -> return None -> mất phân bổ
        #   cho TẤT CẢ tài sản trong bar đó.
        #   Đúng: chỉ loại asset vol≈0, tính tỷ trọng cho phần còn lại.
        #   Ví dụ: vols=[0.01, 1e-15, 0.015] -> loại asset 1, chia vốn cho
        #   asset 0 và 2 với inv_vol weighting.
        # ──────────────────────────────────────────────────────────────────
        valid_mask = vols >= 1e-12

        # Nếu không còn tài sản nào hợp lệ (tất cả đều vol≈0), bỏ qua bar này
        if not valid_mask.any():
            return None

        return {"vols": vols, "valid_mask": valid_mask}

    def _calc_weights(self, ctx: Dict[str, Any]) -> np.ndarray:
        """Tính toán tỷ trọng dựa trên nghịch đảo của biến động.

        Tài sản có vol≈0 nhận tỷ trọng bằng 0; phần còn lại được chuẩn hóa lại
        để tổng luôn bằng 1.
        """
        vols = ctx["vols"]
        valid_mask = ctx["valid_mask"]
        n = len(vols)

        # Khởi tạo mảng tỷ trọng bằng 0 cho tất cả
        weights = np.zeros(n)

        # Tính nghịch đảo biến động chỉ cho các tài sản hợp lệ
        inv_vol = np.where(valid_mask, 1.0 / np.where(valid_mask, vols, 1.0), 0.0)

        # Chuẩn hóa để tổng tỷ trọng của các tài sản hợp lệ luôn bằng 1.0 (100% vốn)
        total = inv_vol.sum()
        if total > 1e-12:
            weights = inv_vol / total

        return weights


def optimize(
    ret: pl.DataFrame,
    pos: pl.DataFrame,
    dates: Union[list, pl.Series],
    lookback: int = 60,
) -> pl.DataFrame:
    """Hàm gọi cấp module: Tái cân bằng danh mục theo phương pháp Nghịch đảo biến động.

    Args:
        ret: Bảng dữ liệu lợi nhuận lịch sử (Polars DataFrame).
        pos: Bảng tín hiệu vị thế ban đầu (Polars DataFrame).
        dates: Các mốc thời gian cần chạy tối ưu tỷ trọng.
        lookback: Số lượng nến nhìn lại quá khứ để đo lường biến động.

    Returns:
        Bảng tỷ trọng phân bổ vốn đã được tinh chỉnh (Polars DataFrame).
    """
    return EqualVolatilityOptimizer(lookback=lookback).optimize(ret, pos, dates)