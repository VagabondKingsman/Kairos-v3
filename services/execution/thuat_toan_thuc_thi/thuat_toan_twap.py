"""TWAP Execution — Chia Nho Lenh Theo Thoi Gian.

Time-Weighted Average Price (TWAP):
Chia lenh lon thanh cac slice nho va dat trong khoang thoi gian deu nhau
de giam tac dong gia (market impact).

Cach dung:
    twap = ThuatToanTWAP(
        so_luong_tong=10.0,          # Tong so luong can mua/ban
        thoi_luong_giay=3600,        # Thuc hien trong 1 gio
        so_slice=12,                 # Chia lam 12 lenh (moi 5 phut)
    )

    while not twap.hoan_thanh:
        slice_info = twap.lay_slice_tiep_theo()
        if slice_info:
            # Dat lenh slice_info.so_luong
            gia_thuc_hien = dat_lenh(slice_info.so_luong)
            twap.xac_nhan_slice(slice_info.thu_tu, gia_thuc_hien)
        time.sleep(twap.khoang_cach_giay)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ThongTinSlice:
    """Thong tin mot slice TWAP.

    Attributes:
        thu_tu: So thu tu (0-based).
        so_luong: Koi luong can dat cho slice nay.
        thoi_diem_du_kien: Unix timestamp du kien dat lenh.
        da_thuc_hien: True sau khi da xac nhan.
        gia_thuc_hien: Gia thuc te da thanh cong (None neu chua).
    """
    thu_tu: int
    so_luong: float
    thoi_diem_du_kien: float
    da_thuc_hien: bool = False
    gia_thuc_hien: Optional[float] = None
    thoi_diem_thuc_te: Optional[float] = None


@dataclass
class KetQuaTWAP:
    """Ket qua tong ket sau khi hoan thanh TWAP.

    Attributes:
        hoan_thanh: True neu da dat du so luong.
        so_luong_tong: So luong tong can dat.
        so_luong_da_dat: So luong da dat thanh cong.
        so_luong_chua_dat: Phan con lai.
        gia_trung_binh: TWAP price trung binh.
        so_slice_thanh_cong: So slice da thuc hien.
        so_slice_that_bai: So slice bi loi.
        thoi_gian_thuc_hien_giay: Tong thoi gian thuc hien.
    """
    hoan_thanh: bool
    so_luong_tong: float
    so_luong_da_dat: float
    so_luong_chua_dat: float
    gia_trung_binh: float
    so_slice_thanh_cong: int
    so_slice_that_bai: int
    thoi_gian_thuc_hien_giay: float


# ---------------------------------------------------------------------------
# ThuatToanTWAP
# ---------------------------------------------------------------------------

class ThuatToanTWAP:
    """Thuat toan khop lenh TWAP — chia nho lenh theo thoi gian.

    Thread-safe. Ho tro dat lenh theo slot thoi gian deu nhau.
    Theo doi tien do va tinh gia trung binh (TWAP price).

    Attributes:
        so_luong_tong: Tong so luong can dat.
        thoi_luong_giay: Khoang thoi gian thuc hien (giay).
        so_slice: So luong slice chia nho.
    """

    def __init__(
        self,
        so_luong_tong: float,
        thoi_luong_giay: float = 3600.0,
        so_slice: int = 12,
        cho_phep_slice_lon_hon: bool = True,
    ) -> None:
        """
        Args:
            so_luong_tong: Tong so luong (co the la lot, BTC, share...).
            thoi_luong_giay: Thoi gian thuc hien TWAP (giay). Mac dinh 1 gio.
            so_slice: So luong slice. Mac dinh 12 (moi 5 phut/lan).
            cho_phep_slice_lon_hon: True = slice cuoi nhan phan du.
        """
        if so_luong_tong <= 0:
            raise ValueError(f"so_luong_tong phai > 0, nhan: {so_luong_tong}")
        if so_slice <= 0:
            raise ValueError(f"so_slice phai > 0, nhan: {so_slice}")

        self.so_luong_tong = so_luong_tong
        self.thoi_luong_giay = thoi_luong_giay
        self.so_slice = so_slice

        # Tinh kich thuoc moi slice
        _so_luong_co_ban = so_luong_tong / so_slice
        slices = [_so_luong_co_ban] * so_slice
        if cho_phep_slice_lon_hon:
            # Phan du (lam tron float) cho slice cuoi
            tong_phan_bo = sum(slices)
            slices[-1] += so_luong_tong - tong_phan_bo

        self._khoang_cach = thoi_luong_giay / so_slice
        self._bat_dau = time.time()

        # Tao danh sach slice
        self._slices: List[ThongTinSlice] = [
            ThongTinSlice(
                thu_tu=i,
                so_luong=round(slices[i], 8),
                thoi_diem_du_kien=self._bat_dau + i * self._khoang_cach,
            )
            for i in range(so_slice)
        ]

        self._chi_so_hien_tai = 0
        logger.info(
            "TWAP khoi tao: tong=%.4f so_slice=%d khoang_cach=%.1fs",
            so_luong_tong, so_slice, self._khoang_cach,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def khoang_cach_giay(self) -> float:
        """Khoang cach thoi gian giua cac slice (giay)."""
        return self._khoang_cach

    @property
    def hoan_thanh(self) -> bool:
        """True neu tat ca slice da duoc xu ly."""
        return self._chi_so_hien_tai >= self.so_slice

    @property
    def so_luong_da_dat(self) -> float:
        """Tong so luong da dat thanh cong."""
        return sum(
            s.so_luong for s in self._slices
            if s.da_thuc_hien and s.gia_thuc_hien is not None
        )

    @property
    def so_luong_chua_dat(self) -> float:
        return max(0.0, self.so_luong_tong - self.so_luong_da_dat)

    @property
    def tien_do_phan_tram(self) -> float:
        """Phan tram hoan thanh (0.0 - 1.0)."""
        if self.so_luong_tong <= 0:
            return 1.0
        return min(self.so_luong_da_dat / self.so_luong_tong, 1.0)

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def lay_slice_tiep_theo(self) -> Optional[ThongTinSlice]:
        """Lay thong tin slice can dat tiep theo.

        Tra ve None neu:
        - Da hoan thanh tat ca slice
        - Chua den thoi diem dat slice tiep theo

        Returns:
            ThongTinSlice can dat, hoac None.
        """
        if self.hoan_thanh:
            return None

        slice_hien_tai = self._slices[self._chi_so_hien_tai]

        # Chua den gio
        if time.time() < slice_hien_tai.thoi_diem_du_kien:
            return None

        return slice_hien_tai

    def xac_nhan_slice(
        self,
        thu_tu: int,
        gia_thuc_hien: float,
        so_luong_thuc: Optional[float] = None,
    ) -> bool:
        """Xac nhan mot slice da dat thanh cong.

        Args:
            thu_tu: Thu tu slice (0-based).
            gia_thuc_hien: Gia thuc te da khop.
            so_luong_thuc: So luong thuc te (neu khac so_luong ke hoach).

        Returns:
            True neu xac nhan thanh cong.
        """
        if thu_tu < 0 or thu_tu >= self.so_slice:
            return False

        s = self._slices[thu_tu]
        s.da_thuc_hien = True
        s.gia_thuc_hien = gia_thuc_hien
        s.thoi_diem_thuc_te = time.time()
        if so_luong_thuc is not None:
            s.so_luong = so_luong_thuc

        self._chi_so_hien_tai = max(self._chi_so_hien_tai, thu_tu + 1)

        logger.debug(
            "TWAP slice #%d xac nhan: so_luong=%.4f gia=%.4f tien_do=%.1f%%",
            thu_tu, s.so_luong, gia_thuc_hien, self.tien_do_phan_tram * 100,
        )
        return True

    def huy_slice(self, thu_tu: int, ly_do: str = "") -> bool:
        """Danh dau mot slice la that bai (skip).

        Args:
            thu_tu: Thu tu slice.
            ly_do: Ly do huy.

        Returns:
            True neu huy thanh cong.
        """
        if thu_tu < 0 or thu_tu >= self.so_slice:
            return False
        self._slices[thu_tu].da_thuc_hien = True
        # gia_thuc_hien = None → danh dau that bai
        self._chi_so_hien_tai = max(self._chi_so_hien_tai, thu_tu + 1)
        logger.warning("TWAP slice #%d bi huy: %s", thu_tu, ly_do)
        return True

    def tong_ket(self) -> KetQuaTWAP:
        """Tao bao cao ket qua TWAP sau khi hoan thanh."""
        slices_thanh_cong = [
            s for s in self._slices
            if s.da_thuc_hien and s.gia_thuc_hien is not None
        ]
        slices_that_bai = [
            s for s in self._slices
            if s.da_thuc_hien and s.gia_thuc_hien is None
        ]

        so_luong_da_dat = sum(s.so_luong for s in slices_thanh_cong)
        tong_gia_tri = sum(s.so_luong * s.gia_thuc_hien for s in slices_thanh_cong)
        gia_tb = tong_gia_tri / so_luong_da_dat if so_luong_da_dat > 0 else 0.0

        return KetQuaTWAP(
            hoan_thanh=self.hoan_thanh,
            so_luong_tong=self.so_luong_tong,
            so_luong_da_dat=so_luong_da_dat,
            so_luong_chua_dat=self.so_luong_chua_dat,
            gia_trung_binh=round(gia_tb, 6),
            so_slice_thanh_cong=len(slices_thanh_cong),
            so_slice_that_bai=len(slices_that_bai),
            thoi_gian_thuc_hien_giay=time.time() - self._bat_dau,
        )

    def lay_thong_tin(self) -> Dict[str, Any]:
        """Thong tin trang thai hien tai."""
        return {
            "so_luong_tong": self.so_luong_tong,
            "so_luong_da_dat": round(self.so_luong_da_dat, 8),
            "so_luong_chua_dat": round(self.so_luong_chua_dat, 8),
            "tien_do_phan_tram": round(self.tien_do_phan_tram * 100, 1),
            "slice_hien_tai": self._chi_so_hien_tai,
            "tong_slice": self.so_slice,
            "hoan_thanh": self.hoan_thanh,
            "khoang_cach_giay": self._khoang_cach,
        }
