import logging
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class RiskConfig:
    max_position_size_percent: float
    max_daily_loss: float
    max_positions: int
    risk_per_trade_percent: float
    max_trades_per_day: int = 12
    max_consecutive_losses: int = 3


class RiskManager:
    def __init__(self, config: RiskConfig) -> None:
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.daily_loss = 0.0
        self.open_positions: List[Dict] = []
        self.emergency_stop_triggered = False
        self.trades_today = 0
        self.consecutive_losses = 0

    # Pre-Trade Validation
    def check_position_size_limit(self, symbol: str, quantity: int, price: float, account_value: float) -> bool:
        position_value = quantity * price
        max_allowed = (self.config.max_position_size_percent / 100.0) * account_value
        if position_value > max_allowed:
            self.logger.warning("Position size limit exceeded for %s", symbol)
            return False
        return True

    def check_daily_loss_limit(self) -> bool:
        if self.daily_loss <= -abs(self.config.max_daily_loss):
            self.logger.warning("Daily loss limit hit")
            return False
        return True

    def check_max_positions(self) -> bool:
        if len(self.open_positions) >= self.config.max_positions:
            self.logger.warning("Max positions reached")
            return False
        return True

    def check_buying_power(self, required_capital: float, buying_power: float) -> bool:
        if required_capital > buying_power:
            self.logger.warning("Insufficient buying power")
            return False
        return True

    # Position sizing
    def calculate_position_size(self, symbol: str, risk_percent: float, stop_loss_distance: float, account_value: float) -> int:
        risk_amount = account_value * (risk_percent / 100.0)
        if stop_loss_distance <= 0:
            raise ValueError("Stop loss distance must be positive")
        size = int(risk_amount / stop_loss_distance)
        self.logger.info("Calculated position size for %s: %s", symbol, size)
        return max(size, 1)

    def validate_position_size(self, size: int, account_value: float, price: float) -> bool:
        position_value = size * price
        max_allowed = (self.config.max_position_size_percent / 100.0) * account_value
        return position_value <= max_allowed

    # Risk Monitoring
    def monitor_open_positions(self) -> List[Dict]:
        return self.open_positions

    def calculate_portfolio_risk(self, account_value: float) -> float:
        total_exposure = sum(p.get("market_value", 0) for p in self.open_positions)
        if account_value == 0:
            return 0.0
        return (total_exposure / account_value) * 100

    def trigger_emergency_stop(self) -> None:
        self.emergency_stop_triggered = True
        self.logger.critical("Emergency stop triggered")

    def record_trade_result(self, pnl: float) -> None:
        self.trades_today += 1
        if pnl < 0:
            self.consecutive_losses += 1
        elif pnl > 0:
            self.consecutive_losses = 0

    def reset_daily_counters(self) -> None:
        self.trades_today = 0
        self.consecutive_losses = 0

    def can_trade(self) -> bool:
        if self.emergency_stop_triggered:
            self.logger.warning("Trading halted by emergency stop")
            return False
        if not self.check_daily_loss_limit():
            return False
        if not self.check_max_positions():
            return False
        if hasattr(self.config, "max_trades_per_day") and self.trades_today >= self.config.max_trades_per_day:
            self.logger.warning("Max trades per day reached")
            return False
        if hasattr(self.config, "max_consecutive_losses") and self.consecutive_losses >= self.config.max_consecutive_losses:
            self.logger.warning("Max consecutive losses reached")
            return False
        return True

    # Configuration setters
    def set_max_position_size(self, percent_of_account: float) -> None:
        self.config.max_position_size_percent = percent_of_account

    def set_max_daily_loss(self, dollar_amount: float) -> None:
        self.config.max_daily_loss = dollar_amount

    def set_max_positions(self, count: int) -> None:
        self.config.max_positions = count

    def set_risk_per_trade(self, percent: float) -> None:
        self.config.risk_per_trade_percent = percent
