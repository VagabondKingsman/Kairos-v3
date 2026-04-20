"""Bộ nhớ phiên làm việc — Shared state giữa các tool calls.

Lưu trữ trạng thái trung gian trong một phiên chạy agent:
- KV store cho kết quả tool
- Bộ đếm số lần gọi tool
- Extra data store tự do
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class BoNhoPhienLam:
    """Bộ nhớ chia sẻ giữa các tool trong một phiên chạy agent.

    Attributes:
        run_dir: Thư mục chạy hiện tại.
        store: Kết quả tool (memory_key → JSON string).
        counters: Bộ đếm số lần gọi mỗi tool.
        extra: KV store tự do cho dữ liệu phái sinh.
    """

    run_dir: Optional[str] = None
    store: Dict[str, str] = field(default_factory=dict)
    counters: Dict[str, int] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    def reset(self) -> None:
        """Đặt lại toàn bộ trạng thái."""
        self.run_dir = None
        self.store.clear()
        self.counters.clear()
        self.extra.clear()

    def luu_ket_qua(self, key: str, value: str) -> None:
        """Lưu kết quả tool.

        Args:
            key: Khóa bộ nhớ (VD: "plan_output").
            value: JSON string kết quả.
        """
        self.store[key] = value

    def lay_ket_qua(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Lấy kết quả tool.

        Args:
            key: Khóa bộ nhớ.
            default: Giá trị mặc định.

        Returns:
            JSON string hoặc default.
        """
        return self.store.get(key, default)

    def tang_dem(self, key: str) -> int:
        """Tăng bộ đếm và trả về giá trị mới.

        Args:
            key: Khóa bộ đếm (thường là tên tool).

        Returns:
            Giá trị bộ đếm sau khi tăng.
        """
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    def dat_extra(self, key: str, value: Any) -> None:
        """Đặt giá trị extra.

        Args:
            key: Tên khóa.
            value: Giá trị bất kỳ.
        """
        self.extra[key] = value

    def lay_extra(self, key: str, default: Any = None) -> Any:
        """Lấy giá trị extra.

        Args:
            key: Tên khóa.
            default: Giá trị mặc định.

        Returns:
            Giá trị đã lưu hoặc default.
        """
        return self.extra.get(key, default)

    def to_summary(self) -> str:
        """Tạo tóm tắt trạng thái để inject vào system prompt.

        Returns:
            Chuỗi tóm tắt dạng markdown list.
        """
        lines = []
        if self.run_dir:
            lines.append(f"- run_dir: {self.run_dir}")
        if self.store:
            completed = list(self.store.keys())
            lines.append(f"- completed: {', '.join(completed)}")
        if self.counters:
            counter_parts = [f"{k}={v}" for k, v in self.counters.items()]
            lines.append(f"- counters: {', '.join(counter_parts)}")
        return "\n".join(lines) if lines else "(trạng thái trống)"
