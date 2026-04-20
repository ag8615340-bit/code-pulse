import { useRef, useEffect } from "react";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  relevantFiles?: string[];
}

const SUGGESTIONS = [
  "How does authentication work?",
  "Where should I start reading?",
  "Explain the folder structure",
  "What does the main entry point do?",
  "Which files handle API calls?",
];

function renderContent(text: string) {
  const parts = text.split(/(```[\s\S]*?```)/g);
  return parts.map((part, i) => {
    if (part.startsWith("```")) {
      const code = part.replace(/^```[a-z]*\n?/, "").replace(/```$/, "");
      return <pre key={i}><code>{code}</code></pre>;
    }
    const inlineParts = part.split(/(`[^`]+`)/g);
    return (
      <span key={i}>
        {inlineParts.map((ip, j) =>
          ip.startsWith("`") ? (
            <code key={j}>{ip.replace(/`/g, "")}</code>
          ) : (
            <span key={j} style={{ whiteSpace: "pre-wrap" }}>{ip}</span>
          )
        )}
      </span>
    );
  });
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  return (
    <div className={`message ${msg.role}`}>
      <div className={`avatar ${msg.role === "assistant" ? "ai" : "user"}`}>
        {msg.role === "assistant" ? "AI" : "You"}
      </div>
      <div className={`bubble ${msg.role === "assistant" ? "ai" : "user"}`}>
        {renderContent(msg.content)}
        {msg.relevantFiles && msg.relevantFiles.length > 0 && (
          <div className="relevant-files">
            {msg.relevantFiles.map((f) => (
              <span key={f} className="file-pill">{f}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5"
      strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}

interface ChatBoxProps {
  messages: ChatMessage[];
  input: string;
  setInput: (v: string) => void;
  onSend: (question?: string) => void;
  loadingChat: boolean;
  repoLoaded: boolean;
}

export default function ChatBox({
  messages,
  input,
  setInput,
  onSend,
  loadingChat,
  repoLoaded,
}: ChatBoxProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loadingChat]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  if (!repoLoaded && messages.length === 0) {
    return (
      <div className="chat-area">
        <div className="empty-state">
          <h1 className="empty-title">
            Understand any <span>codebase</span><br />in minutes.
          </h1>
          <p className="empty-sub">
            Paste a GitHub URL → AI reads the entire repo → Ask anything.
            No more spending days reading code alone.
          </p>
          <div className="suggestion-chips">
            {SUGGESTIONS.map((s) => (
              <span key={s} className="chip">{s}</span>
            ))}
          </div>
        </div>
        <div className="chat-input-bar">
          <textarea className="chat-textarea" rows={1} placeholder="Analyze a repo first →" disabled />
          <button className="btn-send" disabled><SendIcon /></button>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-area">
      <div className="messages-list">
        {messages.map((msg, i) => (
          <MessageBubble key={i} msg={msg} />
        ))}
        {loadingChat && (
          <div className="message">
            <div className="avatar ai">AI</div>
            <div className="bubble ai">
              <div className="typing">
                <span /><span /><span />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {repoLoaded && messages.length === 1 && (
        <div className="suggestion-chips" style={{ padding: "0 1.5rem 0.5rem" }}>
          {SUGGESTIONS.map((s) => (
            <span key={s} className="chip" onClick={() => onSend(s)}>{s}</span>
          ))}
        </div>
      )}

      <div className="chat-input-bar">
        <textarea
          className="chat-textarea"
          rows={1}
          placeholder="Ask anything about the codebase... (Enter to send)"
          value={input}
          disabled={!repoLoaded || loadingChat}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          className="btn-send"
          onClick={() => onSend()}
          disabled={!repoLoaded || !input.trim() || loadingChat}
        >
          {loadingChat ? <span className="spinner" /> : <SendIcon />}
        </button>
      </div>
    </div>
  );
}