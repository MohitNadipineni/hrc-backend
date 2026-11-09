import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import settings


def _connect():
    return psycopg.connect(settings.database_url, row_factory=dict_row)


def create_thread(user_id: str, title: str) -> str:
    with _connect() as conn:
        row = conn.execute(
            "INSERT INTO app.threads (user_id, title) VALUES (%s, %s) RETURNING thread_id",
            (user_id, title),
        ).fetchone()
        return str(row["thread_id"])


def get_thread(thread_id: str, user_id: str) -> dict | None:
    with _connect() as conn:
        return conn.execute(
            "SELECT thread_id, title, created_at FROM app.threads WHERE thread_id = %s AND user_id = %s",
            (thread_id, user_id),
        ).fetchone()


def list_threads(user_id: str) -> list[dict]:
    with _connect() as conn:
        return conn.execute(
            "SELECT thread_id, title, created_at FROM app.threads WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()


def delete_thread(thread_id: str, user_id: str) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM app.threads WHERE thread_id = %s AND user_id = %s",
            (thread_id, user_id),
        )
        return cur.rowcount == 1


def add_message(thread_id: str, role: str, content: str, details: dict | None = None) -> int:
    with _connect() as conn:
        row = conn.execute(
            "INSERT INTO app.messages (thread_id, role, content, details) VALUES (%s, %s, %s, %s) RETURNING message_id",
            (thread_id, role, content, Jsonb(details or {})),
        ).fetchone()
        return row["message_id"]


def get_messages(thread_id: str) -> list[dict]:
    with _connect() as conn:
        return conn.execute(
            "SELECT message_id, role, content, details, created_at FROM app.messages WHERE thread_id = %s ORDER BY message_id",
            (thread_id,),
        ).fetchall()


def answer_owner(message_id: int) -> str | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT t.user_id FROM app.messages m JOIN app.threads t USING (thread_id) "
            "WHERE m.message_id = %s AND m.role = 'assistant'",
            (message_id,),
        ).fetchone()
        return row["user_id"] if row else None


def save_feedback(message_id: int, user_id: str, rating: int, comment: str | None) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO app.feedback (message_id, user_id, rating, comment) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (message_id, user_id) DO UPDATE "
            "SET rating = EXCLUDED.rating, comment = EXCLUDED.comment, created_at = now()",
            (message_id, user_id, rating, comment),
        )