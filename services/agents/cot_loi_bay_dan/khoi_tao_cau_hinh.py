"""Swarm Engine — YAML preset loader.

Reads YAML files from the ``cau_hinh_chuyen_gia`` directory and parses them
into Python data models (SwarmRun, AgentConfig, Task).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

# Prefer ruamel.yaml (installed in this project) or fall back to pyyaml
try:
    from ruamel.yaml import YAML
    yaml = YAML(typ='safe')
    def load_yaml(content: str) -> dict:
        return yaml.load(content)
except ImportError:
    import yaml
    def load_yaml(content: str) -> dict:
        return yaml.safe_load(content)

from services.agents.cot_loi_bay_dan.mo_hinh_du_lieu import (
    RunStatus, AgentConfig, SwarmRun, Task, TaskStatus,
)

CONFIG_DIR = Path(__file__).resolve().parents[1] / "cau_hinh_chuyen_gia"


def load_config(preset_name: str) -> dict:
    """Load a YAML preset file by name.

    Args:
        preset_name: Config file name without the ``.yaml`` extension.

    Returns:
        Parsed YAML as a dict.

    Raises:
        FileNotFoundError: If the config file does not exist.
    """
    path = CONFIG_DIR / f"{preset_name}.yaml"
    if not path.exists():
        available = [p.stem for p in CONFIG_DIR.glob("*.yaml")] if CONFIG_DIR.exists() else []
        raise FileNotFoundError(
            f"Config '{preset_name}' not found at {path}. Available: {available}"
        )
    return load_yaml(path.read_text(encoding="utf-8"))


def list_configs() -> list[dict]:
    """Return summary metadata for all available presets.

    Returns:
        List of dicts with keys: name, title, description, agent count, input variables.
    """
    if not CONFIG_DIR.exists():
        return []

    result: list[dict] = []
    for path in sorted(CONFIG_DIR.glob("*.yaml")):
        try:
            data = load_yaml(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        result.append({
            "ten_tep": data.get("name", path.stem),
            "tieu_de": data.get("title", ""),
            "mo_ta": data.get("description", ""),
            "so_luong_tac_tu": len(data.get("agents", [])),
            "bien_dau_vao": data.get("variables", []),
        })

    return result


def build_run_from_config(preset_name: str, user_vars: dict[str, str]) -> SwarmRun:
    """Create a SwarmRun from a YAML preset and user-supplied variables.

    Steps:
        1. Load the YAML file.
        2. Build the AgentConfig list.
        3. Build the Task list.
        4. Generate run ID: "swarm-{YYYYMMDD}-{HHMMSS}-{uuid}".
        5. Return a fully initialised SwarmRun (status = pending).

    Args:
        preset_name: Config file name (e.g. "credit_research_team").
        user_vars: User-supplied variables injected into prompts
            (e.g. {"target": "Vingroup"}).

    Returns:
        Fully initialised SwarmRun object.

    Raises:
        ValueError: If the YAML is malformed.
    """
    data = load_config(preset_name)

    # 1. Parse agent definitions
    agents: list[AgentConfig] = []
    for agent_data in data.get("agents", []):
        agents.append(AgentConfig(
            id=agent_data["id"],
            role=agent_data.get("role", ""),
            system_prompt=agent_data.get("system_prompt", ""),
            tools=agent_data.get("tools", []),
            skills=agent_data.get("skills", []),
            max_iterations=agent_data.get("max_iterations", 25),
            timeout_seconds=agent_data.get("timeout_seconds", 600),
            model_name=agent_data.get("model_name"),
            max_retries=agent_data.get("max_retries", 2),
        ))

    # 2. Parse task definitions
    tasks: list[Task] = []
    for task_data in data.get("tasks", []):
        depends_on = task_data.get("depends_on", [])
        # Tasks with dependencies start as blocked; independent tasks start as pending
        status = TaskStatus.bi_chan if depends_on else TaskStatus.cho_xu_ly

        tasks.append(Task(
            id=task_data["id"],
            agent_id=task_data["agent_id"],
            prompt_template=task_data.get("prompt_template", ""),
            depends_on=depends_on,
            bi_chan_boi=list(depends_on),
            input_from=task_data.get("input_from", {}),
            trang_thai=status,
        ))

    # 3. Generate run ID
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%d-%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    run_id = f"swarm-{ts}-{short_uuid}"

    # 4. Return the assembled SwarmRun
    return SwarmRun(
        id=run_id,
        preset_name=preset_name,
        trang_thai=RunStatus.cho_xu_ly,
        user_vars=user_vars,
        agents=agents,
        tasks=tasks,
        created_at=now.isoformat(),
    )


# Backward-compatible Vietnamese function aliases
tai_cau_hinh = load_config
danh_sach_cau_hinh = list_configs
xay_dung_phien_tu_cau_hinh = build_run_from_config

# Backward-compatible constant alias
THU_MUC_CAU_HINH = CONFIG_DIR
