"""
classifier.py — Classificador de intenção para mensagens do chat.

Portado de health_classifier.py (Hermes) e master_agent.py::classify() para um
serviço FastAPI. Mantém os mesmos termos e regras — diferença é o formato de
retorno (dataclass + JSON-serializable) e a remoção de qualquer chamada externa.

Decisões:
- SAFETY_ALERT tem prioridade absoluta
- Emparelhamento de ambas as categorias vai para MIXED
- Saudação/comando admin → ORCHESTRATOR
- Orquestrador também cobre GREETING (Master Agent apresenta-se)
- Tudo determinístico (sem LLM)
"""
from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass, asdict


# ── Termos-chave (lowercase, sem acentos no set) ──────────────────────────────

def _norm(s: str) -> str:
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()


NUTRI_TERMS = {
    "comi", "comer", "comida", "almoco", "almoço", "janta", "jantar",
    "cafe", "café", "lanche", "ceia", "refeição", "refeicao",
    "fome", "satisfeito", "saciado", "dieta", "caloria", "kcal",
    "proteina", "proteína", "carbo", "carboidrato", "gordura",
    "peso", "kg", "emagrecer", "engordar", "massa muscular",
    "agua", "água", "hidratacao", "hidratação", "litro", "liquido", "líquido",
    "sono", "dormi", "dormir", "insonia", "insônia",
    "fruta", "verdura", "legume", "arroz", "feijao", "feijão",
    "frango", "carne", "peixe", "salmao", "salmão", "atum",
    "whey", "creatina", "suplemento", "ovo", "banana", "miojo", "miojo",
    "macarrao", "macarrão", "salada", "batata", "mandioca", "queijo",
    "leite", "iogurte", "pao", "pão", "aveia", "granola", "castanha",
    "manteiga", "tapioca", "rapadura", "mel", "suco", "cha", "chá",
}

TREINO_TERMS = {
    "treino", "treinar", "treinou", "treinei", "malhar", "malhei", "malhou",
    "gym", "academia", "musculacao", "musculação",
    "agachamento", "supino", "remada", "flexão", "flexao", "abdominal",
    "core", "abd", "abs",
    "carga", "kg", "serie", "séries", "reps", "rep", "wod", "amrap", "emom",
    "tabata", "halter", "barra",
    "hiit", "liss", "cardio", "corrida", "caminhada", "nadar", "pedalar",
    "bike", "crossfit", "funcional", "pilates", "yoga",
    "rotina", "programa", "plano",
    "dormi o treino", "fiz o treino", "treino de hoje", "treino de hoje",
    "rpe", "esforco", "esforço", "dor muscular", "lesao", "lesão",
}

GREETING_TERMS = {
    "oi", "olá", "ola", "eae", "opa", "hi", "hey", "hello",
    "bom dia", "boa tarde", "boa noite",
}

SAFETY_TERMS = {
    "dor no peito", "dor torácica", "tontura", "desmaiei", "desmaio",
    "falta de ar", "nao consigo respirar", "não consigo respirar",
    "sangramento", "convulsao", "convulsão", "inconsciente",
    "anorexia", "bulimia", "bulímia", "vomito", "vômito", "sangrando",
    "suicidio", "suicídio", "me matar", "quero morrer",
}

# Foods para detecção determinística de refeição (paralelo a FOOD_TABLE do master_agent)
FOOD_PATTERNS = [
    "arroz", "feijao", "feijão", "frango", "carne", "carne moida",
    "ovo", "ovos", "banana", "whey", "mandioca", "salada", "tomate",
    "macarrao", "macarrão", "batata", "peixe", "queijo", "leite",
    "iogurte", "pao", "pão", "tapioca", "aveia", "granola",
]


@dataclass(frozen=True)
class Classification:
    intent: str
    confidence: float
    matched_terms: tuple
    reasoning: str = ""

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "confidence": self.confidence,
            "matched_terms": list(self.matched_terms),
            "reasoning": self.reasoning,
        }


# ── Classificador principal ──────────────────────────────────────────────────

