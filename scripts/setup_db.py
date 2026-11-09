from pathlib import Path

import psycopg

from app.core.config import settings

SQL_FILES = ["deploy/sql/chunks.sql", "deploy/sql/app_tables.sql"]


def main() -> None:
    with psycopg.connect(settings.database_url, autocommit=True) as conn:
        for path in SQL_FILES:
            conn.execute(Path(path).read_text())
            print(f"applied {path}")
        count = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]

    if count == 0:
        print("chunks table is empty, ingesting documents...")
        from scripts.ingest import main as ingest
        ingest()
    else:
        print(f"chunks table already has {count} chunks, skipping ingestion")


if __name__ == "__main__":
    main()