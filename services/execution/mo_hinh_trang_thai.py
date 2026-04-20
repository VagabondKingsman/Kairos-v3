"""State Machine — Agent lifecycle state machine.

Manages agent lifecycle: Idle → Scanning → Trading → Monitoring.
Publishes events to a00 Event Bus on state transitions.

Valid states:
    idle        → idle, waiting
    scanning    → scanning the market
    signal      → signal detected, preparing entry
    trading     → executing order
    monitoring  → monitoring open position
    error       → error occurred, needs handling

Valid transitions:
    idle        → scanning
    scanning    → idle | signal
    signal      → trading | idle (cancel)
    trading     → monitoring | error
    monitoring  → idle (close) | error
    error       → idle (reset)
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State enum
# ---------------------------------------------------------------------------

class AgentState(str, Enum):
    """Valid agent states."""
    idle        = "idle"
    scanning    = "scanning"
    signal      = "signal"
    trading     = "trading"
    monitoring  = "monitoring"
    error       = "error"


# Valid transitions: {from → [list_of_to]}
_VALID_TRANSITIONS: Dict[AgentState, List[AgentState]] = {
    AgentState.idle:       [AgentState.scanning],
    AgentState.scanning:   [AgentState.idle, AgentState.signal],
    AgentState.signal:     [AgentState.trading, AgentState.idle],
    AgentState.trading:    [AgentState.monitoring, AgentState.error],
    AgentState.monitoring: [AgentState.idle, AgentState.error],
    AgentState.error:      [AgentState.idle],
}


# ---------------------------------------------------------------------------
# State transition event dataclass
# ---------------------------------------------------------------------------

@dataclass
class StateTransitionEvent:
    """Data for a single state transition.

    Attributes:
        from_state: Previous state.
        to_state: New state.
        timestamp: Unix timestamp of transition.
        reason: Human-readable reason for transition.
        data: Additional payload.
    """
    from_state: AgentState
    to_state: AgentState
    timestamp: float
    reason: str = ""
    data: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# StateMachine
# ---------------------------------------------------------------------------

class StateMachine:
    """Thread-safe agent lifecycle state machine.

    Publishes events to a00 Event Bus on transitions.
    Keeps transition history for debugging and auditing.

    Example:
        sm = StateMachine(agent_id="agent-crypto-01")
        sm.transition(AgentState.scanning, reason="Starting H4 scan")
        sm.transition(AgentState.signal, data={"ticker": "BTC-USDT"})
        sm.transition(AgentState.trading)
        sm.transition(AgentState.monitoring)
        sm.transition(AgentState.idle, reason="Position closed TP")
    """

    MAX_HISTORY = 200

    def __init__(
        self,
        agent_id: str,
        initial_state: AgentState = AgentState.idle,
        event_callback: Optional[Callable[[StateTransitionEvent], None]] = None,
    ) -> None:
        """
        Args:
            agent_id: Unique agent identifier.
            initial_state: Starting state.
            event_callback: Called after each transition.
        """
        self._agent_id = agent_id
        self._state: AgentState = initial_state
        self._lock = threading.RLock()
        self._history: List[StateTransitionEvent] = []
        self._callback = event_callback
        self._prev_state: Optional[AgentState] = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current_state(self) -> AgentState:
        """Current state (thread-safe)."""
        with self._lock:
            return self._state

    @property
    def previous_state(self) -> Optional[AgentState]:
        """State before the last transition (None if no transition yet)."""
        with self._lock:
            return self._prev_state

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def history(self) -> List[StateTransitionEvent]:
        """Copy of transition history (thread-safe)."""
        with self._lock:
            return list(self._history)

    # ------------------------------------------------------------------
    # Core: transition
    # ------------------------------------------------------------------

    def transition(
        self,
        new_state: AgentState,
        *,
        reason: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Transition to a new state.

        Validates legality before transitioning. Fires callback and a00 event.

        Args:
            new_state: Target state.
            reason: Description of why the transition is happening.
            data: Additional payload (e.g. ticker, price).

        Returns:
            True if transition succeeded.

        Raises:
            ValueError: If the transition is not valid.
        """
        with self._lock:
            old_state = self._state

            # Allow self-transition (no-op)
            if old_state == new_state:
                return True

            # Validate
            valid_targets = _VALID_TRANSITIONS.get(old_state, [])
            if new_state not in valid_targets:
                raise ValueError(
                    f"Invalid transition [{old_state} → {new_state}] "
                    f"for agent '{self._agent_id}'. "
                    f"Valid targets: {[t.value for t in valid_targets]}"
                )

            # Execute transition
            self._prev_state = old_state
            self._state = new_state

            event = StateTransitionEvent(
                from_state=old_state,
                to_state=new_state,
                timestamp=time.time(),
                reason=reason,
                data=data or {},
            )

            # Maintain history
            self._history.append(event)
            if len(self._history) > self.MAX_HISTORY:
                self._history = self._history[-self.MAX_HISTORY:]

        logger.info(
            "[%s] State transition: %s → %s | %s",
            self._agent_id, old_state.value, new_state.value, reason,
        )

        # Fire callbacks outside lock to avoid deadlock
        self._fire_callback(event)
        self._publish_to_bus(event)

        return True

    def force_reset_to_idle(self, reason: str = "reset") -> None:
        """Force reset to idle regardless of current state (emergency reset)."""
        with self._lock:
            old_state = self._state
            self._prev_state = old_state
            self._state = AgentState.idle
            event = StateTransitionEvent(
                from_state=old_state,
                to_state=AgentState.idle,
                timestamp=time.time(),
                reason=f"FORCE_RESET: {reason}",
            )
            self._history.append(event)

        logger.warning("[%s] FORCE_RESET: %s → idle", self._agent_id, old_state.value)
        self._fire_callback(event)
        self._publish_to_bus(event)

    def get_info(self) -> Dict[str, Any]:
        """Summary of current state machine status."""
        with self._lock:
            return {
                "agent_id": self._agent_id,
                "state": self._state.value,
                "previous_state": self._prev_state.value if self._prev_state else None,
                "transition_count": len(self._history),
                "last_transition": {
                    "from": self._history[-1].from_state.value,
                    "to": self._history[-1].to_state.value,
                    "timestamp": self._history[-1].timestamp,
                    "reason": self._history[-1].reason,
                } if self._history else None,
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fire_callback(self, event: StateTransitionEvent) -> None:
        if self._callback:
            try:
                self._callback(event)
            except Exception as exc:
                logger.exception("StateMachine callback error: %s", exc)

    def _publish_to_bus(self, event: StateTransitionEvent) -> None:
        """Publish event to a00 Event Bus if available."""
        try:
            from utils.bus.ket_noi_pubsub import lay_pubsub_mac_dinh
            from utils.bus.bo_dinh_tuyen_tin_nhan import TOPIC_TRANG_THAI_AGENT
            pubsub = lay_pubsub_mac_dinh()
            pubsub.phat(
                TOPIC_TRANG_THAI_AGENT,
                {
                    "agent_id": self._agent_id,
                    "state": event.to_state.value,
                    "previous_state": event.from_state.value,
                    "timestamp": event.timestamp,
                    "reason": event.reason,
                    **event.data,
                },
                nguon=f"state_machine:{self._agent_id}",
            )
        except Exception:
            pass  # Bus not available → skip, no error


# Backward-compatible aliases
TrangThaiAgent = AgentState
SuKienChuyenTiep = StateTransitionEvent
MayTrangThai = StateMachine
