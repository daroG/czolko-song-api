import pytest
from pydantic import ValidationError

from app.models import SongIn, SongOut, SongPublic


def test_songin_trims_and_requires_nonempty():
    s = SongIn(author="  Perfect ", title=" Autobiografia  ")
    assert s.author == "Perfect"
    assert s.title == "Autobiografia"


def test_songin_rejects_blank():
    with pytest.raises(ValidationError):
        SongIn(author="   ", title="x")


def test_public_shape_excludes_id():
    out = SongPublic(author="A", title="T")
    assert out.model_dump() == {"author": "A", "title": "T"}


def test_song_out_includes_id():
    out = SongOut(id=5, author="A", title="T")
    assert out.model_dump() == {"id": 5, "author": "A", "title": "T"}
