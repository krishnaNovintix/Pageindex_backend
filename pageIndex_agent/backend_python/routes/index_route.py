"""
/api/index route

POST / — index a PDF via the PageIndex API and return the structure path.

Body:   { pdf_path, structure_path? }
Return: { response, structure_path }
"""

import os
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()

AGENT_URL = os.getenv("AGENT_URL", "http://localhost:8001")

_BASE        = Path(__file__).resolve().parent.parent
_RESULTS_DIR = Path(os.getenv("RESULTS_DIR", str(_BASE / "results")))


@router.post("/")
async def index_document(body: dict):
    pdf_path = (body.get("pdf_path") or "").strip()
    if not pdf_path:
        raise HTTPException(status_code=400, detail="pdf_path is required")

    # Use the provided structure_path (set at upload time) or derive one
    structure_path = (body.get("structure_path") or "").strip()
    if not structure_path:
        stem = Path(pdf_path).stem
        structure_path = str(_RESULTS_DIR / f"{stem}_structure.json")

    output_dir = str(Path(structure_path).parent)

    try:
        # Call /pageindex-api/index directly — avoids LLM path parsing on Windows
        async with httpx.AsyncClient(timeout=600.0) as client:
            resp = await client.post(
                f"{AGENT_URL}/pageindex-api/index",
                json={"pdf_path": pdf_path, "output_dir": output_dir},
            )

        data = resp.json()

        if not resp.is_success:
            raise HTTPException(
                status_code=resp.status_code,
                detail=data.get("detail") or "Indexing failed",
            )

        # Use the actual structure_path returned by the API (most authoritative)
        actual_structure_path = data.get("structure_path") or structure_path
        return {"response": data.get("message"), "structure_path": actual_structure_path}

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="PageIndex agent is not running. Start it with: python server.py",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
