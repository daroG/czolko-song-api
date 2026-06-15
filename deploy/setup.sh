#!/usr/bin/env bash
# First-time deployment on the VPS: install deps and install/enable the systemd
# unit. The database is created and seeded automatically on first start (the app
# does this in its lifespan handler). Idempotent — safe to re-run.
set -euo pipefail

APPDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APPDIR"

SUDO=""
[ "$(id -u)" -ne 0 ] && SUDO="sudo"

UV="$(command -v uv || true)"
[ -z "$UV" ] && { echo "ERROR: 'uv' not found in PATH. Install it first."; exit 1; }

USER_NAME="$(id -un)"
ENVFILE="$APPDIR/deploy/app.env"

if [ ! -f "$ENVFILE" ]; then
  cp "$APPDIR/deploy/app.env.example" "$ENVFILE"
  echo ">>> Created $ENVFILE"
  echo ">>> EDIT IT NOW (set PORT, EDIT_SECRET and SESSION_SECRET), then re-run this script."
  exit 1
fi

echo "==> Installing dependencies (uv sync)"
uv sync

render() {
  sed -e "s|__USER__|$USER_NAME|g" -e "s|__APPDIR__|$APPDIR|g" -e "s|__UV__|$UV|g" "$1"
}

echo "==> Installing systemd unit"
render deploy/czolko-songs-api.service | $SUDO tee /etc/systemd/system/czolko-songs-api.service >/dev/null

echo "==> Enabling and starting the service"
$SUDO systemctl daemon-reload
$SUDO systemctl enable --now czolko-songs-api.service

echo
echo "Done. The API is running on port ${PORT:-(see deploy/app.env)}."
echo "Manage it with: ./deploy/manage.sh status | logs | restart | deploy"
