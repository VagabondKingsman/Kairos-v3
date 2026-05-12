# KAIROS v3 — Alpha Research Platform
## Implementation Plan (v6)

---

## Triết lý

```
Hypothesis → Data (PiT) → Features → Labels → Validation (purged CV)
  → Backtest → Alpha decay → Capacity → Paper → Shadow → Deploy
```

```
1. Framework = hygiene. Edge = signal quality + hypothesis quality + iteration speed.
2. 1000 ý tưởng → 100 sanity → 20 CV → 5 cost → 2 live → 1 scale.
3. IC realistic (crypto 2026): tốt 0.015-0.025, xuất sắc 0.025-0.040.
   Directional momentum: cost-adjusted IC thường thấp hơn. Nhìn net IR, không nhìn IC gross.
4. Python/ZMQ stack → hourly/daily signals (halflife ≥ 20 bars). Không đánh microstructure.
5. ML priority: Linear/Ridge/Lasso → vắt kiệt trước. LightGBM chỉ khi OOS gain > 15%.
   Crypto SNR cực thấp → non-linear models overfit thảm hại.
6. Research velocity là KPI số 1: 20-50 hypotheses/week, kill trong vài giờ.
7. Focus 1 alpha family trước. Dominate 1 niche trước khi mở rộng.
8. Timeline: 3 tháng framework, 6 tháng vài weak alpha, 12 tháng 1-2 signal usable.
```

---

## Bức tranh hệ thống

```
ĐÃ CÓ:
  dong_co_du_lieu/thu_thap/          ✅ REST + WS: Binance, Bybit, OKX
  dong_co_du_lieu/ong_dan_dac_trung/ ✅ Online feature engine (feature_registry)
  dong_co_du_lieu/xu_ly_dong/        ✅ OHLC + orderbook stream processor
  ho_du_lieu/tho/                    ✅ Raw tick / L2 / funding
  ha_tang/                           ✅ ZMQ bus + schemas + clock
  thuc_thi_lenh/                     ✅ Full execution engine (OMS, portfolio, WAL)
  quan_tri_rui_ro/                   ✅ Pre-trade risk gate
  moi_truong_chay/                   ✅ backtest / paper / live environments

CẦN XÂY:
  dong_co_du_lieu/xu_ly_lo/          ❌ Batch pipeline
  nghien_cuu/nha_may_alpha/          ❌ Alpha factory + registry + cemetery
  nghien_cuu/khung_alpha/            ❌ Taxonomy + meta-research
  nghien_cuu/kiem_thu_qua_khu/       ❌ Vectorized backtest (Phase 1-3)
  nghien_cuu/dong_co_phat_lai/       ❌ Replay engine (Phase 4)
  nghien_cuu/danh_gia/               ❌ Evaluation + diagnostics
  nghien_cuu/so_tay_jupyter/         ❌ Research notebooks
  hoc_may/huan_luyen/                ❌ Labels + Purged CV + Trainer
  hoc_may/mo_hinh/                   ❌ AlphaModel ABC
  hoc_may/to_hop_alpha/              ❌ Alpha combiner + risk model
```

---

## PHASE 0 — Alpha Taxonomy (Tuần 0, không code)

### `nghien_cuu/khung_alpha/alpha_taxonomy.md`

| Priority | Family | Hypothesis | Halflife | IC | Capacity | Data |
|:--------:|--------|-----------|:--------:|:--:|:--------:|:----:|
| P1 | Funding/Carry | Extreme funding → forced unwind; basis → carry | 20-100 bars | 0.015-0.030 | Cao | ✅ |
| P1 | Cross-sectional Momentum | Relative strength persistence | 5-20 bars | 0.012-0.025 | Cao | ✅ |
| P1 | Volatility Regime | Vol expansion/compression → directional bias | 10-30 bars | 0.012-0.022 | Trung bình | ✅ |
| P2 | Liquidation Cascade | OI buildup + extreme funding → cascade | 3-10 bars | 0.015-0.030 | Trung bình | ✅ |
| P2 | Cross-venue Flow | Binance vs Bybit price discovery lag | 5-20 bars | 0.015-0.035 | Thấp | ✅ |
| P3 | Behavioral/Reversal | Panic sell → mean reversion | 1-5 bars | 0.012-0.025 | Thấp | ✅ |
| P3 | On-chain | Exchange inflows/outflows → supply pressure | 50-200 bars | 0.010-0.020 | Cao | ❌ |
| SKIP | ~~Microstructure~~ | ~~OFI, queue imbalance~~ | ~~<5 bars~~ | — | — | Cần colo |

**Output:** Chọn 2 family P1, viết hypothesis 1 câu/signal.

---

## PHASE 0.25 — Data Pipeline Reliability (Prerequisite)

```
□ REST reconciliation chạy 00:30 UTC mỗi đêm (reconcile_gaps.py)
□ Gap report hàng ngày — alert nếu symbol mất > max_gap_bars
□ Universe PiT database sẵn sàng (get_active_universe hoạt động)
□ Coverage ≥ 95%/ngày, ≥ 1000 bars continuous/symbol
```

**`dong_co_du_lieu/xu_ly_lo/reconcile_gaps.py`:**
```python
def reconcile_gaps(exchange, symbols, lookback_days=2):
    # 1. Scan parquet → tìm gaps > 1 bar
    # 2. Fetch missing bars qua REST API
    # 3. Validate bar count
    # 4. Log: gap_count, gap_duration, symbols_affected
    # Nếu REST không có data → NaN, không fake data.
```

---

## PHASE 0.5 — Plumbing Test (Tuần 0)

Dùng `alpha_001_ema_cross` để verify pipeline trước khi research thật.

```
Mục tiêu: Input klines → AlphaReport (PBO + DSR + IR + IC decay) trong < 5 phút.

□ Data load không bị leak (pit_audit pass)
□ Feature tính từ feature_registry
□ Purged CV không bị index shuffle
□ Cost model áp dụng đúng
□ AlphaReport format đúng
□ Experiment tracker lưu được
□ Alpha bị KILL (IC < 0.01) → lifecycle = KILLED
```

---

## PHASE 1 — Research Harness (Tuần 1-4)

### Holdout Policy

