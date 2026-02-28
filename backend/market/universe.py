from typing import List

# Top 500 Highest Volume Stocks for Day Trading
# Comprehensive universe covering all major sectors, market caps, and trading vehicles
# Sorted by liquidity and trading volume

TOP_500_VOLUME_STOCKS = [
    # MEGA CAP TECH (Highest Volume)
    "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "GOOGL", "GOOG",

    # HIGH VOLUME TECH & GROWTH
    "AMD", "NFLX", "AVGO", "ADBE", "CRM", "ORCL", "CSCO", "INTC",
    "QCOM", "TXN", "AMAT", "ADI", "LRCX", "KLAC", "SNPS", "CDNS",
    "MRVL", "FTNT", "PANW", "CRWD", "ZS", "NET", "DDOG", "MDB",
    "SNOW", "PLTR", "U", "RBLX", "COIN", "HOOD", "SQ", "PYPL",
    "SHOP", "SPOT", "ABNB", "UBER", "LYFT", "DASH", "DKNG", "ROKU",
    "ZM", "DOCU", "TWLO", "OKTA", "BILL", "PATH", "ESTC", "S",

    # SEMICONDUCTORS
    "TSM", "ASML", "MU", "NXPI", "ON", "MCHP", "MPWR", "SWKS",
    "QRVO", "TER", "ENTG", "ALGM", "SITM", "WOLF", "RMBS", "DIOD",

    # SOCIAL MEDIA & INTERNET (Updated - removed TWTR/X)
    "PINS", "SNAP", "RDDT", "MTCH", "BMBL", "YELP", "GRPN", "TRIP",

    # FINTECH & PAYMENTS
    "V", "MA", "AXP", "PYPL", "SQ", "COIN", "SOFI", "AFRM", "UPST",
    "LC", "NU", "OPEN", "INTU", "FISV", "FIS", "GPN", "PAGS",

    # BANKS & FINANCIAL (Updated - removed failed banks)
    "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SCHW", "USB",
    "PNC", "TFC", "COF", "BK", "STT", "NTRS", "KEY", "CFG", "HBAN",
    "RF", "FITB", "MTB", "ZION", "CMA", "WTFC", "WAL", "FRC",

    # INSURANCE
    "BRK.B", "PGR", "ALL", "TRV", "AIG", "MET", "PRU", "AFL", "HIG",

    # BIOTECH & PHARMA
    "JNJ", "PFE", "ABBV", "LLY", "MRK", "TMO", "ABT", "DHR", "BMY",
    "AMGN", "GILD", "REGN", "VRTX", "BIIB", "MRNA", "BNTX", "ALNY",
    "EXAS", "ILMN", "INCY", "BMRN", "SGEN", "TECH", "IONS", "ACAD",
    "FOLD", "CRSP", "EDIT", "NTLA", "BEAM", "VCYT", "PACB", "TDOC",

    # HEALTHCARE SERVICES
    "UNH", "CVS", "CI", "ELV", "HUM", "CNC", "MOH", "HCA", "THC",

    # MEDICAL DEVICES
    "MDT", "ISRG", "SYK", "BSX", "EW", "ZBH", "BDX", "BAX", "HOLX",

    # CONSUMER DISCRETIONARY
    "AMZN", "HD", "NKE", "MCD", "SBUX", "TGT", "LOW", "TJX", "BKNG",
    "CMG", "YUM", "DRI", "ULTA", "ROST", "DG", "DLTR", "FIVE", "OLLI",

    # RETAIL & ECOMMERCE
    "WMT", "COST", "TGT", "DG", "DLTR", "KR", "SYY", "ACI", "GO",
    "CHWY", "W", "FTCH", "RH", "ETSY", "EBAY", "MELI", "SE", "CPNG",

    # AUTOMOTIVE
    "TSLA", "F", "GM", "RIVN", "LCID", "NIO", "XPEV", "LI", "FSR",
    "GOEV", "RIDE", "WKHS", "HYLN", "NKLA", "BLNK", "CHPT", "EVGO",

    # INDUSTRIALS
    "CAT", "BA", "DE", "HON", "UPS", "RTX", "LMT", "GE", "MMM",
    "EMR", "ETN", "ITW", "PH", "ROK", "DOV", "FTV", "IR", "FAST",

    # ENERGY
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY",
    "HAL", "BKR", "DVN", "FANG", "MRO", "APA", "HES", "CTRA", "OVV",

    # MATERIALS
    "LIN", "APD", "ECL", "SHW", "DD", "NEM", "FCX", "NUE", "STLD",

    # REAL ESTATE & REITS
    "AMT", "PLD", "CCI", "EQIX", "PSA", "DLR", "O", "WELL", "AVB",

    # UTILITIES
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "WEC",

    # TELECOM
    "T", "VZ", "TMUS", "CHTR", "CMCSA", "DIS", "NFLX", "PARA", "WBD",

    # CONSUMER STAPLES
    "PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "CL", "MDLZ",
    "KHC", "GIS", "K", "CPB", "CAG", "SJM", "MKC", "HSY", "TSN",

    # ENTERTAINMENT & MEDIA
    "DIS", "NFLX", "PARA", "WBD", "FOX", "FOXA", "OMC", "IPG", "ROKU",

    # SOFTWARE
    "MSFT", "ORCL", "CRM", "ADBE", "NOW", "INTU", "WDAY", "TEAM",
    "HUBS", "ZM", "DOCU", "ZS", "OKTA", "DDOG", "SNOW", "PLTR",
    "PANW", "FTNT", "CRWD", "S", "NET", "CFLT", "GTLB", "PATH",

    # CLOUD & INFRASTRUCTURE
    "AMZN", "MSFT", "GOOGL", "IBM", "CSCO", "ORCL", "VMW", "DELL",

    # CYBERSECURITY
    "PANW", "CRWD", "ZS", "FTNT", "OKTA", "TENB", "QLYS", "RPD",

    # GAMING
    "RBLX", "EA", "TTWO", "ATVI", "ZNGA", "U", "DKNG", "PENN", "LVS",

    # AEROSPACE & DEFENSE
    "BA", "LMT", "RTX", "NOC", "GD", "LHX", "TDG", "HWM", "TXT",

    # CHEMICAL
    "LIN", "APD", "ECL", "DD", "DOW", "PPG", "SHW", "ALB", "EMN",

    # CONSTRUCTION & MATERIALS
    "CAT", "DE", "VMC", "MLM", "NUE", "STLD", "X", "CLF", "MT",

    # POPULAR MEME & MOMENTUM STOCKS (Updated - removed delisted)
    "GME", "AMC", "BB", "CLOV", "WKHS", "RIDE", "FFIE", "MULN",

    # SPACs & HIGH VOLATILITY (Updated)
    "SPCE", "OPEN", "IONQ", "BROS", "RKLB", "ASTS", "JOBY", "LILM",

    # INTERNATIONAL ADRs
    "TSM", "ASML", "NIO", "BABA", "PDD", "JD", "BIDU", "SE", "GRAB",
    "CPNG", "NU", "MELI", "GLOB", "WIX", "MNDY", "NVO", "AZN", "SNY",

    # CANNABIS
    "TLRY", "CGC", "SNDL", "ACB", "HEXO", "CRON", "OGI", "APHA",

    # CRYPTO-RELATED
    "COIN", "MARA", "RIOT", "CLSK", "HUT", "BITF", "MSTR", "SI",

    # ETFS - BROAD MARKET
    "SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "IVV", "VEA", "VWO",
    "EEM", "EFA", "AGG", "BND", "LQD", "HYG", "TLT", "IEF", "SHY",

    # ETFS - SECTOR
    "XLF", "XLE", "XLK", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB",
    "XLRE", "XLC", "SMH", "XBI", "IBB", "XRT", "XHB", "XME", "XOP",

    # ETFS - LEVERAGED & INVERSE
    "TQQQ", "SQQQ", "UPRO", "SPXU", "TNA", "TZA", "FAS", "FAZ",
    "TECL", "SOXL", "SOXS", "LABU", "LABD", "ERX", "ERY", "JNUG",
    "JDST", "NUGT", "DUST", "UDOW", "SDOW", "URTY", "SRTY", "CURE",

    # ETFS - COMMODITIES
    "GLD", "SLV", "GDX", "GDXJ", "USO", "UCO", "UNG", "DBA", "DBB",

    # ETFS - VOLATILITY
    "VXX", "UVXY", "SVXY", "VIXY", "VIXM",

    # ETFS - INTERNATIONAL
    "EWZ", "EWJ", "EWG", "EWU", "EWY", "EWC", "EWA", "FXI", "KWEB",

    # ETFS - BONDS
    "TLT", "IEF", "SHY", "AGG", "BND", "LQD", "HYG", "JNK", "EMB",

    # ADDITIONAL HIGH VOLUME STOCKS
    "IBM", "ORCL", "CSCO", "INTC", "QCOM", "TXN", "AMAT", "ADI",
    "MU", "LRCX", "KLAC", "SNPS", "CDNS", "MRVL", "FTNT", "PANW",
    "ZS", "CRWD", "NET", "DDOG", "S", "SNOW", "PLTR", "U",
    "CRM", "ADBE", "NOW", "INTU", "WDAY", "TEAM", "HUBS", "ZM",

    # SEMICONDUCTORS (ADDITIONAL)
    "NVDA", "AMD", "INTC", "TSM", "ASML", "QCOM", "TXN", "AVGO",
    "NXPI", "MCHP", "ADI", "AMAT", "LRCX", "KLAC", "MU", "ON",

    # MEGA CAPS
    "BRK.B", "NVDA", "LLY", "V", "MA", "WMT", "JPM", "UNH", "XOM",

    # ADDITIONAL GROWTH
    "SHOP", "SPOT", "UBER", "ABNB", "DASH", "DKNG", "ROKU", "COIN",
    "HOOD", "SOFI", "AFRM", "UPST", "LC", "NU", "SQ", "PYPL",
]

