# 🧠 Code-Pulse — AI-Powered Codebase Intelligence Platform

> **"Stop reading code line-by-line. Let AI explain it to you."**

Code-Pulse is an AI-powered full-stack platform that acts as your personal **Technical Consultant & Codebase Architect**. Drop in any GitHub repository — and get instant, intelligent insights about the code structure, logic, and architecture — without manual review.

---

## 🚀 Live Demo

🔗 **[Try Code-Pulse Live →](https://code-pulse-orcin.vercel.app/)**
📁 **[View Source Code →](https://github.com/ag8615340-bit/code-pulse)**

---

## ✨ What It Does

| Feature | Description |
|---|---|
| 🔍 **Codebase Analysis** | Understands your entire repository structure at a glance |
| 🤖 **AI Technical Consultant** | Provides high-level operational insights without manual code review |
| 🧭 **Developer Onboarding** | Acts as an automated mentor — explains architecture & function logic to new devs |
| 📊 **Logic Auditing** | Identifies patterns, bottlenecks, and architectural decisions in the code |
| ⚡ **Instant Summaries** | No more reading 1000 lines — get the "what & why" in seconds |

---

## 🛠️ Tech Stack

**Backend**
- 🐍 Python + FastAPI
- 🤖 Groq API (Llama 3.3) — LLM Engine
- 🐙 GitHub API — Repository fetching

**Frontend**
- ⚛️ JavaScript (ES6+)
- 🎨 CSS3 with Advanced Animations

**Deployment**
- ▲ Vercel (Frontend)
- 🟢 Render (Backend)

---

## 📁 Project Structure

```
code-pulse/
├── backend/          # FastAPI server + Groq LLM integration
├── frontend/         # JavaScript UI + CSS animations
├── src/              # Core logic modules
└── .gitignore
```

---

## ⚙️ How To Run Locally

### 1. Clone the Repository
```bash
git clone https://github.com/ag8615340-bit/code-pulse.git
cd code-pulse
```

### 2. Backend Setup
```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file:
```env
GROQ_API_KEY=your_groq_api_key_here
GITHUB_TOKEN=your_github_token_here
```

Start the server:
```bash
uvicorn main:app --reload
```

### 3. Frontend Setup
```bash
cd frontend
# Open index.html in your browser
# OR use Live Server extension in VS Code
```

---

## 🔑 Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Your Groq API key (get it at console.groq.com) |
| `GITHUB_TOKEN` | GitHub Personal Access Token (for private repos) |

---

## 💡 Use Cases

- **Engineering Managers** — Audit codebases without diving into code
- **New Developers** — Understand an unfamiliar repo in minutes
- **Technical Interviews** — Analyze open-source projects quickly
- **Code Reviews** — Get a high-level summary before deep review

---

## 🤝 Connect with the Builder

**Jay Gupta** — AI Full-Stack Developer | Solutions Architect

- 📧 [ak6145117@gmail.com](mailto:ak6145117@gmail.com)
- 💼 [LinkedIn](https://www.linkedin.com/in/jay-gupta-6959472a3/)
- 🐙 [GitHub](https://github.com/ag8615340-bit)

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

<p align="center">Built with ❤️ and Llama 3.3 by Jay Gupta</p>
