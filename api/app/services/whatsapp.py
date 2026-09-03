"""
whatsapp.py — cliente Evolution API pra espelhar as respostas do chat web
também no WhatsApp (opcional).

Regras de robustez (mesmo espírito de llm.py):
- Qualquer falha (rede, timeout, API fora do ar, credenciais erradas) é
  capturada aqui e vira `False`/None — quem chama nunca deixa isso quebrar
  o chat. Mandar mensagem pro WhatsApp é um efeito colateral best-effort,
  nunca bloqueia a resposta do chat web.
- EVOLUTION_API_URL/KEY/INSTANCE só vêm do .env (infra, não editável por
  API). enabled/target_number ficam no banco (whatsapp_config), editáveis
  em runtime — ver repository.get_whatsapp_config().

Referência (Hermes, health/nutri-agent/references/whatsapp-evolution-api.md):
POST {EVOLUTION_API_URL}/message/sendText/{instance}
Header: apikey: <key>
Body: {"number": "<DDI+DDD+numero>@s.whatsapp.net", "text": "..."}
"""
from __future__ import annotations
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_enabled(enabled: bool, target_number: str) -> bool:
    return bool(
        enabled
        and target_number
        and settings.evolution_api_key
        and settings.evolution_instance
    )


def _jid(number: str) -> str:
    """Normaliza o número pro formato que a Evolution API espera. Aceita
    tanto '553199674109' quanto '553199674109@s.whatsapp.net'."""
    number = number.strip()
    return number if number.endswith("@s.whatsapp.net") else f"{number}@s.whatsapp.net"


def send_message(target_number: str, text: str) -> bool:
    """Envia texto pro WhatsApp via Evolution API. True se enviou (HTTP
    2xx), False em qualquer falha — nunca levanta exceção."""
    if not settings.evolution_api_key or not settings.evolution_instance:
        logger.warning("send_message chamado sem EVOLUTION_API_KEY/INSTANCE configurados no .env")
        return False
    if not target_number:
        return False

    url = f"{settings.evolution_api_url}/message/sendText/{settings.evolution_instance}"
    try:
        resp = httpx.post(
            url,
            json={"number": _jid(target_number), "text": text},
            headers={"apikey": settings.evolution_api_key, "Content-Type": "application/json"},
            timeout=15.0,
        )
        resp.raise_for_status()
        return True
    except Exception:
        logger.exception("whatsapp.send_message falhou — resposta do chat web segue normal")
        return False


def test_connection() -> dict:
    """Chamada mínima de verdade (sem enviar mensagem) — usada pelo botão
    "Testar conexão" da tela de Configurações, pra confirmar que a
    instância Evolution está acessível e conectada (`state == "open"`)
    antes de habilitar o espelhamento pro WhatsApp."""
    if not settings.evolution_api_key or not settings.evolution_instance:
        return {"ok": False, "error": "EVOLUTION_API_KEY/EVOLUTION_INSTANCE não configurados no servidor (.env)."}

    url = f"{settings.evolution_api_url}/instance/connectionState/{settings.evolution_instance}"
    try:
        resp = httpx.get(url, headers={"apikey": settings.evolution_api_key}, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        state = (data.get("instance") or {}).get("state") or data.get("state")
        if state == "open":
            return {"ok": True, "state": state}
        return {"ok": False, "state": state, "error": f"Instância '{settings.evolution_instance}' existe mas não está conectada (state={state!r})."}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"ok": False, "error": f"Instância '{settings.evolution_instance}' não encontrada na Evolution API."}
        return {"ok": False, "error": f"Erro HTTP {e.response.status_code} da Evolution API."}
    except Exception as e:
        logger.exception("whatsapp.test_connection falhou")
        return {"ok": False, "error": str(e)[:300]}
