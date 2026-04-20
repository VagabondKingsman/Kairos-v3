"""Event Bus — In-Process Message Router.

Implements an internal message broker without Redis/Kafka.
Uses threading.Queue + threading.Lock for thread-safety.

Architecture:
    Publisher → EventBus.publish(topic, data)
                    ↓
    [Queue topic_1] → Worker thread → callback_1(data)
                    ↓
    [Queue topic_2] → Worker thread → callback_2(data)

Standard system topics:
    - ``ohlcv``         : OHLCV candle data from perception layer
    - ``trade_signal``  : Buy/Sell/Close signals from AI council
    - ``agent_state``   : Health report from each agent
    - ``swarm_result``  : Final result from a swarm run
    - ``log``           : System log events
"""

from __future__ import annotations

import logging
import queue
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Standard topics
# ---------------------------------------------------------------------------

TOPIC_OHLCV             = "ohlcv"
TOPIC_TRADE_SIGNAL      = "trade_signal"
TOPIC_AGENT_STATE       = "agent_state"
TOPIC_SWARM_RESULT      = "swarm_result"
TOPIC_LOG               = "log"

# All valid topics
ALL_TOPICS = {
    TOPIC_OHLCV,
    TOPIC_TRADE_SIGNAL,
    TOPIC_AGENT_STATE,
    TOPIC_SWARM_RESULT,
    TOPIC_LOG,
}

# Backward-compatible aliases
TOPIC_TIN_HIEU_LENH     = TOPIC_TRADE_SIGNAL
TOPIC_TRANG_THAI_AGENT  = TOPIC_AGENT_STATE
TOPIC_KET_QUA_BAY_DAN   = TOPIC_SWARM_RESULT
TOPIC_NHAT_KY           = TOPIC_LOG
TAT_CA_TOPICS           = ALL_TOPICS


# ---------------------------------------------------------------------------
# Event dataclass
# ---------------------------------------------------------------------------

@dataclass
class SystemEvent:
    """Basic data unit travelling through the Event Bus.

    Attributes:
        topic: Distribution channel.
        data: Payload (any JSON-serializable type).
        id: Unique event UUID.
        timestamp: Unix timestamp when event was published.
        source: Module/agent name that published the event (optional).
    """

    topic: str
    data: Any
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: float = field(default_factory=time.time)
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "id": self.id,
            "topic": self.topic,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source,
        }


# Backward-compatible alias
SuKienHeTong = SystemEvent


# ---------------------------------------------------------------------------
# EventBus — Singleton Event Bus
# ---------------------------------------------------------------------------

