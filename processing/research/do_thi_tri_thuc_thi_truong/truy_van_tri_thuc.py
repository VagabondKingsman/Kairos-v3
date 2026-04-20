"""Truy Van Tri Thuc Thi Truong — Market Knowledge Graph Query Engine.

Quan ly va truy van do thi quan he giua cac tai san tai chinh.
Cho phep AI Agent:
    - Tim tai san tuong quan cao voi mot ticker
    - Giai thich bien dong gia dua tren quan he thi truong
    - Tim tai san theo chu de kinh te (lam phat, lai suat, USD...)

Kien truc:
    - ``KhoTriThuc``: Load/save quan he tu JSON, xay dung in-memory graph
    - ``CongCuTriThucTTiTruong``: Expose ham truy van nhu AI Tool
    - ``du_lieu_quan_he.json``: Du lieu quan he mac dinh (seed data)

Cach dung (trong ReAct loop):
    # Agent goi tool
    result = tool.execute(
        hanh_dong="tim_tai_san_tuong_quan",
        ticker="BTC-USDT",
        nguong=0.7,
    )

    result = tool.execute(
        hanh_dong="tim_theo_chu_de",
        chu_de="lam phat",
    )
"""

from __future__ import annotations

import json
import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from processing.research.cong_cu_ai.cong_cu_co_so import CongCuCoSo

logger = logging.getLogger(__name__)

_DIR = Path(__file__).resolve().parent
_FILE_DU_LIEU = _DIR / "du_lieu_quan_he.json"

# Du lieu quan he mac dinh (khi chua co du_lieu_quan_he.json)
_DU_LIEU_MAC_DINH: Dict[str, Any] = {
    "phien_ban": "1.0",
    "mo_ta": "Ban do quan he tai san Kairos — seed data",
    "quan_he": [
        # === Crypto core ===
        {"tu": "BTC-USDT", "den": "ETH-USDT",     "he_so": 0.85, "loai": "tuong_quan", "chu_de": ["crypto", "risk-on"]},
        {"tu": "BTC-USDT", "den": "GOLD-USD",      "he_so": 0.55, "loai": "tuong_quan", "chu_de": ["tru_gia_tri", "lam_phat"]},
        {"tu": "BTC-USDT", "den": "DXY",            "he_so": -0.65, "loai": "tuong_quan", "chu_de": ["usd", "vi_mo"]},
        {"tu": "BTC-USDT", "den": "SPX",            "he_so": 0.60, "loai": "tuong_quan", "chu_de": ["risk-on", "vi_mo"]},
        {"tu": "ETH-USDT", "den": "SOL-USDT",      "he_so": 0.80, "loai": "tuong_quan", "chu_de": ["crypto", "layer1"]},
        {"tu": "ETH-USDT", "den": "BNB-USDT",      "he_so": 0.75, "loai": "tuong_quan", "chu_de": ["crypto", "exchange_token"]},

        # === Macro & Rates ===
        {"tu": "DXY",       "den": "GOLD-USD",      "he_so": -0.70, "loai": "tuong_quan", "chu_de": ["usd", "lam_phat", "vi_mo"]},
        {"tu": "DXY",       "den": "EUR-USD",        "he_so": -0.90, "loai": "tuong_quan", "chu_de": ["forex", "vi_mo"]},
        {"tu": "FED_RATE",  "den": "DXY",            "he_so": 0.60, "loai": "nguyen_nhan", "chu_de": ["lai_suat", "vi_mo"]},
        {"tu": "FED_RATE",  "den": "GOLD-USD",       "he_so": -0.55, "loai": "nguyen_nhan", "chu_de": ["lai_suat", "lam_phat"]},
        {"tu": "FED_RATE",  "den": "BTC-USDT",       "he_so": -0.50, "loai": "nguyen_nhan", "chu_de": ["lai_suat", "crypto"]},
        {"tu": "CPI_US",    "den": "GOLD-USD",       "he_so": 0.65, "loai": "nguyen_nhan", "chu_de": ["lam_phat", "vi_mo"]},
        {"tu": "CPI_US",    "den": "FED_RATE",       "he_so": 0.70, "loai": "nguyen_nhan", "chu_de": ["lam_phat", "lai_suat"]},

        # === Equities ===
        {"tu": "SPX",       "den": "NVDA",           "he_so": 0.75, "loai": "tuong_quan", "chu_de": ["co_phieu", "tech"]},
        {"tu": "SPX",       "den": "AAPL",           "he_so": 0.80, "loai": "tuong_quan", "chu_de": ["co_phieu", "tech"]},
        {"tu": "VN30",      "den": "VCB",            "he_so": 0.78, "loai": "tuong_quan", "chu_de": ["co_phieu", "viet_nam", "ngan_hang"]},
        {"tu": "VN30",      "den": "VHM",            "he_so": 0.70, "loai": "tuong_quan", "chu_de": ["co_phieu", "viet_nam", "bat_dong_san"]},
        {"tu": "VN30",      "den": "DXY",            "he_so": -0.45, "loai": "tuong_quan", "chu_de": ["usd", "viet_nam"]},

        # === Commodities ===
        {"tu": "OIL-WTI",  "den": "XLE",            "he_so": 0.88, "loai": "tuong_quan", "chu_de": ["hang_hoa", "nang_luong"]},
        {"tu": "OIL-WTI",  "den": "CPI_US",         "he_so": 0.60, "loai": "nguyen_nhan", "chu_de": ["hang_hoa", "lam_phat"]},
        {"tu": "COPPER",    "den": "SPX",            "he_so": 0.65, "loai": "tuong_quan", "chu_de": ["hang_hoa", "tang_truong"]},

        # === Stablecoin & Onchain ===
        {"tu": "USDT_DOM",  "den": "BTC-USDT",      "he_so": -0.75, "loai": "tuong_quan", "chu_de": ["crypto", "tam_ly_thi_truong"]},
        {"tu": "FUNDING",   "den": "BTC-USDT",       "he_so": 0.55, "loai": "nguyen_nhan", "chu_de": ["crypto", "derivatives"]},
    ],
    "chu_de_mo_ta": {
        "crypto":           "Tai san tien ma hoa",
        "risk-on":          "Tai san tang khi thi truong risk appetite cao",
        "usd":              "Lien quan den suc manh dong USD",
        "lam_phat":         "Anh huong boi du lieu lam phat (CPI, PPI)",
        "lai_suat":         "Anh huong boi chinh sach lai suat (FED, ECB)",
        "vi_mo":            "Yeu to kinh te vi mo toan cau",
        "co_phieu":         "Thi truong co phieu",
        "hang_hoa":         "Hang hoa co ban (vang, dau, dong...)",
        "viet_nam":         "Thi truong Viet Nam",
        "tam_ly_thi_truong":"Sentiment va cau truc thi truong",
        "derivatives":      "Thi truong phai sinh (futures, options)",
        "tech":             "Co phieu cong nghe",
        "ngan_hang":        "Co phieu ngan hang",
        "bat_dong_san":     "Co phieu bat dong san",
        "layer1":           "Blockchain layer 1",
        "forex":            "Thi truong ngoai hoi",
        "tru_gia_tri":      "Tai san luu tru gia tri (SoV)",
        "tang_truong":      "Chi bao tang truong kinh te",
        "nang_luong":       "Nang luong (dau, khi dot)",
        "exchange_token":   "Token san giao dich",
    },
}