```yaml
# cau_hinh/research.yaml
holdout_start: "2024-09-01"
embargo_start: "2024-06-01"
embargo_end:   "2024-09-01"
research_end:  "2024-05-31"
# holdout chỉ được chạm 1 lần — khi alpha vào paper trade

# Multi-layer validation (ngoài temporal holdout):
cross_exchange_validation:
  train: "binance"
  validate: "bybit"          # alpha thật không phụ thuộc sàn cụ thể
regime_separated_validation:
  # pre_etf_approval "2024-01-10" là hindsight segmentation — biết trước vì nhìn chart
  # Không dùng làm regime split trong training. Chỉ dùng cho post-hoc analysis.
  # Regime detection cho training PHẢI online-only (detect từ data có sẵn tại T, không nhìn T+1)
  # Offline regime label (dùng toàn bộ data) chỉ dùng cho: explain failure, không phải train
  post_hoc_analysis_breakpoints:
    - "2024-01-10"   # BTC ETF approval
    - "2022-05-09"   # LUNA collapse
    - "2022-11-08"   # FTX collapse
# Lý do: 2024 bull regime rất khác 2022-2023 → single temporal holdout chưa đủ

# Parameter freeze rule:
parameter_freeze:
  after_validation: true           # sau khi alpha vào VALIDATION → không tweak thêm
  allowed_changes: []              # chỉ được đổi khi paper trade fail + full re-research
  rationale: "one more tweak = holdout contamination dần dần"
```

---

### 1.1 `dong_co_du_lieu/xu_ly_lo/`

| # | File | Mô tả | Tái dùng |
|:-:|------|--------|----------|
| 1 | `__init__.py` | Package | — |
| 2 | `downloader.py` | REST → parquet (klines + aggTrades + L2 + funding) | `binance_rest.py`, `bybit_rest.py` |
| 3 | `cleaner.py` | Dedup, gap fill, outlier, PiT audit | — |
| 4 | `feature_builder.py` | Batch features + funding alignment | `feature_registry.py` |
| 5 | `dataset_registry.py` | Hash chain + lineage + PiT universe + events | — |
| 6 | `reconcile_gaps.py` | Nightly REST gap backfill | REST API |
| 7 | `liquidity_filter.py` | Universe filter dựa trên L2 depth thực tế | — |

**`cleaner.py`:**
```python
def fill_gaps(df, max_gap_bars=5):
    # gap ≤ max_gap_bars: ffill CHỈ cho features/indicators (price state proxy)
    # KHÔNG bao giờ ffill raw returns hay OHLC prices — bars missing = returns missing
    # Tất cả gap-filled bars được đánh flag `is_gap_filled=True`
    # Signal computation: exclude bars với is_gap_filled=True (không tính IC trên gap bars)
    # Lý do: ffill price trong crypto suppress realized volatility, distort momentum signal,
    #        compress drawdown — backtest Sharpe inflated, live Sharpe thấp hơn nhiều
    # gap > max_gap_bars: mark symbol as inactive cho khoảng đó → loại khỏi universe

def remove_outliers(df, feature_cols, max_return_pct=30.0):
    # KHÔNG xử lý raw returns — tail events là nơi alpha/risk thực sự tồn tại
    # LUNA, FTX, USDC depeg là data thật, không phải noise cần clean
    # Chỉ winsorize features (không returns): expanding window z-score, clip tại ±5σ
    # Nếu return ngoài max_return_pct → flag `is_anomaly=True` để researcher review,
    #   không tự động xóa. Researcher quyết định exclude hay giữ có documented reasoning.

def pit_audit(df, feature_cols):
    # Test 1 — EMBARGO: IC[embargo=0] vs IC[embargo=5], nếu drop > 50% → leak
    # Test 2 — FUTURE PROBE: thêm return[t+1] → model không được chọn
    # Test 3 — CHRONOLOGICAL: df.index.is_monotonic_increasing

def validate_universe_coverage(df, min_bars_per_symbol=1000): ...
```

**`feature_builder.py`:**
```python
def build_batch_features(df, feature_list):
    # Gọi CÙNG feature_registry với live pipeline → zero drift
    registry = FeatureRegistry()
    return registry.compute_batch(df, feature_list)

def align_funding_to_bars(df_klines, df_funding):
    # Funding tại 08:00 UTC → chỉ visible cho bars BẮT ĐẦU TỪ 08:00
    # merge on="open_time", how="left", rồi ffill (không bfill)

def validate_funding_alignment(df, funding_col="funding_rate"):
    # Assert: corr(funding[t], return[t-1]) > corr(funding[t], return[t+1])
    # Nếu ngược lại → alignment sai → front-running funding

def classify_funding_signal_type(signal_logic: str) -> str:
    # Funding signal có 2 loại, khác nhau về leakage risk:
    #   REALIZED: dùng funding đã thực hiện (08:00 UTC) → safe nếu align đúng
    #   PREDICTIVE: dùng premium index / basis để predict funding sắp tới → rủi ro cao
    # Market pricing funding continuously TRƯỚC timestamp 30-60 phút
    # Nếu signal dùng premium index trước announcement → alpha là post-announcement leak
    # Rule: mọi funding signal phải document rõ REALIZED hay PREDICTIVE
    #        PREDICTIVE chỉ valid nếu signal = basis, không phải realized funding rate
    # Classify: "realized_funding" | "predictive_basis" | "funding_expectation"
    # Nếu unclear → default = REALIZED, test thêm corr(signal, next_period_funding) < 0.80
```

**`dataset_registry.py`:**
```python
class DatasetRegistry:
    def register(self, df, metadata) -> str:
        # Hash chain: sha256(raw_hash + cleaning_ver + features + git_commit)

    def get_lineage(self, dataset_id) -> dict:
        # raw_source, cleaning_version, features, feature_registry_commit, label, created_at

    def register_universe(self, date, exchange, active_symbols,
                          delisted_symbols=None, renamed_map: dict = None):
        # renamed_map: {"LUNA": "LUNC", "BTT": "BTTC", "BTTOLD": None}
        # Các trường hợp thực tế: 1000PEPE vs PEPE, reverse split, redenomination,
        # perp migration, contract multiplier change
        # Backtest 2022 dùng LUNA không phải LUNC

    def get_active_universe(self, date: str, exchange: str) -> list[str]:
        # PiT lookup: symbols active tại ngày T trên exchange đó
        # Bao gồm coin delist sau T, không bao gồm coin list sau T

    def register_market_structure_event(self, date, exchange, event_type, detail):
        # event_type: "funding_formula_change" | "tick_size_change" |
        #             "engine_upgrade" | "index_constituent_change" |
        #             "stablecoin_depeg" | "liquidation_engine_change" |
        #             "adl_event" | "timestamp_drift" | "mark_price_anomaly"
        # Stablecoin events quan trọng: USDT stress 2022, USDC depeg 2023, BUSD collapse
        # → Backtest 2022-2023 phải exclude/flag các khoảng này
        # → Alpha chết vì market structure đổi, không phải vì signal tệ

    def get_market_structure_events(self, start, end, exchange) -> list: ...

    def get_research_split(self) -> dict: ...
```

