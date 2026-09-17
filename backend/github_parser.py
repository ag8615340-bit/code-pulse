
import os
import re
import base64
import logging
from urllib.parse import urlparse, quote
from typing import Any

import requests


logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
HEADERS = (
    {"Authorization": f"token {GITHUB_TOKEN}"}
    if GITHUB_TOKEN
    else {}
)

GITHUB_API = "https://api.github.com"

ALLOWED_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs",
    ".java", ".cpp", ".c", ".cs", ".rb", ".php",
    ".json", ".yaml", ".yml", ".toml", ".env.example",
    ".md", ".txt", ".sql",
}

MAX_FILE_SIZE_BYTES = 50_000
MAX_TOTAL_CHARS = 80_000

# Keep the existing per-file preview limit, but make truncation explicit.
MAX_FILE_CHARS = 12_000
README_MAX_CHARS = 8_000
REQUEST_TIMEOUT = 15


def _extract_owner_repo(github_url: str) -> tuple[str, str]:
    """
    Extract owner and repository name from a GitHub URL.

    Supports:
      https://github.com/owner/repo
      https://github.com/owner/repo/tree/branch
      https://github.com/owner/repo.git

    Rejects non-GitHub URLs and malformed repository paths.
    """
    if not isinstance(github_url, str) or not github_url.strip():
        raise ValueError("GitHub URL is required.")

    parsed = urlparse(github_url.strip())

    if parsed.scheme not in ("https", "http"):
        raise ValueError("GitHub URL must use HTTP or HTTPS.")

    if parsed.netloc.lower() not in ("github.com", "www.github.com"):
        raise ValueError("URL must point to github.com.")

    parts = [part for part in parsed.path.strip("/").split("/") if part]

    if len(parts) < 2:
        raise ValueError("Invalid GitHub repository URL.")

    owner = parts[0]
    repo = parts[1]

    if repo.endswith(".git"):
        repo = repo[:-4]

    # GitHub owner/repo names cannot contain arbitrary path separators.
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", owner):
        raise ValueError("Invalid GitHub owner name.")

    if not re.fullmatch(r"[A-Za-z0-9_.-]+", repo):
        raise ValueError("Invalid GitHub repository name.")

    return owner, repo


def _github_get(url: str, timeout: int = REQUEST_TIMEOUT):
    """
    Perform a GitHub API GET request with consistent error handling.
    """
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=timeout,
        )
        return response
    except requests.RequestException as exc:
        logger.warning("GitHub request failed: %s", exc)
        raise RuntimeError(
            "Unable to connect to GitHub. Please try again."
        ) from exc


def _fetch_repo_metadata(owner: str, repo: str) -> dict:
    """
    Retrieve repository metadata, including its default branch.
    """
    url = (
        f"{GITHUB_API}/repos/"
        f"{quote(owner, safe='')}/{quote(repo, safe='')}"
    )

    response = _github_get(url)

    if response.status_code == 404:
        raise ValueError(
            "Repository not found or access is restricted."
        )

    if response.status_code == 403:
        raise RuntimeError(
            "GitHub API access was denied or rate-limited. "
            "Check your GitHub token and API rate limit."
        )

    response.raise_for_status()
    data = response.json()

    return {
        "owner": data.get("owner", {}).get("login", owner),
        "repo": data.get("name", repo),
        "full_name": data.get("full_name", f"{owner}/{repo}"),
        "default_branch": data.get("default_branch", "main"),
        "private": data.get("private", False),
        "html_url": data.get(
            "html_url",
            f"https://github.com/{owner}/{repo}",
        ),
    }


def _fetch_tree(
    owner: str,
    repo: str,
    branch: str | None = None,
) -> list[dict]:
    """
    Fetch the recursive Git tree for a repository branch.

    Uses the repository's default branch when branch is omitted.
    """
    if branch:
        ref = quote(branch, safe="")
    else:
        ref = "HEAD"

    url = (
        f"{GITHUB_API}/repos/"
        f"{quote(owner, safe='')}/{quote(repo, safe='')}"
        f"/git/trees/{ref}?recursive=1"
    )

    response = _github_get(url)

    if response.status_code == 404:
        raise ValueError(
            f"Could not find repository tree for ref: {ref}"
        )

    if response.status_code == 403:
        raise RuntimeError(
            "GitHub API access was denied or rate-limited."
        )

    response.raise_for_status()
    data = response.json()

    if data.get("truncated"):
        logger.warning(
            "GitHub returned a truncated repository tree "
            "for %s/%s",
            owner,
            repo,
        )

    return data.get("tree", [])


