# KAIROS v3 — Sơ đồ luồng dữ liệu & Workflow

> **Ký hiệu:** ✅ = đã có trong codebase | ❌ = cần build | 🔗 = tái dùng module có sẵn

---

## A. Master Data Flow — Toàn cảnh

```mermaid
flowchart TB
    subgraph SOURCE["☁️ Nguồn dữ liệu"]
        VENDOR["Tardis.dev / Databento\nHistorical tick + klines + L2\n(mua, không tự cào REST)"]
        WS_LIVE["WebSocket Gateway ✅\nbinance_ws / bybit_ws / okx_ws\n→ raw stream nội bộ"]
        REST_FB["REST API ✅\nbinance_rest / bybit_rest\nChỉ dùng làm fallback\nkhi WS bị gap"]
    end

    subgraph INGEST["📦 Ingest Layer ✅"]
        direction TB
        OHLC["xu_ly_dong/bo_loc/ohlc_engine.py"]
        OB["xu_ly_dong/bo_loc/orderbook_engine.py"]
        RAW[("ho_du_lieu/tho/\n*.parquet — raw, immutable")]
    end

    subgraph BATCH_PIPELINE["🔧 Batch Pipeline ❌ (build Phase 1)"]
        direction TB
        DL["xu_ly_lo/downloader.py\nVendor parquet + WS stream merge"]
        RECON["xu_ly_lo/reconcile_gaps.py\nNightly — WS stream primary\nREST fallback nếu WS gap\n⚠️ data_source flag = REST_fallback"]
        CL["xu_ly_lo/cleaner.py\ndedup • gap flag • winsorize features\n⚠️ KHÔNG ffill bar prices/returns"]
        LF["xu_ly_lo/liquidity_filter.py\nL2 depth post-spoofing-discount\nFilter universe TRƯỚC backtest"]
        DREG["xu_ly_lo/dataset_registry.py\nhash chain • lineage • PiT universe\nmarket structure events"]
        CLEAN[("ho_du_lieu/da_xu_ly/\n*.parquet — cleaned + flagged")]
    end

    subgraph FEATURE_LAYER["🔩 Feature Layer"]
        direction TB
        FB["xu_ly_lo/feature_builder.py ❌\nbuild_batch_features() gọi\nCÙNG feature_registry với live"]
        FR["ong_dan_dac_trung/online/feature_registry.py ✅\nBit-exact live và batch"]
        IE["ong_dan_dac_trung/online/incremental_engine.py ✅\n(live realtime)"]
        FEAT[("ho_du_lieu/kho_dac_trung/offline/\nfeatures_*.parquet ❌")]
        MEM[("ho_du_lieu/kho_dac_trung/online/memory_store.py ✅\nlive in-memory")]
    end

    subgraph RESEARCH["🔬 Research Layer ❌ (build Phase 1-3)"]
        direction TB
        LB["hoc_may/huan_luyen/labeler.py"]
        PCV["hoc_may/huan_luyen/purged_cv.py\nPurgedKFold + AnchoredWFO"]
        TR["hoc_may/huan_luyen/trainer.py\nLinear → LightGBM (OOS > 15%)"]
        MODEL[("hoc_may/mo_hinh/\nalpha_model_*.pkl")]
        OX["hoc_may/huan_luyen/onnx_exporter.py\n(sau shadow trade)"]
        ONNX[("thuc_thi_lenh/dong_co_tin_hieu/models/\nalpha_v*.onnx")]
    end

    subgraph BACKTEST["📊 Backtest Layer ❌ (build Phase 1-4)"]
        direction TB
        VBT["nghien_cuu/kiem_thu_qua_khu/ma_tran_sie_toc/\nVectorized Backtest — Polars"]
        CM["nghien_cuu/kiem_thu_qua_khu/ma_tran_sie_toc/cost_model.py\nphase1_cost + transient_impact\nc=0.15, dùng true_liquidity"]
        FILL["moi_truong_chay/paper/microstructure_model.py ✅\nBasic fill simulation — cuối Phase 2\n(halflife < 50 bars = MANDATORY gate)"]
        EBT["nghien_cuu/kiem_thu_qua_khu/mo_phong_su_kien/\nEvent-Driven — Phase 4"]
        RPL["nghien_cuu/dong_co_phat_lai/replay_engine.py\nparquet → ZMQ → production pipeline"]
        EVAL["nghien_cuu/danh_gia/evaluator.py\noverfit_tests.py • alpha_diagnostics.py\nregime_analyzer.py • experiment_tracker.py"]
    end

    subgraph DEPLOY["🚀 Production ✅"]
        direction TB
        SIG["thuc_thi_lenh/dong_co_tin_hieu/ml_signal_engine.py\nONNX inference"]
        EMS["thuc_thi_lenh/dong_co_thuc_thi/ems.py"]
        RG["quan_tri_rui_ro/kiem_tra_truoc_lenh/risk_gate.py\nPre-trade risk — hot path"]
        WD["quan_tri_rui_ro/nguoi_gac_cong/watchdog/watchdog.py\n+ emergency_flattener.py"]
        MON["giam_sat/ ✅ + auto_kill.py ❌\n+ reality_gap_monitor.py ❌"]
    end

    WS_LIVE --> OHLC --> RAW
    WS_LIVE --> OB --> RAW
    VENDOR -->|"historical parquet"| DL
    RAW -->|"WS archive — primary"| RECON
    REST_FB -.->|"fallback only\nflag=REST_fallback"| RECON
    DL --> CL
    RECON --> CL
    CL --> CLEAN
    CLEAN --> LF
    LF -->|"universe sau filter"| DREG
    CLEAN --> FB
    FB -->|"gọi same functions"| FR
    IE -->|"gọi same functions"| FR
    FB --> FEAT
    FEAT --> LB --> PCV --> TR --> MODEL --> OX --> ONNX
    FEAT --> VBT
    CM -->|"true_liquidity cost"| VBT
    VBT -->|"halflife < 50 bars → MANDATORY"| FILL
    FILL -->|"survived fill gate?"| EBT
    EBT --> RPL --> DEPLOY
    VBT --> EVAL
    ONNX --> SIG --> EMS --> RG
    IE --> MEM
    MON -.->|"IC decay kill signal"| SIG

    style SOURCE fill:#1a1a2e,stroke:#e94560,color:#fff
    style DEPLOY fill:#0f3460,stroke:#16213e,color:#fff
    style BATCH_PIPELINE fill:#1a2e1a,stroke:#27ae60,color:#fff
```

