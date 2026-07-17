"""Database engine and session lifecycle.

The :class:`Database` class owns a single engine and session factory.
Use it as the **only** way to obtain sessions::

    db = Database("data/web_agent.db")
    db.create_tables()           # once at startup

    with db.session() as s:
        s.query(orm.Project).all()
        # auto-commits on clean exit, rolls back on exception, always closes.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlite3 import Connection as SQLite3Connection

from src.infrastructure.database.models import Base


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class Database:
    """Holds a single :class:`~sqlalchemy.engine.Engine` and
    :class:`~sqlalchemy.orm.sessionmaker` for the application lifetime.

    Parameters
    ----------
    db_path:
        Path to the SQLite file (or ``":memory:"`` for tests).
    """

    __slots__ = ("_engine", "_session_factory")

    def __init__(self, db_path: str = "data/web_agent.db") -> None:
        if db_path == ":memory:":
            url = "sqlite://"
        else:
            url = f"sqlite:///{db_path}"

        # Add connect_args to allow cross-thread usage for SQLite
        connect_args = {"check_same_thread": False} if "sqlite" in url else {}
        
        self._engine: Engine = create_engine(
            url, 
            echo=False, 
            connect_args=connect_args
        )
        
        self._session_factory = sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
        )

    def create_tables(self) -> None:
        """Create all tables.  Call once at application startup."""
        Base.metadata.create_all(self._engine)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Yield a session that commits on success, rolls back on error,
        and always closes."""
        session: Session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self) -> None:
        """Dispose the engine, releasing all connections."""
        self._engine.dispose()

    @property
    def engine(self) -> Engine:
        """The underlying engine (mostly for introspection / testing)."""
        return self._engine