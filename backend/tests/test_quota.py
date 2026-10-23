import logging
import uuid
from datetime import UTC, datetime

import pytest
import redis
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import deps, installs, quota
from app.main import app

pytestmark = pytest.mark.usefixtures("clean")
client = TestClient(app)


def new_install() -> tuple[uuid.UUID, dict[str, str]]:
    issued = client.post("/v1/installs").json()
    return uuid.UUID(issued["install_id"]), {"Authorization": f"Bearer {issued['key']}"}


def test_status_shows_a_full_quota_for_a_new_install() -> None:
    _, auth = new_install()
    response = client.get("/v1/status", headers=auth)
    assert response.status_code == 200
    body = response.json()
    assert body["parses_left"] == body["parses_per_day"] == quota.PARSES_PER_DAY
    # UTC midnight, in a form the extension can turn into local time.
    midnight = quota.midnight(datetime.now(UTC))
    assert body["resets_at"] == midnight.strftime("%Y-%m-%dT00:00:00Z")
    assert body["parsing_available"] is True


def test_status_needs_a_key() -> None:
    assert client.get("/v1/status").status_code == 401


def test_charging_and_refunding_show_in_status() -> None:
    install_id, auth = new_install()
    key = quota.charge_parse(install_id)
    assert client.get("/v1/status", headers=auth).json()["parses_left"] == 2
    quota.refund_parse(key)
    assert client.get("/v1/status", headers=auth).json()["parses_left"] == 3


def test_refuses_a_parse_over_the_daily_quota_until_midnight_utc() -> None:
    install_id, auth = new_install()
    for _ in range(quota.PARSES_PER_DAY):
        quota.charge_parse(install_id)
    with pytest.raises(HTTPException) as refused:
        quota.charge_parse(install_id)
    assert refused.value.status_code == 429
    assert refused.value.headers
    wait = int(refused.value.headers["Retry-After"])
    now = datetime.now(UTC)
    assert abs(wait - (quota.midnight(now) - now).total_seconds()) < 5
    # The refused attempt used nothing, so a refund frees exactly one parse.
    assert client.get("/v1/status", headers=auth).json()["parses_left"] == 0
    quota.refund_parse(quota.counter(install_id, now))
    assert client.get("/v1/status", headers=auth).json()["parses_left"] == 1


def test_spend_alerts_fire_once_each_as_the_total_crosses_them(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def alerts() -> list[tuple[int, int]]:
        return [(r.percent, r.levelno) for r in caplog.records]  # type: ignore[attr-defined]

    percent = quota.SPEND_CAP // 100
    quota.add_spend(49 * percent)
    assert alerts() == []
    quota.add_spend(1 * percent)  # Exactly at 50%.
    assert alerts() == [(50, logging.WARNING)]
    quota.add_spend(40 * percent)  # Jumps past 80% only.
    quota.add_spend(5 * percent)
    quota.add_spend(10 * percent)
    assert alerts() == [
        (50, logging.WARNING),
        (80, logging.ERROR),
        (100, logging.ERROR),
    ]


def test_rate_limits_each_install(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(installs, "PER_INSTALL_PER_MINUTE", 5)
    _, auth = new_install()
    for _ in range(5):
        assert client.get("/v1/status", headers=auth).status_code == 200
    response = client.get("/v1/status", headers=auth)
    assert response.status_code == 429
    assert 0 < int(response.headers["Retry-After"]) <= 60
    _, other = new_install()  # Another install is unaffected.
    assert client.get("/v1/status", headers=other).status_code == 200


def test_refuses_with_503_when_valkey_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    _, auth = new_install()
    monkeypatch.setattr(deps, "cache", redis.Redis.from_url("redis://127.0.0.1:1"))
    for response in (
        client.post("/v1/installs"),
        client.post("/v1/installs/rotate", headers=auth),
        client.get("/v1/status", headers=auth),
    ):
        assert response.status_code == 503
        assert response.headers["Retry-After"] == "60"
        assert response.json() == {
            "detail": "Temporarily unavailable. Try again shortly."
        }
