"""
llm.py — cliente OpenRouter (API compatível com OpenAI) usado para gerar
respostas em linguagem natural e, opcionalmente, classificar intenção.

`enabled`/`model` são passados explicitamente por quem chama (vêm do banco,
via repository.get_llm_config() — editável em runtime por
PUT /api/v1/llm/config, sem restart do container). A API key e a base URL
continuam só no .env (OPENROUTER_API_KEY/OPENROUTER_BASE_URL) — não são
editáveis por API, por segurança.

Regras de segurança/robustez:
- Nunca é chamado para SAFETY_ALERT — isso é sempre resolvido por regra fixa
  em classifier.py, antes de qualquer chamada ao LLM.
- Qualquer falha (rede, timeout, API fora do ar, JSON inválido, intent
  desconhecido) é capturada aqui e vira `None` — quem chama (classifier.py /
  agents.py) cai pro caminho determinístico. O chat nunca quebra por causa
  do LLM.
- Números que vão pro banco (kcal/macros) continuam sempre calculados por
  estimate_macros() em agents.py; o LLM só escreve o texto da resposta.
"""
from __future__ import annotations
import json
import logging
from typing import Optional

import httpx
from openai import (
    OpenAI,
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: Optional[OpenAI] = None


def is_enabled(enabled: bool, model: str) -> bool:
    return bool(enabled and settings.openrouter_api_key and model)


def _parse_models(data: list[dict], free_only: bool) -> list[dict]:
    out = []
    for m in data:
        pricing = m.get("pricing", {})
        is_free = m.get("id", "").endswith(":free") or (
            str(pricing.get("prompt", "")) in ("0", "0.0")
            and str(pricing.get("completion", "")) in ("0", "0.0")
        )
        if free_only and not is_free:
            continue
        out.append({
            "id": m.get("id"),
            "name": m.get("name"),
            "context_length": m.get("context_length"),
            "is_free": is_free,
            "pricing": pricing,
        })
    return out


def list_models(free_only: bool = False) -> list[dict]:
    """Lista o catálogo público de modelos do OpenRouter (openrouter.ai/models).
    Não precisa de LLM_ENABLED nem de OPENROUTER_API_KEY configurados — é o
    catálogo público deles. Retorna [] em caso de qualquer falha de rede."""
    try:
        resp = httpx.get(f"{settings.openrouter_base_url}/models", timeout=10.0)
        resp.raise_for_status()
        data = resp.json().get("data", [])
    except Exception:
        logger.exception("list_models falhou")
        return []
    return _parse_models(data, free_only)


def _get_client() -> Optional[OpenAI]:
    global _client
    if not settings.openrouter_api_key:
        return None
    if _client is None:
        _client = OpenAI(base_url=settings.openrouter_base_url, api_key=settings.openrouter_api_key)
    return _client


def _error_message(e: Exception) -> str:
    return str(getattr(e, "message", None) or e)[:300]


def test_model(model: str) -> dict:
    """Chamada mínima de verdade pro modelo, sem persistir nada — usada
    pelo botão "Testar modelo" da tela de Configurações, pra pegar
    problemas (modelo restrito a agentic harness, nome errado, sem
    créditos, etc.) antes de salvar. Só depende de OPENROUTER_API_KEY, não
    do toggle LLM_ENABLED — testar não é o mesmo que usar em produção.

    Alguns modelos gratuitos do OpenRouter (ex.: alguns `:free` de coding
    agent) recusam chat.completions comum com 403 — daí a utilidade de
    testar antes de salvar como o modelo em uso."""
    if not model or not model.strip():
        return {"ok": False, "error": "Informe um modelo."}
    client = _get_client()
    if client is None:
        return {"ok": False, "error": "OPENROUTER_API_KEY não configurada no servidor (.env)."}

    try:
        resp = client.chat.completions.create(
            model=model,
            max_tokens=10,
            messages=[{"role": "user", "content": "Responda apenas a palavra: ok"}],
        )
        text = (resp.choices[0].message.content or "").strip()
        return {"ok": True, "sample": text[:100]}
    except PermissionDeniedError as e:
        return {"ok": False, "error": f"Modelo recusou a chamada (403 — pode ser restrito a agentic harnesses): {_error_message(e)}"}
    except NotFoundError as e:
        return {"ok": False, "error": f"Modelo não encontrado (404 — confira o slug): {_error_message(e)}"}
    except RateLimitError as e:
        return {"ok": False, "error": f"Rate limit (429 — modelos :free têm limite diário por conta): {_error_message(e)}"}
    except AuthenticationError as e:
        return {"ok": False, "error": f"OPENROUTER_API_KEY inválida (401): {_error_message(e)}"}
    except APIStatusError as e:
        return {"ok": False, "error": f"Erro da API ({e.status_code}): {_error_message(e)}"}
    except APIConnectionError:
        return {"ok": False, "error": "Erro de rede ao conectar no OpenRouter."}
    except Exception as e:
        logger.exception("test_model falhou")
        return {"ok": False, "error": _error_message(e)}


VALID_INTENTS = {"ED_NUTRI", "TED_PERSONAL", "MIXED", "ORCHESTRATOR"}


def _strip_markdown_fence(raw: str) -> str:
    """Alguns modelos envolvem JSON em ```json ... ``` mesmo quando
    instruídos a não fazer isso — remove a cerca antes de json.loads()."""
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s[3:]
        if s.endswith("```"):
            s = s[: -3]
        elif "```" in s:
            s = s.rsplit("```", 1)[0]
    return s.strip()

CLASSIFY_SYSTEM = """Você é o classificador de intenção do chat de um app de saúde (nutrição + treino).
Dada a mensagem do usuário, responda APENAS um JSON válido (sem markdown, sem texto extra), no formato:
{"intent": "...", "confidence": 0.0-1.0, "reasoning": "..."}

"intent" tem que ser exatamente um destes 4 valores:
- ED_NUTRI: fala de comida, refeição, dieta, calorias, macros, água, peso corporal
- TED_PERSONAL: fala de treino, exercício, academia, cardio, RPE, carga
- MIXED: fala claramente das duas coisas (nutrição E treino) na mesma mensagem
- ORCHESTRATOR: saudação, mensagem vaga, ou qualquer coisa que não se encaixe nas outras três

Nunca use "SAFETY_ALERT" — mensagens de risco à saúde já são tratadas antes de chegar em você."""


def classify_via_llm(text: str, model: str):
    """Retorna um Classification (de app.services.classifier) ou None em
    caso de LLM desabilitado ou qualquer falha."""
    client = _get_client()
    if client is None or not model:
        return None
    from app.services.classifier import Classification  # import tardio evita ciclo

    try:
        resp = client.chat.completions.create(
            model=model,
            max_tokens=200,
            temperature=0,
            messages=[
                {"role": "system", "content": CLASSIFY_SYSTEM},
                {"role": "user", "content": text},
            ],
        )
        raw = resp.choices[0].message.content or ""
        data = json.loads(_strip_markdown_fence(raw))
        intent = data["intent"]
        if intent not in VALID_INTENTS:
            raise ValueError(f"intent inválido do LLM: {intent!r}")
        return Classification(
            intent=intent,
            confidence=float(data.get("confidence", 0.6)),
            matched_terms=(),
            reasoning=f"llm: {data.get('reasoning', '')}"[:200],
        )
    except Exception:
        logger.exception("classify_via_llm falhou — caindo pro classificador de regras")
        return None


# A UI do chat renderiza a resposta como texto puro (sem parser de markdown)
# — sintaxe markdown aparece literal na tela (##, **, ---), por isso toda
# persona é instruída a não usar nada disso.
_FORMAT_RULES = (
    " Formatação: texto puro, SEM markdown — nada de #, ##, **negrito**, "
    "listas com -/*, ou linhas --- de separador. Pode usar *asterisco simples* "
    "pra ênfase (estilo WhatsApp) e quebras de linha normais, só isso."
)

PERSONA_SYSTEM = {
    "master": (
        "Você é o Master Agent, o orquestrador de uma equipe de saúde com dois "
        "especialistas: ED o Nutri (nutrição) e ED o Personal (treino). Tom "
        "direto e acolhedor, em português do Brasil, estilo WhatsApp com "
        "emojis moderados. No máximo 4 frases." + _FORMAT_RULES
    ),
    "nutri": (
        "Você é ED o Nutri, nutricionista virtual acolhedor e direto, em "
        "português do Brasil, estilo WhatsApp com emojis moderados (🥗📊🎯). "
        "Você recebe em JSON os totais do dia, as metas e (se detectada) a "
        "refeição estimada — comente o progresso do dia de forma natural, "
        "sem virar uma lista/tabela de números. NUNCA invente valores de "
        "calorias/macros que não estejam no JSON recebido." + _FORMAT_RULES
    ),
    "personal": (
        "Você é ED o Personal, personal trainer virtual motivador e direto, "
        "em português do Brasil, estilo WhatsApp com emojis moderados (💪🔥). "
        "Você recebe em JSON o treino do dia (nome, foco, exercícios) — "
        "apresente de forma natural e motivadora. NUNCA invente exercícios "
        "fora da lista recebida; se a lista vier vazia, oriente o usuário a "
        "cadastrar os exercícios desse treino em Planos → Treino Semanal." + _FORMAT_RULES
    ),
}


def generate_reply_via_llm(agent: str, user_msg: str, context: dict, model: str) -> Optional[str]:
    """Retorna o texto da resposta ou None em caso de LLM desabilitado ou
    qualquer falha (quem chama cai pro template determinístico)."""
    client = _get_client()
    if client is None or not model:
        return None
    system = PERSONA_SYSTEM.get(agent, PERSONA_SYSTEM["master"])
    try:
        resp = client.chat.completions.create(
            model=model,
            max_tokens=400,
            temperature=0.7,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": (
                    f"Dados disponíveis (JSON): {json.dumps(context, ensure_ascii=False)}\n\n"
                    f"Mensagem do usuário: {user_msg}"
                )},
            ],
        )
        text = resp.choices[0].message.content
        return text.strip() if text else None
    except Exception:
        logger.exception("generate_reply_via_llm falhou — caindo pro template determinístico")
        return None
