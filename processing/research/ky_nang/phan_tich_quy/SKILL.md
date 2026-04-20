---
name: phan_tich_quy
description: Phân tích và Sàng lọc Quỹ đầu tư: Xếp hạng Morningstar, Tỷ lệ Sharpe/Information Ratio, Phân tích Hộp Phong cách (Style Box), Phát hiện Lệch Phong cách (Style Drift), Đánh giá Quản lý quỹ, và Xây dựng danh mục FOF/ETF.
category: asset-class
---

# Phân tích và Sàng lọc Quỹ đầu tư (Fund & ETF Analysis)

## Tổng quan

Đánh giá một cách có hệ thống hiệu suất, phong cách đầu tư và năng lực quản lý của các Quỹ tương hỗ (Mutual Funds), Quỹ phòng hộ (Hedge Funds), và ETF. Mục tiêu cốt lõi: Tìm ra "Nguồn lợi nhuận vượt trội (Alpha) bền vững" thay vì đâm đầu vào "Quỹ có thành tích tốt nhất năm ngoái".

Kỹ năng này phù hợp cho việc phân bổ tài sản, chọn lọc ETF toàn cầu, và xây dựng mô hình Quỹ của các Quỹ (Fund of Funds - FOF).

## Các Khái niệm Cốt lõi

### Hệ thống Chỉ số Hiệu suất Quỹ

**Nhóm Chỉ số Lợi nhuận**:
| Chỉ số | Công thức | Ngưỡng Khỏe mạnh | Ý nghĩa |
|------|------|----------|------|
| Lợi suất Thường niên (CAGR) | (1 + Tổng Lợi nhuận)^(1/Số năm) - 1 | Tùy vào Benchmark | Tốc độ tăng trưởng kép. |
| Lợi nhuận Vượt trội (Alpha)| Lợi nhuận Quỹ - Lợi nhuận Benchmark | > 3%/năm | Khả năng kiếm tiền vượt trội thị trường. |
| Information Ratio (IR) | Alpha / Sai số Mô phỏng (Tracking Error) | > 0.5 | Độ ổn định của Alpha (Mỗi đơn vị lệch khỏi Benchmark mang lại bao nhiêu lợi nhuận). |
| Tỷ lệ Thắng (Win Rate) | Số tháng đánh bại Benchmark / Tổng số tháng | > 55% | Sự nhất quán trong phong độ. |

**Nhóm Chỉ số Rủi ro**:
| Chỉ số | Công thức | Ngưỡng Khỏe mạnh | Ý nghĩa |
|------|------|----------|------|
| Sụt giảm Tối đa (Max Drawdown)| Từ đỉnh cao nhất đến đáy thấp nhất | < 20% (Quỹ Cổ phiếu) | Rủi ro cháy tài khoản lớn nhất bạn phải chịu. |
| Độ biến động (Volatility) | std(Lợi nhuận ngày) * √252 | Tùy Benchmark | Mức độ giật xóc của quỹ. |
| Calmar Ratio | Lợi suất Thường niên / Sụt giảm Tối đa | > 1.0 | Khả năng hồi phục sau cú sập. |

**Nhóm Chỉ số Điều chỉnh theo Rủi ro**:
| Chỉ số | Công thức | Ngưỡng Khỏe mạnh | Ý nghĩa |
|------|------|----------|------|
| Sharpe Ratio | (Lợi nhuận Quỹ - Lãi suất phi rủi ro) / Độ biến động | > 1.0 | Cứ 1 đơn vị rủi ro chịu đựng, đổi lại bao nhiêu phần thưởng. |
| Sortino Ratio | (Lợi nhuận Quỹ - Lãi suất phi rủi ro) / Độ biến động Giảm giá | > 1.5 | Giống Sharpe nhưng chỉ phạt khi giá giảm (Downside risk). |

*Lưu ý: Lãi suất phi rủi ro (Risk-free rate) đối với USD thường dùng Trái phiếu Chính phủ Mỹ kỳ hạn 1 năm hoặc 3 tháng (khoảng 4-5% tính đến 2024).*

### Phân tích Hộp Phong cách (Style Box)

**Khung phân loại 9 ô của Morningstar**:
```text
                  Giá trị (Value)     Cân bằng (Blend)    Tăng trưởng (Growth)
Vốn hóa Lớn (Large)   Đại Cổ phiếu - Giá trị | Đại CP - Cân bằng | Đại CP - Tăng trưởng
Vốn hóa Vừa (Mid)     Trung CP - Giá trị    | Trung CP - Cân bằng| Trung CP - Tăng trưởng
Vốn hóa Nhỏ (Small)   Tiểu CP - Giá trị     | Tiểu CP - Cân bằng | Tiểu CP - Tăng trưởng

Cách phát hiện phong cách (Chạy Hồi quy Đa biến):
Lợi nhuận_Quỹ = α + β1×(Large Value) + β2×(Large Growth) + β3×(Small Value) + β4×(Small Growth) + ε

β nào lớn nhất thì quỹ đang chơi theo hệ đó.
Nếu R² (Hệ số xác định) > 0.85 → Quỹ giữ đúng phong cách cam kết.
Nếu R² < 0.70 → Quỹ đánh lướt sóng, đảo hàng liên tục (Market Timing).
```

