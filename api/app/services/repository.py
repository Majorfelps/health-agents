"""
repository.py — Camada de acesso a dados. Encapsula queries que aparecem
em vários endpoints (totais do dia, refeições da semana, agregados).
"""
from __future__ import annotations
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import models as m
from app.services.agents import PLANO_SEMANAL_PADRAO


# ── Users ────────────────────────────────────────────────────────────────────

def get_or_create_user(db: Session, whatsapp_number: str, name: str = "") -> m.User:
    user = db.query(m.User).filter(m.User.whatsapp_number == whatsapp_number).one_or_none()
    if user:
        return user
    user = m.User(whatsapp_number=whatsapp_number, name=name or None)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def seed_default_plans(db: Session, user: m.User) -> None:
    """Cria PlanNutrition e PlanTraining padrão se não existirem (idempotente)."""
    if not user.plan_nutrition:
        plan = m.PlanNutrition(
            user_id=user.id,
            refeicoes_meta={
                "cafe": {"meta_kcal": 445, "P": 24, "F": 15, "C": 51},
                "almoco": {"meta_kcal": 535, "P": 35, "F": 8, "C": 59},
                "lanche": {"meta_kcal": 260, "P": 26, "F": 5, "C": 20},
                "janta": {"meta_kcal": 405, "P": 36, "F": 8, "C": 30},
                "ceia": {"meta_kcal": 125, "P": 9, "F": 1, "C": 10},
            },
        )
        db.add(plan)
    if not user.plan_training:
        plan = m.PlanTraining(
            user_id=user.id,
            protocolo=dict(PLANO_SEMANAL_PADRAO),
        )
        db.add(plan)
    db.commit()


# ── Meals ───────────────────────────────────────────────────────────────────

def today_totals(db: Session, user_id: int) -> dict:
    today_start = datetime.combine(date.today(), datetime.min.time())
    rows = db.query(
        func.coalesce(func.sum(m.Meal.calories), 0).label("kcal"),
        func.coalesce(func.sum(m.Meal.protein_g), 0).label("P"),
        func.coalesce(func.sum(m.Meal.carbs_g), 0).label("C"),
        func.coalesce(func.sum(m.Meal.fat_g), 0).label("F"),
    ).filter(
        m.Meal.user_id == user_id,
        m.Meal.logged_at >= today_start,
    ).one()
    return {
        "kcal": float(rows.kcal or 0),
        "P": float(rows.P or 0),
        "F": float(rows.F or 0),
        "C": float(rows.C or 0),
        "agua_ml": today_water(db, user_id),
    }


def today_water(db: Session, user_id: int) -> float:
    today_start = datetime.combine(date.today(), datetime.min.time())
    total_ml = db.query(
        func.coalesce(func.sum(m.Checkin.water_liters), 0)
    ).filter(
        m.Checkin.user_id == user_id,
        m.Checkin.created_at >= today_start,
    ).scalar() or 0.0
    return float(total_ml) * 1000  # converte L → ml


def last_n_days_totals(db: Session, user_id: int, days: int = 7) -> dict:
    """Retorna {date_str: {kcal, P, F, C, agua_ml}}."""
    start = datetime.combine(date.today() - timedelta(days=days - 1), datetime.min.time())
    meals = db.query(m.Meal).filter(
        m.Meal.user_id == user_id,
        m.Meal.logged_at >= start,
    ).all()
    water = db.query(m.Checkin).filter(
        m.Checkin.user_id == user_id,
        m.Checkin.created_at >= start,
    ).all()

    out: dict[str, dict] = {}
    for i in range(days):
        d = (date.today() - timedelta(days=days - 1 - i)).isoformat()
        out[d] = {"kcal": 0.0, "P": 0.0, "F": 0.0, "C": 0.0, "agua_ml": 0.0}

    for meal in meals:
        d = meal.logged_at.date().isoformat()
        if d in out:
            out[d]["kcal"] += float(meal.calories or 0)
            out[d]["P"] += float(meal.protein_g or 0)
            out[d]["C"] += float(meal.carbs_g or 0)  # carbo
            out[d]["F"] += float(meal.fat_g or 0)    # gordura
    for ck in water:
        d = ck.created_at.date().isoformat()
        if d in out:
            out[d]["agua_ml"] += float(ck.water_liters or 0) * 1000
    return out


def list_recent_meals(db: Session, user_id: int, limit: int = 50) -> list[m.Meal]:
    return db.query(m.Meal).filter(
        m.Meal.user_id == user_id,
    ).order_by(m.Meal.logged_at.desc()).limit(limit).all()


def list_meals_today(db: Session, user_id: int) -> list[m.Meal]:
    today_start = datetime.combine(date.today(), datetime.min.time())
    return db.query(m.Meal).filter(
        m.Meal.user_id == user_id,
        m.Meal.logged_at >= today_start,
    ).order_by(m.Meal.logged_at.asc()).all()


# ── Workouts ────────────────────────────────────────────────────────────────

def list_recent_workouts(db: Session, user_id: int, limit: int = 20) -> list[m.ExerciseLog]:
    return db.query(m.ExerciseLog).filter(
        m.ExerciseLog.user_id == user_id,
    ).order_by(m.ExerciseLog.logged_at.desc()).limit(limit).all()


def has_workout_logged_today(db: Session, user_id: int) -> bool:
    today_start = datetime.combine(date.today(), datetime.min.time())
    return db.query(m.ExerciseLog).filter(
        m.ExerciseLog.user_id == user_id,
        m.ExerciseLog.logged_at >= today_start,
    ).first() is not None


# ── Checkins ─────────────────────────────────────────────────────────────────

def last_checkin(db: Session, user_id: int) -> Optional[m.Checkin]:
    return db.query(m.Checkin).filter(
        m.Checkin.user_id == user_id,
    ).order_by(m.Checkin.created_at.desc()).first()


# ── Agent messages ──────────────────────────────────────────────────────────

def recent_messages(db: Session, user_id: int, limit: int = 100) -> list[m.AgentMessage]:
    return db.query(m.AgentMessage).filter(
        m.AgentMessage.user_id == user_id,
    ).order_by(m.AgentMessage.created_at.desc()).limit(limit).all()


# ── LLM config (singleton) ──────────────────────────────────────────────────

def get_llm_config(db: Session) -> m.LLMConfig:
    """Config atual do LLM (enabled/model), lida do banco — editável em
    runtime via PUT /api/v1/llm/config, sem restart. Cria a linha na 1ª
    chamada, semeada com os valores de LLM_ENABLED/OPENROUTER_MODEL do .env."""
    cfg = db.query(m.LLMConfig).first()
    if cfg is None:
        cfg = m.LLMConfig(enabled=settings.llm_enabled, model=settings.openrouter_model)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def update_llm_config(db: Session, enabled: bool, model: str) -> m.LLMConfig:
    cfg = get_llm_config(db)
    cfg.enabled = enabled
    cfg.model = model
    db.commit()
    db.refresh(cfg)
    return cfg
