"""
processing.ml — Trung Tâm Học Máy KAIROS v3.0

Gồm 6 module ML độc lập, mỗi module có chức năng riêng biệt:

┌──────────────────────────────────────────────────────────────────────────────┐
│  #   Module                  Engine               Model file chính           │
├──────────────────────────────────────────────────────────────────────────────┤
│  1   trang_thai_thi_truong   RegimeEngine (MLP)   model_pytorch.pth          │
│  2   phan_loai_nen           CandleClassifier     cnn_model.pth              │
│  3   phat_hien_bat_thuong    AnomalyEngine        isolation_forest.pkl        │
│  4   du_bao_gia_lstm         LSTMEngine           lstm_model.pth             │
│  5   cho_diem_tin_hieu       SignalScorerEngine   xgb_model.json             │
│  6   toi_uu_danh_muc         PortfolioOptimizer   (Markowitz sẵn sàng)       │
└──────────────────────────────────────────────────────────────────────────────┘

Dữ liệu model lưu tại: data.store/ml/<tên_module>/
Fallback cục bộ:        processing.ml/<module>/du_lieu[_ml]/

Cách dùng:
    from processing.ml import lay_module, tat_ca_trang_thai

    regime  = lay_module("trang_thai")   # RegimeEngine
    candle  = lay_module("phan_loai")    # CandleClassifier
    anomaly = lay_module("bat_thuong")   # AnomalyEngine
    lstm    = lay_module("du_bao_gia")   # LSTMEngine
    scorer  = lay_module("cho_diem")     # SignalScorerEngine
    opt     = lay_module("danh_muc")     # PortfolioOptimizer
"""
from __future__ import annotations
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# MAP: tên ngắn → (package, class)
# ─────────────────────────────────────────────────────────────────────────────
_MODULE_MAP: dict[str, tuple[str, str]] = {
    "trang_thai": ("processing.ml.trang_thai_thi_truong", "RegimeEngine"),
    "phan_loai":  ("processing.ml.phan_loai_nen",         "CandleClassifier"),
    "bat_thuong": ("processing.ml.phat_hien_bat_thuong",   "AnomalyEngine"),
    "du_bao_gia": ("processing.ml.du_bao_gia_lstm",        "LSTMEngine"),
    "cho_diem":   ("processing.ml.cho_diem_tin_hieu",      "SignalScorerEngine"),
    "danh_muc":   ("processing.ml.toi_uu_danh_muc",        "PortfolioOptimizer"),
}

