"""
agents.py — Personas ED o Nutri, ED o Personal e Master Agent (orquestrador).

Portado de:
  - skills/health/nutri-agent/SKILL.md
  - skills/health/personal-trainer/SKILL.md
  - skills/health/master-agent/SKILL.md
  - scripts/master_agent.py (respostas + classificação interna)

Substitui as chamadas ao LLM por templates determinísticos (o chat web
inicia como "demo" — os templates garantem experiência completa sem API key).
A interface é a mesma, então trocar para LLM depois é trivial.
"""
from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


# ── Perfil do usuário (espelha USER_PROFILE do master_agent) ─────────────────

DEFAULT_USER_PROFILE = {
    "name": "Michael",
    "age": 33,
    "sex": "M",
    "weight_kg": 93.0,
    "height_cm": 180,
    "activity": "sedentário",
    "goal": "recomposição corporal (perder ~8kg de gordura + ganhar massa magra)",
    "tdee": 2274,
    "meta_kcal": 1770,
    "meta_p": 186,  # 2g/kg
    "meta_f": 70,
    "meta_c": 165,
    "meta_agua_ml": 2500,
}


# ── Biblioteca de treinos ED o Personal (espelha PLANO_SEMANAL do master_agent) ─
#
# WORKOUT_LIBRARY guarda a definição completa (foco/séries/exercícios) de
# cada treino, indexada pelo *nome*. PLANO_SEMANAL_PADRAO mapeia dia da
# semana → nome, e é só o valor inicial usado no seed de PlanTraining
# (repository.seed_default_plans). O treino "de verdade" de cada usuário
# vem de PlanTraining.protocolo (editável em /plan), resolvido via
# resolve_treino_do_dia() abaixo — PLANO_SEMANAL_PADRAO é o fallback para
# quando o usuário ainda não tem plano salvo, ou escreveu um nome livre
# que não está na biblioteca.

WORKOUT_LIBRARY: dict[str, dict] = {
    "UPPER A": {
        "foco": "peito + costas",
        "series": 18,
        "exercicios": [
            ("Supino reto barra", "3×8–10", "RPE 6–7", "90–120s"),
            ("Remada curvada", "3×8–10", "RPE 6–7", "90–120s"),
            ("Supino inclinado halter", "2×10–12", "RPE 7", "75–90s"),
            ("Puxada frontal", "3×10–12", "RPE 7", "75–90s"),
            ("Desenvolvimento militar", "2×10–12", "RPE 7", "75–90s"),
            ("Abdominal supra", "3×15", "RPE 7", "60s"),
        ],
    },
    "LOWER A": {
        "foco": "quadríceps + posterior",
        "series": 18,
        "exercicios": [
            ("Agachamento livre", "3×8–10", "RPE 6–7", "90–120s"),
            ("Leg press 45°", "3×10–12", "RPE 7", "90s"),
            ("Cadeira extensora", "2×12", "RPE 7", "60s"),
            ("Stiff", "3×8–10", "RPE 7", "90s"),
            ("Cadeira flexora", "2×12", "RPE 7", "60s"),
            ("Panturrilha em pé", "3×15", "RPE 7", "60s"),
        ],
    },
    "CARDIO HIIT 20min": {
        "foco": "cardio alta intensidade",
        "exercicios": [
            ("Aquecimento esteira", "5min", "Zona 1", "—"),
            ("Sprint 30s + caminhada 90s", "8 rounds", "Zona 4", "—"),
            ("Desaquecimento", "3min", "Zona 1", "—"),
        ],
    },
    "UPPER B": {
        "foco": "ombros + braços",
        "exercicios": [
            ("Desenvolvimento halter", "3×10", "RPE 7", "90s"),
            ("Barra fixa assistida", "3×max", "RPE 7", "90s"),
            ("Crucifixo inclinado", "3×12", "RPE 7", "75s"),
            ("Rosca direta", "3×10", "RPE 7", "75s"),
            ("Tríceps corda", "3×12", "RPE 7", "75s"),
            ("Elevação lateral", "3×15", "RPE 7", "60s"),
        ],
    },
    "LOWER B": {
        "foco": "posterior + glúteo",
        "exercicios": [
            ("Terra romeno", "3×8–10", "RPE 7", "90s"),
            ("Agachamento sumô", "3×10", "RPE 7", "90s"),
            ("Cadeira flexora", "3×12", "RPE 7", "75s"),
            ("Agachamento búlgaro", "3×10", "RPE 7", "90s"),
            ("Hiperextensão", "3×12", "RPE 7", "60s"),
            ("Prancha", "3×45s", "RPE 7", "45s"),
        ],
    },
    "CARDIO LISS 35min": {
        "foco": "cardio zona 2",
        "exercicios": [
            ("Esteira / caminhada 6–7km/h", "35min", "Zona 2", "—"),
        ],
    },
    "DESCANSO ATIVO": {
        "foco": "recuperação",
        "exercicios": [
            ("Caminhada leve", "30min", "—", "—"),
            ("Alongamento global", "15min", "—", "—"),
        ],
    },
}

