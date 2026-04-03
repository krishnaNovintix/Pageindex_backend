"""
/api/chat route

POST / — run the Orchestrator agent in-process and return its response.

Body:   { message, pdf_path, structure_path }
Return: { response, task_results }
"""

from fastapi import APIRouter, HTTPException
from Agents.Orchestrator.graph import build_graph
from Agents.Orchestrator.logger import log_request, log_response, log_error, reset_log
import agentops
from agentops import start_trace, end_trace

router = APIRouter()


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

    trace = start_trace(trace_name="orchestrator-request", tags=["orchestrator", "request"])
    try:
        reset_log()
        log_request("orchestrator/run", f"message={message!r} pdf={pdf_path!r}")

        graph = build_graph()
        result = await graph.ainvoke(
            {
                "user_request": message,
                "pdf_path": pdf_path,
                "structure_path": structure_path,
                "tasks": [],
                "current_task_index": 0,
                "task_results": [],
                "final_response": "",
                "error": None,
            }
        )

        final_response = result.get("final_response", "Orchestration completed.")
        task_results   = result.get("task_results", [])

        log_response("orchestrator/run", f"tasks_completed={len(task_results)}")
        end_trace(trace_context=trace, end_state="Success")

        return {
            "response": final_response,
            "task_results": task_results,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
