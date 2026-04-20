import { useState } from "react";
import RepoInput from "./components/RepoInput";
import FileTree, { FileNode } from "./components/FileTree";
import ChatBox, { ChatMessage } from "./components/ChatBox";

const API_BASE = "https://codeboard-tlwd.onrender.com";

export default function App() {
  const [repoUrl, setRepoUrl]         = useState("");
  const [repoName, setRepoName]       = useState("");
  const [repoContext, setRepoContext]  = useState("");
  const [fileTree, setFileTree]       = useState<FileNode[]>([]);
  const [messages, setMessages]       = useState<ChatMessage[]>([]);
  const [input, setInput]             = useState("");
  const [loadingRepo, setLoadingRepo] = useState(false);
  const [loadingChat, setLoadingChat] = useState(false);
  const [error, setError]             = useState("");

  const repoLoaded = repoContext.length > 0;

  // ── Parse Repo ──────────────────────────────────────────────────────────────
  const handleParseRepo = async () => {
    const url = repoUrl.trim();
    if (!url) return;
    setError("");
    setLoadingRepo(true);
    setMessages([]);
    setFileTree([]);
    setRepoContext("");

    try {
      const res = await fetch(`${API_BASE}/api/parse-repo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ github_url: url }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? "Failed to parse repo");
      }
      const data = await res.json();
      setFileTree(data.file_tree);
      setRepoContext(data.repo_context);
      setRepoName(data.repo_name);
      setMessages([
        {
          role: "assistant",
          content: `✅ Successfully analyzed **${data.repo_name}**!\n\nI've read through the codebase. Ask me anything — architecture, specific files, how to get started, or where a feature lives.`,
        },
      ]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoadingRepo(false);
    }
  };

  // ── Send Chat ───────────────────────────────────────────────────────────────
  const handleSend = async (question?: string) => {
    const q = (question ?? input).trim();
    if (!q || !repoContext || loadingChat) return;

    const userMsg: ChatMessage = { role: "user", content: q };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoadingChat(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: q,
          repo_context: repoContext,
          chat_history: messages.map((m) => ({ role: m.role, content: m.content })),
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? "AI response failed");
      }
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.answer, relevantFiles: data.relevant_files },
      ]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoadingChat(false);
    }
  };

  return (
    <div className="app-shell">
      {/* Background orbs */}
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />

      {/* Navbar */}
      <nav className="navbar">
        <span className="logo-dot" />
        <span className="logo">CodeBoard</span>
        {repoLoaded && (
          <span className="status-badge ready" style={{ marginLeft: "auto" }}>
            <span className="status-dot" />
            {repoName}
          </span>
        )}
        {loadingRepo && (
          <span className="status-badge loading" style={{ marginLeft: "auto" }}>
            <span className="status-dot" />
            Analyzing...
          </span>
        )}
      </nav>

      {/* Main grid */}
      <div className="main-grid">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="sidebar-header">Repository</div>
          <RepoInput
            repoUrl={repoUrl}
            setRepoUrl={setRepoUrl}
            onAnalyze={handleParseRepo}
            loading={loadingRepo}
            error={error}
          />
          <FileTree nodes={fileTree} loading={loadingRepo} />
        </aside>

        {/* Chat */}
        <ChatBox
          messages={messages}
          input={input}
          setInput={setInput}
          onSend={handleSend}
          loadingChat={loadingChat}
          repoLoaded={repoLoaded}
        />
      </div>
    </div>
  );
}