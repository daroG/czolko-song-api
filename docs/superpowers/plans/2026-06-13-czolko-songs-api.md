# czolko-songs-api Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI service that serves the Czołko song list publicly (game-compatible `[{author,title}]` JSON) and lets a single authenticated editor manage it via a web UI + JSON API, seeded from the app's bundled songs.

**Architecture:** FastAPI app factory with SQLModel over a single SQLite `Song` table. Public read endpoints return the game-compatible shape; editor endpoints are gated by a signed session cookie (Starlette `SessionMiddleware`) whose login compares against `EDIT_SECRET`. Server-rendered Jinja2 pages + vanilla JS call the JSON API. On startup the DB is created and, if empty, seeded from a checked-in copy of the app's `assets/songs.json`. Binds to `::` for IPv6/dual-stack.

**Tech Stack:** Python 3.11+, `uv`, FastAPI, uvicorn, SQLModel, Jinja2, itsdangerous, pytest, httpx, ruff.

**Constraint:** Do NOT modify the React Native game code in this work. Repointing the app's `SONGS_JSON_URL` is a documented follow-up only.

---

## File Structure

```
czolko-songs-api/
  app/
    __init__.py        # exports create_app
    main.py            # app = create_app()
    app_factory.py     # create_app(): middleware, routers, startup seed
    __main__.py        # python -m app -> uvicorn host "::"
    config.py          # Settings from env, fail-fast
    db.py              # engine, get_session dep, init_db + seed_if_empty
    models.py          # Song (table) + SongIn / SongOut / SongPublic schemas
    auth.py            # is_authenticated, require_auth (API 401)
    routes/
      __init__.py
      public.py        # GET /songs.json, /api/songs, /healthz
      editor.py        # POST/PUT/DELETE /api/songs (auth)
      web.py           # GET /login, POST /login, POST /logout, GET /
    templates/
      base.html
      login.html
      editor.html
    static/
      app.js
      styles.css
  data/
    default_songs.json # copy of app assets/songs.json (178 songs)
  tests/
    conftest.py
    test_public.py
    test_auth.py
    test_crud.py
    test_seed.py
  pyproject.toml
  uv.lock
  .env.example
  .gitignore
  README.md
```

---

### Task 1: Project scaffolding (uv + ruff + deps)

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.env.example`
- Create: `app/__init__.py` (empty for now)

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "czolko-songs-api"
version = "0.1.0"
description = "Serves and edits the Czolko song list"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlmodel>=0.0.22",
    "jinja2>=3.1",
    "python-multipart>=0.0.9",
    "itsdangerous>=2.2",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "httpx>=0.27",
    "ruff>=0.6",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
addopts = "-q"
testpaths = ["tests"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]
```

- [ ] **Step 2: Write `.gitignore`**

```
__pycache__/
*.pyc
.venv/
*.db
*.db-journal
.env
.pytest_cache/
.ruff_cache/
```

- [ ] **Step 3: Write `.env.example`**

```
# Editor login code (required)
EDIT_SECRET=change-me
# Cookie signing key (required) - generate e.g. `python -c "import secrets;print(secrets.token_hex(32))"`
SESSION_SECRET=change-me-too
# SQLite file path (optional)
DATABASE_PATH=./songs.db
```

- [ ] **Step 4: Create empty `app/__init__.py`**

(Empty file; populated in Task 8.)

- [ ] **Step 5: Sync deps**

Run: `uv sync`
Expected: creates `.venv` and `uv.lock`, installs all deps, exit 0.

- [ ] **Step 6: Verify ruff runs**