**`liquidity_filter.py` — Universe filter (tách riêng khỏi cost model):**
```python
def compute_true_liquidity(l2_snapshots_df, depth_bps=20,
                           fill_rate_discount=True) -> pl.DataFrame:
    # Raw L2 depth bị spoof nặng: 70-80% orders sẽ cancel ngay khi price chạy đến
    # Không dùng raw L2 sum → underestimate impact 2-3x → backtest Sharpe 2.0 → live -0.3
    # Spoofing discount: nhân L2 depth với historical fill_rate per level
    #   fill_rate[level] = P(order executed | price reaches level) ước từ trade data
    #   Nếu chưa có fill rate data → conservative discount: chỉ tính 20-30% L2 depth
    # Output: symbol → avg_executable_liquidity_usdt per bar (post-discount)

def apply_liquidity_filter(universe, liquidity_df, min_depth_usdt=50_000) -> list:
    # Loại symbols không đủ thanh khoản TRƯỚC KHI đưa vào backtest
    # Cost model chỉ phạt những gì qua filter này
    # Rule: filter universe weekly (liquidity thay đổi theo regime)
```

> **Data sourcing:** Không tự cào toàn bộ historical data qua REST API.
> Mua từ **Tardis.dev** hoặc **Databento** cho historical tick/klines chuẩn.
> REST reconciliation chỉ dùng cho daily incremental update (< 2 ngày lookback).
> API sàn đôi khi sửa data hồi tố — vendor data có audit trail.
>
> **Data seam risk:** Nối vendor data (historical) với REST/WS data (recent) tạo ra seam
> ngay tại vị trí OOS quan trọng nhất. Binance/Bybit âm thầm retroactive-adjust klines.
> Fix: dùng internal WS stream (đã có trong `dong_co_du_lieu/thu_thap/`) để capture raw data
> từ ngày N-30 trở đi → dùng WS data cho reconcile, không dùng REST klines.
> REST klines chỉ dùng làm fallback nếu WS stream bị gap, với flag `data_source=REST_fallback`.

---

### 1.2 `hoc_may/huan_luyen/`

| # | File | Mô tả |
|:-:|------|--------|
| 1 | `__init__.py` | Package |
| 2 | `labeler.py` | forward_return, triple_barrier, meta_label, volatility_adjusted_horizon |
| 3 | `purged_cv.py` | PurgedKFold (research) + AnchoredWFO (production) |
| 4 | `trainer.py` | prepare_matrices, walk_forward_retrain |

**`purged_cv.py`:**
```python
class PurgedKFold:
    # RESEARCH: evaluate alpha skill → "alpha có thật không?"
    def __init__(self, n_splits=5, embargo_bars=10): ...

class AnchoredWFO:
    # PRODUCTION: train model để deploy → anchor = "2020-01-01", không roll
    def __init__(self, anchor_date="2020-01-01", retrain_freq="monthly"): ...
```

---

### 1.3 `nghien_cuu/kiem_thu_qua_khu/ma_tran_sie_toc/`

| # | File | Mô tả |
|:-:|------|--------|
| 1 | `__init__.py` | Package |
| 2 | `backtest_engine.py` | Vectorized backtester (Polars) |
| 3 | `cost_model.py` | 2-tier cost (Phase 1: bid-ask; Phase 4: book depletion) |

**`cost_model.py`:**
```python
def phase1_cost(order_size, bar_spread_bps, avg_volume, realized_vol,
                fee_bps=4, buffer=1.5, signal_family=None):
    """
    Cost = (spread/2 + market_impact + fee) × buffer × vol_penalty

    market_impact = c × σ × √(order_size / avg_volume)
      c ≈ 0.1 (calibrate từ execution data sau)
      avg_volume: KHÔNG dùng raw ADV — bị wash trading làm phình 5-50× ở altcoin
      Dùng true_liquidity từ liquidity_filter.py (L2 depth ±20bps) làm proxy volume
      Lý do: √(Q/V) với V fake → underestimate impact → backtest Sharpe 2.0 → live -0.3

    vol_penalty (momentum signal = toxic flow):
      vol_low → 1.0, vol_mid → 1.3, vol_high → 1.8
      carry/mean_reversion → 1.0–1.2

    c không phải hằng số — asymmetric theo regime:
      momentum chasing (đuổi theo crowd): c ≈ 0.15-0.30
      liquidation cascade (ngược chiều panic): c ≈ 0.05-0.08 (thanh khoản bơm vào)
      default conservative: c = 0.15 cho đến khi có live execution data để calibrate
    """
    spread_cost = bar_spread_bps / 2
    impact = 0.15 * realized_vol * (order_size / avg_volume) ** 0.5  # bps, c=0.15 conservative
    vol_q = realized_vol.rank(pct=True)
    vol_penalty = 1.8 if (vol_q > 0.75 and signal_family == "momentum") else \
                  1.3 if vol_q > 0.50 else 1.0
    return (spread_cost + impact + fee_bps) * buffer * vol_penalty

def transient_impact_cost(order_size, l2_snapshot, decay_halflife_bars=5):
    # Permanent impact = c × σ × √(Q/V) — giữ mãi trong price
    # Transient impact = phần hồi phục theo thời gian (decay theo exp)
    # Với holding period T: effective_cost = permanent + transient × (1 - exp(-T/τ))
    # Nếu bỏ qua transient → overestimate cost khi hold dài, underestimate khi hold ngắn
    # Crypto crypto: τ ≈ 2-10 bars (khác equity)

def phase4_book_depletion_cost(order_size, l2_snapshot):
    # Chỉ implement ở Phase 4
    # Stack qua bid/ask levels → average fill price → cost in bps

def funding_pnl(position_df, funding_df):
    # Bắt buộc trong P&L — mọi perp position phải tính funding

def borrowing_cost(position_df, borrow_rate_df):
    # Bắt buộc cho carry/basis alpha — bỏ sót = overstated net carry
    # Short spot (để hedge perp long) yêu cầu borrow spot token
    # Altcoin borrow rate trên Binance/Bybit đôi khi 50-100% APY
    # Basis alpha: net_carry = funding_rate - borrow_rate (có thể âm)
    # Nếu không có borrow rate data → conservative: assume borrow = 20% APY cho altcoin
```

---

### 1.4 `nghien_cuu/danh_gia/`

| # | File | Mô tả |
|:-:|------|--------|
| 1 | `__init__.py` | Package |
| 2 | `evaluator.py` | Sharpe, IR, MaxDD, Calmar, IC, equity curve |
| 3 | `experiment_tracker.py` | Log config/metrics/models, research velocity report |
| 4 | `overfit_tests.py` | Deflated Sharpe, PBO, White's Reality Check, BH correction |
| 5 | `feature_diagnostics.py` | IC, IC decay, stability, orthogonality, factor exposure |
| 6 | `alpha_diagnostics.py` | Fundamental Law, decay curve, capacity |
| 7 | `regime_analyzer.py` | 3-dimension regime |

**`experiment_tracker.py`:**
```python
class ExperimentTracker:
    def log_run(self, alpha_id, config, metrics): ...
    def research_velocity_report(self):
        # ideas_per_week, median_time_to_kill, kill_rate (target ≥ 95%),
        # pass_rate_by_stage, time_to_validation
    def compare(self, alpha_ids: list) -> pl.DataFrame: ...
    def best(self, metric="ir_estimate", top_n=10) -> list: ...
```

