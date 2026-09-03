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
│   │   ├── api/v1/          # routers: chat, meals, workouts, plans, checkins, dashboard, llm, whatsapp
│   │   ├── core/            # config, db
│   │   ├── models/          # SQLAlchemy
│   │   ├── schemas/         # Pydantic
│   │   └── services/
│   │       ├── classifier.py       # classifica intenção (NUTRI / TREINO / MIXED / ORCHESTRATOR / SAFETY)
│   │       ├── agents.py           # personas + biblioteca de treinos + estimador de macros
│   │       ├── repository.py       # queries (totais do dia, semana, check-ins, config LLM/WhatsApp)
│   │       ├── llm.py              # cliente OpenRouter opcional (ver "Integração com LLM" abaixo)
│   │       ├── exercise_images.py  # imagens de demonstração (wger.de, ver seção abaixo)
│   │       └── whatsapp.py         # cliente Evolution API opcional (ver "Espelhamento pro WhatsApp")
│   ├── alembic/             # migrações (fonte de verdade do schema — ver db/schema.sql abaixo)
│   ├── tests/                # pytest (testcontainers — Postgres descartável, sem rede real)
│   ├── requirements.txt
│   ├── requirements-dev.txt  # + pytest/testcontainers, só pra rodar tests/
│   └── Dockerfile
├── web/
│   ├── app/
│   │   ├── page.tsx         # Dashboard (totais, metas, treino do dia, gráfico 7 dias)
│   │   ├── chat/            # Chat estilo WhatsApp
│   │   ├── plan/            # Editor de plano nutricional + treino
│   │   ├── checkins/        # Form + histórico
│   │   └── settings/        # Liga/desliga o LLM, escolhe e testa o modelo (OpenRouter)
│   ├── components/NavBar.tsx
│   ├── lib/{api,types}.ts
│   ├── package.json
│   └── Dockerfile
├── db/
│   └── schema.sql           # referência do modelo de dados (não é mais aplicado automaticamente — ver api/alembic/)
├── docs/
│   ├── migration-from-hermes.md
│   └── correcoes-e-melhorias.md  # histórico de correções/melhorias aplicadas
├── .github/workflows/ci.yml  # pytest (api) + lint/build (web)
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

- **http://localhost:3000** — app (dashboard, chat, planos, check-ins, IA)
- **http://localhost:8088/docs** — Swagger da API (8088, não 8000 — porta
  8000 do host já era usada por outro serviço, ver comentário no
  `docker-compose.yml`)

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
| `GET`  | `/api/v1/workouts/today` | Treino do dia, resolvido do plano do usuário (`plan_training`) |
| `POST` | `/api/v1/workouts` | Registra treino feito |
| `GET`  | `/api/v1/plan/nutrition` / `PUT` | CRUD plano nutri |
| `GET`  | `/api/v1/plan/training` / `PUT` | CRUD plano treino |
| `POST` | `/api/v1/checkins` | Check-in (humor, fome, sono, água) |
| `GET`  | `/api/v1/llm/config` / `PUT` | Liga/desliga o LLM e troca o modelo — vale no próximo chat, sem restart |
| `POST` | `/api/v1/llm/test` | Testa um modelo de verdade antes de salvar (não persiste nada) |
| `GET`  | `/api/v1/llm/status` | LLM habilitado? Qual modelo (sem expor a key) |
| `GET`  | `/api/v1/llm/models?free_only=true` | Catálogo de modelos do OpenRouter (só gratuitos por padrão — ver "Integração com LLM" abaixo) |
| `GET`  | `/api/v1/whatsapp/config` / `PUT` | Liga/desliga o espelhamento pro WhatsApp e troca o número — vale no próximo chat, sem restart |
| `POST` | `/api/v1/whatsapp/test` | Confirma que a instância da Evolution API está acessível/conectada (não envia mensagem) |
| `GET`  | `/api/v1/whatsapp/status` | Espelhamento habilitado? Pra qual número (sem expor a key) |
| `GET`  | `/health` | Healthcheck |

## Mapeamento com Hermes original

