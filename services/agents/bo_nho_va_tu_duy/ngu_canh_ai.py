"""Xây dựng ngữ cảnh — System prompt builder cho ReAct Agent Loop.

Tạo system prompt với:
- Mô tả tools (OpenAI function calling format)
- Tóm tắt trạng thái bộ nhớ
- Hướng dẫn task routing
- Format cho tool result và assistant tool_calls messages
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from processing.research.cong_cu_ai.cong_cu_co_so import SoDoTool
from services.agents.bo_nho_va_tu_duy.bo_nho_ai import BoNhoPhienLam

# ---------------------------------------------------------------------------
# Mẫu lời nhắc hệ thống (System prompt)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
Bạn là trợ lý nghiên cứu tài chính AI của hệ thống Kairos Quant System.
Bạn có khả năng sử dụng các công cụ (tools) để nghiên cứu, phân tích và kiểm thử chiến lược giao dịch.

## Công cụ có sẵn

{tool_descriptions}

## Trạng thái hiện tại

{memory_summary}

## Hướng dẫn xử lý yêu cầu

**Kiểm thử chiến lược (Backtest):**
1. Tạo file ``config.json`` với thông tin: source, codes, dates, parameters
2. Tạo file ``code/signal_engine.py`` với class SignalEngine
3. Gọi ``backtest(run_dir=...)`` để chạy kiểm thử
4. Đọc ``artifacts/metrics.csv`` để lấy kết quả

**Phân tích / nghiên cứu:**
- Dùng ``bash`` để chạy Python scripts phân tích
- Dùng ``read_file`` / ``write_file`` để đọc/ghi dữ liệu

**Quy tắc:**
- Trả lời bằng ngôn ngữ người dùng sử dụng
- Hiển thị kết quả dưới dạng bảng markdown
- Sau backtest luôn báo cáo: total_return, sharpe, max_drawdown, trade_count
- Đường dẫn file tương đối so với run_dir (tự động inject)
- Nếu thiếu thông tin quan trọng (mã chứng khoán, ngày, loại chiến lược), hỏi lại người dùng
"""


class XayDungNguCanh:
    """Xây dựng context messages cho ReAct Agent Loop.

    Attributes:
        registry: Registry các công cụ.
        memory: Bộ nhớ phiên làm việc.
    """

    def __init__(
        self,
        registry: SoDoTool,
        memory: BoNhoPhienLam,
    ) -> None:
        """Khởi tạo XayDungNguCanh.

        Args:
            registry: Registry công cụ.
            memory: Bộ nhớ phiên làm việc.
        """
        self.registry = registry
        self.memory = memory

    def tao_system_prompt(self) -> str:
        """Tạo system prompt hoàn chỉnh.

        Returns:
            Chuỗi system prompt đã format.
        """
        return _SYSTEM_PROMPT.format(
            tool_descriptions=self._format_tool_descriptions(),
            memory_summary=self.memory.to_summary(),
        )

    def tao_messages(
        self,
        user_message: str,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Tạo danh sách messages hoàn chỉnh cho LLM call.

        Args:
            user_message: Tin nhắn người dùng.
            history: Lịch sử hội thoại trước đó.

        Returns:
            Danh sách messages theo OpenAI format.
        """
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.tao_system_prompt()},
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        return messages

    def _format_tool_descriptions(self) -> str:
        """Format mô tả tools cho system prompt.

        Returns:
            Chuỗi mô tả tất cả tools.
        """
        lines = []
        for tool in self.registry._tools.values():
            params = tool.parameters.get("properties", {})
            required = tool.parameters.get("required", [])
            param_parts = []
            for pname, pschema in params.items():
                req = " (bắt buộc)" if pname in required else ""
                desc = pschema.get("description", pschema.get("type", ""))
                param_parts.append(f"    - {pname}: {desc}{req}")
            param_text = "\n".join(param_parts) if param_parts else "    (không có tham số)"
            lines.append(f"### {tool.name}\n{tool.description}\n  Tham số:\n{param_text}")
        return "\n\n".join(lines)

    @staticmethod
    def format_tool_result(tool_call_id: str, tool_name: str, result: str) -> Dict[str, Any]:
        """Format kết quả tool thành message.

        Args:
            tool_call_id: ID của tool call.
            tool_name: Tên công cụ.
            result: Kết quả JSON string.

        Returns:
            Message dict theo OpenAI format.
        """
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": result,
        }

    @staticmethod
    def format_assistant_tool_calls(
        tool_calls: list,
        content: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Format assistant message có tool_calls.

        Args:
            tool_calls: Danh sách YeuCauGoiCongCu objects.
            content: Text thinking/reasoning của model.

        Returns:
            Message dict theo OpenAI format.
        """
        return {
            "role": "assistant",
            "content": content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                    },
                }
                for tc in tool_calls
            ],
        }
