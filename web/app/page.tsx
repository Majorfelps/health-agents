"use client";
import NavBar from "@/components/NavBar";
import { useApi } from "@/lib/api";
import { DashboardOut, AGENT_LABEL } from "@/lib/types";
import { useState } from "react";
import clsx from "clsx";

function ProgressBar({ value, max, label, color }: { value: number; max: number; label: string; color: string }) {
  const pct = Math.min(100, Math.round((value / Math.max(1, max)) * 100));
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-600 mb-1">
        <span>{label}</span>
        <span>{value} / {max} ({pct}%)</span>
      </div>
      <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={clsx("h-full", color)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function MacroCard({ icon, label, value, unit, meta }: { icon: string; label: string; value: number; unit: string; meta: number }) {
  return (
    <div className="bg-white rounded-xl p-4 shadow-sm">
      <div className="text-2xl mb-1">{icon}</div>
      <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
      <div className="text-2xl font-bold text-gray-900">{Math.round(value)} <span className="text-sm font-normal text-gray-500">{unit}</span></div>
      <div className="text-xs text-gray-400 mt-1">meta: {meta} {unit}</div>
    </div>
  );
}

export default function Home() {
  const { data, error, isLoading } = useApi<DashboardOut>("/api/v1/dashboard", 30_000);
  const [unit, setUnit] = useState<"L" | "ml">("L");

  if (isLoading) return <Shell><div className="p-8 text-gray-500">Carregando…</div></Shell>;
  if (error) return <Shell><div className="p-8 text-red-600">Erro: {String(error)} — backend está rodando?</div></Shell>;
  if (!data) return <Shell><div className="p-8">Sem dados</div></Shell>;

  const plan = data.plan_nutrition;
  const today = data.today;
  const workout = data.workout_today;

  return (
    <Shell>
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Olá, {data.user.name || "atleta"} 👋</h1>
        <p className="text-sm text-gray-500">
          {new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long" })} — objetivo: {data.user.goal || "recomp"}
        </p>
      </header>

      <section className="mb-6">
        <h2 className="text-lg font-semibold mb-3">📊 Hoje</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <MacroCard icon="🔥" label="Kcal" value={today.kcal} unit="kcal" meta={plan?.meta_kcal || 1770} />
          <MacroCard icon="🥩" label="Proteína" value={today.P} unit="g" meta={plan?.meta_p || 186} />
          <MacroCard icon="🍞" label="Carbo" value={today.C} unit="g" meta={plan?.meta_c || 165} />
          <MacroCard icon="🥑" label="Gordura" value={today.F} unit="g" meta={plan?.meta_f || 70} />
          <MacroCard
            icon="💧"
            label="Água"
            value={unit === "L" ? today.agua_ml / 1000 : today.agua_ml}
            unit={unit}
            meta={unit === "L" ? (plan?.meta_agua_ml || 2500) / 1000 : (plan?.meta_agua_ml || 2500)}
          />
        </div>
        <button
          className="text-xs text-gray-400 mt-1 hover:text-gray-600"
          onClick={() => setUnit((u) => (u === "L" ? "ml" : "L"))}
        >
          trocar unidade ({unit})
        </button>
      </section>

      {plan && (
        <section className="mb-6">
          <h2 className="text-lg font-semibold mb-3">🎯 Meta diária</h2>
          <div className="bg-white rounded-xl p-4 shadow-sm space-y-3">
            <ProgressBar value={today.kcal} max={plan.meta_kcal} label="Calorias" color="bg-orange-500" />
            <ProgressBar value={today.P} max={plan.meta_p} label="Proteína" color="bg-red-500" />
            <ProgressBar value={today.C} max={plan.meta_c} label="Carboidrato" color="bg-yellow-500" />
            <ProgressBar value={today.F} max={plan.meta_f} label="Gordura" color="bg-green-500" />
            <ProgressBar value={today.agua_ml} max={plan.meta_agua_ml} label="Água" color="bg-blue-500" />
          </div>
        </section>
      )}

      <section className="mb-6">
        <h2 className="text-lg font-semibold mb-3">💪 Treino de hoje — {workout.weekday_pt}</h2>
        <div className="bg-white rounded-xl p-4 shadow-sm">
          <div className="font-semibold text-lg text-wa-green-dark mb-1">{workout.nome}</div>
          <div className="text-sm text-gray-500 mb-3">foco: {workout.foco} {workout.series && `· ${workout.series} séries`}</div>
          <ol className="space-y-1.5">
            {workout.exercicios.map(([ex, reps, rpe, desc], i) => (
              <li key={i} className="flex items-baseline gap-2 text-sm">
                <span className="text-gray-400 w-5 text-right">{i + 1}.</span>
                <span className="font-medium flex-1">{ex}</span>
                <span className="text-gray-600">{reps}</span>
                <span className="text-gray-500 text-xs">@ {rpe}</span>
                <span className="text-gray-400 text-xs">desc {desc}</span>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="mb-6">
        <h2 className="text-lg font-semibold mb-3">📅 Últimos 7 dias (kcal)</h2>
        <div className="bg-white rounded-xl p-4 shadow-sm">
          <div className="flex items-end gap-2 h-32">
            {Object.entries(data.last_7_days).map(([d, t]) => {
              const pct = Math.min(100, Math.round((t.kcal / (plan?.meta_kcal || 1770)) * 100));
              return (
                <div key={d} className="flex-1 flex flex-col items-center gap-1">
                  <div className="text-xs text-gray-600 font-medium">{Math.round(t.kcal)}</div>
                  <div className="w-full bg-orange-100 rounded-t" style={{ height: `${pct}%` }}>
                    <div className="w-full bg-orange-500 rounded-t" style={{ height: pct > 0 ? "100%" : "0" }} />
                  </div>
                  <div className="text-[10px] text-gray-400">{d.slice(5)}</div>
                </div>
              );
            })}
          </div>
        </div>
      </section>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <>
      <NavBar />
      <main className="max-w-6xl mx-auto px-4 py-6">{children}</main>
    </>
  );
}
