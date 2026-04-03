"""
/api/chat route

POST / — proxy the user message to the Orchestrator agent and return its response.

Body:   { message, pdf_path, structure_path }
Return: { response, task_results }
"""

import os
import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()

AGENT_URL = os.getenv("AGENT_URL", "http://localhost:8001")


@router.post("/")
async def chat(body: dict):
    message        = (body.get("message") or "").strip()
    pdf_path       = (body.get("pdf_path") or "").strip()
    structure_path = (body.get("structure_path") or "").strip()

    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    if not pdf_path:
        raise HTTPException(status_code=400, detail="pdf_path is required")
    if not structure_path:
        raise HTTPException(
            status_code=400,
            detail="structure_path is required. Index the document first.",
        )

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{AGENT_URL}/orchestrator/run",
                json={"message": message, "pdf_path": pdf_path, "structure_path": structure_path},
            )

        data = resp.json()

        if not resp.is_success:
            raise HTTPException(
                status_code=resp.status_code,
                detail=data.get("detail") or "Orchestrator returned an error",
            )

        return {
            "response": data.get("response"),
            "task_results": data.get("task_results") or [],
        }

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Agent server is not running. Start it with: python server.py",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
