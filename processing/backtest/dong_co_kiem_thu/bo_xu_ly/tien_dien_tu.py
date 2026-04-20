"""Backtest engine for crypto perpetual futures.

Market rules:
  - 24/7 trading, no directional restrictions.
  - Maker/Taker fee separation.
  - Funding fee settled every 8 hours (00:00/08:00/16:00 UTC).
  - Forced liquidation when maintenance margin ratio <= 100%.
  - Fractional position sizes allowed.
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, Any

from processing.backtest.dong_co_kiem_thu.bo_xu_ly.co_so import BaseEngine


# OKX tiered maintenance margin table (simplified)
# (max_position_value_usd, maintenance_margin_rate)
_TIER_TABLE = [
    (100_000, 0.004),
    (500_000, 0.006),
    (1_000_000, 0.01),
    (5_000_000, 0.02),
    (10_000_000, 0.05),
    (float("inf"), 0.10),
]

# Funding fee settlement hours (UTC)
_FUNDING_HOURS = {0, 8, 16}


class CryptoEngine(BaseEngine):
    """Crypto perpetual futures engine.

    Config keys:
      - leverage: default 1.0
      - maker_rate: default 0.0002 (0.02%)
      - taker_rate: default 0.0005 (0.05%)
      - slippage: default 0.0005 (0.05%)
      - margin_mode: "isolated" (default) or "cross"
      - funding_rate: fixed rate per settlement, default 0.0001 (0.01%)
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.maker_rate: float = config.get("maker_rate", 0.0002)
        self.taker_rate: float = config.get("taker_rate", 0.0005)
        self.slippage_rate: float = config.get("slippage", 0.0005)
        self.funding_rate: float = config.get("funding_rate", 0.0001)
        self._funding_applied: set = set()    # (symbol, date, hour) — dedup per intraday window
        self._funding_daily_done: set = set() # (symbol, date) — dedup per daily candle

    def can_execute(self, symbol: str, direction: int, bar: Dict[str, Any]) -> bool:
        """Crypto: 24/7 trading, all directions permitted."""
        return True

    def round_size(self, raw_size: float, price: float) -> float:
        """Fractional sizes supported; round to 6 decimal places."""
        return round(max(raw_size, 0.0), 6)

    def calc_commission(self, size: float, price: float, direction: int, is_open: bool) -> float:
        """Maker/Taker split: open orders fill as Taker, close orders fill as Maker."""
        rate = self.taker_rate if is_open else self.maker_rate
        return size * price * rate

    def apply_slippage(self, price: float, direction: int) -> float:
        """Apply slippage in the adverse direction."""
        return price * (1 + direction * self.slippage_rate)

    def on_bar(self, symbol: str, bar: Dict[str, Any], timestamp: datetime) -> None:
        """Per-bar hook: charge funding fee and check for liquidation."""
        self._apply_funding_fee(symbol, bar, timestamp)
        self._check_liquidation(symbol, bar, timestamp)

    # ── Funding Fee (charged/paid by exchange every 8 hours) ──

    def _apply_funding_fee(
        self, symbol: str, bar: Dict[str, Any], timestamp: datetime,
    ) -> None:
        """Debit/credit funding fee at settlement hours.

        Positive rate: longs pay shorts. Negative rate: shorts pay longs.

        Intraday candles: applied at each 0/8/16 UTC window.
        Daily candles: applied once per day as an approximation.
        """
        # Support both native datetime and objects with a .date() attribute
        current_date = timestamp.date() if hasattr(timestamp, "date") else timestamp
        hour = timestamp.hour if hasattr(timestamp, "hour") else 0

        if hour in _FUNDING_HOURS:
            key = (symbol, current_date, hour)
            if key in self._funding_applied:
                return
            self._funding_applied.add(key)
        else:
            # Non-settlement hour (e.g. daily candle closing at 12:00 UTC)
            day_key = (symbol, current_date)
            if day_key in self._funding_daily_done:
                return
            self._funding_daily_done.add(day_key)

        pos = self.positions.get(symbol)
        if pos is None:
            return

        mark_price = float(bar.get("close", pos.entry_price))
        notional = pos.size * mark_price
        fee = notional * self.funding_rate * pos.direction
        self.capital -= fee

    # ── Liquidation (forced by exchange) ──

    def _check_liquidation(
        self, symbol: str, bar: Dict[str, Any], timestamp: datetime,
    ) -> None:
        """Force-close position when maintenance margin equity drops to or below required level."""
        pos = self.positions.get(symbol)
        if pos is None or pos.leverage <= 1.0:
            return  # Spot positions are not subject to liquidation

        mark_price = float(bar.get("close", pos.entry_price))
        margin = pos.size * pos.entry_price / pos.leverage
        unrealized = pos.direction * pos.size * (mark_price - pos.entry_price)

        # Tiered maintenance margin
        notional = pos.size * mark_price
        maint_rate = self._maintenance_rate(notional)
        maint_margin = notional * maint_rate

        # Position equity = initial margin + unrealized PnL
        equity_in_pos = margin + unrealized
        if equity_in_pos <= maint_margin:
            # Liquidate at market price with Taker slippage
            liq_price = self.apply_slippage(mark_price, -pos.direction)
            self._close_position(symbol, liq_price, timestamp, "liquidation")

    @staticmethod
    def _maintenance_rate(notional_usd: float) -> float:
        """Look up tiered maintenance margin rate."""
        for tier_max, rate in _TIER_TABLE:
            if notional_usd <= tier_max:
                return rate
        return _TIER_TABLE[-1][1]