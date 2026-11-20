def test_chat_success(client, mock_llm):
    r = client.post("/chat", json={"message": "Tell me about Mohit's projects"})
    assert r.status_code == 200
    data = r.json()
    assert "response" in data
    assert "session_id" in data
    assert len(data["session_id"]) > 0


def test_chat_persists_session(client, mock_llm):
    r1 = client.post("/chat", json={"message": "Hello"})
    session_id = r1.json()["session_id"]

    r2 = client.post("/chat", json={"message": "What are his skills?", "session_id": session_id})
    assert r2.status_code == 200
    assert r2.json()["session_id"] == session_id


def test_chat_generates_session_when_missing(client, mock_llm):
    r = client.post("/chat", json={"message": "Hello"})
    assert r.status_code == 200
    assert r.json()["session_id"] is not None


def test_chat_empty_message_rejected(client):
    r = client.post("/chat", json={"message": ""})
    assert r.status_code == 422


def test_chat_whitespace_message_rejected(client):
    r = client.post("/chat", json={"message": "   "})
    assert r.status_code == 422


def test_chat_message_too_long(client):
    r = client.post("/chat", json={"message": "a" * 2001})
    assert r.status_code == 422


def test_chat_missing_message_field(client):
    r = client.post("/chat", json={})
    assert r.status_code == 422
