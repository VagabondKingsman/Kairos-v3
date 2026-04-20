"""Central API Server (Backend) — KAIROS v3.0

Provides endpoints for the Web Interface (a06) to communicate with the core system.
"""

import sys
import os
import csv
import json
from datetime import datetime
from pathlib import Path

# Ensure project root is always on sys.path so AI strategy modules (a04/a07/a01...) can be imported
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
import asyncio

from utils.config import trading_cfg
from utils.helpers import logger

app = FastAPI(
    title="KAIROS Quant System API",
    description="Backend API for KAIROS Pro Terminal v3.0",
    version="3.0.0"
)

# CORS: allow the frontend (React/Vite on port 5900) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info(f"KAIROS API Server starting... (Project root: {_PROJECT_ROOT})")
    try:
        from data.store.duong_dan import A11Paths
        A11Paths.init_all()
    except Exception as e:
        logger.error(f"Failed to initialize a11 directory structure: {e}")

# --- AI Chat Endpoint (SSE Streaming) ---

SYSTEM_PROMPT = """Bạn là KAIROS AI — trợ lý thông minh chuyên về giao dịch thuật toán, phân tích thị trường và xây dựng chiến lược.
Hệ thống bạn đang hỗ trợ là KAIROS Quant System v3.0 với các module: A01 (Dữ liệu), A02 (Phân tích kỹ thuật), A03 (AI Đầu tư), A04 (Backtest), A05 (LLM), A06 (Web), A07 (ML), A08 (Config), A09 (Log), A11 (Data), A10 (Thực thi), A13 (Sàn).
Hãy trả lời bằng tiếng Việt, chuyên nghiệp, có cấu trúc rõ ràng. Khi giải thích chiến lược hãy nêu rõ: tín hiệu vào/ra, quản lý rủi ro, khung thời gian, thị trường phù hợp.

QUAN TRỌNG: Trước khi tạo chiến lược, bạn NÊN sử dụng công cụ `list_skills` để tìm kỹ năng phù hợp (ví dụ SMC, Ichimoku), sau đó dùng `load_skill` để đọc tài liệu chuẩn của dự án.
QUAN TRỌNG: NẾU người dùng yêu cầu "Tạo chiến lược", "Viết chiến lược", hoặc tương tự, bạn bắt buộc PHẢI CUNG CẤP thông số kỹ thuật của chiến lược đó dưới dạng JSON nằm TRONG một khối mã Markdown với cú pháp chính xác như sau:

```strategy
{
  "name": "Tên chiến lược",
  "desc": "Mô tả cực kỳ ngắn gọn",
  "interval": "1H",
  "htf": "1D",
  "codes": ["BTC-USDT"],
  "tags": ["Tag1", "Tag2"],
  "exchange": "OKX",
  "start_date": "2023-01-01",
  "end_date": "2024-01-01",
  "params": {"tham_so_1": 20, "tham_so_2": 70},
  "description_detail": "Chi tiết tín hiệu vào/ra, stop loss, take profit...",
  "backtest_mode": "B2B",
  "python_code": "PYTHON_CODE_HERE"
}
```

═══════════════════════════════════════════════
QUY TẮC BẮT BUỘC KHI VIẾT python_code (TUÂN THEO CHUẨN A02/SKILL.md):
═══════════════════════════════════════════════

1. TEMPLATE BẮT BUỘC — Luôn dùng cấu trúc này, không được đổi:

import sys, os
import polars as pl
import numpy as np

# Thêm đường dẫn gốc
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import BaseStrategy
from processing.backtest.ky_nang_chien_luoc.base_strategy import BaseStrategy

class SignalEngine(BaseStrategy):
    def compute(self, df: pl.DataFrame) -> pl.Expr | pl.Series:
        # VIẾT LOGIC TÍN HIỆU Ở ĐÂY BẰNG POLARS EXPRESSIONS
        # Có thể lấy tham số từ self.get_param('ten_tham_so', mac_dinh)
        
        # Ví dụ một logic mẫu:
        df = df.with_columns(
            signal = (
                pl.when(rsi < oversold).then(1.0)
                .when(rsi > overbought).then(-1.0)
                .otherwise(0.0)
            )
        )
        return df.get_column("signal")

2. QUY TẮC BẮT BUỘC:
   ✅ Kế thừa từ `BaseStrategy` và CHỈ ghi đè hàm `compute(self, df)`. Mọi thao tác đa khung thời gian (MTF) đã được `BaseStrategy` lo!
   ✅ Bạn CÓ SẴN các cột MTF trong `df` như `h4_close`, `d1_open`... Không cần tự gọi hàm `them_vao_df`.
   ✅ Trả về `pl.Expr` hoặc `pl.Series` hợp lệ.
   ✅ Tín hiệu chỉ nhận giá trị: 1.0 (MUA), 0.0 (ĐỨNG NGOÀI), -1.0 (BÁN KHỐNG). `BaseStrategy` sẽ tự động fill_null(0).
   ❌ KHÔNG DÙNG PANDAS. MỌI TÍNH TOÁN PHẢI DÙNG POLARS EXPRESSIONS (pl.col(), pl.when().then(), .rolling_mean(), v.v.)
   ❌ CHÚ Ý CÚ PHÁP POLARS 1: KHÔNG THỂ viết `buy.otherwise(sell)` nếu `buy` và `sell` là các khối `pl.when().then()`. Bạn BẮT BUỘC phải nối chuỗi: `pl.when(dk_mua).then(1.0).when(dk_ban).then(-1.0).otherwise(0.0)`.
   ❌ CHÚ Ý CÚ PHÁP POLARS 2: Các phép tính trong cùng 1 lệnh `with_columns()` chạy song song, KHÔNG THỂ gọi cột vừa tạo ra ngay trong lệnh đó.
   ❌ KHÔNG hardcode ngày tháng hoặc mã cổ phiếu trong code
   ❌ KHÔNG dùng if __name__ == "__main__"
   ❌ KHÔNG import thư viện ngoài hệ sinh thái (chỉ polars, numpy, và các module a04/a07)
   ❌ KHÔNG để code trong định dạng Markdown code fences bên trong python_code
   ❌ KHÔNG GỌI CÁC HÀM ML TỪ a07 NẾU KHÔNG CÓ HƯỚNG DẪN CỤ THỂ, VÌ CẦN MODEL ĐÃ TRAIN. CHỈ VIẾT LOGIC THUẦN POLARS!
   ❌ TUYỆT ĐỐI KHÔNG dùng df.shift(-1) hoặc bất kỳ logic Lookahead Bias nào.

3. API XayDungNenHTF:
   df = htf.them_vao_df(df, "4h", prefix="h4")   # Ghép cột h4_open/high/low/close/volume
   df = htf.them_vao_df(df, "1D", prefix="d1")   # Ghép cột d1_open/high/low/close/volume
   Khung hỗ trợ: "15m", "1h", "4h", "1D", "1W"

4. TRONG python_code, dùng \\n để xuống dòng (vì JSON cần escape).

Bạn có thể giải thích thêm bằng văn bản bên ngoài khối mã này. Giao diện người dùng sẽ tự động render khối mã ```strategy thành một Strategy Card UI tương tác."""

