
import os
import re
import logging

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# --------------------------------------------------
# GROQ CONFIGURATION
# --------------------------------------------------

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is missing. "
        "Set it in your environment variables."
    )

client = Groq(api_key=GROQ_API_KEY)

MODEL = "openai/gpt-oss-120b"

# Maximum repository context passed to the model.
# The parser currently limits the complete repository
# context, so this should be adjusted if that limit changes.
MAX_REPO_CONTEXT_CHARS = int(
    os.getenv("MAX_REPO_CONTEXT_CHARS", "60000")
)

MAX_HISTORY_MESSAGES = 6
MAX_HISTORY_MESSAGE_CHARS = 4000


# --------------------------------------------------
# SYSTEM PROMPT
# --------------------------------------------------

SYSTEM_PROMPT = """You are an expert software engineer and codebase guide.

Your job is to help developers understand the actual GitHub
repository provided in the current repository context.

Your answers must be grounded in the supplied repository
source, not assumptions about how projects usually work.

==================================================
SOURCE-GROUNDING RULES
==================================================

1. Use only repository information that is present in the
   supplied repository context.

2. Never invent:
   - File paths
   - Function or class names
   - Line numbers
   - API endpoints
   - Dependencies
   - Model identifiers
   - Source code
   - Features or implementation details

3. Distinguish clearly between:
   - Directly verified source-code facts
   - README or documentation claims
   - Reasonable inferences
   - Information that is unavailable

4. A README description does not prove that a feature
   is implemented in the source code.

5. A file appearing in a file tree does not prove that
   its contents were retrieved or inspected.

6. Do not claim that the entire repository was searched
   unless the supplied context establishes that.

7. If source code is truncated, incomplete, or missing,
   clearly explain the limitation.

8. If the evidence is insufficient, say:
   "I cannot verify this from the retrieved repository
   context."

9. Do not fill missing implementation details using
   general programming knowledge.

10. Do not treat previous assistant answers as source
    code or proof.

==================================================
CODE AND FILE REFERENCES
==================================================

1. Use exact repository-relative file paths when they
   are explicitly present in the supplied context.

2. Only provide source snippets that are actually present
   in the supplied repository context.

3. Do not reconstruct omitted or truncated code.

4. Only provide exact line numbers when the supplied
   source contains verified original line numbers.

5. If line numbers are unavailable, say they are
   unavailable. Never estimate them.

6. When explaining a flow across multiple files,
   identify the evidence for each connection.

7. Do not claim that one function calls another unless
   the supplied source supports that connection.

8. When asked for relevant files, include only paths
   that actually appear in the supplied repository
   context.

==================================================
ANALYSIS GUIDELINES
==================================================

For architecture questions:
- Explain the high-level flow first.
- Then explain each step using source evidence.
- Identify missing links in the execution flow.

For bug analysis:
- Explain the relevant code and the failure condition.
- Distinguish confirmed bugs from possible issues.
- Do not label a hypothesis as a confirmed bug.

For implementation questions:
- Explain what the current code actually does.
- Do not assume that a planned feature exists.
- If the requested behavior is not visible in the
  supplied source, state that limitation.

For repository comparisons:
- Compare only evidence available for both sides.
- Do not silently treat missing information as proof
  that a feature does not exist.

==================================================
RESPONSE STYLE
==================================================

- Answer clearly, naturally, and concisely.
- Use simple, understandable language.
- Be friendly but precise.
- Answer the user's actual question first.
- Avoid unnecessary repetition.
- Use headings and lists when they improve clarity.
- Do not produce pseudocode when the user requests
  exact source code.
- Do not claim that you independently fetched GitHub
  unless that capability was actually used.

At the end of every answer, list 1-3 relevant
repository file paths under:

📁 Relevant Files:

Only list paths supported by the current context.

You ONLY answer questions related to the provided
repository. If asked something unrelated, politely
redirect the user.
"""


# --------------------------------------------------
# REPOSITORY FILE PATH EXTRACTION
# --------------------------------------------------

