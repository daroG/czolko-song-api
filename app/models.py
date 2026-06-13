from __future__ import annotations

from datetime import datetime, timezone

from pydantic import field_validator
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Song(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    author: str
    title: str
    created_at: datetime = Field(default_factory=_utcnow)


class SongIn(SQLModel):
    author: str
    title: str

    @field_validator("author", "title")
    @classmethod
    def _trim_nonempty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be empty")
        return v


class SongPublic(SQLModel):
    author: str
    title: str


class SongOut(SongPublic):
    id: int