**`alpha_diagnostics.py`:**
```python
def fundamental_law_report(signals_df, returns_df, n_assets, periods_per_year):
    # IC = mean(rank_corr(signal_t, return_t+h))
    # BR_naive = n_assets × periods_per_year × (1 - signal_autocorr)
    # IR_estimate = IC × √BR_effective  ← dùng BR_effective, không phải BR_naive
    # Kill if IR_estimate < 0.30; proceed if > 0.50

def effective_breadth(signal_returns_matrix) -> float:
    # BR_naive inflated vì signals correlated (same regime, same beta, same liquidity)
    # Effective breadth = (sum eigenvalues)² / sum(eigenvalues²)
    #   = eigenvalue participation ratio của signal correlation matrix
    # Nếu 20 signals nhưng corr cao → effective breadth có thể chỉ là 5-8
    # IR thực tế = IC × √BR_effective << IC × √BR_naive
    eigenvalues = np.linalg.eigvalsh(np.corrcoef(signal_returns_matrix))
    return (eigenvalues.sum() ** 2) / (eigenvalues ** 2).sum()

def alpha_decay_curve(signals, returns, horizons=[1, 5, 10, 20, 40, 80]):
    # IC per horizon. Decay halflife = horizon tại IC = 50% ban đầu.

def optimal_holding_period(decay_halflife_bars):
    # optimal hold ≈ 0.5 × decay_halflife_bars

def capacity_estimate(signals, returns, volumes, fee_bps=4): ...

def simplicity_score(alpha_spec: AlphaSpec, model) -> float:
    # Penalty cho complexity → phức tạp thì decay nhanh hơn, khó monitor hơn
    # score = 1 / (param_count × feature_count × nonlinearity_flag × regime_conditions)
    # Linear + 1 feature + 0 regime branches → score ~1.0
    # LightGBM + 20 features + 3 regime conditions → score ~0.05
    # Không kill dựa trên score, nhưng: tie-break bằng simplicity

def live_alpha_halflife(alpha_id, experiment_tracker) -> float:
    # Không chỉ đo backtest decay halflife
    # Đo: sau khi alpha đi vào live, decay speed thực tế là bao nhiêu bars?
    # Nếu live_halflife << backtest_halflife → crowding hoặc regime shift
    # Feed vào MetaResearchEngine để rút học về alpha family nào decay nhanh
```

**`regime_analyzer.py`:**
```python
REGIME_DIMENSIONS = {
    "volatility": ["low", "medium", "high"],      # realized vol 20-bar percentile
    "trend":      ["trending", "mean_reverting"], # hurst / ADX
    "liquidity":  ["liquid", "illiquid"],         # bid-ask spread percentile
}

def detect_regime(df) -> pl.DataFrame: ...  # 3 columns

def regime_conditional_ic(signals, returns, regime_df):
    # IC per regime. Alpha tốt: IC > 0 trong ≥ 2/3 mỗi dimension.

def regime_transition_matrix(regime_series) -> np.ndarray:
    # State transition matrix P[i,j] = P(regime_j | regime_i)
    # Alpha decay xảy ra tại TRANSITION, không phải tại STATE
    # IC giảm mạnh ở 5-10 bars đầu sau transition → cần position taper
    # Input: regime_series (categorical, e.g. "low_vol_trending")

def transition_hazard(regime_series, horizon_bars=20) -> pl.DataFrame:
    # P(transition trong T bars | hiện tại ở regime X)
    # Nếu hazard > 30% → scale down position size trước
    # Output: current_regime → hazard_rate, expected_duration_bars

def regime_persistence_probability(regime_series, t_bars=10) -> dict:
    # P(regime vẫn giữ sau t_bars)
    # Dùng để weight IC: stable regime → full weight; unstable → 50% weight
```

**`feature_diagnostics.py` — feature_exposure:**
```python
def feature_exposure(signal_series, factor_set: dict) -> dict:
    # Decompose signal variance thành known factors TRƯỚC KHI đưa vào portfolio
    # factor_set: {"btc_return": series, "funding_aggregate": series, ...}
    # Output: {factor: R², residual_R²}
    # Nếu R²(BTC) > 0.60 → signal là disguised BTC momentum → neutralize trước
    # Nếu residual_R² < 0.30 → signal không có idiosyncratic content → rủi ro cao
    # Chạy trước overfit tests, không sau — feature mining thường fail đây
```

**`overfit_tests.py`:**
```python
def deflated_sharpe_ratio(sharpe, n_trials, var_sharpe, skew, kurt): ...
def probability_of_backtest_overfit(cv_results): ...  # PBO < 0.50
def whites_reality_check(returns, benchmark_returns, n_boot=1000,
                         bootstrap="stationary"):
    # Crypto returns: serially dependent, heteroskedastic, fat-tailed
    # iid bootstrap (default nhiều library) → p-value quá optimistic
    # Dùng stationary bootstrap (Politis & Romano) hoặc circular block bootstrap
    # block_size nên dynamic, không static:
    #   crypto returns heteroskedastic → high-vol period cần block lớn hơn
    #   regime shift → block_size calibrated trên whole sample bị bias
    #   Solution: block_size per regime = AR(1) halflife của squared returns trong regime đó
    #   Conservative default: block_size = 2 × signal_halflife_bars

def effective_sample_size_warning(returns_df, regime_series) -> dict:
    # 2022-2025 KHÔNG phải "3 năm data độc lập"
    # Thực chất = vài regime episodes: 2022 bear, 2023 recovery, 2024 bull post-ETF
    # Effective n ≈ n_independent_regime_episodes × bars_per_regime / autocorr_factor
    # Ví dụ: 3 regimes × 200 bars × 0.5 autocorr → eff_n ≈ 300, không phải 26,000
    # Output warning nếu eff_n < 200 → DSR/PBO kém tin cậy hơn bạn nghĩ
    ...
def minimum_backtest_length(sharpe_target, n_trials): ...
def multiple_testing_correction(p_values, method="benjamini_hochberg"): ...
```

---

### 1.5 `nghien_cuu/nha_may_alpha/`

| # | File | Mô tả |
|:-:|------|--------|
| 1 | `__init__.py` | Package |
| 2 | `base_alpha.py` | BaseAlpha ABC — Research Harness |
| 3 | `alpha_registry.py` | AlphaSpec + lifecycle |
| 4 | `alpha_cemetery.py` | Research journal — failed alphas |
| 5 | `alphas/alpha_001_ema_cross.py` | Plumbing test (sẽ bị kill) |
| 6 | `alphas/alpha_002_funding_extreme.py` | Funding dislocation |
| 7 | `alphas/alpha_003_cross_sectional_momentum.py` | Relative strength |