---

## B. Research Loop hàng ngày — Jupyter Notebooks

```mermaid
flowchart LR
    subgraph NB0["📓 00_plumbing_test.ipynb ❌"]
        direction TB
        P1["alpha_001_ema_cross\n(dummy alpha)"]
        P2["→ full pipeline → AlphaReport\nMục tiêu: < 5 phút"]
        P3{"pit_audit pass?\nAlphaReport format OK?\nAlpha KILL như kỳ vọng?"}
        P1 --> P2 --> P3
    end

    subgraph NB1["📓 01_data_exploration.ipynb ❌"]
        direction TB
        N1A["downloader.py + dataset_registry\nVendor parquet + WS reconcile"]
        N1B["cleaner.fill_gaps() → flag is_gap_filled\nWinsorize features only\n⚠️ KHÔNG xử lý raw returns"]
        N1C["cleaner.pit_audit() — 3 tests:\n1. Embargo IC test\n2. Future probe\n3. Chronological index"]
        N1D["validate_universe_coverage()\nget_active_universe(date, exchange)"]
        N1A --> N1B --> N1C --> N1D
    end

    subgraph NB2["📓 02_feature_engineering.ipynb ❌"]
        direction TB
        N2A["feature_builder.build_batch_features()\n→ gọi feature_registry.py (live parity)"]
        N2B["align_funding_to_bars() + validate_funding_alignment()\nclassify_funding_signal_type()"]
        N2C["feature_diagnostics: IC • orthogonality • stability\nfeature_exposure(signal, factor_set)\n→ R² per factor (BTC/DeFi/Meme/Funding)"]
        N2D["pit_audit() — chạy lại sau mỗi feature mới"]
        N2A --> N2B --> N2C --> N2D
    end

    subgraph NB3["📓 03_alpha_screening.ipynb ❌"]
        direction TB
        N3A["Triage nhiều ideas song song\nSTAGE 0: 30 phút hypothesis\nSTAGE 1: 2 phút IC screen"]
        N3B["IC < 0.010 → KILL ngay\nAlphaAutopsy → cemetery.bury()"]
        N3C["IC ≥ 0.010 → Stage 2: IC full + decay curve\nIR_estimate = IC × √BR_effective"]
        N3D["Stage 3: PurgedCV + PBO + DSR + BH\nStage 4: cost-adjusted IR + regime IC\nStage 5: marginal IR vs existing alphas"]
        N3A --> N3B --> N3C --> N3D
    end

    subgraph NB4["📓 04_model_training.ipynb ❌"]
        direction TB
        N4A["Labels: forward_return, triple_barrier\nTrainer: Linear/Ridge/Lasso TRƯỚC\nLightGBM chỉ khi OOS gain > 15%"]
        N4B["PurgedKFold (research) vs AnchoredWFO (deploy)\nStationary bootstrap — dynamic block size"]
        N4C["DSR + PBO + White's Reality Check\neffective_sample_size_warning()"]
        N4A --> N4B --> N4C
    end

    subgraph NB5["📓 05_backtest_validation.ipynb ❌"]
        direction TB
        N5A["Vectorized backtest — Polars\ncost_model dùng true_liquidity\n(không dùng ADV)"]
        N5B["Nếu halflife < 50 bars:\nmicrostructure_model.py fill simulation\n→ MANDATORY trước promotion"]
        N5C["regime_conditional_ic + transition_hazard\ndownside_beta + regime_conditional_covariance"]
        N5D["experiment_tracker.log_run()\nalpha_cemetery nếu fail"]
        N5E{{"Survived cost + regime + fill gate?\nPromotion to VALIDATION?"}}
        N5A --> N5B --> N5C --> N5D --> N5E
    end

    NB0 -->|"pipeline verified"| NB1
    NB1 -->|"clean.parquet + universe PiT"| NB2
    NB2 -->|"features.parquet"| NB3
    NB3 -->|"alpha passed Stage 3-5"| NB4
    NB4 -->|"model.pkl"| NB5
```

