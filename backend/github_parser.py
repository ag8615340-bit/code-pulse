import os
import requests
import base64
from typing import Any

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

ALLOWED_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs",
    ".java", ".cpp", ".c", ".cs", ".rb", ".php",
    ".json", ".yaml", ".yml", ".toml", ".env.example",
    ".md", ".txt", ".sql",
}

MAX_FILE_SIZE_BYTES = 50_000   # 50KB per file
MAX_TOTAL_CHARS     = 80_000    # total context cap


def _extract_owner_repo(github_url: str) -> tuple[str, str]:
    """Parse github.com/owner/repo from URL."""
    url = github_url.rstrip("/").replace("https://github.com/", "").replace("http://github.com/", "")
    parts = url.split("/")
    if len(parts) < 2:
        raise ValueError("Invalid GitHub URL. Expected format: https://github.com/owner/repo")
    return parts[0], parts[1]


def _fetch_tree(owner: str, repo: str) -> list[dict]:
    """Fetch flat file tree via Git Trees API (recursive)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code == 404:
        raise ValueError(f"Repo not found: {owner}/{repo}")
    resp.raise_for_status()
    data = resp.json()
    return data.get("tree", [])


def _fetch_file_content(owner: str, repo: str, path: str) -> str | None:
    """Fetch decoded content of a single file."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    if resp.status_code != 200:
        return None
    data = resp.json()
    if data.get("size", 0) > MAX_FILE_SIZE_BYTES:
        return None
    raw = data.get("content", "")
    try:
        return base64.b64decode(raw).decode("utf-8", errors="replace")
    except Exception:
        return None


def _build_tree_nodes(flat_tree: list[dict]) -> list[dict]:
    """Convert flat GitHub tree list into nested dict structure."""
    root: dict[str, Any] = {"name": "root", "path": "", "type": "dir", "children": []}

    def get_or_create_dir(parts: list[str], node: dict) -> dict:
        if not parts:
            return node
        name = parts[0]
        for child in node["children"]:
            if child["name"] == name and child["type"] == "dir":
                return get_or_create_dir(parts[1:], child)
        new_dir: dict = {"name": name, "path": "/".join(parts), "type": "dir", "children": []}
        node["children"].append(new_dir)
        return get_or_create_dir(parts[1:], new_dir)

    for item in flat_tree:
        if item["type"] == "tree":
            continue
        path: str = item["path"]
        parts = path.split("/")
        parent = get_or_create_dir(parts[:-1], root) if len(parts) > 1 else root
        ext = os.path.splitext(parts[-1])[1].lower()
        if ext in ALLOWED_EXTENSIONS or parts[-1].lower() in ("dockerfile", "makefile", "readme"):
            parent["children"].append({"name": parts[-1], "path": path, "type": "file", "children": []})

    return root["children"]


def _fetch_readme(owner: str, repo: str) -> str:
    """Try to fetch README.md content."""
    for name in ["README.md", "readme.md", "Readme.md"]:
        content = _fetch_file_content(owner, repo, name)
        if content:
            return content[:3000]
    return "No README found."


def parse_github_repo(github_url: str) -> dict:
    owner, repo = _extract_owner_repo(github_url)
    flat_tree = _fetch_tree(owner, repo)

    file_tree = _build_tree_nodes(flat_tree)
    readme    = _fetch_readme(owner, repo)

    # Build repo context string (concatenate file contents up to limit)
    context_parts: list[str] = [f"# Repository: {owner}/{repo}\n"]
    context_parts.append(f"## README\n{readme}\n\n## Source Files\n")
    total_chars = sum(len(p) for p in context_parts)

    for item in flat_tree:
        if item["type"] != "blob":
            continue
        path = item["path"]
        ext  = os.path.splitext(path)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            continue
        if total_chars >= MAX_TOTAL_CHARS:
            break
        content = _fetch_file_content(owner, repo, path)
        if content:
            snippet = f"### {path}\n
http://googleusercontent.com/immersive_entry_chip/0

Iske baad Render automatically deploy utha lega aur is baar wo "Syntax Error" nahi aayega. Backend live hote hi batao!