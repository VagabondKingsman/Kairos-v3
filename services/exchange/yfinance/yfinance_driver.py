"""Cánh tay thực thi dùng YFinance (Paper Trading).
Do YFinance chỉ cung cấp dữ liệu giá (không hỗ trợ giao dịch thật), 
Arm này đóng vai trò như một Portfolio Tracker cho chế độ Demo.
"""

import logging
from typing import Any, Dict
from services.exchange.co_so import BaseArm

logger = logging.getLogger("A12_YFinanceArm")

class YFinanceArm(BaseArm):
    """Adapter giả lập giao dịch trên chứng khoán toàn cầu bằng YFinance."""
    
    def __init__(self, initial_balance: float = 100000.0):
        self.balance = initial_balance
        self.positions = {}
        logger.info(f"Khởi tạo YFinance Arm (Paper Trading) thành công. Vốn: {initial_balance}$")

    def execute_order(self, signal_data: Dict[str, Any]) -> bool:
        symbol = signal_data.get("symbol")
        action = signal_data.get("action")
        size = signal_data.get("size")
        price = signal_data.get("price", 0.0) # Phải có giá truyền vào vì YF không khớp lệnh
        
        logger.debug(f"[YFinance Paper] Nhận lệnh {action} {size} {symbol} @ {price}")
        
        try:
            value = size * price
            if action.upper() == "BUY":
                if self.balance >= value:
                    self.balance -= value
                    self.positions[symbol] = self.positions.get(symbol, 0) + size
                    logger.info(f"[YFinance Paper] MUA {size} {symbol}. Số dư còn: {self.balance}$")
                    return True
                else:
                    logger.warning("[YFinance Paper] Không đủ số dư để MUA!")
                    return False
            elif action.upper() == "SELL":
                current_size = self.positions.get(symbol, 0)
                if current_size >= size:
                    self.positions[symbol] -= size
                    self.balance += value
                    logger.info(f"[YFinance Paper] BÁN {size} {symbol}. Số dư còn: {self.balance}$")
                    return True
                else:
                    logger.warning("[YFinance Paper] Không đủ cổ phiếu để BÁN!")
                    return False
        except Exception as e:
            logger.error(f"[YFinance Paper] Lỗi giả lập lệnh: {e}")
            return False

    def get_account_status(self) -> Dict[str, Any]:
        """Lấy số dư hiện tại của tài khoản Paper."""
        return {
            "balance": self.balance,
            "currency": "USD",
            "exchange": "YFinance_Paper",
            "positions": self.positions
        }
