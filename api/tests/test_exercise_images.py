"""
test_exercise_images.py — mapeamento curado exercício → imagem (wger.de),
usado pelo ED o Personal pra anexar demonstração real no chat.

Regressão: o agente tinha um bug real — só mandava a imagem do 1º
exercício do treino que tinha imagem mapeada (e às vezes o LLM chutava
errado dizendo que era "o primeiro exercício" quando na real era outro,
tipo o 4º). Agora manda TODOS os exercícios do treino que têm imagem,
cada um já nomeado — sem depender do LLM adivinhar qual é qual.
"""
from app.services import agents
from app.services.exercise_images import EXERCISE_IMAGES, image_for_exercise, find_images


def test_image_for_exercise_existe():
    url = image_for_exercise("Agachamento livre")
    assert url is not None
    assert url.startswith("https://wger.de/")


def test_image_for_exercise_sem_acento_ou_case_bate_igual():
    assert image_for_exercise("agachamento LIVRE") == image_for_exercise("Agachamento livre")


def test_image_for_exercise_nao_mapeado_retorna_none():
    assert image_for_exercise("Exercício Inventado Que Não Existe") is None


def test_find_images_por_mencao_explicita_na_mensagem():
    """Pergunta sobre 1 exercício específico → só a imagem dele, não o treino inteiro."""
    imgs = find_images("como faz o supino reto barra?", treino=None)
    assert len(imgs) == 1
    assert imgs[0].exercise == "Supino reto barra"
    assert imgs[0].url == EXERCISE_IMAGES["Supino reto barra"]


def test_find_images_pergunta_geral_traz_todos_os_exercicios_com_imagem():
    """Regressão do bug reportado: pergunta geral ('qual o treino de
    hoje?') tem que trazer TODOS os exercícios do treino com imagem
    mapeada, cada um nomeado — não só o primeiro."""
    treino = {
        "exercicios": [
            ("Flexão de braço", "3x10", "RPE 7", "60s"),    # sem imagem mapeada
            ("Cadeira extensora", "3x12", "RPE 7", "60s"),   # tem imagem
            ("Prancha", "3x30s", "RPE 7", "60s"),            # sem imagem mapeada
            ("Cadeira flexora", "3x12", "RPE 7", "60s"),     # tem imagem
        ]
    }
    imgs = find_images("qual o treino de hoje?", treino)
    assert [i.exercise for i in imgs] == ["Cadeira extensora", "Cadeira flexora"]
    assert imgs[0].url == EXERCISE_IMAGES["Cadeira extensora"]
    assert imgs[1].url == EXERCISE_IMAGES["Cadeira flexora"]


def test_find_images_sem_match_nenhum_retorna_lista_vazia():
    treino = {"exercicios": [("Exercício sem imagem", "3x10", "RPE 7", "60s")]}
    assert find_images("qual o treino de hoje?", treino) == []


def test_find_images_sem_treino_e_sem_mencao_retorna_lista_vazia():
    assert find_images("oi, tudo bem?", None) == []


def test_reply_personal_anexa_imagem_de_todos_os_exercicios_do_treino(monkeypatch):
    """protocolo com todo dia = UPPER A pra não depender do dia da semana
    real em que o teste roda. UPPER A tem 6 exercícios, dos quais 4 têm
    imagem mapeada (Supino reto barra, Supino inclinado halter, Puxada
    frontal, Desenvolvimento militar) — todos têm que vir, na ordem do
    treino, não só o primeiro."""
    protocolo = {str(d): "UPPER A" for d in range(7)}
    reply = agents.reply_personal(agents.DEFAULT_USER_PROFILE, "qual o treino de hoje?", protocolo)

    nomes = [img["exercise"] for img in reply.images]
    assert nomes == ["Supino reto barra", "Supino inclinado halter", "Puxada frontal", "Desenvolvimento militar"]
    for img in reply.images:
        assert img["url"] == EXERCISE_IMAGES[img["exercise"]]


def test_reply_mixed_tambem_anexa_imagem_de_todos_os_exercicios():
    protocolo = {str(d): "UPPER A" for d in range(7)}
    reply = agents.reply_mixed(agents.DEFAULT_USER_PROFILE, "to de dieta e vou treinar", protocolo)
    nomes = [img["exercise"] for img in reply.images]
    assert nomes == ["Supino reto barra", "Supino inclinado halter", "Puxada frontal", "Desenvolvimento militar"]