---

## C. Alpha Lifecycle — Kill Gates

```mermaid
flowchart TB
    IDEA["💡 IDEA\nHypothesis + economic_mechanism\nregistered_at timestamp\nfeatures_locked + parameter_ranges"]

    STAGE0["STAGE 0 — 30 phút\nHypothesis documentation\nCemetery check\nHalflife ≥ 20 bars\nData availability"]
    G0{{"economic_mechanism documented?\nNo duplicate in cemetery?\nHalflife ≥ 20 bars?"}}

    STAGE1["STAGE 1 — 2 phút\nQuick IC screen\n2022-2023 subset"]
    G1{{"IC > 0.010?"}}

    STAGE2["STAGE 2 — < 1 giờ\nIC full in-sample\nIC decay curve\nIR_estimate = IC × √BR_effective"]
    G2{{"IR_estimate > 0.30?"}}

    STAGE3["STAGE 3 — < 6 giờ\nPurgedKFold CV\nDSR + PBO + BH correction\nfeature_exposure() R² per factor"]
    G3{{"PBO < 0.50?\nDeflated Sharpe > 0?\nBH p-value < 0.05?\nfeature residual R² > 0.30?"}}

    STAGE4["STAGE 4 — < 1 ngày\nCost-adjusted IR\n(true_liquidity, c=0.15, borrowing cost)\nRegime IC 3 dimensions\nFill simulation nếu halflife < 50 bars"]
    G4{{"Cost-adjusted IR > 0.25?\nRegime IC > 0 trong ≥ 2/3?\nFill gate pass nếu halflife < 50?"}}

    STAGE5["STAGE 5 — < 1 ngày\nCorrelation vs existing alphas\nMarginal IR"]
    G5{{"Correlation < 0.60?\nMarginal IR > 0.05?"}}

    PAPER["📝 PAPER TRADE\n≥ 30 ngày\n+ Tiny Live ≥ 30 ngày (1% size)\nslippage vs estimate"]
    GP{{"Live slippage < 2× estimate?\nLive IR ≥ 0.40?"}}

    SHADOW["👁️ SHADOW LIVE\n≥ 90 ngày\nReal signals, minimal capital"]
    GS{{"Shadow Sharpe ≥ 0.80?\nMaxDD < 15%?\nMarginal IR to portfolio > 0.05?"}}

    PROD["🚀 PRODUCTION\nReal capital\nauto_kill.py monitoring\nreality_gap_monitor.py"]

    KILL["💀 KILL\nAlphaAutopsy → cemetery.bury()\nfailure_pattern_report()"]

    IDEA --> STAGE0 --> G0
    G0 -->|"YES"| STAGE1
    G0 -->|"NO"| KILL
    STAGE1 --> G1
    G1 -->|"YES"| STAGE2
    G1 -->|"NO"| KILL
    STAGE2 --> G2
    G2 -->|"YES"| STAGE3
    G2 -->|"NO"| KILL
    STAGE3 --> G3
    G3 -->|"YES"| STAGE4
    G3 -->|"NO"| KILL
    STAGE4 --> G4
    G4 -->|"YES"| STAGE5
    G4 -->|"NO"| KILL
    STAGE5 --> G5
    G5 -->|"YES"| PAPER
    G5 -->|"NO"| KILL
    PAPER --> GP
    GP -->|"YES"| SHADOW
    GP -->|"NO"| KILL
    SHADOW --> GS
    GS -->|"YES"| PROD
    GS -->|"NO"| KILL

    style KILL fill:#e74c3c,stroke:#c0392b,color:#fff
    style PROD fill:#27ae60,stroke:#229954,color:#fff
    style IDEA fill:#3498db,stroke:#2980b9,color:#fff
```

---

## D. Live vs Research — Code Parity

