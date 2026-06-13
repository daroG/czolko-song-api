import json

import pytest
from fastapi.testclient import TestClient

from app.app_factory import create_app
from app.config import Settings


@pytest.fixture
def seed_file(tmp_path):
    data = [{"author": "Perfect", "title": "Autobiografia"},
            {"author": "Bajm", "title": "Biała armia"}]
    p = tmp_path / "seed.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


@pytest.fixture
def client(tmp_path, seed_file, monkeypatch):
    # Point the default seed at our fixture file.
    import app.db as db
    monkeypatch.setattr(db, "DEFAULT_SEED", seed_file)
    settings = Settings(
        edit_secret="testcode",
        session_secret="testsign",
        database_path=str(tmp_path / "test.db"),
    )
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_client(client):
    r = client.post("/login", data={"code": "testcode"}, follow_redirects=False)
    assert r.status_code == 303
    return client
