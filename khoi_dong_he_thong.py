# -*- coding: utf-8 -*-
"""KAIROS Quant System v3.0 — Trình Khởi Động Hệ Thống."""

from __future__ import annotations

import logging
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
import signal

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.append(str(PROJECT_ROOT))

# ─── ANSI Colors ──────────────────────────────────────────────────────────────
_COLOR = sys.stdout.isatty() or bool(os.environ.get("FORCE_COLOR"))

def _esc(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text

def gold(t: str)   -> str: return _esc("38;5;214", t)
def bold(t: str)   -> str: return _esc("1", t)
def dim(t: str)    -> str: return _esc("2", t)
def green(t: str)  -> str: return _esc("92", t)
def red(t: str)    -> str: return _esc("91", t)
def yellow(t: str) -> str: return _esc("93", t)
def cyan(t: str)   -> str: return _esc("96", t)

OK   = green("✓")
FAIL = red("✗")
WARN = yellow("⚠")
RUN  = cyan("→")

# ─── Fallback logger (trước khi load A09) ─────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("KAIROS-BOOT")
logger.success = logger.info  # type: ignore[attr-defined]

# Danh sách subprocesses để dọn dẹp khi thoát
running_processes: list[subprocess.Popen] = []

# ─── Imports ──────────────────────────────────────────────────────────────────
try:
    from utils.config import cfg
except ImportError as exc:
    print(f"\n  {FAIL}  Không tải được A08: {exc}")
    print(f"  {RUN}  Chạy:  pip install -r requirements.txt\n")
    sys.exit(1)

try:
    from processing.ml import tat_ca_trang_thai
except ImportError:
    tat_ca_trang_thai = None

try:
    from utils.helpers import logger  # noqa: F811
except ImportError:
    pass  # dùng fallback logger bên trên


# ─── Banner ───────────────────────────────────────────────────────────────────
_BANNER_ART = r"""
  ██╗  ██╗ █████╗ ██╗██████╗  ██████╗ ███████╗
  ██║ ██╔╝██╔══██╗██║██╔══██╗██╔═══██╗██╔════╝
  █████╔╝ ███████║██║██████╔╝██║   ██║███████╗
  ██╔═██╗ ██╔══██║██║██╔══██╗██║   ██║╚════██║
  ██║  ██╗██║  ██║██║██║  ██║╚██████╔╝███████║
  ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝"""

def print_banner() -> None:
    print(gold(_BANNER_ART))
    print()
    print(f"  {bold('Hệ Thống Nghiên Cứu Định Lượng AI')}  {dim('— v3.0')}")
    print(f"  {dim('3 Thị Trường · 19 Công Cụ AI · Hội Đồng AI 6 Thành Viên')}")
    print()
    print(f"  {dim('─' * 52)}")
    print()


# ─── Step printer ─────────────────────────────────────────────────────────────
_TOTAL_STEPS = 4
_current_step = 0

def step(label: str) -> None:
    global _current_step
    _current_step += 1
    tag = cyan(f"[{_current_step}/{_TOTAL_STEPS}]")
    print(f"  {tag}  {label}", end="", flush=True)

def done(elapsed: float | None = None) -> None:
    suffix = dim(f"  {elapsed:.2f}s") if elapsed is not None else ""
    print(f"  {OK}{suffix}")

def fail(msg: str = "") -> None:
    extra = f"  {dim(msg)}" if msg else ""
    print(f"  {FAIL}{extra}")

def warn(msg: str = "") -> None:
    extra = f"  {dim(msg)}" if msg else ""
    print(f"  {WARN}{extra}")

def sub(icon: str, label: str, status: str, ok: bool) -> None:
    marker = OK if ok else WARN
    print(f"       {dim('·')} {cyan(icon)}  {label:<22} {dim(status):<20} {marker}")


# ─── Bước 1: Khởi tạo thư mục ────────────────────────────────────────────────
def init_system_folders() -> None:
    step("Khởi tạo cây thư mục hệ thống A11 ...")
    t0 = time.perf_counter()
    try:
        from data.store import A11
        A11.init_all()
    except Exception as exc:
        fail(str(exc))
        raise
    done(time.perf_counter() - t0)


# ─── Bước 2: Kiểm tra cấu hình ───────────────────────────────────────────────
def check_config() -> None:
    step("Kiểm tra cấu hình môi trường ...........")
    t0 = time.perf_counter()
    logger.debug("\n" + cfg.summary())
    done(time.perf_counter() - t0)


# ─── Bước 3: Trạng thái ML ───────────────────────────────────────────────────
def check_ml_status() -> None:
    if tat_ca_trang_thai is None:
        step("Trạng thái ML modules .................")
        warn("A07 không khả dụng — bỏ qua")
        return

    step("Trạng thái ML modules .................")
    print()  # xuống dòng để hiển thị sub-rows
    try:
        ml_status = tat_ca_trang_thai()
        for name, status in ml_status.items():
            trained = bool(status.get("trained"))
            state = "Sẵn sàng" if trained else "Chưa train"
            sub("⚙", name, state, trained)
    except Exception as exc:
        sub("⚙", "ml_status", f"lỗi: {exc}", False)

# ─── Bước 4a: Backend ────────────────────────────────────────────────────────
def start_backend() -> None:
    port = int(cfg.system.backend_port)
    step(f"Khởi động API backend (port {port}) ......")
    t0 = time.perf_counter()

    api_path = PROJECT_ROOT / "services" / "api" / "may_chu_api.py"
    if not api_path.exists():
        fail(f"Không tìm thấy: {api_path.name}")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        already_up = sock.connect_ex(("127.0.0.1", port)) == 0
    finally:
        sock.close()

    if already_up:
        warn(f"Port {port} đã dùng — bỏ qua")
        return

    cmd = [
        sys.executable, "-m", "uvicorn",
        "services.api.may_chu_api:app",
        "--host", "0.0.0.0",
        "--port", str(port),
    ]
    if cfg.system.debug:
        cmd.append("--reload")

    try:
        # Bắt buộc phải có cwd để uvicorn tìm đúng module 'services'
        p = subprocess.Popen(cmd, cwd=str(PROJECT_ROOT))
        
        # Đợi nửa giây để bắt lỗi "chết yểu" nếu uvicorn crash ngay khi chạy
        time.sleep(0.5)
        if p.poll() is not None:
            fail("Backend crash ngay lập tức! Hãy kiểm tra lỗi syntax hoặc import trong may_chu_api.py.")
            return
            
        running_processes.append(p)
        done(time.perf_counter() - t0)
    except Exception as exc:
        fail(f"Lỗi khởi chạy Popen: {exc}")


# ─── Bước 4b: Frontend ───────────────────────────────────────────────────────
def start_frontend() -> None:
    port = int(cfg.system.frontend_port)
    step(f"Khởi động React frontend (port {port}) ...")
    t0 = time.perf_counter()

    frontend_dir = PROJECT_ROOT / "frontend"
    if not frontend_dir.exists():
        fail(f"Thư mục không tồn tại: {frontend_dir.name}")
        return

    try:
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        kwargs = {}
        # Nhóm process lại trên Windows
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            
        p = subprocess.Popen(
            [npm_cmd, "run", "dev", "--", "--port", str(port)],
            cwd=str(frontend_dir),
            **kwargs # Thêm kwargs vào đây
        )
        running_processes.append(p)
    except Exception as exc:
        fail(str(exc))


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print_banner()

    try:
        init_system_folders()
        check_config()
        check_ml_status()
        start_backend()

        if not os.path.exists("/.dockerenv"):
            try:
                print()
                answer = input(f"  {cyan('?')}  Khởi động React frontend? {dim('(y/N)')} : ")
                if answer.strip().lower() == "y":
                    start_frontend()
            except EOFError:
                pass

        print()
        print(f"  {dim('─' * 52)}")
        print(f"  {green('●')}  {bold('KAIROS đã sẵn sàng')}  {dim('— Ctrl+C để thoát')}")
        print(f"  {dim('─' * 52)}")
        print()

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n  {yellow('◌')}  Đang dừng KAIROS...", flush=True)
        for p in running_processes:
            try:
                if sys.platform == "win32":
                    p.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    p.terminate()
            except Exception:
                pass
        print(f"  {dim('Tạm biệt.')}\n")
        sys.exit(0)

    except Exception as exc:
        print(f"\n  {FAIL}  Lỗi nghiêm trọng: {exc}\n")
        logger.exception("Fatal error")
        sys.exit(1)
