"""
test_llm.py — garante que o caminho do LLM é opt-in (desligado por padrão,
sem tocar rede), que a config vem do banco (editável via API, sem
restart), e que qualquer falha do LLM cai pro determinístico sem quebrar
o chat. Não faz nenhuma chamada de rede real.
"""
import httpx

from app.services import agents, classifier, llm


_FAKE_CATALOG = [
    {
        "id": "inclusionai/ling-3.0-flash-fin:free",
        "name": "Ling 3.0 Flash Fin (free)",
        "context_length": 262144,
        "pricing": {"prompt": "0", "completion": "0"},
    },
    {
        "id": "anthropic/claude-haiku-4.5",
        "name": "Claude Haiku 4.5",
        "context_length": 200000,
        "pricing": {"prompt": "0.000001", "completion": "0.000005"},
    },
]


def test_parse_models_free_only():
    result = llm._parse_models(_FAKE_CATALOG, free_only=True)
    assert len(result) == 1
    assert result[0]["id"] == "inclusionai/ling-3.0-flash-fin:free"
    assert result[0]["is_free"] is True


def test_parse_models_todos():
    result = llm._parse_models(_FAKE_CATALOG, free_only=False)
    assert len(result) == 2
    ids = {m["id"] for m in result}
    assert ids == {"inclusionai/ling-3.0-flash-fin:free", "anthropic/claude-haiku-4.5"}
    pago = next(m for m in result if m["id"] == "anthropic/claude-haiku-4.5")
    assert pago["is_free"] is False


def test_list_models_retorna_vazio_em_falha_de_rede(monkeypatch):
    def _explode(*args, **kwargs):
        raise httpx.ConnectError("sem rede")

    monkeypatch.setattr(llm.httpx, "get", _explode)
    assert llm.list_models() == []


def test_strip_markdown_fence_remove_cerca_json():
    raw = '```json\n{"ok": true}\n```'
    assert llm._strip_markdown_fence(raw) == '{"ok": true}'


def test_strip_markdown_fence_sem_cerca_nao_muda():
    raw = '{"ok": true}'
    assert llm._strip_markdown_fence(raw) == '{"ok": true}'


def test_llm_desabilitado_por_padrao():
    assert llm.is_enabled(enabled=True, model="algum/modelo") is False  # sem OPENROUTER_API_KEY no .env de teste
    assert llm.is_enabled(enabled=False, model="algum/modelo") is False
    assert llm.is_enabled(enabled=True, model="") is False


def test_classify_via_llm_retorna_none_se_desabilitado():
    assert llm.classify_via_llm("qualquer coisa", model="algum/modelo") is None


def test_generate_reply_via_llm_retorna_none_se_desabilitado():
    assert llm.generate_reply_via_llm("nutri", "qualquer coisa", {}, model="algum/modelo") is None


def test_classify_smart_cai_pro_determinístico_com_llm_desabilitado():
    r = classifier.classify_smart("comi 100g de arroz")
    assert r.intent == "ED_NUTRI"


def test_classify_smart_safety_nunca_chama_llm(monkeypatch):
    """Mesmo com LLM 'habilitado', SAFETY_ALERT tem que ser resolvido por
    regra fixa, sem chamar classify_via_llm."""
    monkeypatch.setattr(llm, "is_enabled", lambda *a, **k: True)

    def _explode(text, model):
        raise AssertionError("classify_via_llm não deveria ser chamado pra SAFETY_ALERT")

    monkeypatch.setattr(llm, "classify_via_llm", _explode)

    r = classifier.classify_smart("to com dor no peito e falta de ar", llm_enabled=True, llm_model="x/x")
    assert r.intent == "SAFETY_ALERT"


def test_classify_smart_usa_resultado_do_llm_quando_disponivel(monkeypatch):
    monkeypatch.setattr(llm, "is_enabled", lambda *a, **k: True)
    monkeypatch.setattr(
        llm, "classify_via_llm",
        lambda text, model: classifier.Classification(
            intent="MIXED", confidence=0.77, matched_terms=(), reasoning="llm: teste",
        ),
    )
    r = classifier.classify_smart("mensagem qualquer", llm_enabled=True, llm_model="x/x")
    assert r.intent == "MIXED"
    assert r.confidence == 0.77


