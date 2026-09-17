
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


# --------------------------------------------------
# SYSTEM PROMPT
# --------------------------------------------------

SYSTEM_PROMPT = """You are an expert software engineer and codebase guide.

You help new developers understand a GitHub repository
using the repository context provided in the conversation.

Guidelines:
- Answer clearly and concisely.
- Use exact file paths when they are present in the context.
- Never invent file paths, function names, line numbers,
  endpoints, code snippets, or repository details.
- If exact source evidence is missing, clearly say so.
- If asked about architecture, explain the high-level
  flow first, then the details.
- Only show code snippets that are present in the
  provided repository context.
- At the end of every answer, list 1-3 relevant
  file paths under "📁 Relevant Files:".
- Be friendly but precise.

You ONLY answer questions related to the provided
repository. If asked something unrelated, politely
redirect the user.
"""


# --------------------------------------------------
# RELEVANT FILE EXTRACTION
# --------------------------------------------------

def _extract_relevant_files(answer: str) -> list[str]:
    """Extract likely file paths mentioned in the AI response."""

    if not answer:
        return []

    pattern = r"`([^`\n]+\.[a-zA-Z0-9]{1,10})`"
    matches = re.findall(pattern, answer)

    section = re.findall(
        r"(?:Relevant Files?:)([\s\S]*?)(?:\n\n|$)",
        answer,
        flags=re.IGNORECASE,
    )

    if section:
        paths = re.findall(
            r"[`\-\*]?\s*([^\s`\n]+\.[a-zA-Z0-9]{1,10})",
            section[0],
        )
        matches.extend(paths)

    seen: set[str] = set()
    result: list[str] = []

    for match in matches:
        cleaned = match.strip().strip(".,;:()")

        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)

    return result[:5]


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
    """

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question cannot be empty.")

    if not isinstance(repo_context, str):
        raise TypeError("repo_context must be a string.")

    messages: list[dict] = [
        {
            "role": "system",
            "content": (
                f"{SYSTEM_PROMPT}\n\n"
                "--- REPOSITORY CONTEXT ---\n\n"
                f"{repo_context[:8000]}"
            ),
        }
    ]

    # --------------------------------------------------
    # ADD RECENT CHAT HISTORY
    # --------------------------------------------------

    for msg in (chat_history or [])[-6:]:
        if not isinstance(msg, dict):
            continue

        role = msg.get("role")
        content = msg.get("content")

        if (
            role in ("user", "assistant")
            and isinstance(content, str)
            and content.strip()
        ):
            messages.append(
                {
                    "role": role,
                    "content": content,
                }
            )

    # --------------------------------------------------
    # ADD CURRENT QUESTION
    # --------------------------------------------------

    messages.append(
        {
            "role": "user",
            "content": question.strip(),
        }
    )

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

        relevant_files = _extract_relevant_files(answer)

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