### Phát hiện Sự Lệch Phong cách (Style Drift)

Style Drift là căn bệnh "Treo đầu dê bán thịt chó" của giới quản lý quỹ. Ví dụ: Quỹ quảng cáo là mua Cổ phiếu Cổ tức an toàn, nhưng lén lút cầm 40% tài sản đi mua tiền ảo hoặc cổ phiếu AI rủi ro cao để đua top lợi nhuận.

**Cách bắt bài**:
- Dùng cửa sổ thời gian trượt (Rolling Window) 60 ngày để chạy Hồi quy (Regress) liên tục.
- Nếu thấy β của phong cách Giá trị tụt dốc và β của phong cách Tăng trưởng vụt lên → Báo động đỏ: Quỹ đang lệch phong cách. Thay tướng giữa dòng.

## Khung Phân tích Thực chiến

### 1. Phễu Lọc Quỹ (Fund Screening - 5 Bước)

```text
Bước 1: Lọc Sống còn (Hard Filter)
  [ ] Tuổi đời ≥ 3 năm (Chưa trải qua Bear Market thì chưa biết bơi hay chìm).
  [ ] Tài sản quản lý (AUM) > 100 Triệu USD (Nhỏ quá dễ bị đóng quỹ).
  [ ] Người quản lý quỹ hiện tại đã cầm trịch > 2 năm.

Bước 2: Lọc Hiệu suất (Performance)
  [ ] Lợi nhuận năm (CAGR) 3 năm gần nhất > Mức trung bình của các quỹ cùng loại (Peer Group Median).
  [ ] Tỷ lệ Sharpe nằm trong Top 30%.
  [ ] Max Drawdown nhỏ hơn mức trung bình của nhóm.

Bước 3: Lọc Phong cách (Style)
  [ ] Phong cách thực tế khớp với Bản cáo bạch (Prospectus).
  [ ] Lệch phong cách rất thấp.

Bước 4: Đánh giá Quản lý Quỹ (Manager Rating)
  [ ] Alpha do tài năng (Stock Picking) chứ không phải do đánh bạc (Market Timing).
  [ ] Vòng quay danh mục (Turnover Rate) hợp lý. Nếu > 200%/năm là lướt sóng quá nhiều, tốn phí giao dịch.

Bước 5: Lọc Chi phí (Expense Ratio - Cực kỳ quan trọng)
  [ ] Phí quản lý (Management Fee) ≤ 1.0% (Đối với quỹ Chủ động), ≤ 0.1% (Đối với ETF Thị trường).
  [ ] Không có phí phạt rút tiền (Load fees / Redemption fees).
```

### 2. Xây dựng Danh mục FOF (Fund of Funds) / Danh mục ETF Toàn cầu

Ví dụ về một cấu trúc All-Weather (Bốn Mùa) đơn giản hóa dùng các ETF của Mỹ:

```text
Bước 1: Phân bổ Lớp Tài sản lớn (Asset Allocation)
  Cấu trúc chuẩn (Bản sao của mô hình 60/40):
  - 60% Cổ phiếu Toàn cầu
  - 40% Trái phiếu Mỹ & Tiền mặt

Bước 2: Chọn mặt gửi vàng (Chọn ETF Cụ thể)
  Cổ phiếu Mỹ (40%): VOO (S&P 500) hoặc VTI (Toàn thị trường Mỹ)
  Cổ phiếu Quốc tế (20%): VXUS (Cổ phiếu Thế giới trừ Mỹ)
  Trái phiếu Dài hạn Mỹ (20%): TLT (Trái phiếu kho bạc 20+ năm)
  Trái phiếu Trung hạn Mỹ (10%): IEF (Trái phiếu kho bạc 7-10 năm)
  Hàng hóa / Vàng (10%): GLD (Vàng vật chất) hoặc PDBC (Rổ hàng hóa hỗn hợp)

Bước 3: Tái Cân bằng (Rebalancing)
  - Khi nào làm? Định kỳ 6 tháng hoặc khi một tài sản lệch quá 5% so với mục tiêu.
  - Cắt cỏ dại, tưới hoa: Bán bớt thằng đang lãi mạnh (để chốt lời rủi ro), đắp tiền vào thằng đang giảm (mua rẻ).
```

## Dữ liệu và Công cụ (API)

Đối với chứng khoán Mỹ và ETF toàn cầu, sử dụng `yfinance` để kéo dữ liệu giá điều chỉnh (Adjusted Close) và tính toán Sharpe, Max Drawdown. Không dùng dữ liệu Tushare cho kỹ năng này trừ khi phân tích thị trường nội địa Trung Quốc.

```bash
pip install pandas numpy scipy yfinance
```
