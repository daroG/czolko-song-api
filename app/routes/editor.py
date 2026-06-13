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
