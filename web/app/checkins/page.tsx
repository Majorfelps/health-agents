"use client";
import { useState } from "react";
import NavBar from "@/components/NavBar";
import { useApi, postJson } from "@/lib/api";
import { CheckinOut, DashboardOut } from "@/lib/types";

export default function CheckinsPage() {
  const { data, mutate: refresh } = useApi<DashboardOut>("/api/v1/dashboard", 30_000);

  return (
    <>
      <NavBar />
      <main className="max-w-3xl mx-auto px-4 py-6 space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">✅ Check-ins</h1>
        <CheckinForm onCreated={() => refresh()} />
        {data?.last_checkin && (
          <section className="bg-white rounded-xl p-5 shadow-sm">
            <h2 className="text-lg font-semibold mb-2">Último check-in</h2>
            <div className="text-sm space-y-1">
              <div>📅 {new Date(data.last_checkin.created_at).toLocaleString("pt-BR")}</div>
              {data.last_checkin.mood && <div>😊 Humor: {data.last_checkin.mood}</div>}
              {data.last_checkin.hunger_level != null && <div>🍽 Fome: {data.last_checkin.hunger_level}/10</div>}
              {data.last_checkin.sleep_hours != null && <div>😴 Sono: {data.last_checkin.sleep_hours}h</div>}
              {data.last_checkin.water_liters != null && <div>💧 Água: {data.last_checkin.water_liters}L</div>}
              {data.last_checkin.notes && <div className="pt-2 italic text-gray-600">&quot;{data.last_checkin.notes}&quot;</div>}
            </div>
          </section>
        )}
      </main>
    </>
  );
}

function CheckinForm({ onCreated }: { onCreated: () => void }) {
  const [mood, setMood] = useState("");
  const [hunger, setHunger] = useState(5);
  const [sleep, setSleep] = useState<number | "">("");
  const [water, setWater] = useState<number | "">("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await postJson("/api/v1/checkins", {
        type: "manual",
        mood: mood || null,
        hunger_level: hunger,
        sleep_hours: sleep === "" ? null : sleep,
        water_liters: water === "" ? null : water,
        notes: notes || null,
      });
      setMood(""); setHunger(5); setSleep(""); setWater(""); setNotes("");
      setSaved(true);
      onCreated();
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="bg-white rounded-xl p-5 shadow-sm">
      <h2 className="text-lg font-semibold mb-3">Novo check-in</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <label className="block">
          <span className="text-xs text-gray-500">Humor</span>
          <select value={mood} onChange={(e) => setMood(e.target.value)} className="block w-full mt-0.5 px-2 py-1.5 border border-gray-300 rounded text-sm">
            <option value="">—</option>
            <option value="feliz">😄 feliz</option>
            <option value="ok">🙂 ok</option>
            <option value="neutro">😐 neutro</option>
            <option value="cansado">😴 cansado</option>
            <option value="estressado">😤 estressado</option>
            <option value="triste">😞 triste</option>
          </select>
        </label>
        <label className="block">
          <span className="text-xs text-gray-500">Fome (1-10): <strong>{hunger}</strong></span>
          <input type="range" min={1} max={10} value={hunger} onChange={(e) => setHunger(Number(e.target.value))} className="w-full" />
        </label>
        <label className="block">
          <span className="text-xs text-gray-500">Sono (horas)</span>
          <input type="number" step="0.5" min={0} max={24} value={sleep} onChange={(e) => setSleep(e.target.value === "" ? "" : Number(e.target.value))} className="block w-full mt-0.5 px-2 py-1.5 border border-gray-300 rounded text-sm" />
        </label>
        <label className="block">
          <span className="text-xs text-gray-500">Água hoje (L)</span>
          <input type="number" step="0.25" min={0} max={10} value={water} onChange={(e) => setWater(e.target.value === "" ? "" : Number(e.target.value))} className="block w-full mt-0.5 px-2 py-1.5 border border-gray-300 rounded text-sm" />
        </label>
      </div>
      <label className="block mt-3">
        <span className="text-xs text-gray-500">Notas</span>
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} className="block w-full mt-0.5 px-2 py-1.5 border border-gray-300 rounded text-sm" />
      </label>
      <button
        onClick={save}
        disabled={saving}
        className="mt-4 bg-wa-green text-white px-5 py-2 rounded-lg font-medium disabled:opacity-50 hover:bg-wa-teal"
      >
        {saving ? "Salvando…" : saved ? "✓ Salvo" : "Registrar check-in"}
      </button>
    </section>
  );
}
