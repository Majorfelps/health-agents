"""
test_exercise_images.py — mapeamento curado exercício → imagem (wger.de),
usado pelo ED o Personal pra anexar demonstração real no chat.
"""
from app.services import agents
from app.services.exercise_images import EXERCISE_IMAGES, image_for_exercise, find_image


def test_image_for_exercise_existe():
    url = image_for_exercise("Agachamento livre")
    assert url is not None
    assert url.startswith("https://wger.de/")


def test_image_for_exercise_sem_acento_ou_case_bate_igual():
    assert image_for_exercise("agachamento LIVRE") == image_for_exercise("Agachamento livre")


def test_image_for_exercise_nao_mapeado_retorna_none():
    assert image_for_exercise("Exercício Inventado Que Não Existe") is None


def test_find_image_por_mencao_explicita_na_mensagem():
    url = find_image("como faz o supino reto barra?", treino=None)
    assert url == EXERCISE_IMAGES["Supino reto barra"]


def test_find_image_cai_pro_primeiro_exercicio_do_treino_com_imagem():
    treino = {
        "exercicios": [
            ("Flexão de braço", "3x10", "RPE 7", "60s"),   # sem imagem mapeada
            ("Cadeira extensora", "3x12", "RPE 7", "60s"),  # tem imagem
        ]
    }
    url = find_image("qual o treino de hoje?", treino)
    assert url == EXERCISE_IMAGES["Cadeira extensora"]


def test_find_image_sem_match_nenhum_retorna_none():
    treino = {"exercicios": [("Exercício sem imagem", "3x10", "RPE 7", "60s")]}
    assert find_image("qual o treino de hoje?", treino) is None


def test_find_image_sem_treino_e_sem_mencao_retorna_none():
    assert find_image("oi, tudo bem?", None) is None


def test_reply_personal_anexa_imagem_do_treino(monkeypatch):
    """protocolo com todo dia = UPPER A pra não depender do dia da semana
    real em que o teste roda — UPPER A tem Supino reto barra como 1º
    exercício, que está mapeado."""
    protocolo = {str(d): "UPPER A" for d in range(7)}
    reply = agents.reply_personal(agents.DEFAULT_USER_PROFILE, "qual o treino de hoje?", protocolo)
    assert reply.image_url == EXERCISE_IMAGES["Supino reto barra"]


def test_reply_mixed_tambem_anexa_imagem_do_treino():
    protocolo = {str(d): "UPPER A" for d in range(7)}
    reply = agents.reply_mixed(agents.DEFAULT_USER_PROFILE, "to de dieta e vou treinar", protocolo)
    assert reply.image_url == EXERCISE_IMAGES["Supino reto barra"]