@app.post("/api/chat")
async def chat_stream(request: Request):
    """Chat with AI — returns SSE streaming from LLM (A05)."""
    try:
        body = await request.json()
        messages_raw = body.get("messages", [])

        # Build OpenAI-format message list
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in messages_raw:
            messages.append({"role": m["role"], "content": m["content"]})

        async def generate():
            import json as _json
            try:
                from services.llm.xu_ly_doan_chat import ChatLLM
                from utils.config import cfg as _cfg
                import threading
                import queue as _queue

                # Check api_key before calling LLM
                if not _cfg.llm.api_key:
                    msg = (
                        f"⚠️ Chưa có API Key cho provider **{_cfg.llm.provider}**.\n\n"
                        f"Hãy thêm vào file `utils.config/.env`:\n"
                        f"```\nLANGCHAIN_PROVIDER=groq\nGROQ_API_KEY=gsk_xxxx\n```"
                    )
                    yield f"data: {_json.dumps({'delta': msg})}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                
                import asyncio
                loop = asyncio.get_running_loop()
                q = asyncio.Queue()
                
                def run_llm():
                    try:
                        llm = ChatLLM()
                        def on_chunk(delta: str):
                            loop.call_soon_threadsafe(q.put_nowait, ("chunk", delta))
                        llm.stream_chat(messages, on_text_chunk=on_chunk)
                        loop.call_soon_threadsafe(q.put_nowait, ("done", None))
                    except Exception as e:
                        loop.call_soon_threadsafe(q.put_nowait, ("error", str(e)))
                
                thread = threading.Thread(target=run_llm, daemon=True)
                thread.start()
                
                while True:
                    try:
                        event_type, data = await asyncio.wait_for(q.get(), timeout=60.0)
                        if event_type == "chunk":
                            yield f"data: {_json.dumps({'delta': data})}\n\n"
                        elif event_type == "done":
                            yield "data: [DONE]\n\n"
                            break
                        elif event_type == "error":
                            error_message = f"\n\nLoi LLM: {data}"
                            yield f"data: {_json.dumps({'delta': error_message})}\n\n"
                            yield "data: [DONE]\n\n"
                            break
                    except asyncio.TimeoutError:
                        yield "data: [DONE]\n\n"
                        break
                    await asyncio.sleep(0)

            except ImportError as e:
                msg = f"⚠️ Module not installed: {e}. Run `pip install -r requirements.txt`"
                yield f"data: {_json.dumps({'delta': msg})}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                system_error = f"❌ System error: {str(e)}"
                yield f"data: {_json.dumps({'delta': system_error})}\n\n"
                yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            }
        )
    except Exception as e:
        logger.error(f"Chat API error: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "error_code": "INTERNAL_ERROR", "message": str(e)})

@app.post("/api/swarm/analyze_coin")
async def analyze_coin_swarm(request: Request):
    """Trigger A03 (Swarm Engine) to analyze an asset.
    4 specialists (Macro, Bear, Bull, Risk) run in parallel.
    """
    try:
        data = await request.json()
        symbol = data.get("symbol", "BTC-USDT")
        market = data.get("market", "Crypto")
        
        async def generate_swarm_events():
            import json as _json
            from services.agents.cot_loi_bay_dan.vong_lap_thuc_thi import VongLapThucThi
            from services.agents.cot_loi_bay_dan.luu_tru_phien import LuuTruPhien
            from services.agents.cot_loi_bay_dan.mo_hinh_du_lieu import TrangThaiPhien, SuKienBayDan
            import asyncio
            import threading
            
            loop = asyncio.get_running_loop()
            q = asyncio.Queue()
            
            def swarm_callback(su_kien: SuKienBayDan):
                try:
                    # Serialize event to JSON-compatible dict
                    event_data = su_kien.model_dump(mode="json")
                    loop.call_soon_threadsafe(q.put_nowait, ("event", event_data))
                except Exception:
                    pass
                    
            def run_swarm():
                try:
                    from data.store.duong_dan import A11Paths as A11
                    kho_luu_tru = LuuTruPhien(A11.trading_sessions)
                    vong_lap = VongLapThucThi(kho_luu_tru)
                    # Launch uy_ban_dau_tu.yaml (4 specialists in parallel)
                    phien = vong_lap.bat_dau_phien(
                        ten_cau_hinh="uy_ban_dau_tu",
                        bien_nguoi_dung={"target": symbol, "market": market},
                        callback_truc_tiep=swarm_callback
                    )

                    import time
                    while phien.trang_thai in [TrangThaiPhien.cho_xu_ly, TrangThaiPhien.dang_chay]:
                        time.sleep(1)

                    # When finished, send final report
                    loop.call_soon_threadsafe(q.put_nowait, ("done", phien.bao_cao_cuoi_cung or "Analysis complete."))
                except Exception as e:
                    loop.call_soon_threadsafe(q.put_nowait, ("error", str(e)))

            thread = threading.Thread(target=run_swarm, daemon=True)
            thread.start()
            
            start_message = f"🚀 Khởi động Ủy Ban Đầu Tư AI (A03) phân tích {symbol}...\n"
            yield f"data: {_json.dumps({'delta': start_message})}\n\n"
            
            while True:
                try:
                    event_type, event_data = await asyncio.wait_for(q.get(), timeout=120.0)
                    if event_type == "event":
                        # Log nhẹ ra UI
                        if event_data.get("type") == "task_started":
                            msg = f"⏳ Chuyên gia **{event_data.get('agent_id')}** đang phân tích...\n"
                            yield f"data: {_json.dumps({'delta': msg, **event_data})}\n\n"
                        elif event_data.get("type") == "task_completed":
                            msg = f"✅ Tác vụ {event_data.get('task_id')} hoàn tất.\n"
                            yield f"data: {_json.dumps({'delta': msg, **event_data})}\n\n"
                        else:
                            yield f"data: {_json.dumps(event_data)}\n\n"
                    elif event_type == "done":
                        done_message = f"\n\n🎯 **KẾT LUẬN TỪ GIÁM ĐỐC QUẢN LÝ DANH MỤC (PM):**\n{event_data}"
                        yield f"data: {_json.dumps({'delta': done_message})}\n\n"
                        yield "data: [DONE]\n\n"
                        break
                    elif event_type == "error":
                        swarm_error = f"\n\n❌ Lỗi Swarm: {event_data}"
                        yield f"data: {_json.dumps({'delta': swarm_error})}\n\n"
                        yield "data: [DONE]\n\n"
                        break
                except asyncio.TimeoutError:
                    timeout_message = "\n\n⚠️ Timeout khi chờ Swarm."
                    yield f"data: {_json.dumps({'delta': timeout_message})}\n\n"
                    yield "data: [DONE]\n\n"
                    break
                await asyncio.sleep(0)

        return StreamingResponse(
            generate_swarm_events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )
    except Exception as e:
        logger.error(f"Swarm API init error: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "error_code": "INTERNAL_ERROR", "message": str(e)})

@app.get("/")
def read_root():
    return {"status": "ok", "message": "KAIROS API Server is running"}

@app.get("/test_gemini")
def test_gemini():
    try:
        from services.llm.xu_ly_doan_chat import ChatLLM
        llm = ChatLLM()
        res = llm.chat([{"role": "user", "content": "Hello"}])
        return {"status": "ok", "response": res.content}
    except Exception as e:
        logger.error(f"test_gemini error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"status": "error", "error_code": "INTERNAL_ERROR", "message": str(e)})

# --- Configuration Management Endpoints (A08) ---

@app.get("/api/config")
def get_trading_config():
    """Return full trading portfolio configuration."""
    # Reload from file to always serve the latest data
    trading_cfg.load()
    return JSONResponse(content=trading_cfg.config_data)

@app.post("/api/config")
async def update_trading_config(request: Request):
    """Update trading portfolio configuration."""
    try:
        new_data = await request.json()
        success = trading_cfg.save(new_data)
        if success:
            logger.info("Trading config updated via API.")
            return {"status": "success", "message": "Configuration saved successfully"}
        else:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "error_code": "CONFIG_SAVE_FAILED", "message": "Không thể lưu cấu hình."}
            )
    except Exception as e:
        logger.error(f"Config update error: {e}")
        return JSONResponse(
            status_code=400,
            content={"status": "error", "error_code": "CONFIG_INVALID", "message": str(e)}
        )

# --- Paper Trading Engine (A10 Integration) ---
from services.execution.lop_boc_thuc_thi import LopBocThucThi
from data.store.quan_ly_chien_luoc import load_strategies, save_strategies

# Facade instance shared across all API endpoints
from data.store.duong_dan import A11Paths as A11
lop_boc_api = LopBocThucThi()
_BACKTEST_RUNS_DIR = A11.backtest


def _coerce_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


_METRICS_WHITELIST = {
    "total_return", "sharpe_ratio", "max_drawdown", "win_rate",
    "profit_factor", "total_trades", "avg_win", "avg_loss", "rr_ratio", "expectancy",
}


def _load_backtest_run(run_id: str) -> dict | None:
    run_dir = _BACKTEST_RUNS_DIR / run_id
    metrics_path = run_dir / "metrics.json"
    config_path = run_dir / "config.json"
    if not metrics_path.exists():
        return None

    raw_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}

    # Whitelist metrics — only send the 10 fields the UI renders
    metrics = {k: v for k, v in raw_metrics.items() if k in _METRICS_WHITELIST}

    # Resolve strategy name and id
    strategy_name = run_id
    strategy_id = run_id
    strategy = next((item for item in load_strategies() if item.get("id") == run_id), None)
    if strategy:
        strategy_name = strategy.get("name", run_id)
        strategy_id = strategy.get("id", run_id)

    # Build lean config — rename interval→htf, drop internal-only fields
    lean_config = {
        "codes": config.get("codes", []),
        "htf": config.get("htf") or config.get("interval", ""),
        "initial_cash": config.get("initial_cash", 0.0),
        "start_date": config.get("start_date", ""),
        "end_date": config.get("end_date", ""),
    }

    return {
        "run_id": run_id,
        "strategy_id": strategy_id,
        "strategy_name": strategy_name,
        "status": "completed",
        "config": lean_config,
        "metrics": metrics,
    }


