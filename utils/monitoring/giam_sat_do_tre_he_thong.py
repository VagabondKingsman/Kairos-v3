"""Event Latency Monitor — A00.

Tracks end-to-end latency from when an event is published (publish())
to when a subscriber has finished processing it.

Metrics:
    - P50 (median), P95, P99 latency (ms)
    - Throughput (events/second)
    - Queue backlog

Usage:
    monitor = LatencyMonitor()
    bus = EventBus.get_instance()

    # Wrap callback to measure latency
    def my_callback(event):
        monitor.record(event)
        # ... actual processing ...

    bus.subscribe("ohlcv", my_callback)
    bus.publish("ohlcv", data)  # → monitor automatically computes latency
"""

from __future__ import annotations

import logging
import statistics
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class LatencySample:
    """A single latency measurement.

    Attributes:
        topic: Event channel.
        event_id: ID of the SystemEvent.
        publish_time: Unix timestamp when event was published.
        process_time: Unix timestamp when processing completed.
        latency_ms: Latency in milliseconds.
    """

    topic: str
    event_id: str
    publish_time: float
    process_time: float = field(default_factory=time.time)

    @property
    def latency_ms(self) -> float:
        """Latency in milliseconds."""
        return (self.process_time - self.publish_time) * 1000.0


@dataclass
class LatencyReport:
    """Latency statistics for one topic.

    Attributes:
        topic: Event channel.
        sample_count: Total number of samples.
        p50_ms: 50th-percentile (median) latency.
        p95_ms: 95th-percentile latency.
        p99_ms: 99th-percentile latency.
        mean_ms: Mean latency.
        min_ms: Minimum latency.
        max_ms: Maximum latency.
        throughput_per_second: Events processed in the last 60 seconds.
    """

    topic: str
    sample_count: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float
    min_ms: float
    max_ms: float
    throughput_per_second: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "sample_count": self.sample_count,
            "p50_ms": round(self.p50_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p99_ms": round(self.p99_ms, 2),
            "mean_ms": round(self.mean_ms, 2),
            "min_ms": round(self.min_ms, 2),
            "max_ms": round(self.max_ms, 2),
            "throughput_per_second": round(self.throughput_per_second, 2),
        }


# Backward-compatible aliases for Vietnamese field names used by existing callers
@property
def _so_mau(self) -> int:
    return self.sample_count


# ---------------------------------------------------------------------------
# LatencyMonitor — main monitor
# ---------------------------------------------------------------------------

class LatencyMonitor:
    """Per-topic event latency tracker.

    Thread-safe. Keeps at most ``max_history`` samples per topic
    (sliding window for efficient statistics).

    Automatically fires a warning when P99 exceeds the threshold.
    """

    DEFAULT_MAX_HISTORY = 1000        # Maximum samples kept in memory
    DEFAULT_WARN_THRESHOLD_MS = 500.0  # Warn when P99 > 500ms

    def __init__(
        self,
        max_history: int = DEFAULT_MAX_HISTORY,
        warn_threshold_ms: float = DEFAULT_WARN_THRESHOLD_MS,
    ) -> None:
        self._history: Dict[str, Deque[LatencySample]] = {}
        self._lock = threading.Lock()
        self._max_history = max_history
        self._warn_threshold_ms = warn_threshold_ms
        self._total_events: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, event: Any) -> Optional[LatencySample]:
        """Record a processed event and compute its latency.

        Call this IMMEDIATELY after the callback finishes processing.

        Args:
            event: SystemEvent or any object with ``topic``, ``id``, ``timestamp`` attributes.

        Returns:
            LatencySample, or None if attributes are missing.
        """
        try:
            topic = event.topic
            event_id = event.id
            publish_time = event.timestamp
        except AttributeError:
            return None

        sample = LatencySample(
            topic=topic,
            event_id=event_id,
            publish_time=publish_time,
            process_time=time.time(),
        )

        with self._lock:
            if topic not in self._history:
                self._history[topic] = deque(maxlen=self._max_history)
                self._total_events[topic] = 0
            self._history[topic].append(sample)
            self._total_events[topic] += 1

        # Fire warning if P99 is high
        report = self.get_report(topic)
        if report and report.p99_ms > self._warn_threshold_ms:
            logger.warning(
                "HIGH LATENCY WARNING: topic='%s' P99=%.1fms (threshold=%.1fms)",
                topic, report.p99_ms, self._warn_threshold_ms,
            )

        return sample

    def get_report(self, topic: str) -> Optional[LatencyReport]:
        """Compute latency statistics for a topic.

        Args:
            topic: Topic name to inspect.

        Returns:
            LatencyReport, or None if no data.
        """
        with self._lock:
            history = list(self._history.get(topic, []))

        if not history:
            return None

        latencies = [s.latency_ms for s in history]
        latencies_sorted = sorted(latencies)
        n = len(latencies_sorted)

        # Throughput: events processed in the last 60 seconds
        now = time.time()
        recent = [s for s in history if now - s.process_time <= 60.0]
        throughput = len(recent) / 60.0 if recent else 0.0

        return LatencyReport(
            topic=topic,
            sample_count=n,
            p50_ms=_percentile(latencies_sorted, 50),
            p95_ms=_percentile(latencies_sorted, 95),
            p99_ms=_percentile(latencies_sorted, 99),
            mean_ms=statistics.mean(latencies),
            min_ms=latencies_sorted[0],
            max_ms=latencies_sorted[-1],
            throughput_per_second=throughput,
        )

    def get_all_reports(self) -> Dict[str, LatencyReport]:
        """Compute reports for all recorded topics."""
        with self._lock:
            topics = list(self._history.keys())
        return {t: self.get_report(t) for t in topics if self.get_report(t)}

    def log_summary(self) -> None:
        """Print latency report to the log at INFO level."""
        all_reports = self.get_all_reports()
        if not all_reports:
            logger.info("LatencyMonitor: no data yet")
            return
        for report in all_reports.values():
            logger.info(
                "Latency [%s] n=%d | P50=%.1fms P95=%.1fms P99=%.1fms | tpt=%.1f/s",
                report.topic,
                report.sample_count,
                report.p50_ms,
                report.p95_ms,
                report.p99_ms,
                report.throughput_per_second,
            )

    def reset(self) -> None:
        """Clear all recorded data."""
        with self._lock:
            self._history.clear()
            self._total_events.clear()

    # Backward-compatible Vietnamese method aliases
    def ghi_nhan_xu_ly(self, su_kien: Any) -> Optional[LatencySample]:
        return self.record(su_kien)

    def tinh_bao_cao(self, topic: str) -> Optional[LatencyReport]:
        return self.get_report(topic)

    def tinh_tat_ca(self) -> Dict[str, LatencyReport]:
        return self.get_all_reports()

    def xuat_log(self) -> None:
        self.log_summary()

    def dat_lai(self) -> None:
        self.reset()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_global_monitor: Optional[LatencyMonitor] = None


def get_monitor() -> LatencyMonitor:
    """Return the global LatencyMonitor singleton."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = LatencyMonitor()
    return _global_monitor


# Backward-compatible alias
lay_monitor = get_monitor

# Backward-compatible class aliases
GiamSatDoTre = LatencyMonitor
MauDoTre = LatencySample
BaoCaoDoTre = LatencyReport


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _percentile(sorted_data: list, pct: float) -> float:
    """Compute a percentile on a pre-sorted list."""
    if not sorted_data:
        return 0.0
    n = len(sorted_data)
    idx = (pct / 100.0) * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return sorted_data[lo] + frac * (sorted_data[hi] - sorted_data[lo])