**`base_alpha.py`:**
```python
class BaseAlpha(ABC):
    @abstractmethod
    def define_universe(self) -> AlphaUniverse:
        # assets, timeframe, features, horizon_bars

    @abstractmethod
    def generate_signal(self, df: pl.DataFrame) -> pl.Series:
        # Logic alpha. Cấm: future data, global stats, bfill.

    def quick_screen(self) -> QuickScreenResult:
        # < 2 phút. IC < 0.010 → KILL.

    def run_research(self, start_date, end_date) -> AlphaReport:
        # 1. Load + pit_audit
        # 2. generate_signal()
        # 3. PurgedCV → IC + IC_decay
        # 4. Fundamental Law: IR = IC × √BR
        # 5. Overfit tests: PBO, DSR, BH correction
        # 6. phase1_cost → cost-adjusted IR
        # 7. regime_conditional_ic (3 dims)
        # 8. AlphaReport + kill/continue decision
```

**`alpha_cemetery.py`:**
```python
@dataclass
class AlphaAutopsy:
    alpha_id: str
    name: str
    family: str
    hypothesis: str
    kill_stage: int           # 0-5
    kill_reason: str
    kill_date: str
    ic_insample: float
    pbo: float | None
    deflated_sharpe: float | None
    ir_estimate: float | None
    cost_adjusted_ir: float | None
    regime_fragility: str
    lessons: str
    related_to: list[str]

class AlphaCemetery:
    def bury(self, autopsy: AlphaAutopsy): ...
    def failure_pattern_report(self): ...  # kill rate by stage/family/feature
    def search_similar(self, new_hypothesis) -> list[AlphaAutopsy]: ...
```

**`alpha_registry.py`:**
```python
@dataclass
class AlphaSpec:
    name: str
    version: str
    family: str
    hypothesis: str           # bắt buộc
    economic_mechanism: str   # bắt buộc — WHY edge tồn tại về mặt kinh tế
    # Ví dụ: "crowded leverage unwind khi funding extreme → predictable mean reversion"
    # Không có economic_mechanism → feature mining → không research

    # Pre-registration fields — phải điền TRƯỚC khi nhìn bất kỳ backtest result nào
    # Sau khi registered → immutable. Thay đổi = new alpha_id, không phải tweak cũ.
    # Mục đích: chặn "narrative invented after discovery" — dạng overfitting tinh vi nhất
    registered_at: str        # timestamp lúc register, trước mọi compute
    features_locked: list[str]  # feature list không được thêm sau khi xem IC
    parameter_ranges: dict    # {"window": [10, 100], "threshold": [0.01, 0.10]}
    # Ngoài parameter_ranges này → kết quả không được tính là confirmatory

    requires_spot_borrow: bool = False  # True nếu alpha cần short spot (basis/carry)
    # Nếu True → cost model phải bao gồm borrowing_cost(); không được test chỉ với funding_pnl

    expected_ic: float
    expected_decay_halflife_bars: int
    expected_capacity_usdt: float
    kill_thresholds: dict = field(default_factory=lambda: {
        "min_ic": 0.010,
        "max_pbo": 0.50,
        "min_ir_estimate": 0.30,
        "min_cost_adjusted_ir": 0.25,
        "min_regime_survival": 0.67,
    })

class AlphaLifecycle(Enum):
    IDEA = "idea"
    SCREENING = "screening"
    RESEARCH = "research"
    VALIDATION = "validation"
    PAPER = "paper"
    SHADOW = "shadow"
    PRODUCTION = "production"
    PIPELINE_TEST = "pipeline_test"
    KILLED = "killed"
```

---

### 1.6 `nghien_cuu/khung_alpha/`

| # | File | Mô tả |
|:-:|------|--------|
| 1 | `alpha_taxonomy.md` | 10 family từ Phase 0 |
| 2 | `meta_research.py` | Pattern learning từ experiment_tracker + cemetery |

**`meta_research.py`:**
```python
class MetaResearchEngine:
    def feature_survival_report(self): ...    # feature nào có IC halflife dài nhất
    def alpha_family_statistics(self): ...    # kill rate, median IC, decay per family
    def regime_alpha_map(self): ...           # regime nào produce alpha nhiều nhất
    def redundancy_detector(self, new_signals, existing_signals): ...
```

---

### 1.7 `nghien_cuu/so_tay_jupyter/`

| # | Notebook | Nội dung |
|:-:|----------|----------|
| 1 | `00_plumbing_test.ipynb` | EMA cross qua full pipeline |
| 2 | `01_data_exploration.ipynb` | Download → clean → PiT audit → universe check |
| 3 | `02_feature_engineering.ipynb` | Features → IC → orthogonality → stability |
| 4 | `03_alpha_screening.ipynb` | Quick triage: IC screen nhiều ideas |
| 5 | `04_model_training.ipynb` | Labels → Purged CV → Train → Overfit tests |
| 6 | `05_backtest_validation.ipynb` | Backtest → Decay → Capacity → Regime |

---

### Tổng hợp Phase 1

| Module | Files | Tuần |
|--------|:-----:|:----:|
| `dong_co_du_lieu/xu_ly_lo/` | 7 | 1 |
| `hoc_may/huan_luyen/` | 4 | 1-2 |
| `nghien_cuu/kiem_thu_qua_khu/ma_tran_sie_toc/` | 3 | 2 |
| `nghien_cuu/danh_gia/` | 7 | 2-3 |
| `nghien_cuu/nha_may_alpha/` | 7 | 3-4 |
| `nghien_cuu/khung_alpha/` | 2 | 4 |
| `nghien_cuu/so_tay_jupyter/` | 6 | 4 |
| `cau_hinh/research.yaml` | 1 | 0 |
| **Tổng** | **37** | **4 tuần** |

---

## PHASE 2 — Alpha Discovery (Tuần 5-8)

**Gate vào:** Phase 0.5 pass. **Mục tiêu:** 3-5 signals IC > 0.012, stable, survive cost.

> **Chiến lược:** Focus 1 alpha family duy nhất trước. Dominate 1 niche trước khi mở rộng.
> Chọn Funding/Carry làm family đầu tiên — data đã có, economic mechanism rõ nhất.

> **Fill Model gate (CỨNG):** Bất kỳ alpha nào halflife < 50 bars hoặc cross-exchange
> PHẢI pass basic event-driven fill simulation trước khi vào Phase 3.
> Slippage từ L2 snapshot thực tế — không dùng công thức vectorized.
> Lý do: vectorized Sharpe 2.0 → event-driven Sharpe -0.3 là phổ biến ở crypto intraday.
> Alpha fail fill gate → KILL ngay, không đưa vào Portfolio Optimizer.
> Fill model đầy đủ (queue priority, partial fills, latency) vẫn ở Phase 4.

### Alpha Triage

