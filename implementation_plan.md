# KAIROS v3.2 — Implementation Plan

Mid-Frequency Systematic Trading — Microstructure-Aware Architecture

**Version:** 16 | **Date:** 2026-05-16 | **Horizon:** 18 tháng
**Target:** 2–3 live alphas, top-20 crypto perps, capacity $500K–$2M/strategy *(aspirational — validate từ live fills, crowding thực tế, và fee tier sau Phase 2)*

---

## Cách đọc tài liệu này

Mỗi module được viết như một **mắc xích độc lập**: có thể đọc, build, test, và validate riêng lẻ mà không cần đọc toàn bộ document. Mỗi module có:

- **Input / Output** — contract dữ liệu rõ ràng
- **Invariants** — những điều phải đúng, testable
- **Parameters** — với calibration status `[PUBLISHED / ESTIMATED / ASSUMED]`
- **Failure modes** — cách module này fail và cách detect
- **Tests** — test cases tối thiểu phải pass
- **Depends on / Provides to** — dependency graph

**Build priority:**

- `TIER-A` — build ngay, alpha discovery bị blocked nếu thiếu
- `TIER-B` — build sau khi có ≥1 live alpha

---

## Sơ đồ cấu trúc file — Module → Folder Mapping

Tổng: **65 file Tier-A** + **3 file Tier-B** = **68 file mới** (bao gồm 2 file M-D0 Phase 0).
Ký hiệu: `★` = file quan trọng nhất trong folder | `[existing]` = folder đã có | `[new]` = tạo mới

---

### PHASE 0 — TIER A (2 files — build song song với M-D1, trước PHASE 1)

```text
dong_co_du_lieu/quan_ly_phien_ban/  [new]  2 files  ← M-D0 Data Lineage Registry
│  Module coverage: M-D0 (Data Lineage — foundational, không phụ thuộc module nào)
│  [BUILD FIRST — Gate 0→1 yêu cầu M-D0 operational]
├── ★ dataset_record.py             ← DatasetRecord dataclass (frozen, UUID, SHA-256, lineage DAG)
│                                     as_of_feature_snapshot(date) → dataset_id
│                                     Mọi backtest PHẢI log dataset_id_used vào đây
└── lineage_registry.py             ← append-only JSON registry, query by dataset_id + date
                                      feature_logic_hash tracking, as_of snapshot lookup
```

---

### PHASE 1 — TIER A (42 files + 4 additional)

```text
dong_co_du_lieu/xu_ly_lo/          [new]  8 files  ← M-D2 gap + M-D3 PiT + M-D4 L2 batch
│  Module coverage: M-D2 (Gap Reconciliation), M-D3 (PiT Universe), M-D4 (L2 pre-agg)
├── pre_aggregate_l2.py             ← L2 orderbook → 5-min aggregated features
│                                     [CRITICAL] Lưu raw L2 snapshots song song trước khi aggregate.
│                                     Tick data không thể reconstruct từ aggregates.
│                                     Cần cho HFT project sau này. Storage cost thấp.
├── reconcile_borrow_rates.py       ← merge borrow rate từ Coinglass vào bars
├── gap_detector.py                 ← scan missing bars per (exchange, symbol)
├── rest_filler.py                  ← fill gap ≤3 bars từ REST, mark is_gap_filled
├── quality_tagger.py               ← assign data_quality: 0/1/2/3
├── ★ pit_universe.py               ← expanding window, no look-ahead, delisting handler
├── symbol_remapper.py              ← track exchange renames (DEFI-PERP → DEFIUSDT)
└── schema_validator.py             ← validate Parquet schema hash + schema_version tracking
                                      SCHEMA_REGISTRY per dataset type, backward-compat read policy

hoc_may/huan_luyen/                [new]  5 files  ← M-R1 ML Training Pipeline (CRITICAL GAP)
│  Module coverage: M-R1
├── experiment_record.py            ← pre-registration, n_trials/family tracking (immutable)
├── reproducibility.py              ← dataset SHA-256 lock, random seed pin, env snapshot
├── labeler.py                      ← horizon returns, funding blackout → NaN labels
├── ★ trainer.py                    ← train model → export ONNX (LightGBM / Ridge / MLP)
└── dataset_splitter.py             ← PiT-safe train/val split, no future leak

nghien_cuu/kiem_thu_qua_khu/
│  ma_tran_sie_toc/                [existing]  3 files  ← M-R7 cost calibration
│  Module coverage: M-R7 (Cost Model — slippage estimation)
│  ├── ★ slippage_matrix.py         ← size × venue × regime → estimated slippage
│  ├── venue_profiler.py            ← per-exchange liquidity depth, spread stats
│  └── regime_cost_adjuster.py      ← apply regime multiplier to base cost

nghien_cuu/danh_gia/               [existing]  7 files  ← M-R2, M-R4, M-R5 validation
│  Module coverage: M-R2 (Leakage), M-R4 (T1), M-R5 (T2)
├── ★ leakage_audit.py              ← M-R2: future probe + normalization check → PASS/FAIL
├── purged_kfold.py                 ← M-R4: 5-fold, 21-day embargo, label purge
├── dsr_calculator.py               ← M-R4: Deflated Sharpe Ratio (n_trials aware)
├── regime_split.py                 ← M-R4: ADX-based regime IC split
├── walk_forward.py                 ← M-R5: 6-window WF, 4:1 train:test
├── stress_tester.py                ← M-R5: Luna + FTX mandatory stress periods
└── capacity_estimator.py           ← M-R5: L2-based true capacity vs ADV estimate

nghien_cuu/nha_may_alpha/          [existing]  7 files  ← M-R3, M-R4, M-R5, M-R7, M-R8, M-R9
│  Module coverage: T0/T1/T2 screening, cost model, factor neutral, registry
├── t0_screen.py                    ← M-R3: raw IC + rough cost → PASS/KILL ≤15 min
├── t1_validate.py                  ← M-R4: PurgedKFold + DSR + regime + T1.7 stability
├── t2_diligence.py                 ← M-R5: stress + walk-forward + T2.8 halflife
├── ★ cost_model.py                 ← M-R7: round_trip_cost_bps(symbol, side, size, regime)
├── factor_neutralizer.py           ← M-R8: BTC/ETH/sector neutralization
├── alpha_registry.py               ← M-R9: AlphaRecord, stage tracking, similarity search
└── alpha_cemetery.py               ← M-R9: AlphaAutopsy, kill reason, cemetery lookup

nghien_cuu/khung_alpha/            [new]  3 files  ← base contracts cho mọi alpha
│  Module coverage: cross-cutting (M-R3 through M-R5 dùng types từ đây)
├── base_alpha.py                   ← AlphaHypothesis dataclass, venue_type, family enum
├── ★ alpha_contract.py             ← T0Result, T1Result, T2Result, ExperimentRecord types
└── feature_spec.py                 [new, Phase 1]  ← FeatureSpec dataclass registry (INV-D4.18)

nghien_cuu/so_tay_jupyter/         [existing]  8 notebooks  ← research exploration
│  Module coverage: all alpha families (F001–F004, M001–M003, OB001)
├── ★ F001_funding_mean_reversion.ipynb
├── F002_cross_exchange_funding.ipynb
├── F003_oi_funding_lead.ipynb
├── F004_funding_xs_rank.ipynb
├── M001_oi_weighted_momentum.ipynb
├── M002_vol_relative_strength.ipynb
├── M003_momentum_post_funding.ipynb
└── OB001_ofimicrostructure.ipynb   ← BLOCKED until Family 1/2 fills calibrate M-R7

cau_hinh/research.yaml             1 file
│  ic_threshold, dsr_threshold, embargo_days, stress_periods, cost_assumptions

cau_hinh/exchange_metadata.yaml   1 file
│  Per-exchange: funding schedule, maintenance patterns, min_order_size,
│  liquidation engine, index_price_source, api_latency_ms, fee_tiers
│  [SINGLE SOURCE OF TRUTH] — adapters import từ đây, không hardcode

scripts/reveal_holdout.py          1 file  ← M-R5: one-time holdout reveal
scripts/run_alpha_pipeline.py      1 file  ← end-to-end: T0 → T1 → T2 runner

nghien_cuu/kham_pha_dac_trung/     [new]  3 files  ← M-R10 anomaly + feature cache
│  Module coverage: M-R10 (Anomaly Miner — TIER-A Phase 1)
├── observation_log.py              ← log raw observations (anomalies, regime shifts)
├── ★ anomaly_miner.py              ← scan for distribution breaks, IC spikes
└── feature_cache.py                ← offline feature pre-computation cache manager

giam_sat/trang_thai_thi_truong/    [new]  2 files  ← M-R11 Market State Engine (TIER-A Phase 1)
│  Module coverage: M-R11
├── ★ market_state_engine.py        ← 8-dimension state vector per bar (real-time + batch)
└── state_store.py                  ← Parquet persistence + query interface cho downstream

nghien_cuu/danh_gia/               [existing — add 1 file TIER-A, promote from TIER-B]
└── crowding_monitor.py             ← TIER-A Phase 1 (promoted từ TIER-B)
                                       pre-entry drift detection + cross-alpha contagion
```

---

### PHASE 3 — TIER A (8 files)

```text
hoc_may/mo_hinh/                   [existing]  2 files  ← trained model artifacts
│  Module coverage: M-R1 output storage
├── ★ model_registry.py             ← version tracking: alpha_id → onnx path → metrics
└── model_versioner.py              ← promote model version khi PASS T2

hoc_may/to_hop_alpha/              [existing]  4 files  ← M-L4 ERC Portfolio
│  Module coverage: M-L4 (Portfolio Construction)
├── ★ erc_optimizer.py              ← Equal Risk Contribution (scipy minimize)
├── alpha_weighter.py               ← signal → target weight per alpha
├── portfolio_rebalancer.py         ← diff current vs target, generate orders
└── combination_engine.py           ← ensemble N alphas into single signal

nghien_cuu/danh_gia/
│  ├── portfolio_accounting.py      [new]  1 file  ← backtest PnL attribution by alpha
│  └── signal_attribution.py       [new, Phase 3]  ← WHY signal fired per bar
│                                                      signal_score = sum(coef_i × feature_i)
│                                                      Attribution: funding_extreme=+0.42, OI_div=+0.31, crowding=-0.11
│                                                      Dùng để debug decay, live drift, false positives

nghien_cuu/nha_may_alpha/
│  └── alpha_retirement.py          [new]  1 file  ← M-R9: trigger retirement khi decay sustained
```

---

### PHASE 4 — HFT NEW PROJECT (9 files) — rebuild, không phải extension

```text
nghien_cuu/kiem_thu_qua_khu/
│  mo_phong_su_kien/               [existing]  4 files  ← M-H1 Event-Driven Simulator
│  Module coverage: M-H1
│  ├── exchange_simulator.py        ← full order book matching engine simulation
│  ├── ★ event_simulator.py         ← replay market events tick-by-tick
│  ├── queue_model.py               ← maker queue position estimation
│  └── fill_engine.py               ← probabilistic fill based on queue depth

nghien_cuu/dong_co_phat_lai/       [existing]  +1 file  ← M-R6 addition
│  └── vectorized_backtest.py       ← Polars-native vectorized backtest engine

hoc_may/huan_luyen/
│  └── onnx_exporter.py            [new]  1 file  ← M-R1: export trained model → ONNX

giam_sat/                          [existing — add 3 files]  ← M-L2, M-L3 live monitoring
├── execution_parity.py             ← M-L2: live slippage vs model (KS test weekly)
├── reality_gap_monitor.py          ← M-L2: live IC vs backtest IC per alpha
└── ★ auto_kill.py                  ← M-L3: rolling 30d IC < 25% inception → flag kill
```

---

### TIER B — build sau khi có ≥2 live alphas (2 files)

```text
nghien_cuu/danh_gia/               [add to existing]
├── combinatorial_cv.py             ← CPCV: combinatorial purged CV cho robust DSR
└── regime_novelty.py               ← deep regime novelty (full ML — HMM/BOCPD)
                                       [NOTE] M-R11 OOD score đã cover minimum viable detection.
                                       TIER-B này là advanced extension, không prerequisite.

[PROMOTED TO TIER-A Phase 1]:
  crowding_monitor.py               ← đã chuyển vào nghien_cuu/danh_gia/ TIER-A
                                       (xem Phase 1 file structure + M-L4 section)
```

---

```text
────────────────────────────────────────────────────────────────────────
TỔNG KẾT

Phase 0 Tier-A:    2 files             (M-D0 Data Lineage — build TRƯỚC Phase 1)
Phase 1 Tier-A:   43 + 4 = 47 files   (foundation + first alpha research, incl. feature_spec.py)
Phase 3 Tier-A:    9 files             (portfolio construction, incl. signal_attribution.py)
Phase 4 HFT:       9 files             (new project — funded by mid-freq profits)
Tier-B:            3 files             (advanced — sau 2 live alphas)
─────────────────────────────────────────────────────────────────────
Total Tier-A:     66 files
Total (A+B):      69 files

Folders hiện tại cần ADD files (không tạo mới):
  dong_co_du_lieu/xu_ly_lo/         → 8 files mới
  nghien_cuu/danh_gia/              → 7 files + 1 (phase3) + 3 (tier-b)
  nghien_cuu/nha_may_alpha/         → 7 files + 1 (phase3)
  nghien_cuu/so_tay_jupyter/        → 8 notebooks
  hoc_may/to_hop_alpha/             → 4 files
  hoc_may/mo_hinh/                  → 2 files
  giam_sat/                         → 3 files

Folders cần TẠO MỚI:
  dong_co_du_lieu/quan_ly_phien_ban/ ← M-D0, build trước mọi thứ khác
  dong_co_du_lieu/xu_ly_lo/
  hoc_may/huan_luyen/               ← CRITICAL GAP, build đầu tiên trong Phase 1
  nghien_cuu/khung_alpha/
  nghien_cuu/kham_pha_dac_trung/
────────────────────────────────────────────────────────────────────────
```

---

## Nguyên tắc cốt lõi (5 rules)

**R1. Alpha velocity trên hết.** Mọi PR phải kèm: *"This unblocks [step] in [alpha] pipeline."* Không có câu đó → không merge.

**R2. Infrastructure chỉ build khi bị blocked cụ thể.** Không build "phòng khi cần".

**R3. Three-tier screening là luật.** T0 → T1 → T2. Không skip tier.

**R4. Mid-freq code KHÔNG được thiết kế để trở thành HFT code.** HFT là một project riêng, được rebuild từ đầu, funded bởi mid-freq profits. Không optimize latency trong codebase hiện tại. Không extract C/Rust từ Python hiện tại. Viết code sạch vì maintainability, không phải vì "sau này extract được". Xem **HFT Transition Philosophy** bên dưới.

**R5. Live fills là ground truth.** Sau 100 fills đầu tiên, calibrate lại toàn bộ cost model.

---

## HFT Transition Philosophy

```text
Mid-freq và HFT là hai kiến trúc KHÁC NHAU. Không thể evolve cái này thành cái kia.

MID-FREQ (hiện tại) = HỌC VÀ EARN
  Mục tiêu: học microstructure bằng real money ở risk thấp,
            generate capital để fund HFT infrastructure,
            identify cái gì thực sự work trước khi invest vào speed.
  Horizon: 30min–4h bars
  Stack:   Python, Polars, ZMQ, vectorized backtest

HFT (tương lai) = NEW PROJECT — REBUILD TỪ ĐẦU
  Mục tiêu: capture alpha tồn tại ở sub-second, scale capacity vượt mid-freq ceiling.
  Horizon: sub-1min ticks
  Stack:   C/Rust hot path, event-driven, tick data, queue model thực sự
  Funded:  bởi mid-freq profits — không build trước khi có capital từ mid-freq

TRANSITION = KHÔNG PHẢI UPGRADE
  Những gì carry over:   T0/T1/T2 methodology, alpha lifecycle, risk philosophy,
                         market state knowledge, institutional knowledge về decay/crowding
  Những gì REBUILD:      data pipeline, backtest engine, feature compute,
                         execution engine, data storage schema
  Timeline:              HFT project bắt đầu khi mid-freq đạt ≥2 live alphas
                         stable ≥6 tháng với Sharpe > 0.8

ANTI-PATTERN CẦN TRÁNH:
  ✗ Optimize latency trong mid-freq Python code
  ✗ Extract C/Rust từ hot path hiện tại
  ✗ Thiết kế mid-freq "để sau này dùng lại cho HFT"
  ✗ Treat Phase 4 như "extension" của Phase 1–3
  → Tất cả những cách trên đều chậm hơn và tốn kém hơn rebuild riêng.

DỮ LIỆU DUY NHẤT cần preserve cho HFT ngay từ bây giờ:
  Raw L2 snapshots phải được lưu song song với aggregated version.
  pre_aggregate_l2.py hủy tick information — không thể reconstruct sau này.
  Storage cost thấp hơn nhiều so với collect lại toàn bộ tick history.
```

---

## Architecture Map

```text
DATA CORE (Layer 1)
  M-D0: Data Lineage Registry          [BUILD PHASE 0 — song song M-D1]
  M-D1: Raw Ingestion (WS + REST)      [ĐÃ BUILD]
  M-D2: Gap Reconciliation             [ĐÃ BUILD ~80%]
  M-D3: PiT Universe Manager          [BUILD PHASE 0]
  M-D4: Feature Cache Offline         [BUILD PHASE 1]

RESEARCH CORE (Layer 2)
  M-R1: Model Training Pipeline       [BUILD PHASE 0 — CRITICAL GAP] (Ridge default)
  M-R2: Leakage Audit                 [BUILD PHASE 0]
  M-R3: T0 Screen                     [BUILD PHASE 0]
  M-R4: T1 Validate                   [BUILD PHASE 0]
  M-R5: T2 Full Diligence             [BUILD PHASE 1]
  M-R6: Vectorized Backtest           [BUILD PHASE 0]
  M-R7: Cost Model                    [BUILD PHASE 0]
  M-R8: Factor Neutralization         [BUILD PHASE 1]
  M-R9: Alpha Registry + Cemetery     [BUILD PHASE 1]
  M-R10: Anomaly Miner                [BUILD PHASE 1]
  M-R11: Market State Engine          [BUILD PHASE 1 — TIER-A] (8-dim state vector, OOD alert)

LIVE CORE (Layer 3)
  M-L1: Paper Trade + Fill Capture    [ĐÃ BUILD ~95%]
  M-L2: Execution Parity Monitor      [BUILD PHASE 2]
  M-L3: Alpha Decay Monitor           [BUILD PHASE 2]
  M-L4: Portfolio Construction (ERC)  [BUILD PHASE 3]
  M-L5: Risk Gate                     [ĐÃ BUILD ~70%]

HFT PREP (Layer 4 — conditional Phase 4)
  M-H1: Event-Driven Simulator
  M-H2: Hot Path Extraction (C/Rust)
```

---

## Build Order Diagram

```text
PHASE 0 (Weeks 1–4): Foundation + First T0 Run
─────────────────────────────────────────────────────────────────────────
[M-D0] (build week 1, parallel)      data lineage registry — foundation for all research
[M-D1] ──→ [M-D2] ──→ [M-D3]        data pipeline: ingest → gap → universe
                           │
                     (features ready)
                           │
[M-R1] ────────────────────┤          Model training pipeline — CRITICAL GAP (Ridge first)
[M-R7] ────────────────────┤          cost model v1 (needed by T0, T1, T2)
[M-R2] ────────────────────┤          leakage audit (gates T1 — build early)
[M-R6] ────────────────────┤          vectorized backtest (needed by T2)
                           ↓
                        [M-R3]        T0 screen — first kill gate (≤15 min)

Build constraints:
  M-D1 → M-D2 → M-D3 (must be sequential)
  M-R1 ∥ M-R7 ∥ M-R2 ∥ M-R6 (can build in parallel)
  M-R3 needs: M-R7 (cost) + M-R1 (ExperimentRecord)

PHASE 1 (Weeks 5–12): First Alpha Full Validation
─────────────────────────────────────────────────────────────────────────
[M-D3] ──→ [M-D4]                     feature cache offline (needs universe)
               │
               ↓
[M-R8] (factor neutralization)
[M-R11] ──────────────────────────── Market State Engine (parallel, feeds M-R4/R7)
               │
               ↓
    [M-R2 PASS required]
               │
               ↓
           [M-R4]                      T1 validate — needs M-R9 at T1.5, M-R11 at T1.3
               │        ↑
           [M-R9]───────┘              alpha registry — build in Phase 1, not deferred
               │
               ↓
    [M-R4 PASS required]
               │
               ↓
[M-R6] ──→ [M-R5]                     T2 full diligence — feeds M-R6 backtest

[M-R10] can be built in parallel (anomaly miner)
[crowding_monitor.py] TIER-A — build in Phase 1 (promoted from TIER-B)

Build constraints:
  M-R2 PASS is hard gate for M-R4 (no bypass)
  M-R9 must exist before M-R4 runs T1.5 correlation check
  M-R4 PASS is hard gate for M-R5 (no bypass)

PHASE 2 (Weeks 13–24): Paper Trade + Research Loop
─────────────────────────────────────────────────────────────────────────
[M-R5 PASS] ──→ [M-L1] ──→ ┬──→ [M-L2]   execution parity monitor
                             └──→ [M-L3]   alpha decay monitor

Research loop runs in parallel:
  [M-R3 → M-R4 → M-R5] × N new hypotheses (Family 1 first)

Family 3 (OB signals) BLOCKED until Family 1/2 fills calibrate adverse selection in M-R7

PHASE 3 (Month 7–9): Portfolio Construction
─────────────────────────────────────────────────────────────────────────
[≥2 live alphas from M-L3] ──→ [M-L4]    ERC portfolio construction
[M-L5] already built — integrate here     risk gate enforced
[signal_attribution.py] build khi có ≥50 paper fills — cần fills để validate attribution vs actual IC

PHASE 4 (Month 10+): HFT — NEW PROJECT (không phải extension của Phase 1–3)
─────────────────────────────────────────────────────────────────────────
[NHẮC LẠI] Đây là rebuild từ đầu, funded bởi mid-freq profits.
           Mid-freq code KHÔNG được reuse. Xem HFT Transition Philosophy.

Prerequisite cứng trước khi start Phase 4:
  ✓ ≥2 live alphas stable ≥6 tháng với live Sharpe > 0.8
  ✓ Capital từ mid-freq đủ fund HFT infrastructure (co-lo, dev time, data)
  ✓ HFT signal edge đã được identify rõ ràng (không phải "làm nhanh hơn mid-freq")

[M-H1] event-driven tick simulator        — research tool cho HFT alpha validation
[M-H2] HFT execution engine (C/Rust)     — new build, không extract từ Python hiện tại

────────────────────────────────────────────────────────────────────────
CRITICAL PATH to first live alpha:

M-D1 → M-D2 → M-D3 → M-D4
    ↓
  M-R1 → [ExperimentRecord] ─┐
  M-R7 → [CostModel]         ├──→ M-R3 → T0 PASS
  M-R2 → [LeakageAudit PASS] ┤
  M-R6 → [BacktestEngine]    └──→ M-R4 → T1 PASS → M-R5 → T2 PASS
                                                              │
                                                             M-L1
                                                         (paper trade)
────────────────────────────────────────────────────────────────────────
```

---

## Minimal Viable Alpha (MVA) Path — 6–8 Tuần Sprint

**Đây là đường ngắn nhất để ra paper trade alpha đầu tiên.** Dùng khi bị tempted làm infra thêm thay vì nghiên cứu.

```text
WEEK 1–2:
  [M-D1] đang 90% → complete gap WS reconnect + funding_rate field
  [M-D2] đang 80% → complete REST gap fill + data_quality flags
  [M-R7] cost model v1 → maker/taker fee + rough adverse selection (no calibration yet)
  [M-R6] vectorized backtest → Polars, single file, no event-driven

WEEK 3:
  [M-R1] ExperimentRecord + labeler (horizon labels, no leakage)
  [M-R3] T0 screen → raw IC + rough cost, ≤15 phút wall time

WEEK 4–5:
  [M-R2] leakage audit → future probe + normalization check
  [M-D3] PiT universe manager (minimum: expanding window + delisting handling)
  FIRST T0 RUN on F001 (funding mean reversion)

WEEK 6–7:
  [M-R4] T1 validate → PurgedKFold + DSR (no M-R8/M-R9 yet — acceptable for first alpha)
  If T1 PASS → M-R5 T2 with stress tests

WEEK 8:
  [M-L1] paper trade already 95% → fix fill capture
  FIRST PAPER TRADE → track IC live

MODULES CAN DEFER past week 8 (without blocking first alpha):
  M-D4 (feature cache)   — load raw features directly, optimize later
  M-R8 (factor neutral)  — run BTC-neutral manually in T1, full module later
  M-R9 (registry)        — spreadsheet substitute for first alpha
  M-R10 (anomaly miner)  — skip entirely until Phase 1
  M-L2 (parity monitor)  — manual check during paper trade
  M-L3 (decay monitor)   — manual IC tracking during paper trade
  M-L4 (ERC)             — simple equal-weight for first portfolio
  M-H1/M-H2 (HFT prep)   — Phase 4, never before first live alpha
```

**Rule:** Nếu task không nằm trên MVA path và chưa có live alpha → BLOCK task đó.

---

---

# LAYER 1: DATA CORE

---

## M-D0: Data Lineage & Dataset Version Governance

**Phase:** Build Phase 0 (song song với M-D1) | **TIER-A** | **Status:** Chưa build

### Purpose

Immutable registry cho mọi dataset artifact. Đảm bảo: (1) mọi research kết quả
reproducible bằng cách trace về exact data version; (2) forensic debugging khi
live PnL diverge với backtest; (3) phát hiện retroactive data corruption.

Đây là gap lớn nhất ảnh hưởng đến auditability. Không có M-D0:
- Impossible trace tại sao backtest khác live 3 tháng sau.
- Impossible prove không có hindsight nếu feature recomputed retroactively.
- Impossible reproduce exact live decisions nếu cần kiểm tra.

### DatasetRecord Schema

```text
@dataclass(frozen=True)
class DatasetRecord:
  dataset_id:       str     — UUID
  name:             str     — "ohlcv_binance_btcusdt_2024"
  version:          int     — monotonically increasing
  created_at:       datetime
  data_hash_sha256: str     — SHA-256 của raw Parquet bytes (không schema, chỉ data)
  row_count:        int
  date_range:       tuple[date, date]
  exchange:         str
  symbol:           str | None
  derivation_type:  str     — "raw" | "gap_filled" | "feature_cache" | "label"
  derived_from:     tuple[str, ...]  — list[dataset_id] của parent datasets
  feature_logic_hash: str | None    — hash của feature function source code (nếu derived)
```

### As-Of Snapshot Policy