# ---------------------------------------------------------------------------
# KhoTriThuc — In-Memory Graph
# ---------------------------------------------------------------------------

@dataclass
class QuanHeTaiSan:
    """Mot canh trong do thi quan he.

    Attributes:
        tu: Ticker nguon.
        den: Ticker dich.
        he_so: He so tuong quan (-1.0 den 1.0). Am = dao chieu.
        loai: Loai quan he ('tuong_quan', 'nguyen_nhan', 'thay_the').
        chu_de: Danh sach chu de macro lien quan.
    """

    tu: str
    den: str
    he_so: float
    loai: str = "tuong_quan"
    chu_de: List[str] = field(default_factory=list)

    @property
    def la_tuong_quan_duong(self) -> bool:
        return self.he_so > 0

    @property
    def do_manh(self) -> str:
        abs_h = abs(self.he_so)
        if abs_h >= 0.8:
            return "rat_cao"
        elif abs_h >= 0.6:
            return "cao"
        elif abs_h >= 0.4:
            return "trung_binh"
        else:
            return "yeu"


class KhoTriThuc:
    """Kho tri thuc thi truong — quan ly do thi quan he tai san.

    Load/save tu du_lieu_quan_he.json. Cung cap cac phuong phap
    truy van hieu qua.

    Cach dung:
        kho = KhoTriThuc()
        ket_qua = kho.tim_tuong_quan("BTC-USDT", nguong=0.6)
        theo_chu_de = kho.tim_theo_chu_de("lam_phat")
    """

    def __init__(self, file_du_lieu: Optional[Path] = None) -> None:
        self._file = file_du_lieu or _FILE_DU_LIEU
        self._danh_sach: List[QuanHeTaiSan] = []
        self._graph: Dict[str, List[QuanHeTaiSan]] = defaultdict(list)
        self._chu_de_mo_ta: Dict[str, str] = {}
        self._tai_du_lieu()

    def _tai_du_lieu(self) -> None:
        """Tai du lieu tu JSON hoac dung seed data."""
        if self._file.exists():
            try:
                raw = json.loads(self._file.read_text(encoding="utf-8"))
                logger.info("KhoTriThuc: tai tu %s", self._file)
            except Exception as exc:
                logger.warning("Loi tai du_lieu_quan_he.json: %s — dung seed data", exc)
                raw = _DU_LIEU_MAC_DINH
        else:
            logger.info("KhoTriThuc: khong tim thay file, dung seed data va luu lai")
            raw = _DU_LIEU_MAC_DINH
            self._luu_du_lieu(raw)

        self._chu_de_mo_ta = raw.get("chu_de_mo_ta", {})
        for item in raw.get("quan_he", []):
            qh = QuanHeTaiSan(
                tu=item["tu"],
                den=item["den"],
                he_so=float(item.get("he_so", 0.0)),
                loai=item.get("loai", "tuong_quan"),
                chu_de=item.get("chu_de", []),
            )
            self._danh_sach.append(qh)
            # Do thi hai chieu
            self._graph[qh.tu].append(qh)
            # Canh nguoc (dao chieu he_so)
            qh_nguoc = QuanHeTaiSan(
                tu=qh.den, den=qh.tu,
                he_so=qh.he_so,
                loai=qh.loai,
                chu_de=qh.chu_de,
            )
            self._graph[qh.den].append(qh_nguoc)

        logger.info("KhoTriThuc: da tai %d quan he, %d nodes", len(self._danh_sach), len(self._graph))

    def _luu_du_lieu(self, raw: Dict) -> None:
        """Luu seed data ra file JSON."""
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            self._file.write_text(
                json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as exc:
            logger.warning("Khong the luu du_lieu_quan_he.json: %s", exc)

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def tim_tuong_quan(
        self,
        ticker: str,
        nguong: float = 0.5,
        loai: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Tim tat ca tai san co quan he voi ticker.

        Args:
            ticker: Ticker can tim (VD: "BTC-USDT", "GOLD-USD").
            nguong: He so tuong quan toi thieu (gia tri tuyet doi).
            loai: Loc theo loai quan he ('tuong_quan', 'nguyen_nhan', ...).

        Returns:
            Danh sach dict ket qua, sap xep giam dan theo |he_so|.
        """
        ket_qua = []
        for qh in self._graph.get(ticker.upper(), []):
            if abs(qh.he_so) >= nguong:
                if loai and qh.loai != loai:
                    continue
                ket_qua.append({
                    "tai_san": qh.den,
                    "he_so": round(qh.he_so, 3),
                    "loai": qh.loai,
                    "do_manh": qh.do_manh,
                    "huong": "cung_chieu" if qh.he_so > 0 else "nguoc_chieu",
                    "chu_de": qh.chu_de,
                })
        ket_qua.sort(key=lambda x: abs(x["he_so"]), reverse=True)
        return ket_qua

    def tim_theo_chu_de(self, chu_de: str) -> List[Dict[str, Any]]:
        """Tim tat ca cap tai san co lien quan den mot chu de kinh te.

        Args:
            chu_de: Chu de can tim (VD: "lam_phat", "lai_suat", "crypto").
                    Tim kiem khong phan biet hoa thuong va cho phep tu khoa ngan.

        Returns:
            Danh sach quan he phu hop, khong trung lap.
        """
        chu_de_lower = chu_de.lower().replace(" ", "_")
        ket_qua = []
        da_them = set()

        for qh in self._danh_sach:
            match = any(
                chu_de_lower in c.lower() or c.lower() in chu_de_lower
                for c in qh.chu_de
            )
            if match:
                key = f"{qh.tu}|{qh.den}"
                if key not in da_them:
                    da_them.add(key)
                    ket_qua.append({
                        "tu": qh.tu,
                        "den": qh.den,
                        "he_so": round(qh.he_so, 3),
                        "loai": qh.loai,
                        "chu_de_khop": [c for c in qh.chu_de if chu_de_lower in c.lower() or c.lower() in chu_de_lower],
                    })

        ket_qua.sort(key=lambda x: abs(x["he_so"]), reverse=True)
        return ket_qua

    def giai_thich_bien_dong(self, ticker: str, bieu_hien: str = "") -> Dict[str, Any]:
        """Giai thich bien dong cua mot tai san dua tren do thi quan he.

        Args:
            ticker: Tai san can giai thich.
            bieu_hien: Mo ta bieu hien ("tang manh", "giam", "bien dong cao"...).

        Returns:
            Dict chua phan tich: nguyen_nhan_co_the, tai_san_anh_huong, chu_de_lien_quan.
        """
        ticker_up = ticker.upper()
        tuong_quan = self.tim_tuong_quan(ticker_up, nguong=0.4)

        # Tim nguyen nhan co the
        nguyen_nhan = [r for r in tuong_quan if r["loai"] == "nguyen_nhan"]
        # Tim tai san se bi anh huong theo
        bi_anh_huong = []
        for qh in self._danh_sach:
            if qh.tu == ticker_up and abs(qh.he_so) >= 0.5:
                bi_anh_huong.append({
                    "tai_san": qh.den,
                    "he_so": round(qh.he_so, 3),
                    "huong": "cung_chieu" if qh.he_so > 0 else "nguoc_chieu",
                })

        # Tong hop chu de lien quan
        tat_ca_chu_de: Dict[str, int] = defaultdict(int)
        for r in tuong_quan:
            for c in r.get("chu_de", []):
                tat_ca_chu_de[c] += 1
        chu_de_chinh = sorted(tat_ca_chu_de.items(), key=lambda x: x[1], reverse=True)[:5]

        mo_ta_bieu_hien = f"bieu hien '{bieu_hien}'" if bieu_hien else "bien dong"
        return {
            "ticker": ticker_up,
            "bieu_hien": bieu_hien,
            "tom_tat": (
                f"{ticker_up} {mo_ta_bieu_hien} co the lien quan den "
                f"{len(nguyen_nhan)} nguyen nhan chinh va anh huong "
                f"{len(bi_anh_huong)} tai san khac."
            ),
            "nguyen_nhan_co_the": nguyen_nhan[:5],
            "tai_san_bi_anh_huong": bi_anh_huong[:5],
            "chu_de_chinh": [{"chu_de": c, "so_lan": n, "mo_ta": self._chu_de_mo_ta.get(c, "")} for c, n in chu_de_chinh],
            "luu_y": "Cac quan he nay la thong ke lich su, khong dam bao quan he nhan qua trong tuong lai.",
        }

    def them_quan_he(
        self,
        tu: str, den: str,
        he_so: float,
        loai: str = "tuong_quan",
        chu_de: Optional[List[str]] = None,
        luu: bool = True,
    ) -> QuanHeTaiSan:
        """Them mot quan he moi vao do thi va luu lai.

        Args:
            tu: Ticker nguon.
            den: Ticker dich.
            he_so: He so tuong quan (-1.0 den 1.0).
            loai: Loai quan he.
            chu_de: Danh sach chu de.
            luu: True de luu ra file JSON.

        Returns:
            QuanHeTaiSan vua them.
        """
        he_so_clip = max(-1.0, min(1.0, he_so))
        qh = QuanHeTaiSan(
            tu=tu.upper(), den=den.upper(),
            he_so=he_so_clip, loai=loai,
            chu_de=chu_de or [],
        )
        self._danh_sach.append(qh)
        self._graph[qh.tu].append(qh)
        qh_nguoc = QuanHeTaiSan(tu=qh.den, den=qh.tu, he_so=qh.he_so, loai=qh.loai, chu_de=qh.chu_de)
        self._graph[qh.den].append(qh_nguoc)

        if luu:
            self._luu_het()
        return qh

    def _luu_het(self) -> None:
        """Serialize toan bo do thi ra JSON."""
        raw = {
            "phien_ban": "1.0",
            "mo_ta": "Ban do quan he tai san Kairos",
            "chu_de_mo_ta": self._chu_de_mo_ta,
            "quan_he": [
                {
                    "tu": qh.tu, "den": qh.den,
                    "he_so": qh.he_so, "loai": qh.loai,
                    "chu_de": qh.chu_de,
                }
                for qh in self._danh_sach
            ],
        }
        self._luu_du_lieu(raw)

    def lay_thong_ke(self) -> Dict[str, Any]:
        """Thong ke tong quan ve do thi tri thuc."""
        return {
            "tong_quan_he": len(self._danh_sach),
            "tong_nodes": len(self._graph),
            "danh_sach_ticker": sorted(self._graph.keys()),
            "so_chu_de": len(self._chu_de_mo_ta),
            "file_du_lieu": str(self._file),
        }


# ---------------------------------------------------------------------------
# AI Tool — CongCuTriThucTTiTruong
# ---------------------------------------------------------------------------

class CongCuTriThucTTiTruong(CongCuCoSo):
    """Truy van Do Thi Tri Thuc Thi Truong.

    Cung cap 3 hanh dong:
    1. ``tim_tai_san_tuong_quan``: Tim tai san co quan he voi mot ticker
    2. ``giai_thich_bien_dong``: Giai thich tai sao mot tai san bien dong
    3. ``tim_theo_chu_de``: Tim tai san lien quan den chu de kinh te

    Thong tin co the tra loi:
    - "BTC tang manh vi sao?" → giai_thich_bien_dong("BTC-USDT", "tang manh")
    - "Tai san nao tuong quan voi BTC?" → tim_tai_san_tuong_quan("BTC-USDT")
    - "Tai san nao bi anh huong khi lam phat tang?" → tim_theo_chu_de("lam_phat")
    """

    name = "truy_van_tri_thuc"
    description = (
        "Truy van do thi tri thuc thi truong de hieu quan he giua cac tai san. "
        "Co 3 hanh dong: "
        "(1) 'tim_tai_san_tuong_quan': tim tai san co tuong quan cao voi mot ticker "
        "(2) 'giai_thich_bien_dong': giai thich ly do bien dong cua mot tai san "
        "(3) 'tim_theo_chu_de': tim tai san lien quan den chu de kinh te (lam phat, lai suat, usd...)"
    )
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "hanh_dong": {
                "type": "string",
                "enum": ["tim_tai_san_tuong_quan", "giai_thich_bien_dong", "tim_theo_chu_de"],
                "description": "Loai truy van can thuc hien",
            },
            "ticker": {
                "type": "string",
                "description": "Ticker tai san (VD: 'BTC-USDT', 'GOLD-USD', 'VN30'). Dung cho tim_tai_san_tuong_quan va giai_thich_bien_dong.",
            },
            "nguong": {
                "type": "number",
                "description": "He so tuong quan toi thieu (0.0-1.0, mac dinh: 0.5). Chi dung cho tim_tai_san_tuong_quan.",
                "default": 0.5,
            },
            "bieu_hien": {
                "type": "string",
                "description": "Mo ta bieu hien bien dong (VD: 'tang manh', 'giam dot ngot'). Dung cho giai_thich_bien_dong.",
                "default": "",
            },
            "chu_de": {
                "type": "string",
                "description": "Chu de kinh te can tim (VD: 'lam_phat', 'lai_suat', 'crypto', 'usd'). Dung cho tim_theo_chu_de.",
            },
        },
        "required": ["hanh_dong"],
    }
    repeatable = True

    def __init__(self) -> None:
        self._kho: Optional[KhoTriThuc] = None

    def _lay_kho(self) -> KhoTriThuc:
        if self._kho is None:
            self._kho = KhoTriThuc()
        return self._kho

    def execute(
        self,
        hanh_dong: str,
        ticker: str = "",
        nguong: float = 0.5,
        bieu_hien: str = "",
        chu_de: str = "",
        **kwargs: Any,
    ) -> str:
        kho = self._lay_kho()

        if hanh_dong == "tim_tai_san_tuong_quan":
            if not ticker:
                return json.dumps({"status": "error", "error": "Can cung cap 'ticker'"}, ensure_ascii=False)
            ket_qua = kho.tim_tuong_quan(ticker, nguong=nguong)
            return json.dumps({
                "status": "ok",
                "ticker": ticker.upper(),
                "nguong": nguong,
                "so_ket_qua": len(ket_qua),
                "ket_qua": ket_qua,
            }, ensure_ascii=False, indent=2)

        elif hanh_dong == "giai_thich_bien_dong":
            if not ticker:
                return json.dumps({"status": "error", "error": "Can cung cap 'ticker'"}, ensure_ascii=False)
            giai_thich = kho.giai_thich_bien_dong(ticker, bieu_hien)
            giai_thich["status"] = "ok"
            return json.dumps(giai_thich, ensure_ascii=False, indent=2)

        elif hanh_dong == "tim_theo_chu_de":
            if not chu_de:
                return json.dumps({"status": "error", "error": "Can cung cap 'chu_de'"}, ensure_ascii=False)
            ket_qua = kho.tim_theo_chu_de(chu_de)
            return json.dumps({
                "status": "ok",
                "chu_de": chu_de,
                "so_ket_qua": len(ket_qua),
                "ket_qua": ket_qua,
            }, ensure_ascii=False, indent=2)

        else:
            return json.dumps({
                "status": "error",
                "error": f"Hanh dong khong hop le: '{hanh_dong}'",
                "cac_hanh_dong_hop_le": ["tim_tai_san_tuong_quan", "giai_thich_bien_dong", "tim_theo_chu_de"],
            }, ensure_ascii=False)
