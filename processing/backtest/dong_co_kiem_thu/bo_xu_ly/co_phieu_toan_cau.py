"""Backtest engine for global equities (US / Hong Kong).

Market rules:
  US:
    - T+0, long and short allowed
    - Commission-free (retail environment assumption)
    - Fractional shares supported (round to 0.01)
    - Low slippage (high liquidity)
  Hong Kong (HK):
    - T+0, long and short allowed
    - Stamp duty 0.1% both sides + exchange levies
    - Board-lot rounding (simplified to 100-share lots)
    - Higher slippage than US market
"""

from __future__ import annotations
from typing import Dict, Any

from processing.backtest.dong_co_kiem_thu.bo_xu_ly.co_so import BaseEngine


class GlobalEquityEngine(BaseEngine):
    """US / HK equity engine, selected via the *market* parameter.

    Config keys:
      - slippage_us: default 0.0005
      - slippage_hk: default 0.001
      - hk_stamp_tax: default 0.001 (stamp duty 0.1% both sides)
      - hk_commission: default 0.00015 (broker commission 1.5 bps)
      - hk_levy: default 0.0000565 (SFC + FRC regulatory levies)
      - hk_settlement: default 0.00002 (CCASS settlement fee)
    """

    def __init__(self, config: dict, market: str = "us"):
        config = {**config, "leverage": config.get("leverage", 1.0)}
        super().__init__(config)
        self.market = market

        # US defaults
        self.slippage_us: float = config.get("slippage_us", 0.0005)

        # HK defaults
        self.slippage_hk: float = config.get("slippage_hk", 0.001)
        self.hk_stamp_tax: float = config.get("hk_stamp_tax", 0.001)
        self.hk_commission: float = config.get("hk_commission", 0.00015)
        self.hk_levy: float = config.get("hk_levy", 0.0000565)
        self.hk_settlement: float = config.get("hk_settlement", 0.00002)

    def can_execute(self, symbol: str, direction: int, bar: Dict[str, Any]) -> bool:
        """US/HK: T+0, long and short both permitted."""
        return True

    def round_size(self, raw_size: float, price: float) -> float:
        """US: fractional shares (round to 0.01). HK: 100-share board lots."""
        if self.market == "hk":
            return max(int(raw_size / 100) * 100, 0)
        return round(max(raw_size, 0.0), 2)

    def calc_commission(self, size: float, price: float, direction: int, is_open: bool) -> float:
        """US: zero commission. HK: stamp duty + exchange levies."""
        if self.market == "hk":
            notional = size * price
            comm = notional * self.hk_commission    # broker commission
            comm += notional * self.hk_stamp_tax    # stamp duty (both sides)
            comm += notional * self.hk_levy         # SFC + FRC regulatory fee
            comm += notional * self.hk_settlement   # CCASS settlement fee
            return comm

        # US: effectively zero (SEC fee is negligible)
        return 0.0

    def apply_slippage(self, price: float, direction: int) -> float:
        """US: low slippage. HK: moderate slippage."""
        rate = self.slippage_hk if self.market == "hk" else self.slippage_us
        return price * (1 + direction * rate)