"""
deps.py — Dependências compartilhadas.
"""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services import repository as repo
from app.models import models as m


def get_or_create_current_user(
    whatsapp: str = "553199674109",
    db: Session = Depends(get_db),
) -> m.User:
    """User default = Michael (do seed original). Trocar depois por auth real."""
    user = repo.get_or_create_user(db, whatsapp)
    repo.seed_default_plans(db, user)
    return user
