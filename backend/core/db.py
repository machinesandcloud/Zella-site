from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from config import settings


connect_args = {}
engine_kwargs = {"pool_pre_ping": True}
if settings.database_url_effective.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    if ":memory:" in settings.database_url_effective:
        engine_kwargs["poolclass"] = StaticPool

engine = create_engine(settings.database_url_effective, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
