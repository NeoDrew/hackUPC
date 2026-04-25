"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8001";

type ChatRole = "user" | "assistant";

interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  result?: unknown;
}

interface ChatMessage {
  role: ChatRole;
  content: string;
  toolCalls: ToolCall[];
  pending?: boolean;
}

const SUGGESTIONS = [
  "What are the worst-fatiguing creatives this week?",
  "Why is creative 500001 losing?",
  "What's working in our gaming portfolio?",
];

export function ChatLauncher() {
  const pathname = usePathname();
  const search = useSearchParams();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Hide on phone-immersive routes.
  if (pathname.startsWith("/m")) return null;

  // Build a tiny context payload so the agent knows what page the user is on.
  const context = buildContext(pathname, search);

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || streaming) return;
      setError(null);
      const userMsg: ChatMessage = {
        role: "user",
        content: trimmed,
        toolCalls: [],
      };
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: "",
        toolCalls: [],
        pending: true,
      };
      const nextMessages = [...messages, userMsg, assistantMsg];
      setMessages(nextMessages);
      setDraft("");
      setStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const res = await fetch(`${BASE}/api/agent/chat`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            messages: nextMessages
              .filter((m) => m !== assistantMsg) // exclude the still-empty placeholder
              .map((m) => ({ role: m.role, content: m.content })),
            context,
          }),
          signal: controller.signal,
        });
        if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let running = true;
        while (running) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const segments = buffer.split("\n\n");
          buffer = segments.pop() ?? "";
          for (const seg of segments) {
            const event = parseSseEvent(seg);
            if (!event) continue;
            applyEvent(event, setMessages, () => {
              running = false;
            });
            scheduleScroll(scrollerRef);
          }
        }
      } catch (e: unknown) {
        if ((e as { name?: string }).name === "AbortError") return;
        setError(String(e));
        setMessages((prev) =>
          prev.map((m) =>
            m === assistantMsg ? { ...m, pending: false, content: m.content || "(failed)" } : m,
          ),
        );
      } finally {
        setStreaming(false);
        abortRef.current = null;
        setMessages((prev) =>
          prev.map((m) => (m.pending ? { ...m, pending: false } : m)),
        );
        scheduleScroll(scrollerRef);
      }
    },
    [messages, streaming, context],
  );

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  if (!open) {
    return (
      <button
        type="button"
        className="chat-launcher"
        aria-label="Ask Smadex Copilot"
        onClick={() => setOpen(true)}
      >
        <span className="chat-launcher-glyph">✦</span>
        <span className="chat-launcher-label">Ask Copilot</span>
      </button>
    );
  }

  return (
    <section className="chat-panel" role="dialog" aria-label="Smadex Copilot chat">
      <header className="chat-panel-head">
        <span className="chat-panel-title">
          <span className="chat-launcher-glyph small">✦</span>
          Smadex Copilot
          <span className="chat-panel-sub">Gemini 2.5 Flash · grounded on portfolio data</span>
        </span>
        <button
          type="button"
          className="chat-panel-close"
          aria-label="Close chat"
          onClick={() => setOpen(false)}
        >
          ×
        </button>
      </header>
      <div className="chat-panel-body" ref={scrollerRef}>
        {messages.length === 0 ? (
          <div className="chat-empty">
            <p className="t-micro muted">Ask anything about the portfolio. Try:</p>
            <div className="chat-suggestions">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  className="chat-suggestion"
                  onClick={() => send(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m, i) => <ChatMessageRow key={i} message={m} />)
        )}
        {error ? <p className="chat-error">{error}</p> : null}
      </div>
      <form
        className="chat-panel-input"
        onSubmit={(e) => {
          e.preventDefault();
          send(draft);
        }}
      >
        <input
          type="text"
          placeholder="Ask about creatives, cohorts, fatigue…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={streaming}
          autoFocus
        />
        <button
          type="submit"
          className="chat-send"
          disabled={streaming || !draft.trim()}
        >
          {streaming ? "…" : "Send"}
        </button>
      </form>
    </section>
  );
}

function ChatMessageRow({ message }: { message: ChatMessage }) {
  return (
    <div className={`chat-msg chat-msg-${message.role}`}>
      {message.toolCalls.length > 0 ? (
        <div className="chat-tools">
          {message.toolCalls.map((t, i) => (
            <span key={i} className="chat-tool">
              <span className="chat-tool-name">{t.name}</span>
              <span className="chat-tool-args">
                {Object.entries(t.args)
                  .map(([k, v]) => `${k}=${formatToolArg(v)}`)
                  .join(" · ")}
              </span>
            </span>
          ))}
        </div>
      ) : null}
      <p>{message.content || (message.pending ? "Thinking…" : "")}</p>
    </div>
  );
}

function formatToolArg(v: unknown): string {
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return JSON.stringify(v);
}

function parseSseEvent(raw: string): { event: string; data: unknown } | null {
  let event = "message";
  let dataRaw = "";
  for (const line of raw.split("\n")) {
    if (line.startsWith("event: ")) event = line.slice(7).trim();
    else if (line.startsWith("data: ")) dataRaw = line.slice(6);
  }
  if (!dataRaw) return null;
  try {
    return { event, data: JSON.parse(dataRaw) };
  } catch {
    return null;
  }
}

function applyEvent(
  event: { event: string; data: unknown },
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
  finish: () => void,
) {
  setMessages((prev) => {
    const next = [...prev];
    const last = next[next.length - 1];
    if (!last || last.role !== "assistant") return prev;
    const updated: ChatMessage = { ...last };
    switch (event.event) {
      case "tool_call": {
        const data = event.data as { name: string; args: Record<string, unknown> };
        updated.toolCalls = [...updated.toolCalls, { name: data.name, args: data.args }];
        break;
      }
      case "tool_result": {
        const data = event.data as { name: string; result: unknown };
        updated.toolCalls = updated.toolCalls.map((tc, i, arr) =>
          i === arr.length - 1 && tc.name === data.name && tc.result === undefined
            ? { ...tc, result: data.result }
            : tc,
        );
        break;
      }
      case "delta": {
        const data = event.data as { text: string };
        updated.content = (updated.content || "") + (data.text ?? "");
        break;
      }
      case "error": {
        const data = event.data as { message: string };
        updated.content = data.message;
        finish();
        break;
      }
      case "done": {
        updated.pending = false;
        finish();
        break;
      }
    }
    next[next.length - 1] = updated;
    return next;
  });
}

function scheduleScroll(ref: React.MutableRefObject<HTMLDivElement | null>) {
  requestAnimationFrame(() => {
    const el = ref.current;
    if (el) el.scrollTop = el.scrollHeight;
  });
}

function buildContext(
  pathname: string,
  search: ReturnType<typeof useSearchParams>,
): Record<string, unknown> {
  const ctx: Record<string, unknown> = { pathname };
  const tab = search.get("tab");
  if (tab) ctx.tab = tab;
  const creativeMatch = pathname.match(/\/creatives\/(\d+)/);
  if (creativeMatch) ctx.creative_id = Number(creativeMatch[1]);
  const advertiserMatch = pathname.match(/\/advertisers\/(\d+)/);
  if (advertiserMatch) ctx.advertiser_id = Number(advertiserMatch[1]);
  return ctx;
}
