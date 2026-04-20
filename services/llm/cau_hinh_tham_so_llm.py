"""Quản lý cấu hình tham số cho các mô hình ngôn ngữ lớn (LLM).

Đọc cấu hình từ biến môi trường (.env) và cung cấp API thống nhất
để lấy thông tin provider, model name, temperature, timeout, v.v.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Bỏ toàn bộ logic load_dotenv cục bộ, chuyển sang dùng utils.config
from utils.config import cfg



# ---------------------------------------------------------------------------
# Ánh xạ nhà cung cấp (Provider mapping)
# ---------------------------------------------------------------------------

# Mỗi provider: (tên biến API key, tên biến base URL)
# api_key_env = None nghĩa là không cần key (VD: Ollama local)
PROVIDER_MAP: dict[str, tuple[Optional[str], str]] = {
    "openai":     ("OPENAI_API_KEY",     "OPENAI_BASE_URL"),
    "openrouter": ("OPENROUTER_API_KEY",  "OPENROUTER_BASE_URL"),
    "deepseek":   ("DEEPSEEK_API_KEY",    "DEEPSEEK_BASE_URL"),
    "gemini":     ("GEMINI_API_KEY",      "GEMINI_BASE_URL"),
    "groq":       ("GROQ_API_KEY",        "GROQ_BASE_URL"),
    "dashscope":  ("DASHSCOPE_API_KEY",   "DASHSCOPE_BASE_URL"),
    "qwen":       ("DASHSCOPE_API_KEY",   "DASHSCOPE_BASE_URL"),
    "zhipu":      ("ZHIPU_API_KEY",       "ZHIPU_BASE_URL"),
    "moonshot":   ("MOONSHOT_API_KEY",    "MOONSHOT_BASE_URL"),
    "minimax":    ("MINIMAX_API_KEY",     "MINIMAX_BASE_URL"),
    "ollama":     (None,                  "OLLAMA_BASE_URL"),
    "custom":     ("CUSTOM_API_KEY",       "CUSTOM_BASE_URL"),
}


@dataclass(frozen=True)
class CauHinhLLM:
    """Cấu hình đầy đủ cho một phiên kết nối LLM.

    Attributes:
        provider: Tên nhà cung cấp (openai, deepseek, gemini, groq...).
        model_name: Tên model (VD: deepseek-chat, gpt-4o, gemini-2.5-flash).
        api_key: Khóa API đã resolve.
        base_url: URL endpoint đã resolve.
        temperature: Nhiệt độ sampling (0.0 = deterministic).
        timeout: Timeout mỗi lần gọi API (giây).
        max_retries: Số lần thử lại khi lỗi mạng.
    """

    provider: str = "openai"
    model_name: str = ""
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.0
    timeout: int = 120
    max_retries: int = 2


def lay_cau_hinh(model_name: Optional[str] = None, provider_name: Optional[str] = None) -> CauHinhLLM:
    """Đọc cấu hình LLM từ utils.config và trả về CauHinhLLM.

    Args:
        model_name: Override model name. Nếu None, dùng cấu hình mặc định.
        provider_name: Override provider name. Nếu None, dùng cấu hình mặc định.

    Returns:
        CauHinhLLM đã resolve đầy đủ.
    """
    provider = provider_name or cfg.llm.provider
    return CauHinhLLM(
        provider=provider,
        model_name=model_name or cfg.llm.model_name,
        api_key=cfg.llm.get_api_key_for(provider),
        base_url=cfg.llm.get_base_url_for(provider),
        temperature=cfg.llm.temperature,
        timeout=cfg.system.timeout_seconds,
        max_retries=cfg.system.max_retries,
    )

