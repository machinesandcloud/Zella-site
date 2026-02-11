import logging
from typing import Dict, List


class PositionManager:
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.positions: Dict[str, Dict] = {}

    def update_position(self, symbol: str, data: Dict) -> None:
        self.positions[symbol] = data

    def get_positions(self) -> List[Dict]:
        return list(self.positions.values())

    def close_position(self, symbol: str) -> None:
        if symbol in self.positions:
            self.logger.info("Closing position for %s", symbol)
            self.positions.pop(symbol)