@app.get("/api/engine/status")
def get_engine_status():
    """Return detailed Paper Trading Engine status."""
    return JSONResponse(content=lop_boc_api.lay_trang_thai_gia_lap())

@app.post("/api/engine/start")
async def start_engine(request: Request):
    """Start the Paper Trading Engine."""
    try:
        data = await request.json()
        strategy_ids = data.get("strategy_ids", [])
        if not strategy_ids:
            # Default to all available strategies if none specified
            all_strategies = load_strategies()
            data["strategy_ids"] = [s["id"] for s in all_strategies]

        success = lop_boc_api.bat_dau_gia_lap(data)
        if not success:
            return JSONResponse(status_code=400, content={"status": "error", "error_code": "ENGINE_ALREADY_RUNNING", "message": "Engine đang chạy. Dừng trước khi khởi động lại."})

        return JSONResponse(content={"status": "success", "state": lop_boc_api.lay_trang_thai_gia_lap()})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "error_code": "INTERNAL_ERROR", "message": str(e)})

@app.post("/api/engine/stop")
def stop_engine():
    """Stop the Paper Trading Engine."""
    success = lop_boc_api.dung_gia_lap()
    if not success:
        return JSONResponse(status_code=400, content={"status": "error", "error_code": "ENGINE_NOT_RUNNING", "message": "Engine chưa chạy."})
    return JSONResponse(content={"status": "success", "state": lop_boc_api.lay_trang_thai_gia_lap()})

