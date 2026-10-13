import logging
import os
from collections.abc import Iterator

import redis
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)


def setting(name: str, local: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    # On Render a missing setting is a deploy mistake: fail now, rather than
    # start up and report "database down" later.
    if os.environ.get("RENDER"):
        raise RuntimeError(f"{name} is not set")
    return local


engine = create_engine(
    setting("DATABASE_URL", "postgresql://cv:cv@localhost:5433/cv"),
    pool_pre_ping=True,
    # A hung database must not hold request threads: bound the connect, each
    # query, and the wait for a free pooled connection.
    pool_timeout=2,
    connect_args={"connect_timeout": 2, "options": "-c statement_timeout=2000"},
)
cache = redis.Redis.from_url(
    setting("REDIS_URL", "redis://localhost:6379"),
    socket_connect_timeout=2,
    socket_timeout=2,
)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


def database_ok() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        log.warning("database check failed", exc_info=True)
        return False
    return True


def redis_ok() -> bool:
    try:
        cache.ping()
    except redis.RedisError:
        log.warning("redis check failed", exc_info=True)
        return False
    return True
