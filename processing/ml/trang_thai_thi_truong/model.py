import os
import json
import random
import polars as pl
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from pathlib import Path
from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler
from sklearn.model_selection import train_test_split
from processing.ml.trang_thai_thi_truong.feature import compute_live_features as feature_dataset, compute_batch_features as features_vectorized
from utils.helpers import logger

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Đường dẫn dữ liệu: ưu tiên dùng data.store, fallback về cục bộ
FILE_PATH = Path(__file__).resolve()
MODULE_DIR = FILE_PATH.parent  # .../processing.ml/trang_thai_thi_truong_ml/

try:
    from data.store import A11
    _DATA_PATH = A11.ml_model("trang_thai_thi_truong_ml")
except ImportError:
    # Fallback cục bộ nếu chạy độc lập
    _DATA_PATH = MODULE_DIR / "du_lieu_ml"
    _DATA_PATH.mkdir(parents=True, exist_ok=True)

DATA_DIR = str(_DATA_PATH)
MODEL_PATH = str(_DATA_PATH / 'model_pytorch.pth')
SCALER_PATH = str(_DATA_PATH / 'scaler_params.json')
INFO_PATH = str(_DATA_PATH / 'model_info.json')


class MyTorchScaler:
    def __init__(self):
        self.mean = None
        self.std = None
    
    def fit(self, x_tensor):
        self.mean = x_tensor.mean(dim=0).cpu()
        self.std = x_tensor.std(dim=0).cpu()
        self.std[self.std == 0] = 1e-7 # Tránh chia cho 0
        
    def transform(self, x_tensor):
        if self.mean is None: raise ValueError("Scaler chưa fit!")
        return (x_tensor - self.mean.to(x_tensor.device)) / self.std.to(x_tensor.device)
        
    def save(self, path):
        with open(path, 'w') as f:
            json.dump({'mean': self.mean.tolist(), 'std': self.std.tolist()}, f)
            
    def load(self, path):
        with open(path, 'r') as f:
            data = json.load(f)
        self.mean = torch.tensor(data['mean'])
        self.std = torch.tensor(data['std'])

class ResBlock(nn.Module):
    def __init__(self, dim, dropout_rate=0.3):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.GELU(),  # Tối ưu 1: Đổi ReLU thành GELU
            nn.Dropout(dropout_rate),
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim)
        )
    def forward(self, x):
        # Tối ưu 2: Thêm hàm kích hoạt sau khi cộng Residual để giữ tính phi tuyến
        return torch.nn.functional.gelu(x + self.block(x))

class TradingMLP(nn.Module):
    def __init__(self, input_dim, output_dim, hidden_dim=256, dropout_rate=0.3):
        super(TradingMLP, self).__init__()
        
        # 1. Input Layer: Thêm Dropout nhẹ để mô phỏng "nhiễu" dữ liệu đầu vào
        self.input_layer = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout_rate * 0.5) 
        )

        # 2. Residual Blocks: Khối học sâu
        self.res_blocks = nn.Sequential(
            ResBlock(hidden_dim, dropout_rate),
            ResBlock(hidden_dim, dropout_rate),
            ResBlock(hidden_dim, dropout_rate)
        )
        
        # 3. Output Layer: (Đã Fix Lỗ Hổng)
        # Bản cũ của bạn đi thẳng từ 256 -> 64 -> output mà không có rào chắn bảo vệ nào.
        # Rất dễ bị học vẹt ở bước cuối cùng này.
        self.output_layer = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.BatchNorm1d(64),        # Thêm Chuẩn hóa
            nn.GELU(),                 # Đổi ReLU -> GELU
            nn.Dropout(dropout_rate),  # Thêm rào chắn Dropout trước khi ra quyết định
            nn.Linear(64, output_dim)
        )

        # 4. Khởi tạo trọng số thông minh (Kaiming He Initialization)
        self.apply(self._init_weights)

    def _init_weights(self, m):
        """ Giúp mô hình hội tụ nhanh hơn ngay từ Epoch đầu tiên """
        if isinstance(m, nn.Linear):
            nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='relu')
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)

    def forward(self, x):
        x = self.input_layer(x)
        x = self.res_blocks(x)
        return self.output_layer(x)
    
