import re

SYMBOL_RE = re.compile(r"^[A-Z0-9\.\-]{1,10}$")


def validate_symbol(symbol: str) -> str:
    if not SYMBOL_RE.match(symbol):
        raise ValueError("Invalid symbol format")
    return symbol


def validate_quantity(quantity: int) -> int:
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    return quantity


def validate_price(price: float) -> float:
    if price <= 0:
        raise ValueError("Price must be positive")
    return price
