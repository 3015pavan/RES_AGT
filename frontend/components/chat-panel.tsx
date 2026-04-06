"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

import { sendChat } from "@/lib/api-client";
import type { ChatMessage } from "@/lib/types";

export function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!query.trim() || loading) {
      return;
    }

    const text = query.trim();
    setQuery("");
    setError(null);

    setMessages((prev) => [
      ...prev,
      { role: "user", content: text, createdAt: new Date().toISOString() },
    ]);

    setLoading(true);
    try {
      const response = await sendChat(text);
      const content = response.response === "NO DATA AVAILABLE"
        ? "No matching data was found in the current dataset."
        : response.response;
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content, createdAt: new Date().toISOString() },
      ]);
    } catch {
      setError("Server error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card flex h-[72vh] flex-col p-4 md:p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-semibold">AI Assistant</h2>
        {error ? <span className="text-sm text-red-600">{error}</span> : null}
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto rounded-xl bg-[#faf9f2] p-3">
        {messages.length === 0 ? (
          <p className="text-sm text-gray-600">Ask about marks, SGPA, ranking, or reports from real ingested data.</p>
        ) : null}

        {messages.map((message, idx) => (
          <div
            key={`${message.createdAt}-${idx}`}
            className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
              message.role === "user"
                ? "ml-auto bg-accent text-white"
                : "mr-auto border border-stroke bg-white text-ink"
            }`}
          >
            {message.content}
          </div>
        ))}

        {loading ? <div className="text-sm text-gray-600">Thinking...</div> : null}
        <div ref={scrollRef} />
      </div>

      <form onSubmit={onSubmit} className="mt-3 flex items-end gap-2">
        <textarea
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Ask anything grounded in your uploaded and email-ingested data"
          rows={2}
          className="input min-h-[52px] resize-none"
        />
        <button className="btn-primary h-[52px]" type="submit" disabled={loading}>
          Send
        </button>
      </form>
    </section>
  );
}
