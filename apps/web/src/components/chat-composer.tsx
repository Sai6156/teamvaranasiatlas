"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUp, Copy, Maximize2, Minimize2, Square, X } from "lucide-react";

type Props = {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  busy: boolean;
  onStop: () => void;
  onNotice: (text: string) => void;
  focusSignal?: number;
};
export default function ChatComposer({
  value,
  onChange,
  onSend,
  busy,
  onStop,
  onNotice,
  focusSignal = 0,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const input = useRef<HTMLTextAreaElement>(null);
  const expandedInput = useRef<HTMLTextAreaElement>(null);
  const dialog = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = input.current;
    if (!element) return;
    element.style.height = "auto";
    element.style.height = `${Math.min(Math.max(element.scrollHeight, 48), 240)}px`;
  }, [value]);
  useEffect(() => {
    if (focusSignal) {
      input.current?.focus();
      input.current?.setSelectionRange(0, 0);
    }
  }, [focusSignal]);
  useEffect(() => {
    if (!expanded) return;
    expandedInput.current?.focus();
    function key(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setExpanded(false);
        input.current?.focus();
      }
      if (event.key === "Tab") {
        const elements = dialog.current?.querySelectorAll<HTMLElement>(
          "button:not(:disabled),textarea",
        );
        if (!elements?.length) return;
        const first = elements[0],
          last = elements[elements.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    }
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
  }, [expanded]);
  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      onNotice("Prompt copied.");
    } catch {
      onNotice("Select the prompt and press Ctrl+C to copy.");
    }
  }
  function send() {
    if (!busy && value.trim()) {
      setExpanded(false);
      onSend();
    }
  }
  function key(event: React.KeyboardEvent<HTMLTextAreaElement>, large = false) {
    if (event.nativeEvent.isComposing) return;
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      (!large || event.ctrlKey || event.metaKey)
    ) {
      event.preventDefault();
      send();
    }
  }
  const actions = (
    <>
      <button
        type="button"
        className="composer-tool"
        onClick={copy}
        disabled={!value}
        title="Copy entire prompt"
        aria-label="Copy entire prompt"
      >
        <Copy size={16} />
      </button>
      <button
        type="button"
        className="composer-tool"
        onClick={() => setExpanded(true)}
        title="Expand prompt editor"
        aria-label="Expand prompt editor"
      >
        <Maximize2 size={16} />
      </button>
      {busy ? (
        <button
          type="button"
          className="stop-button"
          onClick={onStop}
          aria-label="Stop answer"
        >
          <Square size={17} />
        </button>
      ) : (
        <button
          type="submit"
          disabled={!value.trim()}
          aria-label="Send question"
        >
          <ArrowUp size={20} />
        </button>
      )}
    </>
  );
  return (
    <>
      <form
        className="chat-composer improved-composer"
        onSubmit={(event) => {
          event.preventDefault();
          send();
        }}
      >
        <textarea
          ref={input}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => key(event)}
          aria-label="Your question"
          placeholder="Ask a question. Find a little clarity."
          rows={2}
          maxLength={20000}
        />
        <div className="composer-tools">
          {value.length > 1000 && (
            <span className="prompt-length">
              {value.length.toLocaleString()} / 20,000
            </span>
          )}
          {actions}
        </div>
      </form>
      {expanded && (
        <div
          className="modal-backdrop prompt-backdrop"
          onClick={(event) => {
            if (event.target === event.currentTarget) setExpanded(false);
          }}
        >
          <div
            ref={dialog}
            className="prompt-editor"
            role="dialog"
            aria-modal="true"
            aria-labelledby="prompt-editor-title"
          >
            <header>
              <div>
                <h2 id="prompt-editor-title">Review your full prompt</h2>
                <p>Edit, select, and copy every line before sending.</p>
              </div>
              <button
                className="icon-button"
                onClick={() => setExpanded(false)}
                aria-label="Close prompt editor"
              >
                <X size={20} />
              </button>
            </header>
            <textarea
              ref={expandedInput}
              value={value}
              onChange={(event) => onChange(event.target.value)}
              onKeyDown={(event) => key(event, true)}
              aria-label="Full prompt"
              placeholder="Write or paste your full question here…"
              maxLength={20000}
            />
            <footer>
              <span>
                {value.length.toLocaleString()} / 20,000 characters · Ctrl+Enter
                to send
              </span>
              <button
                className="btn secondary small"
                onClick={copy}
                disabled={!value}
              >
                <Copy size={15} />
                Copy prompt
              </button>
              <button
                className="btn secondary small"
                onClick={() => setExpanded(false)}
              >
                <Minimize2 size={15} />
                Done editing
              </button>
              <button
                className="btn primary small"
                onClick={send}
                disabled={busy || !value.trim()}
              >
                <ArrowUp size={16} />
                Send
              </button>
            </footer>
          </div>
        </div>
      )}
    </>
  );
}
