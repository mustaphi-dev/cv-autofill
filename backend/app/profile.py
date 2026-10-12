from typing import Protocol, Self

from pydantic import model_validator

from app.profile_v1 import ProfileV1


class YearMonth(Protocol):
    # The schema inlines its date type per field (Start, End, IssueDate…).
    @property
    def year(self) -> int: ...
    @property
    def month(self) -> int | None: ...


def not_before(later: YearMonth, earlier: YearMonth) -> bool:
    """Compares by month when both dates have one, otherwise by year."""
    if later.year != earlier.year:
        return later.year > earlier.year
    return (later.month or 12) >= (earlier.month or 1)


DATE_ORDER = [
    ("start", "end", "End date is before start date"),
    ("issueDate", "expiryDate", "Expiry date is before issue date"),
]


class Profile(ProfileV1):
    """The profile plus the rules JSON Schema cannot carry. Each mirrors a
    Zod refine in packages/schema/src/index.ts, and the shared cases in
    packages/schema/fixtures/cases.json keep the two in step."""

    @model_validator(mode="after")
    def rules(self) -> Self:
        problems: list[str] = []
        ids: list[str] = []
        for section in type(self).model_fields:
            entries = getattr(self, section)
            if not isinstance(entries, list):
                continue
            for i, entry in enumerate(entries):
                at = f"{section}[{i}]"
                ids.append(entry.id)
                if getattr(entry, "current", None) and getattr(entry, "end", None):
                    problems.append(
                        f"{at}.end: A current entry cannot have an end date"
                    )
                for first, then, message in DATE_ORDER:
                    a, b = getattr(entry, first, None), getattr(entry, then, None)
                    if a and b and not not_before(b, a):
                        problems.append(f"{at}.{then}: {message}")
                if getattr(entry, "kind", None) == "other" and not entry.label:
                    problems.append(f"{at}.label: A link of kind 'other' needs a label")
        if len(set(ids)) != len(ids):
            problems.append("Two entries share the same id")
        if problems:
            raise ValueError("; ".join(problems))
        return self
