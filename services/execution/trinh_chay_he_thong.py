"""Trading Session Runner — A10.

Orchestrates the full loop of a live/demo trading session:
    1. Initialize StateMachine (A10) for the agent
    2. Subscribe to OHLCV from A00 Event Bus
    3. Run analysis → signal → order placement loop
    4. Monitor SL/TP/Trailing Stop on each candle
    5. Write session logs to A11

Usage:
    from services.execution.trinh_chay_he_thong import TradingSession

    session = TradingSession(
        config=session_cfg,
        executor=executor_instance,
        on_finished=my_callback,
    )
    session.start()
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from services.execution.mo_hinh_trang_thai import StateMachine, AgentState
from services.execution.su_kien_phien import SessionEventManager

logger = logging.getLogger("A10_TradingSession")


@dataclass
class SessionConfig:
    """Configuration for a trading session."""
    session_id: str
    agent_name: str = "kairos-agent"
    check_interval_s: float = 1.0   # Seconds between SL/TP checks
    auto_reconnect: bool = True
    log_to_a11: bool = True


class TradingSession:
    """Manages the full lifecycle of a trading session.

    Features:
    - State machine lifecycle (idle → scanning → trading → monitoring)
    - Auto-subscribe to Event Bus for real-time OHLCV
    - Check SL/TP/Trailing Stop after each candle
    - Full session logging to A11
    """

    def __init__(
        self,
        config: SessionConfig,
        executor: Any,                    # A10 executor instance
        on_finished: Optional[Callable] = None,
    ) -> None:
        self.config = config
        self.executor = executor
        self.on_finished = on_finished

        # State machine
        self.state_machine = StateMachine(agent_id=config.session_id)

        # SL/TP manager
        self.event_manager = SessionEventManager(
            on_triggered=self._handle_triggered_event
        )

        # Internal state
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._ohlcv_sub_id: Optional[str] = None
        self._current_prices: Dict[str, float] = {}
        self._start_time: Optional[float] = None

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the trading session."""
        if self._running:
            logger.warning("[%s] Session already running!", self.config.session_id)
            return

        self._running = True
        self._start_time = time.time()
        self.state_machine.transition(AgentState.scanning, reason="Session started")

        # Subscribe to OHLCV from Event Bus
        self._subscribe_ohlcv()

        # Start monitoring loop in background thread
        self._thread = threading.Thread(
            target=self._monitoring_loop,
            name=f"Session-{self.config.session_id}",
            daemon=True,
        )
        self._thread.start()
        logger.info("[%s] Trading session started.", self.config.session_id)

    def stop(self, reason: str = "User stopped") -> None:
        """Stop the trading session."""
        if not self._running:
            return

        self._running = False
        self._unsubscribe_ohlcv()

        if self.state_machine.current_state != AgentState.idle:
            self.state_machine.force_reset_to_idle(reason=reason)

        logger.warning("[%s] Session stopped: %s", self.config.session_id, reason)

        if self.on_finished:
            try:
                self.on_finished(self.get_report())
            except Exception as exc:
                logger.exception("on_finished callback error: %s", exc)

    # ------------------------------------------------------------------
    # Event Bus integration
    # ------------------------------------------------------------------

    def _subscribe_ohlcv(self) -> None:
        """Subscribe to OHLCV events from A00 Event Bus."""
        try:
            from utils.bus.ket_noi_pubsub import get_default_pubsub
            from utils.bus.bo_dinh_tuyen_tin_nhan import TOPIC_OHLCV
            pubsub = get_default_pubsub()
            self._ohlcv_sub_id = pubsub.subscribe(
                TOPIC_OHLCV,
                self._handle_ohlcv,
                name=f"session_{self.config.session_id}",
            )
            logger.debug("[%s] Subscribed to OHLCV bus.", self.config.session_id)
        except Exception as exc:
            logger.warning("[%s] Could not subscribe to OHLCV bus: %s", self.config.session_id, exc)

    def _unsubscribe_ohlcv(self) -> None:
        """Unsubscribe from OHLCV when session ends."""
        if self._ohlcv_sub_id:
            try:
                from utils.bus.ket_noi_pubsub import get_default_pubsub
                pubsub = get_default_pubsub()
                pubsub.unsubscribe(self._ohlcv_sub_id)
            except Exception:
                pass
            self._ohlcv_sub_id = None

    def _handle_ohlcv(self, event: Any) -> None:
        """Callback for each new OHLCV candle from A00."""
        payload = event.data if hasattr(event, "data") else event
        symbol = payload.get("symbol", "")
        close = payload.get("close")
        if symbol and close:
            self._current_prices[symbol] = float(close)

    # ------------------------------------------------------------------
    # Monitoring loop
    # ------------------------------------------------------------------

    def _monitoring_loop(self) -> None:
        """Background thread: SL/TP/Trailing Stop monitoring."""
        logger.debug("[%s] SL/TP monitoring loop started.", self.config.session_id)
        while self._running:
            try:
                if self._current_prices:
                    self.event_manager.check_all(
                        current_prices=self._current_prices,
                        increment_bars=False,  # Bar count increments via OHLCV events
                    )
            except Exception as exc:
                logger.exception("[%s] Monitoring loop error: %s", self.config.session_id, exc)
            time.sleep(self.config.check_interval_s)
        logger.debug("[%s] Monitoring loop ended.", self.config.session_id)

    def _handle_triggered_event(self, event: Any) -> None:
        """Handle triggered SL/TP/Trailing event → send close order."""
        logger.info(
            "[%s] EVENT TRIGGERED: %s %s PnL=%.2f%%",
            self.config.session_id, event.event_type.value,
            event.ticker, event.pnl_pct,
        )
        if self.executor:
            close_signal = {
                "symbol": event.ticker,
                "action": "CLOSE",
                "position_id": event.position_id,
                "price": event.trigger_price,
                "reason": event.event_type.value,
            }
            try:
                self.executor.process_signal(close_signal)
            except Exception as exc:
                logger.exception("[%s] Error closing position: %s", self.config.session_id, exc)

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def get_report(self) -> Dict[str, Any]:
        """Session summary report."""
        runtime = 0.0
        if self._start_time:
            runtime = time.time() - self._start_time
        return {
            "session_id": self.config.session_id,
            "state": self.state_machine.current_state.value,
            "runtime_s": round(runtime, 1),
            "monitored_positions": self.event_manager.position_count(),
            "current_prices": self._current_prices.copy(),
        }


# Backward-compatible aliases
PhienGiaoDich = TradingSession
CauHinhPhien = SessionConfig

__all__ = ["TradingSession", "SessionConfig", "PhienGiaoDich", "CauHinhPhien"]