```mermaid
flowchart TB
    subgraph SHARED["🔗 Shared Code — CÙNG file, CÙNG function ✅"]
        FR["ong_dan_dac_trung/online/feature_registry.py\n_update_ema() • _update_welford_var()\n_update_ofi() • _update_micro_price()"]
        PS["thoat_vi_the/position_sizer.py\nanti-flip, lot rounding"]
        ES["thoat_vi_the/strategies/\nfixed_percent, trailing, time_based, atr_based"]
    end

    subgraph LIVE["🟢 LIVE / PAPER ✅"]
        direction TB
        WS["thu_thap/websocket/\nbinance_ws / bybit_ws / okx_ws"]
        STREAM["xu_ly_dong/ohlc_engine.py\norderbook_engine.py\n→ raw stream → ho_du_lieu/tho/"]
        IE["ong_dan_dac_trung/online/incremental_engine.py\n(zero-alloc, <10µs)"]
        MEM["ho_du_lieu/kho_dac_trung/online/memory_store.py"]
        SIG["dong_co_tin_hieu/ml_signal_engine.py\nONNX inference"]
        EMS["dong_co_thuc_thi/ems.py"]
        RG["quan_tri_rui_ro/kiem_tra_truoc_lenh/risk_gate.py"]
        EC["quan_ly_danh_muc/thoat_vi_the/exit_coordinator.py"]
        WAL["bo_nho_trang_thai/nhat_ky_wal/durable_wal.py"]

        WS --> STREAM --> IE
        IE -->|"calls"| FR
        IE --> MEM --> SIG --> EMS --> RG
        EMS --> EC
        EC -->|"calls"| ES
        EMS -->|"calls"| PS
        EMS --> WAL
    end

    subgraph RESEARCH["🔵 RESEARCH (Notebooks + Scripts) ❌"]
        direction TB
        PQ["Vendor parquet + WS stream archive\nho_du_lieu/tho/"]
        CL2["xu_ly_lo/cleaner.py\nfill_gaps (flag) + winsorize features only"]
        FB2["xu_ly_lo/feature_builder.py\nbuild_batch_features()"]
        FEAT2["ho_du_lieu/kho_dac_trung/offline/\nfeatures_*.parquet"]
        BT2["nghien_cuu/kiem_thu_qua_khu/\nVectorized Backtest (Polars)"]

        PQ --> CL2 --> FB2
        FB2 -->|"calls SAME functions"| FR
        FB2 --> FEAT2 --> BT2
        BT2 -->|"calls SAME exit logic"| ES
        BT2 -->|"calls SAME sizing logic"| PS
    end

    subgraph PAPER_ENV["📝 PAPER / TINY LIVE ✅"]
        direction TB
        PM["moi_truong_chay/paper/paper_runner.py"]
        PEA["moi_truong_chay/paper/paper_ems_adapter.py"]
        MM["moi_truong_chay/paper/microstructure_model.py\n⚠️ Dùng lại ở cuối Phase 2 cho fill gate"]
        SS["moi_truong_chay/paper/shock_simulator.py"]
        PM --> PEA --> MM
        SS --> MM
    end

    subgraph REPLAY["🟡 REPLAY (Integration Test) ❌"]
        direction TB
        RPE["nghien_cuu/dong_co_phat_lai/replay_engine.py\nparquet → ZMQ format"]
        ZMQ["ha_tang/bus_su_kien/zmq_bus.py ✅\nCÙNG ports như live"]
        FULL["Full production pipeline\nexact same code as live"]

        RPE -->|"emit events"| ZMQ --> FULL
    end

    style SHARED fill:#f39c12,stroke:#e67e22,color:#000
    style LIVE fill:#1a5276,stroke:#154360,color:#fff
    style RESEARCH fill:#1a3c5e,stroke:#154360,color:#fff
    style PAPER_ENV fill:#2e7d32,stroke:#1b5e20,color:#fff
    style REPLAY fill:#7d6608,stroke:#6c5b08,color:#fff
```

---

## E. Backtest Pipeline — Gate Logic

