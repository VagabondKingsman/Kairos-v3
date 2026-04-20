"""Vòng lặp suy nghĩ — ReAct Agent Core Loop.

Triển khai vòng lặp ReAct (Thought → Action → Observation):
- 3 tầng quản lý context (microcompact, auto_compact, manual compact)
- Streaming callback cho UI
- Cancellation support
- JSONL trace logging

Luồng chạy chính:
    while iteration < max_iterations:
        1. Layer 1: nen_nhe — xóa tool result cũ (giữ 3 gần nhất)
        2. Layer 2: nen_tu_dong — nếu token > threshold → LLM tóm tắt + nén
        3. Gọi LLM (streaming) với tool definitions
        4. Nếu không có tool_calls → trả kết quả (kết thúc)
        5. Nếu có tool_calls → thực thi tool → append result → lặp lại
"""

from __future__ import annotations

import json
import logging
import os
import time as _time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from processing.research.cong_cu_ai.cong_cu_co_so import SoDoTool
from services.agents.bo_nho_va_tu_duy.bo_nho_ai import BoNhoPhienLam
from services.agents.bo_nho_va_tu_duy.ngu_canh_ai import XayDungNguCanh
from services.agents.cot_loi_bay_dan.luu_tru_phien import LuuTruPhien
from services.llm.quan_ly_token_va_chi_phi import uoc_tinh_token
from services.llm.xu_ly_doan_chat import ChatLLM
from utils.config import cfg

# ---------------------------------------------------------------------------
# Hằng số cấu hình
# ---------------------------------------------------------------------------

RUNS_DIR = Path(__file__).resolve().parents[2] / "runs"
TOKEN_THRESHOLD = cfg.system.token_threshold
KEEP_RECENT = 3          # Số tool results gần nhất giữ lại (Layer 1)
TOOL_RESULT_LIMIT = 10_000  # Giới hạn ký tự cho mỗi tool result
MAX_ITERATIONS_DEFAULT = 50

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lớp 1: Nén nhẹ (microcompact)
# ---------------------------------------------------------------------------


def _nen_nhe(messages: list) -> None:
    """Layer 1: Xóa nội dung tool results cũ, giữ N gần nhất nguyên vẹn.

    Hoạt động in-place trên danh sách messages.

    Args:
        messages: Danh sách messages (sẽ bị thay đổi).
    """
    tool_msgs = [m for m in messages if m.get("role") == "tool"]
    if len(tool_msgs) <= KEEP_RECENT:
        return
    for msg in tool_msgs[:-KEEP_RECENT]:
        content = msg.get("content", "")
        if isinstance(content, str) and len(content) > 100:
            msg["content"] = "[đã xóa]"


def _kiem_tra_tool_thanh_cong(result: str) -> bool:
    """Kiểm tra tool result có lỗi không.

    Args:
        result: JSON string kết quả tool.

    Returns:
        True nếu không có lỗi.
    """
    return '"error"' not in result[:200]


# ---------------------------------------------------------------------------
# VongLapAgent — ReAct Core Loop
# ---------------------------------------------------------------------------


