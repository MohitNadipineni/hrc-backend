import psycopg
from psycopg.rows import dict_row

from app.core.config import settings

CATALOG_SQL = """
    SELECT c.table_schema, c.table_name, c.column_name, c.data_type,
           obj_description((quote_ident(c.table_schema) || '.' || quote_ident(c.table_name))::regclass) AS table_comment,
           col_description((quote_ident(c.table_schema) || '.' || quote_ident(c.table_name))::regclass,
                           c.ordinal_position) AS column_comment
    FROM information_schema.columns c
    WHERE c.table_schema = ANY(%s)
    ORDER BY c.table_schema, c.table_name, c.ordinal_position
"""


def fetch_columns(schemas: list[str]) -> list[dict]:
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        return conn.execute(CATALOG_SQL, (schemas,)).fetchall()