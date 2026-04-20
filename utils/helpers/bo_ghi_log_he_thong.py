"""Central logging system for KAIROS v3.0 (Loguru).

- Colorized terminal output.
- Persistent file logging under data.store/logs/.
- Dynamic timestamp injection for backtest simulation mode.
- Thread-safe & Intercepts standard Python logging (Uvicorn, FastAPI, Langchain).
"""

import os
import sys
import logging
import threading
from datetime import datetime
from loguru import logger as _logger

# Import cấu hình và đường dẫn chuẩn của KAIROS
from data.store.duong_dan import A11Paths
from utils.config.cau_hinh import cfg

for _stream_name in ("stdout", "stderr"):
    _stream = getattr(sys, _stream_name, None)
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


class TimeContext:
    """Stores simulated time for backtest mode (Thread-safe)."""
    # Sử dụng threading.local() để mỗi luồng backtest có một bộ đếm thời gian riêng, 
    # tránh xung đột khi chạy đa luồng.
    local_state = threading.local()


def _inject_sim_time(record):
    """Override Loguru timestamp with backtest simulation time when active."""
    sim_time = getattr(TimeContext.local_state, 'current_sim_time', None)
    if sim_time and isinstance(sim_time, datetime):
        record["time"] = sim_time
    return record


class InterceptHandler(logging.Handler):
    """Bắt các log tiêu chuẩn của Python và chuyển hướng sang Loguru."""
    def emit(self, record):
        try:
            level = _logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Truy vết stack frame để loguru biết file/dòng nào thực sự gọi log
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        _logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logger():
    """Initialize the global logger with terminal and file handlers."""
    fmt_terminal = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
        "<level>{message}</level>"
    )
    fmt_file = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"

    # 1. Khắc phục lỗi lưu log sai vị trí (Dùng class A11Paths)
    log_file_path = A11Paths.log_file("kairos_system")

    # 2. Đồng bộ Log Level với file .env (Bỏ hardcode)
    log_level_console = cfg.system.log_level
    log_level_file = "DEBUG" if cfg.system.debug else cfg.system.log_level

    _logger.remove()

    # Terminal Handler
    _logger.add(
        sys.stdout,
        format=fmt_terminal,
        level=log_level_console,
        colorize=True,
        filter=_inject_sim_time,
    )

    # File Handler: Rotate daily at midnight, retain 30 days
    _logger.add(
        log_file_path,
        format=fmt_file,
        level=log_level_file,
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
        filter=_inject_sim_time,
        enqueue=True,  # 3. Khắc phục lỗi an toàn đa luồng (Tránh crash khi ghi file)
    )

    # 4. Bắt toàn bộ log của các thư viện bên thứ 3 đổ về file log của hệ thống
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for _log in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", "langchain", "ccxt"]:
        logging_logger = logging.getLogger(_log)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False

    return _logger


def set_log_time(dt: datetime) -> None:
    """Set simulated bar time at the start of each backtest candle iteration."""
    TimeContext.local_state.current_sim_time = dt


def reset_log_time() -> None:
    """Clear simulated time; call when returning to realtime or finishing backtest."""
    TimeContext.local_state.current_sim_time = None


# Single shared logger instance for the entire project
logger = setup_logger()