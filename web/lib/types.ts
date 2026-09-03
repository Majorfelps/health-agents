/** Tipos compartilhados — espelham os schemas Pydantic do backend. */

export type Intent = "ED_NUTRI" | "TED_PERSONAL" | "MIXED" | "ORCHESTRATOR" | "SAFETY_ALERT";

export interface User {
  id: number;
  whatsapp_number: string;
  name: string | null;
  age: number | null;
  sex: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  goal: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlanNutrition {
  id: number;
  user_id: number;
  tdee: number;
  meta_kcal: number;
  meta_p: number;
  meta_f: number;
  meta_c: number;
  meta_agua_ml: number;
  refeicoes_meta: Record<string, { meta_kcal: number; P: number; F: number; C: number }>;
  updated_at: string;
}

export interface PlanTraining {
  id: number;
  user_id: number;
  protocolo: Record<string, string>;
  ativo: boolean;
  updated_at: string;
}

export interface DashboardTotals {
  kcal: number;
  P: number;
  F: number;
  C: number;
  agua_ml: number;
}

export interface DashboardOut {
  user: User;
  plan_nutrition: PlanNutrition | null;
  plan_training: PlanTraining | null;
  today: DashboardTotals;
  last_7_days: Record<string, DashboardTotals>;
  workout_today: { weekday: number; weekday_pt: string; nome: string; foco: string; series?: number; exercicios: Array<[string, string, string, string]> };
  last_checkin: any | null;
}

export interface CheckinOut {
  id: number;
  user_id: number;
  type: string;
  mood: string | null;
  hunger_level: number | null;
  sleep_hours: number | null;
  water_liters: number | null;
  notes: string | null;
  created_at: string;
}

export interface ExerciseImage {
  exercise: string;
  url: string;
}

export interface ChatMessage {
  id?: number;
  agent: string;
  direction: "inbound" | "outbound";
  message: string;
  intent?: string;
  images?: ExerciseImage[];
  created_at?: string;
}

export interface ChatResponse {
  user_message: string;
  intent: Intent;
  confidence: number;
  matched_terms: string[];
  reasoning: string;
  agent: string;
  reply: string;
  detected_meal: { descricao: string; kcal: number; P: number; F: number; C: number } | null;
  detected_water_ml: number | null;
  detected_workout: boolean;
  images: ExerciseImage[];
  whatsapp_sent: boolean;
  message_id: number | null;
}

export interface LLMConfig {
  enabled: boolean;
  model: string;
  updated_at: string;
}

export interface LLMTestResult {
  ok: boolean;
  sample?: string | null;
  error?: string | null;
}

export interface LLMModel {
  id: string;
  name: string;
  context_length: number;
  is_free: boolean;
  pricing: { prompt: string; completion: string };
}

export interface WhatsAppConfig {
  enabled: boolean;
  target_number: string;
  updated_at: string;
}

export interface WhatsAppTestResult {
  ok: boolean;
  state?: string | null;
  error?: string | null;
}

export const AGENT_LABEL: Record<string, { label: string; emoji: string }> = {
  master: { label: "Master Agent", emoji: "🤖" },
  nutri: { label: "ED o Nutri", emoji: "🥗" },
  personal: { label: "ED o Personal", emoji: "💪" },
};

export const INTENT_LABEL: Record<Intent, string> = {
  ED_NUTRI: "Nutri",
  TED_PERSONAL: "Personal",
  MIXED: "Misto (Nutri+Personal)",
  ORCHESTRATOR: "Orquestrador",
  SAFETY_ALERT: "⚠️ Risco",
};
