# Correções e Melhorias — Health Agents

Baseado na auditoria de 2026-09-01 (stack testado via `docker compose up --build`).

## Etapa 1 — Bug crítico (dado errado exibido ao usuário) ✅ concluída (2026-09-01)

- [x] **Corrigir troca de Carboidrato/Gordura em `today_totals()`**
  Arquivo: `api/app/services/repository.py:56-73`
  A query rotula `carbs_g` como `"F"` e `fat_g` como `"C"`. Trocar os `.label(...)`
  para `carbs_g` → `"C"` e `fat_g` → `"F"`, igual já está correto em
  `last_n_days_totals()` (linhas 104-110, usada como referência).
  Confirmado ao vivo: refeição real com F5/C69 apareceu no dashboard como F69/C5.

## Etapa 2 — Consistência dev local / Docker ✅ concluída (2026-09-01)

- [x] **Corrigir `NEXT_PUBLIC_API_URL` no build Docker do `web`**
  Adicionado `ARG`/`ENV NEXT_PUBLIC_API_URL` no `web/Dockerfile` (stage
  `builder`, antes do `RUN npm run build`) e `build.args` no
  `docker-compose.yml` apontando para `http://localhost:8088` (porta
  exposta no host — é o que o *browser* precisa enxergar, não o hostname
  interno `api`). Confirmado via `grep` no `.next/server/app/*.js` do
  container que o valor foi de fato embutido no bundle.
- [x] **Remover o rewrite morto em `next.config.js`**
  Removido — o front nunca usava o proxy relativo (`api.ts` sempre chamou
  `API_BASE + url`, URL absoluta). Ao remover, um `fetch()` solto em
  `web/app/chat/page.tsx` (histórico do chat) que *dependia* desse rewrite
  quebrou (500) — corrigido trocando para `${API_BASE}/api/v1/chat/history`,
  mesmo padrão usado no resto do app. `API_BASE` agora é exportado de
  `web/lib/api.ts`.
- [x] **Criar `web/.env.example`** com `NEXT_PUBLIC_API_URL=http://localhost:8000`
  para dev local sem Docker (a API sobe em 8000 nesse fluxo, não 8088).
- Validado ao vivo: rebuild completo (`docker compose up --build`),
  navegação em `/`, `/chat`, `/plan`, `/checkins` — todas as chamadas de API
  batendo em `localhost:8088`, sem 500/CORS/console errors.

## Etapa 3 — Infraestrutura de banco de dados ✅ concluída (2026-09-01)

Optou-se pela Opção B (Alembic como fonte única de verdade do schema).

- [x] `alembic.ini` + `alembic/env.py` (lê `DATABASE_URL` de
  `app.core.config.settings`, `target_metadata = Base.metadata`) +
  `alembic/script.py.mako` escritos à mão.
- [x] `alembic==1.14.0` adicionado ao `api/requirements.txt`.
- [x] Migração inicial `alembic/versions/2c526581025c_initial_schema.py`
  gerada via `alembic revision --autogenerate` contra um Postgres vazio
  (container descartável), cobrindo as 7 tabelas de `models.py` + o seed
  do usuário Michael (mesmo `INSERT ... ON CONFLICT DO NOTHING` que estava
  em `db/schema.sql`).
- [x] `api/Dockerfile`: `CMD` agora roda `alembic upgrade head && uvicorn ...`
  antes de servir requests.
- [x] `api/app/main.py`: removido `Base.metadata.create_all()` do
  `lifespan` — schema passa a ser 100% responsabilidade do Alembic.
- [x] `docker-compose.yml`: removido o mount de `db/schema.sql` em
  `docker-entrypoint-initdb.d` do serviço `db` (evita as duas fontes
  tentarem criar as mesmas tabelas — `db` agora sobe vazio, o `api`
  aplica a migração no startup).
- [x] `db/schema.sql` marcado como referência histórica no comentário do
  topo (não é mais executado automaticamente).
- [x] README atualizado: seção "Rodando sem Docker" agora manda rodar
  `alembic upgrade head` antes do `uvicorn`, e criar `web/.env.local` a
  partir do `web/.env.example` (Etapa 2).
