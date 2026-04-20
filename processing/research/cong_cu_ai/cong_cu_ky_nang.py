"""Cong Cu Doc Ky Nang — Skill Loader Tools.

Cho phep AI Agent tu tai kien thuc chuyen sau tu thu vien 68 SKILL.md
trong qua trinh ReAct loop.

Skills la gi?
    Moi SKILL.md la mot "so tay chuyen gia" dinh nghia:
    - Cac khai niem co ban (Core Concepts)
    - Cong thuc tinh toan (Python code snippets)
    - Quy tac ra quyet dinh (Decision rules / thresholds)
    - Dinh dang dau ra (Output Format)

    Vi du:
    - earnings-revision: day agent tinh SUE, PEAD, phan tich guidance
    - elliott-wave: quy tac dem song, cau truc impulse/corrective
    - options-strategy: iron condor, bull spread, tinh Greeks
    - onchain-analysis: Exchange Netflow, SOPR, MVRV ratio

Workflow cua Agent:
    1. Goi list_skills() de biet cac skills co san
    2. Goi load_skill("ten-skill") de tai noi dung vao context
    3. Su dung kien thuc de phan tich va ra quyet dinh

Hai cong cu:
    - ``CongCuLietKeKyNang`` (list_skills): Liet ke tat ca skills va description
    - ``CongCuDocKyNang`` (load_skill): Tai noi dung SKILL.md vao context
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from processing.research.cong_cu_ai.cong_cu_co_so import CongCuCoSo

# Thu muc chua cac SKILL.md
_KY_NANG_DIR = Path(__file__).resolve().parents[1] / "ky_nang"


# ---------------------------------------------------------------------------
# Helper: doc YAML frontmatter tu SKILL.md
# ---------------------------------------------------------------------------

def _doc_frontmatter(noi_dung: str) -> Dict[str, str]:
    """Trich xuat YAML frontmatter tu markdown.

    SKILL.md bat dau bang:
        ---
        name: ten-skill
        description: Mo ta...
        category: phan-loai
        ---

    Returns:
        Dict chua cac cap key-value, hoac {} neu khong co frontmatter.
    """
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", noi_dung, re.DOTALL)
    if not match:
        return {}
    frontmatter = {}
    for line in match.group(1).strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            frontmatter[key.strip()] = val.strip().strip('"').strip("'")
    return frontmatter


def _lay_tat_ca_skills() -> List[Dict[str, str]]:
    """Quet thu muc ky_nang/ va tra ve index tat ca skills."""
    if not _KY_NANG_DIR.exists():
        return []
    ket_qua = []
    for skill_dir in sorted(_KY_NANG_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        try:
            noi_dung = skill_file.read_text(encoding="utf-8")
            fm = _doc_frontmatter(noi_dung)
            ket_qua.append({
                "name": fm.get("name", skill_dir.name),
                "description": fm.get("description", "(Khong co mo ta)"),
                "category": fm.get("category", "other"),
            })
        except Exception:
            ket_qua.append({
                "name": skill_dir.name,
                "description": "(Loi khi doc)",
                "category": "other",
            })
    return ket_qua


# ---------------------------------------------------------------------------
# CongCuLietKeKyNang — list_skills
# ---------------------------------------------------------------------------

class CongCuLietKeKyNang(CongCuCoSo):
    """Liet ke tat ca skills co san trong he thong.

    Agent goi tool nay de biet co nhung kien thuc gi truoc khi quyet
    dinh nen tai skill nao.

    Returns:
        JSON array cac skills, moi phan tu co:
        - name: Ten skill (dung de goi load_skill)
        - description: Mo ta ngan
        - category: Phan loai (analysis, asset-class, data-source, ...)
    """

    name = "list_skills"
    description = (
        "Liet ke tat ca skills (so tay chuyen gia) co san trong he thong. "
        "Goi truoc khi dung load_skill() de biet nen tai skill nao. "
        "Moi skill la mot tap hop kien thuc chuyen sau ve mot chu de "
        "(phan tich ky thuat, fundamental, crypto, options, quant...). "
        "Khong co tham so dau vao."
    )
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }
    repeatable = False

    def execute(self, **kwargs: Any) -> str:
        skills = _lay_tat_ca_skills()
        if not skills:
            return json.dumps(
                {"status": "error", "error": f"Khong tim thay thu muc ky_nang tai: {_KY_NANG_DIR}"},
                ensure_ascii=False,
            )
        # Nhom theo category
        nhom: Dict[str, List[Dict]] = {}
        for s in skills:
            cat = s["category"]
            nhom.setdefault(cat, []).append({"name": s["name"], "description": s["description"]})

        return json.dumps(
            {
                "status": "ok",
                "tong_so": len(skills),
                "ghi_chu": "Dung load_skill(skill_name) de tai noi dung chi tiet",
                "skills_theo_nhom": nhom,
            },
            ensure_ascii=False,
            indent=2,
        )


# ---------------------------------------------------------------------------
# CongCuDocKyNang — load_skill
# ---------------------------------------------------------------------------

class CongCuDocKyNang(CongCuCoSo):
    """Tai noi dung chuyen sau cua mot skill vao context cua Agent.

    Skill la mot "so tay chuyen gia" chua:
    - Cac khai niem co ban va cong thuc tinh toan
    - Quy tac phan tich va nguong ra quyet dinh
    - Code mau Python
    - Dinh dang dau ra chuan

    Sau khi goi load_skill(), agent se co kien thuc de:
    - Ap dung phuong phap phan tich chinh xac
    - Tinh toan cac chi so phu hop
    - Dinh dang ket qua theo chuan

    Agent co the goi nhieu lan de tai nhieu skills khac nhau.

    Dung list_skills() truoc de biet ten cac skills co san.
    """

    name = "load_skill"
    description = (
        "Tai kien thuc chuyen sau (SKILL.md) theo ten skill vao context de ho tro phan tich. "
        "Vi du: load_skill('earnings-revision') se day agent cach tinh SUE, PEAD. "
        "load_skill('elliott-wave') cho quy tac dem song. "
        "load_skill('onchain-analysis') cho SOPR, MVRV, Exchange Netflow. "
        "Goi list_skills() truoc de xem danh sach day du."
    )
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "skill_name": {
                "type": "string",
                "description": (
                    "Ten skill can tai. "
                    "Vi du: 'earnings-revision', 'elliott-wave', 'options-strategy', "
                    "'onchain-analysis', 'sentiment-analysis', 'global-macro', ..."
                ),
            },
        },
        "required": ["skill_name"],
    }
    repeatable = True  # Agent co the load nhieu skills trong mot phien

    def execute(self, skill_name: str, **kwargs: Any) -> str:
        """Tai noi dung SKILL.md.

        Args:
            skill_name: Ten skill (khop voi ten thu muc trong ky_nang/).

        Returns:
            JSON string chua noi dung markdown hoac thong tin loi.
        """
        # Sanitize input de tranh path traversal
        skill_name_sach = re.sub(r"[^a-zA-Z0-9\-_]", "", skill_name)
        if not skill_name_sach:
            return json.dumps(
                {"status": "error", "error": "Ten skill khong hop le"},
                ensure_ascii=False,
            )

        skill_file = _KY_NANG_DIR / skill_name_sach / "SKILL.md"

        if not skill_file.exists():
            # Tim kiem gan giong (fuzzy)
            tat_ca = [d.name for d in _KY_NANG_DIR.iterdir() if d.is_dir()]
            goi_y = [s for s in tat_ca if skill_name_sach.lower() in s.lower()][:5]
            return json.dumps(
                {
                    "status": "error",
                    "error": f"Khong tim thay skill '{skill_name_sach}'",
                    "goi_y": goi_y,
                    "huong_dan": "Goi list_skills() de xem danh sach day du",
                },
                ensure_ascii=False,
            )

        try:
            noi_dung = skill_file.read_text(encoding="utf-8")
        except Exception as exc:
            return json.dumps(
                {"status": "error", "error": f"Loi khi doc skill: {exc}"},
                ensure_ascii=False,
            )

        fm = _doc_frontmatter(noi_dung)

        # Xoa frontmatter khoi noi dung tra ve (giu lai phan content)
        noi_dung_sach = re.sub(r"^---\s*\n.*?\n---\s*\n", "", noi_dung, flags=re.DOTALL, count=1)

        return json.dumps(
            {
                "status": "ok",
                "skill_name": fm.get("name", skill_name_sach),
                "category": fm.get("category", "other"),
                "description": fm.get("description", ""),
                "noi_dung": noi_dung_sach.strip(),
                "huong_dan": (
                    f"Da tai skill '{fm.get('name', skill_name_sach)}'. "
                    "Su dung kien thuc nay de phan tich theo yeu cau."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )


# ---------------------------------------------------------------------------
# CongCuLietKeChienLuocA04 — list_a04_strategies
# ---------------------------------------------------------------------------

class CongCuLietKeChienLuocA04(CongCuCoSo):
    """Liet ke cac chien luoc da implement san trong a04/ky_nang_chien_luoc/.

    Khac voi load_skill() (tai kien thuc SKILL.md de doc),
    tool nay tra ve cac Python SignalEngine DA VIET SAN ma agent co the
    import truc tiep vao signal_engine.py khong can viet lai tu dau.

    Cac chien luoc deu su dung XayDungNenHTF (nen_htf) cho phan tich
    da khung thoi gian khong co lookahead bias.
    """

    name = "list_a04_strategies"
    description = (
        "Liet ke cac chien luoc da implement san trong a04 (co the import ngay). "
        "Tat ca deu ho tro Multi-Timeframe qua XayDungNenHTF (khong lookahead). "
        "Dung khi muon tao signal_engine.py nhanh ma khong can viet logic tu dau."
    )
    parameters: Dict[str, Any] = {"type": "object", "properties": {}, "required": []}
    repeatable = False

    _CHIEN_LUOC = [
        {
            "ten": "smc",
            "mo_ta": "Smart Money Concepts — Order Block, FVG, BOS/CHOCH, Premium/Discount zones",
            "class": "SmcSignalEngine",
            "module": "processing.backtest.ky_nang_chien_luoc.dong_tien_thong_minh_smc",
            "htf_default": "4h",
            "base_tf_goi_y": "1H hoac 4H",
            "vi_du_import": (
                "from processing.backtest.ky_nang_chien_luoc"
                ".dong_tien_thong_minh_smc import SmcSignalEngine\n"
                "class SignalEngine:\n"
                "    def __init__(self): self._e = SmcSignalEngine(htf='4h')\n"
                "    def generate(self, data_map): return self._e.generate(data_map)"
            ),
        },
        {
            "ten": "htf_builder",
            "mo_ta": "XayDungNenHTF — Utility xay dung nen HTF khong lookahead",
            "class": "XayDungNenHTF",
            "module": "processing.backtest.nen_htf",
            "htf_default": "N/A",
            "base_tf_goi_y": "bat ky TF nao",
            "vi_du_import": (
                "from processing.backtest.nen_htf import XayDungNenHTF\n"
                "htf = XayDungNenHTF()\n"
                "df = htf.them_vao_df(df, '4h', prefix='h4')"
            ),
        },
    ]

    def execute(self, **kwargs: Any) -> str:
        return json.dumps(
            {
                "status": "ok",
                "so_luong": len(self._CHIEN_LUOC),
                "ghi_chu": (
                    "Import truc tiep vao signal_engine.py. "
                    "Dung load_skill('strategy-generate') de xem workflow day du."
                ),
                "chien_luoc": self._CHIEN_LUOC,
            },
            ensure_ascii=False,
            indent=2,
        )
