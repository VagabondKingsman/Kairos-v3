"""Swarm Engine — Task manager and DAG algorithms.

Each task is stored independently as tasks/task-{id}.json with full CRUD support.
Provides graph algorithms: dependency resolution, cycle detection, and
topological layering.
"""

from __future__ import annotations

import threading
from collections import defaultdict, deque
from pathlib import Path

from services.agents.cot_loi_bay_dan.mo_hinh_du_lieu import Task, TaskStatus


class TaskManager:
    """Per-task file-system store.

    Each task is persisted at ``run_dir/tasks/task-{id}.json``.

    Attributes:
        run_dir: Root directory of the current run.
    """

    def __init__(self, run_dir: Path) -> None:
        """Initialise the task manager.

        Args:
            run_dir: Path to .kairos/runs/{run_id}/
        """
        self.run_dir = run_dir
        self._tasks_dir = run_dir / "tasks"
        self._tasks_dir.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()

    def _task_path(self, task_id: str) -> Path:
        """Return the file path for a task.

        Args:
            task_id: Task identifier.

        Returns:
            Path to the task JSON file.
        """
        return self._tasks_dir / f"task-{task_id}.json"

    def save_task(self, task: Task) -> None:
        """Save or overwrite a task's state (atomic write).

        Args:
            task: Task object to persist.
        """
        path = self._task_path(task.id)
        tmp_path = path.with_suffix(".tmp")
        with self._write_lock:
            tmp_path.write_text(task.model_dump_json(indent=2, by_alias=True), encoding="utf-8")
            tmp_path.replace(path)

    def load_task(self, task_id: str) -> Task:
        """Load a task by ID.

        Args:
            task_id: Task identifier.

        Returns:
            Task object.

        Raises:
            FileNotFoundError: If the task file does not exist.
        """
        path = self._task_path(task_id)
        if not path.exists():
            raise FileNotFoundError(f"Task file not found: {path}")
        return Task.model_validate_json(path.read_text(encoding="utf-8"))

    def load_all(self) -> list[Task]:
        """Load all tasks in the current run, sorted by ID.

        Returns:
            List of Task objects.
        """
        tasks: list[Task] = []
        for path in sorted(self._tasks_dir.glob("task-*.json")):
            try:
                task = Task.model_validate_json(path.read_text(encoding="utf-8"))
                tasks.append(task)
            except Exception:
                continue
        return tasks

    def update_status(
        self, task_id: str, status: TaskStatus, **kwargs
    ) -> Task:
        """Update a task's status and any extra fields.

        Args:
            task_id: Task identifier.
            status: New status (TaskStatus).
            **kwargs: Extra fields to update (tom_tat, loi, hoan_thanh_luc,
                tai_lieu_dinh_kem, etc.).

        Returns:
            Updated Task object.
        """
        task = self.load_task(task_id)
        data = task.model_dump(by_alias=True)

        data["trang_thai"] = status
        for key, value in kwargs.items():
            # Map via alias if key matches a model field, otherwise use directly
            if key in data or key in task.model_fields:
                field_info = task.model_fields.get(key)
                alias_key = field_info.alias if field_info and field_info.alias else key
                data[alias_key] = value

        updated = Task.model_validate(data)
        self.save_task(updated)
        return updated


# ---------------------------------------------------------------------------
# Backward-compatible Vietnamese aliases for class and method names
# ---------------------------------------------------------------------------

QuanLyNhiemVu = TaskManager

# Attach Vietnamese method aliases
TaskManager.luu_nhiem_vu = TaskManager.save_task
TaskManager.tai_nhiem_vu = TaskManager.load_task
TaskManager.tai_tat_ca = TaskManager.load_all
TaskManager.cap_nhat_trang_thai = TaskManager.update_status


