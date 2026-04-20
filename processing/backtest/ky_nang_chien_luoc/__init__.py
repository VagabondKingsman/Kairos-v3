"""a04/ky_nang_chien_luoc — Kho Chien Luoc Da Tao Ra.

Day la noi luu cac chien luoc duoc sinh ra boi AI Agent (tuong tu Vibe-Trading).
Moi chien luoc la mot module Python chua class `SignalEngine` tuan theo contract:

    class SignalEngine:
        def generate(self, data_map: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
            ...

Tat ca chien luoc BAT BUOC su dung XayDungNenHTF tu a04.nen_htf
de phan tich da khung thoi gian (Multi-Timeframe) khong lookahead.

Registry (cac chien luoc co san):
    smc         → dong_tien_thong_minh_smc.SmcSignalEngine
    technical   → (template trong SKILL.md skill "technical-basic")
    ichimoku    → (template trong SKILL.md skill "ichimoku")
    elliott     → (template trong SKILL.md skill "elliott-wave")
    ml_regime   → (template trong SKILL.md skill "ml-strategy")

Cach dung:
    from processing.backtest.ky_nang_chien_luoc import lay_chien_luoc
    engine = lay_chien_luoc("smc")
    signals = engine.generate(data_map)
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Registry: ten → (module_path, class_name)
_REGISTRY = {}

# Tự động scan các file Python trong thư mục hiện tại để đăng ký chiến lược
import os
from pathlib import Path
_current_dir = Path(__file__).parent
for _file in _current_dir.glob("*.py"):
    if _file.name.startswith("__"): continue
    
    _module_name = _file.stem
    _module_path = f"processing.backtest.ky_nang_chien_luoc.{_module_name}"
    
    # Giả định quy ước: Mỗi file chứa một class 'SignalEngine'
    # Ten chien luoc = ten file (vd: rsi_20_days.py -> rsi_20_days)
    _REGISTRY[_module_name] = (_module_path, "SignalEngine")


def lay_chien_luoc(ten: str, **kwargs: Any) -> Any:
    """Lay instance cua mot chien luoc theo ten.
    Tu dong tim file .py trong thu muc va import/reload (ho tro hot-reload).

    Args:
        ten: Ten chien luoc (VD: "smc").
        **kwargs: Tham so truyen vao constructor cua chien luoc.

    Returns:
        Instance cua SignalEngine.
    """
    import os
    import importlib
    from pathlib import Path

    _current_dir = Path(__file__).parent
    _file_path = _current_dir / f"{ten}.py"

    if _file_path.exists():
        module_path = f"processing.backtest.ky_nang_chien_luoc.{ten}"
        class_name = "SignalEngine"
        try:
            # Import module (va reload de lay code moi nhat neu bi thay doi)
            mod = importlib.import_module(module_path)
            importlib.reload(mod)
            cls = getattr(mod, class_name)
            return cls(**kwargs)
        except Exception as exc:
            logger.error("Loi load chien luoc '%s': %s", ten, exc)
            raise

    # Fallback to static registry
    if ten not in _REGISTRY:
        # Quet lai muc de thong bao
        available = [f.stem for f in _current_dir.glob("*.py") if not f.name.startswith("__")]
        raise KeyError(
            f"Chien luoc '{ten}' khong tim thay. "
            f"Cac chien luoc co san: {', '.join(available)}"
        )

    module_path, class_name = _REGISTRY[ten]
    try:
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        return cls(**kwargs)
    except Exception as exc:
        logger.error("Loi load chien luoc '%s': %s", ten, exc)
        raise


def dang_ky_chien_luoc(ten: str, module_path: str, class_name: str) -> None:
    """Dang ky them mot chien luoc moi vao registry.

    Args:
        ten: Ten ngan gon cua chien luoc.
        module_path: Duong dan import Python (VD: "a04...ky_nang_chien_luoc.abc").
        class_name: Ten class SignalEngine ben trong module.
    """
    _REGISTRY[ten] = (module_path, class_name)
    logger.info("Da dang ky chien luoc: %s → %s.%s", ten, module_path, class_name)


def lay_danh_sach() -> list:
    """Tra ve danh sach ten cac chien luoc da dang ky."""
    return sorted(_REGISTRY.keys())


__all__ = [
    "lay_chien_luoc",
    "dang_ky_chien_luoc",
    "lay_danh_sach",
]
