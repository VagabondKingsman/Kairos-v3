import logging
from abc import ABC, abstractmethod
from typing import Dict, Union

import polars as pl
from processing.backtest.nen_htf.xay_dung_nen_htf import HTFBuilder

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """Lớp cơ sở (Base Class) cho tất cả các chiến lược giao dịch sinh bởi AI.
    
    Cung cấp:
    - Khởi tạo thông số (params).
    - Auto-healing: Tự động phát hiện và bọc lại nếu AI trả về Polars Expr thay vì Series.
    - Tự động nhận diện thị trường và đồng bộ giờ (Time Anchor) cho đa khung thời gian.
    - Cắt giá trị tín hiệu về mức an toàn [-1.0, 1.0].
    """

    def __init__(self, **params):
        self.params = params
        # Công cụ nội suy đa khung thời gian
        self._htf = HTFBuilder()
        # Biến lưu trữ mã giao dịch đang được xử lý (để tự động nhận diện offset)
        self.current_code = ""
        
    def get_param(self, name: str, default_value):
        """Lấy tham số an toàn"""
        return self.params.get(name, default_value)

    def _get_market_offset(self, code: str) -> Union[str, None]:
        """Tự động nhận diện thị trường qua mã (symbol) và trả về offset chuẩn."""
        code_upper = code.upper()
        
        # 1. Crypto (VD: BTC-USDT, ETH/USDT) - Cắt ngày lúc 00:00 UTC
        if "USDT" in code_upper or "-" in code_upper or "/" in code_upper:
            return None
            
        # 2. Chứng khoán Hong Kong (VD: 00700.HK) - Mở cửa 09:30 sáng giờ HK
        if code_upper.endswith(".HK"):
            return "9h30m"
            
        # 3. Chứng khoán Mỹ (VD: AAPL.US) - Mở cửa 09:30 sáng giờ EST
        if code_upper.endswith(".US"):
            return "9h30m"
            
        # 4. Forex / Global (VD: EURUSD.FX) - Đóng cửa lúc 17:00 EST (Quy về 22h UTC)
        if code_upper.endswith(".FX") or len(code_upper) == 6:
            return "22h" 
            
        # 5. Mặc định: Chứng khoán Việt Nam (VD: FPT, VNM) - Mở cửa 09:00 sáng
        return "9h"

    def auto_htf(self, df: pl.DataFrame, time_frame: str, prefix: str = None) -> pl.DataFrame:
        """
        Hàm tiện ích cho AI: Tự động gộp nến và chèn offset chuẩn theo thị trường.
        AI chỉ cần gọi: df = self.auto_htf(df, "1d")
        """
        offset = self._get_market_offset(self.current_code)
        
        # Gọi thẳng hàm add_to_dataframe (hoặc them_vao_df) từ HTFBuilder
        return self._htf.them_vao_df(df, time_frame=time_frame, offset=offset, prefix=prefix)

    def generate(self, data_map: Dict[str, pl.DataFrame]) -> Dict[str, pl.Series]:
        """Hàm chính được Động cơ A04 gọi để lấy tín hiệu."""
        signals = {}
        for code, df in data_map.items():
            try:
                # LƯU Ý: Gắn mã hiện tại vào class để hàm auto_htf tự nhận diện thị trường
                self.current_code = code 
                
                # 1. Gọi logic phân tích của lớp con (chiến lược cụ thể do AI viết)
                raw_result = self.compute(df)
                
                # 2. Auto-healing: Ép kiểu và bảo vệ
                if isinstance(raw_result, pl.Expr):
                    # Nếu AI trả về Expr (do dùng pl.when.then), ta tự động evaluate nó
                    final_series = df.select(raw_result.alias("signal"))["signal"]
                elif isinstance(raw_result, pl.Series):
                    final_series = raw_result
                else:
                    logger.warning(f"Chiến lược {code} trả về kiểu {type(raw_result)} không hợp lệ. Khởi tạo mảng 0.")
                    final_series = pl.Series("signal", [0.0] * len(df))
                
                # 3. Fill null và Clip giá trị
                final_series = (
                    final_series
                    .cast(pl.Float64, strict=False)
                    .fill_null(0.0)
                    .clip(-1.0, 1.0)
                )
                
                signals[code] = final_series
            except Exception as e:
                logger.error(f"Lỗi khi chạy logic chiến lược cho mã {code}: {e}")
                # Fallback an toàn nếu có lỗi nội bộ
                signals[code] = pl.Series("signal", [0.0] * len(df))
                
        return signals

    @abstractmethod
    def compute(self, df: pl.DataFrame) -> Union[pl.Expr, pl.Series]:
        """Lớp con (AI sinh ra) CHỈ CẦN tập trung viết logic ở đây.
        ...
        """
        pass