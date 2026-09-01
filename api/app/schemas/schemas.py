"""
schemas.py — Schemas Pydantic (entrada/saída de API).
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ── User ─────────────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    whatsapp_number: str
    name: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    height_cm: Optional[int] = None
    weight_kg: Optional[float] = None
    goal: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


# ── Plan Nutrition ──────────────────────────────────────────────────────────

class PlanNutritionIn(BaseModel):
    tdee: int
    meta_kcal: int
    meta_p: int
    meta_f: int
    meta_c: int
    meta_agua_ml: int
    refeicoes_meta: dict = Field(default_factory=dict)


class PlanNutritionOut(PlanNutritionIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    updated_at: datetime


# ── Plan Training ───────────────────────────────────────────────────────────

class PlanTrainingIn(BaseModel):
    protocolo: dict
    ativo: bool = True


class PlanTrainingOut(PlanTrainingIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    updated_at: datetime


# ── Meal ─────────────────────────────────────────────────────────────────────

class MealIn(BaseModel):
    meal_type: str  # cafe|almoco|lanche|janta|ceia
    description: str
    opcao: Optional[str] = None  # A|B|C
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    source: str = "chat"


class MealOut(MealIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    logged_at: datetime


# ── Exercise Log ────────────────────────────────────────────────────────────

class ExerciseLogIn(BaseModel):
    workout_type: str
    exercises: list = Field(default_factory=list)
    duration_minutes: Optional[int] = None
    perceived_effort: Optional[int] = None  # RPE
    pain_report: Optional[str] = None
    notes: Optional[str] = None
    completed: bool = True


class ExerciseLogOut(ExerciseLogIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    logged_at: datetime


# ── Checkin ─────────────────────────────────────────────────────────────────

class CheckinIn(BaseModel):
    type: str = "general"
    mood: Optional[str] = None
    hunger_level: Optional[int] = None
    sleep_hours: Optional[float] = None
    water_liters: Optional[float] = None
    notes: Optional[str] = None


class CheckinOut(CheckinIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    created_at: datetime


# ── Chat ────────────────────────────────────────────────────────────────────

class ChatIn(BaseModel):
    message: str
    user_whatsapp: str = "553199674109"  # default Michael
    persist: bool = True  # se True, grava a conversa em agent_messages


class ChatOut(BaseModel):
    user_message: str
    intent: str
    confidence: float
    matched_terms: list
    reasoning: str
    agent: str
    reply: str
    detected_meal: Optional[dict] = None
    detected_water_ml: Optional[float] = None
    detected_workout: bool = False
    image_url: Optional[str] = None
    metadata: Optional[dict] = None
    message_id: Optional[int] = None


# ── Dashboard ───────────────────────────────────────────────────────────────

class DashboardTotals(BaseModel):
    kcal: float = 0
    P: float = 0
    F: float = 0
    C: float = 0
    agua_ml: float = 0


class DashboardOut(BaseModel):
    user: UserOut
    plan_nutrition: Optional[PlanNutritionOut] = None
    plan_training: Optional[PlanTrainingOut] = None
    today: DashboardTotals
    last_7_days: dict  # {date: totals}
    workout_today: Optional[dict] = None  # do plano
    last_checkin: Optional[CheckinOut] = None


# ── LLM config ──────────────────────────────────────────────────────────────

class LLMConfigIn(BaseModel):
    enabled: bool
    model: str = ""  # slug do OpenRouter, ex: "anthropic/claude-haiku-4.5" — ver GET /llm/models


class LLMConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    enabled: bool
    model: str
    updated_at: datetime


class LLMTestIn(BaseModel):
    model: str


class LLMTestOut(BaseModel):
    ok: bool
    sample: Optional[str] = None
    error: Optional[str] = None
