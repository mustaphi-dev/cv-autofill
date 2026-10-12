import json

import pytest
import redis
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app import deps
from app.logs import JsonFormatter
from app.main import app

# These tests need the Compose services: `docker compose up -d --wait`.
client = TestClient(app)
CLOSED = "127.0.0.1:1"


def test_ready_when_both_services_are_up() -> None:
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"database": "ok", "redis": "ok"}


def test_names_the_database_when_it_is_down(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    down = create_engine(f"postgresql://cv:secret-pw@{CLOSED}/cv")
    monkeypatch.setattr(deps, "engine", down)
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json() == {"database": "down", "redis": "ok"}
    # Neither the answer nor the logs give away connection details.
    logged = json.dumps([JsonFormatter().format(r) for r in caplog.records])
    assert "OperationalError" in logged
    for detail in ("127.0.0.1", "secret-pw"):
        assert detail not in response.text
        assert detail not in logged


def test_names_redis_when_it_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps, "cache", redis.Redis.from_url(f"redis://{CLOSED}"))
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json() == {"database": "ok", "redis": "down"}


def test_settings_default_to_local_services(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    assert deps.setting("REDIS_URL", "redis://local") == "redis://local"
    monkeypatch.setenv("REDIS_URL", "redis://configured")
    assert deps.setting("REDIS_URL", "redis://local") == "redis://configured"


def test_a_missing_setting_stops_startup_on_render(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
        deps.setting("DATABASE_URL", "postgresql://local")


def test_database_queries_time_out() -> None:
    with deps.engine.connect() as connection:
        timeout = connection.execute(text("SHOW statement_timeout")).scalar()
    assert timeout == "2s"
