"""Swarm Engine core module for the Kairos Quant System.

Provides the multi-agent orchestration infrastructure:
- Agent mailbox management.
- Run state persistence to disk.
- YAML preset loader.
- DAG-based task management.
- Parallel multi-threaded execution loop.
"""

from services.agents.cot_loi_bay_dan.mo_hinh_du_lieu import (
    # English names (primary)
    TaskStatus,
    RunStatus,
    AgentConfig,
    Task,
    SwarmMessage,
    SwarmEvent,
    SwarmRun,
    ExecutionResult,
    # Vietnamese backward-compat aliases
    TrangThaiNhiemVu,
    TrangThaiPhien,
    CauHinhTacTu,
    NhiemVu,
    TinNhanBayDan,
    SuKienBayDan,
    PhienChayBayDan,
    KetQuaThucThi,
)
from services.agents.cot_loi_bay_dan.hop_thu_giao_tiep import AgentMailbox, HopThuGiaoTiep
from services.agents.cot_loi_bay_dan.luu_tru_phien import RunStore, LuuTruPhien
from services.agents.cot_loi_bay_dan.khoi_tao_cau_hinh import (
    load_config, list_configs, build_run_from_config,
    tai_cau_hinh, danh_sach_cau_hinh, xay_dung_phien_tu_cau_hinh,
)
from services.agents.cot_loi_bay_dan.quan_ly_nhiem_vu import (
    TaskManager, resolve_dependencies, validate_dag, compute_layers,
    QuanLyNhiemVu, giai_quyet_phu_thuoc, kiem_tra_do_thi_dag, phan_tang_thuc_thi,
)
from services.agents.cot_loi_bay_dan.tac_tu_thuc_thi import run_agent, chay_tac_tu
from services.agents.cot_loi_bay_dan.vong_lap_thuc_thi import SwarmOrchestrator, VongLapThucThi

__all__ = [
    # English names
    "TaskStatus", "RunStatus", "AgentConfig", "Task",
    "SwarmMessage", "SwarmEvent", "SwarmRun", "ExecutionResult",
    "AgentMailbox", "RunStore",
    "load_config", "list_configs", "build_run_from_config",
    "TaskManager", "resolve_dependencies", "validate_dag", "compute_layers",
    "run_agent",
    "SwarmOrchestrator",
    # Vietnamese backward-compat aliases
    "TrangThaiNhiemVu", "TrangThaiPhien", "CauHinhTacTu", "NhiemVu",
    "TinNhanBayDan", "SuKienBayDan", "PhienChayBayDan", "KetQuaThucThi",
    "HopThuGiaoTiep", "LuuTruPhien",
    "tai_cau_hinh", "danh_sach_cau_hinh", "xay_dung_phien_tu_cau_hinh",
    "QuanLyNhiemVu", "giai_quyet_phu_thuoc", "kiem_tra_do_thi_dag", "phan_tang_thuc_thi",
    "chay_tac_tu",
    "VongLapThucThi",
]
