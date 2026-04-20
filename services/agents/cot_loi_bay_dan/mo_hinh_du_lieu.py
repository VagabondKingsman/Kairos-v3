"""Swarm Engine — Data models.

Defines all Pydantic models shared by run_store, task_manager, agent_mailbox, etc.
Uses str-based Enums to ensure JSON serialization compatibility.
"""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task lifecycle state.

    Transitions:
        cho_xu_ly -> bi_chan -> dang_thuc_thi -> hoan_thanh | that_bai | bi_huy
    """

    cho_xu_ly = "cho_xu_ly"
    bi_chan = "bi_chan"
    dang_thuc_thi = "dang_thuc_thi"
    hoan_thanh = "hoan_thanh"
    that_bai = "that_bai"
    bi_huy = "bi_huy"


class RunStatus(str, Enum):
    """Swarm run lifecycle state.

    Transitions:
        cho_xu_ly -> dang_chay -> hoan_thanh | that_bai | bi_huy
    """

    cho_xu_ly = "cho_xu_ly"
    dang_chay = "dang_chay"
    hoan_thanh = "hoan_thanh"
    that_bai = "that_bai"
    bi_huy = "bi_huy"


class AgentConfig(BaseModel):
    """Role definition and configuration for a swarm agent.

    Parsed from YAML presets in cau_hinh_chuyen_gia. Describes the agent's
    identity, permitted tools, and execution constraints.

    Attributes:
        id: Unique identifier, e.g. "macro_analyst".
        vai_tro: Role description string.
        prompt_he_thong: System prompt injected into the LLM.
        cong_cu: List of permitted tool names.
        ky_nang: List of skill modules to load.
        so_vong_lap_toi_da: Maximum ReAct loop iterations.
        thoi_gian_cho_toi_da: Execution time limit in seconds.
        ten_nha_cung_cap: LLM provider override (None = use default).
        ten_mo_hinh: LLM model override (None = use default).
        so_lan_thu_lai_toi_da: Maximum retry attempts on failure.
    """

    id: str
    vai_tro: str = Field(alias="role")
    prompt_he_thong: str = Field(alias="system_prompt")
    cong_cu: list[str] = Field(default_factory=list, alias="tools")
    ky_nang: list[str] = Field(default_factory=list, alias="skills")
    so_vong_lap_toi_da: int = Field(default=25, alias="max_iterations")
    thoi_gian_cho_toi_da: int = Field(default=300, alias="timeout_seconds")
    ten_nha_cung_cap: str | None = Field(default=None, alias="provider_name")
    ten_mo_hinh: str | None = Field(default=None, alias="model_name")
    so_lan_thu_lai_toi_da: int = Field(default=2, alias="max_retries")


class Task(BaseModel):
    """A task node in the swarm DAG.

    Each task is assigned to one agent. Dependencies are declared via
    ``phu_thuoc_vao``; ``bi_chan_boi`` tracks unfinished upstream tasks at runtime.

    Attributes:
        id: Task identifier (e.g. "task-macro-analysis").
        id_tac_tu: ID of the agent that will execute this task.
        mau_prompt: YAML prompt template with ``{var}`` substitution.
        phu_thuoc_vao: List of upstream task IDs (immutable).
        bi_chan_boi: Upstream task IDs not yet complete (decrements at runtime).
        lay_dau_vao_tu: Map for pulling upstream summaries (e.g. {"macro": "task-macro"}).
        trang_thai: Current task status.
        tom_tat: Text summary after completion.
        tai_lieu_dinh_kem: List of output artifact file paths.
        loi: Error message on failure.
        bat_dau_luc: ISO timestamp when execution started.
        hoan_thanh_luc: ISO timestamp on completion/failure.
        so_vong_lap_thuc_te: Actual ReAct iterations executed.
    """

    id: str
    id_tac_tu: str = Field(alias="agent_id")
    mau_prompt: str = Field(alias="prompt_template")
    phu_thuoc_vao: list[str] = Field(default_factory=list, alias="depends_on")
    bi_chan_boi: list[str] = Field(default_factory=list)
    lay_dau_vao_tu: dict[str, str] = Field(default_factory=dict, alias="input_from")
    trang_thai: TaskStatus = TaskStatus.cho_xu_ly
    tom_tat: str | None = None
    tai_lieu_dinh_kem: list[str] = Field(default_factory=list)
    loi: str | None = None
    bat_dau_luc: str | None = None
    hoan_thanh_luc: str | None = None
    so_vong_lap_thuc_te: int = 0


class SwarmMessage(BaseModel):
    """A message exchanged between agents via the mailbox.

    Carries only summaries and artifact paths to avoid overflowing the LLM context window.

    Attributes:
        id: Unique message identifier.
        loai_tin_nhan: Category (e.g. "task_result", "data_request").
        nguoi_gui: Sending agent ID.
        nguoi_nhan: Receiving agent ID.
        noi_dung: Summary text.
        duong_dan_tai_lieu: Paths to detailed report files.
        thoi_gian: ISO 8601 timestamp.
    """

    id: str
    loai_tin_nhan: str = Field(alias="type")
    nguoi_gui: str = Field(alias="from_agent")
    nguoi_nhan: str = Field(alias="to")
    noi_dung: str = Field(alias="content")
    duong_dan_tai_lieu: list[str] = Field(default_factory=list, alias="artifact_paths")
    thoi_gian: str = Field(alias="timestamp")


class SwarmEvent(BaseModel):
    """A swarm log entry.

    Appended to events.jsonl; supports SSE streaming and audit trails.

    Attributes:
        loai_su_kien: Event type (e.g. "run_started", "task_completed").
        id_tac_tu: Related agent ID (if applicable).
        id_nhiem_vu: Related task ID (if applicable).
        du_lieu: Arbitrary JSON payload associated with the event.
        thoi_gian: ISO timestamp.
    """

    loai_su_kien: str = Field(alias="type")
    id_tac_tu: str | None = Field(default=None, alias="agent_id")
    id_nhiem_vu: str | None = Field(default=None, alias="task_id")
    du_lieu: dict = Field(default_factory=dict, alias="data")
    thoi_gian: str = Field(alias="timestamp")


class SwarmRun(BaseModel):
    """Overall state of a swarm execution session.

    Persisted as .kairos/runs/{id}/run.json. This is the aggregate root.

    Attributes:
        id: Run UUID.
        ten_cau_hinh: Expert group preset invoked (e.g. "credit_research_team").
        trang_thai: Current run status.
        bien_nguoi_dung: User-supplied input variables (e.g. {"target": "VN30"}).
        danh_sach_tac_tu: All agent definitions participating in this run.
        danh_sach_nhiem_vu: All tasks in this run.
        tao_luc: Creation timestamp.
        hoan_thanh_luc: Completion/failure timestamp.
        bao_cao_cuoi_cung: Final synthesized report.
        tong_token_dau_vao: Total input tokens consumed.
        tong_token_dau_ra: Total output tokens produced.
    """

    id: str
    ten_cau_hinh: str = Field(alias="preset_name")
    trang_thai: RunStatus = RunStatus.cho_xu_ly
    bien_nguoi_dung: dict[str, str] = Field(default_factory=dict, alias="user_vars")
    danh_sach_tac_tu: list[AgentConfig] = Field(default_factory=list, alias="agents")
    danh_sach_nhiem_vu: list[Task] = Field(default_factory=list, alias="tasks")
    tao_luc: str = Field(alias="created_at")
    hoan_thanh_luc: str | None = Field(default=None, alias="completed_at")
    bao_cao_cuoi_cung: str | None = Field(default=None, alias="final_report")
    tong_token_dau_vao: int = Field(default=0, alias="total_input_tokens")
    tong_token_dau_ra: int = Field(default=0, alias="total_output_tokens")


class ExecutionResult(BaseModel):
    """Return value after a worker node completes its ReAct loop.

    Attributes:
        trang_thai: "hoan_thanh", "that_bai", "timeout", or "token_limit".
        tom_tat: Execution summary text.
        duong_dan_tai_lieu: Report files produced by the agent.
        so_vong_lap: Actual ReAct iterations executed.
        loi: Error message if failed.
        token_dau_vao: Tokens consumed.
        token_dau_ra: Tokens produced.
    """

    trang_thai: str = Field(alias="status")
    tom_tat: str = Field(alias="summary")
    duong_dan_tai_lieu: list[str] = Field(default_factory=list, alias="artifact_paths")
    so_vong_lap: int = Field(default=0, alias="iterations")
    loi: str | None = Field(default=None, alias="error")
    token_dau_vao: int = Field(default=0, alias="input_tokens")
    token_dau_ra: int = Field(default=0, alias="output_tokens")


# ---------------------------------------------------------------------------
# Backward-compatible Vietnamese aliases
# ---------------------------------------------------------------------------

TrangThaiNhiemVu = TaskStatus
TrangThaiPhien = RunStatus
CauHinhTacTu = AgentConfig
NhiemVu = Task
TinNhanBayDan = SwarmMessage
SuKienBayDan = SwarmEvent
PhienChayBayDan = SwarmRun
KetQuaThucThi = ExecutionResult