PLANO_SEMANAL_PADRAO: dict[int, str] = {
    0: "UPPER A",       # segunda
    1: "LOWER A",        # terça
    2: "CARDIO HIIT 20min",  # quarta
    3: "UPPER B",        # quinta
    4: "LOWER B",         # sexta
    5: "CARDIO LISS 35min",  # sábado
    6: "DESCANSO ATIVO",  # domingo
}

DIAS_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def resolve_treino_do_dia(protocolo: dict | None, weekday: int) -> dict:
    """Resolve o treino do dia a partir do PlanTraining.protocolo do usuário
    (editável via /api/v1/plan/training), com fallback pro padrão quando o
    usuário não tem plano salvo ou o nome não está na biblioteca."""
    nome = None
    if protocolo:
        nome = protocolo.get(str(weekday), protocolo.get(weekday))
    if not nome:
        nome = PLANO_SEMANAL_PADRAO[weekday]

    detalhes = WORKOUT_LIBRARY.get(nome)
    if detalhes is None:
        # Nome customizado que o usuário digitou e não está na biblioteca —
        # mostra só o nome, sem inventar exercícios.
        detalhes = {"foco": "personalizado", "exercicios": []}

    return {"nome": nome, **detalhes}


# ── Estimativa de macros (espelha FOOD_TABLE + estimate_meal_heuristic) ─────

FOOD_TABLE = [
    ("arroz", 128, 2.7, 0.3, 28),
    ("feijao", 76, 4.5, 0.5, 13),
    ("frango", 165, 31, 3.6, 0),
    ("carne moida", 250, 26, 15, 0),
    ("pao", 300, 9, 1, 58),
    ("ovo", 70, 6, 5, 0.5),
    ("banana", 105, 1.3, 0.4, 27),
    ("whey", 120, 24, 2, 3),
    ("mandioca", 125, 1.2, 0.2, 30),
    ("salada", 15, 0.8, 0.1, 3),
    ("tomate", 18, 0.9, 0.2, 4),
    ("macarrao", 158, 5.8, 0.9, 31),
    ("batata", 87, 1.9, 0.1, 20),
    ("peixe", 130, 26, 3, 0),
    ("queijo", 350, 25, 28, 1),
    ("leite", 60, 3.3, 3.3, 4.8),
    ("iogurte", 60, 5, 3, 4),
    ("tapioca", 240, 1, 0.5, 60),
    ("aveia", 389, 17, 7, 66),
]


def _norm(s: str) -> str:
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()


def estimate_macros(text: str) -> Optional[dict]:
    """Estimativa determinística de macros de uma refeição (espelha
    master_agent.estimate_meal_heuristic). Retorna dict ou None."""
    t = _norm(text)
    total = {"kcal": 0.0, "P": 0.0, "F": 0.0, "C": 0.0}
    found = []
    for name, kcal, P, F, C in FOOD_TABLE:
        if re.search(rf"\b{re.escape(name)}", t):
            gm = re.search(rf"(\d+)\s*g\s*(?:de\s*)?{re.escape(name)}", t)
            un = re.search(rf"(\d+)\s*(?:unid\.?|ovos?|bananas?)?\s*{re.escape(name)}", t)
            mult = 1.0
            if gm:
                mult = int(gm.group(1)) / 100.0
            elif name in ("ovo", "banana") and un:
                mult = float(un.group(1))
            elif name == "pao":
                mult = 0.5
            total["kcal"] += kcal * mult
            total["P"] += P * mult
            total["F"] += F * mult
            total["C"] += C * mult
            found.append(name)
    if not found:
        return None
    return {
        "descricao": text[:50],
        "kcal": round(total["kcal"]),
        "P": round(total["P"]),
        "F": round(total["F"]),
        "C": round(total["C"]),
    }


# ── Geradores de resposta ────────────────────────────────────────────────────

@dataclass
class AgentReply:
    text: str
    agent: str
    intent: str
    detected_meal: Optional[dict] = None
    images: list[dict] = field(default_factory=list)  # [{"exercise": str, "url": str}, ...]
    metadata: Optional[dict] = None


