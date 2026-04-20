"""Công cụ đọc/ghi file cho AI Agent.

Cho phép agent đọc nội dung file và ghi file mới vào thư mục chạy.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from processing.research.cong_cu_ai.cong_cu_co_so import CongCuCoSo


class CongCuDocFile(CongCuCoSo):
    """Đọc nội dung file."""

    name = "read_file"
    description = "Read file contents. Returns text content or error."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path (relative to run_dir or absolute).",
            },
            "run_dir": {
                "type": "string",
                "description": "Run directory (auto-injected).",
            },
        },
        "required": ["path"],
    }
    repeatable = True

    def execute(self, path: str = "", run_dir: str = "", **kwargs: Any) -> str:
        """Đọc nội dung file.

        Args:
            path: Đường dẫn file.
            run_dir: Thư mục chạy (dùng làm base cho relative path).

        Returns:
            JSON string chứa nội dung file hoặc lỗi.
        """
        target = Path(path)
        if not target.is_absolute() and run_dir:
            target = Path(run_dir) / path

        if not target.exists():
            return json.dumps(
                {"status": "error", "error": f"File không tồn tại: {target}"},
                ensure_ascii=False,
            )

        try:
            content = target.read_text(encoding="utf-8")
            return json.dumps(
                {
                    "status": "ok",
                    "path": str(target),
                    "content": content[:50_000],  # Giới hạn 50K ký tự
                    "size_bytes": target.stat().st_size,
                },
                ensure_ascii=False,
            )
        except Exception as exc:
            return json.dumps(
                {"status": "error", "error": str(exc)},
                ensure_ascii=False,
            )


class CongCuGhiFile(CongCuCoSo):
    """Ghi nội dung vào file."""

    name = "write_file"
    description = "Write content to a file. Creates parent directories if needed."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path (relative to run_dir or absolute).",
            },
            "content": {
                "type": "string",
                "description": "Content to write.",
            },
            "run_dir": {
                "type": "string",
                "description": "Run directory (auto-injected).",
            },
        },
        "required": ["path", "content"],
    }
    repeatable = True

    def execute(
        self, path: str = "", content: str = "", run_dir: str = "", **kwargs: Any
    ) -> str:
        """Ghi nội dung vào file.

        Args:
            path: Đường dẫn file.
            content: Nội dung cần ghi.
            run_dir: Thư mục chạy.

        Returns:
            JSON string xác nhận hoặc lỗi.
        """
        target = Path(path)
        if not target.is_absolute() and run_dir:
            target = Path(run_dir) / path

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return json.dumps(
                {
                    "status": "ok",
                    "path": str(target),
                    "bytes_written": len(content.encode("utf-8")),
                },
                ensure_ascii=False,
            )
        except Exception as exc:
            return json.dumps(
                {"status": "error", "error": str(exc)},
                ensure_ascii=False,
            )
