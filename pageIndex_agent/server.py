import os
import sys
import time
import datetime
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
import agentops
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

# Alias GEMINI_API_KEY → GOOGLE_API_KEY so langchain_google_genai finds it
if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Make backend_python/ importable so its modules (database, routes.*) resolve
# without moving any files.
# ---------------------------------------------------------------------------
_BACKEND = Path(__file__).parent / "backend_python"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# Backend imports (database + route routers)
from database import connect_db, close_db
from routes.documents    import router as documents_router
from routes.chat         import router as chat_router
from routes.index_route  import router as index_router
from routes.conversations import router as conversations_router

# Agent routers
from Agents.Page_index.router   import router as pageindex_router
from Agents.slack_agent.router  import router as mcp_router
from Agents.Orchestrator.router import router as orchestrator_router
from Agents.Summarization.router import router as summarization_router
from Agents.pageindex_api.router import router as pageindex_api_router

# ---------------------------------------------------------------------------
# AgentOps — initialise once for the whole process
# ---------------------------------------------------------------------------
agentops.init(
    api_key=os.getenv("AGENTOPS_API_KEY"),
    auto_start_session=False,
    tags=["pageindex-agent", "production"],
)

# Disable AgentOps' LangGraph auto-instrumentation — it monkey-patches
# StateGraph.add_node() in a way that breaks ToolNode signature inspection.
from agentops.instrumentation.agentic.langgraph.instrumentation import LanggraphInstrumentor
LanggraphInstrumentor().uninstrument()

# ---------------------------------------------------------------------------
# Lifespan — connect / disconnect MongoDB around the server process
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
_START_TIME = time.time()

app = FastAPI(
    title="PageIndex Server",
    description=(
        "Unified server: LangGraph agents, PageIndex core API, "
        "document registry, conversation history."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow the Next.js frontend (any origin for dev; tighten for prod)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["Content-Type", "Authorization"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_credentials=False,
)

# ---------------------------------------------------------------------------
# Request logger
# ---------------------------------------------------------------------------
@app.middleware("http")
async def request_logger(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    ms = int((time.time() - start) * 1000)
    print(
        f"{datetime.datetime.utcnow().isoformat()} | "
        f"{request.method} {request.url.path} → {response.status_code} ({ms}ms)"
    )
    return response

# ---------------------------------------------------------------------------
# Backend routes  (/api/*)
# ---------------------------------------------------------------------------
app.include_router(documents_router,     prefix="/api/documents")
app.include_router(chat_router,          prefix="/api/chat")
app.include_router(index_router,         prefix="/api/index")
app.include_router(conversations_router, prefix="/api/conversations")

# ---------------------------------------------------------------------------
# Agent routes
# ---------------------------------------------------------------------------
app.include_router(pageindex_router)       # POST /pageindex/run
app.include_router(mcp_router)             # POST /mcp/run
app.include_router(orchestrator_router)    # POST /orchestrator/run
app.include_router(summarization_router)   # POST /summarization/run
app.include_router(pageindex_api_router)   # POST /pageindex-api/index  /retrieve

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "PageIndex Server",
        "uptime": round(time.time() - _START_TIME, 2),
    }

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("server:app", port=port, reload=False)