class AI_Engine:
    def __init__(self, model_path=MODEL_PATH):
        self.model = None
        self.scaler = None
        self.feature_names = [] 
        self.load(model_path)

    def load(self, model_path):
        if not os.path.exists(model_path) or not os.path.exists(SCALER_PATH): 
            logger.warning(f"Không tìm thấy model tại {model_path} hoặc Scaler tại {SCALER_PATH}")
            return
        
        try:
            with open(INFO_PATH, 'r') as f: info = json.load(f)
            self.feature_names = info.get('feature_names', [])
            input_dim = info['input_dim']
            
            # CHÚ Ý: Lấy output_dim từ INFO_PATH thay vì gán cứng để đảm bảo đồng bộ
            output_dim = info.get('output_dim', 8) 

            self.model = TradingMLP(input_dim, output_dim).to(device)
            self.model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
            self.model.eval()
            self.scaler = MyTorchScaler()
            self.scaler.load(SCALER_PATH)
            logger.success("Đã load Model thành công!")
        except Exception as e:
            logger.critical(f"CRITICAL ERROR khi load model: {e}")
            raise e # <-- Phải raise lỗi ra ngoài để ngắt chương trình, không cho backtest chạy mù

    def predict(self, feature_vector_dict, explore=True):
        if not self.model: 
            # Đổi giá trị trả về thành -1 hoặc quăng lỗi để code backtest biết mà dừng lại
            raise RuntimeError("Chưa load model mà đã gọi hàm predict!")

        vals = []
        for name in self.feature_names:
            vals.append(feature_vector_dict.get(name, 0.0))

        x_tensor = torch.tensor(vals, dtype=torch.float32).unsqueeze(0).to(device)

        with torch.no_grad():
            x_scaled = self.scaler.transform(x_tensor)
            logits = self.model(x_scaled)
            probs = torch.softmax(logits, dim=1)[0]
            conf, pred_class = torch.max(probs, 0)

        # 🔥 RANDOM EXPLORATION (Epsilon-Greedy) 🔥
        if explore and conf.item() < 0.2: #20% ngẫu nhiên   
            pred_class = torch.tensor(random.randint(0, probs.shape[0]-1)).to(device)
            conf = torch.tensor(0.1).to(device)

        return int(pred_class.item()), float(conf.item()), probs.tolist()