@app.get("/api/engine/positions")
def get_positions():
    """Return list of currently open positions."""
    return JSONResponse(content=lop_boc_api.lay_danh_sach_vi_the_gia_lap())

@app.get("/api/engine/logs")
def get_engine_logs(limit: int = 100):
    """Return engine log stream."""
    return JSONResponse(content=lop_boc_api.lay_log_gia_lap(limit))

@app.post("/api/engine/deploy/{strategy_id}")
def deploy_strategy(strategy_id: str):
    """Hot-deploy a strategy into the running engine."""
    success, result = lop_boc_api.deploy_chien_luoc_gia_lap(strategy_id)
    if not success:
        return JSONResponse(status_code=404, content={"status": "error", "error_code": "STRATEGY_NOT_FOUND", "message": str(result)})
    return JSONResponse(content={"status": "success", "strategy_ids": result})

@app.delete("/api/engine/deploy/{strategy_id}")
def undeploy_strategy(strategy_id: str):
    """Remove a strategy from the running engine."""
    success, result = lop_boc_api.undeploy_chien_luoc_gia_lap(strategy_id)
    return JSONResponse(content={"status": "success", "strategy_ids": result})



# --- Strategy Management Endpoints ---
from pathlib import Path

@app.get("/api/strategies")
def get_strategies():
    """Return all strategies."""
    strategies = load_strategies()
    return JSONResponse(content=strategies)