class VongLapAgent:
    """Vòng lặp ReAct Agent chính.

    Attributes:
        registry: Registry công cụ.
        llm: ChatLLM client.
        memory: Bộ nhớ phiên làm việc.
        max_iterations: Số vòng lặp tối đa.
    """

    def __init__(
        self,
        registry: SoDoTool,
        llm: ChatLLM,
        luu_tru_phien: LuuTruPhien,
        id_phien: str,
        id_tac_tu: str,
        memory: Optional[BoNhoPhienLam] = None,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        max_iterations: int = MAX_ITERATIONS_DEFAULT,
    ) -> None:
        """Khởi tạo VongLapAgent.

        Args:
            registry: Registry công cụ.
            llm: ChatLLM client.
            memory: Bộ nhớ phiên (tạo mới nếu không truyền).
            event_callback: Callback event ``(event_type, data) -> None``.
            max_iterations: Số vòng lặp tối đa.
        """
        self.registry = registry
        self.llm = llm
        self.luu_tru_phien = luu_tru_phien
        self.id_phien = id_phien
        self.id_tac_tu = id_tac_tu
        self.memory = memory or BoNhoPhienLam()
        self._event_callback = event_callback
        self.max_iterations = max_iterations
        self._called_ok: set[str] = set()
        self._cancelled: bool = False

    def cancel(self) -> None:
        """Hủy vòng lặp hiện tại.

        Loop sẽ thoát ở lần kiểm tra tiếp theo.
        """
        self._cancelled = True

    def run(
        self,
        user_message: str,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Chạy vòng lặp ReAct đồng bộ.

        Args:
            user_message: Tin nhắn người dùng.
            history: Lịch sử hội thoại trước đó.

        Returns:
            Dict kết quả chứa: status, run_dir, run_id, content, react_trace.
        """
        RUNS_DIR.mkdir(parents=True, exist_ok=True)

        # Tạo thư mục chạy
        if self.memory.run_dir and Path(self.memory.run_dir).exists():
            run_dir = Path(self.memory.run_dir)
        else:
            ts = _time.strftime("%Y%m%d-%H%M%S")
            run_dir = RUNS_DIR / f"run-{ts}"
            run_dir.mkdir(parents=True, exist_ok=True)
            self.memory.run_dir = str(run_dir)

        # Xây dựng context
        context = XayDungNguCanh(self.registry, self.memory)
        messages = context.tao_messages(user_message, history)
        react_trace: List[Dict[str, Any]] = []

        # Khởi tạo trace writer
        self.luu_tru_phien.ghi_dau_vet_ai(self.id_phien, self.id_tac_tu, {"type": "start", "prompt": user_message[:500]})

        iteration = 0
        final_content = ""

        try:
            while iteration < self.max_iterations:
                # Kiểm tra hủy
                if self._cancelled:
                    self.luu_tru_phien.ghi_dau_vet_ai(self.id_phien, self.id_tac_tu, {"type": "cancelled", "iter": iteration})
                    logger.info("VongLapAgent bị hủy bởi người dùng")
                    break

                iteration += 1

                # Lớp 1: Nén nhẹ (mỗi vòng lặp)
                _nen_nhe(messages)

                # Lớp 2: Nén tự động (khi vượt ngưỡng token)
                tokens = uoc_tinh_token(messages)
                if tokens > TOKEN_THRESHOLD:
                    logger.info(
                        "Tự động nén: %d tokens > %d threshold",
                        tokens,
                        TOKEN_THRESHOLD,
                    )
                    self._nen_tu_dong(messages)

                logger.info("ReAct iteration %d/%d", iteration, self.max_iterations)

                # Đầu ra luồng (stream) + thu thập văn bản suy nghĩ
                thinking_chunks: List[str] = []

                def _on_text_chunk(delta: str) -> None:
                    thinking_chunks.append(delta)
                    self._emit("text_delta", {"delta": delta, "iter": iteration})

                response = self.llm.stream_chat(
                    messages,
                    tools=self.registry.lay_dinh_nghia(),
                    on_text_chunk=_on_text_chunk,
                )

                thinking_text = "".join(thinking_chunks)
                if thinking_text:
                    self.luu_tru_phien.ghi_dau_vet_ai(self.id_phien, self.id_tac_tu, {
                        "type": "thinking",
                        "iter": iteration,
                        "content": thinking_text[:2000],
                    })
                    self._emit("thinking_done", {
                        "iter": iteration,
                        "content": thinking_text[:500],
                    })

                # Nếu không có tool calls → đây là câu trả lời cuối
                if not response.co_goi_cong_cu:
                    final_content = response.content or ""
                    self.luu_tru_phien.ghi_dau_vet_ai(self.id_phien, self.id_tac_tu, {
                        "type": "answer",
                        "iter": iteration,
                        "content": final_content[:2000],
                    })
                    react_trace.append({
                        "type": "answer",
                        "content": final_content[:500],
                    })
                    break

                # Thêm tin nhắn của trợ lý với các lệnh gọi công cụ
                messages.append(
                    context.format_assistant_tool_calls(
                        response.tool_calls,
                        content=response.content,
                    )
                )

                compact_requested = False

                # Thực thi từng tool call
                for tc in response.tool_calls:
                    tool_def = self.registry.lay(tc.name)

                    # Lớp 3: nén công cụ - đánh dấu rồi trì hoãn
                    if tc.name == "compact":
                        compact_requested = True
                        messages.append(context.format_tool_result(
                            tc.id, "compact",
                            '{"status":"ok","message":"Đang nén..."}',
                        ))
                        self.luu_tru_phien.ghi_dau_vet_ai(self.id_phien, self.id_tac_tu, {"type": "compact_requested", "iter": iteration})
                        continue

                    # Chặn duplicate call (non-repeatable tools)
                    is_repeatable = tool_def.repeatable if tool_def else False
                    if tc.name in self._called_ok and not is_repeatable:
                        logger.warning("Chặn duplicate: %s", tc.name)
                        skip_msg = json.dumps({
                            "skipped": True,
                            "reason": f"{tc.name} đã hoàn thành. Sử dụng kết quả trước.",
                        }, ensure_ascii=False)
                        messages.append(context.format_tool_result(tc.id, tc.name, skip_msg))
                        self.luu_tru_phien.ghi_dau_vet_ai(self.id_phien, self.id_tac_tu, {"type": "tool_skipped", "iter": iteration, "tool": tc.name})
                        react_trace.append({"type": "tool_skipped", "tool": tc.name})
                        continue

                    # Phát sự kiện + ghi dấu vết
                    self._emit("tool_call", {
                        "tool": tc.name,
                        "arguments": {k: str(v)[:200] for k, v in tc.arguments.items()},
                        "iter": iteration,
                    })
                    self.luu_tru_phien.ghi_dau_vet_ai(self.id_phien, self.id_tac_tu, {
                        "type": "tool_call",
                        "iter": iteration,
                        "tool": tc.name,
                        "args": {k: str(v)[:200] for k, v in tc.arguments.items()},
                    })
                    logger.info("Tool call: %s(%s)", tc.name, list(tc.arguments.keys()))

                    # Auto-inject run_dir
                    if "run_dir" not in tc.arguments and self.memory.run_dir:
                        tc.arguments["run_dir"] = self.memory.run_dir

                    # Thực thi tool
                    t0 = _time.perf_counter()
                    result = self.registry.thuc_thi(tc.name, tc.arguments)
                    elapsed_ms = int((_time.perf_counter() - t0) * 1000)

                    # Cập nhật memory
                    self.memory.tang_dem(tc.name)
                    if _kiem_tra_tool_thanh_cong(result):
                        self._called_ok.add(tc.name)

                    # Thêm kết quả của công cụ
                    status = "ok" if _kiem_tra_tool_thanh_cong(result) else "error"
                    truncated = result[:TOOL_RESULT_LIMIT]
                    messages.append(context.format_tool_result(tc.id, tc.name, truncated))

                    self.luu_tru_phien.ghi_dau_vet_ai(self.id_phien, self.id_tac_tu, {
                        "type": "tool_result",
                        "iter": iteration,
                        "tool": tc.name,
                        "status": status,
                        "elapsed_ms": elapsed_ms,
                        "preview": result[:200],
                    })
                    react_trace.append({
                        "type": "tool_call",
                        "tool": tc.name,
                        "result_preview": result[:200],
                    })
                    self._emit("tool_result", {
                        "tool": tc.name,
                        "status": status,
                        "elapsed_ms": elapsed_ms,
                        "preview": result[:200],
                    })

                # Lớp 3: Nén sau khi tất cả công cụ đã chạy xong
                if compact_requested:
                    logger.info("Nén thủ công được model kích hoạt")
                    self._nen_tu_dong(messages)

        except Exception as exc:
            logger.exception("Lỗi VongLapAgent: %s", exc)
            self.luu_tru_phien.ghi_dau_vet_ai(self.id_phien, self.id_tac_tu, {
                "type": "end",
                "status": "error",
                "reason": str(exc),
                "iterations": iteration,
            })
            return {
                "status": "failed",
                "reason": str(exc),
                "run_dir": str(run_dir),
                "run_id": run_dir.name,
                "content": "",
                "react_trace": react_trace,
            }

        # Xác định trạng thái cuối
        if self._cancelled:
            final_status = "cancelled"
        elif final_content:
            final_status = "success"
        else:
            final_status = "failed"

        self.luu_tru_phien.ghi_dau_vet_ai(self.id_phien, self.id_tac_tu, {"type": "end", "status": final_status, "iterations": iteration})

        return {
            "status": final_status,
            "run_dir": str(run_dir),
            "run_id": run_dir.name,
            "content": final_content,
            "react_trace": react_trace,
        }

    # ------------------------------------------------------------------
    # Lớp 2/3: Nén tự động
    # ------------------------------------------------------------------

    def _nen_tu_dong(
        self,
        messages: list,
    ) -> None:
        """Layer 2/3: LLM tóm tắt rồi nén context.

        Lưu transcript trước khi nén.

        Args:
            messages: Danh sách messages (thay thế in-place).
        """
        # Lưu transcript đầy đủ qua LuuTruPhien
        self.luu_tru_phien.ghi_transcript_nen(self.id_phien, self.id_tac_tu, messages)

        # LLM tóm tắt (không tools, text thuần)
        conv_text = json.dumps(messages[1:], default=str, ensure_ascii=False)[:80000]
        summary_resp = self.llm.chat([
            {
                "role": "user",
                "content": (
                    "Tóm tắt cuộc hội thoại này để duy trì tính liên tục. Bao gồm: "
                    "1) Những gì đã hoàn thành, 2) Trạng thái hiện tại, "
                    "3) Các quyết định quan trọng. "
                    "Ngắn gọn nhưng giữ chi tiết quan trọng.\n\n" + conv_text
                ),
            },
        ])
        summary = summary_resp.content or ""

        tokens_before = uoc_tinh_token(messages)
        self.luu_tru_phien.ghi_dau_vet_ai(self.id_phien, self.id_tac_tu, {
            "type": "compact",
            "tokens_before": tokens_before,
            "summary": summary[:500],
        })
        self._emit("compact", {
            "tokens_before": tokens_before,
            "summary": summary[:200],
        })

        # Thay thế: giữ lời nhắc hệ thống + chèn tóm tắt đã nén
        system_msg = messages[0]
        state_summary = self.memory.to_summary()
        compressed = f"[Hội thoại đã được hệ thống nén để tiết kiệm Token]\n\n{summary}"
        if state_summary and state_summary != "(trạng thái trống)":
            compressed += f"\n\nTrạng thái agent hiện tại:\n{state_summary}"

        messages.clear()
        messages.extend([
            system_msg,
            {"role": "user", "content": compressed},
            {"role": "assistant", "content": "Đã hiểu. Tôi có đầy đủ context từ bản tóm tắt. Tiếp tục."},
        ])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Phát event qua callback.

        Args:
            event_type: Loại event.
            data: Dữ liệu event.
        """
        if self._event_callback:
            try:
                self._event_callback(event_type, data)
            except Exception:
                pass
