import io
import json
import logging
import os
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import docx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import deps, extract, logs, parse, quota
from app.main import app
from app.parse import Provider

pytestmark = pytest.mark.usefixtures("clean")
client = TestClient(app)

PRIMARY = Provider("primary", "https://primary.test/v1", "key-1", "model-1", 1, 2)
FAILOVER = Provider("failover", "https://failover.test/v1", "key-2", "model-2", 3, 4)
FIXTURE = Path(__file__).parents[2] / "packages/schema/fixtures/profile.v1.json"

# What a model sends back: nulls for what the CV does not say, no ids.
REPLY: dict[str, Any] = {
    "personal": {"firstName": "Jane", "lastName": "Example", "email": None},
    "summary": None,
    "work": [
        {
            "company": "Acme",
            "title": "Engineer",
            "start": {"year": 2020, "month": 3},
            "end": None,
            "current": True,
            "bullets": ["Built the thing", "  "],
            "location": "",
        }
    ],
    "projects": [{"name": "Side app", "technologies": ["Rust"]}],
}


def cv(*lines: str) -> bytes:
    document = docx.Document()
    for line in lines:
        document.add_paragraph(line)
    out = io.BytesIO()
    document.save(out)
    return out.getvalue()


CV = cv(
    "Jane Example",
    "Engineer, Acme, March 2020 to present",
    "Built the thing that made the other thing faster for everyone, twice over.",
    "Side app: a weekend project in Rust.",
)


class Fake:
    """Stands in for urlopen. Each provider URL answers from its own list of
    replies in turn: a dict is a JSON reply body, an exception is raised."""

    def __init__(self, **replies: list[Any]) -> None:
        self.replies = replies
        self.calls: list[tuple[str, dict[str, str], dict[str, Any]]] = []

    def __call__(self, request: urllib.request.Request, timeout: float) -> io.BytesIO:
        url = request.full_url
        assert isinstance(request.data, bytes)
        self.calls.append((url, dict(request.header_items()), json.loads(request.data)))
        reply = self.replies[url.split("//")[1].split(".")[0]].pop(0)
        if isinstance(reply, Exception):
            raise reply
        return io.BytesIO(json.dumps(reply).encode())