```text
Vấn đề: nếu feature recomputed trên cleaned dataset AFTER gap reconciliation,
historical feature values có thể thay đổi retroactively → hindsight bias.

Rule cứng: mỗi lần feature computation chạy → snapshot dataset_id được lock.
Backtest phải specify dataset_id, không "latest" hoặc "current".

as_of_feature_snapshot(date) → dataset_id:
  Returns dataset_id của feature cache TẠI thời điểm date đó.
  Nếu không có snapshot → FAIL (không được dùng interpolation).

Immutability: một dataset_id không bao giờ được overwrite.
  Update = new dataset_id với derived_from pointing to old.
```

### Feature Lineage DAG

```text
Mỗi feature trong feature_cache phải có lineage entry:
  funding_rate_zscore_30d:
    derived_from: [ohlcv_binance_v3, funding_binance_v2]
    feature_logic_hash: abc123
    normalization: "expanding_window"
    pit_safe: True

Lineage DAG cho phép:
  1. Detect nếu normalization window thay đổi (hash mismatch)
  2. Recompute từ raw nếu feature logic bug được phát hiện
  3. Audit: feature tại bar T chỉ dùng data ≤ T (PiT assertion)
```

### Invariants

```text
[INV-D0.1] dataset_id immutable sau creation — không được delete hoặc modify
[INV-D0.2] Backtest phải log dataset_id_used — không được dùng "current data"
[INV-D0.3] Nếu dataset_id_in_backtest ≠ dataset_id_in_live → ALERT (divergence)
[INV-D0.4] Feature logic hash mismatch → kết quả backtest không compare được
[INV-D0.5] as_of_snapshot phải tồn tại cho mọi research backtest date range
```

### Tests

```text
[T-D0.1] Tạo dataset → hash stable (bit-identical sau 2 lần compute)
[T-D0.2] Thay đổi 1 row → hash mới → new dataset_id created
[T-D0.3] as_of_feature_snapshot(2024-01-15) → trả về dataset_id từ 2024-01-15
[T-D0.4] Backtest không specify dataset_id → FAIL với explicit error
[T-D0.5] Feature logic thay đổi → feature_logic_hash mới → old backtest không invalidated
```

### Depends on

Không phụ thuộc module nào (foundational)

### Provides to

Tất cả modules trong Research Core (via dataset_id tracking)

---

## M-D1: Raw Data Ingestion

**Phase:** Đã build | **TIER-A** | **Status:** 90% complete

### Purpose

Thu thập raw market data từ 3 exchanges qua WebSocket + REST. Lưu immutable Parquet. Không transform, không aggregate tại tầng này.

### Input / Output

```text
INPUT:  Exchange WebSocket streams, REST endpoints
OUTPUT: ho_du_lieu/tho/{exchange}/{symbol}/year={Y}/month={M}/data.parquet

Schema (mandatory fields):
  event_time_ns:  int64   — exchange timestamp, nanoseconds
  recv_time_ns:   int64   — local receive timestamp
  open, high, low, close: float64
  volume:         float64 — quote volume (USDT)
  trades:         int32   — trade count per bar
  funding_rate:   float64 — null if not settlement bar
  oi_usdt:        float64 — open interest in USDT
```

### Invariants

```text
[INV-D1.1] event_time_ns strictly monotonic per (exchange, symbol)
[INV-D1.2] No forward-fill on raw OHLCV — missing bars = null
[INV-D1.3] recv_time_ns >= event_time_ns (cannot receive before event)
[INV-D1.4] Parquet files immutable after write (append-only via new partition)
[INV-D1.5] funding_rate non-null only at settlement bars (00:00, 08:00, 16:00 UTC for Binance)
[INV-D1.6] Bar boundary assignment rule (explicit — không để implicit):
             bar_start_ns <= event_time_ns < bar_end_ns   ← left-inclusive, right-exclusive
             Ví dụ: bar "01:00 UTC" chứa events [01:00:00.000, 01:59:59.999]
             Event tại exactly 02:00:00.000 thuộc bar "02:00", không phải "01:00"
             Áp dụng cho: OHLCV aggregation, funding alignment, feature timestamp join
             Test: funding message arrives 00:00:00.003 UTC → thuộc bar 00:00, không 23:00
```

### Parameters

```text
[PUBLISHED] Binance funding settlement: 00:00, 08:00, 16:00 UTC
[PUBLISHED] Bybit funding settlement: 00:00, 08:00, 16:00 UTC
[PUBLISHED] OKX funding settlement: 00:00, 08:00, 16:00 UTC
[ESTIMATED] Max acceptable clock drift: 500ms
[ASSUMED]   WS reconnect backoff: exponential 1s → 60s
```

### Failure Modes

- WS disconnect không reconnect → gap không được flag → data loss silent
- Exchange maintenance window (Bybit hay maintenance) → correlated gap với market condition
- event_time_ns batching: một số exchanges gửi events theo batch với same timestamp
- Symbol remapping: exchange đổi tên perpetual contract (ví dụ DEFI-PERP → DEFIUSDT) → file path cũ không match, data bị miss silently → feature pipeline nhận NaN
- Rate limit ban: subscription quá nhiều channel quá nhanh → exchange temp-ban WS connection → silent gap trong window bị ban, không có error log
- Mark/index price mismatch: mark price (dùng funding/liquidation) khác index price (dùng signal) → dùng nhầm loại tạo ra alpha artifact trong backtest không tồn tại ngoài live
- Schema drift: exchange thay đổi field name hoặc thêm field mới mà không notify → parser cũ bỏ qua field, write null vào Parquet → downstream feature compute sai lặng lẽ. Mitigation: validate schema hash sau mỗi session
- Timezone mismatch: exchange timestamp là UTC nhưng local clock chạy local timezone → bar alignment sai, look-ahead leak trong short-horizon features. Rule cứng: mọi timestamp trong pipeline phải là UTC nanoseconds, không exception
- Parquet corruption: disk full hoặc crash giữa write → corrupt Parquet không readable → downstream fail với obscure error. Mitigation: write-to-temp rồi atomic rename, verify file sau write

### Tests

```text
[T-D1.1] 48h continuous run, 0 silent gaps (gaps phải được logged)
[T-D1.2] funding_rate null ở non-settlement bars
[T-D1.3] recv_time_ns - event_time_ns < 2000ms (99th percentile)
[T-D1.4] Không có duplicate (exchange, symbol, event_time_ns)
[T-D1.5] Sau WS reconnect, data tiếp tục không bị duplicate
```

### Provides to

M-D2 (gap reconciliation), M-D3 (universe manager)

---

## M-D2: Gap Reconciliation

**Phase:** Build Phase 0 | **TIER-A** | **Status:** 80% complete

### Purpose

Phát hiện và đánh dấu gaps trong data stream. Dùng REST để fill gaps có thể fill được. Mark gaps không thể fill để downstream biết tránh.

**Rule cứng:** Không interpolate. Không forward-fill OHLCV. Gap = null hoặc flag.

### Input / Output

```text
INPUT:  ho_du_lieu/tho/ (raw Parquet từ M-D1)
        REST API endpoints (3 exchanges)

OUTPUT: ho_du_lieu/da_xu_ly/{exchange}/{symbol}/year={Y}/month={M}/data.parquet

Thêm fields:
  is_gap_filled:  bool    — bar được fill từ REST (không phải WS)
  gap_duration_s: float32 — null nếu không phải gap boundary
  data_quality:   int8    — 0=perfect, 1=rest_filled, 2=suspect, 3=missing
```

### Logic

```text
Nightly reconciliation (sau 02:00 UTC):
  1. Scan symbol/date → tìm missing bars (expected vs actual count)
  2. Nếu gap ≤ 3 bars và REST available → fill từ REST, mark is_gap_filled=True
  3. Nếu gap > 3 bars → mark data_quality=3, KHÔNG fill
  4. Nếu REST data inconsistent với WS boundary → mark data_quality=2

Exchange clock audit (daily):
  - Compute mean(recv_time_ns - event_time_ns) per exchange per hour
  - Alert nếu drift > 500ms systematically
  - Log drift series (cần cho PiT alignment downstream)
```

### Invariants

```text
[INV-D2.1] is_gap_filled=True iff data đến từ REST, không phải WS
[INV-D2.2] Không có bars với data_quality=3 được dùng trong IC calculation
[INV-D2.3] Bars REST-filled không được dùng cho short-horizon features (≤5min)
[INV-D2.4] Gap report được tạo mỗi ngày, chứa: symbol, gap_start, gap_end, fill_status
```

### Parameters

```text
[ESTIMATED] max_fillable_gap_bars: 3    — hơn 3 bars REST data không tin cậy
[ESTIMATED] min_daily_coverage: 95%     — dưới này flag symbol
[ESTIMATED] max_clock_drift_ms: 500     — hơn này alert
[ASSUMED]   REST rate limit buffer: 20% — không dùng hết rate limit
```

### Failure Modes

- REST rate limit bị hit → gap fill timeout, gap không được đánh dấu
- Exchange maintenance gap > 3 bars → mark missing, downstream phải loại
- REST trả data khác WS (exchange bug) → data_quality=2 catch được

### Tests

```text
[T-D2.1] Inject synthetic 1-bar gap → is_gap_filled=True sau reconciliation
[T-D2.2] Inject 5-bar gap → data_quality=3, không filled
[T-D2.3] Bars data_quality=3 không xuất hiện trong feature computation
[T-D2.4] Gap report generated daily at 02:30 UTC
[T-D2.5] Alert gửi khi coverage < 95% cho bất kỳ symbol nào
```

### Depends on

M-D1 (raw Parquet)

### Provides to

M-D3 (universe manager), M-D4 (feature cache), M-R2 (leakage audit)

---

## M-D3: PiT Universe Manager

**Phase:** Build Phase 0 | **TIER-A** | **Status:** Chưa build

### Purpose

Quản lý lịch sử universe theo Point-in-Time. Đảm bảo research không dùng hindsight khi chọn symbols.

**Đây là anti-survivorship-bias module quan trọng nhất.**

### Input / Output

```text
INPUT:  ho_du_lieu/da_xu_ly/ (cleaned data)
        Exchange listing/delisting event logs

OUTPUT: ho_du_lieu/lich_su_vu_tru/{snapshot_date}.parquet

Schema:
  asset_id:         str       — UUID v4, immutable per listing event (KHÔNG phải symbol string)
  symbol:           str       — display ticker (có thể reuse: LUNA → LUNC → LUNA2)
  listing_date:     date
  delisting_date:   date | null
  adv_usdt_30d:     float64   — ADV tính đến ngày snapshot_date - 1 (lagged, không dùng same-day)
  in_universe:      bool      — True nếu đủ điều kiện tại snapshot_date
  exclusion_reason: str | null
```

**[CRITICAL] Ticker Collision — Crypto Survivorship Bias Ẩn:**

```text
Vấn đề: Crypto exchanges tái sử dụng ticker symbols.
Ví dụ lịch sử:
  LUNA (cũ, sụp đổ 2022-05-13) → LUNC
  LUNA (mới, ra đời 2022-05-28) → LUNA
  BTT (cũ) → BTTC
  FTT (FTX token, delist 2022-11-08) → nhiều exchanges delist, sau list lại

Nếu map theo string symbol, backtest sẽ:
  - Nối nhầm price series của coin cũ và coin mới
  - Tạo jump giá khổng lồ hoặc look-ahead bias tại thời điểm đổi tên

Giải pháp: asset_id = UUID v4 gắn với từng LISTING EVENT, không phải symbol string.
  Khi exchange list một coin mới (kể cả cùng ticker) → new asset_id.
  symbol_remapper.py (M-D1) phải map exchange_internal_id → asset_id.
  Tất cả joins downstream (features, signals, returns) phải dùng asset_id.
```

### Invariants

```text
[INV-D3.1] get_universe(date) chỉ dùng thông tin có trước date đó
[INV-D3.2] Symbol chỉ vào universe sau min_listing_days kể từ listing_date
[INV-D3.3] Delisted symbols KHÔNG bị xóa khỏi historical universe
            → delisting_date được set, in_universe=False sau đó
[INV-D3.4] Delisting return: nếu không có exit price → mark return = -100%
            (không drop row, không NaN, không 0)
[INV-D3.5] ADV = mean(daily_volume, window=[t-31, t-1]) — lagged 1 ngày.
            KHÔNG dùng volume của ngày t để xác định eligibility tại t.
[INV-D3.6] asset_id KHÔNG bao giờ thay đổi sau khi gán.
            Nếu exchange đổi tên contract → symbol field update, asset_id giữ nguyên.
[INV-D3.7] Mọi join downstream (M-D4, M-R3, M-R6) phải join ON asset_id,
            không join ON symbol (symbol có thể trùng giữa 2 listing events).
[INV-D3.8] Sau đổi tên ticker: cả old_symbol VÀ new_symbol phải được track
            trong symbol_history field, không chỉ current symbol.
```

### Parameters

```text
[ESTIMATED] min_listing_days: 90        — tránh listing pump bias
[ESTIMATED] min_adv_usdt: 5_000_000    — $5M daily volume tối thiểu
[ASSUMED]   adv_lookback_days: 30       — rolling window tính ADV (lagged)
[ASSUMED]   sector_map: L1, L2, DeFi, Meme, RWA, AI (manual, update quarterly)
```

### Logic: Delisting Handling

```text
Khi symbol bị delist:
  1. Ngày cuối cùng có data → set final_return = (last_price - entry_price) / entry_price
  2. Nếu không có last_price (exchange halt) → final_return = -1.0 (-100%)
  3. delisting_date = ngày cuối có data
  4. in_universe = False cho mọi snapshot sau delisting_date
  5. Không xóa rows → historical research vẫn include symbol này
```

### Tests

```text
[T-D3.1] Luna UST (2022-05-09): in_universe=False sau 2022-05-13, final_return=-1.0
[T-D3.2] get_universe(2023-01-01) không include symbols listed sau 2023-01-01
[T-D3.3] Symbol mới listed → chỉ in_universe sau min_listing_days
[T-D3.4] Historical universe count: 2022 có khác 2024 (không static)
[T-D3.5] Pit audit: không có symbol trong universe trước listing_date của nó
```

### Depends on

M-D2 (cleaned data)

### Provides to

M-R2 (leakage audit), M-R6 (vectorized backtest), M-R7 (cost model)

---

## M-D4: Feature Cache (Offline)

**Phase:** Build Phase 1 | **TIER-A** | **Status:** Chưa build | **MVA:** DEFER — load raw features trực tiếp cho first alpha, optimize sau

### Purpose

Pre-compute và cache feature matrices cho research. Tránh recompute 50 lần cho 50 hypotheses. Cache invalidated by feature hash khi logic thay đổi.

### Input / Output

```text
INPUT:  ho_du_lieu/da_xu_ly/ (cleaned OHLCV, funding, OI)
        Feature definitions (function + params)

OUTPUT: ho_du_lieu/kho_dac_trung/offline/{feature_set_hash}/
          {symbol}_{start}_{end}.parquet

Schema (mỗi row = 1 bar):
  timestamp:                  datetime[ns, UTC]
  symbol:                     str
  funding_rate_8h:            float64   — raw funding, settlement-aligned
  funding_rate_zscore_30d:    float64   — expanding window z-score
  oi_change_pct_1h:           float64   — % OI change vs 1h ago
  oi_change_pct_4h:           float64
  perp_spot_basis_bps:        float64   — (perp - spot) / spot × 10000
  return_1h:                  float64   — raw 1h return
  return_4h:                  float64
  return_1h_btc_neutral:      float64   — residual sau rolling OLS vs BTC
  return_4h_btc_neutral:      float64
  volume_ratio_24h:           float64   — symbol vol / mean(universe vol)
  book_pressure_5min:         float64   — OFI aggregated 5-min
  spread_bps:                 float64   — bid-ask spread in bps
```

### Invariants

```text
[INV-D4.1] Tất cả z-score dùng expanding window (PiT-safe), không full-sample
[INV-D4.2] funding_rate chỉ non-null tại settlement bars
[INV-D4.3] btc_neutral features dùng rolling OLS 21-day (không full-sample beta)
[INV-D4.4] Cache hash = hash(feature_function_source + params + data_version)
[INV-D4.5] Khi feature logic thay đổi → hash mới → recompute tự động
[INV-D4.6] Bars với data_quality=3 → features = NaN (không compute)
[INV-D4.7] Expanding z-score trả về NaN cho tất cả bars trong min_periods đầu tiên.
            Không interpolate, không forward-fill, không dùng rolling mean thay thế.
[INV-D4.8] Mọi join với universe history phải dùng asset_id (không symbol string).

[INV-D4.9] OI data source PHẢI declared trong feature lineage (M-D0 DatasetRecord):
            oi_source field bắt buộc có giá trị: "binance_native" | "bybit_native" | "coinglass_agg".
            Feature lineage thiếu oi_source → DatasetRecord rejected.
[INV-D4.10] Live và backtest PHẢI dùng cùng OI source:
             Binance native API ≠ Coinglass aggregated (Coinglass có delay và normalization khác).
             Dùng nhầm source → systematic feature drift từ ngày 1 (OI level khác ~5–15%).
             Verify bởi M-L2 daily parity check.
[INV-D4.11] Coinglass aggregated OI KHÔNG được dùng cho features với horizon < 30 phút:
             Coinglass có aggregate delay 15–20 phút vs exchange native endpoint.
             Dùng exchange native OI (REST) cho bất kỳ feature sub-30min nào.
[INV-D4.12] Funding interpolation method PHẢI declared trong feature lineage:
             Funding rate chỉ settled mỗi 8 giờ — giữa settlements, funding_rate = null.
             Nếu feature cần funding_rate tại non-settlement bars → declare method:
               "carry_forward": forward-fill settlement rate đến settlement tiếp theo (PiT-safe)
               "null": chỉ dùng settlement bars (restrict signal đến bars funding_rate non-null)
               "linear": KHÔNG khuyến nghị — interpolate tuyến tính predict future settlement
             Default nếu không declare: "carry_forward".
             Live và backtest phải dùng cùng method (verified bởi M-L2).
[INV-D4.13] Feature parity — live compute PHẢI import từ cùng module với batch:
             KHÔNG rewrite feature logic trong live pipeline (copy-paste = silent divergence).
             Enforce: single function definition trong feature_registry.py,
             imported bởi cả M-D4 batch pipeline VÀ live IncrementalFeatureEngine.
             Test T-D4.6 (feature parity 1e-6) là test contract của invariant này.
[INV-D4.14] Cold start signal = NaN (không phải 0):
             Symbol vừa pass min_listing_days nhưng chưa có đủ feature history (< min_periods bars).
             feature = NaN → signal = NaN → position = 0.
             NaN KHÔNG được convert thành 0 tại signal layer hoặc feature layer.
             Convert NaN → 0 chỉ tại position sizing layer (sau khi signal đã validated).
             Lý do: signal = 0 trên NaN feature vẫn generate exit trade từ non-existent position
             → systematic noise + cost trong early bars của newly-listed symbols.
```

### Schema Evolution Strategy

```text
[PROBLEM] Thêm column mới vào Parquet schema sau khi data đã được viết:
  - Old Parquet files thiếu column mới
  - Code assume column exists → silent NaN hoặc KeyError → pipeline fail không rõ lý do
  - Xảy ra khi: thêm feature mới, thêm field audit, schema cleanup

[SOLUTION — Versioned Schema Policy]:

Schema version field: mọi Parquet dataset trong ho_du_lieu/ phải có:
  schema_version: int8    — monotonically increasing, default 1

schema_validator.py tracks:
  SCHEMA_REGISTRY = {
    "da_xu_ly":   {1: [...baseline_columns...], 2: [...+borrow_rate...]},
    "kho_dac_trung": {1: [...], 2: [...+book_pressure_5min...]},
  }

Khi thêm column mới (schema upgrade):
  1. Tăng version: SCHEMA_VERSION = 2 trong schema_validator.py
  2. Old files (v1): read_with_default(new_col, default=NaN) — không fail
  3. New files: write với version=2, new_col populated
  4. Migration flag: mark dataset_id mới trong M-D0 (derived_from = old dataset_id)
     KHÔNG rewrite old Parquet files — immutability rule (INV-D1.4)

Backward compatibility rule:
  - v1 files đọc bởi v2 code → missing columns = NaN (không crash)
  - v2 files đọc bởi v1 code → extra columns ignored (Parquet đảm bảo)
  - Code phải dùng .get(col, default=NaN) hoặc try/except KeyError khi read optional columns
  - Columns bắt buộc (required): crash nếu thiếu → detect ngay, không silent fail

Schema diff logging (trong schema_validator.py):
  Sau mỗi write session, log: {dataset, schema_version, added_cols, removed_cols}
  Alert nếu: schema thay đổi mà KHÔNG có version bump
    → Có thể là exchange API thay đổi field name (Gap Failure Mode M-D1)

[INV-D4.15] Mọi Parquet file trong ho_du_lieu/ phải có schema_version field
[INV-D4.16] Code không được hardcode column index — dùng column name access
[INV-D4.17] Required columns: crash fast nếu thiếu; Optional columns: NaN nếu thiếu
[INV-D4.18] Mọi feature trong M-D4 cache phải có FeatureSpec entry trước khi được dùng trong T0/T1/T2.
```

### FeatureSpec Contract

```python
@dataclass(frozen=True)
class FeatureSpec:
    name: str                    # "funding_z_30d"
    inputs: list[str]            # ["funding_rate"]
    frequency: str               # "1h" | "4h"
    min_history_bars: int        # minimum bars trước khi output valid
    pit_safe: bool               # True = expanding window, False = cần review
    live_ready: bool             # True = có thể dùng trong live engine
    normalization: str           # "expanding_z" | "carry_forward" | "none"
    description: str             # ngắn gọn
```

```text
File: nghien_cuu/khung_alpha/feature_spec.py   [new, Phase 1]
      Cùng folder với alpha_contract.py.
      Mọi feature được dùng trong T0/T1/T2 phải có FeatureSpec entry đăng ký tại đây.
      pit_safe=True → verified expanding window, không full-sample normalization.
      live_ready=True → đã có live compute path trong IncrementalFeatureEngine (INV-D4.13).
```

### Expanding Window Normalization + Burn-in Period

```text
ĐÚNG (PiT-safe):
  z = (x - expanding_mean) / expanding_std
  min_periods = 252 bars (1h bars) hoặc 63 bars (4h bars)  ← cứng, không tunable
  Output = NaN cho tất cả bars t < min_periods

SAI (look-ahead leak):
  z = (x - x.mean()) / x.std()  ← NEVER dùng trong research

SAI (noise signal):
  min_periods quá nhỏ (< 21) → variance rất cao tại early bars
  → IC artificially inflated trên "warm-up" period khi sample nhỏ

[CRITICAL — Burn-in Invariant]:
  Nghiên cứu IC chỉ được tính từ bar min_periods trở đi (sau khi expanding window
  có đủ sample). Nếu universe của một symbol không có đủ min_periods history
  trong training window → exclude symbol đó khỏi IC calculation, không impute.
```

### T0 On-the-fly Feature Compute (Subset Mode)

```text
Mục đích: cho phép T0 screen feature mới TRƯỚC KHI commit vào M-D4 batch cache.

Khi nào dùng subset mode:
  - Feature mới chưa có trong M-D4 cache (idea vừa nghĩ ra)
  - Chỉ cần pass/kill decision nhanh (≤15 phút SLA)

Subset mode config:
  symbols:     top-10 liquid (BTC, ETH, BNB, SOL, AVAX, ARB, OP, MATIC, ATOM, LINK)
  period:      last 6 months (không phải full 2 năm)
  compute:     on-the-fly từ ho_du_lieu/da_xu_ly/ (không cần M-D4)

Quy tắc:
  Nếu T0 PASS với subset mode → commit feature vào M-D4 batch → chạy T1/T2 trên full sample
  Nếu T0 KILL với subset mode → kill ngay, không tốn M-D4 compute
  IC từ subset mode không được dùng trong T1/T2 (khác sample)
```

### Tests

```text
[T-D4.1] Recompute với same data → bit-identical output (deterministic)
[T-D4.2] funding_rate_zscore tại bar T chỉ dùng data ≤ T
[T-D4.3] btc_neutral_return tại bar T chỉ dùng BTC returns ≤ T
[T-D4.4] Thay đổi feature_function → hash mới, recompute triggered
[T-D4.5] Bars data_quality=3 → tất cả features = NaN
[T-D4.6] Feature parity: batch compute == live compute (tolerance 1e-6)
```

### Depends on

M-D2 (cleaned data), M-D3 (universe — để biết symbols valid)

### Provides to

M-R3 (T0 screen), M-R4 (T1 validate), M-R5 (T2 diligence), M-R6 (backtest)

---

---

# LAYER 2: RESEARCH CORE

---

## M-R1: Model Training Pipeline

**Phase:** Build Phase 0 — **CRITICAL GAP** | **TIER-A**

**[NOTE] Tại sao "CRITICAL GAP"?** Gap không phải là "thiếu ML". Gap là thiếu infrastructure để chạy *bất kỳ model nào* (kể cả Ridge 5 dòng) một cách có PiT hygiene, reproducibility lock, và versioned artifact. Không có module này → không thể validate bất kỳ hypothesis nào đúng cách.

**Default model là Ridge Regression.** LightGBM chỉ justify khi Ridge PASS và có nonlinearity evidence. Xem "Why ML?" section bên dưới.

### Purpose

Pipeline hoàn chỉnh từ raw features → trained model → versioned artifact. Module này là prerequisite của mọi thứ trong Research Core.

### Files

```text
hoc_may/huan_luyen/
  labeler.py        — tạo forward return labels
  purged_cv.py      — PurgedKFold cross-validation
  dsr.py            — Deflated Sharpe Ratio
  trainer.py        — model training (Ridge first)
  model_registry.py — versioned model storage
```

### Sub-module: Labeler

```text
INPUT:  feature matrix (Polars DataFrame), horizon_minutes, cost_bps
OUTPUT: label series (forward return net of cost)

Key rules:
  - label[t] = btc_neutral_return(t, t+horizon) - round_trip_cost_bps/10000
  - btc_neutral_return = raw_return(t, t+horizon) - beta_btc[t] × btc_return(t, t+horizon)
    beta_btc[t] từ rolling OLS 21-day tại t (không full-sample)
  - [CRITICAL] Nếu signal là BTC-neutral thì label PHẢI BTC-neutral.
    Dùng raw label với BTC-neutral signal → IC đo lường unconditional return,
    không phải alpha. Inconsistency này làm thổi phồng IC giả.
  - Không được dùng prices sau t+horizon để tính label tại t
  - Bars data_quality > 1 → label = NaN
  - Bars trong funding_blackout (60min trước settlement với size > $50K,
    30min với size ≤ $50K) → label = NaN
  - Không ffill labels

Parameters:
  [ESTIMATED] horizon_minutes: 60 (Family 1), 240 (Family 2) — tune per hypothesis
  [ESTIMATED] cost_bps: 10 (maker BTC) to 20 (taker alts) — from M-R7
```