- Validado ao vivo: `docker volume rm` + `docker compose up --build` do
  zero → logs mostram a migração rodando antes do uvicorn subir, 8 tabelas
  criadas (+ `alembic_version`), usuário seed presente, `restart` do `api`
  não tenta recriar nada (idempotente), fluxo de chat com refeição
  funcionando com F/C corretos.

## Etapa 4 — Plano de treino editável (fechar o gap funcional) ✅ concluída (2026-09-01)

- [x] **`/workouts/today`, o dashboard e o chat agora lêem `plan_training.protocolo`
  do banco.** A UI (`web/app/plan/page.tsx`) só edita o *nome* do treino de
  cada dia (texto livre), não a lista de exercícios — então a solução foi
  separar em `api/app/services/agents.py`:
  - `WORKOUT_LIBRARY`: dict nome → {foco, séries, exercícios} (era o antigo
    `PLANO_SEMANAL`, agora indexado por nome em vez de dia da semana).
  - `PLANO_SEMANAL_PADRAO`: dict dia da semana → nome, usado só como seed
    inicial (`repository.seed_default_plans`) e como fallback.
  - `resolve_treino_do_dia(protocolo, weekday)`: resolve o nome salvo pelo
    usuário na biblioteca; nome customizado (fora da biblioteca) degrada
    graciosamente — mostra o nome, sem inventar exercícios, com um aviso
    no chat orientando a usar um dos nomes padrão.
  - `api/app/api/v1/workouts.py::today_workout`, `dashboard.py::dashboard`
    e `chat.py` (via `agents.gerar_resposta(..., protocolo=...)`) agora
    passam `user.plan_training.protocolo` para o resolver.
  - Corrigido de quebra um bug latente no seed: `seed_default_plans` grava
    `"CARDIO HIIT"`/`"CARDIO LISS"` sem o sufixo de duração, que nunca
    batia com as chaves da biblioteca (`"CARDIO HIIT 20min"` etc.) — agora
    usa `PLANO_SEMANAL_PADRAO`, com os nomes corretos, como única fonte.
- Validado ao vivo: troquei o treino de terça (hoje) via `PUT
  /plan/training` para um nome customizado → dashboard, `/workouts/today`
  e o chat ("qual o treino de hoje?") mostraram o fallback consistente nos
  três lugares; troquei para outro nome da biblioteca (UPPER B) → os três
  refletiram os exercícios corretos; revertido pro padrão e conferido
  visualmente no browser (dashboard renderizando LOWER A com macros ainda
  corretos da Etapa 1).

## Etapa 5 — Testes e cobertura ✅ concluída (2026-09-01)

- [x] **24 testes em `api/tests/`** (antes vazio), usando `testcontainers`
  pra subir um Postgres descartável por sessão de teste (não precisa de
  Postgres já rodando na máquina de quem roda `pytest`):
  - `test_classifier.py` — SAFETY_ALERT, GREETING (simples e "bom dia"/
    "boa tarde"), MIXED, ED_NUTRI, TED_PERSONAL, mensagem vazia,
    `looks_like_meal()`.
  - `test_repository.py` — regressão direta pro bug da Etapa 1
    (`today_totals()` e `last_n_days_totals()` não podem trocar F/C),
    soma de múltiplas refeições, usuário sem refeição, idempotência do
    `seed_default_plans`.
  - `test_chat_endpoint.py` — fluxo completo via `TestClient`: saudação,
    refeição persistida batendo com `meals/today`, `persist=false` não
    grava histórico, ordem cronológica do histórico, dashboard refletindo
    plano de treino editado (regressão da Etapa 4), SAFETY_ALERT não
    confunde com refeição.
  - `api/requirements-dev.txt` com `pytest` + `httpx` + `testcontainers`.
- [x] **Bug real pego pelo próprio teste, corrigido**: `classifier.py` não
  reconhecia "bom dia"/"boa tarde"/"boa noite" como saudação — `tokens`
  são palavras soltas (`{"bom","dia"}`) mas `GREETING_TERMS` guardava a
  frase inteira como um elemento do set, então a comparação por
  subconjunto nunca batia. Corrigido com `_GREETING_TOKENS` (palavras
  soltas derivadas de `GREETING_TERMS`).