@app.get("/api/strategies/{strategy_id}")
def get_strategy(strategy_id: str):
    """Return a single strategy by ID."""
    strategies = load_strategies()
    s = next((x for x in strategies if x["id"] == strategy_id), None)
    if not s:
        return JSONResponse(status_code=404, content={"status": "error", "error_code": "STRATEGY_NOT_FOUND", "message": "Không tìm thấy chiến lược."})
    return JSONResponse(content=s)

@app.get("/api/strategies/{strategy_id}/code")
def get_strategy_code(strategy_id: str):
    """Return Python source for a strategy from its .py file in A04."""
    py_path = Path("processing.backtest/ky_nang_chien_luoc") / f"{strategy_id}.py"
    if not py_path.exists():
        return JSONResponse(status_code=404, content={"status": "error", "error_code": "STRATEGY_CODE_NOT_FOUND", "message": "Không tìm thấy file Python cho chiến lược này."})
    try:
        code = py_path.read_text(encoding="utf-8")
        return JSONResponse(content={"code": code})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "error_code": "STRATEGY_CODE_READ_ERROR", "message": str(e)})

@app.post("/api/strategies")
async def create_strategy(request: Request):
    """Create a new strategy."""
    try:
        data = await request.json()
        strategies = load_strategies()

        # --- Ensure valid id BEFORE doing anything else ---
        import uuid as _uuid
        if not data.get("id"):
            # Derive id from strategy name if available, otherwise use uuid
            raw_name = data.get("name", "")
            if raw_name:
                slug = raw_name.lower().replace(" ", "_")[:20]
                data["id"] = f"{slug}_{str(_uuid.uuid4())[:6]}"
            else:
                data["id"] = "ai_strat_" + str(_uuid.uuid4())[:8]

        # Sanitize id: only a-z, 0-9, _ (no hyphens — must be valid as a Python import name)
        import re
        data["id"] = re.sub(r"[^a-z0-9_]", "_", data["id"].lower())

        # Deduplicate id — append suffix if collision
        if any(x["id"] == data["id"] for x in strategies):
            data["id"] = data["id"] + "_" + str(_uuid.uuid4())[:4]

        # --- Save Python file if AI generated code ---
        python_code = data.pop("python_code", None)
        strategy_id = data["id"]

        if python_code:
            # Handle case where AI returns literal '\n' instead of actual newlines
            if "\\n" in python_code and "\n" not in python_code.replace("\\n", ""):
                python_code = python_code.replace("\\n", "\n")

            py_path = Path("processing.backtest/ky_nang_chien_luoc") / f"{strategy_id}.py"
            py_path.parent.mkdir(parents=True, exist_ok=True)
            py_path.write_text(python_code, encoding="utf-8")
            logger.info(f"Saved Python file for strategy: {py_path}")

            # Hot-register into memory registry so a server restart is not required
            try:
                from processing.backtest.ky_nang_chien_luoc import dang_ky_chien_luoc
                dang_ky_chien_luoc(
                    strategy_id,
                    f"processing.backtest.ky_nang_chien_luoc.{strategy_id}",
                    "SignalEngine"
                )
            except Exception as reg_err:
                logger.warning(f"Hot-register failed (restart required for A04): {reg_err}")

        # --- Fill missing default fields ---
        import datetime
        data.setdefault("last_return", 0.0)
        data.setdefault("sharpe", 0.0)
        data.setdefault("max_drawdown", 0.0)
        data.setdefault("win_rate", 0.0)
        data.setdefault("mode", "DEMO")
        data.setdefault("exchange", data.get("exchange", "OKX"))
        data.setdefault("tags", [])
        data.setdefault("codes", [])
        data.setdefault("params", {})
        data.setdefault("backtest_mode", "B2B")
        data.setdefault("created_at", datetime.datetime.now().isoformat())

        strategies.append(data)
        save_strategies(strategies)
        logger.success(f"Created new strategy: {data.get('name')} (id={strategy_id})")
        return JSONResponse(content={"status": "success", "strategy": data})
    except Exception as e:
        logger.error(f"Strategy creation error: {e}")
        return JSONResponse(status_code=400, content={"status": "error", "error_code": "INVALID_BODY", "message": str(e)})


