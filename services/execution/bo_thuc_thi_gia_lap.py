import time
import threading
import uuid
import json
import os
from typing import Any
from pathlib import Path
import pandas as pd
import numpy as np

from processing.backtest.bo_thuc_thi_co_so import BaseExecutor, BoThucThiCoSo
from utils.helpers.bo_ghi_log_he_thong import logger
from data.store.quan_ly_chien_luoc import load_strategies

from data.store.duong_dan import A11Paths as A11
STATE_FILE = A11.root / "trang_thai_lenh.json"

class BoThucThiGiaLap(BaseExecutor):
    """
    Thực thi giả lập (Paper Trading) - Chạy tại A10.
    Bổ sung: Lưu trữ trạng thái xuống file để phục hồi sau khi restart server.
    """
    
    def __init__(self, cau_hinh: dict = None):
        super().__init__(cau_hinh)
        self.is_running = False
        self.mode = "DEMO"
        self.exchange = "OKX"
        self.start_time = None
        self.strategy_ids: list = []    # Danh sách chiến lược đang chạy
        self.positions: list = []       # Vị thế đang mở
        self.closed_trades: list = []   # Lịch sử lệnh đã đóng
        self.logs: list = []            # Log nội bộ engine
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self.equity = 10_000.0          # Vốn Paper (USD)
        self.initial_equity = 10_000.0
        
        # Tự động nạp lại trạng thái cũ nếu có
        self._load_state()

    def load_data(self, *args, **kwargs):
        """ABC contract; paper engine loads data inside _scan_and_trade."""
        return {}

    # Backward-compatible alias
    tai_du_lieu = load_data

    def _save_state(self):
        """Lưu trạng thái hiện tại xuống file JSON (Crash Recovery)."""
        try:
            state = {
                "equity": self.equity,
                "initial_equity": self.initial_equity,
                "positions": self.positions,
                "closed_trades": self.closed_trades[-100:], # Chỉ lưu 100 lệnh gần nhất để tiết kiệm dung lượng
                "strategy_ids": self.strategy_ids
            }
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"Không thể lưu trạng thái Engine: {e}")

    def _load_state(self):
        """Nạp lại trạng thái từ file JSON."""
        if STATE_FILE.exists():
            try:
                state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                self.equity = state.get("equity", 10_000.0)
                self.initial_equity = state.get("initial_equity", 10_000.0)
                self.positions = state.get("positions", [])
                self.closed_trades = state.get("closed_trades", [])
                self.strategy_ids = state.get("strategy_ids", [])
                logger.info(f"✅ Đã phục hồi trạng thái Engine: {len(self.positions)} vị thế đang mở.")
            except Exception as e:
                logger.error(f"Lỗi khi nạp lại trạng thái Engine: {e}")

    def _add_log(self, level: str, msg: str):
        self.logs.append({
            "id": str(uuid.uuid4())[:8],
            "time": time.strftime("%H:%M:%S"),
            "ts": time.time(),
            "level": level,
            "message": msg
        })
        if len(self.logs) > 500:
            self.logs = self.logs[-500:]
        logger.info(f"[ENGINE-{self.mode}] {msg}")

    def run(self, data: Any = None) -> Any:
        if self.is_running:
            return False

        mode = data.get("mode", "DEMO") if isinstance(data, dict) else "DEMO"
        exchange = data.get("exchange", "OKX") if isinstance(data, dict) else "OKX"
        strategy_ids = data.get("strategy_ids", self.strategy_ids)

        self.is_running = True
        self.mode = mode
        self.exchange = exchange
        self.strategy_ids = strategy_ids
        self.start_time = time.time()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="KairosEngine")
        self._thread.start()
        self._add_log("INFO", f"🚀 Engine started | Mode: {mode} | Strategies: {strategy_ids}")
        return True

    # Backward-compatible alias
    chay = run

    def dung(self):
        if not self.is_running:
            return False
        self._stop_event.set()
        self.is_running = False
        self.start_time = None
        self._save_state() # Lưu lại lần cuối khi dừng
        self._add_log("WARNING", "🛑 Engine đã dừng.")
        return True

    def _run_loop(self):
        INTERVAL_S = 30
        while not self._stop_event.is_set():
            try:
                self._scan_and_trade()
                self._save_state() # Lưu trạng thái sau mỗi chu kỳ quét thành công
            except Exception as e:
                self._add_log("ERROR", f"Lỗi vòng lặp: {e}")
            self._stop_event.wait(INTERVAL_S)

    def _scan_and_trade(self):
        strategies = load_strategies()
        active = [s for s in strategies if s["id"] in self.strategy_ids]
        if not active: return

        from processing.backtest.ky_nang_chien_luoc import lay_chien_luoc
        from data.loaders import lay_du_lieu
        
        for s in active:
            try:
                engine = lay_chien_luoc(s["id"], **s.get("params", {}))
                codes = s.get("codes", ["BTC-USDT"])
                htf = s.get("htf", "1H")
                if isinstance(htf, list): htf = htf[0]
                
                data_map = {}
                for code in codes:
                    df_pl = lay_du_lieu(symbol=code, timeframe=htf, source="auto", limit=100)
                    df = df_pl.to_pandas()
                    df.set_index("timestamp", inplace=True)
                    data_map[code] = df

                signals = engine.generate(data_map)

                for symbol, sig_series in signals.items():
                    last_sig = int(sig_series.iloc[-1]) if hasattr(sig_series, "iloc") else 0
                    current_price = float(data_map[symbol]["close"].iloc[-1])
                    has_pos = any(p["symbol"] == symbol and p["strategy_id"] == s["id"] for p in self.positions)

                    if last_sig == 1 and not has_pos:
                        self._add_log("INFO", f"🔔 Chiến lược {s['name']} báo MUA {symbol}. Đang xin ý kiến A03...")
                        
                        try:
                            from services.agents.cot_loi_bay_dan.vong_lap_thuc_thi import VongLapThucThi
                            from services.agents.cot_loi_bay_dan.luu_tru_phien import LuuTruPhien
                            from services.agents.cot_loi_bay_dan.mo_hinh_du_lieu import TrangThaiPhien
                            import time
                            import uuid

                            from data.store.duong_dan import A11Paths as A11
                            kho_luu_tru = LuuTruPhien(A11.trading_sessions)
                            vong_lap = VongLapThucThi(kho_luu_tru)
                            phien = vong_lap.bat_dau_phien(
                                ten_cau_hinh="uy_ban_duyet_lenh",
                                bien_nguoi_dung={"target": symbol, "market": "Crypto"}
                            )
                            
                            # Chờ A03 hoàn thành (Blocking wait)
                            while phien.trang_thai in [TrangThaiPhien.cho_xu_ly, TrangThaiPhien.dang_chay]:
                                time.sleep(2)
                                
                            if phien.trang_thai == TrangThaiPhien.hoan_thanh:
                                ket_luan = phien.bao_cao_cuoi_cung or ""
                                if "DUYỆT" in ket_luan.upper() or "MUA" in ket_luan.upper():
                                    size_usd = self.equity * 0.02
                                    qty = round(size_usd / current_price, 6)
                                    pos = {
                                        "id": str(uuid.uuid4())[:8], "symbol": symbol, "strategy_id": s["id"],
                                        "strategy_name": s["name"], "side": "LONG", "entry_price": current_price,
                                        "qty": qty, "size_usd": round(size_usd, 2),
                                        "sl_pct": s.get("params", {}).get("sl_pct", 2.0),
                                        "tp_ratio": s.get("params", {}).get("tp_ratio", 2.0),
                                        "open_time": time.strftime("%Y-%m-%dT%H:%M:%S"), "unrealized_pnl": 0.0,
                                    }
                                    pos["tp_price"] = current_price * (1 + pos["sl_pct"] * pos["tp_ratio"] / 100)
                                    pos["sl_price"] = current_price * (1 - pos["sl_pct"] / 100)
                                    self.positions.append(pos)
                                    self._add_log("SUCCESS", f"✅ A03 DUYỆT LỆNH: MUA {symbol} @ {current_price:.2f}")
                                else:
                                    ly_do = ket_luan[:100].replace("\n", " ")
                                    self._add_log("WARNING", f"❌ A03 TỪ CHỐI LỆNH MUA {symbol}: {ly_do}...")
                            else:
                                self._add_log("ERROR", f"⚠️ Lỗi A03 khi duyệt lệnh {symbol}: {phien.trang_thai.value}")
                        except Exception as e:
                            self._add_log("ERROR", f"⚠️ Lỗi tích hợp A03: {str(e)}")

                    elif last_sig == -1 and has_pos:
                        pos = next((p for p in self.positions if p["symbol"] == symbol and p["strategy_id"] == s["id"]), None)
                        if pos:
                            pnl = (current_price - pos["entry_price"]) * pos["qty"]
                            self.equity += pnl
                            pnl_pct = round(pnl / pos["size_usd"], 4) if pos.get("size_usd") else 0.0
                            trade_record = {
                                "id": pos["id"],
                                "symbol": pos["symbol"],
                                "strategy_name": pos["strategy_name"],
                                "entry_price": pos["entry_price"],
                                "exit_price": current_price,
                                "close_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                "pnl_usd": round(pnl, 2),
                                "pnl_pct": pnl_pct,
                            }
                            self.closed_trades.append(trade_record)
                            self.positions = [p for p in self.positions if p["id"] != pos["id"]]
                            self._add_log("SUCCESS", f"CLOSE {symbol} | PnL: {pnl:.2f}$")

            except Exception as e:
                self._add_log("ERROR", f"Lỗi chiến lược [{s['id']}]: {e}")

        for pos in self.positions:
            try:
                lp = float(data_map[pos["symbol"]]["close"].iloc[-1])
                pos["unrealized_pnl"] = round((lp - pos["entry_price"]) * pos["qty"], 2)
                pos["current_price"] = lp
            except: pass

    def get_status(self) -> dict:
        uptime = round(time.time() - self.start_time, 0) if self.start_time else 0
        total_pnl = sum(t.get("pnl_usd", 0) for t in self.closed_trades)
        unrealized = sum(p.get("unrealized_pnl", 0) for p in self.positions)
        total_pnl_pct = round((self.equity - self.initial_equity) / self.initial_equity, 4) if self.initial_equity else 0.0
        return {
            "is_running": self.is_running,
            "mode": self.mode,
            "exchange": self.exchange,
            "start_time": self.start_time,
            "uptime_s": uptime,
            "strategy_ids": self.strategy_ids,
            "open_positions": len(self.positions),
            "total_trades": len(self.closed_trades),
            "initial_equity": round(self.initial_equity, 2),
            "equity": round(self.equity, 2),
            "total_pnl_usd": round(total_pnl, 2),
            "total_pnl_pct": total_pnl_pct,
            "unrealized_pnl": round(unrealized, 2),
        }
