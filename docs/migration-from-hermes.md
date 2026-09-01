# Migration from Hermes

Este documento explica o que mudou quando TED/ED foram portados do Hermes
para este monorepo. Útil para quem mantém o Hermes em produção e quer
sincronizar mudanças.

## Arquivos do Hermes que foram portados

### Backend (Python)

| Arquivo Hermes | → health-agents | Mudança |
|---|---|---|
| `~/.hermes/scripts/health_classifier.py` | `api/app/services/classifier.py` | dataclass, sem psycopg2, removeu a parte de DB |
| `~/.hermes/scripts/master_agent.py::classify()` | `api/app/services/classifier.py` | Mesma lógica, importável como serviço |
| `~/.hermes/scripts/master_agent.py::generate_llm_reply()` | `api/app/services/agents.py::gerar_resposta()` | Templates determinísticos (sem LLM) |
| `~/.hermes/scripts/master_agent.py::PLANO_SEMANAL` | `api/app/services/agents.py::PLANO_SEMANAL` | Idêntico, exposto em `/api/v1/workouts/today` |
| `~/.hermes/scripts/master_agent.py::FOOD_TABLE` | `api/app/services/agents.py::FOOD_TABLE` | Idem, retorna `dict` em vez de tuple |
| `~/.hermes/scripts/health_db.py` | `api/app/services/repository.py` + `models/models.py` | SQLAlchemy 2.0, com `plan_nutrition`/`plan_training` |
| `~/.hermes/scripts/health_webhook.py` | (não portado) | Substituído por `/api/v1/chat` direto |
| `~/.hermes/scripts/health_weekly_review.py` | (não portado) | Substituível por `GET /api/v1/dashboard` |

### Schema

| Hermes | → health-agents |
|---|---|
| `~/.hermes/scripts/health_db_bootstrap.sql` (5 tabelas) | `db/schema.sql` (8 tabelas) — adiciona `plan_nutrition`, `plan_training`, e `meals.opcao` |

### Skills (Personas)

| Skill | → health-agents |
|---|---|
| `skills/health/nutri-agent/SKILL.md` | Persona em `api/app/services/agents.py::reply_nutri` |
| `skills/health/personal-trainer/SKILL.md` | Persona em `api/app/services/agents.py::reply_personal` |
| `skills/health/master-agent/SKILL.md` | Persona em `api/app/services/agents.py::reply_*` (greeting/unknown/mixed) |
| `skills/health/ted-corrigido/SKILL.md` | Substituído por `plan_training` editável |
| `skills/health/ted-personal-plano-corrigido/SKILL.md` | Idem |

## Sincronização futura

Se você mudar a persona no SKILL.md do Hermes, **edite também o `agents.py`**
(ou o contrário, se começar pelo código).

Se você mudar a `PLANO_SEMANAL` no `master_agent.py`, atualize a constante no
`agents.py` e também o `plan_training` no banco (PUT `/api/v1/plan/training`).

Se você mudar `FOOD_TABLE` (macros), edite a constante em `agents.py`.

## Diferenças intencionais

1. **Sem LLM no MVP.** Substituí o LLM (OpenRouter stealth/ox-alpha) por
   templates determinísticos. Para reativar LLM, basta preencher
   `generate_llm_reply()` em `agents.py` chamando um provider configurado.
2. **Sem Evolution/WhatsApp no MVP.** O chat é web direto. Para reativar o
   gateway WhatsApp, portar `health_webhook.py` para `api/app/api/v1/webhook.py`
   e ajustar `health_classifier.classify()` para o payload Evolution.
3. **DB schema estendido.** Adicionei `plan_nutrition`, `plan_training` e
   `meals.opcao` (A/B/C) que o Hermes ainda não tem como entidades próprias.
4. **Sem dependência de `/tmp/*` state.json.** Tudo está no Postgres. Se você
   tem dados antigos no `nutri_tracker_state.json`, importe via script de
   migração (TODO).
