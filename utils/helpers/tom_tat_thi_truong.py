"""Market data summarizer (A09).

Reduces token count when sending OHLCV data to LLMs (DeepSeek, GPT-4).
Converts raw DataFrames into concise text summaries.
"""

import polars as pl
import pandas as pd
from typing import Union, Dict, Any

def summarize_ohlcv(df: Union[pl.DataFrame, pd.DataFrame], symbol: str, limit: int = 20) -> str:
    """Summarize OHLCV data as a concise text string.

    Args:
        df: DataFrame containing OHLCV data.
        symbol: Asset symbol (e.g. BTC-USDT).
        limit: Number of most recent candles to include in detail.

    Returns:
        Text summary string.
    """
    if isinstance(df, pd.DataFrame):
        df_pl = pl.from_pandas(df)
    else:
        df_pl = df

    if df_pl.is_empty():
        return f"No data available for {symbol}."

    last_candle = df_pl.tail(1).to_dicts()[0]
    close_price = last_candle.get("close", 0)

    summary = [f"### Market: {symbol}"]
    summary.append(f"- Current price: {close_price:,.2f}")

    if len(df_pl) > 1:
        prev_close = df_pl.offset(-2).tail(1).to_dicts()[0].get("close", 0)
        change_pct = ((close_price - prev_close) / prev_close) * 100 if prev_close != 0 else 0
        trend = "Up" if change_pct > 0 else "Down" if change_pct < 0 else "Sideways"
        summary.append(f"- Trend (last candle): {trend} ({change_pct:+.2f}%)")

    # Add technical indicators if present (assumed computed by A02)
    cols = df_pl.columns
    indicators = []
    if "rsi" in cols:
        rsi_val = df_pl.tail(1)["rsi"][0]
        indicators.append(f"RSI: {rsi_val:.1f}")
    if "ema_20" in cols and "ema_50" in cols:
        e20 = df_pl.tail(1)["ema_20"][0]
        e50 = df_pl.tail(1)["ema_50"][0]
        pos = "Above" if e20 > e50 else "Below"
        indicators.append(f"EMA 20/50: {e20:,.2f} ({pos} EMA 50)")

    if indicators:
        summary.append(f"- Technical indicators: {', '.join(indicators)}")

    # Summarize last N candles volatility (no full table)
    recent = df_pl.tail(limit)
    high_n = recent["high"].max()
    low_n = recent["low"].min()
    summary.append(f"- Range (last {limit} candles): High {high_n:,.2f}, Low {low_n:,.2f}")

    return "\n".join(summary)


# Backward-compatible alias
tom_tat_ohlcv = summarize_ohlcv
