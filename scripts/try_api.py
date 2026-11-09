from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

OHIO = ("Are there Ohio invoices in the audit period with the same certificate problem "
        "that the notice did not cite? What extra tax would we owe?")

tests = [
    ("Tax + compliance user", {"question": OHIO, "user_groups": ["tax", "compliance"]}),
    ("Finance-only user", {"question": OHIO, "user_groups": ["finance"]}),
    ("Empty question", {"question": "", "user_groups": ["tax"]}),
]

for name, body in tests:
    r = client.post("/v1/chat", json=body)
    print(f"--- {name}: status {r.status_code}")
    data = r.json()
    if r.status_code == 200:
        print("route:", data["route"])
        print("citations:", [c["tag"] + " " + c["source"] for c in data["citations"]])
        print("warnings:", data["warnings"] or "none")
    else:
        print("rejected because:", data["detail"][0]["msg"])
    print()