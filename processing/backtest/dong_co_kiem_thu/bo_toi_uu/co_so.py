"""Lớp cơ sở dùng chung cho các bộ tối ưu hóa danh mục đầu tư.

Chịu trách nhiệm tiền xử lý dữ liệu, trượt cửa sổ thời gian để tính hiệp phương sai,
và chuẩn hóa tỷ trọng. Các lớp con (subclasses) sẽ tự triển khai logic tối ưu riêng
trong hàm ``_calc_weights``.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Union

import numpy as np
import polars as pl


class BaseOptimizer(ABC):
    """Bộ tối ưu hóa danh mục trừu tượng.

    Các lớp con bắt buộc phải ghi đè hàm ``_calc_weights``.
    Lớp cơ sở này sẽ tự động xử lý các rắc rối bao gồm:
    - Lọc ra các tài sản đang hoạt động (có tín hiệu giao dịch).
    - Cắt lát dữ liệu (rolling window) và kiểm tra độ dài dữ liệu hợp lệ.
    - Tính toán ma trận hiệp phương sai + kiểm tra giá trị lỗi (NaN).
    - Áp dụng tỷ trọng mới trong khi vẫn giữ nguyên chiều của tín hiệu ban đầu (Long/Short).

    Attributes:
        lookback: Số nến (kỳ) nhìn lại trong quá khứ để tính biến động / trung bình.
        min_data: Số nến tối thiểu cần có để bắt đầu tối ưu (mặc định: lookback // 2, ít nhất 5).
        params: Các tham số bổ sung dành cho các lớp con.
    """

    def __init__(self, lookback: int = 60, min_data: int = 0, **kwargs: Any) -> None:
        self.lookback = lookback
        # Nếu không truyền min_data, tính tự động: một nửa lookback nhưng không ít hơn 5
        self.min_data = min_data if min_data > 0 else max(lookback // 2, 5)
        self.params = kwargs

    # ------------------------------------------------------------------
    # Cổng giao tiếp chính (Public entry)
    # ------------------------------------------------------------------

    def optimize(
        self,
        ret: pl.DataFrame,
        pos: pl.DataFrame,
        dates: Union[list, pl.Series],
    ) -> pl.DataFrame:
        """Áp dụng thuật toán tối ưu lên bảng tỷ trọng các vị thế.

        Args:
            ret: Bảng dữ liệu lợi nhuận lịch sử (Polars DataFrame).
            pos: Tín hiệu vị thế thô ban đầu (Polars DataFrame).
            dates: Các mốc thời gian (aligned với bảng ``pos``).

        Returns:
            Bảng tỷ trọng phân bổ đã được điều chỉnh và tối ưu (Polars DataFrame).
        """
        # Lấy danh sách các mã (loại trừ cột thời gian nếu có)
        codes = [c for c in pos.columns if c != "timestamp"]

        # Nếu chỉ có 1 mã hoặc không có mã nào, không cần tối ưu phân bổ
        if len(codes) <= 1:
            return pos

        # Chuyển đổi sang NumPy để vòng lặp nội bộ đạt tốc độ O(1)
        pos_np = pos.select(codes).to_numpy()
        ret_np = ret.select(codes).to_numpy()

        # Tạo mảng kết quả (bắt đầu từ bản sao của tín hiệu gốc)
        result_np = pos_np.copy()

        # Lặp qua từng mốc thời gian (từng dòng)
        for i in range(pos.height):
            # ──────────────────────────────────────────────────────────────
            # FIX BUG 1 (look-ahead bias):
            #   pos[i] là vị thế quyết định tại close bar i-1, khớp lệnh
            #   mở bar i. Do đó cửa sổ lợi nhuận chỉ được dùng ret[0..i-1]
            #   (ret[i] là lợi nhuận CỦA bar i — chưa xảy ra lúc quyết định).
            #   Trước đây: ret_np[start_idx : i + 1]  <-- sai, gồm ret[i]
            #   Đúng:      ret_np[start_idx : i]       <-- chỉ dữ liệu đã biết
            # ──────────────────────────────────────────────────────────────
            start_idx = max(0, i - self.lookback)
            window_np = ret_np[start_idx : i, :]   # [FIX] i thay vì i+1

            # Cần đủ tối thiểu min_data nến; nếu chưa đủ thì giữ nguyên tín hiệu gốc
            if window_np.shape[0] < self.min_data:
                continue

            # 1. Tìm các tài sản đang "Active" (có tín hiệu mua/bán > 0)
            row_pos = pos_np[i]
            active_indices = [j for j, val in enumerate(row_pos) if abs(val) > 1e-9]

            if not active_indices:
                continue

            # 2. Giữ lại cột của các tài sản đang hoạt động trong cửa sổ
            window_active = window_np[:, active_indices]

            # Tạo một Polars DataFrame siêu nhỏ chứa dữ liệu cắt lát để truyền vào subclasses
            active_codes = [codes[j] for j in active_indices]
            window_pl = pl.DataFrame(window_active, schema=active_codes, orient="row")

            # 3. Tạo bối cảnh toán học (Vector trung bình, Ma trận Covariance...)
            ctx = self._build_context(window_pl, active_codes)
            if ctx is None:
                continue

            # 4. Gọi thuật toán lõi của các lớp con để giải tỷ trọng
            weights = self._calc_weights(ctx)
            if weights is None or len(weights) != len(active_indices):
                continue

            # 5. Lắp ghép tỷ trọng mới vào mảng kết quả, GIỮ NGUYÊN CHIỀU LỆNH (Long/Short)
            for idx_in_active, j in enumerate(active_indices):
                sign = np.sign(row_pos[j])
                result_np[i, j] = sign * weights[idx_in_active]

        # 6. Chuyển đổi mảng NumPy ngược lại thành chuẩn Polars DataFrame
        series_list = [pl.Series(name=c, values=result_np[:, j]) for j, c in enumerate(codes)]
        return pos.with_columns(series_list)

    # ------------------------------------------------------------------
    # Các hàm móc nối (Hooks)
    # ------------------------------------------------------------------

    def _build_context(
        self, window: pl.DataFrame, active: List[str]
    ) -> Union[Dict[str, Any], None]:
        """Tạo từ điển bối cảnh toán học truyền vào cho hàm ``_calc_weights``.

        Mặc định: Chỉ tính Ma trận hiệp phương sai (Covariance Matrix).
        Các lớp con có thể ghi đè hàm này để bổ sung thêm Trung bình (mu), biến động (vol)...
        Trả về None nếu dữ liệu bị lỗi để bỏ qua mốc thời gian đó.

        Args:
            window: Cửa sổ dữ liệu lợi nhuận của các tài sản đang hoạt động.
            active: Danh sách mã tài sản.

        Returns:
            Từ điển chứa ít nhất khóa ``cov``, hoặc None.
        """
        arr = window.to_numpy()

        # Tính hiệp phương sai siêu tốc bằng NumPy
        if arr.shape[1] == 1:
            cov = np.array([[np.var(arr[:, 0], ddof=1)]])
        else:
            cov = np.cov(arr, rowvar=False)

        if np.isnan(cov).any():
            return None

        return {"cov": cov}

    # ------------------------------------------------------------------
    # Giao diện bắt buộc cho Lớp con (Subclass API)
    # ------------------------------------------------------------------

    @abstractmethod
    def _calc_weights(self, ctx: Dict[str, Any]) -> np.ndarray:
        """Tính toán tỷ trọng mục tiêu dựa trên bối cảnh.

        Args:
            ctx: Từ điển nhận được từ hàm ``_build_context``.

        Returns:
            Vector tỷ trọng (n,) có tổng bằng 1.
        """
        pass

    # ------------------------------------------------------------------
    # Tiện ích (Utilities)
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(w: np.ndarray) -> np.ndarray:
        """Chuẩn hóa mảng tỷ trọng sao cho không có số âm và tổng luôn bằng 1."""
        w = np.maximum(w, 0.0)
        s = w.sum()
        if s > 1e-12:
            return w / s
        return np.ones(len(w)) / len(w)

    @staticmethod
    def _equal_weight(n: int) -> np.ndarray:
        """Tạo mảng tỷ trọng chia đều cho n tài sản."""
        if n == 0:
            return np.array([])
        return np.ones(n) / n