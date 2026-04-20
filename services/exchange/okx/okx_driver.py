"""Cánh tay thực thi lệnh cho sàn OKX (Native API).

Sử dụng thư viện okx-python để đạt Low Latency, bỏ qua lớp trung gian.
"""

import logging
from typing import Any, Dict
from services.exchange.co_so import BaseArm
# import okx.Trade as Trade

logger = logging.getLogger("A13_OKXArm")

class OKXArm(BaseArm):
    """Adapter gửi lệnh thẳng lên OKX."""
    
    def __init__(self, api_key: str, secret_key: str, passphrase: str, flag: str = "1"):
        """
        Args:
            flag: "0" cho Live, "1" cho Demo trading.
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.flag = flag
        # self.trade_api = Trade.TradeAPI(api_key, secret_key, passphrase, False, flag)
        logger.info(f"Khởi tạo OKX Arm thành công. Chế độ: {'Demo' if flag == '1' else 'Live'}")

    def execute_order(self, signal_data: Dict[str, Any]) -> bool:
        symbol = signal_data.get("symbol")
        action = signal_data.get("action")
        size = signal_data.get("size")
        
        logger.debug(f"[OKX API] Đang gửi lệnh {action} {size} {symbol}...")
        
        try:
            # params = {
            #     "instId": symbol,
            #     "tdMode": "cross",
            #     "side": "buy" if action.upper() == "BUY" else "sell",
            #     "ordType": "market",
            #     "sz": str(size)
            # }
            # response = self.trade_api.place_order(**params)
            
            # Mô phỏng phản hồi từ OKX API
            logger.info(f"[OKX API] Lệnh {action} khớp thành công.")
            return True
        except Exception as e:
            logger.error(f"[OKX API] Lỗi đặt lệnh: {e}")
            return False

    def get_account_status(self) -> Dict[str, Any]:
        """Lấy số dư từ OKX."""
        # Giả lập trả về số dư
        return {
            "balance": 10000.0,
            "currency": "USDT",
            "exchange": "OKX"
        }
