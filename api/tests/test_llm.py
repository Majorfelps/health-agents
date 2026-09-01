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


def test_gerar_resposta_llm_recebe_memoria_do_dia_no_contexto(monkeypatch):
    """Regressão: refeições já registradas hoje, água detectada nesta
    mensagem e status do treino do dia têm que chegar no contexto passado
    pro LLM — sem isso ele só via totais agregados, sem saber o que
    realmente já tinha acontecido."""
    captured = {}

    def _fake_generate(agent, user_msg, context, model):
        captured["context"] = context
        return "ok"

    monkeypatch.setattr(llm, "is_enabled", lambda *a, **k: True)
    monkeypatch.setattr(llm, "generate_reply_via_llm", _fake_generate)

    agents.gerar_resposta(
        intent="MIXED",
        user_msg="bebi 300ml de água e já treinei",
        profile=agents.DEFAULT_USER_PROFILE,
        today_totals={"kcal": 500, "P": 30, "F": 10, "C": 60, "agua_ml": 0},
        protocolo=None,
        llm_enabled=True,
        llm_model="x/x",
        meals_today=[{"descricao": "arroz com frango", "kcal": 497, "P": 41, "F": 5, "C": 69}],
        water_detected_ml=300.0,
        workout_logged_today=False,
    )

    ctx = captured["context"]
    assert ctx["agua_detectada_nesta_mensagem_ml"] == 300.0
    assert ctx["nutricao"]["refeicoes_ja_registradas_hoje"] == [
        {"descricao": "arroz com frango", "kcal": 497, "P": 41, "F": 5, "C": 69}
    ]
    assert ctx["treino_de_hoje_ja_registrado_como_concluido"] is False


def test_gerar_resposta_llm_anexa_imagem_de_exercicio_mencionado(monkeypatch):
    """image_url é sempre resolvido por regra fixa (exercise_images.py, com
    base no wger.de), nunca inventado pelo LLM — mas o contexto avisa o LLM
    que uma imagem foi anexada, pra ele poder referenciar naturalmente."""
    from app.services.exercise_images import EXERCISE_IMAGES

    captured = {}

    def _fake_generate(agent, user_msg, context, model):
        captured["context"] = context
        return "ok"

    monkeypatch.setattr(llm, "is_enabled", lambda *a, **k: True)
    monkeypatch.setattr(llm, "generate_reply_via_llm", _fake_generate)

    reply = agents.gerar_resposta(
        intent="TED_PERSONAL",
        user_msg="como faz o supino reto barra?",
        profile=agents.DEFAULT_USER_PROFILE,
        llm_enabled=True,
        llm_model="x/x",
    )

    assert reply.image_url == EXERCISE_IMAGES["Supino reto barra"]
    assert captured["context"]["imagem_de_demonstracao_anexada_nesta_resposta"] is True


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


# ── test_model() (botão "Testar modelo" da tela de Configurações) ─────────

class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc

    def create(self, **kwargs):
        if self._exc is not None:
            raise self._exc
        return self._response


class _FakeClient:
    def __init__(self, completions: _FakeCompletions):
        self.chat = type("_Chat", (), {"completions": completions})()


def test_test_model_sem_model():
    assert llm.test_model("") == {"ok": False, "error": "Informe um modelo."}


def test_test_model_sem_api_key_configurada():
    # settings.openrouter_api_key vazia no ambiente de teste (sem .env real)
    r = llm.test_model("qualquer/modelo")
    assert r["ok"] is False
    assert "OPENROUTER_API_KEY" in r["error"]


def test_test_model_sucesso(monkeypatch):
    fake = _FakeClient(_FakeCompletions(response=_FakeResponse("ok")))
    monkeypatch.setattr(llm, "_get_client", lambda: fake)

    r = llm.test_model("algum/modelo")
    assert r == {"ok": True, "sample": "ok"}


def test_test_model_erro_generico_vira_ok_false(monkeypatch):
    fake = _FakeClient(_FakeCompletions(exc=RuntimeError("modelo bugado")))
    monkeypatch.setattr(llm, "_get_client", lambda: fake)

    r = llm.test_model("algum/modelo")
    assert r["ok"] is False
    assert "modelo bugado" in r["error"]


def test_endpoint_llm_test_usa_service_mockado(monkeypatch, client):
    monkeypatch.setattr(llm, "test_model", lambda model: {"ok": False, "error": "403 recusado"})
    r = client.post("/api/v1/llm/test", json={"model": "algum/modelo:free"})
    assert r.status_code == 200
    assert r.json() == {"ok": False, "sample": None, "error": "403 recusado"}
