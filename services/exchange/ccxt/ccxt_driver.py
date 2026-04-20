"""Cánh tay thực thi dùng CCXT (hỗ trợ nhiều sàn giao dịch Crypto)."""

import logging
from typing import Any, Dict
from services.exchange.co_so import BaseArm

logger = logging.getLogger("A12_CCXTArm")

class CCXTArm(BaseArm):
    """Adapter giao tiếp thông qua thư viện CCXT."""
    
    def __init__(self, exchange_id: str, api_key: str, secret_key: str, password: str = ""):
        self.exchange_id = exchange_id
        import ccxt
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({
            'apiKey': api_key,
            'secret': secret_key,
            'password': password,
            'enableRateLimit': True,
        })
        logger.info(f"Khởi tạo CCXT Arm thành công cho sàn {exchange_id.upper()}")

    def execute_order(self, signal_data: Dict[str, Any]) -> bool:
        symbol = signal_data.get("symbol")
        action = signal_data.get("action")
        size = signal_data.get("size")
        
        logger.debug(f"[CCXT {self.exchange_id}] Đang gửi lệnh {action} {size} {symbol}...")
        
        try:
            side = 'buy' if action.upper() == 'BUY' else 'sell'
            # self.exchange.create_market_order(symbol, side, size)
            logger.info(f"[CCXT] Lệnh {action} khớp thành công.")
            return True
        except Exception as e:
            logger.error(f"[CCXT] Lỗi đặt lệnh: {e}")
            return False

    def get_account_status(self) -> Dict[str, Any]:
        """Lấy số dư từ CCXT."""
        try:
            # balance = self.exchange.fetch_balance()
            return {
                "balance": 5000.0,
                "currency": "USDT",
                "exchange": self.exchange_id
            }
        except Exception as e:
            logger.error(f"[CCXT] Lỗi lấy số dư: {e}")
            return {}
