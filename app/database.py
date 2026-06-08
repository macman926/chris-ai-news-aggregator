import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base

load_dotenv()

_engine: Engine | None = None
_SessionLocal = None


def _get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(os.environ["DATABASE_URL"])
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def get_session() -> Session:
    _get_engine()
    return _SessionLocal()


def create_tables() -> None:
    Base.metadata.create_all(bind=_get_engine())