@app.put("/api/strategies/{strategy_id}")
async def update_strategy(strategy_id: str, request: Request):
    """Update a strategy by ID."""
    try:
        data = await request.json()
        strategies = load_strategies()
        idx = next((i for i, x in enumerate(strategies) if x["id"] == strategy_id), None)
        if idx is None:
            return JSONResponse(status_code=404, content={"status": "error", "error_code": "STRATEGY_NOT_FOUND", "message": "Không tìm thấy chiến lược."})
        strategies[idx] = {**strategies[idx], **data}
        save_strategies(strategies)
        logger.info(f"Updated strategy: {strategy_id}")
        return JSONResponse(content={"status": "success", "strategy": strategies[idx]})
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "error_code": "INVALID_BODY", "message": str(e)})

@app.delete("/api/strategies/{strategy_id}")
def delete_strategy(strategy_id: str):
    """Delete a strategy by ID."""
    strategies = load_strategies()
    new_list = [x for x in strategies if x["id"] != strategy_id]
    if len(new_list) == len(strategies):
        return JSONResponse(status_code=404, content={"status": "error", "error_code": "STRATEGY_NOT_FOUND", "message": "Không tìm thấy chiến lược."})
    save_strategies(new_list)

    # Remove corresponding Python file if it exists
    py_path = Path("processing.backtest/ky_nang_chien_luoc") / f"{strategy_id}.py"
    if py_path.exists():
        try:
            py_path.unlink()
            logger.info(f"Deleted Python file: {py_path}")
        except Exception as e:
            logger.error(f"Could not delete file {py_path}: {e}")

    logger.warning(f"Deleted strategy: {strategy_id}")
    return JSONResponse(content={"status": "success", "deleted_id": strategy_id})


