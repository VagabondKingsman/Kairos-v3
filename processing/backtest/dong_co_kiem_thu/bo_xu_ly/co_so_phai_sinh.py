"""Base class for all futures engines.

Extends BaseEngine with contract-multiplier support.
Only derivatives engines inherit from this class; equities/crypto/forex use BaseEngine directly.

The multiplier affects:
  - PnL: direction * size * multiplier * (exit_price - entry_price)
  - Margin: size * price * multiplier / leverage
  - Position sizing: target_notional / (price * multiplier)
"""

from __future__ import annotations

from abc import abstractmethod

from processing.backtest.dong_co_kiem_thu.bo_xu_ly.co_so import BaseEngine


class FuturesBaseEngine(BaseEngine):
    """BaseEngine with contract-multiplier support.

    Subclasses must implement ``get_contract_multiplier(symbol)``
    in addition to the standard market-rule methods.
    """

    @abstractmethod
    def get_contract_multiplier(self, symbol: str) -> float:
        """Contract multiplier for the given instrument.

        Args:
            symbol: Futures contract code, e.g. 'IF2406.CFFEX', 'ESZ4'.

        Returns:
            Point-to-currency multiplier, e.g. IF=300, ES=50.
        """

    # ── Override PnL / margin / sizing to incorporate the contract multiplier ──

    def _calc_pnl(
        self, symbol: str, direction: int, size: float,
        entry_price: float, exit_price: float,
    ) -> float:
        cm = self.get_contract_multiplier(symbol)
        return direction * size * cm * (exit_price - entry_price)

    def _calc_margin(
        self, symbol: str, size: float, price: float, leverage: float,
    ) -> float:
        cm = self.get_contract_multiplier(symbol)
        return size * price * cm / leverage

    def _calc_raw_size(
        self, symbol: str, target_notional: float, price: float,
    ) -> float:
        cm = self.get_contract_multiplier(symbol)
        return target_notional / (price * cm)