"""Swarm Engine — Central orchestration loop (Runtime Orchestrator).

Schedules agents across topological layers of the DAG.
Agents within the SAME layer run in PARALLEL via ThreadPoolExecutor.
Layers are executed sequentially.
Execution happens in a background daemon thread so it does not block the UI.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from services.agents.cot_loi_bay_dan.mo_hinh_du_lieu import (
    RunStatus,
    AgentConfig,
    SwarmEvent,
    SwarmRun,
    Task,
    TaskStatus,
    ExecutionResult,
)
from services.agents.cot_loi_bay_dan.khoi_tao_cau_hinh import build_run_from_config
from services.agents.cot_loi_bay_dan.luu_tru_phien import RunStore
from services.agents.cot_loi_bay_dan.quan_ly_nhiem_vu import (
    TaskManager,
    resolve_dependencies,
    compute_layers,
    validate_dag,
)
from services.agents.cot_loi_bay_dan.tac_tu_thuc_thi import run_agent

logger = logging.getLogger(__name__)


class SwarmOrchestrator:
    """DAG-based swarm orchestration engine.

    Manages the full lifecycle of a run: initialisation, scheduling,
    execution, and cancellation. Each run executes in its own background thread.

    Attributes:
        store: RunStore instance for disk persistence.
        max_workers: Maximum number of agents allowed to run concurrently.
    """

    def __init__(self, store: RunStore, max_workers: int = 4) -> None:
        """Initialise the orchestrator.

        Args:
            store: RunStore instance.
            max_workers: Maximum concurrent threads.
        """
        self._store = store
        self._max_workers = max_workers
        self._cancel_events: dict[str, threading.Event] = {}
        self._live_callbacks: dict[str, Callable] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    def start_run(
        self,
        preset_name: str,
        user_vars: dict[str, str],
        live_callback: Callable | None = None,
    ) -> SwarmRun:
        """Launch a swarm run. Returns immediately; execution happens in the background.

        Args:
            preset_name: YAML expert preset file name.
            user_vars: User-supplied variables.
            live_callback: Optional callback to push log events to the UI (SSE).

        Returns:
            The newly created SwarmRun (status = pending).
        """
        run = build_run_from_config(preset_name, user_vars)
        validate_dag(run.danh_sach_nhiem_vu)
        self._store.create_run(run)

        cancel_event = threading.Event()
        with self._lock:
            self._cancel_events[run.id] = cancel_event
            if live_callback is not None:
                self._live_callbacks[run.id] = live_callback

        thread = threading.Thread(
            target=self._core_loop,
            args=(run, cancel_event),
            name=f"swarm-{run.id}",
            daemon=True,
        )
        with self._lock:
            self._threads[run.id] = thread
        thread.start()

        return run

    def cancel_run(self, run_id: str) -> bool:
        """Signal a running session to cancel.

        Args:
            run_id: Run identifier.

        Returns:
            True if the signal was sent, False if the run was not found.
        """
        with self._lock:
            cancel_event = self._cancel_events.get(run_id)
        if cancel_event is None:
            return False
        cancel_event.set()
        return True

    def shutdown(self, timeout: float = 3.0) -> None:
        """Cancel all active runs and wait for their threads to finish.

        Call this on application shutdown to ensure data is flushed to disk.
        """
        with self._lock:
            run_ids = list(self._cancel_events.keys())
            active_threads = list(self._threads.values())

        logger.info(f"Stopping {len(run_ids)} swarm run(s)...")
        for run_id in run_ids:
            self.cancel_run(run_id)

        for thread in active_threads:
            if thread.is_alive():
                thread.join(timeout=timeout)

    def _emit(self, run_id: str, event: SwarmEvent) -> None:
        """Persist event to disk and forward to the live callback if registered."""
        try:
            self._store.append_event(run_id, event)
        except Exception:
            logger.warning(f"Failed to log event for run {run_id}", exc_info=True)

        with self._lock:
            cb = self._live_callbacks.get(run_id)
        if cb is not None:
            try:
                cb(event)
            except Exception:
                logger.warning(f"Live callback error for run {run_id}", exc_info=True)

    def _make_event(
        self,
        event_type: str,
        agent_id: str | None = None,
        task_id: str | None = None,
        data: dict | None = None,
    ) -> SwarmEvent:
        """Convenience factory for SwarmEvent objects."""
        return SwarmEvent(
            type=event_type,
            agent_id=agent_id,
            task_id=task_id,
            data=data or {},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _core_loop(self, run: SwarmRun, cancel_event: threading.Event) -> None:
        """Core orchestration loop (runs in a background daemon thread).

        Steps:
            1. Transition run to RUNNING.
            2. Initialise TaskManager and persist all tasks.
            3. Use Kahn's algorithm to compute execution layers.
            4. For each layer:
               a. Check for cancellation request.
               b. Submit all tasks in the layer to the thread pool (parallel).
               c. Collect results and unblock downstream tasks.
            5. Finalise run state (COMPLETED / FAILED / CANCELLED).
        """
        run_id = run.id
        run_dir = self._store.run_dir(run_id)

        # 1. Transition to RUNNING
        run.trang_thai = RunStatus.dang_chay
        self._store.update_run(run)
        self._emit(run_id, self._make_event("phien_bat_dau"))

        # 2. Initialise task store
        task_mgr = TaskManager(run_dir)
        for task in run.danh_sach_nhiem_vu:
            task_mgr.save_task(task)

        # Quick agent lookup
        agent_map: dict[str, AgentConfig] = {a.id: a for a in run.danh_sach_tac_tu}

        # 3. Compute execution layers
        layers = compute_layers(run.danh_sach_nhiem_vu)
        task_summaries: dict[str, str] = {}
        all_succeeded = True

        try:
            for layer_idx, task_ids in enumerate(layers):
                # a. Check for cancellation
                if cancel_event.is_set():
                    logger.info(f"Run {run_id} cancelled at layer {layer_idx}")
                    self._cancel_remaining(task_mgr, run.danh_sach_nhiem_vu)
                    all_succeeded = False
                    break

                self._emit(
                    run_id,
                    self._make_event(
                        "tang_bat_dau",
                        data={"vi_tri_tang": layer_idx, "nhiem_vu": task_ids},
                    ),
                )

                # b. Execute the entire layer in parallel
                layer_results = self._execute_layer(
                    run=run,
                    task_mgr=task_mgr,
                    agent_map=agent_map,
                    task_ids=task_ids,
                    upstream_summaries=task_summaries,
                    run_dir=run_dir,
                    cancel_event=cancel_event,
                )

                # c. Process results
                for tid, result in layer_results.items():
                    run.tong_token_dau_vao += result.token_dau_vao
                    run.tong_token_dau_ra += result.token_dau_ra

                    if result.trang_thai in ("hoan_thanh", "timeout", "token_limit"):
                        task_summaries[tid] = result.tom_tat
                        completed_at = datetime.now(timezone.utc).isoformat()

                        task_mgr.update_status(
                            tid, TaskStatus.hoan_thanh,
                            summary=result.tom_tat,
                            completed_at=completed_at,
                            artifacts=result.duong_dan_tai_lieu,
                            worker_iterations=result.so_vong_lap,
                        )
                        # Unblock downstream tasks
                        resolve_dependencies(run_dir / "tasks", tid)

                        self._emit(
                            run_id,
                            self._make_event(
                                "task_completed", task_id=tid,
                                data={"status": result.trang_thai, "iterations": result.so_vong_lap},
                            ),
                        )
                    else:
                        all_succeeded = False
                        task_mgr.update_status(
                            tid, TaskStatus.that_bai,
                            error=result.loi or "Unknown error",
                            completed_at=datetime.now(timezone.utc).isoformat(),
                            worker_iterations=result.so_vong_lap,
                        )
                        self._emit(
                            run_id,
                            self._make_event("task_failed", task_id=tid, data={"error": result.loi}),
                        )
                        # Signal cancellation to avoid hanging dependent tasks
                        cancel_event.set()

        except Exception as exc:
            logger.error(f"Run {run_id} encountered a fatal error", exc_info=True)
            all_succeeded = False
            self._emit(run_id, self._make_event("run_error", data={"error": str(exc)}))

        # 5. Finalise run
        final_status = (
            RunStatus.bi_huy if cancel_event.is_set()
            else RunStatus.hoan_thanh if all_succeeded
            else RunStatus.that_bai
        )

        run.trang_thai = final_status
        run.hoan_thanh_luc = datetime.now(timezone.utc).isoformat()
        run.danh_sach_nhiem_vu = task_mgr.load_all()

        # Use the last layer's first completed task as the final report
        if task_summaries and layers:
            for tid in layers[-1]:
                if tid in task_summaries:
                    run.bao_cao_cuoi_cung = task_summaries[tid]
                    break

        self._store.update_run(run)
        self._emit(run_id, self._make_event("phien_ket_thuc", data={"trang_thai": final_status.value}))

        with self._lock:
            self._cancel_events.pop(run_id, None)
            self._live_callbacks.pop(run_id, None)
            self._threads.pop(run_id, None)

    def _execute_layer(
        self,
        run: SwarmRun,
        task_mgr: TaskManager,
        agent_map: dict[str, AgentConfig],
        task_ids: list[str],
        upstream_summaries: dict[str, str],
        run_dir: Path,
        cancel_event: threading.Event,
    ) -> dict[str, ExecutionResult]:
        """Execute all tasks in one layer in parallel via ThreadPoolExecutor.

        Supports automatic retry if a worker reports failure.
        """
        layer_results: dict[str, ExecutionResult] = {}

        def _event_relay(event: SwarmEvent) -> None:
            self._emit(run.id, event)

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures: dict[Future[ExecutionResult], str] = {}

            for tid in task_ids:
                task = task_mgr.load_task(tid)
                agent_config = agent_map.get(task.id_tac_tu)

                if agent_config is None:
                    layer_results[tid] = ExecutionResult(
                        status="that_bai", summary="",
                        error=f"Agent '{task.id_tac_tu}' not found in YAML config",
                    )
                    continue

                task_mgr.update_status(
                    tid, TaskStatus.dang_thuc_thi,
                    started_at=datetime.now(timezone.utc).isoformat(),
                )
                self._emit(
                    run.id,
                    self._make_event("nhiem_vu_bat_dau", agent_id=agent_config.id, task_id=tid),
                )

                # Gather upstream context for this task
                input_context: dict[str, str] = {}
                for context_key, source_id in task.lay_dau_vao_tu.items():
                    if source_id in upstream_summaries:
                        input_context[context_key] = upstream_summaries[source_id]

                future = executor.submit(
                    self._run_with_retry,
                    agent_config=agent_config,
                    task=task,
                    upstream_context=input_context,
                    user_vars=run.bien_nguoi_dung,
                    run_dir=run_dir,
                    event_callback=_event_relay,
                    run_id=run.id,
                )
                futures[future] = tid

            # Collect results
            for future in as_completed(futures):
                tid = futures[future]
                try:
                    layer_results[tid] = future.result()
                except Exception as exc:
                    logger.error(f"Worker for task {tid} raised an exception", exc_info=True)
                    layer_results[tid] = ExecutionResult(status="that_bai", summary="", error=str(exc))

        return layer_results

    def _run_with_retry(
        self,
        agent_config: AgentConfig,
        task: Task,
        upstream_context: dict[str, str],
        user_vars: dict[str, str],
        run_dir: Path,
        event_callback: Callable[[SwarmEvent], None] | None,
        run_id: str,
    ) -> ExecutionResult:
        """Run an agent worker and automatically retry on failure."""
        max_retries = agent_config.so_lan_thu_lai_toi_da
        total_input = 0
        total_output = 0
        result: ExecutionResult | None = None

        for attempt in range(max_retries + 1):
            if attempt > 0:
                self._emit(
                    run_id,
                    self._make_event(
                        "nhiem_vu_thu_lai",
                        agent_id=agent_config.id,
                        task_id=task.id,
                        data={"lan_thu": attempt + 1, "toi_da": max_retries},
                    ),
                )
                logger.info(f"Retrying task {task.id} (attempt {attempt + 1}/{max_retries + 1})")

            result = run_agent(
                agent_config=agent_config,
                task=task,
                upstream_summaries=upstream_context,
                user_vars=user_vars,
                store=self._store,
                run_id=run_id,
                event_callback=event_callback,
            )

            total_input += result.token_dau_vao
            total_output += result.token_dau_ra

            if result.trang_thai != "that_bai":
                # Success (or timeout / token limit) — stop retrying
                break

        # Merge accumulated token counts into the final result
        if result:
            data = result.model_dump(by_alias=True)
            data["input_tokens"] = total_input
            data["output_tokens"] = total_output
            return ExecutionResult.model_validate(data)

        return ExecutionResult(status="that_bai", summary="", error="Retry exhausted.")

    def _cancel_remaining(self, task_mgr: TaskManager, tasks: list[Task]) -> None:
        """Mark all incomplete tasks as CANCELLED."""
        for task in tasks:
            if task.trang_thai not in (TaskStatus.hoan_thanh, TaskStatus.that_bai):
                try:
                    task_mgr.update_status(task.id, TaskStatus.bi_huy)
                except Exception:
                    logger.warning(f"Failed to mark task {task.id} as cancelled", exc_info=True)


# Backward-compatible Vietnamese class alias
VongLapThucThi = SwarmOrchestrator
