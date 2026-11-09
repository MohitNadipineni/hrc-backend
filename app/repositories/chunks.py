import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector

from app.core.config import settings

INSERT = """
INSERT INTO chunks (doc_id, doc_title, source_path, content_type, section,
                    chunk_index, content, allowed_groups, embedding)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def replace_document_chunks(doc_id: str, rows: list[tuple]) -> None:
    with psycopg.connect(settings.database_url) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chunks WHERE doc_id = %s", (doc_id,))
            cur.executemany(INSERT, rows)

SEARCH_COLUMNS = "chunk_id, doc_id, doc_title, content_type, section, content"


def keyword_search(query: str, groups: list[str], k: int) -> list[dict]:
    sql = f"""
        SELECT {SEARCH_COLUMNS},
               ts_rank_cd(tsv, to_tsquery('english', %s)) AS score
        FROM chunks
        WHERE tsv @@ to_tsquery('english', %s)
          AND allowed_groups && %s
        ORDER BY score DESC
        LIMIT %s
    """
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        return conn.execute(sql, (query, query, groups, k)).fetchall()


def vector_search(embedding, groups: list[str], k: int) -> list[dict]:
    sql = f"""
        SELECT {SEARCH_COLUMNS},
               1 - (embedding <=> %s) AS similarity
        FROM chunks
        WHERE allowed_groups && %s
        ORDER BY embedding <=> %s
        LIMIT %s
    """
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        register_vector(conn)
        return conn.execute(sql, (embedding, groups, embedding, k)).fetchall()