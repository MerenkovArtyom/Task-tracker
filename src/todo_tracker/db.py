from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Shared declarative base for ORM models."""


DEFAULT_DB_URL = f"sqlite:///{Path.home() / '.todo_tracker.db'}"


def create_db_engine(db_url: str = DEFAULT_DB_URL) -> Engine:
    return create_engine(db_url)


def create_session_factory(db_url: str = DEFAULT_DB_URL) -> sessionmaker[Session]:
    engine = create_db_engine(db_url)
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_db(db_url: str = DEFAULT_DB_URL) -> sessionmaker[Session]:
    from todo_tracker.models import Note

    _ = Note
    session_factory = create_session_factory(db_url)
    Base.metadata.create_all(session_factory.kw["bind"])
    return session_factory
