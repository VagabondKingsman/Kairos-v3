"""Gói tối ưu hóa danh mục đầu tư. 

Cung cấp bốn chương trình trọng số: 
- equal_volatility: trọng số biến động nghịch đảo 
- risk_parity: đóng góp rủi ro bằng nhau (kiểu Spinu) 
- mean_variance: Sharpe tối đa thông qua scipy 
- max_diversification: tối đa hóa tỷ lệ đa dạng hóa 

Chọn thông qua ``bo_toi_uu`` trong ``config.json``; mặc định là tắt (1/N). 
Thêm một trình tối ưu hóa mới bằng cách thả một file module vào đây, 
yêu cầu module đó phải có hàm ``optimize()``. 
"""