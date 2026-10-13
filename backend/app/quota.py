import uuid
from datetime import UTC, datetime, time, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import deps, limits
from app.installs import CurrentInstall

# Parsing costs money. The day is the UTC day: one reset time that is easy to
# show, and a counter that expires by itself.
PARSES_PER_DAY = 3

router = APIRouter()


def midnight(now: datetime) -> datetime:
    return datetime.combine(now.date() + timedelta(days=1), time(), UTC)


def counter(install_id: uuid.UUID, now: datetime) -> str:
    return f"quota:parse:{install_id}:{now.date()}"


def charge_parse(install_id: uuid.UUID) -> str:
    """Takes one of today's parses before the parse starts, so two parallel
    uploads cannot share the last one. Returns the counter for refund_parse."""
    now = datetime.now(UTC)
    key = counter(install_id, now)
    seconds = int((midnight(now) - now).total_seconds()) + 1
    try:
        limits.hit(key, PARSES_PER_DAY, seconds, "No CV parses left today.")
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


class Status(BaseModel):
    parses_left: int
    parses_per_day: int
    resets_at: datetime


@router.get("/v1/status")
def status(install: CurrentInstall) -> Status:
    now = datetime.now(UTC)
    used = int(deps.cache.get(counter(install.id, now)) or 0)
    return Status(
        parses_left=max(PARSES_PER_DAY - used, 0),
        parses_per_day=PARSES_PER_DAY,
        resets_at=midnight(now),
    )
