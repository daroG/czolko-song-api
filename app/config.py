from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    edit_secret: str
    session_secret: str
    database_path: str

    @classmethod
    def from_env(cls) -> Settings:
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
