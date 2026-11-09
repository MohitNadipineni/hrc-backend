from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api.routers import chat, health
from app.core.config import settings

INDEX = Path(__file__).parent / "static" / "index.html"

app = FastAPI(title=settings.app_name)
app.include_router(health.router)
app.include_router(chat.router)


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(INDEX)