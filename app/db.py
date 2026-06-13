from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Song

DEFAULT_SEED = Path(__file__).resolve().parent.parent / "data" / "default_songs.json"

_engine = None


def make_engine(database_path: str):
    return create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )


def init_db(engine) -> None:
    SQLModel.metadata.create_all(engine)


def seed_if_empty(engine, seed_file: Path = DEFAULT_SEED) -> None:
    with Session(engine) as session:
        if session.exec(select(Song).limit(1)).first() is not None:
            return
        data = json.loads(Path(seed_file).read_text(encoding="utf-8"))
        for item in data:
            session.add(Song(author=item["author"].strip(), title=item["title"].strip()))
        session.commit()


def set_engine(engine) -> None:
    global _engine
    _engine = engine


def get_session() -> Iterator[Session]:
    assert _engine is not None, "engine not initialized"
    with Session(_engine) as session:
        yield session