### Sub-module: PurgedKFold

```text
Implement PurgedKFold từ Lopez de Prado "Advances in Financial ML":
  - n_splits: 5
  - embargo_days: 21  [ESTIMATED — 1 month lag cho mid-freq]
  - purge: loại training samples có label overlapping với test period
  - embargo: loại thêm embargo_days sau test period

Output per fold:
  - train_idx, test_idx (purged + embargoed)
  - effective_sample_size (sau purging)
  - warn nếu effective_n < 500

[NOTE] Không implement CPCV trong Phase 0-2. PurgedKFold đủ.
CPCV chỉ khi có ≥1 live alpha và cần tighter overfit bounds.
```

### Sub-module: DSR (Deflated Sharpe Ratio)

```text
Implement Bailey & Lopez de Prado (2014) DSR:

dsr(SR, T, skew, kurt, n_trials) → float

Inputs:
  SR:       observed Sharpe ratio
  T:        number of observations
  skew:     return skewness
  kurt:     return excess kurtosis
  n_trials: số lần đã thử (multiple testing correction)

Output:
  DSR: probability that SR > 0 after correcting for:
    - Non-normality (skew, kurt)
    - Multiple testing (n_trials)
    - Finite sample (T)

Threshold: DSR > 0.5 → signal likely non-noise
Kill nếu: DSR < 0.5 tại T1

[ESTIMATED] n_trials tracking — PHẢI honest, đây là nơi quants thường cheat nhất:

  Mỗi action dưới đây là +1 trial (hidden data snooping):
    +1  Chạy IC với feature mới (kể cả feature "rõ ràng")
    +1  Đổi horizon (từ 1h sang 4h → +1, không phải cùng 1 idea)
    +1  Thay đổi normalization (zscore khác window → +1)
    +1  Thêm/bỏ filter (sector, market cap, listing age)
    +1  Retry sau khi xem kết quả và "tune" threshold
    +0  Chạy lại y chang với different random seed (không count)
    +0  Fix code bug rõ ràng → không count nếu result direction không thay đổi

  Rule thực tế:
    Mỗi lần bạn xem kết quả rồi quyết định thay đổi gì đó → n_trials += 1
    "Tôi chỉ thử thêm 1 feature" là câu cổ điển nhất để undercount n_trials

  Nếu không chắc → làm tròn lên. DSR conservative tốt hơn DSR overconfident.

  Reset: chỉ reset khi có independent holdout set hoàn toàn mới (khác time period).
  Không reset chỉ vì đổi family — nếu dùng cùng data để khám phá.

  [CRITICAL] n_trials phải track CROSS-FAMILY, không chỉ per-family:
    Nếu test F001 10 lần + M001 5 lần trên cùng data window →
    n_trials_total = 15 cho DSR của cả hai, không phải 10 và 5 riêng biệt.

    ExperimentRecord fields cần cả hai:
      n_trials_family:   int  — số lần thử trong cùng alpha family
      n_trials_total:    int  — tổng số lần thử trên cùng data window (mọi family)
      config_hash:       str  — SHA-256 của {feature_list + horizons + normalization + filters}
                               được compute tự động khi ExperimentRecord created

    DSR phải dùng n_trials_total, không n_trials_family.
    n_trials_family chỉ dùng cho internal family kill rate tracking (M-R9).

    [AUTOMATED n_trials TRACKING — chống undercount]:
    Vấn đề: manual tracking dẫn đến undercount có chủ ý hoặc vô tình.
    Fix: n_trials được track bằng config_hash, không phải ý chí của researcher.

    Rule tự động:
      Mỗi ExperimentRecord → compute config_hash từ:
        hash(sorted(feature_list) + str(horizons) + str(norm_method) + str(filters))
      
      Nếu config_hash đã tồn tại trong experiment log (cùng data_window):
        → n_trials KHÔNG tăng (chạy lại y chang = không count)
      
      Nếu config_hash mới (bất kỳ thay đổi nào):
        → n_trials_total += 1 (tự động, không cần researcher nhớ)
        → log: {old_config_hash, new_config_hash, change_summary, timestamp}
      
      n_trials_total không bao giờ giảm trong cùng một data window.
      Reset chỉ khi holdout period mới hoàn toàn.

    ExperimentRecord bị REJECT nếu không có config_hash field.
    Trainer.fit() bị BLOCK nếu ExperimentRecord chưa được saved với config_hash.
```

### Why ML? — Decision Framework

```text
Câu hỏi quan trọng trước khi build ML pipeline: "liệu ML có add value vs linear?"

Crypto perp mid-freq thường không cần ML phức tạp vì:
  - Alpha decay nhanh (< 3 tháng) → ít data để fit complex model
  - Signal-to-noise thấp → overfitting risk cao với nonlinear models
  - Linear factors (funding rate, OI rank, momentum) thường sufficient

Khi nào ML justified:
  1. Ridge PASS T2 với IC stable → test nếu LGBM adds > 15% IC OOS
  2. Feature interaction có economic basis rõ ràng (không phải curve-fit)
  3. Có > 2 năm data sạch, > 20 symbols, signal halflife > rebalance_freq × 5

Khi nào KHÔNG dùng ML:
  - Hypothesis chưa pass Ridge (nếu linear không work, ML sẽ overfit)
  - Feature count < 5 (linear là optimal)
  - Crypto black swan events dominant → model sẽ memorize them

Default: Ridge → nếu IC plateau và economic mechanism suggest interactions → LGBM
```

### Sub-module: Trainer

```text
Phase 0-2: Ridge Regression ONLY
  model = Ridge(alpha=1.0)
  cv_result = PurgedKFold.cross_val_score(model, X, y)
  Output: mean_cv_ic, std_cv_ic, model

Phase 3+: LightGBM (chỉ sau khi có live alpha với Ridge)
  Điều kiện cứng: OOS IC gain > 15% vs Ridge trên same holdout
  Lý do giữ Ridge trước: interpretability > performance ở giai đoạn discovery

Cross-validate IC (không MSE):
  cv_ic = [spearman(y_pred_fold_k, y_true_fold_k) for k in folds]
  mean_cv_ic, std_cv_ic
```

### Sub-module: Model Registry

```text
hoc_may/huan_luyen/model_registry.py

save_model(model, feature_list, cv_metrics, experiment_id) → model_id
  model_id format: {date}_{experiment_hash[:6]}_ic{mean_cv_ic:.3f}
  Lưu: model artifact, feature_list, cv_metrics, training_data_hash, timestamp

load_model(model_id) → (model, metadata)

ExperimentRecord (pre-registered TRƯỚC khi chạy backtest):
  Fields:
    experiment_id:    str       — UUID
    hypothesis:       str       — viết trước khi test
    null_hypothesis:  str       — viết trước khi test
    alpha_family:     str       — F, M, OB
    feature_list:     list[str]
    label_horizon:    int       — minutes
    label_cost_bps:   float
    cv_folds:         int
    embargo_days:     int
    n_trials_family:  int       — số lần đã test trong family này
    n_trials_total:   int       — tổng số lần thử trên cùng data window (cross-family)
    config_hash:      str       — SHA-256 của {feature_list + horizons + norm + filters}
                                  auto-computed khi ExperimentRecord created
    data_window:      str       — "YYYY-MM-DD/YYYY-MM-DD" — dùng để group n_trials_total
    created_at:       datetime

Rule cứng: ExperimentRecord phải được saved TRƯỚC khi chạy model.
Hypothesis không được thay đổi sau khi thấy kết quả.
Trainer.fit() bị BLOCK nếu ExperimentRecord thiếu config_hash hoặc n_trials_total.
```

### Tests

```text
[T-R1.1] Label[t] không dùng data sau t+horizon (future probe test)
[T-R1.2] PurgedKFold: không có overlap giữa train và test labels
[T-R1.3] DSR reference check: compute DSR của known SR=1.5, T=252, n_trials=1 → so với paper
[T-R1.4] Model registry: load(save(model)) → identical predictions
[T-R1.5] ExperimentRecord required trước khi trainer.fit() → fail nếu không có
```

### Provides to

M-R3 (T0), M-R4 (T1), M-R5 (T2), M-L1 (paper trade signal)

---

## M-R2: Leakage Audit

**Phase:** Build Phase 0 | **TIER-A**

### Purpose

Systematic check tất cả potential leakage trước khi T1 được phép chạy. Module này là gatekeeper — T1 phải wait for PASS.

### Input / Output

```text
INPUT:  signal DataFrame, feature DataFrame, universe history
OUTPUT: AuditResult(passed: bool, checks: list[CheckResult], report: str)
```

### Audit Checks (tất cả phải PASS)

```text
[AUDIT-1] Future Probe Test
  - Compute IC giữa feature tại t và random noise tại t+1
  - Nếu IC > 0.01 → signal của "feature" bị leak
  - Method: shuffle labels nhiều lần, check nếu IC consistently cao

[AUDIT-2] Normalization PiT Check
  - Verify expanding window, không full-sample
  - Test: z-score tại bar T chỉ dùng data [0, T]
  - Detect: recompute bar T với extended data, check nếu z-score thay đổi

[AUDIT-3] Universe PiT Check
  - Verify không có symbol trong signal mà không in_universe tại timestamp đó
  - JOIN signal với universe_history → flag mismatches

[AUDIT-4] Funding Alignment Check
  - Verify funding_rate features chỉ dùng settled rates (không predicted)
  - Check: funding_rate[t] chỉ non-null tại settlement timestamps
  - Check: không có funding data từ "next expected rate" API endpoints

[AUDIT-5] No ffill OHLCV Check
  - Scan raw feature DataFrame: không có runs of identical OHLCV values
  - Exception: volume=0 bars là OK (market closed / no trades)

[AUDIT-6] Delisted Symbols Check
  - Verify delisted symbols vẫn có trong signal với final_return != NaN
  - Verify không có delisted symbols với return=0 (should be -100% nếu không có exit)

[AUDIT-7] Listing Cohort Filter
  - Momentum hypothesis (M family): exclude symbols listed < 30 ngày
  - Lý do: newly listed coins có return patterns hoàn toàn khác
  - Filter phải applied TRƯỚC khi compute IC

[AUDIT-8] Cross-Sectional Normalization Constituency Leak
  - Cross-sectional demeaning / z-score tại t chỉ được dùng các symbols
    IN_UNIVERSE tại thời điểm t (không phải full current universe)
  - Test: compute sector mean tại t=2023-01-01 → universe snapshot tại 2023-01-01
    phải không include symbols listed sau ngày đó
  - Detect: JOIN signal với PiT universe snapshot TRƯỚC khi compute XS mean
  - FAIL nếu: bất kỳ symbol nào trong XS computation mà in_universe=False tại t

[AUDIT-9] Causal Regime Label Assignment
  - Regime labels (trending/ranging/stressed) phải được gán bằng logic causal:
    ADX[t] chỉ dùng bars [t-14, t] — đã có trong INV-R4.1
  - Test bổ sung: regime label của bar t không thay đổi khi extend data đến t+100
    (recompute bar t với extended history → ADX[t] phải bit-identical)
  - FAIL nếu: regime thresholds được tune SAU KHI researcher thấy regime IC breakdown
    (kiểm tra: thresholds phải match giá trị trong research.yaml TRƯỚC khi T1 chạy,
    không được sửa sau khi xem T1 output)

[AUDIT-10] Funding Timestamp Alignment
  - funding_rate[t] phải là SETTLED rate tại settlement bar đó
  - Test: verify funding_rate timestamp = actual settlement timestamp (00:00/08:00/16:00 UTC),
    không phải "announcement" timestamp (thường sớm hơn 1–5 phút)
  - Check: không có funding data từ "next_funding_rate" API endpoint
    (endpoint này expose dự đoán của exchange, không phải realized)
  - Detect: query raw WS message → verify funding_rate field chỉ non-null
    SAU KHI settlement event nhận được, không trước đó
  - FAIL nếu: funding_rate[t] và event_time_ns[t] lệch hơn 5 giây khỏi settlement time
```

### Rule

```text
T1 chỉ chạy được nếu tất cả 10 checks = PASS
Nếu bất kỳ check nào FAIL → dừng, fix leakage, rerun audit

[OVERRIDE PROTOCOL — tránh false FAILs block toàn bộ research pipeline]:
  AUDIT-1 (future probe) và AUDIT-2 (normalization leak):
    KHÔNG bao giờ override. Đây là fundamental leakage — fix trước.
  
  Operational audits (AUDIT-4, AUDIT-5, AUDIT-10):
    Cho phép override khi có legitimate technical reason:
      AUDIT-4: exchange có legitimate delay trong funding settlement API
      AUDIT-5: exchange maintenance → volume=0 bars dài hợp lý
      AUDIT-10: exchange API timestamp precision issue (không phải look-ahead)
    
    Override protocol:
      max_overrides_per_year: 2 (tổng tất cả audits)
      Required: human sign-off + written reason trong ExperimentRecord
      Flag: T1Result.m_r2_override = True (propagate đến T2 và AlphaRecord)
      NOT allowed: override AUDIT-1, AUDIT-2, AUDIT-3, AUDIT-6, AUDIT-7, AUDIT-8, AUDIT-9
    
    Nếu AUDIT-4/5/10 FAIL liên tục > 3 lần → đây là pipeline bug, không phải override case.
    Investigate và fix thay vì override.
```

### Tests

```text
[T-R2.1] Inject full-sample normalization → AUDIT-2 FAIL
[T-R2.2] Include symbol outside universe → AUDIT-3 FAIL
[T-R2.3] Include predicted funding rate → AUDIT-4 FAIL
[T-R2.4] Inject ffilled OHLCV → AUDIT-5 FAIL
[T-R2.5] All clean data → all 10 PASS
[T-R2.6] Inject future-listed symbol vào XS mean → AUDIT-8 FAIL
[T-R2.7] Inject "next_funding_rate" API data → AUDIT-10 FAIL
```

### Depends on

M-D3 (universe history), M-D4 (feature cache)

### Provides to

M-R4 (T1 — requires PASS before running)

---

## M-R3: T0 Screen (Quick Kill)

**Phase:** Build Phase 0 | **TIER-A**

### Purpose

Loại 90% hypotheses trong ≤15 phút. Không cần code phức tạp — chỉ cần raw IC và rough cost.

### Input / Output

```text
INPUT:  signal: pl.Series (raw signal values, aligned với returns)
        returns: pl.Series (forward returns, BTC-neutralized)
        turnover: float (estimate, avg daily position change fraction)
        cost_model: CostModel (từ M-R7)

OUTPUT: T0Result(
          decision: "PASS" | "KILL",
          raw_ic: float,
          cost_adj_ic: float,
          turnover_estimate: float,
          cost_estimate_bps: float,
          kill_reason: str | None
        )
```

### Logic (thứ tự check)

```text
Step 1: BTC-neutralize returns (nếu chưa có btc_neutral version)
Step 2: Spearman IC (toàn sample, không CV)
Step 3: Rough turnover = mean(|signal[t] - signal[t-1]|) / mean(|signal|)
Step 4: Rough cost = turnover × round_trip_cost_bps (từ M-R7)
Step 5: Cost-adjusted IC = raw_ic - cost_estimate/10000

Kill conditions (check theo thứ tự, dừng tại condition đầu tiên FAIL):
  K1: |raw_ic| < 0.025 → "IC too low"
  K2: cost_adj_ic < 0.015 → "Net IC below threshold after cost"
  K3: cost_estimate > 0.40 × |raw_ic| × 10000 → "Cost > 40% gross IC"
```

### Parameters

```text
[ESTIMATED] ic_threshold: 0.025             — absolute value
[ESTIMATED] ic_cost_adj_threshold: 0.015
[ESTIMATED] max_cost_fraction: 0.40         — cost/gross_IC ratio
[ESTIMATED] round_trip_cost_maker_bps: 10   — BTC/ETH, phải calibrate sau 100 fills
[ESTIMATED] round_trip_cost_taker_bps: 18
```

### Dynamic Thresholds (based on effective sample size)

```text
effective_n = T × (1 - autocorrelation_lag1)^2 / signal_halflife

effective_n < 300  → strict mode:    ic_threshold = 0.030, ic_cost_adj = 0.020
300 ≤ n ≤ 600     → standard mode:  ic_threshold = 0.025, ic_cost_adj = 0.015
effective_n > 600  → relaxed mode:   ic_threshold = 0.020, ic_cost_adj = 0.012

[NOTE] Thresholds chỉ strict hơn khi sample nhỏ — không bao giờ loosen khi sample lớn.
Lý do: IC 0.04+ trên small sample có thể là noise; IC 0.02 stable trên large sample là real.
```

### IC Threshold Justification — Effective Breadth Framework

```text
IC = 0.025 (T0) và 0.020 (T1) không phải random — được derive từ:

Fundamental Law: IR ≈ IC × √(effective_breadth)
  effective_breadth ≠ n_symbols × n_bars
  effective_breadth ≈ n_independent_bets_per_year
    = n_symbols × (holding_period_bars / signal_halflife_bars) × (1 / autocorr_penalty)

Với KAIROS mid-freq (20 symbols, 1h bars, halflife ~4h, turnover ~2/day):
  n_independent_bets/year ≈ 20 × (252 × 24 / 4) / 2 ≈ 20 × 756 ≈ 15,000 raw
  autocorr_penalty (ρ=0.3) ≈ (1-ρ)/(1+ρ) ≈ 0.54
  effective_breadth ≈ 15,000 × 0.54 ≈ 8,000

IC → Sharpe mapping (trước cost):
  IR ≈ IC × √effective_breadth
  IC=0.025 → IR ≈ 0.025 × √8000 ≈ 2.24
  Sharpe annualized ≈ IR (đã annual)
  → Sharpe trước cost ≈ 2.24 → sau 2× cost (round trip ~12bps, signal ~30bps) → Sharpe ~1.0-1.2

IC=0.020 (T1 floor):
  IR ≈ 0.020 × √8000 ≈ 1.79 → Sharpe trước cost ~1.7 → sau cost ~0.7-0.9
  → Biên an toàn mỏng hơn, do đó T1 cần ICIR > 1.0 và DSR > 0.50 bổ sung

[CAVEAT] effective_breadth thay đổi theo:
  - Universe size (top-10 vs top-20)
  - Holding period thực tế (dài hơn → ít bets hơn)
  - Signal autocorrelation (cao hơn → fewer independent bets)
Thresholds 0.025/0.020 được calibrated cho top-10 to 20 symbols, 1h bars, ~4h halflife.
Nếu universe hoặc horizon thay đổi đáng kể → re-derive thresholds.
```

### Threshold Limitation & Override Protocol

```text
Hard thresholds (IC < 0.025 → kill) là pragmatic shortcut, KHÔNG phải ground truth.
IC thực tế phụ thuộc: universe size, horizon, neutralization depth, turnover, execution quality.
Một signal IC = 0.022 trên broad universe (50+ symbols) có thể tốt hơn IC = 0.040 trên 5 symbols.

Khi nào cho phép human override T0 kill:
  1. IC chỉ thấp vì universe nhỏ (< 10 symbols) và có strong economic mechanism
  2. IC thấp vì horizon quá ngắn → test horizon 2× trước khi kill
  3. Signal là component của ensemble, IC đơn lẻ không đại diện

Override protocol:
  - Document lý do override trong ExperimentRecord (immutable)
  - Set max_override_per_family = 2 (không override vô tội vạ)
  - Override không skip T1/T2 — chỉ cho phép tiến đến T1 với flag "T0 OVERRIDE"
  - Nếu T1 sau đó kill → override không justify lần sau cho cùng mechanism

T0 là speed gate, không phải truth gate. Khi override, burden of proof chuyển sang T1.
```

### Output Format

```text
Không plot. Không full diagnostics. Chỉ output T0Result.

Print ra terminal:
"[T0] F001 | IC: 0.047 | CostAdj: 0.031 | Turnover: 2.3x/day | Cost: 8bps | → PASS"
"[T0] F001 | IC: 0.018 | → KILL: IC too low"
```

### Runtime

```text
Target: ≤15 phút wall time (bao gồm load data từ M-D4)
Nếu > 15 phút → feature computation quá chậm → M-D4 cần optimize
```

### Tests

```text
[T-R3.1] IC = 0.018 → KILL K1
[T-R3.2] IC = 0.030, cost_adj_ic = 0.010 → KILL K2
[T-R3.3] IC = 0.040, cost = 18bps, raw_IC_bps = 40bps → cost/IC = 45% → KILL K3
[T-R3.4] IC = 0.040, cost_adj_ic = 0.025 → PASS
[T-R3.5] Runtime với 2 năm data, 20 symbols ≤ 15 phút
```

### Depends on

M-D4 (feature cache), M-R7 (cost model — rough estimate)

### Provides to

M-R4 (T1 — chỉ chạy nếu T0 PASS)

---

## M-R4: T1 Validate

**Phase:** Build Phase 0 | **TIER-A**

### Purpose

Confirm signal không phải artifact. Kiểm tra statistical validity với proper CV methodology.

**Prerequisite cứng:** M-R2 (leakage audit) PASS trước khi T1 chạy.

### Input / Output

```text
INPUT:  signal: pl.DataFrame (aligned với features, returns)
        experiment_record: ExperimentRecord (từ M-R1, pre-registered)
        cost_model: CostModel (từ M-R7)

OUTPUT: T1Result(
          decision: "PASS" | "KILL",
          mean_cv_ic: float,
          std_cv_ic: float,
          icir: float,                 — mean_cv_ic / std_cv_ic (IC Information Ratio)
          dsr: float,
          ic_by_regime: dict[str, float],
          capacity_usd: float,
          max_corr_vs_registry: float,
          residual_beta: float,
          ic_long: float,              — IC trên long-signal bars
          ic_short: float,             — IC trên short-signal bars (absolute)
          ic_asymmetry_flag: bool,     — True nếu |ic_long - ic_short| > 0.015
          kill_reason: str | None
        )
```

### Checks (tất cả phải pass)

```text
[T1.1] PurgedKFold CV (5-fold, embargo 21 days)
        mean_cv_ic > 0.020 threshold
        Kill nếu: mean_cv_ic ≤ 0.020

[T1.1b] ICIR (IC Information Ratio) — IC consistency filter
        ICIR = mean(IC_series) / std(IC_series)   ← tính trên toàn bộ CV IC vector
        Kill nếu: ICIR < 1.0
        Warn nếu: ICIR < 1.5

        Lý do: IC mean = 0.04, IC std = 0.08 → ICIR = 0.5 → edge không stable, risky
                IC mean = 0.025, IC std = 0.010 → ICIR = 2.5 → rất consistent, viable
        
        ICIR là filter mạnh hơn DSR cho detecting genuine stable edge.
        Một alpha có thể pass DSR nhờ high peak IC nhưng fail ICIR vì IC rất noisy.
        
        [NOTE] Phân biệt: IC_series = [IC_fold_1, IC_fold_2, ... IC_fold_k] từ PurgedKFold
        Không dùng full-sample rolling IC std (correlated, không independent observations).

[T1.2] Deflated Sharpe Ratio
        DSR > 0.50 (n_trials từ ExperimentRecord.n_trials_total — cross-family)
        Kill nếu: DSR ≤ 0.50
        [NOTE] n_trials phải honest — không reset khi idea không work
        [NOTE] Dùng n_trials_total (không phải n_trials_family) để tránh
               undercount khi researcher đã test nhiều families trên cùng data

[T1.3] Regime Split IC
        3 regimes: trending (ADX > 25), ranging (ADX ≤ 25, low vol), stressed (VIX-equivalent > 2σ)
        Kill nếu: bất kỳ regime nào có IC < -0.010
        [NOTE] không kill nếu IC thấp trong 1 regime, chỉ kill nếu negative

        [PRE-COMMITMENT INVARIANT — chống look-ahead implicit]:
        Tất cả regime thresholds (ADX_trending = 25, vol_stressed = 2σ) phải được
        commit vào research.yaml TRƯỚC KHI T0 screen bất kỳ hypothesis nào.
        Không được thay đổi thresholds sau khi researcher thấy regime IC breakdown.
        
        Lý do: nếu researcher thấy "IC tốt khi ADX > 20" và đổi threshold từ 25→20
        để maximize IC → đây là implicit data snooping, làm tăng n_trials ẩn.
        
        Change protocol: nếu thay đổi regime thresholds là cần thiết (economic basis mới):
          - Ghi rõ lý do kinh tế (không phải "IC cao hơn") trong ExperimentRecord
          - n_trials += 1 cho tất cả hypotheses đang active trên cùng data window
          - Rerun T1 từ đầu với new thresholds

        [INV-R4.1] ADX PHẢI được compute dùng rolling window (14-bar default),
        không full-sample. Full-sample ADX tạo regime labels bằng thông tin tương lai
        (look-ahead leak nghiêm trọng vì regime assignment thay đổi retroactively).
        Test: ADX[t] chỉ dùng bars [t-14, t]. Verify bằng cách recompute bar 100
        với extended data — ADX[100] không được thay đổi.

        [INV-R4.2] Cross-sectional sector demeaning (M-R8) chỉ dùng symbols
        thuộc universe TẠI thời điểm t (không phải future-listed assets).
        JOIN với PiT universe snapshot (asset_id, không symbol) trước khi compute sector mean.

[T1.4] Capacity Estimate (rough)
        max_capacity_usd = 0.05 × ADV_bottom_quartile_universe × halflife_bars
        Kill nếu: max_capacity_usd < min_target_capacity ($100K)

[T1.5] Correlation vs Alpha Registry
        max_corr_vs_existing_alphas (trên return series) < 0.60
        Kill nếu: max_corr ≥ 0.60 (redundant với existing)

[T1.6] BTC/ETH Beta Check
        residual_beta = beta sau BTC + ETH neutralization
        Kill nếu: |residual_beta| > 0.15
        [NOTE] nếu beta bị loại, recompute IC trên neutralized returns

[T1.7] Feature Importance Stability (Ridge coefficient stability)
        Fit Ridge regression (signal ~ features) trên mỗi CV fold
        
        [CRITICAL — Standardization Required]:
        Trước khi compute coefficient stability, PHẢI standardize features:
          X_std = (X - mean(X_train)) / std(X_train)  ← per-fold, không full-sample
          coef_std_k = coef_k × std(X_train_k)        ← standardized coefficient
        
        Lý do: funding_rate_zscore (range ±3) vs oi_change_pct_1h (range ±0.30) →
        raw Ridge coef của oi_change_pct_1h cao gấp 10× đơn giản vì scale khác,
        không phải vì importance khác. Stability check trên raw coef = noise.
        
        stability_score = mean(|coef_std_fold_k|) / std(|coef_std_fold_k|) across folds
        Kill nếu: stability_score < 2.0 (coefficient flip-flopping across folds)
        Warn nếu: top-3 features thay đổi hoàn toàn giữa folds (feature instability)
        [NOTE] model với unstable features sẽ fail out-of-sample ngay cả khi in-sample IC cao

[T1.8] Long/Short IC Asymmetry Check
        ic_long  = spearman(signal[signal > 0], return[signal > 0])
        ic_short = spearman(|signal[signal < 0]|, |return[signal < 0]|)
        
        Warn nếu: |ic_long - ic_short| > 0.015
          → strategy có thể work longs nhưng fail shorts (hoặc ngược lại)
          → Investigate: crowding asymmetry, borrow cost, funding carry direction bias
        
        Investigate (KHÔNG auto-kill) nếu: ic_short < -0.01
          → short signals predict opposite direction → short leg actively harmful
          → Options: (1) long-only version, (2) review cost model on short side,
            (3) check funding carry direction (short perp = pay funding → systematic drag)
        
        [POSITION CONSTRAINT khi ic_short < -0.01]:
          max_short_weight ≤ 50% trong paper trade (không phải full allocation)
          Lý do: không kill alpha vì có thể long-side valid, nhưng limit short exposure
            cho đến khi paper trade confirms ic_short không tiếp tục deteriorate.
          Gate: KHÔNG promote lên SHADOW cho đến khi paper gate (60 ngày) xác nhận
            ic_short ổn định (không < -0.01 trên rolling 30d trong paper period).
          Log: ic_short_paper_30d phải có trong T2Result và PaperResult schema.
        
        Document trong AlphaRecord.mechanism_tags nếu có asymmetry:
          "long_only_viable" | "short_side_drag_funding" | "symmetric"
        [NOTE] IC asymmetry có thể có economic basis. Không kill — nhưng PHẢI document.
               Undocumented asymmetry → alpha behavior unpredictable khi regime shifts.
```

