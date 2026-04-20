---
name: chuyen_doi_pine_script
description: Dịch ngược các chiến lược Backtest từ Python sang TradingView Pine Script v6, hoặc lập trình Pine Script trực tiếp từ ngôn ngữ tự nhiên. 
category: tool
---

## Tổng quan

Kỹ năng này cung cấp 2 quy trình làm việc (Workflows):
1. **Xuất file (Export)**: Chuyển đổi mã nguồn `signal_engine.py` (từ một chiến lược Python đã backtest thành công) sang định dạng TradingView Pine Script v6 để người dùng cài lên đồ thị.
2. **Sáng tạo (Generate)**: Viết trực tiếp code Pine Script v6 dựa trên yêu cầu miêu tả bằng văn bản.

File đầu ra: `artifacts/strategy.pine`.

## Bảng Xếp hạng (Mapping) Python → Pine Script v6

### Chỉ báo Kỹ thuật (Technical Indicators)

| Python (pandas/numpy) | Pine Script v6 |
|------------------------|----------------|
| `df['close'].rolling(n).mean()` | `ta.sma(close, n)` |
| `df['close'].ewm(span=n).mean()` | `ta.ema(close, n)` |
| `ta.RSI(df['close'], n)` | `ta.rsi(close, n)` |
| `ta.MACD(df['close'])` | `[macdLine, signalLine, hist] = ta.macd(close, 12, 26, 9)` |
| `df['close'].rolling(n).std()` | `ta.stdev(close, n)` |
| `df['high'].rolling(n).max()` | `ta.highest(high, n)` |
| `df['close'].pct_change()` | `(close - close[1]) / close[1]` |
| Dải Bollinger (Bollinger Bands) | `[mid, upper, lower] = ta.bb(close, length, mult)` |
| ATR | `ta.atr(length)` |
| VWAP | `ta.vwap` |

### Tham chiếu Dữ liệu (Data References)

| Python | Pine Script v6 |
|--------|----------------|
| `df['close'].shift(1)` (Nến trước đó) | `close[1]` |
| `df['close'].shift(n)` | `close[n]` |
| `df.index` | `time` |

### Logic Tạo Tín hiệu (Signal Logic)

| Python | Pine Script v6 |
|---------------|----------------|
| `Cắt lên: (fast > slow) & (fast.shift(1) <= slow.shift(1))` | `ta.crossover(fast, slow)` |
| `Cắt xuống: (fast < slow) & (fast.shift(1) >= slow.shift(1))` | `ta.crossunder(fast, slow)` |
| `signal.fillna(0)` | `nz(signal, 0)` |

### Quản lý Vị thế (Position Sizing)

| Python Pattern | Pine Script v6 |
|---------------|----------------|
| Mua All-in 100% tài khoản | `default_qty_type=strategy.percent_of_equity, default_qty_value=100` |
| Chia đều N tài sản (1/N) | `default_qty_value = 100/N` |
| Dừng lỗ (Stop-loss) | `strategy.exit("Exit", stop=entryPrice * (1 - stopPct))` |
| Chốt lời (Take-profit) | `strategy.exit("Exit", limit=entryPrice * (1 + tpPct))` |

## Template Tiêu chuẩn của Pine Script v6

```pinescript
// Chiến lược này được tự động tạo bởi KAIROS Quant System
// Copy và Dán vào TradingView Pine Editor → Thêm vào biểu đồ
//@version=6
strategy("Tên Chiến Lược", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=100, commission_type=strategy.commission.percent, commission_value=0.1, initial_capital=100000)

// ============================================================================
// ĐẦU VÀO (INPUTS)
// ============================================================================
len = input.int(20, title="Chiều dài (Length)")
mult = input.float(2.0, title="Hệ số (Multiplier)")

// ============================================================================
// TÍNH TOÁN (CALCULATIONS)
// ============================================================================
[mid, upper, lower] = ta.bb(close, len, mult)

// ============================================================================
// ĐIỀU KIỆN (CONDITIONS)
// ============================================================================
longCondition = ta.crossover(close, lower)
shortCondition = ta.crossunder(close, upper)
exitLongCondition = close > mid
exitShortCondition = close < mid

// ============================================================================
// VÀO/RA LỆNH (STRATEGY EXECUTION)
// ============================================================================
if longCondition
    strategy.entry("Long", strategy.long)
if shortCondition
    strategy.entry("Short", strategy.short)
if exitLongCondition
    strategy.close("Long")
if exitShortCondition
    strategy.close("Short")

// ============================================================================
// ĐỒ HỌA (PLOTS)
// ============================================================================
plot(mid, color=color.blue, title="Basis")
p1 = plot(upper, color=color.red, title="Upper")
p2 = plot(lower, color=color.green, title="Lower")
fill(p1, p2, color=color.new(color.blue, 90))

// ============================================================================
// CẢNH BÁO (ALERTS)
// ============================================================================
alertcondition(longCondition, title="Tín hiệu Mua", message="Đã khớp tín hiệu MUA")
```

## Các Luật Cấm Kỵ (Quy định bắt buộc của Pine v6)

1. **Dòng đầu tiên bắt buộc phải là**: `//@version=6`
2. **Toán tử 3 ngôi (Ternary operators) KHÔNG ĐƯỢC ngắt dòng**:
   ```pinescript
   // LỖI (Sẽ báo lỗi "end of line without line continuation")
   text = condition ? "Mua" :
          "Bán"

   // CHUẨN
   text = condition ? "Mua" : "Bán"
   ```
3. **Thụt lề (Indentation)**: Dòng tiếp nối phải thụt lề SÂU HƠN dòng bắt đầu.
4. **Không bao giờ dùng hàm `plot()` bên trong if/for/function**:
   ```pinescript
   // LỖI CỰC MẠNH (Tradingview sẽ sập)
   if condition
       plot(value)

   // CHUẨN MỰC
   plot(condition ? value : na)
   ```
5. Bắt buộc chuyển đổi Mã giao dịch (Ticker) về định dạng của TradingView:
   - `BTC-USDT` (OKX) -> `OKX:BTCUSDT` hoặc `BINANCE:BTCUSDT`
   - `AAPL.US` -> `NASDAQ:AAPL`

## Hướng dẫn Sử dụng (Luôn in ra cho người dùng đọc)

```text
Hướng dẫn cách ném code này vào TradingView:
1. Mở biểu đồ TradingView -> Click tab "Pine Editor" ở dưới cùng màn hình.
2. Bấm "Open" (Mở) -> Chọn "New blank indicator" (Chỉ báo trống mới).
3. Bôi đen và Xóa sạch toàn bộ code cũ mặc định.
4. Paste (Dán) đoạn code Pine Script vừa tạo ở trên vào.
5. Bấm nút "Add to Chart" (Thêm vào biểu đồ).
6. Chuyển sang tab "Strategy Tester" (Trình thử nghiệm Chiến lược) để xem biểu đồ Lời/Lỗ (Equity Curve).
```
