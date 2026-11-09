from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
ALICE = {"X-User-Id": "alice"}
BOB = {"X-User-Id": "bob"}


def sources(data: dict) -> list[str]:
    return [f"{c['tag']} {c['source']} / {c['detail']}" for c in data["citations"]]


# 1. Alice starts a conversation
first = client.post("/v1/chat", json={"question": "What is the deadline to file a SAR?"}, headers=ALICE).json()
tid = first["thread_id"]
print("1. New thread:", tid)

# 2. Alice asks a follow-up IN the same thread
follow = client.post("/v1/chat", json={"question": "Tell me more about that.", "thread_id": tid},
                     headers=ALICE).json()
print("\n2. Follow-up WITH memory")
print("   standalone question:", follow["standalone_question"])
for s in sources(follow)[:3]:
    print("  ", s)

# 3. The same follow-up in a brand-new thread (no memory), for comparison
alone = client.post("/v1/chat", json={"question": "Tell me more about that."}, headers=ALICE).json()
print("\n3. Same follow-up WITHOUT memory")
print("   standalone question:", alone["standalone_question"])
for s in sources(alone)[:3]:
    print("  ", s)

# 4. Listing conversations
print("\n4. Alice's threads:", len(client.get("/v1/threads", headers=ALICE).json()))
print("   Bob's threads:  ", len(client.get("/v1/threads", headers=BOB).json()))

# 5. Bob tries to read, continue and delete Alice's thread
print("\n5. Bob reads Alice's thread:    ", client.get(f"/v1/threads/{tid}", headers=BOB).status_code)
print("   Bob continues Alice's thread:",
      client.post("/v1/chat", json={"question": "hi", "thread_id": tid}, headers=BOB).status_code)
print("   Bob deletes Alice's thread:  ", client.delete(f"/v1/threads/{tid}", headers=BOB).status_code)

# 6. Alice reads her own thread, then deletes it
print("\n6. Alice reads her thread:", client.get(f"/v1/threads/{tid}", headers=ALICE).status_code,
      "with", len(client.get(f"/v1/threads/{tid}", headers=ALICE).json()["messages"]), "messages")
print("   Alice deletes her thread:", client.delete(f"/v1/threads/{tid}", headers=ALICE).status_code)
client.delete(f"/v1/threads/{alone['thread_id']}", headers=ALICE)