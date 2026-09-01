"""
dashboard.py — endpoint agregado: dados que a home page consome de uma vez.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas import schemas as s
from app.services import repository as repo
from app.services.agents import DIAS_PT, resolve_treino_do_dia
from datetime import date

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=s.DashboardOut)
def dashboard(
    user_whatsapp: str = Query("553199674109"),
    db: Session = Depends(get_db),
):
    user = repo.get_or_create_user(db, user_whatsapp)
    repo.seed_default_plans(db, user)

    today = repo.today_totals(db, user.id)
    week = repo.last_n_days_totals(db, user.id, days=7)
    last_ck = repo.last_checkin(db, user.id)

    weekday = date.today().weekday()
    protocolo = user.plan_training.protocolo if user.plan_training else None
    plano = resolve_treino_do_dia(protocolo, weekday)

    return s.DashboardOut(
        user=s.UserOut.model_validate(user),
        plan_nutrition=(
            s.PlanNutritionOut.model_validate(user.plan_nutrition)
            if user.plan_nutrition else None
        ),
        plan_training=(
            s.PlanTrainingOut.model_validate(user.plan_training)
            if user.plan_training else None
        ),
        today=s.DashboardTotals(**today),
        last_7_days=week,
        workout_today={
            "weekday": weekday,
            "weekday_pt": DIAS_PT[weekday],
            **plano,
        },
        last_checkin=(
            s.CheckinOut.model_validate(last_ck) if last_ck else None
        ),
    )