# Thứ tự model file cần kiểm tra (primary, optional_extras...)
# "always_ready" = True: module hoạt động không cần file train (Markowitz, v.v.)
_MODULE_STATUS_CFG: dict[str, dict] = {
    "trang_thai_thi_truong": {
        "pkg":          "processing.ml.trang_thai_thi_truong",
        "data_attr":    "DATA_DIR",
        "primary":      "model_pytorch.pth",
        "extras":       ["scaler_params.json"],
        "always_ready": False,
    },
    "phan_loai_nen": {
        "pkg":          "processing.ml.phan_loai_nen.model",
        "data_attr":    "DATA_DIR",
        "primary":      "cnn_model.pth",
        "extras":       ["kmeans_model.pkl"],
        "always_ready": False,
    },
    "phat_hien_bat_thuong": {
        "pkg":          "processing.ml.phat_hien_bat_thuong.model",
        "data_attr":    "DATA_DIR",
        "primary":      "isolation_forest.pkl",
        "extras":       ["autoencoder.pth"],
        "always_ready": False,
    },
    "du_bao_gia_lstm": {
        "pkg":          "processing.ml.du_bao_gia_lstm.model",
        "data_attr":    "DATA_DIR",
        "primary":      "lstm_model.pth",
        "extras":       [],
        "always_ready": False,
    },
    "cho_diem_tin_hieu": {
        "pkg":          "processing.ml.cho_diem_tin_hieu.model",
        "data_attr":    "DATA_DIR",
        "primary":      "xgb_model.json",
        "extras":       [],
        "always_ready": False,
    },
    "toi_uu_danh_muc": {
        "pkg":          "processing.ml.toi_uu_danh_muc",
        "data_attr":    "DATA_DIR",
        "primary":      None,                   # Markowitz/Kelly không cần model file
        "extras":       ["ppo_model.zip"],      # PPO là optional
        "always_ready": True,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def load_ml_module(module_name: str) -> Any:
    """Load and instantiate an ML engine by short name.

    Args:
        module_name: 'trang_thai' | 'phan_loai' | 'bat_thuong' |
                     'du_bao_gia' | 'cho_diem' | 'danh_muc'

    Returns:
        Instantiated engine (model loaded if available).

    Raises:
        ValueError: Unknown module name.
        ImportError: Missing dependency (torch, xgboost...).
    """
    if module_name not in _MODULE_MAP:
        available = ", ".join(_MODULE_MAP.keys())
        raise ValueError(f"Module '{module_name}' not found. Available: {available}")

    import importlib
    pkg_name, class_name = _MODULE_MAP[module_name]
    pkg = importlib.import_module(pkg_name)
    cls = getattr(pkg, class_name)
    return cls()


# Backward-compatible alias
lay_module = load_ml_module


def all_module_status() -> dict:
    """Kiểm tra trạng thái (trained / ready) của tất cả 6 module.

    Trả về dict:
        {
            "trang_thai_thi_truong": {
                "trained": bool,
                "always_ready": bool,
                "primary_model": str,
                "extras": {file: exists},
                "data_dir": str,
            },
            ...
        }
    """
    import importlib
    result = {}

    for module_key, cfg in _MODULE_STATUS_CFG.items():
        try:
            pkg = importlib.import_module(cfg["pkg"])
            data_dir = getattr(pkg, cfg["data_attr"])
        except Exception:
            result[module_key] = {
                "trained":      False,
                "always_ready": cfg["always_ready"],
                "primary_model": cfg["primary"],
                "extras":       {},
                "data_dir":     "(import error)",
                "error":        True,
            }
            continue

        # Kiểm tra model file chính
        if cfg["primary"] is None:
            primary_ok = True   # Không cần model file
        else:
            primary_ok = (data_dir / cfg["primary"]).exists()

        # Kiểm tra extras
        extras_status = {
            f: (data_dir / f).exists()
            for f in cfg["extras"]
        }

        trained = cfg["always_ready"] or primary_ok

        result[module_key] = {
            "trained":       trained,
            "always_ready":  cfg["always_ready"],
            "primary_model": cfg["primary"],
            "extras":        extras_status,
            "data_dir":      str(data_dir),
        }

    return result


def print_module_status() -> None:
    """Print a status table of all 6 ML modules to the console."""
    status = all_module_status()
    print("\n" + "─" * 72)
    print(f"{'Module':<30} {'Trained':<10} {'Primary model':<25} {'Note'}")
    print("─" * 72)
    for name, info in status.items():
        if info.get("error"):
            icon = "❌"
            note = "Import error"
        elif info["always_ready"]:
            icon = "✅"
            note = "Sẵn sàng (không cần train)"
        elif info["trained"]:
            icon = "✅"
            note = ""
        else:
            icon = "🔲"
            note = "Chưa train"

        primary = info["primary_model"] or "—"
        print(f"{icon} {name:<28} {str(info['trained']):<10} {primary:<25} {note}")

        for extra, exists in info.get("extras", {}).items():
            e_icon = "  ✅" if exists else "  ○ "
            print(f"  {e_icon} {extra}")

    print("─" * 72 + "\n")


__all__ = ["load_ml_module", "all_module_status", "print_module_status",
           "lay_module", "tat_ca_trang_thai", "in_trang_thai"]

# Backward-compatible aliases
tat_ca_trang_thai = all_module_status
in_trang_thai     = print_module_status
