"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ChevronDown,
  Loader2,
  Maximize2,
  Mic,
  Minimize2,
  PanelRight,
  Square,
  X,
} from "lucide-react";

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

const TAB_LABEL: Record<string, string> = {
  scale: "scale",
  watch: "watch",
  rescue: "rescue",
  cut: "cut",
};

function buildSuggestions(context: Record<string, unknown>): string[] {
  const creativeId = context.creative_id as number | undefined;
  const advertiserId = context.advertiser_id as number | undefined;
  const tab = context.tab as string | undefined;
  const pathname = (context.pathname as string | undefined) ?? "";

  if (creativeId && pathname.endsWith("/twin")) {
    return [
      `Why is creative ${creativeId} losing to its twin?`,
      `Which attributes should I copy from the winner?`,
      `What's the predicted lift if I ship the variant?`,
    ];
  }
  if (creativeId) {
    return [
      `Why is this creative losing?`,
      `Find me a twin for ${creativeId}`,
      `What attributes are dragging it down?`,
    ];
  }
  if (advertiserId) {
    return [
      `Which of this advertiser's creatives are winning?`,
      `Where is fatigue concentrated in their portfolio?`,
      `What should they test next?`,
    ];
  }
  if (tab && TAB_LABEL[tab]) {
    return [
      `What's driving the ${TAB_LABEL[tab]} list?`,
      `Top 3 creatives in ${TAB_LABEL[tab]} right now`,
      `What attributes do these share?`,
    ];
  }
  return [
    "What are the worst-fatiguing creatives this week?",
    "What's working in our gaming portfolio?",
    "Top performers I should scale today",
  ];
}

type PanelState = "idle" | "open" | "closing";

const CLOSE_ANIMATION_MS = 220;

export function ChatLauncher() {
  const pathname = usePathname();
  const search = useSearchParams();
  const [panelState, setPanelState] = useState<PanelState>("idle");
  const [expanded, setExpanded] = useState(false);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dictation = useDictation((finalText) => {
    setDraft((prev) => (prev ? `${prev.trimEnd()} ${finalText}` : finalText));
  });

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
    return () => {
      abortRef.current?.abort();
      if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
    };
  }, []);

  const beginClose = useCallback(() => {
    if (panelState !== "open") return;
    setPanelState("closing");
    if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
    closeTimerRef.current = setTimeout(() => {
      setPanelState("idle");
      setExpanded(false);
    }, CLOSE_ANIMATION_MS);
  }, [panelState]);

  const beginOpen = useCallback(() => {
    if (closeTimerRef.current) {
      clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
    setPanelState("open");
  }, []);

  if (panelState === "idle") {
    return (
      <button
        type="button"
        className="chat-launcher"
        aria-label="Open assistant"
        onClick={beginOpen}
      >
        <PanelRight size={14} strokeWidth={1.75} aria-hidden />
        <span className="chat-launcher-label">Open assistant</span>
      </button>
    );
  }

  return (
    <section
      className="chat-panel"
      role="dialog"
      aria-label="Assistant"
      data-state={panelState}
      data-expanded={expanded ? "true" : undefined}
    >
      <header className="chat-panel-head">
        <span className="chat-panel-title">
          Assistant
          <span className="chat-panel-sub">Gemini 2.5 Flash · grounded on portfolio data</span>
        </span>
        <div className="chat-panel-actions">
          <button
            type="button"
            className="chat-panel-icon"
            aria-label={expanded ? "Collapse" : "Expand"}
            title={expanded ? "Collapse" : "Expand"}
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? <Minimize2 size={14} strokeWidth={1.75} aria-hidden /> : <Maximize2 size={14} strokeWidth={1.75} aria-hidden />}
          </button>
          <button
            type="button"
            className="chat-panel-icon chat-panel-close"
            aria-label="Close"
            onClick={beginClose}
          >
            <X size={16} strokeWidth={1.75} aria-hidden />
          </button>
        </div>
      </header>
      <div className="chat-panel-body" ref={scrollerRef}>
        {messages.length === 0 ? (
          <div className="chat-empty">
            <p className="t-micro muted">Ask anything about the portfolio. Try:</p>
            <div className="chat-suggestions">
              {buildSuggestions(context).map((s) => (
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
          placeholder={dictation.listening ? "Listening…" : "Ask about creatives, cohorts, fatigue…"}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={streaming}
          autoFocus
        />
        {dictation.supported ? (
          <button
            type="button"
            className="chat-mic"
            data-active={dictation.listening ? "true" : undefined}
            aria-label={dictation.listening ? "Stop dictation" : "Start dictation"}
            title={dictation.listening ? "Stop dictation" : "Speak"}
            onClick={() => (dictation.listening ? dictation.stop() : dictation.start())}
            disabled={streaming}
          >
            {dictation.listening ? (
              <Square size={12} strokeWidth={2} fill="currentColor" aria-hidden />
            ) : (
              <Mic size={14} strokeWidth={1.75} aria-hidden />
            )}
          </button>
        ) : null}
        <button
          type="submit"
          className="chat-send"
          disabled={streaming || !draft.trim()}
        >
          {streaming ? <Loader2 size={14} strokeWidth={2} className="chat-send-spin" aria-hidden /> : "Send"}
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
            <ToolCallChip key={i} call={t} />
          ))}
        </div>
      ) : null}
      {message.role === "assistant" ? (
        message.content ? (
          <MarkdownLite text={message.content} />
        ) : message.pending ? (
          <p className="chat-thinking">Thinking…</p>
        ) : null
      ) : (
        <p>{message.content}</p>
      )}
    </div>
  );
}

