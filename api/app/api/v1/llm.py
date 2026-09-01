"""
llm.py (router) — endpoints utilitários pro LLM opcional. Não fazem parte
do fluxo de chat em si (esse continua em /chat, ver chat.py).

A troca de modelo/toggle é feita aqui (GET/PUT /llm/config), persistida no
banco (LLMConfig, singleton) — passa a valer no próximo request de chat,
sem precisar reiniciar o container.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas import schemas as s
from app.services import llm as llm_service
from app.services import repository as repo

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/config", response_model=s.LLMConfigOut)
def get_config(db: Session = Depends(get_db)):
    """Config atual do LLM (não expõe a API key — essa só vive no .env)."""
    return repo.get_llm_config(db)


@router.put("/config", response_model=s.LLMConfigOut)
def update_config(payload: s.LLMConfigIn, db: Session = Depends(get_db)):
    """Troca o modelo e/ou liga/desliga o LLM. Passa a valer no próximo
    request de chat, sem restart. Use GET /llm/models pra achar um slug
    válido de OPENROUTER_MODEL."""
    return repo.update_llm_config(db, enabled=payload.enabled, model=payload.model)


@router.get("/status")
def status(db: Session = Depends(get_db)):
    """Se o LLM está habilitado/configurado, e qual modelo — sem expor a
    API key. Igual a GET /llm/config, formato mais enxuto."""
    cfg = repo.get_llm_config(db)
    return {"enabled": llm_service.is_enabled(cfg.enabled, cfg.model), "model": cfg.model or None}


@router.post("/test", response_model=s.LLMTestOut)
def test_model(payload: s.LLMTestIn):
    """Faz uma chamada mínima de verdade pro modelo, sem salvar nada — use
    antes de PUT /llm/config pra confirmar que o modelo escolhido funciona
    pra chat comum (alguns modelos gratuitos são restritos a agentic
    harnesses e recusam com 403). Só precisa de OPENROUTER_API_KEY no
    .env, não do toggle LLM_ENABLED."""
    return llm_service.test_model(payload.model)


@router.get("/models")
def list_models(
    free_only: bool = Query(
        True,
        description="Só modelos gratuitos do OpenRouter (bons pra testar sem gastar) — false lista o catálogo inteiro.",
    ),
):
    """Lista o catálogo do OpenRouter. Não precisa de LLM_ENABLED nem de
    OPENROUTER_API_KEY configurados — é o catálogo público deles
    (openrouter.ai/models). Use o campo "id" no PUT /llm/config."""
    return {"models": llm_service.list_models(free_only=free_only)}
