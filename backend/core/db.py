from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import settings


connect_args = {}
if settings.database_url_effective.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url_effective, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
