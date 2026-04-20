---
name: chuan_doan_backtest
description: Chẩn đoán các lần chạy backtest thất bại hoặc hiệu suất kém, tìm ra nguyên nhân gốc rễ và sửa lỗi code.
category: tool
---

# Chẩn đoán Backtest (Backtest Diagnosis)

## Tổng quan

Sử dụng kỹ năng này khi một lần chạy backtest gặp lỗi (crash), không sinh ra giao dịch, hoặc cho kết quả quá tệ.

## Quy trình Chẩn đoán

1. **Đọc báo cáo**: Xem file `artifacts/metrics.csv`, `equity.csv`, và `trades.csv`.
2. **Đọc code**: Xem file `code/signal_engine.py` và `config.json`.
3. **Phân loại lỗi**: Đối chiếu với bảng phân loại lỗi bên dưới để tìm nguyên nhân gốc rễ.
4. **Sửa lỗi**: Sửa code `signal_engine.py`, sau đó chạy lại lệnh backtest.
5. **Xác nhận**: Đọc lại `metrics.csv` mới để đảm bảo lỗi đã được khắc phục.

## Bảng Phân loại Lỗi

### Lỗi Runtime (`exit_code != 0`)

| Loại lỗi | Nguyên nhân phổ biến | Cách sửa |
|---------|---------|---------|
| ImportError | Thiếu thư viện | `bash("pip install xxx")` |
| KeyError | Sai tên cột DataFrame | Kiểm tra lại tên cột thực tế trong `data_map` |
| IndexError | Dữ liệu rỗng hoặc độ dài không đủ | Thêm các hàm kiểm tra độ dài (length checks) |
| TypeError | Sai kiểu dữ liệu của tín hiệu | Đảm bảo trả về `pd.Series` |

### Lỗi Logic (Backtest chạy thành công nhưng kết quả bất thường)

1. **Không có giao dịch (`trade_count=0`)**: Lỗi logic tạo tín hiệu. Điều kiện vào lệnh quá khắt khe khiến tín hiệu luôn bằng 0. Kiểm tra lại điều kiện mua/bán.
2. **Giao dịch quá trễ** (Lệnh đầu tiên diễn ra sau hơn 2 năm kể từ ngày bắt đầu): Lỗi do khung nhìn (lookback window) quá dài, hoặc hàm `dropna` đã xóa quá nhiều dữ liệu đầu. Hãy thu ngắn cửa sổ lookback.
3. **Mức sử dụng vốn < 50%** (Đa số tiền để không): Lỗi quản lý vị thế. Tín hiệu quá thưa thớt, hoặc chia tỷ trọng sai.
4. **Còn vị thế mở ở ngày cuối cùng**: Lỗi thiếu tín hiệu đóng lệnh (exit). Cần thêm logic tự động thanh lý lệnh hoặc kiểm tra lại phần thoát lệnh.

### Lỗi Dữ liệu

| Triệu chứng | Nguyên nhân | Cách sửa |
|------|------|---------|
| Không tải được dữ liệu | Sai API token hoặc lỗi kết nối | Kiểm tra lại `config.json` |
| Dữ liệu quá ít | Khoảng thời gian quá hẹp | Mở rộng `start_date` và `end_date` |

### Danh sách Lỗi Dữ liệu BỎ QUA (Không tự sửa code)

Nếu gặp các từ khóa sau, **tuyệt đối không sửa code**. Vấn đề nằm ở nhà cung cấp dữ liệu:
- Báo lỗi "no data available" (Không có dữ liệu)
- `rate limit` (Giới hạn tốc độ)
- `API limit` (Hết lượt gọi API)
- `daily limit` (Hết giới hạn ngày)

Lúc này, hãy báo cho người dùng biết để họ đổi nguồn dữ liệu hoặc chờ reset quota.

## Danh sách Tự kiểm tra (Hard-Gate Checklist)

1. `artifacts/metrics.csv` tồn tại và không rỗng.
2. `artifacts/equity.csv` tồn tại và không rỗng.
3. `trade_count > 0` (0 giao dịch nghĩa là có lỗi code).
4. Chuỗi vốn (equity) không chứa giá trị `NaN`.
5. `exit_code == 0`.

## Nguyên tắc Sửa lỗi

- Sửa đúng phần bị lỗi, không đập đi xây lại toàn bộ chiến lược trừ khi logic cốt lõi sai hoàn toàn.
- Sửa từng lỗi một, chạy lại backtest ngay lập tức để kiểm tra.
- Giới hạn bản thân trong tối đa 3 vòng lặp sửa lỗi (để tránh đi vào ngõ cụt).

## Quy tắc Xác nhận sau khi sửa

1. **Test cú pháp**: `bash("python -c \"import ast; ast.parse(open('code/signal_engine.py').read()); print('OK')\"")`
2. **Phải có class**: Phải có dòng `class SignalEngine:`
3. **Phải có hàm generate**: Phải có hàm `def generate(self, data_map):`
4. **Chạy lại backtest**: Cực kỳ quan trọng.

## Định dạng Ghi chú `action_items`

Sau khi chẩn đoán, phải xuất ra các hành động cụ thể:
- Ví dụ: `"Đổi ngưỡng RSI từ 30 sang 25 tại dòng 42 trong signal_engine.py"`
- Ví dụ: `"Thêm signals = signals.fillna(0) trước khi return để tránh lỗi NaN"`
- Phải có ít nhất 2 items.