Run: `uv run ruff check .`
Expected: "All checks passed!" (or no errors).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock .gitignore .env.example app/__init__.py
git commit -m "chore: scaffold uv project with ruff config and deps"
```

---

### Task 2: Configuration (fail-fast env settings)

**Files:**
- Create: `app/config.py`
- Test: `tests/test_config.py` (temporary; can stay)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL with "No module named 'app.config'".

- [ ] **Step 3: Write minimal implementation**

```python
# app/config.py
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    edit_secret: str
    session_secret: str
    database_path: str

    @classmethod
    def from_env(cls) -> "Settings":
        missing = [k for k in ("EDIT_SECRET", "SESSION_SECRET") if not os.environ.get(k)]
        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}"
            )
        return cls(
            edit_secret=os.environ["EDIT_SECRET"],
            session_secret=os.environ["SESSION_SECRET"],
            database_path=os.environ.get("DATABASE_PATH", "./songs.db"),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: add fail-fast env settings"
```

---

### Task 3: Models (Song table + schemas)

**Files:**
- Create: `app/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
import pytest
from pydantic import ValidationError
from app.models import Song, SongIn, SongPublic, SongOut


def test_songin_trims_and_requires_nonempty():
    s = SongIn(author="  Perfect ", title=" Autobiografia  ")
    assert s.author == "Perfect"
    assert s.title == "Autobiografia"


def test_songin_rejects_blank():
    with pytest.raises(ValidationError):
        SongIn(author="   ", title="x")


def test_public_shape_excludes_id():
    out = SongPublic(author="A", title="T")
    assert out.model_dump() == {"author": "A", "title": "T"}


def test_song_out_includes_id():
    out = SongOut(id=5, author="A", title="T")
    assert out.model_dump() == {"id": 5, "author": "A", "title": "T"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL with "No module named 'app.models'".

- [ ] **Step 3: Write minimal implementation**

```python
# app/models.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_models.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/test_models.py
git commit -m "feat: add Song model and request/response schemas"
```

---

### Task 4: Seed data file

**Files:**
- Create: `data/default_songs.json` (copy of the app's `assets/songs.json`)

- [ ] **Step 1: Copy the app's bundled songs into the seed file**

Run (from repo root `czolko-songs-api`):
```bash
cp "../../js/czolko-song-react-native/assets/songs.json" data/default_songs.json
```

- [ ] **Step 2: Verify it is a non-empty JSON array of {author,title}**

Run:
```bash
python -c "import json;d=json.load(open('data/default_songs.json',encoding='utf-8'));assert isinstance(d,list) and d and set(d[0])=={'author','title'};print(len(d),'songs')"
```
Expected: prints `178 songs` (or current count), exit 0.

- [ ] **Step 3: Commit**

```bash
git add data/default_songs.json
git commit -m "feat: add default song list seed (copy of app assets)"
```

---

### Task 5: Database layer (engine, session, init + seed)

**Files:**
- Create: `app/db.py`
- Test: `tests/test_seed.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_seed.py
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
    seed_file.write_text(__import__("json").dumps(seed_data), encoding="utf-8")
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_seed.py -v`
Expected: FAIL with "No module named 'app.db'".

- [ ] **Step 3: Write minimal implementation**

```python
# app/db.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_seed.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add app/db.py tests/test_seed.py
git commit -m "feat: add db engine, init and idempotent seeding"
```

---

### Task 6: Auth helpers

**Files:**
- Create: `app/auth.py`
- Test: covered via integration tests in Task 9 (test_auth.py). Add a unit test here.
- Test: `tests/test_auth_unit.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_auth_unit.py
from app.auth import verify_code


def test_verify_code_true():
    assert verify_code("secret", "secret") is True


def test_verify_code_false():
    assert verify_code("secret", "nope") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_auth_unit.py -v`
Expected: FAIL with "No module named 'app.auth'".

- [ ] **Step 3: Write minimal implementation**

```python
# app/auth.py
from __future__ import annotations

import secrets

from fastapi import HTTPException, Request, status

SESSION_KEY = "authenticated"


def verify_code(expected: str, provided: str) -> bool:
    return secrets.compare_digest(expected, provided)


def is_authenticated(request: Request) -> bool:
    return bool(request.session.get(SESSION_KEY))


def require_auth(request: Request) -> None:
    """FastAPI dependency for JSON edit endpoints: 401 when not logged in."""
    if not is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_auth_unit.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add app/auth.py tests/test_auth_unit.py
git commit -m "feat: add auth helpers (constant-time verify, session checks)"
```

---

### Task 7: Routers (public + editor API)

**Files:**
- Create: `app/routes/__init__.py` (empty)
- Create: `app/routes/public.py`
- Create: `app/routes/editor.py`
- Test: integration tests added in Tasks 9–10.

- [ ] **Step 1: Create empty `app/routes/__init__.py`**

(Empty file.)

- [ ] **Step 2: Write `app/routes/public.py`**

```python
# app/routes/public.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.models import Song, SongOut, SongPublic

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/songs.json", response_model=list[SongPublic])
def songs_json(session: Session = Depends(get_session)) -> list[Song]:
    return session.exec(select(Song).order_by(Song.id)).all()


@router.get("/api/songs", response_model=list[SongOut])
def api_songs(session: Session = Depends(get_session)) -> list[Song]:
    return session.exec(select(Song).order_by(Song.id)).all()
```

- [ ] **Step 3: Write `app/routes/editor.py`**

```python
# app/routes/editor.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.auth import require_auth
from app.db import get_session
from app.models import Song, SongIn, SongOut

router = APIRouter(prefix="/api/songs", dependencies=[Depends(require_auth)])


@router.post("", response_model=SongOut, status_code=status.HTTP_201_CREATED)
def create_song(payload: SongIn, session: Session = Depends(get_session)) -> Song:
    song = Song(author=payload.author, title=payload.title)
    session.add(song)
    session.commit()
    session.refresh(song)
    return song


@router.put("/{song_id}", response_model=SongOut)
def update_song(song_id: int, payload: SongIn, session: Session = Depends(get_session)) -> Song:
    song = session.get(Song, song_id)
    if song is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    song.author = payload.author
    song.title = payload.title
    session.add(song)
    session.commit()
    session.refresh(song)
    return song


@router.delete("/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_song(song_id: int, session: Session = Depends(get_session)) -> None:
    song = session.get(Song, song_id)
    if song is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    session.delete(song)
    session.commit()
```

- [ ] **Step 4: Run ruff to verify the new files lint**

Run: `uv run ruff check app/routes`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add app/routes
git commit -m "feat: add public and editor API routers"
```

---

### Task 8: Web pages router + templates + app factory

**Files:**
- Create: `app/routes/web.py`
- Create: `app/templates/base.html`, `login.html`, `editor.html`
- Create: `app/static/app.js`, `app/static/styles.css`
- Create: `app/app_factory.py`, `app/main.py`, `app/__main__.py`
- Modify: `app/__init__.py`

- [ ] **Step 1: Write `app/routes/web.py`**

```python
# app/routes/web.py
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import SESSION_KEY, is_authenticated, verify_code
from app.config import Settings

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
def login_submit(request: Request, code: str = Form(...)):
    settings: Settings = request.app.state.settings
    if verify_code(settings.edit_secret, code):
        request.session[SESSION_KEY] = True
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(
        request, "login.html", {"error": "Invalid code"}, status_code=401
    )


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@router.get("/", response_class=HTMLResponse)
def editor_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request, "editor.html", {})
```

- [ ] **Step 2: Write `app/templates/base.html`**

```html
<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{% block title %}Czołko Songs{% endblock %}</title>
  <link rel="stylesheet" href="/static/styles.css" />
</head>
<body>
  <main>{% block content %}{% endblock %}</main>
  {% block scripts %}{% endblock %}
</body>
</html>
```

- [ ] **Step 3: Write `app/templates/login.html`**

```html
{% extends "base.html" %}
{% block title %}Logowanie{% endblock %}
{% block content %}
<h1>Logowanie</h1>
{% if error %}<p class="error">{{ error }}</p>{% endif %}
<form method="post" action="/login">
  <label>Kod dostępu
    <input type="password" name="code" autofocus required />
  </label>
  <button type="submit">Zaloguj</button>
</form>
{% endblock %}
```

- [ ] **Step 4: Write `app/templates/editor.html`**

```html
{% extends "base.html" %}
{% block title %}Edycja piosenek{% endblock %}
{% block content %}
<header class="bar">
  <h1>Piosenki</h1>
  <form method="post" action="/logout"><button type="submit">Wyloguj</button></form>
</header>

<form id="add-form" class="row">
  <input name="author" placeholder="Wykonawca" required />
  <input name="title" placeholder="Tytuł" required />
  <button type="submit">Dodaj</button>
</form>

<p id="status" class="status"></p>
<table id="songs">
  <thead><tr><th>Wykonawca</th><th>Tytuł</th><th></th></tr></thead>
  <tbody></tbody>
</table>
{% endblock %}
{% block scripts %}<script src="/static/app.js"></script>{% endblock %}
```

- [ ] **Step 5: Write `app/static/styles.css`**

```css
:root { font-family: system-ui, sans-serif; }
body { margin: 0; padding: 1rem; max-width: 900px; margin-inline: auto; }
.bar { display: flex; justify-content: space-between; align-items: center; }
.row { display: flex; gap: .5rem; margin: 1rem 0; }
.row input { flex: 1; padding: .4rem; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: .4rem; border-bottom: 1px solid #ddd; }
td input { width: 100%; padding: .3rem; box-sizing: border-box; }
button { padding: .4rem .8rem; cursor: pointer; }
.error { color: #b00020; }
.status { color: #555; min-height: 1.2em; }
```

- [ ] **Step 6: Write `app/static/app.js`**

```javascript
const tbody = document.querySelector("#songs tbody");
const statusEl = document.querySelector("#status");

function setStatus(msg) { statusEl.textContent = msg; }

async function api(method, url, body) {
  const opts = { method, headers: {} };
  if (body) { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(`${method} ${url} -> ${res.status}`);
  return res.status === 204 ? null : res.json();
}

function row(song) {
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td><input value="${escapeAttr(song.author)}" data-field="author" /></td>
    <td><input value="${escapeAttr(song.title)}" data-field="title" /></td>
    <td><button data-save>Zapisz</button> <button data-del>Usuń</button></td>`;
  const get = (f) => tr.querySelector(`[data-field="${f}"]`).value;
  tr.querySelector("[data-save]").onclick = async () => {
    try { await api("PUT", `/api/songs/${song.id}`, { author: get("author"), title: get("title") });
      setStatus("Zapisano."); } catch (e) { setStatus(e.message); }
  };
  tr.querySelector("[data-del]").onclick = async () => {
    try { await api("DELETE", `/api/songs/${song.id}`); tr.remove(); setStatus("Usunięto."); }
    catch (e) { setStatus(e.message); }
  };
  return tr;
}

function escapeAttr(s) { return String(s).replace(/"/g, "&quot;"); }

async function load() {
  tbody.replaceChildren();
  const songs = await api("GET", "/api/songs");
  for (const s of songs) tbody.appendChild(row(s));
  setStatus(`${songs.length} piosenek.`);
}

document.querySelector("#add-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  try {
    await api("POST", "/api/songs", { author: f.author.value, title: f.title.value });
    f.reset(); await load();
  } catch (err) { setStatus(err.message); }
});

load().catch((e) => setStatus(e.message));
```

- [ ] **Step 7: Write `app/app_factory.py`**

```python
# app/app_factory.py
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import Settings
from app.db import init_db, make_engine, seed_if_empty, set_engine
from app.routes import editor, public, web

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = make_engine(settings.database_path)
        init_db(engine)
        seed_if_empty(engine)
        set_engine(engine)
        yield

    app = FastAPI(title="Czolko Songs API", lifespan=lifespan)
    app.state.settings = settings
    app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(public.router)
    app.include_router(editor.router)
    app.include_router(web.router)
    return app
```

- [ ] **Step 8: Write `app/main.py`**

```python
# app/main.py
from app.app_factory import create_app

app = create_app()
```

- [ ] **Step 9: Write `app/__main__.py`**

```python
# app/__main__.py
import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", "::"),
        port=int(os.environ.get("PORT", "8000")),
    )
```

- [ ] **Step 10: Write `app/__init__.py`**

```python
from app.app_factory import create_app

__all__ = ["create_app"]
```

- [ ] **Step 11: Lint**

Run: `uv run ruff check app`
Expected: no errors.

- [ ] **Step 12: Commit**

```bash
git add app
git commit -m "feat: add web pages, templates, static assets and app factory"
```

---

### Task 9: Integration tests — public + auth gating

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_public.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write `tests/conftest.py`**

```python
# tests/conftest.py
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
```

- [ ] **Step 2: Write `tests/test_public.py`**

```python
# tests/test_public.py
def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_songs_json_shape_and_order(client):
    r = client.get("/songs.json")
    assert r.status_code == 200
    data = r.json()
    assert data == [
        {"author": "Perfect", "title": "Autobiografia"},
        {"author": "Bajm", "title": "Biała armia"},
    ]


def test_api_songs_includes_id(client):
    data = client.get("/api/songs").json()
    assert all("id" in s for s in data)
    assert {s["author"] for s in data} == {"Perfect", "Bajm"}
```

- [ ] **Step 3: Write `tests/test_auth.py`**

```python
# tests/test_auth.py
def test_edit_requires_auth(client):
    assert client.post("/api/songs", json={"author": "A", "title": "T"}).status_code == 401
    assert client.put("/api/songs/1", json={"author": "A", "title": "T"}).status_code == 401
    assert client.delete("/api/songs/1").status_code == 401


def test_login_bad_code(client):
    r = client.post("/login", data={"code": "wrong"}, follow_redirects=False)
    assert r.status_code == 401


def test_editor_page_redirects_when_anonymous(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_login_then_access(auth_client):
    assert auth_client.get("/", follow_redirects=False).status_code == 200


def test_logout_clears_session(auth_client):
    auth_client.post("/logout", follow_redirects=False)
    assert auth_client.post("/api/songs", json={"author": "A", "title": "T"}).status_code == 401
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_public.py tests/test_auth.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py tests/test_public.py tests/test_auth.py
git commit -m "test: add public endpoint and auth-gating integration tests"
```

---

### Task 10: Integration tests — CRUD round-trip

**Files:**
- Create: `tests/test_crud.py`

- [ ] **Step 1: Write `tests/test_crud.py`**

```python
# tests/test_crud.py
def test_create_song(auth_client):
    r = auth_client.post("/api/songs", json={"author": "  Kombii ", "title": " Słodkiego  "})
    assert r.status_code == 201
    body = r.json()
    assert body["author"] == "Kombii"  # trimmed
    assert body["title"] == "Słodkiego"
    assert isinstance(body["id"], int)


def test_create_rejects_blank(auth_client):
    assert auth_client.post("/api/songs", json={"author": "  ", "title": "x"}).status_code == 422


def test_update_song(auth_client):
    new_id = auth_client.post("/api/songs", json={"author": "A", "title": "T"}).json()["id"]
    r = auth_client.put(f"/api/songs/{new_id}", json={"author": "A2", "title": "T2"})
    assert r.status_code == 200
    assert r.json() == {"id": new_id, "author": "A2", "title": "T2"}


def test_update_unknown_404(auth_client):
    assert auth_client.put("/api/songs/99999", json={"author": "A", "title": "T"}).status_code == 404


def test_delete_song(auth_client):
    new_id = auth_client.post("/api/songs", json={"author": "A", "title": "T"}).json()["id"]
    assert auth_client.delete(f"/api/songs/{new_id}").status_code == 204
    ids = {s["id"] for s in auth_client.get("/api/songs").json()}
    assert new_id not in ids


def test_delete_unknown_404(auth_client):
    assert auth_client.delete("/api/songs/99999").status_code == 404
```

- [ ] **Step 2: Run the tests**

Run: `uv run pytest tests/test_crud.py -v`
Expected: all passed.

- [ ] **Step 3: Run the full suite + lint**

Run: `uv run pytest && uv run ruff check .`
Expected: all tests pass; ruff clean.

- [ ] **Step 4: Commit**

```bash
git add tests/test_crud.py
git commit -m "test: add CRUD round-trip integration tests"
```

---

### Task 11: README + smoke run

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

````markdown
# czolko-songs-api

FastAPI service that serves and edits the song list for the *Czołko Song* game.

- Public, game-compatible list: `GET /songs.json` → `[{ "author", "title" }]`
- Editor web UI at `/` (login with `EDIT_SECRET`), JSON API under `/api/songs`.
- SQLite storage, seeded on first run from `data/default_songs.json`.

## Requirements
- Python 3.11+ and [uv](https://docs.astral.sh/uv/).

## Setup
```bash
uv sync
cp .env.example .env   # then edit EDIT_SECRET and SESSION_SECRET
```

Generate a session secret:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Run (IPv6 / dual-stack)
```bash
set -a; . ./.env; set +a       # load env (bash); or use your process manager
uv run uvicorn app.main:app --host :: --port 8000
# or:
uv run python -m app           # honours HOST (default ::) and PORT
```
Binding to `::` serves IPv6 and IPv4-mapped clients.

## Test & lint
```bash
uv run pytest
uv run ruff check .
uv run ruff format .
```

## Deployment (uvicorn + reverse proxy)
Run behind your existing reverse proxy on dgansty.pl; the proxy terminates TLS
and should `listen [::]:443`. Persist the SQLite file via `DATABASE_PATH`.

Example systemd unit:
```ini
[Unit]
Description=czolko-songs-api
After=network.target

[Service]
WorkingDirectory=/srv/czolko-songs-api
Environment=DATABASE_PATH=/srv/czolko-songs-api/songs.db
EnvironmentFile=/srv/czolko-songs-api/.env
ExecStart=/usr/local/bin/uv run uvicorn app.main:app --host :: --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Connecting the game
Point `SONGS_JSON_URL` in the React Native app
(`src/utils/songsDownload.js`) at this service's `/songs.json` once deployed.
(Not changed automatically — the app keeps working via its bundled fallback.)
````

- [ ] **Step 2: Smoke-run the server with real env**

Run:
```bash
EDIT_SECRET=dev SESSION_SECRET=devsign DATABASE_PATH=./smoke.db \
  uv run python -c "from fastapi.testclient import TestClient; from app.main import app; c=TestClient(app); c.__enter__(); print(c.get('/songs.json').status_code, len(c.get('/songs.json').json()))"
```
Expected: prints `200 178` (seeded from the real `data/default_songs.json`). Then `rm -f smoke.db`.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup, IPv6 run, and deployment notes"
```

---

## Self-Review notes

- **Spec coverage:** public `/songs.json` shape (Task 7/9), `/api/songs` with id (7/9), editor CRUD with auth (7/10), session login UI (8/9), SQLite + seeding from app assets (4/5), env config fail-fast (2), IPv6 bind (8 `__main__`, 11 README), uv deps + ruff (1), tests (9/10), README/deploy (11). No game-code changes (constraint honored).
- **Type consistency:** `Song`, `SongIn`, `SongOut`, `SongPublic` used consistently; `get_session`/`set_engine`/`make_engine`/`init_db`/`seed_if_empty` signatures match across db.py and callers; `verify_code`, `is_authenticated`, `require_auth`, `SESSION_KEY` consistent across auth.py, web.py, editor.py.
- **No placeholders:** all steps contain full code/commands.
