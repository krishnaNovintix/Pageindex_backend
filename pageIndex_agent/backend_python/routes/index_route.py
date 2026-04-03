"""
/api/index route

POST / — index a PDF in-process via the PageIndex core and return the structure path.

Body:   { pdf_path, structure_path? }
Return: { response, structure_path }
"""

import json
import os
from pathlib import Path

import agentops
from agentops import TraceState
from fastapi import APIRouter, HTTPException
from asyncio import get_event_loop
from concurrent.futures import ThreadPoolExecutor

import pageIndex_agent.pageindex.utils as pi_utils
from pageIndex_agent.pageindex.page_index import page_index_main
from pageIndex_agent.pageindex.utils import ConfigLoader

router = APIRouter()

_BASE        = Path(__file__).resolve().parent.parent
_RESULTS_DIR = Path(os.getenv("RESULTS_DIR", str(_BASE / "results")))

_executor = ThreadPoolExecutor(max_workers=2)


def _count_nodes(tree: list) -> int:
    count = 0
    for node in tree:
        count += 1
        if node.get("nodes"):
            count += _count_nodes(node["nodes"])
    return count


@router.post("/")
async def index_document(body: dict):
    pdf_path = (body.get("pdf_path") or "").strip()
    if not pdf_path:
        raise HTTPException(status_code=400, detail="pdf_path is required")

    pdf_path = os.path.abspath(pdf_path)
    if not os.path.isfile(pdf_path):
        raise HTTPException(status_code=404, detail=f"PDF not found: {pdf_path}")

    # Use the provided structure_path or derive one
    structure_path = (body.get("structure_path") or "").strip()
    if not structure_path:
        stem = Path(pdf_path).stem
        structure_path = str(_RESULTS_DIR / f"{stem}_structure.json")

    output_dir = Path(structure_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    trace = agentops.start_trace(
        trace_name="pdf_indexing",
        tags=["indexing", "pdf", Path(pdf_path).name],
    )
    try:
        opt = ConfigLoader().load(None)

        # page_index_main is CPU-bound/sync — run in thread pool to avoid blocking
        loop = get_event_loop()
        result = await loop.run_in_executor(_executor, page_index_main, pdf_path, opt)

        pdf_stem = Path(pdf_path).stem
        output_path = output_dir / f"{pdf_stem}_structure.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        agentops.end_trace(trace, end_state=TraceState.SUCCESS)
        return {
            "response": f"Indexed successfully. Structure saved to {output_path}",
            "structure_path": str(output_path),
        }

    except HTTPException:
        agentops.end_trace(trace, end_state=TraceState.ERROR)
        raise
    except Exception as exc:
        agentops.end_trace(trace, end_state=TraceState.ERROR)
        raise HTTPException(status_code=500, detail=f"Indexing failed: {exc}")
