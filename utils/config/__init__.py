"""
utils.config — Trung Tâm Cấu Hình KAIROS v3.0

MỌI biến cấu hình (API key, URL, timeout, tham số hệ thống) đều được
đọc và expose từ đây. Không module nào được dùng os.environ trực tiếp
hoặc gọi load_dotenv() riêng lẻ.

Cách dùng:
    from utils.config import cfg

    # LLM
    client = OpenAI(api_key=cfg.llm.api_key, base_url=cfg.llm.base_url)
    model  = cfg.llm.model_name

    # Dữ liệu
    key = cfg.data.okx_api_key

    # Hệ thống
    timeout = cfg.system.timeout_seconds
"""
from pathlib import Path
from utils.config.cau_hinh import cfg
from utils.config.quan_ly_danh_muc import TradingConfigManager

# Khởi tạo tự động trading_cfg
_trading_config_path = Path(__file__).parent / "danh_muc_giao_dich.json"
trading_cfg = TradingConfigManager(_trading_config_path)

__all__ = ["cfg", "trading_cfg"]