```mermaid
flowchart LR
    ALL["Alpha ideas\nqua Stage 0-2 triage"]

    subgraph TIER1["⚡ Vectorized Backtest\nnghien_cuu/kiem_thu_qua_khu/ma_tran_sie_toc/\n(vài giây / 4 năm data)"]
        direction TB
        V1["Polars batch signal compute\n(feature_registry.py — same as live)"]
        V2["cost_model.py: phase1_cost\n+ transient_impact\nc=0.15, true_liquidity không phải ADV"]
        V3["Exit logic từ thoat_vi_the/strategies/ ✅"]
        V4["evaluator.py: IC • IR • DSR • PBO\nalpha_diagnostics: decay • capacity\nregime_conditional_ic • effective_breadth"]
        V1 --> V2 --> V3 --> V4
    end

    GATE1{{"IC > 0.015?\nPBO < 0.50?\nDSR > 0?\nBH corrected p < 0.05?"}}

    subgraph FILL_GATE["⚠️ Fill Gate — MANDATORY\ncuối Phase 2 cho halflife < 50 bars"]
        direction TB
        FG1["moi_truong_chay/paper/microstructure_model.py ✅\nL2 snapshot fill simulation\nKhông dùng công thức mượt"]
        FG2{{"Slippage_actual ≤ 2× phase1_cost estimate?\nIR sau fill cost > 0?"}}
        FG1 --> FG2
    end

    subgraph TIER2["🎯 Event-Driven Backtest — Phase 4\nnghien_cuu/kiem_thu_qua_khu/mo_phong_su_kien/"]
        direction TB
        E1["event_backtest.py: tick-by-tick"]
        E2["fill_model.py: queue priority\npartial fills • latency injection"]
        E3["phase4_book_depletion_cost()"]
        E4["portfolio_optimizer.py + margin_ratio constraint\nround_to_lot() sau CVXPY"]
        E1 --> E2 --> E3 --> E4
    end

    GATE2{{"Sharpe_event > 0.7 × Sharpe_vectorized?\nMargin constraint satisfied?"}}

    subgraph TIER3["🔄 Replay — Phase 4\nnghien_cuu/dong_co_phat_lai/"]
        direction TB
        R1["replay_engine.py: parquet → ZMQ"]
        R2["Full production pipeline ✅"]
        R3["reality_gap_monitor.py tracking"]
        R1 --> R2 --> R3
    end

    ALL -->|"triage pass"| TIER1
    TIER1 --> GATE1
    GATE1 -->|"halflife < 50 bars\nhoặc cross-exchange"| FILL_GATE
    GATE1 -->|"halflife ≥ 50 bars\n→ VALIDATION trực tiếp"| VALIDATION["VALIDATION lifecycle"]
    FG2 -->|"pass"| VALIDATION
    FG2 -->|"fail"| DEAD1["💀 KILL\n(execution killed edge)"]
    GATE1 -->|"fail"| DEAD0["💀 KILL"]
    VALIDATION -->|"Phase 4"| TIER2
    TIER2 --> GATE2
    GATE2 -->|"pass"| TIER3
    GATE2 -->|"fail"| DEAD2["💀 KILL"]
    TIER3 -->|"Paper 30 ngày\n+ Tiny Live 30 ngày"| PAPER["📝 Paper/Tiny Live"]

    style DEAD0 fill:#e74c3c,color:#fff
    style DEAD1 fill:#e74c3c,color:#fff
    style DEAD2 fill:#e74c3c,color:#fff
    style PAPER fill:#27ae60,color:#fff
    style FILL_GATE fill:#e67e22,stroke:#d35400,color:#fff
```

---

## F. Feature Development Workflow

```mermaid
flowchart TB
    subgraph HYPOTHESIS["1️⃣ Hypothesis"]
        H1["Quan sát + economic mechanism\nVí dụ: funding spike → forced unwind\n→ predictable reversion trong 10-40 bars"]
    end

    subgraph BUILD["2️⃣ Build"]
        direction TB
        B1["Viết trong notebook cell\ndf = df.with_columns(...)"]
        B2["Phân loại:\nTier 1 — cần live parity → feature_registry.py\nTier 2 — research only → feature_builder.py"]
        B3["Funding signal? → classify_funding_signal_type()\n'realized' hoặc 'predictive_basis' — document rõ"]
    end

    subgraph TEST["3️⃣ Quality checks"]
        direction TB
        T1["pit_audit() — 3 tests\n(embargo • future probe • chronological)"]
        T2["feature_exposure(signal, factor_set)\n→ R² per factor\nRed flag: R²(BTC) > 0.60\nMinimum: residual R² > 0.30"]
        T3["IC • orthogonality • stability check"]
        T4["ic_decay_curve() — halflife bars"]
        T1 --> T2 --> T3 --> T4
    end

    subgraph DECIDE["4️⃣ Decision"]
        D1{{"pit_audit pass?\nfeature residual R² > 0.30?\nIC > 0.010?\nOrthogonal vs existing features?"}}
    end

    subgraph REGISTER["5️⃣ Register"]
        direction TB
        R1["Tier 2: thêm vào feature_builder.py\nDùng cho research, không có trên live"]
        R2["Tier 1: đăng ký vào feature_registry.py ✅\n→ cần update incremental_engine.py ✅\n→ verify: batch == live diff < 1e-6"]
    end

    REJECT["❌ Reject — log lý do\nAlphaAutopsy.lessons nếu cả alpha bị kill"]

    HYPOTHESIS --> BUILD --> TEST --> DECIDE
    DECIDE -->|"PASS"| REGISTER
    DECIDE -->|"FAIL"| REJECT

    style REJECT fill:#e74c3c,color:#fff
    style REGISTER fill:#27ae60,color:#fff
```

