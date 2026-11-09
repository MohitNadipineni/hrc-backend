from app.core.config import settings

ALICE = {"X-User-Id": "test-alice"}
BOB = {"X-User-Id": "test-bob"}
SAR = "What is the deadline to file a SAR?"
OHIO = ("Are there Ohio invoices in the audit period with the same certificate problem "
        "that the notice did not cite? What extra tax would we owe?")


def test_health_checks(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json()["status"] == "ready"


def test_ohio_question_cites_documents_and_query(client):
    data = client.post("/v1/chat", json={"question": OHIO}, headers=ALICE).json()
    tags = [c["tag"] for c in data["citations"]]
    assert data["route"] == "hybrid"
    assert "S1" in tags
    assert any(t.startswith("D") for t in tags)
    assert data["warnings"] == []


def test_follow_up_uses_the_earlier_question(client):
    first = client.post("/v1/chat", json={"question": SAR}, headers=ALICE).json()
    follow = client.post("/v1/chat", json={"question": "Tell me more about that.",
                                           "thread_id": first["thread_id"]}, headers=ALICE).json()
    alone = client.post("/v1/chat", json={"question": "Tell me more about that."}, headers=ALICE).json()

    assert "SAR" in follow["standalone_question"]
    assert any(c["source"] == "AML-SOP-021" for c in follow["citations"])
    assert alone["citations"] == []


def test_stream_sends_meta_then_tokens_then_done(client):
    r = client.post("/v1/chat/stream", json={"question": SAR}, headers=ALICE)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    assert r.text.count("event: meta") == 1
    assert r.text.count("event: done") == 1
    assert r.text.count("event: token") > 10


def test_feedback_only_on_own_answers(client):
    mid = client.post("/v1/chat", json={"question": SAR}, headers=ALICE).json()["message_id"]
    assert client.post("/v1/feedback", json={"message_id": mid, "rating": 1}, headers=ALICE).status_code == 204
    assert client.post("/v1/feedback", json={"message_id": mid, "rating": 1}, headers=BOB).status_code == 404
    assert client.post("/v1/feedback", json={"message_id": mid, "rating": 5}, headers=ALICE).status_code == 422


def test_empty_question_is_rejected(client):
    assert client.post("/v1/chat", json={"question": ""}, headers=ALICE).status_code == 422


def test_api_key_mode_ignores_claimed_groups(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_mode", "apikey")
    monkeypatch.setattr(settings, "api_keys", {"k-fin": {"user_id": "test-finn", "groups": ["finance"]}})

    assert client.post("/v1/chat", json={"question": OHIO}).status_code == 401
    data = client.post("/v1/chat", json={"question": OHIO},
                       headers={"X-API-Key": "k-fin", "X-User-Groups": "tax"}).json()
    assert "S1" not in [c["tag"] for c in data["citations"]]