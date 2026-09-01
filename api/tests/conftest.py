"""
conftest.py — sobe um Postgres descartável (testcontainers) e aponta
DATABASE_URL pra ele ANTES de qualquer import de app.*, já que
app.core.config.settings é lido uma vez no import do módulo. Cria o
schema via Base.metadata (equivalente ao que o Alembic aplicaria) e
trunca as tabelas entre testes pra isolamento, sem precisar de um
Postgres já rodando na máquina de quem for rodar `pytest`.
"""
import atexit
import os

from testcontainers.postgres import PostgresContainer

_pg = PostgresContainer("postgres:17-alpine")
_pg.start()
atexit.register(_pg.stop)

os.environ["DATABASE_URL"] = _pg.get_connection_url().replace(
    "postgresql+psycopg2", "postgresql+psycopg"
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

import app.models.models  # noqa: E402,F401 — registra os models no Base.metadata
from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402

Base.metadata.create_all(bind=engine)

_TABLES = [
    "agent_messages", "meals", "exercise_logs", "checkins",
    "plan_training", "plan_nutrition", "llm_config", "users",
]


@pytest.fixture(autouse=True)
def _clean_db():
    """Trunca tudo depois de cada teste (isolamento entre testes)."""
    yield
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {', '.join(_TABLES)} RESTART IDENTITY CASCADE"))


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    with TestClient(fastapi_app) as c:
        yield c
