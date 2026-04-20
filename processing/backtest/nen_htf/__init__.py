"""a04/nen_htf — HTF Candle Builder.

Export:
    HTFBuilder       — OOP wrapper (new name)
    XayDungNenHTF    — backward-compatible alias
    build_htf_candle — core function
"""

from processing.backtest.nen_htf.xay_dung_nen_htf import (
    HTFBuilder,
    XayDungNenHTF,
    build_htf_candle,
)

__all__ = ["HTFBuilder", "XayDungNenHTF", "build_htf_candle"]
