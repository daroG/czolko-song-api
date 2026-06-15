# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

FastAPI service that serves and edits the song list for the *Czołko Song* game.
Public read-only `GET /songs.json` (game-compatible `[{author, title}]`), plus a
cookie-authenticated editor web UI at `/` with a JSON CRUD API under `/api/songs`.
SQLite storage, seeded on first run from `data/default_songs.json`.

## Commands

Tooling is [uv](https://docs.astral.sh/uv/); Python 3.11+.

```bash
uv sync                                  # install deps (incl. dev group)
cp .env.example .env                     # set EDIT_SECRET and SESSION_SECRET

uv run pytest                            # run all tests
uv run pytest tests/test_crud.py         # single file
uv run pytest tests/test_crud.py::test_name -q   # single test
uv run ruff check .                      # lint (E, F, I, UP, B)
uv run ruff format .                     # format (line length 100)

# Run (binds :: for IPv6 + IPv4-mapped clients)
uv run uvicorn app.main:app --host :: --port 8000
uv run python -m app                     # honours HOST (default ::) and PORT
```

Required env vars (`Settings.from_env` raises `RuntimeError` if `EDIT_SECRET` or
`SESSION_SECRET` is missing): `EDIT_SECRET` (editor login code), `SESSION_SECRET`
(cookie signing key), and optional `DATABASE_PATH` (default `./songs.db`).

## Architecture

`app/main.py` exposes `app = create_app()` for uvicorn. `create_app` (in
`app/app_factory.py`) is an **app factory** taking optional `Settings` — pass a
`Settings` instance to build an isolated app (this is how tests inject a temp DB
and test secrets; see `tests/conftest.py`).

**Engine lifecycle — the key non-obvious detail.** The SQLAlchemy engine is a
**process-global** in `app/db.py` (`_engine`, set via `set_engine`). It is created
and wired up inside the FastAPI **lifespan** handler in `create_app`:
`make_engine → init_db → seed_if_empty → set_engine`. Route handlers depend on
`get_session`, which reads that global. Consequences:

- The DB is only initialized when the lifespan runs. Tests must enter the
  `TestClient(app)` **context manager** (`with TestClient(app) as c:`) so lifespan
  fires; otherwise `get_session` asserts "engine not initialized".
- The global is shared across apps in a process — relevant if you ever construct
  multiple apps in one test session.

**Seeding.** `seed_if_empty` only inserts when the table is empty, and resolves
`DEFAULT_SEED` *at call time* (not as a default arg) specifically so tests can
`monkeypatch.setattr(db, "DEFAULT_SEED", ...)`. Preserve that pattern.

**Auth — two enforcement styles, both backed by a signed session cookie**
(`SessionMiddleware`, `app/auth.py`):
- JSON edit endpoints: `app/routes/editor.py` mounts the whole `/api/songs` router
  with `dependencies=[Depends(require_auth)]`, which returns **401** when not
  logged in.
- Web pages: `app/routes/web.py` handlers check `is_authenticated` and **redirect**
  to `/login` (303) instead. `POST /login` compares the code with
  `secrets.compare_digest` and sets `request.session[SESSION_KEY]`.

**Routers** (registered in `create_app`):
- `routes/public.py` — unauthenticated: `/healthz`, `/songs.json` (`SongPublic`),
  `/api/songs` GET (`SongOut`, includes `id`, used by the editor UI).
- `routes/editor.py` — authenticated CRUD: POST/PUT/DELETE `/api/songs`.
- `routes/web.py` — Jinja2 pages (`/`, `/login`, `/logout`) from `app/templates/`,
  with static assets mounted at `/static` from `app/static/`.

**Models** (`app/models.py`): `Song` is the SQLModel table; `SongIn` is the write
schema (trims and rejects empty `author`/`title`); `SongPublic` / `SongOut` are
response schemas (`SongOut` adds `id`). Use the right schema as the FastAPI
`response_model` to control field exposure.
