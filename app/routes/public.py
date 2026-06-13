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