| Hermes (origem) | health-agents (este repo) | Notas |
|---|---|---|
| `scripts/health_classifier.py` (144 linhas) | `api/app/services/classifier.py` | Mesmas regras, removido LLM, dataclass → JSON-serializable |
| `scripts/master_agent.py::classify()` (741 linhas) | `api/app/services/classifier.py` | Função `classify()` portada com prioridade GREETING→MIXED→específico |
| `scripts/master_agent.py::generate_llm_reply()` (LLM) | `api/app/services/agents.py` + `llm.py` | Templates determinísticos por padrão; LLM via OpenRouter opcional (ver "Integração com LLM") |
| `scripts/master_agent.py::PLANO_SEMANAL` | `api/app/services/agents.py::WORKOUT_LIBRARY` | Idêntico, agora indexado por nome (não por dia) e resolvido a partir do plano do usuário, editável via UI em `plan/training` |
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
4. **Templates determinísticos por padrão, LLM opcional.** O chat funciona
   offline, sem necessidade de API key — a interface (`AgentReply`) já foi
   pensada pra isso. Um LLM via OpenRouter pode ser ligado sem mudar
   endpoint nenhum (ver "Integração com LLM" abaixo).
5. **Classificador continua 100% regras por padrão.** `classifier.classify()`
   (usada quando o LLM tá desligado, e como fallback de qualquer falha do
   LLM) segue sendo regras puras (espelha `master_agent.py`) — sem
   alucinação nem dependência de rede nesse caminho.
6. **CORS aberto para localhost por default.** Em produção, ajustar.

## Integração com LLM (opcional)

