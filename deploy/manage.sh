#!/usr/bin/env bash
# One-command management for the VPS deployment.
set -euo pipefail

APPDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APPDIR"

SUDO=""
[ "$(id -u)" -ne 0 ] && SUDO="sudo"

API="czolko-songs-api"

case "${1:-help}" in
  setup)
    exec "$APPDIR/deploy/setup.sh"
    ;;
  deploy)
    echo "==> Pulling latest"
    git pull --ff-only
    echo "==> Syncing dependencies"
    uv sync
    echo "==> Restarting API"
    $SUDO systemctl restart "$API"
    $SUDO systemctl --no-pager --lines=5 status "$API" || true
    ;;
  start)    $SUDO systemctl start "$API" ;;
  stop)     $SUDO systemctl stop "$API" ;;
  restart)  $SUDO systemctl restart "$API" ;;
  status)   $SUDO systemctl --no-pager status "$API" || true ;;
  logs)     $SUDO journalctl -u "$API" -n 100 -f ;;
  *)
    cat <<EOF
Usage: ./deploy/manage.sh <command>

  setup         First-time install (deps, systemd unit)
  deploy        git pull + uv sync + restart API
  start|stop|restart   Control the API service
  status        Show API service status
  logs          Tail the API logs (journalctl -f)
EOF
    ;;
esac
