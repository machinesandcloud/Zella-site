from typing import List

# Day Trading Universe - High Volume, Liquid Stocks Perfect for Intraday Trading
# Focused on: Tech, Mega Caps, Popular Day Trading Names, High Beta Stocks

DAY_TRADING_UNIVERSE = [
    # MEGA CAP TECH (Highest Volume)
    "AAPL",   # Apple - Most liquid stock
    "MSFT",   # Microsoft
    "GOOGL",  # Google
    "AMZN",   # Amazon
    "META",   # Meta/Facebook
    "TSLA",   # Tesla - High volatility
    "NVDA",   # Nvidia - AI/Chip leader

    # HIGH VOLUME TECH
    "AMD",    # AMD - Chip competitor to NVDA
    "NFLX",   # Netflix
    "PYPL",   # PayPal
    "SQ",     # Block (Square)
    "SHOP",   # Shopify
    "ABNB",   # Airbnb
    "UBER",   # Uber
    "LYFT",   # Lyft
    "SNOW",   # Snowflake
    "PLTR",   # Palantir
    "RBLX",   # Roblox

    # POPULAR DAY TRADING STOCKS
    "GME",    # GameStop - High retail interest
    "AMC",    # AMC - Meme stock
    "BB",     # BlackBerry
    "BBBY",   # Bed Bath & Beyond
    "SOFI",   # SoFi
    "RIVN",   # Rivian
    "LCID",   # Lucid Motors
    "NIO",    # Nio
    "COIN",   # Coinbase - Crypto proxy

    # SEMICONDUCTORS (High Beta)
    "INTC",   # Intel
    "MU",     # Micron
    "QCOM",   # Qualcomm
    "AVGO",   # Broadcom
    "TSM",    # TSMC
    "ASML",   # ASML

    # FINANCIAL TECH
    "V",      # Visa
    "MA",     # Mastercard
    "JPM",    # JP Morgan
    "BAC",    # Bank of America
    "GS",     # Goldman Sachs
    "MS",     # Morgan Stanley

    # CONSUMER / RETAIL
    "DIS",    # Disney
    "NKE",    # Nike
    "SBUX",   # Starbucks
    "TGT",    # Target
    "WMT",    # Walmart
    "COST",   # Costco
    "HD",     # Home Depot

    # HEALTHCARE / BIOTECH
    "JNJ",    # Johnson & Johnson
    "PFE",    # Pfizer
    "MRNA",   # Moderna
    "BNTX",   # BioNTech

    # ENERGY
    "XOM",    # Exxon
    "CVX",    # Chevron
    "OXY",    # Occidental

    # COMMUNICATION
    "CMCSA",  # Comcast
    "T",      # AT&T
    "VZ",     # Verizon

    # ETFS (Great for broader market plays)
    "SPY",    # S&P 500 - Most liquid ETF
    "QQQ",    # Nasdaq 100 - Tech heavy
    "IWM",    # Russell 2000 - Small caps
    "DIA",    # Dow Jones
    "TLT",    # 20+ Year Treasury
    "GLD",    # Gold
    "SLV",    # Silver
    "USO",    # Oil
    "VXX",    # Volatility
    "SQQQ",   # 3x Inverse QQQ
    "TQQQ",   # 3x QQQ
    "UVXY",   # 2x VIX

    # ADDITIONAL HIGH VOLUME STOCKS
    "BA",     # Boeing
    "CAT",    # Caterpillar
    "F",      # Ford
    "GM",     # General Motors
    "IBM",    # IBM
    "ORCL",   # Oracle
    "CRM",    # Salesforce
    "ADBE",   # Adobe
    "CSCO",   # Cisco
    "PEP",    # PepsiCo
    "KO",     # Coca-Cola
    "MCD",    # McDonald's
]

# Legacy small universe (kept for backwards compatibility)
DEFAULT_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "TSLA", "AMZN",
    "META", "AMD", "GOOGL", "SPY", "QQQ"
]


def get_default_universe() -> List[str]:
    """Get default day trading universe (90+ liquid stocks)"""
    return DAY_TRADING_UNIVERSE.copy()


def get_small_universe() -> List[str]:
    """Get small universe for testing (10 stocks)"""
    return DEFAULT_UNIVERSE.copy()


def get_mega_cap_universe() -> List[str]:
    """Get only mega cap stocks (safest, most liquid)"""
    return [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA",
        "SPY", "QQQ", "IWM", "DIA"
    ]