function ToolCallChip({ call }: { call: ToolCall }) {
  const argSummary = Object.entries(call.args)
    .map(([k, v]) => `${k}=${formatToolArg(v)}`)
    .join(" · ");
  const hasResult = call.result !== undefined;
  return (
    <details className="chat-tool" data-has-result={hasResult ? "true" : undefined}>
      <summary>
        <span className="chat-tool-name">{call.name}</span>
        {argSummary ? <span className="chat-tool-args">{argSummary}</span> : null}
        <span className="chat-tool-state" aria-hidden>
          {hasResult ? <ChevronDown size={12} strokeWidth={1.75} /> : "…"}
        </span>
      </summary>
      {hasResult ? (
        <pre className="chat-tool-result">{formatToolResult(call.result)}</pre>
      ) : null}
    </details>
  );
}

function formatToolArg(v: unknown): string {
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return JSON.stringify(v);
}

function formatToolResult(result: unknown): string {
  try {
    return JSON.stringify(result, null, 2);
  } catch {
    return String(result);
  }
}

// Tiny markdown renderer for the agent's tight prose: **bold**, *italic*,
// `code`, and `- ` bullet lists. The system prompt asks for 3-5 sentences,
// so headings/tables aren't worth the dependency.
function MarkdownLite({ text }: { text: string }) {
  const blocks = parseBlocks(text);
  return (
    <div className="chat-md">
      {blocks.map((block, i) =>
        block.type === "list" ? (
          <ul key={i}>
            {block.items.map((item, j) => (
              <li key={j}>{renderInline(item)}</li>
            ))}
          </ul>
        ) : (
          <p key={i}>{renderInline(block.text)}</p>
        ),
      )}
    </div>
  );
}

type Block = { type: "p"; text: string } | { type: "list"; items: string[] };

function parseBlocks(text: string): Block[] {
  const lines = text.split(/\r?\n/);
  const blocks: Block[] = [];
  let para: string[] = [];
  let list: string[] = [];
  const flushPara = () => {
    if (para.length) {
      blocks.push({ type: "p", text: para.join(" ") });
      para = [];
    }
  };
  const flushList = () => {
    if (list.length) {
      blocks.push({ type: "list", items: list });
      list = [];
    }
  };
  for (const raw of lines) {
    const line = raw.trimEnd();
    const bullet = /^\s*[-*]\s+(.*)$/.exec(line);
    if (bullet) {
      flushPara();
      list.push(bullet[1]);
      continue;
    }
    if (line.trim() === "") {
      flushPara();
      flushList();
      continue;
    }
    flushList();
    para.push(line);
  }
  flushPara();
  flushList();
  return blocks;
}

function renderInline(text: string): React.ReactNode[] {
  // Tokenize on **bold**, *italic*, and `code` in one pass.
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  const out: React.ReactNode[] = [];
  let last = 0;
  let key = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("**")) {
      out.push(<strong key={key++}>{tok.slice(2, -2)}</strong>);
    } else if (tok.startsWith("`")) {
      out.push(<code key={key++}>{tok.slice(1, -1)}</code>);
    } else {
      out.push(<em key={key++}>{tok.slice(1, -1)}</em>);
    }
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
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

// Web Speech API wrapper. Chrome/Safari ship it under different names; Firefox
// doesn't support it at all, so the mic button is hidden when unsupported.
interface DictationApi {
  supported: boolean;
  listening: boolean;
  start: () => void;
  stop: () => void;
}

interface SpeechRecognitionLike {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }> }) => void) | null;
  onerror: ((e: unknown) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

function useDictation(onFinalText: (text: string) => void): DictationApi {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const callbackRef = useRef(onFinalText);
  callbackRef.current = onFinalText;

  useEffect(() => {
    if (typeof window === "undefined") return;
    const w = window as unknown as {
      SpeechRecognition?: new () => SpeechRecognitionLike;
      webkitSpeechRecognition?: new () => SpeechRecognitionLike;
    };
    const Ctor = w.SpeechRecognition ?? w.webkitSpeechRecognition;
    if (!Ctor) return;
    setSupported(true);
    return () => {
      recognitionRef.current?.abort();
      recognitionRef.current = null;
    };
  }, []);

  const start = useCallback(() => {
    if (typeof window === "undefined") return;
    const w = window as unknown as {
      SpeechRecognition?: new () => SpeechRecognitionLike;
      webkitSpeechRecognition?: new () => SpeechRecognitionLike;
    };
    const Ctor = w.SpeechRecognition ?? w.webkitSpeechRecognition;
    if (!Ctor) return;
    const r = new Ctor();
    r.continuous = false;
    r.interimResults = false;
    r.lang = "en-US";
    r.onresult = (e) => {
      let finalText = "";
      for (let i = 0; i < e.results.length; i++) {
        const result = e.results[i];
        if (result.isFinal) finalText += result[0].transcript;
      }
      finalText = finalText.trim();
      if (finalText) callbackRef.current(finalText);
    };
    r.onerror = () => {
      setListening(false);
    };
    r.onend = () => {
      setListening(false);
      recognitionRef.current = null;
    };
    try {
      r.start();
      recognitionRef.current = r;
      setListening(true);
    } catch {
      setListening(false);
    }
  }, []);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  return { supported, listening, start, stop };
}
