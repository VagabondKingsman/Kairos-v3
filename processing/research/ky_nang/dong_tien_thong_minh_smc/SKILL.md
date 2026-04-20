---
name: dong_tien_thong_minh_smc
description: Dòng tiền thông minh (Smart Money Concepts - ICT) — Phát hiện khối lệnh (Order Block), khoảng trống giá (FVG), phá vỡ cấu trúc (BOS/CHOCH), vùng Premium/Discount kết hợp đa khung thời gian qua nen_htf. Đã tích hợp sẵn trong a04/ky_nang_chien_luoc/.
category: strategy
---

# Khái niệm Dòng Tiền Thông Minh (Smart Money Concepts - SMC / ICT)

## Mục đích

Cung cấp hệ thống giao dịch bám theo dấu chân của dòng tiền lớn (Các tổ chức tài chính, Cá voi). Dựa trên nguyên lý: Dòng tiền lớn không thể giấu được hành vi của mình trên biểu đồ, họ để lại các "Vết chân" dưới dạng Khối lệnh (Order Block) và Khoảng trống Thanh khoản (Fair Value Gap).

| Khái niệm | Viết tắt | Giải nghĩa Cơ bản |
|---------|--------|---------|
| Break of Structure | BOS | Phá vỡ cấu trúc — Đánh dấu xu hướng tiếp diễn (Đáy sau cao hơn đáy trước). |
| Change of Character | CHOCH | Đổi gác (Thay đổi tính chất) — Dấu hiệu sớm nhất của sự đảo chiều xu hướng. |
| Fair Value Gap | FVG | Khoảng trống Giá trị Hợp lý — Thị trường chạy quá nhanh để lại thanh khoản rỗng, giá thường quay lại lấp đầy vùng này. |
| Order Block | OB | Khối lệnh — Vùng giá (cây nến) cuối cùng trước khi một đợt bùng nổ mạnh xảy ra (Nơi cá mập gom/xả hàng). |
| Premium/Discount | P/D | Vùng Đắt/Rẻ — Kéo Fibonacci từ Đáy lên Đỉnh. Nửa trên là Đắt (Chỉ Bán), nửa dưới là Rẻ (Chỉ Mua). |

## Tư duy Đa Khung Thời Gian (Multi-Timeframe)

Bí quyết thành bại của SMC là **tuyệt đối không giao dịch nếu không nhìn khung lớn**.

```text
Khung Ngày (D1)  → Nhìn Xu hướng bức tranh lớn (Tìm vùng Premium/Discount).
Khung H4         → Tìm các Khối lệnh (Order Block) cứng và Điểm phá vỡ BOS/CHOCH.
Khung H1         → Tìm FVG, đợi giá đâm vào FVG rồi bật lên để xác nhận vào lệnh.
```

## Logic Giao dịch Điển hình

```text
Vào lệnh MUA (Long = +1):
  Bối cảnh HTF (D1) = XU HƯỚNG TĂNG.
  + Giá đã điều chỉnh về nửa dưới của lưới Fibonacci (Vùng Discount < 50%).
  + Tại vùng này có một Khối lệnh Tăng (Bullish OB) hợp lệ (Chưa từng bị giá đâm thủng).
  + Trên khung nhỏ (LTF) xuất hiện một cú CHOCH (Đảo chiều cấu trúc từ Giảm sang Tăng).
  -> Tiến hành Mua ngay khi giá hồi về FVG của cú CHOCH đó.

Vào lệnh BÁN (Short = -1):
  Bối cảnh HTF (D1) = XU HƯỚNG GIẢM.
  + Giá đã nảy lên nửa trên của lưới Fibonacci (Vùng Premium > 50%).
  + Tại vùng này có Khối lệnh Giảm (Bearish OB) chặn lại.
  + Khung nhỏ (LTF) xuất hiện cú CHOCH rớt xuống.
  -> Bán Khống (Short).
```

## Triển khai bằng Công cụ KAIROS (`SmcSignalEngine`)

Toàn bộ thuật toán nhận diện SMC cực kỳ phức tạp đã được KAIROS code sẵn trong `a04_kho_chien_luoc_va_kiem_thu/ky_nang_chien_luoc/dong_tien_thong_minh_smc.py`.
Bạn chỉ cần nạp nó vào `signal_engine.py` và chạy.

### Mẫu Gọi `signal_engine.py`

```python
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from a04_kho_chien_luoc_va_kiem_thu.ky_nang_chien_luoc.dong_tien_thong_minh_smc import SmcSignalEngine
from typing import Dict
import pandas as pd

class SignalEngine:
    """Chiến lược SMC tự động hoàn toàn."""

    def __init__(self):
        self._engine = SmcSignalEngine(
            ob_window=10,      # Quét 10 nến gần nhất để tìm Order Block
            swing_window=5,    # Dùng 5 nến hai bên để xác định các đỉnh đáy quan trọng
            htf="4h",          # Phóng to lên khung 4H để lấy bối cảnh xu hướng
        )

    def generate(self, data_map: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
        # Tự động trả về tín hiệu +1 / -1 / 0
        return self._engine.generate(data_map)
```

## File `config.json` Bắt buộc

```json
{
  "source": "okx",
  "codes": ["BTC-USDT"],
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "interval": "1H", 
  "initial_cash": 1000000,
  "commission": 0.001,
  "engine": "crypto"
}
```

**Quan trọng**: `interval` phải là khung nhỏ (Ví dụ `"1H"`). Hệ thống `nen_htf` bên dưới sẽ tự động lấy các nến 1H này gộp lại thành nến 4H và D1 để phân tích đa khung, hoàn toàn không bị dính lỗi Lookahead Bias (Nhìn trước tương lai).

## Các Lưu ý Đau thương (Pitfalls)

1. **Hiệu lực của Khối lệnh (Mitigation)**: OB chỉ có tác dụng nếu nó CHƯA TỪNG bị giá chạm vào (Unmitigated). Nếu giá đã đâm xuyên qua cái OB đó rồi, nó sẽ biến thành cục rác vô dụng. Máy đã tự code luật này.
2. **Quét Thanh khoản (Liquidity Sweep)**: Rất nhiều khi giá đâm thủng đáy giả bộ phá vỡ (Breakout) nhưng rút râu cái rụp. SMC gọi đây là Quét Thanh khoản để lấy đà đi lên, không phải là CHOCH.
3. **Tuyệt đối tuân thủ Premium/Discount**: Không bao giờ Bán Khống ở vùng rẻ (Discount), và Cấm tuyệt đối Mua (Long) trên đỉnh vùng Đắt (Premium). Mua vùng Premium là thanh khoản cho Cá voi xả hàng.
