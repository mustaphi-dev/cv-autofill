import json
import logging
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.logs import JsonFormatter
from app.main import app

MARKER = "CANARY-7f3c9e"


@app.post("/test/echo/{item_id}")
def echo(item_id: str, body: dict[str, str]) -> dict[str, str]:
    logging.getLogger("app.test").info("handled")
    return body


@app.get("/test/boom")
def boom(q: str) -> None:
    raise ValueError(q)


client = TestClient(app)


def entries(caplog: pytest.LogCaptureFixture) -> list[dict[str, Any]]:
    return [json.loads(JsonFormatter().format(r)) for r in caplog.records]


def test_healthz() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_logs_one_json_line_per_request(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    response = client.get("/healthz")
    [entry] = [e for e in entries(caplog) if e["message"] == "request"]
    assert entry["method"] == "GET"
    assert entry["route"] == "/healthz"
    assert entry["status"] == 200
    assert entry["request_id"] == response.headers["X-Request-ID"]


def test_request_ids_are_always_new() -> None:
    a = client.get("/healthz", headers={"X-Request-ID": "chosen-by-caller"})
    b = client.get("/healthz")
    assert a.headers["X-Request-ID"] != "chosen-by-caller"
    assert a.headers["X-Request-ID"] != b.headers["X-Request-ID"]
    uuid.UUID(a.headers["X-Request-ID"])


def test_request_data_never_reaches_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    ok = client.post(
        f"/test/echo/{MARKER}?q={MARKER}",
        json={"cv": MARKER},
        headers={"X-Note": MARKER},
    )
    invalid = client.post("/test/echo/x", json=[MARKER])
    client.get(f"/{MARKER}")
    assert (ok.status_code, invalid.status_code) == (200, 422)

    logged = entries(caplog)
    assert [e["route"] for e in logged if e["message"] == "request"] == [
        "/test/echo/{item_id}",
        "/test/echo/{item_id}",
        "unmatched",
    ]
    # Logs from inside a handler carry the request ID.
    [handled] = [e for e in logged if e["message"] == "handled"]
    assert handled["request_id"] == ok.headers["X-Request-ID"]
    assert MARKER not in json.dumps(logged)


def test_unhandled_errors_keep_the_request_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    response = client.get(f"/test/boom?q={MARKER}")
    assert response.status_code == 500
    rid = response.headers["X-Request-ID"]

    logged = entries(caplog)
    [error] = [e for e in logged if e["message"] == "unhandled"]
    assert error["request_id"] == rid
    assert error["exception"] == "ValueError"
    [request] = [e for e in logged if e["message"] == "request"]
    assert (request["request_id"], request["status"]) == (rid, 500)
    assert MARKER not in json.dumps(logged)


def test_exceptions_are_logged_by_type_only(
    caplog: pytest.LogCaptureFixture,
) -> None:
    try:
        raise ValueError(MARKER)
    except ValueError:
        logging.getLogger("app.test").exception("failed")
    [entry] = entries(caplog)
    assert entry["exception"] == "ValueError"
    assert MARKER not in json.dumps(entry)
