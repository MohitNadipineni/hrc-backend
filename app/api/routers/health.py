import psycopg

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import settings

router = APIRouter(tags=["health"] )

@router.get("/healthz")
def health_check():
    return {"status": "ok"}
@router.get("/readyz")
def ready_check():
    try:
        with psycopg.connect(settings.database_url, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
            return  {"status": "ready" , "database": "up"}
    except Exception:
            return JSONResponse(status_code=503, content={"status": "not ready", "database": "down"})


