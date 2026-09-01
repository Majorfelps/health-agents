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

## Etapa 5 — Testes e cobertura

- [ ] **Adicionar testes em `api/tests/`** (hoje vazio). Prioridade:
  1. `classifier.classify()` — casos de SAFETY_ALERT, GREETING, MIXED,
     ED_NUTRI, TED_PERSONAL (é a lógica mais frágil/regras many-branch).
  2. `repository.today_totals()` / `last_n_days_totals()` — regressão pro
     bug da Etapa 1, garantir que não volte a acontecer.
  3. Endpoint `/api/v1/chat` — fluxo completo (classificação → resposta →
     persistência → detected_meal).
- [ ] Adicionar um job de CI simples (`.github/workflows/` já existe a pasta,
  mas só tem `.gitkeep`) rodando `pytest` e `npm run lint` / `next build`.

## Etapa 6 — Itens do roadmap já sinalizados no README (não urgentes)

Sem mudança de prioridade sugerida aqui, apenas repetindo o que já está
documentado no `README.md` para manter tudo num lugar só:

- [ ] Autenticação (OAuth2/JWT) — hoje todo endpoint usa o usuário fixo
  `553199674109` (Michael) via default de query param.
- [ ] Multi-tenant (múltiplos usuários reais).
- [ ] Integração opcional com LLM (toggle em `.env`) no lugar dos templates
  determinísticos em `agents.py`.
- [ ] Exportar PDF de relatório semanal.
- [ ] Bot Telegram/WhatsApp opcional reusando a API atual.

---

**Sugestão de ordem de execução**: Etapa 1 (bug de dado) → Etapa 2 (consistência
de ambiente) → Etapa 5.2 (teste de regressão do bug 1) → Etapa 4 (fechar gap
funcional do plano de treino) → Etapa 3 (Alembic) → Etapa 5 (resto dos testes)
→ Etapa 6 (roadmap de produto).