def _get_extension(path: str) -> str:
    """
    Return a file extension, including special handling for
    .env.example.
    """
    filename = path.rsplit("/", 1)[-1].lower()

    if filename == ".env.example":
        return ".env.example"

    return os.path.splitext(filename)[1].lower()


def _is_allowed_file(path: str) -> bool:
    return _get_extension(path) in ALLOWED_EXTENSIONS


def _fetch_file_content(
    owner: str,
    repo: str,
    path: str,
) -> str | None:
    """
    Fetch and decode a file from the GitHub Contents API.

    Returns None when the file cannot be retrieved.
    """
    encoded_path = quote(path, safe="/")

    url = (
        f"{GITHUB_API}/repos/"
        f"{quote(owner, safe='')}/{quote(repo, safe='')}"
        f"/contents/{encoded_path}"
    )

    try:
        response = _github_get(url, timeout=REQUEST_TIMEOUT)

        if response.status_code != 200:
            logger.warning(
                "Could not fetch GitHub file %s: HTTP %s",
                path,
                response.status_code,
            )
            return None

        data = response.json()

        if data.get("type") != "file":
            return None

        raw = data.get("content", "")
        encoding = data.get("encoding", "")

        if encoding != "base64" or not raw:
            logger.warning(
                "Unsupported or empty GitHub content for %s",
                path,
            )
            return None

        decoded = base64.b64decode(
            raw,
            validate=False,
        )

        return decoded.decode(
            "utf-8",
            errors="replace",
        )

    except (
        requests.RequestException,
        RuntimeError,
        ValueError,
        TypeError,
    ) as exc:
        logger.warning(
            "File retrieval failed for %s: %s",
            path,
            exc,
        )
        return None


def _build_tree_nodes(flat_tree: list[dict]) -> list[dict]:
    """
    Convert GitHub's flat tree into nested directory nodes.
    """
    root: dict[str, Any] = {
        "name": "root",
        "path": "",
        "type": "dir",
        "children": [],
    }

    directory_cache = {"": root}

    def get_or_create_dir(path: str) -> dict:
        if path in directory_cache:
            return directory_cache[path]

        parent_path, _, name = path.rpartition("/")
        parent = get_or_create_dir(parent_path)

        new_dir = {
            "name": name,
            "path": path,
            "type": "dir",
            "children": [],
        }

        parent["children"].append(new_dir)
        directory_cache[path] = new_dir

        return new_dir

    for item in flat_tree:
        if item.get("type") != "blob":
            continue

        path = item.get("path", "")

        if not path:
            continue

        if not _is_allowed_file(path):
            continue

        parent_path, _, filename = path.rpartition("/")
        parent = get_or_create_dir(parent_path)

        parent["children"].append({
            "name": filename,
            "path": path,
            "type": "file",
            "children": [],
            "size": item.get("size"),
        })

    return root["children"]


def _fetch_readme(
    owner: str,
    repo: str,
    flat_tree: list[dict] | None = None,
) -> str:
    """
    Find README case-insensitively in the repository tree.
    """
    if flat_tree:
        readme_candidates = [
            item.get("path", "")
            for item in flat_tree
            if item.get("type") == "blob"
            and item.get("path", "").rsplit("/", 1)[-1].lower()
            in ("readme.md", "readme.txt", "readme")
        ]

        # Prefer a root-level README.
        readme_candidates.sort(
            key=lambda path: (
                "/" in path,
                path.lower(),
            )
        )

        for path in readme_candidates:
            content = _fetch_file_content(owner, repo, path)

            if content:
                return content[:README_MAX_CHARS]

    # Fallback for repositories whose tree did not expose a README.
    for name in ("README.md", "readme.md", "Readme.md"):
        content = _fetch_file_content(owner, repo, name)

        if content:
            return content[:README_MAX_CHARS]

    return "No README found."


def _add_line_numbers(content: str) -> str:
    """
    Add stable 1-based line numbers to source excerpts.
    """
    lines = content.splitlines()

    if not lines:
        return ""

    width = len(str(len(lines)))

    return "\n".join(
        f"{line_number:>{width}} | {line}"
        for line_number, line in enumerate(lines, start=1)
    )


