"""
chat.py — POST /chat e GET /chat/history.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_or_create_current_user
from app.core.db import get_db
from app.models import models as m
from app.schemas import schemas as s
from app.services import classifier, agents, repository as repo

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=s.ChatOut)
def chat(
    payload: s.ChatIn,
    db: Session = Depends(get_db),
):
    """Classifica a mensagem, despacha para o agente certo, persiste conversa."""
    user = repo.get_or_create_user(db, payload.user_whatsapp)
    repo.seed_default_plans(db, user)

    # 1. Classificar (LLM opcional, config vem do banco — editável via API)
    llm_cfg = repo.get_llm_config(db)
    cls = classifier.classify_smart(payload.message, llm_enabled=llm_cfg.enabled, llm_model=llm_cfg.model)

    # 2. Carregar perfil (do user + plan_nutrition)
    plan = user.plan_nutrition
    profile = {
        "name": user.name or "usuário",
        "age": user.age or 33,
        "sex": user.sex or "M",
        "weight_kg": float(user.weight_kg) if user.weight_kg else 93.0,
        "height_cm": user.height_cm or 180,
        "tdee": plan.tdee if plan else 2274,
        "meta_kcal": plan.meta_kcal if plan else 1770,
        "meta_p": plan.meta_p if plan else 186,
        "meta_f": plan.meta_f if plan else 70,
        "meta_c": plan.meta_c if plan else 165,
        "meta_agua_ml": plan.meta_agua_ml if plan else 2500,
    }

    # 3. Totais do dia (para a resposta do Nutri ser contextual)
    today_totals = repo.today_totals(db, user.id)

    # 4. Gerar resposta
    protocolo = user.plan_training.protocolo if user.plan_training else None
    reply = agents.gerar_resposta(
        intent=cls.intent,
        user_msg=payload.message,
        profile=profile,
        today_totals=today_totals,
        protocolo=protocolo,
        llm_enabled=llm_cfg.enabled,
        llm_model=llm_cfg.model,
    )

    # 5. Se o agente detectou refeição, grava em meals
    message_id = None
    extra = {
        "intent": cls.intent,
        "confidence": cls.confidence,
        "matched_terms": list(cls.matched_terms),
        "reasoning": cls.reasoning,
    }

    if payload.persist:
        # inbound
        in_msg = m.AgentMessage(
            user_id=user.id,
            agent=reply.agent,
            direction="inbound",
            message=payload.message,
            intent=cls.intent,
            extra=extra,
        )
        db.add(in_msg)
        db.flush()
        # outbound
        out_msg = m.AgentMessage(
            user_id=user.id,
            agent=reply.agent,
            direction="outbound",
            message=reply.text,
            intent=cls.intent,
            extra=extra,
        )
        db.add(out_msg)
        db.flush()
        message_id = out_msg.id

        # Se refeição detectada, cria Meal
        if reply.detected_meal:
            meal = m.Meal(
                user_id=user.id,
                meal_type=_infer_meal_type(payload.message),
                description=reply.detected_meal["descricao"],
                calories=reply.detected_meal["kcal"],
                protein_g=reply.detected_meal["P"],
                carbs_g=reply.detected_meal["C"],
                fat_g=reply.detected_meal["F"],
                source="chat",
            )
            db.add(meal)

        db.commit()

    return s.ChatOut(
        user_message=payload.message,
        intent=cls.intent,
        confidence=cls.confidence,
        matched_terms=list(cls.matched_terms),
        reasoning=cls.reasoning,
        agent=reply.agent,
        reply=reply.text,
        detected_meal=reply.detected_meal,
        metadata=extra,
        message_id=message_id,
    )


def _infer_meal_type(text: str) -> str:
    """Heurística simples para categorizar refeição (espelha o que master_agent faz
    quando há contexto suficiente — aqui é fallback quando não há contexto prévio)."""
    import unicodedata
    t = unicodedata.normalize("NFD", text.lower()).encode("ascii", "ignore").decode()
    if "cafe" in t or "café" in t:
        return "cafe"
    if "almo" in t:
        return "almoco"
    if "janta" in t or "jantar" in t:
        return "janta"
    if "lanche" in t:
        return "lanche"
    if "ceia" in t:
        return "ceia"
    return "outro"


@router.get("/history")
def history(
    user_whatsapp: str = Query("553199674109"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    user = repo.get_or_create_user(db, user_whatsapp)
    msgs = repo.recent_messages(db, user.id, limit=limit)
    # Mensagens em ordem cronológica (mais antiga → mais nova)
    msgs = list(reversed(msgs))
    return [
        {
            "id": m.id,
            "agent": m.agent,
            "direction": m.direction,
            "message": m.message,
            "intent": m.intent,
            "created_at": m.created_at.isoformat(),
        }
        for m in msgs
    ]
