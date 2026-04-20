---
name: kien_thuc_phap_ly
description: Thư viện Kiến thức Pháp lý & Quy tắc Sàn (Regulatory knowledge): PDT Mỹ (Pattern Day Trader), LULD, Margin Crypto, thuế suất, và giới hạn Short-selling quốc tế.
category: tool
---

# Thư viện Quy tắc Giao dịch & Pháp lý (Regulatory Knowledge)

## Tổng quan

Đây là kiến thức bắt buộc phải có cho Quant. Việc code một hệ thống có lợi nhuận trong Backtest là vô nghĩa nếu hệ thống đó giả định sai luật của sàn giao dịch (Ví dụ: Backtest đánh T+0 trên một thị trường chỉ cho phép T+2, hoặc không tính phí vay Margin/Borrowing fee khi bán khống).

Sử dụng kỹ năng này để áp đặt các "Rào cản" (Constraints) sát thực tế nhất cho hệ thống `a10` (Máy Trạng Thái).

## Các Quy tắc Thị trường Cốt lõi

### 1. Thị trường Chứng khoán Mỹ (US Equities)

**Quy tắc PDT (Pattern Day Trader - Chống Giao dịch Trong ngày)**:
- **Điều kiện vi phạm**: Thực hiện từ 4 giao dịch "Trong Ngày" (Mở và Đóng vị thế trong cùng 1 phiên) trong vòng 5 ngày làm việc.
- **Hậu quả**: Nếu tài khoản Margin của bạn có số dư dưới $25,000, bạn sẽ bị gắn cờ PDT và khóa tài khoản (chỉ cho phép đóng lệnh) trong 90 ngày.
- **Cách né trong KAIROS**: 
  - Code máy trạng thái (State Machine) chặn không cho xuất tín hiệu Đóng lệnh trong cùng ngày mở lệnh (Overnight hold required) nếu vốn < 25k.
  - Hoặc chuyển sang Cash Account (Nhưng sẽ dính luật T+2 Settlement, tiền mất 2 ngày mới về, vốn sẽ bị kẹt).

**Quy tắc LULD (Limit Up-Limit Down - Cầu dao Tự động)**:
- Chứng khoán Mỹ không có biên độ trần/sàn cứng (như ±10% của Châu Á).
- Nhưng có LULD: Nếu một mã vốn hóa lớn biên động ±5% (hoặc ±10% với mã nhỏ) chỉ trong 5 phút -> Cổ phiếu đó sẽ bị "Tạm ngừng giao dịch" (Halted) trong 5 phút.
- **Tác động Backtest**: Lệnh Stop-loss của bạn có thể bị trượt giá (Slippage) cực kỳ nặng sau khi cổ phiếu được mở giao dịch trở lại (Gap down).

**Quy tắc Bán khống (Short Selling - Reg SHO)**:
- **Locate Requirement**: Trước khi Bán khống, Broker của bạn phải "Tìm được" (Locate) cổ phiếu để mượn. Không được bán khống khống (Naked Shorting).
- **Uptick Rule (Quy tắc Giá nhích lên)**: Nếu cổ phiếu rớt >10% trong ngày, bạn chỉ được phép đặt lệnh Short ở giá cao hơn giá khớp gần nhất.

### 2. Thị trường Crypto (Tiền điện tử)

**Quy tắc Giao dịch**:
- 24/7/365: Không có giờ mở cửa, không có nghỉ lễ, không có cuối tuần.
- **Biên độ**: Vô cực. Không có LULD, không có trần sàn. Một coin có thể bốc hơi 99% trong 1 tiếng.

**Cơ chế Ký quỹ & Thanh lý (Margin & Liquidation)**:
- Đòn bẩy (Leverage) lên tới 100x hoặc 125x.
- **Cross Margin vs Isolated Margin**: KAIROS v3.0 mặc định dùng Isolated Margin để giới hạn mức lỗ tối đa cho từng vị thế.
- **Giá Thanh lý (Liquidation Price)**: Được tính dựa trên **Giá Đánh dấu (Mark Price)**, KHÔNG PHẢI Giá Khớp lệnh cuối (Last Price). Điều này để chống lại việc thao túng giá trên sổ lệnh.
- **Phí Thanh lý**: Sàn giao dịch sẽ ăn một khoản phí rất lớn nếu bạn bị thanh lý. Đừng bao giờ để vị thế chạm tới giá Liquidation, hãy cắt lỗ trước đó bằng lệnh Stop Market.

### 3. Tác động của Chi phí và Thuế (Taxes & Fees)

Việc không đưa chi phí ẩn vào Backtest là con đường nhanh nhất dẫn đến cháy tài khoản thực.

**Chi phí giao dịch Crypto Thực tế**:
- **Taker Fee (Khớp ngay)**: ~0.04% đến 0.05% một chiều.
- **Maker Fee (Treo lệnh)**: ~0.01% đến 0.02% một chiều.
- **Trượt giá (Slippage)**: Đối với Altcoin, trượt giá cho một lệnh $10,000 có thể lên tới 0.2% - 0.5%.
- **Phí Funding (Funding Rate)**: Chi phí đắt đỏ nhất nếu ôm vị thế Hợp đồng Vĩnh cửu (Perps) ngược hướng với đám đông.

**Tác động Thuế (Hoa Kỳ - Dành cho User US)**:
- Lợi nhuận Ngắn hạn (Short-term Capital Gains - Hold < 1 năm): Bị đánh thuế thu nhập cá nhân (có thể lên tới 37%).
- Lợi nhuận Dài hạn (Hold > 1 năm): 0%, 15%, hoặc 20%.
- **Wash-Sale Rule**: Bán cắt lỗ rồi mua lại đúng mã đó trong vòng 30 ngày -> Khoản lỗ đó KHÔNG ĐƯỢC khấu trừ thuế.
- *Lưu ý KAIROS*: Thuế là yếu tố cá nhân, KAIROS không tính thuế vào Net Profit của Backtest, nhưng hệ thống sẽ phạt (Penalize) các chiến lược lướt sóng quá nhiều bằng Commission rate cao.

## Khung Phân tích Tuân thủ (Compliance Framework) cho Chiến lược

Trước khi đưa bất kỳ chiến lược nào vào chạy Thực chiến (Live Trading), chạy Check-list sau:

```text
1. Có tín hiệu Mua/Bán cùng ngày không? -> Kiểm tra luật PDT (Mỹ).
2. Tín hiệu Bán Khống (Short) lấy dữ liệu từ đâu? -> Có trừ phí mượn (Borrow fee/Funding) không?
3. Tính toán Trượt giá lúc thị trường hoảng loạn chưa? -> Mở rộng Spread lúc Volatility tăng vọt.
4. Stop-loss là Lệnh Limit hay Market? -> Limit thì nguy cơ bị bỏ qua (Bypass), Market thì nguy cơ trượt giá (Slippage) nát xương.
```
