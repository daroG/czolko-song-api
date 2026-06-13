def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_songs_json_shape_and_order(client):
    r = client.get("/songs.json")
    assert r.status_code == 200
    data = r.json()
    assert data == [
        {"author": "Perfect", "title": "Autobiografia"},
        {"author": "Bajm", "title": "Biała armia"},
    ]


def test_api_songs_includes_id(client):
    data = client.get("/api/songs").json()
    assert all("id" in s for s in data)
    assert {s["author"] for s in data} == {"Perfect", "Bajm"}
