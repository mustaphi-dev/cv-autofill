import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app import deps

# Tests that touch the database or Valkey use the Compose services:
# `docker compose up -d --wait`.


@pytest.fixture(scope="session")
def migrated() -> None:
    # The fixtures truncate, flush and drop: never point them at a real server.
    local = {"localhost", "127.0.0.1"}
    redis_host = deps.cache.connection_pool.connection_kwargs.get("host")
    if deps.engine.url.host not in local or redis_host not in local:
        pytest.exit("Tests only run against the local Compose services.")
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture
def clean(migrated: None) -> None:
    with deps.engine.begin() as connection:
        connection.execute(text("TRUNCATE installs"))
    deps.cache.flushdb()
