"""
models.py — Modelos SQLAlchemy. Espelha o schema de
scripts/health_db_bootstrap.sql do Hermes, estendido com:
  - plan_nutrition (1:1 com user — meta kcal, P/F/C, agua, 5 refeições)
  - plan_training (1:1 com user — protocolo semanal)
  - meals (refeições com 3 opções A/B/C cada)
  - exercise_logs (séries/reps de cada exercício feito)

Decisão de design: o estado do agente (qual foi a última refeição registrada,
totais do dia) vive no banco, não em state.json. Isso elimina a divergência
que existia entre /tmp/nutri_tracker_state.json e a tabela nutrition_logs.
"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import (
    String, Integer, Numeric, Text, ForeignKey, DateTime, Boolean, JSON, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    whatsapp_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(120))
    age: Mapped[int | None] = mapped_column(Integer)
    sex: Mapped[str | None] = mapped_column(String(20))
    height_cm: Mapped[int | None] = mapped_column(Integer)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 2))
    goal: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    plan_nutrition: Mapped["PlanNutrition | None"] = relationship(
        "PlanNutrition", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    plan_training: Mapped["PlanTraining | None"] = relationship(
        "PlanTraining", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class PlanNutrition(Base):
    """Plano nutricional (1:1 com user). Substitui os valores hardcoded nas skills."""
    __tablename__ = "plan_nutrition"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    tdee: Mapped[int] = mapped_column(Integer, default=2274)
    meta_kcal: Mapped[int] = mapped_column(Integer, default=1770)
    meta_p: Mapped[int] = mapped_column(Integer, default=186)  # 2g/kg
    meta_f: Mapped[int] = mapped_column(Integer, default=70)
    meta_c: Mapped[int] = mapped_column(Integer, default=165)
    meta_agua_ml: Mapped[int] = mapped_column(Integer, default=2500)
    refeicoes_meta: Mapped[dict] = mapped_column(JSON, default=dict)  # 5 refeições + ceia com kcal/P/F/C
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="plan_nutrition")


class PlanTraining(Base):
    """Plano de treino semanal (1:1 com user). Substitui a PLANO_SEMANAL hardcoded."""
    __tablename__ = "plan_training"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    protocolo: Mapped[dict] = mapped_column(JSON, default=dict)  # 7 dias com exercícios
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="plan_training")


class LLMConfig(Base):
    """Config do LLM opcional (singleton — sempre 1 linha). Editável via
    PUT /api/v1/llm/config, sem precisar reiniciar o container. Valores
    iniciais vêm de LLM_ENABLED/OPENROUTER_MODEL no .env (só na 1ª criação
    da linha); depois disso, o banco manda. A API key continua só no .env
    — não é editável por aqui."""
    __tablename__ = "llm_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    model: Mapped[str] = mapped_column(String(200), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Meal(Base):
    """Refeição registrada (com 3 opções A/B/C). Espelha nutrition_logs."""
    __tablename__ = "meals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    meal_type: Mapped[str] = mapped_column(String(50))  # cafe|almoco|lanche|janta|ceia
    description: Mapped[str] = mapped_column(Text)
    opcao: Mapped[str | None] = mapped_column(String(1))  # 'A' | 'B' | 'C' | None
    calories: Mapped[float | None] = mapped_column(Numeric(8, 2))
    protein_g: Mapped[float | None] = mapped_column(Numeric(8, 2))
    carbs_g: Mapped[float | None] = mapped_column(Numeric(8, 2))
    fat_g: Mapped[float | None] = mapped_column(Numeric(8, 2))
    source: Mapped[str] = mapped_column(String(50), default="chat")  # chat|whatsapp|cron
    logged_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    __table_args__ = (
        Index("idx_meals_user_date", "user_id", "logged_at"),
    )


class ExerciseLog(Base):
    """Sessão de treino (espelha training_logs)."""
    __tablename__ = "exercise_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    workout_type: Mapped[str] = mapped_column(String(80))  # UPPER_A | LOWER_A | CARDIO_HIIT | ...
    exercises: Mapped[dict] = mapped_column(JSON, default=list)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    perceived_effort: Mapped[int | None] = mapped_column(Integer)  # RPE 1-10
    pain_report: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    completed: Mapped[bool] = mapped_column(Boolean, default=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class Checkin(Base):
    """Check-in de humor, fome, sono, água."""
    __tablename__ = "checkins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(50), default="general")
    mood: Mapped[str | None] = mapped_column(String(50))
    hunger_level: Mapped[int | None] = mapped_column(Integer)  # 1-10
    sleep_hours: Mapped[float | None] = mapped_column(Numeric(4, 2))
    water_liters: Mapped[float | None] = mapped_column(Numeric(4, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class AgentMessage(Base):
    """Mensagem trocada com um agente (inbound/outbound)."""
    __tablename__ = "agent_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    agent: Mapped[str] = mapped_column(String(50))  # master | nutri | personal
    direction: Mapped[str] = mapped_column(String(20))  # inbound | outbound
    message: Mapped[str] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(String(50))
    extra: Mapped[dict] = mapped_column(JSON, default=dict)  # classification, detecção de refeição
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    __table_args__ = (
        Index("idx_agent_messages_user_date", "user_id", "created_at"),
    )
