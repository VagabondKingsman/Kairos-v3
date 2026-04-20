"""Backtest engine for the Vietnam cash equity market.

Market rules:
  - T+2.5: Shares purchased settle on the afternoon of T+2.
  - Short selling: Not permitted for retail investors on the cash market.
  - Price limits: ±7% (HOSE), ±10% (HNX), ±15% (UPCOM).
  - Minimum lot size: 100 shares.
  - Commission: Typically 0.1%–0.3% (both sides).
  - Tax (stamp/income tax): 0.1% on the sell side only.
"""

from __future__ import annotations
from typing import Dict, Any
import numpy as np

from processing.backtest.dong_co_kiem_thu.bo_xu_ly.co_so import BaseEngine

class VietnamEquityEngine(BaseEngine):
    """Engine for the Vietnam cash equity market."""

    def __init__(self, config: dict):
        config = {**config, "leverage": config.get("leverage", 1.0)}  # Cash market: no margin by default
        super().__init__(config)
        self.commission_rate: float = config.get("commission_rate", 0.0015)
        self.tax_rate: float = config.get("tax_rate", 0.001)
        self.slippage_rate: float = config.get("slippage", 0.001)
        self.default_board: str = config.get("default_board", "HOSE")

    def can_execute(self, symbol: str, direction: int, bar: Dict[str, Any]) -> bool:
        """Check whether an order can be executed at the current bar's open price."""
        # 1. Block short selling (VN cash market rule)
        if direction == -1:
            return False

        # 2. T+2.5 rule: shares must settle before they can be sold
        if direction == 0:
            pos = self.positions.get(symbol)
            if pos is not None:
                current_date = str(bar.get("timestamp", ""))[:10]
                entry_date = str(pos.entry_time)[:10]
                
                try:
                    # Đếm ngày làm việc (Bỏ qua T7, CN)
                    days_passed = np.busday_count(entry_date, current_date)
                    if days_passed < 2:  
                        return False
                    elif days_passed == 2:
                        # Nếu đúng ngày T+2, chỉ cho phép bán vào buổi chiều (Sau 13:00)
                        current_time = str(bar.get("timestamp", ""))[11:16]
                        if current_time and current_time < "13:00":
                            return False
                except Exception:
                    # Fallback an toàn nếu lỗi parse ngày
                    bars_held = self._bar_idx - pos.entry_bar_idx
                    if bars_held < 3: # Nến 1D cần 3 cây nến để sang ngày T+3
                        return False

        # 3. Khôi phục: Kiểm tra giá Trần/Sàn (Ceiling/Floor)
        open_price = bar.get("open")
        pre_close = bar.get("pre_close")

        if open_price and pre_close:
            limit = _price_limit(symbol, self.default_board)
            ceiling_price = round(pre_close * (1 + limit), 2)
            floor_price = round(pre_close * (1 - limit), 2)

            # Không thể mua nếu mở cửa đã chạm giá Trần (Không ai bán)
            if direction == 1 and open_price >= ceiling_price - 0.01:
                return False

            # Không thể bán nếu mở cửa đã chạm giá Sàn (Không ai mua)
            if direction == 0 and open_price <= floor_price + 0.01:
                return False

        return True

    def round_size(self, raw_size: float, price: float) -> float:
        """Round lot size to the nearest 100-share board lot."""
        return max(int(raw_size / 100) * 100, 0)

    def calc_commission(self, size: float, price: float, direction: int, is_open: bool) -> float:
        """VN fee structure: brokerage commission (both sides) + tax (sell side only)."""
        notional = size * price
        comm = notional * self.commission_rate
        if not is_open:
            comm += notional * self.tax_rate
        return comm

    def apply_slippage(self, price: float, direction: int) -> float:
        """Apply slippage in the adverse direction."""
        return price * (1 + direction * self.slippage_rate)

# ── Helpers ──

def _calc_pct_change(bar: Dict[str, Any]):
    """Calculate price change percentage from a bar dict."""
    if "pct_chg" in bar:
        val = bar["pct_chg"]
        if val is not None and not (isinstance(val, float) and val != val):
            raw = float(val)
            return raw / 100.0 if abs(raw) > 1.0 else raw

    close = bar.get("close")
    pre_close = bar.get("pre_close")
    if close is not None and pre_close is not None and pre_close > 0:
        return (float(close) - float(pre_close)) / float(pre_close)
    return None

def _price_limit(symbol: str, default_board: str = "HOSE") -> float:
    """Return the price limit (ceiling/floor band) for the given exchange."""
    sym_upper = symbol.upper()
    if sym_upper.endswith(".HN") or sym_upper.endswith(".HNX"):
        return 0.10
    if sym_upper.endswith(".UP") or sym_upper.endswith(".UPCOM"):
        return 0.15
    if sym_upper.endswith(".HM") or sym_upper.endswith(".HSX") or sym_upper.endswith(".VN"):
        return 0.07

    if default_board.upper() == "HNX":
        return 0.10
    if default_board.upper() == "UPCOM":
        return 0.15
    return 0.07