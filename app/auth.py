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
