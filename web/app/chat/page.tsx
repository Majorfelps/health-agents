"use client";
import { useEffect, useRef, useState } from "react";
import NavBar from "@/components/NavBar";
import { ChatResponse, ChatMessage, AGENT_LABEL, INTENT_LABEL } from "@/lib/types";
import { postJson, API_BASE } from "@/lib/api";
import clsx from "clsx";

const SUGESTOES = [
  "oi",
  "qual o treino de hoje?",
  "comi 100g de arroz com feijão e 150g de frango",
  "bebi 500ml de água",
  "to fazendo dieta e vou treinar",
  "tô com dor no peito",
  "bora malhar",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [lastMeta, setLastMeta] = useState<ChatResponse | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Carrega histórico
  useEffect(() => {
    fetch(`${API_BASE}/api/v1/chat/history?limit=50`)
      .then((r) => r.json())
      .then((msgs) => setMessages(msgs || []))
      .catch(() => setMessages([]));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function send(text?: string) {
    const content = (text ?? input).trim();
    if (!content || busy) return;
    setInput("");

    // otimista: mostra a msg do user imediatamente
    const tempUser: ChatMessage = {
      agent: "user",
      direction: "inbound",
      message: content,
      created_at: new Date().toISOString(),
    };
    setMessages((m) => [...m, tempUser]);
    setBusy(true);

    try {
      const r = await postJson<ChatResponse>("/api/v1/chat", { message: content, persist: true });
      setLastMeta(r);
      const replyMsg: ChatMessage = {
        id: r.message_id ?? undefined,
        agent: r.agent,
        direction: "outbound",
        message: r.reply,
        intent: r.intent,
        images: r.images,
        created_at: new Date().toISOString(),
      };
      setMessages((m) => [...m, replyMsg]);
    } catch (e: any) {
      setMessages((m) => [
        ...m,
        { agent: "system", direction: "outbound", message: "Erro: " + String(e?.message || e), created_at: new Date().toISOString() },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <NavBar />
      <main className="max-w-3xl mx-auto h-[calc(100vh-58px)] flex flex-col">
        <header className="px-4 py-3 bg-wa-green-dark text-white flex items-center gap-2">
          <span className="text-2xl">🤖</span>
          <div>
            <div className="font-semibold">Master Agent</div>
            <div className="text-xs opacity-80">roteia para ED o Nutri 🥗 ou ED o Personal 💪</div>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto bg-wa-bg p-4 flex flex-col gap-2">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 my-8">
              <div className="text-3xl mb-2">👋</div>
              <div className="text-sm">Comece dizendo &quot;oi&quot; ou clique em uma sugestão abaixo.</div>
            </div>
          )}
          {messages.map((m, i) => {
            const isUser = m.agent === "user";
            const agent = AGENT_LABEL[m.agent] || { label: m.agent, emoji: "•" };
            return (
              <div key={i} className={clsx("bubble flex flex-col", isUser ? "bubble-out" : "bubble-in")}>
                {!isUser && <div className="agent-tag">{agent.emoji} {agent.label}</div>}
                <div>{m.message}</div>
                {m.images && m.images.length > 0 && (
                  <div className="mt-2 flex flex-col gap-2">
                    {m.images.map((img, j) => (
                      <div key={j}>
                        <img
                          src={img.url}
                          alt={`Demonstração: ${img.exercise}`}
                          className="rounded-lg max-w-full max-h-64 object-contain border border-gray-200"
                          loading="lazy"
                        />
                        <div className="text-xs text-gray-500 mt-0.5">{img.exercise}</div>
                      </div>
                    ))}
                  </div>
                )}
                {!isUser && m.intent && (
                  <div className="intent-tag">
                    intent: {m.intent}
                    {m.created_at && ` · ${new Date(m.created_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`}
                  </div>
                )}
              </div>
            );
          })}
          {busy && (
            <div className="bubble bubble-in self-start">
              <div className="agent-tag">…</div>
              <div className="flex gap-1">
                <span className="animate-bounce">•</span>
                <span className="animate-bounce" style={{ animationDelay: "100ms" }}>•</span>
                <span className="animate-bounce" style={{ animationDelay: "200ms" }}>•</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {lastMeta?.detected_meal && (
          <div className="px-4 py-2 bg-green-50 border-t border-green-200 text-sm text-green-900">
            <strong>🍽 Refeição detectada:</strong> {lastMeta.detected_meal.descricao} — {lastMeta.detected_meal.kcal} kcal | P {lastMeta.detected_meal.P}g | F {lastMeta.detected_meal.F}g | C {lastMeta.detected_meal.C}g
          </div>
        )}

        <div className="px-3 py-2 bg-gray-100 border-t border-gray-200 flex gap-1.5 flex-wrap">
          {SUGESTOES.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              disabled={busy}
              className="text-xs px-2 py-1 rounded-full bg-white border border-gray-300 hover:bg-gray-50 disabled:opacity-50"
            >
              {s}
            </button>
          ))}
        </div>

        <form
          className="flex gap-2 p-3 bg-gray-50 border-t border-gray-200"
          onSubmit={(e) => { e.preventDefault(); send(); }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Digite uma mensagem…"
            className="flex-1 rounded-full px-4 py-2 border border-gray-300 focus:outline-none focus:border-wa-green"
            disabled={busy}
            autoFocus
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            className="bg-wa-green text-white px-5 py-2 rounded-full font-medium disabled:opacity-50 hover:bg-wa-teal"
          >
            Enviar
          </button>
        </form>
      </main>
    </>
  );
}
