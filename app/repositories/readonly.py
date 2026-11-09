import psycopg
from psycopg.rows import dict_row

from app.core.config import settings


def run_readonly(sql: str) -> list[dict]:
    with psycopg.connect(settings.database_ro_url, row_factory=dict_row) as conn:
        conn.read_only = True
        with conn.transaction():
            conn.execute(f"SET LOCAL statement_timeout = {int(settings.sql_timeout_ms)}")
            return conn.execute(sql).fetchall()