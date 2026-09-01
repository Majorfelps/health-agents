"""
test_classifier.py — cobre os ramos mais frágeis de classify() (muitas
regras encadeadas, fácil quebrar um caso ao mexer em outro).
"""
from app.services.classifier import classify, looks_like_meal


def test_safety_alert_tem_prioridade_absoluta():
    r = classify("comi arroz mas to com dor no peito")
    assert r.intent == "SAFETY_ALERT"


def test_greeting_simples():
    r = classify("oi")
    assert r.intent == "ORCHESTRATOR"
    assert r.reasoning == "greeting detected"


def test_bom_dia_e_greeting():
    r = classify("bom dia")
    assert r.intent == "ORCHESTRATOR"
    assert r.reasoning == "greeting detected"


def test_nutri_por_alimento():
    r = classify("comi 200g de arroz com feijao e frango")
    assert r.intent == "ED_NUTRI"


def test_nutri_por_termo_macro():
    r = classify("quantas calorias eu já comi hoje?")
    assert r.intent == "ED_NUTRI"


def test_treino_por_verbo():
    r = classify("acabei de treinar peito")
    assert r.intent == "TED_PERSONAL"


def test_treino_pergunta_qual_treino_hoje():
    r = classify("qual o treino de hoje?")
    assert r.intent == "TED_PERSONAL"


def test_mixed_treino_e_dieta():
    r = classify("to fazendo dieta e vou treinar")
    assert r.intent == "MIXED"


def test_unknown_mensagem_sem_sinal_claro():
    r = classify("xablau")
    assert r.intent == "ORCHESTRATOR"
    assert r.reasoning == "no clear match"


def test_mensagem_vazia():
    r = classify("")
    assert r.intent == "ORCHESTRATOR"
    assert r.confidence == 0.0


def test_looks_like_meal_positivo():
    assert looks_like_meal("comi 100g de arroz com feijão") is True


def test_looks_like_meal_pergunta_nao_e_refeicao_consumida():
    assert looks_like_meal("o que posso comer no almoço?") is False


def test_looks_like_meal_agua_sozinha_nao_e_refeicao():
    assert looks_like_meal("bebi 500ml de água") is False
