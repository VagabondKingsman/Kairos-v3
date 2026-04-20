"""Công cụ cơ sở — BaseTool và ToolRegistry cho hệ thống AI Agent.

Mọi công cụ (tool) trong Kairos đều kế thừa ``CongCuCoSo`` và đăng ký
vào ``SoDoTool``. Registry cung cấp:
- Chuyển đổi sang OpenAI function calling format
- Thực thi an toàn (bắt exception → trả JSON error)
- Lọc tool theo danh sách cho phép (cho Swarm worker)
"""

from __future__ import annotations

import json
import traceback
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class CongCuCoSo(ABC):
    """Lớp cơ sở cho mọi công cụ AI.

    Mỗi tool phải khai báo ``name``, ``description``, ``parameters``
    và implement ``execute(**kwargs) -> str``.

    Attributes:
        name: Định danh duy nhất của công cụ (VD: "backtest", "read_file").
        description: Mô tả hiển thị cho LLM (ngắn gọn, tiếng Anh hoặc Việt).
        parameters: Định nghĩa tham số theo JSON Schema format.
        repeatable: True nếu tool có thể gọi nhiều lần trong một session.
    """

    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}
    repeatable: bool = False

    @abstractmethod
    def execute(self, **kwargs: Any) -> str:
        """Thực thi công cụ và trả về kết quả dạng JSON string.

        Args:
            **kwargs: Tham số được LLM truyền vào.

        Returns:
            JSON string chứa kết quả hoặc thông tin lỗi.
        """

    def to_openai_schema(self) -> Dict[str, Any]:
        """Chuyển đổi sang OpenAI function calling format.

        Returns:
            Dict theo format ``{"type": "function", "function": {...}}``.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters or {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }


class SoDoTool:
    """Registry quản lý và thực thi các công cụ AI.

    Attributes:
        _tools: Dict lưu trữ tool theo name.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, CongCuCoSo] = {}

    def dang_ky(self, tool: CongCuCoSo) -> None:
        """Đăng ký một công cụ vào registry.

        Args:
            tool: Instance của CongCuCoSo.
        """
        self._tools[tool.name] = tool

    def lay(self, name: str) -> Optional[CongCuCoSo]:
        """Lấy công cụ theo tên.

        Args:
            name: Tên công cụ.

        Returns:
            CongCuCoSo hoặc None nếu không tìm thấy.
        """
        return self._tools.get(name)

    def lay_dinh_nghia(self) -> List[Dict[str, Any]]:
        """Trả về tất cả tools ở OpenAI function calling format.

        Returns:
            Danh sách tool definitions.
        """
        return [t.to_openai_schema() for t in self._tools.values()]

    def thuc_thi(self, name: str, params: Dict[str, Any]) -> str:
        """Thực thi một công cụ và đảm bảo trả về JSON hợp lệ.

        Nếu tool không tồn tại hoặc xảy ra lỗi, trả về JSON error
        thay vì raise exception.

        Args:
            name: Tên công cụ.
            params: Dict tham số.

        Returns:
            JSON string kết quả.
        """
        tool = self._tools.get(name)
        if not tool:
            return json.dumps(
                {"status": "error", "error": f"Công cụ '{name}' không tồn tại"},
                ensure_ascii=False,
            )
        try:
            return tool.execute(**params)
        except Exception as exc:
            return json.dumps(
                {
                    "status": "error",
                    "tool": name,
                    "error": str(exc),
                    "traceback": traceback.format_exc()[-500:],
                },
                ensure_ascii=False,
            )

    @property
    def danh_sach_ten(self) -> List[str]:
        """Danh sách tên tất cả tools đã đăng ký."""
        return list(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
