"use client";
import { useState } from "react";
import NavBar from "@/components/NavBar";
import { useApi, putJson } from "@/lib/api";
import { LLMConfig, LLMModel } from "@/lib/types";

export default function SettingsPage() {
  const { data: cfg, mutate: refreshCfg } = useApi<LLMConfig>("/api/v1/llm/config");
  const [freeOnly, setFreeOnly] = useState(true);
  const { data: modelsData, isLoading: loadingModels } = useApi<{ models: LLMModel[] }>(
    `/api/v1/llm/models?free_only=${freeOnly}`
  );

  return (
    <>
      <NavBar />
      <main className="max-w-3xl mx-auto px-4 py-6 space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">🤖 Configurações de IA</h1>
        {cfg ? (
          <LLMForm
            initial={cfg}
            models={modelsData?.models ?? []}
            loadingModels={loadingModels}
            freeOnly={freeOnly}
            onFreeOnlyChange={setFreeOnly}
            onSaved={() => refreshCfg()}
          />
        ) : (
          <div className="text-gray-500">Carregando…</div>
        )}
      </main>
    </>
  );
}

function LLMForm({
  initial,
  models,
  loadingModels,
  freeOnly,
  onFreeOnlyChange,
  onSaved,
}: {
  initial: LLMConfig;
  models: LLMModel[];
  loadingModels: boolean;
  freeOnly: boolean;
  onFreeOnlyChange: (v: boolean) => void;
  onSaved: () => void;
}) {
  const [enabled, setEnabled] = useState(initial.enabled);
  const [model, setModel] = useState(initial.model);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await putJson("/api/v1/llm/config", { enabled, model });
      setSaved(true);
      onSaved();
      setTimeout(() => setSaved(false), 2000);
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="bg-white rounded-xl p-5 shadow-sm space-y-5">
      <div>
        <label className="flex items-center gap-2 text-sm font-medium">
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          Respostas geradas por LLM (via OpenRouter)
        </label>
        <p className="text-xs text-gray-500 mt-1">
          Desligado: chat 100% determinístico e offline (como sempre foi). Ligado: as respostas do Master/Nutri/Personal
          são geradas pelo modelo escolhido abaixo — mas alertas de saúde (SAFETY_ALERT) e os macros das refeições
          continuam sempre por regra fixa, nunca vêm do LLM.
        </p>
      </div>

      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-sm font-medium text-gray-700">Modelo</span>
          <label className="flex items-center gap-1.5 text-xs text-gray-500">
            <input type="checkbox" checked={freeOnly} onChange={(e) => onFreeOnlyChange(e.target.checked)} />
            só gratuitos
          </label>
        </div>

        <select
          value={models.some((m) => m.id === model) ? model : ""}
          onChange={(e) => setModel(e.target.value)}
          disabled={loadingModels}
          className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm mb-2"
        >
          <option value="" disabled>
            {loadingModels ? "carregando catálogo…" : `selecione (${models.length} modelo${models.length === 1 ? "" : "s"})`}
          </option>
          {models.map((m) => (
            <option key={m.id} value={m.id}>
              {m.id} {m.is_free ? "· grátis" : ""} · {Math.round(m.context_length / 1000)}k ctx
            </option>
          ))}
        </select>

        <input
          type="text"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          placeholder="ou digite o slug manualmente (ex: anthropic/claude-haiku-4.5)"
          className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm font-mono"
        />
        {freeOnly && (
          <p className="text-xs text-gray-400 mt-1">
            Modelos gratuitos têm limite de ~50 requisições/dia por conta OpenRouter (bons pra testar).
          </p>
        )}
      </div>

      {error && <div className="text-sm text-red-600">Erro ao salvar: {error}</div>}

      <button
        onClick={save}
        disabled={saving || (enabled && !model)}
        className="bg-wa-green text-white px-5 py-2 rounded-lg font-medium disabled:opacity-50 hover:bg-wa-teal"
      >
        {saving ? "Salvando…" : saved ? "✓ Salvo — já vale no próximo chat" : "Salvar"}
      </button>
    </section>
  );
}
