from __future__ import annotations

from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

from sqlalchemy import Engine, create_engine, event, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings


SessionFactory = sessionmaker[Session]


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_database(
    settings: Settings | None = None,
    *,
    database_url: str | None = None,
    engine_options: dict[str, Any] | None = None,
) -> Database:
    resolved_settings = settings or get_settings()
    resolved_url = database_url or resolved_settings.sqlalchemy_database_url
    url = make_url(resolved_url)
    options: dict[str, Any] = {
        "echo": resolved_settings.database_echo,
        "pool_pre_ping": True,
    }

    if url.get_backend_name() == "sqlite":
        options["connect_args"] = {"check_same_thread": False}
        if url.database in (None, "", ":memory:"):
            options["poolclass"] = StaticPool
    else:
        options.update(
            pool_size=resolved_settings.database_pool_size,
            max_overflow=resolved_settings.database_max_overflow,
            pool_timeout=resolved_settings.database_pool_timeout_seconds,
        )

    if engine_options:
        options.update(engine_options)

    engine = create_engine(resolved_url, **options)
    if url.get_backend_name() == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)

    factory = sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )
    return Database(engine=engine, session_factory=factory)


@contextmanager
def session_scope(session_factory: SessionFactory) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@dataclass(frozen=True)
class Database:
    engine: Engine
    session_factory: SessionFactory

    def transaction(self) -> AbstractContextManager[Session]:
        return session_scope(self.session_factory)

    def dispose(self) -> None:
        self.engine.dispose()