---

## G. Walk-Forward Retraining Workflow

```mermaid
flowchart TB
    subgraph INITIAL["🔰 Initial Training"]
        I1["AnchoredWFO\nanchor = 2020-01-01\nretrain_freq = monthly"]
        I2["Model stack: Linear → Ridge → Lasso\n→ LightGBM chỉ khi OOS gain > 15%"]
        I3["Validate: PurgedKFold + DSR + PBO\neffective_sample_size_warning()"]
        I1 --> I2 --> I3
    end

    subgraph MONITOR["📡 Live Monitoring"]
        direction TB
        M1["Deploy model"]
        M2["reality_gap_monitor.py ❌\ntrack: IC live • turnover • fill_rate • slippage\nZ-score mỗi dimension vs backtest"]
        M3["auto_kill.py ❌\nPrimary: IC decay < 30% backtest IC × 20 ngày\nSecondary: Sharpe z < -2.58"]
        M4{{"Degradation?"}}
        M1 --> M2 --> M3 --> M4
    end

    subgraph RETRAIN["🔄 Walk-Forward Retrain"]
        direction TB
        W1["Slide window\nAnchoredWFO.retrain()"]
        W2["Train v2 — same hyperparams\n(parameter freeze rule)"]
        W3["Validate: Purged CV + DSR + PBO\nSo sánh IC_v2 vs IC_v1"]
        W4{{"v2 > v1 + DSR pass?"}}
        W1 --> W2 --> W3 --> W4
    end

    subgraph SWAP["🔀 Model Swap"]
        direction TB
        S1["Export model (ONNX sau shadow)"]
        S2["Shadow 3 ngày — v1 trade, v2 quan sát"]
        S3{{"v2 reality_gap OK?"}}
        S4["Hot-swap: v1 → v2"]
        S1 --> S2 --> S3 --> S4
    end

    KEEP["Giữ v1\nThử lại sau"]

    I3 --> MONITOR
    M4 -->|"NO — healthy"| M2
    M4 -->|"YES — IC decay"| RETRAIN
    M4 -->|"YES — slippage drift"| RETRAIN
    W4 -->|"YES"| SWAP
    W4 -->|"NO"| KEEP
    S3 -->|"YES"| S4
    S3 -->|"NO"| KEEP
    KEEP -->|"next cycle"| RETRAIN
    S4 -->|"v2 live"| MONITOR

    style KEEP fill:#f39c12,color:#000
    style SWAP fill:#27ae60,color:#fff
```

---

## H. Alpha Combination & Portfolio Construction

```mermaid
flowchart TB
    subgraph ALPHAS["🔬 Alphas — lifecycle = VALIDATION"]
        A1["Funding/Carry family\nIC ≈ 0.015-0.030"]
        A2["Cross-sectional Momentum\nIC ≈ 0.012-0.025"]
        A3["Volatility Regime\nIC ≈ 0.012-0.022"]
    end

    subgraph RISK["🔩 Risk Model — hoc_may/to_hop_alpha/risk_model.py ❌"]
        direction TB
        R1["explicit_factor_neutralize()\nFactors: BTC, ETH, Layer1, DeFi, Meme, AI,\nAggregate Funding Rate, Exchange Spread Matrix"]
        R2["shrink_covariance() — Ledoit-Wolf\nTRƯỚC PCA, TRƯỚC MVO"]
        R3["pca_factor_model(residual, n_factors=3)"]
        R4["downside_beta() — tail regime\nregime_conditional_covariance() — per regime"]
        R1 --> R2 --> R3
        R2 --> R4
    end

    subgraph COMBINE["⚗️ AlphaCombiner ❌"]
        direction TB
        C1["effective_breadth() — BR_effective vs BR_naive\nSo sánh với BR_naive để detect fake IR"]
        C2["marginal_ir() — ngưỡng > 0.05\ncorrelation_clustering() — tránh cluster = 1 alpha"]
        C3["simplicity_score() — tie-break\n(simpler alpha → decay chậm hơn)"]
        C1 --> C2 --> C3
    end

    subgraph OPT["📐 Portfolio Optimizer ❌\nhoc_may/to_hop_alpha/portfolio_optimizer.py"]
        direction TB
        O1["Convex: max w^T μ - λ_risk w^T Σ w - λ_turnover ||w-w_prev||_1\nConstraints: margin_ratio ≥ 1.2\n|w_i| ≤ 0.20, ||w||_1 ≤ leverage"]
        O2["round_to_lot(weights, lot_sizes)\nRecheck margin_ratio sau rounding"]
        O1 --> O2
    end

    subgraph STRESS["🔴 Stress Test"]
        direction TB
        S1["stress_test(): BTC -30%, alts -50%, meme -80%\nDùng regime_conditional_covariance(tail)"]
        S2["risk_attribution(): BTC < 60%, sector < 40%"]
    end

    ALPHAS --> RISK --> COMBINE --> OPT --> STRESS
    STRESS -->|"stress OK → PAPER"| PAPER["📝 Paper Trade"]

    style PAPER fill:#27ae60,color:#fff
```

