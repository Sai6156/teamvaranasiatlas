"use client";
import { useEffect, useRef, useState } from "react";
import { Clock, Loader2, MessageSquare, Search, X } from "lucide-react";
import { api, type Conversation } from "@/lib/client";

export default function ChatHistory({
  workspaceId,
  selected,
  onSelect,
  onClose,
}: {
  workspaceId: string;
  selected: string | null;
  onSelect: (id: string) => void;
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<Conversation[]>([]);
  const [busy, setBusy] = useState(false);
  const [more, setMore] = useState(false);
  const [error, setError] = useState("");
  const version = useRef(0);
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    input.current?.focus();
    function key(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
  }, [onClose]);
  async function load(offset = 0, expected = version.current) {
    setBusy(true);
    setError("");
    try {
      const next = await api<Conversation[]>(
        `/workspaces/${workspaceId}/conversations?limit=50&offset=${offset}&search=${encodeURIComponent(query)}`,
      );
      if (expected !== version.current) return;
      setRows((old) =>
        offset
          ? [
              ...old,
              ...next.filter((c) => !old.some((item) => item.id === c.id)),
            ]
          : next,
      );
      setMore(next.length === 50);
    } catch (error) {
      if (expected === version.current)
        setError(
          error instanceof Error
            ? error.message
            : "Could not load conversations.",
        );
    } finally {
      if (expected === version.current) setBusy(false);
    }
  }
  useEffect(() => {
    const expected = ++version.current;
    const timer = setTimeout(() => {
      void load(0, expected);
    }, 200);
    return () => clearTimeout(timer);
  }, [query, workspaceId]);
  return (
    <div
      className="modal-backdrop history-backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="history-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="history-title"
      >
        <header>
          <div>
            <h2 id="history-title">Your conversations</h2>
            <p>Search and return to any chat in this workspace.</p>
          </div>
          <button
            className="icon-button"
            onClick={onClose}
            aria-label="Close conversation history"
          >
            <X size={20} />
          </button>
        </header>
        <label className="history-search">
          <Search size={18} />
          <input
            ref={input}
            aria-label="Search all conversations"
            placeholder="Search conversation titles…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            maxLength={100}
          />
          <span>Ctrl K</span>
        </label>
        <div className="history-results">
          {rows.map((conversation) => (
            <button
              className={selected === conversation.id ? "active" : ""}
              key={conversation.id}
              onClick={() => {
                onSelect(conversation.id);
                onClose();
              }}
            >
              <MessageSquare size={18} />
              <span>
                <strong>{conversation.title}</strong>
                <small>
                  <Clock size={12} />
                  {new Date(
                    conversation.updated_at || conversation.created_at,
                  ).toLocaleString("en-IN", {
                    day: "numeric",
                    month: "short",
                    hour: "numeric",
                    minute: "2-digit",
                  })}
                </small>
              </span>
            </button>
          ))}
          {error && <p className="notice error">{error}</p>}
          {busy && (
            <p className="history-loading">
              <Loader2 size={17} className="spin" />
              Loading conversations…
            </p>
          )}
          {!busy && !rows.length && !error && (
            <p className="history-loading">
              {query
                ? "No conversations match that title."
                : "Your conversations will appear here."}
            </p>
          )}
          {more && !busy && (
            <button
              className="btn secondary full"
              onClick={() => load(rows.length)}
            >
              Load more conversations
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
