import logging
from typing import Any, Dict, List

from core.signals import Signal


class BaseStrategy:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._logs: List[str] = []
        self._performance: Dict[str, Any] = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
        }

    def on_market_data(self, symbol: str, data: Dict[str, Any]) -> List[Signal]:
        return []

    def get_performance(self) -> Dict[str, Any]:
        return self._performance

    def get_logs(self) -> List[str]:
        return self._logs

    def log(self, message: str) -> None:
        self._logs.append(message)
        self.logger.info(message)
