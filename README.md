# PageIndex — Backend

The backend is composed of **two FastAPI servers** that work together:

| Server | Entry point | Default port | Role |
|---|---|---|---|
| **REST API** | `pageIndex_agent/backend_python/main.py` | `3001` | Document registry, conversation history, chat proxy |
| **Agent Server** | `pageIndex_agent/server.py` | `8001` | LangGraph agents: Orchestrator, Page Index, Summarization, Slack MCP |

---

## Tech Stack

- **Python 3.11+**
- **FastAPI** + **Uvicorn**
- **LangGraph** — agent graph orchestration
- **LiteLLM** / **langchain-google-genai** — LLM calls (Gemini)
- **Motor** — async MongoDB driver
- **AgentOps** — agent session tracing
- **PyMuPDF / PyPDF2** — PDF parsing
- **Slack SDK** — Slack MCP integration
- **python-dotenv** — environment variable loading

---

## Project Structure

```
backend/
├── requirements.txt                  # Agent server dependencies
└── pageIndex_agent/
    ├── .env                          # ← single env file for both servers
    ├── server.py                     # Agent server (port 8001)
    ├── backend_python/               # REST API server (port 3001)
    │   ├── main.py
    │   ├── database.py               # Motor MongoDB singleton
    │   ├── utils.py
    │   ├── requirements.txt          # REST API dependencies
    │   ├── documents/                # Uploaded PDF storage
    │   └── routes/
    │       ├── documents.py          # CRUD + file upload
    │       ├── chat.py               # Proxy → Orchestrator agent
    │       ├── conversations.py      # Conversation history
    │       └── index_route.py        # Trigger indexing
    ├── pageindex/                    # Core indexing library
    │   ├── page_index.py
    │   ├── retrieve.py
    │   └── client.py
    └── Agents/
        ├── Orchestrator/             # Top-level multi-task agent
        ├── Page_index/               # PDF indexing agent
        ├── Summarization/            # Document summarization agent
        ├── slack_agent/              # Slack MCP agent
        └── pageindex_api/            # Internal API router
```

---

## Prerequisites

- **Python 3.11+**
- **MongoDB** (local or Atlas — provide URI in `.env`)
- A **Gemini API key** (or compatible LLM)

---

## Environment Variables

Create `pageIndex_agent/.env` (one file, loaded by both servers):

```env
# MongoDB
MONGO_URI=mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/<dbname>

# LLM
GEMINI_API_KEY=your_gemini_api_key
# GOOGLE_API_KEY is auto-aliased from GEMINI_API_KEY if not set

# Agent server base URL (used by the REST API chat proxy)
AGENT_URL=http://localhost:8001

# AgentOps (optional — for tracing)
AGENTOPS_API_KEY=your_agentops_key

# Storage overrides (optional)
DOCUMENTS_DIR=/absolute/path/to/documents
RESULTS_DIR=/absolute/path/to/results

# Ports (optional, defaults shown)
PORT=3001
```

---

## Installation

```bash
# Install agent server dependencies
cd backend
pip install -r requirements.txt

# Install REST API dependencies
pip install -r pageIndex_agent/backend_python/requirements.txt
```

---

## Running

Both servers must be running for the full stack to work.

**1. REST API (port 3001)**
```bash
cd backend/pageIndex_agent/backend_python
uvicorn main:app --reload --port 3001
```

**2. Agent Server (port 8001)**
```bash
cd backend/pageIndex_agent
python server.py
```

---

## API Reference

### REST API — `http://localhost:3001`

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/documents` | List all documents |
| `POST` | `/api/documents/upload` | Upload a PDF file |
| `GET` | `/api/documents/{id}` | Get document by ID |
| `PUT` | `/api/documents/{id}` | Update document metadata |
| `DELETE` | `/api/documents/{id}` | Delete document record |
| `POST` | `/api/documents/{id}/mark-indexed` | Mark document as indexed |
| `POST` | `/api/chat` | Send message → Orchestrator |
| `POST` | `/api/index` | Trigger document indexing |
| `GET` | `/api/conversations` | List conversations |
| `GET` | `/api/conversations/{id}` | Get conversation by ID |

### Agent Server — `http://localhost:8001`

| Method | Path | Description |
|---|---|---|
| `POST` | `/orchestrator/run` | Run multi-task orchestration |
| `POST` | `/pageindex/run` | Run page indexing |
| `POST` | `/summarization/run` | Summarize a document |
| `POST` | `/slack/run` | Slack agent action |

---

## How It Works

```
Frontend (port 3000)
    │
    ▼
REST API  (port 3001)  ──── MongoDB (Motor)
    │
    ▼  POST /orchestrator/run
Agent Server (port 8001)
    │
    ├── Orchestrator (LangGraph)
    │       ├── Page_index agent  ──── PyMuPDF / pageindex/
    │       ├── Summarization agent
    │       └── Slack MCP agent
    │
    └── LiteLLM → Gemini API
```

1. The frontend uploads a PDF → REST API saves it to disk and registers it in MongoDB.
2. The user triggers indexing → REST API calls the Agent Server's Page Index agent, which parses the PDF and builds a structural JSON index.
3. During chat, the REST API proxies the message + PDF paths to the Orchestrator agent.
4. The Orchestrator routes sub-tasks (retrieval, summarization, etc.) across specialised agents and returns a final answer.
