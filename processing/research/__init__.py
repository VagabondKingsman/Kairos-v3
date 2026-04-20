"""
processing.research — Bộ 64 Kỹ Năng Phân Tích Thị Trường

Mỗi kỹ năng là một thư mục con độc lập, cung cấp một tool/skill
có thể được gọi bởi Agent A03 (ReAct).

Danh mục kỹ năng bao gồm:
    - Phân tích kỹ thuật cơ bản (nến Nhật, Ichimoku, SMC...)
    - Phân tích tài chính (báo cáo tài chính, định giá...)
    - Phân tích on-chain và crypto (funding, stablecoin...)
    - Phân tích vĩ mô và địa chính trị
    - Machine Learning chiến lược
    - Phân tích VNStock và toàn cầu (YFinance)
    - Và nhiều hơn nữa...

Máy chủ MCP:
    python -m processing.research.may_chu_mcp
"""
from pathlib import Path

# Danh sách kỹ năng được đăng ký (64 subdirectory)
_KY_NANG_DIR = Path(__file__).parent / "ky_nang"

def lay_danh_sach_ky_nang() -> list:
    """Trả về danh sách tên tất cả kỹ năng đã cài đặt."""
    if not _KY_NANG_DIR.exists():
        return []
    return sorted([d.name for d in _KY_NANG_DIR.iterdir() if d.is_dir()])

__all__ = ["lay_danh_sach_ky_nang"]
