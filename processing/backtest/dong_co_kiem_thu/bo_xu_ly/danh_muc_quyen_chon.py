"""Options portfolio backtest engine (v2) — Polars version.

Supports European and American options via Black-Scholes with an implied
volatility smile approximation. Synthesizes theoretical option prices from
underlying spot prices; supports multi-leg strategies.

Signal interface: OptionsSignalEngine.generate(data_map) → list of trade orders.
Artifacts: equity.csv, metrics.csv, trades.csv, greeks.csv.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import polars as pl
from scipy.stats import norm


# --- Black-Scholes Pricing ---
def bs_price(S: float, K: float, T: float, r: float, sigma: float,
             option_type: str = "call") -> float:
    """Price a European option using Black-Scholes."""
    if T <= 0 or sigma <= 0:
        if option_type == "call":
            return max(S - K, 0.0)
        return max(K - S, 0.0)

    d1 = (np.log(S / K) + (r + sigma ** 2 / 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == "call":
        return float(S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2))
    return float(K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1))


# --- Greeks ---


def bs_greeks(S: float, K: float, T: float, r: float, sigma: float,
              option_type: str = "call") -> Dict[str, float]:
    """Calculate Black-Scholes Greeks."""
    if T <= 0 or sigma <= 0:
        intrinsic_call = 1.0 if S > K else 0.0
        delta = intrinsic_call if option_type == "call" else intrinsic_call - 1.0
        return {"delta": delta, "gamma": 0.0, "theta": 0.0, "vega": 0.0}

    sqrt_T = np.sqrt(T)
    d1 = (np.log(S / K) + (r + sigma ** 2 / 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    nd1_pdf = float(norm.pdf(d1))

    if option_type == "call":
        delta = float(norm.cdf(d1))
    else:
        delta = float(norm.cdf(d1) - 1.0)

    gamma = float(nd1_pdf / (S * sigma * sqrt_T))

    theta_common = -(S * nd1_pdf * sigma) / (2 * sqrt_T)
    if option_type == "call":
        theta = theta_common - r * K * np.exp(-r * T) * norm.cdf(d2)
    else:
        theta = theta_common + r * K * np.exp(-r * T) * norm.cdf(-d2)
    theta = float(theta / 365.0)  

    vega = float(S * nd1_pdf * sqrt_T / 100.0)

    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega}


# --- IV Smile Model (v2) ---


def iv_smile_adjustment(S: float, K: float, base_iv: float,
                        skew: float = -0.15, curvature: float = 0.05) -> float:
    """Adjust IV for moneyness using a quadratic smile model."""
    if S <= 0 or K <= 0:
        return max(base_iv, 0.01)
    log_moneyness = np.log(K / S)
    adj = base_iv + skew * log_moneyness + curvature * log_moneyness ** 2
    return max(adj, 0.01)


# --- American Early Exercise (v2) ---


def american_exercise_value(
    S: float, K: float, T: float, r: float, sigma: float,
    option_type: str = "put",
) -> float:
    """Check whether early exercise is optimal for an American option."""
    intrinsic = max(K - S, 0.0) if option_type == "put" else max(S - K, 0.0)
    continuation = bs_price(S, K, T, r, sigma, option_type)
    return max(intrinsic, continuation)


# --- Option Position ---


class OptionPosition:
    """A single option leg position."""

    def __init__(self, option_type: str, strike: float, expiry: str,
                 qty: int, entry_price: float, entry_date: str,
                 underlying_code: str):
        self.option_type = option_type
        self.strike = strike

        # Pre-process expiry string to native Python datetime
        if "T" in expiry:
            self.expiry = datetime.fromisoformat(expiry)
        else:
            self.expiry = datetime.strptime(expiry[:10], "%Y-%m-%d")
            
        self.qty = qty
        self.entry_price = entry_price
        self.entry_date = entry_date
        self.underlying_code = underlying_code

    def time_to_expiry(self, current_date: datetime) -> float:
        days = (self.expiry - current_date).days
        return max(days / 365.0, 0.0)

    def is_expired(self, current_date: datetime) -> bool:
        return current_date >= self.expiry

    def intrinsic_value(self, spot: float) -> float:
        if self.option_type == "call":
            return max(spot - self.strike, 0.0)
        return max(self.strike - spot, 0.0)


# --- Backtest Runner ---


def run_options_backtest(
    config: Dict[str, Any],
    loader: Any,
    engine: Any,
    run_dir: Path,
    bars_per_year: int = 252,
) -> Dict[str, Any]:
    """Entry point for the options backtest using the Polars engine."""
    codes = config.get("codes", [])
    start_date = config.get("start_date", "")
    end_date = config.get("end_date", "")
    initial_cash = config.get("initial_cash", 1_000_000)
    commission = config.get("commission", 0.001)
    options_cfg = config.get("options_config", {})
    risk_free_rate = options_cfg.get("risk_free_rate", 0.05)
    contract_multiplier = options_cfg.get("contract_multiplier", 1.0)
    exercise_style = options_cfg.get("exercise_style", "european")
    iv_skew = options_cfg.get("iv_skew", 0.0)
    iv_curvature = options_cfg.get("iv_curvature", 0.0)

    # Load underlying data (loader returns Dict[str, pl.DataFrame])
    data_map = loader.fetch(codes, start_date, end_date)
    if not data_map:
        print(json.dumps({"error": "No data fetched"}))
        sys.exit(1)

    # Vectorized IV calculation + compress into O(1) lookup dict
    all_dates = set()
    fast_data: Dict[str, Dict[datetime, Dict[str, float]]] = {}

    for code, df in data_map.items():
        # Normalize timestamp column name
        if "timestamp" not in df.columns and "date" in df.columns:
            df = df.rename({"date": "timestamp"})

        # Compute IV directly via Polars expression
        df = df.with_columns(
            (pl.col("close") / pl.col("close").shift(1)).log()
            .rolling_std(window_size=30)
            .mul(np.sqrt(252))
            .fill_null(strategy="forward")
            .fill_null(0.3)
            .alias("iv")
        )
        data_map[code] = df

        # Build fast-access memory dict
        fast_data[code] = {}
        for row in df.select(["timestamp", "close", "iv"]).to_dicts():
            ts_val = row["timestamp"]
            # Convert to Python datetime if data comes as string/number from various DBs
            if not isinstance(ts_val, datetime):
                if isinstance(ts_val, str):
                    ts_val = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))[:10]
                else:
                    ts_val = ts_val  # Assume already datetime-compatible

            all_dates.add(ts_val)
            fast_data[code][ts_val] = {"close": row["close"], "iv": row["iv"]}

    dates = sorted(list(all_dates))

    # Generate trading signals
    signals = engine.generate(data_map)

    # Index signals by date string
    signal_by_date: Dict[str, List[Dict[str, Any]]] = {}
    for sig in signals:
        d = sig.get("date", "")
        if isinstance(d, datetime):
            d_str = d.strftime("%Y-%m-%d")
        else:
            d_str = str(d)[:10]
        signal_by_date.setdefault(d_str, []).append(sig)

    # Simulation state
    cash = float(initial_cash)
    positions: List[OptionPosition] = []
    trade_records: List[Dict[str, Any]] = []
    greeks_records: List[Dict[str, Any]] = []
    equity_records: List[Dict[str, Any]] = []

    last_seen_spot = {}
    last_seen_iv = {}

    for ts in dates:
        date_str = ts.strftime("%Y-%m-%d")

        # 1. Update underlying spot prices — O(1) access
        for code in codes:
            d_dict = fast_data.get(code, {})
            if ts in d_dict:
                last_seen_spot[code] = d_dict[ts]["close"]
                last_seen_iv[code] = d_dict[ts]["iv"]
                
        spot_prices = {c: last_seen_spot.get(c, 0.0) for c in codes}
        ivs = {c: last_seen_iv.get(c, 0.3) for c in codes}

        # 2a. American early exercise (v2)
        if exercise_style == "american":
            for pos in list(positions):
                if pos.is_expired(ts):
                    continue  
                spot = spot_prices.get(pos.underlying_code, 0.0)
                iv_val_ex = ivs.get(pos.underlying_code, 0.3)
                T_ex = pos.time_to_expiry(ts)
                if T_ex <= 0:
                    continue
                
                intrinsic = pos.intrinsic_value(spot)
                continuation = bs_price(spot, pos.strike, T_ex, risk_free_rate, iv_val_ex, pos.option_type)
                
                if intrinsic > 0 and intrinsic > continuation * 1.02:
                    settlement = intrinsic * pos.qty * contract_multiplier
                    cash += settlement
                    pnl = (intrinsic - pos.entry_price) * pos.qty * contract_multiplier
                    trade_records.append({
                        "timestamp": date_str,
                        "code": pos.underlying_code,
                        "option_type": pos.option_type,
                        "strike": pos.strike,
                        "expiry": pos.expiry.strftime("%Y-%m-%d"),
                        "side": "early_exercise",
                        "price": round(intrinsic, 4),
                        "qty": pos.qty,
                        "pnl": round(pnl, 4),
                        "entry_date": pos.entry_date,
                    })
                    positions.remove(pos)

        # 2b. Process expirations
        expired = [p for p in positions if p.is_expired(ts)]
        for pos in expired:
            spot = spot_prices.get(pos.underlying_code, 0.0)
            intrinsic = pos.intrinsic_value(spot)

            settlement = intrinsic * pos.qty * contract_multiplier
            cash += settlement
            pnl = (intrinsic - pos.entry_price) * pos.qty * contract_multiplier

            side = "exercise" if intrinsic > 0 else "expire"
            trade_records.append({
                "timestamp": date_str,
                "code": pos.underlying_code,
                "option_type": pos.option_type,
                "strike": pos.strike,
                "expiry": pos.expiry.strftime("%Y-%m-%d"),
                "side": side,
                "price": round(intrinsic, 4),
                "qty": pos.qty,
                "pnl": round(pnl, 4),
                "entry_date": pos.entry_date,
            })
            positions.remove(pos)

        # 3. Execute today's signals
        day_signals = signal_by_date.get(date_str, [])
        for sig in day_signals:
            action = sig.get("action", "")
            legs = sig.get("legs", [])
            underlying = sig.get("underlying", codes[0] if codes else "")

            spot = spot_prices.get(underlying, 0.0)
            iv_val = ivs.get(underlying, 0.3)

            for leg in legs:
                leg_type = leg.get("type", "call")
                strike = leg.get("strike", spot)
                expiry = leg.get("expiry", "")
                qty = leg.get("qty", 1)

                if "T" in expiry:
                    expiry_ts = datetime.fromisoformat(expiry)
                else:
                    expiry_ts = datetime.strptime(expiry[:10], "%Y-%m-%d")
                    
                T = max((expiry_ts - ts).days / 365.0, 0.001)

                adj_iv = iv_val
                if iv_skew != 0 or iv_curvature != 0:
                    adj_iv = iv_smile_adjustment(spot, strike, iv_val, iv_skew, iv_curvature)

                opt_price = bs_price(spot, strike, T, risk_free_rate, adj_iv, leg_type)

                if action == "open":
                    abs_cost = opt_price * abs(qty) * contract_multiplier
                    if qty > 0:
                        cash -= abs_cost * (1 + commission)
                    else:
                        cash += abs_cost * (1 - commission)

                    positions.append(OptionPosition(
                        option_type=leg_type,
                        strike=strike,
                        expiry=expiry,
                        qty=qty,
                        entry_price=opt_price,
                        entry_date=date_str,
                        underlying_code=underlying,
                    ))

                    trade_records.append({
                        "timestamp": date_str,
                        "code": underlying,
                        "option_type": leg_type,
                        "strike": strike,
                        "expiry": expiry,
                        "side": "buy" if qty > 0 else "sell",
                        "price": round(opt_price, 4),
                        "qty": qty,
                        "pnl": 0.0,
                        "entry_date": date_str,
                    })

                elif action == "close":
                    matched = _find_matching_position(positions, underlying, leg_type, strike, expiry)
                    if matched:
                        pnl = (opt_price - matched.entry_price) * matched.qty * contract_multiplier
                        abs_close = opt_price * abs(matched.qty) * contract_multiplier
                        if matched.qty > 0:
                            cash += abs_close * (1 - commission)
                        else:
                            cash -= abs_close * (1 + commission)

                        trade_records.append({
                            "timestamp": date_str,
                            "code": underlying,
                            "option_type": leg_type,
                            "strike": strike,
                            "expiry": expiry,
                            "side": "close",
                            "price": round(opt_price, 4),
                            "qty": matched.qty,
                            "pnl": round(pnl, 4),
                            "entry_date": matched.entry_date,
                        })
                        positions.remove(matched)

        # 4. Mark-to-market portfolio valuation
        portfolio_value = cash
        total_delta = 0.0
        total_gamma = 0.0
        total_theta = 0.0
        total_vega = 0.0

        for pos in positions:
            spot = spot_prices.get(pos.underlying_code, 0.0)
            iv_val = ivs.get(pos.underlying_code, 0.3)
            T = pos.time_to_expiry(ts)

            mark_price = bs_price(spot, pos.strike, T, risk_free_rate, iv_val, pos.option_type)
            portfolio_value += mark_price * pos.qty * contract_multiplier

            greeks = bs_greeks(spot, pos.strike, T, risk_free_rate, iv_val, pos.option_type)
            total_delta += greeks["delta"] * pos.qty * contract_multiplier
            total_gamma += greeks["gamma"] * pos.qty * contract_multiplier
            total_theta += greeks["theta"] * pos.qty * contract_multiplier
            total_vega += greeks["vega"] * pos.qty * contract_multiplier

        equity_records.append({
            "timestamp": date_str,
            "equity": round(portfolio_value, 4),
            "cash": round(cash, 4),
            "positions_value": round(portfolio_value - cash, 4),
        })

        greeks_records.append({
            "timestamp": date_str,
            "delta": round(total_delta, 6),
            "gamma": round(total_gamma, 6),
            "theta": round(total_theta, 6),
            "vega": round(total_vega, 6),
            "num_positions": len(positions),
        })

    # Compute performance metrics using Polars expressions
    if not equity_records:
        print(json.dumps({"error": "No equity data generated"}))
        sys.exit(1)

    equity_df = pl.DataFrame(equity_records)
    equity_series = equity_df["equity"]

    metrics = _calc_options_metrics(equity_series, initial_cash, trade_records, bars_per_year)

    # Write artifacts
    out = run_dir / "artifacts"
    out.mkdir(parents=True, exist_ok=True)

    for code, df in data_map.items():
        df.write_csv(out / f"ohlcv_{code}.csv")

    equity_df.write_csv(out / "equity.csv")

    trade_cols = ["timestamp", "code", "option_type", "strike", "expiry",
                  "side", "price", "qty", "pnl", "entry_date"]
                  
    if trade_records:
        pl.DataFrame(trade_records, schema=trade_cols, strict=False).write_csv(out / "trades.csv")
    else:
        pl.DataFrame(schema=trade_cols).write_csv(out / "trades.csv")

    pl.DataFrame(greeks_records).write_csv(out / "greeks.csv")
    pl.DataFrame([metrics]).write_csv(out / "metrics.csv")

    print(json.dumps(metrics, indent=2))
    return metrics


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _find_matching_position(
    positions: List[OptionPosition],
    underlying: str,
    option_type: str,
    strike: float,
    expiry: str,
) -> Optional[OptionPosition]:
    """Find an open position matching the given criteria."""
    if "T" in expiry:
        expiry_ts = datetime.fromisoformat(expiry)
    else:
        expiry_ts = datetime.strptime(expiry[:10], "%Y-%m-%d")
        
    for pos in positions:
        if (pos.underlying_code == underlying
                and pos.option_type == option_type
                and abs(pos.strike - strike) < 1e-6
                and pos.expiry == expiry_ts):
            return pos
    return None


def _calc_options_metrics(
    equity: pl.Series,
    initial_cash: float,
    trades: List[Dict[str, Any]],
    bars_per_year: int = 252,
) -> Dict[str, Any]:
    """Compute options backtest performance metrics (native Polars)."""
    n = len(equity)
    if n < 2:
        return {
            "final_value": initial_cash, "total_return": 0, "annual_return": 0,
            "max_drawdown": 0, "sharpe": 0, "calmar": 0, "sortino": 0,
            "trade_count": len(trades), "win_rate": 0, "profit_loss_ratio": 0,
        }

    returns = (equity / equity.shift(1) - 1).fill_null(0.0)

    total_ret = float(equity[-1] / initial_cash - 1)
    ann_ret = float((1 + total_ret) ** (bars_per_year / max(n, 1)) - 1)

    vol = float(returns.std())
    sharpe = float(returns.mean() / (vol + 1e-10) * np.sqrt(bars_per_year))

    peak = equity.cum_max()
    dd = (equity - peak) / peak.map_elements(lambda x: 1.0 if x == 0 else x, return_dtype=pl.Float64)
    max_dd = float(dd.min())
    calmar = ann_ret / abs(max_dd) if abs(max_dd) > 1e-10 else 0.0

    downside = returns.filter(returns < 0)
    downside_std = float(downside.std()) if len(downside) > 1 else 1e-10
    sortino = float(returns.mean() / (downside_std + 1e-10) * np.sqrt(bars_per_year))

    # Trade statistics
    closed_pnl = [t["pnl"] for t in trades if t.get("pnl", 0) != 0]
    wins = [p for p in closed_pnl if p > 0]
    losses = [p for p in closed_pnl if p < 0]
    win_rate = len(wins) / len(closed_pnl) if closed_pnl else 0.0
    avg_win = np.mean(wins) if wins else 0.0
    avg_loss = abs(np.mean(losses)) if losses else 1e-10
    pl_ratio = avg_win / avg_loss if avg_loss > 1e-10 else 0.0

    return {
        "final_value": round(float(equity[-1]), 2),
        "total_return": round(total_ret, 6),
        "annual_return": round(ann_ret, 6),
        "max_drawdown": round(max_dd, 6),
        "sharpe": round(sharpe, 4),
        "calmar": round(calmar, 4),
        "sortino": round(sortino, 4),
        "trade_count": len(trades),
        "win_rate": round(win_rate, 4),
        "profit_loss_ratio": round(pl_ratio, 4),
    }