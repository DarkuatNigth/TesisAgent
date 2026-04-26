"use client";
import { useEffect, useRef, useState } from "react";
import { X, Send, Bot, User } from "lucide-react";
import type { ChatMessage } from "@/types";

const API_KEY  = process.env.NEXT_PUBLIC_GEMINI_KEY ?? "";
const MODEL    = "gemini-2.0-flash";
const GREETING = "Hola, soy el asistente académico de InnoTech. Puedo ayudarte a interpretar los resultados de rendimiento estudiantil, explicar los planes de recuperación generados o responder dudas sobre el sistema. ¿En qué te puedo ayudar?";

export default function AgentChat({ onClose }: { onClose: () => void }) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "assistant", content: GREETING },
  ]);
  const [input, setInput]     = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef             = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function enviar() {
    if (!input.trim() || loading) return;
    const userMsg: ChatMessage = { role: "user", content: input.trim() };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);

    // Placeholder de la respuesta mientras hace streaming
    setMessages((m) => [...m, { role: "assistant", content: "" }]);

    try {
      const history = [...messages, userMsg].map((m) => ({
        role: m.role === "assistant" ? "model" : "user",
        parts: [{ text: m.content }],
      }));

      const res = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:streamGenerateContent?alt=sse&key=${API_KEY}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            system_instruction: {
              parts: [{ text: "Eres un asistente educativo del sistema InnoTech de la Universidad Bolivariana del Ecuador. Ayudas a interpretar análisis de rendimiento estudiantil generados por IA Gemini. Responde siempre en español, de forma clara y concisa." }],
            },
            contents: history,
          }),
        }
      );

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const json = line.slice(6).trim();
          if (!json || json === "[DONE]") continue;
          try {
            const chunk = JSON.parse(json);
            const text: string =
              chunk?.candidates?.[0]?.content?.parts?.[0]?.text ?? "";
            if (text) {
              setMessages((m) => {
                const updated = [...m];
                updated[updated.length - 1] = {
                  role: "assistant",
                  content: updated[updated.length - 1].content + text,
                };
                return updated;
              });
            }
          } catch {}
        }
      }
    } catch (e) {
      setMessages((m) => {
        const updated = [...m];
        updated[updated.length - 1] = {
          role: "assistant",
          content: "Ocurrió un error al conectar con el agente. Verifica tu conexión.",
        };
        return updated;
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-end p-4 sm:p-6"
         style={{ background: "rgba(0,0,0,0.35)" }}
         onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="flex w-full max-w-md flex-col rounded-2xl bg-white shadow-2xl"
           style={{ height: "520px" }}>
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600">
              <Bot size={16} className="text-white" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">Agente Académico</p>
              <p className="text-xs text-gray-400">InnoTech · Gemini</p>
            </div>
          </div>
          <button onClick={onClose}
                  className="rounded-full p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>

        {/* Mensajes */}
        <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-2 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
              <div className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-white
                ${msg.role === "assistant" ? "bg-indigo-600" : "bg-gray-700"}`}>
                {msg.role === "assistant" ? <Bot size={13} /> : <User size={13} />}
              </div>
              <div className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm leading-relaxed
                ${msg.role === "assistant"
                  ? "bg-gray-100 text-gray-800"
                  : "bg-indigo-600 text-white"}`}>
                {msg.content || (
                  <span className="flex gap-1">
                    <span className="animate-bounce">·</span>
                    <span className="animate-bounce" style={{ animationDelay: "0.15s" }}>·</span>
                    <span className="animate-bounce" style={{ animationDelay: "0.3s" }}>·</span>
                  </span>
                )}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-100 px-3 py-3">
          <div className="flex items-center gap-2 rounded-xl border border-gray-200 bg-gray-50 px-3 py-2">
            <input
              className="flex-1 bg-transparent text-sm text-gray-800 outline-none placeholder:text-gray-400"
              placeholder="Escribe tu pregunta…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && enviar()}
              disabled={loading}
            />
            <button
              onClick={enviar}
              disabled={loading || !input.trim()}
              className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-600
                         text-white transition hover:bg-indigo-700 disabled:opacity-40"
            >
              <Send size={13} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}