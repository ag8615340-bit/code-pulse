import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

MODEL = "openai/gpt-oss-120b"

# Reduced context/history limits to help avoid Groq 413 errors.
MAX_REPO_CONTEXT_CHARS = 3000
MAX_HISTORY_MESSAGES = 2
MAX_HISTORY_MESSAGE_CHARS = 500


SYSTEM_PROMPT = """You are an expert software engineer and codebase guide.
You have been given source code and structure from a GitHub repository.
Your job is to help NEW DEVELOPERS understand this codebase quickly.

Guidelines:
- Answer clearly and concisely
- Always mention EXACT file paths when referring to code
- If asked about architecture, explain the high-level flow first
- If you reference code, use markdown code blocks
- At the end of every answer, list 1-3 relevant file paths under "📁 Relevant Files:"
- Be friendly but precise — you are a senior dev helping a junior
- Use only information supported by the provided repository context
- If information is missing, clearly say you cannot verify it

You ONLY answer questions related to the provided repository.
If asked something unrelated, politely redirect.
"""


def _extract_relevant_files(answer: str) -> list[str]:
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

    for m in matches:
        if m not in seen:
            seen.add(m)
            result.append(m)

    return result[:5]


def get_ai_response(
    question: str,
    repo_context: str,
    chat_history: list[dict],
) -> dict:

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question cannot be empty.")

    if not isinstance(repo_context, str):
        raise TypeError("repo_context must be a string.")

    # Reduce repository context size.
    prepared_context = repo_context[:MAX_REPO_CONTEXT_CHARS]

    messages: list[dict] = [
        {
            "role": "system",
            "content": (
                f"{SYSTEM_PROMPT}\n\n"
                "---\n\n"
                f"{prepared_context}"
            ),
        }
    ]

    # Keep only a small amount of recent chat history.
    if isinstance(chat_history, list):
        for msg in chat_history[-MAX_HISTORY_MESSAGES:]:
            if not isinstance(msg, dict):
                continue

            role = msg.get("role")
            content = msg.get("content")

            if role not in ("user", "assistant"):
                continue

            if not isinstance(content, str) or not content.strip():
                continue

            messages.append({
                "role": role,
                "content": content[:MAX_HISTORY_MESSAGE_CHARS],
            })

    messages.append({
        "role": "user",
        "content": question.strip(),
    })

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=1024,
    )

    answer = (
        response.choices[0].message.content
        or "Sorry, I couldn't generate a response."
    )

    relevant_files = _extract_relevant_files(answer)

    return {
        "answer": answer,
        "relevant_files": relevant_files,
    }
