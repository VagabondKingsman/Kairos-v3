---
name: doc_tai_lieu
description: Đọc các tài liệu PDF (Luận văn, Báo cáo thường niên, Báo cáo phân tích nghiên cứu), tự động trích xuất các trang văn bản và áp dụng công nghệ OCR (Nhận dạng ký tự quang học) cho các trang hình ảnh/scan. Yêu cầu sử dụng công cụ `read_document`.
category: tool
---
# Đọc Tài liệu PDF (Document Reader)

## Mục đích

Đọc toàn văn các tài liệu PDF và tự động xử lý 2 loại trang:
- **Trang Văn bản** (Đa số các Luận văn và Báo cáo kỹ thuật số) → Trích xuất trực tiếp trong vài mili-giây.
- **Trang Hình ảnh / Scan** (Biểu đồ trong Báo cáo thường niên, Báo cáo nghiên cứu dạng ảnh chụp) → Nhận dạng quang học (OCR) hỗ trợ tiếng Việt, Trung, Anh.

Áp dụng cho các tài liệu PDF như: Luận văn học thuật, Báo cáo tài chính thường niên, Báo cáo phân tích của công ty chứng khoán, Các thông báo, và Hợp đồng.

## Cách sử dụng

**Gọi trực tiếp công cụ `read_document` (TUYỆT ĐỐI KHÔNG dùng bash để viết script Python):**

```python
read_document(file_path="uploads/paper.pdf")
read_document(file_path="uploads/annual_report.pdf", pages="1-10")
read_document(file_path="uploads/research.pdf", pages="1,3,15-20")
```

**Lệnh cấm**: Không được chạy script Python từ terminal (`bash`) để đọc PDF. Bắt buộc phải gọi tool `read_document` có sẵn của hệ thống.

## Định dạng Trả về (Return Format)

```json
{
  "status": "ok",
  "file": "paper.pdf",
  "total_pages": 45,
  "pages_read": 45,
  "ocr_pages": 3,
  "char_count": 52000,
  "truncated": true,
  "text": "--- Page 1 ---\n...\n--- Page 5 [OCR] ---\n..."
}
```

- `ocr_pages`: Số lượng trang phải nhận dạng bằng OCR (Trang ảnh / Scan).
- `truncated`: Bằng `true` nếu nội dung vượt quá giới hạn 15.000 ký tự và bị cắt xén.
- Dòng `[OCR]` chỉ báo cho bạn biết trang đó được đọc bằng máy quét hình ảnh.

## Các Quy trình Phổ biến (Workflows)

### Tóm tắt Luận văn Học thuật
```text
1. read_document(file_path="paper.pdf")  → Lấy toàn văn.
2. Phân tích văn bản, trích xuất phần Tóm tắt (Abstract), Phương pháp nghiên cứu, và Kết luận.
3. In ra bản tóm tắt cho người dùng.
```

### Phân tích Báo cáo Thường niên (Annual Report)
```text
1. read_document(file_path="annual_report.pdf", pages="1-5")  → Đọc phần tóm lược trước.
2. Từ phần tóm lược/Mục lục, khoanh vùng số trang của các phần quan trọng.
3. read_document(file_path="...", pages="15-25")  → Đọc đúng phần Dữ liệu Tài chính.
4. Trích xuất các chỉ số biên lợi nhuận, doanh thu.
```

### Review Báo cáo Phân tích
```text
1. read_document(file_path="research.pdf")  → Lấy toàn văn báo cáo.
2. Trích xuất Luận điểm đầu tư (Core thesis), Giá mục tiêu (Target price), và Các rủi ro tiềm ẩn.
```

## Lưu ý

- Nếu nội dung dài hơn 15.000 ký tự, phần đuôi sẽ bị cắt đi. Đối với tài liệu dài, hãy dùng tham số `pages` để đọc cuốn chiếu từng phần.
- Quá trình đọc trang OCR rất chậm (khoảng 1-3 giây / trang), trong khi trang văn bản thuần túy chỉ mất vài mili-giây.
- Thuật toán OCR đối với các Bảng biểu phức tạp (Table) trong hình ảnh có thể không hoàn hảo, dữ liệu các cột có thể bị lệch. Bạn cần tự kiểm tra chéo các con số.
- Công cụ này CHỈ hỗ trợ định dạng PDF.