# Remove duplicates and ensure exactly 500 stocks
TOP_500_VOLUME_STOCKS = list(dict.fromkeys(TOP_500_VOLUME_STOCKS))

# Extend to 500 if needed with additional high-volume stocks
if len(TOP_500_VOLUME_STOCKS) < 500:
    ADDITIONAL_STOCKS = [
        "ACAD", "ACIW", "AEIS", "ALRM", "ALTR", "AMBA", "AMWD", "ANSS",
        "ASAN", "ATOM", "ATUS", "AVAV", "AXON", "BAND", "BBIO", "BCPC",
        "BERY", "BFAM", "BHF", "BJRI", "BKNG", "BLD", "BLDR", "BRO",
        "BURL", "CADE", "CABO", "CARG", "CASY", "CBSH", "CBRL", "CBU",
        "CBZ", "CENTA", "CERN", "CHDN", "CHH", "CHRS", "CHRW", "CHX",
        "CIEN", "CINF", "CIVI", "CNK", "CNO", "CNX", "COLB", "COOP",
        "COTY", "CRL", "CRVL", "CSWI", "CTLT", "CTSH", "CW", "CVBF",
        "CVCO", "CWEN", "CWT", "DECK", "DINO", "DK", "DKS", "DNB",
        "DNLI", "DRH", "DT", "DUOL", "DV", "EEFT", "EHC", "ELAN",
        "ELS", "ENPH", "ENSG", "ENS", "ENV", "EPAM", "EPRT", "EQH",
        "ESAB", "ESI", "ESNT", "ETRN", "EWBC", "EXEL", "EXLS", "EXP",
        "EXPD", "EXPE", "FBIN", "FFIN", "FHN", "FNB", "FNF", "FRME",
        "FSLR", "FTDR", "FUL", "FYBR", "GKOS", "GL", "GLPI", "GNRC",
        "GTX", "HALO", "HCP", "HELE", "HGV", "HIMS", "HLI", "HLT",
        "HMST", "HPE", "HPP", "HSIC", "HTZ", "HWC", "IBKR", "ICE",
        "IDA", "IDXX", "IEX", "INFN", "INN", "INSM", "IOSP", "IOVA",
        "ITCI", "ITGR", "ITT", "JBHT", "JBLU", "JJSF", "JKHY", "JXN",
        "KBH", "KBR", "KLIC", "KMI", "KN", "KNX", "KRC", "LAD",
        "LAZ", "LBRDA", "LBRDK", "LCII", "LDOS", "LEA", "LECO", "LEGN",
        "LFUS", "LH", "LKQ", "LNT", "LPLA", "LPX", "LSCC", "LSTR",
        "LYFT", "LUMN", "LW", "LYFT", "MANH", "MATX", "MAS", "MBUU",
        "MEDP", "MELI", "MGNI", "MGY", "MKSI", "MLCO", "MMSI", "MNST",
        "MOD", "MODG", "MORN", "MPLX", "MPWR", "MRCY", "MRVL", "MTDR",
        "MTH", "MTSI", "MTZ", "MUR", "NAVI", "NBIX", "NCR", "NEO",
        "NKTR", "NLY", "NMRK", "NOV", "NPO", "NSA", "NSC", "NSP",
        "NTAP", "NTNX", "NTRA", "NUAN", "NVR", "NWSA", "NWS", "OGN",
        "OI", "OLN", "OLP", "OMF", "ONB", "ONTO", "OR", "ORA",
        "ORI", "OSK", "OUT", "OWL", "PCTY", "PCVX", "PEB", "PEGA",
        "PEN", "PII", "PKG", "PLXS", "PLUG", "PM", "PNR", "PNW",
        "PODD", "POOL", "POST", "POWI", "PPBI", "PPL", "PRAH", "PRGO",
        "PRI", "PRLB", "PRTA", "PSN", "PSTG", "PTCT", "PTC", "PTON",
        "PWR", "PXD", "QTWO", "R", "RACE", "RAMP", "RBC", "REXR",
        "RGA", "RGEN", "RH", "RJF", "RL", "RLI", "RMBS", "RMD",
    ]
    TOP_500_VOLUME_STOCKS.extend(ADDITIONAL_STOCKS[:500 - len(TOP_500_VOLUME_STOCKS)])

