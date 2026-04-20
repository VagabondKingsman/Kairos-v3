"""
Các mô hình dữ liệu dùng chung cho hệ thống backtest.

Sử dụng dataclasses (frozen=True) để đảm bảo tính bất biến của dữ liệu
cho các vị thế, lịch sử giao dịch và ảnh chụp trạng thái tài khoản.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Position:
    """
    Thông tin về một vị thế đang mở.

    Attributes:
        symbol: Mã chứng khoán / tài sản.
        direction: Hướng giao dịch (1 cho Long/Mua, -1 cho Short/Bán).
        entry_price: Giá khớp lệnh tại điểm vào.
        entry_time: Thời điểm mở vị thế (datetime).
        size: Khối lượng cổ phiếu / hợp đồng / coin.
        leverage: Đòn bẩy tài chính sử dụng (mặc định 1.0 cho cổ phiếu cơ sở).
        entry_bar_idx: Chỉ số cây nến tại thời điểm vào (dùng để tính thời gian nắm giữ).
        entry_commission: Phí giao dịch đã trả khi mở vị thế.
    """

    symbol: str
    direction: int
    entry_price: float
    entry_time: datetime
    size: float
    leverage: float = 1.0
    entry_bar_idx: int = 0
    entry_commission: float = 0.0


@dataclass(frozen=True)
class TradeRecord:
    """
    Bản ghi về một giao dịch đã hoàn tất (Round-trip).

    Attributes:
        symbol: Mã chứng khoán / tài sản.
        direction: Hướng giao dịch ban đầu (1 cho Long, -1 cho Short).
        entry_price: Giá thực hiện lệnh vào.
        exit_price: Giá thực hiện lệnh ra.
        entry_time: Thời điểm vào lệnh.
        exit_time: Thời điểm thoát lệnh.
        size: Khối lượng đã giao dịch.
        leverage: Đòn bẩy đã sử dụng.
        pnl: Lợi nhuận/Lỗ thực tế (bằng tiền mặt).
        pnl_pct: Lợi nhuận/Lỗ tính theo phần trăm trên vốn ký quỹ.
        exit_reason: Lý do đóng vị thế (tín hiệu, thanh lý, hoặc kết thúc backtest).
        holding_bars: Số lượng cây nến đã nắm giữ vị thế.
        commission: Tổng phí giao dịch (phí vào + phí ra).
    """

    symbol: str
    direction: int
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    size: float
    leverage: float
    pnl: float
    pnl_pct: float
    exit_reason: str
    holding_bars: int
    commission: float


@dataclass(frozen=True)
class EquitySnapshot:
    """
    Ảnh chụp trạng thái tài sản tại một thời điểm (mỗi cây nến).

    Attributes:
        timestamp: Thời điểm chụp ảnh (thường là thời gian đóng cửa nến).
        capital: Tiền mặt hiện có (Sức mua khả dụng).
        unrealized: Tổng lợi nhuận/lỗ tạm tính của tất cả các vị thế đang mở.
        equity: Tổng tài sản thực tế (Tiền mặt + Ký quỹ đang dùng + Lãi/lỗ tạm tính).
        positions: Số lượng vị thế đang mở tại thời điểm đó.
    """

    timestamp: datetime
    capital: float
    unrealized: float
    equity: float
    positions: int