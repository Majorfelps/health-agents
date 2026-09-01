-- ============================================================================
-- health-agents — Schema (Postgres 17)
-- HISTÓRICO / REFERÊNCIA — não é mais aplicado automaticamente pelo
-- docker-compose. O schema real é gerenciado por Alembic
-- (api/alembic/versions/), rodado via `alembic upgrade head` no entrypoint
-- do container `api`. Mantido aqui só como leitura rápida do modelo de
-- dados; se divergir de api/app/models/models.py, o models.py (+ Alembic)
-- é que manda.
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  whatsapp_number VARCHAR(50) UNIQUE NOT NULL,
  name VARCHAR(120),
  age INTEGER,
  sex VARCHAR(20),
  height_cm INTEGER,
  weight_kg NUMERIC(5,2),
  goal TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS plan_nutrition (
  id SERIAL PRIMARY KEY,
  user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tdee INTEGER NOT NULL DEFAULT 2274,
  meta_kcal INTEGER NOT NULL DEFAULT 1770,
  meta_p INTEGER NOT NULL DEFAULT 186,
  meta_f INTEGER NOT NULL DEFAULT 70,
  meta_c INTEGER NOT NULL DEFAULT 165,
  meta_agua_ml INTEGER NOT NULL DEFAULT 2500,
  refeicoes_meta JSONB NOT NULL DEFAULT '{}',
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS plan_training (
  id SERIAL PRIMARY KEY,
  user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  protocolo JSONB NOT NULL DEFAULT '{}',
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS meals (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  meal_type VARCHAR(50) NOT NULL,
  description TEXT NOT NULL,
  opcao VARCHAR(1),
  calories NUMERIC(8,2),
  protein_g NUMERIC(8,2),
  carbs_g NUMERIC(8,2),
  fat_g NUMERIC(8,2),
  source VARCHAR(50) NOT NULL DEFAULT 'chat',
  logged_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_meals_user_date ON meals(user_id, logged_at DESC);

CREATE TABLE IF NOT EXISTS exercise_logs (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  workout_type VARCHAR(80) NOT NULL,
  exercises JSONB NOT NULL DEFAULT '[]',
  duration_minutes INTEGER,
  perceived_effort INTEGER,
  pain_report TEXT,
  notes TEXT,
  completed BOOLEAN NOT NULL DEFAULT TRUE,
  logged_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_exercise_logs_user_date ON exercise_logs(user_id, logged_at DESC);

CREATE TABLE IF NOT EXISTS checkins (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type VARCHAR(50) NOT NULL DEFAULT 'general',
  mood VARCHAR(50),
  hunger_level INTEGER,
  sleep_hours NUMERIC(4,2),
  water_liters NUMERIC(4,2),
  notes TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_checkins_user_date ON checkins(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS agent_messages (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  agent VARCHAR(50) NOT NULL,
  direction VARCHAR(20) NOT NULL,
  message TEXT NOT NULL,
  intent VARCHAR(50),
  extra JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_agent_messages_user_date ON agent_messages(user_id, created_at DESC);

-- Seed: Michael
INSERT INTO users (whatsapp_number, name, age, sex, height_cm, weight_kg, goal)
VALUES ('553199674109', 'Michael Cruz', 33, 'M', 180, 93, 'recomposição corporal (perder ~8kg de gordura + ganhar massa magra)')
ON CONFLICT (whatsapp_number) DO NOTHING;