### Runtime

```text
Target: ≤2 giờ wall time
5-fold CV trên 2 năm data, 20 symbols phải xong trong budget này
Nếu > 2 giờ → CV computation quá chậm → optimize feature loading
```

### Effective Sample Size Warning

```text
effective_n = T × (1 - autocorrelation_lag1)^2 / signal_halflife
Warn nếu effective_n < 500:
  "WARNING: effective sample size = {n}, statistical conclusions weak"
  "Consider: longer data history, more symbols, or extend paper trade"
Không kill tự động — chỉ warn + adaptive_threshold
```

### Adaptive Thresholds

```text
Nếu effective_n < 500 → strict thresholds
  mean_cv_ic threshold tăng lên 0.025 (thay vì 0.020)
  paper_trade_days tăng lên 60 (thay vì 30)
Không loosen thresholds — chỉ strict hơn khi sample nhỏ
```

### Tests

```text
[T-R4.1] Synthetic signal với IC=0.015 → T1.1 KILL
[T-R4.2] T1 chạy được khi leakage audit PASS, block khi FAIL
[T-R4.3] n_trials=10 → DSR thấp hơn n_trials=1 với cùng SR (multiple testing)
[T-R4.4] Signal correlated 0.70 với existing alpha → T1.5 KILL
[T-R4.5] Effective sample size warning khi n < 500
```

### Depends on

M-R1 (ExperimentRecord), M-R2 (leakage audit PASS), M-R7 (cost model), M-D4 (features), M-R9 (alpha registry — cho T1.5)

### Provides to

M-R5 (T2 — chỉ chạy nếu T1 PASS)

---

## M-R5: T2 Full Diligence

**Phase:** Build Phase 1 | **TIER-A**

### Purpose

Full validation trước khi shadow trade. Đây là last gate trước capital exposure.

### Input / Output

```text
INPUT:  signal, features, T1Result (phải PASS)
        cost_model (calibrated nếu có paper fills)
        alpha_registry (existing alphas cho portfolio fit)

OUTPUT: T2Result(
          decision: "PASS" | "KILL",
          backtest_sharpe: float,
          backtest_max_dd: float,
          wf_ic_mean: float, wf_ic_std: float,
          stress_luna_return: float, stress_ftx_return: float,
          random_stress_pass_rate: float,   — fraction passed (≥ 0.70 required)
          capacity_usd: float,
          marginal_sharpe: float,
          adjusted_marginal_sharpe: float,  — marginal_sharpe × capital_efficiency_factor
          ir_vs_benchmark: float,           — alpha contribution vs equal-weight benchmark
          sharpe_optimistic: float,         — Scenario A fill rate
          sharpe_conservative: float,       — Scenario B fill rate
          kill_reason: str | None
        )
```

### Checks

```text
[T2.1] Full vectorized backtest (2 năm, Polars)
        backtest_sharpe > 0.8 (cost-adjusted)
        backtest_max_dd < 0.25 (25%)
        
        ir_vs_benchmark ≥ 0.20
          benchmark = equal-weight buy-and-hold portfolio (cùng universe symbols, PiT-safe)
          
          [BENCHMARK NEUTRALIZATION — CRITICAL]:
          Benchmark PHẢI dùng cùng neutralization protocol với strategy:
            BTC-neutral strategy → benchmark = equal-weight BTC-neutral returns
            Raw strategy         → benchmark = equal-weight raw returns
          KHÔNG mix neutralization: strategy BTC-neutral vs benchmark raw → IR vô nghĩa
          (benchmark có positive raw return từ BTC beta → strategy looks bad unfairly)
          
          BacktestConfig fields bắt buộc cho IR calculation:
            benchmark_neutralization: str — "btc_neutral" | "raw" | "sector_neutral"
            benchmark_rebalance:      str — "daily" (default)
            benchmark_include_cost:   bool — True (default: benchmark also pays cost)
          
          ir_vs_benchmark = (strategy_return_ann - benchmark_return_ann) / tracking_error_annual
          Kill nếu: ir_vs_benchmark < 0.20
          Lý do: backtest_sharpe > 0.8 có thể đến từ market beta trong crypto bull run 2020–2021.
          IR vs benchmark đo pure alpha contribution độc lập với market direction.
          [NOTE] Benchmark phải backtest trên cùng PiT universe (không dùng BTC hoặc ETH làm
                 benchmark — chúng có bias và không represent universe diversification).

        [LIVE DEGRADATION EXPECTATION — quan trọng]
        Backtest IC → live IC thường bị haircut 30–60% vì:
          - Crowding (signal bị discovered bởi các player khác)
          - Regime instability (crypto market structure thay đổi nhanh)
          - Execution slippage thực > model cost
          - Feature drift (live feature != batch recompute)
        
        Implication cho threshold:
          backtest_sharpe = 0.8 → expect live Sharpe ≈ 0.3–0.5 (sau haircut)
          backtest_sharpe = 1.5 → expect live Sharpe ≈ 0.6–1.0
        
        Chỉ forward backtest strategies với backtest_sharpe ≥ 1.2 nếu muốn live Sharpe > 0.5.
        backtest_sharpe 0.8 là minimum gate, không phải confident target.

[T2.2] Walk-forward analysis (6 windows, 4:1 train:test ratio)
        Refit model trên each train window, evaluate on test
        wf_ic_stability: wf_ic_std < 0.50 × wf_ic_mean
        Kill nếu: IC không stable (model không generalizable)
        
        [WF SPLIT ISOLATION — chống implicit data snooping]:
        Walk-forward window boundaries PHẢI được defined trong research.yaml TRƯỚC
        khi T1 chạy (cùng session). Không adjust WF windows sau khi thấy T1 result.
        
        WF test windows KHÔNG được overlap với T1 PurgedKFold embargo periods.
        Lý do: researcher thấy T1 pass → tiến lên T2. Nếu T2 WF trains trên một số
        bars mà T1 test set dùng → implicit data snooping ở tier boundary.
        
        Implementation rule: wf_test_dates được log vào research.yaml cùng thời điểm
        với t1_fold_dates. Nếu wf_test_dates không có trong research.yaml khi T2 chạy
        → T2 bị BLOCK (phải pre-define WF splits).
        
        [CALIBRATION STATUS] wf_n_windows=6, wf_train_test_ratio=4 là ESTIMATED.
        Không tune số windows để maximize WF IC stability.

[T2.3] Stress test (mandatory periods + random high-vol)
        
        Tier 1 — Named Events (mandatory):
        Luna crash: 2022-05-01 to 2022-05-15 → stress_luna_return
        FTX collapse: 2022-11-01 to 2022-11-15 → stress_ftx_return
        Kill nếu: cả hai đều negative (không diversify được với market stress)
        Acceptable: negative ở 1 period, không negative ở cả 2

        Tier 2 — Random High-Vol Periods (mandatory, anti-selection-bias):
        [CRITICAL] Named events (Luna, FTX) là look-ahead ở framework level.
        Researcher biết đây là "bad periods" vì đã sống qua chúng.
        Đây là conditional survivorship: "does strategy survive KNOWN catastrophes?"
        
        Bổ sung bắt buộc: test trên 20 random periods với cùng volatility profile:
          sample_criterion: BTC 24h realized vol > 90th percentile AND kéo dài ≥ 5 bars
          sample_count: 20 periods (random seed cố định trong research.yaml)
          pass_threshold: strategy phải survive ≥ 14/20 periods (không negative return)
        
        random_stress_periods = sample_high_vol_periods(
            data=ohlcv_btc,
            vol_percentile=0.90,
            min_duration_bars=5,
            n_samples=20,
            seed=research_yaml["stress_random_seed"]  ← cố định, không tune
        )
        
        Kill nếu: random_stress_pass_rate < 0.70 (fail ≥ 7/20 periods)
        Warn nếu: random_stress_pass_rate < 0.80

[T2.4] Full cost model với adverse selection
        Dùng full M-R7 (không rough estimate như T0)
        Bao gồm: adverse selection, spoof discount, funding window penalty

[T2.5] Drawdown analysis
        max_dd, time_to_recovery_days, calmar_ratio
        Kill nếu: time_to_recovery > 90 ngày (alpha quá slow-recovering)

[T2.6] Capacity (refined)
        Dùng true L2 depth (không raw ADV)
        capacity_usd = min(5% × true_liquidity, capacity_from_halflife)

[T2.7] Portfolio fit
        marginal_sharpe = Sharpe(portfolio + new_alpha) - Sharpe(portfolio)
        
        [CAPITAL EFFICIENCY FACTOR — Cross-Exchange Strategies]:
        Cross-exchange strategies (F002) lock collateral trên 2 sàn đồng thời.
        Không thể dùng cùng capital cho strategies khác trong khi F002 legs open.
        
        capital_efficiency_factor:
          single_exchange strategy: 1.0  — capital available toàn bộ
          cross_exchange strategy:  0.5  — capital bị lock trên 2 legs đồng thời
        
        adjusted_marginal_sharpe = marginal_sharpe × capital_efficiency_factor
        Kill nếu: adjusted_marginal_sharpe < 0.05 (khi đã có existing alphas)
        N/A nếu không có existing alphas (first alpha luôn pass T2.7, nhưng vẫn log factor)
        
        Lý do: marginal_sharpe 0.10 của F002 thực ra equivalent 0.05 vì capital locked
        trên 2 sàn không available cho F001/M001 simultaneously.

[T2.8] Edge Half-Life by Regime
        Compute IC autocorrelation function (ACF) separately within each regime:
          trending, ranging, stressed (same regime definition as T1.3)
        halflife_regime[r] = lag tại ACF drops below 0.10
        Kill nếu: halflife_regime[stressed] < 3 bars (edge degrades too fast under stress)
        Warn nếu: halflife_regime variance > 3× across regimes (unstable edge timing)
        [NOTE] strategy với halflife < rebalance_freq là incoherent — bạn không thể capture signal nhanh hơn bạn rebalance
```

### Stress Periods Mandatory

```text
Phải test ít nhất:
  Luna/UST: 2022-05-01 to 2022-05-15
  FTX:      2022-11-01 to 2022-11-15
  Thêm khi xảy ra: update list mỗi khi có black swan event mới

Nếu strategy không có position trong period (funding strategy hedge có thể flat)
→ mark as N/A, không kill, document lý do
```

### Tests

```text
[T-R5.1] Sharpe < 0.8 → T2.1 KILL
[T-R5.2] wf_ic_std > 0.6 × wf_ic_mean → T2.2 KILL
[T-R5.3] Negative cả Luna lẫn FTX → T2.3 KILL
[T-R5.4] time_to_recovery > 90 ngày → T2.5 KILL
[T-R5.5] marginal_sharpe < 0 khi có existing alpha → T2.7 KILL
```

### Depends on

M-R4 (T1 PASS), M-R6 (vectorized backtest), M-R7 (full cost model), M-R9 (registry — marginal Sharpe)

### Provides to

M-R9 (alpha registry — update stage ke VALIDATION), M-L1 (paper trade)

---

## M-R6: Vectorized Backtest

**Phase:** Build Phase 0 | **TIER-A**

### Purpose

Fast backtest engine cho research. Polars-based. Single file. Không dùng event-driven backtesting trong Phase 0–2 — vectorized đủ cho mid-freq.

### Input / Output

```text
INPUT:  signals: pl.DataFrame (timestamp, symbol, signal_value)
        prices: pl.DataFrame (timestamp, symbol, open, close)
        cost_model: CostModel
        config: BacktestConfig

OUTPUT: BacktestResult(
          sharpe: float,
          max_dd: float,
          calmar: float,
          ic_series: pl.Series,
          turnover_daily: float,
          capacity_usd: float,
          returns_series: pl.Series,
          fill_probability_maker: float,    — est. fraction of maker orders filled
          margin_trajectory: pl.Series,     — per-bar simulated margin utilization
          max_margin_utilization: float,    — peak margin usage (để detect F002 risk)
          gross_vs_net_sharpe: tuple[float, float]  — hiển thị funding drag
        )
```

### BacktestConfig

```text
@dataclass
class BacktestConfig:
    start_date: date
    end_date: date
    rebalance_freq: str        — "1h", "4h", "1d"
    position_sizing: str       — "equal_weight" | "signal_weight" | "vol_target"
    vol_target: float          — annualized, 0.15 default
    max_position: float        — max per-symbol fraction, 0.20 default
    cost_side: str             — "maker" | "taker"
    maker_fill_rate: float     — 0.80 BTC/ETH, 0.60 mid-cap, 0.40 alts [ESTIMATED]
    is_cross_exchange: bool    — True nếu strategy cần hedge 2 sàn (F002)
    max_margin_per_leg: float  — 0.50 (50% capital per exchange leg, F002 only)
    execution_lag_bars: int    — 1 (default): signal tại bar t → fill tại open của bar t+1
    execution_price: str       — "open_next" (default) | "close" | "vwap_next"
    rolling_vol_window: int    — 21 (default): số bars dùng cho rolling vol trong "vol_target" sizing

[VOL WINDOW INVARIANT]:
rolling_vol_window phải ≥ min_periods / 12 (min_periods = 252 bars).
Nếu rolling_vol_window < 21 → WARN (vol estimate noise dominates signal).
Trong first rolling_vol_window bars sau burn-in: dùng expanding window fallback thay vì rolling.
  → không bỏ qua bars đầu (thường nhỏ hơn 21 bars), nhưng size nhỏ hơn do wider CI.

[CRITICAL — Execution Price Assumption]:
Default phải là "open_next", KHÔNG phải "close".
Lý do: signal được compute sau khi bar close → không thể fill cùng bar đó.
  Nếu fill tại "close": backtest assume bạn biết bar close price TRƯỚC khi bar đóng
  → systematic look-ahead bias, thổi phồng Sharpe ~20–40% tùy signal halflife.
  
"open_next" = fill tại open price của bar tiếp theo = realistic cho 1h bars.
Nếu execution_price = "close" trong ExperimentRecord → Trainer.fit() WARN + flag.
Không hard-block (có thể có special case) nhưng phải document lý do.
```

### Position Sizing

```text
"vol_target" (recommended):
  target_vol = vol_target / sqrt(252 × bars_per_day)
  position[s,t] = signal[s,t] × target_vol / rolling_vol[s,t]
  clip to max_position

[NOTE] Không normalize signals full-sample (look-ahead)
Dùng rolling quantile hoặc expanding quantile cho signal normalization
```

### IC Calculation

```text
IC[t] = spearman(signal[t], forward_return[t])
        cross-sectional, per rebalance period

Mean IC phải match T0/T1 IC (với same data, same horizon)
Nếu không match → bug trong labeling hoặc alignment
```

### Cost Application

```text
Cost per trade = round_trip_cost (từ M-R7)
Turnover[t] = sum(|position[t] - position[t-1]|) / 2
Cost[t] = turnover[t] × round_trip_cost × portfolio_value
Net_return[t] = Gross_return[t] - Cost[t]
```

### Maker Fill Simulation — Dual Scenario Mandatory

```text
[CRITICAL] Strategy phải PASS T2 với CẢ HAI scenarios. Chỉ pass optimistic = không đủ.

Scenario A — Optimistic (structural queue advantage):
  BTC/ETH:    maker_fill_rate = 0.85   ← giả định queue position tốt
  Top-10:     maker_fill_rate = 0.70
  Alts:       maker_fill_rate = 0.50

Scenario B — Conservative (mid-freq systematic reality):
  BTC/ETH:    maker_fill_rate = 0.55   ← systematic strategy thường cuối queue
  Top-10:     maker_fill_rate = 0.40
  Alts:       maker_fill_rate = 0.25

Lý do Scenario B thực tế hơn cho mid-freq systematic:
  - Systematic strategy đặt order SAU signal → luôn cuối queue, không đầu
  - Cancel/replace khi signal update → queue position reset về cuối mỗi lần
  - Queue Position Reset: mỗi lần cancel/replace order (do signal thay đổi) →
    order bị đẩy xuống cuối queue. Với 1h rebalancing, nếu signal thay đổi
    trong bar → bạn cancel lệnh cũ, place lệnh mới → đứng cuối hàng
  - Kết quả: thực tế là blended cost (maker × fill_rate + taker × (1-fill_rate))
    trong đó fill_rate thực ≈ 0.50–0.60 cho BTC, không phải 0.85

fill_probability_maker[symbol, t, scenario] = min(1.0,
  volume[t] × fill_rate_config[scenario] / (order_size_usd / price[t]))

Nếu fill_probability_maker < 1.0:
  actual_cost = maker_cost × fill_rate + taker_cost × (1 - fill_rate)
  Backtest áp dụng blended cost, không thuần maker.

Kill conditions:
  Nếu backtest_sharpe[Scenario_A] ≥ 0.8 BUT backtest_sharpe[Scenario_B] < 0.5:
    → Kill: strategy quá sensitive với execution quality
    → Không viable nếu không có HFT infrastructure
  
  Nếu fill_probability_maker[Scenario_B] < 0.40 average:
    → Kill: strategy không viable với realistic queue dynamics

BacktestResult phải log cả hai: sharpe_optimistic, sharpe_conservative
T2 gate: backtest_sharpe[Scenario_A] ≥ 0.80 AND backtest_sharpe[Scenario_B] ≥ 0.75
  [RATIONALE] Scenario_B (conservative) không được có gate thấp hơn Scenario_A (optimistic).
  Logic: strategy phải đủ mạnh để survive realistic conditions, không chỉ look good dưới
  optimistic assumptions. ≥ 0.75 cho Scenario_B reflect haircut từ lower fill rates
  (không phải free pass).
```

### Cross-Exchange Margin Trajectory (F002)

```text
Chỉ áp dụng khi is_cross_exchange = True:

Mỗi bar, simulate margin utilization per leg:
  margin_used_leg_A[t] = |position_A[t]| × (1 + margin_buffer)
  margin_used_leg_B[t] = |position_B[t]| × (1 + margin_buffer)

Kill F002 nếu: max(margin_used_leg_A hoặc B) > max_margin_per_leg = 0.50
Lý do: spike price có thể liquidate một chân dù tổng PnL = 0.

Thêm vào BacktestResult: margin_trajectory (Polars Series), max_margin_utilization
```

### Tests

```text
[T-R6.1] Backtest với zero signal → Sharpe ≈ 0 (no edge)
[T-R6.2] Backtest với perfect predictor → Sharpe >> 3
[T-R6.3] IC series mean ≈ T0 IC (same data, same horizon)
[T-R6.4] Turnover consistent với T0 turnover estimate (±20%)
[T-R6.5] Cost-adjusted returns < gross returns (cost always positive)
[T-R6.6] Runtime: 2 năm, 20 symbols, 1h bars ≤ 60 giây
[T-R6.7] Maker fill_probability < 0.60 → blended cost applied, kết quả tệ hơn
[T-R6.8] F002 margin spike → max_margin_utilization > 0.50 flagged
```

### Depends on

M-D4 (feature cache), M-R7 (cost model)

### Provides to

M-R5 (T2 diligence), M-R4 (T1 backtest component)

---

## M-R7: Cost Model

**Phase:** Build Phase 0 | **TIER-A**

### Purpose

Estimate trading costs cho backtest và screening. Honest về assumptions. Calibrate từ live fills sau Phase 3.

### Components

```text
round_trip_cost_bps(symbol, side, size_usd, regime) → float

Components:
  fee        = maker_fee hoặc taker_fee (per exchange, tier)
  adv_sel    = adverse_selection_bps (per fill direction)
  impact     = market_impact_bps(size_usd, true_liquidity)
  spoof_disc = spoof_discount(symbol) — reduce effective liquidity
  fund_pen   = funding_window_penalty (nếu bar trong blackout)
  borrow     = borrow_cost_per_day (chỉ khi short spot)

Total = (fee + adv_sel + impact + fund_pen) × 2 + borrow × hold_days
```

### Parameter Table

```text
Component                         Value        Status       Calibrate After
─────────────────────────────────────────────────────────────────────────────
Maker fee (Binance VIP0, USDT-M) +0.02%        PUBLISHED    Verify per tier/coin
Taker fee (Binance VIP0, USDT-M) +0.05%        PUBLISHED    —
Maker fee (Bybit VIP0, USDT-M)   +0.02%        PUBLISHED    Verify per tier
Taker fee (Bybit VIP0, USDT-M)   +0.055%       PUBLISHED    Verify per tier
Adverse selection maker           4 bps         ESTIMATED    100 fills
Adverse selection taker           8 bps         ESTIMATED    100 fills
Market impact (under $50K)        2 bps         ESTIMATED    500 fills
Market impact ($50K–$200K)        5 bps         ASSUMED      200 large fills
Spoof discount BTC/ETH           15–20% depth   ESTIMATED    L2 analysis
Spoof discount alts              35% depth      ASSUMED      —
Funding window penalty           ~5 bps         ESTIMATED    Live observation
Borrow rate (calm)               0.03%/day      ASSUMED      Coinglass data
Borrow rate (stressed, 5× spike) 0.15%/day      ASSUMED      Live observation
Cancel/replace overhead          0.5 bps        ASSUMED      Monitor
─────────────────────────────────────────────────────────────────────────────
Conservative round-trip (maker, BTC/ETH, <$50K): 14–20 bps
Conservative round-trip (taker, BTC/ETH, <$50K): 22–30 bps
Minimum gross IC profitable:  0.045 (maker) | 0.055 (taker)

[WARNING] -0.01% maker rebate (BNB discount tier, FDUSD, hoặc VIP4+) KHÔNG áp dụng
cho VIP0 USDT-M perps tiêu chuẩn. Sử dụng +0.02% là conservative default. Verify
fee schedule thực tế của account trước khi T0 screen bất kỳ strategy nào. Dùng nhầm
negative fee làm thổi phồng IC cost-adjusted và cho phép strategies không viable qua T0.
```

### Spoof Discount Logic

```text
L2 displayed depth thường bị inflate 15–35% bởi spoofing.
Discount trước khi dùng depth để estimate impact:

effective_depth = displayed_depth × (1 - spoof_discount)
  BTC/ETH:   discount = 0.17 (estimate)
  Top-10:    discount = 0.25 (estimate)
  Alts:      discount = 0.35 (assumed)

Impact dùng effective_depth, không raw depth
```

### Funding Window Blackout

```text
Funding blackout theo size:
  size ≤ $50K:  blackout [T-30min, T]
  size > $50K:  blackout [T-60min, T]
  Blackout windows: T ∈ {00:00, 08:00, 16:00 UTC}

Lý do: large players bắt đầu positioning 1–2 giờ trước settlement.
Price distortion từ funding-driven flow thường bắt đầu 60–90 phút trước,
không phải 30 phút. 30 phút chỉ đủ cho micro-positions.

Bars trong blackout window → label = NaN trong M-R1 (labeler)
Bars trong blackout window → cost nhân 2.5× nếu vẫn phải trade
(tăng từ 2.0× để reflect higher adverse selection gần settlement)
```

### Market Impact Model

```text
Dùng square-root model:
  impact_bps = c × σ × sqrt(Q / V_effective)
    c:           0.20 (conservative; equity default là 0.10)
    σ:           30-min realized vol
    Q:           trade size (USD)
    V_effective: true_liquidity × (1 - spoof_discount)

OB imbalance multiplier:
  Nếu top-5-level imbalance > 0.80 → impact × 2.2
  Lý do: mất queue position khi book imbalanced

Inventory Accumulation Multiplier:
  Điều kiện: sign(position_delta[t]) == sign(position_delta[t-1]) == sign(position_delta[t-2])
    → 3 bars liên tiếp cùng chiều accumulation (không phải rebalance nhỏ)
  Hệ quả: impact × 1.5 cho bar t+1
  Lý do: adversarial participants (HFT, market maker) detect sustained flow pattern →
    adjust quotes → realized impact 2–3× model cho $100K+ sustained positions.
    Mỗi cancel/replace để move queue position = thêm queue reset cost vào impact.
  Parameter: [ASSUMED] — calibrate sau 500 fills thực tế. Log mỗi lần trigger.
  [NOTE] Áp dụng cho impact component; adverse selection multiplier tính riêng (không stack).
```

### Adverse Selection Regime Multiplier

