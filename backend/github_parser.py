import os
import requests
import base64
from typing import Any

# Purana HEADERS wala line delete kar dena, uski zarurat nahi hai yahan

ALLOWED_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs",
    ".java", ".cpp", ".c", ".cs", ".rb", ".php",
    ".json", ".yaml", ".yml", ".toml", ".env.example",
    ".md", ".txt", ".sql",
}

MAX_FILE_SIZE_BYTES = 50_000
MAX_TOTAL_CHARS = 80_000

# Ek helper function jo har baar naya token aur header generate karega
def get_headers():
    token = os.getenv("GITHUB_TOKEN", "")
    if token:
        return {"Authorization": f"token {token}"}
    return {}

def _extract_owner_repo(github_url: str) -> tuple[str, str]:
    url = github_url.rstrip("/").replace("https://github.com/", "").replace("http://github.com/", "")
    parts = url.split("/")
    if len(parts) < 2:
        raise ValueError("Invalid GitHub URL")
    return parts[0], parts[1]

def _fetch_tree(owner: str, repo: str) -> list[dict]:
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
    # Yahan HEADERS ki jagah get_headers() call kiya hai
    resp = requests.get(url, headers=get_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json().get("tree", [])

def _fetch_file_content(owner: str, repo: str, path: str) -> str | None:
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    # Yahan bhi HEADERS ki jagah get_headers() call kiya hai
    resp = requests.get(url, headers=get_headers(), timeout=10)
    if resp.status_code != 200:
        return None
    data = resp.json()
    raw = data.get("content", "")
    try:
        return base64.b64decode(raw).decode("utf-8", errors="replace")
    except Exception:
        return None

# Baki saara code (build_tree_nodes, fetch_readme, parse_github_repo) 
# bilkul waisa hi rahega jaisa aapne diya hai... niche paste kar dena.