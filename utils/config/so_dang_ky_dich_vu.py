from typing import Any, Dict
from utils.helpers.bo_ghi_log_he_thong import logger

class SoDangKyDichVu:
    """Registry Pattern để quản lý các tài nguyên dùng chung như ML models, cấu hình."""
    _thuc_the = None

    def __new__(cls):
        if cls._thuc_the is None:
            cls._thuc_the = super(SoDangKyDichVu, cls).__new__(cls)
            cls._thuc_the._dich_vu = {}
        return cls._thuc_the

    def dang_ky(self, ten: str, dich_vu: Any):
        self._dich_vu[ten] = dich_vu
        logger.debug(f"Đã đăng ký dịch vụ: {ten}")

    def lay(self, ten: str) -> Any:
        if ten not in self._dich_vu:
            logger.warning(f"Dịch vụ chưa được đăng ký: {ten}")
            return None
        return self._dich_vu[ten]

# Khởi tạo singleton
_so_dang_ky = SoDangKyDichVu()

def dang_ky_mo_hinh_ml(ten: str, mo_hinh: Any):
    _so_dang_ky.dang_ky(f"ml_model_{ten}", mo_hinh)

def lay_mo_hinh_ml(ten: str) -> Any:
    return _so_dang_ky.lay(f"ml_model_{ten}")
