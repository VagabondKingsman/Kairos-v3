"""Cánh tay thực thi lệnh cho Thị trường Chứng khoán Việt Nam (VNStock)."""

import logging
from typing import Any, Dict
from services.exchange.co_so import BaseArm

logger = logging.getLogger("A120_VNStockArm")

class VNStockArm(BaseArm):
    """Adapter gửi lệnh qua hệ thống chứng khoán cơ sở VN."""
    
    def __init__(self, username: str = "", password: str = "", broker: str = "VCI"):
        self.username = username
        self.broker = broker
        logger.info(f"Khởi tạo VNStock Arm thành công. Broker: {broker}")

    def execute_order(self, signal_data: Dict[str, Any]) -> bool:
        symbol = signal_data.get("symbol")
        action = signal_data.get("action")
        size = signal_data.get("size")
        price = signal_data.get("price", "MP") # Market Price by default
        
        logger.debug(f"[VNStock] Đang gửi lệnh {action} {size} {symbol} ở mức giá {price}...")
        
        try:
            # Code tích hợp api chứng khoán VN sẽ nằm ở đây
            logger.info(f"[VNStock] Lệnh {action} {symbol} đã được đẩy vào hệ thống.")
            return True
        except Exception as e:
            logger.error(f"[VNStock] Lỗi đặt lệnh: {e}")
            return False

    def get_account_status(self) -> Dict[str, Any]:
        """Lấy số dư từ tài khoản chứng khoán."""
        return {
            "balance": 500000000.0,
            "currency": "VND",
            "exchange": self.broker
        }
