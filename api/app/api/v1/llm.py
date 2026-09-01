"""
llm.py (router) — endpoints utilitários pro LLM opcional. Não fazem parte
do fluxo de chat em si (esse continua em /chat, ver chat.py).
"""
from fastapi import APIRouter, Query

from app.core.config import settings
from app.services import llm as llm_service

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/status")
def status():
    """Se o LLM está habilitado/configurado, e qual modelo — sem expor a
    API key."""
    return {
        "enabled": llm_service.is_enabled(),
        "model": settings.openrouter_model or None,
    }


@router.get("/models")
def list_models(
    free_only: bool = Query(
        True,
        description="Só modelos gratuitos do OpenRouter (bons pra testar sem gastar) — false lista o catálogo inteiro.",
    ),
):
    """Lista o catálogo do OpenRouter. Não precisa de LLM_ENABLED nem de
    OPENROUTER_API_KEY configurados — é o catálogo público deles
    (openrouter.ai/models). Use o campo "id" como OPENROUTER_MODEL no .env."""
    return {"models": llm_service.list_models(free_only=free_only)}
