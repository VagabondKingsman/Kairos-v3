"""Swarm Engine — Run state persistence.

Persists PhienChayBayDan (SwarmRun) state to the file system.

Directory layout:
    .kairos/runs/{run_id}/
    ├── run.json         # Run state (atomic writes)
    ├── events.jsonl     # Append-only event log
    ├── tasks/           # Per-task state files
    ├── inboxes/         # Agent mailboxes
    ├── artifacts/       # Agent reports and outputs
    ├── traces/          # LLM reasoning traces
    └── transcripts/     # Compressed chat histories
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from services.agents.cot_loi_bay_dan.mo_hinh_du_lieu import SwarmEvent, SwarmRun


class RunStore:
    """File-system store for SwarmRun state.

    Each run lives under ``base_dir/{run_id}/``.
    run.json uses atomic writes (write to .tmp, then rename) to prevent
    corruption under concurrent access or unexpected shutdown.
    events.jsonl is append-only for SSE streaming and audit purposes.

    Attributes:
        base_dir: Root storage directory (e.g. .kairos/runs).
    """

    def __init__(self, base_dir: Path) -> None:
        """Initialise the run store.

        Args:
            base_dir: Root storage path (e.g. Path(".kairos/runs")).
        """
        self.base_dir = base_dir
        self._write_lock = threading.Lock()

    def run_dir(self, run_id: str) -> Path:
        """Return the directory path for a specific run.

        Args:
            run_id: Run identifier.

        Returns:
            Path to the run directory.
        """
        return self.base_dir / run_id

    def create_run(self, run: SwarmRun) -> Path:
        """Create the directory structure for a new run and write initial state.

        Args:
            run: SwarmRun object to persist.

        Returns:
            Path to the newly created run directory.

        Raises:
            FileExistsError: If the run directory already exists.
        """
        run_path = self.run_dir(run.id)
        run_path.mkdir(parents=True, exist_ok=False)

        # Create subdirectories
        (run_path / "tasks").mkdir()
        (run_path / "inboxes").mkdir()
        (run_path / "artifacts").mkdir()
        (run_path / "traces").mkdir()
        (run_path / "transcripts").mkdir()

        # Write initial run state
        self._atomic_write(run_path / "run.json", run.model_dump_json(indent=2, by_alias=True))
        return run_path

    def load_run(self, run_id: str) -> SwarmRun | None:
        """Load the state of an existing run.

        Args:
            run_id: Run identifier.

        Returns:
            SwarmRun object, or None if not found.
        """
        run_file = self.run_dir(run_id) / "run.json"
        if not run_file.exists():
            return None
        return SwarmRun.model_validate_json(run_file.read_text(encoding="utf-8"))

    def update_run(self, run: SwarmRun) -> None:
        """Atomically update run state on disk.

        Args:
            run: Updated SwarmRun object.

        Raises:
            FileNotFoundError: If the run directory does not exist.
        """
        run_path = self.run_dir(run.id)
        if not run_path.exists():
            raise FileNotFoundError(f"Run directory not found: {run_path}")
        self._atomic_write(run_path / "run.json", run.model_dump_json(indent=2, by_alias=True))

    def list_runs(self, limit: int = 50) -> list[SwarmRun]:
        """List runs sorted by creation time (newest first).

        Args:
            limit: Maximum number of runs to return.

        Returns:
            List of SwarmRun objects.
        """
        if not self.base_dir.exists():
            return []

        runs: list[SwarmRun] = []
        for entry in self.base_dir.iterdir():
            if not entry.is_dir():
                continue

            run_file = entry / "run.json"
            if run_file.exists():
                try:
                    run = SwarmRun.model_validate_json(run_file.read_text(encoding="utf-8"))
                    runs.append(run)
                except (json.JSONDecodeError, ValueError):
                    # Skip corrupted files
                    continue

        runs.sort(key=lambda r: r.tao_luc, reverse=True)
        return runs[:limit]

    def append_event(self, run_id: str, event: SwarmEvent) -> None:
        """Append an event to the run's events.jsonl log.

        Args:
            run_id: Run identifier.
            event: SwarmEvent to log.

        Raises:
            FileNotFoundError: If the run directory does not exist.
        """
        run_path = self.run_dir(run_id)
        if not run_path.exists():
            raise FileNotFoundError(f"Run directory not found: {run_path}")

        event_log = run_path / "events.jsonl"
        with self._write_lock:
            with event_log.open("a", encoding="utf-8") as f:
                f.write(event.model_dump_json(by_alias=True) + "\n")

    def read_events(self, run_id: str, skip: int = 0) -> list[SwarmEvent]:
        """Read the event log, with optional offset for SSE streaming.

        Args:
            run_id: Run identifier.
            skip: Number of leading lines to skip (for resumable streaming).

        Returns:
            List of SwarmEvent objects.
        """
        event_log = self.run_dir(run_id) / "events.jsonl"
        if not event_log.exists():
            return []

        events: list[SwarmEvent] = []
        lines = event_log.read_text(encoding="utf-8").strip().splitlines()

        for line in lines[skip:]:
            stripped = line.strip()
            if stripped:
                try:
                    events.append(SwarmEvent.model_validate_json(stripped))
                except Exception:
                    continue

        return events

    def write_trace(self, run_id: str, agent_id: str, trace_data: dict) -> None:
        """Append an LLM reasoning trace line for an agent.

        Args:
            run_id: Run identifier.
            agent_id: Agent ID (e.g. "macro_analyst").
            trace_data: Trace payload dict (a ``ts`` field is added automatically).
        """
        run_path = self.run_dir(run_id)
        traces_dir = run_path / "traces"
        traces_dir.mkdir(parents=True, exist_ok=True)

        trace_file = traces_dir / f"{agent_id}_trace.jsonl"

        if "ts" not in trace_data:
            trace_data["ts"] = time.time()

        with self._write_lock:
            with trace_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(trace_data, ensure_ascii=False) + "\n")

    def write_transcript(self, run_id: str, agent_id: str, messages: list) -> None:
        """Persist the full chat history before it is compressed due to token overflow.

        Args:
            run_id: Run identifier.
            agent_id: Agent ID.
            messages: List of chat messages to save.
        """
        run_path = self.run_dir(run_id)
        transcripts_dir = run_path / "transcripts"
        transcripts_dir.mkdir(parents=True, exist_ok=True)

        timestamp = int(time.time())
        transcript_file = transcripts_dir / f"{agent_id}_{timestamp}.jsonl"

        with self._write_lock:
            with transcript_file.open("w", encoding="utf-8") as f:
                for msg in messages:
                    f.write(json.dumps(msg, default=str, ensure_ascii=False) + "\n")

    def write_artifact(self, run_id: str, agent_id: str, filename: str, content: str) -> Path:
        """Save an agent's report or analysis output (atomic write).

        Args:
            run_id: Run identifier.
            agent_id: Agent ID.
            filename: Output file name (e.g. 'summary_report.md').
            content: Text content to write.

        Returns:
            Absolute path to the saved file.
        """
        run_path = self.run_dir(run_id)
        artifact_dir = run_path / "artifacts" / agent_id
        artifact_dir.mkdir(parents=True, exist_ok=True)

        file_path = artifact_dir / filename
        self._atomic_write(file_path, content)
        return file_path

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write content atomically: write to .tmp then rename.

        Prevents file corruption when another process is reading or when
        the process is killed mid-write.

        Args:
            path: Target file path.
            content: Content to write.
        """
        tmp_path = path.with_suffix(".tmp")
        with self._write_lock:
            tmp_path.write_text(content, encoding="utf-8")
            tmp_path.replace(path)


# ---------------------------------------------------------------------------
# Backward-compatible Vietnamese aliases
# ---------------------------------------------------------------------------

LuuTruPhien = RunStore

RunStore.duong_dan_phien = RunStore.run_dir
RunStore.tao_phien = RunStore.create_run
RunStore.tai_phien = RunStore.load_run
RunStore.cap_nhat_phien = RunStore.update_run
RunStore.danh_sach_phien = RunStore.list_runs
RunStore.ghi_nhat_ky = RunStore.append_event
RunStore.doc_nhat_ky = RunStore.read_events
RunStore.ghi_dau_vet_ai = RunStore.write_trace
RunStore.ghi_transcript_nen = RunStore.write_transcript
RunStore.ghi_artifact = RunStore.write_artifact
RunStore._ghi_nguyen_tu = RunStore._atomic_write
