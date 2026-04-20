"""Công cụ kiểm thử (Backtest) cho AI Agent.

Kết nối với processing.backtest để chạy backtest
và trả về metrics cho agent.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from processing.research.cong_cu_ai.cong_cu_co_so import CongCuCoSo

logger = logging.getLogger(__name__)


class CongCuKiemThu(CongCuCoSo):
    """Chạy backtest trên chiến lược giao dịch.

    Agent cần tạo ``config.json`` và ``code/signal_engine.py``
    trong run_dir trước khi gọi tool này.
    """

    name = "backtest"
    description = (
        "Run vectorized backtest engine. Requires config.json and "
        "code/signal_engine.py in run_dir. Returns performance metrics "
        "(total_return, sharpe, max_drawdown, trade_count)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "run_dir": {
                "type": "string",
                "description": "Run directory containing config.json and code/signal_engine.py.",
            },
        },
        "required": ["run_dir"],
    }
    repeatable = False

    def execute(self, run_dir: str = "", **kwargs: Any) -> str:
        """Chạy backtest engine.

        Args:
            run_dir: Thư mục chứa config.json và code/signal_engine.py.

        Returns:
            JSON string chứa metrics hoặc lỗi.
        """
        if not run_dir:
            return json.dumps(
                {"status": "error", "error": "run_dir không được để trống"},
                ensure_ascii=False,
            )

        run_path = Path(run_dir)

        # Kiểm tra file bắt buộc
        config_path = run_path / "config.json"
        signal_path = run_path / "code" / "signal_engine.py"

        if not config_path.exists():
            return json.dumps(
                {"status": "error", "error": f"Thiếu config.json tại {config_path}"},
                ensure_ascii=False,
            )

        if not signal_path.exists():
            return json.dumps(
                {
                    "status": "error",
                    "error": f"Thiếu code/signal_engine.py tại {signal_path}",
                },
                ensure_ascii=False,
            )

        # Thử import và chạy backtest engine
        try:
            from processing.backtest.dong_co_kiem_thu.trinh_chay import main as chay_kiem_thu

            ket_qua = chay_kiem_thu(str(run_path))

            # Đọc metrics nếu đã tạo
            metrics_path = run_path / "artifacts" / "metrics.csv"
            if metrics_path.exists():
                metrics_content = metrics_path.read_text(encoding="utf-8")
                return json.dumps(
                    {
                        "status": "ok",
                        "metrics_csv": metrics_content[:5000],
                        "run_dir": str(run_path),
                    },
                    ensure_ascii=False,
                )

            return json.dumps(
                {
                    "status": "ok",
                    "result": str(ket_qua)[:5000] if ket_qua else "Hoàn thành",
                    "run_dir": str(run_path),
                },
                ensure_ascii=False,
            )

        except ImportError as exc:
            logger.warning("Không thể import backtest engine: %s", exc)
            return json.dumps(
                {
                    "status": "error",
                    "error": f"Không thể import backtest engine: {exc}",
                },
                ensure_ascii=False,
            )
        except Exception as exc:
            logger.exception("Lỗi khi chạy backtest")
            return json.dumps(
                {"status": "error", "error": str(exc)},
                ensure_ascii=False,
            )
