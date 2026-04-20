import json
import numpy as np
import polars as pl
import torch
import torch.nn as nn
import torch.optim as optim
from pathlib import Path
from torch.utils.data import DataLoader, TensorDataset

from processing.ml.du_bao_gia_lstm.features import (
    build_lstm_features, build_lstm_sequences, SEQ_LEN, N_FEATURES,
)
tao_feature_lstm   = build_lstm_features    # backward-compat alias used internally
xay_trinh_tu_lstm  = build_lstm_sequences
from utils.helpers import logger

try:
    from data.store import A11
    DATA_DIR = A11.ml_model("du_bao_gia_lstm")
except ImportError:
    DATA_DIR = Path(__file__).parent / "du_lieu"
    DATA_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = DATA_DIR / "lstm_model.pth"
INFO_PATH  = DATA_DIR / "model_info.json"

HIDDEN = 128
LAYERS = 2
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class LSTMNet(nn.Module):
    """LSTM → FC → Sigmoid: dự báo xác suất log return > 0 (tăng giá)."""

    def __init__(self, n_features: int = N_FEATURES, hidden: int = HIDDEN, n_layers: int = LAYERS):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden,
            num_layers=n_layers,
            batch_first=True,
            dropout=0.2,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden, 64),
            nn.GELU(),
            nn.Dropout(0.3),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )
        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            nn.init.xavier_normal_(m.weight)
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :]).squeeze(-1)   # (B,)


def huan_luyen(
    df_1m: pl.DataFrame,
    regime_arr:  np.ndarray | None = None,
    anomaly_arr: np.ndarray | None = None,
    pattern_arr: np.ndarray | None = None,
    epochs: int = 30,
    batch_size: int = 256,
) -> None:
    """Huấn luyện LSTM từ dữ liệu lịch sử.

    Nếu regime/anomaly/pattern không được truyền vào, dùng giá trị mặc định (0).
    """
    logger.info("du_bao_gia_lstm | Bước 1: Trích xuất đặc trưng LSTM...")
    df_feat = tao_feature_lstm(df_1m)
    n = len(df_feat)

    if regime_arr is None:
        regime_arr = np.zeros(n, dtype=np.int32)
    if anomaly_arr is None:
        anomaly_arr = np.full(n, 50.0, dtype=np.float32)
    if pattern_arr is None:
        pattern_arr = np.zeros(n, dtype=np.int32)

    # Đảm bảo cùng độ dài
    regime_arr  = regime_arr[:n]
    anomaly_arr = anomaly_arr[:n]
    pattern_arr = pattern_arr[:n]

    X, y_ret = xay_trinh_tu_lstm(df_feat, regime_arr, anomaly_arr, pattern_arr)
    if len(X) == 0:
        logger.error("du_bao_gia_lstm | Không đủ dữ liệu để train.")
        return

    # Chuyển label returns → xác suất nhị phân (tăng = 1, giảm = 0)
    y_bin = (y_ret > 0).astype(np.float32)

    X_tensor = torch.tensor(X, dtype=torch.float32)
    y_tensor = torch.tensor(y_bin, dtype=torch.float32)

    split = int(len(X_tensor) * 0.9)
    X_train, X_val = X_tensor[:split], X_tensor[split:]
    y_train, y_val = y_tensor[:split], y_tensor[split:]

    loader = DataLoader(TensorDataset(X_train, y_train), batch_size=batch_size, shuffle=True)

    model = LSTMNet(N_FEATURES, HIDDEN, LAYERS).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    criterion = nn.BCELoss()
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    logger.info(f"du_bao_gia_lstm | Train {len(X_train)} mẫu trên {device}...")
    model.train()
    for epoch in range(epochs):
        total = 0.0
        for bx, by in loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            pred = model(bx)
            loss = criterion(pred, by)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total += loss.item()
        scheduler.step()

        if (epoch + 1) % 5 == 0 or epoch == 0:
            model.eval()
            with torch.no_grad():
                val_pred = model(X_val.to(device))
                val_loss = criterion(val_pred, y_val.to(device)).item()
            acc = ((val_pred > 0.5).float() == y_val.to(device)).float().mean().item()
            logger.info(f"  Epoch {epoch+1}/{epochs} | Train Loss: {total/len(loader):.4f} | Val Loss: {val_loss:.4f} | Acc: {acc:.3f}")
            model.train()

    torch.save(model.state_dict(), MODEL_PATH)
    with open(INFO_PATH, "w") as f:
        json.dump({"n_features": N_FEATURES, "hidden": HIDDEN, "n_layers": LAYERS, "seq_len": SEQ_LEN}, f)
    logger.success("du_bao_gia_lstm | Train xong LSTM!")