---

## I. Production Monitoring & Auto-Kill Loop

```mermaid
flowchart TB
    subgraph DEPLOY["🚀 Production"]
        D1["thuc_thi_lenh/dong_co_tin_hieu/ml_signal_engine.py ✅\nONNX inference"]
        D2["thuc_thi_lenh/dong_co_thuc_thi/ems.py ✅"]
        D3["quan_tri_rui_ro/ ✅\nrisk_gate + watchdog + emergency_flattener"]
        D1 --> D2 --> D3
    end

    subgraph MONITOR["📡 Monitoring ✅ + ❌"]
        direction TB
        M1["giam_sat/chi_so_hieu_suat/collector.py ✅\nLatency • throughput • resource"]
        M2["giam_sat/canh_bao/alert_manager.py ✅\nTelegram alerts"]
        M3["giam_sat/reality_gap_monitor.py ❌\nDimensions: IC_live • fill_rate • turnover\nholding • slippage vs estimate\nZ-score mỗi dimension — flag |z| > 2.0\nRoot cause: IC diverge = signal mất\nSlippage diverge = execution model sai"]
        M4["giam_sat/auto_kill.py ❌\nPrimary kill: IC_live < 30% × IC_backtest\n  sustained 20 ngày\nSecondary: Sharpe z < -2.58\nOutput: ok / scale_down / kill_candidate"]
        M5{{"Kill condition?"}}
        M1 --> M5
        M2 --> M5
        M3 --> M5
        M4 --> M5
    end

    subgraph RISK_LAYER["🔴 Risk Layers — tách biệt"]
        RL1["auto_kill.py — Alpha decay detection\n(statistical breach of IC)"]
        RL2["quan_tri_rui_ro/risk_gate.py ✅\nPre-trade risk\n(position/notional limits)"]
        RL3["watchdog/emergency_flattener.py ✅\nDD > threshold → flatten all\n(PnL breach)"]
        RL1 --- RL2
        RL2 --- RL3
    end

    subgraph ACTIONS["⚡ Actions"]
        A1["🟡 SCALE DOWN\nauto_kill: scale_factor = 0.5\n+ Telegram alert"]
        A2["🟠 KILL CANDIDATE\nMonitor 10 ngày thêm\nPost-mortem analysis"]
        A3["🔴 HALT / FLATTEN\nEmergencyFlattener ✅\nWatchdog trigger ✅"]
        A4["🔄 RETRAIN\nWalk-forward retrain\n(Workflow G)"]
    end

    D3 --> MONITOR
    M5 -->|"IC decay scale_down"| A1
    M5 -->|"IC decay kill_candidate"| A2
    M5 -->|"DD breach"| A3
    M5 -->|"IC drift sustainable"| A4
    A4 -->|"new model"| D1
    A1 -->|"continue monitoring"| MONITOR
    A2 -->|"10 ngày monitor"| MONITOR

    style A1 fill:#f1c40f,color:#000
    style A2 fill:#e67e22,color:#fff
    style A3 fill:#e74c3c,color:#fff
    style A4 fill:#3498db,color:#fff
    style RISK_LAYER fill:#2c2c2c,stroke:#e74c3c,color:#fff
```

---

## J. Data Sourcing & Reconciliation Flow