@app.get("/api/runs")
def list_backtest_runs():
    """List all saved backtest runs for frontend review."""
    if not _BACKTEST_RUNS_DIR.exists():
        return JSONResponse(content=[])

    runs = []
    for run_dir in sorted(_BACKTEST_RUNS_DIR.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
        if not run_dir.is_dir():
            continue
        run_data = _load_backtest_run(run_dir.name)
        if run_data is not None:
            runs.append(run_data)
    return JSONResponse(content=runs)


@app.get("/api/runs/{run_id}")
def get_backtest_run(run_id: str):
    """Return backtest results by run id (frontend-compatible)."""
    run_data = _load_backtest_run(run_id)
    if run_data is None:
        return JSONResponse(status_code=404, content={"status": "error", "error_code": "RUN_NOT_FOUND", "message": "Không tìm thấy backtest run."})
    return JSONResponse(content=run_data)


@app.get("/api/artifacts/{run_id}/{file_name}")
def get_backtest_artifact(run_id: str, file_name: str):
    """Serve a CSV/JSON artifact file for a backtest run."""
    allowed_exact = {"equity.csv", "trades.csv", "positions.csv", "metrics.csv", "metrics.json", "config.json"}

    # Allow static files and dynamic ohlcv_* files
    if file_name not in allowed_exact and not file_name.startswith("ohlcv_"):
        return JSONResponse(status_code=400, content={"status": "error", "error_code": "ARTIFACT_NOT_ALLOWED", "message": "File này không được phép truy cập."})

    run_dir = _BACKTEST_RUNS_DIR / run_id
    candidates = [
        run_dir / "artifacts" / file_name,
        run_dir / file_name,
    ]
    file_path = next((path for path in candidates if path.exists() and path.is_file()), None)
    if file_path is None:
        return JSONResponse(status_code=404, content={"status": "error", "error_code": "ARTIFACT_NOT_FOUND", "message": "Không tìm thấy artifact."})

    media_type = "application/json" if file_path.suffix == ".json" else "text/csv"
    return FileResponse(path=file_path, media_type=media_type, filename=file_path.name)


@app.post("/api/backtest/run")
async def run_backtest_from_payload(request: Request):
    """Trigger a full backtest via the A04 engine and return complete results."""
    import shutil
    import json
    import datetime
    
    try:
        data = await request.json()
    except Exception:
        data = {}
        
    strategy_id = data.get("strategy_id")
    if not strategy_id:
        return JSONResponse(status_code=400, content={"status": "error", "error_code": "MISSING_FIELD", "message": "Trường 'strategy_id' là bắt buộc."})

    strategies = load_strategies()
    s = next((x for x in strategies if x["id"] == strategy_id), None)
    if not s:
        return JSONResponse(status_code=404, content={"status": "error", "error_code": "STRATEGY_NOT_FOUND", "message": "Không tìm thấy chiến lược."})

    try:
        # 1. Prepare run directory (sandbox)
        from data.store.duong_dan import A11Paths as A11
        run_dir = A11.backtest_run(strategy_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        code_dir = run_dir / "code"
        code_dir.mkdir(exist_ok=True)

        # 2. Write config.json
        codes = s.get("codes", ["BTC-USDT"])
        if not codes: codes = ["BTC-USDT"]

        raw_htf = s.get("htf", "1H")
        if isinstance(raw_htf, list) and raw_htf: raw_htf = raw_htf[0]
        if isinstance(raw_htf, str) and "/" in raw_htf: raw_htf = raw_htf.split("/")[0]
        interval = str(raw_htf).lower()

        start_date = s.get("start_date", "")
        end_date = s.get("end_date", "")

        bt_config = {
            "source": "auto",
            "codes": codes,
            "htf": interval,
            "interval": interval,
            "initial_cash": float(s.get("initial_cash", 1000000)),
            "slippage": float(s.get("slippage", 0.001)),
            "maker_rate": 0.0002,
            "taker_rate": 0.0005,
        }
        if start_date: bt_config["start_date"] = start_date
        if end_date: bt_config["end_date"] = end_date

        with open(run_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(bt_config, f, indent=2)

        # 3. Copy strategy file
        src_py = Path(f"processing.backtest/ky_nang_chien_luoc/{strategy_id}.py")
        if not src_py.exists():
            return JSONResponse(status_code=404, content={"status": "error", "error_code": "STRATEGY_CODE_NOT_FOUND", "message": "Không tìm thấy file code cho chiến lược này."})

        shutil.copy2(src_py, code_dir / "signal_engine.py")

        # 4. Run A04 engine via LopBocThucThi
        logger.info(f"[BACKTEST] Starting A04 engine for {strategy_id}...")
        from services.execution.lop_boc_thuc_thi import LopBocThucThi
        try:
            lop_boc = LopBocThucThi()
            lop_boc.thuc_thi_kiem_thu(str(run_dir))
        except Exception as exec_err:
            logger.error(f"[A04 Engine Error] {exec_err}")
            return JSONResponse(status_code=500, content={"status": "error", "error_code": "BACKTEST_ENGINE_ERROR", "message": str(exec_err)})

        # 5. Read results from A04 (using _read_csv_rows helper instead of pandas)
        metrics_file = run_dir / "metrics.json"
        trades_file = run_dir / "trades.csv"
        equity_file = run_dir / "equity.csv"

        if not metrics_file.exists():
            logger.error(f"Backtest finished but {metrics_file} not found.")
            return JSONResponse(status_code=500, content={"status": "error", "error_code": "BACKTEST_RESULTS_MISSING", "message": "Backtest hoàn thành nhưng không tạo được file kết quả."})

        with open(metrics_file, "r", encoding="utf-8") as f:
            metrics = json.load(f)

        # 6. Persist metrics to the strategy database (JSON)
        s["last_return"] = round(metrics.get("total_return", 0), 2)
        s["sharpe"] = round(metrics.get("sharpe_ratio", 0), 2)
        s["max_drawdown"] = round(metrics.get("max_drawdown", 0), 2)
        s["win_rate"] = round(metrics.get("win_rate", 0), 2)
        save_strategies(strategies)

        logger.success(f"[BACKTEST] Backtest completed for {strategy_id}.")
        return JSONResponse(content={"run_id": strategy_id})

    except Exception as e:
        logger.error(f"Backtest run error: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "error_code": "INTERNAL_ERROR", "message": str(e)})
