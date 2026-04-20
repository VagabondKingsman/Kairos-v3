# Hướng Dẫn Tích Hợp Kairos MCP Server vào Claude Desktop và Cursor

Để điều khiển toàn bộ "Hội đồng AI" của Kairos Quant System v3.0 thông qua giao diện chat tự nhiên của Claude hoặc tích hợp thẳng vào IDE lập trình, anh hãy cấu hình theo các hướng dẫn dưới đây.

**Lưu ý:** Vui lòng thay thế đường dẫn tới file chạy `python` nếu anh đang sử dụng Virtual Environment (Ví dụ: `venv\Scripts\python.exe`).

---

## 1. Tích hợp vào Claude Desktop

Claude Desktop hỗ trợ giao thức MCP mặc định. Khi cấu hình thành công, Claude sẽ có biểu tượng cái búa (Tools) chứa các công cụ của Kairos.

**Bước 1:** Mở tệp cấu hình của Claude Desktop:
- **Windows:** Bấm phím `Win + R`, nhập `%APPDATA%\Claude\claude_desktop_config.json` và nhấn Enter.
- **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`

**Bước 2:** Chỉnh sửa file JSON bằng đoạn mã sau (Thay đổi đường dẫn thư mục nếu cần thiết):

```json
{
  "mcpServers": {
    "Kairos_Quant_System": {
      "command": "python",
      "args": [
        "D:\\The V\\Kairos_Quant_System_v3.0\\a02_tro_ly_nghien_cuu_ai\\may_chu_mcp.py"
      ]
    }
  }
}
```

**Bước 3:** Khởi động lại Claude Desktop hoàn toàn (Tắt ở System Tray góc dưới màn hình rồi bật lại).
**Bước 4:** Bắt đầu chat với Claude bằng câu lệnh: *"Hãy gọi danh_sach_cau_hinh_bay_dan để xem có những chuyên gia nào trong quỹ của tôi."*

---

## 2. Tích hợp vào Cursor IDE

Cursor có khả năng tích hợp thẳng MCP Server để hỗ trợ trong quá trình code và phát triển chiến lược.

**Bước 1:** Trong Cursor, mở cửa sổ Settings (Bấm nút bánh răng góc phải trên hoặc tổ hợp phím `Ctrl + ,`).
**Bước 2:** Điều hướng đến mục **Features** > **MCP Servers**.
**Bước 3:** Bấm nút **+ Add New MCP Server** và cấu hình như sau:

- **Name:** `Kairos_Quant_System`
- **Type:** `command`
- **Command:** `python "D:\The V\Kairos_Quant_System_v3.0\a02_tro_ly_nghien_cuu_ai\may_chu_mcp.py"`

*(Nhớ giữ nguyên dấu ngoặc kép bọc đường dẫn vì tên thư mục "The V" có khoảng trắng).*

**Bước 4:** Nhấn **Save**. Lúc này biểu tượng chấm tròn cạnh tên server sẽ chuyển sang màu xanh lá cây 🟢 nghĩa là đã kết nối thành công.
**Bước 5:** Trong khung Chat của Cursor, bấm `@` và chọn công cụ của Kairos để bắt đầu sử dụng.

---

## 3. Chế độ Máy Chủ Web (Dành cho Dashboard v3)

Nếu anh định xây dựng giao diện web riêng biệt (VD: Next.js/React) tại `a06_giao_dien_v3`, anh có thể mở cổng SSE (Server-Sent Events) độc lập mà không cần dùng đến Claude/Cursor.

**Mở Terminal (CMD/PowerShell) và gõ lệnh:**
```bash
python "D:\The V\Kairos_Quant_System_v3.0\a02_tro_ly_nghien_cuu_ai\may_chu_mcp.py" --transport sse --port 8900
```

Hệ thống sẽ mở cổng `http://localhost:8900/sse` và sẵn sàng nhận lệnh từ Web Front-end!
