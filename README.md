# 🤖 AI Incident Management & Knowledge Assistant

> **Enterprise-grade AI-powered IT Incident Management Platform** built with FastAPI, LangGraph, RAG, ChromaDB, and Streamlit. Supports multi-tier automated troubleshooting (L1 → L2 → L3 → Human Handoff), multilingual voice interface with 30-language selection, guardrails validation, delete-ticket, and comprehensive analytics.

---

## 📑 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [Technology Stack](#technology-stack)
5. [Project Structure](#project-structure)
6. [Installation](#installation)
7. [Configuration](#configuration)
8. [Running the Application](#running-the-application)
9. [Voice & Multilingual Support](#voice--multilingual-support)
10. [Input Guardrails](#input-guardrails)
11. [AI Workflow](#ai-workflow)
12. [Analytics & Metrics](#analytics--metrics)
13. [Admin Guide](#admin-guide)
14. [User Guide](#user-guide)
15. [API Reference](#api-reference)
16. [Evaluation](#evaluation)
17. [Testing](#testing)
18. [Acceptance Test Checklist](#acceptance-test-checklist)
19. [Troubleshooting](#troubleshooting)
20. [Security](#security)

---

## Overview

The **AI Incident Management** platform automates IT helpdesk workflows using a multi-tier AI pipeline:

| Tier | Description |
|------|-------------|
| **L1** | First-line automated troubleshooting using RAG (knowledge base search) |
| **L2** | Advanced analysis using gathered diagnostics |
| **L3** | Expert-level inference and deep system analysis |
| **Human Handoff** | Escalation to live agents when AI cannot resolve |

Users submit incidents in **any language** via text or **voice (microphone)**. The AI responds in the same language. All conversations are persisted and fully auditable.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER / ADMIN BROWSER                          │
│           (Chrome recommended for Voice features)                │
└────────────────────────┬────────────────────────────────────────┘
                         │  HTTP (localhost:8501)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                STREAMLIT FRONTEND  (Port 8501)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │  Login/Auth  │  │ User Pages   │  │    Admin Pages      │   │
│  │  Guardrails  │  │ New Incident │  │  Dashboard/Analytic │   │
│  │  Voice Input │  │ History      │  │  Handoffs/Users     │   │
│  │  TTS Output  │  │ Details      │  │  Evaluation/System  │   │
│  └──────────────┘  └──────────────┘  └─────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │  REST API (localhost:8000)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 FASTAPI BACKEND  (Port 8000)                     │
│                                                                   │
│  ┌────────────┐  ┌────────────────┐  ┌──────────────────────┐  │
│  │  /auth     │  │  /incidents    │  │  /admin              │  │
│  │  register  │  │  create        │  │  dashboard           │  │
│  │  login     │  │  resume        │  │  analytics           │  │
│  │  check-    │  │  history       │  │  handoffs            │  │
│  │  user      │  │  stats         │  │  users / eval        │  │
│  └─────┬──────┘  └───────┬────────┘  └──────────────────────┘  │
│        │                 │                                        │
│        │         ┌───────▼──────────────────────────────────┐   │
│        │         │     LANGGRAPH WORKFLOW ENGINE             │   │
│        │         │                                           │   │
│        │         │  RAG → L1 → [Verify] → Diagnostics        │   │
│        │         │            → Routing → L2 → [Verify]      │   │
│        │         │                       → L3 → [Verify]     │   │
│        │         │                              → Handoff     │   │
│        │         └──────────┬───────────────────────────────┘   │
│        │                    │                                     │
│  ┌─────▼──────┐   ┌─────────▼────────┐  ┌──────────────────┐  │
│  │  SQLite DB │   │  ChromaDB        │  │  OpenAI LLM      │  │
│  │  (SQLAlch) │   │  Vector Store    │  │  gpt-4o-mini     │  │
│  │  Users     │   │  Knowledge Base  │  │  (or Ollama)     │  │
│  │  Incidents │   │  7 guides        │  └──────────────────┘  │
│  │  Handoffs  │   └──────────────────┘                         │
│  └────────────┘                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### LangGraph Incident Workflow

```
START ──► RAG (ChromaDB) ──► L1 Resolution
                                    │
                             ┌──────▼──────┐
                             │  User asked:│
                             │ "Resolved?" │
                             └──────┬──────┘
                              YES ──┤── FINAL RESPONSE ──► RESOLVED
                              NO ───┤
                                    ▼
                              Diagnostics (up to 3 rounds)
                                    │
                              Routing Decision
                                    │
                     ┌──────────────┼──────────────────┐
                     ▼             ▼                   ▼
               L2 Resolution  MORE_DIAGNOSTICS   HUMAN_HANDOFF
                     │
              ┌──────▼──────┐
              │  "Resolved?"│
              └──────┬──────┘
               YES ──┤── FINAL RESPONSE ──► RESOLVED (L2)
               NO ───┤
                     ▼
               L3 Expert Resolution
                     │
              ┌──────▼──────┐
              │  "Resolved?"│
              └──────┬──────┘
               YES ──┤── FINAL RESPONSE ──► RESOLVED (L3)
               NO ───┤
                     ▼
              HUMAN HANDOFF ──► ESCALATED
```

---

## Features

### 👤 User Features
| Feature | Description |
|---------|-------------|
| 🔐 Secure Registration | Username + email + password (bcrypt hashed) |
| 🎯 Smart Login Validation | Shows "Please register first" if user not in DB |
| 🤖 AI Troubleshooting | Multi-tier L1 → L2 → L3 automated resolution |
| 🎤 Voice Input | Browser microphone (Web Speech API), any language |
| 🔊 Text-to-Speech | AI answers are read aloud in the detected language |
| 💬 Chat Interface | ChatGPT-style conversation with history |
| 🌍 Multilingual | Supports English, Spanish, French, German, Hindi, Arabic, Chinese, Japanese, Korean, Russian, and more |
| 📋 Incident History | Persistent history survives restarts |
| 🔍 Incident Details | Full lifecycle view with conversation timeline |
| 🛡️ Guardrails | Prompt injection, jailbreak, profanity detection |

### 🎛️ Admin Features
| Feature | Description |
|---------|-------------|
| 📊 Extended Dashboard | 12 KPI metrics across 3 metric rows |
| 🚨 Handoff Management | View, assign, resolve escalated incidents |
| 📋 All Incidents | Filter by status, user, resolution level |
| 📈 Analytics | 6 charts including funnel, pie, bar, time-series |
| 🧪 Model Evaluation | DeepEval with 5 RAG metrics |
| 👥 User Management | Activate/deactivate users, promote to admin |
| ⚙️ System Health | Database, ChromaDB, LLM, RAG status |

---

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend | Python, FastAPI, Uvicorn | Python 3.12+ |
| Database | SQLAlchemy + SQLite | SQLAlchemy 2.0+ |
| AI/LLM | LangChain, LangGraph, OpenAI | gpt-4o-mini |
| Vector DB | ChromaDB | 0.5+ |
| Embeddings | OpenAI text-embedding-3-small | — |
| Frontend | Streamlit | 1.38+ |
| Voice | Web Speech API (browser-native) | — |
| Evaluation | DeepEval | 1.0+ |
| Auth | JWT (python-jose) + bcrypt | — |
| Charts | Plotly | 5.20+ |
| Guardrails | Regex patterns (server + client) | — |

---

## Project Structure

```
AI_Incident_Management/
├── backend/
│   ├── api/
│   │   ├── auth.py           # /auth/login, /register, /check-user
│   │   ├── incidents.py      # /incidents CRUD & workflow
│   │   ├── admin.py          # /admin/* (dashboard, analytics, users)
│   │   ├── evaluation.py     # /admin/evaluations
│   │   ├── deps.py           # JWT dependency injection
│   │   ├── main.py           # FastAPI app, lifespan, CORS
│   │   └── schemas.py        # Pydantic models (+ server-side guardrails)
│   ├── database/
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   ├── connection.py     # DB engine / SessionLocal
│   │   └── repository.py     # All CRUD operations
│   ├── graph/
│   │   ├── state.py          # LangGraph IncidentState TypedDict
│   │   ├── nodes.py          # RAG, L1, L2, L3, Handoff, Persist nodes
│   │   ├── routing.py        # Conditional edge routing functions
│   │   ├── workflow.py       # build_workflow() + get_workflow()
│   │   └── prompts.py        # LLM prompts (multilingual instruction)
│   ├── rag/
│   │   ├── vectorstore.py    # ChromaDB setup
│   │   ├── embeddings.py     # Embedding model factory
│   │   ├── loader.py         # Document loader
│   │   └── retriever.py      # Similarity search
│   ├── services/
│   │   ├── auth_service.py   # hash_password, verify, JWT
│   │   ├── incident_service.py # create_new_incident, resume_incident
│   │   ├── analytics_service.py # get_admin_analytics()
│   │   ├── memory_service.py  # LangGraph thread memory
│   │   └── evaluation_service.py # DeepEval runner
│   └── config.py             # Pydantic settings (env vars)
├── frontend/
│   ├── app.py                # Entry point: login, guardrails, routing
│   ├── pages/
│   │   ├── user_dashboard.py
│   │   ├── new_incident.py   # Voice input + TTS + guardrails
│   │   ├── incident_history.py
│   │   ├── incident_details.py
│   │   ├── admin_dashboard.py  # 12-metric dashboard
│   │   ├── analytics.py        # Extended analytics + funnel chart
│   │   ├── human_handoffs.py
│   │   ├── all_incidents.py
│   │   ├── admin_incident_detail.py
│   │   ├── evaluation.py
│   │   ├── users.py
│   │   └── system.py
│   ├── components/
│   │   ├── chat.py           # Conversation render
│   │   ├── charts.py         # Plotly chart helpers
│   │   ├── metric_card.py    # KPI card component
│   │   ├── incident_card.py  # Incident list card
│   │   └── sidebar.py        # User/Admin sidebars
│   └── utils/
│       ├── api.py            # All backend API calls (+ check_user_exists)
│       ├── auth.py           # Token/session helpers
│       └── session.py        # Page navigation helpers
├── evaluation/
│   ├── dataset.json          # 11 realistic test cases
│   ├── run_evaluation.py     # DeepEval runner
│   └── metrics.py            # Metric definitions
├── data/
│   └── knowledge_base/       # Add .txt/.pdf/.md/.docx here
├── artifacts/
│   ├── chroma_db/            # Persistent vector store
│   └── incidents.db          # SQLite database
├── tests/                    # Pytest test suite
├── .env.example              # Environment template
├── requirements.txt
├── run.py                    # Convenience runner CLI
└── README.md
```

---

## Installation

### Prerequisites
- **Python 3.12+** (`python --version`)
- **OpenAI API key** (or Ollama for local inference)
- **Google Chrome** (recommended — for voice features)

### Step 1: Clone / Navigate to Project
```bash
cd AI-Incident-Management-main
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## Configuration

### Step 4: Create .env File
```bash
cp .env.example .env
```

Edit `.env` and set:

```env
# Required
OPENAI_API_KEY=sk-your-openai-api-key-here
SECRET_KEY=your-random-secret-key-here

# Optional (defaults shown)
LLM_MODEL=gpt-4o-mini
LLM_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

# Admin defaults
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@company.com

# Server
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
FRONTEND_PORT=8501
```

**Generate a secure SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Running the Application

### Step 5: Initialize Database
```bash
python run.py init-db
```

### Step 6: Create Admin Account
```bash
python run.py setup-admin
```

> **Tip:** If you skip step 6, the backend auto-creates an admin on first start and prints the password to the console. **Save it immediately.**

### Step 7: Build Vector Store (ChromaDB)
```bash
python run.py init-rag
```
This only runs once. The vector store persists to `artifacts/chroma_db/`.

### Step 8: Start Backend (Terminal 1)
```bash
python run.py backend
# OR directly:
uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8000
```

### Step 9: Start Frontend (Terminal 2)
```bash
python run.py frontend
# OR directly:
streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
```

Open: **http://localhost:8501**

---

## Voice & Multilingual Support

### 🎤 Speech-to-Text (Voice Input)
- Uses the **Web Speech API** built into Chrome/Edge
- Click the **🎤 Speak** button on the New Incident page
- Speak in **any language** — the transcript is auto-copied to clipboard
- Paste it into the text area to submit
- **No API key required** — runs entirely in the browser

### 🔊 Text-to-Speech (AI Response Playback)
- Each AI response includes a **🔊 Listen** button
- AI detects the language from your query
- The TTS voice matches the response language automatically
- Uses the **Web Speech Synthesis API** (browser-native)

### 🌍 Supported Languages (auto-detected)
English, Spanish, French, German, Italian, Portuguese, Arabic, Chinese, Japanese, Korean, Hindi, Russian — and any other language supported by your browser's Speech API.

### How Multilingual Works
1. User types or speaks in their language (e.g., Spanish)
2. The AI detects the language from the query text
3. LLM prompts include an instruction: *"Respond in the same language as the user's query"*
4. All AI responses (L1/L2/L3) are returned in the same language
5. The 🔊 Listen button plays the response in the correct voice/language

---

## Input Guardrails

The platform enforces security guardrails at **two layers**:

### Frontend Guardrails (frontend/app.py, frontend/pages/new_incident.py)
| Check | Description |
|-------|-------------|
| Empty input | Blocked with friendly message |
| Min length (3 chars) | Prevents junk submissions |
| Max length (5000 chars) | Prevents abuse |
| Prompt injection detection | Blocks "ignore previous instructions", "jailbreak", etc. |
| SQL injection patterns | Blocks "DROP TABLE", "DELETE FROM", etc. |
| Script injection | Blocks `<script>` tags |
| Profanity filter | Professional language enforced |
| Email format validation | RFC-compliant regex check |
| Username format validation | Only safe characters allowed |
| Password strength | Minimum 8 characters |
| Password confirmation | Must match on register |

### Backend Guardrails (backend/api/schemas.py)
| Check | Description |
|-------|-------------|
| Query length (server-side) | 3-5000 characters enforced |
| Prompt injection | Regex scan on all incident queries |
| SQL injection | Pattern scan before LLM processing |
| Username length | 3-64 characters |
| Password length | Minimum 8 characters |
| Email uniqueness | Checked before creation |
| Username uniqueness | Checked before creation |
| JWT validation | Every API request validated |
| Ownership enforcement | Users only see their own incidents |

### Login Validation Flow
```
User enters credentials
       │
       ▼
  Check if user exists → [NOT FOUND] → "Please register first"
       │
  [FOUND]
       │
       ▼
  Verify password → [WRONG] → "Incorrect password. Please try again."
       │
  [CORRECT]
       │
       ▼
  Check is_active → [DISABLED] → "Account is disabled"
       │
  [ACTIVE]
       │
       ▼
  Issue JWT → Redirect to Dashboard
```

---

## AI Workflow

### How the LangGraph Pipeline Works

| Node | Input | Output |
|------|-------|--------|
| **RAG** | User query | Retrieved KB documents + context |
| **L1 Resolution** | Query + context | Troubleshooting steps, asks user to verify |
| **Diagnostics** | L1 failure + history | Targeted diagnostic question |
| **Routing Decision** | Diagnostic answers | L2 / MORE_DIAGNOSTICS / HUMAN_HANDOFF |
| **L2 Resolution** | All context | Advanced steps, asks user to verify |
| **L3 Resolution** | All context | Expert analysis, asks user to verify |
| **Human Handoff** | Failure context | Escalation record created |
| **Generate Final Response** | Resolution level | Confirmation message |
| **Persist Incident** | Full state | Saved to SQLite |

### State Management
- Each incident has a unique `thread_id` for LangGraph memory
- `IncidentState` TypedDict carries all data through the graph
- `MemorySaver` checkpoints within-session state
- Database persistence handles cross-session recovery

---

## Analytics & Metrics

### Dashboard Metrics (12 KPIs)
| Row | Metrics |
|-----|---------|
| **Incident Overview** | Total, Resolved, Escalated, In Progress |
| **AI Resolution Tiers** | L1, L2, L3 Resolved, Human Handoff count |
| **Performance Rates** | Resolution %, Escalation %, AI Automation %, Handoff % |

### Analytics Page Charts
| Chart | Description |
|-------|-------------|
| Incidents Over Time | 30-day daily trend line |
| Resolution Level Breakdown | Donut pie (L1/L2/L3/Handoff) |
| Incidents by Status | Bar chart (Resolved/Escalated/In Progress) |
| Incidents by User | Top-10 users bar chart |
| AI Resolution Tier Funnel | Funnel chart showing how incidents flow through tiers |
| Metrics Summary Table | All 11 KPIs in a sortable table |

---

## Admin Guide

### Accessing Admin Functions
1. Login with your admin credentials at http://localhost:8501
2. You are automatically routed to the Admin Dashboard

### Managing Human Handoffs
1. Navigate to **🚨 Human Handoffs**
2. View all escalated incidents with AI confidence scores
3. Click **Take Ownership** to assign to yourself
4. Add notes and click **Mark Resolved**

### User Management
1. Navigate to **👥 Users**
2. View all registered users
3. Toggle user active/inactive status
4. Promote users to admin role

### Running Model Evaluation
1. Navigate to **🧪 Model Evaluation**
2. Click **▶️ Run Evaluation** (requires OPENAI_API_KEY)
3. View 5 RAG metrics: Faithfulness, Answer Relevancy, Contextual Relevancy, Contextual Precision, Contextual Recall

---

## User Guide

### Creating an Account
1. Go to http://localhost:8501
2. Click the **Register** tab
3. Enter username, email, password, confirm password
4. Click **Register**
5. Login using the **Login** tab

### Creating an Incident
1. Click **➕ New Incident** in the sidebar
2. **Optional:** Click **🎤 Speak** to dictate your issue (Chrome required)
3. Type or paste your issue description
4. Click **🚀 Start**

### During AI Troubleshooting
- **When asked "Resolved?"** — click ✅ Yes or ❌ No
- **When asked a diagnostic question** — type (or speak) your answer
- **🔊 Listen button** — have the AI response read aloud in your language
- The AI automatically escalates from L1 → L2 → L3 → Human if needed

### Viewing Incident History
- Click **📋 My Incidents** in the sidebar
- Click any incident to view full conversation history

---

## API Reference

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | None | Backend health check |
| `/auth/register` | POST | None | Create new user |
| `/auth/login` | POST | None | Login, get JWT token |
| `/auth/check-user` | GET | None | Check if username/email exists |
| `/auth/me` | GET | JWT | Get current user profile |
| `/incidents` | POST | JWT | Start new incident (runs L1) |
| `/incidents/{thread_id}/resume` | POST | JWT | Resume incident with user input |
| `/incidents/history` | GET | JWT | List current user's incidents |
| `/incidents/stats` | GET | JWT | Current user's stats |
| `/incidents/{incident_id}` | GET | JWT | Incident detail |
| `/admin/dashboard` | GET | Admin JWT | Dashboard statistics |
| `/admin/analytics` | GET | Admin JWT | Full analytics data |
| `/admin/incidents` | GET | Admin JWT | All incidents (filterable) |
| `/admin/handoffs` | GET | Admin JWT | Human handoff queue |
| `/admin/users` | GET | Admin JWT | All users |
| `/system/health` | GET | Admin JWT | Detailed system status |

---

## Evaluation

The platform uses **DeepEval** to evaluate RAG quality with 5 metrics:

| Metric | Description | Target |
|--------|-------------|--------|
| **Faithfulness** | Are answers grounded in retrieved docs? | > 0.7 |
| **Answer Relevancy** | Does the answer address the question? | > 0.7 |
| **Contextual Relevancy** | Is retrieved context relevant? | > 0.6 |
| **Contextual Precision** | Are retrieved docs precisely relevant? | > 0.6 |
| **Contextual Recall** | Are all relevant docs retrieved? | > 0.6 |

### Run Evaluation
```bash
# Via CLI
python evaluation/run_evaluation.py

# Via Admin UI
# Admin → Model Evaluation → ▶️ Run Evaluation
```

---

## Testing

```bash
# Run all tests
python run.py test

# Individual test files
pytest tests/test_auth.py -v
pytest tests/test_workflow.py -v
pytest tests/test_memory.py -v
pytest tests/test_incidents.py -v
pytest tests/test_evaluation.py -v
```

---

## Acceptance Test Checklist

| # | Action | Expected Result |
|---|--------|----------------|
| 1 | Register new user | ✅ Account created |
| 2 | Login with unregistered email | ⚠️ "Please register first" shown |
| 3 | Login with wrong password | ❌ "Incorrect password" shown |
| 4 | Login with correct credentials | ✅ Routed to dashboard |
| 5 | Submit incident with profanity | ⚠️ Guardrail blocked |
| 6 | Submit incident with "jailbreak" | ⚠️ Injection blocked |
| 7 | Create VPN incident | 🔍 RAG retrieves KB docs |
| 8 | L1 displays steps | Steps + 🔊 Listen button shown |
| 9 | Click 🎤 Speak | Microphone activates (Chrome) |
| 10 | Answer NO to L1 | Diagnostic questions begin |
| 11 | Answer diagnostic questions | No repeated questions |
| 12 | L2 resolution displayed | Advanced steps shown |
| 13 | Answer NO to L2 | L3 begins |
| 14 | Answer NO to L3 | Human handoff created |
| 15 | Check incident status | ESCALATED |
| 16 | Admin sees escalation | Human Handoffs queue shows it |
| 17 | Submit incident in Spanish | AI responds in Spanish |
| 18 | Click 🔊 Listen on Spanish response | TTS speaks Spanish |
| 19 | Restart backend/frontend | Previous incidents still visible |
| 20 | Click old incident | Historical conversation loads |
| 21 | Admin runs DeepEval | 5 metrics calculated |

---

## Troubleshooting

### Backend Won't Start
```bash
# Check Python version (must be 3.12+)
python --version

# Reinstall dependencies
pip install -r requirements.txt

# Check .env file exists
ls .env
```

### ChromaDB Errors
```bash
# Rebuild vector store
python run.py init-rag
```

### "No LLM Configured"
- Set `OPENAI_API_KEY` in `.env`
- Or install Ollama: `ollama pull llama3.2`

### Database Errors
```bash
# Re-initialize database
python run.py init-db
```

### Voice Not Working
- Use **Google Chrome** (required for Web Speech API)
- Ensure microphone permissions are granted in browser
- Check browser console for errors

### Port Already in Use
```bash
# Windows — kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Kill port 8501
netstat -ano | findstr :8501
taskkill /PID <PID> /F
```

---

## Security

| Feature | Implementation |
|---------|---------------|
| Password storage | bcrypt hashed, never plaintext |
| JWT tokens | HS256, 8-hour expiry (configurable) |
| API keys | Environment variables only, never in source |
| User data isolation | Users only access their own incidents (enforced at API) |
| CORS | Restricted to localhost:8501 only |
| Input sanitization | Regex-based prompt injection, SQL injection, XSS prevention |
| Rate limiting | Per-request timeout enforced on all API calls |
| Secret key | Random 32-byte hex string (never use defaults in production) |


---