Por padrão o chat é 100% determinístico e offline (como descrito acima). Pra
ligar respostas geradas por LLM via [OpenRouter](https://openrouter.ai/models)
(API compatível com OpenAI, qualquer modelo do catálogo deles):

1. Defina a chave no `.env` (só isso é env-only, por segurança — não dá pra
   trocar por API):
   ```bash
   OPENROUTER_API_KEY=sk-or-v1-...
   ```
   Com Docker, o `docker-compose.yml` já repassa essa variável do `.env` da
   raiz pro serviço `api`.
2. **Liga o LLM e escolhe o modelo pela própria aplicação** — tela **IA**
   (`/settings`) no web, ou direto na API:
   ```bash
   # lista modelos gratuitos do OpenRouter (bons pra testar sem gastar —
   # ~50 req/dia por conta, sobe pra 1000/dia comprando 10 créditos)
   curl http://localhost:8088/api/v1/llm/models | jq

   # catálogo inteiro
   curl "http://localhost:8088/api/v1/llm/models?free_only=false" | jq

   # testa o modelo ANTES de salvar (chamada real, não persiste nada) —
   # alguns modelos :free são restritos a "agentic harnesses" e recusam
   # chat comum com 403; o teste pega isso na hora
   curl -X POST http://localhost:8088/api/v1/llm/test \
     -H "Content-Type: application/json" \
     -d '{"model": "anthropic/claude-haiku-4.5"}'

   # liga e escolhe o modelo — vale no próximo chat, sem reiniciar nada
   curl -X PUT http://localhost:8088/api/v1/llm/config \
     -H "Content-Type: application/json" \
     -d '{"enabled": true, "model": "anthropic/claude-haiku-4.5"}'

   # confere a config atual (sem expor a API key)
   curl http://localhost:8088/api/v1/llm/config
   ```

Essa config (`enabled`/`model`) fica no banco (tabela `llm_config`, uma
linha só), não em variável de ambiente — trocar de modelo ou desligar o LLM
é imediato, não precisa editar `.env` nem dar restart no container.
`LLM_ENABLED`/`OPENROUTER_MODEL` no `.env` só definem o valor inicial (1ª
vez que o app sobe com o banco vazio); depois disso quem manda é o banco.

O que muda com o LLM habilitado:

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
- **Qualquer falha do LLM** (rede, timeout, resposta malformada, rate limit,
  modelo restrito/indisponível) cai automaticamente pro
  classificador/templates determinísticos — o chat nunca quebra por causa do
  LLM. Ver `api/app/services/llm.py`. Use `POST /api/v1/llm/test` (ou o
  botão "Testar modelo" em `/settings`) antes de trocar o modelo em uso,
  pra pegar esses problemas na hora em vez de só ver o fallback silencioso.

## Imagens de demonstração de exercício (ED o Personal)

Quando a mensagem menciona um exercício específico (ex: "como faz o supino
reto barra?") o ED o Personal anexa só a foto desse exercício; numa
pergunta geral (ex: "qual o treino de hoje?") ele anexa a foto de **todos**
os exercícios do treino do dia que tiverem imagem mapeada — cada uma já
nomeada com o exercício certo, tanto na resposta do LLM quanto na UI —
via [wger.de](https://wger.de) (banco de exercícios aberto, CC0/CC-BY-SA,
sem API key).

Avaliamos gerar imagem por IA primeiro: **nenhum modelo gratuito da
OpenRouter gera imagem** (catálogo checado ao vivo — só 11 modelos com
saída de imagem no total, todos pagos), e além do custo, geração por IA
não é confiável pra mostrar postura/forma corretas de um exercício. Fotos
reais de um banco aberto resolvem isso sem custo nenhum.

É um **mapeamento curado, não busca ao vivo** — a API pública do wger não
tem busca por nome funcional (só filtro por match exato), então
`api/app/services/exercise_images.py` mapeia manualmente os exercícios do
`WORKOUT_LIBRARY` que têm imagem real disponível (10 dos 30 atualmente).
Exercício fora do mapeamento simplesmente não manda imagem — cai pro texto
normal, sem quebrar nada. Pra adicionar mais, ver o docstring do arquivo.

## Espelhamento pro WhatsApp (opcional)

Por padrão as respostas do chat ficam só no web. Pra também chegarem no
WhatsApp via [Evolution API](https://github.com/EvolutionAPI/evolution-api)
(**mesma instância que o bot antigo do Hermes usa** — ver observação
importante abaixo):

1. Defina as credenciais no `.env` (infra, só `.env`, igual
   `OPENROUTER_API_KEY`):
   ```bash
   EVOLUTION_API_URL=http://host.docker.internal:8080  # ou o host onde a Evolution roda
   EVOLUTION_API_KEY=...
   EVOLUTION_INSTANCE=...   # nome da instância conectada (confira com /instance/fetchInstances)
   ```
   Com Docker, `docker-compose.yml` já repassa essas variáveis e resolve
   `host.docker.internal` (Linux, Docker Engine ≥20.10) — útil quando a
   Evolution API roda num container/stack separado deste projeto.
2. **Liga o espelhamento e escolhe o número pela própria aplicação** —
   tela **IA** (`/settings`) no web, seção "Espelhar no WhatsApp", ou
   direto na API:
   ```bash
   # testa a conexão ANTES de habilitar (não envia mensagem)
   curl -X POST http://localhost:8088/api/v1/whatsapp/test

   # liga e define o número — vale no próximo chat, sem restart
   curl -X PUT http://localhost:8088/api/v1/whatsapp/config \
     -H "Content-Type: application/json" \
     -d '{"enabled": true, "target_number": "553199674109"}'
   ```

Essa config (`enabled`/`target_number`) fica no banco (tabela
`whatsapp_config`), como no LLM — `WHATSAPP_ENABLED`/`WHATSAPP_TARGET_NUMBER`
no `.env` só semeiam o valor inicial.

**O que é enviado:** só a resposta do agente (texto), depois que ela é
gerada — nunca a mensagem que você digitou no web (você já a viu lá).
Qualquer falha de envio (rede, instância desconectada, credenciais erradas)
é capturada e nunca quebra a resposta do chat web — ver
`api/app/services/whatsapp.py`.

**⚠️ Se você já usa um bot de WhatsApp separado no mesmo número** (como o
`master_agent_listener` do Hermes, que responde mensagens recebidas de
verdade): esse espelhamento é **só de saída** (web → WhatsApp) — o
health-agents não lê nem responde mensagens que chegam no WhatsApp, então
não some com o outro bot nem cria loop de resposta automática. Mas os dois
sistemas continuam sendo cérebros **independentes** (estados separados,
classificação separada) — se você responder no WhatsApp uma mensagem que
o health-agents mandou, quem processa é o outro bot, não este projeto.

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
