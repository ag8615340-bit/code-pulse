from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from github_parser import parse_github_repo
from ai_engine import get_ai_response

load_dotenv()

app = FastAPI(title="Codebase Onboarding Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RepoRequest(BaseModel):
    github_url: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    question: str
    repo_context: str
    chat_history: Optional[List[ChatMessage]] = []

class FileNode(BaseModel):
    name: str
    path: str
    type: str
    children: Optional[List["FileNode"]] = []

FileNode.model_rebuild()

class RepoResponse(BaseModel):
    file_tree: List[FileNode]
    repo_context: str
    readme: str
    repo_name: str

class ChatResponse(BaseModel):
    answer: str
    relevant_files: List[str]

@app.get("/")
def root():
    return {"status": "Codebase Onboarding Assistant is live 🚀"}

@app.post("/api/parse-repo", response_model=RepoResponse)
async def parse_repo(request: RepoRequest):
    try:
        result = parse_github_repo(request.github_url)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse repo: {str(e)}")

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    if not request.repo_context.strip():
        raise HTTPException(status_code=400, detail="Repo context is missing")
    try:
        result = get_ai_response(
            question=request.question,
            repo_context=request.repo_context,
            chat_history=[msg.model_dump() for msg in request.chat_history],
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI engine error: {str(e)}")