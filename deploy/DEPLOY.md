# Deploying to a VPS (Mikrus, no Docker)

The API is a single `uvicorn` worker (~30–50 MB RAM) — comfortable on the
smallest Mikrus. Management is via `systemd` + one helper script.

## What gets installed

| Unit | Type | Role |
|------|------|------|
| `czolko-songs-api.service` | service | the FastAPI app, auto-restart, starts on boot |

The unit reads `deploy/app.env` (port + secrets). The SQLite DB lives in the repo
dir (`DATABASE_PATH`) and is created + seeded from `data/default_songs.json`
automatically on first start.

## One-time setup

SSH into the VPS, then:

```bash
# 1. Prerequisites (if missing)
curl -LsSf https://astral.sh/uv/install.sh | sh        # install uv
source ~/.bashrc                                        # put uv on PATH

# 2. Get the code
git clone https://github.com/daroG/czolko-song-api.git
cd czolko-song-api

# 3. Configure: create the env file and fill it in
cp deploy/app.env.example deploy/app.env
nano deploy/app.env        # set PORT (your Mikrus port), EDIT_SECRET, SESSION_SECRET

# 4. Install everything (deps, systemd unit)
./deploy/manage.sh setup
```

`setup.sh` is idempotent. On the very first run it creates `deploy/app.env` and
asks you to edit it; after that it installs deps and installs/enables the service.
(If not running as root it uses `sudo` for the systemd steps.)

> **Mikrus port:** bind to the public port your panel assigns you (set it as
> `PORT` in `app.env`). The app then answers at `http://srvNN.mikr.us:PORT`.
> If you've set up a Mikrus domain/proxy to a local port, point `PORT` there.

## Day-to-day

```bash
./deploy/manage.sh status        # API service status
./deploy/manage.sh logs          # tail API logs (Ctrl-C to stop)
./deploy/manage.sh restart       # restart the API
./deploy/manage.sh deploy        # git pull + uv sync + restart API
```

## Updating

```bash
cd czolko-song-api
./deploy/manage.sh deploy
```

## Notes

- **Secrets** never touch git: they live only in `deploy/app.env` (ignored) and
  are passed to the unit via `EnvironmentFile`. Generate `SESSION_SECRET` with
  `python -c "import secrets; print(secrets.token_hex(32))"`.
- **Health check:** `curl http://127.0.0.1:$PORT/healthz` → `{"status":"ok"}`.
- **Database:** seeded once from `data/default_songs.json` when the table is
  empty; subsequent edits made via the editor UI persist in the SQLite file at
  `DATABASE_PATH`. Back that file up to preserve the curated list.
- **Logs** go to the journal: `journalctl -u czolko-songs-api`.
- **Public list for the game:** `GET /songs.json`. Point the React Native app's
  `SONGS_JSON_URL` at this once deployed.
