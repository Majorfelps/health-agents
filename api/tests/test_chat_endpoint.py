"""
test_chat_endpoint.py — fluxo completo via TestClient: classificação →
resposta do agente → persistência → detected_meal → totais refletidos.
"""


def test_chat_saudacao_retorna_master_agent(client):
    r = client.post("/api/v1/chat", json={"message": "oi"})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "ORCHESTRATOR"
    assert body["agent"] == "master"


def test_chat_refeicao_persiste_e_aparece_em_meals_today(client):
    r = client.post("/api/v1/chat", json={
        "message": "comi 200g de arroz com feijao e frango",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "ED_NUTRI"
    assert body["detected_meal"] is not None
    detected = body["detected_meal"]

    today = client.get("/api/v1/meals/today").json()
    # today_totals() precisa bater com o que o chat estimou — regressão
    # direta pro bug da Etapa 1 (F/C trocados), agora via HTTP de ponta a ponta.
    assert today["kcal"] == detected["kcal"]
    assert today["P"] == detected["P"]
    assert today["F"] == detected["F"]
    assert today["C"] == detected["C"]


def test_chat_persist_false_nao_grava_historico(client):
    client.post("/api/v1/chat", json={"message": "oi", "persist": False})
    history = client.get("/api/v1/chat/history").json()
    assert history == []


def test_chat_history_ordem_cronologica(client):
    client.post("/api/v1/chat", json={"message": "oi"})
    client.post("/api/v1/chat", json={"message": "qual o treino de hoje?"})

    history = client.get("/api/v1/chat/history").json()
    created_ats = [h["created_at"] for h in history]
    assert created_ats == sorted(created_ats)


def test_dashboard_reflete_treino_do_plano_editado(client):
    plan = client.get("/api/v1/plan/training").json()
    protocolo = dict(plan["protocolo"])
    protocolo["0"] = "LOWER B"  # troca o treino de segunda
    client.put("/api/v1/plan/training", json={
        "protocolo": protocolo, "ativo": plan["ativo"],
    })

    dash = client.get("/api/v1/dashboard").json()
    workout_today = client.get("/api/v1/workouts/today").json()
    # ambos resolvem do mesmo plano — se um bater com a biblioteca o outro
    # também bate (senão o dashboard/workouts voltaria a ler o estático).
    assert dash["workout_today"]["nome"] == workout_today["nome"]


def test_safety_alert_nao_confunde_com_refeicao(client):
    r = client.post("/api/v1/chat", json={
        "message": "comi arroz mas to com dor no peito e falta de ar",
    })
    body = r.json()
    assert body["intent"] == "SAFETY_ALERT"
    assert body["detected_meal"] is None


def test_chat_agua_detectada_persiste_e_aparece_em_meals_today(client):
    """Regressão: água mencionada no chat tem que virar Checkin de verdade,
    não só aparecer na resposta e sumir."""
    r = client.post("/api/v1/chat", json={"message": "bebi 500ml de água"})
    assert r.status_code == 200
    assert r.json()["detected_water_ml"] == 500.0

    today = client.get("/api/v1/meals/today").json()
    assert today["agua_ml"] == 500.0


def test_chat_sem_mencao_de_agua_nao_persiste_nada(client):
    r = client.post("/api/v1/chat", json={"message": "qual o treino de hoje?"})
    assert r.json()["detected_water_ml"] is None

    today = client.get("/api/v1/meals/today").json()
    assert today["agua_ml"] == 0.0


def test_chat_treino_concluido_persiste_exercise_log(client):
    """Regressão: 'treinei hoje' tem que virar ExerciseLog de verdade — antes
    disso, treino mencionado no chat nunca era salvo em lugar nenhum."""
    r = client.post("/api/v1/chat", json={"message": "treinei hoje, foi pesado"})
    assert r.status_code == 200
    assert r.json()["detected_workout"] is True

    workouts = client.get("/api/v1/workouts").json()
    assert len(workouts) == 1
    assert workouts[0]["completed"] is True


def test_chat_pergunta_sobre_treino_nao_persiste_exercise_log(client):
    r = client.post("/api/v1/chat", json={"message": "qual o treino de hoje?"})
    assert r.json()["detected_workout"] is False

    workouts = client.get("/api/v1/workouts").json()
    assert workouts == []


def test_chat_exercicio_mencionado_anexa_imagem_de_demonstracao(client):
    r = client.post("/api/v1/chat", json={"message": "quero fazer supino reto barra hoje"})
    body = r.json()
    assert body["intent"] == "TED_PERSONAL"
    assert len(body["images"]) == 1
    assert body["images"][0]["exercise"] == "Supino reto barra"
    assert body["images"][0]["url"].startswith("https://wger.de/")

    # a imagem também aparece no histórico (persistida no extra do outbound)
    history = client.get("/api/v1/chat/history").json()
    outbound = [h for h in history if h["direction"] == "outbound"][-1]
    assert outbound["images"] == body["images"]


def test_chat_saudacao_nao_anexa_imagem(client):
    r = client.post("/api/v1/chat", json={"message": "oi"})
    assert r.json()["images"] == []


def test_chat_pergunta_geral_traz_imagem_de_todos_os_exercicios_do_treino(client):
    """Regressão do bug reportado: 'qual o treino de hoje?' tinha que
    trazer TODOS os exercícios do treino com imagem mapeada, não só 1.
    Força o treino de hoje pra UPPER A (via plan/training) — ela tem 4
    dos 6 exercícios mapeados, então tem que vir os 4."""
    plan = client.get("/api/v1/plan/training").json()
    protocolo = {str(d): "UPPER A" for d in range(7)}
    client.put("/api/v1/plan/training", json={"protocolo": protocolo, "ativo": plan["ativo"]})

    r = client.post("/api/v1/chat", json={"message": "qual o treino de hoje?"})
    body = r.json()

    nomes = [img["exercise"] for img in body["images"]]
    assert nomes == ["Supino reto barra", "Supino inclinado halter", "Puxada frontal", "Desenvolvimento militar"]


def test_chat_persist_false_nao_grava_agua_nem_treino(client):
    client.post("/api/v1/chat", json={"message": "bebi 500ml de água", "persist": False})
    client.post("/api/v1/chat", json={"message": "treinei hoje", "persist": False})

    today = client.get("/api/v1/meals/today").json()
    assert today["agua_ml"] == 0.0
    assert client.get("/api/v1/workouts").json() == []
