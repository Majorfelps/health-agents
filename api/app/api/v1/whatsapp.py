"""
whatsapp.py (router) — endpoints pro espelhamento opcional das respostas
do chat web também no WhatsApp (Evolution API).

O toggle/número é feito aqui (GET/PUT /whatsapp/config), persistido no
banco (WhatsAppConfig, singleton) — passa a valer no próximo request de
chat, sem restart. Credenciais da Evolution API (EVOLUTION_API_KEY/URL/
INSTANCE) só vivem no .env — não editáveis por aqui.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas import schemas as s
from app.services import whatsapp as whatsapp_service
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
