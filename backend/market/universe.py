from typing import List

DEFAULT_UNIVERSE = [
    "AAPL",
    "MSFT",
    "NVDA",
    "TSLA",
    "AMZN",
    "META",
    "AMD",
    "GOOGL",
    "SPY",
    "QQQ",
]


def get_default_universe() -> List[str]:
    return DEFAULT_UNIVERSE.copy()