```
**Research Budget (hard limit):**
```
STAGE 0:  30 phút max → KILL hoặc go
STAGE 1:  2 phút compute
STAGE 2:  1 giờ max
STAGE 3:  6 giờ max, max 3 parameter sweeps
STAGE 4:  1 ngày max
STAGE 5:  1 ngày max
Tổng idea → validation: ≤ 2 ngày wall time. Vượt quá → tự động kill.
```

STAGE 0 — Hypothesis (30 phút, không code):
  □ 1 câu: "X xảy ra vì [lý do kinh tế]"
  □ economic_mechanism documented (forced unwind? dealer imbalance? inventory transfer?)
  □ Cemetery check: hypothesis tương tự đã chết chưa?
  □ halflife ≥ 20 bars + data có sẵn
  □ Exclude khoảng thời gian có market structure events (từ dataset_registry)
  □ FAIL bất kỳ → KILL

STAGE 1 — Quick Screen (< 2 phút):
  □ IC trên 2022-2023 subset, IC < 0.010 → KILL

STAGE 2 — IC Validation (< 1 giờ):
  □ IC full in-sample, IC decay curve
  □ IR_estimate (Grinold-Kahn) > 0.30 → continue

STAGE 3 — Robustness (< 6 giờ):
  □ Purged CV + embargo
  □ PBO < 0.50, Deflated Sharpe > 0, BH p-value < 0.05

STAGE 4 — Cost + Regime (< 1 ngày):
  □ cost-adjusted IR > 0.25
  □ Regime IC > 0 trong ≥ 2/3 combinations
  □ Capacity > min_capital

STAGE 5 — Portfolio (< 1 ngày):
  □ Correlation với existing alphas < 0.60
  □ Marginal IR > 0.05
  □ PASS → lifecycle = VALIDATION
```

### Alpha Ideas (P1 families)

```
FUNDING/CARRY:
  A: funding > 0.08%/8h → short perp, expect reversion
  B: basis (spot-perp spread) divergence → carry signal
  C: funding divergence Binance vs Bybit → directional

CROSS-SECTIONAL MOMENTUM:
  D: 24h return rank across 20 coins → long top, short bottom
  E: volume-weighted relative strength

VOLATILITY REGIME:
  F: vol compression → upcoming expansion
  G: vol regime transition → alpha activation
```

---

## PHASE 3 — Portfolio + Validation (Tuần 9-12)

**Gate:** ≥ 3 alpha ở lifecycle = VALIDATION.

### `hoc_may/mo_hinh/`

| # | File | Mô tả |
|:-:|------|--------|
| 1 | `__init__.py` | Package |
| 2 | `alpha_model.py` | ABC: fit, predict, feature_importance |

```python
# Priority: Linear > LightGBM (OOS gain > 15%) > NN (> 100k samples)
```

### `hoc_may/to_hop_alpha/`

| # | File | Mô tả |
|:-:|------|--------|
| 1 | `__init__.py` | Package |
| 2 | `alpha_combiner.py` | Combine + marginal IR + crowding |
| 3 | `risk_model.py` | BTC beta neutralization → PCA |
| 4 | `portfolio_optimizer.py` | Convex optimization với turnover penalty |

**`portfolio_optimizer.py`:**
```python
def optimize_portfolio(mu, sigma, w_prev, lambda_risk=1.0, lambda_turnover=0.1,
                       w_max=0.20, leverage=1.0):
    """
    Maximize  w^T μ  −  λ_risk × w^T Σ w  −  λ_turnover × ||w − w_prev||_1

    Dùng cvxpy. ||w − w_prev||_1 penalize turnover (→ giảm cost).
    lambda_turnover calibrate từ phase1_cost estimate:
      low lambda → hight turnover → cost > alpha decay → net IR âm
    Constraints: sum(w) = 1, |w_i| ≤ w_max, ||w||_1 ≤ leverage,
                 margin_ratio ≥ min_margin_ratio  # BẮTBUỘC — xem note dưới

    Lưu ý thực tế:
    - Fee Binance theo tier (VIP0: 4bps, VIP5: 1.2bps) → lambda_turnover phải dùng fee thực tế
    - Funding không đối xứng: long perp pays funding khi > 0, short receives; nhưng basis
      spread Binance vs Bybit systematic trong uptrend → position routing ảnh hưởng net cost
    - Rebalance quá nhỏ (|Δw| < threshold) → skip để tránh L1 tối ưu "chính xác" nhưng
      cost thực tế > lợi ích tái cân bằng

    Margin constraint (BẮTBUỘC — retail thường bỏ qua, đây là nguyên nhân cháy tài khoản):
    - Cross-margin: khi BTC sập, giá trị collateral giảm + unrealized loss + funding cực âm
    - Vectorized backtest Phase 1-2 ghi "drawdown 15%" → thực tế tài khoản bị thanh lý ở -12%
    - margin_ratio = (equity - initial_margin) / maintenance_margin phải ≥ 1.2 (buffer)
    - Tính margin_ratio theo Binance/Bybit cross-margin rules cho từng symbol
    - Nếu constraint này binding → reduce leverage, không reduce signal
    """
    import cvxpy as cp
    n = len(mu)
    w = cp.Variable(n)
    turnover_cost = cp.norm1(w - w_prev)
    objective = cp.Maximize(mu @ w - lambda_risk * cp.quad_form(w, sigma)
                            - lambda_turnover * turnover_cost)
    constraints = [cp.sum(w) == 1, cp.norm_inf(w) <= w_max,
                   cp.norm1(w) <= leverage]
    prob = cp.Problem(objective, constraints)
    prob.solve(solver=cp.CLARABEL)
    raw_weights = w.value

    # Tick size / lot size rounding — BẮTBUỘC trước khi gửi order
    # CVXPY ra weights liên tục (ví dụ 1.23456 BTC), sàn có step_size constraint
    # Nếu portfolio nhỏ: rounding theo lot_size có thể xóa sạch optimal hedge
    # round_to_lot(raw_weights, lot_sizes, notional) → discrete weights
    # Sau rounding: recompute margin_ratio để verify constraint vẫn satisfied
    return round_to_lot(raw_weights, lot_sizes, notional)
```

