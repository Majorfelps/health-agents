"""
whatsapp.py (router) — endpoints pro espelhamento opcional das respostas
do chat web também no WhatsApp (Evolution API), nos dois sentidos:

- GET/PUT /whatsapp/config: toggle/número, persistido no banco
  (WhatsAppConfig, singleton) — passa a valer no próximo request, sem
  restart. Credenciais da Evolution API (EVOLUTION_API_KEY/URL/INSTANCE)
  só vivem no .env — não editáveis por aqui.
- POST /whatsapp/webhook: recebe eventos da Evolution API (configurado
  fora desta aplicação, via POST /webhook/set — ver README § "Espelhamento
  pro WhatsApp") e reflete a conversa (dos dois lados) no histórico do
  chat web, sem nunca gerar/enviar resposta própria — quem responde no
  WhatsApp continua sendo o sistema que já responde lá (ver
  docs/correcoes-e-melhorias.md pra contexto completo dessa decisão).
"""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import models as m
from app.schemas import schemas as s
from app.services import agents, classifier, whatsapp as whatsapp_service
from app.services import repository as repo

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.get("/config", response_model=s.WhatsAppConfigOut)
def get_config(db: Session = Depends(get_db)):
    """Config atual do espelhamento pro WhatsApp (não expõe a API key —
    essa só vive no .env)."""
    return repo.get_whatsapp_config(db)


@router.put("/config", response_model=s.WhatsAppConfigOut)
def update_config(payload: s.WhatsAppConfigIn, db: Session = Depends(get_db)):
    """Liga/desliga o espelhamento e/ou troca o número de destino. Passa a
    valer no próximo request de chat, sem restart."""
    return repo.update_whatsapp_config(db, enabled=payload.enabled, target_number=payload.target_number)


@router.get("/status")
def status(db: Session = Depends(get_db)):
    """Se o espelhamento está habilitado/configurado, e pra qual número —
    sem expor a API key. Igual a GET /whatsapp/config, formato mais enxuto."""
    cfg = repo.get_whatsapp_config(db)
    return {
        "enabled": whatsapp_service.is_enabled(cfg.enabled, cfg.target_number),
        "target_number": cfg.target_number or None,
    }


@router.post("/test", response_model=s.WhatsAppTestOut)
def test_connection():
    """Confirma que a instância da Evolution API está acessível e
    conectada (state == "open") — sem enviar mensagem nenhuma. Use antes
    de habilitar o espelhamento."""
    return whatsapp_service.test_connection()


@router.post("/webhook")
def webhook(payload: dict, db: Session = Depends(get_db)):
    """Recebe eventos `messages.upsert` da Evolution API e reflete a
    conversa configurada (`target_number`) no histórico do chat web.

    - Mensagem do usuário (fromMe=false): roda a mesma detecção de
      refeição/água/treino do chat web (mesmas regras fixas, sem LLM —
      não há resposta sendo gerada aqui) e persiste em
      Meal/Checkin/ExerciseLog, unificando os totais entre WhatsApp e
      web. NUNCA gera nem envia resposta própria — quem responde nessa
      conversa já é outro sistema.
    - Mensagem que não foi enviada por este app (fromMe=true, ID
      desconhecido): é a resposta de quem já responde nesse WhatsApp —
      só registrada pro histórico aparecer completo, sem side-effects.
    - Mensagem que ESTE app enviou via POST /chat (fromMe=true, ID já
      gravado em `evolution_message_id`): ignorada — já está no
      histórico, evita duplicar.

    Sempre responde 200 (mesmo em payload inesperado) — não sinaliza erro
    pra Evolution não ficar retentando por eventos que não processamos de
    propósito (media sem legenda, outra conversa, etc.)."""
    event = (payload.get("event") or "").upper().replace(".", "").replace("_", "")
    if event != "MESSAGESUPSERT":
        return {"ok": True, "skipped": f"evento ignorado: {payload.get('event')!r}"}

    data = payload.get("data")
    items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []

    processed = sum(1 for item in items if _ingest_message(db, item))
    return {"ok": True, "processed": processed}


def _ingest_message(db: Session, msg) -> bool:
    if not isinstance(msg, dict):
        return False
    key = msg.get("key") or {}
    evo_id = key.get("id")
    remote_jid = key.get("remoteJid") or ""
    from_me = bool(key.get("fromMe", False))
    if not evo_id or not remote_jid:
        return False

    cfg = repo.get_whatsapp_config(db)
    if not cfg.target_number or remote_jid != whatsapp_service.to_jid(cfg.target_number):
        return False  # não é a conversa configurada (ex: outro contato na mesma instância) — ignora

    already = db.query(m.AgentMessage).filter(m.AgentMessage.evolution_message_id == evo_id).first()
    if already:
        return False  # já registrada (mandada por nós via /chat, ou retry do webhook)

    text = whatsapp_service.extract_text(msg.get("message") or {})
    if not text:
        return False  # mídia sem legenda, reação, etc. — ignora por ora

    user = repo.get_or_create_user(db, cfg.target_number)
    repo.seed_default_plans(db, user)

    if from_me:
        # resposta de quem já responde esse WhatsApp — só reflete no histórico
        db.add(m.AgentMessage(
            user_id=user.id, agent="whatsapp", direction="outbound",
            message=text, intent=None, source="whatsapp",
            evolution_message_id=evo_id, extra={},
        ))
        db.commit()
        return True

    # mensagem real do usuário via WhatsApp — mesma detecção do chat web
    # (regra fixa, sem LLM: aqui não existe resposta sendo gerada, só
    # persistência), pra unificar os totais entre os dois canais.
    cls = classifier.classify(text)
    detected_meal = None
    if cls.intent == "ED_NUTRI" and classifier.looks_like_meal(text):
        detected_meal = agents.estimate_macros(text)
    water_ml = classifier.looks_like_water(text)
    workout_now = classifier.looks_like_completed_workout(text)

    db.add(m.AgentMessage(
        user_id=user.id, agent="whatsapp", direction="inbound",
        message=text, intent=cls.intent, source="whatsapp",
        evolution_message_id=evo_id,
        extra={"confidence": cls.confidence, "matched_terms": list(cls.matched_terms), "reasoning": cls.reasoning},
    ))

    if detected_meal:
        db.add(m.Meal(
            user_id=user.id,
            meal_type=agents.infer_meal_type(text),
            description=detected_meal["descricao"],
            calories=detected_meal["kcal"],
            protein_g=detected_meal["P"],
            carbs_g=detected_meal["C"],
            fat_g=detected_meal["F"],
            source="whatsapp",
        ))
    if water_ml is not None:
        db.add(m.Checkin(user_id=user.id, type="water", water_liters=water_ml / 1000))
    if workout_now:
        protocolo = user.plan_training.protocolo if user.plan_training else None
        treino = agents.resolve_treino_do_dia(protocolo, date.today().weekday())
        db.add(m.ExerciseLog(
            user_id=user.id,
            workout_type=treino["nome"],
            exercises=treino.get("exercicios", []),
            completed=True,
            notes=text,
        ))

    db.commit()
    return True
