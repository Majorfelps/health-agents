# Health Agents — TED & ED

Aplicação web full-stack com **dashboard + chat estilo WhatsApp** para os
agentes de saúde **ED o Nutri** (nutrição) e **ED o Personal / TED** (treino),
mais o **Master Agent** que roteia entre eles.

Portado dos skills/scripts do [Hermes Agent](https://github.com/...) do Michael
(Eckomining), originalmente enviados por WhatsApp via Evolution API.

## Stack

| Camada | Tecnologia | Path |
|---|---|---|
| Backend | FastAPI 0.115 (Python 3.12) | `api/` |
| Frontend | Next.js 15 (App Router, React 19, TypeScript, Tailwind) | `web/` |
| DB | PostgreSQL 17 | `db/schema.sql` |
| Orquestração | Docker Compose | `docker-compose.yml` |

## Estrutura

```
health-agents/
├── api/
│   ├── app/
│   │   ├── api/v1/          # routers: chat, meals, workouts, plans, checkins, dashboard
│   │   ├── core/            # config, db
│   │   ├── models/          # SQLAlchemy
│   │   ├── schemas/         # Pydantic
│   │   └── services/
│   │       ├── classifier.py    # classifica intenção (NUTRI / TREINO / MIXED / ORCHESTRATOR / SAFETY)
│   │       ├── agents.py        # personas + plano semanal + estimador de macros
│   │       └── repository.py    # queries (totais do dia, semana, últimos check-ins)
│   ├── alembic/             # migrações (fonte de verdade do schema — ver db/schema.sql abaixo)
│   ├── requirements.txt
│   └── Dockerfile
├── web/
│   ├── app/
│   │   ├── page.tsx         # Dashboard (totais, metas, treino do dia, gráfico 7 dias)
│   │   ├── chat/            # Chat estilo WhatsApp
│   │   ├── plan/            # Editor de plano nutricional + treino
│   │   └── checkins/        # Form + histórico
│   ├── components/NavBar.tsx
│   ├── lib/{api,types}.ts
│   ├── package.json
│   └── Dockerfile
├── db/
│   └── schema.sql           # referência do modelo de dados (não é mais aplicado automaticamente — ver api/alembic/)
├── docs/
│   └── migration-from-hermes.md
├── docker-compose.yml
├── .env.example
└── README.md
```

## Rodando localmente (Docker)

```bash
cp .env.example .env       # opcional, defaults funcionam
docker compose up --build
```

Aguarde ~30s e abra:

- **http://localhost:3000** — app (dashboard, chat, planos, check-ins)
- **http://localhost:8000/docs** — Swagger da API

## Rodando sem Docker (dev)

Em terminais separados:

```bash
# 1) Postgres (vazio — schema é criado pelo Alembic no passo 2)
docker run --rm -d --name health-db \
  -e POSTGRES_USER=health -e POSTGRES_PASSWORD=health -e POSTGRES_DB=health_agents \
  -p 5432:5432 postgres:17-alpine

# 2) API
cd api
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://health:health@localhost:5432/health_agents
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3) Web
cd web
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```

## API — endpoints principais

| Método | Path | Função |
|---|---|---|
| `POST` | `/api/v1/chat` | Recebe mensagem, classifica, despacha, persiste |
| `GET`  | `/api/v1/chat/history?limit=100` | Histórico do user |
| `GET`  | `/api/v1/dashboard` | Dados agregados (totais hoje, semana, treino do dia, último check-in) |
| `GET`  | `/api/v1/meals/today` | Totais de kcal/P/F/C/água do dia |
| `GET`  | `/api/v1/meals/week` | Totais por dia (últimos 7) |
| `POST` | `/api/v1/meals` | Cria refeição manual |
| `GET`  | `/api/v1/workouts/today` | Treino do dia (PLANO_SEMANAL) |
| `POST` | `/api/v1/workouts` | Registra treino feito |
| `GET`  | `/api/v1/plan/nutrition` / `PUT` | CRUD plano nutri |
| `GET`  | `/api/v1/plan/training` / `PUT` | CRUD plano treino |
| `POST` | `/api/v1/checkins` | Check-in (humor, fome, sono, água) |
| `GET`  | `/health` | Healthcheck |

## Mapeamento com Hermes original

| Hermes (origem) | health-agents (este repo) | Notas |
|---|---|---|
| `scripts/health_classifier.py` (144 linhas) | `api/app/services/classifier.py` | Mesmas regras, removido LLM, dataclass → JSON-serializable |
| `scripts/master_agent.py::classify()` (741 linhas) | `api/app/services/classifier.py` | Função `classify()` portada com prioridade GREETING→MIXED→específico |
| `scripts/master_agent.py::generate_llm_reply()` (LLM) | `api/app/services/agents.py` | Templates determinísticos (substituíveis por LLM depois) |
| `scripts/master_agent.py::PLANO_SEMANAL` | `api/app/services/agents.py::PLANO_SEMANAL` | Idêntico, agora também editável via UI em `plan/training` |
| `scripts/master_agent.py::FOOD_TABLE` | `api/app/services/agents.py::FOOD_TABLE` | Tabela de macros, agora retorna dict padronizado |
| `scripts/health_db.py` (psycopg2) | `api/app/services/repository.py` + `models/models.py` | SQLAlchemy 2.0, async-ready, com 1:N relations e JSONB |
| `scripts/health_db_bootstrap.sql` (Postgres) | `db/schema.sql` | + tabelas `plan_nutrition`, `plan_training`, `meals.opcao` (A/B/C) |
| `scripts/health_webhook.py` (Evolution → DB) | — (não portado) | Versão web não usa Evolution; chat é direto via `/api/v1/chat` |
| `~/.hermes/scripts/send_nutri_tracker.py` (state.json) | banco Postgres | Substitui `/tmp/nutri_tracker_state.json` por `meals` (totais via SQL) |
| `skills/health/nutri-agent/SKILL.md` | persona em `agents.py::reply_nutri` | Comportamento idêntico, sem dependência do Hermes runtime |
| `skills/health/personal-trainer/SKILL.md` | persona em `agents.py::reply_personal` | Idem |
| `skills/health/master-agent/SKILL.md` | persona em `agents.py::reply_*` | Classificação + templates |
| `skills/health/ted-corrigido/SKILL.md` | `plan_training` editável na UI | Plano da semana agora vive no DB |


## O que mudou de design

1. **Estado do agente no banco, não em `state.json`.** O Hermes original
   mantinha `/tmp/nutri_tracker_state.json` e `/tmp/master_agent_context.json`
   — duas fontes da verdade que divergiam do DB. Aqui, tudo é SQL.
2. **Plano editável.** `PlanNutrition` e `PlanTraining` são entidades de primeira
   classe com endpoint CRUD. No Hermes eram strings hardcoded no prompt.
3. **Refeições com 3 opções (A/B/C).** A feature introduzida em 31/08/2026
   no Nutri está no campo `meals.opcao`.
4. **Templates determinísticos no lugar do LLM.** O chat funciona offline,
   sem necessidade de API key. A interface (`AgentReply`) permite trocar para
   LLM depois sem mudar os endpoints.
5. **Sem LLM = sem alucinação para classificador e respostas simples.**
   O `classifier.py` continua sendo regras puras (espelha `master_agent.py`).
6. **CORS aberto para localhost por default.** Em produção, ajustar.

## Integração com LLM (opcional)

Por padrão o chat é 100% determinístico e offline (como descrito acima). Pra
ligar respostas geradas por LLM via [OpenRouter](https://openrouter.ai/models)
(API compatível com OpenAI, qualquer modelo do catálogo deles), defina no
`.env`:

```bash
LLM_ENABLED=true
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=anthropic/claude-haiku-4.5   # qualquer slug do openrouter.ai/models
```

Com Docker, o `docker-compose.yml` já repassa essas variáveis do `.env` da
raiz pro serviço `api`. O que muda com `LLM_ENABLED=true`:

- **Texto da resposta** (Nutri/Personal/Master) passa a ser gerado pelo LLM,
  na voz de cada persona, com os dados reais (totais do dia, metas, treino de
  hoje) passados como contexto.
- **Classificação de intenção** (`ED_NUTRI`/`TED_PERSONAL`/`MIXED`/
  `ORCHESTRATOR`) também passa a ser feita pelo LLM.

O que **nunca** muda, mesmo com LLM habilitado:

- **`SAFETY_ALERT` nunca passa pelo LLM.** Termos de risco à saúde (dor no
  peito, ideação suicida, etc.) são sempre detectados por regra fixa em
  `classifier.py`, antes de qualquer chamada ao LLM — a resposta de
  emergência é sempre o texto fixo com SAMU/CVV.
- **Macros persistidas no banco continuam vindas de `estimate_macros()`**
  (regra fixa), nunca do LLM — o LLM só escreve o texto, os números que vão
  pro `meals`/dashboard nunca são "inventados" por ele.
- **Qualquer falha do LLM** (rede, timeout, resposta malformada) cai
  automaticamente pro classificador/templates determinísticos — o chat nunca
  quebra por causa do LLM. Ver `api/app/services/llm.py`.

## Próximos passos (roadmap)

- [ ] Autenticação (OAuth2/JWT)
- [ ] Múltiplos usuários (multi-tenant)
- [ ] Versão mobile (React Native ou PWA)
- [ ] Exportar PDF de relatório semanal
- [ ] Bot Telegram/WhatsApp opcional que reusa a API
- [ ] Migração para SQLite (para dev single-user)

## Licença

MIT — código de Michael Cruz, TI Eckomining. Dados do plano são pessoais;
**não commite dados reais de usuário** em produção.
