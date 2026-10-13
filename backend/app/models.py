import uuid
from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Model(DeclarativeBase):
    pass


class Install(Model):
    """One browser install. Holds nothing about the user: only the SHA-256 of
    its key (the key itself is shown once, at issue)."""

    __tablename__ = "installs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    key_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
