from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import agentops
from agentops import start_trace, end_trace

from Agents.Orchestrator.graph import build_graph
from Agents.Orchestrator.logger import log_request, log_response, log_error, reset_log

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


class OrchestratorRequest(BaseModel):
    message: str
    pdf_path: str
    structure_path: str


class TaskResultOut(BaseModel):
    topic: str
    pageindex_result: str
    mcp_result: str


class OrchestratorResponse(BaseModel):
    response: str
    task_results: list[TaskResultOut]


@router.post("/run", response_model=OrchestratorResponse)
async def run_orchestrator(body: OrchestratorRequest):
    """
    High-level orchestration endpoint. Starts a new AgentOps session
    for every request so each run is independently tracked.
    """
    trace = start_trace(trace_name="orchestrator-request", tags=["orchestrator", "request"])
    try:
        reset_log()
        log_request(
            "orchestrator/run",
            f"message={body.message!r} pdf={body.pdf_path!r}",
        )

        graph = build_graph()
        result = await graph.ainvoke(
            {
                "user_request": body.message,
                "pdf_path": body.pdf_path,
                "structure_path": body.structure_path,
                "tasks": [],
                "current_task_index": 0,
                "task_results": [],
                "final_response": "",
                "error": None,
            }
        )

        final_response: str = result.get("final_response", "Orchestration completed.")
        task_results: list = result.get("task_results", [])

        log_response(
            "orchestrator/run",
            f"tasks_completed={len(task_results)}",
        )

        end_trace(trace_context=trace, end_state="Success")
        return JSONResponse(
            content={
                "response": final_response,
                "task_results": task_results,
            }
        )

    except Exception as exc:
        log_error("router/run", str(exc))
        end_trace(trace_context=trace, end_state="Fail")
        raise HTTPException(status_code=500, detail=f"Orchestrator error: {exc}")
