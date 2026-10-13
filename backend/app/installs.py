import hashlib
import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import limits
from app.deps import get_session, setting
from app.models import Install

# Sign-up limits. The overall cap is the real bound on cost: IPs are cheap to
# rotate. Both are counted in Valkey and expire with the hour.
PER_IP_PER_HOUR = 5
ALL_PER_HOUR = 300
# Required on Render: unset, every client would look like the proxy and share
# one per-IP counter.
TRUSTED_PROXY_HOPS = int(setting("TRUSTED_PROXY_HOPS", "0"))

router = APIRouter(prefix="/v1/installs")
DbSession = Annotated[Session, Depends(get_session)]


def digest(key: str) -> bytes:
    # A 256-bit random key cannot be guessed or reversed from its SHA-256, so
    # a slow password hash would add cost and no safety.
    return hashlib.sha256(key.encode()).digest()


def client_ip(request: Request) -> str:
    """Render's proxy appends to X-Forwarded-For, so the leftmost entries can
    be forged by the client. Count TRUSTED_PROXY_HOPS entries from the right
    (0 locally, where there is no proxy)."""
    hops = TRUSTED_PROXY_HOPS
    forwarded = request.headers.get("X-Forwarded-For", "").split(",")
    entries = [e.strip() for e in forwarded if e.strip()]
    if hops and len(entries) >= hops:
        return entries[-hops]
    return request.client.host if request.client else "unknown"


def current_install(
    session: DbSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))
    ],
) -> Install:
    install = credentials and session.scalar(
        select(Install).where(
            Install.key_hash == digest(credentials.credentials),
            Install.revoked_at.is_(None),
        )
    )
    if not install:
        raise HTTPException(
            401, "Missing or invalid install key", {"WWW-Authenticate": "Bearer"}
        )
    return install


class Issued(BaseModel):
    install_id: uuid.UUID
    key: str


def issue_key(install: Install) -> Issued:
    key = "cvk_" + secrets.token_urlsafe(32)
    install.key_hash = digest(key)
    return Issued(install_id=install.id, key=key)


@router.post("", status_code=201)
def create(request: Request, session: DbSession) -> Issued:
    # The counter is named by a hash of the IP, never the IP itself, and
    # expires with the hour. Nothing about the IP reaches Postgres or logs.
    ip = hashlib.sha256(client_ip(request).encode()).hexdigest()
    for counter, limit in (
        (f"installs:ip:{ip}", PER_IP_PER_HOUR),
        ("installs:all", ALL_PER_HOUR),
    ):
        wait = limits.hit(counter, limit, 3600)
        if wait is not None:
            raise HTTPException(
                429,
                "Too many new installs. Try again later.",
                {"Retry-After": str(wait)},
            )
    install = Install(id=uuid.uuid4())
    issued = issue_key(install)
    session.add(install)
    session.commit()
    return issued


@router.post("/rotate")
def rotate(
    install: Annotated[Install, Depends(current_install)], session: DbSession
) -> Issued:
    """A new key for this install. The old one stops working at once."""
    issued = issue_key(install)
    session.commit()
    return issued
