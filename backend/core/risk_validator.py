from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CheckResult:
    passed: bool
    severity: str = "INFO"
    reason: Optional[str] = None
    warning: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    approved: bool
    reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class PreTradeRiskValidator:
    def __init__(
        self,
        max_position_size_percent: float,
        max_daily_loss: float,
        max_positions: int,
        max_spread_percent: float = 0.5,
    ) -> None:
        self.max_position_size_percent = max_position_size_percent
        self.max_daily_loss = max_daily_loss
        self.max_positions = max_positions
        self.max_spread_percent = max_spread_percent

    def validate(
        self,
        symbol: str,
        quantity: int,
        price: float,
        account_value: float,
        daily_pnl: float,
        open_positions: int,
        buying_power: float,
        spread_percent: Optional[float] = None,
    ) -> ValidationResult:
        checks = [
            self._check_daily_loss(daily_pnl),
            self._check_position_size(symbol, quantity, price, account_value),
            self._check_max_positions(open_positions),
            self._check_buying_power(quantity, price, buying_power),
            self._check_spread(spread_percent),
        ]

        failures = [check for check in checks if not check.passed]
        warnings = [check.warning for check in checks if check.warning]
        suggestions = [check.suggestion for check in checks if check.suggestion]

        if failures:
            reason = "; ".join([check.reason or "Risk check failed" for check in failures])
            return ValidationResult(approved=False, reason=reason, warnings=warnings, suggestions=suggestions)

        return ValidationResult(approved=True, warnings=warnings, suggestions=suggestions)

    def _check_daily_loss(self, daily_pnl: float) -> CheckResult:
        if daily_pnl <= -abs(self.max_daily_loss):
            return CheckResult(
                passed=False,
                reason=f"Daily loss limit reached: ${daily_pnl:.2f}",
                severity="CRITICAL",
            )
        warning_threshold = -abs(self.max_daily_loss) * 0.8
        if daily_pnl <= warning_threshold:
            return CheckResult(
                passed=True,
                warning=f"Near daily loss limit: ${daily_pnl:.2f}",
                severity="WARNING",
            )
        return CheckResult(passed=True)

    def _check_position_size(
        self, symbol: str, quantity: int, price: float, account_value: float
    ) -> CheckResult:
        if account_value <= 0:
            return CheckResult(passed=True)
        position_value = quantity * price
        percent = (position_value / account_value) * 100
        if percent > self.max_position_size_percent:
            return CheckResult(
                passed=False,
                reason=f"Position size {percent:.1f}% exceeds limit {self.max_position_size_percent}%",
                severity="ERROR",
            )
        return CheckResult(passed=True)

    def _check_max_positions(self, open_positions: int) -> CheckResult:
        if open_positions >= self.max_positions:
            return CheckResult(
                passed=False,
                reason=f"Max positions reached ({open_positions}/{self.max_positions})",
                severity="ERROR",
            )
        return CheckResult(passed=True)

    def _check_buying_power(self, quantity: int, price: float, buying_power: float) -> CheckResult:
        required = quantity * price
        if required > buying_power:
            return CheckResult(
                passed=False,
                reason=f"Insufficient buying power: need ${required:.2f}",
                severity="ERROR",
                suggestion="Reduce quantity or use a smaller risk preset.",
            )
        return CheckResult(passed=True)

    def _check_spread(self, spread_percent: Optional[float]) -> CheckResult:
        if spread_percent is None:
            return CheckResult(passed=True)
        if spread_percent > self.max_spread_percent:
            return CheckResult(
                passed=False,
                reason=f"Spread too wide: {spread_percent:.2f}%",
                severity="ERROR",
                suggestion="Wait for better liquidity or use a limit order.",
            )
        return CheckResult(passed=True)