- [x] **CI em `.github/workflows/ci.yml`** (a pasta só tinha `.gitkeep` e,
  por engano, um `__init__.py` — removido): job `api-tests` (pytest, sobe
  o Postgres via Docker do próprio runner) e `web-build` (`npm install` +
  `npm run lint` + `npm run build`).
- [x] **Corrigido de quebra pra CI funcionar**: `npm run lint` ficava preso
  num wizard interativo — `eslint`/`eslint-config-next` nunca tinham sido
  instalados de verdade, só o script no `package.json`. Adicionadas as
  deps + `web/.eslintrc.json`, e corrigidos 2 erros reais de lint (aspas
  não escapadas em JSX, `chat/page.tsx` e `checkins/page.tsx`).
- [x] **Achado à parte, corrigido**: `npm install` acusou `next@15.1.6`
  com ~30 CVEs conhecidas (1 crítica — exposição de informação/RCE via
  protocolo React Flight). Atualizado para `next@15.5.25` (mesma major,
  sem mudança de API usada no projeto) — `npm audit` cai de 3
  vulnerabilidades (2 high, 1 crítica) pra 2 (a única alta restante é
  `postcss` embutido dentro do próprio `next`, só resolvida com upgrade
  pra Next 16, que é breaking — deixado de fora por ora).
- Validado ao vivo: 24/24 testes passando, `npm run lint`/`npm run build`
  limpos, rebuild Docker completo com o Next atualizado (`docker compose
  up --build` do zero) — dashboard, chat e macros (Etapa 1) continuam
  corretos no browser.

## Etapa 6 — Itens do roadmap já sinalizados no README (não urgentes)

Estes itens não têm uma correção de código a aplicar — são decisões de
produto/escopo maior, cada uma merecendo sua própria conversa antes de
começar a implementar. Deixados aqui só pra manter tudo num lugar só; sem
mudança de prioridade sugerida em relação ao que já estava no `README.md`:

- [ ] Autenticação (OAuth2/JWT) — hoje todo endpoint usa o usuário fixo
  `553199674109` (Michael) via default de query param.
- [ ] Multi-tenant (múltiplos usuários reais).
- [x] **Integração opcional com LLM** ✅ concluída (2026-09-01) — via
  OpenRouter. `api/app/services/llm.py` gera o texto das respostas e
  (mesmo toggle) a classificação de intenção — `SAFETY_ALERT` continua
  sempre por regra fixa em `classifier.py`, nunca chega a chamar o LLM, e
  macros persistidas continuam vindas de `estimate_macros()`, nunca do
  LLM. Qualquer falha (rede, timeout, JSON malformado, rate limit) cai pro
  caminho determinístico.
  - **Troca de modelo/toggle pela própria aplicação** (não só `.env`):
    config (`enabled`/`model`) fica numa tabela `llm_config` (singleton),
    editável via `GET`/`PUT /api/v1/llm/config` e pela tela **IA**
    (`/settings`) no web — vale no próximo chat, sem restart do
    container. `.env` (`LLM_ENABLED`/`OPENROUTER_MODEL`) só semeia o
    valor inicial na 1ª criação da linha; `OPENROUTER_API_KEY` continua
    só no `.env` (não editável por API, por segurança).
  - `GET /api/v1/llm/models?free_only=true` lista o catálogo do
    OpenRouter (público, não precisa de config) — filtra só os gratuitos
    por padrão, bons pra testar. Confirmado ao vivo: modelos `:free` têm
    rate limit de ~50 req/dia por conta.
  - **`POST /api/v1/llm/test`** + botão "Testar modelo" na tela de
    Configurações: faz uma chamada real (sem persistir nada) pro modelo
    digitado/selecionado, antes de salvar. Adicionado depois que o
    usuário reportou o Master Agent "respondendo de forma automatizada" —
    na real era o fallback funcionando certo: o modelo escolhido
    (`thinkingmachines/inkling:free`) é restrito a "agentic harnesses" no
    OpenRouter e recusa chat comum com 403. O teste pega esse tipo de
    problema antes de salvar como modelo em uso, com a mensagem de erro
    exibida na UI.
  - 24 testes em `api/tests/test_llm.py` (mocks — sem chamada de rede
    real no CI), cobrindo fallback, endpoints, persistência da config e
    `test_model()`.
  - Validado ao vivo com chave real do OpenRouter: os 5 caminhos de
    intenção, troca de modelo via `curl` e via UI (browser) sem restart,
    volta ao determinístico quando o modelo escolhido bate rate limit ou
    é restrito a agentic harnesses, e o botão "Testar modelo" pegando
    esse último caso na hora (antes de salvar) tanto via `curl` quanto
    clicando na UI. Três bugs achados e corrigidos no processo: o modelo
    envolvia o JSON da classificação em ` ```json ``` ` (quebrava o
    parser), usava markdown (`**`, `#`, `---`) que aparecia literal na UI
    (texto puro, sem parser de markdown), e a falta de uma forma de
    validar um modelo antes de salvá-lo como o modelo em uso.
