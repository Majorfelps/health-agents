"use client";
import { useState } from "react";
import NavBar from "@/components/NavBar";
import { useApi, putJson } from "@/lib/api";
import { PlanNutrition, PlanTraining } from "@/lib/types";

export default function PlanPage() {
  const { data: planN, mutate: refreshN } = useApi<PlanNutrition>("/api/v1/plan/nutrition");
  const { data: planT, mutate: refreshT } = useApi<PlanTraining>("/api/v1/plan/training");

  return (
    <>
      <NavBar />
      <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">📋 Planos</h1>
        {planN && <NutritionForm initial={planN} onSaved={() => refreshN()} />}
        {planT && <TrainingForm initial={planT} onSaved={() => refreshT()} />}
      </main>
    </>
  );
}

function NutritionForm({ initial, onSaved }: { initial: PlanNutrition; onSaved: () => void }) {
  const [tdee, setTdee] = useState(initial.tdee);
  const [metaKcal, setMetaKcal] = useState(initial.meta_kcal);
  const [metaP, setMetaP] = useState(initial.meta_p);
  const [metaF, setMetaF] = useState(initial.meta_f);
  const [metaC, setMetaC] = useState(initial.meta_c);
  const [metaAgua, setMetaAgua] = useState(initial.meta_agua_ml);
  const [refeicoesMeta, setRefeicoesMeta] = useState(initial.refeicoes_meta);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await putJson("/api/v1/plan/nutrition", {
        tdee, meta_kcal: metaKcal, meta_p: metaP, meta_f: metaF, meta_c: metaC,
        meta_agua_ml: metaAgua, refeicoes_meta: refeicoesMeta,
      });
      setSaved(true);
      onSaved();
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="bg-white rounded-xl p-5 shadow-sm">
      <h2 className="text-lg font-semibold mb-4">🥗 Plano Nutricional</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
        <NumberField label="TDEE" value={tdee} onChange={setTdee} />
        <NumberField label="Meta kcal" value={metaKcal} onChange={setMetaKcal} />
        <NumberField label="Proteína (g)" value={metaP} onChange={setMetaP} />
        <NumberField label="Gordura (g)" value={metaF} onChange={setMetaF} />
        <NumberField label="Carbo (g)" value={metaC} onChange={setMetaC} />
        <NumberField label="Água (ml)" value={metaAgua} onChange={setMetaAgua} />
      </div>

      <h3 className="text-sm font-semibold text-gray-700 mb-2">Metas por refeição</h3>
      <div className="space-y-2">
        {Object.entries(refeicoesMeta).map(([key, r]) => (
          <div key={key} className="grid grid-cols-5 gap-2 items-center text-sm">
            <span className="font-medium capitalize">{key}</span>
            <NumberFieldSmall label="kcal" value={r.meta_kcal} onChange={(v) => setRefeicoesMeta({ ...refeicoesMeta, [key]: { ...r, meta_kcal: v } })} />
            <NumberFieldSmall label="P" value={r.P} onChange={(v) => setRefeicoesMeta({ ...refeicoesMeta, [key]: { ...r, P: v } })} />
            <NumberFieldSmall label="F" value={r.F} onChange={(v) => setRefeicoesMeta({ ...refeicoesMeta, [key]: { ...r, F: v } })} />
            <NumberFieldSmall label="C" value={r.C} onChange={(v) => setRefeicoesMeta({ ...refeicoesMeta, [key]: { ...r, C: v } })} />
          </div>
        ))}
      </div>

      <button
        onClick={save}
        disabled={saving}
        className="mt-4 bg-wa-green text-white px-5 py-2 rounded-lg font-medium disabled:opacity-50 hover:bg-wa-teal"
      >
        {saving ? "Salvando…" : saved ? "✓ Salvo" : "Salvar"}
      </button>
    </section>
  );
}

function TrainingForm({ initial, onSaved }: { initial: PlanTraining; onSaved: () => void }) {
  const [protocolo, setProtocolo] = useState<Record<string, string>>(initial.protocolo);
  const [ativo, setAtivo] = useState(initial.ativo);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const dias = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"];
  const chaves = [0, 1, 2, 3, 4, 5, 6];

  async function save() {
    setSaving(true);
    try {
      await putJson("/api/v1/plan/training", { protocolo, ativo });
      setSaved(true);
      onSaved();
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="bg-white rounded-xl p-5 shadow-sm">
      <h2 className="text-lg font-semibold mb-4">💪 Plano de Treino Semanal</h2>
      <div className="space-y-2 mb-4">
        {dias.map((d, i) => (
          <div key={d} className="grid grid-cols-3 gap-2 items-center text-sm">
            <span className="font-medium capitalize">{d}</span>
            <input
              className="col-span-2 px-2 py-1 border border-gray-300 rounded"
              value={String(protocolo[chaves[i]] ?? "")}
              onChange={(e) => setProtocolo({ ...protocolo, [chaves[i]]: e.target.value })}
            />
          </div>
        ))}
      </div>
      <label className="flex items-center gap-2 text-sm mb-4">
        <input type="checkbox" checked={ativo} onChange={(e) => setAtivo(e.target.checked)} />
        Plano ativo
      </label>
      <button
        onClick={save}
        disabled={saving}
        className="bg-wa-green text-white px-5 py-2 rounded-lg font-medium disabled:opacity-50 hover:bg-wa-teal"
      >
        {saving ? "Salvando…" : saved ? "✓ Salvo" : "Salvar"}
      </button>
    </section>
  );
}

function NumberField({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <label className="block">
      <span className="text-xs text-gray-500">{label}</span>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="block w-full mt-0.5 px-2 py-1 border border-gray-300 rounded text-sm"
      />
    </label>
  );
}

function NumberFieldSmall({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <label className="block">
      <span className="text-xs text-gray-500">{label}</span>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="block w-full mt-0.5 px-2 py-1 border border-gray-300 rounded text-sm"
      />
    </label>
  );
}
