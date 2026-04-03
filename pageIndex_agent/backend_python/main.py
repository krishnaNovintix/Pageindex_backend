"""
PageIndex Python Backend
Equivalent of the Node.js backend/index.js.

Start with:
    uvicorn main:app --reload --port 3001

Or directly:
    python main.py
"""

import os
import time
import datetime
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
# Explicitly load the .env located in the pageIndex_agent root (parent of backend_python)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from database import connect_db, close_db
from routes.documents    import router as documents_router
from routes.chat         import router as chat_router
from routes.index_route  import router as index_router
from routes.conversations import router as conversations_router

_START_TIME = time.time()


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="PageIndex Backend",
    description="Python backend for PageIndex — document registry, chat proxy, and conversation history.",
    version="1.0.0",
    lifespan=lifespan,
)


# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["Content-Type", "Authorization"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_credentials=False,
)


# ── Request logger ────────────────────────────────────────────────────────────

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


# ── Global error handler ──────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    print(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(documents_router,    prefix="/api/documents")
app.include_router(chat_router,         prefix="/api/chat")
app.include_router(index_router,        prefix="/api/index")
app.include_router(conversations_router, prefix="/api/conversations")


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "PageIndex Backend",
        "uptime": round(time.time() - _START_TIME, 2),
    }


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", "3001"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
