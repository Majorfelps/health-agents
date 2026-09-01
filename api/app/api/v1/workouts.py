"""
workouts.py — endpoints para registrar e listar treinos.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import models as m
from app.schemas import schemas as s
from app.services import repository as repo
from app.services.agents import DIAS_PT, resolve_treino_do_dia

router = APIRouter(prefix="/workouts", tags=["workouts"])


@router.post("", response_model=s.ExerciseLogOut)
def create_workout(
    payload: s.ExerciseLogIn,
    user_whatsapp: str = Query("553199674109"),
    db: Session = Depends(get_db),
):
    user = repo.get_or_create_user(db, user_whatsapp)
    log = m.ExerciseLog(
        user_id=user.id,
        workout_type=payload.workout_type,
        exercises=payload.exercises,
        duration_minutes=payload.duration_minutes,
        perceived_effort=payload.perceived_effort,
        pain_report=payload.pain_report,
        notes=payload.notes,
        completed=payload.completed,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("", response_model=list[s.ExerciseLogOut])
def list_workouts(
    user_whatsapp: str = Query("553199674109"),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    user = repo.get_or_create_user(db, user_whatsapp)
    return repo.list_recent_workouts(db, user.id, limit=limit)


@router.get("/today")
def today_workout(
    user_whatsapp: str = Query("553199674109"),
    db: Session = Depends(get_db),
):
    """Retorna o treino do dia, resolvido do PlanTraining do usuário (com
    fallback pro padrão)."""
    from datetime import date
    user = repo.get_or_create_user(db, user_whatsapp)
    repo.seed_default_plans(db, user)
    weekday = date.today().weekday()
    protocolo = user.plan_training.protocolo if user.plan_training else None
    plano = resolve_treino_do_dia(protocolo, weekday)
    return {
        "weekday": weekday,
        "weekday_pt": DIAS_PT[weekday],
        **plano,
    }