# --- 5. HÀM HUẤN LUYỆN
def train_model(df_5m, df_15m, df_1h, df_4h):
    os.makedirs(DATA_DIR, exist_ok=True)
    log_path = os.path.join(DATA_DIR, "trading_memory.csv")
    
    X_list, y_list = [], []
    VALID_FEATURES = []

    # --- CASE 1: EXPERIENCE LOG EXISTS ---
    if os.path.exists(log_path):
        try:
            df_log = pl.read_csv(log_path)
            if len(df_log) >= 10:
                logger.info(f"Found {len(df_log)} experience samples. AI learning from history...")
                for row in df_log.iter_rows(named=True):
                    try:
                        feats = json.loads(row['features_json'])
                        X_list.append(list(feats.values()))

                        correct_val = row['correct']
                        label = int(correct_val) if correct_val is not None else int(row['state'])
                        y_list.append(label)

                        if not VALID_FEATURES: VALID_FEATURES = list(feats.keys())
                    except: continue
        except Exception as e:
            logger.error(f"Error reading log: {e}")

    # --- CASE 2: NO LOG -> INITIALIZE WITH BLANK BRAIN ---
    if len(X_list) < 10:
        logger.warning("No log data found. Initializing blank brain model to collect experience...")
        feats = feature_dataset(df_5m, df_15m, df_1h, df_4h)

        if feats is None or feats.is_empty():
            logger.error("Failed to extract current features.")
            return

        VALID_FEATURES = feats.columns
        INPUT_DIM = len(VALID_FEATURES)
        OUTPUT_DIM = 8
        
        # 1. TẠO SCALER TRƠ (IDENTITY SCALER) CHO BỘ NÃO TRẮNG
        # Gán trung bình = 0 và độ lệch chuẩn = 1 để không bóp méo dữ liệu khi chưa train
        scaler = MyTorchScaler()
        scaler.mean = torch.zeros(INPUT_DIM, dtype=torch.float32)
        scaler.std = torch.ones(INPUT_DIM, dtype=torch.float32)
        scaler.save(SCALER_PATH)
        
        # 2. KHỞI TẠO MODEL TRẮNG VÀ LƯU NGAY (KHÔNG HUẤN LUYỆN)
        # Model lúc này sẽ chứa các trọng số ngẫu nhiên ban đầu (Random weights)
        model = TradingMLP(INPUT_DIM, OUTPUT_DIM).to(device)
        torch.save(model.state_dict(), MODEL_PATH)
        
        # 3. LƯU THÔNG TIN CẤU HÌNH (INFO)
        with open(INFO_PATH, 'w') as f:
            json.dump({
                'input_dim': INPUT_DIM,
                'output_dim': OUTPUT_DIM,
                'feature_names': VALID_FEATURES 
            }, f)
            
        logger.success(f"Đã tạo xong 'Bộ não trắng' (Input: {INPUT_DIM}). Các file weights, scaler, info đã được lưu!")
        logger.info("Hệ thống KAIROS giờ có thể tiếp tục chạy để dự đoán mù và ghi Log. Hãy chạy lại hàm train khi có đủ dữ liệu thực tế.")
        
        return  # THOÁT HÀM TẠI ĐÂY - Bỏ qua toàn bộ phần khởi tạo Optimizer và vòng lặp Epoch bên dưới.

    X_tensor = torch.tensor(X_list, dtype=torch.float32)
    y_tensor = torch.tensor(y_list, dtype=torch.long).to(device)

    scaler = MyTorchScaler()
    scaler.fit(X_tensor)
    X_train_scaled = scaler.transform(X_tensor).to(device)
    scaler.save(SCALER_PATH)

    INPUT_DIM = X_train_scaled.shape[1]
    OUTPUT_DIM = 8
    model = TradingMLP(INPUT_DIM, OUTPUT_DIM).to(device)
    
    optimizer = optim.AdamW(model.parameters(), lr=0.001)

    counts = np.bincount(y_list, minlength=8)
    weights = torch.tensor((1.0 / (counts + 1)) / (1.0 / (counts + 1)).sum() * 8, dtype=torch.float32).to(device)
    criterion = nn.CrossEntropyLoss(weight=weights)

    logger.info(f"Đang huấn luyện bộ lọc trên {len(X_list)} mẫu (Device: {device})...")
    model.train()
    for epoch in range(50):
        optimizer.zero_grad()
        outputs = model(X_train_scaled)
        loss = criterion(outputs, y_tensor)
        loss.backward()
        optimizer.step()

    torch.save(model.state_dict(), MODEL_PATH)
    with open(INFO_PATH, 'w') as f:
        json.dump({
            'input_dim': INPUT_DIM,
            'output_dim': OUTPUT_DIM,
            'feature_names': VALID_FEATURES 
        }, f)
        
    logger.success(f"Đã cập nhật xong Bộ lọc AI. Model sẵn sàng chạy (Input: {INPUT_DIM}).")

