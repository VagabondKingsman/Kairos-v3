"""Tiện ích ước tính token và theo dõi chi phí sử dụng LLM.

Cung cấp hàm ước tính token nhanh (dựa trên số ký tự) và bộ đếm
tích lũy token input/output cho mỗi phiên chạy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List


def uoc_tinh_token(messages: List[Dict[str, Any]]) -> int:
    """Ước tính số token từ danh sách messages (xấp xỉ ~4 ký tự/token).

    Args:
        messages: Danh sách messages theo format OpenAI.

    Returns:
        Số token ước tính.
    """
    return len(json.dumps(messages, default=str, ensure_ascii=False)) // 4


def uoc_tinh_token_chuoi(text: str) -> int:
    """Ước tính số token từ một chuỗi văn bản.

    Args:
        text: Văn bản cần ước tính.

    Returns:
        Số token ước tính.
    """
    return len(text) // 4


@dataclass
class BoQuanLyToken:
    """Bộ quản lý theo dõi token và chi phí qua các phiên chạy.

    Attributes:
        tong_token_dau_vao: Tổng token đầu vào (input) tích lũy.
        tong_token_dau_ra: Tổng token đầu ra (output) tích lũy.
        lich_su_phien: Lịch sử token từng lần gọi LLM.
    """

    tong_token_dau_vao: int = 0
    tong_token_dau_ra: int = 0
    lich_su_phien: List[Dict[str, int]] = field(default_factory=list)

    def ghi_nhan(self, token_vao: int, token_ra: int) -> None:
        """Ghi nhận token sử dụng cho một lần gọi LLM.

        Args:
            token_vao: Số token đầu vào.
            token_ra: Số token đầu ra.
        """
        self.tong_token_dau_vao += token_vao
        self.tong_token_dau_ra += token_ra
        self.lich_su_phien.append({
            "dau_vao": token_vao,
            "dau_ra": token_ra,
        })

    @property
    def tong_token(self) -> int:
        """Tổng token đã sử dụng (đầu vào + đầu ra)."""
        return self.tong_token_dau_vao + self.tong_token_dau_ra

    @property
    def so_lan_goi(self) -> int:
        """Số lần gọi LLM."""
        return len(self.lich_su_phien)

    def to_dict(self) -> Dict[str, Any]:
        """Xuất thống kê sử dụng token dưới dạng dict."""
        return {
            "tong_token_dau_vao": self.tong_token_dau_vao,
            "tong_token_dau_ra": self.tong_token_dau_ra,
            "tong_token": self.tong_token,
            "so_lan_goi": self.so_lan_goi,
        }

    def reset(self) -> None:
        """Đặt lại bộ đếm về 0."""
        self.tong_token_dau_vao = 0
        self.tong_token_dau_ra = 0
        self.lich_su_phien.clear()