```text
[CRITICAL] Adverse selection KHÔNG phải static. Nó là highly regime-dependent.
Static estimate (4 bps maker) chỉ đúng trong calm market.
Khi strategy muốn trade nhất (funding spike, high vol) → adverse selection cao nhất.

adverse_selection_bps_effective = base_adv_sel × regime_multiplier(state)

regime_multiplier:
  Bình thường (funding_zscore ≤ 1.5, vol_percentile ≤ 75th): × 1.0
  Pre-funding (funding_zscore > 1.5):                          × 1.8
  High-funding (funding_zscore > 2.5):                         × 2.5
  Extreme-funding (funding_zscore > 3.5):                      × 4.0
  Vol spike (vol_percentile > 90th):                           × 2.2
  Vol extreme (vol_percentile > 95th):                         × 3.5
  Liquidation cascade (mark_price / index_price > 0.3%):       × 5.0

[COMBINING RULE — khi nhiều conditions xảy ra đồng thời]:
  adv_sel_multiplier = max(funding_mult, vol_mult, cascade_mult)
  KHÔNG nhân (multiplicative): 4.0 × 3.5 = 14.0 là unrealistic outlier compounding.
  Lý do: các multipliers không độc lập — extreme funding thường kèm extreme vol.
  Dùng max() captures worst condition mà không double-count.
  
  Ví dụ Luna crash: funding_zscore > 3.5 (×4.0) AND vol > 95th (×3.5) AND cascade (×5.0)
  → adv_sel_multiplier = max(4.0, 3.5, 5.0) = 5.0 (không phải 4.0 × 3.5 × 5.0 = 70.0)

Funding period penalty đã có (+5 bps, nhân 2.5×) — regime multiplier là THÊM VÀO,
áp dụng cho adverse selection component riêng biệt, không toàn bộ cost.

Impact cho T0/T1/T2: backtest phải dùng time-varying adverse selection,
không static. Tính toán: adv_sel_t = base × regime_mult(funding_zscore_t, vol_pct_t).
```

### Liquidity Vacuum Multiplier

```text
Crypto có đặc tính "liquidity vacuum": trong high-vol, market impact không tăng
theo hàm sqrt mà tăng theo hàm exponential khi bid-ask spread collapse.

Khi spread_bps[t] > spread_pct_threshold × median_spread:
  Effective depth giảm phi tuyến:
    spread_ratio = spread_bps[t] / median_spread_bps
    liquidity_discount = min(0.80, 1.0 - 0.30 × log(spread_ratio))
    effective_depth = displayed_depth × (1 - spoof_discount) × liquidity_discount

Thresholds:
  spread_ratio > 2×:  liquidity_discount = 0.70 (depth giảm 30%)
  spread_ratio > 5×:  liquidity_discount = 0.50 (depth giảm 50%)
  spread_ratio > 10×: liquidity_discount = 0.30 (depth giảm 70%)

Backtest phải apply vacuum multiplier mỗi khi spread_bps > 2× median.
Nếu strategy cost-viable CHỈ với tight spread → flag: "spread-regime dependent".
```

### Liquidity Sourcing Urgency Score

```text
Thay vì static "maker" hoặc "taker" per strategy, đề xuất dynamic logic:

urgency_score[t] = signal_IC_decay_rate[t] × |current_position_gap[t]|
  signal_IC_decay_rate: estimated IC halflife decay per bar (from T2.8)
  position_gap: |target_position - current_position| / max_position

urgency_threshold = 0.70 (tune trong paper trade)

Nếu urgency_score > urgency_threshold:
  → Dùng taker (pay spread, get fill immediately)
Nếu urgency_score ≤ urgency_threshold:
  → Dùng maker (save spread, accept fill risk)

Backtest cost tính với dynamic blended:
  cost_t = urgency_score[t] × taker_cost + (1 - urgency_score[t]) × blended_maker_cost

[NOTE] urgency_threshold phải được calibrated trong paper trade, không optimized
trong backtest (overfitting risk). Default 0.70 là conservative prior.
```

### Calibration Protocol (sau 100 fills)

```text
1. Compute actual adverse_selection = mean(signed_return_5min × fill_direction)
2. Compare vs estimate (4 bps maker)
3. Update adverse_selection_bps nếu actual > estimate × 1.5
4. Log: old_value, new_value, n_fills, date
5. Rerun T1/T2 của existing alphas với new cost → check if still PASS

Nếu maker fill rate thực tế sau 100 fills < 0.55 (BTC/ETH):
  [HARD GATE] Toàn bộ cost model phải recalibrate trước khi bất kỳ alpha nào
  được promote lên shadow. Không exception.
  Lý do: đây là single biggest live performance gap — không bao giờ underestimate.
```

### Transaction Cost Analysis (TCA) Protocol

```text
TCA là bắt buộc sau mỗi 100 fills để biết NGUYÊN NHÂN cost cao, không chỉ biết cost cao.

Decomposition per fill:
  tca_signal_mid_price:       mid_price tại thời điểm signal generated
  tca_order_mid_price:        mid_price tại thời điểm order submitted
  tca_fill_price:             price thực tế fill
  tca_timing_cost:            (order_mid - signal_mid) × direction  ← delay từ signal
  tca_implementation_cost:    (fill_price - order_mid) × direction  ← market move during exec
  tca_market_impact:          implementation_cost - fee - adverse_selection_measured
  tca_opportunity_cost:       nếu order không fill → (next_bar_mid - signal_mid) × direction

Aggregation mỗi 100 fills:
  mean_timing_cost:           → nếu cao: signal generation lag, cần tối ưu latency
  mean_implementation_cost:   → nếu cao: execution slippage, cần adjust order placement
  mean_market_impact:         → nếu cao: capacity bị exceed, reduce size
  fill_rate:                  → nếu thấp: opportunity cost cao, xem xét urgency score
  
Action map:
  timing_cost > 2 bps    → investigate signal-to-order latency
  impact > 3 bps         → reduce position size 20%
  fill_rate < 0.55       → urgency_threshold giảm 0.10 (taker nhiều hơn)
  opportunity_cost > 5 bps → signal halflife có thể ngắn hơn estimate
```

### Funding Decomposition (quan trọng cho Family 1)

```text
raw_return = price_return + funding_income - funding_cost

Khi research funding alpha (F001–F004):
  Test IC trên price_return, không tổng return
  Nếu không: funding carry contaminate IC calculation

surprise_funding = realized_funding - expected_funding_from_premium_index_MA
  expected_funding tính từ Premium Index MA, không shift(1)
  surprise_funding là true signal, không expected_funding
```

### Family 3 (OB Signals) — Queue Position Warning

```text
Model hiện tại UNDERSTATES cost cho sub-5min OB strategies.

Vấn đề: cost model giả định fill tại bid/ask. Thực tế với maker orders:
  - Queue position quyết định fill probability
  - Deeper queue position → fill chậm hơn → signal stale khi fill xảy ra
  - Cost thực = fee + adverse_selection + QUEUE_WAIT_COST

Queue wait cost không được estimate trong model hiện tại vì thiếu live data.

CHÍNH SÁCH: Family 3 (OB signals) BLOCKED khỏi FULL paper trade cho đến khi:
  1. Family 1 hoặc 2 đã có ≥100 live maker fills
  2. adverse_selection calibrated từ live data
  3. Observed queue position stats từ actual fills
  4. Rerun T2 cho Family 3 hypotheses với calibrated cost

[EXCEPTION — Capped Paper Track]:
  Cho phép paper trade Family 3 hypotheses SONG SONG với F1/F2 paper, với điều kiện:
    - position_size ≤ 10% của normal paper size (micro-lot research only)
    - Chỉ dùng để collect adverse selection data thực tế, KHÔNG phải để validate IC
    - IC từ capped paper KHÔNG được dùng làm paper gate (sample quá nhỏ)
    - Ghi rõ trong AlphaRecord: ob_capped_paper = True, start_date, n_fills_capped
    - Mục đích duy nhất: calibrate queue_position_stats và adverse_selection sớm hơn
      → accelerate M-R7 calibration cho Family 3, không validate alpha
  Prerequisite: T2 phải PASS với cost_multiplier = 1.5× TRƯỚC KHI bắt đầu capped paper.
  Nếu T2 chỉ PASS với 1.0×: capped paper KHÔNG cho phép.

Trong backtest cho Family 3: dùng cost_multiplier = 1.5× maker estimate (conservative).
Nếu alpha vẫn PASS T2 với 1.5× cost → hypothesis đủ strong để test capped paper.
Nếu PASS chỉ với 1.0× maker cost → halt hypothesis đến khi có live calibration.
```

### Tests

```text
[T-R7.1] VIP0 default: Maker = +0.02% (no rebate), Taker = +0.05% → verified vs Binance account API
           KHÔNG dùng -0.01% maker rebate cho VIP0 USDT-M perps (xem WARNING dòng trên)
           Edge case test: inject rebate tier (VIP4+) → round_trip_cost giảm → verify monotonic
[T-R7.2] impact_bps increases với Q/V ratio (monotonic)
[T-R7.3] Bars trong funding blackout → penalty applied
[T-R7.4] Calibration: inject synthetic fills → update adverse_selection
[T-R7.5] surprise_funding != shift(funding_rate, 1) (phải từ premium index)
[T-R7.6] Family 3 hypothesis với 1.0× maker cost PASS nhưng 1.5× FAIL → blocked flag set
```

### Provides to

M-R3 (T0), M-R4 (T1), M-R5 (T2), M-R6 (backtest)

---

## M-R8: Factor Neutralization

**Phase:** Build Phase 1 | **TIER-A**

### Purpose

Loại beta exposure khỏi signals. Đảm bảo IC đo lường genuine alpha, không phải market beta được disguise.

### Components

```text
1. BTC Beta Neutralization
   Rolling OLS, 21-day window:
     beta_btc[t] = OLS(symbol_return, btc_return, window=21d)
     neutral_return[t] = symbol_return[t] - beta_btc[t] × btc_return[t]

   Kill signal nếu: R² (symbol vs BTC) > 0.60 trước neutralization
     → signal chủ yếu là BTC beta, không phải alpha

2. ETH Beta Neutralization (sau BTC)
   Same method, applied on BTC-neutral residuals

3. Cross-sectional Sector Demeaning
   Sectors: L1, L2, DeFi, Meme, RWA, AI (manual classification, update quarterly)
   sector_neutral_signal[t] = signal[t] - mean(signal trong cùng sector, tại t)

4. Aggregate Funding Beta
   funding_neutral_return[t] = return[t] - beta_funding × mean_funding_rate_universe[t]
   Lý do: nhiều "alpha" trong funding family thực chất là aggregate funding exposure
```

### Invariants

```text
[INV-R8.1] Beta computation chỉ dùng data ≤ t (expanding hoặc rolling, không full-sample)
[INV-R8.2] Sau neutralization, IC được tính trên neutral returns (không raw)
[INV-R8.3] R² check trước neutralization (nếu R² > 0.60 → warn + document)
```

### Tests

```text
[T-R8.1] BTC-neutral returns: correlation(neutral_return, btc_return) ≈ 0
[T-R8.2] Rolling beta tại bar T chỉ dùng 21d trailing data (không future)
[T-R8.3] Sector-neutral signals: mean(signal trong sector) ≈ 0
[T-R8.4] Funding alpha: IC trên price_return khác IC trên total_return
```

### Depends on

M-D4 (features with BTC returns)

### Provides to

M-R3 (T0), M-R4 (T1), M-R6 (backtest)

---

## M-R9: Alpha Registry + Cemetery

**Phase:** Build Phase 1 | **TIER-A**

### Purpose

Tracking toàn bộ vòng đời của alpha. Registry là SSOT cho stage transitions. Cemetery là institutional memory để tránh tái phát minh bánh xe.

### Files

```text
nghien_cuu/nha_may_alpha/
  registry.py   — AlphaRecord CRUD, stage transitions
  cemetery.py   — AlphaAutopsy storage + search
  lifecycle.py  — stage gate validation
```

### AlphaRecord Schema

```text
@dataclass(frozen=True)
class AlphaRecord:
  alpha_id:           str     — UUID
  name:               str
  family:             str     — "F", "M", "OB"
  hypothesis:         str     — immutable sau registration
  null_hypothesis:    str     — immutable
  mechanism_tags:     tuple[str, ...]  — ["funding_carry", "mean_reversion", "momentum",
                                          "basis_arb", "oi_signal", "microstructure"]
                                         Dùng cho similarity search dựa trên mechanism,
                                         không chỉ return correlation.
  venue_type:         str     — "agnostic" | "dependent"
  spot_price_source:  str     — declared spot reference (ví dụ: "binance_spot_BTCUSDT")
                                Bắt buộc cho mọi alpha có basis feature. None nếu không dùng basis.
  registered_at:      datetime
  features_used:      tuple[str, ...]
  asset_ids_in_scope: tuple[str, ...]  — danh sách asset_id (không symbol) trong universe lúc register
  label_horizon_min:  int
  n_trials_at_registration: int  — snapshot của n_trials_total lúc register
  config_hash_at_registration: str  — SHA-256 của experiment config lúc register (từ M-R1)
  stage:              str     — IDEA|SCREENING|PAPER|SHADOW|LIVE|HIBERNATING|RETIRED|KILLED

  # Filled as alpha progresses
  t0_ic:              float | None
  t1_dsr:             float | None
  t1_cv_ic_mean:      float | None
  paper_ic_live:      float | None
  paper_sharpe:       float | None
  live_ic_inception:  float | None
  live_sharpe:        float | None
  retired_at:         datetime | None
  kill_reason:        str | None
```

### Stage Transitions (lifecycle.py)

```text
IDEA → SCREENING:   manual (researcher decision, hypothesis documented)
SCREENING → PAPER:  T0 PASS + T1 PASS + T2 PASS
PAPER → SHADOW:     paper_trading_days ≥ 60 AND paper_ic_absolute ≥ 0.025
                    AND paper_ic ≥ 0.70 × backtest_ic
                    AND paper_sharpe ≥ 0.60 annualized
                    AND paper_ic_min_rolling_10d ≥ 0.015 (IC stable, không chỉ average)
                    
                    [NOTE] Thay đổi từ 30 → 60 TRADING DAYS (không calendar days):
                    Lý do: với 1h rebalancing, effective_n sau autocorr adjustment:
                    30 ngày × 24 bars × (1-autocorr)^2 / halflife ≈ 90 obs — quá ít
                    để reject IC=0 with 95% confidence.
                    60 trading days ≈ 3 tháng, bao phủ ≥ 2 funding cycles + 1 regime shift.
                    
                    Thêm paper_ic_min_rolling_10d ≥ 0.015:
                    IC drift trong paper period là early warning của instability.
                    High average IC che giấu "IC tốt tháng 1, crash tháng 2" pattern.
                    Rolling 10-day IC phải stable, không chỉ overall average phải cao.
                    
                    Thêm paper_ic_absolute ≥ 0.025:
                    Nếu backtest IC bị contaminated (subtle leakage) → 70% × contaminated IC
                    vẫn pass. Absolute floor đảm bảo paper IC genuinely positive.
                    
                    Nếu shadow period "calm market":
                    Extend thêm 30 ngày nếu không có ≥ 1 funding spike (funding_zscore > 2.5)
                    trong toàn bộ paper period. Document trong AlphaRecord nếu skip extension.
SHADOW → LIVE:      shadow_days ≥ 90 AND shadow_sharpe ≥ 0.80 AND max_dd < 15%
                    AND maker_fill_rate_actual ≥ 0.55 BTC/ETH từ shadow fills
                    AND tca_impact_cost_bps < 4.0 average (capacity không exceed)

[DEFINITION] SHADOW = live execution với fixed micro-lot size ($1K–$5K per trade).
  Mục đích: capture REAL adverse selection, queue behavior, và fill rate
  TRƯỚC khi commit full capital.
  SHADOW khác PAPER: SHADOW dùng real orders (không simulated fills).
  SHADOW khác LIVE: SHADOW dùng fixed micro-lot, không scale theo signal strength.
  SHADOW capital: tối đa 0.5% của intended live capital.
  Tại sao cần SHADOW: paper fills không capture queue dynamics, latency jitter thực,
  và exchange throttling behavior — những thứ SHADOW sẽ reveal.
LIVE → HIBERNATING: HARD_DECAY + M-R11 crisis regime (btc_alt_corr > 0.8 OR vacuum)
HIBERNATING → LIVE: IC recover trong reactivation test (10% size, 30 ngày)
HIBERNATING → RETIRED: IC không recover sau max_hibernate_days = 90
LIVE → RETIRED:     alpha_decay_monitor trigger (M-L3, không phải HIBERNATING state) OR manual
any → KILLED:       kill criteria met at any stage (KILLED khác RETIRED — implies bug/leakage)

Transitions phải be logged với timestamp và approver
```

### AlphaCemetery (cemetery.py)

```text
@dataclass
class AlphaAutopsy:
  alpha_id:       str
  name:           str
  kill_stage:     str
  kill_date:      datetime
  kill_reason:    str     — cụ thể, không "poor performance"
  t0_ic:          float | None
  t1_dsr:         float | None
  lesson:         str     — "Crowded signal. OI correlation > 0.6 before kill."

similarity_search(new_hypothesis: str) → list[AlphaAutopsy]:
  Tìm autopsy có hypothesis tương tự (keyword match)
  Dùng trong Stage -1 để tránh reinvent killed ideas
```

### Research Velocity Tracking

```text
Weekly report (ExperimentTracker):
  ideas_generated:   int   — hypotheses trong week
  ideas_t0_killed:   int
  ideas_t1_killed:   int
  ideas_t2_killed:   int
  ideas_to_paper:    int
  kill_rate_t0:      float — target: 85–95%
  kill_rate_t1:      float — target: 60–80%
  ideas_per_week:    float — target: 3–5 T0 screens

Nếu kill_rate_t0 < 70%: T0 threshold quá lỏng → tighten
Nếu ideas_per_week < 3: throughput quá thấp → simplify T0

Family Exhaustion Indicator:
  family_exhaustion_ratio[F] = n_trials_family[F] / max(1, n_t2_pass_family[F])
    n_trials_family:  số lần test trong family F (từ ExperimentRecord)
    n_t2_pass_family: số alphas trong F đã pass T2

  Alert nếu: family_exhaustion_ratio[F] > 20
    → 20 trials nhưng chỉ 1 T2 pass (hoặc 40 trials, 2 pass, v.v.)
    → Family này đang diminishing returns → suggest suspend new hypotheses từ F
    → Require human sign-off để tiếp tục research trong family F
  
  Suspend: không auto-suspend, chỉ flag + report trong weekly velocity report.
  Log per family: exhaustion_ratio, last_t2_pass_date, total_trials_family.
  Lý do: family exhaustion là signal research đang churn cùng ý tưởng với biến thể nhỏ.
    Không phải kill — một số families hồi sinh khi market regime thay đổi.
```

### Tests

```text
[T-R9.1] Stage transition SCREENING → PAPER requires all T0/T1/T2 PASS
[T-R9.2] Hypothesis field immutable sau registration
[T-R9.3] Cemetery similarity search: inject alpha, kill, search → found
[T-R9.4] Stage LIVE alpha có đủ fields (live_ic_inception, live_sharpe)
[T-R9.5] Weekly research velocity report generated mỗi Monday
```

### Depends on

M-R3 (T0 result), M-R4 (T1 result), M-R5 (T2 result)

### Provides to

M-R4 (T1.5 correlation check), M-R5 (T2.7 portfolio fit), M-L3 (decay monitor)

---

## M-R10: Anomaly Miner

**Phase:** Build Phase 1 | **TIER-B** | **MVA:** SKIP — không nằm trên critical path, build sau khi có ≥1 live alpha

### Purpose

Daily automated scan phát hiện market events bất thường. Feed hypothesis generation — không auto-generate hypothesis, chỉ notify human để investigate.

### Input / Output

```text
INPUT:  ho_du_lieu/da_xu_ly/ (daily batch)
OUTPUT: AnomalyReport(date, anomalies: list[AnomalySignal])

AnomalySignal:
  type:      str     — "funding_spike" | "oi_diverge" | "basis_anomaly" | ...
  symbol:    str | None
  metric:    str     — e.g., "funding_rate_zscore"
  value:     float   — observed value
  zscore:    float   — vs 30d history
  timestamp: datetime
```

### Scan Rules

```text
Chạy nightly sau M-D2 (gap reconciliation hoàn tất):

[SCAN-1] Funding Rate Spike
  Alert nếu: funding_rate_zscore_30d > 2.5 cho bất kỳ symbol nào
  Context: symbol, current_funding, historical_mean, zscore

[SCAN-2] OI Divergence
  Alert nếu: oi_change_pct_4h > 3σ (vs 30d history)
  Context: symbol, oi_change, direction

[SCAN-3] Basis Anomaly (cross-exchange)
  Alert nếu: |basis_binance - basis_bybit| > 2σ (vs 7d history)
  Context: symbols, basis_spread, normal_range

[SCAN-4] Cross-Asset Correlation Breakdown
  Alert nếu: rolling_corr(BTC, ETH, 24h) < -0.20 (unusual decorrelation)
  Context: corr_value, 30d_mean_corr

[SCAN-5] Liquidity Collapse
  Alert nếu: spread_bps > 3× median cho top-10 symbols
  Context: symbol, current_spread, normal_spread
```

### Output

```text
Telegram notification với report tóm tắt
Format:
  "🔍 KAIROS Anomaly [{date}]
   FUNDING: ETH +3.2σ (0.12% 8h rate vs 0.04% avg)
   OI: SOL +4.1σ (OI tăng 18% trong 4h)
   BASIS: BTC Binance-Bybit spread 2.8σ"

Human reads → decides whether to generate hypothesis
Module KHÔNG auto-generate hypothesis
```

### Tests

```text
[T-R10.1] Inject funding spike > 2.5σ → alert generated
[T-R10.2] Normal market → 0 alerts (no false positives on calm day)
[T-R10.3] Telegram notification sent (mock in test)
[T-R10.4] Report generated ≤ 10 phút sau M-D2 completion
```

### Depends on

M-D2 (cleaned data), M-D4 (feature cache — z-scores)

### Provides to

Researcher (human loop — anomalies → hypothesis ideas)

---

## M-R11: Market State Engine

**Phase:** Build Phase 1 | **TIER-A** | **Status:** Chưa build

### Purpose

Cung cấp real-time và historical market state vector cho tất cả downstream modules.
Crypto mid-freq alpha không phải die từ từ do IC decay — chúng die đột ngột khi
regime transition xảy ra. Market State Engine là early warning system và risk modifier.

ADX/vol là insufficient. Crypto có nhiều dimension of market state quan trọng hơn.

### Market State Dimensions

```text
Mỗi bar t, M-R11 compute state_vector[t] gồm 8 dimensions:

[STATE-1] Spread Regime
  spread_percentile: percentile của spread_bps trong rolling 30d window
  → normal (<50th), wide (50–80th), very_wide (>80th), crisis (>95th)

[STATE-2] Liquidity Regime (depth-based)
  depth_ratio: effective_depth[t] / median_effective_depth_30d
  → deep (>1.5), normal (0.7–1.5), thin (0.3–0.7), vacuum (<0.3)
  [NOTE] dùng effective_depth = displayed_depth × (1 - spoof_discount)

[STATE-3] Funding Dispersion Regime
  funding_xsec_std: std(funding_rate_universe) tại t
  → low (market consensus), high (dispersion), extreme (potential squeeze)
  Signals: high dispersion → F001/F004 edge tốt hơn; low dispersion → edge kém

[STATE-4] Liquidation Intensity
  liquidation_proxy: |OI_change| khi giá move mạnh (OI drop + price drop = forced close)
  → quiescent, active, cascade (OI drop > 5% trong 1h)
  Cascade state: adverse selection spike 3–5×

[STATE-5] Exchange Fragmentation
  basis_dispersion: std(funding_rate per exchange) across Binance/Bybit/OKX
  → unified (<0.5 bps), fragmented (0.5–2 bps), dislocated (>2 bps)
  F002 edge: cao khi fragmented/dislocated; risk: execution kém khi dislocated

[STATE-6] Realized Correlation Regime
  btc_alt_corr: rolling_corr(BTC_return, mean_alt_return, 24h)
  → low (<0.5), normal (0.5–0.8), crisis_high (>0.8)
  Crisis_high: XS momentum strategies break down (mọi alt move với BTC)

[STATE-7] Stablecoin Stress
  usdt_usdc_depeg: |USDT_price_vs_USD - 1| hoặc |USDC_price_vs_USD - 1|
  → stable (<0.001), stress (0.001–0.005), critical (>0.005)
  Critical: risk override — reduce all positions 50%, halt F002

[STATE-8] Out-of-Distribution Alert (Minimum Viable Regime Novelty)
  Compute: rolling_zscore của [spread, depth_ratio, funding_xsec_std, btc_alt_corr]
  ood_score = mean(|zscore_i| for i in dimensions)
  Alert nếu: ood_score > 2.5 (state vector outside training distribution)
  
  [NOTE] Đây là minimum viable OOD detection, không cần full ML model.
  Đủ để catch major structural breaks không có trong training data.

[STATE-FASTPATH] Extreme Event Fast-Path Detector (sub-bar, real-time)
  Vấn đề: ood_score > 2.5 × 10 ngày là SLOW PATH — không phù hợp cho crypto black swans
  xảy ra trong giờ (Luna 2022: từ $80 → $0 trong 3 ngày; FTX: halt withdrawals trong 24h).

  Fast-path triggers (check MỖI BAR, không phải daily):
    TRIGGER-F1: btc_1h_return_zscore > 4.0σ (vs rolling 30d vol)
      → Đây là 4σ move trong 1 bar — xảy ra < 0.003% thời gian, nhưng là extreme event
      → Action: IMMEDIATE_SCALE: reduce all positions 50% trong bar tiếp theo
    TRIGGER-F2: funding_rate_1settle > 0.2% absolute (≈ 876% APR annualized)
      → Funding extreme → adverse selection spike guaranteed
      → Action: BLOCK new entries trong funding_blackout window, extend blackout 2× 
    TRIGGER-F3: depth_ratio < 0.10 (liquidity vacuum — book 90% thinner than normal)
      → Action: HALT ALL new orders, giữ existing positions (market orders catastrophic)
      → Resume: khi depth_ratio > 0.30 trong 3 bars liên tiếp
    TRIGGER-F4: mark_price / index_price deviation > 1.0% sustained 2 bars
      → Liquidation cascade active
      → Action: BLOCK new longs nếu deviation > 0 (mark > index), BLOCK new shorts nếu < 0

  Fast-path vs Slow-path hierarchy:
    Fast-path: trigger within CURRENT BAR → action trong NEXT BAR
    Slow-path (ood_score > 2.5 × 10d): escalate to HIBERNATE decision
    Fast-path KHÔNG replace slow-path — chúng operate ở different timescales

  Fast-path log requirement:
    Mỗi lần trigger: log {trigger_id, bar_timestamp, trigger_value, action_taken, positions_before, positions_after}
    Review weekly: nếu false positive rate > 2/week → recalibrate threshold
```

### Mode A vs Mode B

