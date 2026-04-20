"""Time utilities for KAIROS v3.0.

Provides current-time helpers for both realtime and backtest environments.
In backtest mode, time is controlled by the Logger (A09 TimeContext).
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

# Vietnam timezone (UTC+7)
TZ_VN = timezone(timedelta(hours=7))


def now_local() -> datetime:
    """Return current time in Vietnam timezone (UTC+7)."""
    return datetime.now(tz=TZ_VN)


def now_utc() -> datetime:
    """Return current time in UTC."""
    return datetime.now(tz=timezone.utc)


def backtest_time() -> Optional[datetime]:
    """Return simulated time from Logger if in backtest mode, else None."""
    try:
        from utils.helpers.bo_ghi_log_he_thong import TimeContext
        return TimeContext.current_sim_time
    except ImportError:
        return None


def effective_now() -> datetime:
    """Return effective current time: backtest sim-time if active, else local VN time.

    Use this instead of datetime.now() throughout the system.
    """
    bt = backtest_time()
    if bt is not None:
        return bt
    return now_local()


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format a datetime object as a string.

    Args:
        dt: The datetime object.
        fmt: strftime format string. Default: 'YYYY-MM-DD HH:MM:SS'.

    Returns:
        Formatted datetime string.
    """
    return dt.strftime(fmt)


def unix_to_datetime(unix_ts: float, tz: timezone = TZ_VN) -> datetime:
    """Convert Unix timestamp to datetime.

    Args:
        unix_ts: Unix timestamp in seconds.
        tz: Target timezone. Default: UTC+7.

    Returns:
        Converted datetime object.
    """
    return datetime.fromtimestamp(unix_ts, tz=tz)


def datetime_to_unix(dt: datetime) -> float:
    """Convert datetime to Unix timestamp.

    Args:
        dt: The datetime object.

    Returns:
        Unix timestamp in seconds.
    """
    return dt.timestamp()


__all__ = [
    "TZ_VN",
    "now_local",
    "now_utc",
    "backtest_time",
    "effective_now",
    "format_datetime",
    "unix_to_datetime",
    "datetime_to_unix",
]
