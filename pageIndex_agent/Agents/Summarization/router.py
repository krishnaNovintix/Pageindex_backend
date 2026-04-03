from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from typing import Any
import agentops
from agentops import start_trace, end_trace

from Agents.Summarization.graph import build_graph
from Agents.Summarization.logger import log_request, log_response, log_error

router = APIRouter(prefix="/summarization", tags=["summarization"])


def _to_str(v: Any) -> str:
    """Coerce a value to str — handles None, Gemini content-block lists, etc."""
    if v is None:
        return ""
    if isinstance(v, list):
        return " ".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in v
        ).strip()
    return str(v)


class TaskResultIn(BaseModel):
    topic: str = ""
    pageindex_result: str = ""
    mcp_result: str = ""

    @field_validator("topic", "pageindex_result", "mcp_result", mode="before")
    @classmethod
    def coerce_to_str(cls, v: Any) -> str:  # noqa: N805
        return _to_str(v)


class SummarizationRequest(BaseModel):
    user_request: str
    task_results: list[TaskResultIn]


class SummarizationResponse(BaseModel):
    summary: str


@router.post("/run", response_model=SummarizationResponse)
async def run_summarization(body: SummarizationRequest):
    """
    Summarization agent endpoint.  Accepts the user's original request and all
    per-task retrieved results, then returns a single coherent Markdown summary.
    """
    trace = start_trace(
        trace_name="summarization-request",
        tags=["summarization", "request"],
    )
    try:
        log_request(
            "summarization/run",
            f"user_request={body.user_request!r} tasks={len(body.task_results)}",
        )

        graph = build_graph()
        result = await graph.ainvoke(
            {
                "user_request": body.user_request,
                "task_results": [tr.model_dump() for tr in body.task_results],
                "summary": "",
                "error": None,
            }
        )

        summary: str = result.get("summary", "")
        error: Any = result.get("error")

        if error:
            log_error("summarization/run", str(error))
            end_trace(trace_context=trace, end_state="Fail")
            raise HTTPException(status_code=500, detail=f"Summarization error: {error}")

        log_response("summarization/run", f"summary_length={len(summary)}")
        end_trace(trace_context=trace, end_state="Success")
        return JSONResponse(content={"summary": summary})

    except HTTPException:
        raise
    except Exception as exc:
        log_error("summarization/run", str(exc))
        end_trace(trace_context=trace, end_state="Fail")
        raise HTTPException(status_code=500, detail=f"Summarization error: {exc}")
