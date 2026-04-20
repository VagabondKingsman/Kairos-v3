"""Xử lý đoạn chat — ChatLLM wrapper thống nhất cho ReAct Agent Loop.

Cung cấp lớp ``ChatLLM`` với hỗ trợ:
- Function calling (OpenAI tool format)
- Streaming text delta
- Retry logic tự động (qua openai SDK)
- Parse response thành ``PhanHoiLLM`` chuẩn hóa
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from services.llm.cau_hinh_tham_so_llm import CauHinhLLM, lay_cau_hinh

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mô hình dữ liệu
# ---------------------------------------------------------------------------

@dataclass
class YeuCauGoiCongCu:
    """Yêu cầu gọi công cụ trả về từ LLM."""
    id: str
    name: str
    arguments: Dict[str, Any]

@dataclass
class PhanHoiLLM:
    """Phản hồi chuẩn hóa từ LLM."""
    content: Optional[str] = None
    tool_calls: List[YeuCauGoiCongCu] = field(default_factory=list)
    finish_reason: str = "stop"

    @property
    def co_goi_cong_cu(self) -> bool:
        """True nếu response chứa tool calls."""
        return len(self.tool_calls) > 0

# ---------------------------------------------------------------------------
# ChatLLM (Dùng LiteLLM)
# ---------------------------------------------------------------------------

class ChatLLM:
    """Lớp giao tiếp LLM với hỗ trợ function calling.

    Sử dụng LiteLLM để tương thích 100+ nhà cung cấp AI.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        provider_name: Optional[str] = None,
        cau_hinh: Optional[CauHinhLLM] = None,
    ) -> None:
        if cau_hinh is None:
            cau_hinh = lay_cau_hinh(model_name=model_name, provider_name=provider_name)
        self._cau_hinh = cau_hinh
        self.model_name = cau_hinh.model_name

    def _build_kwargs(self) -> Dict[str, Any]:
        """Tạo bộ tham số chuẩn cho LiteLLM."""
        model = self.model_name
        # LiteLLM cần prefix nhà cung cấp (vd: gemini/gemini-pro)
        if self._cau_hinh.provider and "/" not in model and self._cau_hinh.provider != "openai":
            model = f"{self._cau_hinh.provider}/{model}"

        kwargs = {
            "model": model,
            "temperature": self._cau_hinh.temperature,
            "drop_params": True,  # Tự động bỏ tham số không được provider hỗ trợ
        }
        
        if self._cau_hinh.api_key:
            kwargs["api_key"] = self._cau_hinh.api_key
            
        # LiteLLM tự động biết URL gốc của Gemini, OpenAI, Groq, DeepSeek.
        # Ta CHỈ truyền api_base nếu là local model (Ollama) hoặc proxy tùy chỉnh.
        if self._cau_hinh.base_url and self._cau_hinh.provider in ["custom", "ollama", "openrouter"]:
            kwargs["api_base"] = self._cau_hinh.base_url
            
        return kwargs

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout: Optional[int] = None,
    ) -> PhanHoiLLM:
        import litellm

        kwargs = self._build_kwargs()
        kwargs["messages"] = messages
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if timeout:
            kwargs["timeout"] = float(timeout)

        response = litellm.completion(**kwargs)
        return self._parse_response(response)

    def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        on_text_chunk: Optional[Callable[[str], None]] = None,
        timeout: Optional[int] = None,
    ) -> PhanHoiLLM:
        kwargs = self._build_kwargs()
        kwargs["messages"] = messages
        kwargs["stream"] = True
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if timeout:
            kwargs["timeout"] = float(timeout)

        try:
            return self._stream_and_collect(kwargs, on_text_chunk)
        except Exception as e:
            logger.warning(f"Streaming thất bại ({e}), fallback sang chat() đồng bộ")
            return self.chat(messages, tools=tools, timeout=timeout)

    def _stream_and_collect(
        self,
        kwargs: Dict[str, Any],
        on_text_chunk: Optional[Callable[[str], None]],
    ) -> PhanHoiLLM:
        import litellm
        
        content_parts: List[str] = []
        tool_call_acc: Dict[int, Dict[str, Any]] = {}
        finish_reason = "stop"

        stream = litellm.completion(**kwargs)

        for chunk in stream:
            choice = chunk.choices[0] if chunk.choices else None
            if choice is None:
                continue

            delta = choice.delta
            if choice.finish_reason:
                finish_reason = choice.finish_reason

            if delta and getattr(delta, "content", None):
                content_parts.append(delta.content)
                if on_text_chunk:
                    on_text_chunk(delta.content)

            if delta and getattr(delta, "tool_calls", None):
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_call_acc:
                        tool_call_acc[idx] = {
                            "id": "",
                            "name": "",
                            "arguments_parts": [],
                        }
                    acc = tool_call_acc[idx]
                    if tc_delta.id:
                        acc["id"] = tc_delta.id
                    if getattr(tc_delta, "function", None):
                        if tc_delta.function.name:
                            acc["name"] = tc_delta.function.name
                        if getattr(tc_delta.function, "arguments", None):
                            acc["arguments_parts"].append(tc_delta.function.arguments)

        tool_calls: List[YeuCauGoiCongCu] = []
        for idx in sorted(tool_call_acc.keys()):
            acc = tool_call_acc[idx]
            args_str = "".join(acc["arguments_parts"])
            try:
                arguments = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                arguments = {"_raw": args_str}
            tool_calls.append(YeuCauGoiCongCu(
                id=acc["id"],
                name=acc["name"],
                arguments=arguments,
            ))

        content = "".join(content_parts) or None
        return PhanHoiLLM(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
        )

    @staticmethod
    def _parse_response(response: Any) -> PhanHoiLLM:
        choice = response.choices[0] if response.choices else None
        if choice is None:
            return PhanHoiLLM(content="", tool_calls=[], finish_reason="stop")

        content = getattr(choice.message, "content", None)
        finish_reason = getattr(choice, "finish_reason", "stop") or "stop"

        tool_calls: List[YeuCauGoiCongCu] = []
        raw_calls = getattr(choice.message, "tool_calls", []) or []
        for tc in raw_calls:
            try:
                args_str = getattr(tc.function, "arguments", "")
                arguments = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                arguments = {"_raw": getattr(tc.function, "arguments", "")}
            tool_calls.append(YeuCauGoiCongCu(
                id=getattr(tc, "id", ""),
                name=getattr(tc.function, "name", ""),
                arguments=arguments,
            ))

        return PhanHoiLLM(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
        )
