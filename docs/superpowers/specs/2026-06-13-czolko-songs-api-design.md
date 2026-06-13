# czolko-songs-api — Design

**Date:** 2026-06-13
**Status:** Approved (pending spec review)

## Purpose

A small FastAPI service that serves the song list consumed by the *Czołko Song*
React Native game and provides a cookie-authenticated web UI + JSON API for a
single editor to manage that list. The default/seed list is taken from the app's
bundled `assets/songs.json`.

Today the game fetches a static `[{author, title}]` array from
`https://dgansty.pl/czolko/songs.json` and falls back to the bundled
`assets/songs.json` when the remote is unreachable. This service replaces the
static file with a dynamic, editable source while keeping the **exact same JSON
shape**, so the app needs no parsing changes (only the URL is repointed once
deployed).

## Location & tooling

- **Repo:** `C:\Users\Darek\Documents\Projects\python\czolko-songs-api` (own git repo).
- **Dependency management:** `uv` with `pyproject.toml` (PEP 621) + `uv.lock`.
  - Runtime deps: `fastapi`, `uvicorn[standard]`, `sqlmodel`, `jinja2`,
    `python-multipart`, `itsdangerous` (session signing).
  - Dev group: `pytest`, `httpx`, `ruff`.
  - Commands: `uv sync`, `uv run uvicorn ...`, `uv run pytest`, `uv run ruff check`.
- **Lint/format:** `ruff` configured in `pyproject.toml` (`[tool.ruff]`),
  rule set `E,F,I,UP,B`, line length 100, ruff formatter.
- **Python:** 3.11+.

## Key technical choices

- **DB layer:** SQLModel (SQLAlchemy + Pydantic) over a single SQLite table —
  typed models and validation with minimal boilerplate. Rejected raw `sqlite3`
  (more hand-written glue).
- **Web UI:** server-rendered Jinja2 templates + small vanilla JS calling the
  JSON API. No frontend framework (single-editor admin page).
- **Auth:** Starlette `SessionMiddleware` (signed cookie). Login form compares
  the submitted code to `EDIT_SECRET` using a constant-time comparison and sets
  `session["authenticated"] = True`. Edit endpoints depend on that flag.
- **IPv6:** uvicorn binds to `::` (dual-stack: serves IPv6 and IPv4-mapped).
  No IPv4-hardcoded binds. `app/__main__.py` defaults host to `::`.
- **Dropped (YAGNI):** song reordering UI — the game selects songs randomly, so
  list order is cosmetic. Output is ordered by `id` (insertion order). Can be
  added later.

## Data model

Single `Song` table:

| field        | type     | notes                                   |
|--------------|----------|-----------------------------------------|
| `id`         | int PK   | autoincrement                           |
| `author`     | str      | non-empty (trimmed)                     |
| `title`      | str      | non-empty (trimmed)                     |
| `created_at` | datetime | set on insert                           |

Game-facing serialization is exactly `{"author": ..., "title": ...}`.

## Endpoints

### Public (no auth)
- `GET /songs.json` → `[{author, title}]`, ordered by `id`. The URL the app points at.
- `GET /api/songs` → same data including `id` (used by the editor UI).
- `GET /healthz` → `{"status": "ok"}` (liveness; convenient behind a proxy).

### Editor (session auth required)
- `GET /login` → login form.
- `POST /login` → validate code, set session, redirect to `/`.
- `POST /logout` → clear session.
- `GET /` → editor page; redirects to `/login` when not authenticated.
- `POST /api/songs` → add `{author, title}` → returns created song.
- `PUT /api/songs/{id}` → update author/title → returns updated song.
- `DELETE /api/songs/{id}` → delete → `204`.

Auth behavior: unauthenticated **API** calls return `401`; unauthenticated
**browser page** requests redirect to `/login`.

## Configuration (env vars)

| var              | required | default      | purpose                          |
|------------------|----------|--------------|----------------------------------|
| `EDIT_SECRET`    | yes      | —            | editor login code                |
| `SESSION_SECRET` | yes      | —            | cookie signing key               |
| `DATABASE_PATH`  | no       | `./songs.db` | SQLite file path                 |

Missing a required var → fail fast at startup with a clear message.
`.env.example` documents all three.

## Seeding & data flow

On startup, create tables if absent. If the `Song` table is empty, seed it from
`data/default_songs.json` — a checked-in **copy of the app's current
`assets/songs.json` (178 songs)**. After seeding, edits live only in SQLite;
the seed file is never re-read.

## Error handling

- Missing `EDIT_SECRET` / `SESSION_SECRET` at startup → raise with a clear message.
- Unauthenticated edit: API `401`, page redirect to `/login`.
- Empty/whitespace `author` or `title` → `422` (validation).
- `PUT`/`DELETE` on unknown `id` → `404`.

## Testing

`pytest` + FastAPI `TestClient` against a temp/in-memory SQLite:
- `test_public.py` — `/songs.json` shape & ordering; `/api/songs` includes `id`; `/healthz`.
- `test_auth.py` — edit endpoints `401` when unauthenticated; login success/failure; page redirect.
- `test_crud.py` — add/edit/delete round-trip; `404` on unknown id; `422` on empty fields.
- Seeding test — empty DB seeds from `default_songs.json`.

## App integration

Point `SONGS_JSON_URL` in `src/utils/songsDownload.js` (currently
`https://dgansty.pl/czolko/songs.json`) at the deployed service's `/songs.json`.
The app's existing fallback to bundled data keeps it working regardless of
deploy state. This is the only app-side change.

## Deployment

Plain uvicorn on dgansty.pl behind the existing reverse proxy:

```
uv run uvicorn app.main:app --host :: --port 8000
```

Reverse proxy terminates TLS and forwards to the service; expected to
`listen [::]:443` for IPv6. SQLite file persisted on the host filesystem
(`DATABASE_PATH`). systemd unit example included in the README.

## Project layout

```
czolko-songs-api/
  app/
    __init__.py
    main.py            # app factory, middleware, route registration, startup seed
    __main__.py        # python -m app -> uvicorn on host "::"
    config.py          # env-var settings, fail-fast validation
    db.py              # engine, session dependency, init_db + seed
    models.py          # Song SQLModel + request/response schemas
    auth.py            # session helpers + require_auth dependency
    routes/
      __init__.py
      public.py        # GET /songs.json, /api/songs, /healthz
      editor.py        # POST/PUT/DELETE /api/songs (auth)
      web.py           # /login, /logout, / (pages)
    templates/
      base.html
      login.html
      editor.html
    static/
      app.js
      styles.css
  data/
    default_songs.json # seed copy of app assets/songs.json
  tests/
    conftest.py
    test_public.py
    test_auth.py
    test_crud.py
  pyproject.toml       # deps (uv) + ruff config
  uv.lock
  .env.example
  .gitignore
  README.md
```
