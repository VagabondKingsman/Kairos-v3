"""a02 - Công cụ AI — Registry builder.

Cung cấp hàm ``tao_bo_cong_cu()`` để tạo ToolRegistry đầy đủ,
và ``tao_bo_cong_cu_loc()`` để tạo registry chỉ chứa tools cho phép.

Tools có sẵn:
    - CongCuChayLenh     : Chạy lệnh terminal
    - CongCuDocFile      : Đọc file (PDF, CSV, MD)
    - CongCuGhiFile      : Ghi file
    - CongCuKiemThu      : Backtest tool cho AI
    - CongCuLietKeKyNang : list_skills — liệt kê 68+ skills có sẵn
    - CongCuDocKyNang    : load_skill — tải SKILL.md vào context
    - CongCuTriThucTTiTruong: truy_van_tri_thuc — query đồ thị quan hệ tài sản
    - CongCuLietKeChienLuocA04: list_a04_strategies — liệt kê SignalEngine đã code sẵn trong a04
"""

from processing.research.cong_cu_ai.cong_cu_co_so import (
    CongCuCoSo,
    SoDoTool,
)


def tao_bo_cong_cu() -> SoDoTool:
    """Tạo ToolRegistry đầy đủ với tất cả tools có sẵn.

    Returns:
        SoDoTool chứa tất cả tools đã đăng ký.
    """
    from processing.research.cong_cu_ai.cong_cu_chay_lenh import CongCuChayLenh
    from processing.research.cong_cu_ai.cong_cu_doc_file import (
        CongCuDocFile,
        CongCuGhiFile,
    )
    from processing.research.cong_cu_ai.cong_cu_kiem_thu import CongCuKiemThu
    from processing.research.cong_cu_ai.cong_cu_ky_nang import (
        CongCuDocKyNang,
        CongCuLietKeKyNang,
        CongCuLietKeChienLuocA04,
    )
    from processing.research.do_thi_tri_thuc_thi_truong.truy_van_tri_thuc import (
        CongCuTriThucTTiTruong,
    )

    registry = SoDoTool()
    for tool in [
        CongCuChayLenh(),
        CongCuDocFile(),
        CongCuGhiFile(),
        CongCuKiemThu(),
        CongCuLietKeKyNang(),
        CongCuDocKyNang(),
        CongCuTriThucTTiTruong(),
        CongCuLietKeChienLuocA04(),
    ]:
        registry.dang_ky(tool)

    return registry


def tao_bo_cong_cu_loc(danh_sach_ten: list[str]) -> SoDoTool:
    """Tạo ToolRegistry chỉ chứa các tools trong danh sách cho phép.

    Dùng cho Swarm worker — mỗi agent chỉ thấy tools được phép.

    Args:
        danh_sach_ten: Danh sách tên tools cần bao gồm.

    Returns:
        SoDoTool đã lọc.
    """
    full = tao_bo_cong_cu()
    filtered = SoDoTool()
    for name in danh_sach_ten:
        tool = full.lay(name)
        if tool:
            filtered.dang_ky(tool)
    return filtered


__all__ = [
    "CongCuCoSo",
    "SoDoTool",
    "tao_bo_cong_cu",
    "tao_bo_cong_cu_loc",
]
