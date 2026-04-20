"""Trading portfolio configuration manager.

Reads and writes danh_muc_giao_dich.json to manage the list of
trading pairs, risk parameters — allowing the user or frontend (a06)
to update settings easily.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("A08_TradingConfig")

class TradingConfigManager:
    """Dynamic trading configuration manager (JSON-backed)."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config_data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load data from JSON file."""
        if not self.config_path.exists():
            logger.warning(f"{self.config_path.name} not found. Please create the config file.")
            self.config_data = {}
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config_data = json.load(f)
            logger.info("✅ Trading config loaded (trading_cfg)")
        except Exception as e:
            logger.error(f"Error reading config JSON: {e}")
            self.config_data = {}

    def save(self, new_data: Dict[str, Any] = None) -> bool:
        """Update and persist data to JSON file. Used by frontend."""
        if new_data is not None:
            self.config_data = new_data

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            logger.info("✅ Trading config saved successfully!")
            return True
        except Exception as e:
            logger.error(f"Error saving config JSON: {e}")
            return False

    def get_active_symbols(self, market_type: str) -> List[str]:
        """Get list of trading symbols/pairs for a given market type.

        Args:
            market_type: 'crypto', 'vnstock', or 'global_stocks'.
        """
        markets = self.config_data.get("markets", {})
        target_market = markets.get(market_type, {})

        # Supports both 'pairs' and 'symbols' keys
        return target_market.get("pairs", target_market.get("symbols", []))

    def get_risk_params(self) -> Dict[str, float]:
        """Get risk management parameters."""
        return self.config_data.get("risk_management", {})

    def get_a03_settings(self) -> Dict[str, Any]:
        """Get A03 filter settings."""
        return self.config_data.get("a03_filter_settings", {})
