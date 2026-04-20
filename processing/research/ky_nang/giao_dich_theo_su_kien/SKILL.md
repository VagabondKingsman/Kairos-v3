---
name: giao_dich_theo_su_kien
description: Chiến lược Giao dịch theo Sự kiện (Event-driven) dựa trên các tín hiệu được chấm điểm tâm lý từ tin tức, thông báo, và các sự kiện vĩ mô. LLM đóng vai trò là lõi NLP (Xử lý ngôn ngữ tự nhiên), và dữ liệu sự kiện được lưu theo định dạng CSV.
category: strategy
---
# Chiến lược Giao dịch theo Sự kiện (Event-Driven)

## Mục đích

Sử dụng luồng thông tin từ tin tức, báo cáo, và các chính sách vĩ mô. LLM sẽ đọc và chấm điểm sắc thái tâm lý (Sentiment) cùng với mức độ tác động để tạo ra tín hiệu giao dịch sự kiện. Dữ liệu này được lưu trong file CSV, sau đó được trộn với tín hiệu kỹ thuật thông qua công thức phân bổ trọng số để ra quyết định cuối cùng.

## Luồng công việc (Workflow)

1. **Thu thập dữ liệu**: Dùng công cụ `read_url` để lấy toàn văn tin tức/báo cáo.
2. **Phân tích bằng LLM**: LLM đọc tin và chấm điểm từ `-1.0` đến `1.0` (Cực kỳ Bearish đến Cực kỳ Bullish) theo một Prompt tiêu chuẩn.
3. **Tạo file CSV Sự kiện**: Ghi dữ liệu vào CSV theo chuẩn `date,event_type,score,source,summary`.
4. **Hợp nhất Tín hiệu**: File `signal_engine.py` sẽ đọc CSV sự kiện, tính toán độ suy giảm theo thời gian (Time decay), và trộn nó với Tín hiệu phân tích kỹ thuật.

**Nguyên lý cốt lõi: CSV Sự kiện là Tầng Dữ Liệu, còn `signal_engine.py` là Tầng Logic. Phải giữ chúng tách biệt hoàn toàn.**

## Cấu trúc CSV Sự kiện (Schema)

```csv
date,event_type,score,source,summary
2024-01-15,earnings,0.8,read_url,Doanh thu Q4 vượt kỳ vọng 30%
2024-01-20,macro,-0.5,read_url,FED tăng lãi suất thêm 25 điểm cơ bản
2024-02-01,policy,0.3,read_url,Chính phủ gia hạn trợ cấp xe điện
2024-02-10,sentiment,-0.7,read_url,Tâm lý bán tháo tràn ngập trên mạng xã hội
2024-03-05,insider,0.4,read_url,CEO tự bỏ tiền túi mua 5 triệu cổ phiếu
```

| Trường dữ liệu | Kiểu | Mô tả |
|------|------|------|
| `date` | str | Ngày mà sự kiện BẮT ĐẦU ĐƯỢC BIẾT ĐẾN (Nếu tin ra sau giờ đóng cửa -> Dùng ngày giao dịch tiếp theo). |
| `event_type` | str | Phân loại: `earnings` (Báo cáo Lợi nhuận) / `macro` (Vĩ mô) / `policy` (Chính sách) / `sentiment` (Tâm lý) / `insider` (Nội gián) / `technical_break` (Phá vỡ kỹ thuật). |
| `score` | float | Điểm chuẩn hóa từ LLM: `-1.0 ~ 1.0`. |
| `source` | str | Nguồn dữ liệu (VD: `read_url`). |
| `summary` | str | Tóm tắt sự kiện (Ghi đúng 1 câu, TUYỆT ĐỐI KHÔNG DÙNG DẤU PHẨY). |

## Phân loại Sự kiện và Mức độ Tác động

| Loại | Ý nghĩa | Tác động Điển hình | Thời gian ảnh hưởng |
|------|------|---------|---------|
| `earnings` | Ra BCTC | Sốc ngắn hạn | 1-5 ngày |
| `macro` | Dữ liệu Vĩ mô / Chính sách NHTW | Tác động trung hạn | 5-20 ngày |
| `policy` | Quy định nhà nước / Luật mới | Tác động dài hạn | 20-60 ngày |
| `sentiment` | Đám đông hoảng loạn/hưng phấn | Sốc cực ngắn | 1-3 ngày |
| `insider` | Giao dịch nội gián | Tín hiệu trung hạn | 5-10 ngày |
| `technical_break`| Vượt đỉnh/Thủng đáy quan trọng | Chất xúc tác kỹ thuật | 1-5 ngày |

## Hợp nhất Tín hiệu (Signal Aggregation)

### Sự Suy giảm Thời gian của Sự kiện (Time Decay)

Một tin tức nóng hổi sẽ mất dần giá trị khi thời gian trôi qua. Ta dùng hàm suy giảm hàm mũ (Exponential Decay):

