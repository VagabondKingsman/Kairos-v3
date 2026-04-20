---
name: nghien_cuu_nhan_to
description: Khung Nghiên cứu Nhân tố (Factor research) bao gồm kiểm định IC/IR, Backtest phân vị (Quantile backtesting), và Tổ hợp Nhân tố. Phù hợp để đánh giá sức mạnh chọn lọc tài sản chéo của các yếu tố định lượng.
category: analysis
---

# Khung Nghiên cứu Nhân tố Định lượng (Factor Research Framework)

## Mục đích

Đánh giá một cách có hệ thống sức mạnh dự báo của một hoặc nhiều Nhân tố (Factors). Sử dụng kiểm định thống kê IC/IR và Backtest phân vị để xác định xem nhân tố đó có khả năng "chọn hàng" (Stock-selection) hay không, từ đó làm cơ sở để lọc và kết hợp nhân tố.

**Các kịch bản ứng dụng:**
- Kiểm định tính hợp lệ của một nhân tố đơn lẻ (Động lượng, Giá trị, Chất lượng, Biến động, v.v.).
- Xác định trọng số khi trộn nhiều nhân tố lại với nhau.
- Phân tích độ phân rã của nhân tố (IC suy giảm thế nào qua các thời gian nắm giữ khác nhau).

## Luồng công việc (Workflow)

1. **Tính toán giá trị nhân tố**: Tính điểm nhân tố cho mọi tài sản trên một mặt cắt ngang (Cross-section), xuất ra file CSV Nhân tố (`index=date`, `columns=codes`).
2. **Tính toán Lợi nhuận**: Tính lợi nhuận N-ngày tiến về tương lai (Forward return) của từng tài sản, xuất ra file CSV Lợi nhuận (Cùng cấu trúc).
3. **Chạy Phân tích**: Sử dụng công cụ `factor_analysis`, truyền vào 2 file CSV nói trên.
4. **Đọc kết quả**: Phán xét nhân tố là Rác hay Kim cương dựa trên chuẩn mực IC/IR và đồ thị phân vị.
5. **Tổ hợp (Combination)**: Giữ lại các nhân tố tốt, trộn chúng lại bằng phương pháp Chia đều trọng số hoặc Trọng số theo IC.

**Điểm CHẾT NGƯỜI**: Các hàng (Ngày) và cột (Mã tài sản) của file CSV Nhân tố và CSV Lợi nhuận phải KHỚP NHAU Y ĐÚC. Lợi nhuận BẮT BUỘC phải là lợi nhuận của khoảng thời gian SAU NGÀY tính nhân tố (Để tránh lỗi Nhìn trước tương lai - Look-ahead bias).

## Công cụ `factor_analysis`

| Tham số | Ý nghĩa |
|------|------|
| `factor_csv` | Đường dẫn đến file chứa điểm số nhân tố. |
| `return_csv` | Đường dẫn đến file chứa Lợi nhuận tương lai N-ngày. |
| `output_dir` | Thư mục lưu kết quả phân tích. |
| `n_groups` | Số nhóm phân vị để cắt lát (Mặc định: 5). |

## Tiêu chuẩn Phán xét IC/IR (Hệ số Tương quan Thông tin)

IC (Information Coefficient) đo lường tương quan giữa Điểm nhân tố và Lợi nhuận thực tế. 

| Chỉ số | Ngưỡng | Đánh giá |
|------|------|------|
| Trung bình IC | > 0.03 | Nhân tố có sức mạnh dự báo cơ bản. |
| Trung bình IC | > 0.05 | Nhân tố có sức mạnh dự báo MẠNH. |
| Trung bình IC | > 0.10 | Cao bất thường; Có mùi của lỗi Nhìn trước tương lai (Leakage). |
| IR (IC / Độ lệch chuẩn IC) | > 0.5 | Nhân tố hiệu quả cực kỳ Ổn định. |
| IR | > 1.0 | Chén thánh, vô cùng hiếm gặp ở thị trường thực. |
| Tỷ lệ ngày có IC > 0 | > 55% | Hướng của nhân tố là đồng nhất. |
| Tỷ lệ ngày có IC > 0 | ~ 50% | Nhân tố hoạt động ngẫu nhiên như tung đồng xu, vứt đi. |

*Lưu ý: IC âm cũng là nhân tố xịn (Nhân tố đảo chiều). Hãy nhìn vào giá trị tuyệt đối của IC. Khi áp dụng thực tế, chỉ cần đảo ngược dấu (Nhân -1) là xong.*