def test_classify_smart_cai_pro_determinístico_se_llm_falhar(monkeypatch):
    """classify_via_llm() já devolve None em qualquer erro interno — smart
    tem que cair pro classify() de regras nesse caso, sem propagar exceção."""
    monkeypatch.setattr(llm, "is_enabled", lambda *a, **k: True)
    monkeypatch.setattr(llm, "classify_via_llm", lambda text, model: None)

    r = classifier.classify_smart("comi 100g de arroz", llm_enabled=True, llm_model="x/x")
    assert r.intent == "ED_NUTRI"  # resultado do classify() de regras


def test_gerar_resposta_cai_pro_template_se_llm_falhar(monkeypatch):
    """agents.gerar_resposta() com LLM 'habilitado' mas generate_reply_via_llm
    falhando (retorna None) tem que devolver a resposta determinística de
    sempre — o chat nunca pode quebrar por causa do LLM."""
    monkeypatch.setattr(llm, "is_enabled", lambda *a, **k: True)
    monkeypatch.setattr(llm, "generate_reply_via_llm", lambda agent, user_msg, context, model: None)

    reply = agents.gerar_resposta(
        intent="ED_NUTRI",
        user_msg="comi 100g de arroz",
        profile=agents.DEFAULT_USER_PROFILE,
        today_totals={"kcal": 0, "P": 0, "F": 0, "C": 0, "agua_ml": 0},
        llm_enabled=True,
        llm_model="x/x",
    )
    assert reply.agent == "nutri"
    assert "ED o Nutri" in reply.text  # template determinístico, não o do LLM


def test_gerar_resposta_usa_texto_do_llm_mas_macros_continuam_deterministicos(monkeypatch):
    monkeypatch.setattr(llm, "is_enabled", lambda *a, **k: True)
    monkeypatch.setattr(
        llm, "generate_reply_via_llm",
        lambda agent, user_msg, context, model: "resposta gerada pelo llm de teste",
    )

    reply = agents.gerar_resposta(
        intent="ED_NUTRI",
        user_msg="comi 200g de arroz com feijao e frango",
        profile=agents.DEFAULT_USER_PROFILE,
        today_totals={"kcal": 0, "P": 0, "F": 0, "C": 0, "agua_ml": 0},
        llm_enabled=True,
        llm_model="x/x",
    )
    assert reply.text == "resposta gerada pelo llm de teste"
    # macros continuam vindas de estimate_macros(), nunca do LLM
    assert reply.detected_meal is not None
    assert reply.detected_meal["F"] == 5
    assert reply.detected_meal["C"] == 69


def test_gerar_resposta_safety_alert_nunca_chama_llm(monkeypatch):
    monkeypatch.setattr(llm, "is_enabled", lambda *a, **k: True)

    def _explode(agent, user_msg, context, model):
        raise AssertionError("generate_reply_via_llm não deveria ser chamado pra SAFETY_ALERT")

    monkeypatch.setattr(llm, "generate_reply_via_llm", _explode)

    reply = agents.gerar_resposta(
        intent="SAFETY_ALERT", user_msg="quero morrer", llm_enabled=True, llm_model="x/x",
    )
    assert reply.intent == "SAFETY_ALERT"
    assert "SAMU" in reply.text


# ── Endpoints /api/v1/llm/* ───────────────────────────────────────────────

def test_endpoint_llm_status_desabilitado_por_padrao(client):
    r = client.get("/api/v1/llm/status")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    assert body["model"] is None


def test_endpoint_llm_config_get_cria_com_defaults(client):
    r = client.get("/api/v1/llm/config")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    assert body["model"] == ""


def test_endpoint_llm_config_put_troca_o_modelo(client):
    r = client.put("/api/v1/llm/config", json={"enabled": True, "model": "meta-llama/llama-3.1-8b:free"})
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert body["model"] == "meta-llama/llama-3.1-8b:free"

    # persistiu — uma nova leitura reflete o valor trocado, sem restart
    r2 = client.get("/api/v1/llm/config")
    assert r2.json()["model"] == "meta-llama/llama-3.1-8b:free"


def test_endpoint_llm_models_usa_catalogo_mockado(monkeypatch, client):
    monkeypatch.setattr(llm, "list_models", lambda free_only=False: [{"id": "fake/model:free"}])
    r = client.get("/api/v1/llm/models?free_only=true")
    assert r.status_code == 200
    assert r.json() == {"models": [{"id": "fake/model:free"}]}