```text
[MODE A — Hourly Bar Close (default, batch + backtest)]:
  Compute tất cả 8 dimensions sau khi bar t close.
  Dùng cho: backtesting, research, historical state replay.
  Latency acceptable: up to 5 giây sau bar close.

[MODE B — Sub-Hourly Critical Dimensions (live system only, 5-min interval)]:
  3 dimensions có thể bứt phá nguy hiểm trong < 1 bar và cần real-time override:
  
  STATE-4 (Liquidation Intensity):
    liquidation_proxy_5min = |OI_change_5min| khi |price_change_5min| > 0.5%
    Nếu > cascade_threshold → NGAY LẬP TỨC set liquidation_intensity = "cascade"
    Không đợi hourly bar close — cascade có thể hoàn tất trong 5–10 phút.
  
  STATE-7 (Stablecoin Stress):
    Check USDT/USDC depeg mỗi 5 phút
    Nếu depeg > 0.3% → SET stablecoin_stress = True immediately
    Không đợi bar close (depeg spike + recover trong < 1 bar là phổ biến).
  
  STATE-1 (Spread Regime) — emergency override only:
    Nếu spread_5min > 5× median → SET spread_regime = "crisis" temporarily
    Tự động revert về Mode A state khi spread về < 3× median.
  
  Mode B state overrides Mode A cho risk decisions trong M-L5.
  Mode B output KHÔNG lưu vào Parquet history (ephemeral, không dùng cho backtest).
  Mode A (hourly) là SSOT cho backtesting và research.

[MODE B GAP QUANTIFICATION — bắt buộc trong T2]:
  Mode B tạo asymmetry: live system cắt positions mid-bar khi cascade detected,
  nhưng backtest không thể model điều này (Mode B ephemeral).
  
  Để quantify gap, T2 phải chạy thêm Scenario C — "Cascade Exit":
    Lấy tất cả bars lịch sử có liquidation_intensity = "cascade" (từ M-R11 historical)
    Trong Scenario C: force exit positions tại open của bar tiếp theo sau cascade bar
    So sánh: Sharpe_standard vs Sharpe_cascade_exit
    
  Gap metric: cascade_impact = (Sharpe_standard - Sharpe_cascade_exit) / Sharpe_standard
  
  Document gap trong T2Result:
    cascade_exit_sharpe: float    — Sharpe sau forced exit tại cascade bars
    cascade_frequency:  float    — tần suất cascade bars trong 2-năm sample
    cascade_impact_pct: float    — % Sharpe degradation từ Mode B behavior
  
  Kill nếu: cascade_impact > 0.30 (Mode B cuts > 30% Sharpe → live performance
  materially worse than backtest → alpha not viable under realistic live conditions)
  
  [NOTE] Scenario C là proxy. Thực tế live: Mode B triggers sau 5-min check,
  không ngay tại bar open. Actual gap ≈ 50–70% của Scenario C gap.
```

### Output Schema

```text
market_state_vector[t]:
  timestamp:              datetime
  spread_regime:          str    — "normal"|"wide"|"very_wide"|"crisis"
  liquidity_regime:       str    — "deep"|"normal"|"thin"|"vacuum"
  funding_dispersion:     float  — cross-sectional std of funding
  liquidation_intensity:  str    — "quiescent"|"active"|"cascade"
  exchange_fragmentation: str    — "unified"|"fragmented"|"dislocated"
  btc_alt_corr:           float  — 24h rolling correlation
  stablecoin_stress:      bool   — True nếu USDT/USDC depeg > 0.1%
  ood_score:              float  — out-of-distribution severity
  ood_alert:              bool   — ood_score > 2.5

Lưu vào: ho_du_lieu/trang_thai_thi_truong/{date}.parquet
```

### Integration với các modules khác

```text
M-R7 (Cost Model):
  adv_sel_multiplier = regime_multiplier(funding_dispersion, spread_regime)
  liquidity_vacuum = depth_ratio → liquidity_discount
  Truyền state_vector[t] vào round_trip_cost_bps() computation

M-R4 (T1 Validate):
  ic_by_market_state: compute IC cho mỗi combination của spread_regime × funding_dispersion
  Kill nếu: IC negative trong BOTH (thin liquidity) AND (high funding dispersion)

M-R5 (T2 Stress):
  stress test trên liquidation_cascade periods (thay vì chỉ named events)

M-L3 (Decay Monitor):
  Decay trong state "btc_alt_corr > 0.8" = regime-specific, không signal decay
  → trigger HIBERNATE, không KILL

M-L5 (Risk Gate):
  ood_alert → reduce all positions 25%
  stablecoin_stress → override all risk limits 2×
  liquidation_cascade → block new entries, manage exits only
```

### Invariants

```text
[INV-R11.1] state_vector[t] chỉ dùng data ≤ t (PiT — rolling windows)
[INV-R11.2] Tất cả thresholds (spread_percentile=80th, ood_score=2.5) phải được
            commit vào research.yaml TRƯỚC khi M-R11 đi vào production
[INV-R11.3] ood_score dùng rolling 30d mean/std (không full-sample)
[INV-R11.4] Stablecoin depeg check phải query composite price (≥2 sources)
[INV-R11.5] state_vector lưu vào disk mỗi bar, không recompute on-the-fly
            (cần cho backtesting reproducibility và lineage tracking)
```

### Tests

```text
[T-R11.1] Inject Luna crash period → stablecoin_stress=True, liquidation_cascade → detected
[T-R11.2] Inject wide spread day → spread_regime="crisis"
[T-R11.3] OOD: inject state vector outside training range → ood_alert=True
[T-R11.4] PiT: state_vector[t] không thay đổi khi extend data đến t+100
[T-R11.5] Integration: M-R7 nhận adv_sel_multiplier từ M-R11 đúng cách
```

### Depends on

M-D2 (cleaned data), M-D3 (universe — cho funding_dispersion), M-D4 (features)

### Provides to

M-R4 (regime-conditional IC), M-R5 (T2 stress), M-R7 (dynamic cost), M-L3 (hibernate trigger), M-L5 (risk override)

---

---

# LAYER 3: LIVE CORE

---

## M-L1: Paper Trade + Fill Capture

**Phase:** Đã build ~95% | **TIER-A**

### Purpose

Realistic paper trading simulation. Capture fills data cho cost model calibration. Bridge từ research sang live.

### Mid-Freq Execution Simulation — Đã Build

```text
[NOTE — cho người đọc plan]: Paper trade engine đã có đầy đủ mid-freq execution simulation.
Không cần build thêm module riêng.

Đã implement trong:
  paper_ems_adapter.py (37KB):
    - Maker fill probability: P(fill | queue_position, spread, volatility)
    - Queue delay estimate: time-in-queue model based on order book depth
    - Cancel latency simulation: round-trip latency per exchange

  microstructure_model.py:
    - Adverse price move before fill: 500ms short_return model
    - Market regime: CALM / VOLATILE / ILLIQUID → adjusts fill probability
    - Self-impact decay: residual_impact_bps sau large orders

  shock_simulator.py:
    - Stress scenario injection: funding spike, liquidity vacuum, cascade

Cái này cover đầy đủ: queue delay, maker fill probability, adverse move before fill,
cancel latency — đúng những gì cần cho mid-freq backtest validation.
```

### Fill Capture Schema

```text
fills_log/{alpha_id}/{date}.parquet

Schema:
  fill_id:               str
  alpha_id:              str
  asset_id:              str       — UUID từ M-D3 (không phải symbol string)
  symbol:                str       — display only
  side:                  str       — "buy" | "sell"
  size_usd:              float64
  fill_price:            float64
  intended_price:        float64
  slippage_bps:          float64   — (fill - intended) / intended × 10000 × side
  is_maker:              bool
  fill_time:             datetime
  signal_time:           datetime
  order_submit_time:     datetime  — khi order được gửi đến exchange (mới thêm)
  latency_ms:            float64   — signal_time to fill_time
  adverse_sel_5min:      float64   — price move 5 min after fill (signed)
  market_state:          str       — spread_regime tại thời điểm fill (từ M-R11)
  
  # TCA Decomposition (bắt buộc — không optional)
  tca_signal_mid:        float64   — mid_price tại signal_time
  tca_order_mid:         float64   — mid_price tại order_submit_time
  tca_timing_cost_bps:   float64   — (tca_order_mid - tca_signal_mid) × direction × 10000
  tca_impact_cost_bps:   float64   — (fill_price - tca_order_mid) × direction × 10000 - fee_bps
  tca_total_cost_bps:    float64   — fee + tca_timing_cost + tca_impact_cost
```

### TCA Monitoring (mỗi 100 fills)

```text
Aggregate per alpha, per symbol_tier, per market_state:
  mean_timing_cost_bps:  → nếu > 2 bps: investigate signal generation latency
  mean_impact_cost_bps:  → nếu > 3 bps: reduce position size 20% cho tier đó
  fill_rate_maker:       → nếu < 0.55 (BTC/ETH): trigger cost model recalibration
  opportunity_cost_bps:  → nếu > 5 bps: signal halflife ngắn hơn estimate

Action triggers tự động:
  impact > 3 bps sustained 200 fills → position_size_limit × 0.80
  fill_rate_maker < 0.45 → urgency_threshold giảm 0.10 (taker nhiều hơn)
  timing_cost > 3 bps → alert: signal-to-order latency investigation needed
```

### Slippage Tracking

```text
Sau mỗi 100 fills:
  mean_slippage_maker: float  — vs cost_model estimate
  mean_slippage_taker: float
  adverse_selection_realized: float  — mean(adverse_sel_5min)
  fill_rate_maker: float      — fills / orders attempted as maker

Alert nếu:
  mean_slippage > 2× cost_model estimate → calibrate M-R7
  fill_rate_maker < 0.50 → execution quality issue
  adverse_selection_realized > 8 bps maker → adverse selection underestimated
```

### Paper vs Live IC Parity Gate

```text
Sau 30 ngày paper trade:
  paper_ic_live = IC tính từ actual fills (realized PnL vs signal)
  backtest_ic = IC từ T2

Gate: paper_ic_live ≥ 0.70 × backtest_ic AND paper_sharpe ≥ 0.60
  Pass → proceed to shadow/tiny live
  Fail → investigate:
    - Feature drift? (M-L2 check)
    - Cost model too optimistic? (calibrate M-R7)
    - Signal decay? (M-L3 check)
    - Execution issue? (slippage too high)
```

### Tests

```text
[T-L1.1] Fill capture schema: tất cả fields present, không null
[T-L1.2] slippage_bps computed correctly (verified manually)
[T-L1.3] adverse_sel_5min: price move 5 min sau fill, signed by direction
[T-L1.4] Paper IC ≈ backtest IC (trong 40%) cho dummy alpha
[T-L1.5] Slippage alert triggered khi inject synthetic high slippage fills
```

### Depends on

M-R5 (T2 PASS), M-R7 (cost model), M-L5 (risk gate)

### Provides to

M-L2 (execution parity), M-L3 (IC decay), M-R7 (cost calibration)

---

## M-L2: Execution Parity Monitor

**Phase:** Build Phase 2 | **TIER-A**

### Purpose

Verify live signals == research signals. Feature drift là silent killer — alpha dies không phải do signal decay mà do computation drift.

### Daily Checks

```text
For each feature in feature_list:
  live_value:     từ live feature engine (M-D4 online path)
  research_value: batch recompute từ same raw data

  diff = |live_value - research_value|
  pct_diff = diff / |research_value|

  Alert nếu: pct_diff > 0.01 (1%) cho bất kỳ feature nào
  Critical nếu: pct_diff > 0.10 (10%) → pause alpha immediately
```

### Weekly Checks

```text
For each feature:
  KS test: live_distribution (last 30 bars) vs baseline_distribution (first 90 days)
  Alert nếu: KS p-value < 0.05

  signal_direction_distribution: fraction long vs short vs flat
  Alert nếu: ratio thay đổi > 30% vs paper period
```

### Alert Levels

```text
OK:       diff < 1%, KS p > 0.10
WARNING:  diff 1–10%, KS p 0.05–0.10 → log, monitor
ALERT:    diff > 10% → pause alpha, investigate
CRITICAL: live == 0 khi research != 0 → pipeline broken, halt immediately
```

### Root Cause Taxonomy

```text
Nếu feature drift detected, check theo thứ tự:
  1. Exchange API format change → M-D1 parser broken
  2. Normalization window difference → online vs offline logic diverge
  3. Symbol mapping change → wrong symbol being used
  4. Timestamp alignment issue → bars not aligned correctly
  5. NaN handling difference → online vs offline handle missing differently
```

### Tests

```text
[T-L2.1] Inject 5% difference vào live feature → WARNING
[T-L2.2] Inject 15% difference → ALERT + alpha paused
[T-L2.3] KS test với drifted distribution → p < 0.05 detected
[T-L2.4] Daily report generated và logged
```

### Depends on

M-D4 (offline feature cache), live feature engine (M-D4 online)

### Provides to

M-L3 (IC decay — để phân biệt signal decay vs feature drift)

---

## M-L3: Alpha Decay Monitor

**Phase:** Build Phase 2 | **TIER-A**

### Purpose

Phát hiện alpha decay sớm. Distinguish giữa: signal truly decaying vs feature drift vs cost model underestimate.

### Metrics Tracked (rolling 30 days)

```text
ic_live_rolling:    spearman(signal, realized_return), rolling 30d
ic_live_inception:  IC từ khi go live (reference)
sharpe_rolling_30d: annualized Sharpe, rolling 30d
slippage_trend:     regression slope của slippage_bps over time
feature_drift_flag: từ M-L2 (có drift không?)
```

### Alert Thresholds + Hibernate Mode

```text
[SOFT_DECAY] ic_live_rolling < 0.50 × ic_live_inception (10+ ngày):
  Action: scale down 25%, increase monitoring frequency
  Investigate: M-L2 feature drift? Cost model drift?

[HARD_DECAY] ic_live_rolling < 0.25 × ic_live_inception (14 ngày liên tiếp):
  [KHÔNG AUTO-KILL — check M-R11 market state trước]
  Nếu M-R11: btc_alt_corr > 0.80 (crisis correlation) hoặc liquidity_regime = "vacuum":
    → HIBERNATE (không KILL): giảm position về 0, nhưng GIỮ alpha trong registry
    → Hibernate conditions: scale to 0%, set hibernate_until = current_date + 21 days
    → Reactivate check: sau 21 ngày, nếu M-R11 state normalize → test với 10% size
    → Nếu IC recover trong 30 ngày paper → reactivate fully; nếu không → RETIRE
    Lý do: crypto alpha có mùa vụ. Funding alpha tắt trong ranging market,
    hồi sinh khi uptrend quay lại. Kill vĩnh viễn = mất alpha "đang ngủ".
  
  Nếu M-R11: market state bình thường:
    → HARD_KILL: kill alpha, update M-R9 stage = RETIRED
    → Post-mortem: mandatory (decay nguyên nhân gì nếu market bình thường?)

[CROWDING_SIGNAL] corr(signal, OI_change) > 0.60 (14 ngày):
  Action: scale down 50%, add to AlphaAutopsy.kill_reason
  Investigate: are we seeing crowding?

[EXECUTION_SATURATION] slippage_trend slope > 0 significantly (p < 0.05, 30 ngày):
  Action: pause, recalibrate cost model
  Investigate: is capacity exceeded?

[REGIME_NOVELTY] M-R11 ood_score > 2.5 (≥ 3 ngày liên tiếp):
  Action: scale all alphas xuống 50% (portfolio-wide, không per-alpha)
  Reason: out-of-distribution market state — mọi backtest assumption có thể invalid
  Resume: khi ood_score < 1.5 trong 5 ngày liên tiếp
```

### Alpha Stage trong Hibernate

```text
M-R9 AlphaRecord stages bổ sung:
  LIVE → HIBERNATING: khi HARD_DECAY nhưng regime = crisis
    hibernate_start:   datetime
    hibernate_reason:  str  — "btc_alt_corr_crisis" | "liquidity_vacuum" | ...
    hibernate_until:   date  — estimated reactivation check date
  HIBERNATING → LIVE: khi IC recover trong reactivation test
  HIBERNATING → RETIRED: khi IC không recover sau max_hibernate_days = 90
```

### Decay Root Cause

```text
Decay detected → run diagnosis:
  1. Check M-L2 (feature drift) → nếu có drift → likely execution issue, not signal
  2. Check regime (M-D4) → regime thay đổi → regime obsolescence
  3. Check slippage trend → increasing → crowding/saturation
  4. Check correlation vs OI change → crowding indicator
  5. Check BTC beta drift → hidden beta exposure?
```

### Online Adaptation — Retrain Trigger Policy

```text
Crypto alpha decay nhanh (1–6 tháng). Không có adaptive lifecycle → alpha chết
trước khi system phản ứng. Retrain policy bắt buộc:

Champion/Challenger Framework:
  - champion: current deployed model
  - challenger: model retrained trên recent data
  
  Retrain trigger (bất kỳ điều kiện nào):
    (a) SOFT_DECAY sustained 7+ ngày
    (b) Monthly scheduled retrain (calendar-based)
    (c) Regime shift detected (ADX cross threshold 7+ bars)

  Retrain process:
    1. Extend training window: thêm recent live data vào train set
       [INV] Không retrain trên holdout period
    2. Run M-R1 (trainer) → new model artifact với timestamp
    3. Paper trade challenger trong 21 ngày (không kill champion)
       [MINIMUM 21 NGÀY — không giảm xuống dù áp lực operational]
       Lý do: với 4h bar signals (signal_halflife ≈ 3–5 bars = 12–20h),
       21 ngày = ~120 bars → đủ independent predictions để detect IC divergence.
       7 ngày chỉ cho 42 bars — power gần 0 để reject null hypothesis "v1 = v2".
    4. Compare: challenger_ic_21d vs champion_ic_last30d
       Promote nếu: challenger IC ≥ champion IC × 0.90
       Kill challenger nếu: challenger IC < champion IC × 0.75
    5. Log promotion event trong M-R9 (model version history)

  Hard rules:
    - Không auto-promote challenger mà không có human sign-off
    - Không retrain để "fix" a kill decision (nếu alpha killed → cemetery)
    - Mỗi retrain = +0 DSR n_trials (vì không thay đổi hypothesis)
    - Retrain chỉ được extend training data, KHÔNG thay đổi features hoặc hyperparameters
      → thay đổi features = new experiment = n_trials += 1
    
    [INV-L3-RETRAIN.1] Training data cutoff = current_bar - horizon_bars (HARD RULE):
      Lý do: bars [cutoff+1, current_bar] có forward return labels chưa fully realized.
      Nếu retrain include unrealized labels → look-ahead leak trong retrain cycle.
      AUDIT: sau mỗi retrain, verify training_set.last_bar < current_bar - horizon_bars.
      Ví dụ: horizon = 4h = 4 bars (1h bars), bar hiện tại = bar 1000
             training cutoff phải ≤ bar 996 (không phải bar 999 hoặc 1000)
      [NOTE] M-R2 audit KHÔNG catch leak này vì M-R2 chạy trên research data,
             không phải live retrain cycle. INV-L3-RETRAIN.1 phải được verify
             bằng assertion trong Trainer.fit() khi mode = "retrain_live".

  Rollback: nếu promote và performance drop ngay → revert champion trong 24h
```

### Scheduled T2 Re-validation

```text
[CRITICAL] Alpha pass T2 ≠ alpha valid forever. Market structure thay đổi → T2 assumptions expire.

Trigger re-validation (bất kỳ):
  (a) Scheduled: mỗi 6 tháng calendar (tính từ ngày T2 lần cuối pass)
  (b) OOD alert: M-R11 ood_score > 2.5 sustained ≥ 10 ngày liên tiếp

Re-validation process:
  1. Lấy most recent 2-year window (PiT-safe, không overlap với original T2 train)
  2. Chạy đầy đủ T2: stress test + walk-forward + cost model + fill simulation
  3. Giữ nguyên: original BacktestConfig (không thay đổi thông số để "make it pass")

Kết quả:
  PASS: log T2_revalidation_date + T2_revalidation_result trong AlphaRecord
  FAIL: → SOFT_DECAY (không immediate kill) + mandatory investigation
    Investigation: so sánh regime distribution của 2-year window mới vs original T2
    Nếu regime drift → regime obsolescence (không signal decay)
    Nếu signal decay trong same regime → genuine decay → escalate to HARD_DECAY path

[NOTE] Re-validation KHÔNG thay đổi n_trials_total (không phải new hypothesis).
T2 thất bại trong re-validation không trigger DSR adjustment.
```

### Tests

```text
[T-L3.1] SOFT_DECAY: inject ic_live = 0.45 × ic_inception × 10 ngày → scale 25%
[T-L3.2] HARD_DECAY: inject ic_live = 0.20 × ic_inception × 14 ngày → kill
[T-L3.3] CROWDING: inject corr(signal, OI) = 0.65 → alert
[T-L3.4] Daily IC computed correctly từ fills
[T-L3.5] Retrain trigger: SOFT_DECAY 7 ngày → challenger created, không kill champion
[T-L3.6] Challenger IC < 75% champion → challenger killed, champion retained
```

### Depends on

M-L1 (fills — realized IC), M-L2 (feature drift flag), M-R9 (alpha registry)

---

## Alert Management — Fatigue Prevention

**Phase:** Build Phase 2 (trước khi có live fills) | **TIER-A**

### Vấn đề

17 risk checks × N alphas × M symbols → dễ dàng 50–100+ alerts/ngày nếu không có routing policy.
Solo operator = single point of failure → alert đêm mà không có severity tiering = burnout hoặc bỏ qua.

### Alert Severity Routing

```text
CRITICAL  → Telegram tức thì (24/7, không suppress)
  Điều kiện: bất kỳ điều kiện HALT nào trong M-L5 (RG-1 đến RG-17)
             dead-man switch fire (RG-15)
             position desync > 1% (RG-11 imbalance)
             exchange withdrawal freeze signal (RG-17)
             pipeline crash (live == 0 khi research != 0)
  Format:  "[🔴 HALT] RG-4 PnL circuit breaker | daily_pnl=-6.2% | Action: halt all orders"
  Yêu cầu: human response trong 15 phút (nếu không → watchdog flatten)

ALERT     → Telegram tức thì (trong giờ trading: 00:00–20:00 UTC)
  Điều kiện: effective_leverage > 1.8 (approaching limit)
             feature drift pct_diff > 10% (M-L2 ALERT)
             ADL rank top-5% (RG-16)
             crowding signal: pre_entry_drift_bps > 1.5 (sustained)
             IC SOFT_DECAY triggered (30d IC < 50% inception)
  Format:  "[🟠 ALERT] M-L2 feature drift | funding_zscore pct_diff=12.3% | Alpha: F001"
  Yêu cầu: human review trong 2 giờ

WARNING   → Daily digest (aggregated, không real-time)
  Điều kiện: feature drift 1–10% (M-L2 WARNING)
             clock drift > 500ms (M-D2)
             cancel rate > 15% trong 1 giờ (RG-14 sub-threshold)
             ICIR warn (T1.1b warn < 1.5 khi paper trade IC computed)
             symbol coverage < 95% ngày hôm nay (M-D2)
  Format:  Daily digest lúc 07:00 UTC: "[📋 DAILY] 3 WARNINGs: [list]"
  Yêu cầu: review buổi sáng, không urgent

INFO      → Log file only (không Telegram)
  Điều kiện: normal order fills, daily IC report, regime state update
             gate 1→2 checklist progress, backtest completion
```

### Suppression Rules

```text
Same-source suppression:
  Nếu cùng alert type + cùng source (alpha/symbol/check) fire trong vòng 5 phút:
  → Suppress duplicate, chỉ fire lần đầu
  → Exception: CRITICAL không bao giờ suppressed

Flood protection:
  Nếu > 5 ALERT trong 10 phút → aggregate thành 1 "[🟠 ALERT FLOOD] N alerts trong 10 min"
  → Gửi summary, suppress individual alerts
  → Điều này thường báo hiệu systemic issue, không phải nhiều independent events

Cool-down sau HALT:
  Sau khi HALT cleared và resume → suppress tất cả sub-CRITICAL alerts 30 phút
  Lý do: resume period thường noisy, alert storm ngay sau resume = false positives
```

### Daily Digest Format (07:00 UTC)

```text
[📋 KAIROS Daily | 2026-05-22]
Portfolio:
  Daily PnL:   +0.42% | Weekly: +1.8%
  Positions:   F001 BTCUSDT +$12K | F003 ETHUSDT -$8K
  Leverage:    1.3× gross, 0.2× net

Alpha Health:
  F001: IC_30d=0.031 (121% inception) ✅ | Fills: 23 maker (67% rate) ✅
  F003: IC_30d=0.024 (96% inception) ⚠️  | Fills: 11 maker (52% rate) ⚠️

Warnings (3):
  - [M-D2] Bybit SOLUSDT coverage 93.1% (target 95%)
  - [M-L2] F001 funding_zscore drift 4.2% (below ALERT threshold)
  - [RG-14] F003 cancel rate 13% trong 14:00–15:00 UTC window

System:
  Data pipeline: OK | Feature engine: OK | WAL: 4.8MB | Uptime: 99.9%
```

### Tests

```text
[T-ALERT.1] CRITICAL alert → Telegram gửi trong 30 giây
[T-ALERT.2] Same alert 2 lần trong 3 phút → 2nd suppressed
[T-ALERT.3] 6 ALERT trong 8 phút → flood protection kích hoạt
[T-ALERT.4] Daily digest generated lúc 07:00 UTC chính xác
[T-ALERT.5] WARNING không gửi Telegram real-time, chỉ vào digest
```

---

## M-L4: Portfolio Construction (ERC)

**Phase:** Build Phase 3 | **TIER-A (khi có 2+ alphas)**

### Purpose

Combine multiple alphas thành portfolio signal với equal risk contribution. Không fancy optimizer ở Phase 3.

### Alpha Combination Logic (combination_engine.py)

```text
combination_engine.py nhận N alpha signals → output 1 combined signal per symbol per bar.

Method: IC-weighted average (Phase 3 default)
  weight_i = max(0, rolling_ic_21d_alpha_i) / sum(max(0, rolling_ic_21d_alpha_j) for j)
  combined_signal[s,t] = sum(weight_i × signal_i[s,t] for i in active_alphas)
  
  Lý do chọn IC-weighted vs simple average:
    - IC-weighted tự động down-weight alphas đang decay (rolling IC giảm → weight giảm)
    - Ít sensitive hơn ERC trong Phase 3 khi số alpha ít (2-3)
    - Nếu alpha IC âm → weight = 0 (không đảo chiều signal của alpha decay)

Signal concentration check TRƯỚC khi gửi order:
  Sau khi combine, check combined signal concentration:
    For each symbol: |combined_signal[s]| / sum(|combined_signal[s]| for all s)
    Nếu bất kỳ symbol vượt 40% total signal weight → scale xuống 40%, phân phối lại
  Lý do: F001 + F003 cùng react với funding → combined có thể overweight BTC/ETH

Correlated alpha safeguard:
  Nếu T1.5 check: corr(signal_i, signal_j) > 0.60 → combined_signal bị shrink:
    effective_alpha_count = N / (1 + mean(pairwise_corr))
    combined_signal_shrunk = combined_signal × min(1, sqrt(effective_alpha_count / N))
  Lý do: correlated alphas F001 + F003 tạo combined overshoot khi cùng direction

Fallback nếu rolling IC không đủ (< 21 ngày data): dùng equal weight.

[INV-L4-COMB.1] combined_signal không được NaN nếu ≥1 active alpha có signal
[INV-L4-COMB.2] weight_i chỉ dùng historical IC (không future IC) — PiT safe
[INV-L4-COMB.3] combined_signal logged cùng với individual alpha_i signals cho attribution
```

