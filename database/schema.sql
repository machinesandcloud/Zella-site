-- users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    ibkr_account_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- trades table
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    symbol VARCHAR(10) NOT NULL,
    strategy_name VARCHAR(50),
    action VARCHAR(4) NOT NULL, -- BUY/SELL
    quantity INTEGER NOT NULL,
    entry_price DECIMAL(10, 2),
    exit_price DECIMAL(10, 2),
    stop_loss DECIMAL(10, 2),
    take_profit DECIMAL(10, 2),
    pnl DECIMAL(10, 2),
    pnl_percent DECIMAL(5, 2),
    commission DECIMAL(10, 2),
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    status VARCHAR(20), -- OPEN/CLOSED/CANCELLED
    notes TEXT,
    is_paper_trade BOOLEAN DEFAULT TRUE
);

-- orders table
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    trade_id INTEGER REFERENCES trades(id),
    ibkr_order_id INTEGER,
    symbol VARCHAR(10) NOT NULL,
    asset_type VARCHAR(10) DEFAULT 'STK',
    exchange VARCHAR(20),
    currency VARCHAR(10),
    expiry VARCHAR(20),
    strike DECIMAL(10, 2),
    right VARCHAR(4),
    multiplier VARCHAR(10),
    order_type VARCHAR(20) NOT NULL,
    action VARCHAR(4) NOT NULL,
    quantity INTEGER NOT NULL,
    limit_price DECIMAL(10, 2),
    stop_price DECIMAL(10, 2),
    filled_quantity INTEGER DEFAULT 0,
    avg_fill_price DECIMAL(10, 2),
    status VARCHAR(20),
    placed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    filled_at TIMESTAMP
);

-- strategy_performance table
CREATE TABLE strategy_performance (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    strategy_name VARCHAR(50) NOT NULL,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    total_pnl DECIMAL(10, 2) DEFAULT 0,
    max_drawdown DECIMAL(10, 2),
    sharpe_ratio DECIMAL(5, 2),
    date DATE DEFAULT CURRENT_DATE
);

-- account_snapshots table
CREATE TABLE account_snapshots (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    account_value DECIMAL(12, 2),
    cash_balance DECIMAL(12, 2),
    buying_power DECIMAL(12, 2),
    daily_pnl DECIMAL(10, 2),
    snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_paper_account BOOLEAN
);