def resolve_dependencies(tasks_dir: Path, completed_task_id: str) -> list[str]:
    """Remove a completed task ID from ``bi_chan_boi`` lists across all tasks.

    Scans every task file in the directory. If a task is blocked by
    ``completed_task_id``, that ID is removed. When ``bi_chan_boi`` becomes
    empty the task transitions to pending.

    Args:
        tasks_dir: Path to the ``tasks/`` directory.
        completed_task_id: ID of the task that just finished.

    Returns:
        IDs of tasks that were just unblocked and can now be queued.
    """
    unblocked: list[str] = []

    for path in tasks_dir.glob("task-*.json"):
        try:
            task = Task.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        if completed_task_id not in task.bi_chan_boi:
            continue

        # Remove the completed task from the blocked-by list
        new_blocked = [tid for tid in task.bi_chan_boi if tid != completed_task_id]
        data = task.model_dump(by_alias=True)
        data["bi_chan_boi"] = new_blocked

        # Transition to pending when fully unblocked
        if not new_blocked and task.trang_thai == TaskStatus.bi_chan:
            data["trang_thai"] = TaskStatus.cho_xu_ly
            unblocked.append(task.id)

        updated = Task.model_validate(data)

        # Atomic write (no class lock available at module level)
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(updated.model_dump_json(indent=2, by_alias=True), encoding="utf-8")
        tmp_path.replace(path)

    return unblocked


def validate_dag(tasks: list[Task]) -> None:
    """DFS cycle detection on the task dependency graph.

    Ensures no task is part of a circular dependency chain
    (e.g. A waits for B, B waits for C, C waits for A).

    Args:
        tasks: List of Task objects.

    Raises:
        ValueError: If a cycle is detected; the message names the cycle path.
    """
    graph: dict[str, list[str]] = {t.id: list(t.phu_thuoc_vao) for t in tasks}
    all_ids = {t.id for t in tasks}

    # Check for references to non-existent tasks
    for task in tasks:
        for dep in task.phu_thuoc_vao:
            if dep not in all_ids:
                raise ValueError(f"Task '{task.id}' depends on non-existent task '{dep}'")

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {tid: WHITE for tid in all_ids}
    path: list[str] = []

    def dfs(node: str) -> None:
        color[node] = GRAY
        path.append(node)

        for neighbour in graph.get(node, []):
            if color[neighbour] == GRAY:
                cycle_start = path.index(neighbour)
                cycle = path[cycle_start:] + [neighbour]
                raise ValueError(f"Cycle detected in DAG configuration: {' -> '.join(cycle)}")

            if color[neighbour] == WHITE:
                dfs(neighbour)

        path.pop()
        color[node] = BLACK

    for tid in all_ids:
        if color[tid] == WHITE:
            dfs(tid)


def compute_layers(tasks: list[Task]) -> list[list[str]]:
    """Kahn's algorithm for topological layer decomposition.

    Groups independent tasks into the same layer so they can run in parallel.
    Tasks within a layer have no mutual dependencies.

    Args:
        tasks: Task list (must be cycle-free).

    Returns:
        List of layers; each layer is a list of task IDs that can run concurrently.

    Raises:
        ValueError: If the graph contains a cycle.
    """
    in_degree: dict[str, int] = {t.id: 0 for t in tasks}
    dependents: dict[str, list[str]] = defaultdict(list)

    for task in tasks:
        in_degree[task.id] = len(task.phu_thuoc_vao)
        for dep in task.phu_thuoc_vao:
            dependents[dep].append(task.id)

    # Seed the queue with all tasks that have no dependencies
    queue: deque[str] = deque(tid for tid, deg in in_degree.items() if deg == 0)

    layers: list[list[str]] = []
    processed = 0

    while queue:
        current_layer: list[str] = list(queue)
        queue.clear()
        layers.append(current_layer)
        processed += len(current_layer)

        for tid in current_layer:
            for downstream in dependents[tid]:
                in_degree[downstream] -= 1
                if in_degree[downstream] == 0:
                    queue.append(downstream)

    if processed != len(tasks):
        raise ValueError(
            f"Graph contains a cycle: only processed {processed}/{len(tasks)} tasks."
        )

    return layers


# Backward-compatible Vietnamese function aliases
giai_quyet_phu_thuoc = resolve_dependencies
kiem_tra_do_thi_dag = validate_dag
phan_tang_thuc_thi = compute_layers
