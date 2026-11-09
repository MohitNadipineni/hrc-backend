import psycopg
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

TEST_USERS = ["test-alice", "test-bob", "test-tara", "test-finn"]


def _db_is_up() -> bool:
    try:
        with psycopg.connect(settings.database_url, connect_timeout=2):
            return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def db():
    if not _db_is_up():
        pytest.skip("Database is not running. Start Docker, then: docker compose up -d db")


@pytest.fixture(scope="session")
def client(db):
    yield TestClient(app)
    with psycopg.connect(settings.database_url) as conn:
        conn.execute("DELETE FROM app.threads WHERE user_id = ANY(%s)", (TEST_USERS,))