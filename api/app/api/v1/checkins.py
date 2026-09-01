"""
checkins.py — endpoints para registrar e listar check-ins.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import models as m
from app.schemas import schemas as s
from app.services import repository as repo

router = APIRouter(prefix="/checkins", tags=["checkins"])


@router.post("", response_model=s.CheckinOut)
def create_checkin(
    payload: s.CheckinIn,
    user_whatsapp: str = Query("553199674109"),
    db: Session = Depends(get_db),
):
    user = repo.get_or_create_user(db, user_whatsapp)
    ck = m.Checkin(
        user_id=user.id,
        type=payload.type,
        mood=payload.mood,
        hunger_level=payload.hunger_level,
        sleep_hours=payload.sleep_hours,
        water_liters=payload.water_liters,
        notes=payload.notes,
    )
    db.add(ck)
    db.commit()
    db.refresh(ck)
    return ck


@router.get("/last", response_model=s.CheckinOut | None)
def last_checkin(
    user_whatsapp: str = Query("553199674109"),
    db: Session = Depends(get_db),
):
    user = repo.get_or_create_user(db, user_whatsapp)
    return repo.last_checkin(db, user.id)
