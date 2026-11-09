import json

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)
ALICE, BOB = {"X-User-Id": "alice"}, {"X-User-Id": "bob"}
OHIO = ("Are there Ohio invoices in the audit period with the same certificate problem "
        "that the notice did not cite? What extra tax would we owe?")

# A. Streaming
r = client.post("/v1/chat/stream", json={"question": "What is the deadline to file a SAR?"}, headers=ALICE)
print("A. Stream status:", r.status_code, "| type:", r.headers["content-type"])
print("   events -> meta:", r.text.count("event: meta"), "| token:", r.text.count("event: token"),
      "| done:", r.text.count("event: done"))
meta = json.loads(r.text.split("data: ", 1)[1].split("\n", 1)[0])
tid, mid = meta["thread_id"], meta["message_id"]

# B. Feedback
fb = "/v1/feedback"
print("\nB. Alice thumbs-up her answer:   ", client.post(fb, json={"message_id": mid, "rating": 1}, headers=ALICE).status_code)
print("   Alice changes to thumbs-down:  ", client.post(fb, json={"message_id": mid, "rating": -1, "comment": "too long"}, headers=ALICE).status_code)
print("   Bob rates Alice's answer:      ", client.post(fb, json={"message_id": mid, "rating": 1}, headers=BOB).status_code)
print("   Rating of 5 (not allowed):     ", client.post(fb, json={"message_id": mid, "rating": 5}, headers=ALICE).status_code)
client.delete(f"/v1/threads/{tid}", headers=ALICE)

# C. API-key logins
settings.auth_mode = "apikey"
settings.api_keys = {
    "key-tax": {"user_id": "tara", "groups": ["tax", "compliance"]},
    "key-fin": {"user_id": "finn", "groups": ["finance"]},
}
print("\nC. No key:   ", client.post("/v1/chat", json={"question": OHIO}).status_code)
print("   Wrong key:", client.post("/v1/chat", json={"question": OHIO}, headers={"X-API-Key": "guess"}).status_code)

tax = client.post("/v1/chat", json={"question": OHIO}, headers={"X-API-Key": "key-tax"}).json()
print("   Tax key:", [c["tag"] for c in tax["citations"]], "| warnings:", tax["warnings"] or "none")

fin = client.post("/v1/chat", json={"question": OHIO},
                  headers={"X-API-Key": "key-fin", "X-User-Groups": "tax"}).json()
print("   Finance key pretending to be tax:", [c["tag"] for c in fin["citations"]], "| warnings:", fin["warnings"])

client.delete(f"/v1/threads/{tax['thread_id']}", headers={"X-API-Key": "key-tax"})
client.delete(f"/v1/threads/{fin['thread_id']}", headers={"X-API-Key": "key-fin"})
settings.auth_mode = "dev"