def _profile_brief(profile: dict) -> str:
    return (
        f"{profile.get('name', 'usuário')}: {profile.get('age', '?')}a, "
        f"{profile.get('weight_kg', '?')}kg, {profile.get('height_cm', '?')}cm, "
        f"meta {profile.get('meta_kcal', '?')} kcal/dia "
        f"(P {profile.get('meta_p', '?')}g | F {profile.get('meta_f', '?')}g | "
        f"C {profile.get('meta_c', '?')}g), "
        f"água {profile.get('meta_agua_ml', '?')}ml."
    )


def reply_greeting(profile: dict) -> AgentReply:
    return AgentReply(
        text=(
            "🤖 *Master Agent* — olá! Sou o orquestrador da sua equipe de saúde.\n\n"
            "Posso te conectar com:\n"
            "🥗 *ED o Nutri* — alimentação, dieta, macros, kcal\n"
            "💪 *ED o Personal* — treino, exercícios, cardio, carga\n\n"
            "Me diz: o que você precisa hoje? 🔥"
        ),
        agent="master",
        intent="ORCHESTRATOR",
    )


def reply_unknown(profile: dict, user_msg: str) -> AgentReply:
    return AgentReply(
        text=(
            "🤖 *Master Agent* — não entendi direito, pode ser mais específico? 🤔\n\n"
            "Exemplos do que eu sei responder:\n"
            "🥗 \"comi 100g de arroz com feijão\"\n"
            "💪 \"qual o treino de hoje?\"\n"
            "📊 \"quanto falta pra meta de proteína?\"\n"
            "🫗 \"bebi 500ml de água\""
        ),
        agent="master",
        intent="ORCHESTRATOR",
    )


def reply_safety(profile: dict) -> AgentReply:
    return AgentReply(
        text=(
            "⚠️ *Master Agent* — identifiquei um sinal de risco na sua mensagem.\n\n"
            "Se você está passando mal AGORA, procure atendimento:\n"
            "• SAMU: 192\n"
            "• CVV (crise emocional): 188 ou chat cvv.org.br\n\n"
            "Para dúvidas de saúde rotineiras, me conta o que está sentindo que eu oriento com base no seu plano. "
            "Não substituo médico."
        ),
        agent="master",
        intent="SAFETY_ALERT",
    )


def reply_mixed(profile: dict, user_msg: str, protocolo: dict | None = None) -> AgentReply:
    from app.services.exercise_images import find_images
    return AgentReply(
        text=(
            "🤖 *Master Agent* — entendi que envolve nutrição + treino, vou te dar a visão integrada.\n\n"
            f"💪 Treino: {_treino_hoje_resumo(protocolo)}\n"
            f"🥗 Dieta: {_dieta_resumo(profile)}\n\n"
            "Quer que eu detalhe um dos lados? (foco treino / foco nutrição)"
        ),
        agent="master",
        intent="MIXED",
        images=[i.to_dict() for i in find_images(user_msg, _treino_hoje(protocolo))],
    )


def reply_nutri(profile: dict, user_msg: str, today_totals: dict | None = None) -> AgentReply:
    """Resposta do ED o Nutri. Se a mensagem descrever refeição consumida,
    inclui linha REGISTRO: <desc> | P P F F C C kcal K."""
    totals = today_totals or {"kcal": 0, "P": 0, "F": 0, "C": 0, "agua_ml": 0}
    meta = profile
    faltam_kcal = max(0, meta["meta_kcal"] - totals["kcal"])
    faltam_p = max(0, meta["meta_p"] - totals["P"])
    faltam_f = max(0, meta["meta_f"] - totals["F"])
    faltam_c = max(0, meta["meta_c"] - totals["C"])
    faltam_agua = max(0, meta["meta_agua_ml"] - totals["agua_ml"])

    # Detecta se é refeição
    from .classifier import looks_like_meal
    is_meal = looks_like_meal(user_msg)
    est = None
    registro_line = ""
    if is_meal:
        est = estimate_macros(user_msg)
        if est:
            registro_line = (
                f"\n\nREGISTRO: {est['descricao']} | "
                f"P{est['P']} F{est['F']} C{est['C']} kcal{est['kcal']}"
            )

    body = (
        f"🥗 *ED o Nutri* — anotado!\n\n"
        f"📊 *Hoje:* {totals['kcal']} kcal | P {totals['P']}g | "
        f"F {totals['F']}g | C {totals['C']}g | 💧 {totals['agua_ml']}ml\n"
        f"🎯 *Meta:* {meta['meta_kcal']} kcal | P {meta['meta_p']}g | "
        f"F {meta['meta_f']}g | C {meta['meta_c']}g | 💧 {meta['meta_agua_ml']}ml\n"
        f"📉 *Faltam:* {faltam_kcal} kcal | P {faltam_p}g | "
        f"F {faltam_f}g | C {faltam_c}g | 💧 {faltam_agua}ml"
    )
    if is_meal and est:
        body += (
            f"\n\n🍽 *Refeição estimada:* {est['descricao']}\n"
            f"   {est['kcal']} kcal | P {est['P']}g | F {est['F']}g | C {est['C']}g"
        )

    return AgentReply(
        text=body + registro_line,
        agent="nutri",
        intent="ED_NUTRI",
        detected_meal=est,
    )


