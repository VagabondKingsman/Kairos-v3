"""PubSub Connection — Abstract Interface + Implementations.

Abstract interface for Publish-Subscribe, with two implementations:
- InProcessPubSub: Uses internal EventBus (no Redis needed).
- RedisPubSub: Placeholder for Redis-based deployment.

Usage:
    from utils.bus.ket_noi_pubsub import get_pubsub
    pubsub = get_pubsub()
    pubsub.publish("ohlcv", data)
    pubsub.subscribe("trade_signal", my_callback)
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from utils.config import cfg

from utils.bus.bo_dinh_tuyen_tin_nhan import (
    EventBus,
    SystemEvent,
    # backward-compat aliases kept for any code still using old names
    BoTrungChuyen,
    SuKienHeTong,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract interfaces
# ---------------------------------------------------------------------------

class Publisher(ABC):
    """Event publisher interface."""

    @abstractmethod
    def publish(self, topic: str, data: Any, *, source: str = "") -> None:
        """Publish a message to all subscribers."""

    @abstractmethod
    def close(self) -> None:
        """Release connection resources."""

    # Backward-compatible alias
    def phat(self, topic: str, data: Any, *, nguon: str = "") -> None:
        self.publish(topic, data, source=nguon)

    def dong(self) -> None:
        self.close()


class Subscriber(ABC):
    """Event subscriber interface."""

    @abstractmethod
    def subscribe(
        self,
        topic: str,
        callback: Callable[[SystemEvent], None],
        *,
        name: str = "",
    ) -> str:
        """Subscribe to a topic. Returns subscription ID."""

    @abstractmethod
    def unsubscribe(self, sub_id: str) -> bool:
        """Unsubscribe by ID."""

    # Backward-compatible aliases
    def dang_ky(self, topic: str, callback: Callable, *, ten: str = "") -> str:
        return self.subscribe(topic, callback, name=ten)

    def huy_dang_ky(self, sub_id: str) -> bool:
        return self.unsubscribe(sub_id)


class PubSubConnection(Publisher, Subscriber):
    """Combined publish + subscribe interface."""

    @abstractmethod
    def activate(self) -> None:
        """Start the connection."""

    @abstractmethod
    def get_info(self) -> dict:
        """Return connection status info."""

    # Backward-compatible aliases
    def kich_hoat(self) -> None:
        self.activate()

    def lay_thong_tin(self) -> dict:
        return self.get_info()


# Backward-compatible class aliases
NhaPhatHanh = Publisher
NguoiDangKy = Subscriber
KetNoiPubSub = PubSubConnection


# ---------------------------------------------------------------------------
# Implementation 1: In-Process
# ---------------------------------------------------------------------------

class InProcessPubSub(PubSubConnection):
    """PubSub using the internal EventBus — no Redis required."""

    def __init__(self) -> None:
        self._bus: Optional[EventBus] = None

    def activate(self) -> None:
        self._bus = EventBus.get_instance()
        logger.info("InProcessPubSub activated")

    def publish(self, topic: str, data: Any, *, source: str = "") -> None:
        if self._bus is None:
            self.activate()
        self._bus.publish(topic, data, source=source)

    def subscribe(
        self,
        topic: str,
        callback: Callable[[SystemEvent], None],
        *,
        name: str = "",
    ) -> str:
        if self._bus is None:
            self.activate()
        return self._bus.subscribe(topic, callback, name=name)

    def unsubscribe(self, sub_id: str) -> bool:
        if self._bus is None:
            return False
        return self._bus.unsubscribe(sub_id)

    def close(self) -> None:
        logger.debug("InProcessPubSub.close() — bus singleton stays running")

    def get_info(self) -> dict:
        if self._bus is None:
            return {"type": "in_process", "status": "not_activated"}
        info = self._bus.get_info()
        info["type"] = "in_process"
        return info

    # Backward-compatible aliases that callers still use
    def phat(self, topic: str, data: Any = None, *, du_lieu: Any = None, nguon: str = "") -> None:
        self.publish(topic, data if data is not None else du_lieu, source=nguon)

    def dang_ky(self, topic: str, callback: Callable, *, ten: str = "") -> str:
        return self.subscribe(topic, callback, name=ten)

    def huy_dang_ky(self, sub_id: str) -> bool:
        return self.unsubscribe(sub_id)

    def kich_hoat(self) -> None:
        self.activate()

    def dong(self) -> None:
        self.close()

    def lay_thong_tin(self) -> dict:
        return self.get_info()


# ---------------------------------------------------------------------------
# Implementation 2: Redis Stub
# ---------------------------------------------------------------------------

class RedisPubSub(PubSubConnection):
    """PubSub using Redis — placeholder for future upgrade.

    Configure via environment variables:
        REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: int = 0,
    ) -> None:
        self._host = host or cfg.system.redis_host
        self._port = port or cfg.system.redis_port
        self._db = db
        self._client = None

    def activate(self) -> None:
        try:
            import redis  # type: ignore
        except ImportError as exc:
            raise ImportError("Install redis to use RedisPubSub: pip install redis") from exc
        self._client = redis.Redis(
            host=self._host, port=self._port, db=self._db, decode_responses=True
        )
        self._client.ping()
        logger.info("RedisPubSub connected: %s:%d", self._host, self._port)

    def publish(self, topic: str, data: Any, *, source: str = "") -> None:
        if self._client is None:
            self.activate()
        payload = json.dumps({"data": data, "source": source}, ensure_ascii=False, default=str)
        self._client.publish(topic, payload)

    def subscribe(self, topic: str, callback: Callable, *, name: str = "") -> str:
        logger.warning("RedisPubSub.subscribe() not implemented — use InProcessPubSub")
        import uuid as _uuid
        return str(_uuid.uuid4())[:12]

    def unsubscribe(self, sub_id: str) -> bool:
        return False

    def close(self) -> None:
        if self._client:
            self._client.close()

    def get_info(self) -> dict:
        return {"type": "redis", "host": self._host, "port": self._port, "connected": self._client is not None}

    # Backward-compatible aliases
    def phat(self, topic: str, data: Any = None, *, du_lieu: Any = None, nguon: str = "") -> None:
        self.publish(topic, data if data is not None else du_lieu, source=nguon)

    def dang_ky(self, topic: str, callback: Callable, *, ten: str = "") -> str:
        return self.subscribe(topic, callback, name=ten)

    def huy_dang_ky(self, sub_id: str) -> bool:
        return self.unsubscribe(sub_id)

    def kich_hoat(self) -> None:
        self.activate()

    def dong(self) -> None:
        self.close()

    def lay_thong_tin(self) -> dict:
        return self.get_info()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_pubsub(backend_type: Optional[str] = None) -> PubSubConnection:
    """Create the appropriate PubSub implementation.

    Args:
        backend_type: "in_process" (default) or "redis".
                      Can also be set via PUBSUB_BACKEND env var.
    """
    backend = backend_type or cfg.system.pubsub_backend
    instance: PubSubConnection = RedisPubSub() if backend == "redis" else InProcessPubSub()
    instance.activate()
    return instance


_default_pubsub: Optional[PubSubConnection] = None


def get_default_pubsub() -> PubSubConnection:
    """Singleton default PubSub for the system."""
    global _default_pubsub
    if _default_pubsub is None:
        _default_pubsub = get_pubsub()
    return _default_pubsub


# Backward-compatible aliases
lay_pubsub          = get_pubsub
lay_pubsub_mac_dinh = get_default_pubsub
