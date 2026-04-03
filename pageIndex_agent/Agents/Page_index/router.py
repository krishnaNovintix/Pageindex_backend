import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
import agentops
from agentops import start_trace, end_trace
from Agents.Page_index.graph import get_agent
from Agents.Page_index.logger import log_request, log_response, log_error, reset_log

router = APIRouter(prefix="/pageindex", tags=["pageindex"])


class AgentRequest(BaseModel):
    message: str


class AgentResponse(BaseModel):
    response: str


@router.post("/run", response_model=AgentResponse)
async def run_agent(body: AgentRequest):
    """
    Send a natural language message to the PageIndex agent.

    The agent decides whether to index a PDF or retrieve content from one
    based on your message, calls the appropriate tool, and returns the result.

    Examples:
    - "Index the PDF at /docs/report.pdf and save the structure to /docs/index/"
    - "What does chapter 3 say about climate change? PDF: /docs/report.pdf, structure: /docs/index/report.json"
    """
    trace = start_trace(trace_name="pageindex-request", tags=["pageindex", "request"])
    try:
        reset_log()
        log_request("agent/run", f"message={body.message!r}")

        result = await asyncio.to_thread(
            get_agent().invoke,
            {"messages": [HumanMessage(content=body.message)]}
        )

        ai_message = result["messages"][-1]
        raw_content = ai_message.content
        # Gemini may return a list of content blocks instead of a plain string
        if isinstance(raw_content, list):
            response_text = " ".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in raw_content
            ).strip()
        else:
            response_text = raw_content or ""

        log_response("agent/run", f"response={response_text[:120]!r}")
        end_trace(trace_context=trace, end_state="Success")
        return JSONResponse(content={"response": response_text})

    except Exception as e:
        log_error("router/run", str(e))
        end_trace(trace_context=trace, end_state="Fail")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
