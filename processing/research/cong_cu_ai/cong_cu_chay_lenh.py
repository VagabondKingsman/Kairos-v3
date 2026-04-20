"""Công cụ chạy lệnh shell cho AI Agent.

Cho phép agent chạy lệnh bash/powershell trong sandbox giới hạn
với timeout và output truncation.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from processing.research.cong_cu_ai.cong_cu_co_so import CongCuCoSo

_DEFAULT_TIMEOUT = 60  # giây
_MAX_OUTPUT = 20_000   # ký tự


class CongCuChayLenh(CongCuCoSo):
    """Chạy lệnh shell (bash / powershell)."""

    name = "bash"
    description = (
        "Run a shell command and return stdout/stderr. "
        "Use for Python scripts, data processing, etc. "
        "Timeout: 60s. Output truncated to 20K chars."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to execute.",
            },
            "run_dir": {
                "type": "string",
                "description": "Working directory (auto-injected).",
            },
        },
        "required": ["command"],
    }
    repeatable = True

    def execute(
        self, command: str = "", run_dir: str = "", **kwargs: Any
    ) -> str:
        """Thực thi lệnh shell.

        Args:
            command: Lệnh cần chạy.
            run_dir: Thư mục làm việc.

        Returns:
            JSON string chứa stdout, stderr, return code.
        """
        if not command.strip():
            return json.dumps(
                {"status": "error", "error": "Lệnh trống"},
                ensure_ascii=False,
            )

        cwd = run_dir if run_dir and Path(run_dir).exists() else None

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=_DEFAULT_TIMEOUT,
                cwd=cwd,
                env=None,  # Kế thừa env hiện tại
            )

            stdout = result.stdout[:_MAX_OUTPUT] if result.stdout else ""
            stderr = result.stderr[:_MAX_OUTPUT] if result.stderr else ""
            truncated = len(result.stdout or "") > _MAX_OUTPUT

            return json.dumps(
                {
                    "status": "ok" if result.returncode == 0 else "error",
                    "return_code": result.returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                    "truncated": truncated,
                },
                ensure_ascii=False,
            )
        except subprocess.TimeoutExpired:
            return json.dumps(
                {
                    "status": "error",
                    "error": f"Lệnh quá thời gian ({_DEFAULT_TIMEOUT}s)",
                },
                ensure_ascii=False,
            )
        except Exception as exc:
            return json.dumps(
                {"status": "error", "error": str(exc)},
                ensure_ascii=False,
            )
