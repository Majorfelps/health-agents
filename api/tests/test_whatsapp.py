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
    assert whatsapp._jid("553199674109") == "553199674109@s.whatsapp.net"


def test_jid_nao_duplica_sufixo_se_ja_tiver():
    assert whatsapp._jid("553199674109@s.whatsapp.net") == "553199674109@s.whatsapp.net"


def test_send_message_retorna_false_sem_credenciais():
    # EVOLUTION_API_KEY/INSTANCE vazios no ambiente de teste — não tenta rede
    assert whatsapp.send_message("553199674109", "oi") is False


def test_send_message_retorna_false_sem_numero(monkeypatch):
    monkeypatch.setattr(whatsapp.settings, "evolution_api_key", "fake-key")
    monkeypatch.setattr(whatsapp.settings, "evolution_instance", "migrar")
    assert whatsapp.send_message("", "oi") is False


def test_send_message_sucesso(monkeypatch):
    monkeypatch.setattr(whatsapp.settings, "evolution_api_key", "fake-key")
    monkeypatch.setattr(whatsapp.settings, "evolution_instance", "migrar")

    class _FakeResponse:
        def raise_for_status(self):
            pass

    monkeypatch.setattr(whatsapp.httpx, "post", lambda *a, **k: _FakeResponse())

    assert whatsapp.send_message("553199674109", "oi") is True


def test_send_message_falha_de_rede_vira_false_nao_levanta(monkeypatch):
    monkeypatch.setattr(whatsapp.settings, "evolution_api_key", "fake-key")
    monkeypatch.setattr(whatsapp.settings, "evolution_instance", "migrar")

    def _explode(*a, **k):
        raise httpx.ConnectError("sem rede")

    monkeypatch.setattr(whatsapp.httpx, "post", _explode)

    assert whatsapp.send_message("553199674109", "oi") is False


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
        return True

    monkeypatch.setattr(whatsapp, "send_message", _fake_send)

    r = client.post("/api/v1/chat", json={"message": "oi"})
    body = r.json()

    assert body["whatsapp_sent"] is True
    assert captured["target_number"] == "553199674109"
    assert captured["text"] == body["reply"]


def test_chat_falha_no_envio_whatsapp_nao_quebra_a_resposta(monkeypatch, client):
    monkeypatch.setattr(whatsapp.settings, "evolution_api_key", "fake-key")
    monkeypatch.setattr(whatsapp.settings, "evolution_instance", "migrar")
    client.put("/api/v1/whatsapp/config", json={"enabled": True, "target_number": "553199674109"})
    monkeypatch.setattr(whatsapp, "send_message", lambda target_number, text: False)

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
