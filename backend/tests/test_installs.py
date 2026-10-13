import hashlib
import json
import uuid

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from app import deps, installs
from app.admin import revoke
from app.logs import JsonFormatter
from app.main import app
from app.models import Install

pytestmark = pytest.mark.usefixtures("clean")
client = TestClient(app)


def issue(ip: str = "203.0.113.1") -> dict[str, str]:
    response = client.post("/v1/installs", headers={"X-Forwarded-For": ip})
    assert response.status_code == 201, response.text
    body: dict[str, str] = response.json()
    return body


def rotate(key: str) -> int:
    response = client.post(
        "/v1/installs/rotate", headers={"Authorization": f"Bearer {key}"}
    )
    return response.status_code


@pytest.fixture(autouse=True)
def behind_render_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(installs, "TRUSTED_PROXY_HOPS", 1)


def test_issues_a_key_and_stores_only_its_hash() -> None:
    issued = issue()
    assert issued["key"].startswith("cvk_")
    assert len(issued["key"]) > 40
    with deps.engine.connect() as connection:
        [row] = connection.execute(select(Install.__table__)).all()
    assert str(row.id) == issued["install_id"]
    assert row.key_hash == hashlib.sha256(issued["key"].encode()).digest()
    assert row.revoked_at is None
    # Nothing else about the install, or the person, is kept.
    assert set(row._fields) == {"id", "key_hash", "created_at", "revoked_at"}


def test_rotating_replaces_the_key_at_once() -> None:
    old = issue()["key"]
    response = client.post(
        "/v1/installs/rotate", headers={"Authorization": f"Bearer {old}"}
    )
    assert response.status_code == 200
    new = response.json()["key"]
    assert new != old
    assert rotate(old) == 401
    assert rotate(new) == 200


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer cvk_made-up"}, {"Authorization": "Basic abc"}],
    ids=["missing", "unknown", "not bearer"],
)
def test_rejects_requests_without_a_valid_key(headers: dict[str, str]) -> None:
    response = client.post("/v1/installs/rotate", headers=headers)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_a_revoked_key_stops_working() -> None:
    issued = issue()
    install_id = uuid.UUID(issued["install_id"])
    assert revoke(install_id) is True
    assert rotate(issued["key"]) == 401
    assert revoke(install_id) is False
    assert revoke(uuid.uuid4()) is False


def test_limits_new_installs_per_ip() -> None:
    for _ in range(installs.PER_IP_PER_HOUR):
        issue("203.0.113.1")
    response = client.post("/v1/installs", headers={"X-Forwarded-For": "203.0.113.1"})
    assert response.status_code == 429
    assert 0 < int(response.headers["Retry-After"]) <= 3600
    issue("203.0.113.2")  # Another IP is unaffected.


def test_a_forged_leftmost_ip_does_not_get_around_the_limit() -> None:
    # Render appends the real client IP; whatever the client sent is on the left.
    for i in range(installs.PER_IP_PER_HOUR):
        issue(f"10.0.0.{i}, 203.0.113.1")
    response = client.post(
        "/v1/installs", headers={"X-Forwarded-For": "10.9.9.9, 203.0.113.1"}
    )
    assert response.status_code == 429


def test_caps_new_installs_overall(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(installs, "ALL_PER_HOUR", 2)
    issue("203.0.113.1")
    issue("203.0.113.2")
    response = client.post("/v1/installs", headers={"X-Forwarded-For": "203.0.113.3"})
    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_keys_and_ips_never_reach_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("DEBUG")
    first = issue("198.51.100.77")["key"]
    second = client.post(
        "/v1/installs/rotate", headers={"Authorization": f"Bearer {first}"}
    ).json()["key"]
    logged = json.dumps([JsonFormatter().format(r) for r in caplog.records])
    for secret in (first, second, "198.51.100.77"):
        assert secret not in logged


def test_migrations_run_down_and_up() -> None:
    alembic = Config("alembic.ini")
    command.downgrade(alembic, "base")
    assert "installs" not in inspect(deps.engine).get_table_names()
    command.upgrade(alembic, "head")
    assert "installs" in inspect(deps.engine).get_table_names()
