"""
meals.py — endpoints para registrar e listar refeições.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import models as m
from app.schemas import schemas as s
from app.services import repository as repo

router = APIRouter(prefix="/meals", tags=["meals"])


@router.post("", response_model=s.MealOut)
def create_meal(
    payload: s.MealIn,
    user_whatsapp: str = Query("553199674109"),
    db: Session = Depends(get_db),
):
    user = repo.get_or_create_user(db, user_whatsapp)
    meal = m.Meal(
        user_id=user.id,
        meal_type=payload.meal_type,
        description=payload.description,
        opcao=payload.opcao,
        calories=payload.calories,
        protein_g=payload.protein_g,
        carbs_g=payload.carbs_g,
        fat_g=payload.fat_g,
        source=payload.source,
    )
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return meal


@router.get("", response_model=list[s.MealOut])
def list_meals(
    user_whatsapp: str = Query("553199674109"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    user = repo.get_or_create_user(db, user_whatsapp)
    return repo.list_recent_meals(db, user.id, limit=limit)


@router.get("/today")
def today_totals(
    user_whatsapp: str = Query("553199674109"),
    db: Session = Depends(get_db),
):
    user = repo.get_or_create_user(db, user_whatsapp)
    return repo.today_totals(db, user.id)


@router.get("/week")
def week_totals(
    user_whatsapp: str = Query("553199674109"),
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    user = repo.get_or_create_user(db, user_whatsapp)
    return repo.last_n_days_totals(db, user.id, days=days)
