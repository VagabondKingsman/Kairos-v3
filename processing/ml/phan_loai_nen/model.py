import json
import pickle
import numpy as np
import polars as pl
import torch
import torch.nn as nn
import torch.optim as optim
from pathlib import Path
from torch.utils.data import DataLoader, TensorDataset
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from processing.ml.phan_loai_nen.features import (
    build_candle_features, label_candles_rule_based, build_sequences, SEQ_LEN, N_FEATURES,
)
tao_feature_nen     = build_candle_features        # backward-compat aliases
dat_nhan_rule_based = label_candles_rule_based
xay_trinh_tu        = build_sequences
from utils.helpers import logger

try:
    from data.store import A11
    DATA_DIR = A11.ml_model("phan_loai_nen")
except ImportError:
    DATA_DIR = Path(__file__).parent / "du_lieu"
    DATA_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH  = DATA_DIR / "cnn_model.pth"
KMEANS_PATH = DATA_DIR / "kmeans_model.pkl"
SCALER_PATH = DATA_DIR / "cnn_scaler.pkl"
INFO_PATH   = DATA_DIR / "model_info.json"

N_PATTERNS  = 10
N_CLUSTERS  = 20
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class CandleCNN(nn.Module):
    """CNN 1D phân loại chuỗi 20 nến thành 10 mẫu hình."""

    def __init__(self, seq_len: int = SEQ_LEN, n_features: int = N_FEATURES, n_classes: int = N_PATTERNS):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(n_features, 32, kernel_size=3, padding=1),
            nn.BatchNorm1d(32), nn.GELU(),
            nn.Conv1d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm1d(64), nn.GELU(),
            nn.Conv1d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm1d(128), nn.GELU(),
        )
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.fc = nn.Sequential(
            nn.Linear(128, 64), nn.GELU(), nn.Dropout(0.3),
            nn.Linear(64, n_classes),
        )
        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, (nn.Linear, nn.Conv1d)):
            nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, seq_len, features) → (B, features, seq_len) for Conv1d
        x = x.transpose(1, 2)
        x = self.pool(self.conv(x)).squeeze(-1)
        return self.fc(x)


def huan_luyen(df_1m: pl.DataFrame, epochs: int = 30, batch_size: int = 512) -> None:
    """Huấn luyện CandleCNN từ rule-based labels + KMeans unsupervised."""
    logger.info("phan_loai_nen | Bước 1: Trích xuất đặc trưng nến...")

    df_feat   = tao_feature_nen(df_1m)
    df_lbl    = dat_nhan_rule_based(df_1m)
    df_feat   = df_feat.with_columns(df_lbl["pattern"])

    X_seq = xay_trinh_tu(df_feat, SEQ_LEN)           # (N, 20, 5)
    if len(X_seq) == 0:
        logger.error("phan_loai_nen | Không đủ dữ liệu để train.")
        return

    y_arr = df_feat["pattern"].to_numpy()[SEQ_LEN - 1:].astype(np.int64)
    if len(y_arr) > len(X_seq):
        y_arr = y_arr[: len(X_seq)]

    # ── KMeans unsupervised ──────────────────────────────────────────────────
    logger.info("phan_loai_nen | Bước 2: Train KMeans unsupervised...")
    X_flat = X_seq.reshape(len(X_seq), -1)
    scaler = StandardScaler()
    X_flat_s = scaler.fit_transform(X_flat)
    km = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    km.fit(X_flat_s)
    with open(KMEANS_PATH, "wb") as f:
        pickle.dump(km, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)
    logger.info(f"phan_loai_nen | KMeans xong ({N_CLUSTERS} clusters).")

    # ── CNN supervised ───────────────────────────────────────────────────────
    logger.info("phan_loai_nen | Bước 3: Train CandleCNN supervised...")
    X_tensor = torch.tensor(X_seq, dtype=torch.float32)
    y_tensor = torch.tensor(y_arr, dtype=torch.long)

    loader = DataLoader(TensorDataset(X_tensor, y_tensor), batch_size=batch_size, shuffle=True)

    model = CandleCNN().to(device)
    optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)

    counts = np.bincount(y_arr, minlength=N_PATTERNS).astype(float)
    w = torch.tensor(1.0 / (counts + 1), dtype=torch.float32).to(device)
    criterion = nn.CrossEntropyLoss(weight=w / w.sum() * N_PATTERNS)

    model.train()
    for epoch in range(epochs):
        total = 0.0
        for bx, by in loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            loss = criterion(model(bx), by)
            loss.backward()
            optimizer.step()
            total += loss.item()
        if (epoch + 1) % 10 == 0 or epoch == 0:
            logger.info(f"  Epoch {epoch+1}/{epochs} | Loss: {total/len(loader):.4f}")

    torch.save(model.state_dict(), MODEL_PATH)
    with open(INFO_PATH, "w") as f:
        json.dump({"seq_len": SEQ_LEN, "n_features": N_FEATURES, "n_classes": N_PATTERNS}, f)
    logger.success("phan_loai_nen | Train xong CandleCNN!")