```mermaid
flowchart TB
    subgraph SOURCES["Nguồn dữ liệu"]
        V["Tardis.dev / Databento\nHistorical tick • klines • L2 • funding\nAudit trail — không bị retroactive mutation"]
        WS2["WS nội bộ ✅\nthu_thap/websocket/\n→ raw stream lưu liên tục\nPrimary source cho recent data"]
        REST2["REST API ✅\nthu_thap/rest_api/\n⚠️ Fallback only — sàn hay retroactive-adjust"]
    end

    subgraph MERGE["xu_ly_lo/downloader.py ❌"]
        direction TB
        MG1["Vendor parquet (historical T-∞ → T-30)"]
        MG2["WS stream archive (T-30 → now)\nReconcile: khớp không? Log discrepancy"]
        MG3["Seam check tại T-30:\n  hash_vendor(T-30) == hash_ws(T-30)?"]
        MG4["REST fallback chỉ khi WS gap\nFlag: data_source = 'REST_fallback'\n⚠️ Không tin tưởng REST cho IC computation"]
        MG1 --> MG3
        MG2 --> MG3
        MG3 -->|"seam OK"| RAW2[("ho_du_lieu/tho/\nunified parquet")]
        MG4 -.->|"last resort"| RAW2
    end

    subgraph CLEAN2["xu_ly_lo/cleaner.py ❌"]
        direction TB
        CL1["dedup (exchange can send duplicates)"]
        CL2["fill_gaps():\n  gap ≤ 5 bars → ffill features, flag is_gap_filled\n  gap > 5 bars → mark symbol inactive\n  ⚠️ KHÔNG ffill OHLC / returns"]
        CL3["winsorize features only\n(không xử lý raw returns)"]
        CL4["pit_audit(): embargo + future probe + chronological"]
        CL5["validate_universe_coverage(): ≥ 95%/ngày"]
        CL1 --> CL2 --> CL3 --> CL4 --> CL5
    end

    subgraph LIQ["xu_ly_lo/liquidity_filter.py ❌"]
        direction TB
        L1["compute_true_liquidity(l2_snapshots, depth_bps=20)\nDiscount spoofing: × fill_rate per level\nDefault conservative: 20-30% of raw L2"]
        L2["apply_liquidity_filter(universe, min_depth=50k USDT)\nRun weekly — liquidity thay đổi theo regime"]
    end

    subgraph DREG2["xu_ly_lo/dataset_registry.py ❌"]
        direction TB
        DR1["register(): hash chain + lineage"]
        DR2["register_universe(): PiT symbols\nrenamed_map: LUNA→LUNC, 1000PEPE vs PEPE"]
        DR3["register_market_structure_event():\nfunding_formula_change • stablecoin_depeg\nADL events • timestamp_drift\npost_hoc_analysis_breakpoints"]
        DR1 --> DR2 --> DR3
    end

    V -->|"bulk download"| MERGE
    WS2 -->|"streaming archive"| MERGE
    REST2 -.->|"fallback"| MERGE
    RAW2 --> CLEAN2 --> LIQ --> DREG2

    style REST2 fill:#4a1a1a,stroke:#e74c3c,color:#fff
    style V fill:#1a2e1a,stroke:#27ae60,color:#fff
```

---

## K. Alpha Triage — Research Velocity

```mermaid
flowchart LR
    POOL["Alpha Pool\n20-50 ideas/tuần\nFocus: Funding/Carry\ntrước tiên"]

    subgraph S0["STAGE 0 — 30 phút\nKhông code"]
        direction TB
        S0A["1 câu hypothesis\nEconomic mechanism"]
        S0B["Cemetery check:\nSearch_similar() trước"]
        S0C["Halflife ≥ 20 bars?\nData available?"]
        S0D["Pre-register:\nfeatures_locked\nparameter_ranges\nregistered_at timestamp"]
        S0A --> S0B --> S0C --> S0D
    end

    subgraph S1["STAGE 1 — 2 phút\n2022-2023 subset"]
        S1A["IC < 0.010 → KILL"]
    end

    subgraph S2["STAGE 2 — < 1 giờ"]
        S2A["IC full in-sample\nIC decay curve\nfeature_exposure() R²\nIR_estimate = IC × √BR_effective"]
    end

    subgraph S3["STAGE 3 — < 6 giờ\nMax 3 param sweeps"]
        S3A["PurgedKFold CV\nDSR • PBO • BH correction\nStationary bootstrap\neffective_sample_size_warning()"]
    end

    subgraph S4["STAGE 4 — < 1 ngày"]
        S4A["Cost-adjusted IR:\n  true_liquidity (spoofing discount)\n  borrowing_cost() nếu spot short\nRegime conditional IC\nFill simulation nếu halflife < 50"]
    end

    subgraph S5["STAGE 5 — < 1 ngày"]
        S5A["Marginal IR vs existing alphas\nCorrelation clustering\nSimplicity score"]
    end

    KILL2["💀 KILL\nAutoAutopsy\n→ cemetery"]
    VAL["→ VALIDATION lifecycle\nlifecycle = VALIDATION"]

    POOL --> S0
    S0 -->|"fail"| KILL2
    S0 -->|"pass"| S1
    S1 -->|"fail"| KILL2
    S1 -->|"pass"| S2
    S2 -->|"IR < 0.30"| KILL2
    S2 -->|"IR ≥ 0.30"| S3
    S3 -->|"fail"| KILL2
    S3 -->|"pass"| S4
    S4 -->|"fail"| KILL2
    S4 -->|"pass"| S5
    S5 -->|"fail"| KILL2
    S5 -->|"pass"| VAL

    style KILL2 fill:#e74c3c,color:#fff
    style VAL fill:#27ae60,color:#fff
    style S0 fill:#1a2e3e,stroke:#3498db,color:#fff
```