def _extract_repo_paths(repo_context: str) -> list[str]:
    """
    Extract repository-relative file paths from the
    repository context.

    Supports the file headings produced by the parser,
    such as:
        ### path/to/file.py

    Also supports a Source Files section containing
    backtick-quoted file paths.

    This does not prove that every listed file's full
    contents were retrieved.
    """

    if not isinstance(repo_context, str) or not repo_context:
        return []

    paths = []
    seen = set()

    patterns = [
        r"(?m)^###\s+(?:Source File:\s*)?([^\r\n]+?)\s*$",
        r"(?m)^\s*[-*]\s+`([^`\r\n]+\.[a-zA-Z0-9]{1,15})`",
    ]

    for pattern in patterns:
        for match in re.findall(pattern, repo_context):
            path = match.strip().strip("`").strip()

            # Remove any additional descriptive suffix.
            path = path.split(" (", 1)[0].strip()

            if not path:
                continue

            # Avoid accepting headings that are not file paths.
            if path.startswith("#") or path.startswith("http"):
                continue

            if "/" not in path and "." not in path:
                continue

            if path not in seen:
                seen.add(path)
                paths.append(path)

    return paths


def _extract_relevant_files(
    answer: str,
    repo_context: str = "",
) -> list[str]:
    """
    Extract file paths mentioned in the answer, then
    keep only paths present in the supplied repository
    context.

    This prevents the API response from reporting
    arbitrary invented paths as relevant files.
    """

    if not answer:
        return []

    known_paths = _extract_repo_paths(repo_context)

    if not known_paths:
        return []

    known_set = set(known_paths)

    # Match backtick-quoted paths in the answer.
    candidates = re.findall(
        r"`([^`\n]+)`",
        answer,
    )

    # Also inspect the Relevant Files section.
    sections = re.findall(
        r"(?:Relevant Files?:)([\s\S]*?)(?:\n\n|$)",
        answer,
        flags=re.IGNORECASE,
    )

    for section in sections:
        candidates.extend(
            re.findall(
                r"`([^`\n]+)`",
                section,
            )
        )

    result = []
    seen = set()

    for candidate in candidates:
        cleaned = candidate.strip().strip(".,;:()")

        if cleaned in known_set and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)

    # Keep the existing maximum of 5 results.
    return result[:5]


# --------------------------------------------------
# CHAT HISTORY SANITIZATION
# --------------------------------------------------

def _sanitize_chat_history(
    chat_history: list[dict] | None,
) -> list[dict]:
    """
    Keep only valid user/assistant messages.

    The current repository context is supplied separately
    and should remain the source of truth.
    """

    if not isinstance(chat_history, list):
        return []

    cleaned_history = []

    for msg in chat_history[-MAX_HISTORY_MESSAGES:]:
        if not isinstance(msg, dict):
            continue

        role = msg.get("role")
        content = msg.get("content")

        if role not in ("user", "assistant"):
            continue

        if not isinstance(content, str):
            continue

        content = content.strip()

        if not content:
            continue

        if len(content) > MAX_HISTORY_MESSAGE_CHARS:
            content = (
                content[:MAX_HISTORY_MESSAGE_CHARS]
                + "\n[Previous message truncated]"
            )

        cleaned_history.append({
            "role": role,
            "content": content,
        })

    return cleaned_history


# --------------------------------------------------
# REPOSITORY CONTEXT PREPARATION
# --------------------------------------------------

def _prepare_repo_context(repo_context: str) -> str:
    """
    Prepare repository context without silently pretending
    that truncated content is complete.
    """

    if not isinstance(repo_context, str):
        raise TypeError("repo_context must be a string.")

    context = repo_context.strip()

    if not context:
        return ""

    if len(context) > MAX_REPO_CONTEXT_CHARS:
        logger.warning(
            "Repository context exceeds configured limit. "
            "Original chars: %s, limit: %s",
            len(context),
            MAX_REPO_CONTEXT_CHARS,
        )

        context = (
            context[:MAX_REPO_CONTEXT_CHARS]
            + "\n\n"
            + "[WARNING: Repository context was truncated "
              "before being sent to the AI. Some files or "
              "source lines may be missing.]"
        )

    return context