## Đọc hiểu Backtest Phân vị (Quantile Backtest)

Backtest phân vị sẽ sắp xếp các tài sản từ điểm thấp nhất đến cao nhất, sau đó cắt chúng thành N nhóm (Mặc định 5 nhóm) và đầu tư đều đặn vào từng nhóm.

**Tiêu chuẩn Vàng:**
- **Tính Đơn điệu (Monotonicity)**: Đường cong Lợi nhuận từ `Nhóm 1` đến `Nhóm 5` phải xếp lớp như bậc thang (Hoặc tăng dần, hoặc giảm dần). Bậc thang càng đều -> Khả năng phân loại của nhân tố càng tuyệt vời.
- **Biên độ Long-Short (Spread)**: Khoảng cách lợi nhuận giữa Nhóm Tốt nhất và Nhóm Tệ nhất. Biên độ càng rộng -> Nhân tố càng sắc bén.

**Cờ Đỏ (Red Flags):**
- Đường cong 5 nhóm dính chặt vào nhau như mì ống -> Nhân tố vô dụng.
- Đồ thị hình chữ V hoặc chữ A -> Nhân tố có tính phi tuyến tính (Nằm ở giữa thì xịt, nằm ở 2 đuôi thì ăn), cần kỹ thuật xử lý đặc biệt.

## Phương pháp Tổ hợp Nhân tố (Factor Combination)

Khi đã rây lọc được vài nhân tố xuất sắc, hãy "nấu" chúng lại thành 1 siêu nhân tố.

### 1. Trọng số Bằng nhau (Equal-Weight)
Cách đơn giản nhất và thường là ít bị Overfit nhất. Chỉ cần chuẩn hóa Z-Score cho từng nhân tố rồi cộng chúng lại.
```text
Siêu Nhân tố = Z(Động lượng) + Z(Giá trị) + Z(Chất lượng)
```

### 2. Trọng số theo IC (IC-Weighted)
Nhân tố nào có lịch sử IC cao hơn thì được "cấp vốn" (Trọng số) nhiều hơn.
```text
Trọng số (i) = |IC trung bình của i| / Tổng(|IC trung bình các nhân tố|)
```

### 3. Trực giao hóa (Orthogonalized Combination)
Nếu bạn có 2 nhân tố (VD: PE và PB) có độ tương quan quá cao với nhau, việc cộng chúng lại là dư thừa (Đa cộng tuyến). Dùng phương pháp Schmidt để triệt tiêu phần trùng lặp, lấy phần cốt lõi thuần túy, rồi mới tổ hợp.

## Các Cạm bẫy Kinh điển

### 1. Lỗi Nhìn trước tương lai (Look-Ahead Bias)
- **Lỗi ngớ ngẩn nhất**: Lấy giá Đóng cửa ngày T để tính Nhân tố, rồi đối chiếu với Lợi nhuận của ngày T. -> IC sẽ cao chót vót, nhưng ra trade thật sẽ bán nhà.
- **Cách đúng**: Tính nhân tố lúc Đóng cửa ngày T. Lợi nhuận phải là: Biến động từ Đóng cửa T đến Đóng cửa T+1.

### 2. Phân phối Bị lệch (Skewed Distributions)
Các nhân tố như Vốn hóa thị trường (Market Cap) bị lệch phải cực nặng (Cá mập quá lớn). Nếu tính IC trực tiếp, đám cá mập sẽ bóp méo kết quả.
-> **Giải pháp**: Xếp hạng (Rank) hoặc Chuẩn hóa Z-Score toàn bộ tài sản trước khi tính IC.

### 3. Tập mẫu quá nhỏ
Một Cross-section cần tối thiểu 30-50 tài sản để tính IC cho chuẩn. Nếu bạn chỉ có 5 mã Crypto, IC sẽ nhảy múa loạn xạ và IR trở nên vô nghĩa.

### 4. Thiên kiến Sống sót (Survivorship Bias)
Nếu bạn chỉ lấy dữ liệu của các mã còn sống khỏe đến tận hôm nay để Backtest 10 năm trước, kết quả sẽ luôn luôn là siêu lợi nhuận. Phải dùng bộ dữ liệu bao gồm cả các mã đã bị Hủy niêm yết/Chết (Delisted) trong quá khứ.
