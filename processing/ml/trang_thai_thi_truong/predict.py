import os
import json
from datetime import datetime
import csv

# --- THƯ VIỆN LÕI ---
import torch
import numpy as np
import polars as pl

from processing.ml.trang_thai_thi_truong.model import AI_Engine, DATA_DIR
from processing.ml.trang_thai_thi_truong.feature import compute_live_features as feature_dataset, compute_batch_features as features_vectorized
from utils.helpers import logger

LOG_FILE = os.path.join(DATA_DIR, "trading_memory.csv")
engine = AI_Engine() 

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


STATE_MAP = {
    0: "DONG_BANG",       # Dead Market — Không trade, vol cạn kiệt
    1: "NEN_CHAT",        # Squeeze — Tích lũy nén chặt, canh Breakout
    2: "DAU_XU_HUONG",    # Early Trend — Xu hướng chớm hình thành, vào lệnh sớm
    3: "XU_HUONG_MANH",   # Strong Trend — H4/H1/M15 đồng thuận, Follow trend
    4: "CAO_TRAO",        # Climax — Giá chạy quá xa, chuẩn bị Scale out / chốt lời
    5: "HOI_QUY",         # Mean Reversion — Giá giật ngược về trung bình (Counter-trend)
    6: "NHIEU_DONG",      # Choppy / Range — Đi ngang, giật liên tục, đánh Range
    7: "DAO_CHIEU",       # Reversal — Vol đột biến + cấu trúc gãy, canh đảo chiều
}

def predict_market_state(df_5m, df_15m, df_1h, df_4h, last_state=None):

    feature_dict = feature_dataset(df_5m, df_15m, df_1h, df_4h, last_state=last_state)

    if feature_dict is None or feature_dict.is_empty():
        return None

    input_vector = feature_dict.to_dicts()[0]
    
    # 2. Dự đoán
    state_id, conf, probs = engine.predict(input_vector)
    
    if state_id is None: return None

    # 3. Đóng gói
    packet = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'state_id': state_id,
        'state_name': STATE_MAP.get(state_id, "UNKNOWN"),
        'confidence': round(conf, 4),
        'probs': probs,
        'features_snapshot': input_vector 
    }
    return packet

def predict_state_vectorized(df_1m: pl.DataFrame) -> pl.DataFrame:
    """
    Nhận DataFrame 1m gốc. Xuất ra DataFrame có cột 'regime' và 'confidence' 
    do mô hình AI dự đoán (Xử lý hàng loạt - Vectorized Inference).
    """
    # 1. Trích xuất Features
    df_feat = features_vectorized(df_1m)
    
    # Trả về Mặc định nếu DataFrame rỗng
    if df_feat is None or df_feat.is_empty():
        return df_1m.with_columns([pl.lit(0).alias("regime"), pl.lit(0.0).alias("confidence")])

    engine_vector = AI_Engine()
    
    # 🔥 SAFEGUARD 1: KIỂM TRA ĐÃ CÓ MODEL CHƯA? (Thay vì raise ValueError gây crash bot)
    if engine_vector.model is None or engine_vector.scaler is None:
        logger.warning("AI Model hoặc Scaler chưa được huấn luyện! Trả về Regime 0 mặc định.")
        return df_1m.with_columns([pl.lit(0).alias("regime"), pl.lit(0.0).alias("confidence")])

    feature_cols = engine_vector.feature_names
    
    # 🔥 SAFEGUARD 2: KIỂM TRA LỖI LỆCH TÊN CỘT (MISMATCH FEATURES)
    missing_cols = [c for c in feature_cols if c not in df_feat.columns]
    if len(missing_cols) > 0:
        logger.error(f"Dataset bị thiếu {len(missing_cols)} cột Features (Vd: {missing_cols[:3]}). Đã Bypass về Regime 0.")
        return df_1m.with_columns([pl.lit(0).alias("regime"), pl.lit(0.0).alias("confidence")])

    # 2. Chuyển DataFrame thành Tensor
    # Đảm bảo thứ tự cột khớp với lúc train
    X_numpy = df_feat.select(feature_cols).to_numpy()
    X_tensor = torch.tensor(X_numpy, dtype=torch.float32)

    # 3. Chạy qua Model Hàng Loạt (Batch Inference)
    engine_vector.model.eval()
    with torch.no_grad():
        # Scale data & đưa lên GPU/CPU
        X_scaled = engine_vector.scaler.transform(X_tensor).to(device)
        
        # Dự đoán
        logits = engine_vector.model(X_scaled)
        probs = torch.softmax(logits, dim=1)
        
        # Lấy Class có xác suất cao nhất và độ tự tin
        confidences, predictions = torch.max(probs, dim=1)

    # 4. Đưa kết quả về CPU và ghép vào DataFrame ban đầu
    preds_np = predictions.cpu().numpy()
    confs_np = confidences.cpu().numpy()
    
    # Tạo DataFrame kết quả trung gian
    df_results = pl.DataFrame({
        "timestamp": df_feat["timestamp"],
        "regime": preds_np.astype(np.int32),
        "confidence": confs_np.astype(np.float64)
    })

    # Ghép lại với df_1m gốc (Những dòng đầu bị NaN feature sẽ được fill regime=0)
    df_final = df_1m.join(df_results, on="timestamp", how="left") \
                    .with_columns([
                        pl.col("regime").fill_null(0).cast(pl.Int32),
                        pl.col("confidence").fill_null(0.0).cast(pl.Float64)
                    ])

    return df_final.select(["timestamp", "open", "high", "low", "close", "volume", "regime", "confidence"])

def evaluate_prediction(packet, pnl, dd, correct=None):

    if not packet: return

    if correct is None:
        correct = 'NaN'

    state_name = packet['state_name']

    if pnl > 0:
        reward = pnl * 1.0 
    else:
        reward = pnl * 2.0 

    # --- 2. ĐIỀU CHỈNH THEO CHIẾN THUẬT ---
    if state_name == 'NHIEU_DONG':          # Đánh Range — lãi nhỏ cũng thưởng, lỗ phạt nặng
        if pnl < 0: reward -= 2.0
        elif 0 < pnl < 0.5: reward += 0.5
    elif state_name == 'NEN_CHAT':           # Đánh Breakout — lãi to thưởng lớn
        if pnl < 0: reward -= 2.0
        elif pnl > 2.0: reward += 2.0
    elif state_name == 'XU_HUONG_MANH':     # Follow trend — lỗ phạt x1.5, lãi to thưởng mạnh
        if pnl < 0: reward *= 1.5
        elif pnl > 3.0: reward += 3.0
    elif state_name == 'DAO_CHIEU':         # Counter-trend — rủi ro cao, thắng phải lớn
        if pnl < -1.0: reward -= 3.0
        elif pnl > 1.5: reward += 2.0
    elif state_name == 'HOI_QUY':           # Mean Reversion — tương tự Dao Chiều
        if pnl < -1.0: reward -= 2.0
        elif pnl > 1.0: reward += 1.5
    else:
        if dd < -1.0: reward -= 1.0

    reward = max(min(reward, 10), -10)

    # --- 3. LƯU LOG ---
    log_row = {
        'timestamp': packet['timestamp'],
        'state': packet['state_id'],      
        'correct': correct,
        'state_name': packet['state_name'],
        'confidence': packet['confidence'],
        'pnl': round(pnl, 4),
        'reward': round(reward, 4),
        'features_json': json.dumps(packet['features_snapshot'])
    }
    
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=log_row.keys())
        if not file_exists: writer.writeheader()
        writer.writerow(log_row)