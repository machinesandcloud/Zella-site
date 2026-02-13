from sqlalchemy import inspect, text

from models import Base
from .db import engine


def _ensure_trade_columns() -> None:
    inspector = inspect(engine)
    if "trades" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("trades")}
    alterations = []
    if "setup_tag" not in columns:
        alterations.append("ADD COLUMN setup_tag VARCHAR(50)")
    if "catalyst" not in columns:
        alterations.append("ADD COLUMN catalyst VARCHAR(120)")
    if "stop_method" not in columns:
        alterations.append("ADD COLUMN stop_method VARCHAR(30)")
    if "risk_mode" not in columns:
        alterations.append("ADD COLUMN risk_mode VARCHAR(20)")
    if not alterations:
        return
    statement = "ALTER TABLE trades " + ", ".join(alterations)
    with engine.begin() as conn:
        conn.execute(text(statement))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_trade_columns()
