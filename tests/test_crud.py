def test_create_song(auth_client):
    r = auth_client.post("/api/songs", json={"author": "  Kombii ", "title": " Słodkiego  "})
    assert r.status_code == 201
    body = r.json()
    assert body["author"] == "Kombii"  # trimmed
    assert body["title"] == "Słodkiego"
    assert isinstance(body["id"], int)


def test_create_rejects_blank(auth_client):
    assert auth_client.post("/api/songs", json={"author": "  ", "title": "x"}).status_code == 422


def test_update_song(auth_client):
    new_id = auth_client.post("/api/songs", json={"author": "A", "title": "T"}).json()["id"]
    r = auth_client.put(f"/api/songs/{new_id}", json={"author": "A2", "title": "T2"})
    assert r.status_code == 200
    assert r.json() == {"id": new_id, "author": "A2", "title": "T2"}


def test_update_unknown_404(auth_client):
    assert auth_client.put(
        "/api/songs/99999", json={"author": "A", "title": "T"}
    ).status_code == 404


def test_delete_song(auth_client):
    new_id = auth_client.post("/api/songs", json={"author": "A", "title": "T"}).json()["id"]
    assert auth_client.delete(f"/api/songs/{new_id}").status_code == 204
    ids = {s["id"] for s in auth_client.get("/api/songs").json()}
    assert new_id not in ids


def test_delete_unknown_404(auth_client):
    assert auth_client.delete("/api/songs/99999").status_code == 404
