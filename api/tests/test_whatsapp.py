"""
test_whatsapp.py — espelhamento opcional das respostas do chat pro
WhatsApp via Evolution API. Desligado por padrão (whatsapp_enabled=False);
qualquer falha de rede/API é capturada e nunca quebra o chat. Não faz
nenhuma chamada de rede real.
"""
import httpx

from app.services import whatsapp


def test_is_enabled_false_por_padrao_sem_config_no_env():
    # settings.evolution_api_key/instance vazios no ambiente de teste
    assert whatsapp.is_enabled(enabled=True, target_number="553199674109") is False


def test_is_enabled_false_sem_numero():
    assert whatsapp.is_enabled(enabled=True, target_number="") is False


def test_is_enabled_false_com_enabled_false():
    assert whatsapp.is_enabled(enabled=False, target_number="553199674109") is False


def test_jid_adiciona_sufixo():
    assert whatsapp.to_jid("553199674109") == "553199674109@s.whatsapp.net"


def test_jid_nao_duplica_sufixo_se_ja_tiver():
    assert whatsapp.to_jid("553199674109@s.whatsapp.net") == "553199674109@s.whatsapp.net"


def test_send_message_retorna_none_sem_credenciais():
    # EVOLUTION_API_KEY/INSTANCE vazios no ambiente de teste — não tenta rede
    assert whatsapp.send_message("553199674109", "oi") is None


def test_send_message_retorna_none_sem_numero(monkeypatch):
    monkeypatch.setattr(whatsapp.settings, "evolution_api_key", "fake-key")
    monkeypatch.setattr(whatsapp.settings, "evolution_instance", "migrar")
    assert whatsapp.send_message("", "oi") is None


def test_send_message_sucesso_retorna_id_da_mensagem(monkeypatch):
    monkeypatch.setattr(whatsapp.settings, "evolution_api_key", "fake-key")
    monkeypatch.setattr(whatsapp.settings, "evolution_instance", "migrar")

    class _FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"key": {"id": "3EB0ABC123", "fromMe": True, "remoteJid": "553199674109@s.whatsapp.net"}}

    monkeypatch.setattr(whatsapp.httpx, "post", lambda *a, **k: _FakeResponse())

    assert whatsapp.send_message("553199674109", "oi") == "3EB0ABC123"


def test_send_message_falha_de_rede_vira_none_nao_levanta(monkeypatch):
    monkeypatch.setattr(whatsapp.settings, "evolution_api_key", "fake-key")
    monkeypatch.setattr(whatsapp.settings, "evolution_instance", "migrar")

    def _explode(*a, **k):
        raise httpx.ConnectError("sem rede")

    monkeypatch.setattr(whatsapp.httpx, "post", _explode)

    assert whatsapp.send_message("553199674109", "oi") is None


def test_extract_text_conversation():
    assert whatsapp.extract_text({"conversation": "oi"}) == "oi"


def test_extract_text_extended_text_message():
    assert whatsapp.extract_text({"extendedTextMessage": {"text": "oi"}}) == "oi"


def test_extract_text_midia_sem_legenda_retorna_none():
    assert whatsapp.extract_text({"imageMessage": {}}) is None


def test_extract_text_vazio_retorna_none():
    assert whatsapp.extract_text({}) is None
    assert whatsapp.extract_text(None) is None


def test_test_connection_sem_credenciais():
    r = whatsapp.test_connection()
    assert r["ok"] is False
    assert "EVOLUTION_API_KEY" in r["error"]


def test_test_connection_instancia_aberta(monkeypatch):
    monkeypatch.setattr(whatsapp.settings, "evolution_api_key", "fake-key")
    monkeypatch.setattr(whatsapp.settings, "evolution_instance", "migrar")

    class _FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"instance": {"instanceName": "migrar", "state": "open"}}

    monkeypatch.setattr(whatsapp.httpx, "get", lambda *a, **k: _FakeResponse())

    r = whatsapp.test_connection()
    assert r == {"ok": True, "state": "open"}


