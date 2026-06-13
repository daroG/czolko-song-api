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

## Endpoints
| Method | Path             | Auth | Purpose                                   |
|--------|------------------|------|-------------------------------------------|
| GET    | `/songs.json`    | no   | Game-compatible `[{author,title}]` list   |
| GET    | `/api/songs`     | no   | List with `id` (used by the editor UI)    |
| GET    | `/healthz`       | no   | Liveness check                            |
| GET    | `/`              | yes  | Editor page (redirects to `/login`)       |
| GET    | `/login`         | no   | Login form                                |
| POST   | `/login`         | no   | Submit `EDIT_SECRET`, sets session cookie |
| POST   | `/logout`        | yes  | Clears session                            |
| POST   | `/api/songs`     | yes  | Add a song                                |
| PUT    | `/api/songs/{id}`| yes  | Update a song                             |
| DELETE | `/api/songs/{id}`| yes  | Delete a song                             |

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
