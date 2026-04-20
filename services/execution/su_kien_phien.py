"""Session Events — SL/TP/Trailing Stop event handlers.

Handles Stop Loss, Take Profit, and Trailing Stop events during live trading.
Publishes events to a00 Event Bus when triggered.

Usage:
    manager = SessionEventManager()

    # Add position to monitor
    manager.add_position(
        position_id="pos-btc-01",
        ticker="BTC-USDT",
        direction=1,           # 1=long, -1=short
        entry_price=65000.0,
        stop_loss=63000.0,
        take_profit=70000.0,
        trailing_stop_pct=2.0, # 2% trailing stop
    )

    # Check against current prices
    triggered = manager.check_all(current_prices={"BTC-USDT": 62500.0})
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & Data Classes
# ---------------------------------------------------------------------------

class SessionEventType(str, Enum):
    """Types of session events."""
    stop_loss       = "stop_loss"
    take_profit     = "take_profit"
    trailing_stop   = "trailing_stop"
    time_exit       = "time_exit"    # Exit after N bars


@dataclass
class PositionConfig:
    """Monitoring configuration for a single position.

    Attributes:
        position_id: Unique position ID.
        ticker: Asset symbol.
        direction: 1=long, -1=short.
        entry_price: Entry price.
        stop_loss: Stop loss level (None = no SL).
        take_profit: Take profit level (None = no TP).
        trailing_stop_pct: Trailing stop % (None = no trailing).
        entry_time: Unix timestamp of entry.
        max_bars: Exit after N bars (None = no limit).
    """
    position_id: str
    ticker: str
    direction: int  # 1=long, -1=short
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop_pct: Optional[float] = None  # %
    entry_time: float = field(default_factory=time.time)
    max_bars: Optional[int] = None

    # Internal trailing stop tracking
    _highest_price: float = field(init=False, repr=False, default=0.0)
    _lowest_price: float = field(init=False, repr=False, default=float("inf"))
    _bar_count: int = field(init=False, repr=False, default=0)

    def __post_init__(self) -> None:
        self._highest_price = self.entry_price
        self._lowest_price = self.entry_price


@dataclass
class TriggeredSessionEvent:
    """Data for a triggered session event.

    Attributes:
        position_id: ID of the triggered position.
        ticker: Asset symbol.
        event_type: Type of event that triggered.
        trigger_price: Price at trigger time.
        sl_tp_level: The SL/TP level that was set.
        pnl_pct: Estimated P&L (%).
        timestamp: Unix timestamp of trigger.
        note: Additional description.
    """
    position_id: str
    ticker: str
    event_type: SessionEventType
    trigger_price: float
    sl_tp_level: float
    pnl_pct: float
    timestamp: float = field(default_factory=time.time)
    note: str = ""


# ---------------------------------------------------------------------------
# SessionEventManager
# ---------------------------------------------------------------------------

class SessionEventManager:
    """Manages SL/TP/Trailing Stop events for a portfolio of positions.

    Features:
    - Add/remove positions to monitor
    - Check SL, TP, Trailing Stop against current prices
    - Trailing stop self-adjusts to highest/lowest price
    - Publishes events to a00 bus when triggered
    - Calls on_triggered callback to handle position close

    Usage:
        manager = SessionEventManager(
            on_triggered=lambda e: close_position(e.position_id, e.trigger_price)
        )
    """

    def __init__(
        self,
        on_triggered: Optional[Callable[[TriggeredSessionEvent], None]] = None,
    ) -> None:
        self._positions: Dict[str, PositionConfig] = {}
        self._on_triggered = on_triggered

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------

    def add_position(
        self,
        position_id: str,
        ticker: str,
        direction: int,
        entry_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        trailing_stop_pct: Optional[float] = None,
        max_bars: Optional[int] = None,
    ) -> None:
        """Add a position to the monitoring list.

        Args:
            position_id: Unique ID.
            ticker: Asset symbol.
            direction: 1=long, -1=short.
            entry_price: Entry price.
            stop_loss: SL level (None = no SL).
            take_profit: TP level (None = no TP).
            trailing_stop_pct: Trailing % (None = no trailing).
            max_bars: Exit after N bars.
        """
        config = PositionConfig(
            position_id=position_id,
            ticker=ticker,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop_pct=trailing_stop_pct,
            max_bars=max_bars,
        )
        self._positions[position_id] = config
        logger.info(
            "Add position: %s %s @%.4f SL=%.4f TP=%.4f trailing=%s%%",
            ticker, "LONG" if direction == 1 else "SHORT", entry_price,
            stop_loss or 0, take_profit or 0, trailing_stop_pct,
        )

    def remove_position(self, position_id: str) -> bool:
        """Remove a position from the monitoring list."""
        if position_id in self._positions:
            del self._positions[position_id]
            return True
        return False

    def position_count(self) -> int:
        """Number of positions currently monitored."""
        return len(self._positions)

    # ------------------------------------------------------------------
    # Event checking
    # ------------------------------------------------------------------

    def check_all(
        self,
        current_prices: Dict[str, float],
        increment_bars: bool = True,
    ) -> List[TriggeredSessionEvent]:
        """Check all positions against current prices.

        Args:
            current_prices: Dict {ticker → current_price}.
            increment_bars: True to increment bar counter for each position.

        Returns:
            List of triggered events (may be empty).
        """
        triggered_list: List[TriggeredSessionEvent] = []
        triggered_ids: List[str] = []

        for position_id, cfg in list(self._positions.items()):
            current_price = current_prices.get(cfg.ticker)
            if current_price is None:
                continue

            if increment_bars:
                cfg._bar_count += 1

            # Update trailing high/low
            if cfg.direction == 1:  # Long
                cfg._highest_price = max(cfg._highest_price, current_price)
            else:  # Short
                cfg._lowest_price = min(cfg._lowest_price, current_price)

            event = self._check_one_position(cfg, current_price)
            if event:
                triggered_list.append(event)
                triggered_ids.append(position_id)
                self._publish_event(event)
                if self._on_triggered:
                    try:
                        self._on_triggered(event)
                    except Exception as exc:
                        logger.exception("on_triggered callback error: %s", exc)

        # Remove triggered positions
        for position_id in triggered_ids:
            self.remove_position(position_id)

        return triggered_list

    def _check_one_position(
        self,
        cfg: PositionConfig,
        current_price: float,
    ) -> Optional[TriggeredSessionEvent]:
        """Check a single position for trigger conditions."""

        def make_event(event_type: SessionEventType, sl_tp_level: float, note: str = "") -> TriggeredSessionEvent:
            pnl_pct = cfg.direction * (current_price - cfg.entry_price) / cfg.entry_price * 100
            return TriggeredSessionEvent(
                position_id=cfg.position_id,
                ticker=cfg.ticker,
                event_type=event_type,
                trigger_price=current_price,
                sl_tp_level=sl_tp_level,
                pnl_pct=round(pnl_pct, 4),
                note=note,
            )

        # 1. STOP LOSS
        if cfg.stop_loss is not None:
            if cfg.direction == 1 and current_price <= cfg.stop_loss:
                return make_event(SessionEventType.stop_loss, cfg.stop_loss)
            if cfg.direction == -1 and current_price >= cfg.stop_loss:
                return make_event(SessionEventType.stop_loss, cfg.stop_loss)

        # 2. TAKE PROFIT
        if cfg.take_profit is not None:
            if cfg.direction == 1 and current_price >= cfg.take_profit:
                return make_event(SessionEventType.take_profit, cfg.take_profit)
            if cfg.direction == -1 and current_price <= cfg.take_profit:
                return make_event(SessionEventType.take_profit, cfg.take_profit)

        # 3. TRAILING STOP
        if cfg.trailing_stop_pct is not None:
            ts_pct = cfg.trailing_stop_pct / 100.0
            if cfg.direction == 1:
                trailing_sl = cfg._highest_price * (1 - ts_pct)
                if current_price <= trailing_sl:
                    return make_event(
                        SessionEventType.trailing_stop,
                        trailing_sl,
                        f"Trailing SL={trailing_sl:.4f} (Peak={cfg._highest_price:.4f})",
                    )
            else:
                trailing_sl = cfg._lowest_price * (1 + ts_pct)
                if current_price >= trailing_sl:
                    return make_event(
                        SessionEventType.trailing_stop,
                        trailing_sl,
                        f"Trailing SL={trailing_sl:.4f} (Trough={cfg._lowest_price:.4f})",
                    )

        # 4. TIME EXIT
        if cfg.max_bars is not None and cfg._bar_count >= cfg.max_bars:
            return make_event(
                SessionEventType.time_exit,
                current_price,
                f"Exit after {cfg._bar_count} bars",
            )

        return None

    def _publish_event(self, event: TriggeredSessionEvent) -> None:
        """Publish event to a00 bus."""
        logger.info(
            "EVENT: [%s] %s %s @%.4f (PnL %.2f%%)",
            event.event_type.value, event.ticker,
            event.position_id, event.trigger_price,
            event.pnl_pct,
        )
        try:
            from utils.bus.ket_noi_pubsub import lay_pubsub_mac_dinh
            from utils.bus.bo_dinh_tuyen_tin_nhan import TOPIC_TIN_HIEU_LENH
            pubsub = lay_pubsub_mac_dinh()
            pubsub.phat(
                TOPIC_TIN_HIEU_LENH,
                {
                    "action": "CLOSE_POSITION",
                    "position_id": event.position_id,
                    "ticker": event.ticker,
                    "reason": event.event_type.value,
                    "trigger_price": event.trigger_price,
                    "pnl_pct": event.pnl_pct,
                    "timestamp": event.timestamp,
                },
                nguon="session_events",
            )
        except Exception:
            pass


# Backward-compatible aliases
LoaiSuKienPhien = SessionEventType
CauHinhViThe = PositionConfig
SuKienPhienKichHoat = TriggeredSessionEvent
QuanLySuKienPhien = SessionEventManager