def test_test_connection_instancia_fechada(monkeypatch):
    monkeypatch.setattr(whatsapp.settings, "evolution_api_key", "fake-key")
    monkeypatch.setattr(whatsapp.settings, "evolution_instance", "migrar")

    class _FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"instance": {"instanceName": "migrar", "state": "close"}}

    monkeypatch.setattr(whatsapp.httpx, "get", lambda *a, **k: _FakeResponse())

    r = whatsapp.test_connection()
    assert r["ok"] is False
    assert r["state"] == "close"


# ── Endpoints /api/v1/whatsapp/* ──────────────────────────────────────────

def test_endpoint_whatsapp_status_desabilitado_por_padrao(client):
    r = client.get("/api/v1/whatsapp/status")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    assert body["target_number"] is None


def test_endpoint_whatsapp_config_get_cria_com_defaults(client):
    r = client.get("/api/v1/whatsapp/config")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    assert body["target_number"] == ""


def test_endpoint_whatsapp_config_put_troca_numero(client):
    r = client.put("/api/v1/whatsapp/config", json={"enabled": True, "target_number": "553199674109"})
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert body["target_number"] == "553199674109"

    r2 = client.get("/api/v1/whatsapp/config")
    assert r2.json()["target_number"] == "553199674109"


def test_endpoint_whatsapp_test_usa_service_mockado(monkeypatch, client):
    monkeypatch.setattr(whatsapp, "test_connection", lambda: {"ok": False, "error": "instância fechada"})
    r = client.post("/api/v1/whatsapp/test")
    assert r.status_code == 200
    assert r.json() == {"ok": False, "state": None, "error": "instância fechada"}


# ── Integração com /api/v1/chat ───────────────────────────────────────────

def test_chat_nao_manda_whatsapp_quando_desabilitado(client):
    r = client.post("/api/v1/chat", json={"message": "oi"})
    assert r.json()["whatsapp_sent"] is False


def test_chat_manda_whatsapp_quando_habilitado(monkeypatch, client):
    client.put("/api/v1/whatsapp/config", json={"enabled": True, "target_number": "553199674109"})

    # is_enabled() também exige EVOLUTION_API_KEY/INSTANCE configurados
    # (infra) — vazios por padrão no ambiente de teste
    monkeypatch.setattr(whatsapp.settings, "evolution_api_key", "fake-key")
    monkeypatch.setattr(whatsapp.settings, "evolution_instance", "migrar")

    captured = {}

    def _fake_send(target_number, text):
        captured["target_number"] = target_number
        captured["text"] = text
        return "3EB0ABC123"

    monkeypatch.setattr(whatsapp, "send_message", _fake_send)

    r = client.post("/api/v1/chat", json={"message": "oi"})
    body = r.json()

    assert body["whatsapp_sent"] is True
    assert captured["target_number"] == "553199674109"
    assert captured["text"] == body["reply"]

    # o ID da mensagem enviada fica gravado no histórico, pro webhook
    # reconhecer e não duplicar quando ela ecoar de volta
    history = client.get("/api/v1/chat/history").json()
    outbound = [h for h in history if h["direction"] == "outbound"][-1]
    assert outbound["source"] == "web"


def test_chat_falha_no_envio_whatsapp_nao_quebra_a_resposta(monkeypatch, client):
    monkeypatch.setattr(whatsapp.settings, "evolution_api_key", "fake-key")
    monkeypatch.setattr(whatsapp.settings, "evolution_instance", "migrar")
    client.put("/api/v1/whatsapp/config", json={"enabled": True, "target_number": "553199674109"})
    monkeypatch.setattr(whatsapp, "send_message", lambda target_number, text: None)

    r = client.post("/api/v1/chat", json={"message": "oi"})
    assert r.status_code == 200
    assert r.json()["whatsapp_sent"] is False


