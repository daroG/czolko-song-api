def test_edit_requires_auth(client):
    assert client.post("/api/songs", json={"author": "A", "title": "T"}).status_code == 401
    assert client.put("/api/songs/1", json={"author": "A", "title": "T"}).status_code == 401
    assert client.delete("/api/songs/1").status_code == 401


def test_login_bad_code(client):
    r = client.post("/login", data={"code": "wrong"}, follow_redirects=False)
    assert r.status_code == 401


def test_editor_page_redirects_when_anonymous(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_login_then_access(auth_client):
    assert auth_client.get("/", follow_redirects=False).status_code == 200


def test_logout_clears_session(auth_client):
    auth_client.post("/logout", follow_redirects=False)
    assert auth_client.post("/api/songs", json={"author": "A", "title": "T"}).status_code == 401