# --------------------------------------------------
# AI RESPONSE GENERATION
# --------------------------------------------------

def get_ai_response(
    question: str,
    repo_context: str,
    chat_history: list[dict],
) -> dict:
    """
    Generate a repository-grounded response using Groq.

    Existing interface preserved:
      question
      repo_context
      chat_history

    Existing return structure preserved:
      answer
      relevant_files
    """

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question cannot be empty.")

    if not isinstance(repo_context, str):
        raise TypeError("repo_context must be a string.")

    question = question.strip()

    prepared_context = _prepare_repo_context(repo_context)

    if not prepared_context:
        raise ValueError("Repository context is empty.")

    repo_paths = _extract_repo_paths(prepared_context)

    if repo_paths:
        file_inventory = "\n".join(
            f"- {path}"
            for path in repo_paths
        )
    else:
        file_inventory = (
            "No explicit repository file paths "
            "could be extracted from the supplied context."
        )

    # --------------------------------------------------
    # BUILD SYSTEM MESSAGE
    # --------------------------------------------------

    system_content = (
        f"{SYSTEM_PROMPT}\n\n"
        "==================================================\n"
        "CURRENT REPOSITORY CONTEXT\n"
        "==================================================\n\n"
        f"{prepared_context}\n\n"
        "==================================================\n"
        "FILE PATHS FOUND IN THIS CONTEXT\n"
        "==================================================\n\n"
        f"{file_inventory}\n\n"
        "IMPORTANT: This inventory only reflects paths "
        "found in the supplied context. It does not prove "
        "that every file in the actual GitHub repository "
        "was retrieved."
    )

    messages: list[dict] = [
        {
            "role": "system",
            "content": system_content,
        }
    ]

    # --------------------------------------------------
    # ADD RECENT CHAT HISTORY
    # --------------------------------------------------

    sanitized_history = _sanitize_chat_history(
        chat_history
    )

    for msg in sanitized_history:
        messages.append(msg)

    # --------------------------------------------------
    # ADD CURRENT QUESTION
    # --------------------------------------------------

    messages.append({
        "role": "user",
        "content": (
            "Answer the following question using the "
            "current repository context and the source-"
            "grounding rules.\n\n"
            f"Question: {question}"
        ),
    })

    # --------------------------------------------------
    # CALL GROQ API
    # --------------------------------------------------

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            reasoning_effort="low",
            max_completion_tokens=4096,
        )

        if not response.choices:
            logger.error(
                "Groq returned no choices. Model: %s",
                MODEL,
            )

            return {
                "answer": (
                    "The AI returned no response. "
                    "Please try again."
                ),
                "relevant_files": [],
            }

        choice = response.choices[0]
        message = choice.message

        answer = message.content

        # --------------------------------------------------
        # HANDLE EMPTY RESPONSE
        # --------------------------------------------------

        if not answer or not answer.strip():
            logger.warning(
                "Groq returned empty content. "
                "Model: %s, finish_reason: %s",
                MODEL,
                choice.finish_reason,
            )

            answer = (
                "The AI returned an empty response. "
                "Please try asking your question again. "
                "If this continues, check the server logs."
            )

        # --------------------------------------------------
        # EXTRACT VERIFIED RELEVANT FILES
        # --------------------------------------------------

        relevant_files = _extract_relevant_files(
            answer=answer,
            repo_context=prepared_context,
        )

        return {
            "answer": answer,
            "relevant_files": relevant_files,
        }

    # --------------------------------------------------
    # ERROR LOGGING
    # --------------------------------------------------

    except Exception:
        logger.exception(
            "Groq API request failed. Model: %s",
            MODEL,
        )
        raise
