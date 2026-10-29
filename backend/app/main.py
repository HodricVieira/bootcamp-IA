from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router

app = FastAPI(title="DocuMind API", version="1.0.0")
app.include_router(health_router)
app.include_router(documents_router)
app.mount(
    "/",
    StaticFiles(directory=Path(__file__).resolve().parents[2] / "frontend", html=True),
    name="frontend",
)
