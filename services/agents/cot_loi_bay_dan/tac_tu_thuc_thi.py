"""Swarm Engine — Worker node (Agent executor).

Implements the ReAct (Reasoning and Acting) loop for a single agent,
built on top of ChatLLM. Keeps the agent core fully self-contained.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Any

from services.agents.cot_loi_bay_dan.luu_tru_phien import RunStore

from services.agents.cot_loi_bay_dan.mo_hinh_du_lieu import (
    AgentConfig,
    SwarmEvent,
    Task,
    ExecutionResult,
)

from services.llm.xu_ly_doan_chat import ChatLLM

logger = logging.getLogger(__name__)

DEFAULT_MAX_ITERATIONS = 50
DEFAULT_TIMEOUT = 300
ESTIMATED_TOKEN_LIMIT = 60_000

# Backward-compatible Vietnamese constant aliases
SO_VONG_LAP_TOI_DA_MAC_DINH = DEFAULT_MAX_ITERATIONS
THOI_GIAN_CHO_MAC_DINH = DEFAULT_TIMEOUT
GIOI_HAN_TOKEN_UOC_TINH = ESTIMATED_TOKEN_LIMIT


def _emit_event(
    callback: Callable[[SwarmEvent], None] | None,
    event_type: str,
    agent_id: str,
    task_id: str,
    data: dict | None = None,
) -> None:
    """Fire a swarm event via callback for real-time SSE streaming.

    Args:
        callback: Optional event callback; does nothing if None.
        event_type: Event type string.
        agent_id: ID of the agent that triggered the event.
        task_id: ID of the related task.
        data: Optional extra payload dict.
    """
    if callback is None:
        return
    event = SwarmEvent(
        type=event_type,
        agent_id=agent_id,
        task_id=task_id,
        data=data or {},
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    try:
        callback(event)
    except Exception:
        logger.warning(f"Error emitting event {event_type}", exc_info=True)


def build_agent_prompt(
    agent_config: AgentConfig,
    upstream_summaries: dict[str, str],
    skills_description: str,
) -> str:
    """Build the system prompt with role, upstream context, and available skills.

    Args:
        agent_config: Agent role configuration.
        upstream_summaries: Results from upstream dependency tasks.
        skills_description: Text description of available skill tools.

    Returns:
        Fully assembled prompt string to inject into the LLM.
    """
    # NOTE: The prompt sections below are intentionally in Vietnamese because
    # they are user-facing AI instructions that define the agent's language
    # and response style for Vietnamese financial analysis.

    upstream_block = ""
    if upstream_summaries:
        parts = []
        for key, summary in upstream_summaries.items():
            parts.append(f"### {key}\n{summary}")
        upstream_block = (
            "## Dữ Liệu Đầu Vào (Từ các chuyên gia phân tích trước)\n\n"
            + "\n\n".join(parts)
        )

    # Substitute {upstream_context} placeholder if present in the template
    main_prompt = agent_config.prompt_he_thong.replace("{upstream_context}", upstream_block)

    sections = [
        f"## Vai Trò Của Bạn\n\n{agent_config.vai_tro}",
        main_prompt,
    ]

    if skills_description and skills_description != "(Không có kỹ năng)":
        sections.append(
            f"## Các Kỹ Năng / Công Cụ Khả Dụng\n\n{skills_description}"
        )

    sections.append(
        "## Quy tắc Thực thi (ReAct Framework)\n\n"
        "Bạn có GIỚI HẠN TUYỆT ĐỐI là 20 lần gọi công cụ. Vượt quá sẽ bị ngắt kết nối. Hãy làm việc tối ưu.\n\n"
        "**Giai đoạn 1 — Lên Kế Hoạch (0 lần gọi công cụ):** Trước khi làm gì, hãy vạch ra 3-5 gạch đầu dòng kế hoạch.\n\n"
        "**Giai đoạn 2 — Thực Thi (≤15 lần gọi công cụ):**\n"
        "- Dùng công cụ đọc dữ liệu hoặc quét API theo logic được giao.\n"
        "- Nếu gặp lỗi lập trình, đọc thông báo lỗi, sửa mã và chạy lại. Tối đa thử lại 2 lần.\n\n"
        "**Giai đoạn 3 — Tổng Kết (0 lần gọi công cụ):**\n"
        "- Viết báo cáo cuối cùng của bạn bằng ngôn ngữ Markdown trực tiếp trong câu trả lời.\n"
        "- BẮT BUỘC đưa ra các con số, kết luận rõ ràng, sắc bén mang tính chất ra quyết định đầu tư.\n"
        "- TRẢ LỜI HOÀN TOÀN BẰNG TIẾNG VIỆT CHUYÊN NGÀNH TÀI CHÍNH."
    )

    return "\n\n".join(sections)


def run_agent(
    agent_config: AgentConfig,
    task: Task,
    upstream_summaries: dict[str, str],
    user_vars: dict[str, str],
    store: RunStore,
    run_id: str,
    event_callback: Callable[[SwarmEvent], None] | None = None,
) -> ExecutionResult:
    """Execute a task via the ReAct (Reasoning and Acting) loop.

    Connects to the LLM, passes context, and iterates tool calls until the
    LLM produces a final answer or the iteration/time limit is reached.

    Args:
        agent_config: Agent role definition.
        task: Task to execute.
        upstream_summaries: Results from upstream dependency tasks.
        user_vars: User-supplied variables.
        store: Centralized run store for artifact persistence.
        run_id: Current run identifier.
        event_callback: Optional real-time event callback for SSE.

    Returns:
        ExecutionResult with status, summary, and output artifact paths.
    """
    agent_id = agent_config.id
    task_id = task.id
    max_iterations = agent_config.so_vong_lap_toi_da or DEFAULT_MAX_ITERATIONS
    timeout = agent_config.thoi_gian_cho_toi_da or DEFAULT_TIMEOUT

    _emit_event(event_callback, "task_started", agent_id, task_id)

    # =========================================================================
    # STEP 1: INITIALISE TOOLS AND PROMPT
    # =========================================================================

    try:
        llm = ChatLLM(
            model_name=agent_config.ten_mo_hinh,
            provider_name=agent_config.ten_nha_cung_cap,
        )
    except Exception as exc:
        error = f"LLM init error ({agent_config.ten_nha_cung_cap} / {agent_config.ten_mo_hinh}): {exc}"
        _emit_event(event_callback, "task_failed", agent_id, task_id, {"error": error})
        return ExecutionResult(status="that_bai", summary="", iterations=0, error=error)

    class Registry_Mock:
        def get_definitions(self): return []
        def execute(self, name, args): return "TOOL RESULT"

    registry = Registry_Mock()
    skills_description = "(Không có kỹ năng)"  # Will be loaded from a09 module later

    system_prompt = build_agent_prompt(agent_config, upstream_summaries, skills_description)

    try:
        user_prompt = task.mau_prompt.format(**user_vars)
    except KeyError as exc:
        error = f"Missing variable in prompt template: {exc}"
        _emit_event(event_callback, "task_failed", agent_id, task_id, {"error": error})
        return ExecutionResult(status="that_bai", summary="", iterations=0, error=error)

    chat_history: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Ensure the artifact directory exists before collecting files
    artifact_dir = store.run_dir(run_id) / "artifacts" / agent_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # STEP 2: REACT LOOP
    # =========================================================================
    t0 = time.monotonic()
    total_input_tokens = 0
    total_output_tokens = 0
    last_content = ""

    for iteration in range(max_iterations):

        # 1. Check timeout
        elapsed = time.monotonic() - t0
        if elapsed > timeout:
            summary = last_content or f"Agent stopped: exceeded {timeout}s time limit."
            _emit_event(event_callback, "tac_tu_qua_gio", agent_id, task_id)
            store.write_artifact(run_id, agent_id, "bao_cao_tom_tat.md", summary)
            return ExecutionResult(
                status="timeout", summary=summary, iterations=iteration,
                input_tokens=total_input_tokens, output_tokens=total_output_tokens,
            )

        # 2. Call LLM
        try:
            remaining = max(10, int(timeout - elapsed))
            response = llm.chat(chat_history, tools=registry.get_definitions(), timeout=remaining)

            summary = response.content or ""
            has_tool_calls = response.co_goi_cong_cu

            # Approximate token count until ChatLLM exposes usage natively
            total_input_tokens += len(str(chat_history)) // 4
            total_output_tokens += len(summary) // 4

        except Exception as exc:
            error = f"LLM call error at iteration {iteration}: {exc}"
            _emit_event(event_callback, "task_failed", agent_id, task_id, {"error": error})
            return ExecutionResult(
                status="that_bai", summary=last_content, error=error, iterations=iteration,
            )

        # 3. Handle response
        last_content = summary

        # No tool calls → LLM has reached a final answer
        if not has_tool_calls:
            _emit_event(
                event_callback, "tac_tu_hoan_thanh", agent_id, task_id,
                {"vong_lap": iteration + 1},
            )
            store.write_artifact(run_id, agent_id, "bao_cao_tom_tat.md", summary)
            return ExecutionResult(
                status="hoan_thanh",
                summary=summary,
                artifact_paths=_collect_artifacts(artifact_dir),
                iterations=iteration + 1,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
            )

        # Tool calls present → execute tools and feed results back into history
        # (tool execution logic not yet implemented — using mock registry)

    # Iteration limit reached
    final_summary = last_content or f"Agent reached maximum iterations ({max_iterations})"
    _emit_event(event_callback, "tac_tu_gioi_han_vong_lap", agent_id, task_id)
    store.write_artifact(run_id, agent_id, "bao_cao_tom_tat.md", final_summary)
    return ExecutionResult(
        status="hoan_thanh",
        summary=final_summary,
        artifact_paths=_collect_artifacts(artifact_dir),
        iterations=max_iterations,
    )


def _collect_artifacts(artifact_dir: Path) -> list[str]:
    """Return paths of all files produced by an agent."""
    if not artifact_dir.exists():
        return []
    return [str(p) for p in artifact_dir.iterdir() if p.is_file()]


# Backward-compatible Vietnamese function aliases
chay_tac_tu = run_agent
xay_dung_prompt_tac_tu = build_agent_prompt
_phat_su_kien = _emit_event
_thu_thap_file = _collect_artifacts
