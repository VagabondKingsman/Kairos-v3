"""a05 - Kết Nối Mô Hình AI.

Module cung cấp khả năng kết nối đến các nhà cung cấp LLM khác nhau
thông qua OpenAI-compatible API. Hỗ trợ 10+ providers.

Sử dụng:
    >>> from services.llm import ChatLLM
    >>> llm = ChatLLM()
    >>> response = llm.chat([{"role": "user", "content": "Xin chào"}])
    >>> print(response.content)
"""

from services.llm.cau_hinh_tham_so_llm import (
    CauHinhLLM,
    lay_cau_hinh,
)
from services.llm.nha_cung_cap_llm import (
    tao_client,
    lay_client_mac_dinh,
    dat_lai_client,
)
from services.llm.xu_ly_doan_chat import (
    ChatLLM,
    PhanHoiLLM,
    YeuCauGoiCongCu,
)
from services.llm.quan_ly_token_va_chi_phi import (
    uoc_tinh_token,
    uoc_tinh_token_chuoi,
    BoQuanLyToken,
)

__all__ = [
    # Config
    "CauHinhLLM",
    "lay_cau_hinh",
    # Client
    "tao_client",
    "lay_client_mac_dinh",
    "dat_lai_client",
    # Chat
    "ChatLLM",
    "PhanHoiLLM",
    "YeuCauGoiCongCu",
    # Token
    "uoc_tinh_token",
    "uoc_tinh_token_chuoi",
    "BoQuanLyToken",
]
