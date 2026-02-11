from dataclasses import dataclass
from typing import Optional


@dataclass
class Signal:
    symbol: str
    action: str
    quantity: int
    order_type: str
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