def classify(text: str) -> Classification:
    """Classifica a mensagem do usuário em uma das 5 intenções.

    Returns:
        Classification com intent ∈ {SAFETY_ALERT, ED_NUTRI, TED_PERSONAL,
        MIXED, ORCHESTRATOR}.
    """
    if not text or not text.strip():
        return Classification(
            intent="ORCHESTRATOR", confidence=0.0, matched_terms=(),
            reasoning="empty message"
        )

    t = text.strip().lower()
    tn = _norm(t)
    tokens = set(re.findall(r"\b\w+\b", tn))

    # 1. SAFETY_ALERT tem prioridade absoluta
    safety_hits = [w for w in SAFETY_TERMS if w in tn]
    if safety_hits:
        return Classification(
            intent="SAFETY_ALERT", confidence=0.99,
            matched_terms=tuple(safety_hits),
            reasoning="safety keyword detected",
        )

    # 2. GREETING
    greeting_hits = [g for g in GREETING_TERMS if g in tn]
    is_short = len(tokens) <= 4
    if (tokens <= GREETING_TERMS) or (is_short and greeting_hits and len(tokens - GREETING_TERMS) <= 1):
        return Classification(
            intent="ORCHESTRATOR", confidence=0.85,
            matched_terms=tuple(greeting_hits),
            reasoning="greeting detected",
        )

    # 3. MIXED (antes dos individuais) — mensagens com 2+ sinais de cada lado
    nutri_hits = [w for w in NUTRI_TERMS if w in tn]
    treino_hits = [w for w in TREINO_TERMS if w in tn]

    # Comportamento MIXED do master_agent:
    if re.search(r"(quer|quero|vou|fazer|estao|estão|fazendo).*(trein|malh)", tn) and \
       re.search(r"(dieta|comer|macros|calorias|aliment)", tn):
        return Classification(
            intent="MIXED", confidence=0.9,
            matched_terms=("intent_verb+nutri",),
            reasoning="querer/fazer + treinar + dieta",
        )
    if re.search(r"(trein|malh)", tn) and re.search(r"(dieta|comer|macros|calorias)", tn):
        return Classification(
            intent="MIXED", confidence=0.85,
            matched_terms=("cross_intent",),
            reasoning="treinar + dieta/comer",
        )
    n = len(tokens & {_norm(w) for w in NUTRI_TERMS})
    w = len(tokens & {_norm(w) for w in TREINO_TERMS})
    if n >= 2 and w >= 2 and abs(n - w) <= 2:
        return Classification(
            intent="MIXED", confidence=0.8,
            matched_terms=("balanced_tokens",),
            reasoning=f"balanced nutri({n}) treino({w})",
        )

    # 4. NUTRI (comportamento do master_agent — sequencial, sem \b)
    if re.search(r"\b(arroz|frango|ovo|feij[ãa]o|batata|macarr[aã]o|salada|legume|carne|peixe|salm[ãa]o|atum|p[áa]o|whey|banana|mandioca|queijo)", tn):
        return Classification("ED_NUTRI", 0.9, tuple(nutri_hits), "food token")
    if re.search(r"\b(comer|comi|como|vou comer|queria comer)\b", tn):
        return Classification("ED_NUTRI", 0.85, tuple(nutri_hits), "comer verb")
    if re.search(r"\b(kcal|macro|macros|caloria|calorias|dieta|suplemento|whey|creatina|prote[ií]na|carboidrato|gordura|fibra|vitaminas|mineral)\b", tn):
        return Classification("ED_NUTRI", 0.9, tuple(nutri_hits), "macros term")
    if re.search(r"\b(cafe|café|almo[çc]ar|jantar|lanche|ceia|refei[çc][ãa]o|refeicoes)\b", tn):
        return Classification("ED_NUTRI", 0.85, tuple(nutri_hits), "refeição term")
    if re.search(r"\b(ganhar peso|perder peso|perder barriga|ganhar massa|magro|massa|gordura|corp[oa]|imc|peso)\b", tn):
        return Classification("ED_NUTRI", 0.8, tuple(nutri_hits), "body goal")
    if re.search(r"\bo que .*(comer|almo[çc]|jantar|cafe|lanche)\b", tn):
        return Classification("ED_NUTRI", 0.8, tuple(nutri_hits), "o que comer")
    if re.search(r"(quais?|quanto|quantas?).*(macro|caloria|kcal|prote[ií]na|carbo)", tn):
        return Classification("ED_NUTRI", 0.8, tuple(nutri_hits), "quanto/quais macros")

    if n >= 2:
        return Classification("ED_NUTRI", 0.7, tuple(nutri_hits), f"token-fallback nutri({n})")

    # 5. TREINO
    treino_pattern_hits = []
    if re.search(r"\b(nao treinei|não treinei|nao entrenei|não entrenhei|nao malhei|não malhei|dormi o treino|n fiz treino)\b", tn):
        treino_pattern_hits.append("pulei treino")
    if re.search(r"\b(treino|treinar|trein|malhar|malhou|gym|academia|muscula[çc][ãa]o)\b", tn):
        treino_pattern_hits.append("treino verb")
    if re.search(r"\b(rotina|programa|plano)\b", tn):
        treino_pattern_hits.append("plano")
    if re.search(r"\b(hiit|liss|cardio|corrida|caminhada|nadar|pedalar|bike|crossfit|funcional|pilates|yoga|agach|supino|remada|terra|flexão|abd|abs)\b", tn):
        treino_pattern_hits.append("exercicio")
    if re.search(r"\b(serie|séries|reps|carga|kg|quilo|wod|amrap|emom|tabata|halter|barra)\b", tn):
        treino_pattern_hits.append("carga")
    if treino_pattern_hits:
        return Classification("TED_PERSONAL", 0.85,
                              tuple(treino_hits),
                              f"pattern: {','.join(treino_pattern_hits)}")
    if w >= 2:
        return Classification("TED_PERSONAL", 0.7, tuple(treino_hits), f"token-fallback treino({w})")

    # 6. UNKNOWN → ORCHESTRATOR
    return Classification(
        intent="ORCHESTRATOR", confidence=0.3,
        matched_terms=(),
        reasoning="no clear match",
    )


# ── Helpers para detecção de refeição (espelha master_agent.looks_like_meal) ─

MEAL_NEGATIVE = re.compile(
    r"\b(o que|quanto|qual|quais|posso|devo|planejar|sugere|recomenda|"
    r"meta|faltam|falta|preciso|vou comer|queria comer|ideia|op[çc][ãa]o)\b",
    re.I,
)


def looks_like_meal(text: str) -> bool:
    """True se a mensagem parece descrever refeição JÁ consumida."""
    t = _norm(text)
    if MEAL_NEGATIVE.search(t):
        return False
    if re.search(r"\bagua\b", t) and not re.search(
        r"(p[áa]o|arroz|feij[ãa]o|frango|ovo|banana|whey|carne|comi|almocei|jantei)", t):
        return False
    food_re = "|".join(FOOD_PATTERNS)
    return bool(re.search(rf"\b({food_re}|comi|almocei|jantei|refeic|ingeri)\b", t))
