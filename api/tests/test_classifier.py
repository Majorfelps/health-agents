"""
test_classifier.py — cobre os ramos mais frágeis de classify() (muitas
regras encadeadas, fácil quebrar um caso ao mexer em outro).
"""
from app.services.classifier import (
    classify, looks_like_meal, looks_like_water, looks_like_completed_workout,
)


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


def test_looks_like_water_com_ml_explicito():
    assert looks_like_water("bebi 500ml de água") == 500.0


def test_looks_like_water_com_litros():
    assert looks_like_water("tomei 1,5 litro de água") == 1500.0


def test_looks_like_water_sem_quantidade_usa_padrao_de_1_copo():
    assert looks_like_water("bebi água") == 200.0


def test_looks_like_water_pergunta_nao_conta():
    assert looks_like_water("quanto de água falta pra hoje?") is None


def test_looks_like_water_mensagem_sem_agua_retorna_none():
    assert looks_like_water("comi 100g de arroz") is None


def test_looks_like_completed_workout_positivo():
    assert looks_like_completed_workout("treinei hoje, foi pesado") is True


def test_looks_like_completed_workout_fiz_o_treino():
    assert looks_like_completed_workout("fiz o treino de hoje completo") is True


def test_looks_like_completed_workout_pergunta_nao_conta():
    assert looks_like_completed_workout("qual treino de hoje?") is False


def test_looks_like_completed_workout_futuro_nao_conta():
    assert looks_like_completed_workout("vou treinar daqui a pouco") is False


def test_looks_like_completed_workout_mensagem_neutra_retorna_false():
    assert looks_like_completed_workout("comi 100g de arroz") is False
