"""
main.py — Entry point FastAPI. Cria tabelas no startup (dev only).
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db import Base, engine
from app.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cria tabelas no startup (em prod, use Alembic)
    import app.models.models  # noqa: F401 — registra os models no metadata
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}
