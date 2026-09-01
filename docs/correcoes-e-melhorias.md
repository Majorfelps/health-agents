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

## Etapa 3 — Infraestrutura de banco de dados

- [ ] **Decidir sobre o Alembic**: hoje `api/alembic/` existe mas está vazio
  (sem `alembic.ini`, `env.py`, migrações, nem a lib no `requirements.txt`).
  - Opção A (mínima): remover a pasta e continuar só com `db/schema.sql` +
    `create_all()` no startup — documentar essa decisão no README.
  - Opção B (recomendada para produção real): inicializar o Alembic de
    verdade (`alembic init`, `env.py` apontando para `Base.metadata`,
    gerar a migração inicial a partir de `db/schema.sql`), adicionar
    `alembic` ao `requirements.txt`, e trocar `Base.metadata.create_all()`
    no `main.py` por `alembic upgrade head` no entrypoint do container.

## Etapa 4 — Plano de treino editável (fechar o gap funcional)

- [ ] **Fazer `/workouts/today`, o dashboard e o chat lerem `plan_training.protocolo`
  do banco** em vez do dicionário estático `PLANO_SEMANAL` em `agents.py`.
  Hoje o `PUT /api/v1/plan/training` grava no banco mas nada lê esse valor —
  editar o plano pela UI (`web/app/plan/page.tsx`) não muda o que aparece
  como "treino de hoje".
  - Manter `PLANO_SEMANAL` só como seed inicial (já é usado assim em
    `repository.seed_default_plans`).
  - Ajustar `api/app/api/v1/workouts.py::today_workout` e
    `api/app/api/v1/dashboard.py::dashboard` para buscar
    `user.plan_training.protocolo[weekday]` com fallback pro estático se
    vazio.

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
