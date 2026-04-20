import { useState } from "react";

export interface FileNode {
  name: string;
  path: string;
  type: "file" | "dir";
  children?: FileNode[];
}

function getIcon(node: FileNode, collapsed: boolean): string {
  if (node.type === "dir") return collapsed ? "📁" : "📂";
  const ext = node.name.split(".").pop()?.toLowerCase();
  const icons: Record<string, string> = {
    py: "🐍", ts: "📘", tsx: "⚛️", js: "📜", jsx: "⚛️",
    json: "📋", md: "📝", yml: "⚙️", yaml: "⚙️", css: "🎨",
    html: "🌐", sql: "🗄️", go: "🐹", rs: "🦀", env: "🔑",
  };
  return icons[ext ?? ""] ?? "📄";
}

function TreeNode({ node, depth }: { node: FileNode; depth: number }) {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <div>
      <div
        className={`tree-item ${node.type}`}
        style={{ paddingLeft: `${8 + depth * 12}px` }}
        onClick={() => node.type === "dir" && setCollapsed((p) => !p)}
        title={node.path}
      >
        <span className="tree-icon">{getIcon(node, collapsed)}</span>
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {node.name}
        </span>
      </div>
      {node.type === "dir" && !collapsed && node.children && node.children.length > 0 && (
        <div>
          {node.children.map((child) => (
            <TreeNode key={child.path} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function FileTree({ nodes, loading }: { nodes: FileNode[]; loading: boolean }) {
  return (
    <div className="file-tree">
      {loading ? (
        <p style={{ fontSize: "0.72rem", color: "var(--muted)", padding: "0.75rem" }}>
          Fetching files...
        </p>
      ) : nodes.length > 0 ? (
        nodes.map((node) => <TreeNode key={node.path} node={node} depth={0} />)
      ) : (
        <p style={{ fontSize: "0.72rem", color: "var(--muted)", padding: "0.75rem" }}>
          No repo loaded yet
        </p>
      )}
    </div>
  );
}