def reply_personal(profile: dict, user_msg: str, protocolo: dict | None = None) -> AgentReply:
    """Resposta do ED o Personal. Por padrão mostra o treino do dia
    (resolvido do plano do usuário — ver resolve_treino_do_dia)."""
    hoje = _treino_hoje(protocolo)
    if hoje["nome"] == "DESCANSO ATIVO":
        body = (
            f"💪 *ED o Personal* — hoje é *{DIAS_PT[date.today().weekday()]}*, dia de descanso ativo 🧘\n\n"
            f"🎯 Sugestão:\n"
            f"   • Caminhada leve 30min\n"
            f"   • Alongamento global 15min\n\n"
            f"Recuperação também é treino. Descanse bem!"
        )
    elif not hoje["exercicios"]:
        body = (
            f"💪 *ED o Personal* — *{DIAS_PT[date.today().weekday()]} → {hoje['nome']}*\n\n"
            "Ainda não tenho os exercícios desse treino cadastrados — edita em "
            "*Planos → Treino Semanal* ou usa um dos nomes padrão "
            "(UPPER A/B, LOWER A/B, CARDIO HIIT/LISS, DESCANSO ATIVO)."
        )
    else:
        linhas = [
            f"💪 *ED o Personal* — *{DIAS_PT[date.today().weekday()]} → {hoje['nome']}* "
            f"({hoje['foco']}, {hoje.get('series', '?')} séries)\n"
        ]
        for i, (ex, reps, rpe, desc) in enumerate(hoje["exercicios"], 1):
            linhas.append(f"  {i}. {ex} — {reps} @ {rpe} (desc {desc})")
        body = "\n".join(linhas) + (
            "\n\nBora! 🔥 Marca o ✅ quando terminar e me passa o RPE médio (1–10)."
        )
    from app.services.exercise_images import find_images
    return AgentReply(
        text=body, agent="personal", intent="TED_PERSONAL",
        images=[i.to_dict() for i in find_images(user_msg, hoje)],
    )


# ── Helpers ─────────────────────────────────────────────────────────────────

def _treino_hoje(protocolo: dict | None = None) -> dict:
    """Retorna o treino de hoje, do plano do usuário (com fallback pro padrão)."""
    return resolve_treino_do_dia(protocolo, date.today().weekday())


def _treino_hoje_resumo(protocolo: dict | None = None) -> str:
    h = _treino_hoje(protocolo)
    return f"{DIAS_PT[date.today().weekday()]} = {h['nome']} ({h['foco']})"


def _dieta_resumo(profile: dict) -> str:
    return (
        f"meta {profile['meta_kcal']} kcal/dia, "
        f"P {profile['meta_p']}g | F {profile['meta_f']}g | C {profile['meta_c']}g, "
        f"5 refeições + 1 ceia opcional"
    )


def gerar_resposta(
    intent: str,
    user_msg: str,
    profile: dict | None = None,
    today_totals: dict | None = None,
    protocolo: dict | None = None,
    llm_enabled: bool = False,
    llm_model: str = "",
    meals_today: list[dict] | None = None,
    water_detected_ml: float | None = None,
    workout_logged_today: bool = False,
) -> AgentReply:
    """Despacho principal: dada uma intenção, retorna a resposta do agente certo.

    `protocolo` é o PlanTraining.protocolo do usuário (dia da semana → nome
    do treino), usado para resolver o treino de hoje nas intents que falam
    de treino (TED_PERSONAL / MIXED).

    `meals_today`/`water_detected_ml`/`workout_logged_today` são "memória do
    dia" (calculada em chat.py a partir do banco, antes desta mensagem ser
    persistida) — só usados pra enriquecer o contexto passado ao LLM, pra
    ele responder de forma correta pro momento (o que já foi comido hoje, se
    já bebeu água, se o treino de hoje já foi registrado). Não afetam o
    caminho determinístico.

    `llm_enabled`/`llm_model` vêm da config do LLM lida do banco (ver
    repository.get_llm_config() — editável via API, sem restart). Se
    habilitado, tenta gerar o *texto* da resposta via LLM (nunca pra
    SAFETY_ALERT) — mas `detected_meal` e o treino do dia continuam sempre
    calculados por regra fixa (estimate_macros / resolve_treino_do_dia), pra
    nunca persistir um número que o LLM inventou. Qualquer falha do LLM cai
    pro template determinístico abaixo, sem quebrar o chat."""
    profile = profile or DEFAULT_USER_PROFILE

    if intent != "SAFETY_ALERT":
        from app.services import llm
        if llm.is_enabled(llm_enabled, llm_model):
            resposta_llm = _gerar_resposta_llm(
                intent, user_msg, profile, today_totals, protocolo, llm_model,
                meals_today, water_detected_ml, workout_logged_today,
            )
            if resposta_llm is not None:
                return resposta_llm

    return _gerar_resposta_deterministica(intent, user_msg, profile, today_totals, protocolo)


