import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are an expert software engineer and codebase guide.
You have been given the full source code and structure of a GitHub repository.
Your job is to help NEW DEVELOPERS understand this codebase quickly.

Guidelines:
- Answer clearly and concisely
- Always mention EXACT file paths when referring to code (e.g. `src/auth/login.ts`)
- If asked about architecture, explain the high-level flow first, then details
- If you reference code, use markdown code blocks
- At the end of every answer, list 1-3 relevant file paths under "📁 Relevant Files:"
- Be friendly but precise — you are a senior dev helping a junior

You ONLY answer questions related to the provided repository. If asked something unrelated, politely redirect.
"""


def _extract_relevant_files(answer: str) -> list[str]:
    pattern = r"`([^`]+\.[a-zA-Z]{1,6})`"
    matches = re.findall(pattern, answer)
    section = re.findall(r"(?:Relevant Files?:)([\s\S]*?)(?:\n\n|$)", answer)
    if section:
        paths = re.findall(r"[`\-\*]?\s*([^\s`\n]+\.[a-zA-Z]{1,6})", section[0])
        matches.extend(paths)
    seen: set[str] = set()
    result: list[str] = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result[:5]


def get_ai_response(question: str, repo_context: str, chat_history: list[dict]) -> dict:
    messages: list[dict] = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n---\n\n{repo_context}"},
    ]
    for msg in chat_history[-6:]:
        if msg["role"] in ("user", "assistant"):
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=1024,
    )

    answer = response.choices[0].message.content or "Sorry, I couldn't generate a response."
    relevant_files = _extract_relevant_files(answer)

    return {
        "answer": answer,
        "relevant_files": relevant_files,
<<<<<<< HEAD
    }
=======
    }
>>>>>>> eade00dfe17ef9cfe30c002f6a61978f4f720ec6
