"""
Thư mục Engines cho hệ thống Backtest đa thị trường.
Mỗi engine kế thừa từ BaseEngine và định nghĩa các quy tắc giao dịch (luật T+, phí, trượt giá...)
đặc thù cho từng loại tài sản.
"""

from processing.backtest.dong_co_kiem_thu.bo_xu_ly.co_so import BaseEngine
from processing.backtest.dong_co_kiem_thu.bo_xu_ly.co_so_phai_sinh import FuturesBaseEngine
from processing.backtest.dong_co_kiem_thu.bo_xu_ly.tien_dien_tu import CryptoEngine
from processing.backtest.dong_co_kiem_thu.bo_xu_ly.ngoai_hoi import ForexEngine
from processing.backtest.dong_co_kiem_thu.bo_xu_ly.co_phieu_toan_cau import GlobalEquityEngine
from processing.backtest.dong_co_kiem_thu.bo_xu_ly.phai_sinh_toan_cau import GlobalFuturesEngine
from processing.backtest.dong_co_kiem_thu.bo_xu_ly.co_phieu_viet_nam import VietnamEquityEngine
from processing.backtest.dong_co_kiem_thu.bo_xu_ly.danh_muc_quyen_chon import run_options_backtest, OptionPosition

__all__ = [
    "BaseEngine",
    "FuturesBaseEngine",
    "CryptoEngine",
    "ForexEngine",
    "GlobalEquityEngine",
    "GlobalFuturesEngine",
    "VietnamEquityEngine",
    "run_options_backtest",
    "OptionPosition",
]
