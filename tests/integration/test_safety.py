import psycopg
import pytest

from app.repositories.readonly import run_readonly
from app.services.retrieval import search
from app.services.sql.guard import UnsafeSQLError
from app.services.sql.runner import run_safe_sql

ALICE = {"X-User-Id": "test-alice"}
BOB = {"X-User-Id": "test-bob"}
SAR = "What is the deadline to file a SAR?"


# ---------- Safety test 1: restricted documents stay hidden ----------

def test_restricted_document_hidden_without_group(db):
    found = {r["doc_id"] for r in search(SAR, user_groups=[], top_k=20)}
    assert "AML-SOP-021" not in found


def test_restricted_document_visible_with_group(db):
    found = {r["doc_id"] for r in search(SAR, user_groups=["compliance"], top_k=5)}
    assert "AML-SOP-021" in found


# ---------- Safety test 2: AI-written SQL can never change data ----------

@pytest.mark.parametrize("sql", [
    "DELETE FROM tax.invoices",
    "UPDATE tax.invoices SET amount_usd = 0",
    "DROP TABLE tax.invoices",
])
def test_sql_that_changes_data_is_blocked(db, sql):
    with pytest.raises(UnsafeSQLError):
        run_safe_sql(sql, ["tax"])


def test_read_only_session_refuses_writes_even_without_the_guard(db):
    with pytest.raises(psycopg.Error):
        run_readonly("DELETE FROM tax.invoices")


def test_invoices_are_still_all_there(db):
    assert run_readonly("SELECT count(*) AS n FROM tax.invoices")[0]["n"] == 245


def test_schema_outside_users_groups_is_blocked(db):
    with pytest.raises(UnsafeSQLError):
        run_safe_sql("SELECT * FROM banking.transactions", ["tax"])


# ---------- Safety test 3: nobody can read someone else's conversation ----------

def test_users_cannot_touch_each_others_threads(client):
    tid = client.post("/v1/chat", json={"question": SAR}, headers=ALICE).json()["thread_id"]

    assert client.get(f"/v1/threads/{tid}", headers=BOB).status_code == 404
    assert client.post("/v1/chat", json={"question": "hi", "thread_id": tid}, headers=BOB).status_code == 404
    assert client.delete(f"/v1/threads/{tid}", headers=BOB).status_code == 404
    assert all(t["thread_id"] != tid for t in client.get("/v1/threads", headers=BOB).json())
    assert client.get(f"/v1/threads/{tid}", headers=ALICE).status_code == 200