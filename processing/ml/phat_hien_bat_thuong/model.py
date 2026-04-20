import json
import pickle
import numpy as np
import polars as pl
import torch
import torch.nn as nn
import torch.optim as optim
from pathlib import Path
from torch.utils.data import DataLoader, TensorDataset
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from processing.ml.phat_hien_bat_thuong.features import (
    build_anomaly_features, build_ae_sequences, AE_SEQ_LEN,
)
tao_feature_bat_thuong = build_anomaly_features   # backward-compat alias
xay_trinh_tu_ae        = build_ae_sequences
from utils.helpers import logger

try:
    from data.store import A11
    DATA_DIR = A11.ml_model("phat_hien_bat_thuong")
except ImportError:
    DATA_DIR = Path(__file__).parent / "du_lieu"
    DATA_DIR.mkdir(parents=True, exist_ok=True)

ISO_PATH    = DATA_DIR / "isolation_forest.pkl"
AE_PATH     = DATA_DIR / "autoencoder.pth"
SCALER_PATH = DATA_DIR / "anomaly_scaler.pkl"
INFO_PATH   = DATA_DIR / "model_info.json"

N_FEAT = 6
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class AnomalyAutoencoder(nn.Module):
    """LSTM Autoencoder: encode chuỗi → decode → so sánh reconstruction error."""

    def __init__(self, n_features: int = N_FEAT, hidden: int = 64, seq_len: int = AE_SEQ_LEN):
        super().__init__()
        self.seq_len = seq_len
        self.encoder = nn.LSTM(n_features, hidden, batch_first=True)
        self.decoder = nn.LSTM(hidden, n_features, batch_first=True)

    def forward(self, x: torch.Tensor):
        # Encode
        _, (h, _) = self.encoder(x)
        # Repeat hidden state seq_len lần để feed decoder
        dec_in = h.squeeze(0).unsqueeze(1).repeat(1, x.size(1), 1)
        out, _ = self.decoder(dec_in)
        return out


def huan_luyen(df_1m: pl.DataFrame, epochs: int = 20, batch_size: int = 256,
               iso_contamination: float = 0.02) -> None:
    """Huấn luyện Isolation Forest + LSTM Autoencoder."""
    logger.info("phat_hien_bat_thuong | Bước 1: Trích xuất đặc trưng...")
    df_feat = tao_feature_bat_thuong(df_1m)

    feat_cols = ["ret_1", "ret_5", "spread_atr", "vol_z", "body_prop", "wick_extreme"]
    X_tab = df_feat.select(feat_cols).to_numpy().astype(np.float32)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_tab)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

    # ── Isolation Forest ────────────────────────────────────────────────────
    logger.info("phat_hien_bat_thuong | Bước 2: Train Isolation Forest...")
    iso = IsolationForest(n_estimators=200, contamination=iso_contamination,
                          random_state=42, n_jobs=-1)
    iso.fit(X_scaled)
    with open(ISO_PATH, "wb") as f:
        pickle.dump(iso, f)
    logger.info("phat_hien_bat_thuong | Isolation Forest xong.")

    # ── LSTM Autoencoder ────────────────────────────────────────────────────
    logger.info("phat_hien_bat_thuong | Bước 3: Train LSTM Autoencoder...")
    X_seq = xay_trinh_tu_ae(df_feat, AE_SEQ_LEN)
    if len(X_seq) == 0:
        logger.warning("phat_hien_bat_thuong | Không đủ dữ liệu cho Autoencoder.")
        return

    X_tensor = torch.tensor(X_seq, dtype=torch.float32)
    loader = DataLoader(TensorDataset(X_tensor), batch_size=batch_size, shuffle=True)

    model = AnomalyAutoencoder(N_FEAT, 64, AE_SEQ_LEN).to(device)
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.MSELoss()

    model.train()
    for epoch in range(epochs):
        total = 0.0
        for (bx,) in loader:
            bx = bx.to(device)
            optimizer.zero_grad()
            recon = model(bx)
            loss = criterion(recon, bx)
            loss.backward()
            optimizer.step()
            total += loss.item()
        if (epoch + 1) % 5 == 0 or epoch == 0:
            logger.info(f"  AE Epoch {epoch+1}/{epochs} | Loss: {total/len(loader):.6f}")

    torch.save(model.state_dict(), AE_PATH)
    with open(INFO_PATH, "w") as f:
        json.dump({"n_features": N_FEAT, "seq_len": AE_SEQ_LEN}, f)
    logger.success("phat_hien_bat_thuong | Train xong Autoencoder!")
