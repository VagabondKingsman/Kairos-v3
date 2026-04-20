"""Nhà cung cấp LLM — Factory tạo OpenAI client cho mọi provider.

Sử dụng ``openai`` SDK trực tiếp (không qua LangChain) để giảm dependency.
Tất cả providers hỗ trợ OpenAI-compatible API sẽ hoạt động thông qua
việc map ``api_key`` + ``base_url`` phù hợp.
"""

from __future__ import annotations

import logging
from typing import Optional

from openai import OpenAI

from services.llm.cau_hinh_tham_so_llm import CauHinhLLM, lay_cau_hinh

logger = logging.getLogger(__name__)


def tao_client(cau_hinh: Optional[CauHinhLLM] = None) -> OpenAI:
    """Tạo một OpenAI client từ cấu hình.

    Args:
        cau_hinh: Cấu hình LLM. Nếu None, tự đọc từ biến môi trường.

    Returns:
        OpenAI client đã cấu hình, sẵn sàng gọi API.

    Raises:
        RuntimeError: Nếu thiếu cấu hình bắt buộc.
    """
    if cau_hinh is None:
        cau_hinh = lay_cau_hinh()

    # Gemini OpenAI-compatible endpoint nhận API key qua Bearer token — giống mọi provider khác.
    # base_url: https://generativelanguage.googleapis.com/v1beta/openai/
    kwargs: dict = {
        "api_key": cau_hinh.api_key or "dummy",
        "timeout": float(cau_hinh.timeout),
        "max_retries": cau_hinh.max_retries,
    }

    if cau_hinh.base_url:
        kwargs["base_url"] = cau_hinh.base_url

    logger.info(
        "Tạo OpenAI client: provider=%s, model=%s, base_url=%s",
        cau_hinh.provider,
        cau_hinh.model_name,
        cau_hinh.base_url or "(default)",
    )

    return OpenAI(**kwargs)


# ---------------------------------------------------------------------------
# Singleton client (tùy chọn — dùng khi không cần nhiều instance)
# ---------------------------------------------------------------------------

_default_client: Optional[OpenAI] = None


def lay_client_mac_dinh() -> OpenAI:
    """Lấy hoặc tạo OpenAI client singleton.

    Sử dụng cấu hình từ biến môi trường. Client được cache lại
    sau lần tạo đầu tiên.

    Returns:
        OpenAI client singleton.
    """
    global _default_client
    if _default_client is None:
        _default_client = tao_client()
    return _default_client


def dat_lai_client() -> None:
    """Xóa client singleton (để tạo lại với cấu hình mới)."""
    global _default_client
    _default_client = None
