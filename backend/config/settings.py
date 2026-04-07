from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # IBKR Configuration
    ibkr_host: str = "127.0.0.1"
    ibkr_paper_port: int = 7497
    ibkr_live_port: int = 7496
    ibkr_client_id: int = 1

    # Database
    database_url: str = "postgresql+psycopg2://user:password@localhost:5432/trading_bot"
    sqlite_url: str = "sqlite:///./trading_bot.db"
    redis_url: str = "redis://localhost:6379"
    use_sqlite: bool = False

    # Security
    secret_key: str = "your-secret-key-here"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Auth
    allow_signup: bool = False
    admin_username: str = "admin"
    admin_email: str = "admin@zella.local"
    admin_password: str = "zella-auto-login-2024"  # Auto-generated for auto-login
    auto_login_enabled: bool = True  # Enable automatic login

    # Trading Defaults - UPDATED per expert review recommendations
    default_trading_mode: str = "PAPER"
    max_position_size_percent: float = 5.0  # Was 10% - reduced to limit concentration per position
    max_daily_loss: float = 2000.0  # Was $500 - raised to 2% of $100k (must be >= max single trade loss)
    max_risk_per_trade: float = 1.0  # Was 2% - reduced for safety during validation phase
    max_concurrent_positions: int = 3  # Was 5 - reduced to limit portfolio correlation risk
    max_trades_per_day: int = 15  # Allow reasonable activity
    max_consecutive_losses: int = 4  # Was 3 - slight increase to avoid premature halt

    # Execution settings - NEW per expert review
    use_limit_orders: bool = True  # Use limit orders instead of market orders
    limit_order_buffer_pct: float = 0.05  # 0.05% buffer above/below for limit orders
    limit_order_timeout_seconds: int = 10  # Cancel unfilled limit orders after this time
    track_slippage: bool = True  # Track and log slippage metrics
    max_acceptable_slippage_pct: float = 0.3  # Alert if slippage exceeds 0.3%

    # Strategy settings - NEW per expert review
    enabled_strategy_mode: str = "PROVEN_ONLY"  # PROVEN_ONLY | ALL - only use validated strategies
    min_confidence_threshold: float = 0.70  # Was 0.55-0.65 - raised to 70% minimum
    min_strategies_required: int = 2  # Require at least 2 strategies to agree

    # Portfolio risk settings - NEW per expert review
    max_sector_exposure_pct: float = 30.0  # Max 30% of portfolio in one sector
    max_total_exposure_pct: float = 60.0  # Max 60% of account deployed at once
    correlation_check_enabled: bool = True  # Check for correlated positions

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/trading_bot.log"

    # CORS
    cors_allowed_origins: str = "https://zella-site.netlify.app,http://localhost:3000,http://localhost:5173"
    cors_allow_origin_regex: str = r"https://.*\.netlify\.app"

    # QA / Dev
    use_mock_ibkr: bool = False
    use_free_data: bool = False
    use_ibkr_webapi: bool = False
    ibkr_webapi_base_url: str = "https://localhost:5000/v1/api"
    ibkr_webapi_account_id: str = ""
    ibkr_webapi_verify_ssl: bool = False

    # Alpaca Configuration
    use_alpaca: bool = False
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_paper: bool = True  # True for paper trading, False for live
    alpaca_data_feed: str = "iex"  # "iex" for free accounts, "sip" for paid

    # Market data add-ons
    polygon_api_key: str = ""
    polygon_base_url: str = "https://api.polygon.io"

    # Screener defaults — calibrated for Alpaca IEX data feed (IEX = ~0.3% of real market volume)
    # Real AAPL volume: 60M/day → IEX shows ~200-300k. Thresholds must reflect IEX scale.
    # Relative volume filter handles quality — absolute volume just blocks zero-liquidity stocks.
    screener_min_avg_volume: float = 15000   # IEX scale floor (real equivalent ~5M/day)
    screener_min_avg_volume_low_float: float = 10000   # Low float: smaller absolute volume ok
    screener_min_avg_volume_mid_float: float = 20000   # Mid float (21M-500M shares)
    screener_min_avg_volume_large_float: float = 50000  # Large float / ETFs
    screener_min_price: float = 1.0  # Allow stocks above $1
    screener_max_price: float = 500.0  # Focus on tradeable range
    screener_min_volatility: float = 0.2  # ATR % minimum (0.2% = barely moves; 0.5%+ is active)
    screener_min_relative_volume: float = 1.5  # Balanced relative volume threshold
    screener_min_relative_volume_low_float: float = 2.0  # Low float momentum needs higher rvol
    screener_min_relative_volume_mid_float: float = 1.5
    screener_min_relative_volume_large_float: float = 1.2  # Large caps can move on lower rvol
    screener_min_premarket_volume: float = 25000  # Premarket liquidity threshold for gappers
    screener_require_premarket_volume: bool = True  # Enforce premarket volume on gappers/premarket
    screener_require_daily_trend: bool = True  # Enforce daily SMA20/50 trend filter
    screener_low_float_max: float = 20.0  # Book: low float < 20M
    screener_mid_float_max: float = 500.0  # Book: mid float 20-500M
    screener_in_play_min_rvol: float = 2.0  # In-play threshold for relative volume
    screener_in_play_gap_percent: float = 2.0  # In-play gap threshold
    screener_in_play_volume_multiplier: float = 0.5  # Allow lower avg volume when in-play
    screener_debug: bool = False  # Include full screener debug metrics in logs/WS
    trade_frequency_profile: str = "balanced"  # conservative | balanced | active

    # Autonomous engine resilience
    autonomous_auto_resume: bool = True  # Auto-resume engine on restart/reconnect

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def database_url_effective(self) -> str:
        if self.use_sqlite:
            return self.sqlite_url
        return self.database_url or self.sqlite_url

    @property
    def use_alpaca_effective(self) -> bool:
        # Enable Alpaca if explicitly requested or if keys are present.
        return self.use_alpaca or (self.alpaca_api_key != "" and self.alpaca_secret_key != "")

    def validate_configuration(self) -> list[str]:
        """
        Validate configuration and return list of warnings/errors.

        Returns:
            List of warning messages (empty if all OK)
        """
        import os
        warnings = []

        # Check secret key - CRITICAL in production
        if self.secret_key == "your-secret-key-here":
            # In production (Render), this should fail startup
            if os.environ.get("RENDER") or os.environ.get("PRODUCTION"):
                raise ValueError("CRITICAL: SECRET_KEY must be set to a secure value in production!")
            warnings.append("⚠️  SECRET_KEY is set to default value - CHANGE THIS in production!")

        # Check admin password - CRITICAL in production
        if self.admin_password == "zella-auto-login-2024":
            if os.environ.get("RENDER") or os.environ.get("PRODUCTION"):
                raise ValueError("CRITICAL: ADMIN_PASSWORD must be changed from default in production!")
            warnings.append("⚠️  ADMIN_PASSWORD is set to default value - CHANGE THIS in production!")

        # Check Alpaca configuration
        if self.use_alpaca_effective:
            if not self.alpaca_api_key or not self.alpaca_secret_key:
                warnings.append("⚠️  Alpaca enabled but API keys are missing")
            elif len(self.alpaca_api_key) < 10:
                warnings.append("⚠️  Alpaca API key appears to be invalid (too short)")
            elif len(self.alpaca_secret_key) < 10:
                warnings.append("⚠️  Alpaca secret key appears to be invalid (too short)")

        # Check if both IBKR and Alpaca are disabled
        if not self.use_alpaca_effective and not self.use_ibkr_webapi and self.use_mock_ibkr:
            warnings.append("ℹ️  Running with mock IBKR (no real trading)")

        return warnings


settings = Settings()
