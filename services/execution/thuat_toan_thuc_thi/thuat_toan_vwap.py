"""Thuật Toán Thực Thi VWAP (Volume-Weighted Average Price).

Chia lệnh lớn thành nhiều lệnh nhỏ, phân phối theo trọng số khối lượng
giao dịch thực tế trong kỳ, giúp giảm market impact và trượt giá.

So với TWAP (phân phối đều theo thời gian), VWAP thông minh hơn:
    - Giao dịch nhiều hơn trong giai đoạn khối lượng cao (mở cửa, đóng cửa)
    - Giao dịch ít hơn trong giai đoạn khối lượng thấp (giữa phiên)

Cách dùng:
    vwap = VWAPExecutor(total_quantity=10.0, num_slices=8)
    vwap.cap_nhat_khoi_luong(khoi_luong_nen=1500.0)
    lenh = vwap.lay_lenh_tiep_theo(gia_hien_tai=65000.0)
    if lenh:
        arm.execute_order(lenh)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("A10_VWAP")


@dataclass
class LenhVWAP:
    """Một lệnh con của thuật toán VWAP."""
    so_thu_tu: int
    khoi_luong: float
    gia_tham_chieu: float
    thoi_diem: float = field(default_factory=time.time)
    da_thuc_thi: bool = False


class VWAPExecutor:
    """Bộ thực thi lệnh theo thuật toán VWAP.

    Attributes:
        tong_khoi_luong: Tổng khối lượng cần mua/bán.
        so_luoi: Số lệnh con để chia nhỏ.
        symbol: Mã tài sản.
    """

    def __init__(
        self,
        tong_khoi_luong: float,
        so_luoi: int = 10,
        symbol: str = "",
        action: str = "BUY",
    ) -> None:
        if tong_khoi_luong <= 0:
            raise ValueError("tong_khoi_luong phải lớn hơn 0")
        if so_luoi < 1:
            raise ValueError("so_luoi phải >= 1")

        self.tong_khoi_luong = tong_khoi_luong
        self.so_luoi = so_luoi
        self.symbol = symbol
        self.action = action.upper()

        # Trạng thái nội bộ
        self._lich_su_khoi_luong: List[float] = []  # Khối lượng từng nến
        self._lenh_da_thuc_thi: List[LenhVWAP] = []
        self._khoi_luong_da_thuc_thi: float = 0.0
        self._slice_index: int = 0

        logger.info(
            "[VWAP] Khởi tạo: %s %s x %.4f (%d slices)",
            self.action, self.symbol, self.tong_khoi_luong, self.so_luoi,
        )

    # ------------------------------------------------------------------
    # Cập nhật dữ liệu thị trường
    # ------------------------------------------------------------------

    def cap_nhat_khoi_luong(self, khoi_luong_nen: float) -> None:
        """Gọi mỗi nến để cập nhật lịch sử khối lượng.

        Args:
            khoi_luong_nen: Khối lượng giao dịch của nến vừa đóng.
        """
        if khoi_luong_nen > 0:
            self._lich_su_khoi_luong.append(khoi_luong_nen)
            # Giới hạn lịch sử để tránh dùng dữ liệu quá cũ
            if len(self._lich_su_khoi_luong) > 100:
                self._lich_su_khoi_luong = self._lich_su_khoi_luong[-100:]

    # ------------------------------------------------------------------
    # Tính toán lệnh
    # ------------------------------------------------------------------

    def _tinh_trong_so_vwap(self) -> List[float]:
        """Tính trọng số VWAP cho từng slice dựa trên lịch sử khối lượng."""
        if not self._lich_su_khoi_luong:
            # Không có dữ liệu → phân phối đều như TWAP
            return [1.0 / self.so_luoi] * self.so_luoi

        tong = sum(self._lich_su_khoi_luong)
        if tong == 0:
            return [1.0 / self.so_luoi] * self.so_luoi

        # Lấy N mẫu cuối, phân phối theo trọng số
        n = min(len(self._lich_su_khoi_luong), self.so_luoi)
        mau = self._lich_su_khoi_luong[-n:]
        tong_mau = sum(mau)

        trong_so = [v / tong_mau for v in mau]

        # Nếu số mẫu < so_luoi, padding bằng trung bình
        if len(trong_so) < self.so_luoi:
            trung_binh = 1.0 / self.so_luoi
            while len(trong_so) < self.so_luoi:
                trong_so.append(trung_binh)
            # Chuẩn hoá lại
            tong_tw = sum(trong_so)
            trong_so = [w / tong_tw for w in trong_so]

        return trong_so

    def lay_lenh_tiep_theo(
        self,
        gia_hien_tai: float,
        gia_toi_thieu: Optional[float] = None,
        gia_toi_da: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Tạo lệnh con tiếp theo theo VWAP.

        Args:
            gia_hien_tai: Giá thị trường hiện tại.
            gia_toi_thieu: Giá sàn chấp nhận (chỉ dùng cho lệnh BUY).
            gia_toi_da: Giá trần chấp nhận (chỉ dùng cho lệnh BUY).

        Returns:
            Dict signal_data nếu còn lệnh, None nếu đã hoàn tất.
        """
        if self.hoan_tat:
            logger.info("[VWAP] Đã hoàn tất tất cả %d slices.", self.so_luoi)
            return None

        # Kiểm tra điều kiện giá
        if gia_toi_thieu is not None and gia_hien_tai < gia_toi_thieu:
            logger.debug("[VWAP] Bỏ qua slice — giá %.4f < min %.4f", gia_hien_tai, gia_toi_thieu)
            return None
        if gia_toi_da is not None and gia_hien_tai > gia_toi_da:
            logger.debug("[VWAP] Bỏ qua slice — giá %.4f > max %.4f", gia_hien_tai, gia_toi_da)
            return None

        trong_so = self._tinh_trong_so_vwap()
        khoi_luong_slice = self.tong_khoi_luong * trong_so[self._slice_index]

        # Điều chỉnh slice cuối để tránh lệch do làm tròn
        con_lai = self.tong_khoi_luong - self._khoi_luong_da_thuc_thi
        if self._slice_index == self.so_luoi - 1:
            khoi_luong_slice = con_lai
        else:
            khoi_luong_slice = min(khoi_luong_slice, con_lai)

        if khoi_luong_slice <= 0:
            self._slice_index += 1
            return None

        lenh = LenhVWAP(
            so_thu_tu=self._slice_index + 1,
            khoi_luong=round(khoi_luong_slice, 8),
            gia_tham_chieu=gia_hien_tai,
        )
        self._lenh_da_thuc_thi.append(lenh)
        self._khoi_luong_da_thuc_thi += khoi_luong_slice
        self._slice_index += 1

        signal = {
            "symbol": self.symbol,
            "action": self.action,
            "size": lenh.khoi_luong,
            "price": gia_hien_tai,
            "algo": "VWAP",
            "slice": f"{lenh.so_thu_tu}/{self.so_luoi}",
        }

        logger.info(
            "[VWAP] Slice %d/%d | %s %.8f %s @ %.4f",
            lenh.so_thu_tu, self.so_luoi, self.action, lenh.khoi_luong,
            self.symbol, gia_hien_tai,
        )
        return signal

    # ------------------------------------------------------------------
    # Trạng thái
    # ------------------------------------------------------------------

    @property
    def hoan_tat(self) -> bool:
        """True nếu đã thực thi hết tất cả slices."""
        return self._slice_index >= self.so_luoi

    @property
    def tien_do(self) -> float:
        """Tiến độ thực thi (0.0 → 1.0)."""
        if self.tong_khoi_luong == 0:
            return 1.0
        return min(self._khoi_luong_da_thuc_thi / self.tong_khoi_luong, 1.0)

    def lay_thong_ke(self) -> Dict[str, Any]:
        """Thống kê tổng quan quá trình thực thi."""
        return {
            "symbol": self.symbol,
            "action": self.action,
            "tong_khoi_luong": self.tong_khoi_luong,
            "da_thuc_thi": round(self._khoi_luong_da_thuc_thi, 8),
            "con_lai": round(self.tong_khoi_luong - self._khoi_luong_da_thuc_thi, 8),
            "tien_do_pct": round(self.tien_do * 100, 2),
            "so_slices_hoan_tat": self._slice_index,
            "tong_slices": self.so_luoi,
            "hoan_tat": self.hoan_tat,
        }


__all__ = ["VWAPExecutor", "LenhVWAP"]
