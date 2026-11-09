import httpx

BASE = "http://localhost:8000"
OHIO = ("Are there Ohio invoices in the audit period with the same certificate problem "
        "that the notice did not cite? What extra tax would we owe?")


def show(title: str, data: dict) -> dict:
    print(f"\n=== {title}")
    print("route:     ", data["route"])
    print("searched:  ", data["standalone_question"])
    print("citations: ", ", ".join(f"{c['tag']} {c['source']}" for c in data["citations"]) or "none")
    if data.get("sql"):
        print("SQL [S1]:  ", data["sql"][:110] + "...")
    for line in data["answer"].splitlines()[1:4]:
        print("  ", line[:140])
    print("warnings:  ", data["warnings"] or "none")
    return data


def main() -> None:
    me = {"X-User-Id": "demo-user"}
    with httpx.Client(base_url=BASE, timeout=60) as client:
        print("Health:", client.get("/readyz").json())

        show("1. A document question", client.post(
            "/v1/chat", json={"question": "What is the deadline to file a SAR?"}, headers=me).json())

        show("2. A database question", client.post(
            "/v1/chat", json={"question": "How much use tax did we pay to each state in Q2 2026?"},
            headers=me).json())

        first = show("3. A hybrid question (documents + database)", client.post(
            "/v1/chat", json={"question": OHIO}, headers=me).json())

        show("4. A follow-up in the same conversation", client.post(
            "/v1/chat", json={"question": "Tell me more about that.", "thread_id": first["thread_id"]},
            headers=me).json())

        show("5. The same question from a finance-only user (no tax data allowed)", client.post(
            "/v1/chat", json={"question": OHIO},
            headers={"X-User-Id": "demo-finance", "X-User-Groups": "finance"}).json())

        other = client.get(f"/v1/threads/{first['thread_id']}", headers={"X-User-Id": "someone-else"})
        print(f"\n=== 6. Someone else tries to read the demo conversation: {other.status_code}")

        for user in ("demo-user", "demo-finance"):
            h = {"X-User-Id": user}
            for t in client.get("/v1/threads", headers=h).json():
                client.delete(f"/v1/threads/{t['thread_id']}", headers=h)
        print("\nDemo conversations cleaned up.")


if __name__ == "__main__":
    main()