def test_chat_persist_false_nao_manda_whatsapp(monkeypatch, client):
    monkeypatch.setattr(whatsapp.settings, "evolution_api_key", "fake-key")
    monkeypatch.setattr(whatsapp.settings, "evolution_instance", "migrar")
    client.put("/api/v1/whatsapp/config", json={"enabled": True, "target_number": "553199674109"})

    def _explode(target_number, text):
        raise AssertionError("send_message não deveria ser chamado com persist=False")

    monkeypatch.setattr(whatsapp, "send_message", _explode)

    r = client.post("/api/v1/chat", json={"message": "oi", "persist": False})
    assert r.json()["whatsapp_sent"] is False


# ── POST /api/v1/whatsapp/webhook (ingestão WhatsApp → web) ───────────────

def _upsert(remote_jid: str, evo_id: str, text: str, from_me: bool) -> dict:
    return {
        "event": "messages.upsert",
        "instance": "migrar",
        "data": {
            "key": {"remoteJid": remote_jid, "fromMe": from_me, "id": evo_id},
            "pushName": "Michael Cruz",
            "message": {"conversation": text},
            "messageType": "conversation",
            "messageTimestamp": 1788460000,
        },
    }


def test_webhook_evento_desconhecido_e_ignorado(client):
    r = client.post("/api/v1/whatsapp/webhook", json={"event": "connection.update", "data": {}})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "processed" not in body  # nem chega a tentar processar — evento não é de mensagem


def test_webhook_mensagem_de_conversa_nao_configurada_e_ignorada(client):
    client.put("/api/v1/whatsapp/config", json={"enabled": False, "target_number": "553199674109"})
    payload = _upsert("559999999999@s.whatsapp.net", "MSG1", "oi", from_me=False)
    r = client.post("/api/v1/whatsapp/webhook", json=payload)
    assert r.json() == {"ok": True, "processed": 0}

    history = client.get("/api/v1/chat/history").json()
    assert history == []


def test_webhook_mensagem_do_usuario_vira_inbound_e_detecta_refeicao(client):
    client.put("/api/v1/whatsapp/config", json={"enabled": False, "target_number": "553199674109"})
    payload = _upsert(
        "553199674109@s.whatsapp.net", "MSG-REAL-1",
        "comi 200g de arroz com feijao e frango", from_me=False,
    )
    r = client.post("/api/v1/whatsapp/webhook", json=payload)
    assert r.json() == {"ok": True, "processed": 1}

    history = client.get("/api/v1/chat/history").json()
    assert len(history) == 1
    assert history[0]["direction"] == "inbound"
    assert history[0]["source"] == "whatsapp"
    assert history[0]["intent"] == "ED_NUTRI"

    # unifica os totais — a refeição detectada foi persistida de verdade
    today = client.get("/api/v1/meals/today").json()
    assert today["kcal"] > 0


def test_webhook_mensagem_do_usuario_detecta_agua_e_treino(client):
    client.put("/api/v1/whatsapp/config", json={"enabled": False, "target_number": "553199674109"})
    client.post("/api/v1/whatsapp/webhook", json=_upsert(
        "553199674109@s.whatsapp.net", "MSG-AGUA-1", "bebi 500ml de água", from_me=False,
    ))
    client.post("/api/v1/whatsapp/webhook", json=_upsert(
        "553199674109@s.whatsapp.net", "MSG-TREINO-1", "treinei hoje, foi pesado", from_me=False,
    ))

    today = client.get("/api/v1/meals/today").json()
    assert today["agua_ml"] == 500.0

    workouts = client.get("/api/v1/workouts").json()
    assert len(workouts) == 1
    assert workouts[0]["completed"] is True


