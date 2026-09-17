import os
import re
import logging

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is missing. Set it in your environment variables."
    )

client = Groq(api_key=GROQ_API_KEY)

MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """You are an expert software engineer and codebase guide.
You have been given the source code and structure of a GitHub repository.
Your job is to help NEW DEVELOPERS understand this codebase quickly.

Guidelines:
- Answer clearly and concisely.
- Always mention EXACT file paths when referring to code.
- If asked about architecture, explain the high-level flow first, then details.
- If you reference code, use markdown code blocks.
- At the end of every answer, list 1-3 relevant file paths under
  "📁 Relevant Files:".
- Be friendly but precise — you are a senior developer helping a junior.

You ONLY answer questions related to the provided repository.
If asked something unrelated, politely redirect.
"""


def _extract_relevant_files(answer: str) -> list[str]:
    """Extract likely file paths mentioned in the AI response."""

    pattern = r"`([^`]+\.[a-zA-Z]{1,6})`"
    matches = re.findall(pattern, answer)

    section = re.findall(
        r"(?:Relevant Files?:)([\s\S]*?)(?:\n\n|$)",
        answer,
        flags=re.IGNORECASE,
    )

    if section:
        paths = re.findall(
            r"[`\-\*]?\s*([^\s`\n]+\.[a-zA-Z]{1,6})",
            section[0],
        )
        matches.extend(paths)

    seen: set[str] = set()
    result: list[str] = []

    for match in matches:
        cleaned = match.strip().strip(".,;:")
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)

    return result[:5]


def get_ai_response(
    question: str,
    repo_context: str,
    chat_history: list[dict],
) -> dict:
    """
    Generate a repository-grounded response using Groq.
    """

    if not question or not question.strip():
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

    # Add recent conversation history.
    for msg in (chat_history or [])[-6:]:
        if not isinstance(msg, dict):
            continue

        role = msg.get("role")
        content = msg.get("content")

        if role in ("user", "assistant") and isinstance(content, str):
            messages.append(
                {
                    "role": role,
                    "content": content,
                }
            )

    # Add the current question.
    messages.append(
        {
            "role": "user",
            "content": question.strip(),
        }
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_completion_tokens=1024,
        )

        answer = response.choices[0].message.content

        if not answer:
            answer = "Sorry, I couldn't generate a response."

        relevant_files = _extract_relevant_files(answer)

        return {
            "answer": answer,
            "relevant_files": relevant_files,
        }

    except Exception:
        # Logs the traceback without printing the API key.
        logger.exception(
            "Groq API request failed. Model: %s",
            MODEL,
        )
        raise