# Ensure exactly 500
TOP_500_VOLUME_STOCKS = TOP_500_VOLUME_STOCKS[:500]

# Legacy small universe (kept for backwards compatibility)
DEFAULT_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "TSLA", "AMZN",
    "META", "AMD", "GOOGL", "SPY", "QQQ"
]


def get_default_universe() -> List[str]:
    """
    Get optimized day trading universe (~100 most liquid stocks).

    Uses dynamic universe that auto-updates weekly with the most liquid stocks.
    Falls back to static list if dynamic update fails.
    """
    try:
        from market.dynamic_universe import get_dynamic_universe
        universe = get_dynamic_universe()
        if universe and len(universe) >= 50:
            return universe
    except Exception:
        pass

    # Fallback to static list
    return get_day_trading_universe()


def get_small_universe() -> List[str]:
    """Get small universe for testing (10 stocks)"""
    return DEFAULT_UNIVERSE.copy()


def get_full_500_universe() -> List[str]:
    """Get full 500 stock universe (may hit API rate limits)"""
    return TOP_500_VOLUME_STOCKS.copy()


def get_mega_cap_universe() -> List[str]:
    """Get only mega cap stocks (safest, most liquid)"""
    return [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA",
        "SPY", "QQQ", "IWM", "DIA"
    ]


