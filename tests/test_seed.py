import json
from pathlib import Path

from sqlmodel import Session, create_engine, select

from app.db import init_db, seed_if_empty
from app.models import Song


def _engine(tmp_path: Path):
    return create_engine(f"sqlite:///{tmp_path/'t.db'}")


def test_seed_populates_empty_db(tmp_path):
    eng = _engine(tmp_path)
    init_db(eng)
    seed_data = [{"author": "A", "title": "T1"}, {"author": "B", "title": "T2"}]
    seed_file = tmp_path / "seed.json"
    seed_file.write_text(json.dumps(seed_data), encoding="utf-8")
    seed_if_empty(eng, seed_file)
    with Session(eng) as s:
        rows = s.exec(select(Song)).all()
    assert {(r.author, r.title) for r in rows} == {("A", "T1"), ("B", "T2")}


def test_seed_is_noop_when_not_empty(tmp_path):
    eng = _engine(tmp_path)
    init_db(eng)
    with Session(eng) as s:
        s.add(Song(author="X", title="Y"))
        s.commit()
    seed_file = tmp_path / "seed.json"
    seed_file.write_text('[{"author":"A","title":"T"}]', encoding="utf-8")
    seed_if_empty(eng, seed_file)
    with Session(eng) as s:
        rows = s.exec(select(Song)).all()
    assert len(rows) == 1
