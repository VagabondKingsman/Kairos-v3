"""
services.exchange — Cánh Tay Thực Thi (Action Taker) KAIROS v3.0

Driver gắn kết trực tiếp với từng sàn giao dịch / nguồn dữ liệu.
Tất cả driver phải kế thừa từ BaseArm và triển khai 2 phương thức:
    - execute_order(signal_data)
    - get_account_status()

Các adapter hiện có:
    ┌──────────────┬──────────────────────────────────────────┐
    │ OKXArm       │ OKX Native API (crypto, thấp độ trễ)    │
    │ CCXTArm      │ CCXT (Binance, Bybit, v.v...)           │
    │ VNStockArm   │ Chứng khoán Việt Nam (VCI, SSI)         │
    │ YFinanceArm  │ Cổ phiếu toàn cầu (chỉ đọc/backtest)   │
    └──────────────┴──────────────────────────────────────────┘

Cách dùng:
    from services.exchange import tao_canh_tay
    arm = tao_canh_tay("OKX", api_key=..., secret_key=..., passphrase=...)
    arm.execute_order({"symbol": "BTC-USDT", "action": "BUY", "size": 0.01})
"""
from services.exchange.co_so import BaseArm
from typing import Any


def tao_canh_tay(san: str, **kwargs) -> BaseArm:
    """Factory tạo Cánh tay thực thi theo tên sàn.

    Args:
        san: "OKX", "CCXT", "VNSTOCK", hoặc "YFINANCE".
        **kwargs: Tham số khởi tạo cho driver tương ứng.

    Returns:
        Instance của adapter tương ứng.

    Raises:
        ValueError: Nếu tên sàn không hợp lệ.
    """
    san_upper = san.upper()
    if san_upper == "OKX":
        from services.exchange.okx.okx_driver import OKXArm
        return OKXArm(**kwargs)
    elif san_upper == "CCXT":
        from services.exchange.ccxt.ccxt_driver import CCXTArm
        return CCXTArm(**kwargs)
    elif san_upper == "VNSTOCK":
        from services.exchange.vnstock.vnstock_driver import VNStockArm
        return VNStockArm(**kwargs)
    elif san_upper == "YFINANCE":
        from services.exchange.yfinance.yfinance_driver import YFinanceArm
        return YFinanceArm(**kwargs)
    else:
        raise ValueError(
            f"Sàn '{san}' không được hỗ trợ. Chọn: OKX | CCXT | VNSTOCK | YFINANCE"
        )


__all__ = ["tao_canh_tay", "BaseArm"]
