#!/usr/bin/env python3
"""Máy chủ MCP (Model Context Protocol) cho Kairos Quant System.

Quản lý kết nối và giao thức, bộc lộ các chức năng của Lõi Bầy Đàn (Swarm Engine)
và các Công cụ Nghiên cứu ra ngoại vi (Cursor, Claude Desktop, v.v.).

Cách sử dụng:
    python may_chu_mcp.py                    # Giao thức stdio (mặc định)
    python may_chu_mcp.py --transport sse    # Giao thức SSE cho Web clients
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Đảm bảo thư mục gốc của dự án nằm trong sys.path để import dễ dàng
THU_MUC_GOC = Path(__file__).resolve().parents[1]
if str(THU_MUC_GOC) not in sys.path:
    sys.path.insert(0, str(THU_MUC_GOC))

# Import thư viện MCP
from fastmcp import FastMCP

# Khởi tạo Máy chủ
mcp = FastMCP("Kairos-Quant")

# ===========================================================================
# Tiện ích khởi tạo Kho lưu trữ Bầy Đàn
# ===========================================================================

def _lay_kho_luu_tru():
    """Tạo và trả về đối tượng LuuTruPhien để truy xuất dữ liệu trên đĩa."""
    from services.agents.cot_loi_bay_dan import LuuTruPhien
    thu_muc_runs = THU_MUC_GOC / ".kairos" / "runs"
    thu_muc_runs.mkdir(parents=True, exist_ok=True)
    return LuuTruPhien(thu_muc_goc=thu_muc_runs)

def _dinh_dang_phien(phien) -> dict:
    """Định dạng đối tượng PhienChayBayDan thành Từ điển JSON (Dict)."""
    return {
        "id_phien": phien.id,
        "trang_thai": phien.trang_thai.value,
        "cau_hinh_goc": phien.ten_cau_hinh,
        "tao_luc": phien.tao_luc,
        "nhiem_vu": [
            {
                "id": t.id,
                "id_tac_tu": t.id_tac_tu,
                "trang_thai": t.trang_thai.value,
                "tom_tat": t.tom_tat,
            }
            for t in phien.danh_sach_nhiem_vu
        ],
        "bao_cao_cuoi_cung": phien.bao_cao_cuoi_cung,
        "tong_token_dau_vao": phien.tong_token_dau_vao,
        "tong_token_dau_ra": phien.tong_token_dau_ra,
    }


# ===========================================================================
# Công cụ Cấu hình Bầy Đàn
# ===========================================================================

@mcp.tool
def danh_sach_cau_hinh_bay_dan() -> str:
    """Liệt kê danh sách các Cấu hình Chuyên gia (Presets) của Hệ thống Kairos.

    Mỗi cấu hình đại diện cho một "Hội đồng AI" chuyên biệt (Ví dụ: Nhóm Phân tích Vĩ mô,
    Ban Cổ phiếu Toàn cầu, Phòng Nghiên cứu Cặp tiền).
    
    Trả về: Tên cấu hình, mô tả, số lượng tác tử và các biến đầu vào yêu cầu.
    """
    from services.agents.cot_loi_bay_dan import danh_sach_cau_hinh
    danh_sach = danh_sach_cau_hinh()
    return json.dumps(danh_sach, ensure_ascii=False, indent=2)


# ===========================================================================
# Công cụ Điều hành (Runners)
# ===========================================================================

@mcp.tool
def chay_bay_dan(ten_cau_hinh: str, bien_nguoi_dung: dict[str, str]) -> str:
    """Khởi chạy một phiên hội đồng AI (Swarm Run) và trả về báo cáo cuối cùng.

    Tự động lắp ráp các chuyên gia dựa trên `ten_cau_hinh` và chạy quy trình DAG.
    Ví dụ: 'ban_kinh_doanh_chenh_lech_thong_ke' sẽ chạy nhóm Stat-Arb.

    Sử dụng danh_sach_cau_hinh_bay_dan() để xem danh sách cấu hình và biến yêu cầu.

    Args:
        ten_cau_hinh: Tên file cấu hình chuyên gia (Không chứa đuôi .yaml).
        bien_nguoi_dung: Biến do người dùng truyền vào (Ví dụ: {"ticker": "VNM"}).
    """
    from services.agents.cot_loi_bay_dan import VongLapThucThi, TrangThaiPhien
    
    kho_luu_tru = _lay_kho_luu_tru()
    vong_lap = VongLapThucThi(kho_luu_tru=kho_luu_tru)

    try:
        phien_chay = vong_lap.bat_dau_phien(ten_cau_hinh, bien_nguoi_dung)
    except FileNotFoundError as exc:
        return json.dumps({"trang_thai": "loi", "loi": str(exc)}, ensure_ascii=False)
    except ValueError as exc:
        return json.dumps({"trang_thai": "loi", "loi": f"Lỗi đồ thị DAG: {exc}"}, ensure_ascii=False)

    # Chặn luồng hiện tại để chờ kết quả (Tối đa 30 phút = 360 * 5s)
    # Lõi bầy đàn sẽ chạy ở Background Thread. Ở đây ta chỉ Polling kiểm tra DB.
    for _ in range(360):
        time.sleep(5)
        phien_hien_tai = kho_luu_tru.tai_phien(phien_chay.id)
        
        if phien_hien_tai is None:
            return json.dumps({"trang_thai": "loi", "loi": "Mất kết nối với cơ sở dữ liệu phiên chạy"}, ensure_ascii=False)
            
        if phien_hien_tai.trang_thai in (TrangThaiPhien.hoan_thanh, TrangThaiPhien.that_bai, TrangThaiPhien.bi_huy):
            danh_sach_nhiem_vu = [
                {"id": t.id, "id_tac_tu": t.id_tac_tu, "trang_thai": t.trang_thai.value, "tom_tat": t.tom_tat}
                for t in phien_hien_tai.danh_sach_nhiem_vu
            ]
            return json.dumps({
                "trang_thai": phien_hien_tai.trang_thai.value,
                "cau_hinh": ten_cau_hinh,
                "id_phien": phien_hien_tai.id,
                "bao_cao_cuoi_cung": phien_hien_tai.bao_cao_cuoi_cung,
                "nhiem_vu": danh_sach_nhiem_vu,
                "tong_token_dau_vao": phien_hien_tai.tong_token_dau_vao,
                "tong_token_dau_ra": phien_hien_tai.tong_token_dau_ra,
            }, ensure_ascii=False, indent=2)

    return json.dumps({"trang_thai": "loi", "loi": "Phiên chạy bị Quá giờ (Timeout) sau 30 phút"}, ensure_ascii=False)


# ===========================================================================
# Công cụ Giám sát (Monitoring)
# ===========================================================================

@mcp.tool
def lay_trang_thai_bay_dan(id_phien: str) -> str:
    """Kiểm tra trạng thái hiện tại của một phiên Bầy Đàn (Swarm Run).

    Dùng để theo dõi tiến độ của các chiến dịch dài hạn mà không bị block.
    Trả về trạng thái chung, số dư Token tiêu thụ, và tiến độ từng Task.

    Args:
        id_phien: Mã ID phiên chạy do hệ thống sinh ra.
    """
    kho_luu_tru = _lay_kho_luu_tru()
    phien_hien_tai = kho_luu_tru.tai_phien(id_phien)
    if phien_hien_tai is None:
        return json.dumps({"trang_thai": "loi", "loi": f"Không tìm thấy phiên chạy: {id_phien}"}, ensure_ascii=False)
    return json.dumps(_dinh_dang_phien(phien_hien_tai), ensure_ascii=False, indent=2)


@mcp.tool
def danh_sach_phien_chay(gioi_han: int = 20) -> str:
    """Liệt kê các chiến dịch hội đồng (Swarm Runs) diễn ra gần đây nhất.

    Trả về ID phiên, cấu hình sử dụng, trạng thái và mốc thời gian.
    Để xem chi tiết kết quả của một phiên, sử dụng lay_trang_thai_bay_dan(id_phien).

    Args:
        gioi_han: Số lượng phiên tối đa cần hiển thị (Mặc định: 20).
    """
    kho_luu_tru = _lay_kho_luu_tru()
    danh_sach = kho_luu_tru.danh_sach_phien(gioi_han=gioi_han)
    ket_qua = []
    for phien in danh_sach:
        ket_qua.append({
            "id_phien": phien.id,
            "cau_hinh_goc": phien.ten_cau_hinh,
            "trang_thai": phien.trang_thai.value,
            "tao_luc": phien.tao_luc,
            "tong_token_dau_vao": phien.tong_token_dau_vao,
            "tong_token_dau_ra": phien.tong_token_dau_ra,
        })
    return json.dumps(ket_qua, ensure_ascii=False, indent=2)


# ===========================================================================
# Điểm khởi chạy (Entry Point)
# ===========================================================================

def main():
    """Điểm kích hoạt command-line cho MCP Server."""
    import argparse

    parser = argparse.ArgumentParser(description="Máy chủ MCP Kairos Quant System")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio",
                        help="Phương thức vận chuyển MCP (Mặc định: stdio)")
    parser.add_argument("--port", type=int, default=8900,
                        help="Cổng SSE (Chỉ dùng khi --transport sse)")
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
