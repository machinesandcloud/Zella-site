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
    admin_password: str = ""
    auto_login_enabled: bool = False

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
    cors_allowed_origins: str = "https://zella-site.netlify.app"
    cors_allow_origin_regex: str = r"https://.*\\.netlify\\.app"

    # QA / Dev
    use_mock_ibkr: bool = True
    use_free_data: bool = True
    use_ibkr_webapi: bool = False
    ibkr_webapi_base_url: str = "https://localhost:5000/v1/api"
    ibkr_webapi_account_id: str = ""
    ibkr_webapi_verify_ssl: bool = False

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


settings = Settings()