```python
import numpy as np
import pandas as pd

def compute_event_signal(event_df: pd.DataFrame, dates: pd.DatetimeIndex,
                         decay_lambda: float = 0.1,
                         min_score_threshold: float = 0.2,
                         event_lookback: int = 30) -> pd.Series:
    """
    Tính toán tín hiệu sự kiện kết hợp hiệu ứng phai mờ theo thời gian.
    decay_lambda = 0.1 nghĩa là sức ảnh hưởng của tin tức sẽ rớt còn ~37% sau 10 ngày.
    """
    event_df = event_df[event_df["score"].abs() >= min_score_threshold].copy()
    event_df["date"] = pd.to_datetime(event_df["date"])

    signal = pd.Series(0.0, index=dates)

    for trade_date in dates:
        # Ngăn chặn "Nhìn trước tương lai" (Look-ahead bias): Chỉ lấy các sự kiện xảy ra trước hoặc bằng ngày trade_date
        mask = (event_df["date"] <= trade_date) & \
               (event_df["date"] >= trade_date - pd.Timedelta(days=event_lookback))
        relevant = event_df[mask]

        if relevant.empty:
            continue

        days_since = (trade_date - relevant["date"]).dt.days.values
        scores = relevant["score"].values
        # Giảm xóc hàm mũ: Điểm số * exp(-lambda * số ngày đã qua)
        decayed = scores * np.exp(-decay_lambda * days_since)
        
        # Cộng dồn tất cả các sự kiện trong ngày và giới hạn tín hiệu trong vùng [-1.0, 1.0]
        signal[trade_date] = np.clip(decayed.sum(), -1.0, 1.0)

    return signal
```

### Trộn Tín hiệu Kỹ thuật và Sự kiện

```python
def combine_signals(tech_signal: pd.Series, event_signal: pd.Series,
                    alpha: float = 0.6) -> pd.Series:
    """
    alpha = 0.6 nghĩa là Tín hiệu kỹ thuật chiếm 60% trọng số, Sự kiện chiếm 40%.
    """
    combined = alpha * tech_signal + (1 - alpha) * event_signal
    return combined.clip(-1.0, 1.0)
```

## Template Chấm điểm cho LLM (LLM Scoring Prompt)

Để chấm điểm khách quan và nhất quán, luôn dùng Prompt sau để hỏi LLM khi đọc tin:

```text
Bạn là một chuyên gia phân tích sự kiện tài chính. Hãy đọc tin tức/thông báo sau và chấm điểm mức độ tác động của nó lên giá cổ phiếu/tài sản.

Thang điểm:
- 1.0: Cực kỳ Bullish (Ví dụ: Lợi nhuận vượt xa mọi kỳ vọng, Chính sách giải cứu khổng lồ)
- 0.5: Bullish mức độ trung bình (Lợi nhuận cao hơn dự báo một chút, Tin tức ngành tích cực)
- 0.2: Bullish nhẹ
- 0.0: Trung lập (Không có tác động rõ ràng)
- -0.2: Bearish nhẹ
- -0.5: Bearish mức độ trung bình (Lợi nhuận trượt kỳ vọng, Siết chặt pháp lý)
- -1.0: Cực kỳ Bearish (Gian lận kế toán, Lãnh đạo bị bắt, Thiên nga đen)

Chấm điểm nghiêm ngặt theo thang đo trên. CHỈ IN RA MỘT CON SỐ DUY NHẤT. Tuyệt đối không giải thích gì thêm.

Nội dung tin tức:
{news_content}

Điểm số:
```

## Các Cái Bẫy Cần Tránh (Pitfalls)

1. **Nhìn trước tương lai (Look-ahead bias)**: Cột `date` phải là "Ngày mà công chúng bắt đầu biết tin". Nếu công ty ra báo cáo lúc 8 giờ tối (đã đóng cửa sàn), bạn phải gán `date` là ngày giao dịch sáng hôm sau.
2. **Chấm điểm trùng lặp**: Một sự kiện lớn sẽ được hàng chục tờ báo đưa tin. Đừng ghi vào CSV 10 dòng giống hệt nhau, nó sẽ làm điểm số bị nhân lên 10 lần. Phải gộp lại hoặc lấy giá trị trung bình.
3. **Dấu phẩy trong tóm tắt**: Cột `summary` tuyệt đối không được có dấu phẩy `,` vì nó sẽ làm hỏng cấu trúc file CSV.
4. **Sự kiện trống rỗng**: 90% các ngày giao dịch trên thị trường chả có sự kiện gì quan trọng cả. Khi đó tín hiệu sự kiện = 0, và thuật toán sẽ chỉ dựa vào Tín hiệu kỹ thuật. Chuyện này rất bình thường, đừng cố bịa ra sự kiện để lấp đầy ngày.
