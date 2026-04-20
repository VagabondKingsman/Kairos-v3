from utils.helpers.bo_ghi_log_he_thong import logger
from processing.backtest.bo_thuc_thi_kiem_thu import BacktestExecutor, BoThucThiKiemThu
from services.execution.bo_thuc_thi_gia_lap import BoThucThiGiaLap
from services.execution.bo_thuc_thi_thuc_te import BoThucThiThucTe
from data.store.quan_ly_chien_luoc import load_strategies

class LopBocThucThi:
    """
    Facade API cho Động cơ Thực thi - Hiện đã chuyển sang A10.
    Quản lý Singleton cho Paper Trading Engine.
    """
    _gia_lap_engine = None

    def __init__(self, cau_hinh: dict = None):
        self.cau_hinh = cau_hinh or {}
        if LopBocThucThi._gia_lap_engine is None:
            LopBocThucThi._gia_lap_engine = BoThucThiGiaLap(self.cau_hinh)

    def thuc_thi_kiem_thu(self, thu_muc_run: str):
        bo_thuc_thi = BacktestExecutor(self.cau_hinh)
        return bo_thuc_thi.run(thu_muc_run)

    def lay_trang_thai_gia_lap(self) -> dict:
        return self._gia_lap_engine.get_status()

    def bat_dau_gia_lap(self, data: dict):
        return self._gia_lap_engine.run(data)

    def dung_gia_lap(self):
        return self._gia_lap_engine.dung()

    def lay_danh_sach_vi_the_gia_lap(self):
        return {
            "positions": self._gia_lap_engine.positions, 
            "closed_trades": self._gia_lap_engine.closed_trades[-50:]
        }

    def lay_log_gia_lap(self, limit: int = 100):
        return {"logs": self._gia_lap_engine.logs[-limit:]}

    def deploy_chien_luoc_gia_lap(self, strategy_id: str):
        strategies = load_strategies()
        s = next((x for x in strategies if x["id"] == strategy_id), None)
        if not s: return False, "Strategy not found"
        if strategy_id not in self._gia_lap_engine.strategy_ids:
            self._gia_lap_engine.strategy_ids.append(strategy_id)
            self._gia_lap_engine._add_log("INFO", f"🔌 Hot-deploy: {s['name']}")
        return True, self._gia_lap_engine.strategy_ids

    def undeploy_chien_luoc_gia_lap(self, strategy_id: str):
        if strategy_id in self._gia_lap_engine.strategy_ids:
            self._gia_lap_engine.strategy_ids.remove(strategy_id)
        return True, self._gia_lap_engine.strategy_ids

    def thuc_thi_thuc_te(self, ket_noi_san):
        bo_thuc_thi = BoThucThiThucTe(self.cau_hinh)
        return bo_thuc_thi.run(ket_noi_san)
