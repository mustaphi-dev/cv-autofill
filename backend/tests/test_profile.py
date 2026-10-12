import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.profile import Profile

FIXTURES = Path(__file__).parents[2] / "packages/schema/fixtures"
# The extension runs the same cases against Zod (packages/schema/test/cases.test.ts).
CASES: list[dict[str, Any]] = json.loads((FIXTURES / "cases.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_shared_case(case: dict[str, Any]) -> None:
    raw = json.dumps(case["profile"])
    if case["valid"]:
        Profile.model_validate_json(raw)
        return
    with pytest.raises(ValidationError) as error:
        Profile.model_validate_json(raw)
    if "rule" in case:
        assert case["rule"] in str(error.value)


def test_frozen_v1_profile_loads() -> None:
    Profile.model_validate_json((FIXTURES / "profile.v1.json").read_text())


def test_text_is_trimmed_like_zod() -> None:
    case = next(c for c in CASES if c["name"].startswith("text with spaces"))
    work = Profile.model_validate_json(json.dumps(case["profile"])).work
    assert work is not None
    assert work[0].company == "a" * 300
    assert work[0].bullets == ["Led the rewrite"]


def test_rule_errors_say_where() -> None:
    case = next(c for c in CASES if c["name"] == "end before start")
    with pytest.raises(ValidationError, match=r"projects\[0\]\.end: End date"):
        Profile.model_validate_json(json.dumps(case["profile"]))
