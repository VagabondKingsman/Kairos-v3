"""Agent mailbox — file-system-based message passing between swarm agents.

Each agent owns an independent inbox directory. Messages are sorted by timestamp
and carry only summaries plus artifact paths to avoid loading large payloads into
the LLM context window.

Directory layout:
    inboxes/{recipient_id}/msg-{timestamp}-{uuid_short}.json
"""

from __future__ import annotations

import uuid
from pathlib import Path
from services.agents.cot_loi_bay_dan.mo_hinh_du_lieu import SwarmMessage


class AgentMailbox:
    """File-system-backed message store for the swarm.

    Each agent has its own subdirectory at ``run_dir/inboxes/{agent_id}/``.
    Messages are stored as JSON files with a timestamp prefix for easy ordering.

    Attributes:
        run_dir: Root directory of the current run.
    """

    def __init__(self, run_dir: Path) -> None:
        """Initialise the mailbox.

        Args:
            run_dir: Path to the run directory (e.g. ``.kairos/runs/{run_id}/``).
        """
        self.run_dir = run_dir
        self._inboxes_dir = run_dir / "inboxes"
        self._inboxes_dir.mkdir(parents=True, exist_ok=True)

    def send(self, message: SwarmMessage) -> None:
        """Deliver a message to the recipient's inbox.

        Uses write-then-rename for concurrency safety: writes to a ``.tmp`` file
        first, then atomically renames it to ``.json``.

        Args:
            message: SwarmMessage to deliver.
        """
        inbox_dir = self._inboxes_dir / message.nguoi_nhan
        inbox_dir.mkdir(parents=True, exist_ok=True)

        # Replace colons and dots to produce a filesystem-safe timestamp string
        safe_ts = message.thoi_gian.replace(":", "-").replace(".", "-")
        uid = uuid.uuid4().hex[:8]
        filename = f"msg-{safe_ts}-{uid}.json"

        msg_path = inbox_dir / filename
        tmp_path = msg_path.with_suffix(".tmp")

        tmp_path.write_text(message.model_dump_json(indent=2), encoding="utf-8")
        # Atomic rename (single filesystem operation on most OSes)
        tmp_path.replace(msg_path)

    def read_inbox(self, recipient: str) -> list[SwarmMessage]:
        """Read all messages in an agent's inbox, sorted by timestamp ascending.

        Args:
            recipient: Recipient agent ID.

        Returns:
            List of SwarmMessage objects in chronological order.
        """
        inbox_dir = self._inboxes_dir / recipient
        if not inbox_dir.exists():
            return []

        messages: list[SwarmMessage] = []
        for path in sorted(inbox_dir.glob("msg-*.json")):
            try:
                msg = SwarmMessage.model_validate_json(path.read_text(encoding="utf-8"))
                messages.append(msg)
            except Exception:
                # Skip corrupted files to avoid crashing the agent
                continue

        # Re-sort by the timestamp inside the JSON for accuracy
        messages.sort(key=lambda m: m.thoi_gian)
        return messages

    def read_from(self, recipient: str, sender: str) -> list[SwarmMessage]:
        """Filter and return messages sent by a specific agent.

        Args:
            recipient: Recipient agent ID.
            sender: Sender agent ID to filter by.

        Returns:
            List of SwarmMessage objects from ``sender``, sorted chronologically.
        """
        return [m for m in self.read_inbox(recipient) if m.nguoi_gui == sender]


# Backward-compatible Vietnamese class alias
HopThuGiaoTiep = AgentMailbox

# Vietnamese method aliases
AgentMailbox.gui_tin_nhan = AgentMailbox.send
AgentMailbox.doc_hop_thu = AgentMailbox.read_inbox
AgentMailbox.doc_tu_tac_tu = AgentMailbox.read_from