### Equal Risk Contribution (ERC)

```text
Với N alphas, ERC weights:
  σ_i = rolling_vol(alpha_i, window=21d)
  w_i = (1/σ_i) / sum(1/σ_j for j in 1..N)

Mỗi alpha contribute equal volatility đến portfolio.
Không correlation optimization (Phase 3).
Thêm MVO/Black-Litterman chỉ khi có 4+ live alphas.
```

### Constraints

```text
gross_leverage ≤ 2.0
net_leverage   ≤ 0.5
single_alpha   ≤ 35% portfolio weight
sector         ≤ 40% concentration
daily_turnover ≤ 20% notional (budget constraint)

BTC beta của portfolio: |beta_portfolio| ≤ 0.30
  Nếu drift trên 0.30 → rebalance hoặc hedge
```

### Turnover Budget

```text
Nếu ERC weights imply > 20% daily turnover:
  Scale down position changes: Δw_actual = Δw_desired × min(1, budget / Δw_desired_total)
  Ưu tiên: alpha với highest marginal Sharpe contribution
```

### Cross-Alpha Dependency Monitoring

```text
2 alphas "uncorrelated trên returns" vẫn có thể:
  - Crash cùng nhau khi crowding event xảy ra
  - Compete cho cùng liquidity pool (shared symbols)
  - Consume chung inventory capacity

Weekly cross-alpha dependency check:
  1. Correlation matrix của returns (rolling 21d): alert nếu bất kỳ pair > 0.60
  2. Shared symbol overlap: fraction of positions in same symbols
     Alert nếu overlap > 50% (alphas competing for same liquidity)
  3. Turnover netting: nếu alpha A long X và alpha B short X → net out
     actual_turnover = sum(|net_position_change|), không phải sum(|gross|)
     Savings từ netting phải được credit back vào cost budget

Nếu cross-alpha correlation > 0.70 sustained 14 ngày:
  → Scale xuống alpha có lower marginal Sharpe
  → Document correlation regime trong M-R9

Cross-alpha crowding contagion trigger:
  Nếu M-L3 detect SOFT_DECAY trên 2+ alphas đồng thời (cùng 7-day window) →
  Flag: crowding contagion event (không phải signal-specific decay)
  Action: reduce all affected alphas 25%, hold investigation
```

### Portfolio-Level Capacity Check

```text
[CRITICAL — Cross-Alpha Aggregate Capacity]:
Mỗi alpha có thể pass T2.6 capacity check riêng lẻ, nhưng khi nhiều alphas cùng
hold positions trong cùng symbol → aggregate capacity có thể exceed true liquidity.

Bắt buộc check sau mỗi bar:
  For each symbol s in active positions:
    aggregate_exposure[s] = sum(|position_alpha_i[s]| for all active alphas i)
    true_liquidity[s] = M-D4/M-R7 effective depth estimate
    capacity_utilization[s] = aggregate_exposure[s] / true_liquidity[s]
  
  Alert nếu: capacity_utilization[s] > 0.05 (5% true liquidity)
    → Block new entries cho symbol s cho đến khi aggregate < 4%
  Critical nếu: capacity_utilization[s] > 0.08
    → Reduce existing positions proportionally để bring < 5%

Lý do: mỗi alpha model capacity = 5% true_liquidity. Với 3 alphas cùng đánh BTC → 15%.
Unwind scenario: nếu cần exit nhanh → 15% trên cùng venue = significant market impact.
[NOTE] Capacity check phải tính NET position nếu các alpha đi ngược chiều nhau
(alpha A long BTC, alpha B short BTC → net exposure gần 0, không cộng absolute).
```

### Family Concentration Monitor

```text
[CRITICAL] Nhiều alphas cùng một family (F001, F002...) có correlated edge → concentrated risk.
Nếu family edge decay → toàn bộ family fail cùng lúc.

Family Concentration Cap:
  family_exposure[F] = sum(|alpha_weight_i| for alpha_i in family F)
  
  Alert nếu: family_exposure[F] > 60% portfolio weight
    → Block new LIVE promotions trong family F cho đến khi < 50%
    → Scale xuống alpha có lowest marginal Sharpe trong F
  Lý do: 60% ≠ single_alpha ≤ 35% — nhưng nếu 2 alphas F001 + F001-variant = 70% thì
    hidden concentration (chúng cùng fail khi F001 edge tắt).

Portfolio-Wide Family IC Kill Trigger:
  family_ic_30d[F] = mean(rolling_ic_30d[alpha_i] for alpha_i in family F and stage = LIVE)
  
  Kill trigger: family_ic_30d[F] < 0.010 trên ALL live alphas trong F đồng thời (30 ngày)
    → Signal: toàn bộ family edge đã decay, không phải per-alpha noise
    → Action: move tất cả alphas trong F sang SOFT_DECAY simultaneously
    → Flag trong M-R9 as "family_edge_exhaustion" event (không phải per-alpha decay)
  
  [NOTE] IC kill trigger chỉ fire khi TẤT CẢ live alphas trong family fail cùng lúc.
  Nếu chỉ 1/3 alphas trong family fail → per-alpha SOFT_DECAY path (không phải family kill).
```

### Funding Drag (mandatory) + Cross-Margin Leverage Check

```text
Nếu strategy hold perp positions:

  [CRITICAL — Settlement-Aligned Funding, không per-bar approximation]:
  Funding chỉ settle MỖI 8H tại 00:00, 08:00, 16:00 UTC. Charge funding sai thời điểm
  sẽ bias toàn bộ backtest (overcounting = kill alpha tốt; undercounting = live worse).

  Rule cứng trong backtest và M-R6 vectorized engine:
    Funding cost CHỈ được charge tại bar t NẾU:
      (1) funding_rate[t] IS NOT NULL  (= settlement bar)
      VÀ (2) position[t] != 0         (open trước settlement)
      VÀ (3) position[t-1] != 0       (chưa close trước settlement)
    
    Nếu position open 01:00 UTC và close 07:00 UTC → KHÔNG bị charge funding 08:00.
    Nếu position open 07:30 UTC và vẫn open 08:00 UTC → bị charge funding 08:00.

  funding_charge[t] = |position[t]| × funding_rate[t]  IF điều kiện trên đúng, ELSE 0

  funding_drag_period = sum(funding_charge[t] for t in all bars)
  
  [NOTE] Dùng realized_funding_rate (funding_rate[t] từ INV-D1.5), không expected rate.
  funding_rate_expected từ Premium Index MA có thể sai khi cần nhất (volatile periods).
  Report cả: gross Sharpe, net-of-cost Sharpe, net-of-cost-and-funding Sharpe.
  Portfolio return net = gross - funding_drag_period - cost

KHÔNG report gross Sharpe mà không có funding drag

[CRITICAL — Cross-Margin Leverage Monitoring]:
Funding rate được trừ TRỰC TIẾP từ margin balance trong crypto perps.
Nếu nhiều alphas cùng hold vị thế bị funding âm → free collateral giảm liên tục,
NGAY CẢ KHI giá không thay đổi → gross_leverage effective tăng lên.

Bắt buộc kiểm tra mỗi bar:
  funding_drain_1h = sum(|position_size[i]| × funding_rate[i]) for i in all_positions
  free_collateral = total_capital - sum(|position_size[i]| × initial_margin_req[i])
  effective_leverage = sum(|position_size|) / (free_collateral - funding_drain_1h × 24)
  
  Alert nếu: effective_leverage > 1.8 (approaching 2.0 limit)
  Halt nếu: effective_leverage > 2.1 (exceeded limit due to funding drain)
  Action: reduce positions proportionally để bring effective_leverage ≤ 1.5
```

### Crowding Monitor — Upgrade to TIER-A

```text
[NOTE] Crowding monitor (crowding_monitor.py) được nâng từ TIER-B lên TIER-A Phase 1.

Lý do: trong crypto perp, alpha decay chủ yếu do crowding, không phải signal staleness.
Deferring đến "after 2 live alphas" là quá late — crowding xảy ra từ PAPER stage.

TIER-A crowding_monitor.py (thêm vào Phase 1, nghien_cuu/danh_gia/):

Weekly cross-alpha dependency check (đã có):
  correlation matrix, symbol overlap, turnover netting

Bổ sung — Crowding Pre-entry Detection (mới):
  Compute: realized_slippage_direction_bias[t-10, t-1]
    = mean(signed_price_move_5min_before_fill × fill_direction)
  Nếu bias > 0 liên tục: "bạn đang bị front-run"
  
  Crowding proxy bổ sung:
    pre_entry_drift_bps = mean(mid_price_move_5min_before_signal) × signal_direction
    Alert nếu: pre_entry_drift_bps > 1.5 bps (sustained 10 fills)
    Lý do: nếu market đã move 1.5 bps trong hướng signal trước khi bạn gửi order
            → signal đã được discovered bởi faster players

  Cross-family crowding contagion (đã có trong plan):
    Nếu SOFT_DECAY trên ≥ 2 alphas đồng thời → crowding event flag
    Action: reduce all affected alphas 25%, hold investigation
```

### Tests

```text
[T-L4.1] 2 alphas với khác vol → weights inversely proportional to vol
[T-L4.2] gross_leverage ≤ 2.0 luôn enforced
[T-L4.3] BTC beta của portfolio ≤ 0.30 sau ERC
[T-L4.4] Turnover budget: scale down khi cần
[T-L4.5] Funding drag included trong return calculation
```

### Depends on

M-L3 (active alphas), M-R7 (cost model — funding drag), M-L5 (risk gate)

---

## M-L5: Risk Gate (Pre-trade)

**Phase:** Đã build ~70% | **TIER-A**

### Purpose

Hard stop trước khi lệnh được gửi. Bảo vệ capital khỏi bugs, model errors, và extreme scenarios.

### Pre-trade Checks (theo thứ tự)

```text
[RG-1] Notional Check
  Reject nếu: order_size_usd > max_order_size_usd (config per alpha)
  Default max: $50K per order

[RG-2] Portfolio Leverage
  Reject nếu: new_gross_leverage > 2.0 sau order
  Reject nếu: new_net_leverage > 0.5 sau order

[RG-3] Single Name Concentration
  Reject nếu: new_position_symbol > 20% portfolio

[RG-4] PnL Circuit Breaker
  Reject nếu: daily_pnl < -5% portfolio value
  Reject nếu: weekly_pnl < -10% portfolio value
  Action: halt all new orders, alert, human review

[RG-5] State Staleness
  Reject nếu: last_feature_update > 5 phút ago
  Lý do: stale signals → wrong decisions

[RG-6] Feature Parity Alert (từ M-L2)
  Reject nếu: M-L2 status = CRITICAL
  Halt nếu: M-L2 status = ALERT
```

### Missing Risk Checks (thêm vào Phase 2)

```text
[RG-7] Stuck Order Detection
  Nếu open order chưa fill sau max_open_time (default 5 phút maker, 30s taker):
    Cancel order
    Log: symbol, side, size, elapsed_time, reason="timeout"
    Alert nếu cancel rate > 20% trong 1 giờ (signal stale hoặc book thin)

[RG-8] Partial Fill State Machine
  States: PENDING → PARTIAL → FILLED | CANCELLED | TIMEOUT
  PARTIAL fill: recalculate remaining size vs signal
    Nếu signal vẫn valid → send remainder
    Nếu signal flip → cancel remainder, hold partial
  Track partial fill ratio per symbol → alert nếu > 40% fills là partial

[RG-9] Exchange Failure Handling
  Khi exchange API down (timeout > 3 lần liên tiếp):
    Immediate halt: không gửi lệnh mới
    DO NOT cancel open orders without confirmation (có thể đã fill)
    Wait for reconnect → reconcile trước khi resume
    Phân loại: total outage vs partial (WS down, REST up) → xử lý khác nhau

[RG-10] Liquidation Cascade Protection
  Nếu funding_rate > 3× normal (extreme funding event):
    Reduce position size 50% cho symbols bị ảnh hưởng
    Block new positions trong funding window ± 1 giờ
  Nếu mark_price deviation từ index_price > 0.5%:
    Flag: potential manipulation / liquidation cascade
    Halt affected symbol, alert human review

[RG-11] Cross-Exchange Inventory Risk + F002 Hedge Gap Protection
  Track net exposure per symbol across all exchanges (nếu multi-exchange)
  Reject nếu: hedged position imbalance > $10K (one leg fills, other pending)
  Alert nếu: exchange rejects order due to margin insufficiency
  
  [F002 SPECIFIC — max_hedge_gap_seconds]:
  Khi F002 (cross-exchange funding arb) enter leg A:
    max_hedge_gap_seconds = 30 (default)
    Nếu leg B không fill trong max_hedge_gap_seconds sau leg A fill:
      → Cancel leg A IMMEDIATELY (unhedged exposure không acceptable)
      → Log: leg_a_asset, leg_a_fill_price, leg_b_cancel_reason
      → Alert: execution quality issue, investigate exchange B latency
    
    Exchange freeze protection (FTX-pattern):
    Maintain min 20% unencumbered cash at EACH exchange (không chỉ tổng).
    Nếu exchange B margin < 20% → block F002 new entries cho leg B.
    Forced cover trigger: nếu exchange B withdrawal freeze flagged (RG-17):
      → Close leg A immediately (accept unhedged loss, không giữ exposure)
    
  [INV-RG11.1] Sau mỗi bar, verify: |position_A + position_B| < hedge_tolerance (0.5%)
               Nếu |imbalance| > 1% → ALERT + halt new F002 entries

[RG-12] Borrow Availability Check
  Trước khi short spot: query available borrow size
  Reject nếu: available_borrow < 120% of intended short size
  Track borrow rate spike: nếu rate > 3× baseline → alert, review short thesis
  Forced close trigger: nếu borrow recalled → cover within 1 bar

[RG-13] Inventory Skew Management
  Nếu một symbol chiếm > 60% realized PnL (positive hoặc negative) trong 7 ngày:
    Flag: inventory concentration
  Target inventory profile: không có symbol nào dominant trong PnL attribution
  Skew metric: HHI (Herfindahl-Hirschman Index) trên |pnl_per_symbol|
    HHI > 0.30 → warn (1 symbol = 30%+ của tổng)
    HHI > 0.50 → alert + reduce position của symbol dominant 25%
  Lý do: skewed inventory = unintended single-name bet, không phải systematic alpha

[RG-14] Cancel/Replace Storm Prevention
  Cancel storm: > N cancels trong T giây = likely algo bug hoặc signal flip-flopping
  Threshold: > 10 cancels/min cho 1 symbol → pause trading symbol đó 5 phút
  Threshold: > 30 cancels/min across all → halt, alert (potential runaway loop)
  Root cause logging: mỗi cancel phải có reason code (timeout, signal_flip, risk_reject)
  Review trigger: nếu cancel_rate > 15% of orders trong 1 giờ → investigate signal quality

[RG-15] Dead-Man Switch
  Nếu không nhận được heartbeat từ main process trong max_silence_seconds (default 300s):
    Watchdog process (independent) → cancel tất cả open orders
    Flatten tất cả positions tại market (không maker)
    Lock trading: không cho phép mở orders mới cho đến khi human restart
  Heartbeat design: main loop ghi timestamp vào file mỗi 30s
  Watchdog check: separate process đọc file mỗi 60s
  Lý do: nếu main process crash silent, positions open không có ai manage = unlimited risk
```

[RG-16] ADL (Auto-Deleveraging) Risk Monitor
  Perp futures: khi position có ADL rank cao + thị trường extreme, exchange
  có thể force-close position (ADL) không qua margin call thông thường.
  
  Alert nếu: ADL rank của bất kỳ position nào trong top-10% (exchange ADL indicator)
  Action nếu ADL rank top-5%:
    Reduce position 30% (không đợi margin call)
    Block new entries cho symbol đó
  Lý do: ADL xảy ra bất ngờ, không có cancel hoặc warning — position biến mất.

[RG-17] Counterparty (Exchange) Solvency Monitor
  Không để > 20% total capital tại một exchange bất kỳ tại mọi thời điểm.
  Daily check: exchange health indicators:
    - Withdrawal processing time (alert nếu > 2× baseline)
    - Exchange insurance fund size trend (alert nếu giảm > 15% trong 7 ngày)
    - On-chain reserve proof (nếu exchange publish)
  FTX pattern flag: halt nếu:
    - Multiple large withdrawal failures reported
    - Native token price crash > 30% trong 24h
    - Exchange Twitter/status page outage patterns
  Action khi flag: initiate withdrawal của 50% balance, halt new entries

### Emergency Actions

```text
Manual kill switch: halt all alphas immediately
Auto-kill triggers:
  - Max DD > 15% (tính từ inception) → halt + alert
  - Exchange API error rate > 10% (5 min window) → halt
  - Position reconciliation fail > 2 consecutive checks → halt
  - mark_price / index_price spread > 1% sustained 5 min → halt + alert
  - Funding rate > 5× normal → pause new entries, alert
  - ADL rank top-5% → reduce + block (RG-16)
  - Exchange solvency flag triggered → partial withdrawal + halt (RG-17)

Escalation: halt → alert → manual review → resume (no auto-resume)
```

### Recovery Protocols — Sau Mỗi Loại Halt

```text
[RECOVERY-1] Max DD > 15%
  Halt:   Tất cả new orders bị block. Existing positions maintained (không auto-flatten).
  Wait:   Mandatory cooling-off ≥ 7 ngày.
  Review: Postmortem bắt buộc: DD do signal decay, regime shift, hay cost model sai?
  Resume: 
    Bước 1: Paper trade ≥ 14 ngày với SAME alpha (không chỉnh sửa)
    Bước 2: Nếu paper IC ≥ 70% backtest IC → resume tại 25% size
    Bước 3: Scale lên 50% sau 14 ngày nếu live IC ≥ inception IC × 0.70
    Bước 4: Full size sau thêm 21 ngày nếu tiếp tục ổn định
    Kill thay vì resume: nếu postmortem cho thấy structural edge loss

[RECOVERY-2] Exchange API Outage
  Halt:   Không gửi orders mới. Giữ nguyên positions.
  Wait:   Reconnect confirmed (REST + WS cả hai stable ≥ 5 phút).
  Review: Reconcile positions (REST query) vs local state trước khi bất kỳ order nào.
  Resume:
    Bước 1: Verify |local_position - exchange_position| < 0.1% cho mỗi symbol
    Bước 2: Verify feature pipeline nhận data mới (last_feature_update < 5 phút)
    Bước 3: Resume normal trading — không cần ramp-up (outage ≠ signal decay)
    Block: Nếu outage > 4 giờ → verify không có missed fills → manual review trước resume

[RECOVERY-3] Feature Drift CRITICAL (M-L2 status = CRITICAL)
  Halt:   Block new orders cho alpha bị ảnh hưởng. Existing positions maintained.
  Wait:   Tối thiểu 48 giờ sau khi drift source được identify.
  Review: Tìm nguyên nhân: data schema change? OI source thay đổi? Normalization drift?
  Resume:
    Bước 1: Fix drift source → re-validate feature parity (live == backtest)
    Bước 2: Paper trade ≥ 7 ngày để confirm feature drift đã fix
    Bước 3: Resume full size nếu M-L2 status = OK ≥ 7 ngày liên tiếp
    Kill: Nếu drift không thể fix (data source thay đổi vĩnh viễn) → retire alpha

[RECOVERY-4] Stablecoin Depeg
  Halt:   Halt tất cả new entries. Flatten positions nếu position USDT-denominated > $50K.
  Wait:   Depeg resolution (USDT peg < 0.1% lệch khỏi $1.000) sustained ≥ 2 giờ.
  Resume: Resume ngay sau peg restore — không cần ramp-up.
  Monitor: 24 giờ sau resume: check margin calculations vẫn correct (không drift từ depeg event)

[RECOVERY-5] ADL Risk Top-5% (RG-16)
  Halt:   Reduce vị thế bị ảnh hưởng xuống 50% ngay lập tức.
  Wait:   ADL rank thoát top-15% (cải thiện đủ để có buffer).
  Resume: Tăng lại size dần: 50% → 75% → 100% mỗi 4 giờ nếu ADL rank ổn định.

[RECOVERY-6] Rolling 30d IC SOFT_DECAY (< 50% inception, 10+ ngày)
  Halt:   Scale position xuống 25% (không halt hoàn toàn).
  Wait:   14 ngày minimum observation period.
  Review: Compare IC với market regime (M-R11): decay do regime shift hay signal loss?
  Resume to 50%: Nếu IC recover ≥ 60% inception trong 14 ngày
  Resume to 100%: Nếu IC recover ≥ 75% inception trong 21 ngày
  Kill: Nếu IC < 25% inception sustained 14 ngày → HARD_DECAY path (xem M-L3)

[HALT DECISION TREE]:
  Is it infrastructure? (API, feature drift, data) → RECOVERY-2 hoặc RECOVERY-3
  Is it market condition? (depeg, ADL) → RECOVERY-4 hoặc RECOVERY-5
  Is it signal quality? (DD, IC decay) → RECOVERY-1 hoặc RECOVERY-6
  Never conflate: infrastructure halt ≠ signal decay → recovery path khác nhau
```

### Spot Price Reference — System Invariant

```text
[CRITICAL — Feature Parity Risk]:
perp_spot_basis_bps = (perp_price - spot_price) / spot_price × 10000

Spot price source PHẢI được declare explicitly:
  Spot source: Binance Spot (BTCUSDT perpetual reference)
  Không dùng Coinbase, Kraken, hay OKX Spot mà không declare rõ ràng
  
Lý do critical:
  BTC spot price varies across exchanges: Binance vs Coinbase có thể differ 0.1–0.5%
  trong stressed markets. Nếu backtest dùng Binance spot nhưng live query
  Coinbase spot → feature drift ngay từ ngày 1, silent và persistent.

Invariants:
  [INV-L5-SP.1] spot_source phải declared trong research.yaml và feature_lineage (M-D0)
  [INV-L5-SP.2] Live và backtest phải dùng SAME spot_source (verified by M-L2)
  [INV-L5-SP.3] Nếu spot_source thay đổi (exchange thêm/bỏ) → dataset_id mới,
                n_trials += 1 cho mọi hypothesis dùng basis feature
  [INV-L5-SP.4] Composite spot (weighted average ≥ 2 exchanges) là BETTER PRACTICE
                nhưng phải consistent: same weight formula live và batch
  [INV-EXC.1]  Mọi exchange-specific constant (min_order_size, fee_tier, funding_schedule)
                phải reference cau_hinh/exchange_metadata.yaml — không hardcode trong adapter code
```

### Position Reconciliation

```text
Hourly: compare local position state vs exchange position
If |local - exchange| > tolerance (0.1%) for any symbol:
  Alert + log discrepancy
  Do NOT auto-fix (manual review)
  Halt new orders for that symbol until resolved

Exchange desync recovery protocol:
  Step 1: query exchange REST (not WS — WS may be stale)
  Step 2: compare vs local state
  Step 3: if diff → log both states, compute diff
  Step 4: human decision required → no automated position reset
  Lý do: automated reset có thể double-execute nếu exchange lag
```

### Tests

```text
[T-L5.1] Order khi gross_leverage = 1.9 → pass; khi = 2.1 → reject
[T-L5.2] Daily PnL = -6% → all orders rejected, alert sent
[T-L5.3] Stale features (6 min) → orders rejected
[T-L5.4] M-L2 CRITICAL → orders halted
[T-L5.5] Position reconciliation: inject discrepancy → alert generated
```

### Depends on

M-L2 (parity monitor), M-L4 (portfolio state)

---

---

# ALPHA TAXONOMY

**IC Calibration Note (quan trọng):**

```text
IC expectations trong bảng dưới là gross IC (trước cost), trên 5-fold PurgedKFold.

Benchmarks thực tế trong crypto mid-freq:
  IC > 0.03 stable across regimes  → viable (meet minimum T1 bar)
  IC > 0.05 sustained over 6+ months → very good, consider live
  IC > 0.08 sustained                 → exceptional, rare

Các khoảng IC cao (0.08–0.10) trong Expected IC column là ASPIRATIONAL, không phải minimum.
Nếu hypothesis đạt IC 0.04–0.05 stable + DSR > 0.5 → đủ để paper trade.
Không nên kill hypothesis chỉ vì IC < upper bound trong bảng.
```

---

## Family 1: Funding Dislocation (Priority 1 — Phase 2)

Structural edge, ít crowded ở mid-freq, data quality tốt.

| ID | Hypothesis | Horizon | Expected IC | Features |
| -- | ---------- | ------- | ----------- | -------- |
| F001 | Perp funding > threshold → mean reversion của price | 1–4h | 0.04–0.08 | funding\_rate, funding\_zscore |
| F002 | Cross-exchange funding divergence Binance vs Bybit | 30min–2h | 0.05–0.10 | funding\_binance, funding\_bybit, basis |
| F003 | OI spike → predict funding spike (lead indicator) | 15min–1h | 0.03–0.06 | oi\_change\_1h, funding\_rate |
| F004 | Funding-adjusted cross-sectional rank (momentum net of carry) | 1–4h | 0.03–0.05 | return\_4h\_btc\_neutral, funding\_rate |

**venue\_type:** F001/F003/F004 = "agnostic" | F002 = "dependent" (cross-exchange)

**Cost note:** Funding carry positions hold overnight → borrow cost phải included trong T2.

---

## Family 2: OI-Weighted XS Momentum (Priority 2 — Phase 2)

Standard signal, edge đến từ OI-weighting + BTC-neutralization.

| ID | Hypothesis | Horizon | Expected IC | Features |
| -- | ---------- | ------- | ----------- | -------- |
| M001 | 1h return XS momentum, weighted by OI | 30min–2h | 0.03–0.05 | return\_1h\_btc\_neutral, oi |
| M002 | Volume-adjusted relative strength | 1–4h | 0.03–0.05 | return\_4h\_btc\_neutral, volume\_ratio\_24h |
| M003 | Momentum post-funding extreme (mean reversion delayed) | 1–4h | 0.04–0.07 | return\_1h\_btc\_neutral, funding\_zscore |

**venue\_type:** "agnostic" — cross-exchange validation required

**Listing cohort filter:** exclude symbols listed < 30 ngày (listing pump distorts momentum)