def answer(content: Any) -> dict[str, Any]:
    body = content if isinstance(content, str) else json.dumps(content)
    return {
        "choices": [{"message": {"content": body}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
    }


def down(status: int = 500) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://x.test", status, "down", None, None)  # type: ignore[arg-type]


@pytest.fixture
def llm(monkeypatch: pytest.MonkeyPatch) -> Callable[..., Fake]:
    monkeypatch.setattr(parse, "PROVIDERS", [PRIMARY, FAILOVER])

    def use(**replies: list[Any]) -> Fake:
        fake = Fake(**replies)
        monkeypatch.setattr(urllib.request, "urlopen", fake)
        return fake

    return use


def new_install() -> dict[str, str]:
    issued = client.post("/v1/installs").json()
    return {"Authorization": f"Bearer {issued['key']}"}


def post(auth: dict[str, str], data: bytes = CV) -> Any:
    return client.post("/v1/parse", content=data, headers=auth)


def parses_left(auth: dict[str, str]) -> int:
    return int(client.get("/v1/status", headers=auth).json()["parses_left"])


def test_returns_a_checked_profile_and_uses_one_parse(llm: Callable[..., Fake]) -> None:
    fake = llm(primary=[answer(REPLY)])
    auth = new_install()
    response = post(auth)
    assert response.status_code == 200
    profile = response.json()["profile"]
    assert profile["schemaVersion"] == 1
    assert profile["personal"] == {"firstName": "Jane", "lastName": "Example"}
    work = profile["work"][0]
    # Nulls and blanks are dropped, ids are ours.
    assert work["bullets"] == ["Built the thing"]
    assert "end" not in work and "location" not in work
    assert uuid.UUID(work["id"]) and uuid.UUID(profile["projects"][0]["id"])
    assert parses_left(auth) == quota.PARSES_PER_DAY - 1

    url, headers, body = fake.calls[0]
    assert url == "https://primary.test/v1/chat/completions"
    assert headers["Authorization"] == "Bearer key-1"
    assert body["model"] == "model-1"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert "Side app: a weekend project in Rust." in body["messages"][1]["content"]


def test_fails_over_when_the_primary_is_down(llm: Callable[..., Fake]) -> None:
    fake = llm(primary=[down()], failover=[answer(REPLY)])
    auth = new_install()
    assert post(auth).status_code == 200
    assert [call[2]["model"] for call in fake.calls] == ["model-1", "model-2"]
    assert parses_left(auth) == quota.PARSES_PER_DAY - 1


@pytest.mark.parametrize(
    "failure",
    [down(500), down(429), down(401), TimeoutError(), urllib.error.URLError("dns")],
)
def test_both_down_says_so_and_gives_the_parse_back(
    llm: Callable[..., Fake], failure: Exception
) -> None:
    llm(primary=[failure], failover=[{"no": "choices"}])
    auth = new_install()
    response = post(auth)
    assert response.status_code == 503
    assert response.json()["detail"] == parse.UNAVAILABLE
    assert parses_left(auth) == quota.PARSES_PER_DAY


def spent() -> int:
    return quota.spent(datetime.now(UTC))


def test_asks_again_once_with_the_problems_when_the_output_is_invalid(
    llm: Callable[..., Fake],
) -> None:
    ended_first = {"work": [{**REPLY["work"][0], "end": {"year": 2019}}]}
    fake = llm(primary=[answer(ended_first), answer(REPLY)])
    assert post(new_install()).status_code == 200
    # Both calls are paid for: 100 tokens in at $1/M, 50 out at $2/M, twice.
    assert spent() == 2 * (100 * 1 + 50 * 2)
    retry = fake.calls[1][2]["messages"]
    assert retry[-2]["role"] == "assistant"
    assert "work[0].end" in retry[-1]["content"]
    assert "current entry cannot have an end date" in retry[-1]["content"]


def test_gives_up_after_two_invalid_answers(llm: Callable[..., Fake]) -> None:
    fake = llm(primary=[answer("not json"), answer({"work": [{"company": 5}]})])
    auth = new_install()
    response = post(auth)
    assert response.status_code == 502
    assert response.json()["detail"] == parse.FAILED
    assert len(fake.calls) == 2  # The failover is for outages, not bad answers.
    assert parses_left(auth) == quota.PARSES_PER_DAY


def test_without_usage_a_call_costs_the_most_it_could(
    llm: Callable[..., Fake], caplog: pytest.LogCaptureFixture
) -> None:
    llm(primary=[{**answer(REPLY), "usage": None}])
    assert post(new_install()).status_code == 200
    assert spent() > parse.MAX_TOKENS * 2
    assert "llm usage missing" in caplog.messages


def test_pauses_at_the_daily_spend_cap_until_midnight_utc(
    llm: Callable[..., Fake],
) -> None:
    fake = llm()
    auth = new_install()
    quota.add_spend(quota.SPEND_CAP)
    assert client.get("/v1/status", headers=auth).json()["parsing_available"] is False
    response = post(auth)
    assert response.status_code == 503
    assert response.json()["detail"] == parse.PAUSED
    now = datetime.now(UTC)
    wait = int(response.headers["Retry-After"])
    assert abs(wait - (quota.midnight(now) - now).total_seconds()) < 5
    assert not fake.calls
    assert parses_left(auth) == quota.PARSES_PER_DAY


def test_an_unreadable_file_uses_no_parse(llm: Callable[..., Fake]) -> None:
    fake = llm()
    auth = new_install()
    response = post(auth, b"just some text")
    assert response.status_code == 422
    assert response.json()["detail"] == extract.NOT_SUPPORTED
    assert not fake.calls
    assert parses_left(auth) == quota.PARSES_PER_DAY


def test_refuses_files_over_the_limit(llm: Callable[..., Fake]) -> None:
    response = post(new_install(), b"%PDF-" + b"x" * extract.MAX_BYTES)
    assert response.status_code == 413
    assert response.json()["detail"] == extract.TOO_BIG


def test_refuses_without_quota_before_calling_the_model(
    llm: Callable[..., Fake],
) -> None:
    fake = llm(primary=[answer(REPLY)] * quota.PARSES_PER_DAY)
    auth = new_install()
    for _ in range(quota.PARSES_PER_DAY):
        assert post(auth).status_code == 200
    response = post(auth)
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0
    assert len(fake.calls) == quota.PARSES_PER_DAY


def test_needs_a_key(llm: Callable[..., Fake]) -> None:
    assert client.post("/v1/parse", content=CV).status_code == 401


def test_unavailable_when_no_provider_is_set_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(parse, "PROVIDERS", [])
    response = post(new_install())
    assert response.status_code == 503
    assert response.json()["detail"] == parse.UNAVAILABLE


def test_a_provider_needs_its_key_model_and_prices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_URL", "https://primary.test/v1/")
    monkeypatch.setenv("LLM_KEY", "k")
    monkeypatch.setenv("LLM_MODEL", "m")
    monkeypatch.setenv("LLM_INPUT_PRICE", "0.18")
    monkeypatch.setenv("LLM_OUTPUT_PRICE", "0.7")
    monkeypatch.setenv("LLM_FAILOVER_URL", "https://failover.test/v1")
    monkeypatch.setenv("LLM_FAILOVER_KEY", "k2")
    monkeypatch.setenv("LLM_FAILOVER_MODEL", "m2")
    with pytest.raises(RuntimeError, match="LLM_FAILOVER_URL needs"):
        parse.providers()
    monkeypatch.delenv("LLM_FAILOVER_URL")
    assert parse.providers() == [
        Provider("primary", "https://primary.test/v1", "k", "m", 0.18, 0.7)
    ]


def test_the_llm_schema_is_strict_and_leaves_ids_to_us() -> None:
    def walk(node: Any) -> None:
        if isinstance(node, dict):
            assert "$ref" not in node and "pattern" not in node
            if "properties" in node:
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
                assert not {"id", "schemaVersion"} & set(node["properties"])
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(parse.LLM_SCHEMA)
    # Lists are always sent; an optional single value may be null.
    assert parse.LLM_SCHEMA["properties"]["summary"]["anyOf"][1] == {"type": "null"}


def test_the_llm_schema_refuses_keywords_it_does_not_know() -> None:
    with pytest.raises(ValueError, match="oneOf"):
        parse.for_llm({"type": "object", "properties": {"a": {"oneOf": []}}}, {})


def test_the_frozen_profile_round_trips_without_its_ids() -> None:
    profile = json.loads(FIXTURE.read_text())

    def strip(node: Any) -> Any:
        if isinstance(node, dict):
            return {k: strip(v) for k, v in node.items() if k != "id"}
        if isinstance(node, list):
            return [strip(v) for v in node]
        return node

    rebuilt = parse.to_profile(strip(profile)).model_dump(
        mode="json", exclude_unset=True
    )
    assert strip(rebuilt) == strip(profile)


def test_canary_never_leaves_the_request(
    llm: Callable[..., Fake],
    caplog: pytest.LogCaptureFixture,
    capfd: pytest.CaptureFixture[str],
) -> None:
    marker = f"CANARY-{uuid.uuid4().hex}"
    file = cv("Jane Example", f"Engineer at {marker}, 2020 to present", "x" * 120)
    echoed = {"work": [{"company": marker, "title": "Engineer"}]}
    fake = llm(
        primary=[answer(echoed), answer("bad"), answer({"bad": marker}), down()],
        failover=[down()],
    )
    caplog.set_level(logging.DEBUG)
    started = time.time()
    auth = new_install()
    # Success, invalid output twice, and both providers down.
    assert [post(auth, file).status_code for _ in range(3)] == [200, 502, 503]
    # The marker really went through: to the model, and back in the profile.
    assert marker in fake.calls[0][2]["messages"][1]["content"]

    formatter = logs.JsonFormatter()
    written = "".join(formatter.format(r) for r in caplog.records)
    out, err = capfd.readouterr()
    assert written and marker not in written + out + err

    with deps.engine.connect() as connection:
        tables = connection.scalars(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        ).all()
        for table in tables:  # names from pg_tables, not input
            query = f'SELECT row_to_json(t)::text FROM "{table}" t'  # noqa: S608
            rows = connection.scalars(text(query))
            assert all(marker not in row for row in rows)
    for key in deps.cache.scan_iter():
        assert marker.encode() not in key + (deps.cache.dump(key) or b"")

    for folder in {Path(tempfile.gettempdir()), Path.cwd()}:
        for root, _, names in os.walk(folder):
            for name in names:
                path = Path(root, name)
                try:
                    if path.stat().st_mtime >= started:
                        assert marker.encode() not in path.read_bytes()
                except OSError:
                    continue  # gone or unreadable: not ours