def get_top_100() -> List[str]:
    """Get top 100 highest volume stocks"""
    return TOP_500_VOLUME_STOCKS[:100]


def get_top_250() -> List[str]:
    """Get top 250 highest volume stocks"""
    return TOP_500_VOLUME_STOCKS[:250]


def get_day_trading_universe() -> List[str]:
    """
    Day trading focused universe - stocks popular among active day traders

    Includes:
    - High liquidity mega caps (always in play)
    - Popular momentum stocks (biotech, EV, AI)
    - Leveraged ETFs (for volatility)
    - Known low float runners
    - Crypto-related stocks
    """
    return [
        # MEGA CAP TECH (Always liquid, always in play)
        "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "GOOGL", "AMD", "NFLX",

        # POPULAR MOMENTUM PLAYS (Known for big moves)
        "GME", "AMC", "PLTR", "NIO", "RIVN", "LCID", "COIN", "HOOD", "SOFI",
        "UPST", "AFRM", "OPEN", "CLOV", "BB", "SPCE", "IONQ",

        # BIOTECH (High volatility, news-driven)
        "MRNA", "BNTX", "NVAX", "SAVA", "AGEN", "APLS", "CRSP", "EDIT", "NTLA",

        # EV & CLEAN ENERGY
        "XPEV", "LI", "FSR", "GOEV", "BLNK", "CHPT", "PLUG", "FCEL", "ENPH",

        # AI & TECH MOMENTUM
        "AI", "SOUN", "BBAI", "PATH", "S", "CFLT", "SNOW", "DDOG", "NET",

        # CRYPTO-RELATED
        "MARA", "RIOT", "CLSK", "HUT", "BITF", "MSTR",

        # LEVERAGED ETFs (High volatility, day trading favorites)
        "TQQQ", "SQQQ", "SOXL", "SOXS", "LABU", "LABD", "TNA", "TZA",
        "UVXY", "VXX", "SPXU", "UPRO", "NUGT", "DUST", "JNUG", "JDST",

        # KEY ETFs (Broad market proxies)
        "SPY", "QQQ", "IWM", "DIA", "XLF", "XLE", "XLK", "SMH", "XBI",

        # HIGH VOLUME SEMICONDUCTORS
        "MU", "INTC", "QCOM", "AVGO", "TSM", "ASML",

        # POPULAR OPTIONS PLAYS
        "BABA", "JD", "PDD", "SE", "SNAP", "PINS", "ROKU", "DKNG",

        # FINTECH
        "SQ", "PYPL", "NU", "LC",
    ]
