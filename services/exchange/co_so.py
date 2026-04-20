"""Cánh tay thực thi cơ sở (Base Execution Arm).

Chứa Abstract class yêu cầu các adapter của từng sàn giao dịch 
phải triển khai 2 phương thức cốt lõi.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseArm(ABC):
    """Giao diện chuẩn cho tất cả các cánh tay thực thi lệnh."""
    
    @abstractmethod
    def execute_order(self, signal_data: Dict[str, Any]) -> bool:
        """Đẩy lệnh xuống sàn giao dịch.
        
        Args:
            signal_data: Tín hiệu giao dịch (symbol, action, price, size, stop_loss...)
            
        Returns:
            True nếu lệnh thành công, False nếu thất bại.
        """
        pass
        
    @abstractmethod
    def get_account_status(self) -> Dict[str, Any]:
        """Lấy thông tin trạng thái tài khoản.
        
        Returns:
            Dict chứa balance, margin, positions...
        """
        pass