def auto_learn_from_log():
    log_path = os.path.join(DATA_DIR, "trading_memory.csv")
    if not os.path.exists(log_path): return

    logger.info("Reviewing experience from live trading history...")
    try:
        df_log = pl.read_csv(log_path)
    except Exception: return

    # Filter good and bad memories
    good_memories = df_log.filter(pl.col('reward') > 0.0)
    bad_memories = df_log.filter(pl.col('reward') < 0.0)

    if len(good_memories) + len(bad_memories) < 10: return

    X_list, y_list = [], []

    # 1. Process good memories
    for row in good_memories.iter_rows(named=True):
        try:
            feats = json.loads(row['features_json']) if isinstance(row['features_json'], str) else row['features_json']
            X_list.append(list(feats.values()))
            y_list.append(int(row['state']))
        except: continue

    # 2. Process bad memories (correct mistakes)
    if len(bad_memories) > 0:
        for row in bad_memories.iter_rows(named=True):
            try:
                feats = json.loads(row['features_json']) if isinstance(row['features_json'], str) else row['features_json']
                wrong_state = int(row['state'])
                corrected_state = wrong_state

                correct_val = row.get('correct')
                has_teacher = correct_val is not None and str(correct_val).strip() != ''
                if has_teacher:
                    corrected_state = int(correct_val)
                else:
                    # Logic tự sửa sai cơ bản nếu không có thầy giáo
                    if wrong_state in [0, 1, 3]: corrected_state = 2 
                    elif wrong_state == 2: corrected_state = 0 
                    elif wrong_state == 5: corrected_state = 0

                if corrected_state != wrong_state:
                    X_list.append(list(feats.values()))
                    y_list.append(corrected_state)
            except: continue

    if not X_list: return

    # Chuyển sang Tensor
    X_train = torch.tensor(X_list, dtype=torch.float32)
    y_train = torch.tensor(y_list, dtype=torch.long).to(device)

    # --- KHỞI TẠO ENGINE ---
    # Lưu ý: Không cần import lại AI_Engine vì đang ở trong cùng file
    engine = AI_Engine() 
    
    # --- KIỂM TRA KHỚP DỮ LIỆU (FIX LỖI 72 vs 120) ---
    input_dim_new = X_train.shape[1]
    input_dim_old = 0
    
    # Lấy kích thước của Scaler cũ nếu có
    if engine.scaler is not None and engine.scaler.mean is not None:
        input_dim_old = engine.scaler.mean.shape[0]

    model = None
    scaler = None
    
    # Nếu dữ liệu mới khác kích thước dữ liệu cũ -> RESET MODEL & SCALER
    if input_dim_new != input_dim_old:
        logger.warning(f"Phát hiện thay đổi dữ liệu (Cũ: {input_dim_old} -> Mới: {input_dim_new}). Tiến hành huấn luyện lại từ đầu...")
        
        # Tạo Scaler mới và fit ngay lập tức với dữ liệu hiện tại
        scaler = MyTorchScaler()
        scaler.fit(X_train)
        
        # Tạo Model mới tương ứng với input_dim mới
        model = TradingMLP(input_dim_new, 8).to(device) # Giả sử output là 8 lớp
        
        # Gán lại vào engine để tí nữa dùng
        engine.model = model
        engine.scaler = scaler
        
        # Cập nhật lại file info để lần sau load đúng
        with open(INFO_PATH, 'w') as f:
            # Lấy tên feature từ dòng đầu tiên của log (nếu có thể) để lưu lại tên cột
            feature_names_new = []
            try:
                first_row_feat = json.loads(good_memories.row(0, named=True)['features_json'])
                feature_names_new = list(first_row_feat.keys())
            except: pass
            
            json.dump({
                'input_dim': input_dim_new,
                'output_dim': 8,
                'feature_names': feature_names_new 
            }, f)
            
    else:
        # Nếu khớp dimension thì dùng tiếp model/scaler cũ
        logger.success(f"Dữ liệu khớp ({input_dim_new} features). Đang tinh chỉnh model...")
        model = engine.model
        scaler = engine.scaler

    # --- TIẾN HÀNH TRAINING ---
    model.train() 
    optimizer = optim.Adam(model.parameters(), lr=0.0001) 
    criterion = nn.CrossEntropyLoss()

    # --- CHUẨN BỊ DỮ LIỆU CHIA BATCH ---
    # CHÚ Ý: Tạm thời giữ dữ liệu ở CPU, KHÔNG dùng .to(device) ở đây để tránh tràn RAM GPU
    X_train_scaled = scaler.transform(X_train).cpu() 
    y_train_cpu = y_train.cpu()

    # Khởi tạo DataLoader để chia nhỏ dữ liệu
    # Nếu vẫn bị lỗi OOM, hãy giảm batch_size xuống 128 hoặc 64
    batch_size = 256 
    dataset = TensorDataset(X_train_scaled, y_train_cpu)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    # --- TIẾN HÀNH TRAINING THEO BATCH ---
    model.train() 
    optimizer = optim.Adam(model.parameters(), lr=0.0001) 
    criterion = nn.CrossEntropyLoss()

    for epoch in range(10): # Train 10 epoch
        total_loss = 0.0
        for batch_X, batch_y in dataloader:
            # Chỉ đưa từng gói dữ liệu nhỏ (256 dòng) lên GPU
            batch_X = batch_X.to(device)
            batch_y = batch_y.to(device)

            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            
        logger.info(f"  + Epoch {epoch+1}/10 - Loss: {total_loss/len(dataloader):.4f}")

    # --- LƯU LẠI MODEL VÀ SCALER MỚI ---
    torch.save(model.state_dict(), MODEL_PATH)
    scaler.save(SCALER_PATH) 
    
    logger.success(f"Đã học xong {len(X_list)} bài học mới trên GPU (Input: {input_dim_new}).")