def _make_source_excerpt(path: str, content: str) -> str:
    """
    Format a source file for the model with explicit path and
    truncation metadata.
    """
    original_chars = len(content)
    truncated = original_chars > MAX_FILE_CHARS

    excerpt = content[:MAX_FILE_CHARS]
    numbered_excerpt = _add_line_numbers(excerpt)

    header = (
        f"### Source File: {path}\n"
        f"Complete source retrieved: {'no' if truncated else 'yes'}\n"
        f"Source characters: {original_chars}\n"
    )

    if truncated:
        header += (
            f"NOTE: Source truncated after "
            f"{MAX_FILE_CHARS} characters. "
            f"Later lines are not included.\n"
        )

    return (
        header
        + "```text\n"
        + numbered_excerpt
        + "\n```\n\n"
    )


def parse_github_repo(
    github_url: str,
    branch: str | None = None,
) -> dict:
    """
    Parse a GitHub repository and construct source context.

    Existing return keys are preserved:
      - file_tree
      - repo_context
      - readme
      - repo_name

    Additional metadata:
      - repository
      - branch
      - retrieved_files
      - skipped_files
      - fetch_errors
      - context_truncated
      - total_context_chars
    """
    owner, repo = _extract_owner_repo(github_url)

    metadata = _fetch_repo_metadata(owner, repo)

    selected_branch = branch or metadata["default_branch"]

    flat_tree = _fetch_tree(
        owner,
        repo,
        selected_branch,
    )

    file_tree = _build_tree_nodes(flat_tree)

    readme = _fetch_readme(
        owner,
        repo,
        flat_tree,
    )

    context_parts = [
        f"# Repository: {metadata['full_name']}\n",
        f"Branch: {selected_branch}\n",
        f"Repository URL: {metadata['html_url']}\n",
        f"\n## README\n{readme}\n\n",
        "## Retrieved Source Files\n\n",
    ]

    total_chars = sum(
        len(part)
        for part in context_parts
    )

    retrieved_files = []
    skipped_files = []
    fetch_errors = []
    context_truncated = False

    for item in flat_tree:
        if item.get("type") != "blob":
            continue

        path = item.get("path", "")

        if not path or not _is_allowed_file(path):
            continue

        size = item.get("size")

        if (
            isinstance(size, int)
            and size > MAX_FILE_SIZE_BYTES
        ):
            skipped_files.append({
                "path": path,
                "reason": "file exceeds MAX_FILE_SIZE_BYTES",
                "size": size,
            })
            continue

        if total_chars >= MAX_TOTAL_CHARS:
            context_truncated = True
            skipped_files.append({
                "path": path,
                "reason": "repository context character limit reached",
                "size": size,
            })
            continue

        content = _fetch_file_content(
            owner,
            repo,
            path,
        )

        if content is None:
            fetch_errors.append({
                "path": path,
                "reason": "file fetch failed or content unavailable",
            })
            continue

        if len(content.encode("utf-8")) > MAX_FILE_SIZE_BYTES:
            skipped_files.append({
                "path": path,
                "reason": "decoded file exceeds MAX_FILE_SIZE_BYTES",
                "size": len(content.encode("utf-8")),
            })
            continue

        excerpt = _make_source_excerpt(
            path,
            content,
        )

        remaining_chars = MAX_TOTAL_CHARS - total_chars

        if len(excerpt) > remaining_chars:
            excerpt = excerpt[:remaining_chars]
            context_truncated = True

            skipped_files.append({
                "path": path,
                "reason": "source excerpt truncated by total context limit",
                "size": size,
            })

        context_parts.append(excerpt)
        total_chars += len(excerpt)

        retrieved_files.append({
            "path": path,
            "size": len(content.encode("utf-8")),
            "source_chars": len(content),
            "included_chars": min(
                len(content),
                MAX_FILE_CHARS,
            ),
            "truncated": len(content) > MAX_FILE_CHARS,
        })

    repo_context = "".join(context_parts)

    return {
        # Existing keys retained for compatibility.
        "file_tree": file_tree,
        "repo_context": repo_context,
        "readme": readme,
        "repo_name": metadata["full_name"],

        # Additional retrieval and freshness metadata.
        "repository": metadata,
        "branch": selected_branch,
        "retrieved_files": retrieved_files,
        "skipped_files": skipped_files,
        "fetch_errors": fetch_errors,
        "context_truncated": context_truncated,
        "total_context_chars": len(repo_context),
    }
