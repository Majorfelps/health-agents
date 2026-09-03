"use client";
import { useState } from "react";
import NavBar from "@/components/NavBar";
import { useApi, putJson, postJson } from "@/lib/api";
import { LLMConfig, LLMModel, LLMTestResult, WhatsAppConfig, WhatsAppTestResult } from "@/lib/types";

export default function SettingsPage() {
  const { data: cfg, mutate: refreshCfg } = useApi<LLMConfig>("/api/v1/llm/config");
  const [freeOnly, setFreeOnly] = useState(true);
  const { data: modelsData, isLoading: loadingModels } = useApi<{ models: LLMModel[] }>(
    `/api/v1/llm/models?free_only=${freeOnly}`
  );
  const { data: waCfg, mutate: refreshWaCfg } = useApi<WhatsAppConfig>("/api/v1/whatsapp/config");

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

        <h2 className="text-xl font-bold text-gray-900 pt-2">📱 Espelhar no WhatsApp</h2>
        {waCfg ? (
          <WhatsAppForm initial={waCfg} onSaved={() => refreshWaCfg()} />
        ) : (
          <div className="text-gray-500">Carregando…</div>
        )}
      </main>
    </>
  );
}

function WhatsAppForm({ initial, onSaved }: { initial: WhatsAppConfig; onSaved: () => void }) {
  const [enabled, setEnabled] = useState(initial.enabled);
  const [targetNumber, setTargetNumber] = useState(initial.target_number);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<WhatsAppTestResult | null>(null);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await putJson("/api/v1/whatsapp/config", { enabled, target_number: targetNumber });
      setSaved(true);
      onSaved();
      setTimeout(() => setSaved(false), 2000);
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally {
      setSaving(false);
    }
  }

  async function testConnection() {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await postJson<WhatsAppTestResult>("/api/v1/whatsapp/test", {});
      setTestResult(r);
    } catch (e: any) {
      setTestResult({ ok: false, error: String(e?.message || e) });
    } finally {
      setTesting(false);
    }
  }

  return (
    <section className="bg-white rounded-xl p-5 shadow-sm space-y-5">
      <div>
        <label className="flex items-center gap-2 text-sm font-medium">
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          Enviar respostas do chat também pro WhatsApp
        </label>
        <p className="text-xs text-gray-500 mt-1">
          Via Evolution API (número/instância configurados no servidor via .env). Desligado por padrão — o chat web
          continua funcionando normalmente sem isso. Só a resposta do agente é enviada, não a sua mensagem (você já a
          digitou aqui).
        </p>
      </div>

      <div>
        <span className="text-sm font-medium text-gray-700">Número de destino</span>
        <div className="flex gap-2 mt-1.5">
          <input
            type="text"
            value={targetNumber}
            onChange={(e) => {
              setTargetNumber(e.target.value);
              setTestResult(null);
            }}
            placeholder="ex: 553199674109 (DDI+DDD+número, sem @s.whatsapp.net)"
            className="flex-1 px-2 py-1.5 border border-gray-300 rounded text-sm font-mono"
          />
          <button
            type="button"
            onClick={testConnection}
            disabled={testing}
            className="px-3 py-1.5 rounded text-sm font-medium border border-gray-300 hover:bg-gray-50 disabled:opacity-50 whitespace-nowrap"
          >
            {testing ? "Testando…" : "Testar conexão"}
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-1">
          &quot;Testar conexão&quot; só confirma se a instância da Evolution API está acessível/conectada — não envia
          mensagem nenhuma.
        </p>

        {testResult && (
          <p className={"text-xs mt-1.5 " + (testResult.ok ? "text-green-700" : "text-red-600")}>
            {testResult.ok
              ? `✓ Instância conectada (state: ${testResult.state})`
              : `✗ ${testResult.error}`}
          </p>
        )}
      </div>

      {error && <div className="text-sm text-red-600">Erro ao salvar: {error}</div>}

      <button
        onClick={save}
        disabled={saving || (enabled && !targetNumber)}
        className="bg-wa-green text-white px-5 py-2 rounded-lg font-medium disabled:opacity-50 hover:bg-wa-teal"
      >
        {saving ? "Salvando…" : saved ? "✓ Salvo — já vale no próximo chat" : "Salvar"}
      </button>
    </section>
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
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<LLMTestResult | null>(null);

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

  async function testModel() {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await postJson<LLMTestResult>("/api/v1/llm/test", { model });
      setTestResult(r);
    } catch (e: any) {
      setTestResult({ ok: false, error: String(e?.message || e) });
    } finally {
      setTesting(false);
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
          onChange={(e) => {
            setModel(e.target.value);
            setTestResult(null);
          }}
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

        <div className="flex gap-2">
          <input
            type="text"
            value={model}
            onChange={(e) => {
              setModel(e.target.value);
              setTestResult(null);
            }}
            placeholder="ou digite o slug manualmente (ex: anthropic/claude-haiku-4.5)"
            className="flex-1 px-2 py-1.5 border border-gray-300 rounded text-sm font-mono"
          />
          <button
            type="button"
            onClick={testModel}
            disabled={testing || !model}
            className="px-3 py-1.5 rounded text-sm font-medium border border-gray-300 hover:bg-gray-50 disabled:opacity-50 whitespace-nowrap"
          >
            {testing ? "Testando…" : "Testar modelo"}
          </button>
        </div>

        {testResult && (
          <p className={"text-xs mt-1.5 " + (testResult.ok ? "text-green-700" : "text-red-600")}>
            {testResult.ok
              ? `✓ Funcionou — resposta de teste: "${testResult.sample}"`
              : `✗ ${testResult.error}`}
          </p>
        )}

        {freeOnly && (
          <p className="text-xs text-gray-400 mt-1">
            Modelos gratuitos têm limite de ~50 requisições/dia por conta OpenRouter, e alguns são restritos a
            agentic harnesses (recusam chat comum) — use &quot;Testar modelo&quot; antes de salvar.
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
