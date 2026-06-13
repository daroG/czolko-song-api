import pytest

from app.config import Settings


def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("EDIT_SECRET", "code123")
    monkeypatch.setenv("SESSION_SECRET", "sign123")
    monkeypatch.setenv("DATABASE_PATH", "/tmp/x.db")
    s = Settings.from_env()
    assert s.edit_secret == "code123"
    assert s.session_secret == "sign123"
    assert s.database_path == "/tmp/x.db"


def test_settings_defaults_database_path(monkeypatch):
    monkeypatch.setenv("EDIT_SECRET", "c")
    monkeypatch.setenv("SESSION_SECRET", "s")
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    s = Settings.from_env()
    assert s.database_path == "./songs.db"


def test_settings_missing_required_raises(monkeypatch):
    monkeypatch.delenv("EDIT_SECRET", raising=False)
    monkeypatch.setenv("SESSION_SECRET", "s")
    with pytest.raises(RuntimeError, match="EDIT_SECRET"):
        Settings.from_env()