class EventBus:
    """Thread-safe in-process event bus (Singleton).

    The entire system shares one bus instance.

    Example:
        bus = EventBus.get_instance()
        bus.subscribe("ohlcv", lambda e: print(e.data))
        bus.publish("ohlcv", {"symbol": "BTC-USDT", "close": 65000})
    """

    _instance: Optional["EventBus"] = None
    _lock_singleton = threading.Lock()

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[_Subscription]] = defaultdict(list)
        self._lock = threading.RLock()
        self._workers: Dict[str, _WorkerThread] = {}
        self._running = False

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EventBus":
        """Return the singleton instance (creates if absent)."""
        if cls._instance is None:
            with cls._lock_singleton:
                if cls._instance is None:
                    inst = cls()
                    inst.start()
                    cls._instance = inst
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (for unit tests)."""
        if cls._instance is not None:
            cls._instance.stop()
            cls._instance = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the Event Bus — creates worker threads for each topic."""
        if self._running:
            return
        self._running = True
        for topic in ALL_TOPICS:
            self._ensure_worker(topic)
        logger.info("EventBus started with %d topics", len(ALL_TOPICS))

    def stop(self) -> None:
        """Stop the Event Bus — exits all worker threads."""
        self._running = False
        with self._lock:
            for worker in self._workers.values():
                worker.stop()
        self._workers.clear()
        logger.info("EventBus stopped")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def subscribe(
        self,
        topic: str,
        callback: Callable[[SystemEvent], None],
        *,
        name: str = "",
    ) -> str:
        """Subscribe to a topic.

        Args:
            topic: Topic name to listen on.
            callback: Function receiving SystemEvent on new events.
            name: Display name for the subscriber (optional, for debugging).

        Returns:
            Subscription ID — use to unsubscribe later.
        """
        sub_id = str(uuid.uuid4())[:12]
        sub = _Subscription(id=sub_id, topic=topic, callback=callback, name=name or sub_id)
        with self._lock:
            self._subscribers[topic].append(sub)
            self._ensure_worker(topic)
        logger.debug("Subscribed to topic '%s' id=%s", topic, sub_id)
        return sub_id

    def unsubscribe(self, sub_id: str) -> bool:
        """Unsubscribe by ID.

        Args:
            sub_id: ID returned by subscribe().

        Returns:
            True if found and removed.
        """
        with self._lock:
            for topic_list in self._subscribers.values():
                for i, sub in enumerate(topic_list):
                    if sub.id == sub_id:
                        topic_list.pop(i)
                        logger.debug("Unsubscribed id=%s", sub_id)
                        return True
        return False

    def publish(
        self,
        topic: str,
        data: Any,
        *,
        source: str = "",
    ) -> SystemEvent:
        """Publish an event to all subscribers of a topic.

        Non-blocking — event is enqueued to workers.

        Args:
            topic: Target topic.
            data: Event payload.
            source: Publishing module name (optional).

        Returns:
            The SystemEvent that was published.
        """
        event = SystemEvent(topic=topic, data=data, source=source)
        with self._lock:
            worker = self._workers.get(topic)
            if worker is None:
                self._ensure_worker(topic)
                worker = self._workers[topic]
            worker.enqueue(event)
        return event

    def publish_and_wait(
        self,
        topic: str,
        data: Any,
        timeout: float = 5.0,
        *,
        source: str = "",
    ) -> bool:
        """Publish event and block until all subscribers finish processing.

        Args:
            topic: Target topic.
            data: Payload.
            timeout: Max wait time (seconds).
            source: Publishing module name.

        Returns:
            True if all subscribers finished within timeout.
        """
        event = SystemEvent(topic=topic, data=data, source=source)
        done = threading.Event()

        with self._lock:
            sub_count = len(self._subscribers.get(topic, []))

        if sub_count == 0:
            return True

        counter = {"n": 0}
        lock_counter = threading.Lock()

        def _on_done(e: SystemEvent) -> None:
            with lock_counter:
                counter["n"] += 1
                if counter["n"] >= sub_count:
                    done.set()

        with self._lock:
            worker = self._workers.get(topic)
            if worker:
                worker.enqueue(event, on_complete=_on_done)

        return done.wait(timeout=timeout)

    def subscriber_count(self, topic: str) -> int:
        """Number of subscribers listening to a topic."""
        with self._lock:
            return len(self._subscribers.get(topic, []))

    def get_info(self) -> Dict[str, Any]:
        """Summary of Event Bus status."""
        with self._lock:
            return {
                "running": self._running,
                "topics": {
                    t: {
                        "subscriber_count": len(subs),
                        "queue_size": self._workers[t].queue_size()
                        if t in self._workers else 0,
                    }
                    for t, subs in self._subscribers.items()
                },
            }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ensure_worker(self, topic: str) -> None:
        """Create worker thread for topic if absent (must hold lock)."""
        if topic not in self._workers:
            worker = _WorkerThread(
                topic=topic,
                get_subscribers=lambda t=topic: self._subscribers.get(t, []),
            )
            worker.start()
            self._workers[topic] = worker

    # Backward-compatible method aliases
    lay_instance             = get_instance
    dat_lai                  = reset
    khoi_dong                = start
    dung                     = stop
    dang_ky                  = subscribe
    huy_dang_ky              = unsubscribe
    phat                     = publish
    phat_va_cho              = publish_and_wait
    lay_so_luong_subscribers = subscriber_count
    lay_thong_tin            = get_info


# Backward-compatible class alias
BoTrungChuyen = EventBus


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

@dataclass
class _Subscription:
    """Internal subscriber record."""

    id: str
    topic: str
    callback: Callable[[SystemEvent], None]
    name: str = ""


class _WorkerThread(threading.Thread):
    """Event processing thread for one topic."""

    _SENTINEL = object()  # Stop signal

    def __init__(
        self,
        topic: str,
        get_subscribers: Callable[[], List[_Subscription]],
    ) -> None:
        super().__init__(name=f"BTC-{topic}", daemon=True)
        self._topic = topic
        self._get_subscribers = get_subscribers
        self._q: queue.Queue = queue.Queue()
        self._running = True

    def enqueue(
        self,
        event: SystemEvent,
        on_complete: Optional[Callable[[SystemEvent], None]] = None,
    ) -> None:
        """Enqueue event for processing (non-blocking)."""
        self._q.put((event, on_complete))

    def queue_size(self) -> int:
        """Number of events waiting to be processed."""
        return self._q.qsize()

    def stop(self) -> None:
        """Send stop signal and wait for thread to exit."""
        self._running = False
        self._q.put((self._SENTINEL, None))
        self.join(timeout=2.0)

    def run(self) -> None:
        while self._running:
            try:
                item, on_complete = self._q.get(timeout=1.0)
            except queue.Empty:
                continue

            if item is self._SENTINEL:
                break

            event: SystemEvent = item
            subscribers = self._get_subscribers()
            for sub in subscribers:
                try:
                    sub.callback(event)
                except Exception as exc:
                    logger.exception(
                        "Subscriber '%s' error (topic=%s): %s",
                        sub.name, self._topic, exc,
                    )

            if on_complete:
                try:
                    on_complete(event)
                except Exception:
                    pass

            self._q.task_done()
