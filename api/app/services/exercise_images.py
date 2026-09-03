"""
exercise_images.py — mapeamento curado exercício → imagem de demonstração,
usando o wger.de (banco de exercícios aberto, CC0/CC-BY-SA, sem API key).

É um mapeamento manual, não busca ao vivo: a API pública do wger não tem
busca por nome funcional de verdade (só filtro por match exato — `search`/
`language` não funcionam na instância pública, testado em 2026-09-01), e
nem todo exercício de lá tem imagem cadastrada. Em vez de depender disso em
runtime (lento, frágil, chance de imagem errada), curamos uma vez só os
exercícios do WORKOUT_LIBRARY que realmente têm imagem disponível.
Exercícios fora dessa lista simplesmente não mandam imagem — cai pro texto
normal, sem quebrar nada (mesmo espírito do fallback do LLM).

Pra adicionar mais: procure o exercício em wger.de/en/exercise/overview/,
pegue o ID e confirme imagem em GET /api/v2/exerciseinfo/<id>/?format=json
(campo "images" — pode vir vazio, nem todo exercício tem).
"""
from __future__ import annotations
import unicodedata
from dataclasses import dataclass

# nome (idêntico ao usado em WORKOUT_LIBRARY) → URL pública da imagem
EXERCISE_IMAGES: dict[str, str] = {
    "Agachamento livre": "https://wger.de/media/exercise-images/1801/60043328-1cfb-4289-9865-aaf64d5aaa28.jpg",
    "Leg press 45°": "https://wger.de/media/exercise-images/371/d2136f96-3a43-4d4c-9944-1919c4ca1ce1.webp",
    "Cadeira extensora": "https://wger.de/media/exercise-images/369/78c915d1-e46d-4d30-8124-65d68664c3ef.png",
    "Cadeira flexora": "https://wger.de/media/exercise-images/364/b318dde9-f5f2-489f-940a-cd864affb9e3.png",
    "Supino reto barra": "https://wger.de/media/exercise-images/192/Bench-press-1.png",
    "Supino inclinado halter": "https://wger.de/media/exercise-images/16/Incline-press-1.png",
    "Desenvolvimento militar": "https://wger.de/media/exercise-images/418/fa2a2207-43cb-4dc0-bc2a-039e32544790.png",
    "Puxada frontal": "https://wger.de/media/exercise-images/1127/4942b7c0-6bda-4983-88e5-86547c3d445e.png",
    "Rosca direta": "https://wger.de/media/exercise-images/1012/8270fdb8-28f1-4eff-b410-af8642085b3f.png",
    "Hiperextensão": "https://wger.de/media/exercise-images/301/2d5c2f99-b8ff-4095-b515-4c2a85afde70.png",
}


def _norm(s: str) -> str:
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()


_NORMALIZED_IMAGES = {_norm(k): v for k, v in EXERCISE_IMAGES.items()}


@dataclass
class ExerciseImage:
    exercise: str  # nome exato do exercício (o mesmo do WORKOUT_LIBRARY)
    url: str

    def to_dict(self) -> dict:
        return {"exercise": self.exercise, "url": self.url}


def image_for_exercise(name: str) -> str | None:
    """Imagem de demonstração pro exercício, se tiver mapeado (comparação
    sem acento/case, pra não depender de digitação exata)."""
    return _NORMALIZED_IMAGES.get(_norm(name))


def find_images(user_msg: str, treino: dict | None) -> list[ExerciseImage]:
    """Resolve quais imagens mandar no chat, cada uma já nomeada com o
    exercício correspondente (pra nunca virar "a foto do primeiro
    exercício" — o LLM recebe o nome certo de cada uma):

    - Se a mensagem cita exercício(s) específico(s) por nome (ex: "como
      faz o supino reto barra?"), manda só a(s) imagem(ns) do(s)
      exercício(s) citado(s) — não polui com o resto do treino.
    - Senão (pergunta geral, ex: "qual o treino de hoje?"), manda a
      imagem de TODOS os exercícios do treino do dia que tiverem
      mapeamento — não só o primeiro.

    Lista vazia se nada bater (treino sem exercícios mapeados, ou
    mensagem sem treino/exercício algum)."""
    msg_norm = _norm(user_msg)
    mencionados = [
        ExerciseImage(exercise=name, url=url)
        for name, url in EXERCISE_IMAGES.items()
        if _norm(name) in msg_norm
    ]
    if mencionados:
        return mencionados

    if not treino:
        return []

    out: list[ExerciseImage] = []
    for ex in treino.get("exercicios", []):
        nome_exercicio = ex[0] if ex else None
        if not nome_exercicio:
            continue
        img = image_for_exercise(nome_exercicio)
        if img:
            out.append(ExerciseImage(exercise=nome_exercicio, url=img))
    return out
