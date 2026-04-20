---
name: doc_trang_web
description: Công cụ Đọc trang Web (Web reader) — Biến các đường link URL, bài báo tài chính, và tài liệu API thành văn bản Markdown sạch sẽ. Dùng trực tiếp tool read_url, không dùng bash.
category: tool
---

# Đọc Trang Web (Web Reading)

## Mục đích

Biến bất kỳ đường link URL nào thành đoạn text Markdown sạch sẽ, tự động gỡ bỏ quảng cáo, thanh điều hướng (navigation) và các thành tố HTML gây xao nhãng.
Cực kỳ hữu dụng cho:
- Đọc tài liệu API (Cách kết nối `OKX`, `yfinance`, v.v.).
- Đọc các bài blog phân tích kỹ thuật, báo cáo thị trường.
- Lấy báo cáo nghiên cứu và các thông báo mới nhất.
- Đọc các trang README hoặc Wiki trên GitHub.

## Hướng dẫn Sử dụng (Dành cho AI)

**Gọi TRỰC TIẾP công cụ `read_url` (Cấm tuyệt đối việc dùng tool `bash` để chạy lệnh `curl` hay `requests`):**

```python
# Gọi Tool (Chỉ dành cho mô hình AI gọi hàm)
read_url(url="https://docs.okx.com/api/v5")
```

Kết quả trả về sẽ ở định dạng JSON:
```json
{
  "status": "ok",
  "title": "Tên bài viết / Trang Web",
  "url": "URL gốc",
  "content": "Nội dung trang web đã được format sạch sẽ dưới dạng Markdown",
  "length": 12345
}
```

## Các Lưu ý Quan trọng

- Nếu trang web quá dài (> 8000 ký tự), nội dung sẽ bị cắt bớt ở phần cuối, kèm theo độ dài tổng cộng được ghi chú lại.
- Một số trang web có hệ thống chống Bot (Anti-bot / Cloudflare) có thể chặn Jina Reader (trả về lỗi HTTP 451 hoặc 403). Nếu gặp trường hợp này, MỚI ĐƯỢC PHÉP chuyển sang dùng `bash` kết hợp thư viện `requests` kèm Headers mạo danh Trình duyệt (User-Agent).
- Các trang web viết bằng React/Vue (Single Page Application - SPA) đôi khi chỉ trả về các thẻ HTML rỗng vì không có Javascript thực thi.
- Hỗ trợ tiếng Việt và các ngôn ngữ khác hoàn toàn bình thường.

## Ví dụ Tình huống Phổ biến

### 1. Đọc Tài liệu API
Khi người dùng yêu cầu "Cập nhật lại cách gọi API của sàn OKX", hãy dùng `read_url` trỏ tới trang Docs của OKX.
```python
read_url(url="https://www.okx.com/docs-v5/en/")
```

### 2. Đọc Bài báo Tài chính
Đọc một bài phân tích Macro về Cục dự trữ Liên bang (FED) để lấy ý chính.
```python
read_url(url="https://www.cnbc.com/finance/")
```

### 3. Tìm hiểu dự án Mã nguồn mở
Lấy nội dung file README của một dự án Github để biết cách cài đặt.
```python
read_url(url="https://github.com/ccxt/ccxt")
```