**`risk_model.py`:**
```python
class RiskModel:
    def explicit_factor_neutralize(self, returns_df, factor_returns_df):
        # Bước 1: regress out explicit factors trước PCA
        # Crypto factor list (theo thứ tự variance contribution):
        #   BTC, ETH, Layer1 sector, DeFi sector, Meme sector, AI sector,
        #   Exchange liquidity (Binance vs Bybit spread), Stablecoin dominance
        #   Aggregate Market Funding Rate (perp basis avg toàn thị trường)
        #   Exchange Spread Matrix (Binance_funding - Bybit_funding systematic diff)
        # Aggregate Funding Factor: trong uptrend mạnh, toàn market long nặng →
        #   funding alpha bị diluted; factor này neutralize crowded-long-market exposure
        # Exchange Spread Factor: Bybit basis drift vs Binance = systematic, không phải edge
        # Nếu chỉ regress BTC → Meme coin event làm portfolio lệch nặng
        # Residual = truly idiosyncratic return

    def shrink_covariance(self, returns_matrix) -> np.ndarray:
        # Ledoit-Wolf shrinkage TRƯỚC PCA và TRƯỚC MVO
        # Sample covariance "maximize errors" khi T/N nhỏ (crypto: T~500, N~50)
        # LW tìm optimal α: Σ_shrunk = (1-α) Σ_sample + α μ_trace × I
        # Dùng sklearn.covariance.LedoitWolf hoặc implement analytical shrinkage
        # Output: shrunk covariance matrix, cùng shape, condition number tốt hơn
        from sklearn.covariance import LedoitWolf
        lw = LedoitWolf().fit(returns_matrix)
        return lw.covariance_

    def pca_factor_model(self, residual_returns, n_factors=3):
        # Bước 2: PCA trên residual (sau shrink_covariance) → unlabeled latent factors

    def downside_beta(self, returns_df, market_returns, threshold_pct=-0.02):
        # Beta khi market < threshold (tail regime)
        # Crypto: bình thường beta=1.2 → khi BTC -10% beta của alt lên 2.0-3.0
        # Linear factor model nói "market neutral" → margin call thực tế
        # Tính: OLS chỉ trên rows market_returns < threshold → downside_beta_matrix
        # Red flag: downside_beta > 2 × normal_beta → hidden tail exposure

    def regime_conditional_covariance(self, returns_df, regime_series):
        # Covariance per regime, không phải covariance tĩnh toàn thời gian
        # Crypto tail: correlations → 1.0 → PCA decomposition invalid
        # Tính: shrink_covariance() per regime bucket → 3 covariance matrices
        # Dùng trong stress_test, không dùng trong daily optimization (stability)

    def risk_attribution(self, portfolio_weights, factor_loadings):
        # % variance per factor. Red flag: BTC > 60%, any single sector > 40%.

    def stress_test(self, portfolio_weights, scenario):
        # {"BTC": -30%, "alts": -50%, "meme_sector": -80%} → expected drawdown
        # Dùng regime_conditional_covariance(tail regime) thay vì covariance bình thường
```

**`alpha_combiner.py`:**
```python
class AlphaCombiner:
    def marginal_ir(self, new_signals) -> float: ...    # < 0.05 → skip
    def correlation_clustering(self) -> dict: ...       # tránh cluster = 1 alpha
    def crowding_exposure(self) -> float: ...           # corr với CTA factor
    def combine(self, method="risk_parity"): ...
```

---

## PHASE 4 — Execution Reality (Tuần 13+)

**Gate:** ≥ 3 alphas, IR_combined > 0.50, BTC-beta neutralized, vectorized Sharpe > 1.5.

| # | File | Mô tả |
|:-:|------|--------|
| 1 | `nghien_cuu/kiem_thu_qua_khu/mo_phong_su_kien/event_backtest.py` | Queue, partial fills, latency |
| 2 | `nghien_cuu/kiem_thu_qua_khu/mo_phong_su_kien/fill_model.py` | Book depletion cost |
| 3 | `nghien_cuu/dong_co_phat_lai/replay_engine.py` | parquet → ZMQ → production pipeline |
| 4 | `hoc_may/huan_luyen/onnx_exporter.py` | Sau shadow trade |

**`replay_engine.py`:** Đọc parquet → emit ZMQ format của `ha_tang/bus_su_kien/` → tích hợp `moi_truong_chay/backtest/`.

### Live Auto-Kill / Dynamic Alpha Decay

**`giam_sat/auto_kill.py`:**
```python
class AlphaAutoKill:
    """
    Rolling live Sharpe vs backtest expectation → auto scale down khi ngoài CI.
    Alpha không chết đột ngột — nó decay dần dần khi regime đổi.
    """
    def compute_live_ic_decay(self, alpha_id, window_days=30) -> float:
        # IC decay là kill signal tốt hơn Sharpe z-score cho alpha monitoring
        # Rolling Sharpe có noise quá lớn với window 60 ngày → whipsaw:
        #   kill alpha đúng lúc nó drawdown bình thường, trước khi mean-revert
        # IC decay: rolling IC (live) vs backtest IC mean
        # Nếu live_IC < 0.3 × backtest_IC sustained 20 ngày → signal edge đang mất
        # Tách biệt khỏi PnL: alpha có thể IC ổn nhưng PnL kém vì cost tăng → khác cause

    def compute_live_sharpe_zscore(self, alpha_id, window_days=60) -> float:
        # Dùng như secondary signal — không phải primary kill trigger
        # z = (live_sharpe_rolling - bt_sharpe_mean) / bt_sharpe_std

    def check_kill_condition(self, alpha_id) -> str:
        # Primary: IC decay < 30% of backtest IC for 20 days → scale_down
        # Secondary: Sharpe z < -2.58 (99%) → scale_down (supporting evidence only)
        # Cả 2 triggered → kill_candidate
        # Không kill dựa trên Sharpe z-score đơn lẻ — quá nhiều false positives
        # Return: "ok" | "scale_down" | "kill_candidate"

    def auto_scale(self, alpha_id, portfolio_manager):
        # Gọi portfolio_manager.set_alpha_weight(alpha_id, scale_factor)
        # Log event vào experiment_tracker để postmortem
```

> **Lưu ý:** Auto-kill dựa trên statistical breach, không phải PnL breach.
> PnL breach = risk management (đã có `quan_tri_rui_ro/`).
> Auto-kill = alpha decay detection — 2 cơ chế tách biệt.

### Reality Gap Monitor

**`giam_sat/reality_gap_monitor.py`:**
```python
class RealityGapMonitor:
    """
    Track divergence backtest → live liên tục. Alpha chết chậm mà không ai biết.
    """
    def track(self, alpha_id):
        # Các dimension cần monitor:
        # fill_rate:     expected fills % vs actual fills %
        # turnover:      expected daily turnover vs actual
        # holding:       expected avg hold bars vs actual
        # ic_live:       rolling live IC vs backtest IC
        # decay_live:    live IC decay halflife vs backtest halflife
        # slippage:      actual slippage vs phase1_cost estimate

    def divergence_report(self, alpha_id, window_days=30) -> dict:
        # z-score mỗi dimension. Flag nếu |z| > 2.0.
        # Nếu slippage/turnover/holding cùng diverge → execution model sai
        # Nếu chỉ ic_live diverge → signal edge đang mất
        # 2 root causes khác nhau → fix khác nhau
```

---

## Promotion Gates

