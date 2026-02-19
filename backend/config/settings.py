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

    # Trading Defaults
    default_trading_mode: str = "PAPER"
    max_position_size_percent: float = 10.0
    max_daily_loss: float = 500.0
    max_risk_per_trade: float = 2.0
    max_concurrent_positions: int = 5
    max_trades_per_day: int = 12
    max_consecutive_losses: int = 3

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

    # Screener defaults
    screener_min_avg_volume: float = 500000
    screener_min_price: float = 5.0
    screener_max_price: float = 1000.0
    screener_min_volatility: float = 0.005
    screener_min_relative_volume: float = 2.0

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
        warnings = []

        # Check secret key
        if self.secret_key == "your-secret-key-here":
            warnings.append("⚠️  SECRET_KEY is set to default value - CHANGE THIS in production!")

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
