"""Chong Truot Gia (Slippage Protection) — Kiem Tra Do Sau So Lenh.

Uoc tinh va kiem soat slippage truoc khi dat lenh lon:
1. Uoc tinh slippage dua tren orderbook depth
2. Kiem tra co du thanh khoan khong
3. Goi y chia nho lenh neu slippage qua cao

Cach dung:
    bao_ve = ChongTruotGia(nguong_slippage_pct=0.3)

    # Kiem tra truoc khi dat lenh
    ket_qua = bao_ve.kiem_tra(
        gia_mong_muon=65000.0,
        so_luong=1.5,         # 1.5 BTC
        chieu=1,              # 1=mua, -1=ban
        orderbook=orderbook,  # {"bids": [...], "asks": [...]}
    )

    if ket_qua.an_toan:
        dat_lenh(ket_qua.gia_thuc_hien_uoc_tinh, so_luong)
    elif ket_qua.nen_chia_nho:
        # Chia lam nhieu lenh nho hon
        for slice_size in ket_qua.phan_chia_de_xuat:
            dat_lenh(gia, slice_size)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class KetQuaKiemTraSlippage:
    """Ket qua kiem tra slippage.

    Attributes:
        an_toan: True neu slippage nam trong nguong chap nhan.
        slippage_pct: Slippage uoc tinh (%).
        gia_thuc_hien_uoc_tinh: Gia trung binh uoc tinh sau khi quet so lenh.
        tong_kha_dung: Tong so luong co the fill o nguong slippage.
        du_thanh_khoan: True neu orderbook co du so luong.
        nen_chia_nho: True neu nen chia lenh de giam impact.
        phan_chia_de_xuat: Danh sach kich thuoc slice de xuat.
        ly_do: Giai thich ket qua.
    """
    an_toan: bool
    slippage_pct: float
    gia_thuc_hien_uoc_tinh: float
    tong_kha_dung: float
    du_thanh_khoan: bool
    nen_chia_nho: bool = False
    phan_chia_de_xuat: List[float] = field(default_factory=list)
    ly_do: str = ""


# ---------------------------------------------------------------------------
# ChongTruotGia — Slippage Guard
# ---------------------------------------------------------------------------

class ChongTruotGia:
    """Kiem soat truot gia truoc khi dat lenh lon.

    Features:
    - Quet orderbook depth de uoc tinh gia trung binh fill
    - So sanh voi nguong slippage cho phep
    - Goi y chia nho lenh neu can
    - Simulate orderbook neu khong co du lieu thuc

    Attributes:
        nguong_slippage_pct: Nguong slippage toi da chap nhan (%).
        nguong_nen_chia_nho_pct: Nguong de khuyen nen chia nho lenh (%).
        so_slice_de_xuat: So phan chia khi goi y chia nho.
    """

    DEFAULT_NGUONG_PCT = 0.30      # 0.3%
    DEFAULT_NGUONG_CHIA_NHO = 0.10 # 0.1% → nen chia nho

    def __init__(
        self,
        nguong_slippage_pct: float = DEFAULT_NGUONG_PCT,
        nguong_nen_chia_nho_pct: float = DEFAULT_NGUONG_CHIA_NHO,
        so_slice_de_xuat: int = 4,
    ) -> None:
        self.nguong_slippage_pct = nguong_slippage_pct
        self.nguong_nen_chia_nho_pct = nguong_nen_chia_nho_pct
        self.so_slice_de_xuat = so_slice_de_xuat

    def kiem_tra(
        self,
        gia_mong_muon: float,
        so_luong: float,
        chieu: int,  # 1=mua (quet ask), -1=ban (quet bid)
        orderbook: Optional[Dict[str, List]] = None,
        bien_do_spread_pct: float = 0.05,
    ) -> KetQuaKiemTraSlippage:
        """Kiem tra slippage va do sau orderbook.

        Args:
            gia_mong_muon: Gia dat lenh mong muon.
            so_luong: So luong can dat (BTC, share, lot...).
            chieu: 1 = mua (quet asks), -1 = ban (quet bids).
            orderbook: Dict {"asks": [[gia, so_luong], ...], "bids": [[gia, so_luong], ...]}.
                       None → simulate orderbook don gian.
            bien_do_spread_pct: Spread uoc tinh khi khong co orderbook (%).

        Returns:
            KetQuaKiemTraSlippage.
        """
        if gia_mong_muon <= 0 or so_luong <= 0:
            return KetQuaKiemTraSlippage(
                an_toan=False,
                slippage_pct=0.0,
                gia_thuc_hien_uoc_tinh=gia_mong_muon,
                tong_kha_dung=0.0,
                du_thanh_khoan=False,
                ly_do="Gia hoac so luong khong hop le",
            )

        if orderbook:
            return self._kiem_tra_voi_orderbook(gia_mong_muon, so_luong, chieu, orderbook)
        else:
            return self._kiem_tra_khong_orderbook(gia_mong_muon, so_luong, bien_do_spread_pct)

    def _kiem_tra_voi_orderbook(
        self,
        gia_mong_muon: float,
        so_luong: float,
        chieu: int,
        orderbook: Dict[str, List],
    ) -> KetQuaKiemTraSlippage:
        """Quet qua orderbook de tinh slippage chinh xac."""
        side_key = "asks" if chieu == 1 else "bids"
        levels = orderbook.get(side_key, [])

        if not levels:
            return KetQuaKiemTraSlippage(
                an_toan=False,
                slippage_pct=99.0,
                gia_thuc_hien_uoc_tinh=gia_mong_muon,
                tong_kha_dung=0.0,
                du_thanh_khoan=False,
                ly_do=f"Orderbook trong ({side_key} = [])",
            )

        # Quet qua cac muc gia
        so_luong_con_lai = so_luong
        tong_gia_tri = 0.0
        tong_da_fill = 0.0

        for level in levels:
            gia_muc, kl_muc = float(level[0]), float(level[1])
            co_the_fill = min(kl_muc, so_luong_con_lai)
            tong_gia_tri += co_the_fill * gia_muc
            tong_da_fill += co_the_fill
            so_luong_con_lai -= co_the_fill
            if so_luong_con_lai <= 1e-10:
                break

        du_thanh_khoan = so_luong_con_lai <= 1e-10

        if tong_da_fill > 0:
            gia_tb_fill = tong_gia_tri / tong_da_fill
        else:
            gia_tb_fill = gia_mong_muon

        # Tinh slippage
        if chieu == 1:
            slippage_pct = (gia_tb_fill - gia_mong_muon) / gia_mong_muon * 100
        else:
            slippage_pct = (gia_mong_muon - gia_tb_fill) / gia_mong_muon * 100

        slippage_pct = abs(slippage_pct)

        return self._tao_ket_qua(
            an_toan=du_thanh_khoan and slippage_pct <= self.nguong_slippage_pct,
            slippage_pct=slippage_pct,
            gia_thuc_hien_uoc_tinh=gia_tb_fill,
            tong_kha_dung=tong_da_fill,
            du_thanh_khoan=du_thanh_khoan,
            so_luong_goc=so_luong,
        )

    def _kiem_tra_khong_orderbook(
        self,
        gia_mong_muon: float,
        so_luong: float,
        bien_do_spread_pct: float,
    ) -> KetQuaKiemTraSlippage:
        """Uoc tinh slippage don gian khi khong co orderbook."""
        # Uoc tinh: slippage tuong duong spread / 2
        slippage_pct = bien_do_spread_pct / 2.0
        gia_uoc_tinh = gia_mong_muon * (1 + slippage_pct / 100.0)

        return self._tao_ket_qua(
            an_toan=slippage_pct <= self.nguong_slippage_pct,
            slippage_pct=slippage_pct,
            gia_thuc_hien_uoc_tinh=gia_uoc_tinh,
            tong_kha_dung=so_luong,  # Gia su du thanh khoan
            du_thanh_khoan=True,
            so_luong_goc=so_luong,
            ly_do="Uoc tinh spread don gian (khong co orderbook)",
        )

    def _tao_ket_qua(
        self,
        an_toan: bool,
        slippage_pct: float,
        gia_thuc_hien_uoc_tinh: float,
        tong_kha_dung: float,
        du_thanh_khoan: bool,
        so_luong_goc: float,
        ly_do: str = "",
    ) -> KetQuaKiemTraSlippage:
        """Tao KetQuaKiemTraSlippage day du."""
        nen_chia_nho = slippage_pct > self.nguong_nen_chia_nho_pct

        phan_chia: List[float] = []
        if nen_chia_nho and so_luong_goc > 0:
            kich_thuoc_slice = so_luong_goc / self.so_slice_de_xuat
            phan_chia = [round(kich_thuoc_slice, 8)] * self.so_slice_de_xuat
            # Phan du cho slice cuoi
            tong_pb = sum(phan_chia)
            if abs(tong_pb - so_luong_goc) > 1e-10:
                phan_chia[-1] += so_luong_goc - tong_pb

        if not ly_do:
            if not du_thanh_khoan:
                ly_do = f"Khong du thanh khoan (chi co {tong_kha_dung:.4f}/{so_luong_goc:.4f})"
            elif not an_toan:
                ly_do = f"Slippage {slippage_pct:.3f}% > nguong {self.nguong_slippage_pct:.3f}%"
            else:
                ly_do = f"An toan: Slippage {slippage_pct:.3f}% <= {self.nguong_slippage_pct:.3f}%"

        return KetQuaKiemTraSlippage(
            an_toan=an_toan,
            slippage_pct=round(slippage_pct, 6),
            gia_thuc_hien_uoc_tinh=round(gia_thuc_hien_uoc_tinh, 6),
            tong_kha_dung=round(tong_kha_dung, 8),
            du_thanh_khoan=du_thanh_khoan,
            nen_chia_nho=nen_chia_nho,
            phan_chia_de_xuat=phan_chia,
            ly_do=ly_do,
        )

    def uoc_tinh_market_impact(
        self,
        adv_24h: float,
        so_luong: float,
        gia: float,
    ) -> Dict[str, float]:
        """Uoc tinh market impact theo mo hinh sqrt.

        Square-root model: impact = sigma * sqrt(Q/ADV)

        Args:
            adv_24h: Average Daily Volume (so luong, khong phai gia tri).
            so_luong: So luong can dat.
            gia: Gia hien tai.

        Returns:
            Dict: {"impact_pct", "gia_sau_impact", "nen_chia_nho"}
        """
        if adv_24h <= 0:
            return {"impact_pct": 0.0, "gia_sau_impact": gia, "nen_chia_nho": False}

        ty_le = so_luong / adv_24h
        # Sigma uoc tinh ~ 2% (co the tuy chinh theo lich su vol)
        sigma = 0.02
        impact_pct = sigma * (ty_le ** 0.5) * 100

        return {
            "impact_pct": round(impact_pct, 4),
            "gia_sau_impact": round(gia * (1 + impact_pct / 100), 6),
            "nen_chia_nho": impact_pct > self.nguong_nen_chia_nho_pct,
            "ty_le_adv": round(ty_le * 100, 4),
        }