```yaml
# cau_hinh/research.yaml

promotion_gates:
  screening_to_research:
    - ic_insample > 0.010
    - hypothesis_documented: true
    - frequency_halflife_bars >= 20
    - cemetery_check_passed: true

  research_to_validation:
    - ic_insample > 0.015
    - pbo < 0.50
    - deflated_sharpe > 0.0
    - ir_estimate > 0.30
    - bh_corrected_pvalue < 0.05

  validation_to_paper:
    - ic_oos > 0.012                    # embargo set, NOT holdout
    - deflated_sharpe_oos > 0.0
    - regime_survival >= 0.67
    - capacity_estimate > min_capital
    - btc_beta_neutralized_ir > 0.25
    - portfolio_correlation < 0.60

  paper_to_shadow:
    - paper_days >= 30                  # tăng từ 14 → 30: 14 ngày crypto quá ngắn để phân biệt edge vs luck
    - live_tiny_days >= 30              # tăng từ 21 → 30: tiền thật, size = 1% target
    - live_slippage_vs_estimate < 2.0
    - live_ir >= 0.40

  shadow_to_production:
    - shadow_days >= 90                 # tăng từ 60 → 90: 2 tháng vẫn có thể survive bởi luck
    - shadow_sharpe >= 0.80
    - portfolio_correlation_live < 0.30
    - max_drawdown_shadow < 0.15
    - marginal_ir_to_portfolio > 0.05

early_phase_exception:
  # 6 tháng đầu: cho phép 1-2 alpha borderline đi qua full pipeline để test path
  ir_estimate_minimum: 0.20
  promotion_to: "PIPELINE_TEST"
  max_capital: "100 USDT"
```

---

## Verification Plan

| Test | Cách test | Pass |
|------|-----------|:----:|
| PiT embargo | IC[embargo=0] vs IC[embargo=5] | Drop < 20% |
| PiT future probe | return[t+1] feature | Model không chọn |
| Gap handling | Gap > max_gap_bars | NaN, không ffill |
| Funding alignment | validate_funding_alignment() | corr(f[t], r[t-1]) > corr(f[t], r[t+1]) |
| Universe PiT | get_active_universe(T) | Không có coin listed after T |
| Survivorship bias | Backtest 2022 | LUNA tracked, không phải LUNC |
| Data coverage | Daily gap report | ≥ 95%/ngày |
| Feature parity | batch vs live | max diff < 1e-6 |
| Pipeline idempotency | Chạy 2 lần | bit-exact |
| PBO | CSCV | < 50% |
| Deflated Sharpe | Bailey & LdP | > 0 |
| Multiple testing | BH correction | Corrected p < 0.05 |
| IC stability | std/mean | < 0.5 |
| Fundamental Law | IC × √BR | > 0.30 |
| Regime survival | IC per regime | > 0 in ≥ 2/3 |
| BTC beta | IR after explicit_factor_neutralize | > 0 |
| Sector risk | Sector factor % variance | < 40% per sector |
| Risk attribution | BTC factor % | < 60% |
| Market impact | phase1_cost dùng volume | Low-liq coin không được chọn |
| Effective breadth | BR_effective vs BR_naive | BR_effective < BR_naive |
| Market structure | Exclude event windows | IC stable ngoài event windows |
| Momentum cost | vol_penalty applied | Sharpe drop ≤ 30% |
| Tiny live slippage | 1% size vs estimate | ≤ 2× |
| Plumbing test | Dummy alpha full run | AlphaReport < 5 min |
| Ledoit-Wolf | condition_number(Σ_shrunk) vs Σ_sample | Condition số giảm ≥ 10× |
| Convex opt turnover | lambda_turnover sweep | Net IR tăng khi có penalty |
| Auto-kill | Inject synthetic decay | Scale down trigger trong ≤ 3 ngày |
| Regime transition | transition_matrix row sums | = 1.0 per row |
| Feature exposure | feature_exposure(signal, factors) | residual R² > 0.30 |
| Cross-exchange val | IC Binance vs IC Bybit | Drop < 30% |
| Simplicity score | simplicity_score() | không kill, chỉ tie-break |
| Reality gap | fill_rate divergence z-score | ≤ 2.0 |
| Parameter freeze | post-validation tweak count | = 0 |
| Pre-registration | features_locked filled trước backtest | True |
| Funding signal type | classify_funding_signal_type() | "realized" hoặc "predictive_basis" |
| Margin constraint | optimizer margin_ratio | ≥ 1.2 |
| Downside beta | beta tại market < -2% | < 2 × normal beta |
| Bootstrap | whites_reality_check | stationary bootstrap |
| phase1_cost volume | source of avg_volume | true_liquidity (L2), not ADV |
| Data seam | reconcile source | WS stream, không phải REST klines |
| Gap fill | is_gap_filled bars in IC | Excluded |
| Outlier handling | raw returns modified | False (features only) |
| L2 spoofing | fill_rate_discount applied | Effective depth < raw depth |
| Auto-kill trigger | primary signal | IC decay (not Sharpe z) |
| Borrowing cost | carry/basis alpha | requires_spot_borrow → borrowing_cost() included |
| Lot size rounding | optimizer output | round_to_lot() before order |
| Effective n | effective_sample_size_warning() | n_independent_episodes logged |

---

## Roadmap

```
Tuần 0:    Phase 0.25 — Pipeline reliability + universe PiT DB
           Phase 0    — Alpha Taxonomy + holdout policy
Tuần 1-4:  Phase 1    — Research Harness (36 files)
Tuần 4:    Phase 0.5  — Plumbing Test
Tuần 5-8:  Phase 2    — Alpha Discovery (triage 50+ ideas)
Tuần 9-12: Phase 3    — Portfolio + Validation
Tuần 13+:  Phase 4    — Event-driven → Paper 30 ngày → Tiny Live 30 ngày → Shadow 90 ngày → Production
```

---

## Tổng hợp files

| Phase | Module | Files |
|:-----:|--------|:-----:|
| 1 | `dong_co_du_lieu/xu_ly_lo/` | 7 |
| 1 | `hoc_may/huan_luyen/` | 4 |
| 1 | `nghien_cuu/kiem_thu_qua_khu/ma_tran_sie_toc/` | 3 |
| 1 | `nghien_cuu/danh_gia/` | 7 |
| 1 | `nghien_cuu/nha_may_alpha/` | 7 |
| 1 | `nghien_cuu/khung_alpha/` | 2 |
| 1 | `nghien_cuu/so_tay_jupyter/` | 6 |
| 1 | `cau_hinh/research.yaml` | 1 |
| 3 | `hoc_may/mo_hinh/` | 2 |
| 3 | `hoc_may/to_hop_alpha/` | 4 |
| 4 | `nghien_cuu/kiem_thu_qua_khu/mo_phong_su_kien/` | 3 |
| 4 | `nghien_cuu/dong_co_phat_lai/` | 1 |
| 4 | `hoc_may/huan_luyen/onnx_exporter.py` | 1 |
| 4 | `giam_sat/auto_kill.py` | 1 |
| 4 | `giam_sat/reality_gap_monitor.py` | 1 |
| | **Tổng** | **49** |