- [x] **Água e treino mencionados no chat não eram persistidos** ✅
  corrigido (2026-09-01) — reportado pelo usuário ("a memória das
  refeições, água e exercícios não está sendo guardada"). Investigando:
  refeições já eram persistidas (`meals`, desde sempre), mas água e
  treino mencionados no chat nunca viravam registro nenhum — só existiam
  via os forms separados (`POST /checkins`, `POST /workouts`), que o chat
  nunca aciona. E mesmo refeições: o LLM só recebia totais agregados
  (kcal/P/F/C), nunca a lista do que foi comido.
  - `classifier.looks_like_water(text)` — detecta "bebi/tomei Xml/X
    litros de água" (200ml padrão sem quantidade explícita), exclui
    perguntas/metas. `classifier.looks_like_completed_workout(text)` —
    detecta treino já concluído ("treinei", "fiz o treino", "malhei"),
    exclui perguntas ("qual treino hoje?") e intenção futura ("vou
    treinar").
  - `chat.py` agora persiste `Checkin(type="water")` e
    `ExerciseLog(completed=True)` quando detectados (mesmo padrão de
    `payload.persist` que já valia pra `Meal`) — o treino usa
    `resolve_treino_do_dia()` pra pegar nome/exercícios reais do plano do
    usuário, não inventa nada.
  - Contexto passado ao LLM (`agents._gerar_resposta_llm`) enriquecido
    com `refeicoes_ja_registradas_hoje` (lista, não só totais), `agua_
    detectada_nesta_mensagem_ml` e `treino_de_hoje_ja_registrado_como_
    concluido` — assim ele responde pro momento real, não só pros
    números agregados.
  - `ChatOut` ganhou `detected_water_ml`/`detected_workout` (mesmo padrão
    de `detected_meal`), pro frontend/testes confirmarem o que foi
    persistido.
  - Sem migração nova — só reusa colunas que já existiam em `Checkin`/
    `ExerciseLog`.
  - 19 testes novos (detectores, repository, endpoint HTTP de ponta a
    ponta, contexto do LLM). Validado ao vivo: "bebi 500ml de água" →
    `agua_ml` bate em `/meals/today` E o LLM referencia os 500ml na
    resposta; "treinei hoje" → `ExerciseLog` criado com o treino real do
    dia E uma pergunta seguinte ("qual treino de hoje?") já vem com "já
    registrado como concluído"; pergunta "o que eu já comi hoje?" → LLM
    lista as refeições específicas do dia, não só o total.
- [ ] Exportar PDF de relatório semanal.
- [ ] Bot Telegram/WhatsApp opcional reusando a API atual.

---

**Sugestão de ordem de execução**: Etapa 1 (bug de dado) → Etapa 2 (consistência
de ambiente) → Etapa 5.2 (teste de regressão do bug 1) → Etapa 4 (fechar gap
funcional do plano de treino) → Etapa 3 (Alembic) → Etapa 5 (resto dos testes)
→ Etapa 6 (roadmap de produto).
