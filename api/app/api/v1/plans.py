"""
plans.py — CRUD dos planos de nutrição e treino.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import models as m
from app.schemas import schemas as s
from app.services import repository as repo

router = APIRouter(prefix="/plan", tags=["plans"])


# ── Nutrition ────────────────────────────────────────────────────────────────

@router.get("/nutrition", response_model=s.PlanNutritionOut)
def get_nutrition_plan(
    user_whatsapp: str = Query("553199674109"),
    db: Session = Depends(get_db),
):
    user = repo.get_or_create_user(db, user_whatsapp)
    repo.seed_default_plans(db, user)
    if not user.plan_nutrition:
        raise HTTPException(404, "no plan yet")
    return user.plan_nutrition


@router.put("/nutrition", response_model=s.PlanNutritionOut)
def upsert_nutrition_plan(
    payload: s.PlanNutritionIn,
    user_whatsapp: str = Query("553199674109"),
    db: Session = Depends(get_db),
):
    user = repo.get_or_create_user(db, user_whatsapp)
    plan = user.plan_nutrition
    if plan is None:
        plan = m.PlanNutrition(user_id=user.id)
        db.add(plan)
    plan.tdee = payload.tdee
    plan.meta_kcal = payload.meta_kcal
    plan.meta_p = payload.meta_p
    plan.meta_f = payload.meta_f
    plan.meta_c = payload.meta_c
    plan.meta_agua_ml = payload.meta_agua_ml
    plan.refeicoes_meta = payload.refeicoes_meta
    db.commit()
    db.refresh(plan)
    return plan


# ── Training ────────────────────────────────────────────────────────────────

@router.get("/training", response_model=s.PlanTrainingOut)
def get_training_plan(
    user_whatsapp: str = Query("553199674109"),
    db: Session = Depends(get_db),
):
    user = repo.get_or_create_user(db, user_whatsapp)
    repo.seed_default_plans(db, user)
    if not user.plan_training:
        raise HTTPException(404, "no plan yet")
    return user.plan_training


@router.put("/training", response_model=s.PlanTrainingOut)
def upsert_training_plan(
    payload: s.PlanTrainingIn,
    user_whatsapp: str = Query("553199674109"),
    db: Session = Depends(get_db),
):
    user = repo.get_or_create_user(db, user_whatsapp)
    plan = user.plan_training
    if plan is None:
        plan = m.PlanTraining(user_id=user.id)
        db.add(plan)
    plan.protocolo = payload.protocolo
    plan.ativo = payload.ativo
    db.commit()
    db.refresh(plan)
    return plan