def test_webhook_resposta_de_quem_ja_responde_no_whatsapp_vira_outbound(client):
    client.put("/api/v1/whatsapp/config", json={"enabled": False, "target_number": "553199674109"})
    payload = _upsert(
        "553199674109@s.whatsapp.net", "MSG-BOT-1", "Boa! Anotei sua refeição aqui 💪", from_me=True,
    )
    r = client.post("/api/v1/whatsapp/webhook", json=payload)
    assert r.json() == {"ok": True, "processed": 1}

    history = client.get("/api/v1/chat/history").json()
    assert len(history) == 1
    assert history[0]["direction"] == "outbound"
    assert history[0]["source"] == "whatsapp"
    assert history[0]["agent"] == "whatsapp"

    # mensagem só refletida — não gera side-effect de refeição/água/treino
    today = client.get("/api/v1/meals/today").json()
    assert today["kcal"] == 0


def test_webhook_nao_duplica_mensagem_que_o_proprio_app_ja_enviou(monkeypatch, client):
    """Regressão do risco de duplicata: uma mensagem que o health-agents
    mandou via POST /chat (com evolution_message_id gravado) não pode
    virar uma SEGUNDA entrada no histórico quando o webhook ecoa ela de
    volta."""
    monkeypatch.setattr(whatsapp.settings, "evolution_api_key", "fake-key")
    monkeypatch.setattr(whatsapp.settings, "evolution_instance", "migrar")
    client.put("/api/v1/whatsapp/config", json={"enabled": True, "target_number": "553199674109"})
    monkeypatch.setattr(whatsapp, "send_message", lambda target_number, text: "MSG-NOSSA-1")

    client.post("/api/v1/chat", json={"message": "oi"})
    assert len(client.get("/api/v1/chat/history").json()) == 2  # inbound (web) + outbound (web)

    # a Evolution ecoa a mensagem que nós mesmos mandamos
    payload = _upsert("553199674109@s.whatsapp.net", "MSG-NOSSA-1", "qualquer coisa", from_me=True)
    r = client.post("/api/v1/whatsapp/webhook", json=payload)
    assert r.json() == {"ok": True, "processed": 0}  # ignorada, já registrada

    assert len(client.get("/api/v1/chat/history").json()) == 2  # não duplicou


def test_webhook_retry_do_mesmo_evento_e_idempotente(client):
    client.put("/api/v1/whatsapp/config", json={"enabled": False, "target_number": "553199674109"})
    payload = _upsert("553199674109@s.whatsapp.net", "MSG-RETRY-1", "oi", from_me=False)

    r1 = client.post("/api/v1/whatsapp/webhook", json=payload)
    r2 = client.post("/api/v1/whatsapp/webhook", json=payload)  # Evolution reenviando o mesmo evento

    assert r1.json() == {"ok": True, "processed": 1}
    assert r2.json() == {"ok": True, "processed": 0}
    assert len(client.get("/api/v1/chat/history").json()) == 1


def test_webhook_midia_sem_legenda_e_ignorada(client):
    client.put("/api/v1/whatsapp/config", json={"enabled": False, "target_number": "553199674109"})
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "553199674109@s.whatsapp.net", "fromMe": False, "id": "MSG-IMG-1"},
            "message": {"imageMessage": {}},
        },
    }
    r = client.post("/api/v1/whatsapp/webhook", json=payload)
    assert r.json() == {"ok": True, "processed": 0}


def test_webhook_lista_de_mensagens_processa_cada_uma(client):
    client.put("/api/v1/whatsapp/config", json={"enabled": False, "target_number": "553199674109"})
    payload = {
        "event": "MESSAGES_UPSERT",
        "data": [
            _upsert("553199674109@s.whatsapp.net", "MSG-A", "oi", from_me=False)["data"],
            _upsert("553199674109@s.whatsapp.net", "MSG-B", "tudo bem?", from_me=False)["data"],
        ],
    }
    r = client.post("/api/v1/whatsapp/webhook", json=payload)
    assert r.json() == {"ok": True, "processed": 2}
    assert len(client.get("/api/v1/chat/history").json()) == 2