def _gerar_resposta_llm(
    intent: str,
    user_msg: str,
    profile: dict,
    today_totals: dict | None,
    protocolo: dict | None,
    llm_model: str,
    meals_today: list[dict] | None = None,
    water_detected_ml: float | None = None,
    workout_logged_today: bool = False,
) -> AgentReply | None:
    from app.services import llm
    from app.services.classifier import looks_like_meal
    from app.services.exercise_images import find_images

    agent = {"ED_NUTRI": "nutri", "TED_PERSONAL": "personal"}.get(intent, "master")

    detected_meal = None
    if intent == "ED_NUTRI" and looks_like_meal(user_msg):
        detected_meal = estimate_macros(user_msg)

    images: list = []
    context: dict = {"intent": intent}
    if water_detected_ml is not None:
        context["agua_detectada_nesta_mensagem_ml"] = water_detected_ml
    if intent in ("ED_NUTRI", "MIXED"):
        totals = today_totals or {"kcal": 0, "P": 0, "F": 0, "C": 0, "agua_ml": 0}
        context["nutricao"] = {
            "hoje": totals,
            "meta": {k: profile[k] for k in ("meta_kcal", "meta_p", "meta_f", "meta_c", "meta_agua_ml")},
            "refeicoes_ja_registradas_hoje": meals_today or [],
            "refeicao_detectada_nesta_mensagem": detected_meal,
        }
    if intent in ("TED_PERSONAL", "MIXED"):
        treino = _treino_hoje(protocolo)
        context["treino_hoje"] = treino
        context["dia_da_semana"] = DIAS_PT[date.today().weekday()]
        context["treino_de_hoje_ja_registrado_como_concluido"] = workout_logged_today
        # imagens de demonstração são sempre resolvidas por regra fixa
        # (wger.de curado), nunca inventadas/geradas pelo LLM — mas o LLM
        # recebe o nome de CADA exercício cuja foto foi anexada, pra nunca
        # ter que adivinhar/chutar qual é ("o primeiro exercício" etc.)
        images = [i.to_dict() for i in find_images(user_msg, treino)]
        context["fotos_anexadas_nesta_resposta"] = [i["exercise"] for i in images]

    text = llm.generate_reply_via_llm(agent, user_msg, context, llm_model)
    if text is None:
        return None
    return AgentReply(text=text, agent=agent, intent=intent, detected_meal=detected_meal, images=images)


def _gerar_resposta_deterministica(
    intent: str,
    user_msg: str,
    profile: dict,
    today_totals: dict | None,
    protocolo: dict | None,
) -> AgentReply:
    if intent == "SAFETY_ALERT":
        return reply_safety(profile)
    if intent == "ORCHESTRATOR":
        # Greeting vs unknown
        norm = _norm(user_msg)
        tokens = set(re.findall(r"\b\w+\b", norm))
        greeting_terms = {"oi", "ola", "olá", "eae", "opa", "hi", "hey", "hello",
                          "bom", "dia", "tarde", "noite", "boa"}
        if tokens <= greeting_terms or (len(tokens) <= 3 and any(g in norm for g in greeting_terms)):
            return reply_greeting(profile)
        return reply_unknown(profile, user_msg)
    if intent == "ED_NUTRI":
        return reply_nutri(profile, user_msg, today_totals)
    if intent == "TED_PERSONAL":
        return reply_personal(profile, user_msg, protocolo)
    if intent == "MIXED":
        return reply_mixed(profile, user_msg, protocolo)
    return reply_unknown(profile, user_msg)