def train_from_dataframe(df_labeled: pl.DataFrame, epochs=20, batch_size=512):
    """
    Nhận DataFrame đã được label bởi detect_regime_vectorized.
    Trích xuất feature, CẮT 30 NGÀY NHIỄU, CHỈ CẮT GỌT CLASS LỚN (KHÔNG NHÂN BẢN) và huấn luyện Model.
    """
    logger.info("BƯỚC 1: Đang trích xuất Features (Vectorized)...")
    df_feat = features_vectorized(df_labeled)
    
    # Lấy lable từ df_labeled ghép vào df_feat
    df_final = df_feat.join(df_labeled.select(["timestamp", "regime"]), on="timestamp", how="inner")
    
    # ---------------------------------------------------------
    # ✂️ BƯỚC 1: CẮT BỎ 30 NGÀY ĐẦU TIÊN (DATA WARM-UP)
    # ---------------------------------------------------------
    df_final = df_final.sort("timestamp") 
    
    DROP_ROWS = 30 * 24 * 60  # 30 ngày * 24 giờ * 60 phút = 43.200 nến
    if df_final.height > DROP_ROWS:
        df_final = df_final.slice(DROP_ROWS)
        logger.info(f"Đã cắt bỏ {DROP_ROWS} nến (30 ngày đầu) để loại bỏ nhiễu chỉ báo.")
    else:
        logger.warning("Cảnh báo: Dữ liệu quá ngắn, không đủ 30 ngày để cắt!")

    # Tách X (Features) và y (Labels)
    feature_cols = [col for col in df_final.columns if col not in ["timestamp", "regime"]]
    X_numpy = df_final.select(feature_cols).to_numpy()
    y_numpy = df_final.select("regime").to_numpy().flatten()
    
    logger.info(f"Dữ liệu sau khi cắt warmup: {len(X_numpy)} mẫu.")

    # ---------------------------------------------------------
    # ⚖️ BƯỚC 2: CHỈ CẮT GỌT DỮ LIỆU THỪA (PURE DOWNSAMPLING TỐI ĐA)
    # ---------------------------------------------------------
    counts = np.bincount(y_numpy, minlength=8)
    logger.info(f"Phân bổ nhãn thực tế lúc này: {counts}")

    # Lấy mảng đếm của các class Tín Hiệu (từ 1 đến 7)
    minority_counts = counts[1:] 
    valid_minorities = minority_counts[minority_counts > 0]
    
    if len(valid_minorities) > 0:
        # 🔥 ĐÃ SỬA: Lấy ĐÚNG số lượng của class THẤP NHẤT làm Mức trần (Không dùng số cố định)
        limit_cap = int(np.min(valid_minorities)) 
    else:
        # Phòng hờ trường hợp thị trường rác 100% không có bất kỳ tín hiệu 1-7 nào
        limit_cap = len(y_numpy) 

    logger.info(f"Thiết lập Mức Trần (Cap Limit) TUYỆT ĐỐI: {limit_cap} dòng.")

    balanced_indices = []
    for c in range(8):
        if counts[c] == 0: continue 
        
        idx_c = np.where(y_numpy == c)[0]
        
        # Áp dụng trần cho class này (Vẫn giữ đặc quyền cho Regime 0 nhiều gấp rưỡi để tránh Bot bị "ngáo" nhiễu)
        current_limit = int(limit_cap * 1.5) if c == 0 else limit_cap
        
        # Đảm bảo không bốc lố số lượng thực tế đang có
        current_limit = min(current_limit, counts[c])

        if counts[c] > current_limit:
            # CHỈ CẮT GỌT (DOWN-SAMPLE): Bốc ngẫu nhiên cắt bỏ không thương tiếc
            idx_sampled = np.random.choice(idx_c, current_limit, replace=False)
            logger.info(f"Cắt gọt Regime {c}: {counts[c]} -> {current_limit} dòng")
        else:
            # GIỮ NGUYÊN (NO OVERSAMPLING)
            idx_sampled = idx_c
            logger.info(f"  ✅ Giữ nguyên Regime {c}: {counts[c]} dòng")
            
        balanced_indices.extend(idx_sampled)

    # Xáo trộn lộn xộn dữ liệu lên để AI không bị thiên kiến thứ tự
    np.random.shuffle(balanced_indices)
    
    X_balanced = X_numpy[balanced_indices]
    y_balanced = y_numpy[balanced_indices]
    print(f"🚀 Dữ liệu CHUẨN sau khi cắt gọt: {len(X_balanced)} mẫu. Bắt đầu Train!")
    
    # ---------------------------------------------------------

    balanced_indices = []
    for c in range(8):
        if counts[c] == 0: continue 
        
        idx_c = np.where(y_numpy == c)[0]
        
        # Mức trần cho class này (Ưu tiên class 0 được giữ nhiều gấp rưỡi để duy trì độ "tĩnh" của AI)
        current_limit = int(limit_cap * 1.5) if c == 0 else limit_cap

        if counts[c] > current_limit:
            # CHỈ CẮT GỌT (DOWN-SAMPLE): Bốc ngẫu nhiên cắt bỏ ko thương tiếc
            idx_sampled = np.random.choice(idx_c, current_limit, replace=False)
            logger.info(f"Cắt gọt Regime {c}: {counts[c]} -> {current_limit} dòng")
        else:
            # GIỮ NGUYÊN (NO OVERSAMPLING): Lấy tất cả 100% dữ liệu gốc
            idx_sampled = idx_c
            logger.info(f"  ✅ Giữ nguyên Regime {c}: {counts[c]} dòng (Không nhân bản)")
            
        balanced_indices.extend(idx_sampled)

    # Xáo trộn lộn xộn dữ liệu lên để AI không bị thiên kiến thứ tự
    np.random.shuffle(balanced_indices)
    
    X_balanced = X_numpy[balanced_indices]
    y_balanced = y_numpy[balanced_indices]
    print(f"🚀 Dữ liệu CHUẨN sau khi cắt gọt: {len(X_balanced)} mẫu. Bắt đầu Train!")
    # ---------------------------------------------------------

    # 2. Chuẩn bị Tensor & Scaler 
    X_tensor = torch.tensor(X_balanced, dtype=torch.float32)
    y_tensor = torch.tensor(y_balanced, dtype=torch.long)
    
    scaler = MyTorchScaler()
    scaler.fit(X_tensor)
    X_scaled = scaler.transform(X_tensor)
    scaler.save(SCALER_PATH)

    # 3. Khởi tạo Model
    input_dim = len(feature_cols)
    output_dim = 8
    model = TradingMLP(input_dim, output_dim).to(device)

    # DataLoader KHÔNG DÙNG Sampler nữa
    dataset = TensorDataset(X_scaled, y_tensor)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    # Khởi tạo Loss và Optimizer (Thêm weight_decay để chống quá khớp nếu dữ liệu bị cắt đi nhiều)
    criterion = nn.CrossEntropyLoss().to(device)
    optimizer = optim.AdamW(model.parameters(), lr=0.001, weight_decay=1e-4)

    logger.info(f"🔥 BƯỚC 3: Bắt đầu huấn luyện Model trên {device}...")
    model.train()
    for epoch in range(epochs):
        total_loss = 0.0
        for batch_X, batch_y in dataloader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            
        if (epoch + 1) % 5 == 0 or epoch == 0:
            logger.info(f"   + Epoch {epoch+1}/{epochs} | Loss: {total_loss/len(dataloader):.4f}")

    # 4. Lưu Model và Info
    torch.save(model.state_dict(), MODEL_PATH)
    with open(INFO_PATH, 'w') as f:
        json.dump({'input_dim': input_dim, 'output_dim': output_dim, 'feature_names': feature_cols}, f)
        
    logger.success("Đã học xong và lưu Model!")
