import logging
import uuid
from datetime import UTC, datetime, time, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import deps, limits
from app.installs import CurrentInstall

# Parsing costs money. The day is the UTC day: one reset time that is easy to
# show, and a counter that expires by itself.
PARSES_PER_DAY = 3
# All installs together. Our provider has no hard limit, so this is the one
# that stops spending: parsing pauses until midnight UTC once it is reached.
SPEND_CAP = 3_000_000  # micro-dollars a day: $3
ALERTS = ((50, logging.WARNING), (80, logging.ERROR), (100, logging.ERROR))

log = logging.getLogger(__name__)
router = APIRouter()


def midnight(now: datetime) -> datetime:
    return datetime.combine(now.date() + timedelta(days=1), time(), UTC)


def until_midnight(now: datetime) -> int:
    return int((midnight(now) - now).total_seconds()) + 1


def counter(install_id: uuid.UUID, now: datetime) -> str:
    return f"quota:parse:{install_id}:{now.date()}"


def charge_parse(install_id: uuid.UUID) -> str:
    """Takes one of today's parses before the parse starts, so two parallel
    uploads cannot share the last one. Returns the counter for refund_parse."""
    now = datetime.now(UTC)
    key = counter(install_id, now)
    try:
        limits.hit(key, PARSES_PER_DAY, until_midnight(now), "No CV parses left today.")
    except HTTPException:
        refund_parse(key)  # A refused attempt uses nothing.
        raise
    return key


def refund_parse(key: str) -> None:
    """Gives a parse back when it failed on our side. If midnight has passed,
    the old day's counter is gone: the expiry stops a stray -1 living forever."""
    pipe = deps.cache.pipeline()
    pipe.decr(key)
    pipe.expire(key, 86400, nx=True)
    pipe.execute()


def spend_key(now: datetime) -> str:
    return f"spend:{now.date()}"


def spent(now: datetime) -> int:
    return int(deps.cache.get(spend_key(now)) or 0)


def add_spend(amount: int) -> None:
    """Adds one LLM call's cost to today's total and logs each alert once,
    when the total crosses it."""
    now = datetime.now(UTC)
    pipe = deps.cache.pipeline()
    pipe.incrby(spend_key(now), amount)
    pipe.expire(spend_key(now), until_midnight(now), nx=True)
    total = pipe.execute()[0]
    for percent, level in ALERTS:
        if total - amount < SPEND_CAP * percent // 100 <= total:
            log.log(
                level,
                "llm spend alert",
                extra={"percent": percent, "spent_usd": total / 1_000_000},
            )


class Status(BaseModel):
    parses_left: int
    parses_per_day: int
    resets_at: datetime
    # False once today's spend cap is reached. On Render a provider is always
    # set up, so the cap is the only thing that turns parsing off.
    parsing_available: bool


@router.get("/v1/status")
def status(install: CurrentInstall) -> Status:
    now = datetime.now(UTC)
    used = int(deps.cache.get(counter(install.id, now)) or 0)
    return Status(
        parses_left=max(PARSES_PER_DAY - used, 0),
        parses_per_day=PARSES_PER_DAY,
        resets_at=midnight(now),
        parsing_available=spent(now) < SPEND_CAP,
    )