---

## Family 3: OB Microstructure Aggregated (Priority 3 — Phase 3+)

Chỉ research sau khi có live fills từ Family 1/2 để calibrate adverse selection.

| ID | Hypothesis | Horizon | Expected IC | Features |
| -- | ---------- | ------- | ----------- | -------- |
| OB001 | 5-min OFI cross-sectional rank | 5–30min | 0.04–0.09 | book\_pressure\_5min |
| OB002 | Book imbalance persistence → short-term continuation | 15–60min | 0.03–0.06 | book\_pressure\_5min, spread\_bps |
| OB003 | Spread expansion → volatility prediction | 30min–2h | 0.02–0.04 | spread\_bps |

**Cost note:** Family 3 có adverse selection cao nhất. Cần calibrated cost model trước khi research.

---

## Stage Gate Summary

```text
Stage -1 (≤15 min, NO CODE):
  □ Economic mechanism explainable in 2 sentences?
  □ Cemetery similarity search: không có identical killed alpha
  □ Feature count ≤ 5 (simplicity prior — kill nếu > 5)
  □ Data dependency feasible?
  □ halflife sanity: < 5 bars → caveated, < 2 bars → KILL

Stage 0 (≤30 min, NO CODE):
  □ Hypothesis + null hypothesis documented (immutable)
  □ venue_type declared
  □ Listing cohort filter applied (M family: exclude < 30 days)
  □ Market structure events excluded from sample

Stage 1 = T0 (≤15 min):  [M-R3]
Stage 2 = T1 (≤2 giờ):   [M-R4] — requires M-R2 PASS
Stage 3 = T2 (≤1 ngày):  [M-R5] — requires T1 PASS

Total wall time budget: ≤5 days per idea (bao gồm paper trade gate setup)
Auto-kill nếu vượt quá budget mà không có quyết định rõ ràng
```

---

---

# PHASES

---

## Phase 0 — Foundation (Tuần 1–6)

**Mục tiêu:** Data reliable. Research harness skeleton. Dummy alpha end-to-end.

**Deliverables theo tuần:**

```text
Tuần 1–2: M-D2 validated, M-D3 built, M-R1 (labeler + purged_cv + dsr) built
Tuần 2–3: M-R2 (leakage audit) built, M-R3 (T0) built
Tuần 3–4: M-R6 (vectorized backtest) built, M-R7 (cost model v1) built
Tuần 5–6: Plumbing test với alpha_001_ema_cross
```

**Plumbing test checklist (tuần 5–6):**

```text
□ Load 1 năm clean data top-10 pairs (3 exchanges) — không crash
□ M-R2 audit PASS cho dummy data
□ M-R3 T0 screen chạy ≤15 phút
□ M-R6 backtest chạy ≤60 giây
□ Paper trade 1 tuần — không crash
□ Research IC ≈ Paper IC (trong 40%) — parity check
□ ExperimentRecord saved trước khi backtest chạy
```

**Kill gate:** Nếu data không clean (< 95% coverage) sau 2 tuần → fix data trước, không move on.

---

## Phase 1 — Research Harness Complete (Tuần 6–12)

**Mục tiêu:** T0/T1/T2 hoàn chỉnh. Feature store ready. Family F sẵn sàng screen.

**Deliverables:**

```text
Tuần 6–7:  M-D4 (feature cache) built + populated cho Family 1+2 features
Tuần 7–8:  M-R4 (T1) built, M-R7 cost model v2 (với spoof discount + funding blackout)
Tuần 8:    M-R8 (factor neutralization) built
Tuần 9:    M-R9 (alpha registry + cemetery) built
Tuần 10–11: M-R5 (T2) built với stress test periods
Tuần 11–12: M-R10 (anomaly miner) built + first week of daily scans
```

**Phase 1 Done khi:**

```text
□ T0 ≤ 15 phút, T1 ≤ 2 giờ, T2 ≤ 1 ngày
□ M-R1 full (Ridge CV + model registry) operational
□ DSR verified vs reference implementation (paper result)
□ M-R9 registered ≥1 killed alpha (plumbing test kill)
□ Family F001–F004 đã được T0-screened, kết quả documented
□ M-R10 running daily, ≥7 days anomaly reports
```

---

## Phase 2 — Alpha Discovery (Tháng 3–9)

**Mục tiêu:** ≥1 alpha survive T2 + 30 ngày paper trade.

### Live Monitoring Dashboard — Build Trước Khi Có Fills

```text
[BẮT BUỘC] Phải có dashboard trước ngày 1 của paper trade.
Không có dashboard = monitoring bằng cách chạy scripts thủ công = miss anomalies.
Solo operator cần one-screen health view mỗi sáng ≤ 5 phút.

Tools: script Python + rich/tabulate terminal, hoặc Grafana nếu đã có infra.
Default: terminal dashboard (không cần external infra), refresh mỗi giờ qua cron.

─────────────────────────────────────────────
SCREEN 1: HEALTH (nhìn vào buổi sáng — ≤60 giây)
─────────────────────────────────────────────
┌─────────────────────────────────────────────┐
│ KAIROS │ 2026-05-22 07:05 UTC │ LIVE: 1α   │
│─────────────────────────────────────────────│
│ PORTFOLIO                                   │
│  PnL today:  +0.42%  │ Week: +1.8%          │
│  Gross lev:   1.3×   │ Net:   0.2×          │
│  Free coll:  $48K    │ Funding drain: -$12/h │
│─────────────────────────────────────────────│
│ ALPHA STATUS                                │
│  F001 [LIVE]   IC_30d=0.031 ✅  fills=23   │
│  F003 [PAPER]  IC_30d=0.024 ⚠️  fills=11   │
│─────────────────────────────────────────────│
│ SYSTEM                                      │
│  Pipeline: OK │ Feature: OK │ WAL: 4.8MB   │
│  Last fill: 14 min ago │ Open orders: 2     │
│─────────────────────────────────────────────│
│ ALERTS (0 CRITICAL, 3 WARNING)              │
│  [W] Bybit SOL coverage 93% │ [see digest] │
└─────────────────────────────────────────────┘

─────────────────────────────────────────────
SCREEN 2: ALPHA DETAIL (nhìn khi có vấn đề)
─────────────────────────────────────────────
Per-alpha metrics (refresh daily):
  IC series (last 30d):       spark-line hoặc tabular
  IC vs inception:            current / inception (%) → ≥70% target
  Paper vs backtest IC:       ratio → ≥70% target
  Fill rate maker:            actual vs target (≥0.55 BTC/ETH gate)
  Slippage vs cost model:     actual / model (≥2× → pause)
  TCA decomposition:          timing_cost / impact_cost / fee split
  Signal direction:           % long / short / flat vs paper baseline

─────────────────────────────────────────────
SCREEN 3: COST & EXECUTION (nhìn hàng tuần)
─────────────────────────────────────────────
Weekly TCA report:
  total_round_trip_cost_bps:   actual vs model
  adverse_selection_bps:       actual vs model (update research.yaml khi gap > 30%)
  maker_fill_rate:             by symbol, by hour-of-day
  urgency_score_distribution:  fraction maker vs taker trades
  cancel_rate:                 by symbol (alert if > 15%)

─────────────────────────────────────────────
SCREEN 4: REGIME & MARKET STATE (nhìn hàng tuần)
─────────────────────────────────────────────
M-R11 state_vector (last 7d):
  regime:          trending / ranging / stressed (most common this week)
  ood_score:       max this week (alert if > 2.5 on 3+ days)
  btc_alt_corr:    rolling 7d (alert if > 0.80 — crisis mode indicator)
  funding_extreme: any day with |funding_zscore| > 2.5?

─────────────────────────────────────────────
METRICS KHÔNG ĐƯA VÀO DASHBOARD (chống gamification)
─────────────────────────────────────────────
  ✗ Unrealized PnL per position (chỉ xem khi cần investigate — không daily)
  ✗ Sharpe (quá noisy ở time scales ngắn — weekly là minimum meaningful)
  ✗ Max drawdown real-time (gây panic, chỉ compute sau close of day)
  Lý do: nhìn unrealized PnL minute-by-minute = emotional trading, không systematic

Dashboard implementation priority:
  Week 1 của paper trade: Screen 1 (Health) + Alerts
  Week 2: Screen 2 (Alpha Detail)
  Week 4+: Screen 3 (TCA) sau khi có ≥50 fills
  Month 2+: Screen 4 (Regime) sau khi M-R11 đã running
```

**Research rhythm (hàng tuần):**

```text
Thứ 2:   Generate 3–5 hypotheses (1 family, không mix)
          Stage -1 check ngay (15 min): cemetery search, simplicity prior
Thứ 2–3: T0 screen survivors
Thứ 3–4: T1 validate T0 survivors
Thứ 5:   T2 diligence nếu T1 pass
Thứ 6:   Document vào M-R9, update research velocity report
```

**Cross-exchange validation (venue\_type = "agnostic"):**

```text
Sau T2 PASS: cross-exchange IC check
  ic_bybit / ic_binance > 0.70 → validate, agnostic confirmed
  ic_bybit / ic_binance ≤ 0.70 → re-classify as "dependent" hoặc KILL
  Lý do: agnostic alpha phải work cross-venue, không phải Binance-specific
```

**Phase 2 Done khi:**

```text
□ ≥10 ideas T0-screened (đa số bị kill — bình thường và tốt)
□ ≥1 idea pass T2 (Scenario_A ≥ 0.80 AND Scenario_B ≥ 0.75, ir_vs_benchmark ≥ 0.20)
□ ≥1 alpha in paper trade ≥ 60 trading days (không phải calendar days)
□ Paper IC ≥ 70% backtest IC AND paper_ic_absolute ≥ 0.025
□ Paper rolling 10d IC không drop dưới 0.015 bất kỳ window nào
□ M-R7 calibrated từ paper fills (adverse_selection updated, TCA decomposed)
□ Maker fill_rate xác nhận ≥ 0.55 BTC/ETH từ ≥ 100 paper fills
□ M-R11 Market State Engine operational (state_vector lưu daily)
□ crowding_monitor.py running weekly (không phát hiện crowding signal trước shadow)
```

---

## Phase 3 — Live Validation (Tháng 6–15)

**Mục tiêu:** Tiny live → full live. Portfolio 2–3 signals.

**Tiny live protocol:**

```text
Week 1:   0.1% intended size — test execution path only
Week 2–4: 1% nếu execution clean (slippage < 2× cost model)
Month 2:  10% nếu IC không degrade > 30%
Month 3+: Full size theo ERC weights (M-L4)
```

**M-L1 paper-to-live parity requirement:**

```text
paper_ic_live ≥ 70% backtest_ic AND paper_sharpe ≥ 0.60 (sau 60 trading days paper)
paper_ic_absolute ≥ 0.025 (floor — không phụ thuộc backtest IC quality)
paper rolling 10d IC ≥ 0.015 mọi window (stability check)
Nếu 70–85% IC parity: monitor closely, investigate cost model
Nếu < 70%: KILL, investigate leakage hoặc cost model
```

**Phase 3 Done khi:**

```text
□ 1 alpha live > 60 ngày, IC không decay (M-L3)
□ Live Sharpe ≥ 0.70 (annualized)
□ Cost model calibrated từ actual fills (M-R7 updated)
□ M-L2 parity monitor operational
□ M-L3 decay monitor operational
□ M-L4 ERC built (nếu có 2+ alphas)
□ Position reconciliation verified daily (M-L5)
```

---

## Phase 4 — HFT Preparation (Tháng 12–24, conditional)

**Prerequisite cứng:** ≥2 live alphas profitable ≥3 tháng. Không start sớm hơn.

**Decision framework (trả lời trước khi build bất kỳ thứ gì):**

```text
Q1: Exchange co-location available và affordable?
    → cost < 5% expected annual PnL
    → exchange có maker rebate tier cao với co-location
    → Nếu không: sub-second strategies không viable → SKIP Phase 4

Q2: Current mid-freq alphas co-location sensitive?
    → Test: same strategy từ VPS gần exchange vs xa
    → Nếu không sensitive: mid-freq IR tốt mà không cần co-location
    → Nếu sensitive: quantify IR improvement vs cost

Q3: Family 3 (OB) signals viable sau full cost (sub-second)?
    → IC > 0.06 sau adverse selection + co-location cost?
    → Nếu không: OB signals không profitable, skip
```

**Nếu proceed:**

```text
M-H1: Event-Driven Simulator
  Stateful backtest với queue position model
  Binance latency tiers: remote 50ms, optimized 15ms, co-located 3ms
  Viability threshold: Sharpe drop ≤ 40% khi latency = 15ms

M-H2: Hot Path Extraction
  Extract feature computation sang C extension (cffi wrapper trên ctypes logic)
  Order book state → C struct (192 bytes, 20-level L2, zero-copy ZMQ)
  Signal serialization → msgpack (không JSON trên hot path)
```

---

---

# KILL CRITERIA

---

## Research Kill

| Condition | Stage | Action |
| --------- | ----- | ------ |
| Stage -1: > 5 features | IDEA | Kill immediately |
| Stage -1: identical to cemetery alpha | IDEA | Kill, log similarity |
| T0: IC < 0.025 | SCREENING | Kill, log to cemetery |
| T0: cost > 40% gross IC | SCREENING | Kill, log reason |
| T1: ICIR < 1.0 | SCREENING | Kill, IC không consistent |
| T1: DSR ≤ 0.50 | SCREENING | Kill, log n\_trials |
| T1: any regime IC < -0.010 | SCREENING | Kill, investigate regime |
| T1: correlation ≥ 0.60 vs existing | SCREENING | Kill, redundant |
| T2: Sharpe\_A < 0.80 OR Sharpe\_B < 0.75 | RESEARCH | Kill — dual fill gate |
| T2: ir\_vs\_benchmark < 0.20 | RESEARCH | Kill — likely beta, not alpha |
| T2: WF IC std > 0.50 × mean | RESEARCH | Kill, unstable |
| T2: negative in both Luna + FTX | RESEARCH | Kill |
| Paper: trading_days < 60 OR IC < 0.025 absolute | PAPER | Extend paper, không promote |
| Paper: IC < 70% backtest IC OR paper Sharpe < 0.60 | PAPER | Kill, investigate |
| Paper: rolling 10d IC dưới 0.015 bất kỳ window nào | PAPER | Kill, unstable IC |

## Live Kill / Hibernate

| Condition | M-R11 Market State | Action |
| --------- | ------------------ | ------ |
| Rolling 30d IC < 50% inception (10+ ngày) | Bất kỳ | Scale to 25%, investigate |
| Rolling 30d IC < 25% inception (14 ngày) | CRISIS (btc_alt_corr > 0.8 OR vacuum) | HIBERNATE 21 ngày |
| Rolling 30d IC < 25% inception (14 ngày) | BÌNH THƯỜNG | Kill, retire to M-R9 |
| M-R11 ood_score > 2.5 (3+ ngày) | N/A | Scale all alphas 50%, portfolio-wide |
| Live max DD > 15% | Bất kỳ | Kill immediately, halt all |
| Maker fill_rate thực tế < 0.55 BTC/ETH (100 fills) | Bất kỳ | HARD GATE: recalibrate M-R7 trước shadow |
| Slippage > 2× cost model | Bất kỳ | Pause, calibrate M-R7 + TCA decompose |
| M-L2: feature drift CRITICAL | Bất kỳ | Halt, investigate pipeline |
| Exchange API changes strategy behavior | Bất kỳ | Pause, assess |
| HIBERNATING alpha: IC không recover sau 90 ngày | N/A | RETIRE permanent |

## Project Kill

```text
Sau 9 tháng không có alpha nào pass T2:
  → Strategic pivot: đổi alpha family
  → Re-assess: data quality (hidden leakage?)
  → Re-assess: hypothesis generation process
  → Không build thêm infrastructure
  
Sau 6 tháng không có T1 pass:
  → Review cost model — có thể quá conservative
  → Review IC threshold — có thể quá strict cho tập data
  → Review hypothesis originality
```

---

---

# VERIFICATION GATES

---

## Gate 0 → 1

```text
□ Data coverage ≥ 95% daily, top-10 pairs, 3 exchanges, ≥1 năm
□ M-D0: dataset_id tracking operational (backtest logs dataset_id_used)
□ M-D0: as_of_snapshot exists cho toàn bộ research period
□ M-D0: spot_price_source declared trong feature lineage
□ M-D2: gap reconciliation running nightly
□ M-D3: PiT universe validated (no look-ahead in 5 spot checks)
□ M-D3: asset_id assigned cho tất cả symbols (không join on symbol string)
□ M-D3: ticker collision test: LUNA old ≠ LUNA new (khác asset_id)
□ M-D4: burn-in period enforced — NaN returned cho bars < min_periods
□ M-D4: INV-D4.9/10/11: OI source declared trong lineage, live=backtest source verified
□ M-D4: INV-D4.12: funding interpolation method declared trong research.yaml
□ M-D4: INV-D4.13: feature parity — live imports từ cùng module với batch (single function)
□ M-D4: INV-D4.14: cold start NaN verified — signal = NaN (không phải 0) trong burn-in
□ M-D4: T0 subset mode operational (top-10, 6 months, on-the-fly)
□ M-R1: Ridge CV chạy end-to-end (no errors)
□ M-R1: config_hash auto-computed, ExperimentRecord rejected nếu thiếu
□ M-R1: DSR dùng n_trials_total (verified vs n_trials_family để không undercount)
□ M-R1: DSR verified vs reference (known input → known output)
□ M-R1: Label BTC-neutral verified (neutral_label_ic ≠ raw_label_ic — chúng phải khác)
□ M-R2: leakage audit PASS trên synthetic clean data (tất cả 10 checks)
□ M-R2: AUDIT-8 test: inject future-listed symbol vào XS mean → FAIL
□ M-R2: AUDIT-10 test: inject next_funding_rate API → FAIL
□ M-R3: T0 dummy alpha ≤ 15 phút (subset mode) + ≤ 15 phút (full M-D4)
□ M-R6: backtest 2 năm ≤ 60 giây (dùng dataset_id, không "current")
□ M-R6: DUAL SCENARIO: fill_probability_maker logged cho BOTH optimistic + conservative
□ M-R6: execution_lag_bars=1 set, execution_price="open_next" (không fill tại bar close)
□ M-R7: Binance fee = +0.02% maker (verified vs account API, không hardcode)
□ M-R7: adverse_selection regime multiplier integrated (không static 4 bps)
□ M-L1: paper trade 1 tuần không crash
□ M-L1: paper IC ≈ research IC (trong 40%)
□ M-L1: TCA fields present trong fill schema (tca_timing_cost, tca_impact_cost)
```

## Gate 1 → 2

```text
□ [NULL HYPOTHESIS VALIDATION — chạy một lần trước khi bắt đầu nghiên cứu thực]:
  Mục đích: xác nhận screening pipeline đủ strict, không pass random noise.
  
  Step 1: Generate 100 random signals (seed=99 từ research.yaml, không tune)
    random_signal[s,t] = random.normal(0, 1, size=(n_symbols, n_bars))
  Step 2: Run T0 screen trên tất cả 100 signals
    Expected: ≤5 signals PASS T0 (≤5% pass rate)
    FAIL nếu: > 5 signals PASS → T0 threshold quá lỏng, tighten trước Phase 2
  Step 3: Run T1 trên tất cả T0-passers
    Expected: ≤2 signals PASS T1 (≤2% của 100)
    FAIL nếu: > 2 signals PASS T1 → screening pipeline unreliable
  
  Đây là một lần (one-shot), không repeat. Kết quả log vào ExperimentRecord với
  n_trials += 0 (không count random signals vào n_trials của real hypotheses).
  Nếu FAIL → điều chỉnh thresholds trong research.yaml → rerun → recommend lại.

□ M-D4: feature cache populated, hash-invalidation tested
□ M-D4: feature standardization test: coef_std stable (T1.7 verified)
□ feature_spec.py: mọi feature dùng trong T1 đã có FeatureSpec entry (pit_safe=True verified)
□ M-R4: T1 full pipeline, DSR integrated
□ M-R4: T1.3 regime thresholds committed vào research.yaml TRƯỚC khi run
□ M-R4: T1.7 sử dụng standardized coefficients (verified)
□ M-R4: T1.8 long/short IC asymmetry check operational (ic_long, ic_short logged)
□ M-R5: T2.1 ir_vs_benchmark computed (benchmark = equal-weight PiT universe, kill < 0.20)
□ M-R5: T2.7 capital_efficiency_factor applied (cross-exchange = 0.5)
□ M-R5: T2 với stress test Luna + FTX AND random high-vol (20 periods)
□ M-R5: random_stress_seed documented trong research.yaml (immutable)
□ M-R7: cost model v2 (spoof discount + funding blackout + regime multiplier + vacuum)
□ M-R7: urgency_score logic integrated (dynamic maker/taker)
□ M-R8: factor neutralization verified (neutral return ≈ 0 corr với BTC)
□ M-R9: alpha registry + cemetery operational (asset_id + config_hash fields present)
□ M-R10: anomaly miner running ≥ 7 ngày liên tiếp
□ M-R11: Market State Engine operational — state_vector lưu mỗi bar
□ M-R11: OOD alert test: inject out-of-distribution state → ood_alert=True
□ crowding_monitor.py: running weekly, pre_entry_drift_bps tracked
□ Family F001–F004: T0-screened (cả subset mode VÀ full M-D4), kết quả documented trong M-R9
□ Research velocity: ≥3 T0 screens/week feasible (timing test)
```

## Gate 2 → 3

```text
□ ≥1 alpha pass T2 với BOTH fill scenarios (Scenario_A ≥ 0.80 AND Scenario_B ≥ 0.75)
□ T2.1: ir_vs_benchmark ≥ 0.20 (verified — không phải beta trong bull run)
□ T2.3: random high-vol stress test PASS (≥ 14/20 periods)
□ Cross-exchange validation passed (nếu venue_type = "agnostic")
□ Paper trade ≥ 60 trading days:
    paper IC ≥ 70% backtest IC AND paper IC absolute ≥ 0.025
    paper Sharpe ≥ 0.60 annualized
    rolling 10d IC ≥ 0.015 mọi window (stability)
    ≥1 funding spike event trong paper period (funding_zscore > 2.5 ít nhất 1 lần)
□ Maker fill_rate BTC/ETH ≥ 0.55 từ ≥ 100 fills (confirmed — not assumed)
□ M-R7 calibrated từ paper fills (adverse_selection updated, TCA decomposed)
□ M-R11 Market State Engine: state_vector lưu đầy đủ cho toàn bộ paper period
□ crowding_monitor: no crowding signal (pre_entry_drift_bps < 1.5) trong 30 ngày cuối
□ M-L5 risk gate: all pre-trade checks operational (bao gồm max_hedge_gap_seconds)
□ Stress test: không negative cả Luna lẫn FTX AND random_stress_pass_rate ≥ 0.70
□ Alpha decay monitoring operational (M-L3 với hibernate mode verified)
□ M-L3: INV-L3-RETRAIN.1 enforced — retrain cutoff assertion present trong Trainer.fit()
□ M-L4: portfolio capacity check operational (aggregate ≤ 5% true_liquidity per symbol)
□ M-R11: Mode B operational — 5-min sub-hourly check cho liquidation/stablecoin/spread
□ Spot price reference declared trong research.yaml và M-D0 feature lineage
```

## Gate 3 → 4

```text
□ ≥2 live alphas profitable ≥ 90 ngày
□ Live Sharpe ≥ 0.70 annualized
□ M-L2: parity monitor operational, no ALERT in ≥ 30 ngày
□ M-L4: ERC portfolio live (nếu có 2+ alphas)
□ Co-location decision: written decision (proceed / skip)
□ Sub-second IC > 0.06 sau cost (nếu pursuing HFT)
```

---

---

# KHÔNG BUILD TRONG 12 THÁNG ĐẦU

Mỗi khi có impulse build một trong những thứ này → đọc lại danh sách này và đặt câu hỏi: *"alpha pipeline của tôi đang bị blocked bởi thứ này không?"*

```text
TIER-B (chỉ sau ≥2 live alphas):
  Combinatorial Purged CV (CPCV)     — Purged CV đủ cho Phase 0–2
  Event-driven tick backtest          — vectorized đủ cho mid-freq
  CVXPY optimizer                     — ERC đủ cho 2–3 alphas
  Full covariance + PCA              — Ledoit-Wolf đủ cho Phase 3
  regime_novelty.py (full ML)         — M-R11 OOD score đã cover minimum viable

ALREADY PROMOTED TO TIER-A (không defer):
  crowding_monitor.py                 — Phase 1, xem M-L4 section
  Market State Engine (M-R11)        — Phase 1, xem M-R11 section

POSTPONE đến Phase 4+:
  C/Rust hot path extraction          — sau khi có co-location decision
  Queue position model (full)         — chỉ cần khi halflife < 20 bars + co-located
                                        [NOTE] Queue reset cost ĐÃ được model trong M-R6
                                        Dual Scenario; full queue model chỉ cần cho HFT

DELETE hoàn toàn:
  Transition hazard matrix            — academic, không actionable
  Novelty score engine                — surrogate cho research taste thật
  Alpha causality decomposition       — uninterpretable noise trong crypto
  Alpha economics / ROI engine        — portfolio management, không alpha
  Meta-research analytics             — Two Sigma tooling
  Regime persistence probability      — sample size crypto quá nhỏ
  Dynamic bootstrap block sizing      — stationary assumption violated
  Genetic programming / formula parser — distraction từ hypothesis quality
  WAL cho research environment        — nếu crash, restart
```

---

## Timeline

| Milestone | Optimistic | Realistic | Pessimistic |
| --------- | ---------- | --------- | ----------- |
| Phase 0 complete | 4 tuần | 6 tuần | 10 tuần |
| Phase 1 complete | 8 tuần | 12 tuần | 18 tuần |
| First alpha pass T2 | Tháng 4 | Tháng 6 | Tháng 9 |
| First paper alpha (30d) | Tháng 5 | Tháng 7 | Tháng 11 |
| First live alpha | Tháng 6 | Tháng 9 | Tháng 14 |
| 2+ live alphas | Tháng 10 | Tháng 14 | Tháng 20 |
| HFT phase (conditional) | Tháng 12 | Tháng 18 | Tháng 24+ |

Realistic target: **9 tháng đến first live alpha.**

---

## Rule Quan Trọng Nhất

> Không có new infrastructure commit nào được merge cho đến khi có một named, specific bottleneck trong alpha discovery pipeline bị blocked bởi thiếu infrastructure đó.

PR description phải chứa: *"This unblocks [module/step] for [alpha\_id/hypothesis]."*
Không viết được câu đó → đừng build.

---

Review lại sau Phase 1 complete hoặc sau 3 tháng, tùy cái nào đến trước.
