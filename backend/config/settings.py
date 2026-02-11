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

    # Security
    secret_key: str = "your-secret-key-here"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Trading Defaults
    default_trading_mode: str = "PAPER"
    max_position_size_percent: float = 10.0
    max_daily_loss: float = 500.0
    max_risk_per_trade: float = 2.0
    max_concurrent_positions: int = 5

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/trading_bot.log"

    # QA / Dev
    use_mock_ibkr: bool = True

    # Screener defaults
    screener_min_avg_volume: float = 500000
    screener_min_price: float = 5.0
    screener_max_price: float = 1000.0
    screener_min_volatility: float = 0.005

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def database_url_effective(self) -> str:
        return self.database_url or self.sqlite_url


settings = Settings()
