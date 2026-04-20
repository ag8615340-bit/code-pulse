interface RepoInputProps {
  repoUrl: string;
  setRepoUrl: (url: string) => void;
  onAnalyze: () => void;
  loading: boolean;
  error: string;
}

export default function RepoInput({
  repoUrl,
  setRepoUrl,
  onAnalyze,
  loading,
  error,
}: RepoInputProps) {
  return (
    <div className="repo-input-section">
      <label className="input-label">GitHub URL</label>
      <input
        className="repo-input"
        placeholder="https://github.com/owner/repo"
        value={repoUrl}
        onChange={(e) => setRepoUrl(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && onAnalyze()}
        style={{ height: "36px" }}
      />
      <button
        className="btn-analyze"
        onClick={onAnalyze}
        disabled={loading || !repoUrl.trim()}
      >
        {loading ? (
          <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
            <span className="spinner" /> Analyzing...
          </span>
        ) : (
          "⚡ Analyze Repo"
        )}
      </button>
      {error && (
        <p style={{ marginTop: "0.5rem", fontSize: "0.7rem", color: "#fa6d6d" }}>
          ⚠️ {error}
        </p>
      )}
    </div>
  );
}